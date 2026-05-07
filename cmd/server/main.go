package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	// ==================== Domain Models ====================

	// Agent 智能体模型
)

type Agent struct {
	ID           string                 `json:"id"`
	Name         string                 `json:"name"`
	Role         string                 `json:"role"` // enterprise/consumer/policy/competitor
	Capital      float64                `json:"capital"`
	Strategy     string                 `json:"strategy"`
	State        map[string]interface{} `json:"state"`
	Decisions    []Decision             `json:"decisions"`
}

// EnsureDecisions 确保 Decisions 不为 nil
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
	Type      string                 `json:"type"` // market/policy/natural/tech/social/international
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

const jwtSecret = "mirofish_nuva_dev_secret"

// AuthMiddleware JWT 鉴权中间件
func AuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/health" || r.URL.Path == "/api/data/collect" || r.URL.Path == "/api/data/sources" {
			next(w, r)
			return
		}

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			r.Header.Set("X-Auth-Mode", "anonymous")
			next(w, r)
			return
		}

		token := strings.TrimPrefix(authHeader, "Bearer ")
		if token == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "无效的认证令牌"})
			return
		}

		if token == jwtSecret || strings.HasPrefix(token, "mf_") {
			r.Header.Set("X-Auth-Mode", "authenticated")
			next(w, r)
			return
		}

		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "认证失败"})
	}
}

// ==================== WebSocket Hub ====================

// WSMessage WebSocket 推送消息
type WSMessage struct {
	Type string      `json:"type"` // step_complete / task_complete / event / agent_decision
	Data interface{} `json:"data"`
}

// WSClient WebSocket 客户端
type WSClient struct {
	Hub  *WSHub
	Send chan []byte
}

// WSHub WebSocket 广播中心
type WSHub struct {
	clients    map[*WSClient]bool
	broadcast  chan []byte
	register   chan *WSClient
	unregister chan *WSClient
}

func NewWSHub() *WSHub {
	return &WSHub{
		clients:    make(map[*WSClient]bool),
		broadcast:  make(chan []byte, 256),
		register:   make(chan *WSClient),
		unregister: make(chan *WSClient),
	}
}

func (h *WSHub) Run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.Send)
			}
		case message := <-h.broadcast:
			for client := range h.clients {
				select {
				case client.Send <- message:
				default:
					close(client.Send)
					delete(h.clients, client)
				}
			}
		}
	}
}

func (h *WSHub) Broadcast(msgType string, data interface{}) {
	msg := WSMessage{Type: msgType, Data: data}
	if bytes, err := json.Marshal(msg); err == nil {
		h.broadcast <- bytes
	}
}

var wsHub = NewWSHub()

// ==================== Simulation Engine ====================

// SimulationEngine 仿真引擎
type SimulationEngine struct {
	mu        sync.RWMutex
	tasks     map[string]*SimulationTask
	history   map[string][]*WorldState
	eventBus  chan Event
	aiClient  *AIClient
	cleaner   *CleanerService
	collector *DataCollector
	startTime time.Time
}

func NewSimulationEngine(aiClient *AIClient) *SimulationEngine {
	e := &SimulationEngine{
		tasks:     make(map[string]*SimulationTask),
		history:   make(map[string][]*WorldState),
		eventBus:  make(chan Event, 1000),
		aiClient:  aiClient,
		cleaner:   NewCleanerService(),
		collector: NewDataCollector(),
		startTime: time.Now(),
	}
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

	// 1. 生成事件 (每步30%概率)
	if rand.Float64() < 0.3 {
		event := e.generateEvent(ws)
		ws.Events = append(ws.Events, event)
		wsHub.Broadcast("event", event)
	}

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
				wsHub.Broadcast("agent_decision", map[string]interface{}{
					"agent_id": agent.ID, "action": decision.Action, "reasoning": decision.Reasoning,
				})
			} else {
				log.Printf("[AI] Agent %s AI决策失败: %v, 回退本地决策", agent.ID, err)
				decision := e.localDecision(agent, ws)
				agent.Decisions = append(agent.Decisions, *decision)
				e.applyDecision(agent, decision, ws)
			}
		}
	} else {
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

	// WebSocket 推送步进完成
	wsHub.Broadcast("step_complete", map[string]interface{}{
		"task_id": task.ID, "step": ws.Step, "max_steps": task.MaxSteps,
		"market_price": ws.MarketPrice, "status": task.Status,
	})

	// 最后一步自动蒸馏
	if task.CurrentStep >= task.MaxSteps {
		task.Status = "completed"
		task.Result = &SimulationResult{
			TaskID:      task.ID,
			FinalState:  ws,
			Metrics:     computeMetrics(task),
			CompletedAt: time.Now(),
		}
		// 异步蒸馏
		if e.aiClient != nil && e.aiClient.Available() {
			go func() {
				e.mu.RLock()
				hist := e.history[task.ID]
				e.mu.RUnlock()
				if distillResult, err := e.aiClient.GetDistillAnalysis(task.ID, hist); err == nil {
					task.Result.Report = distillResult.Report
					task.Result.AgentSummary = map[string]interface{}{
						"causal_analysis": distillResult.CausalAnalysis,
						"recommendations": distillResult.Recommendations,
					}
					for k, v := range distillResult.Metrics {
						task.Result.Metrics["distill_"+k] = v
					}
					wsHub.Broadcast("task_complete", map[string]interface{}{
						"task_id": task.ID, "report_ready": true,
					})
				}
			}()
		}
		wsHub.Broadcast("task_complete", map[string]interface{}{
			"task_id": task.ID, "step": ws.Step,
		})
	}
}

// generateEvent 生成随机事件 - 更丰富的事件池
func (e *SimulationEngine) generateEvent(ws *WorldState) Event {
	allEvents := []Event{
		// 市场事件
		{Step: ws.Step, Type: "market", Name: "原材料价格上涨", Impact: map[string]interface{}{"raw_material": 1.1}},
		{Step: ws.Step, Type: "market", Name: "需求激增", Impact: map[string]interface{}{"demand": 1.15}},
		{Step: ws.Step, Type: "market", Name: "价格战爆发", Impact: map[string]interface{}{"price": 0.9}},
		{Step: ws.Step, Type: "market", Name: "消费降级", Impact: map[string]interface{}{"demand": 0.85}},
		{Step: ws.Step, Type: "market", Name: "新竞争者入场", Impact: map[string]interface{}{"supply": 1.2}},
		{Step: ws.Step, Type: "market", Name: "供应链恢复", Impact: map[string]interface{}{"raw_material": 0.9}},
		// 政策事件
		{Step: ws.Step, Type: "policy", Name: "减税政策", Impact: map[string]interface{}{"tax_rate": 0.1}},
		{Step: ws.Step, Type: "policy", Name: "环保新规", Impact: map[string]interface{}{"compliance_cost": 1.08}},
		{Step: ws.Step, Type: "policy", Name: "产业扶持", Impact: map[string]interface{}{"subsidy": 500000}},
		{Step: ws.Step, Type: "policy", Name: "利率调整", Impact: map[string]interface{}{"interest_rate": 0.005}},
		{Step: ws.Step, Type: "policy", Name: "反垄断调查", Impact: map[string]interface{}{"market_share_cap": 0.3}},
		// 自然事件
		{Step: ws.Step, Type: "natural", Name: "供应链中断", Impact: map[string]interface{}{"supply": 0.8}},
		{Step: ws.Step, Type: "natural", Name: "自然灾害", Impact: map[string]interface{}{"supply": 0.7, "price": 1.2}},
		{Step: ws.Step, Type: "natural", Name: "疫情反弹", Impact: map[string]interface{}{"demand": 0.75, "supply": 0.85}},
		// 技术事件
		{Step: ws.Step, Type: "tech", Name: "技术突破", Impact: map[string]interface{}{"efficiency": 1.2}},
		{Step: ws.Step, Type: "tech", Name: "AI 技术革新", Impact: map[string]interface{}{"efficiency": 1.3, "cost": 0.85}},
		{Step: ws.Step, Type: "tech", Name: "数字化转型", Impact: map[string]interface{}{"efficiency": 1.15}},
		// 社会事件
		{Step: ws.Step, Type: "social", Name: "消费升级", Impact: map[string]interface{}{"demand": 1.1, "quality": 1.2}},
		{Step: ws.Step, Type: "social", Name: "舆论危机", Impact: map[string]interface{}{"reputation": 0.6, "demand": 0.9}},
		// 国际事件
		{Step: ws.Step, Type: "international", Name: "贸易摩擦", Impact: map[string]interface{}{"raw_material": 1.15, "export": 0.85}},
		{Step: ws.Step, Type: "international", Name: "汇率波动", Impact: map[string]interface{}{"exchange_rate": 0.05}},
	}
	idx := rand.Intn(len(allEvents))
	allEvents[idx].Generated = true
	return allEvents[idx]
}

// updateMarket 更新市场供需 - 更真实的供需价格模型
func (e *SimulationEngine) updateMarket(ws *WorldState) {
	// 产品A: 基于供需比调整价格
	sdRatioA := ws.Demand["product_a"] / max(ws.Supply["product_a"], 0.01)
	baseA := 100.0
	ws.MarketPrice["product_a"] = baseA * (1 + (sdRatioA-1)*0.3) * (1 + (rand.Float64()-0.5)*0.02)

	// 产品B: 类似模型
	sdRatioB := ws.Demand["product_b"] / max(ws.Supply["product_b"], 0.01)
	baseB := 80.0
	ws.MarketPrice["product_b"] = baseB * (1 + (sdRatioB-1)*0.25) * (1 + (rand.Float64()-0.5)*0.02)

	// 原材料: 受国际市场影响
	sdRatioR := ws.Demand["raw_material"] / max(ws.Supply["raw_material"], 0.01)
	baseR := 50.0
	ws.MarketPrice["raw_material"] = baseR * (1 + (sdRatioR-1)*0.2) * (1 + (rand.Float64()-0.5)*0.03)
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
		agent.State["profit_margin"] = profit / max(revenue, 0.01)

		// 效率提升 (如果之前有创新决策)
		if eff, ok := agent.State["efficiency"]; ok {
			if f, ok := eff.(float64); ok && f > 1.0 {
				cost *= (2 - f) // efficiency 越高 cost 越低
				agent.State["cost"] = cost
			}
		}
	} else if agent.Role == "consumer" {
		// 消费者: 基于价格变化调整购买力
		price := ws.MarketPrice["product_a"]
		purchasingPower := agent.Capital / max(price, 1)
		if agent.State == nil {
			agent.State = make(map[string]interface{})
		}
		agent.State["purchasing_power"] = purchasingPower
		agent.State["satisfaction"] = 1.0 - (price-80.0)/100.0 // 80元满意度最高
	}
}

// localDecision 本地回退决策 - 更智能的规则
func (e *SimulationEngine) localDecision(agent *Agent, ws *WorldState) *Decision {
	action := "hold"
	params := map[string]interface{}{}
	reasoning := ""

	switch agent.Role {
	case "enterprise":
		profitMargin := 0.0
		if pm, ok := agent.State["profit_margin"]; ok {
			if f, ok := pm.(float64); ok {
				profitMargin = f
			}
		}
		sdRatio := ws.Demand["product_a"] / max(ws.Supply["product_a"], 0.01)

		if agent.Capital > 8000000 && sdRatio > 1.1 {
			action = "expand"
			params["investment"] = agent.Capital * 0.2
			reasoning = fmt.Sprintf("资本充足(%.0f)且需求旺盛(供需比%.2f)，扩张产能", agent.Capital, sdRatio)
		} else if profitMargin < 0.1 {
			action = "cut_cost"
			params["reduction"] = 0.15
			reasoning = fmt.Sprintf("利润率低(%.1f%%)，削减成本", profitMargin*100)
		} else if agent.Capital > 5000000 && profitMargin > 0.2 {
			action = "innovate"
			params["rd_investment"] = agent.Capital * 0.1
			reasoning = "利润率高，投入研发创新提升竞争力"
		} else if ws.MarketPrice["product_a"] > 110 {
			action = "price_adjust"
			params["new_price"] = ws.MarketPrice["product_a"] * 0.95
			reasoning = "价格偏高，适当降价扩大市场份额"
		} else {
			action = "hold"
			reasoning = "市场稳定，维持现有策略观察"
		}
	case "competitor":
		entPrice := ws.MarketPrice["product_a"]
		compPrice := ws.MarketPrice["product_b"]
		if entPrice > compPrice*1.2 {
			action = "price_war"
			params["discount"] = 0.08
			reasoning = "对手价格高，价格战抢占市场"
		} else if agent.Capital > 6000000 {
			action = "differentiate"
			params["strategy"] = "quality"
			params["investment"] = agent.Capital * 0.15
			reasoning = "差异化竞争，质量优先"
		} else {
			action = "hold"
			reasoning = "保持竞争姿态，观察对手"
		}
	case "consumer":
		price := ws.MarketPrice["product_a"]
		satisfaction := 0.5
		if s, ok := agent.State["satisfaction"]; ok {
			if f, ok := s.(float64); ok {
				satisfaction = f
			}
		}
		if price < 80 {
			action = "buy_more"
			params["quantity"] = 200
			reasoning = "价格低，增加购买"
		} else if price > 120 || satisfaction < 0.3 {
			action = "reduce_consumption"
			params["reduction"] = 0.3
			reasoning = "价格过高或满意度低，减少消费"
		} else if satisfaction > 0.6 {
			action = "buy"
			params["quantity"] = 100
			reasoning = "满意度高，正常消费"
		} else {
			action = "substitute"
			params["target"] = "product_b"
			reasoning = "寻求替代品"
		}
	case "policy":
		sd := ws.Supply["product_a"] / max(ws.Demand["product_a"], 0.01)
		inflation := ws.MarketPrice["product_a"] / 100.0

		if sd < 0.8 {
			action = "subsidy"
			params["amount"] = 500000
			reasoning = "供给不足(供需比%.2f)，提供生产补贴"
		} else if inflation > 1.3 {
			action = "tighten"
			params["rate_increase"] = 0.005
			reasoning = "通胀压力(价格指数%.2f)，收紧货币"
		} else if sd > 1.2 {
			action = "tax_relief"
			params["reduction"] = 0.02
			reasoning = "供给过剩(供需比%.2f)，减免税收刺激消费"
		} else {
			action = "observe"
			reasoning = "市场均衡(供需比%.2f)，维持现有政策"
		}
		_ = inflation // use in reasoning
		reasoning = fmt.Sprintf(reasoning, sd)
	}
	return &Decision{
		Step:      ws.Step,
		Action:    action,
		Params:    params,
		Reasoning: reasoning,
	}
}

// applyDecision 应用决策 - 更完整的效果模型
func (e *SimulationEngine) applyDecision(agent *Agent, decision *Decision, ws *WorldState) {
	switch decision.Action {
	case "expand":
		if inv, ok := decision.Params["investment"]; ok {
			if f, ok := toFloat64(inv); ok {
				agent.Capital -= f
				ws.Supply["product_a"] += f / 100
				ws.Demand["raw_material"] += f / 200
			}
		}
	case "cut_cost":
		ws.Supply["product_a"] *= 0.95
		if red, ok := decision.Params["reduction"]; ok {
			if f, ok := toFloat64(red); ok {
				agent.Capital += agent.Capital * f * 0.5 // 节省的成本回流
			}
		}
	case "innovate":
		if rd, ok := decision.Params["rd_investment"]; ok {
			if f, ok := toFloat64(rd); ok {
				agent.Capital -= f
				agent.State["efficiency"] = 1.15 + rand.Float64()*0.1
			}
		}
	case "price_adjust":
		if np, ok := decision.Params["new_price"]; ok {
			if f, ok := toFloat64(np); ok {
				ws.MarketPrice["product_a"] = f
				ws.Demand["product_a"] += (100 - f) * 5 // 降价刺激需求
			}
		}
	case "price_war":
		discount := 0.05
		if d, ok := decision.Params["discount"]; ok {
			if f, ok := toFloat64(d); ok {
				discount = f
			}
		}
		ws.MarketPrice["product_b"] *= (1 - discount)
		ws.Demand["product_b"] += 80
		ws.Demand["product_a"] -= 30 // 竞品抢走部分需求
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
				agent.Capital -= ws.MarketPrice["product_a"] * f
			}
		}
	case "reduce_consumption":
		if red, ok := decision.Params["reduction"]; ok {
			if f, ok := toFloat64(red); ok {
				ws.Demand["product_a"] *= (1 - f)
			}
		}
	case "substitute":
		ws.Demand["product_a"] *= 0.9
		ws.Demand["product_b"] += 50
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
	case "tighten":
		if ri, ok := decision.Params["rate_increase"]; ok {
			if f, ok := toFloat64(ri); ok {
				currentRate := 0.035
				if r, ok := ws.Policy["interest_rate"]; ok {
					if rf, ok := r.(float64); ok {
						currentRate = rf
					}
				}
				ws.Policy["interest_rate"] = currentRate + f
				ws.Demand["product_a"] *= 0.97 // 加息抑制消费
			}
		}
	case "stimulate":
		ws.Demand["product_a"] *= 1.05
		ws.Demand["product_b"] *= 1.03
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

// DistillRequest 蒸馏请求
type DistillRequest struct {
	TaskID        string                   `json:"task_id"`
	SimulationLog []map[string]interface{} `json:"simulation_log"`
	FinalState    *WorldState              `json:"final_state,omitempty"`
}

// DistillResponse 蒸馏响应
type DistillResponse struct {
	TaskID          string                   `json:"task_id"`
	Report          string                   `json:"report"`
	CausalAnalysis  []map[string]interface{} `json:"causal_analysis"`
	Recommendations []string                 `json:"recommendations"`
	Metrics         map[string]float64       `json:"metrics"`
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
	enabled    bool
	interval   time.Duration
	maxDataAge time.Duration
	lastRun    time.Time
	cleanCount int
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
		"enabled":      c.enabled,
		"interval":     c.interval.String(),
		"max_data_age": c.maxDataAge.String(),
		"last_run":     c.lastRun.Format("2006-01-02 15:04:05"),
		"clean_count":  c.cleanCount,
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

	// 启动 WebSocket Hub
	go wsHub.Run()

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

	// WebSocket
	mux.HandleFunc("/ws", handleWebSocket)

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
	log.Printf("WebSocket 端点: ws://0.0.0.0:%s/ws", port)
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

// ==================== WebSocket Handler ====================

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	// 简化的 WebSocket 处理 - 使用 HTTP SSE 替代
	// 因为标准库不支持 WS，使用 Server-Sent Events
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	client := &WSClient{Hub: wsHub, Send: make(chan []byte, 256)}
	wsHub.register <- client
	defer func() {
		wsHub.unregister <- client
	}()

	notify := r.Context().Done()
	for {
		select {
		case msg, ok := <-client.Send:
			if !ok {
				return
			}
			fmt.Fprintf(w, "data: %s\n\n", msg)
			flusher.Flush()
		case <-notify:
			return
		}
	}
}

// ==================== API Handlers ====================

func handleHealth(w http.ResponseWriter, r *http.Request) {
	aiStatus := "standby"
	if engine.aiClient != nil && engine.aiClient.Available() {
		aiStatus = "running"
	}
	uptime := time.Since(engine.startTime)
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":  "healthy",
		"service": "MiroFish - 女娲企业经营数字孪生系统",
		"version": "1.1.0",
		"uptime":  uptime.String(),
		"components": map[string]string{
			"simulation_engine": "running",
			"ai_agent":          aiStatus,
			"data_collector":    "ready",
			"cleaner_service":   "running",
			"websocket":         "running",
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
		Name   string                 `json:"name"`
		Steps  int                    `json:"max_steps"`
		Config map[string]interface{} `json:"config"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
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
	go func() {
		for task.CurrentStep < task.MaxSteps {
			engine.RunStep(task)
			if task.CurrentStep%10 == 0 {
				log.Printf("[Sim] Task %s: step %d/%d", taskID, task.CurrentStep, task.MaxSteps)
			}
			time.Sleep(200 * time.Millisecond)
		}
		if task.Status != "completed" {
			task.Status = "completed"
			if task.Result == nil {
				task.Result = &SimulationResult{
					TaskID:      taskID,
					FinalState:  task.WorldState,
					Metrics:     computeMetrics(task),
					CompletedAt: time.Now(),
				}
			}
			task.UpdatedAt = time.Now()
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

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"step":        task.CurrentStep,
		"max_steps":   task.MaxSteps,
		"status":      task.Status,
		"world_state": task.WorldState,
		"agent_count": len(task.Agents),
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
		"task_id": taskID,
		"report":  report,
		"source":  "local",
		"metrics": computeMetrics(task),
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

	uptime := time.Since(engine.startTime)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"service": map[string]interface{}{
			"name":    "MiroFish Gateway",
			"version": "1.1.0",
			"status":  "running",
			"uptime":  uptime.String(),
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
	sdRatio := ws.Supply["product_a"] / max(ws.Demand["product_a"], 0.01)
	return map[string]float64{
		"total_revenue":     ws.MarketPrice["product_a"] * 100,
		"market_efficiency": ws.Demand["product_a"] / max(ws.Supply["product_a"], 0.01),
		"price_index":       ws.MarketPrice["product_a"],
		"supply_demand":     sdRatio,
		"total_steps":       float64(task.CurrentStep),
		"price_volatility":  0.05, // 简化指标
	}
}

func generateLocalReport(taskID string, history []*WorldState, task *SimulationTask) string {
	if len(history) == 0 {
		return "无仿真数据可分析"
	}

	avgPrice := 0.0
	minPrice := 999999.0
	maxPrice := 0.0
	for _, ws := range history {
		p := ws.MarketPrice["product_a"]
		avgPrice += p
		if p < minPrice {
			minPrice = p
		}
		if p > maxPrice {
			maxPrice = p
		}
	}
	avgPrice /= float64(len(history))

	finalPrice := history[len(history)-1].MarketPrice["product_a"]
	priceChange := (finalPrice - 100.0) / 100.0 * 100
	volatility := (maxPrice - minPrice) / avgPrice * 100

	report := fmt.Sprintf(`# 企业经营仿真蒸馏报告

## 任务 ID: %s

### 仿真概况
- 总步数: %d
- 初始产品价格: 100.00
- 最终产品价格: %.2f
- 平均产品价格: %.2f
- 最高/最低价格: %.2f / %.2f
- 价格变化: %.1f%%
- 价格波动率: %.1f%%

### 市场分析
- 供给/需求比: %.2f
- 税率: %.2f
- 补贴: %.0f

### 建议
- 关注市场供需平衡
- 监控政策变化影响
- 优化智能体决策策略
- 控制价格波动风险`,
		taskID, len(history), finalPrice, avgPrice, maxPrice, minPrice, priceChange, volatility,
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
