<template>
  <div class="data-pipeline">
    <h2>数据采集管道</h2>

    <!-- 数据源状态 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="src in dataSources" :key="src.name">
        <el-card class="source-card" shadow="hover">
          <div class="source-header">
            <div class="source-icon" :style="{ background: src.color }">
              {{ src.name.charAt(0) }}
            </div>
            <div class="source-info">
              <div class="source-name">{{ src.name }}</div>
              <el-tag :type="src.active ? 'success' : 'info'" size="small">{{ src.active ? '活跃' : '待激活' }}</el-tag>
            </div>
          </div>
          <div class="source-stats">
            <div class="s-stat">
              <div class="s-stat-val">{{ src.records.toLocaleString() }}</div>
              <div class="s-stat-label">记录数</div>
            </div>
            <div class="s-stat">
              <div class="s-stat-val">{{ src.quality }}%</div>
              <div class="s-stat-label">数据质量</div>
            </div>
            <div class="s-stat">
              <div class="s-stat-val">{{ src.frequency }}</div>
              <div class="s-stat-label">更新频率</div>
            </div>
          </div>
          <el-progress :percentage="src.quality" :color="src.quality > 90 ? '#67c23a' : src.quality > 70 ? '#e6a23c' : '#f56c6c'" :stroke-width="6" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 过滤流程 + 数据量趋势 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>三层过滤流程</span></template>
          <div class="filter-pipeline">
            <div class="filter-step" v-for="(f, i) in filterSteps" :key="i">
              <div class="filter-num">{{ i + 1 }}</div>
              <div class="filter-body">
                <div class="filter-name">{{ f.name }}</div>
                <div class="filter-desc">{{ f.desc }}</div>
                <div class="filter-ratio">通过率: {{ f.passRate }}%</div>
              </div>
              <el-icon v-if="i < filterSteps.length - 1" style="color:#555;font-size:20px;"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>数据量趋势</span></template>
          <div ref="volumeChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { ArrowRight } from '@element-plus/icons-vue'
import { api } from '../api'

const volumeChart = ref<HTMLElement | null>(null)
let volumeChartInstance: echarts.ECharts | null = null

const dataSources = ref<any[]>([])
const filterSteps = [
  { name: '规则粗过滤', desc: '格式校验、去空去重、范围检查', passRate: 72 },
  { name: '格式标准化', desc: '单位统一、编码转换、时间格式对齐', passRate: 91 },
  { name: '语义去重', desc: '向量相似度检测、跨源信息融合', passRate: 85 },
]

async function loadData() {
  try {
    const res = await api.get('/data/collect')
    const d = res.data
    const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#00d4ff']
    dataSources.value = (d.sources || []).map((s: any, i: number) => ({
      ...s,
      color: colors[i % colors.length],
      active: s.status === 'active',
      frequency: ['实时', '5min', '1h', '1d', '1h', '1d'][i] || '1d',
    }))
  } catch {
    dataSources.value = []
  }
}

function initVolumeChart() {
  if (!volumeChart.value) return
  volumeChartInstance = echarts.init(volumeChart.value, 'dark')
  const days = Array.from({ length: 7 }, (_, i) => `Day ${i + 1}`)
  volumeChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['东方财富', '巨潮资讯', '国家统计局'], textStyle: { color: '#999' } },
    xAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { type: 'value', name: '记录数', axisLine: { lineStyle: { color: '#444' } }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
    series: [
      { name: '东方财富', type: 'bar', stack: 'total', data: [320, 332, 301, 334, 390, 330, 320], itemStyle: { color: '#409eff' } },
      { name: '巨潮资讯', type: 'bar', stack: 'total', data: [120, 132, 101, 134, 90, 230, 210], itemStyle: { color: '#67c23a' } },
      { name: '国家统计局', type: 'bar', stack: 'total', data: [220, 182, 191, 234, 290, 330, 310], itemStyle: { color: '#e6a23c' } },
    ],
  })
}

onMounted(async () => {
  await loadData()
  await nextTick()
  initVolumeChart()
})

onUnmounted(() => { volumeChartInstance?.dispose() })
</script>

<style scoped>
.data-pipeline h2 { margin-bottom: 20px; color: #00d4ff; }
.source-card { background: #1a1a2e; border: 1px solid #2a2a4a; margin-bottom: 20px; }
.source-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.source-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; }
.source-name { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.source-stats { display: flex; gap: 12px; margin-bottom: 12px; }
.s-stat { flex: 1; text-align: center; padding: 8px; background: #16213e; border-radius: 4px; }
.s-stat-val { font-size: 18px; font-weight: 700; color: #00d4ff; }
.s-stat-label { font-size: 11px; color: #888; margin-top: 2px; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.filter-pipeline { display: flex; align-items: flex-start; gap: 8px; }
.filter-step { display: flex; align-items: flex-start; gap: 8px; flex: 1; }
.filter-num { width: 28px; height: 28px; border-radius: 50%; background: #00d4ff; color: #000; font-weight: 700; font-size: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.filter-body { flex: 1; }
.filter-name { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.filter-desc { font-size: 12px; color: #888; margin-bottom: 4px; }
.filter-ratio { font-size: 12px; color: #67c23a; }
</style>
