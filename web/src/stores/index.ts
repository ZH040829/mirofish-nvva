/**
 * MiroFish 仿真数据 Store
 * 管理仿真任务、世界状态、智能体等全局数据
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'

export const useSimulationStore = defineStore('simulation', () => {
  // ==================== State ====================
  const tasks = ref<any[]>([])
  const currentTask = ref<any>(null)
  const worldHistory = ref<any[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ==================== Getters ====================
  const runningTasks = computed(() => tasks.value.filter(t => t.status === 'running'))
  const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed'))
  const taskCount = computed(() => tasks.value.length)

  // ==================== Actions ====================
  async function fetchTasks() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.getSimulationList()
      tasks.value = data.tasks || []
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createTask(name: string, maxSteps: number = 100) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.createSimulation({ name, max_steps: maxSteps })
      currentTask.value = data.task
      tasks.value.push(data.task)
      return data.task
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function startTask(taskId: string) {
    try {
      const { data } = await api.startSimulation(taskId)
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function stepTask(taskId: string) {
    try {
      const { data } = await api.stepSimulation(taskId)
      if (currentTask.value && currentTask.value.id === taskId) {
        currentTask.value.current_step = data.step
        currentTask.value.status = data.status
        currentTask.value.world_state = data.world_state
      }
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function stopTask(taskId: string) {
    try {
      const { data } = await api.stopSimulation(taskId)
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function fetchTaskStatus(taskId: string) {
    try {
      const { data } = await api.getSimulationStatus(taskId)
      currentTask.value = data
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function fetchResult(taskId: string) {
    try {
      const { data } = await api.getSimulationResult(taskId)
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function fetchHistory(taskId?: string) {
    try {
      const { data } = await api.getWorldHistory(taskId)
      worldHistory.value = data.history || []
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  return {
    tasks,
    currentTask,
    worldHistory,
    loading,
    error,
    runningTasks,
    completedTasks,
    taskCount,
    fetchTasks,
    createTask,
    startTask,
    stepTask,
    stopTask,
    fetchTaskStatus,
    fetchResult,
    fetchHistory,
  }
})

export const useSystemStore = defineStore('system', () => {
  const health = ref<any>(null)
  const status = ref<any>(null)
  const dataSources = ref<any[]>([])
  const aiStats = ref<any>(null)

  async function fetchHealth() {
    try {
      const { data } = await api.getSystemHealth()
      health.value = data
    } catch (e) {
      health.value = null
    }
  }

  async function fetchStatus() {
    try {
      const { data } = await api.getSystemStatus()
      status.value = data
    } catch (e) {
      status.value = null
    }
  }

  async function fetchDataSources() {
    try {
      const { data } = await api.getDataSources()
      dataSources.value = data.sources || []
    } catch (e) {
      dataSources.value = []
    }
  }

  async function fetchAIStats() {
    try {
      const { data } = await api.getAgentStats()
      aiStats.value = data
    } catch (e) {
      aiStats.value = null
    }
  }

  async function cleanSystem() {
    try {
      const { data } = await api.triggerSystemClean()
      return data
    } catch (e) {
      return null
    }
  }

  return {
    health,
    status,
    dataSources,
    aiStats,
    fetchHealth,
    fetchStatus,
    fetchDataSources,
    fetchAIStats,
    cleanSystem,
  }
})
