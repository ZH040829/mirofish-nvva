<template>
  <div class="agents-page">
    <h2>智能体管理</h2>
    <el-row :gutter="20">
      <el-col :span="8" v-for="agent in agents" :key="agent.id">
        <el-card class="agent-card panel" shadow="hover">
          <div class="agent-header">
            <el-avatar :size="48" :style="{ background: agent.color }">{{ agent.name[0] }}</el-avatar>
            <div>
              <h3>{{ agent.name }}</h3>
              <el-tag :type="agent.active ? 'success' : 'info'" size="small">
                {{ agent.active ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>
          <el-divider />
          <div class="agent-props">
            <div class="prop"><span class="label">角色类型</span><span>{{ agent.role }}</span></div>
            <div class="prop"><span class="label">LLM模型</span><span>{{ agent.model }}</span></div>
            <div class="prop"><span class="label">RAG知识库</span><span>{{ agent.ragCollection }}</span></div>
            <div class="prop"><span class="label">决策次数</span><span>{{ agent.decisions }}</span></div>
            <div class="prop"><span class="label">平均响应</span><span>{{ agent.avgLatency }}ms</span></div>
          </div>
          <el-button type="primary" size="small" style="margin-top:12px;width:100%;" @click="configureAgent(agent)">
            配置
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const agents = ref([
  { id: 1, name: '企业决策AI', role: '企业经营者', model: 'glm-4', ragCollection: 'enterprise_kb', decisions: 512, avgLatency: 156, active: true, color: '#409eff' },
  { id: 2, name: '竞品模拟AI', role: '竞争对手', model: 'deepseek-v3', ragCollection: 'competitor_kb', decisions: 487, avgLatency: 203, active: true, color: '#67c23a' },
  { id: 3, name: '消费者AI', role: '市场消费者', model: 'qwen-plus', ragCollection: 'consumer_kb', decisions: 1024, avgLatency: 89, active: true, color: '#e6a23c' },
  { id: 4, name: '政策环境AI', role: '监管者', model: 'glm-4', ragCollection: 'policy_kb', decisions: 64, avgLatency: 312, active: false, color: '#909399' },
])

const configureAgent = (agent: any) => {
  console.log('Configure:', agent.name)
}
</script>

<style scoped>
.agents-page h2 { margin-bottom: 20px; color: #00d4ff; }
.panel { background: #1a1a2e; border: 1px solid #2a2a4a; }
:deep(.el-card__header) { background: #16213e; border-bottom: 1px solid #2a2a4a; color: #e0e0e0; }
.agent-header { display: flex; align-items: center; gap: 12px; }
.agent-header h3 { color: #e0e0e0; margin: 0; font-size: 16px; }
.agent-props { display: flex; flex-direction: column; gap: 8px; }
.prop { display: flex; justify-content: space-between; font-size: 13px; }
.prop .label { color: #888; }
.prop span:last-child { color: #e0e0e0; }
:deep(.el-divider) { border-color: #2a2a4a; }
</style>
