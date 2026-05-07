<template>
  <div class="data-ingestion-view">
    <h2>数据接入</h2>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>数据源管理</span>
              <el-button size="small" type="primary" @click="refreshSources">刷新</el-button>
            </div>
          </template>
          <el-table :data="sources" size="small">
            <el-table-column prop="name" label="数据源" />
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.status_bool" active-text="开" inactive-text="关" size="small" @change="toggleSource(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="quality" label="质量" width="80">
              <template #default="{ row }">
                <span :style="{color: row.quality > 90 ? '#67c23a' : '#e6a23c'}">{{ row.quality }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>采集任务</span></template>
          <div class="ingestion-actions">
            <el-button type="primary" @click="triggerCollect" :loading="collecting" style="width:100%;">
              触发全量采集
            </el-button>
            <el-button @click="triggerCollect" style="width:100%;margin-top:10px;">
              触发增量采集
            </el-button>
          </div>
          <div v-if="collectResult" class="collect-result">
            <el-descriptions :column="1" border size="small" style="margin-top:16px;">
              <el-descriptions-item label="消息">{{ collectResult.message }}</el-descriptions-item>
              <el-descriptions-item label="数据源数">{{ collectResult.sources_count }}</el-descriptions-item>
              <el-descriptions-item label="活跃数">{{ collectResult.active_count }}</el-descriptions-item>
              <el-descriptions-item label="总记录">{{ collectResult.total_records?.toLocaleString() }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '../api'

const sources = ref<any[]>([])
const collecting = ref(false)
const collectResult = ref<any>(null)

async function refreshSources() {
  try {
    const { data } = await api.getDataSources()
    sources.value = (data.sources || []).map((s: any) => ({
      ...s,
      status_bool: s.status === 'active',
    }))
  } catch { sources.value = [] }
}

function toggleSource(row: any) {
  row.status = row.status_bool ? 'active' : 'inactive'
}

async function triggerCollect() {
  collecting.value = true
  try {
    const { data } = await api.collectData()
    collectResult.value = data
    await refreshSources()
  } catch {
    collectResult.value = { message: '采集失败' }
  } finally {
    collecting.value = false
  }
}

onMounted(() => {
  refreshSources()
})
</script>

<style scoped>
.data-ingestion-view h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
:deep(.el-table) { background: transparent; }
:deep(.el-table tr) { background: #16213e; }
.ingestion-actions { padding: 10px 0; }
</style>
