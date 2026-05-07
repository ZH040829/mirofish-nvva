<template>
  <div class="simulation">
    <h2>仿真推演</h2>

    <el-row :gutter="20">
      <!-- 左侧：控制面板 -->
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>仿真控制</span></template>
          <el-form :model="createForm" label-width="80px" size="default">
            <el-form-item label="场景名称">
              <el-input v-model="createForm.name" placeholder="输入仿真场景名称" />
            </el-form-item>
            <el-form-item label="最大轮次">
              <el-input-number v-model="createForm.max_steps" :min="1" :max="200" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="createSim" :loading="creating">创建仿真</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="panel" style="margin-top: 20px;" v-if="currentSim">
          <template #header><span>推演控制</span></template>
          <div class="sim-info">
            <div class="sim-info-row"><span>场景:</span><strong>{{ currentSim.name }}</strong></div>
            <div class="sim-info-row"><span>轮次:</span><strong>{{ currentSim.current_step }} / {{ currentSim.max_steps }}</strong></div>
            <div class="sim-info-row"><span>状态:</span>
              <el-tag :type="statusType(currentSim.status)" size="small">{{ statusLabel(currentSim.status) }}</el-tag>
            </div>
          </div>
          <div class="sim-actions">
            <el-button type="success" @click="stepSim" :loading="stepping" :disabled="currentSim.status === 'completed'">
              单步推演
            </el-button>
            <el-button type="warning" @click="autoStep" :disabled="autoRunning || currentSim.status === 'completed'">
              {{ autoRunning ? '自动运行中...' : '自动推演' }}
            </el-button>
            <el-button @click="stopAuto" :disabled="!autoRunning">停止</el-button>
          </div>
        </el-card>

        <el-card class="panel" style="margin-top: 20px;">
          <template #header><span>仿真任务列表</span></template>
          <div class="task-list">
            <div class="task-item" v-for="t in tasks" :key="t.id" @click="selectTask(t)" :class="{ active: currentSim?.id === t.id }">
              <div class="task-name">{{ t.name }}</div>
              <div class="task-meta">Step {{ t.current_step }}/{{ t.max_steps }}</div>
              <el-tag :type="statusType(t.status)" size="small">{{ statusLabel(t.status) }}</el-tag>
            </div>
            <div v-if="tasks.length === 0" class="empty-hint">暂无仿真任务</div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：仿真可视化 -->
      <el-col :span="16">
        <!-- 价格走势图 -->
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>价格走势</span>
              <el-tag size="small" type="info">步数: {{ historyData.length }}</el-tag>
            </div>
          </template>
          <div ref="priceChart" style="height: 300px;"></div>
        </el-card>

        <!-- 世界状态 + 事件 -->
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="12">
            <el-card class="panel">
              <template #header><span>世界状态</span></template>
              <div class="world-state" v-if="worldState">
                <div class="ws-section">
                  <h4>市场价格</h4>
                  <div class="ws-grid">
                    <div class="ws-item"><span>产品A</span><strong>{{ worldState.market_price?.product_a?.toFixed(1) }}</strong></div>
                    <div class="ws-item"><span>产品B</span><strong>{{ worldState.market_price?.product_b?.toFixed(1) }}</strong></div>
                    <div class="ws-item"><span>原材料</span><strong>{{ worldState.market_price?.raw_material?.toFixed(1) }}</strong></div>
                  </div>
                </div>
                <div class="ws-section">
                  <h4>供需关系</h4>
                  <div class="ws-grid">
                    <div class="ws-item"><span>A供给</span><strong>{{ worldState.supply?.product_a?.toFixed(0) }}</strong></div>
                    <div class="ws-item"><span>A需求</span><strong>{{ worldState.demand?.product_a?.toFixed(0) }}</strong></div>
                    <div class="ws-item"><span>B供给</span><strong>{{ worldState.supply?.product_b?.toFixed(0) }}</strong></div>
                    <div class="ws-item"><span>B需求</span><strong>{{ worldState.demand?.product_b?.toFixed(0) }}</strong></div>
                  </div>
                </div>
                <div class="ws-section">
                  <h4>政策</h4>
                  <div class="ws-grid">
                    <div class="ws-item"><span>税率</span><strong>{{ (worldState.policy?.tax_rate * 100)?.toFixed(1) }}%</strong></div>
                    <div class="ws-item"><span>利率</span><strong>{{ (worldState.policy?.interest_rate * 100)?.toFixed(2) }}%</strong></div>
                    <div class="ws-item"><span>补贴</span><strong>{{ worldState.policy?.subsidy?.toFixed(0) }}</strong></div>
                  </div>
                </div>
              </div>
              <div v-else class="empty-hint">请选择或创建仿真任务</div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="panel">
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <span>事件流</span>
                  <el-tag size="small" type="warning">{{ currentEvents.length }} 个事件</el-tag>
                </div>
              </template>
              <div class="event-list">
                <div class="event-item" v-for="(e, i) in currentEvents" :key="i">
                  <el-tag :type="eventTypeTag(e.type)" size="small" style="margin-right:8px;">{{ e.type }}</el-tag>
                  <span class="event-name">{{ e.name }}</span>
                  <span class="event-desc">{{ e.description }}</span>
                </div>
                <div v-if="currentEvents.length === 0" class="empty-hint">当前轮次无事件</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore } from '../stores'

const simStore = useSimulationStore()

const createForm = ref({ name: '企业经营仿真', max_steps: 50 })
const creating = ref(false)
const stepping = ref(false)
const autoRunning = ref(false)
let autoTimer: number | null = null

const priceChart = ref<HTMLElement | null>(null)
let priceChartInstance: echarts.ECharts | null = null

const currentSim = computed(() => simStore.currentTask)
const tasks = computed(() => simStore.tasks)
const worldState = computed(() => currentSim.value?.world_state)
const currentEvents = computed(() => worldState.value?.events || [])
const historyData = computed(() => simStore.worldHistory)

function statusType(s: string) { return s === 'completed' ? 'success' : s === 'running' ? 'warning' : 'info' }
function statusLabel(s: string) { return s === 'completed' ? '已完成' : s === 'running' ? '运行中' : s === 'stopped' ? '已停止' : '待启动' }
function eventTypeTag(t: string) {
  const map: Record<string, string> = { policy: 'warning', natural: 'danger', tech: 'success', market: 'info' }
  return map[t] || 'info'
}

async function createSim() {
  creating.value = true
  try {
    await simStore.createSimulation(createForm.value.name, createForm.value.max_steps)
    await simStore.fetchTasks()
  } finally {
    creating.value = false
  }
}

async function stepSim() {
  if (!currentSim.value) return
  stepping.value = true
  try {
    await simStore.stepSimulation(currentSim.value.id)
    await simStore.fetchTaskStatus(currentSim.value.id)
    await simStore.fetchHistory(currentSim.value.id)
    updatePriceChart()
  } finally {
    stepping.value = false
  }
}

async function autoStep() {
  autoRunning.value = true
  autoTimer = window.setInterval(async () => {
    if (!currentSim.value || currentSim.value.status === 'completed') {
      stopAuto()
      return
    }
    await stepSim()
  }, 1500)
}

function stopAuto() {
  autoRunning.value = false
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null }
}

async function selectTask(t: any) {
  simStore.selectTask(t.id)
  await simStore.fetchTaskStatus(t.id)
  await simStore.fetchHistory(t.id)
  updatePriceChart()
}

function initPriceChart() {
  if (priceChart.value) {
    priceChartInstance = echarts.init(priceChart.value, 'dark')
    priceChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { data: ['产品A', '产品B', '原材料'], textStyle: { color: '#999' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: [], name: '步数', axisLine: { lineStyle: { color: '#444' } } },
      yAxis: { type: 'value', name: '价格', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
      series: [
        { name: '产品A', type: 'line', data: [], smooth: true, lineStyle: { color: '#00d4ff', width: 2 }, itemStyle: { color: '#00d4ff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,212,255,0.3)' }, { offset: 1, color: 'rgba(0,212,255,0)' }] } } },
        { name: '产品B', type: 'line', data: [], smooth: true, lineStyle: { color: '#67c23a', width: 2 }, itemStyle: { color: '#67c23a' } },
        { name: '原材料', type: 'line', data: [], smooth: true, lineStyle: { color: '#e6a23c', type: 'dashed', width: 1 }, itemStyle: { color: '#e6a23c' } },
      ],
    })
  }
}

function updatePriceChart() {
  if (!priceChartInstance) return
  const h = historyData.value
  if (h.length === 0) return
  priceChartInstance.setOption({
    xAxis: { data: h.map((d: any) => d.step || 0) },
    series: [
      { data: h.map((d: any) => d.market_price?.product_a || 0) },
      { data: h.map((d: any) => d.market_price?.product_b || 0) },
      { data: h.map((d: any) => d.market_price?.raw_material || 0) },
    ],
  })
}

watch(historyData, () => updatePriceChart())

onMounted(async () => {
  await simStore.fetchTasks()
  await nextTick()
  initPriceChart()
  if (simStore.currentTask) {
    await simStore.fetchHistory(simStore.currentTask.id)
    updatePriceChart()
  }
})

onUnmounted(() => {
  stopAuto()
  priceChartInstance?.dispose()
})
</script>

<style scoped>
.simulation h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.sim-info { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.sim-info-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
.sim-info-row span { color: #888; }
.sim-actions { display: flex; gap: 8px; }
.task-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
.task-item { display: flex; align-items: center; gap: 8px; padding: 10px; border-radius: 6px; background: #16213e; cursor: pointer; transition: all .2s; }
.task-item:hover { background: #2a2a4a; }
.task-item.active { border-left: 3px solid #00d4ff; }
.task-name { flex: 1; font-size: 14px; }
.task-meta { font-size: 12px; color: #888; }
.world-state { display: flex; flex-direction: column; gap: 16px; }
.ws-section h4 { color: #00d4ff; font-size: 13px; margin-bottom: 8px; }
.ws-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.ws-item { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 8px; background: #16213e; border-radius: 4px; }
.ws-item span { color: #888; }
.ws-item strong { color: #e0e0e0; }
.event-list { display: flex; flex-direction: column; gap: 8px; max-height: 350px; overflow-y: auto; }
.event-item { display: flex; align-items: center; gap: 4px; padding: 6px 8px; background: #16213e; border-radius: 4px; font-size: 13px; }
.event-name { color: #e0e0e0; white-space: nowrap; }
.event-desc { color: #888; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-hint { color: #555; text-align: center; padding: 20px; }
</style>
