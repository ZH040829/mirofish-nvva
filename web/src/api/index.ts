/**
 * MiroFish API 层
 * 封装所有与 Go 后端 (9090) 和 Python AI 服务 (8000) 的通信
 */
import axios from 'axios'

// Go 后端 API
const gateway = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Python AI 服务 API
const ai = axios.create({
  baseURL: '/ai/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// ==================== 系统健康 ====================
export const getSystemHealth = () => gateway.get('/health')
export const getSystemStatus = () => gateway.get('/system/status')
export const triggerSystemClean = () => gateway.post('/system/clean')

// ==================== 仿真任务 ====================
export const createSimulation = (data: { name: string; max_steps: number; config?: Record<string, any> }) =>
  gateway.post('/simulation/create', data)

export const startSimulation = (taskId: string) =>
  gateway.post(`/simulation/start/${taskId}`)

export const stepSimulation = (taskId: string) =>
  gateway.post(`/simulation/step/${taskId}`)

export const stopSimulation = (taskId: string) =>
  gateway.post(`/simulation/stop/${taskId}`)

export const getSimulationStatus = (taskId: string) =>
  gateway.get(`/simulation/status/${taskId}`)

export const getSimulationList = () =>
  gateway.get('/simulation/list')

export const getSimulationResult = (taskId: string) =>
  gateway.get(`/simulation/result/${taskId}`)

// ==================== 世界状态 ====================
export const getWorldState = (taskId: string) =>
  gateway.get(`/world/state/${taskId}`)

export const getWorldHistory = (taskId?: string) =>
  gateway.get('/world/history', { params: { task_id: taskId } })

// ==================== 智能体 ====================
export const getAgents = (taskId: string) =>
  gateway.get(`/agents/${taskId}`)

// ==================== 数据采集 ====================
export const collectData = () =>
  gateway.post('/data/collect')

export const getDataSources = () =>
  gateway.get('/data/sources')

// ==================== 蒸馏分析 ====================
export const getDistillAnalysis = (taskId: string) =>
  gateway.get(`/distill/${taskId}`)

// ==================== AI 服务 ====================
export const getAIHealth = () => ai.get('/health')
export const getAgentRoles = () => ai.get('/agent/roles')
export const getAgentStats = () => ai.get('/agent/stats')
export const getRAGSearch = (query: string, industry?: string, topK: number = 5) =>
  ai.post('/rag/search', { query, industry, top_k: topK })

export default {
  gateway,
  ai,
  getSystemHealth,
  getSystemStatus,
  triggerSystemClean,
  createSimulation,
  startSimulation,
  stepSimulation,
  stopSimulation,
  getSimulationStatus,
  getSimulationList,
  getSimulationResult,
  getWorldState,
  getWorldHistory,
  getAgents,
  collectData,
  getDataSources,
  getDistillAnalysis,
  getAIHealth,
  getAgentRoles,
  getAgentStats,
  getRAGSearch,
}
