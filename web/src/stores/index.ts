import { defineStore } from 'pinia'
import { api, mirofishApi } from '../api'

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
    comparisonResult: null as any,
    negotiationResult: null as any,
    nlConfig: null as any,
    exportData: null as any,
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
        const data = await mirofishApi.getSimulationList()
        this.tasks = data.tasks || []
        if (this.currentTaskId) {
          const updated = this.tasks.find((t: any) => t.id === this.currentTaskId)
          if (updated) this.currentTask = updated
        }
      } catch (e) { console.error('fetchTasks failed:', e) }
    },

    async createSimulation(name: string, maxSteps: number) {
      const data = await mirofishApi.createSimulation(name, maxSteps)
      const task = data.task
      this.tasks.push(task)
      this.selectTask(task.id)
      return task
    },

    async stepSimulation(taskId: string) {
      const data = await mirofishApi.stepSimulation(taskId)
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
        const data = await mirofishApi.getSimulationStatus(taskId)
        if (this.currentTask && this.currentTask.id === taskId) {
          this.currentTask = { ...this.currentTask, ...data }
        }
        const idx = this.tasks.findIndex((t: any) => t.id === taskId)
        if (idx >= 0) { this.tasks[idx] = { ...this.tasks[idx], ...data } }
      } catch (e) { console.error('fetchTaskStatus failed:', e) }
    },

    async fetchHistory(taskId: string) {
      try {
        const data = await mirofishApi.getSimulationHistory(taskId)
        this.worldHistory = data.history || []
      } catch (e) { console.error('fetchHistory failed:', e); this.worldHistory = [] }
    },

    async nlCreateSimulation(text: string) {
      try {
        const data = await mirofishApi.nlCreateConfig(text)
        this.nlConfig = data.config
        return data
      } catch (e) { console.error('nlCreateSimulation failed:', e); return null }
    },

    async compareSimulations(ids: string[]) {
      try {
        this.comparisonResult = await mirofishApi.getSimulationComparison(ids)
        return this.comparisonResult
      } catch (e) { console.error('compareSimulations failed:', e); return null }
    },

    async exportSimulation(id: string, format: string = 'json') {
      try {
        this.exportData = await mirofishApi.exportSimulation(id, format)
        return this.exportData
      } catch (e) { console.error('exportSimulation failed:', e); return null }
    },

    // 仿真复盘
    async replayAnalysis(taskId: string, history: any[]) {
      try {
        return await mirofishApi.replayAnalysis(taskId, history)
      } catch (e) { console.error('replayAnalysis failed:', e); return null }
    },

    // 协商
    async negotiate(proposals: any[]) {
      try {
        this.negotiationResult = await mirofishApi.negotiate(proposals)
        return this.negotiationResult
      } catch (e) { console.error('negotiate failed:', e); return null }
    },
  },
})

export const useSystemStore = defineStore('system', {
  state: () => ({
    health: null as any,
    aiHealth: null as any,
    aiStats: null as any,
    dataSources: [] as any[],
    memories: [] as any[],
    memoryStats: null as any,
  }),
  actions: {
    async fetchHealth() {
      try { this.health = await mirofishApi.getHealth() } catch (e) { console.error(e) }
    },
    async fetchAIHealth() {
      try { this.aiHealth = await mirofishApi.getAIHealth() } catch (e) { console.error(e) }
    },
    async fetchAIStats() {
      try { this.aiStats = await mirofishApi.getAIStats() } catch (e) { console.error(e) }
    },
    async fetchDataSources() {
      try {
        const data = await mirofishApi.getDataCollect()
        this.dataSources = data.sources || []
      } catch (e) { console.error(e) }
    },
    async fetchMemories(query: string = '', tag: string = '', limit: number = 10) {
      try {
        const data = await mirofishApi.recallMemory(query, tag, limit)
        this.memories = data.results || []
      } catch (e) { console.error(e) }
    },
    async fetchMemoryStats() {
      try { this.memoryStats = await mirofishApi.getMemoryStats() } catch (e) { console.error(e) }
    },
  },
})
