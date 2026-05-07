<template>
  <div class="system-view">
    <h2>系统运维</h2>

    <el-row :gutter="20">
      <!-- 服务状态 -->
      <el-col :span="12">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>服务状态</span>
              <el-button size="small" @click="refreshStatus">刷新</el-button>
            </div>
          </template>
          <div class="service-list" v-if="systemStatus">
            <div class="service-item" v-for="(comp, name) in systemStatus.components" :key="name">
              <div class="service-name">{{ componentLabel(name as string) }}</div>
              <el-tag :type="comp === 'running' ? 'success' : comp === 'ready' ? '' : 'info'" size="small">
                {{ comp === 'running' ? '运行中' : comp === 'ready' ? '就绪' : comp === 'standby' ? '待机' : comp }}
              </el-tag>
            </div>
          </div>
          <el-empty v-else description="无法获取系统状态" :image-size="60" />
        </el-card>
      </el-col>

      <!-- AI 服务状态 -->
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>AI 服务详情</span></template>
          <div v-if="aiStats" class="ai-stats">
            <div class="stat-row">
              <span class="label">LLM 可用</span>
              <el-tag :type="aiStats.llm_available ? 'success' : 'danger'" size="small">
                {{ aiStats.llm_available ? '在线' : '离线' }}
              </el-tag>
            </div>
            <div class="stat-row">
              <span class="label">总决策数</span>
              <span class="value">{{ aiStats.total_decisions }}</span>
            </div>
            <div class="stat-row">
              <span class="label">LLM 决策数</span>
              <span class="value" style="color:#67c23a">{{ aiStats.llm_decisions }}</span>
            </div>
            <div class="stat-row">
              <span class="label">规则回退数</span>
              <span class="value" style="color:#e6a23c">{{ aiStats.rule_decisions }}</span>
            </div>
          </div>
          <el-empty v-else description="AI 服务不可用" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统运维操作 -->
    <el-row :gutter="20" style="margin-top:20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>运维操作</span></template>
          <div class="ops-grid">
            <el-button type="primary" @click="cleanSystem" :loading="cleaning">执行系统清理</el-button>
            <el-button @click="refreshStatus">刷新系统状态</el-button>
            <el-button type="danger" @click="resetAll">重置所有仿真</el-button>
          </div>
          <div v-if="cleanResult" class="clean-result">
            <el-descriptions :column="1" border size="small" style="margin-top:16px;">
              <el-descriptions-item label="消息">{{ cleanResult.message }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>仿真任务概览</span></template>
          <div class="task-summary" v-if="taskSummary">
            <div class="summary-item">
              <span>总任务数</span>
              <strong>{{ taskSummary.total }}</strong>
            </div>
            <div class="summary-item">
              <span>运行中</span>
              <strong style="color:#e6a23c">{{ taskSummary.running }}</strong>
            </div>
            <div class="summary-item">
              <span>已完成</span>
              <strong style="color:#67c23a">{{ taskSummary.completed }}</strong>
            </div>
            <div class="summary-item">
              <span>其他</span>
              <strong>{{ taskSummary.other }}</strong>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统健康 -->
    <el-card class="panel" style="margin-top:20px;">
      <template #header><span>系统健康检查</span></template>
      <div class="health-check" v-if="healthData">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="服务名称">{{ healthData.service }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ healthData.version }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="healthData.status === 'healthy' ? 'success' : 'danger'" size="small">
              {{ healthData.status === 'healthy' ? '健康' : '异常' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as api from '../api'
import { useSimulationStore, useSystemStore } from '../stores'

const simStore = useSimulationStore()
const sysStore = useSystemStore()

const healthData = ref<any>(null)
const systemStatus = ref<any>(null)
const aiStats = ref<any>(null)
const cleaning = ref(false)
const cleanResult = ref<any>(null)

const taskSummary = computed(() => {
  const tasks = simStore.tasks
  return {
    total: tasks.length,
    running: tasks.filter(t => t.status === 'running').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    other: tasks.filter(t => t.status !== 'running' && t.status !== 'completed').length,
  }
})

function componentLabel(name: string) {
  const map: Record<string, string> = {
    simulation_engine: '仿真引擎',
    ai_agent: 'AI 智能体',
    data_collector: '数据采集',
    cleaner_service: '清理服务',
  }
  return map[name] || name
}

async function refreshStatus() {
  try {
    const [healthRes, statusRes, statsRes] = await Promise.all([
      api.getSystemHealth(),
      api.getSystemStatus(),
      api.getAgentStats().catch(() => ({ data: null })),
    ])
    healthData.value = healthRes.data
    systemStatus.value = statusRes.data
    aiStats.value = statsRes.data
  } catch { /* ignore */ }
  await simStore.fetchTasks()
}

async function cleanSystem() {
  cleaning.value = true
  try {
    const { data } = await api.triggerSystemClean()
    cleanResult.value = data
  } catch {
    cleanResult.value = { message: '清理失败' }
  } finally {
    cleaning.value = false
  }
}

function resetAll() {
  // 清空当前选中任务
  simStore.currentTask = null
}

onMounted(() => {
  refreshStatus()
})
</script>

<style scoped>
.system-view h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
.service-list { display: flex; flex-direction: column; gap: 12px; }
.service-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #16213e; border-radius: 6px; }
.service-name { font-size: 14px; color: #e0e0e0; }
.ai-stats { display: flex; flex-direction: column; gap: 12px; }
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
.stat-row .label { color: #888; font-size: 14px; }
.stat-row .value { color: #e0e0e0; font-size: 14px; font-weight: 600; }
.ops-grid { display: flex; gap: 12px; flex-wrap: wrap; }
.task-summary { display: flex; gap: 20px; }
.summary-item { text-align: center; flex: 1; background: #16213e; padding: 16px; border-radius: 8px; }
.summary-item span { display: block; color: #888; font-size: 12px; margin-bottom: 8px; }
.summary-item strong { font-size: 24px; color: #00d4ff; }
</style>
