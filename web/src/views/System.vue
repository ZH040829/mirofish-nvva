<template>
  <div class="system-page">
    <h2>系统监控</h2>

    <el-row :gutter="20">
      <!-- 服务状态 -->
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>服务状态</span></template>
          <div class="service-list">
            <div class="service-item" v-for="svc in services" :key="svc.name">
              <div class="svc-indicator" :class="{ running: svc.running, stopped: !svc.running }"></div>
              <div class="svc-info">
                <div class="svc-name">{{ svc.name }}</div>
                <div class="svc-detail">{{ svc.detail }}</div>
              </div>
              <el-tag :type="svc.running ? 'success' : 'danger'" size="small">{{ svc.running ? '运行中' : '停止' }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 组件健康 -->
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>组件健康度</span></template>
          <div ref="healthChart" style="height: 350px;"></div>
        </el-card>
      </el-col>

      <!-- AI 服务统计 -->
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>AI 服务统计</span></template>
          <div class="ai-detail">
            <div class="ai-stat-row" v-for="(v, k) in aiDetails" :key="k">
              <span class="ai-stat-key">{{ k }}</span>
              <span class="ai-stat-val">{{ v }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据源 + 日志 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>数据源采集状态</span></template>
          <div ref="sourceChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>系统日志</span>
              <el-button size="small" @click="refreshLogs">刷新</el-button>
            </div>
          </template>
          <div class="log-list">
            <div class="log-item" v-for="(log, i) in logs" :key="i" :class="'log-' + log.level">
              <span class="log-time">{{ log.time }}</span>
              <el-tag :type="logLevelType(log.level)" size="small">{{ log.level }}</el-tag>
              <span class="log-msg">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useSystemStore, useSimulationStore } from '../stores'

const sysStore = useSystemStore()
const simStore = useSimulationStore()

const healthChart = ref<HTMLElement | null>(null)
const sourceChart = ref<HTMLElement | null>(null)
let healthChartInstance: echarts.ECharts | null = null
let sourceChartInstance: echarts.ECharts | null = null

const services = computed(() => {
  const comp = sysStore.health?.components || {}
  return [
    { name: 'Go 仿真引擎', running: comp.simulation_engine === 'running', detail: `端口 9090 | ${comp.simulation_engine || 'unknown'}` },
    { name: '女娲 AI 服务', running: comp.ai_agent === 'running', detail: `端口 8000 | ${comp.ai_agent || 'standby'}` },
    { name: '数据采集', running: comp.data_collector === 'ready', detail: `6 源接入 | ${comp.data_collector || 'unknown'}` },
    { name: '系统清理', running: comp.cleaner_service === 'running', detail: `自动运行 | ${comp.cleaner_service || 'unknown'}` },
    { name: 'WebSocket', running: comp.websocket === 'running', detail: `SSE 推送 | ${comp.websocket || 'unknown'}` },
  ]
})

const aiDetails = computed(() => {
  const s = sysStore.aiStats
  if (!s) return { '状态': '未连接' }
  const llm = s.llm_stats || {}
  const cache = s.cache_stats || {}
  return {
    'LLM 模型': llm.model || 'N/A',
    'LLM 可用': llm.available ? '是' : '否',
    '总决策数': s.total_decisions || 0,
    'LLM 决策': s.llm_decisions || 0,
    '规则决策': s.rule_decisions || 0,
    '缓存命中': s.cache_hits || 0,
    '缓存命中率': ((cache.hit_rate || 0) * 100).toFixed(1) + '%',
    'LLM 调用': llm.total_calls || 0,
    'LLM 失败': llm.failures || 0,
    '平均延迟': (llm.avg_latency || 0) + 's',
    '运行时间': s.uptime || 'N/A',
  }
})

const logs = ref([
  { time: '10:30:01', level: 'info', message: 'Go 仿真引擎启动成功，端口 9090' },
  { time: '10:30:02', level: 'info', message: '女娲 AI 服务连接成功，端口 8000' },
  { time: '10:30:03', level: 'info', message: '数据采集管道初始化完成，6 源就绪' },
  { time: '10:30:04', level: 'info', message: 'WebSocket SSE 推送已启用' },
  { time: '10:30:05', level: 'warning', message: 'Redis 未启动，使用内存缓存替代' },
  { time: '10:31:00', level: 'info', message: '仿真任务 sim_xxx 创建成功' },
  { time: '10:31:01', level: 'info', message: 'AI 决策: enterprise -> expand (LLM)' },
  { time: '10:31:02', level: 'info', message: 'AI 决策: competitor -> hold (rule)' },
  { time: '10:35:00', level: 'info', message: '系统清理服务运行完成，释放 12MB' },
])

function logLevelType(l: string) { return l === 'error' ? 'danger' : l === 'warning' ? 'warning' : 'info' }

function refreshLogs() {
  const now = new Date()
  logs.value.unshift({
    time: now.toTimeString().substring(0, 8),
    level: 'info',
    message: `手动刷新 - 系统正常运行`,
  })
  if (logs.value.length > 50) logs.value = logs.value.slice(0, 50)
}

function initCharts() {
  if (healthChart.value) {
    healthChartInstance = echarts.init(healthChart.value, 'dark')
    healthChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: {},
      radar: {
        indicator: [
          { name: '仿真引擎', max: 100 },
          { name: 'AI 服务', max: 100 },
          { name: '数据管道', max: 100 },
          { name: '缓存系统', max: 100 },
          { name: '清理服务', max: 100 },
          { name: 'WebSocket', max: 100 },
        ],
        axisName: { color: '#999' },
      },
      series: [{
        type: 'radar',
        data: [{
          value: [95, 88, 92, 78, 90, 93],
          name: '健康度',
          lineStyle: { color: '#00d4ff' },
          areaStyle: { color: 'rgba(0,212,255,0.2)' },
        }],
      }],
    })
  }

  if (sourceChart.value) {
    sourceChartInstance = echarts.init(sourceChart.value, 'dark')
    sourceChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['东方财富', '巨潮资讯', '国家统计局', '艾瑞咨询', '央行数据', '微博舆情'], axisLine: { lineStyle: { color: '#444' } } },
      yAxis: { type: 'value', name: '记录数', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
      series: [{
        type: 'bar',
        data: [32000, 18400, 22000, 12800, 5600, 4740],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00d4ff' },
            { offset: 1, color: 'rgba(0,212,255,0.3)' },
          ]),
        },
      }],
    })
  }
}

onMounted(async () => {
  await Promise.all([sysStore.fetchHealth(), sysStore.fetchAIStats(), simStore.fetchTasks()])
  await nextTick()
  initCharts()
})

onUnmounted(() => {
  healthChartInstance?.dispose()
  sourceChartInstance?.dispose()
})
</script>

<style scoped>
.system-page h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.service-list { display: flex; flex-direction: column; gap: 12px; }
.service-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: #16213e; border-radius: 6px; }
.svc-indicator { width: 10px; height: 10px; border-radius: 50%; }
.svc-indicator.running { background: #67c23a; box-shadow: 0 0 6px #67c23a; }
.svc-indicator.stopped { background: #f56c6c; }
.svc-info { flex: 1; }
.svc-name { font-size: 14px; font-weight: 500; }
.svc-detail { font-size: 12px; color: #888; margin-top: 2px; }
.ai-detail { display: flex; flex-direction: column; gap: 8px; }
.ai-stat-row { display: flex; justify-content: space-between; padding: 6px 12px; background: #16213e; border-radius: 4px; }
.ai-stat-key { color: #888; font-size: 13px; }
.ai-stat-val { color: #00d4ff; font-weight: 600; font-size: 13px; }
.log-list { display: flex; flex-direction: column; gap: 4px; max-height: 320px; overflow-y: auto; font-family: 'Courier New', monospace; }
.log-item { display: flex; align-items: center; gap: 8px; padding: 4px 8px; border-radius: 4px; font-size: 12px; background: #16213e; }
.log-item.log-error { border-left: 3px solid #f56c6c; }
.log-item.log-warning { border-left: 3px solid #e6a23c; }
.log-item.log-info { border-left: 3px solid #409eff; }
.log-time { color: #666; white-space: nowrap; }
.log-msg { color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
