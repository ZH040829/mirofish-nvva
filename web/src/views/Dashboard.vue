<template>
  <div class="dashboard">
    <h2>仿真仪表盘 <el-tag size="small" type="info">v1.5.0</el-tag></h2>

    <!-- AI 摘要横幅 -->
    <el-card v-if="dashboardSummary" class="summary-banner" shadow="hover">
      <div class="summary-content">
        <el-icon><Warning /></el-icon>
        <span>{{ dashboardSummary }}</span>
      </div>
    </el-card>

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

    <!-- 仿真趋势 + 智能体 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>经营趋势</span>
              <div>
                <el-tag size="small" type="info">实时</el-tag>
                <el-button size="small" type="primary" link @click="loadPrediction" style="margin-left:8px;">AI预测</el-button>
              </div>
            </div>
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
              <el-tag :type="getAgentTag(agent)" size="small">{{ getAgentAction(agent) }}</el-tag>
            </div>
            <div v-if="agents.length === 0" class="empty-hint">创建仿真任务后显示智能体</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- v1.5.0: 排行榜 + 财务概览 + 通知 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>排行榜</span></template>
          <div class="leaderboard">
            <div class="leader-item" v-for="entry in leaderboard" :key="entry.rank" :class="'rank-' + entry.rank">
              <div class="rank-badge">{{ entry.rank }}</div>
              <div class="leader-info">
                <div class="leader-name">{{ entry.agent_name }}</div>
                <div class="leader-detail">Lv.{{ entry.level }} | 净值 {{ formatMoney(entry.net_worth) }}</div>
              </div>
              <div class="leader-score">{{ entry.score }}</div>
            </div>
            <div v-if="leaderboard.length === 0" class="empty-hint">暂无排行数据</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>财务概览</span></template>
          <div ref="financeChart" style="height: 260px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>通知</span>
              <el-badge v-if="unreadCount > 0" :value="unreadCount" :max="99" />
            </div>
          </template>
          <div class="notif-list">
            <div class="notif-item" v-for="n in notifications" :key="n.id"
              :class="{ unread: !n.read }" @click="markRead(n)">
              <el-tag :type="notifType(n.type)" size="small" class="notif-tag">{{ n.title }}</el-tag>
              <div class="notif-msg">{{ n.message }}</div>
              <div class="notif-time">{{ n.time }}</div>
            </div>
            <div v-if="notifications.length === 0" class="empty-hint">暂无通知</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 供需雷达 + 最近仿真 + 风险预警 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>市场雷达</span></template>
          <div ref="radarChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>最近仿真任务</span></template>
          <el-table :data="recentTasks" style="width: 100%" size="small" :header-cell-style="{background:'#1a1a2e',color:'#e0e0e0'}">
            <el-table-column prop="id" label="ID" width="100">
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.id.substring(0,10) }}...</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="场景" />
            <el-table-column prop="current_step" label="轮次" width="80">
              <template #default="{ row }">{{ row.current_step }}/{{ row.max_steps }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>风险预警</span>
              <el-tag :type="riskLevelTag" size="small">{{ riskLevelLabel }}</el-tag>
            </div>
          </template>
          <div class="risk-list">
            <div class="risk-item" v-for="r in riskAlerts" :key="r.id" :class="'risk-' + r.level">
              <div class="risk-header">
                <el-tag :type="riskTagType(r.level)" size="small">{{ r.level }}</el-tag>
                <span class="risk-title">{{ r.title }}</span>
              </div>
              <div class="risk-desc">{{ r.description }}</div>
              <div class="risk-action" v-if="r.mitigation">建议: {{ r.mitigation }}</div>
            </div>
            <div v-if="riskAlerts.length === 0" class="empty-hint">暂无风险预警</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- v1.4.0: 市场情绪 + 行业赛道 + AI 对话 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>市场情绪仪表盘</span></template>
          <div ref="sentimentChart" style="height: 280px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>行业赛道</span></template>
          <div class="sector-grid">
            <div class="sector-item" v-for="s in sectors" :key="s.id"
              :class="{ active: activeSector === s.id }"
              @click="switchSector(s.id)">
              <div class="sector-name">{{ s.name }}</div>
              <div class="sector-desc">{{ s.description }}</div>
              <div class="sector-stats">波动{{ (s.volatility * 100).toFixed(0) }}% | 增长{{ (s.growthRate * 100).toFixed(0) }}%</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>AI 仿真助手</span></template>
          <div class="chat-box">
            <div class="chat-messages" ref="chatMessagesEl">
              <div v-for="(msg, i) in chatMessages" :key="i" :class="['chat-msg', msg.role]">
                <span class="msg-text">{{ msg.text }}</span>
              </div>
            </div>
            <div class="chat-input">
              <el-input v-model="chatInput" placeholder="输入指令...如: 推演3步、查看风险、交易建议" @keyup.enter="sendChat" size="small">
                <template #append>
                  <el-button @click="sendChat" :loading="chatLoading" size="small">发送</el-button>
                </template>
              </el-input>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore, useSystemStore } from '../stores'
import { mirofishApi } from '../api'
import { demoData, isDemoMode } from '../api/demo'

const simStore = useSimulationStore()
const sysStore = useSystemStore()
const demo = isDemoMode()

// v1.5.0: Dashboard summary, leaderboard, notifications, risk, finance
const dashboardSummary = ref('')
const leaderboard = ref<any[]>([])
const notifications = ref<any[]>([])
const riskAlerts = ref<any[]>([])
const financeChart = ref<HTMLElement | null>(null)
let financeChartInstance: echarts.ECharts | null = null

const unreadCount = computed(() => notifications.value.filter((n: any) => !n.read).length)
const riskLevelLabel = computed(() => {
  if (riskAlerts.value.length === 0) return '安全'
  const levels = riskAlerts.value.map((r: any) => r.level)
  if (levels.includes('critical')) return '严重'
  if (levels.includes('high')) return '高风险'
  if (levels.includes('medium')) return '中等'
  return '低风险'
})
const riskLevelTag = computed(() => {
  const l = riskLevelLabel.value
  if (l === '严重' || l === '高风险') return 'danger'
  if (l === '中等') return 'warning'
  return 'success'
})

function riskTagType(level: string) {
  if (level === 'critical' || level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  return 'success'
}
function notifType(type: string) {
  if (type === 'danger') return 'danger'
  if (type === 'warning') return 'warning'
  if (type === 'success') return 'success'
  return 'info'
}
function formatMoney(n: number) {
  if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(0) + '万'
  return n.toLocaleString()
}

async function markRead(n: any) {
  if (n.read) return
  n.read = true
  if (!demo) {
    try { await mirofishApi.markNotificationRead(n.id) } catch { /* ignore */ }
  }
}

async function loadDashboard(taskId: string) {
  if (demo) {
    const db = demoData.dashboard
    if (db) {
      leaderboard.value = demoData.leaderboard || []
      notifications.value = demoData.notifications || []
      riskAlerts.value = demoData.riskAlerts || []
      dashboardSummary.value = db.summary || ''
    }
    return
  }
  try {
    const data = await mirofishApi.getDashboard(taskId)
    if (data) {
      leaderboard.value = data.leaderboard || data.entries || []
      dashboardSummary.value = data.summary || ''
    }
  } catch { /* ignore */ }
  try {
    const nData = await mirofishApi.getNotifications(taskId)
    notifications.value = nData.notifications || []
  } catch { /* ignore */ }
  try {
    const rData = await mirofishApi.getRiskAlerts(taskId)
    riskAlerts.value = rData.alerts || []
  } catch { /* ignore */ }
  try {
    const lData = await mirofishApi.getLeaderboard(taskId)
    leaderboard.value = lData.entries || []
  } catch { /* ignore */ }
}

function initFinanceChart() {
  if (!financeChart.value) return
  financeChartInstance = echarts.init(financeChart.value, 'dark')
  updateFinanceChart()
}

function updateFinanceChart() {
  if (!financeChartInstance) return
  if (demo) {
    const financeData = demoData.finance || []
    financeChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#999' } },
      grid: { top: 30, bottom: 30, left: 60, right: 20 },
      xAxis: { type: 'category', data: financeData.map((f: any) => f.agent_name), axisLine: { lineStyle: { color: '#444' } } },
      yAxis: { type: 'value', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
      series: [
        { name: '收入', type: 'bar', data: financeData.map((f: any) => f.revenue / 10000), itemStyle: { color: '#67c23a' } },
        { name: '成本', type: 'bar', data: financeData.map((f: any) => f.cost / 10000), itemStyle: { color: '#f56c6c' } },
        { name: '利润', type: 'bar', data: financeData.map((f: any) => f.profit / 10000), itemStyle: { color: '#409eff' } },
      ],
    })
    return
  }
  // Use store data
  const finance = simStore.finance
  if (finance.length === 0) return
  financeChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#999' } },
    grid: { top: 30, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category', data: finance.map((f: any) => f.agent_name), axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
    series: [
      { name: '收入', type: 'bar', data: finance.map((f: any) => (f.revenue || 0) / 10000), itemStyle: { color: '#67c23a' } },
      { name: '成本', type: 'bar', data: finance.map((f: any) => (f.cost || 0) / 10000), itemStyle: { color: '#f56c6c' } },
      { name: '利润', type: 'bar', data: finance.map((f: any) => (f.profit || 0) / 10000), itemStyle: { color: '#409eff' } },
    ],
  })
}

async function loadPrediction() {
  const taskId = simStore.currentTask?.id
  if (!taskId && !demo) return
  try {
    const prices = simStore.worldHistory.map((h: any) => h.market_price?.product_a || 100)
    const data = demo ? demoData.marketPrediction : await mirofishApi.marketPredict({
      price_history: prices, supply: 1100, demand: 1050,
      sentiment: sentiment.value
    })
    if (data && data.price_forecast && trendChartInstance) {
      const currentSteps = simStore.worldHistory.map((h: any) => h.step || 0)
      const lastStep = currentSteps[currentSteps.length - 1] || 0
      const forecastSteps = data.price_forecast.map((_: any, i: number) => lastStep + i + 1)
      const allSteps = [...currentSteps, ...forecastSteps]
      const actualPrices = simStore.worldHistory.map((h: any) => h.market_price?.product_a || 0)
      const lastPrice = actualPrices[actualPrices.length - 1] || 100
      const forecastData = [...Array(actualPrices.length - 1).fill(null), lastPrice, ...data.price_forecast]
      trendChartInstance.setOption({
        xAxis: { data: allSteps },
        series: [
          { data: actualPrices },
          { data: simStore.worldHistory.map((h: any) => h.market_price?.product_b || 0) },
          { data: simStore.worldHistory.map((h: any) => h.market_price?.raw_material || 0) },
          { name: 'AI预测', type: 'line', data: forecastData, lineStyle: { color: '#ff6b6b', type: 'dashed', width: 2 }, itemStyle: { color: '#ff6b6b' }, symbol: 'diamond' },
        ],
      })
    }
  } catch { /* ignore */ }
}

// v1.4.0: Sentiment, Sectors, Chat
const sentimentChart = ref<HTMLElement | null>(null)
let sentimentChartInstance: echarts.ECharts | null = null
const sentiment = ref({ overall: 50, greed: 30, fear: 20, optimism: 60, volatility: 30, confidence: 55, description: '市场情绪中性' })
const sectors = ref<any[]>([])
const activeSector = ref('tech')
const chatMessages = ref<{role: string, text: string}[]>([
  { role: 'assistant', text: '你好！我是女娲AI仿真助手 v1.5。试试: "创建科技仿真"、"推演3步"、"查看风险"、"交易建议"' }
])
const chatInput = ref('')
const chatLoading = ref(false)
const chatMessagesEl = ref<HTMLElement | null>(null)

const agentColors: Record<string, string> = {
  enterprise: '#409eff',
  competitor: '#67c23a',
  consumer: '#e6a23c',
  policy: '#909399',
}

const trendChart = ref<HTMLElement | null>(null)
const radarChart = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null
let radarChartInstance: echarts.ECharts | null = null
let refreshTimer: number | null = null

const coreMetrics = computed(() => {
  const aiStats = sysStore.aiStats
  const totalDec = aiStats?.total_decisions || 0
  const llmDec = aiStats?.llm_decisions || 0
  const aiRate = totalDec > 0 ? Math.round(llmDec / totalDec * 100) : 0
  const db = demo ? demoData.dashboard : simStore.dashboard
  return [
    { label: '仿真轮次', value: simStore.currentTask?.current_step || db?.total_steps || '0', trend: 12, color: '#00d4ff' },
    { label: '活跃智能体', value: String(agents.value.length || db?.active_agents || 4), trend: 0, color: '#67c23a' },
    { label: '总交易额', value: db?.total_trade_value ? formatMoney(db.total_trade_value) : '0', trend: 8, color: '#e6a23c' },
    { label: 'AI 决策率', value: totalDec > 0 ? aiRate + '%' : 'N/A', trend: 0, color: '#f56c6c' },
  ]
})

const agents = computed(() => simStore.currentTask?.agents || [])
const recentTasks = computed(() => simStore.tasks.slice(-5).reverse())
const aiAvailable = computed(() => sysStore.health?.components?.ai_agent === 'running')

const healthItems = computed(() => {
  const comp = sysStore.health?.components || {}
  return [
    { name: '仿真引擎', health: comp.simulation_engine === 'running' ? 95 : 30, detail: comp.simulation_engine === 'running' ? 'CPU 正常, MEM 1.2GB' : '未启动' },
    { name: 'AI 智能体', health: comp.ai_agent === 'running' ? 88 : 45, detail: comp.ai_agent === 'running' ? 'LLM 在线' : '规则回退模式' },
    { name: '数据管道', health: comp.data_collector === 'ready' ? 92 : 30, detail: comp.data_collector === 'ready' ? '6 源接入' : '未就绪' },
    { name: '清理服务', health: comp.cleaner_service === 'running' ? 90 : 30, detail: comp.cleaner_service === 'running' ? '自动运行中' : '未启动' },
    { name: 'WebSocket', health: comp.websocket === 'running' ? 93 : 30, detail: comp.websocket === 'running' ? 'SSE 已连接' : '未连接' },
  ]
})

function getLatestDecision(agent: any): string {
  if (!agent.decisions || agent.decisions.length === 0) return '等待决策...'
  const last = agent.decisions[agent.decisions.length - 1]
  return last.reasoning || last.action
}

function getAgentTag(agent: any): string {
  if (!agent.decisions || agent.decisions.length === 0) return 'info'
  const last = agent.decisions[agent.decisions.length - 1]
  const action = last.action || ''
  if (['expand', 'innovate', 'buy_more'].includes(action)) return 'success'
  if (['cut_cost', 'reduce_consumption'].includes(action)) return 'danger'
  if (['price_war', 'tighten'].includes(action)) return 'warning'
  return 'info'
}

function getAgentAction(agent: any): string {
  if (!agent.decisions || agent.decisions.length === 0) return '等待'
  const last = agent.decisions[agent.decisions.length - 1]
  const map: Record<string, string> = {
    expand: '扩张', cut_cost: '削减', innovate: '创新', price_adjust: '调价', hold: '维持',
    price_war: '价格战', differentiate: '差异化', buy: '购买', buy_more: '增购',
    reduce_consumption: '减消', substitute: '替代', subsidy: '补贴', tax_relief: '减税',
    tighten: '收紧', stimulate: '刺激', observe: '观察',
  }
  return map[last.action] || last.action
}

function statusType(s: string) {
  return s === 'completed' ? 'success' : s === 'running' ? 'warning' : 'info'
}
function statusLabel(s: string) {
  return s === 'completed' ? '已完成' : s === 'running' ? '运行中' : s === 'stopped' ? '已停止' : '待启动'
}

function initCharts() {
  if (trendChart.value) {
    trendChartInstance = echarts.init(trendChart.value, 'dark')
    trendChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { data: ['产品A价格', '产品B价格', '原材料', 'AI预测'], textStyle: { color: '#999' } },
      xAxis: { type: 'category', data: [], name: '步数', axisLine: { lineStyle: { color: '#444' } } },
      yAxis: { type: 'value', name: '价格', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
      series: [
        { name: '产品A价格', type: 'line', data: [], smooth: true, lineStyle: { color: '#00d4ff' }, itemStyle: { color: '#00d4ff' } },
        { name: '产品B价格', type: 'line', data: [], smooth: true, lineStyle: { color: '#67c23a' }, itemStyle: { color: '#67c23a' } },
        { name: '原材料', type: 'line', data: [], smooth: true, lineStyle: { color: '#e6a23c', type: 'dashed' }, itemStyle: { color: '#e6a23c' } },
        { name: 'AI预测', type: 'line', data: [], lineStyle: { color: '#ff6b6b', type: 'dashed', width: 2 }, itemStyle: { color: '#ff6b6b' }, symbol: 'diamond' },
      ],
    })
  }
  if (radarChart.value) {
    radarChartInstance = echarts.init(radarChart.value, 'dark')
    radarChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: {},
      radar: {
        indicator: [
          { name: '价格水平', max: 200 },
          { name: '供给量', max: 3000 },
          { name: '需求量', max: 3000 },
          { name: '税率', max: 30 },
          { name: '补贴', max: 1000000 },
        ],
        axisName: { color: '#999' },
        splitArea: { areaStyle: { color: ['rgba(0,212,255,0.05)', 'rgba(0,212,255,0.1)'] } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: [100, 1000, 900, 13, 0],
          name: '当前状态',
          lineStyle: { color: '#00d4ff' },
          areaStyle: { color: 'rgba(0,212,255,0.2)' },
        }],
      }],
    })
  }
}

function updateCharts() {
  const ws = simStore.currentTask?.world_state
  if (!ws || !trendChartInstance) return

  const history = simStore.worldHistory
  if (history.length > 0) {
    const steps = history.map((h: any) => h.step || 0)
    const pricesA = history.map((h: any) => h.market_price?.product_a || 0)
    const pricesB = history.map((h: any) => h.market_price?.product_b || 0)
    const rawMat = history.map((h: any) => h.market_price?.raw_material || 0)
    trendChartInstance.setOption({
      xAxis: { data: steps },
      series: [{ data: pricesA }, { data: pricesB }, { data: rawMat }],
    })
  }

  if (radarChartInstance && ws.market_price) {
    radarChartInstance.setOption({
      series: [{
        data: [{
          value: [
            ws.market_price.product_a || 0,
            ws.supply?.product_a || 0,
            ws.demand?.product_a || 0,
            (ws.policy?.tax_rate || 0) * 100,
            ws.policy?.subsidy || 0,
          ],
          name: '当前状态',
        }],
      }],
    })
  }
}

async function refreshData() {
  if (demo) {
    // In demo mode, use demo data
    leaderboard.value = demoData.leaderboard || []
    notifications.value = demoData.notifications || []
    riskAlerts.value = demoData.riskAlerts || []
    dashboardSummary.value = demoData.dashboard?.summary || ''
    return
  }
  await Promise.all([
    sysStore.fetchHealth(),
    sysStore.fetchAIStats(),
  ])
  const running = simStore.currentTask
  if (running) {
    await Promise.all([
      simStore.fetchHistory(running.id),
      simStore.fetchTaskStatus(running.id),
      loadDashboard(running.id),
    ])
    updateCharts()
    updateFinanceChart()
  }
}

// Sentiment chart
function initSentimentChart() {
  if (!sentimentChart.value) return
  sentimentChartInstance = echarts.init(sentimentChart.value, 'dark')
  updateSentimentChart()
}

function updateSentimentChart() {
  if (!sentimentChartInstance) return
  const s = sentiment.value
  sentimentChartInstance.setOption({
    series: [{
      type: 'gauge', center: ['50%', '60%'], radius: '85%',
      min: 0, max: 100,
      axisLine: { lineStyle: { width: 15, color: [[0.25, '#f56c6c'], [0.5, '#e6a23c'], [0.75, '#67c23a'], [1, '#409eff']] } },
      pointer: { width: 5 },
      detail: { formatter: '{value}', fontSize: 28, offsetCenter: [0, '30%'], color: '#e0e0e0' },
      title: { show: true, offsetCenter: [0, '60%'], fontSize: 14, color: '#888' },
      data: [{ value: Math.round(s.overall), name: s.description }]
    }]
  })
}

async function loadSectors() {
  try {
    const res = await mirofishApi.getSectors()
    sectors.value = res.sectors || []
  } catch { sectors.value = [
    { id: 'tech', name: '科技', description: '高波动高增长', volatility: 0.08, growthRate: 0.12 },
    { id: 'consumer', name: '消费品', description: '稳定低波动', volatility: 0.03, growthRate: 0.05 },
    { id: 'finance', name: '金融', description: '政策敏感', volatility: 0.06, growthRate: 0.08 },
    { id: 'energy', name: '能源', description: '资源依赖', volatility: 0.10, growthRate: 0.06 },
    { id: 'healthcare', name: '医疗', description: '刚需驱动', volatility: 0.04, growthRate: 0.09 },
  ]}
}

async function switchSector(sectorId: string) {
  activeSector.value = sectorId
  try {
    await mirofishApi.switchSector(sectorId, simStore.currentTask?.id || '')
    chatMessages.value.push({ role: 'assistant', text: `已切换到${sectorId}赛道` })
  } catch { /* ignore */ }
}

async function sendChat() {
  const msg = chatInput.value.trim()
  if (!msg) return
  chatMessages.value.push({ role: 'user', text: msg })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const res = await mirofishApi.chatControl(msg, simStore.currentTask?.id || '')
    chatMessages.value.push({ role: 'assistant', text: res.response })
  } catch {
    chatMessages.value.push({ role: 'assistant', text: '暂时无法响应，请稍后再试。' })
  }
  chatLoading.value = false
  await nextTick()
  if (chatMessagesEl.value) chatMessagesEl.value.scrollTop = chatMessagesEl.value.scrollHeight
}

async function loadSentiment() {
  const taskId = simStore.currentTask?.id
  if (!taskId && !demo) return
  if (demo) {
    sentiment.value = demoData.sentiment.sentiment
    updateSentimentChart()
    return
  }
  try {
    const res = await mirofishApi.getSentiment(taskId)
    if (res.sentiment) sentiment.value = res.sentiment
    updateSentimentChart()
  } catch { /* ignore */ }
}

onMounted(async () => {
  await refreshData()
  await nextTick()
  initCharts()
  updateCharts()
  initSentimentChart()
  initFinanceChart()
  await loadSectors()
  await loadSentiment()

  // Demo mode initialization
  if (demo) {
    leaderboard.value = demoData.leaderboard || []
    notifications.value = demoData.notifications || []
    riskAlerts.value = demoData.riskAlerts || []
    dashboardSummary.value = demoData.dashboard?.summary || ''
  }

  refreshTimer = window.setInterval(async () => {
    await refreshData()
    await loadSentiment()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  trendChartInstance?.dispose()
  radarChartInstance?.dispose()
  sentimentChartInstance?.dispose()
  financeChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard h2 { margin-bottom: 20px; color: #00d4ff; }
.summary-banner { background: linear-gradient(135deg, #1a2a3a, #0d1b2a); border: 1px solid #2a4a6a; margin-bottom: 20px; }
.summary-content { display: flex; align-items: center; gap: 8px; color: #e0e0e0; font-size: 14px; }
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
.empty-hint { color: #555; text-align: center; padding: 20px; font-size: 13px; }
.health-grid { display: flex; flex-direction: column; gap: 12px; }
.health-item { padding: 4px 0; }
.health-name { font-size: 14px; margin-bottom: 6px; }
.health-detail { font-size: 12px; color: #888; margin-top: 4px; }
:deep(.el-table) { background: transparent; }
:deep(.el-table tr) { background: #16213e; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background: #1a1a2e; }
/* v1.5.0: Leaderboard */
.leaderboard { display: flex; flex-direction: column; gap: 10px; }
.leader-item { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 8px; background: #16213e; transition: all 0.2s; }
.leader-item:hover { background: #1a2a3a; }
.leader-item.rank-1 { border-left: 3px solid #ffd700; }
.leader-item.rank-2 { border-left: 3px solid #c0c0c0; }
.leader-item.rank-3 { border-left: 3px solid #cd7f32; }
.rank-badge { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
.rank-1 .rank-badge { background: #ffd700; color: #000; }
.rank-2 .rank-badge { background: #c0c0c0; color: #000; }
.rank-3 .rank-badge { background: #cd7f32; color: #fff; }
.rank-4 .rank-badge { background: #444; color: #aaa; }
.leader-info { flex: 1; }
.leader-name { font-size: 14px; font-weight: 500; }
.leader-detail { font-size: 12px; color: #888; }
.leader-score { font-size: 20px; font-weight: 700; color: #00d4ff; }
/* v1.5.0: Notifications */
.notif-list { max-height: 260px; overflow-y: auto; }
.notif-item { padding: 8px; border-radius: 6px; margin-bottom: 6px; background: #16213e; cursor: pointer; transition: all 0.2s; }
.notif-item:hover { background: #1a2a3a; }
.notif-item.unread { border-left: 3px solid #409eff; }
.notif-tag { margin-right: 6px; }
.notif-msg { font-size: 13px; color: #ccc; margin-top: 4px; }
.notif-time { font-size: 11px; color: #666; margin-top: 2px; }
/* v1.5.0: Risk alerts */
.risk-list { max-height: 260px; overflow-y: auto; }
.risk-item { padding: 10px; border-radius: 6px; margin-bottom: 8px; background: #16213e; border-left: 3px solid; }
.risk-item.risk-critical { border-left-color: #f56c6c; }
.risk-item.risk-high { border-left-color: #e6a23c; }
.risk-item.risk-medium { border-left-color: #f7ba2a; }
.risk-item.risk-low { border-left-color: #67c23a; }
.risk-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.risk-title { font-size: 14px; font-weight: 500; }
.risk-desc { font-size: 13px; color: #ccc; }
.risk-action { font-size: 12px; color: #67c23a; margin-top: 4px; }
/* Sectors */
.sector-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sector-item { padding: 10px; border-radius: 8px; background: #16213e; cursor: pointer; transition: all 0.2s; border: 1px solid transparent; }
.sector-item:hover { border-color: #00d4ff; }
.sector-item.active { border-color: #00d4ff; background: #0d2a4a; }
.sector-name { font-size: 14px; font-weight: 500; margin-bottom: 2px; }
.sector-desc { font-size: 11px; color: #888; }
.sector-stats { font-size: 11px; color: #00d4ff; margin-top: 4px; }
/* Chat */
.chat-box { display: flex; flex-direction: column; height: 300px; }
.chat-messages { flex: 1; overflow-y: auto; padding: 8px; }
.chat-msg { margin-bottom: 8px; padding: 6px 10px; border-radius: 8px; max-width: 85%; font-size: 13px; line-height: 1.5; }
.chat-msg.user { background: #2a4a6a; margin-left: auto; color: #e0e0e0; }
.chat-msg.assistant { background: #1a2a3a; color: #ccc; }
.chat-input { padding-top: 8px; border-top: 1px solid #2a2a4a; }
</style>
