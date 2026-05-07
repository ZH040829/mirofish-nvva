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

// 统一 API 对象
export const api = {
  // Go 仿真引擎
  get: (url: string) => gateway.get(url),
  post: (url: string, data?: any) => gateway.post(url, data),

  // AI 智能体（直接访问 AI 服务）
  ai: {
    get: (url: string) => aiService.get(url),
    post: (url: string, data?: any) => aiService.post(url, data),
  },
}

// 请求/响应拦截器
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
