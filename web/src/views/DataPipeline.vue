<template>
  <div class="data-page">
    <h2>数据管道</h2>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>数据源状态</span>
              <el-button size="small" type="primary" @click="collectNow" :loading="collecting">手动采集</el-button>
            </div>
          </template>
          <el-table :data="dataSources" size="small">
            <el-table-column prop="name" label="数据源" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="records" label="记录数" width="100">
              <template #default="{ row }">{{ row.records.toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="quality" label="质量" width="80">
              <template #default="{ row }">
                <el-tag :type="row.quality > 90 ? 'success' : row.quality > 70 ? 'warning' : 'danger'" size="small">
                  {{ row.quality }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <span :class="row.status === 'active' ? 'status-active' : 'status-inactive'">
                  {{ row.status === 'active' ? '采集中' : '暂停' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="last_sync" label="最后同步" width="160" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>三层过滤统计</span></template>
          <div class="filter-stats">
            <div class="filter-item">
              <div class="filter-name">规则粗过滤</div>
              <el-progress :percentage="85" :stroke-width="10" color="#409eff" />
              <div class="filter-detail">过滤 15% 脏数据</div>
            </div>
            <div class="filter-item">
              <div class="filter-name">格式清洗</div>
              <el-progress :percentage="92" :stroke-width="10" color="#67c23a" />
              <div class="filter-detail">标准化 8% 异常格式</div>
            </div>
            <div class="filter-item">
              <div class="filter-name">语义去重</div>
              <el-progress :percentage="96" :stroke-width="10" color="#e6a23c" />
              <div class="filter-detail">去重 4% 相似内容</div>
            </div>
          </div>
        </el-card>

        <el-card class="panel" style="margin-top:20px;">
          <template #header><span>采集统计</span></template>
          <div class="collect-stats">
            <div class="c-item"><span>活跃数据源</span><strong>{{ activeCount }}</strong></div>
            <div class="c-item"><span>总记录数</span><strong>{{ totalRecords.toLocaleString() }}</strong></div>
            <div class="c-item"><span>平均质量</span><strong>{{ avgQuality }}%</strong></div>
          </div>
        </el-card>

        <el-card class="panel" style="margin-top:20px;">
          <template #header><span>RAG 向量检索</span></template>
          <el-input v-model="ragQuery" placeholder="输入搜索关键词" size="small" style="margin-bottom:10px;">
            <template #append>
              <el-button @click="searchRAG" :loading="ragSearching">搜索</el-button>
            </template>
          </el-input>
          <div v-if="ragResults.length > 0" class="rag-results">
            <div class="rag-item" v-for="r in ragResults" :key="r.content">
              <div class="rag-score">相关度: {{ (r.score * 100).toFixed(0) }}%</div>
              <div class="rag-content">{{ r.content }}</div>
              <div class="rag-source">来源: {{ r.source }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as api from '../api'
import { useSystemStore } from '../stores'

const sysStore = useSystemStore()
const dataSources = ref<any[]>([])
const collecting = ref(false)
const ragQuery = ref('')
const ragSearching = ref(false)
const ragResults = ref<any[]>([])

const activeCount = computed(() => dataSources.value.filter(s => s.status === 'active').length)
const totalRecords = computed(() => dataSources.value.reduce((sum, s) => sum + s.records, 0))
const avgQuality = computed(() => {
  if (dataSources.value.length === 0) return 0
  return (dataSources.value.reduce((sum, s) => sum + s.quality, 0) / dataSources.value.length).toFixed(1)
})

async function collectNow() {
  collecting.value = true
  try {
    await api.collectData()
    await fetchSources()
  } finally {
    collecting.value = false
  }
}

async function searchRAG() {
  if (!ragQuery.value) return
  ragSearching.value = true
  try {
    const { data } = await api.getRAGSearch(ragQuery.value)
    ragResults.value = data.results || []
  } catch {
    ragResults.value = []
  } finally {
    ragSearching.value = false
  }
}

async function fetchSources() {
  try {
    const { data } = await api.getDataSources()
    dataSources.value = data.sources || []
  } catch {
    dataSources.value = []
  }
}

onMounted(() => {
  fetchSources()
})
</script>

<style scoped>
.data-page h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
:deep(.el-table) { background: transparent; }
:deep(.el-table tr) { background: #16213e; }
.status-active { color: #67c23a; }
.status-inactive { color: #909399; }
.filter-stats { display: flex; flex-direction: column; gap: 20px; }
.filter-name { font-size: 14px; margin-bottom: 6px; }
.filter-detail { font-size: 12px; color: #888; margin-top: 4px; }
.collect-stats { display: flex; flex-direction: column; gap: 12px; }
.c-item { display: flex; justify-content: space-between; font-size: 14px; }
.c-item span { color: #888; }
.c-item strong { color: #e0e0e0; }
.rag-results { display: flex; flex-direction: column; gap: 10px; }
.rag-item { background: #16213e; padding: 10px; border-radius: 6px; }
.rag-score { font-size: 12px; color: #00d4ff; }
.rag-content { font-size: 13px; color: #e0e0e0; margin-top: 4px; }
.rag-source { font-size: 11px; color: #888; margin-top: 4px; }
</style>
