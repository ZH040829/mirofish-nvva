<template>
  <div class="report-page">
    <h2>蒸馏分析报告</h2>

    <el-row :gutter="20">
      <!-- 报告生成 -->
      <el-col :span="6">
        <el-card class="panel">
          <template #header><span>生成报告</span></template>
          <el-form label-width="80px" size="default">
            <el-form-item label="仿真任务">
              <el-select v-model="selectedTaskId" placeholder="选择任务" style="width:100%;" @change="onTaskSelect">
                <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateReport" :loading="generating" :disabled="!selectedTaskId">
                蒸馏分析
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="panel" style="margin-top: 20px;" v-if="report">
          <template #header><span>关键指标</span></template>
          <div class="metrics">
            <div class="metric-item" v-for="(v, k) in report.metrics" :key="k">
              <div class="metric-label">{{ metricLabel(k) }}</div>
              <div class="metric-value" :style="{ color: metricColor(k, v) }">{{ formatMetric(k, v) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 报告内容 -->
      <el-col :span="18">
        <el-card class="panel" v-if="report">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>分析报告</span>
              <el-tag size="small" type="success">任务: {{ report.task_id?.substring(0, 12) }}...</el-tag>
            </div>
          </template>
          <div class="report-content" v-html="renderedReport"></div>
        </el-card>

        <el-card class="panel" v-if="report" style="margin-top: 20px;">
          <template #header><span>因果分析链路</span></template>
          <el-timeline>
            <el-timeline-item
              v-for="(c, i) in report.causal_analysis"
              :key="i"
              :timestamp="`Step ${c.step}`"
              :type="causalType(c.type)"
              placement="top"
            >
              <div class="causal-item">
                <strong>{{ c.event }}</strong>
                <el-tag size="small" style="margin-left:8px;">{{ c.type }}</el-tag>
              </div>
              <div class="causal-impact" v-if="c.impact && Object.keys(c.impact).length > 0">
                <span v-for="(v, k) in c.impact" :key="k" class="impact-tag">
                  {{ k }}: {{ typeof v === 'number' ? v.toFixed(3) : v }}
                </span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <el-card class="panel" v-if="report && report.recommendations.length > 0" style="margin-top: 20px;">
          <template #header><span>经营建议</span></template>
          <div class="recommendations">
            <div class="rec-item" v-for="(r, i) in report.recommendations" :key="i">
              <div class="rec-num">{{ i + 1 }}</div>
              <div class="rec-text">{{ r }}</div>
            </div>
          </div>
        </el-card>

        <el-card class="panel" v-if="!report">
          <div class="empty-hint">
            <div style="font-size:48px;margin-bottom:16px;">📊</div>
            <div>选择仿真任务并点击"蒸馏分析"生成报告</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '../stores'
import { api } from '../api'

const simStore = useSimulationStore()

const selectedTaskId = ref('')
const generating = ref(false)
const report = ref<any>(null)

const tasks = computed(() => simStore.tasks)

function onTaskSelect() { report.value = null }

async function generateReport() {
  if (!selectedTaskId.value) return
  generating.value = true
  try {
    // 获取仿真历史
    await simStore.fetchHistory(selectedTaskId.value)
    const history = simStore.worldHistory
    if (history.length === 0) {
      report.value = { task_id: selectedTaskId.value, report: '无仿真数据', causal_analysis: [], recommendations: [], metrics: {} }
      return
    }
    // 调用蒸馏 API (AI 服务端口 8000)
    const res = await api.ai.post('/distill/analyze', {
      task_id: selectedTaskId.value,
      simulation_log: history,
    })
    report.value = res.data
  } catch (e: any) {
    report.value = { task_id: selectedTaskId.value, report: '生成失败: ' + (e.message || '未知错误'), causal_analysis: [], recommendations: [], metrics: {} }
  } finally {
    generating.value = false
  }
}

const renderedReport = computed(() => {
  if (!report.value?.report) return ''
  return report.value.report
    .replace(/# /g, '<h3 style="color:#00d4ff;margin:16px 0 8px;">')
    .replace(/\n/g, '<br>')
    .replace(/## /g, '<h4 style="color:#67c23a;margin:12px 0 6px;">')
    .replace(/### /g, '<h5 style="color:#e6a23c;margin:10px 0 4px;">')
    .replace(/- /g, '<div style="padding-left:16px;margin:2px 0;color:#ccc;">• ')
})

function causalType(t: string) { const m: Record<string, string> = { policy: 'warning', natural: 'danger', tech: 'success', market: 'primary' }; return m[t] || 'info' }
function metricLabel(k: string) { const m: Record<string, string> = { total_steps: '总步数', avg_price: '平均价格', stability_index: '稳定性', market_efficiency: '市场效率', price_volatility: '波动率', risk_level: '风险等级' }; return m[k] || k }
function metricColor(k: string, v: any) { if (k === 'risk_level') return v === 'high' ? '#f56c6c' : v === 'medium' ? '#e6a23c' : '#67c23a'; if (typeof v === 'number' && k.includes('volatility')) return v > 0.3 ? '#f56c6c' : '#67c23a'; return '#00d4ff' }
function formatMetric(k: string, v: any) { if (typeof v === 'number') return v.toFixed(k.includes('index') || k.includes('efficiency') ? 3 : 2); return String(v) }
</script>

<style scoped>
.report-page h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; padding: 12px 20px; }
.metrics { display: flex; flex-direction: column; gap: 12px; }
.metric-item { padding: 8px 12px; background: #16213e; border-radius: 6px; }
.metric-label { font-size: 12px; color: #888; }
.metric-value { font-size: 20px; font-weight: 700; }
.report-content { line-height: 1.8; color: #ccc; }
.causal-item { display: flex; align-items: center; }
.causal-impact { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px; }
.impact-tag { font-size: 12px; padding: 2px 8px; background: #16213e; border-radius: 4px; color: #aaa; }
.recommendations { display: flex; flex-direction: column; gap: 10px; }
.rec-item { display: flex; gap: 12px; padding: 10px; background: #16213e; border-radius: 6px; }
.rec-num { width: 24px; height: 24px; border-radius: 50%; background: #00d4ff; color: #000; font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rec-text { color: #ccc; font-size: 14px; line-height: 1.6; }
.empty-hint { text-align: center; padding: 40px; color: #555; }
</style>
