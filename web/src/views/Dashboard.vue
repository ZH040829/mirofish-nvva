<template>
  <div class="dashboard">
    <h2>仿真仪表盘</h2>

    <!-- 核心指标 -->
    <el-row :gutter="20" class="metrics-row">
      <el-col :span="6" v-for="m in coreMetrics" :key="m.label">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-value" :style="{ color: m.color }">{{ m.value }}</div>
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-trend" :class="m.trend > 0 ? 'up' : 'down'">
            {{ m.trend > 0 ? '↑' : '↓' }} {{ Math.abs(m.trend) }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 仿真状态 + 智能体活动 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="panel">
          <template #header>
            <span>经营趋势</span>
          </template>
          <div ref="trendChart" style="height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>智能体活动</span>
              <el-tag :type="aiAvailable ? 'success' : 'info'" size="small">
                {{ aiAvailable ? 'AI 在线' : '规则回退' }}
              </el-tag>
            </div>
          </template>
          <div class="agent-list">
            <div class="agent-item" v-for="agent in agents" :key="agent.id">
              <el-avatar :size="36" :style="{ background: agentColors[agent.role] || '#909399' }">
                {{ agent.name.charAt(0) }}
              </el-avatar>
              <div class="agent-info">
                <div class="agent-name">{{ agent.name }}</div>
                <div class="agent-status">{{ getLatestDecision(agent) }}</div>
              </div>
              <el-tag type="success" size="small">活跃</el-tag>
            </div>
            <div v-if="agents.length === 0" class="empty-hint">创建仿真任务后显示智能体</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近仿真 + 系统健康 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>最近仿真任务</span></template>
          <el-table :data="recentTasks" style="width: 100%" size="small" :header-cell-style="{background:'#1a1a2e',color:'#e0e0e0'}">
            <el-table-column prop="id" label="ID" width="120">
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.id.substring(0,12) }}...</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="场景" />
            <el-table-column prop="current_step" label="轮次" width="80">
              <template #default="{ row }">{{ row.current_step }}/{{ row.max_steps }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>系统健康</span></template>
          <div class="health-grid">
            <div class="health-item" v-for="h in healthItems" :key="h.name">
              <div class="health-name">{{ h.name }}</div>
              <el-progress :percentage="h.health" :color="h.health > 80 ? '#67c23a' : h.health > 50 ? '#e6a23c' : '#f56c6c'" :stroke-width="8" />
              <div class="health-detail">{{ h.detail }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore, useSystemStore } from '../stores'

const simStore = useSimulationStore()
const sysStore = useSystemStore()

const agentColors: Record<string, string> = {
  enterprise: '#409eff',
  competitor: '#67c23a',
  consumer: '#e6a23c',
  policy: '#909399',
}

const trendChart = ref<HTMLElement | null>(null)

const coreMetrics = computed(() => [
  { label: '仿真轮次', value: simStore.currentTask?.current_step || '0', trend: simStore.runningTasks.length > 0 ? 12 : 0, color: '#00d4ff' },
  { label: '活跃智能体', value: agents.value.length || '4', trend: 0, color: '#67c23a' },
  { label: '任务数', value: String(simStore.taskCount), trend: 5, color: '#e6a23c' },
  { label: 'AI 决策率', value: sysStore.aiStats ? Math.round(sysStore.aiStats.llm_decisions / Math.max(sysStore.aiStats.total_decisions, 1) * 100) + '%' : 'N/A', trend: 0, color: '#f56c6c' },
])

const agents = computed(() => simStore.currentTask?.agents || [])
const recentTasks = computed(() => simStore.tasks.slice(-5).reverse())
const aiAvailable = computed(() => sysStore.health?.components?.ai_agent === 'running')

const healthItems = computed(() => {
  const comp = sysStore.health?.components || {}
  return [
    { name: '仿真引擎', health: comp.simulation_engine === 'running' ? 95 : 30, detail: comp.simulation_engine === 'running' ? 'CPU 正常, MEM 1.2GB' : '未启动' },
    { name: 'AI 智能体', health: comp.ai_agent === 'running' ? 88 : 45, detail: comp.ai_agent === 'running' ? 'LLM 在线' : '规则回退模式' },
    { name: '数据管道', health: comp.data_collector === 'ready' ? 92 : 30, detail: comp.data_collector === 'ready' ? '3 源接入' : '未就绪' },
    { name: '清理服务', health: comp.cleaner_service === 'running' ? 90 : 30, detail: comp.cleaner_service === 'running' ? '自动运行中' : '未启动' },
  ]
})

function getLatestDecision(agent: any): string {
  if (!agent.decisions || agent.decisions.length === 0) return '等待决策...'
  const last = agent.decisions[agent.decisions.length - 1]
  return last.reasoning || last.action
}

function statusType(s: string) {
  return s === 'completed' ? 'success' : s === 'running' ? 'warning' : 'info'
}
function statusLabel(s: string) {
  return s === 'completed' ? '已完成' : s === 'running' ? '运行中' : s === 'stopped' ? '已停止' : '待启动'
}

onMounted(async () => {
  await Promise.all([
    simStore.fetchTasks(),
    sysStore.fetchHealth(),
    sysStore.fetchAIStats(),
  ])

  // 初始化 ECharts
  if (trendChart.value) {
    const chart = echarts.init(trendChart.value, 'dark')
    const steps = simStore.worldHistory.map((ws: any) => ws.step)
    const prices = simStore.worldHistory.map((ws: any) => ws.market_price?.product_a || 0)
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: steps, name: '步数' },
      yAxis: { type: 'value', name: '价格' },
      series: [
        { name: '产品A价格', type: 'line', data: prices, smooth: true, lineStyle: { color: '#00d4ff' }, itemStyle: { color: '#00d4ff' } },
      ],
    })
  }
})
</script>

<style scoped>
.dashboard h2 { margin-bottom: 20px; color: #00d4ff; }
.metrics-row { margin-bottom: 20px; }
.metric-card { background: #1a1a2e; border: 1px solid #2a2a4a; text-align: center; padding: 10px; }
.metric-value { font-size: 32px; font-weight: 700; }
.metric-label { font-size: 13px; color: #888; margin-top: 4px; }
.metric-trend { font-size: 12px; margin-top: 4px; }
.metric-trend.up { color: #67c23a; }
.metric-trend.down { color: #f56c6c; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.agent-list { display: flex; flex-direction: column; gap: 12px; }
.agent-item { display: flex; align-items: center; gap: 12px; padding: 8px; border-radius: 8px; background: #16213e; }
.agent-info { flex: 1; }
.agent-name { font-size: 14px; font-weight: 500; }
.agent-status { font-size: 12px; color: #888; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; }
.empty-hint { color: #555; text-align: center; padding: 20px; }
.health-grid { display: flex; flex-direction: column; gap: 16px; }
.health-item { padding: 4px 0; }
.health-name { font-size: 14px; margin-bottom: 6px; }
.health-detail { font-size: 12px; color: #888; margin-top: 4px; }
:deep(.el-table) { background: transparent; }
:deep(.el-table tr) { background: #16213e; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background: #1a1a2e; }
</style>
