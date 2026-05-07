// MiroFish Demo 模式 - 后端不可用时使用模拟数据
// 让 GitHub Pages 上也能展示完整功能

export const demoData = {
  health: {
    status: 'healthy',
    version: '1.4.0',
    uptime: '2h 15m',
    components: {
      simulation: 'running',
      ai_agent: 'running',
      database: 'running',
      redis: 'running',
      data_pipeline: 'running',
    }
  },

  aiHealth: {
    status: 'healthy',
    version: '1.4.0',
    components: {
      llm: 'online',
      cache: 'active',
      redis: 'connected',
    },
    stats: {
      total_decisions: 128,
      llm_decisions: 96,
      rule_decisions: 32,
      cache_hits: 45,
    }
  },

  aiStats: {
    total_decisions: 128,
    llm_decisions: 96,
    rule_decisions: 32,
    cache_hits: 45,
    cache_stats: { size: 96, max_size: 500, hit_rate: 0.35 },
    redis_stats: { available: true, keys: 96 },
    llm_stats: { model: 'glm-4.7', available: true, calls: 96, avg_latency: 8.2 },
    negotiation_count: 12,
  },

  simulation: {
    task: {
      id: 'demo_sim_001',
      name: 'Demo 仿真演示',
      status: 'running',
      current_step: 8,
      max_steps: 20,
      created_at: new Date().toISOString(),
    },
    step: 8,
    max_steps: 20,
    status: 'running',
    world_state: {
      step: 8,
      market_price: { product_a: 108.5, product_b: 82.3, raw_material: 53.7 },
      supply: { product_a: 1150, product_b: 870, raw_material: 1850 },
      demand: { product_a: 1050, product_b: 920, raw_material: 1750 },
      policy: { tax_rate: 0.13, subsidy: 50000, interest_rate: 0.035 },
      events: [
        { name: '技术突破', type: 'tech', description: '生产效率提升10%', impact: { efficiency: 0.1 } },
        { name: '消费刺激政策', type: 'policy', description: '政府发放消费券', impact: { demand_boost: 0.05 } },
      ],
      sentiment: {
        overall: 62.3,
        greed: 48.5,
        fear: 28.2,
        optimism: 65.1,
        volatility: 35.8,
        confidence: 58.7,
        description: '市场情绪偏乐观，投资意愿较强',
      },
      agents: {
        ent_1: { id: 'ent_1', name: '核心企业A', role: 'enterprise', capital: 10500000, strategy: 'growth',
          evolution: { level: 3, experience: 180, specialization: 'growth', traits: { aggression: 0.55, adaptability: 0.6, risk_tolerance: 0.52 }, learned_patterns: ['step3:供不应求→扩张策略', 'step5:技术突破→加大研发'], adaptations: 2 }
        },
        comp_1: { id: 'comp_1', name: '竞争企业B', role: 'competitor', capital: 7800000, strategy: 'aggressive',
          evolution: { level: 2, experience: 120, specialization: 'aggressive', traits: { aggression: 0.7, adaptability: 0.45, risk_tolerance: 0.65 }, learned_patterns: ['step2:价格战→跟进降价', 'step6:需求上升→扩大产能'], adaptations: 1 }
        },
        consumer_1: { id: 'consumer_1', name: '消费者群体', role: 'consumer', capital: 5000000, strategy: 'balanced',
          evolution: { level: 2, experience: 95, specialization: 'balanced', traits: { aggression: 0.3, adaptability: 0.7, risk_tolerance: 0.4 }, learned_patterns: ['step4:价格稳定→增加消费'], adaptations: 1 }
        },
        gov_1: { id: 'gov_1', name: '政策制定者', role: 'policy', capital: 0, strategy: 'stability',
          evolution: { level: 1, experience: 60, specialization: 'stability', traits: { aggression: 0.2, adaptability: 0.5, risk_tolerance: 0.3 }, learned_patterns: [], adaptations: 0 }
        },
      }
    },
    agents: [
      { id: 'ent_1', name: '核心企业A', role: 'enterprise', capital: 10500000, strategy: 'growth', state: {}, decisions: [
        { action: 'expand', reasoning: '需求持续旺盛，扩大产能抢占市场', confidence: 0.85, source: 'llm', step: 7 },
        { action: 'innovate', reasoning: '技术突破窗口期，加大研发投入', confidence: 0.78, source: 'llm', step: 6 },
      ]},
      { id: 'comp_1', name: '竞争企业B', role: 'competitor', capital: 7800000, strategy: 'aggressive', state: {}, decisions: [
        { action: 'price_adjust', reasoning: '对手扩张期间降价抢客户', confidence: 0.72, source: 'llm', step: 7 },
        { action: 'expand', reasoning: '需求上升期扩大产能', confidence: 0.68, source: 'llm', step: 6 },
      ]},
      { id: 'consumer_1', name: '消费者群体', role: 'consumer', capital: 5000000, strategy: 'balanced', state: {}, decisions: [
        { action: 'increase_consumption', reasoning: '收入稳定增长，消费信心提升', confidence: 0.8, source: 'rule', step: 7 },
      ]},
      { id: 'gov_1', name: '政策制定者', role: 'policy', capital: 0, strategy: 'stability', state: {}, decisions: [
        { action: 'stimulate', reasoning: '经济增长平稳，微调刺激政策', confidence: 0.75, source: 'llm', step: 7 },
      ]},
    ]
  },

  taskList: {
    total: 3,
    tasks: [
      { id: 'demo_sim_001', name: 'Demo 仿真演示', status: 'running', current_step: 8, max_steps: 20 },
      { id: 'demo_sim_002', name: '科技行业竞争', status: 'completed', current_step: 50, max_steps: 50 },
      { id: 'demo_sim_003', name: '金融政策冲击', status: 'completed', current_step: 20, max_steps: 20 },
    ]
  },

  dataSources: {
    sources: [
      { name: '东方财富', status: 'active', records: 24531, quality: 95, last_update: '5分钟前' },
      { name: '巨潮资讯', status: 'active', records: 18203, quality: 92, last_update: '10分钟前' },
      { name: '国家统计局', status: 'active', records: 8456, quality: 98, last_update: '1小时前' },
      { name: '艾瑞咨询', status: 'active', records: 12340, quality: 88, last_update: '30分钟前' },
      { name: '央行数据', status: 'active', records: 6789, quality: 96, last_update: '2小时前' },
      { name: '百度指数', status: 'standby', records: 15255, quality: 78, last_update: '15分钟前' },
    ],
    sources_count: 6,
    active_count: 5,
    total_records: 85574,
    message: '数据采集完成，6个数据源中5个活跃',
  },

  sectors: {
    total: 5,
    sectors: [
      { id: 'tech', name: '科技行业', description: '高科技、高增长、高波动', base_price: 150, volatility: 0.08, growth_rate: 0.12 },
      { id: 'consumer', name: '消费品行业', description: '稳定需求、低波动', base_price: 80, volatility: 0.03, growth_rate: 0.05 },
      { id: 'finance', name: '金融行业', description: '政策敏感、中等波动', base_price: 120, volatility: 0.06, growth_rate: 0.08 },
      { id: 'energy', name: '能源行业', description: '资源依赖、高波动', base_price: 90, volatility: 0.10, growth_rate: 0.06 },
      { id: 'healthcare', name: '医疗行业', description: '刚需、政策驱动', base_price: 110, volatility: 0.04, growth_rate: 0.09 },
    ]
  },

  sentiment: {
    task_id: 'demo_sim_001',
    step: 8,
    sentiment: {
      overall: 62.3, greed: 48.5, fear: 28.2, optimism: 65.1, volatility: 35.8, confidence: 58.7,
      description: '市场情绪偏乐观，投资意愿较强'
    }
  },

  evolution: {
    task_id: 'demo_sim_001',
    total: 4,
    agents: [
      { id: 'ent_1', name: '核心企业A', role: 'enterprise', level: 3, experience: 180, specialization: 'growth', traits: { aggression: 0.55, adaptability: 0.6, risk_tolerance: 0.52 }, learned_patterns_count: 2, adaptations: 2 },
      { id: 'comp_1', name: '竞争企业B', role: 'competitor', level: 2, experience: 120, specialization: 'aggressive', traits: { aggression: 0.7, adaptability: 0.45, risk_tolerance: 0.65 }, learned_patterns_count: 2, adaptations: 1 },
      { id: 'consumer_1', name: '消费者群体', role: 'consumer', level: 2, experience: 95, specialization: 'balanced', traits: { aggression: 0.3, adaptability: 0.7, risk_tolerance: 0.4 }, learned_patterns_count: 1, adaptations: 1 },
      { id: 'gov_1', name: '政策制定者', role: 'policy', level: 1, experience: 60, specialization: 'stability', traits: { aggression: 0.2, adaptability: 0.5, risk_tolerance: 0.3 }, learned_patterns_count: 0, adaptations: 0 },
    ]
  },

  priceHistory: [
    { step: 1, product_a: 100, product_b: 80, raw_material: 50 },
    { step: 2, product_a: 102.3, product_b: 81.1, raw_material: 50.5 },
    { step: 3, product_a: 99.8, product_b: 79.5, raw_material: 51.2 },
    { step: 4, product_a: 103.5, product_b: 80.8, raw_material: 51.0 },
    { step: 5, product_a: 105.2, product_b: 81.5, raw_material: 52.3 },
    { step: 6, product_a: 104.1, product_b: 82.0, raw_material: 52.8 },
    { step: 7, product_a: 107.3, product_b: 81.8, raw_material: 53.2 },
    { step: 8, product_a: 108.5, product_b: 82.3, raw_material: 53.7 },
  ],

  report: {
    task_id: 'demo_sim_001',
    status: 'completed',
    report: '## 仿真分析报告\n\n### 市场概况\n本次仿真共推演8步，模拟了核心企业与竞争企业在市场中的博弈行为。\n\n### 关键发现\n1. **市场供需**：产品A长期供不应求，供需缺口约9%，推动价格持续上涨8.5%\n2. **技术突破**：Step5出现技术突破事件，生产效率提升10%，核心企业率先受益\n3. **政策干预**：消费刺激政策有效拉动需求增长5%\n4. **竞争格局**：核心企业A凭借技术优势扩大领先，竞争企业B被迫降价应对\n\n### 风险提示\n- 价格持续上涨可能触发调控政策\n- 竞争企业B的价格战策略可能引发恶性竞争\n- 原材料成本上升挤压利润空间',
    causal_analysis: [
      { step: 5, event: '技术突破', effect: '生产效率+10%，核心企业扩大产能', confidence: 0.85 },
      { step: 6, event: '企业扩张', effect: '供给增加，价格短期回调', confidence: 0.72 },
      { step: 7, event: '消费刺激', effect: '需求+5%，价格重新上涨', confidence: 0.78 },
    ],
    recommendations: [
      { priority: 'high', action: '加大研发投入', reason: '技术优势是当前核心竞争力的关键' },
      { priority: 'medium', action: '锁定原材料供应', reason: '原材料成本持续上升' },
      { priority: 'low', action: '关注政策动向', reason: '价格过热可能触发调控' },
    ],
    metrics: { total_steps: 8, price_change: 8.5, supply_demand_ratio: 1.1, event_count: 2 }
  }
}

// Demo 模式下模拟推演
let demoStep = 8
export function demoStepSimulation() {
  demoStep++
  const base = 100 + demoStep * 1.2 + (Math.random() - 0.3) * 3
  const simData = demoData.simulation
  simData.step = demoStep
  simData.world_state.step = demoStep
  simData.world_state.market_price.product_a = Math.round(base * 100) / 100
  simData.world_state.market_price.product_b = Math.round((base * 0.76) * 100) / 100
  simData.world_state.market_price.raw_material = Math.round((base * 0.49) * 100) / 100

  // Update sentiment
  const sent = simData.world_state.sentiment
  sent.overall = Math.min(100, Math.max(0, 50 + (Math.random() - 0.4) * 20))
  sent.greed = Math.min(100, Math.max(0, sent.overall - 10 + Math.random() * 15))
  sent.fear = Math.min(100, Math.max(0, 100 - sent.overall - 10 + Math.random() * 15))

  // Add to price history
  demoData.priceHistory.push({
    step: demoStep,
    product_a: simData.world_state.market_price.product_a,
    product_b: simData.world_state.market_price.product_b,
    raw_material: simData.world_state.market_price.raw_material,
  })

  if (demoStep >= 20) {
    simData.status = 'completed'
    simData.task.status = 'completed'
  }

  return simData
}

// 检测是否在 Demo 模式
export function isDemoMode(): boolean {
  const config = localStorage.getItem('mirofish_api_config')
  if (config) {
    try {
      const parsed = JSON.parse(config)
      if (parsed.demoMode) return true
    } catch {}
  }
  // 如果不在 localhost 且没有配置过，默认 demo 模式
  const hostname = window.location.hostname
  return hostname !== 'localhost' && hostname !== '127.0.0.1' && !localStorage.getItem('mirofish_api_config')
}
