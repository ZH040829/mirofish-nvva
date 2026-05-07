<template>
  <div class="data-page">
    <h2>数据管道</h2>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="panel">
          <template #header><span>数据源状态</span></template>
          <el-table :data="dataSources" size="small">
            <el-table-column prop="name" label="数据源" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="records" label="记录数" width="100" />
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
            <el-table-column prop="lastSync" label="最后同步" width="160" />
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
          <template #header><span>Qdrant 向量库</span></template>
          <div class="qdrant-stats">
            <div class="q-item"><span>集合数</span><strong>6</strong></div>
            <div class="q-item"><span>向量总数</span><strong>128,456</strong></div>
            <div class="q-item"><span>存储大小</span><strong>2.1 GB</strong></div>
            <div class="q-item"><span>索引状态</span><strong style="color:#67c23a">正常</strong></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const dataSources = ref([
  { name: '巨潮资讯-财报数据', type: '财报', records: '12,345', quality: 98, status: 'active', lastSync: '2026-05-06 16:00' },
  { name: '东方财富-市场数据', type: '市场', records: '45,678', quality: 95, status: 'active', lastSync: '2026-05-06 15:55' },
  { name: '国家统计局-宏观数据', type: '宏观', records: '8,901', quality: 99, status: 'active', lastSync: '2026-05-06 12:00' },
  { name: '百度指数-舆情数据', type: '舆情', records: '23,456', quality: 82, status: 'active', lastSync: '2026-05-06 16:05' },
  { name: '艾瑞咨询-行业报告', type: '行业', records: '3,210', quality: 94, status: 'inactive', lastSync: '2026-05-05 09:00' },
  { name: '央行-政策数据', type: '政策', records: '1,567', quality: 97, status: 'active', lastSync: '2026-05-06 08:00' },
])
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
.qdrant-stats { display: flex; flex-direction: column; gap: 12px; }
.q-item { display: flex; justify-content: space-between; font-size: 14px; }
.q-item span { color: #888; }
.q-item strong { color: #e0e0e0; }
</style>
