// MiroFish Demo 模式 - 后端不可用时使用模拟数据
// 让 GitHub Pages 上也能展示完整功能
// v1.5.0: 新增交易、财务、排行榜、通知、风险预警、Dashboard、市场预测数据

export const demoData = {
  health: {
    status: 'healthy',
    version: '1.5.0',
    uptime: '2h 15m',
    components: {
      simulation: 'running',
      ai_agent: 'running',
      database: 'running',
      redis: 'running',
      data_pipeline: 'running',
      market_predict: 'ready',
      risk_analyzer: 'ready',
      trade_advisor: 'ready',
    }
  },

  aiHealth: {
    status: 'healthy',
    version: '1.5.0',
    components: {
      llm: 'online',
      cache: 'active',
      redis: 'connected',
      market_predict: 'ready',
      risk_analyzer: 'ready',
      trade_advisor: 'ready',
      sse_stream: 'ready',
    },
    stats: {
      total_decisions: 256,
      llm_decisions: 198,
      rule_decisions: 58,
      cache_hits: 89,
    }
  },

  aiStats: {
    total_decisions: 256,
    llm_decisions: 198,
    rule_decisions: 58,
    cache_hits: 89,
    cache_stats: { size: 192, max_size: 500, hit_rate: 0.42 },
    redis_stats: { available: true, keys: 192 },
    llm_stats: { model: 'glm-4.7', available: true, calls: 198, avg_latency: 7.5 },
    negotiation_count: 24,
    memory_stats: { local_entries: 45, redis_available: true },
  },

  simulation: {
    task: {
      id: 'demo_sim_001',
      name: 'Demo 仿真演示',
      status: 'running',
      current_step: 12,
      max_steps: 20,
      created_at: new Date().toISOString(),
    },
    step: 12,
    max_steps: 20,
    status: 'running',
    world_state: {
      step: 12,
      market_price: { product_a: 112.5, product_b: 86.3, raw_material: 56.7 },
      supply: { product_a: 1200, product_b: 920, raw_material: 1950 },
      demand: { product_a: 1100, product_b: 980, raw_material: 1850 },
      policy: { tax_rate: 0.13, subsidy: 80000, interest_rate: 0.035 },
      events: [
        { name: '技术突破', type: 'tech', description: '生产效率提升10%', impact: { efficiency: 0.1 } },
        { name: '消费刺激政策', type: 'policy', description: '政府发放消费券', impact: { demand_boost: 0.05 } },
      ],
      sentiment: {
        overall: 65.3,
        greed: 52.5,
        fear: 25.2,
        optimism: 68.1,
        volatility: 32.8,
        confidence: 62.7,
        description: '市场情绪偏乐观，投资意愿较强',
      },
      agents: {
        ent_1: { id: 'ent_1', name: '核心企业A', role: 'enterprise', capital: 12500000, strategy: 'growth',
          evolution: { level: 5, experience: 380, specialization: 'growth', traits: { aggression: 0.55, adaptability: 0.7, risk_tolerance: 0.52 }, learned_patterns: ['step3:供不应求→扩张策略', 'step5:技术突破→加大研发', 'step9:竞争加剧→差异化'], adaptations: 3 }
        },
        comp_1: { id: 'comp_1', name: '竞争企业B', role: 'competitor', capital: 8200000, strategy: 'aggressive',
          evolution: { level: 3, experience: 220, specialization: 'aggressive', traits: { aggression: 0.75, adaptability: 0.5, risk_tolerance: 0.65 }, learned_patterns: ['step2:价格战→跟进降价', 'step6:需求上升→扩大产能', 'step10:利润下滑→成本控制'], adaptations: 2 }
        },
        consumer_1: { id: 'consumer_1', name: '消费者群体', role: 'consumer', capital: 5800000, strategy: 'balanced',
          evolution: { level: 3, experience: 175, specialization: 'balanced', traits: { aggression: 0.3, adaptability: 0.75, risk_tolerance: 0.4 }, learned_patterns: ['step4:价格稳定→增加消费', 'step8:补贴发放→积极消费'], adaptations: 2 }
        },
        gov_1: { id: 'gov_1', name: '政策制定者', role: 'policy', capital: 0, strategy: 'stability',
          evolution: { level: 2, experience: 110, specialization: 'stability', traits: { aggression: 0.2, adaptability: 0.6, risk_tolerance: 0.3 }, learned_patterns: ['step7:通胀压力→适度收紧'], adaptations: 1 }
        },
      }
    },
    agents: [
      { id: 'ent_1', name: '核心企业A', role: 'enterprise', capital: 12500000, strategy: 'growth', state: { revenue: 4500000, cost: 3200000, profit_margin: 0.29 }, decisions: [
        { action: 'expand', reasoning: '需求持续旺盛，扩大产能抢占市场', confidence: 0.85, source: 'llm', step: 11 },
        { action: 'innovate', reasoning: '技术突破窗口期，加大研发投入', confidence: 0.78, source: 'llm', step: 10 },
      ]},
      { id: 'comp_1', name: '竞争企业B', role: 'competitor', capital: 8200000, strategy: 'aggressive', state: { revenue: 3100000, cost: 2600000, profit_margin: 0.16 }, decisions: [
        { action: 'price_war', reasoning: '对手扩张期间降价抢客户', confidence: 0.72, source: 'llm', step: 11 },
        { action: 'cut_cost', reasoning: '利润下滑，优化运营', confidence: 0.68, source: 'llm', step: 10 },
      ]},
      { id: 'consumer_1', name: '消费者群体', role: 'consumer', capital: 5800000, strategy: 'balanced', state: { satisfaction: 0.72 }, decisions: [
        { action: 'buy_more', reasoning: '收入稳定增长，消费信心提升', confidence: 0.8, source: 'llm', step: 11 },
      ]},
      { id: 'gov_1', name: '政策制定者', role: 'policy', capital: 0, strategy: 'stability', state: {}, decisions: [
        { action: 'stimulate', reasoning: '经济增长平稳，微调刺激政策', confidence: 0.75, source: 'llm', step: 11 },
      ]},
    ]
  },

  taskList: {
    total: 3,
    tasks: [
      { id: 'demo_sim_001', name: 'Demo 仿真演示', status: 'running', current_step: 12, max_steps: 20 },
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
    step: 12,
    sentiment: {
      overall: 65.3, greed: 52.5, fear: 25.2, optimism: 68.1, volatility: 32.8, confidence: 62.7,
      description: '市场情绪偏乐观，投资意愿较强'
    }
  },

  evolution: {
    task_id: 'demo_sim_001',
    total: 4,
    agents: [
      { id: 'ent_1', name: '核心企业A', role: 'enterprise', level: 5, experience: 380, specialization: 'growth', traits: { aggression: 0.55, adaptability: 0.7, risk_tolerance: 0.52 }, learned_patterns_count: 3, adaptations: 3 },
      { id: 'comp_1', name: '竞争企业B', role: 'competitor', level: 3, experience: 220, specialization: 'aggressive', traits: { aggression: 0.75, adaptability: 0.5, risk_tolerance: 0.65 }, learned_patterns_count: 3, adaptations: 2 },
      { id: 'consumer_1', name: '消费者群体', role: 'consumer', level: 3, experience: 175, specialization: 'balanced', traits: { aggression: 0.3, adaptability: 0.75, risk_tolerance: 0.4 }, learned_patterns_count: 2, adaptations: 2 },
      { id: 'gov_1', name: '政策制定者', role: 'policy', level: 2, experience: 110, specialization: 'stability', traits: { aggression: 0.2, adaptability: 0.6, risk_tolerance: 0.3 }, learned_patterns_count: 1, adaptations: 1 },
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
    { step: 9, product_a: 106.8, product_b: 83.1, raw_material: 54.2 },
    { step: 10, product_a: 109.2, product_b: 84.5, raw_material: 55.0 },
    { step: 11, product_a: 110.8, product_b: 85.6, raw_material: 55.8 },
    { step: 12, product_a: 112.5, product_b: 86.3, raw_material: 56.7 },
  ],

  report: {
    task_id: 'demo_sim_001',
    status: 'completed',
    report: '## 仿真分析报告\n\n### 市场概况\n本次仿真共推演12步，模拟了核心企业与竞争企业在市场中的博弈行为。\n\n### 关键发现\n1. **市场供需**：产品A长期供不应求，供需缺口约8%，推动价格持续上涨12.5%\n2. **技术突破**：Step5出现技术突破事件，生产效率提升10%，核心企业率先受益\n3. **政策干预**：消费刺激政策有效拉动需求增长5%\n4. **竞争格局**：核心企业A凭借技术优势扩大领先，竞争企业B被迫降价应对\n\n### 风险提示\n- 价格持续上涨可能触发调控政策\n- 竞争企业B的价格战策略可能引发恶性竞争\n- 原材料成本上升挤压利润空间',
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
    metrics: { total_steps: 12, price_change: 12.5, supply_demand_ratio: 1.1, event_count: 2 }
  },

  // === v1.5.0: 交易数据 ===
  trades: [
    { id: 'trade_001', from_agent: 'ent_1', from_name: '核心企业A', to_agent: 'consumer_1', to_name: '消费者群体', item: 'product_a', quantity: 200, price: 110.5, total: 22100, step: 11, status: 'completed' },
    { id: 'trade_002', from_agent: 'comp_1', from_name: '竞争企业B', to_agent: 'consumer_1', to_name: '消费者群体', item: 'product_b', quantity: 150, price: 84.2, total: 12630, step: 11, status: 'completed' },
    { id: 'trade_003', from_agent: 'ent_1', from_name: '核心企业A', to_agent: 'comp_1', to_name: '竞争企业B', item: 'raw_material', quantity: 300, price: 56.0, total: 16800, step: 10, status: 'completed' },
    { id: 'trade_004', from_agent: 'ent_1', from_name: '核心企业A', to_agent: 'consumer_1', to_name: '消费者群体', item: 'product_a', quantity: 180, price: 112.3, total: 20214, step: 10, status: 'completed' },
    { id: 'trade_005', from_agent: 'comp_1', from_name: '竞争企业B', to_agent: 'consumer_1', to_name: '消费者群体', item: 'product_b', quantity: 120, price: 82.8, total: 9936, step: 9, status: 'completed' },
  ],

  // === v1.5.0: 财务数据 ===
  finance: [
    { agent_id: 'ent_1', agent_name: '核心企业A', revenue: 4500000, cost: 3200000, profit: 1300000, net_worth: 12500000, profit_margin: 0.289, step: 12 },
    { agent_id: 'comp_1', agent_name: '竞争企业B', revenue: 3100000, cost: 2600000, profit: 500000, net_worth: 8200000, profit_margin: 0.161, step: 12 },
    { agent_id: 'consumer_1', agent_name: '消费者群体', revenue: 0, cost: 2800000, profit: -2800000, net_worth: 5800000, profit_margin: 0, step: 12 },
  ],

  // === v1.5.0: 排行榜 ===
  leaderboard: [
    { rank: 1, agent_id: 'ent_1', agent_name: '核心企业A', role: 'enterprise', score: 920, net_worth: 12500000, profit_margin: 0.289, level: 5 },
    { rank: 2, agent_id: 'comp_1', agent_name: '竞争企业B', role: 'competitor', score: 680, net_worth: 8200000, profit_margin: 0.161, level: 3 },
    { rank: 3, agent_id: 'consumer_1', agent_name: '消费者群体', role: 'consumer', score: 450, net_worth: 5800000, profit_margin: 0, level: 3 },
    { rank: 4, agent_id: 'gov_1', agent_name: '政策制定者', role: 'policy', score: 350, net_worth: 0, profit_margin: 0, level: 2 },
  ],

  // === v1.5.0: 通知 ===
  notifications: [
    { id: 'notif_001', type: 'success', title: '技术突破', message: '生产效率提升10%，核心企业率先受益', read: false, step: 12, time: '2分钟前' },
    { id: 'notif_002', type: 'warning', title: '竞争加剧', message: '竞争企业B发起价格战，市场压力增大', read: false, step: 11, time: '5分钟前' },
    { id: 'notif_003', type: 'info', title: '政策调整', message: '消费刺激政策生效，需求增长5%', read: true, step: 10, time: '10分钟前' },
    { id: 'notif_004', type: 'danger', title: '原材料涨价', message: '原材料价格突破55，成本压力上升', read: false, step: 10, time: '12分钟前' },
    { id: 'notif_005', type: 'info', title: '仿真进度', message: '仿真已推进到第12步，剩余8步', read: true, step: 12, time: '刚刚' },
  ],

  // === v1.5.0: 风险预警 ===
  riskAlerts: [
    { id: 'risk_001', type: 'market', level: 'medium', title: '市场波动', description: '产品A价格波动率35.8%，接近警戒线', mitigation: '建议设置价格对冲策略', step: 12, active: true },
    { id: 'risk_002', type: 'credit', level: 'low', title: '信用风险', description: '竞争企业B利润率持续下降，偿债能力减弱', mitigation: '关注其资本状况变化', step: 11, active: true },
    { id: 'risk_003', type: 'operational', level: 'high', title: '原材料供应', description: '原材料价格持续上涨，供应紧张', mitigation: '建议签订长期供应合同锁定价格', step: 12, active: true },
    { id: 'risk_004', type: 'liquidity', level: 'low', title: '流动性', description: '消费者群体资金消耗较快', mitigation: '政策面可适度补贴', step: 10, active: false },
  ],

  // === v1.5.0: Dashboard 汇总 ===
  dashboard: {
    task_id: 'demo_sim_001',
    total_steps: 12,
    max_steps: 20,
    active_agents: 4,
    avg_price: 108.4,
    price_trend: 'up',
    volatility: 0.328,
    total_trades: 5,
    total_trade_value: 81680,
    risk_level: 'medium',
    unread_notifications: 3,
    top_agent: { name: '核心企业A', score: 920 },
    sector: 'default',
    summary: '仿真运行中，市场偏乐观但波动加剧。核心企业A以920分领跑排行榜，原材料涨价风险需关注。',
  },

  // === v1.5.0: 市场预测 ===
  marketPrediction: {
    price_forecast: [114.2, 115.8, 117.1, 116.5, 118.3],
    trend: 'up',
    confidence: 0.72,
    key_factors: ['供需缺口持续', '技术红利释放', '原材料成本上涨'],
    risk_level: 'medium',
  },

  // === v1.5.0: 风险分析 ===
  riskAnalysis: {
    risk_level: 'medium',
    risk_categories: [
      { type: 'market', severity: 0.6, description: '价格波动接近警戒线', mitigation: '设置对冲策略' },
      { type: 'operational', severity: 0.7, description: '原材料供应紧张', mitigation: '锁定长期合约' },
      { type: 'credit', severity: 0.3, description: '竞争企业利润率下滑', mitigation: '监控偿债能力' },
    ],
    overall_score: 0.55,
    alerts: ['原材料价格持续上涨', '竞争企业B利润率仅16%'],
    recommendations: ['签订长期原材料采购合同', '关注竞争企业资金链', '适时调整定价策略'],
  },
}

// Demo 模式下模拟推演
let demoStep = 12
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

  // v1.5.0: 动态添加交易和通知
  if (Math.random() > 0.4) {
    const items = ['product_a', 'product_b', 'raw_material']
    const item = items[Math.floor(Math.random() * items.length)]
    const qty = 50 + Math.floor(Math.random() * 200)
    const price = simData.world_state.market_price[item as keyof typeof simData.world_state.market_price] || 80
    demoData.trades.unshift({
      id: `trade_demo_${Date.now()}`,
      from_agent: 'ent_1', from_name: '核心企业A',
      to_agent: 'consumer_1', to_name: '消费者群体',
      item, quantity: qty, price: Math.round(price * 100) / 100,
      total: Math.round(qty * price), step: demoStep, status: 'completed'
    })
    if (demoData.trades.length > 20) demoData.trades.pop()
  }

  // 随机添加通知
  const notifTypes = ['info', 'warning', 'success'] as const
  const notifMessages = [
    { type: 'info' as const, title: '仿真推进', message: `仿真已推进到第${demoStep}步` },
    { type: 'warning' as const, title: '价格波动', message: `产品A价格波动${(Math.random()*10+2).toFixed(1)}%` },
    { type: 'success' as const, title: '交易完成', message: '新的一笔交易已完成' },
  ]
  if (Math.random() > 0.5) {
    const n = notifMessages[Math.floor(Math.random() * notifMessages.length)]
    demoData.notifications.unshift({
      id: `notif_demo_${Date.now()}`, ...n, read: false, step: demoStep, time: '刚刚'
    })
    if (demoData.notifications.length > 15) demoData.notifications.pop()
  }

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
