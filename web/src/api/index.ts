import axios from 'axios'

// ==================== 动态 API 地址配置 ====================
// 优先从 localStorage 读取用户配置，否则自动检测

function getGatewayBase(): string {
  const saved = localStorage.getItem('mirofish_gateway_url')
  if (saved) return saved
  // 如果通过 nginx 代理访问（同源），直接用相对路径
  if (window.location.port === '80' || window.location.port === '') {
    return '/api'
  }
  // 本地开发
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:9090/api'
  }
  // GitHub Pages 等外部访问，提示配置
  return ''
}

function getAIServiceBase(): string {
  const saved = localStorage.getItem('mirofish_ai_url')
  if (saved) return saved
  // 如果通过 nginx 代理，Go 后端会转发 AI 请求
  if (window.location.port === '80' || window.location.port === '') {
    return '/ai-api'
  }
  // 本地开发
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api'
  }
  return ''
}

// Go 仿真引擎 API
export const gateway = axios.create({
  baseURL: getGatewayBase(),
  timeout: 30000,
})

// AI 智能体服务 API
export const aiService = axios.create({
  baseURL: getAIServiceBase(),
  timeout: 60000,
})

// 动态更新 API 地址（用户从设置面板配置时调用）
export function updateApiConfig(gatewayUrl: string, aiUrl: string) {
  localStorage.setItem('mirofish_gateway_url', gatewayUrl)
  localStorage.setItem('mirofish_ai_url', aiUrl)
  gateway.defaults.baseURL = gatewayUrl
  aiService.defaults.baseURL = aiUrl
}

// 获取当前配置
export function getApiConfig() {
  return {
    gatewayUrl: gateway.defaults.baseURL || getGatewayBase(),
    aiUrl: aiService.defaults.baseURL || getAIServiceBase(),
  }
}

// 检测 API 是否可用
export async function probeApiConnectivity(): Promise<{go: boolean, ai: boolean}> {
  const result = { go: false, ai: false }
  try {
    await gateway.get('/health', { timeout: 5000 })
    result.go = true
  } catch { /* ignore */ }
  try {
    await aiService.get('/health', { timeout: 5000 })
    result.ai = true
  } catch { /* ignore */ }
  return result
}

// WebSocket 连接管理
class SimulationWS {
  private ws: WebSocket | null = null
  private url: string
  private listeners: Map<string, Function[]> = new Map()

  constructor(taskId: string) {
    const base = (gateway.defaults.baseURL || getGatewayBase()).replace('/api', '').replace('http', 'ws')
    this.url = `${base}/api/simulation/stream/${taskId}`
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('update', data)
        } catch {
          this.emit('raw', event.data)
        }
      }
      this.ws.onclose = () => this.emit('close', {})
      this.ws.onerror = (e) => this.emit('error', e)
      this.ws.onopen = () => this.emit('open', {})
    } catch (e) {
      console.warn('[WS] 连接失败:', e)
    }
  }

  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) this.listeners.set(event, [])
    this.listeners.get(event)!.push(callback)
  }

  private emit(event: string, data: any) {
    (this.listeners.get(event) || []).forEach(cb => cb(data))
  }

  close() {
    this.ws?.close()
    this.listeners.clear()
  }
}

// 高级 API 封装
export const mirofishApi = {
  // === Go 仿真引擎 ===
  getHealth: () => gateway.get('/health').then(r => r.data),
  createSimulation: (name: string, maxSteps: number = 50) =>
    gateway.post('/simulation/create', { name, max_steps: maxSteps }).then(r => r.data),
  stepSimulation: (id: string) =>
    gateway.post(`/simulation/step/${id}`).then(r => r.data),
  getSimulationStatus: (id: string) =>
    gateway.get(`/simulation/status/${id}`).then(r => r.data),
  getSimulationList: () =>
    gateway.get('/simulation/list').then(r => r.data),
  getSimulationHistory: (id: string) =>
    gateway.get(`/simulation/history/${id}`).then(r => r.data),
  getAgents: (id: string) =>
    gateway.get(`/agents/${id}`).then(r => r.data),
  getDataCollect: () =>
    gateway.get('/data/collect').then(r => r.data),
  getSimulationTemplates: () =>
    gateway.get('/simulation/templates').then(r => r.data),
  nlCreateSimulation: (text: string) =>
    gateway.post('/simulation/nl-create', { text }).then(r => r.data),
  getSimulationComparison: (ids: string[]) =>
    gateway.post('/simulation/compare', { task_ids: ids }).then(r => r.data),
  exportSimulation: (id: string, format: string = 'json') =>
    gateway.get(`/simulation/export/${id}?format=${format}`).then(r => r.data),
  getSimulationMetrics: (id: string) =>
    gateway.get(`/simulation/metrics/${id}`).then(r => r.data),

  // === AI 智能体服务 ===
  getAIHealth: () => aiService.get('/health').then(r => r.data),
  getAIDecision: (agent: any, world: any) =>
    aiService.post('/agent/decision', { agent, world }).then(r => r.data),
  getAIBatchDecision: (agents: any[], world: any) =>
    aiService.post('/agent/batch', { agents, world }).then(r => r.data),
  negotiate: (proposals: any[]) =>
    aiService.post('/agent/negotiate', { proposals }).then(r => r.data),
  nlCreateConfig: (text: string) =>
    aiService.post('/simulation/nl-create', { user_input: text }).then(r => r.data),
  distillAnalysis: (taskId: string, log: any[]) =>
    aiService.post('/distill/analyze', { task_id: taskId, simulation_log: log }).then(r => r.data),
  replayAnalysis: (taskId: string, history: any[]) =>
    aiService.post('/replay/analyze', { task_id: taskId, history }).then(r => r.data),
  ragSearch: (query: string, topK: number = 5) =>
    aiService.post('/rag/search', { query, top_k: topK }).then(r => r.data),
  getAIStats: () => aiService.get('/agent/stats').then(r => r.data),
  getAIRoles: () => aiService.get('/agent/roles').then(r => r.data),
  clearAICache: () => aiService.post('/cache/clear').then(r => r.data),

  // === 跨仿真记忆 ===
  recordMemory: (taskId: string, lesson: string, metrics: any = {}, tag: string = '') =>
    aiService.post('/memory/record', { task_id: taskId, lesson, metrics, tag }).then(r => r.data),
  recallMemory: (query: string = '', tag: string = '', limit: number = 10) =>
    aiService.post('/memory/recall', { query, tag, limit }).then(r => r.data),
  getMemoryStats: () => aiService.get('/memory/stats').then(r => r.data),

  // === v1.4.0: 行业赛道 ===
  getSectors: () => gateway.get('/sectors').then(r => r.data),
  switchSector: (sectorId: string, taskId: string = '') =>
    gateway.get(`/sectors/switch/${sectorId}?task_id=${taskId}`).then(r => r.data),

  // === v1.4.0: 市场情绪 ===
  getSentiment: (taskId: string) =>
    gateway.get(`/sentiment/${taskId}`).then(r => r.data),

  // === v1.4.0: 智能体进化 ===
  getAgentEvolution: (taskId: string) =>
    gateway.get(`/agent/evolution/${taskId}`).then(r => r.data),
  analyzeEvolution: (taskId: string, agentId: string = '') =>
    aiService.post('/agent/evolution-analyze', { task_id: taskId, agent_id: agentId }).then(r => r.data),

  // === v1.4.0: 对话式控制 ===
  chatControl: (message: string, taskId: string = '', context: any = null) =>
    aiService.post('/chat/control', { message, task_id: taskId || null, context }).then(r => r.data),

  // === v1.4.0: 仿真回放 SSE ===
  createReplayStream(taskId: string): EventSource {
    const base = (gateway.defaults.baseURL || getGatewayBase())
    return new EventSource(`${base}/simulation/replay/${taskId}`)
  },

  // === v1.5.0: 交易系统 ===
  getTrades: (taskId: string) =>
    gateway.get(`/trades/${taskId}`).then(r => r.data),
  getFinance: (taskId: string) =>
    gateway.get(`/finance/${taskId}`).then(r => r.data),
  getLeaderboard: (taskId: string) =>
    gateway.get(`/leaderboard/${taskId}`).then(r => r.data),

  // === v1.5.0: 通知系统 ===
  getNotifications: (taskId: string) =>
    gateway.get(`/notifications?task_id=${taskId}`).then(r => r.data),
  markNotificationRead: (id: string) =>
    gateway.post(`/notifications/read/${id}`).then(r => r.data),

  // === v1.5.0: 风险预警 ===
  getRiskAlerts: (taskId: string) =>
    gateway.get(`/risk/alerts?task_id=${taskId}`).then(r => r.data),

  // === v1.5.0: Dashboard 汇总 ===
  getDashboard: (taskId: string) =>
    gateway.get(`/dashboard/${taskId}`).then(r => r.data),

  // === v1.5.0: AI 新能力 ===
  marketPredict: (data: any) =>
    aiService.post('/market/predict', data).then(r => r.data),
  riskAnalyze: (data: any) =>
    aiService.post('/risk/analyze', data).then(r => r.data),
  tradeAdvice: (data: any) =>
    aiService.post('/trade/advice', data).then(r => r.data),
  dashboardSummary: (data: any) =>
    aiService.post('/dashboard/summary', data).then(r => r.data),

  // === v1.5.0: SSE 流式决策 ===
  createDecisionStream(agent: any, world: any): EventTarget {
    const base = (aiService.defaults.baseURL || getAIServiceBase())
    const url = `${base}/agent/decision-stream`
    const target = new EventTarget()
    // 使用 fetch + ReadableStream 实现 SSE
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent, world }),
    }).then(async (response) => {
      const reader = response.body?.getReader()
      if (!reader) return
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        for (const line of text.split('\n')) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              target.dispatchEvent(new CustomEvent('done'))
              break
            }
            try {
              const parsed = JSON.parse(data)
              target.dispatchEvent(new CustomEvent('message', { detail: parsed }))
            } catch { /* ignore */ }
          }
        }
      }
    }).catch((err) => {
      target.dispatchEvent(new CustomEvent('error', { detail: err }))
    })
    return target
  },

  // === WebSocket ===
  createWS(taskId: string) {
    return new SimulationWS(taskId)
  },
}

// 拦截器
gateway.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error(`[Gateway API Error] ${err.config?.url}:`, err.message)
    return Promise.reject(err)
  }
)

aiService.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error(`[AI Service Error] ${err.config?.url}:`, err.message)
    return Promise.reject(err)
  }
)

// 向后兼容
export const api = {
  get: (url: string) => gateway.get(url),
  post: (url: string, data?: any) => gateway.post(url, data),
  ai: {
    get: (url: string) => aiService.get(url),
    post: (url: string, data?: any) => aiService.post(url, data),
  },
  createWS: mirofishApi.createWS,
}

export default api
