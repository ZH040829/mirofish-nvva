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
            <el-button type="primary" @click="createAndStart" :loading="creating" style="width: 100%;margin-bottom:8px;">
              {{ creating ? '创建中...' : '创建仿真' }}
            </el-button>
            <el-button type="success" @click="runStep" :loading="stepping" :disabled="!currentTaskId" style="width: 100%;margin-bottom:8px;">
              单步推演
            </el-button>
            <el-button type="warning" @click="runAll" :loading="running" :disabled="!currentTaskId" style="width: 100%;margin-bottom:8px;">
              {{ running ? '运行中...' : '全量运行' }}
            </el-button>
            <el-button @click="stopSim" :disabled="!currentTaskId" style="width: 100%;">
              停止仿真
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
              <div v-if="currentTaskId">
                <el-tag type="warning" size="small">轮次 {{ stepInfo }}/{{ params.rounds }}</el-tag>
                <el-tag :type="simStatus === 'running' ? 'warning' : simStatus === 'completed' ? 'success' : 'info'" size="small" style="margin-left:8px;">
                  {{ simStatusLabel }}
                </el-tag>
              </div>
            </div>
          </template>

          <!-- 无任务时 -->
          <div v-if="!currentTaskId" class="empty-state">
            <el-icon :size="64" color="#2a2a4a"><VideoPlay /></el-icon>
            <p>配置参数后创建仿真任务</p>
          </div>

          <!-- 有任务时 -->
          <div v-else class="sim-active">
            <!-- 世界状态 -->
            <div class="world-state" v-if="worldState">
              <el-row :gutter="12">
                <el-col :span="6" v-for="(val, key) in worldState.market_price" :key="key">
                  <div class="ws-item">
                    <div class="ws-label">{{ productLabel(key as string) }}</div>
                    <div class="ws-value">{{ (val as number).toFixed(1) }}</div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <!-- 事件 -->
            <div v-if="events.length > 0" class="events-section">
              <h4>近期事件</h4>
              <div class="event-list">
                <el-tag v-for="e in events.slice(-3)" :key="e.name" :type="eventTypeTag(e.type)" size="small" style="margin:2px;">
                  {{ e.name }}
                </el-tag>
              </div>
            </div>

            <!-- 智能体决策 -->
            <div class="agents-section">
              <h4>智能体状态</h4>
              <div class="agent-states">
                <div class="agent-state" v-for="a in taskAgents" :key="a.id">
                  <div class="agent-avatar" :style="{background: agentColor(a.role)}">{{ a.name[0] }}</div>
                  <div class="agent-detail">
                    <strong>{{ a.name }}</strong>
                    <p class="agent-capital">资本: {{ formatCapital(a.capital) }}</p>
                    <p class="agent-decision">{{ getDecisionText(a) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import * as api from '../api'

const params = reactive({
  scenario: 'price_war',
  rounds: 50,
  agentCount: 4,
  realDataRatio: 80,
  ragEnabled: true,
})

const creating = ref(false)
const stepping = ref(false)
const running = ref(false)
const currentTaskId = ref('')
const stepInfo = ref(0)
const simStatus = ref('pending')
const worldState = ref<any>(null)
const taskAgents = ref<any[]>([])
const events = ref<any[]>([])

const simStatusLabel = computed(() => {
  const map: Record<string, string> = { pending: '待启动', running: '运行中', completed: '已完成', stopped: '已停止' }
  return map[simStatus.value] || simStatus.value
})

function productLabel(key: string) {
  const map: Record<string, string> = { product_a: '产品A', product_b: '产品B', raw_material: '原材料' }
  return map[key] || key
}

function agentColor(role: string) {
  const map: Record<string, string> = { enterprise: '#409eff', competitor: '#67c23a', consumer: '#e6a23c', policy: '#909399' }
  return map[role] || '#909399'
}

function eventTypeTag(type: string) {
  const map: Record<string, string> = { market: 'warning', policy: '', natural: 'danger', tech: 'success' }
  return (map[type] || 'info') as any
}

function formatCapital(c: number) {
  if (c >= 1000000) return (c / 1000000).toFixed(1) + 'M'
  if (c >= 1000) return (c / 1000).toFixed(1) + 'K'
  return c.toFixed(0)
}

function getDecisionText(a: any) {
  if (!a.decisions || a.decisions.length === 0) return '等待决策...'
  const last = a.decisions[a.decisions.length - 1]
  return `${last.action}: ${last.reasoning || ''}`.substring(0, 40)
}

async function createAndStart() {
  creating.value = true
  try {
    const { data } = await api.createSimulation({
      name: `${params.scenario}_仿真`,
      max_steps: params.rounds,
      config: { ai_enabled: true, data_source: 'auto', real_data_ratio: params.realDataRatio / 100 },
    })
    currentTaskId.value = data.task.id
    stepInfo.value = 0
    simStatus.value = 'pending'
    taskAgents.value = data.task.agents || []
    worldState.value = data.task.world_state
    events.value = []
  } catch (e: any) {
    console.error('创建仿真失败:', e)
  } finally {
    creating.value = false
  }
}

async function runStep() {
  if (!currentTaskId.value) return
  stepping.value = true
  try {
    const { data } = await api.stepSimulation(currentTaskId.value)
    stepInfo.value = data.step
    simStatus.value = data.status
    worldState.value = data.world_state
    events.value = data.world_state?.events || []
    // 更新智能体
    if (data.world_state?.agents) {
      const agentMap = data.world_state.agents
      taskAgents.value = Object.values(agentMap)
    }
  } catch (e: any) {
    console.error('推演失败:', e)
  } finally {
    stepping.value = false
  }
}

async function runAll() {
  if (!currentTaskId.value) return
  running.value = true
  try {
    await api.startSimulation(currentTaskId.value)
    simStatus.value = 'running'
    // 轮询状态
    const poll = setInterval(async () => {
      try {
        const { data } = await api.getSimulationStatus(currentTaskId.value)
        stepInfo.value = data.current_step
        simStatus.value = data.status
        worldState.value = data.world_state
        events.value = data.world_state?.events || []
        if (data.world_state?.agents) {
          taskAgents.value = Object.values(data.world_state.agents)
        }
        if (data.status === 'completed' || data.status === 'stopped' || data.status === 'failed') {
          clearInterval(poll)
          running.value = false
        }
      } catch {
        clearInterval(poll)
        running.value = false
      }
    }, 500)
  } catch (e: any) {
    console.error('运行失败:', e)
    running.value = false
  }
}

async function stopSim() {
  if (!currentTaskId.value) return
  try {
    await api.stopSimulation(currentTaskId.value)
    simStatus.value = 'stopped'
  } catch (e: any) {
    console.error('停止失败:', e)
  }
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

.sim-active { padding: 10px; }
.world-state { margin-bottom: 20px; }
.ws-item { background: #16213e; padding: 12px; border-radius: 8px; text-align: center; }
.ws-label { font-size: 12px; color: #888; }
.ws-value { font-size: 20px; font-weight: 700; color: #00d4ff; margin-top: 4px; }

.events-section { margin-bottom: 20px; }
.events-section h4 { color: #e0e0e0; margin-bottom: 8px; }
.event-list { display: flex; flex-wrap: wrap; gap: 4px; }

.agents-section h4 { color: #e0e0e0; margin-bottom: 12px; }
.agent-states { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.agent-state {
  display: flex; gap: 10px; padding: 12px;
  background: #16213e; border-radius: 8px;
}
.agent-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: bold; color: #fff; flex-shrink: 0;
}
.agent-detail { overflow: hidden; }
.agent-detail strong { color: #e0e0e0; font-size: 14px; }
.agent-capital { color: #67c23a; font-size: 12px; margin-top: 2px; }
.agent-decision { color: #888; font-size: 12px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
