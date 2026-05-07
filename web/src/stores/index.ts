import { defineStore } from 'pinia'
import { mirofishApi } from '../api'
import { demoData, isDemoMode, demoStepSimulation } from '../api/demo'

const demo = isDemoMode()

export const useSimulationStore = defineStore('simulation', {
  state: () => ({
    currentTask: null as any,
    tasks: [] as any[],
    worldHistory: [] as any[],
    nlConfig: null as any,
    comparisonResult: null as any,
    exportData: null as any,
    negotiationResult: null as any,
    sectors: [] as any[],
    sentiment: null as any,
    evolution: null as any,
    isDemo: demo,
  }),
  actions: {
    async createSimulation(name: string, maxSteps: number = 50) {
      if (this.isDemo) {
        const sim = { ...demoData.simulation }
        sim.task = { ...sim.task, name, max_steps: maxSteps, id: 'demo_' + Date.now() }
        this.currentTask = sim.task
        this.tasks.push(sim.task)
        return sim
      }
      const data = await mirofishApi.createSimulation(name, maxSteps)
      this.currentTask = data.task
      this.tasks.push(data.task)
      return data
    },

    async stepSimulation(taskId: string) {
      if (this.isDemo) {
        return demoStepSimulation()
      }
      const data = await mirofishApi.stepSimulation(taskId)
      if (this.currentTask && this.currentTask.id === taskId) {
        this.currentTask = { ...this.currentTask, current_step: data.step, max_steps: data.max_steps, status: data.status, world_state: data.world_state, agents: data.agents || this.currentTask.agents }
      }
      const idx = this.tasks.findIndex((t: any) => t.id === taskId)
      if (idx >= 0) {
        this.tasks[idx] = { ...this.tasks[idx], current_step: data.step, max_steps: data.max_steps, status: data.status, world_state: data.world_state, agents: data.agents || this.tasks[idx].agents }
      }
      return data
    },

    async fetchTaskStatus(taskId: string) {
      if (this.isDemo) { return }
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
      if (this.isDemo) {
        this.worldHistory = demoData.priceHistory
        return
      }
      try {
        const data = await mirofishApi.getSimulationHistory(taskId)
        this.worldHistory = data.history || []
      } catch (e) { console.error('fetchHistory failed:', e); this.worldHistory = [] }
    },

    async fetchSectors() {
      if (this.isDemo) {
        this.sectors = demoData.sectors.sectors
        return
      }
      try {
        const data = await mirofishApi.getSectors()
        this.sectors = data.sectors || []
      } catch (e) { console.error(e) }
    },

    async fetchSentiment(taskId: string) {
      if (this.isDemo) {
        this.sentiment = demoData.sentiment.sentiment
        return
      }
      try {
        const data = await mirofishApi.getSentiment(taskId)
        this.sentiment = data.sentiment
      } catch (e) { console.error(e) }
    },

    async fetchEvolution(taskId: string) {
      if (this.isDemo) {
        this.evolution = demoData.evolution
        return
      }
      try {
        this.evolution = await mirofishApi.getAgentEvolution(taskId)
      } catch (e) { console.error(e) }
    },

    async nlCreateSimulation(text: string) {
      if (this.isDemo) { this.nlConfig = { name: 'Demo: ' + text, max_steps: 20 }; return { parsed: true, config: this.nlConfig } }
      try {
        const data = await mirofishApi.nlCreateConfig(text)
        this.nlConfig = data.config
        return data
      } catch (e) { console.error('nlCreateSimulation failed:', e); return null }
    },

    async compareSimulations(ids: string[]) {
      if (this.isDemo) { return null }
      try {
        this.comparisonResult = await mirofishApi.getSimulationComparison(ids)
        return this.comparisonResult
      } catch (e) { console.error('compareSimulations failed:', e); return null }
    },

    async exportSimulation(id: string, format: string = 'json') {
      if (this.isDemo) { return demoData.simulation }
      try {
        this.exportData = await mirofishApi.exportSimulation(id, format)
        return this.exportData
      } catch (e) { console.error('exportSimulation failed:', e); return null }
    },

    async replayAnalysis(taskId: string, history: any[]) {
      if (this.isDemo) { return demoData.report }
      try {
        return await mirofishApi.replayAnalysis(taskId, history)
      } catch (e) { console.error('replayAnalysis failed:', e); return null }
    },

    async negotiate(proposals: any[]) {
      if (this.isDemo) { return { conflicts: 1, resolutions: ['AI建议双方妥协'], recommendation: '建议适度降价以维持市场稳定' } }
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
    isDemo: demo,
  }),
  actions: {
    async fetchHealth() {
      if (this.isDemo) { this.health = demoData.health; return }
      try { this.health = await mirofishApi.getHealth() } catch (e) { console.error(e) }
    },
    async fetchAIHealth() {
      if (this.isDemo) { this.aiHealth = demoData.aiHealth; return }
      try { this.aiHealth = await mirofishApi.getAIHealth() } catch (e) { console.error(e) }
    },
    async fetchAIStats() {
      if (this.isDemo) { this.aiStats = demoData.aiStats; return }
      try { this.aiStats = await mirofishApi.getAIStats() } catch (e) { console.error(e) }
    },
    async fetchDataSources() {
      if (this.isDemo) { this.dataSources = demoData.dataSources.sources; return }
      try {
        const data = await mirofishApi.getDataCollect()
        this.dataSources = data.sources || []
      } catch (e) { console.error(e) }
    },
    async fetchMemories(query: string = '', tag: string = '', limit: number = 10) {
      if (this.isDemo) { return }
      try {
        const data = await mirofishApi.recallMemory(query, tag, limit)
        this.memories = data.results || []
      } catch (e) { console.error(e) }
    },
    async fetchMemoryStats() {
      if (this.isDemo) { return }
      try { this.memoryStats = await mirofishApi.getMemoryStats() } catch (e) { console.error(e) }
    },
  },
})
