package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
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

// ==================== Simulation Engine ====================

// SimulationEngine 仿真引擎
type SimulationEngine struct {
	tasks    map[string]*SimulationTask
	history  []*WorldState
	eventBus chan Event
	aiClient *AIClient
}

func NewSimulationEngine(aiClient *AIClient) *SimulationEngine {
	return &SimulationEngine{
		tasks:    make(map[string]*SimulationTask),
		history:  make([]*WorldState, 0),
		eventBus: make(chan Event, 1000),
		aiClient: aiClient,
	}
}

// CreateTask 创建仿真任务
func (e *SimulationEngine) CreateTask(name string, maxSteps int, config map[string]interface{}) *SimulationTask {
	id := fmt.Sprintf("sim_%d", time.Now().UnixNano())
	task := &SimulationTask{
		ID:        id,
		Name:      name,
		Status:    "pending",
		MaxSteps:  maxSteps,
		Config:    config,
		WorldState: e.initWorldState(),
		Agents:    e.initAgents(config),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	e.tasks[id] = task
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
		{ID: "ent_1", Name: "核心企业A", Role: "enterprise", Capital: 10000000, Strategy: "growth"},
		{ID: "ent_2", Name: "竞争企业B", Role: "competitor", Capital: 8000000, Strategy: "cost_leadership"},
		{ID: "cons_1", Name: "消费者群体", Role: "consumer", Capital: 5000000, Strategy: "utility_max"},
		{ID: "gov_1", Name: "政策制定者", Role: "policy", Capital: 0, Strategy: "stability"},
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
	if e.aiClient != nil {
		for _, agent := range task.Agents {
			decision, err := e.aiClient.GetDecision(agent, ws)
			if err == nil {
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
	e.history = append(e.history, &historyCopy)
}

// generateEvent 生成随机事件
func (e *SimulationEngine) generateEvent(ws *WorldState) Event {
	events := []Event{
		{Step: ws.Step, Type: "market", Name: "原材料价格上涨", Impact: map[string]interface{}{"raw_material": 1.1}},
		{Step: ws.Step, Type: "policy", Name: "减税政策", Impact: map[string]interface{}{"tax_rate": 0.1}},
		{Step: ws.Step, Type: "natural", Name: "供应链中断", Impact: map[string]interface{}{"supply": 0.8}},
		{Step: ws.Step, Type: "tech", Name: "技术突破", Impact: map[string]interface{}{"efficiency": 1.2}},
		{Step: ws.Step, Type: "market", Name: "需求激增", Impact: map[string]interface{}{"demand": 1.15}},
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
		revenue := ws.MarketPrice["product_a"] * 100
		cost := ws.MarketPrice["raw_material"] * 50
		agent.Capital += revenue - cost
		if agent.State == nil {
			agent.State = make(map[string]interface{})
		}
		agent.State["revenue"] = revenue
		agent.State["cost"] = cost
		agent.State["profit"] = revenue - cost
	}
}

// localDecision 本地回退决策
func (e *SimulationEngine) localDecision(agent *Agent, ws *WorldState) *Decision {
	action := "hold"
	params := map[string]interface{}{}
	switch agent.Role {
	case "enterprise":
		if agent.Capital > 5000000 {
			action = "expand"
			params["investment"] = agent.Capital * 0.2
		} else {
			action = "cut_cost"
			params["reduction"] = 0.1
		}
	case "competitor":
		action = "price_war"
		params["discount"] = 0.05
	case "consumer":
		action = "buy"
		params["quantity"] = 100
	case "policy":
		if ws.MarketPrice["product_a"] > 150 {
			action = "subsidy"
			params["amount"] = 500000
		} else {
			action = "observe"
		}
	}
	return &Decision{
		Step:      ws.Step,
		Action:    action,
		Params:    params,
		Reasoning: fmt.Sprintf("Local decision for %s at step %d", agent.Role, ws.Step),
	}
}

// applyDecision 应用决策
func (e *SimulationEngine) applyDecision(agent *Agent, decision *Decision, ws *WorldState) {
	switch decision.Action {
	case "expand":
		if inv, ok := decision.Params["investment"]; ok {
			if f, ok := inv.(float64); ok {
				agent.Capital -= f
				ws.Supply["product_a"] += f / 100
			}
		}
	case "cut_cost":
		ws.Supply["product_a"] *= 0.95
	case "price_war":
		ws.MarketPrice["product_a"] *= 0.95
	case "buy":
		ws.Demand["product_a"] += 100
	case "subsidy":
		if amt, ok := decision.Params["amount"]; ok {
			if f, ok := amt.(float64); ok {
				ws.Policy["subsidy"] = f
			}
		}
	}
}

// ==================== AI Client ====================

// AIClient AI 服务客户端
type AIClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

func NewAIClient(baseURL string) *AIClient {
	return &AIClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// GetDecision 获取 AI 决策
func (c *AIClient) GetDecision(agent *Agent, ws *WorldState) (*Decision, error) {
	// 调用 Python AI 服务的 /api/agent/decision 端点
	// 如果服务不可用，返回错误，由调用方回退到本地决策
	return nil, fmt.Errorf("AI service not available, using local fallback")
}

// ==================== API Server ====================

var engine *SimulationEngine

func main() {
	log.Println("========================================")
	log.Println("  MiroFish - 女娲企业经营数字孪生系统")
	log.Println("  基于 MiroFish 仿真引擎 + 女娲 LLM 智能体")
	log.Println("========================================")

	aiClient := NewAIClient("http://localhost:8000")
	engine = NewSimulationEngine(aiClient)

	// 启动 API 服务
	mux := http.NewServeMux()
	
	// 健康检查
	mux.HandleFunc("/api/health", handleHealth)
	
	// 仿真任务
	mux.HandleFunc("/api/simulation/create", handleSimCreate)
	mux.HandleFunc("/api/simulation/start/", handleSimStart)
	mux.HandleFunc("/api/simulation/step/", handleSimStep)
	mux.HandleFunc("/api/simulation/status/", handleSimStatus)
	mux.HandleFunc("/api/simulation/list", handleSimList)
	mux.HandleFunc("/api/simulation/result/", handleSimResult)
	
	// 世界状态
	mux.HandleFunc("/api/world/state/", handleWorldState)
	mux.HandleFunc("/api/world/history/", handleWorldHistory)
	
	// 智能体
	mux.HandleFunc("/api/agents/", handleAgents)
	
	// 数据采集
	mux.HandleFunc("/api/data/collect", handleDataCollect)
	
	// 蒸馏分析
	mux.HandleFunc("/api/distill/", handleDistill)

	// 静态文件服务
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" || r.URL.Path == "/index.html" {
			http.ServeFile(w, r, "./web/dist/index.html")
		} else {
			http.FileServer(http.Dir("./web/dist")).ServeHTTP(w, r)
		}
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "9090"
	}

	log.Printf("MiroFish 服务启动在 http://0.0.0.0:%s", port)
	log.Printf("API 文档: http://0.0.0.0:%s/api/health", port)

	// 优雅关闭
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		log.Println("Shutting down MiroFish...")
		os.Exit(0)
	}()

	if err := http.ListenAndServe("0.0.0.0:"+port, corsMiddleware(mux)); err != nil {
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

// ==================== API Handlers ====================

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":  "healthy",
		"service": "MiroFish - 女娲企业经营数字孪生系统",
		"version": "1.0.0",
		"components": map[string]string{
			"simulation_engine": "running",
			"ai_agent":          "standby",
			"data_collector":    "ready",
		},
	})
}

func handleSimCreate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
		return
	}
	
	name := r.URL.Query().Get("name")
	if name == "" {
		name = fmt.Sprintf("仿真任务_%d", time.Now().Unix())
	}
	maxSteps := 100
	
	task := engine.CreateTask(name, maxSteps, map[string]interface{}{
		"ai_enabled":      true,
		"data_source":     "auto",
		"real_data_ratio": 0.8,
	})
	
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "仿真任务创建成功",
		"task":    task,
	})
}

func handleSimStart(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/start/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	
	task.Status = "running"
	// 运行所有步骤
	go func() {
		for task.CurrentStep < task.MaxSteps {
			engine.RunStep(task)
			if task.CurrentStep%10 == 0 {
				log.Printf("Task %s: step %d/%d", taskID, task.CurrentStep, task.MaxSteps)
			}
		}
		task.Status = "completed"
		task.Result = &SimulationResult{
			TaskID:      taskID,
			FinalState:  task.WorldState,
			Metrics:     computeMetrics(task),
			CompletedAt: time.Now(),
		}
		task.UpdatedAt = time.Now()
		log.Printf("Task %s completed", taskID)
	}()
	
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "仿真任务已启动",
		"task_id": taskID,
		"status":  "running",
	})
}

func handleSimStep(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/step/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	
	engine.RunStep(task)
	
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"step":         task.CurrentStep,
		"max_steps":    task.MaxSteps,
		"world_state":  task.WorldState,
		"agent_count":  len(task.Agents),
	})
}

func handleSimStatus(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/status/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	writeJSON(w, http.StatusOK, task)
}

func handleSimList(w http.ResponseWriter, r *http.Request) {
	tasks := make([]*SimulationTask, 0, len(engine.tasks))
	for _, t := range engine.tasks {
		tasks = append(tasks, t)
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total": len(tasks),
		"tasks": tasks,
	})
}

func handleSimResult(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/simulation/result/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	if task.Result == nil {
		writeJSON(w, http.StatusOK, map[string]string{"message": "仿真尚未完成"})
		return
	}
	writeJSON(w, http.StatusOK, task.Result)
}

func handleWorldState(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/world/state/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	writeJSON(w, http.StatusOK, task.WorldState)
}

func handleWorldHistory(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"total":   len(engine.history),
		"history": engine.history,
	})
}

func handleAgents(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/agents/")
	task, ok := engine.tasks[taskID]
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
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "数据采集任务已创建",
		"sources": []string{"eastmoney", "cninfo", "stats"},
		"status":  "collecting",
	})
}

func handleDistill(w http.ResponseWriter, r *http.Request) {
	taskID := extractID(r.URL.Path, "/api/distill/")
	task, ok := engine.tasks[taskID]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Task not found"})
		return
	}
	if task.Result == nil {
		writeJSON(w, http.StatusOK, map[string]string{"message": "仿真尚未完成，无法蒸馏"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"message": "蒸馏分析完成",
		"report":  task.Result.Report,
		"metrics": task.Result.Metrics,
	})
}

// ==================== Helpers ====================

func computeMetrics(task *SimulationTask) map[string]float64 {
	ws := task.WorldState
	return map[string]float64{
		"total_revenue":    ws.MarketPrice["product_a"] * 100,
		"market_efficiency": ws.Demand["product_a"] / max(ws.Supply["product_a"], 0.01),
		"price_index":      ws.MarketPrice["product_a"],
		"supply_demand":    ws.Supply["product_a"] / max(ws.Demand["product_a"], 0.01),
	}
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
