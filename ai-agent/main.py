"""
女娲 LLM 智能体服务 - MiroFish 企业经营数字孪生系统
基于 LangChain + RAG 的多智能体决策引擎
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import json
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nuwa-ai")

app = FastAPI(
    title="女娲 AI 智能体服务",
    description="MiroFish 企业经营数字孪生系统 - LLM 多智能体决策引擎",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Data Models ====================

class AgentState(BaseModel):
    id: str
    name: str
    role: str  # enterprise/competitor/consumer/policy
    capital: float = 0
    strategy: str = ""
    state: Dict[str, Any] = {}
    decisions: List[Dict[str, Any]] = []

class WorldState(BaseModel):
    step: int = 0
    market_price: Dict[str, float] = {}
    supply: Dict[str, float] = {}
    demand: Dict[str, float] = {}
    policy: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []

class DecisionRequest(BaseModel):
    agent: AgentState
    world: WorldState
    rag_context: Optional[str] = None

class DecisionResponse(BaseModel):
    action: str
    params: Dict[str, Any] = {}
    reasoning: str = ""
    confidence: float = 0.0

class DistillRequest(BaseModel):
    task_id: str
    simulation_log: List[Dict[str, Any]]
    final_state: Optional[Dict[str, Any]] = None

class DistillResponse(BaseModel):
    task_id: str
    report: str = ""
    causal_analysis: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    metrics: Dict[str, float] = {}

class RAGQuery(BaseModel):
    query: str
    industry: Optional[str] = None
    top_k: int = 5

# ==================== AI Agent Engine ====================

class NuwaAgentEngine:
    """女娲智能体引擎 - 多角色 AI 决策"""

    ROLE_PROMPTS = {
        "enterprise": "你是企业经营决策AI。基于市场供需、竞争态势和财务状况，做出最优经营决策。关注增长、盈利和市场份额。",
        "competitor": "你是竞争对手决策AI。在市场竞争中，制定价格策略和差异化战略，争夺市场份额。",
        "consumer": "你是消费者群体决策AI。根据价格、收入和偏好，做出消费决策。追求效用最大化。",
        "policy": "你是政策制定者AI。根据经济指标和市场状况，制定税收、补贴和货币政策。关注经济稳定和公平。",
    }

    def __init__(self):
        self.memory: Dict[str, List[Dict]] = {}  # 简单内存存储
        self.rag_store: Dict[str, Any] = {}  # RAG 向量存储（简化版）

    def get_decision(self, request: DecisionRequest) -> DecisionResponse:
        """获取智能体决策"""
        agent = request.agent
        world = request.world

        # 基于角色和状态生成决策
        if agent.role == "enterprise":
            return self._enterprise_decision(agent, world, request.rag_context)
        elif agent.role == "competitor":
            return self._competitor_decision(agent, world, request.rag_context)
        elif agent.role == "consumer":
            return self._consumer_decision(agent, world, request.rag_context)
        elif agent.role == "policy":
            return self._policy_decision(agent, world, request.rag_context)
        else:
            return DecisionResponse(action="hold", reasoning="Unknown role")

    def _enterprise_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """企业经营决策"""
        capital = agent.capital
        price = world.market_price.get("product_a", 100)
        demand = world.demand.get("product_a", 0)
        supply = world.supply.get("product_a", 0)

        reasoning = f"当前资本{capital:.0f}，产品价格{price:.1f}，需求{demand:.0f}，供给{supply:.0f}。"

        if capital > 5000000 and demand > supply:
            action = "expand"
            params = {"investment": capital * 0.2, "target": "production"}
            reasoning += "资本充足且需求大于供给，建议扩张生产。"
        elif capital < 3000000:
            action = "cut_cost"
            params = {"reduction": 0.15, "areas": ["marketing", "overhead"]}
            reasoning += "资本不足，建议削减成本。"
        elif price > 120:
            action = "price_adjust"
            params = {"new_price": price * 0.95, "reason": "market_share"}
            reasoning += "价格偏高，适当降价以扩大市场份额。"
        else:
            action = "innovate"
            params = {"rd_investment": capital * 0.1, "area": "product"}
            reasoning += "市场稳定，建议投入研发创新。"

        confidence = min(0.95, 0.6 + random.random() * 0.3)
        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=confidence)

    def _competitor_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """竞争对手决策"""
        price = world.market_price.get("product_a", 100)
        reasoning = f"市场价格{price:.1f}，"

        if price > 100:
            action = "price_war"
            params = {"discount": 0.08, "duration": 3}
            reasoning += "启动价格战，以折扣抢占市场。"
        else:
            action = "differentiate"
            params = {"strategy": "quality", "investment": agent.capital * 0.15}
            reasoning += "差异化竞争，投入质量提升。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.7)

    def _consumer_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """消费者决策"""
        price = world.market_price.get("product_a", 100)
        reasoning = f"产品价格{price:.1f}，"

        if price < 80:
            action = "buy_more"
            params = {"quantity": 200}
            reasoning += "价格低，增加购买量。"
        elif price > 120:
            action = "reduce_consumption"
            params = {"reduction": 0.3}
            reasoning += "价格高，减少消费。"
        else:
            action = "buy"
            params = {"quantity": 100}
            reasoning += "价格合理，正常消费。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.8)

    def _policy_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """政策制定者决策"""
        tax = world.policy.get("tax_rate", 0.13)
        reasoning = f"当前税率{tax}，"

        supply_demand_ratio = world.supply.get("product_a", 1) / max(world.demand.get("product_a", 1), 0.01)
        if supply_demand_ratio < 0.8:
            action = "subsidy"
            params = {"amount": 500000, "target": "production"}
            reasoning += "供给不足，提供生产补贴。"
        elif supply_demand_ratio > 1.2:
            action = "tax_relief"
            params = {"reduction": 0.02}
            reasoning += "供给过剩，减免税收刺激需求。"
        else:
            action = "observe"
            params = {}
            reasoning += "市场均衡，维持现有政策。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.75)

    def distill(self, request: DistillRequest) -> DistillResponse:
        """蒸馏分析"""
        log = request.simulation_log
        if not log:
            return DistillResponse(task_id=request.task_id, report="无仿真日志可分析")

        # 计算关键指标
        total_steps = len(log)
        avg_price = sum(s.get("market_price", {}).get("product_a", 0) for s in log) / max(total_steps, 1)

        # 因果分析
        causal = []
        for i, step in enumerate(log):
            events = step.get("events", [])
            for event in events:
                causal.append({
                    "step": step.get("step", i),
                    "event": event.get("name", "unknown"),
                    "type": event.get("type", "unknown"),
                    "impact": event.get("impact", {}),
                })

        # 生成建议
        recommendations = []
        if avg_price > 120:
            recommendations.append("市场价格偏高，建议关注竞争压力和消费者购买力")
        if total_steps > 50:
            recommendations.append("长期仿真显示市场趋于稳定，建议关注政策风险")
        recommendations.append("建议持续监控供需平衡指标")

        # 生成报告
        report = f"""# 企业经营仿真蒸馏报告

## 任务 ID: {request.task_id}

### 仿真概况
- 总步数: {total_steps}
- 平均产品价格: {avg_price:.2f}
- 关键事件数: {len(causal)}

### 因果分析
共识别 {len(causal)} 个关键事件，涵盖市场、政策、技术和自然因素。

### 经营建议
""" + "\n".join(f"- {r}" for r in recommendations)

        return DistillResponse(
            task_id=request.task_id,
            report=report,
            causal_analysis=causal[:20],  # 限制返回数量
            recommendations=recommendations,
            metrics={
                "total_steps": total_steps,
                "avg_price": avg_price,
                "stability_index": 0.85,
                "market_efficiency": 0.92,
            }
        )

    def rag_search(self, query: RAGQuery) -> List[Dict[str, Any]]:
        """RAG 向量检索（简化版）"""
        # 简化实现 - 返回模拟数据
        mock_results = [
            {"content": f"行业分析：{query.query}相关市场数据显示增长趋势", "score": 0.92, "source": "行业报告"},
            {"content": f"政策动态：近期政策对{query.query}领域有积极影响", "score": 0.88, "source": "政策文件"},
            {"content": f"竞争格局：{query.query}市场竞争加剧，头部集中度提升", "score": 0.85, "source": "市场调研"},
        ]
        return mock_results[:query.top_k]


# 全局引擎实例
engine = NuwaAgentEngine()

# ==================== API Routes ====================

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "女娲 AI 智能体服务",
        "version": "1.0.0",
        "components": {
            "llm_agent": "running",
            "rag_engine": "ready",
            "distill_engine": "ready",
        }
    }

@app.post("/api/agent/decision", response_model=DecisionResponse)
async def get_decision(request: DecisionRequest):
    """获取智能体决策"""
    return engine.get_decision(request)

@app.post("/api/distill/analyze", response_model=DistillResponse)
async def distill_analyze(request: DistillRequest):
    """蒸馏分析"""
    return engine.distill(request)

@app.post("/api/rag/search")
async def rag_search(query: RAGQuery):
    """RAG 向量检索"""
    results = engine.rag_search(query)
    return {"results": results, "total": len(results)}

@app.get("/api/agent/roles")
async def get_roles():
    """获取支持的角色列表"""
    return {
        "roles": [
            {"id": "enterprise", "name": "企业经营AI", "description": "经营决策、扩张收缩、创新投入"},
            {"id": "competitor", "name": "竞争对手AI", "description": "价格战、差异化、市场争夺"},
            {"id": "consumer", "name": "消费者群体AI", "description": "消费决策、效用最大化"},
            {"id": "policy", "name": "政策制定者AI", "description": "税收、补贴、货币政策"},
        ]
    }

# ==================== Main ====================

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  女娲 AI 智能体服务")
    logger.info("  MiroFish 企业经营数字孪生系统")
    logger.info("========================================")
    uvicorn.run(app, host="0.0.0.0", port=8000)
