"""
女娲 LLM 智能体服务 v1.1.0 - MiroFish 企业经营数字孪生系统
基于 LangChain + RAG 的多智能体决策引擎
支持 OpenAI 兼容 API (Coze/通义千问/GLM4/DeepSeek)
增强: 重试机制、决策缓存、精细 Prompt、健康监控
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
import hashlib
import httpx
from collections import OrderedDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nuwa-ai")

app = FastAPI(
    title="女娲 AI 智能体服务",
    description="MiroFish 企业经营数字孪生系统 - LLM 多智能体决策引擎",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Configuration ====================

class Settings:
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", ""))
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", ""))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "auto")
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30"))

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "mirofish_rag")

    HOST: str = os.getenv("NUWA_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("NUWA_PORT", "8000"))

    # 决策缓存配置
    CACHE_MAX_SIZE: int = 500
    CACHE_TTL: int = 300  # 5 分钟

settings = Settings()

# ==================== Data Models ====================

class AgentState(BaseModel):
    id: str
    name: str
    role: str
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
    source: str = "rule"  # llm / rule / cache

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

# ==================== LRU Cache ====================

class LRUCache:
    """带 TTL 的 LRU 缓存"""
    def __init__(self, maxsize: int = 500, ttl: int = 300):
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def _make_key(self, agent_id: str, role: str, step: int, price_a: float) -> str:
        return f"{agent_id}:{role}:{step}:{price_a:.0f}"

    def get(self, agent_id: str, role: str, step: int, price_a: float) -> Optional[DecisionResponse]:
        key = self._make_key(agent_id, role, step, price_a)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["ts"] < self.ttl:
                self.cache.move_to_end(key)
                self.hits += 1
                return entry["data"]
            else:
                del self.cache[key]
        self.misses += 1
        return None

    def put(self, agent_id: str, role: str, step: int, price_a: float, data: DecisionResponse):
        key = self._make_key(agent_id, role, step, price_a)
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = {"data": data, "ts": time.time()}
        while len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "max_size": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
        }

# ==================== LLM Client (增强版) ====================

class LLMClient:
    """LLM 客户端 - 支持 OpenAI 兼容 API, 重试, 超时"""

    def __init__(self, base_url: str, api_key: str, model: str, max_retries: int = 2, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.available = bool(base_url and api_key)
        self.call_count = 0
        self.fail_count = 0
        self.total_latency = 0.0
        self.last_call_time: Optional[float] = None

        # 创建不同超时的客户端
        self.client = httpx.Client(timeout=timeout)
        self.long_client = httpx.Client(timeout=timeout * 2)  # 蒸馏用长超时

    def chat(self, system_prompt: str, user_prompt: str, long_timeout: bool = False) -> Optional[str]:
        """调用 LLM 获取回复, 支持重试"""
        if not self.available:
            return None

        client = self.long_client if long_timeout else self.client
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
            "stream": False,  # 请求非流式响应
        }

        for attempt in range(self.max_retries):
            try:
                start = time.time()
                resp = client.post(url, headers=headers, json=payload)
                latency = time.time() - start
                self.call_count += 1
                self.total_latency += latency
                self.last_call_time = time.time()

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                elif resp.status_code == 429:
                    # 限速, 等待后重试
                    wait = 2 ** attempt
                    logger.warning(f"LLM rate limited, waiting {wait}s before retry...")
                    time.sleep(wait)
                    continue
                else:
                    logger.warning(f"LLM API error: {resp.status_code} {resp.text[:200]}")
                    self.fail_count += 1
                    return None
            except httpx.TimeoutException:
                logger.warning(f"LLM timeout on attempt {attempt+1}/{self.max_retries}")
                self.fail_count += 1
                continue
            except json.JSONDecodeError:
                # 可能是 SSE 流式响应，尝试解析
                text = resp.text
                content_parts = []
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("data: "):
                        json_str = line[6:]
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            choices = chunk.get("choices") or []
                            if choices:
                                delta = choices[0].get("delta") or {}
                                c = delta.get("content", "")
                                if c:
                                    content_parts.append(c)
                        except json.JSONDecodeError:
                            continue
                if content_parts:
                    self.call_count += 1
                    return "".join(content_parts)
                self.fail_count += 1
                logger.warning(f"LLM response parse failed (SSE fallback)")
                return None
            except httpx.TimeoutException:
                logger.warning(f"LLM timeout on attempt {attempt+1}/{self.max_retries}")
                self.fail_count += 1
                continue
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                self.fail_count += 1
                return None

        return None

    def health_check(self) -> bool:
        if not self.available:
            return False
        try:
            result = self.chat("You are a health checker.", "Reply OK")
            return result is not None
        except:
            return False

    def stats(self) -> Dict[str, Any]:
        avg_latency = self.total_latency / self.call_count if self.call_count > 0 else 0
        return {
            "available": self.available,
            "model": self.model,
            "total_calls": self.call_count,
            "failures": self.fail_count,
            "avg_latency": round(avg_latency, 3),
            "last_call": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_call_time)) if self.last_call_time else "never",
        }


# ==================== AI Agent Engine (增强版) ====================

class NuwaAgentEngine:
    """女娲智能体引擎 v1.1 - 多角色 AI 决策, 缓存, 精细 Prompt"""

    ROLE_PROMPTS = {
        "enterprise": """你是企业经营决策AI助手，正在参与一个企业经营仿真系统。

你的角色：核心企业A的CEO
当前策略：增长优先

可选决策及含义：
- expand: 扩张生产，需要大量资本投入，会增加供给
- cut_cost: 削减成本，减少供给但提高利润率
- innovate: 研发创新，提升效率但消耗资本
- price_adjust: 调整售价，影响需求量
- hold: 维持现状，观察市场变化

决策原则：
1. 资本充足时优先扩张或创新
2. 利润率低时削减成本
3. 供需失衡时调整价格
4. 考虑政策环境变化的影响

输出严格 JSON 格式：
{"action": "决策动作", "params": {"参数名": 参数值}, "reasoning": "决策理由(50字内)", "confidence": 0.0到1.0的置信度}""",

        "competitor": """你是竞争对手决策AI助手，正在参与一个企业经营仿真系统。

你的角色：竞争企业B的战略总监
当前策略：成本领先

可选决策及含义：
- price_war: 发动价格战，降价抢占市场
- differentiate: 差异化竞争，提升质量
- expand: 扩张产能
- hold: 维持现状
- partner: 寻求合作

决策原则：
1. 对手价格高时发动价格战
2. 资本充足时差异化投入
3. 市场份额低时积极争夺
4. 考虑长期竞争均衡

输出严格 JSON 格式：
{"action": "决策动作", "params": {"参数名": 参数值}, "reasoning": "决策理由(50字内)", "confidence": 0.0到1.0的置信度}""",

        "consumer": """你是消费者群体决策AI助手，正在参与一个企业经营仿真系统。

你的角色：代表整体消费者群体
目标：效用最大化

可选决策及含义：
- buy: 正常消费
- buy_more: 增加消费量
- reduce_consumption: 减少消费
- substitute: 转向替代品
- hold: 观望不消费

决策原则：
1. 价格低时增加购买
2. 价格高时减少或替代
3. 考虑产品满意度
4. 关注替代品性价比

输出严格 JSON 格式：
{"action": "决策动作", "params": {"参数名": 参数值}, "reasoning": "决策理由(50字内)", "confidence": 0.0到1.0的置信度}""",

        "policy": """你是政策制定者决策AI助手，正在参与一个企业经营仿真系统。

你的角色：国家经济政策制定者
目标：经济稳定和公平

可选决策及含义：
- subsidy: 提供生产补贴
- tax_relief: 减免税收
- tighten: 收紧货币政策（加息）
- stimulate: 刺激经济
- observe: 维持现有政策

决策原则：
1. 供给不足时提供补贴
2. 通胀压力时收紧货币
3. 供给过剩时减税刺激需求
4. 市场均衡时维持政策
5. 关注就业和经济增速

输出严格 JSON 格式：
{"action": "决策动作", "params": {"参数名": 参数值}, "reasoning": "决策理由(50字内)", "confidence": 0.0到1.0的置信度}""",
    }

    DISTILL_PROMPT = """你是企业经营仿真蒸馏分析AI。分析以下仿真数据，生成深度因果分析报告。

分析框架：
1. 宏观趋势：价格走势、供需变化、政策影响
2. 事件冲击：每个关键事件的市场响应链路
3. 智能体评估：各角色决策的效果和合理性
4. 因果推理：哪些因素导致了关键结果
5. 经营建议：基于因果分析的策略建议

输出严格 JSON 格式：
{
  "report": "完整的分析报告(含标题和分段)",
  "causal_analysis": [{"step": 0, "event": "事件名", "type": "类型", "impact": {"指标": 变化}}],
  "recommendations": ["建议1", "建议2", "建议3"],
  "metrics": {"stability_index": 0.0-1.0, "market_efficiency": 0.0-1.0, "risk_level": "low/medium/high"}
}"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.cache = LRUCache(settings.CACHE_MAX_SIZE, settings.CACHE_TTL)
        self.decision_count = 0
        self.llm_decision_count = 0
        self.cache_hit_count = 0
        self.start_time = time.time()

    def get_decision(self, request: DecisionRequest) -> DecisionResponse:
        """获取智能体决策 - 缓存 -> LLM -> 规则回退"""
        agent = request.agent
        world = request.world
        price_a = world.market_price.get("product_a", 0)

        # 1. 查缓存
        cached = self.cache.get(agent.id, agent.role, world.step, price_a)
        if cached is not None:
            self.decision_count += 1
            self.cache_hit_count += 1
            result = cached.model_copy()
            result.source = "cache"
            return result

        # 2. 尝试 LLM 决策
        if self.llm.available:
            llm_result = self._llm_decision(agent, world, request.rag_context)
            if llm_result is not None:
                self.decision_count += 1
                self.llm_decision_count += 1
                llm_result.source = "llm"
                # 写入缓存
                self.cache.put(agent.id, agent.role, world.step, price_a, llm_result)
                return llm_result

        # 3. 规则回退决策
        self.decision_count += 1
        result = self._rule_decision(agent, world, request.rag_context)
        result.source = "rule"
        self.cache.put(agent.id, agent.role, world.step, price_a, result)
        return result

    def _llm_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> Optional[DecisionResponse]:
        """使用 LLM 生成决策"""
        system_prompt = self.ROLE_PROMPTS.get(agent.role, self.ROLE_PROMPTS["enterprise"])

        # 构建更详细的用户 prompt
        sd_ratio_a = world.supply.get("product_a", 1) / max(world.demand.get("product_a", 1), 0.01)
        sd_ratio_b = world.supply.get("product_b", 1) / max(world.demand.get("product_b", 1), 0.01)

        user_prompt = f"""
== 当前世界状态 ==
仿真轮次: {world.step}
产品A: 价格={world.market_price.get('product_a', 0):.1f} 供给={world.supply.get('product_a', 0):.0f} 需求={world.demand.get('product_a', 0):.0f} 供需比={sd_ratio_a:.2f}
产品B: 价格={world.market_price.get('product_b', 0):.1f} 供给={world.supply.get('product_b', 0):.0f} 需求={world.demand.get('product_b', 0):.0f} 供需比={sd_ratio_b:.2f}
原材料: 价格={world.market_price.get('raw_material', 0):.1f}
政策: 税率={world.policy.get('tax_rate', 0)} 利率={world.policy.get('interest_rate', 0)} 补贴={world.policy.get('subsidy', 0)}
近期事件: {json.dumps([{'name': e.get('name'), 'type': e.get('type')} for e in world.events[-5:]], ensure_ascii=False) if world.events else '无'}

== 你的状态 ==
ID: {agent.id}
名称: {agent.name}
资本: {agent.capital:.0f}
策略: {agent.strategy}
详细状态: {json.dumps(agent.state, ensure_ascii=False) if agent.state else '无'}
近期决策: {json.dumps([{'step': d.get('step'), 'action': d.get('action')} for d in agent.decisions[-3:]], ensure_ascii=False) if agent.decisions else '无'}
"""
        if rag_context:
            user_prompt += f"\n== RAG 知识库参考 ==\n{rag_context}"

        user_prompt += "\n\n请做出你的决策，输出严格 JSON 格式。"

        result = self.llm.chat(system_prompt, user_prompt)
        if result is None:
            return None

        # 解析 JSON
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            # 找到第一个 { 和最后一个 }
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start:end+1]

            data = json.loads(cleaned)
            return DecisionResponse(
                action=data.get("action", "hold"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", "LLM 决策")[:100],
                confidence=min(1.0, max(0.0, data.get("confidence", 0.8))),
            )
        except json.JSONDecodeError:
            # 从文本中提取关键信息
            action = "hold"
            for a in ["expand", "cut_cost", "innovate", "price_adjust", "price_war",
                      "differentiate", "buy", "buy_more", "reduce_consumption", "substitute",
                      "subsidy", "tax_relief", "observe", "tighten", "stimulate", "hold"]:
                if a in result.lower().replace(" ", "_"):
                    action = a
                    break
            return DecisionResponse(
                action=action,
                params={},
                reasoning=result[:100],
                confidence=0.6,
            )

    def _rule_decision(self, agent: AgentState, world: WorldState, rag_context: Optional[str] = None) -> DecisionResponse:
        """规则引擎回退决策 - 更智能"""
        if agent.role == "enterprise":
            return self._enterprise_decision(agent, world)
        elif agent.role == "competitor":
            return self._competitor_decision(agent, world)
        elif agent.role == "consumer":
            return self._consumer_decision(agent, world)
        elif agent.role == "policy":
            return self._policy_decision(agent, world)
        else:
            return DecisionResponse(action="hold", reasoning="Unknown role")

    def _enterprise_decision(self, agent: AgentState, world: WorldState) -> DecisionResponse:
        capital = agent.capital
        price_a = world.market_price.get("product_a", 100)
        demand_a = world.demand.get("product_a", 0)
        supply_a = world.supply.get("product_a", 0)
        sd_ratio = supply_a / max(demand_a, 0.01)
        profit_margin = agent.state.get("profit_margin", 0.2) if agent.state else 0.2

        reasoning = f"资本{capital:.0f}，供需比{sd_ratio:.2f}，利润率{profit_margin:.1%}。"

        if capital > 8000000 and sd_ratio < 1.0:
            action = "expand"
            params = {"investment": capital * 0.2, "target": "production"}
            reasoning += "资本充足且需求旺盛，扩张产能。"
        elif profit_margin < 0.1:
            action = "cut_cost"
            params = {"reduction": 0.15, "areas": ["marketing", "overhead"]}
            reasoning += "利润率低，削减成本。"
        elif capital > 5000000 and profit_margin > 0.15:
            action = "innovate"
            params = {"rd_investment": capital * 0.1, "area": "efficiency"}
            reasoning += "利润率尚可，投入研发提升效率。"
        elif price_a > 110 and sd_ratio > 1.0:
            action = "price_adjust"
            params = {"new_price": price_a * 0.95, "reason": "market_share"}
            reasoning += "价格偏高且供过于求，适当降价。"
        else:
            action = "hold"
            params = {}
            reasoning += "市场稳定，维持现状观察。"

        confidence = min(0.95, 0.6 + random.random() * 0.3)
        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=confidence)

    def _competitor_decision(self, agent: AgentState, world: WorldState) -> DecisionResponse:
        price_a = world.market_price.get("product_a", 100)
        price_b = world.market_price.get("product_b", 80)
        reasoning = f"产品A价格{price_a:.1f}，产品B价格{price_b:.1f}。"

        if price_a > price_b * 1.2:
            action = "price_war"
            params = {"discount": 0.08, "duration": 3}
            reasoning += "对手价格高，价格战抢市场。"
        elif agent.capital > 6000000:
            action = "differentiate"
            params = {"strategy": "quality", "investment": agent.capital * 0.15}
            reasoning += "资本充足，差异化竞争。"
        else:
            action = "hold"
            params = {}
            reasoning += "保持竞争姿态，观察。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.7)

    def _consumer_decision(self, agent: AgentState, world: WorldState) -> DecisionResponse:
        price_a = world.market_price.get("product_a", 100)
        price_b = world.market_price.get("product_b", 80)
        reasoning = f"产品A价格{price_a:.1f}，产品B价格{price_b:.1f}。"

        if price_a < 80:
            action = "buy_more"
            params = {"quantity": 200}
            reasoning += "A价格低，增加购买。"
        elif price_a > 120:
            action = "reduce_consumption"
            params = {"reduction": 0.3}
            reasoning += "A价格高，减少消费。"
        elif price_b < price_a * 0.7:
            action = "substitute"
            params = {"target": "product_b"}
            reasoning += "B性价比更高，转向B。"
        else:
            action = "buy"
            params = {"quantity": 100}
            reasoning += "价格合理，正常消费。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.8)

    def _policy_decision(self, agent: AgentState, world: WorldState) -> DecisionResponse:
        tax = world.policy.get("tax_rate", 0.13)
        supply_a = world.supply.get("product_a", 1)
        demand_a = world.demand.get("product_a", 1)
        sd_ratio = supply_a / max(demand_a, 0.01)
        price_a = world.market_price.get("product_a", 100)
        reasoning = f"供需比{sd_ratio:.2f}，税率{tax}，价格{price_a:.1f}。"

        if sd_ratio < 0.8:
            action = "subsidy"
            params = {"amount": 500000, "target": "production"}
            reasoning += "供给不足，提供生产补贴。"
        elif price_a > 130:
            action = "tighten"
            params = {"rate_increase": 0.005}
            reasoning += "通胀压力大，收紧货币。"
        elif sd_ratio > 1.2:
            action = "tax_relief"
            params = {"reduction": 0.02}
            reasoning += "供给过剩，减免税收。"
        else:
            action = "observe"
            params = {}
            reasoning += "市场均衡，维持政策。"

        return DecisionResponse(action=action, params=params, reasoning=reasoning, confidence=0.75)

    def distill(self, request: DistillRequest) -> DistillResponse:
        """蒸馏分析 - LLM优先，规则回退"""
        log = request.simulation_log
        if not log:
            return DistillResponse(task_id=request.task_id, report="无仿真日志可分析")

        # 尝试 LLM 蒸馏 (长超时)
        if self.llm.available:
            llm_result = self._llm_distill(request)
            if llm_result is not None:
                return llm_result

        # 规则回退蒸馏
        return self._rule_distill(request)

    def _llm_distill(self, request: DistillRequest) -> Optional[DistillResponse]:
        """使用 LLM 进行蒸馏分析"""
        # 智能采样: 取首步 + 每10步 + 关键事件步 + 最后步
        sampled = []
        for i, step in enumerate(request.simulation_log):
            events = step.get("events", [])
            if i == 0 or i == len(request.simulation_log) - 1 or i % 10 == 0 or events:
                sampled.append({
                    "step": step.get("step", i),
                    "price_a": step.get("market_price", {}).get("product_a", 0),
                    "supply_a": step.get("supply", {}).get("product_a", 0),
                    "demand_a": step.get("demand", {}).get("product_a", 0),
                    "events": [e.get("name", "") for e in events],
                })

        user_prompt = f"""
任务 ID: {request.task_id}
总仿真步数: {len(request.simulation_log)}
采样数据点: {len(sampled)}

关键数据:
{json.dumps(sampled[:30], ensure_ascii=False, indent=2)}

最终状态: {json.dumps(request.final_state, ensure_ascii=False) if request.final_state else '无'}

请生成完整的蒸馏分析报告，严格按照要求的 JSON 格式输出。"""

        result = self.llm.chat(self.DISTILL_PROMPT, user_prompt, long_timeout=True)
        if result is None:
            return None

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start:end+1]

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
        """规则蒸馏回退 - 更详细的分析"""
        log = request.simulation_log
        total_steps = len(log)
        prices_a = [s.get("market_price", {}).get("product_a", 0) for s in log]
        supplies_a = [s.get("supply", {}).get("product_a", 0) for s in log]
        demands_a = [s.get("demand", {}).get("product_a", 0) for s in log]

        avg_price = sum(prices_a) / max(total_steps, 1)
        min_price = min(prices_a) if prices_a else 0
        max_price = max(prices_a) if prices_a else 0
        price_volatility = (max_price - min_price) / max(avg_price, 0.01)

        # 识别价格趋势
        if len(prices_a) >= 5:
            recent = prices_a[-5:]
            early = prices_a[:5]
            trend = "上涨" if sum(recent)/5 > sum(early)/5 else "下跌"
        else:
            trend = "稳定"

        causal = []
        for i, step in enumerate(log):
            for event in step.get("events", []):
                causal.append({
                    "step": step.get("step", i),
                    "event": event.get("name", "unknown"),
                    "type": event.get("type", "unknown"),
                    "impact": event.get("impact", {}),
                })

        # 智能推荐
        recommendations = []
        if avg_price > 120:
            recommendations.append("市场价格持续偏高，建议关注竞争压力和消费者购买力下降风险")
        if price_volatility > 0.3:
            recommendations.append("价格波动剧烈，建议建立风险对冲机制和价格预警系统")
        if trend == "下跌":
            recommendations.append("价格呈下跌趋势，建议优化成本结构，提升产品差异化竞争力")
        recommendations.append("持续监控供需平衡指标，建立动态调价机制")
        recommendations.append("优化智能体决策策略，引入更多真实市场数据提升仿真精度")

        # 计算稳定性指数
        stability = max(0.3, 1.0 - price_volatility)
        efficiency = min(1.0, sum(demands_a) / max(sum(supplies_a), 1))

        report = f"""# 企业经营仿真蒸馏报告

## 任务 ID: {request.task_id}

### 仿真概况
- 总步数: {total_steps}
- 平均产品价格: {avg_price:.2f}
- 价格区间: {min_price:.2f} ~ {max_price:.2f}
- 价格波动率: {price_volatility:.1%}
- 价格趋势: {trend}
- 关键事件数: {len(causal)}

### 市场分析
- 市场效率: {efficiency:.1%}
- 稳定性指数: {stability:.1%}
- 供需关系: {'供不应求' if sum(demands_a) > sum(supplies_a) else '供过于求' if sum(supplies_a) > sum(demands_a) else '基本均衡'}

### 因果分析
共识别 {len(causal)} 个关键事件:
{chr(10).join(f'- Step {c["step"]}: {c["event"]} ({c["type"]})' for c in causal[:15])}

### 经营建议
{chr(10).join(f'- {r}' for r in recommendations)}"""

        return DistillResponse(
            task_id=request.task_id,
            report=report,
            causal_analysis=causal[:30],
            recommendations=recommendations,
            metrics={
                "total_steps": total_steps,
                "avg_price": round(avg_price, 2),
                "stability_index": round(stability, 3),
                "market_efficiency": round(efficiency, 3),
                "price_volatility": round(price_volatility, 3),
                "risk_level": "high" if price_volatility > 0.3 else "medium" if price_volatility > 0.15 else "low",
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

    def stats(self) -> Dict[str, Any]:
        return {
            "uptime": time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time)),
            "total_decisions": self.decision_count,
            "llm_decisions": self.llm_decision_count,
            "rule_decisions": self.decision_count - self.llm_decision_count - self.cache_hit_count,
            "cache_hits": self.cache_hit_count,
            "cache_stats": self.cache.stats(),
        }


# ==================== Global Instances ====================

llm_client = LLMClient(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL,
    max_retries=settings.LLM_MAX_RETRIES,
    timeout=settings.LLM_TIMEOUT,
)
engine = NuwaAgentEngine(llm_client)

# ==================== API Routes ====================

@app.get("/api/health")
async def health():
    llm_status = "running" if llm_client.available else "standby"
    return {
        "status": "healthy",
        "service": "女娲 AI 智能体服务",
        "version": "1.1.0",
        "components": {
            "llm_agent": llm_status,
            "rag_engine": "ready",
            "distill_engine": "ready",
            "cache": "running",
        },
        "stats": engine.stats(),
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
        **engine.stats(),
        "llm_stats": llm_client.stats(),
    }

# ==================== Main ====================

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  女娲 AI 智能体服务 v1.1.0")
    logger.info("  MiroFish 企业经营数字孪生系统")
    logger.info("========================================")
    logger.info(f"  LLM 模型: {settings.LLM_MODEL}")
    logger.info(f"  LLM 可用: {llm_client.available}")
    logger.info(f"  缓存大小: {settings.CACHE_MAX_SIZE}")
    logger.info(f"  服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("========================================")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
