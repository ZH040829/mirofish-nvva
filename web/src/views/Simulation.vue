<template>
  <div class="simulation">
    <h2>仿真推演</h2>

    <!-- 参数配置 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="panel">
          <template #header><span>仿真参数</span></template>
          <el-form label-position="top" size="small">
            <el-form-item label="仿真场景">
              <el-select v-model="params.scenario" placeholder="选择场景">
                <el-option label="价格战推演" value="price_war" />
                <el-option label="新品上市" value="new_product" />
                <el-option label="供应链风险" value="supply_chain" />
                <el-option label="政策扰动" value="policy_shock" />
                <el-option label="全量博弈" value="full_game" />
              </el-select>
            </el-form-item>
            <el-form-item label="仿真轮次">
              <el-input-number v-model="params.rounds" :min="10" :max="500" :step="10" />
            </el-form-item>
            <el-form-item label="智能体数量">
              <el-input-number v-model="params.agentCount" :min="2" :max="20" />
            </el-form-item>
            <el-form-item label="数据来源比例(%)">
              <el-slider v-model="params.realDataRatio" :min="0" :max="100" :step="10" />
              <div class="slider-label">真实数据 {{ params.realDataRatio }}% | 模拟数据 {{ 100 - params.realDataRatio }}%</div>
            </el-form-item>
            <el-form-item label="RAG 增强">
              <el-switch v-model="params.ragEnabled" active-text="启用" inactive-text="关闭" />
            </el-form-item>
            <el-button type="primary" @click="startSimulation" :loading="running" style="width: 100%;">
              {{ running ? '仿真运行中...' : '启动仿真' }}
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 仿真实时视图 -->
      <el-col :span="16">
        <el-card class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>仿真沙盘</span>
              <div v-if="running">
                <el-tag type="warning" size="small">轮次 {{ currentRound }}/{{ params.rounds }}</el-tag>
              </div>
            </div>
          </template>
          <div v-if="!running && !result" class="empty-state">
            <el-icon :size="64" color="#2a2a4a"><VideoPlay /></el-icon>
            <p>配置参数后启动仿真</p>
          </div>
          <div v-else-if="running" class="sim-running">
            <div class="round-info">
              <h3>第 {{ currentRound }} 轮</h3>
              <p>{{ currentEvent }}</p>
            </div>
            <div class="agent-states">
              <div class="agent-state" v-for="a in simAgents" :key="a.name">
                <div class="agent-avatar" :style="{background: a.color}">{{ a.name[0] }}</div>
                <div class="agent-detail">
                  <strong>{{ a.name }}</strong>
                  <p>{{ a.decision }}</p>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="sim-result">
            <h3>仿真完成</h3>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="总轮次">{{ result.rounds }}</el-descriptions-item>
              <el-descriptions-item label="场景">{{ result.scenario }}</el-descriptions-item>
              <el-descriptions-item label="综合评分">{{ result.score }}</el-descriptions-item>
              <el-descriptions-item label="关键发现">{{ result.finding }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

const params = reactive({
  scenario: 'price_war',
  rounds: 50,
  agentCount: 4,
  realDataRatio: 80,
  ragEnabled: true,
})

const running = ref(false)
const currentRound = ref(0)
const currentEvent = ref('')
const result = ref<any>(null)

const simAgents = ref([
  { name: '企业决策', color: '#409eff', decision: '维持当前定价策略' },
  { name: '竞品模拟', color: '#67c23a', decision: '降价5%抢占市场份额' },
  { name: '消费者', color: '#e6a23c', decision: '价格敏感度上升' },
  { name: '政策', color: '#909399', decision: '无新政策出台' },
])

const startSimulation = () => {
  running.value = true
  currentRound.value = 0
  result.value = null

  const interval = setInterval(() => {
    currentRound.value++
    currentEvent.value = ['市场波动', '竞争加剧', '需求变化', '政策调整', '供给冲击'][Math.floor(Math.random() * 5)]

    simAgents.value.forEach(a => {
      const actions = ['调整策略', '观望等待', '主动出击', '防守应对', '合作博弈']
      a.decision = actions[Math.floor(Math.random() * actions.length)]
    })

    if (currentRound.value >= params.rounds) {
      clearInterval(interval)
      running.value = false
      result.value = {
        rounds: params.rounds,
        scenario: params.scenario,
        score: Math.floor(75 + Math.random() * 20),
        finding: '价格战导致行业利润率下降12%，建议转向差异化竞争策略',
      }
    }
  }, 200)
}
</script>

<style scoped>
.simulation h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
:deep(.el-form-item__label) { color: #ccc; }
.slider-label { font-size: 12px; color: #888; margin-top: 4px; }
.empty-state { text-align: center; padding: 80px 0; color: #555; }
.empty-state p { margin-top: 16px; }

.sim-running { padding: 10px; }
.round-info { text-align: center; margin-bottom: 20px; }
.round-info h3 { color: #00d4ff; }
.round-info p { color: #e6a23c; margin-top: 8px; }
.agent-states { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.agent-state {
  display: flex; gap: 10px; padding: 12px;
  background: #16213e; border-radius: 8px;
}
.agent-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: bold; color: #fff;
}
.agent-detail strong { color: #e0e0e0; }
.agent-detail p { color: #888; font-size: 12px; margin-top: 4px; }
.sim-result h3 { color: #67c23a; margin-bottom: 16px; }
</style>
