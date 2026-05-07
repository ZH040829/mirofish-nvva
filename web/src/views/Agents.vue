<template>
  <div class="agents-page">
    <h2>智能体管理</h2>

    <el-row :gutter="20">
      <!-- 智能体卡片 -->
      <el-col :span="6" v-for="agent in agents" :key="agent.id">
        <el-card class="agent-card" shadow="hover">
          <div class="agent-header" :style="{ borderColor: agentColors[agent.role] }">
            <el-avatar :size="48" :style="{ background: agentColors[agent.role] }">
              {{ agent.name.charAt(0) }}
            </el-avatar>
            <div class="agent-title">
              <div class="agent-name">{{ agent.name }}</div>
              <el-tag size="small" :type="roleTagType(agent.role)">{{ roleLabel(agent.role) }}</el-tag>
            </div>
          </div>
          <div class="agent-stats">
            <div class="stat-item"><span>资本</span><strong>{{ formatCapital(agent.capital) }}</strong></div>
            <div class="stat-item"><span>策略</span><strong>{{ agent.strategy }}</strong></div>
            <div class="stat-item"><span>决策数</span><strong>{{ agent.decisions?.length || 0 }}</strong></div>
          </div>
          <!-- 决策历史 -->
          <div class="decision-list">
            <div class="decision-item" v-for="(d, i) in (agent.decisions || []).slice(-5).reverse()" :key="i">
              <div class="decision-header">
                <el-tag size="small" :type="actionTagType(d.action)">{{ actionLabel(d.action) }}</el-tag>
                <span class="decision-step">Step {{ d.step }}</span>
              </div>
              <div class="decision-reason">{{ d.reasoning }}</div>
            </div>
            <div v-if="!agent.decisions || agent.decisions.length === 0" class="empty-hint">暂无决策</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 智能体关系图 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>决策分布</span></template>
          <div ref="decisionChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>AI 决策统计</span></template>
          <div class="ai-stats">
            <div class="stat-row" v-for="(val, key) in aiStats" :key="key">
              <span class="stat-key">{{ key }}</span>
              <span class="stat-val">{{ val }}</span>
            </div>
            <div v-if="Object.keys(aiStats).length === 0" class="empty-hint">无统计数据</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore, useSystemStore } from '../stores'

const simStore = useSimulationStore()
const sysStore = useSystemStore()

const agentColors: Record<string, string> = { enterprise: '#409eff', competitor: '#67c23a', consumer: '#e6a23c', policy: '#909399' }

const decisionChart = ref<HTMLElement | null>(null)
let decisionChartInstance: echarts.ECharts | null = null

const agents = computed(() => simStore.currentTask?.agents || [])
const aiStats = computed(() => {
  const s = sysStore.aiStats
  if (!s) return {}
  return {
    '总决策数': s.total_decisions || 0,
    'LLM 决策': s.llm_decisions || 0,
    '规则决策': s.rule_decisions || 0,
    '缓存命中': s.cache_hits || 0,
    'LLM 调用次数': s.llm_stats?.total_calls || 0,
    'LLM 失败次数': s.llm_stats?.failures || 0,
    '平均延迟': (s.llm_stats?.avg_latency || 0) + 's',
  }
})

function roleTagType(r: string) { const m: Record<string, string> = { enterprise: '', competitor: 'success', consumer: 'warning', policy: 'info' }; return m[r] || 'info' }
function roleLabel(r: string) { const m: Record<string, string> = { enterprise: '企业', competitor: '竞品', consumer: '消费者', policy: '政策' }; return m[r] || r }
function actionTagType(a: string) {
  const pos = ['expand', 'innovate', 'buy_more', 'subsidy', 'stimulate']
  const neg = ['cut_cost', 'price_war', 'reduce_consumption', 'tighten']
  if (pos.includes(a)) return 'success'
  if (neg.includes(a)) return 'danger'
  return 'info'
}
function actionLabel(a: string) {
  const m: Record<string, string> = { expand: '扩张', cut_cost: '削减', innovate: '创新', price_adjust: '调价', hold: '维持', price_war: '价格战', differentiate: '差异化', buy: '购买', buy_more: '增购', reduce_consumption: '减消', substitute: '替代', subsidy: '补贴', tax_relief: '减税', tighten: '收紧', stimulate: '刺激', observe: '观察' }
  return m[a] || a
}
function formatCapital(c: number) { return c >= 1000000 ? (c / 1000000).toFixed(1) + 'M' : c >= 1000 ? (c / 1000).toFixed(0) + 'K' : String(c) }

function initDecisionChart() {
  if (!decisionChart.value) return
  decisionChartInstance = echarts.init(decisionChart.value, 'dark')
  updateDecisionChart()
}

function updateDecisionChart() {
  if (!decisionChartInstance) return
  const ags = agents.value
  if (ags.length === 0) {
    decisionChartInstance.setOption({ backgroundColor: 'transparent', title: { text: '等待仿真数据', left: 'center', top: 'center', textStyle: { color: '#555' } } })
    return
  }
  const actionCounts: Record<string, number> = {}
  ags.forEach(a => (a.decisions || []).forEach(d => { actionCounts[d.action] = (actionCounts[d.action] || 0) + 1 }))
  decisionChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: Object.entries(actionCounts).map(([k, v]) => ({ name: actionLabel(k), value: v })),
      label: { color: '#999' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  })
}

onMounted(async () => {
  await simStore.fetchTasks()
  if (simStore.currentTask) await simStore.fetchTaskStatus(simStore.currentTask.id)
  await sysStore.fetchAIStats()
  await nextTick()
  initDecisionChart()
})

onUnmounted(() => { decisionChartInstance?.dispose() })
</script>

<style scoped>
.agents-page h2 { margin-bottom: 20px; color: #00d4ff; }
.agent-card { background: #1a1a2e; border: 1px solid #2a2a4a; }
.agent-header { display: flex; align-items: center; gap: 12px; padding-bottom: 12px; border-bottom: 2px solid; margin-bottom: 12px; }
.agent-title { flex: 1; }
.agent-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.agent-stats { display: flex; gap: 12px; margin-bottom: 12px; }
.stat-item { flex: 1; text-align: center; padding: 8px; background: #16213e; border-radius: 4px; }
.stat-item span { display: block; font-size: 12px; color: #888; margin-bottom: 4px; }
.stat-item strong { font-size: 14px; }
.decision-list { display: flex; flex-direction: column; gap: 6px; max-height: 200px; overflow-y: auto; }
.decision-item { padding: 6px 8px; background: #16213e; border-radius: 4px; }
.decision-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.decision-step { font-size: 11px; color: #666; }
.decision-reason { font-size: 12px; color: #aaa; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.ai-stats { display: flex; flex-direction: column; gap: 10px; }
.stat-row { display: flex; justify-content: space-between; padding: 8px 12px; background: #16213e; border-radius: 4px; }
.stat-key { color: #888; font-size: 14px; }
.stat-val { color: #00d4ff; font-weight: 600; }
.empty-hint { color: #555; text-align: center; padding: 20px; }
</style>
