-- MiroFish 女娲企业经营数字孪生系统 - 数据库初始化

-- 仿真任务表
CREATE TABLE IF NOT EXISTS simulation_tasks (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    current_step INTEGER NOT NULL DEFAULT 0,
    max_steps INTEGER NOT NULL DEFAULT 100,
    world_state JSONB,
    config JSONB,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 智能体表
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) REFERENCES simulation_tasks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    capital DOUBLE PRECISION DEFAULT 0,
    strategy VARCHAR(64),
    state JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 决策记录表
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    step INTEGER NOT NULL,
    action VARCHAR(64) NOT NULL,
    params JSONB,
    reasoning TEXT,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 世界状态历史表
CREATE TABLE IF NOT EXISTS world_state_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    step INTEGER NOT NULL,
    world_state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 事件表
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    step INTEGER NOT NULL,
    type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    impact JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 数据源表
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL,
    url VARCHAR(512),
    records INTEGER DEFAULT 0,
    quality DOUBLE PRECISION DEFAULT 0,
    status VARCHAR(32) DEFAULT 'active',
    last_sync TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 蒸馏报告表
CREATE TABLE IF NOT EXISTS distill_reports (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    report TEXT,
    causal_analysis JSONB,
    recommendations JSONB,
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_agents_task_id ON agents(task_id);
CREATE INDEX IF NOT EXISTS idx_decisions_agent_id ON decisions(agent_id);
CREATE INDEX IF NOT EXISTS idx_decisions_task_id ON decisions(task_id);
CREATE INDEX IF NOT EXISTS idx_world_state_history_task_id ON world_state_history(task_id);
CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_distill_reports_task_id ON distill_reports(task_id);

-- 初始数据源
INSERT INTO data_sources (name, type, url, records, quality, status) VALUES
    ('巨潮资讯-财报数据', '财报', 'https://www.cninfo.com.cn', 12345, 98, 'active'),
    ('东方财富-市场数据', '市场', 'https://data.eastmoney.com', 45678, 95, 'active'),
    ('国家统计局-宏观数据', '宏观', 'https://data.stats.gov.cn', 8901, 99, 'active'),
    ('百度指数-舆情数据', '舆情', 'https://index.baidu.com', 23456, 82, 'active'),
    ('艾瑞咨询-行业报告', '行业', 'https://www.iresearch.cn', 3210, 94, 'inactive'),
    ('央行-政策数据', '政策', 'https://www.pbc.gov.cn', 1567, 97, 'active');
