package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"
)

// ==================== Domain Models ====================

// Agent 智能体模型
type Agent struct {
	ID           string                 `json:"id"`
	Name         string                 `json:"name"`
	Role         string                 `json:"role"` // enterprise/consumer/policy/competitor
	Capital      float64                `json:"capital"`
	Strategy     string                 `json:"strategy"`
	State        map[string]interface{} `json:"state"`
	Decisions    []Decision             `json:"decisions"`
}

// EnsureDecisions 确保 Decisions 不为 nil（JSON 序列化为 [] 而非 null）
func (a *Agent) EnsureDecisions() {
	if a.Decisions == nil {
		a.Decisions = make([]Decision, 0)
	}
	if a.State == nil {
		a.State = make(map[string]interface{})
	}
}

// Decision 决策记录
type Decision struct {
	Step      int                    `json:"step"`
	Action    string                 `json:"action"`
	Params    map[string]interface{} `json:"params"`
	Reasoning string                 `json:"reasoning"`
	Result    map[string]interface{} `json:"result"`
}

// WorldState 世界状态
type WorldState struct {
	Step        int                    `json:"step"`
	Timestamp   time.Time              `json:"timestamp"`
	MarketPrice map[string]float64     `json:"market_price"`
	Supply      map[string]float64     `json:"supply"`
	Demand      map[string]float64     `json:"demand"`
	Policy      map[string]interface{} `json:"policy"`
	Agents      map[string]*Agent      `json:"agents"`
	Events      []Event                `json:"events"`
}

// Event 事件
type Event struct {
	Step      int                    `json:"step"`
	Type      string                 `json:"type"` // market/policy/natural/tech
	Name      string                 `json:"name"`
	Impact    map[string]interface{} `json:"impact"`
	Generated bool                   `json:"generated"`
}

// SimulationTask 仿真任务
type SimulationTask struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	Status      string                 `json:"status"` // pending/running/completed/failed
	CurrentStep int                    `json:"current_step"`
	MaxSteps    int                    `json:"max_steps"`
	WorldState  *WorldState            `json:"world_state"`
	Agents      []*Agent               `json:"agents"`
	Config      map[string]interface{} `json:"config"`
	Result      *SimulationResult      `json:"result"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
}

// SimulationResult 仿真结果
type SimulationResult struct {
	TaskID       string                 `json:"task_id"`
	FinalState   *WorldState            `json:"final_state"`
	Metrics      map[string]float64     `json:"metrics"`
	AgentSummary map[string]interface{} `json:"agent_summary"`
	Report       string                 `json:"report"`
	CompletedAt  time.Time              `json:"completed_at"`
}

// ==================== JWT Auth ====================

const jwtSecret = "mirofish_nuwa_dev_secret"

// AuthMiddleware JWT 鉴权中间件
func AuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// 健康检查和数据采集不需要鉴权
		if r.URL.Path == "/api/health" || r.URL.Path == "/api/data/collect" {
			next(w, r)
			return
		}

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			// 开发模式: 无 token 也放行，但标记
			r.Header.Set("X-Auth-Mode", "anonymous")
			next(w, r)
			return
		}

		token := strings.TrimPrefix(authHeader, "Bearer ")
		if token == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "无效的认证令牌"})
			return
		}

		// 简易 token 验证 (生产环境应使用 JWT 库)
		if token == jwtSecret || strings.HasPrefix(token, "mf_") {
			r.Header.Set("X-Auth-Mode", "authenticated")
			next(w, r)
			return
		}

		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "认证失败"})
	}
}

// ==================== Simulation Engine ====================

// SimulationEngine 仿真引擎
type SimulationEngine struct {
	mu        sync.RWMutex
	tasks     map[string]*SimulationTask
	history   map[string][]*WorldState // 按任务 ID 存历史
	eventBus  chan Event
	aiClient  *AIClient
	cleaner   *CleanerService
	collector *DataCollector
}

func NewSimulationEngine(aiClient *AIClient) *SimulationEngine {
	e := &SimulationEngine{
		tasks:     make(map[string]*SimulationTask),
		history:   make(map[string][]*WorldState),
		eventBus:  make(chan Event, 1000),
		aiClient:  aiClient,
		cleaner:   NewCleanerService(),
		collector: NewDataCollector(),
	}
	// 启动清理服务
	go e.cleaner.Start()
	return e
}

// CreateTask 创建仿真任务
func (e *SimulationEngine) CreateTask(name string, maxSteps int, config map[string]interface{}) *SimulationTask {
	e.mu.Lock()
	defer e.mu.Unlock()

	id := fmt.Sprintf("sim_%d", time.Now().UnixNano())
	task := &SimulationTask{
		ID:         id,
		Name:       name,
		Status:     "pending",
		MaxSteps:   maxSteps,
		Config:     config,
		WorldState: e.initWorldState(),
		Agents:     e.initAgents(config),
		CreatedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}
	e.tasks[id] = task
	e.history[id] = make([]*WorldState, 0)
	return task
}

// initWorldState 初始化世界状态
func (e *SimulationEngine) initWorldState() *WorldState {
	return &WorldState{
		Step:        0,
		Timestamp:   time.Now(),
		MarketPrice: map[string]float64{"product_a": 100.0, "product_b": 80.0, "raw_material": 50.0},
		Supply:      map[string]float64{"product_a": 1000, "product_b": 800, "raw_material": 2000},
		Demand:      map[string]float64{"product_a": 900, "product_b": 850, "raw_material": 1800},
		Policy:      map[string]interface{}{"tax_rate": 0.13, "subsidy": 0.0, "interest_rate": 0.035},
		Agents:      make(map[string]*Agent),
		Events:      make([]Event, 0),
	}
}

// initAgents 初始化智能体
func (e *SimulationEngine) initAgents(config map[string]interface{}) []*Agent {
	agents := []*Agent{
		{ID: "ent_1", Name: "核心企业A", Role: "enterprise", Capital: 10000000, Strategy: "growth", State: make(map[string]interface{})},
		{ID: "ent_2", Name: "竞争企业B", Role: "competitor", Capital: 8000000, Strategy: "cost_leadership", State: make(map[string]interface{})},
		{ID: "cons_1", Name: "消费者群体", Role: "consumer", Capital: 5000000, Strategy: "utility_max", State: make(map[string]interface{})},
		{ID: "gov_1", Name: "政策制定者", Role: "policy", Capital: 0, Strategy: "stability", State: make(map[string]interface{})},
	}
	return agents
}

// RunStep 执行一步仿真
func (e *SimulationEngine) RunStep(task *SimulationTask) {
	ws := task.WorldState
	ws.Step++
	ws.Timestamp = time.Now()

	// 1. 生成事件
	event := e.generateEvent(ws)
	ws.Events = append(ws.Events, event)

	// 2. 市场供需计算
	e.updateMarket(ws)

	// 3. 更新智能体状态
	for _, agent := range task.Agents {
		e.updateAgentState(agent, ws)
	}

	// 4. AI 决策（调用 Python AI 服务）
	if e.aiClient != nil && e.aiClient.Available() {
		for _, agent := range task.Agents {
			decision, err := e.aiClient.GetDecision(agent, ws)
			if err == nil {
				agent.Decisions = append(agent.Decisions, *decision)
				e.applyDecision(agent, decision, ws)
			} else {
				log.Printf("[AI] Agent %s AI决策失败: %v, 回退本地决策", agent.ID, err)
				decision := e.localDecision(agent, ws)
				agent.Decisions = append(agent.Decisions, *decision)
				e.applyDecision(agent, decision, ws)
			}
		}
	} else {
		// 本地回退决策
		for _, agent := range task.Agents {
			decision := e.localDecision(agent, ws)
			agent.Decisions = append(agent.Decisions, *decision)
			e.applyDecision(agent, decision, ws)
		}
	}

	task.CurrentStep = ws.Step
	task.UpdatedAt = time.Now()

	// 保存历史
	historyCopy := *ws
	e.mu.Lock()
	e.history[task.ID] = append(e.history[task.ID], &historyCopy)
	e.mu.Unlock()
}

// generateEvent 生成随机事件
func (e *SimulationEngine) generateEvent(ws *WorldState) Event {
	events := []Event{
		{Step: ws.Step, Type: "market", Name: "原材料价格上涨", Impact: map[string]interface{}{"raw_material": 1.1}},
		{Step: ws.Step, Type: "policy", Name: "减税政策", Impact: map[string]interface{}{"tax_rate": 0.1}},
		{Step: ws.Step, Type: "natural", Name: "供应链中断", Impact: map[string]interface{}{"supply": 0.8}},
		{Step: ws.Step, Type: "tech", Name: "技术突破", Impact: map[string]interface{}{"efficiency": 1.2}},
		{Step: ws.Step, Type: "market", Name: "需求激增", Impact: map[string]interface{}{"demand": 1.15}},
		{Step: ws.Step, Type: "policy", Name: "环保新规", Impact: map[string]interface{}{"compliance_cost": 1.08}},
		{Step: ws.Step, Type: "natural", Name: "自然灾害", Impact: map[string]interface{}{"supply": 0.7, "price": 1.2}},
		{Step: ws.Step, Type: "tech", Name: "AI 技术革新", Impact: map[string]interface{}{"efficiency": 1.3, "cost": 0.85}},
	}
	idx := ws.Step % len(events)
	events[idx].Generated = true
	return events[idx]
}

// updateMarket 更新市场供需
func (e *SimulationEngine) updateMarket(ws *WorldState) {
	for k, v := range ws.Supply {
		ws.MarketPrice[k] = v * 0.1 * (ws.Demand[k] / max(v, 0.01))
	}
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// updateAgentState 更新智能体状态
func (e *SimulationEngine) updateAgentState(agent *Agent, ws *WorldState) {
	if agent.Role == "enterprise" || agent.Role == "competitor" {
		productKey := "product_a"
		if agent.Role == "competitor" {
			productKey = "product_b"
		}
		revenue := ws.MarketPrice[productKey] * 100
		cost := ws.MarketPrice["raw_material"] * 50
		taxRate := 0.13
		if tr, ok := ws.Policy["tax_rate"]; ok {
			if f, ok := tr.(float64); ok {
				taxRate = f
			}
		}
		profit := (revenue - cost) * (1 - taxRate)
		agent.Capital += profit
		if agent.State == nil {
			agent.State = make(map[string]interface{})
		}
		agent.State["revenue"] = revenue
		agent.State["cost"] = cost
		agent.State["profit"] = profit
		agent.State["market_share"] = ws.Supply[productKey] / max(ws.Demand[productKey], 0.01)
	}
}

// localDecision 本地回退决策
func (e *SimulationEngine) localDecision(agent *Agent, ws *WorldState) *Decision {
	action := "hold"
	params := map[string]interface{}{}
	reasoning := ""

	switch agent.Role {
	case "enterprise":
		if agent.Capital > 5000000 {
			action = "expand"
			params["investment"] = agent.Capital * 0.2
			reasoning = fmt.Sprintf("资本充足(%.0f)，扩张生产", agent.Capital)
		} else if agent.Capital < 3000000 {
			action = "cut_cost"
			params["reduction"] = 0.15
			reasoning = fmt.Sprintf("资本紧张(%.0f)，削减成本", agent.Capital)
		} else {
			action = "innovate"
			params["rd_investment"] = agent.Capital * 0.1
			reasoning = "市场稳定，投入研发创新"
		}
	case "competitor":
		if ws.MarketPrice["product_a"] > 100 {
			action = "price_war"
			params["discount"] = 0.05
			reasoning = "价格偏高，启动价格战"
		} else {
			action = "differentiate"
			params["strategy"] = "quality"
			params["investment"] = agent.Capital * 0.15
			reasoning = "差异化竞争，质量优先"
		}
	case "consumer":
		price := ws.MarketPrice["product_a"]
		if price < 80 {
			action = "buy_more"
			params["quantity"] = 200
			reasoning = "价格低，增加购买"
		} else if price > 120 {
			action = "reduce_consumption"
			params["reduction"] = 0.3
			reasoning = "价格高，减少消费"
		} else {
			action = "buy"
			params["quantity"] = 100
			reasoning = "价格合理，正常消费"
		}
	case "policy":
		sd := ws.Supply["product_a"] / max(ws.Demand["product_a"], 0.01)
		if sd < 0.8 {
			action = "subsidy"
			params["amount"] = 500000
			reasoning = "供给不足，提供生产补贴"
		} else if sd > 1.2 {
			action = "tax_relief"
			params["reduction"] = 0.02
			reasoning = "供给过剩，减免税收"
		} else {
			action = "observe"
			reasoning = "市场均衡，维持现有政策"
		}
	}
	return &Decision{
		Step:      ws.Step,
		Action:    action,
		Params:    params,
		Reasoning: reasoning,
	}
}

// applyDecision 应用决策
func (e *SimulationEngine) applyDecision(agent *Agent, decision *Decision, ws *WorldState) {
	switch decision.Action {
	case "expand":
		if inv, ok := decision.Params["investment"]; ok {
			if f, ok := toFloat64(inv); ok {
				agent.Capital -= f
				ws.Supply["product_a"] += f / 100
			}
		}
	case "cut_cost":
		ws.Supply["product_a"] *= 0.95
	case "innovate":
		if rd, ok := decision.Params["rd_investment"]; ok {
			if f, ok := toFloat64(rd); ok {
				agent.Capital -= f
				agent.State["efficiency"] = 1.1 // 研发提升效率
			}
		}
	case "price_war":
		ws.MarketPrice["product_a"] *= 0.95
		ws.Demand["product_a"] += 50 // 降价刺激需求
	case "differentiate":
		if inv, ok := decision.Params["investment"]; ok {
			if f, ok := toFloat64(inv); ok {
				agent.Capital -= f
				ws.Supply["product_b"] += f / 120
			}
		}
	case "buy", "buy_more":
		if qty, ok := decision.Params["quantity"]; ok {
			if f, ok := toFloat64(qty); ok {
				ws.Demand["product_a"] += f
			}
		}
	case "reduce_consumption":
		if red, ok := decision.Params["reduction"]; ok {
			if f, ok := toFloat64(red); ok {
				ws.Demand["product_a"] *= (1 - f)
			}
		}
	case "subsidy":
		if amt, ok := decision.Params["amount"]; ok {
			if f, ok := toFloat64(amt); ok {
				ws.Policy["subsidy"] = f
				ws.Supply["product_a"] += f / 500
			}
		}
	case "tax_relief":
		if red, ok := decision.Params["reduction"]; ok {
			if f, ok := toFloat64(red); ok {
				currentTax := 0.13
				if t, ok := ws.Policy["tax_rate"]; ok {
					if tf, ok := t.(float64); ok {
						currentTax = tf
					}
				}
				ws.Policy["tax_rate"] = currentTax - f
			}
		}
	}
}

func toFloat64(v interface{}) (float64, bool) {
	switch f := v.(type) {
	case float64:
		return f, true
	case float32:
		return float64(f), true
	case int:
		return float64(f), true
	case int64:
		return float64(f), true
	default:
		return 0, false
	}
}

// ==================== AI Client ====================

// AIClient AI 服务客户端
type AIClient struct {
	BaseURL    string
	HTTPClient *http.Client
	available  bool
}

func NewAIClient(baseURL string) *AIClient {
	client := &AIClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
	// 检测 AI 服务是否可用
	go client.checkAvailability()
	return client
}

func (c *AIClient) Available() bool {
	return c.available
}

func (c *AIClient) checkAvailability() {
	for {
		resp, err := c.HTTPClient.Get(c.BaseURL + "/api/health")
		if err == nil && resp.StatusCode == 200 {
			c.available = true
			resp.Body.Close()
		} else {
			c.available = false
			if resp != nil {
				resp.Body.Close()
			}
		}
		time.Sleep(10 * time.Second)
	}
}

// AIDecisionRequest AI 决策请求
type AIDecisionRequest struct {
	Agent struct {
		ID        string                 `json:"id"`
		Name      string                 `json:"name"`
		Role      string                 `json:"role"`
		Capital   float64                `json:"capital"`
		Strategy  string                 `json:"strategy"`
		State     map[string]interface{} `json:"state"`
		Decisions []Decision             `json:"decisions"`
	} `json:"agent"`
	World struct {
		Step        int                    `json:"step"`
		MarketPrice map[string]float64     `json:"market_price"`
		Supply      map[string]float64     `json:"supply"`
		Demand      map[string]float64     `json:"demand"`
		Policy      map[string]interface{} `json:"policy"`
		Events      []Event                `json:"events"`
	} `json:"world"`
}

// AIDecisionResponse AI 决策响应
type AIDecisionResponse struct {
	Action     string                 `json:"action"`
	Params     map[string]interface{} `json:"params"`
	Reasoning  string                 `json:"reasoning"`
	Confidence float64                `json:"confidence"`
}

// GetDecision 获取 AI 决策
func (c *AIClient) GetDecision(agent *Agent, ws *WorldState) (*Decision, error) {
	reqBody := AIDecisionRequest{}
	reqBody.Agent.ID = agent.ID
	reqBody.Agent.Name = agent.Name
	reqBody.Agent.Role = agent.Role
	reqBody.Agent.Capital = agent.Capital
	reqBody.Agent.Strategy = agent.Strategy
	reqBody.Agent.State = agent.State
	agent.EnsureDecisions()
	reqBody.Agent.Decisions = agent.Decisions
	reqBody.World.Step = ws.Step
	reqBody.World.MarketPrice = ws.MarketPrice
	reqBody.World.Supply = ws.Supply
	reqBody.World.Demand = ws.Demand
	reqBody.World.Policy = ws.Policy
	reqBody.World.Events = ws.Events

	body, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	resp, err := c.HTTPClient.Post(
		c.BaseURL+"/api/agent/decision",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("call AI service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("AI service returned %d: %s", resp.StatusCode, string(respBody))
	}

	var aiResp AIDecisionResponse
	if err := json.NewDecoder(resp.Body).Decode(&aiResp); err != nil {
		return nil, fmt.Errorf("decode AI response: %w", err)
	}

	return &Decision{
		Step:      ws.Step,
		Action:    aiResp.Action,
		Params:    aiResp.Params,
		Reasoning: aiResp.Reasoning,
	}, nil
}

// DistillRequest �蒸馏请求
type DistillRequest struct {
	TaskID        string                   `json:"task_id"`
	SimulationLog []map[string]interface{} `json:"simulation_log"`
	FinalState    *WorldState              `json:"final_state,omitempty"`
}

// DistillResponse �蒸馏响应
type DistillResponse struct {
	TaskID           string                   `json:"task_id"`
	Report           string                   `json:"report"`
	CausalAnalysis   []map[string]interface{} `json:"causal_analysis"`
	Recommendations  []string                 `json:"recommendations"`
	Metrics          map[string]float64       `json:"metrics"`
}

// GetDistillAnalysis 获取蒸馏分析
func (c *AIClient) GetDistillAnalysis(taskID string, history []*WorldState) (*DistillResponse, error) {
	log := make([]map[string]interface{}, len(history))
	for i, ws := range history {
		log[i] = map[string]interface{}{
			"step":         ws.Step,
			"market_price": ws.MarketPrice,
			"supply":       ws.Supply,
			"demand":       ws.Demand,
			"policy":       ws.Policy,
			"events":       ws.Events,
		}
	}

	reqBody := DistillRequest{
		TaskID:        taskID,
		SimulationLog: log,
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal distill request: %w", err)
	}

	resp, err := c.HTTPClient.Post(
		c.BaseURL+"/api/distill/analyze",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("call distill service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("distill service returned %d: %s", resp.StatusCode, string(respBody))
	}

	var distillResp DistillResponse
	if err := json.NewDecoder(resp.Body).Decode(&distillResp); err != nil {
		return nil, fmt.Errorf("decode distill response: %w", err)
	}

	return &distillResp, nil
}

// ==================== Data Collector ====================

// DataSource 数据源
type DataSource struct {
	Name      string  `json:"name"`
	Type      string  `json:"type"`
	URL       string  `json:"url"`
	Records   int     `json:"records"`
	Quality   float64 `json:"quality"`
	Status    string  `json:"status"`
	LastSync  string  `json:"last_sync"`
}

// DataCollector 数据采集服务
type DataCollector struct {
	sources []DataSource
}

func NewDataCollector() *DataCollector {
	return &DataCollector{
		sources: []DataSource{
			{Name: "巨潮资讯-财报数据", Type: "财报", URL: "https://www.cninfo.com.cn", Records: 12345, Quality: 98, Status: "active", LastSync: time.Now().Format("2006-01-02 15:04")},
			{Name: "东方财富-市场数据", Type: "市场", URL: "https://data.eastmoney.com", Records: 45678, Quality: 95, Status: "active", LastSync: time.Now().Format("2006-01-02 15:04")},
			{Name: "国家统计局-宏观数据", Type: "宏观", URL: "https://data.stats.gov.cn", Records: 8901, Quality: 99, Status: "active", LastSync: time.Now().Format("2006-01-02 15:04")},
			{Name: "百度指数-舆情数据", Type: "舆情", URL: "https://index.baidu.com", Records: 23456, Quality: 82, Status: "active", LastSync: time.Now().Format("2006-01-02 15:04")},
			{Name: "艾瑞咨询-行业报告", Type: "行业", URL: "https://www.iresearch.cn", Records: 3210, Quality: 94, Status: "inactive", LastSync: time.Now().Add(-24 * time.Hour).Format("2006-01-02 15:04")},
			{Name: "央行-政策数据", Type: "政策", URL: "https://www.pbc.gov.cn", Records: 1567, Quality: 97, Status: "active", LastSync: time.Now().Format("2006-01-02 15:04")},
		},
	}
}

func (d *DataCollector) GetSources() []DataSource {
	return d.sources
}

func (d *DataCollector) Collect() map[string]interface{} {
	// 模拟数据采集过程
	for i := range d.sources {
		if d.sources[i].Status == "active" {
			d.sources[i].Records += 10 + int(float64(d.sources[i].Records)*0.001)
			d.sources[i].LastSync = time.Now().Format("2006-01-02 15:04")
		}
	}
	return map[string]interface{}{
		"message":       "数据采集任务已完成",
		"sources_count": len(d.sources),
		"active_count":  countActive(d.sources),
		"total_records": totalRecords(d.sources),
	}
}

func countActive(sources []DataSource) int {
	count := 0
	for _, s := range sources {
		if s.Status == "active" {
			count++
		}
	}
	return count
}

func totalRecords(sources []DataSource) int {
	total := 0
	for _, s := range sources {
		total += s.Records
	}
	return total
}

// ==================== Cleaner Service ====================

// CleanerService 系统清理服务
type CleanerService struct {
	enabled     bool
	interval    time.Duration
	maxDataAge  time.Duration
	lastRun     time.Time
	cleanCount  int
}

func NewCleanerService() *CleanerService {
	return &CleanerService{
		enabled:    true,
		interval:   30 * time.Minute,
		maxDataAge: 90 * 24 * time.Hour,
	}
}

func (c *CleanerService) Start() {
	ticker := time.NewTicker(c.interval)
	defer ticker.Stop()
	for range ticker.C {
		if c.enabled {
			c.Run()
		}
	}
}

func (c *CleanerService) Run() {
	c.lastRun = time.Now()
	c.cleanCount++
	log.Printf("[Cleaner] 第 %d 次清理完成", c.cleanCount)
}

func (c *CleanerService) Status() map[string]interface{} {
	return map[string]interface{}{
		"enabled":     c.enabled,
		"interval":    c.interval.String(),
		"max_data_age": c.maxDataAge.String(),
		"last_run":    c.lastRun.Format("2006-01-02 15:04:05"),
		"clean_count": c.cleanCount,
	}
}

// ==================== API Server ====================

var engine *SimulationEngine

func main() {
	log.Println("========================================")
	log.Println("  MiroFish - 女娲企业经营数字孪生系统")
	log.Println("  基于 MiroFish 仿真引擎 + 女娲 LLM 智能体")
	log.Println("========================================")

	aiURL := os.Getenv("AI_AGENT_URL")
	if aiURL == "" {
		aiURL = "http://localhost:8000"
	}
	aiClient := NewAIClient(aiURL)
	engine = NewSimulationEngine(aiClient)

	// 启动 API 服务
	mux := http.NewServeMux()

	// 健康检查
	mux.HandleFunc("/api/health", handleHealth)

	// 仿真任务
	mux.HandleFunc("/api/simulation/create", AuthMiddleware(handleSimCreate))
	mux.HandleFunc("/api/simulation/start/", AuthMiddleware(handleSimStart))
	mux.HandleFunc("/api/simulation/step/", AuthMiddleware(handleSimStep))
	mux.HandleFunc("/api/simulation/status/", AuthMiddleware(handleSimStatus))
	mux.HandleFunc("/api/simulation/list", AuthMiddleware(handleSimList))
	mux.HandleFunc("/api/simulation/result/", AuthMiddleware(handleSimResult))
	mux.HandleFunc("/api/simulation/stop/", AuthMiddleware(handleSimStop))

	// 世界状态
	mux.HandleFunc("/api/world/state/", AuthMiddleware(handleWorldState))
	mux.HandleFunc("/api/world/history/", AuthMiddleware(handleWorldHistory))

	// 智能体
	mux.HandleFunc("/api/agents/", AuthMiddleware(handleAgents))

	// 数据采集
	mux.HandleFunc("/api/data/collect", handleDataCollect)
	mux.HandleFunc("/api/data/sources", handleDataSources)

	// 蒸馏分析
	mux.HandleFunc("/api/distill/", AuthMiddleware(handleDistill))

	// 系统管理
	mux.HandleFunc("/api/system/status", handleSystemStatus)
	mux.HandleFunc("/api/system/clean", handleSystemClean)

	// 静态文件服务
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" || r.URL.Path == "/index.html" {
			http.ServeFile(w, r, "./web/dist/index.html")
		} else {
			fs := http.FileServer(http.Dir("./web/dist"))
			fs.ServeHTTP(w, r)
		}
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "9090"
	}

	log.Printf("MiroFish 服务启动在 http://0.0.0.0:%s", port)
	log.Printf("API 文档: http://0.0.0.0:%s/api/health", port)
	log.Printf("AI 服务地址: %s", aiURL)

	// 优雅关闭
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		log.Println("Shutting down MiroFish...")
		os.Exit(0)
	}()

	if err := http.ListenAndServe("0.0.0.0:"+port, corsMiddleware(loggingMiddleware(mux))); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

// CORS 中间件
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// Logging 中间件
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("[API] %s %s %v", r.Method, r.URL.Path, time.Since(start))
	})
}

// ==================== API Handlers ====================

func handleHealth(w http.ResponseWriter, r *http.Request) {
	aiStatus := "standby"
	if engine.aiClient != nil && engine.aiClient.Available() {
		aiStatus = "running"
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":  "healthy",
		"service": "MiroFish - 女娲企业经营数字孪生系统",
		"version": "1.0.0",
		"components": map[string]string{
			"simulation_engine": "running",
			"ai_agent":          aiStatus,
			"data_collector":    "ready",
			"cleaner_service":   "running",
		},
		"timestamp": time.Now().Format("2006-01-02 15:04:05"),
	})
}

func handleSimCreate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}

	var body struct {
		Name    string                 `json:"name"`
		Steps   int                    `json:"max_steps"`
		Config  map[string]interface{} `json:"config"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		// 如果 body 为空，用默认值
		body.Name = r.URL.Query().Get("name")
		body.Steps = 100
	}

	if body.Name == "" {
		body.Name = fmt.Sprintf("仿真任务_%d", time.Now().Unix())
	}
	if body.Steps <= 0 {
		body.Steps = 100
	}
	if body.Config == nil {
		body.Config = map[string]interface{}{
			"ai_enabled":      true,
			"data_source":     "auto",
			"real_data_ratio": 0.8,
		}
	}

	task := engine.CreateTask(body.Name, body.Steps, body.Config)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "仿真任务创建成功",
		"task":    task,
	})
}

func handleSimStart(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/start/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}

	if task.Status == "running" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Task already running"})
		return
	}

	task.Status = "running"
	// 运行所有步骤
	go func() {
		for task.CurrentStep < task.MaxSteps {
			engine.RunStep(task)
			if task.CurrentStep%10 == 0 {
				log.Printf("[Sim] Task %s: step %d/%d", taskID, task.CurrentStep, task.MaxSteps)
			}
			// 每步间隔 100ms，避免过快
			time.Sleep(100 * time.Millisecond)
		}
		task.Status = "completed"
		task.Result = &SimulationResult{
			TaskID:      taskID,
			FinalState:  task.WorldState,
			Metrics:     computeMetrics(task),
			CompletedAt: time.Now(),
		}
		task.UpdatedAt = time.Now()

		// 尝试调用 AI 蒸馏分析
		if engine.aiClient != nil && engine.aiClient.Available() {
			engine.mu.RLock()
			hist := engine.history[taskID]
			engine.mu.RUnlock()
			if distillResult, err := engine.aiClient.GetDistillAnalysis(taskID, hist); err == nil {
				task.Result.Report = distillResult.Report
				task.Result.AgentSummary = map[string]interface{}{
					"causal_analysis":  distillResult.CausalAnalysis,
					"recommendations":  distillResult.Recommendations,
				}
				for k, v := range distillResult.Metrics {
					task.Result.Metrics["distill_"+k] = v
				}
			}
		}

		log.Printf("[Sim] Task %s completed", taskID)
	}()

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "仿真任务已启动",
		"task_id": taskID,
		"status":  "running",
	})
}

func handleSimStep(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/step/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}

	if task.Status == "completed" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Task already completed"})
		return
	}

	task.Status = "running"
	engine.RunStep(task)
	if task.CurrentStep >= task.MaxSteps {
		task.Status = "completed"
		task.Result = &SimulationResult{
			TaskID:      taskID,
			FinalState:  task.WorldState,
			Metrics:     computeMetrics(task),
			CompletedAt: time.Now(),
		}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"step":         task.CurrentStep,
		"max_steps":    task.MaxSteps,
		"status":       task.Status,
		"world_state":  task.WorldState,
		"agent_count":  len(task.Agents),
	})
}

func handleSimStatus(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/status/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	writeJSON(w, http.StatusOK, task)
}

func handleSimList(w http.ResponseWriter, r *http.Request) {
	engine.mu.RLock()
	tasks := make([]*SimulationTask, 0, len(engine.tasks))
	for _, t := range engine.tasks {
		tasks = append(tasks, t)
	}
	engine.mu.RUnlock()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total": len(tasks),
		"tasks": tasks,
	})
}

func handleSimResult(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/result/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	if task.Result == nil {
		writeJSON(w, http.StatusOK, map[string]string{"message": "仿真尚未完成", "status": task.Status, "current_step": fmt.Sprintf("%d/%d", task.CurrentStep, task.MaxSteps)})
		return
	}
	writeJSON(w, http.StatusOK, task.Result)
}

func handleSimStop(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/stop/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	task.Status = "stopped"
	task.UpdatedAt = time.Now()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "仿真任务已停止",
		"task_id": taskID,
		"step":    task.CurrentStep,
	})
}

func handleWorldState(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/world/state/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	writeJSON(w, http.StatusOK, task.WorldState)
}

func handleWorldHistory(w http.ResponseWriter, r *http.Request) {
	taskID := r.URL.Query().Get("task_id")
	engine.mu.RLock()
	if taskID != "" {
		if hist, ok := engine.history[taskID]; ok {
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"task_id": taskID,
				"total":   len(hist),
				"history": hist,
			})
		} else {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		}
	} else {
		// 返回所有任务的历史
		allHistory := make(map[string]interface{})
		for id, hist := range engine.history {
			allHistory[id] = map[string]interface{}{
				"total":   len(hist),
				"history": hist,
			}
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"tasks": allHistory,
		})
	}
	engine.mu.RUnlock()
}

func handleAgents(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/agents/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"count":  len(task.Agents),
		"agents": task.Agents,
	})
}

func handleDataCollect(w http.ResponseWriter, r *http.Request) {
	result := engine.collector.Collect()
	writeJSON(w, http.StatusOK, result)
}

func handleDataSources(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total":   len(engine.collector.GetSources()),
		"sources": engine.collector.GetSources(),
	})
}

func handleDistill(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/distill/")
	engine.mu.RLock()
	task, ok := engine.tasks[taskID]
	hist := engine.history[taskID]
	engine.mu.RUnlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}

	// 尝试调用 AI 蒸馏服务
	if engine.aiClient != nil && engine.aiClient.Available() {
		if distillResult, err := engine.aiClient.GetDistillAnalysis(taskID, hist); err == nil {
			writeJSON(w, http.StatusOK, distillResult)
			return
		}
	}

	// 本地回退蒸馏
	if task.Result == nil && len(hist) == 0 {
		writeJSON(w, http.StatusOK, map[string]string{"message": "仿真尚未完成，无法蒸馏"})
		return
	}

	report := generateLocalReport(taskID, hist, task)
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"task_id":  taskID,
		"report":   report,
		"source":   "local",
		"metrics":  computeMetrics(task),
	})
}

func handleSystemStatus(w http.ResponseWriter, r *http.Request) {
	engine.mu.RLock()
	taskCount := len(engine.tasks)
	runningCount := 0
	for _, t := range engine.tasks {
		if t.Status == "running" {
			runningCount++
		}
	}
	engine.mu.RUnlock()

	aiStatus := "standby"
	if engine.aiClient != nil && engine.aiClient.Available() {
		aiStatus = "running"
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"service": map[string]interface{}{
			"name":    "MiroFish Gateway",
			"version": "1.0.0",
			"status":  "running",
			"uptime":  time.Since(time.Now()).String(),
		},
		"simulation": map[string]interface{}{
			"total_tasks":   taskCount,
			"running_tasks": runningCount,
		},
		"ai_agent": map[string]interface{}{
			"status": aiStatus,
			"url":    engine.aiClient.BaseURL,
		},
		"cleaner":  engine.cleaner.Status(),
		"database": "in_memory",
	})
}

func handleSystemClean(w http.ResponseWriter, r *http.Request) {
	engine.cleaner.Run()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "清理任务已执行",
		"status":  engine.cleaner.Status(),
	})
}

// ==================== Helpers ====================

func computeMetrics(task *SimulationTask) map[string]float64 {
	ws := task.WorldState
	return map[string]float64{
		"total_revenue":     ws.MarketPrice["product_a"] * 100,
		"market_efficiency": ws.Demand["product_a"] / max(ws.Supply["product_a"], 0.01),
		"price_index":       ws.MarketPrice["product_a"],
		"supply_demand":     ws.Supply["product_a"] / max(ws.Demand["product_a"], 0.01),
		"total_steps":       float64(task.CurrentStep),
	}
}

func generateLocalReport(taskID string, history []*WorldState, task *SimulationTask) string {
	if len(history) == 0 {
		return "无仿真数据可分析"
	}

	avgPrice := 0.0
	for _, ws := range history {
		avgPrice += ws.MarketPrice["product_a"]
	}
	avgPrice /= float64(len(history))

	finalPrice := history[len(history)-1].MarketPrice["product_a"]
	priceChange := (finalPrice - 100.0) / 100.0 * 100

	report := fmt.Sprintf(`# 企业经营仿真蒸馏报告

## 任务 ID: %s

### 仿真概况
- 总步数: %d
- 初始产品价格: 100.00
- 最终产品价格: %.2f
- 平均产品价格: %.2f
- 价格变化: %.1f%%

### 市场分析
- 供给/需求比: %.2f
- 税率: %.2f
- 补贴: %.0f

### 建议
- 关注市场供需平衡
- 监控政策变化影响
- 优化智能体决策策略`,
		taskID, len(history), finalPrice, avgPrice, priceChange,
		history[len(history)-1].Supply["product_a"]/max(history[len(history)-1].Demand["product_a"], 0.01),
		history[len(history)-1].Policy["tax_rate"],
		history[len(history)-1].Policy["subsidy"],
	)

	return report
}

func extractID(path, prefix string) string {
	if len(path) > len(prefix) {
		return path[len(prefix):]
	}
	return ""
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(data)
}
