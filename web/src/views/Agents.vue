<template>
  <div class="agents-page">
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12"><h2>智能体管理</h2></el-col>
      <el-col :span="12" style="text-align: right">
        <el-button type="primary" @click="fetchAgents" :loading="loading">刷新</el-button>
        <el-button @click="negotiate" :loading="negoLoading" :disabled="agents.length < 2">协商分析</el-button>
      </el-col>
    </el-row>

    <!-- 智能体关系图谱 (D3.js) -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>智能体关系图谱</span>
          <el-tag size="small" type="info">{{ agents.length }} 个智能体</el-tag>
        </div>
      </template>
      <div ref="graphContainer" style="width:100%;height:400px;border:1px solid var(--el-border-color-light);border-radius:8px;overflow:hidden"></div>
    </el-card>

    <!-- 智能体卡片 -->
    <el-row :gutter="16">
      <el-col :span="6" v-for="agent in agents" :key="agent.id">
        <el-card shadow="hover" :body-style="{padding:'16px'}">
          <div style="display:flex;align-items:center;margin-bottom:12px">
            <el-avatar :size="40" :style="{backgroundColor: getRoleColor(agent.role)}">
              {{ getRoleIcon(agent.role) }}
            </el-avatar>
            <div style="margin-left:10px">
              <div style="font-weight:bold;font-size:14px">{{ agent.name }}</div>
              <el-tag size="small" :type="getRoleTagType(agent.role)">{{ getRoleLabel(agent.role) }}</el-tag>
            </div>
          </div>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="资本">{{ formatCapital(agent.capital) }}</el-descriptions-item>
            <el-descriptions-item label="策略">{{ agent.strategy }}</el-descriptions-item>
            <el-descriptions-item label="决策数">{{ agent.decisions?.length || 0 }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="agent.decisions?.length" style="margin-top:8px">
            <div style="font-size:12px;color:var(--el-text-color-secondary);margin-bottom:4px">最近决策:</div>
            <el-tag v-for="(d,i) in agent.decisions.slice(-3)" :key="i" size="small" style="margin:2px"
              :type="d.source==='llm'?'success':'info'">
              {{ d.action }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 协商结果 -->
    <el-card v-if="negotiationResult" shadow="hover" style="margin-top:20px">
      <template #header><span>协商分析结果</span></template>
      <el-alert v-if="negotiationResult.conflicts?.length" :title="'发现 ' + negotiationResult.conflicts.length + ' 个冲突'" type="warning" :closable="false" style="margin-bottom:12px" />
      <el-row :gutter="20">
        <el-col :span="12">
          <h4>冲突点</h4>
          <ul><li v-for="(c,i) in negotiationResult.conflicts" :key="i">{{ c }}</li></ul>
          <h4>解决方案</h4>
          <ul><li v-for="(r,i) in negotiationResult.resolutions" :key="i">{{ r }}</li></ul>
        </el-col>
        <el-col :span="12">
          <h4>推荐方案</h4>
          <p>{{ negotiationResult.recommendation }}</p>
          <h4>分析理由</h4>
          <p style="color:var(--el-text-color-secondary)">{{ negotiationResult.reasoning }}</p>
        </el-col>
      </el-row>
    </el-card>

    <!-- AI 统计 -->
    <el-card shadow="hover" style="margin-top:20px">
      <template #header><span>AI 决策统计</span></template>
      <el-row :gutter="20">
        <el-col :span="6"><el-statistic title="总决策" :value="aiStats.total_decisions || 0" /></el-col>
        <el-col :span="6"><el-statistic title="LLM决策" :value="aiStats.llm_decisions || 0" /></el-col>
        <el-col :span="6"><el-statistic title="规则决策" :value="aiStats.rule_decisions || 0" /></el-col>
        <el-col :span="6"><el-statistic title="缓存命中" :value="aiStats.cache_hits || 0" /></el-col>
      </el-row>
    </el-card>

    <!-- 跨仿真记忆 -->
    <el-card shadow="hover" style="margin-top:20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>跨仿真经验库</span>
          <el-button size="small" @click="fetchMemories">查看经验</el-button>
        </div>
      </template>
      <el-table :data="memories" size="small" v-if="memories.length" stripe>
        <el-table-column prop="task_id" label="任务" width="140" />
        <el-table-column prop="lesson" label="经验" />
        <el-table-column prop="tag" label="标签" width="80" />
      </el-table>
      <el-empty v-else description="暂无经验记录，完成仿真后将自动积累" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { mirofishApi } from '../api'
import * as d3 from 'd3'

const loading = ref(false)
const negoLoading = ref(false)
const agents = ref<any[]>([])
const negotiationResult = ref<any>(null)
const aiStats = ref<any>({})
const memories = ref<any[]>([])
const graphContainer = ref<HTMLElement>()

let timer: any = null
let simulation: any = null

const roleColors: Record<string, string> = {
  enterprise: '#409EFF', competitor: '#F56C6C', consumer: '#E6A23C', policy: '#67C23A'
}
const roleIcons: Record<string, string> = {
  enterprise: '企', competitor: '竞', consumer: '消', policy: '政'
}
const roleLabels: Record<string, string> = {
  enterprise: '企业', competitor: '竞品', consumer: '消费者', policy: '政策'
}

function getRoleColor(role: string) { return roleColors[role] || '#909399' }
function getRoleIcon(role: string) { return roleIcons[role] || '?' }
function getRoleLabel(role: string) { return roleLabels[role] || role }
function getRoleTagType(role: string) {
  const map: Record<string, string> = { enterprise: '', competitor: 'danger', consumer: 'warning', policy: 'success' }
  return map[role] || 'info'
}
function formatCapital(v: number) {
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

async function fetchAgents() {
  loading.value = true
  try {
    const tasks = await mirofishApi.getSimulationList()
    if (tasks.tasks?.length) {
      const latest = tasks.tasks[tasks.tasks.length - 1]
      const data = await mirofishApi.getAgents(latest.id)
      agents.value = data.agents || []
      await nextTick()
      renderGraph()
    }
  } catch (e) { console.error(e) }
  loading.value = false
}

async function negotiate() {
  if (agents.value.length < 2) return
  negoLoading.value = true
  try {
    const proposals = agents.value.map(a => ({
      agent_id: a.id, agent_name: a.name, role: a.role,
      action: a.decisions?.at(-1)?.action || 'hold',
      reasoning: a.decisions?.at(-1)?.reasoning || '待决策',
      confidence: a.decisions?.at(-1)?.confidence || 0.5
    }))
    negotiationResult.value = await mirofishApi.negotiate(proposals)
  } catch (e) { console.error(e) }
  negoLoading.value = false
}

async function fetchAiStats() {
  try { aiStats.value = await mirofishApi.getAIStats() } catch {}
}

async function fetchMemories() {
  try {
    const data = await mirofishApi.recallMemory('', '', 10)
    memories.value = data.results || []
  } catch {}
}

function renderGraph() {
  if (!graphContainer.value || !agents.value.length) return
  const container = graphContainer.value
  const width = container.clientWidth
  const height = 400

  d3.select(container).selectAll('*').remove()

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height)

  // 节点数据
  const nodes = agents.value.map(a => ({
    id: a.id, name: a.name, role: a.role, capital: a.capital,
    color: getRoleColor(a.role), radius: Math.max(20, Math.min(50, a.capital / 300000))
  }))

  // 关系边 - 不同角色之间的关系
  const edges = [
    { source: 'ent_1', target: 'comp_1', relation: '竞争', color: '#F56C6C' },
    { source: 'ent_1', target: 'cons_1', relation: '供应', color: '#409EFF' },
    { source: 'comp_1', target: 'cons_1', relation: '供应', color: '#409EFF' },
    { source: 'pol_1', target: 'ent_1', relation: '调控', color: '#67C23A' },
    { source: 'pol_1', target: 'comp_1', relation: '调控', color: '#67C23A' },
    { source: 'pol_1', target: 'cons_1', relation: '保护', color: '#E6A23C' },
  ].filter(e => nodes.find(n => n.id === e.source) && nodes.find(n => n.id === e.target))

  simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(edges).id((d: any) => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius((d: any) => d.radius + 10))

  const link = svg.append('g').selectAll('line').data(edges).enter().append('line')
    .attr('stroke', (d: any) => d.color).attr('stroke-width', 2).attr('stroke-opacity', 0.6)

  const linkLabel = svg.append('g').selectAll('text').data(edges).enter().append('text')
    .attr('font-size', 10).attr('fill', '#999').attr('text-anchor', 'middle')
    .text((d: any) => d.relation)

  const node = svg.append('g').selectAll('g').data(nodes).enter().append('g')
    .call(d3.drag<SVGGElement, any>()
      .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
      .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
    )

  node.append('circle')
    .attr('r', (d: any) => d.radius).attr('fill', (d: any) => d.color).attr('fill-opacity', 0.7)
    .attr('stroke', (d: any) => d.color).attr('stroke-width', 3)

  node.append('text')
    .attr('dy', -5).attr('text-anchor', 'middle').attr('font-size', 12).attr('font-weight', 'bold')
    .attr('fill', '#fff').text((d: any) => roleIcons[d.role] || '?')

  node.append('text')
    .attr('dy', (d: any) => d.radius + 15).attr('text-anchor', 'middle')
    .attr('font-size', 11).attr('fill', 'var(--el-text-color-primary)')
    .text((d: any) => d.name)

  simulation.on('tick', () => {
    link.attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y)
    linkLabel.attr('x', (d: any) => (d.source.x + d.target.x) / 2)
            .attr('y', (d: any) => (d.source.y + d.target.y) / 2)
    node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
  })
}

onMounted(() => {
  fetchAgents()
  fetchAiStats()
  fetchMemories()
  timer = setInterval(() => { fetchAgents(); fetchAiStats() }, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (simulation) simulation.stop()
})

watch(agents, () => { nextTick(renderGraph) })
</script>

<style scoped>
.agents-page { padding: 20px }
h2 { margin: 0 }
h4 { color: var(--el-text-color-secondary); margin: 8px 0 4px }
ul { padding-left: 18px; margin: 4px 0 }
li { margin: 2px 0; font-size: 13px }
p { font-size: 13px; margin: 4px 0 }
</style>
