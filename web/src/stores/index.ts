import { defineStore } from 'pinia'
import { api } from '../api'

export const useSimulationStore = defineStore('simulation', {
  state: () => ({
    tasks: [] as any[],
    currentTask: null as any,
    currentTaskId: '' as string,
    worldHistory: [] as any[],
    templates: [
      { name: '标准企业经营', max_steps: 50, description: '4 智能体标准博弈' },
      { name: '快速压力测试', max_steps: 10, description: '短周期高压仿真' },
      { name: '长期战略推演', max_steps: 200, description: '长期经营策略模拟' },
    ] as any[],
  }),
  getters: {
    taskCount: (state) => state.tasks.length,
    runningTasks: (state) => state.tasks.filter((t: any) => t.status === 'running'),
    completedTasks: (state) => state.tasks.filter((t: any) => t.status === 'completed'),
  },
  actions: {
    selectTask(id: string) {
      this.currentTaskId = id
      this.currentTask = this.tasks.find((t: any) => t.id === id) || null
    },

    async fetchTasks() {
      try {
        const res = await api.get('/simulation/list')
        this.tasks = res.data.tasks || []
        if (this.currentTaskId) {
          const updated = this.tasks.find((t: any) => t.id === this.currentTaskId)
          if (updated) this.currentTask = updated
        }
      } catch (e) {
        console.error('fetchTasks failed:', e)
      }
    },

    async createSimulation(name: string, maxSteps: number) {
      const res = await api.post('/simulation/create', { name, max_steps: maxSteps })
      const task = res.data.task
      this.tasks.push(task)
      this.selectTask(task.id)
      return task
    },

    async stepSimulation(taskId: string) {
      const res = await api.post(`/simulation/step/${taskId}`)
      const data = res.data
      if (this.currentTask && this.currentTask.id === taskId) {
        this.currentTask.current_step = data.step
        this.currentTask.max_steps = data.max_steps
        this.currentTask.status = data.status
        this.currentTask.world_state = data.world_state
        this.currentTask.agents = data.agents || this.currentTask.agents
      }
      const idx = this.tasks.findIndex((t: any) => t.id === taskId)
      if (idx >= 0) {
        this.tasks[idx] = { ...this.tasks[idx], current_step: data.step, max_steps: data.max_steps, status: data.status, world_state: data.world_state, agents: data.agents || this.tasks[idx].agents }
      }
      return data
    },

    async fetchTaskStatus(taskId: string) {
      try {
        const res = await api.get(`/simulation/status/${taskId}`)
        const data = res.data
        if (this.currentTask && this.currentTask.id === taskId) {
          this.currentTask = { ...this.currentTask, ...data }
        }
        const idx = this.tasks.findIndex((t: any) => t.id === taskId)
        if (idx >= 0) {
          this.tasks[idx] = { ...this.tasks[idx], ...data }
        }
      } catch (e) {
        console.error('fetchTaskStatus failed:', e)
      }
    },

    async fetchHistory(taskId: string) {
      try {
        const res = await api.get(`/simulation/history/${taskId}`)
        this.worldHistory = res.data.history || []
      } catch (e) {
        console.error('fetchHistory failed:', e)
        this.worldHistory = []
      }
    },

    // 仿真复盘
    async replayAnalysis(taskId: string, history: any[]) {
      try {
        const res = await api.ai.post('/replay/analyze', { task_id: taskId, history })
        return res.data
      } catch (e) {
        console.error('replayAnalysis failed:', e)
        return null
      }
    },
  },
})

export const useSystemStore = defineStore('system', {
  state: () => ({
    health: null as any,
    aiHealth: null as any,
    aiStats: null as any,
    dataSources: [] as any[],
  }),
  actions: {
    async fetchHealth() {
      try {
        const res = await api.get('/health')
        this.health = res.data
      } catch (e) {
        console.error('fetchHealth failed:', e)
      }
    },
    async fetchAIHealth() {
      try {
        const res = await api.ai.get('/health')
        this.aiHealth = res.data
      } catch (e) {
        console.error('fetchAIHealth failed:', e)
      }
    },
    async fetchAIStats() {
      try {
        const res = await api.ai.get('/agent/stats')
        this.aiStats = res.data
      } catch (e) {
        console.error('fetchAIStats failed:', e)
      }
    },
    async fetchDataSources() {
      try {
        const res = await api.get('/data/collect')
        this.dataSources = res.data.sources || []
      } catch (e) {
        console.error('fetchDataSources failed:', e)
      }
    },
  },
})
