<template>
  <div class="agents-page">
    <h2>智能体管理</h2>

    <!-- 智能体角色卡片 -->
    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="6" v-for="role in roles" :key="role.id">
        <el-card class="agent-card panel" shadow="hover">
          <div class="agent-header">
            <el-avatar :size="48" :style="{ background: roleColors[role.id] }">{{ role.name[0] }}</el-avatar>
            <div>
              <h3>{{ role.name }}</h3>
              <el-tag type="success" size="small">在线</el-tag>
            </div>
          </div>
          <el-divider />
          <div class="agent-desc">{{ role.description }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 当前仿真智能体详情 -->
    <el-card class="panel" v-if="agents.length > 0">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>当前仿真智能体详情</span>
          <el-button size="small" @click="fetchAgents">刷新</el-button>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="agent in agents" :key="agent.id">
          <el-card class="panel agent-detail-card" shadow="hover">
            <div class="agent-header">
              <el-avatar :size="48" :style="{ background: roleColors[agent.role] }">{{ agent.name[0] }}</el-avatar>
              <div>
                <h3>{{ agent.name }}</h3>
                <el-tag :type="agentRoleTag(agent.role)" size="small">{{ agentRoleLabel(agent.role) }}</el-tag>
              </div>
            </div>
            <el-divider />
            <div class="agent-props">
              <div class="prop"><span class="label">资本</span><span>{{ formatCapital(agent.capital) }}</span></div>
              <div class="prop"><span class="label">策略</span><span>{{ agent.strategy }}</span></div>
              <div class="prop"><span class="label">决策次数</span><span>{{ agent.decisions?.length || 0 }}</span></div>
              <div class="prop">
                <span class="label">最新决策</span>
                <span>{{ latestAction(agent) }}</span>
              </div>
              <div class="prop" v-if="agent.state?.profit !== undefined">
                <span class="label">利润</span>
                <span :style="{ color: agent.state.profit > 0 ? '#67c23a' : '#f56c6c' }">
                  {{ formatCapital(agent.state.profit as number) }}
                </span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- AI 服务统计 -->
    <el-card class="panel" style="margin-top:20px;">
      <template #header><span>AI 决策统计</span></template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="stat in aiStats" :key="stat.label">
          <div class="stat-item">
            <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as api from '../api'
import { useSimulationStore, useSystemStore } from '../stores'

const simStore = useSimulationStore()
const sysStore = useSystemStore()

const roleColors: Record<string, string> = {
  enterprise: '#409eff',
  competitor: '#67c23a',
  consumer: '#e6a23c',
  policy: '#909399',
}

const roles = ref<any[]>([])

const agents = computed(() => {
  if (simStore.currentTask?.agents) {
    return simStore.currentTask.agents
  }
  return []
})

const aiStats = computed(() => {
  const stats = sysStore.aiStats
  if (!stats) return [
    { label: '总决策数', value: 'N/A', color: '#00d4ff' },
    { label: 'LLM 决策', value: 'N/A', color: '#67c23a' },
    { label: '规则决策', value: 'N/A', color: '#e6a23c' },
    { label: 'LLM 可用', value: 'N/A', color: '#f56c6c' },
  ]
  return [
    { label: '总决策数', value: stats.total_decisions, color: '#00d4ff' },
    { label: 'LLM 决策', value: stats.llm_decisions, color: '#67c23a' },
    { label: '规则决策', value: stats.rule_decisions, color: '#e6a23c' },
    { label: 'LLM 可用', value: stats.llm_available ? '是' : '否', color: stats.llm_available ? '#67c23a' : '#f56c6c' },
  ]
})

function agentRoleTag(role: string) {
  const map: Record<string, string> = { enterprise: '', competitor: 'success', consumer: 'warning', policy: 'info' }
  return (map[role] || 'info') as any
}

function agentRoleLabel(role: string) {
  const map: Record<string, string> = { enterprise: '企业', competitor: '竞品', consumer: '消费者', policy: '政策' }
  return map[role] || role
}

function formatCapital(c: number) {
  if (c >= 1000000) return (c / 1000000).toFixed(1) + 'M'
  if (c >= 1000) return (c / 1000).toFixed(1) + 'K'
  return c.toFixed(0)
}

function latestAction(agent: any) {
  if (!agent.decisions || agent.decisions.length === 0) return '无'
  return agent.decisions[agent.decisions.length - 1].action
}

async function fetchAgents() {
  await simStore.fetchTasks()
  await sysStore.fetchAIStats()
}

onMounted(async () => {
  try {
    const { data } = await api.getAgentRoles()
    roles.value = data.roles || []
  } catch { roles.value = [] }
  await fetchAgents()
})
</script>

<style scoped>
.agents-page h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
.agent-header { display: flex; align-items: center; gap: 12px; }
.agent-header h3 { color: #e0e0e0; margin: 0; font-size: 16px; }
.agent-desc { color: #888; font-size: 13px; }
.agent-props { display: flex; flex-direction: column; gap: 8px; }
.prop { display: flex; justify-content: space-between; font-size: 13px; }
.prop .label { color: #888; }
.prop span:last-child { color: #e0e0e0; }
:deep(.el-divider) { border-color: #2a2a4a; }
.stat-item { text-align: center; padding: 20px; background: #16213e; border-radius: 8px; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #888; margin-top: 8px; }
</style>
