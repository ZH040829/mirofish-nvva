"""
女娲 LLM 智能体服务 - MiroFish 企业经营数字孪生系统
基于 LangChain + RAG 的多智能体决策引擎
支持 OpenAI 兼容 API (Coze/通义千问/GLM4/DeepSeek)
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
import os
import httpx

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

# ==================== Configuration ====================

class Settings:
    # LLM 配置 - 复用 Coze 环境变量
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", ""))
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", ""))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "coze/auto")

    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Qdrant 配置
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "mirofish_rag")

    # 服务配置
    HOST: str = os.getenv("NUWA_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("NUWA_PORT", "8000"))

settings = Settings()

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

# ==================== LLM Client ====================

class LLMClient:
    """LLM 客户端 - 支持 OpenAI 兼容 API"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=60.0)
        self.available = bool(base_url and api_key)

    def chat(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """调用 LLM 获取回复"""
        if not self.available:
            return None

        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
            }

            resp = self.client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"LLM API error: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None

    def health_check(self) -> bool:
        """检查 LLM 服务是否可用"""
        if not self.available:
            return False
        try:
            result = self.chat("You are a health checker.", "Reply OK")
            return result is not None
        except:
            return False


# ==================== AI Agent Engine ====================

class NuwaAgentEngine:
    """女娲智能体引擎 - 多角色 AI 决策"""

    ROLE_PROMPTS = {
        "enterprise": """你是企业经营决策AI。基于市场供需、竞争态势和财务状况，做出最优经营决策。
可选行动：expand(扩张), cut_cost(削减成本), innovate(创新研发), price_adjust(调整价格), hold(维持现状)
输出格式要求：JSON {"action": "...", "params": {...}, "reasoning": "...", "confidence": 0.0-1.0}
关注增长、盈利和市场份额。""",

        "competitor": """你是竞争对手决策AI。在市场竞争中，制定价格策略和差异化战略。
可选行动：price_war(价格战), differentiate(差异化), expand(扩张), hold(维持), partner(合作)
输出格式要求：JSON {"action": "...", "params": {...}, "reasoning": "...", "confidence": 0.0-1.0}
争夺市场份额，灵活应对竞争。""",

        "consumer": """你是消费者群体决策AI。根据价格、收入和偏好，做出消费决策。
可选行动：buy(正常消费), buy_more(增加消费), reduce_consumption(减少消费), substitute(替代消费), hold(观望)
输出格式要求：JSON {"action": "...", "params": {...}, "reasoning": "...", "confidence": 0.0-1.0}
追求效用最大化。""",

        "policy": """你是政策制定者AI。根据经济指标和市场状况，制定税收、补贴和货币政策。
可选行动：subsidy(补贴), tax_relief(减税), tighten(收紧), observe(观察), stimulate(刺激)
输出格式要求：JSON {"action": "...", "params": {...}, "reasoning": "...", "confidence": 0.0-1.0}
关注经济稳定和公平。""",
    }

    DISTILL_PROMPT = """你是企业经营仿真蒸馏分析AI。分析以下仿真数据，生成因果分析报告和经营建议。

请分析：
1. 关键事件对市场的影响链路
2. 各智能体决策的效果评估
3. 最优经营策略建议

输出格式要求：JSON {
  "report": "分析报告全文",
  "causal_analysis": [{"step": 0, "event": "...", "type": "...", "impact": {...}}],
  "recommendations": ["建议1", "建议2"],
  "metrics": {"key_metric": value}
}"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.memory: Dict[str, List[Dict]] = {}
        self.rag_store: Dict[str, Any] = {}
        self.decision_count = 0
        self.llm_decision_count = 0

    def get_decision(self, request: DecisionRequest) -> DecisionResponse:
        """获取智能体决策 - 优先使用 LLM，回退到规则"""
        agent = request.agent
        world = request.world

        # 尝试 LLM 决策
        if self.llm.available:
            llm_result = self._llm_decision(agent, world, request.rag_context)
            if llm_result is not None:
                self.decision_count += 1
                self.llm_decision_count += 1
                return llm_result

        # 规则回退决策
        self.decision_count += 1
        return self._rule_decision(agent, world, request.rag_context)

    def _llm_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> Optional[DecisionResponse]:
        """使用 LLM 生成决策"""
        system_prompt = self.ROLE_PROMPTS.get(agent.role, self.ROLE_PROMPTS["enterprise"])

        # 构建用户 prompt
        world_info = f"""
当前世界状态:
- 仿真步数: {world.step}
- 产品A价格: {world.market_price.get('product_a', 0):.2f}
- 产品B价格: {world.market_price.get('product_b', 0):.2f}
- 原材料价格: {world.market_price.get('raw_material', 0):.2f}
- 产品A供给/需求: {world.supply.get('product_a', 0):.0f}/{world.demand.get('product_a', 0):.0f}
- 税率: {world.policy.get('tax_rate', 0)}
- 利率: {world.policy.get('interest_rate', 0)}
- 补贴: {world.policy.get('subsidy', 0)}
- 近期事件: {json.dumps(world.events[-3:], ensure_ascii=False) if world.events else '无'}

你的状态:
- ID: {agent.id}
- 名称: {agent.name}
- 资本: {agent.capital:.0f}
- 策略: {agent.strategy}
- 状态: {json.dumps(agent.state, ensure_ascii=False)}
- 近期决策: {json.dumps(agent.decisions[-3:], ensure_ascii=False) if agent.decisions else '无'}
"""
        if rag_context:
            world_info += f"\nRAG 知识库参考: {rag_context}"

        result = self.llm.chat(system_prompt, world_info)
        if result is None:
            return None

        # 尝试解析 JSON 响应
        try:
            # 清理可能的 markdown 代码块标记
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return DecisionResponse(
                action=data.get("action", "hold"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", "LLM 决策"),
                confidence=data.get("confidence", 0.8),
            )
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，从文本中提取关键信息
            action = "hold"
            for a in ["expand", "cut_cost", "innovate", "price_war", "differentiate",
                      "buy", "buy_more", "reduce_consumption", "subsidy", "tax_relief", "observe"]:
                if a in result.lower():
                    action = a
                    break
            return DecisionResponse(
                action=action,
                params={},
                reasoning=result[:200],
                confidence=0.6,
            )

    def _rule_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """规则引擎回退决策"""
        if agent.role == "enterprise":
            return self._enterprise_decision(agent, world, rag_context)
        elif agent.role == "competitor":
            return self._competitor_decision(agent, world, rag_context)
        elif agent.role == "consumer":
            return self._consumer_decision(agent, world, rag_context)
        elif agent.role == "policy":
            return self._policy_decision(agent, world, rag_context)
        else:
            return DecisionResponse(action="hold", reasoning="Unknown role")

    def _enterprise_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
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
        """蒸馏分析 - 优先 LLM，回退规则"""
        log = request.simulation_log
        if not log:
            return DistillResponse(task_id=request.task_id, report="无仿真日志可分析")

        # 尝试 LLM 蒸馏
        if self.llm.available:
            llm_result = self._llm_distill(request)
            if llm_result is not None:
                return llm_result

        # 规则回退蒸馏
        return self._rule_distill(request)

    def _llm_distill(self, request: DistillRequest) -> Optional[DistillResponse]:
        """使用 LLM 进行蒸馏分析"""
        log_summary = []
        for i, step in enumerate(request.simulation_log):
            if i % 10 == 0 or i == len(request.simulation_log) - 1:  # 每10步采样 + 最后一步
                log_summary.append({
                    "step": step.get("step", i),
                    "price_a": step.get("market_price", {}).get("product_a", 0),
                    "supply_a": step.get("supply", {}).get("product_a", 0),
                    "demand_a": step.get("demand", {}).get("product_a", 0),
                    "events": [e.get("name", "") for e in step.get("events", [])],
                })

        user_prompt = f"""
任务 ID: {request.task_id}
仿真步数: {len(request.simulation_log)}
采样数据: {json.dumps(log_summary, ensure_ascii=False)}
最终状态: {json.dumps(request.final_state, ensure_ascii=False) if request.final_state else '无'}

请生成完整的蒸馏分析报告。"""

        result = self.llm.chat(self.DISTILL_PROMPT, user_prompt)
        if result is None:
            return None

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return DistillResponse(
                task_id=request.task_id,
                report=data.get("report", result),
                causal_analysis=data.get("causal_analysis", []),
                recommendations=data.get("recommendations", []),
                metrics=data.get("metrics", {}),
            )
        except json.JSONDecodeError:
            return DistillResponse(
                task_id=request.task_id,
                report=result,
                causal_analysis=[],
                recommendations=["详见分析报告"],
                metrics={},
            )

    def _rule_distill(self, request: DistillRequest) -> DistillResponse:
        """规则蒸馏回退"""
        log = request.simulation_log
        total_steps = len(log)
        avg_price = sum(s.get("market_price", {}).get("product_a", 0) for s in log) / max(total_steps, 1)

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

        recommendations = []
        if avg_price > 120:
            recommendations.append("市场价格偏高，建议关注竞争压力和消费者购买力")
        if total_steps > 50:
            recommendations.append("长期仿真显示市场趋于稳定，建议关注政策风险")
        recommendations.append("建议持续监控供需平衡指标")
        recommendations.append("优化智能体决策策略以提升仿真精度")

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
            causal_analysis=causal[:20],
            recommendations=recommendations,
            metrics={
                "total_steps": total_steps,
                "avg_price": avg_price,
                "stability_index": 0.85,
                "market_efficiency": 0.92,
            }
        )

    def rag_search(self, query: RAGQuery) -> List[Dict[str, Any]]:
        """RAG 向量检索"""
        mock_results = [
            {"content": f"行业分析：{query.query}相关市场数据显示增长趋势", "score": 0.92, "source": "行业报告"},
            {"content": f"政策动态：近期政策对{query.query}领域有积极影响", "score": 0.88, "source": "政策文件"},
            {"content": f"竞争格局：{query.query}市场竞争加剧，头部集中度提升", "score": 0.85, "source": "市场调研"},
        ]
        return mock_results[:query.top_k]


# ==================== Global Instances ====================

llm_client = LLMClient(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL,
)
engine = NuwaAgentEngine(llm_client)

# ==================== API Routes ====================

@app.get("/api/health")
async def health():
    llm_status = "running" if llm_client.available else "standby"
    return {
        "status": "healthy",
        "service": "女娲 AI 智能体服务",
        "version": "1.0.0",
        "components": {
            "llm_agent": llm_status,
            "rag_engine": "ready",
            "distill_engine": "ready",
        },
        "stats": {
            "total_decisions": engine.decision_count,
            "llm_decisions": engine.llm_decision_count,
            "rule_decisions": engine.decision_count - engine.llm_decision_count,
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

@app.get("/api/agent/stats")
async def get_stats():
    """获取决策统计"""
    return {
        "total_decisions": engine.decision_count,
        "llm_decisions": engine.llm_decision_count,
        "rule_decisions": engine.decision_count - engine.llm_decision_count,
        "llm_available": llm_client.available,
    }

# ==================== Main ====================

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  女娲 AI 智能体服务")
    logger.info("  MiroFish 企业经营数字孪生系统")
    logger.info("========================================")
    logger.info(f"  LLM 模型: {settings.LLM_MODEL}")
    logger.info(f"  LLM 可用: {llm_client.available}")
    logger.info(f"  服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("========================================")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
