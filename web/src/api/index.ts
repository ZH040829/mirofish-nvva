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

// 统一 API 对象
export const api = {
  // Go 仿真引擎
  get: (url: string) => gateway.get(url),
  post: (url: string, data?: any) => gateway.post(url, data),

  // AI 智能体服务
  ai: {
    get: (url: string) => aiService.get(url),
    post: (url: string, data?: any) => aiService.post(url, data),
  },

  // WebSocket
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

export default api
