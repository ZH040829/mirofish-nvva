<template>
  <div class="report-view">
    <h2>蒸馏分析报告</h2>

    <!-- 选择仿真任务 -->
    <el-card class="panel" style="margin-bottom:20px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>选择仿真任务</span>
          <el-button size="small" @click="refreshTasks">刷新列表</el-button>
        </div>
      </template>
      <el-select v-model="selectedTaskId" placeholder="选择已完成的仿真任务" style="width:100%;" @change="loadReport">
        <el-option v-for="t in completedTasks" :key="t.id" :label="`${t.name} (${t.current_step}/${t.max_steps}步)`" :value="t.id" />
      </el-select>
      <el-button type="primary" @click="loadReport" :loading="loading" :disabled="!selectedTaskId" style="margin-top:12px;">
        生成蒸馏报告
      </el-button>
    </el-card>

    <!-- 报告内容 -->
    <div v-if="report" class="report-content">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card class="panel">
            <template #header><span>分析报告</span></template>
            <div class="markdown-body" v-html="renderedReport"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <!-- 核心指标 -->
          <el-card class="panel" style="margin-bottom:20px;">
            <template #header><span>核心指标</span></template>
            <div class="metrics-list">
              <div class="metric-row" v-for="(val, key) in report.metrics" :key="key">
                <span class="metric-key">{{ formatMetricKey(key as string) }}</span>
                <span class="metric-val">{{ typeof val === 'number' ? val.toFixed(2) : val }}</span>
              </div>
            </div>
          </el-card>

          <!-- 建议 -->
          <el-card class="panel" v-if="report.recommendations && report.recommendations.length > 0">
            <template #header><span>经营建议</span></template>
            <div class="recommendations">
              <div class="rec-item" v-for="(r, i) in report.recommendations" :key="i">
                <el-icon color="#67c23a"><Check /></el-icon>
                <span>{{ r }}</span>
              </div>
            </div>
          </el-card>

          <!-- 因果分析 -->
          <el-card class="panel" style="margin-top:20px;" v-if="report.causal_analysis && report.causal_analysis.length > 0">
            <template #header><span>因果分析</span></template>
            <div class="causal-list">
              <div class="causal-item" v-for="c in report.causal_analysis.slice(0, 10)" :key="c.step">
                <el-tag :type="causalType(c.type)" size="small">{{ c.type }}</el-tag>
                <span class="causal-name">{{ c.event }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-empty v-else-if="!loading" description="请选择已完成的仿真任务以生成蒸馏报告" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Check } from '@element-plus/icons-vue'
import * as api from '../api'
import { useSimulationStore } from '../stores'

const simStore = useSimulationStore()
const selectedTaskId = ref('')
const report = ref<any>(null)
const loading = ref(false)

const completedTasks = computed(() => simStore.tasks.filter(t => t.status === 'completed' || t.current_step > 0))

const renderedReport = computed(() => {
  if (!report.value?.report) return ''
  return report.value.report
    .replace(/### (.*)/g, '<h4>$1</h4>')
    .replace(/## (.*)/g, '<h3>$1</h3>')
    .replace(/# (.*)/g, '<h2>$1</h2>')
    .replace(/- (.*)/g, '<li>$1</li>')
    .replace(/\n/g, '<br/>')
})

function formatMetricKey(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function causalType(type: string) {
  const map: Record<string, string> = { market: 'warning', policy: '', natural: 'danger', tech: 'success' }
  return (map[type] || 'info') as any
}

async function refreshTasks() {
  await simStore.fetchTasks()
}

async function loadReport() {
  if (!selectedTaskId.value) return
  loading.value = true
  report.value = null
  try {
    const { data } = await api.getDistillAnalysis(selectedTaskId.value)
    report.value = data
  } catch (e: any) {
    console.error('蒸馏分析失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshTasks()
})
</script>

<style scoped>
.report-view h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
.markdown-body { color: #e0e0e0; line-height: 1.8; }
.markdown-body h2 { color: #00d4ff; margin: 16px 0 8px; }
.markdown-body h3 { color: #67c23a; margin: 12px 0 6px; }
.markdown-body h4 { color: #e6a23c; margin: 8px 0 4px; }
.markdown-body li { margin-left: 20px; }
.metrics-list { display: flex; flex-direction: column; gap: 10px; }
.metric-row { display: flex; justify-content: space-between; font-size: 13px; }
.metric-key { color: #888; }
.metric-val { color: #00d4ff; font-weight: 600; }
.recommendations { display: flex; flex-direction: column; gap: 10px; }
.rec-item { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #e0e0e0; }
.causal-list { display: flex; flex-direction: column; gap: 8px; }
.causal-item { display: flex; align-items: center; gap: 8px; }
.causal-name { font-size: 13px; color: #e0e0e0; }
</style>
