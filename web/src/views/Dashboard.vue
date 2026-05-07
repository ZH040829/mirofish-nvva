<template>
  <div class="dashboard">
    <h2>仿真仪表盘</h2>

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

    <!-- 仿真状态 + 智能体活动 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="panel">
          <template #header>
            <span>经营趋势</span>
          </template>
          <div ref="trendChart" style="height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="panel">
          <template #header>
            <span>智能体活动</span>
          </template>
          <div class="agent-list">
            <div class="agent-item" v-for="agent in agents" :key="agent.id">
              <el-avatar :size="36" :style="{ background: agent.color }">
                {{ agent.name.charAt(0) }}
              </el-avatar>
              <div class="agent-info">
                <div class="agent-name">{{ agent.name }}</div>
                <div class="agent-status">{{ agent.action }}</div>
              </div>
              <el-tag :type="agent.status === 'active' ? 'success' : 'info'" size="small">
                {{ agent.status === 'active' ? '活跃' : '待命' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近仿真 + 系统健康 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>最近仿真任务</span></template>
          <el-table :data="recentSimulations" style="width: 100%" size="small" :header-cell-style="{background:'#1a1a2e',color:'#e0e0e0'}">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="scenario" label="场景" />
            <el-table-column prop="rounds" label="轮次" width="80" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'running' ? 'warning' : 'info'" size="small">
                  {{ row.status === 'completed' ? '已完成' : row.status === 'running' ? '运行中' : '待启动' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="评分" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="panel">
          <template #header><span>系统健康</span></template>
          <div class="health-grid">
            <div class="health-item" v-for="h in healthStatus" :key="h.name">
              <div class="health-name">{{ h.name }}</div>
              <el-progress :percentage="h.health" :color="h.health > 80 ? '#67c23a' : h.health > 50 ? '#e6a23c' : '#f56c6c'" :stroke-width="8" />
              <div class="health-detail">{{ h.detail }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const coreMetrics = ref([
  { label: '仿真轮次', value: '128', trend: 12, color: '#00d4ff' },
  { label: '活跃智能体', value: '4', trend: 0, color: '#67c23a' },
  { label: '数据质量', value: '96.5%', trend: 3, color: '#e6a23c' },
  { label: '决策准确率', value: '89.2%', trend: 5, color: '#f56c6c' },
])

const agents = ref([
  { id: 1, name: '企业决策AI', action: '分析市场竞争态势', status: 'active', color: '#409eff' },
  { id: 2, name: '竞品模拟AI', action: '调整定价策略', status: 'active', color: '#67c23a' },
  { id: 3, name: '消费者AI', action: '评估购买意愿', status: 'active', color: '#e6a23c' },
  { id: 4, name: '政策环境AI', action: '等待政策更新', status: 'idle', color: '#909399' },
])

const recentSimulations = ref([
  { id: 'S001', scenario: 'Q2价格战推演', rounds: 32, status: 'completed', score: 92 },
  { id: 'S002', scenario: '新品上市策略', rounds: 24, status: 'completed', score: 87 },
  { id: 'S003', scenario: '供应链风险模拟', rounds: 16, status: 'running', score: '-' },
  { id: 'S004', scenario: '政策扰动影响', rounds: 0, status: 'pending', score: '-' },
])

const healthStatus = ref([
  { name: '仿真引擎', health: 95, detail: 'CPU 23%, MEM 1.2GB' },
  { name: 'AI 智能体', health: 88, detail: '4/4 在线, 延迟 120ms' },
  { name: '数据管道', health: 92, detail: '3 源接入, 质量 96.5%' },
  { name: '向量数据库', health: 78, detail: 'Qdrant 2.1GB, 128K 向量' },
])

const trendChart = ref(null)
onMounted(() => {
  // ECharts would be initialized here in production
})
</script>

<style scoped>
.dashboard h2 { margin-bottom: 20px; color: #00d4ff; }
.metrics-row { margin-bottom: 20px; }
.metric-card {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  text-align: center;
  padding: 10px;
}
.metric-value { font-size: 32px; font-weight: 700; }
.metric-label { font-size: 13px; color: #888; margin-top: 4px; }
.metric-trend { font-size: 12px; margin-top: 4px; }
.metric-trend.up { color: #67c23a; }
.metric-trend.down { color: #f56c6c; }

.panel {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
}
:deep(.el-card__header) {
  background: #16213e;
  border-bottom: 1px solid #2a2a4a;
  color: #e0e0e0;
  padding: 12px 20px;
}

.agent-list { display: flex; flex-direction: column; gap: 12px; }
.agent-item {
  display: flex; align-items: center; gap: 12px;
  padding: 8px; border-radius: 8px; background: #16213e;
}
.agent-info { flex: 1; }
.agent-name { font-size: 14px; font-weight: 500; }
.agent-status { font-size: 12px; color: #888; margin-top: 2px; }

.health-grid { display: flex; flex-direction: column; gap: 16px; }
.health-item { padding: 4px 0; }
.health-name { font-size: 14px; margin-bottom: 6px; }
.health-detail { font-size: 12px; color: #888; margin-top: 4px; }

:deep(.el-table) { background: transparent; }
:deep(.el-table tr) { background: #16213e; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background: #1a1a2e; }
</style>
