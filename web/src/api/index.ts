import axios from 'axios'

// Go 仿真引擎 API
const gateway = axios.create({
  baseURL: 'http://localhost:9090/api',
  timeout: 30000,
})

// AI 智能体服务 API
const aiService = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 60000,
})

// WebSocket 连接管理
class SimulationWS {
  private ws: WebSocket | null = null
  private url: string
  private listeners: Map<string, Function[]> = new Map()

  constructor(taskId: string) {
    this.url = `ws://localhost:9090/api/simulation/stream/${taskId}`
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
    return new EventSource(`http://localhost:9090/api/simulation/replay/${taskId}`)
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
