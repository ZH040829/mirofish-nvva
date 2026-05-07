#!/usr/bin/env python3
"""
女娲 AI 智能体服务 v1.5.0
MiroFish 企业经营数字孪生系统 - AI 决策引擎

增强: 多轮协商、自然语言建仿真、跨仿真记忆、批量优化、精细Prompt
v1.4.0: 市场情绪、智能体进化、对话控制、SSE回放
v1.5.0: 市场预测、风险预警、交易建议、SSE流式决策、Dashboard AI汇总
"""

import os, time, json, logging, hashlib, re
from typing import List, Dict, Any, Optional
from collections import OrderedDict
from dataclasses import dataclass

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("nuwa")

# ==================== Config ====================

class Settings:
    LLM_BASE_URL: str = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", os.getenv("LLM_BASE_URL", ""))
    LLM_API_KEY: str = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", os.getenv("LLM_API_KEY", ""))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "auto")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "500"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    HOST: str = os.getenv("AI_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("AI_PORT", "8000"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

settings = Settings()

# ==================== Redis Cache ====================

class RedisCache:
    def __init__(self, url: str):
        self.url = url
        self.client = None
        self.available = False
        self._connect()

    def _connect(self):
        try:
            import redis
            self.client = redis.from_url(self.url, socket_timeout=3, socket_connect_timeout=3)
            self.client.ping()
            self.available = True
            logger.info(f"[Redis] 连接成功: {self.url}")
        except Exception as e:
            logger.warning(f"[Redis] 连接失败: {e}，使用本地缓存")
            self.available = False

    def get(self, key: str) -> Optional[str]:
        if not self.available or not self.client: return None
        try: return self.client.get(key)
        except: return None

    def set(self, key: str, value: str, ttl: int = 300):
        if not self.available or not self.client: return
        try: self.client.setex(key, ttl, value)
        except: pass

    def delete(self, pattern: str):
        if not self.available or not self.client: return
        try:
            for key in self.client.scan_iter(pattern):
                self.client.delete(key)
        except: pass

    def lpush(self, key: str, value: str, maxlen: int = 100):
        if not self.available or not self.client: return
        try:
            self.client.lpush(key, value)
            self.client.ltrim(key, 0, maxlen - 1)
        except: pass

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        if not self.available or not self.client: return []
        try: return [v.decode() for v in self.client.lrange(key, start, end)]
        except: return []

    def stats(self) -> Dict[str, Any]:
        if not self.available or not self.client:
            return {"available": False}
        try:
            info = self.client.info("stats")
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            return {"available": True, "keys": self.client.dbsize(), "hits": hits, "misses": misses,
                    "hit_rate": hits / max(hits + misses, 1)}
        except: return {"available": False}

# ==================== LRU Cache ====================

class LRUCache:
    def __init__(self, max_size: int = 500, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _make_key(self, agent_id: str, role: str, step: int, world_hash: str) -> str:
        return f"{agent_id}:{role}:{step}:{world_hash[:8]}"

    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["ts"] < self.ttl:
                self.cache.move_to_end(key)
                self.hits += 1
                return entry["data"]
            del self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, data: Dict):
        if key in self.cache: del self.cache[key]
        self.cache[key] = {"data": data, "ts": time.time()}
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {"size": len(self.cache), "max_size": self.max_size, "hits": self.hits,
                "misses": self.misses, "hit_rate": self.hits / max(total, 1)}

    def clear(self):
        self.cache.clear(); self.hits = 0; self.misses = 0

# ==================== Cross-Simulation Memory ====================

class CrossSimMemory:
    """跨仿真记忆系统 - 记录不同仿真的经验教训"""
    def __init__(self, redis_cache: RedisCache):
        self.redis = redis_cache
        self.local_memory: List[Dict] = []
        self.max_local = 200

    def record(self, task_id: str, lesson: str, metrics: Dict[str, float], tag: str = ""):
        entry = {"task_id": task_id, "lesson": lesson, "metrics": metrics,
                 "tag": tag, "ts": time.time()}
        self.local_memory.append(entry)
        if len(self.local_memory) > self.max_local:
            self.local_memory = self.local_memory[-self.max_local:]
        # 同时写入 Redis
        if self.redis.available:
            self.redis.lpush("nuwa:memory:lessons", json.dumps(entry, ensure_ascii=False), maxlen=500)

    def recall(self, query: str = "", tag: str = "", limit: int = 10) -> List[Dict]:
        results = []
        # 先从本地查
        for entry in reversed(self.local_memory):
            if tag and entry.get("tag") != tag: continue
            if query and query.lower() not in entry.get("lesson", "").lower(): continue
            results.append(entry)
            if len(results) >= limit: break
        # 再从 Redis 查
        if len(results) < limit and self.redis.available:
            redis_entries = self.redis.lrange("nuwa:memory:lessons", 0, 50)
            for raw in redis_entries:
                try:
                    entry = json.loads(raw)
                    if tag and entry.get("tag") != tag: continue
                    if query and query.lower() not in entry.get("lesson", "").lower(): continue
                    if entry not in results: results.append(entry)
                    if len(results) >= limit: break
                except: continue
        return results

    def stats(self) -> Dict[str, Any]:
        return {"local_entries": len(self.local_memory),
                "redis_available": self.redis.available}

# ==================== LLM Client ====================

class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str = "auto",
                 max_retries: int = 2, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.available = bool(base_url and api_key)
        self.call_count = 0
        self.fail_count = 0
        self.total_latency = 0.0

    def _parse_sse_response(self, resp: httpx.Response) -> str:
        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if "text/event-stream" in content_type or (text and "data:" in text[:100]):
            full_content = []
            reasoning_content = []
            for line in text.split("\n"):
                line = line.strip()
                if not line or line.startswith(":"): continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]": break
                    try:
                        chunk = json.loads(data)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            c = delta.get("content", "")
                            r = delta.get("reasoning_content", "")
                            if c: full_content.append(c)
                            if r: reasoning_content.append(r)
                    except json.JSONDecodeError: continue
            # 优先返回 content, 如果为空则从 reasoning_content 中提取 JSON
            result = "".join(full_content)
            if not result and reasoning_content:
                rc = "".join(reasoning_content)
                # 尝试从 reasoning_content 中提取 JSON
                import re
                json_patterns = [
                    r'\{[^{}]*"action"[^{}]*"reasoning"[^{}]*\}',  # 单层 JSON with action+reasoning
                    r'\{[^{}]*"action"[^{}]*\}',  # 单层 JSON with action
                    r'```json\s*(\{.*?\})\s*```',   # 代码块包裹
                    r'```(\{.*?\})```',              # 无语言标记
                ]
                for pat in json_patterns:
                    m = re.search(pat, rc, re.DOTALL)
                    if m:
                        result = m.group(1) if m.lastindex else m.group(0)
                        break
                if not result:
                    # 最后尝试：找最后一个 { 开始到 } 结束的 JSON 块
                    last_brace = rc.rfind('{')
                    if last_brace >= 0:
                        depth = 0
                        for i in range(last_brace, len(rc)):
                            if rc[i] == '{': depth += 1
                            elif rc[i] == '}': depth -= 1
                            if depth == 0:
                                candidate = rc[last_brace:i+1]
                                try:
                                    json.loads(candidate)
                                    result = candidate
                                    break
                                except: pass
                if not result:
                    result = rc  # 全量返回，让调用方处理
            return result
        else:
            try:
                data = resp.json()
                choices = data.get("choices", [])
                if choices: return choices[0].get("message", {}).get("content", "")
            except: pass
            return text

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
        if not self.available: return None
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], "temperature": temperature, "max_tokens": max_tokens}

        for attempt in range(self.max_retries + 1):
            try:
                start = time.time()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                latency = time.time() - start
                self.call_count += 1
                self.total_latency += latency
                if resp.status_code == 200:
                    result = self._parse_sse_response(resp)
                    if result: return result
                    logger.warning(f"[LLM] 响应为空 (attempt {attempt+1})")
                else:
                    logger.warning(f"[LLM] HTTP {resp.status_code} (attempt {attempt+1})")
            except httpx.TimeoutException:
                logger.warning(f"[LLM] 超时 (attempt {attempt+1})"); self.fail_count += 1
            except Exception as e:
                logger.warning(f"[LLM] 异常: {e} (attempt {attempt+1})"); self.fail_count += 1
            if attempt < self.max_retries: time.sleep(0.5 * (attempt + 1))
        return None

    def chat_multi_turn(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 800) -> Optional[str]:
        """多轮对话"""
        if not self.available: return None
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                self.call_count += 1
                if resp.status_code == 200:
                    result = self._parse_sse_response(resp)
                    if result: return result
            except: self.fail_count += 1
            if attempt < self.max_retries: time.sleep(0.5 * (attempt + 1))
        return None

    def stats(self) -> Dict[str, Any]:
        avg_lat = self.total_latency / max(self.call_count, 1)
        return {"available": self.available, "model": self.model, "calls": self.call_count,
                "failures": self.fail_count, "avg_latency": round(avg_lat, 2)}

# ==================== Prompt Templates ====================

ROLE_PROMPTS = {
    "enterprise": {
        "system": """你是企业经营AI决策助手。根据市场数据选择决策。
选项: expand/cut_cost/innovate/price_adjust/hold
直接输出一行JSON，不要分析过程:
{"action":"expand","params":{},"reasoning":"简短理由","confidence":0.8}""",
        "user": """企业{agent_name}: 资本={capital:.0f} 策略={strategy} 收入={revenue:.0f} 成本={cost:.0f}
价格A={price_a:.1f} 供需比={sd_ratio:.2f} 税率={tax_rate:.1%}
事件:{events} 经验:{memory}
输出JSON:""",
    },
    "competitor": {
        "system": """你是竞争企业AI决策助手。根据市场数据选择决策。
选项: price_war/differentiate/hold/expand/innovate
直接输出一行JSON，不要分析过程:
{"action":"price_war","params":{},"reasoning":"简短理由","confidence":0.7}""",
        "user": """竞争者{agent_name}: 资本={capital:.0f} 对手价={price_a:.1f} 我方价={price_b:.1f}
价比={price_ratio:.2f} 事件:{events} 经验:{memory}
输出JSON:""",
    },
    "consumer": {
        "system": """你是消费者群体AI决策助手。根据价格数据选择决策。
选项: buy/buy_more/reduce_consumption/substitute
直接输出一行JSON，不要分析过程:
{"action":"buy","params":{},"reasoning":"简短理由","confidence":0.6}""",
        "user": """消费者: 资金={capital:.0f} 价格A={price_a:.1f} B={price_b:.1f}
购买力={purchasing_power:.1f} 满意度={satisfaction:.1%}
事件:{events} 经验:{memory}
输出JSON:""",
    },
    "policy": {
        "system": """你是政策制定者AI决策助手。根据经济数据选择决策。
选项: subsidy/tax_relief/tighten/stimulate/observe
直接输出一行JSON，不要分析过程:
{"action":"observe","params":{},"reasoning":"简短理由","confidence":0.85}""",
        "user": """政策(第{step}轮): 通胀={inflation:.2f} 供需比={sd_ratio:.2f}
价格A={price_a:.1f} 信心={market_confidence:.1%}
税率={tax_rate:.1%} 利率={interest_rate:.2%}
事件:{events} 经验:{memory}
输出JSON:""",
    },
}

NEGOTIATION_PROMPT = """你是企业经营仿真的协商调解AI。
以下智能体提出了各自的决策方案，请评估并协调冲突：

{proposals}

请分析:
1. 各方案之间是否存在冲突？
2. 如果存在冲突，建议如何协调？
3. 最终推荐方案是什么？

输出JSON: {"conflicts":["冲突1","冲突2"],"resolutions":["解决1","解决2"],"recommendation":"推荐方案","reasoning":"理由"}"""

NL_CREATE_PROMPT = """你是企业经营仿真系统的自然语言理解AI。
用户用自然语言描述了想要创建的仿真场景，请解析为结构化配置。

用户输入: "{user_input}"

输出JSON: {{
  "name": "仿真名称",
  "max_steps": 50,
  "agents": [
    {{"role": "enterprise", "name": "企业名", "capital": 10000000, "strategy": "growth"}},
    {{"role": "competitor", "name": "竞争者名", "capital": 8000000, "strategy": "aggressive"}},
    {{"role": "consumer", "name": "消费者", "capital": 500000, "strategy": "balanced"}},
    {{"role": "policy", "name": "政策制定者", "capital": 0, "strategy": "balanced"}}
  ],
  "initial_state": {{
    "market_price": {{"product_a": 100, "product_b": 80, "raw_material": 50}},
    "policy": {{"tax_rate": 0.13, "subsidy": 0, "interest_rate": 0.035}}
  }},
  "event_config": {{
    "crisis_probability": 0.05,
    "enable_cascade": true
  }}
}}"""

# ==================== Data Models ====================

class DecisionRequest(BaseModel):
    agent: Dict[str, Any]
    world: Dict[str, Any]

class DecisionResponse(BaseModel):
    action: str
    params: Dict[str, Any] = {}
    reasoning: str = ""
    confidence: float = 0.5
    source: str = "rule"
    latency_ms: float = 0.0

class BatchDecisionRequest(BaseModel):
    agents: List[Dict[str, Any]]
    world: Dict[str, Any]

class BatchDecisionResponse(BaseModel):
    decisions: List[DecisionResponse]
    total: int
    llm_count: int
    rule_count: int
    cache_count: int

class DistillRequest(BaseModel):
    task_id: str
    simulation_log: List[Dict[str, Any]] = []
    final_state: Optional[Dict[str, Any]] = None

class DistillResponse(BaseModel):
    task_id: str
    report: str = ""
    causal_analysis: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    metrics: Dict[str, float] = {}

class RAGQuery(BaseModel):
    query: str
    top_k: int = 5

class ReplayRequest(BaseModel):
    task_id: str
    history: List[Dict[str, Any]]
    focus_step: Optional[int] = None
    focus_agent: Optional[str] = None

class ReplayResponse(BaseModel):
    task_id: str
    summary: str
    key_moments: List[Dict[str, Any]]
    agent_trajectory: Dict[str, List[str]]
    lessons: List[str]

class NegotiationRequest(BaseModel):
    proposals: List[Dict[str, Any]]  # [{agent_id, agent_name, role, action, reasoning, confidence}]

class NegotiationResponse(BaseModel):
    conflicts: List[str]
    resolutions: List[str]
    recommendation: str
    reasoning: str

class NLCreateRequest(BaseModel):
    user_input: str

class NLCreateResponse(BaseModel):
    config: Dict[str, Any]
    parsed: bool
    message: str

class MemoryRecordRequest(BaseModel):
    task_id: str
    lesson: str
    metrics: Dict[str, float] = {}
    tag: str = ""

class MemoryRecallRequest(BaseModel):
    query: str = ""
    tag: str = ""
    limit: int = 10

# ==================== Nuwa Agent Engine ====================

class NuwaAgentEngine:
    def __init__(self, llm_client: LLMClient, redis_cache: RedisCache):
        self.llm = llm_client
        self.redis = redis_cache
        self.local_cache = LRUCache(settings.CACHE_MAX_SIZE, settings.CACHE_TTL)
        self.cross_memory = CrossSimMemory(redis_cache)
        self.start_time = time.time()
        self.decision_count = 0
        self.llm_decision_count = 0
        self.rule_decision_count = 0
        self.cache_hit_count = 0
        self.negotiation_count = 0

    def _world_hash(self, world: Dict) -> str:
        key_data = json.dumps({"step": world.get("step", 0), "price": world.get("market_price", {})}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_memory(self, role: str, limit: int = 3) -> str:
        """获取相关历史经验"""
        memories = self.cross_memory.recall(tag=role, limit=limit)
        if not memories: return "暂无"
        return "; ".join([m.get("lesson", "") for m in memories[:limit]])

    def _format_prompt(self, role: str, agent: Dict, world: Dict) -> tuple:
        prompts = ROLE_PROMPTS.get(role, ROLE_PROMPTS["enterprise"])
        state = agent.get("state", {})
        price_a = world.get("market_price", {}).get("product_a", 100)
        price_b = world.get("market_price", {}).get("product_b", 80)
        supply_a = world.get("supply", {}).get("product_a", 1000)
        demand_a = world.get("demand", {}).get("product_a", 900)
        policy = world.get("policy", {})
        events_list = [e.get("name", "") for e in world.get("events", [])]
        events_str = ", ".join(events_list) if events_list else "无"
        memory_str = self._get_memory(role)

        common = {"agent_name": agent.get("name", "Unknown"), "capital": agent.get("capital", 0),
                  "strategy": agent.get("strategy", ""), "step": world.get("step", 0),
                  "price_a": price_a, "price_b": price_b,
                  "supply_a": supply_a, "demand_a": demand_a,
                  "sd_ratio": demand_a / max(supply_a, 0.01),
                  "tax_rate": policy.get("tax_rate", 0.13), "interest_rate": policy.get("interest_rate", 0.035),
                  "subsidy": policy.get("subsidy", 0), "events": events_str, "memory": memory_str}

        if role == "enterprise":
            common.update({"revenue": state.get("revenue", 0), "cost": state.get("cost", 0),
                           "profit_margin": state.get("profit_margin", 0), "market_share": state.get("market_share", 0)})
        elif role == "competitor":
            common.update({"price_ratio": price_a / max(price_b, 0.01)})
        elif role == "consumer":
            common.update({"purchasing_power": state.get("purchasing_power", 50),
                           "satisfaction": state.get("satisfaction", 0.5)})
        elif role == "policy":
            common.update({"inflation": price_a / 100.0,
                           "market_confidence": 1.0 - abs(price_a - 100) / 100.0})

        try:
            system = prompts["system"]
            user = prompts["user"].format(**common)
        except (KeyError, IndexError):
            system = prompts["system"]
            user = json.dumps({"agent": agent, "world": world}, ensure_ascii=False)
        return system, user

    def get_decision(self, request: DecisionRequest) -> DecisionResponse:
        agent = request.agent
        world = request.world
        role = agent.get("role", "enterprise")
        agent_id = agent.get("id", "unknown")
        step = world.get("step", 0)

        # Cache check
        world_hash = self._world_hash(world)
        cache_key = self.local_cache._make_key(agent_id, role, step, world_hash)

        cached = self.local_cache.get(cache_key)
        if cached:
            self.cache_hit_count += 1; self.decision_count += 1
            resp = DecisionResponse(**cached); resp.source = "cache"; return resp

        if self.redis.available:
            redis_val = self.redis.get(f"nuwa:decision:{cache_key}")
            if redis_val:
                try:
                    cached_data = json.loads(redis_val)
                    self.cache_hit_count += 1; self.decision_count += 1
                    self.local_cache.put(cache_key, cached_data)
                    resp = DecisionResponse(**cached_data); resp.source = "cache"; return resp
                except: pass

        # LLM
        if self.llm.available:
            system_prompt, user_prompt = self._format_prompt(role, agent, world)
            start = time.time()
            result = self.llm.chat(system_prompt, user_prompt, temperature=0.7, max_tokens=1500)
            latency = (time.time() - start) * 1000
            if result:
                parsed = self._parse_decision(result, role, world)
                parsed.source = "llm"; parsed.latency_ms = round(latency, 1)
                self.llm_decision_count += 1; self.decision_count += 1
                cache_data = parsed.model_dump()
                self.local_cache.put(cache_key, cache_data)
                if self.redis.available:
                    self.redis.set(f"nuwa:decision:{cache_key}", json.dumps(cache_data), settings.CACHE_TTL)
                return parsed

        # Rule fallback
        self.rule_decision_count += 1; self.decision_count += 1
        return self._rule_decision(role, agent, world)

    def batch_decision(self, request: BatchDecisionRequest) -> BatchDecisionResponse:
        decisions = []; llm_c = 0; rule_c = 0; cache_c = 0
        for agent in request.agents:
            dec_req = DecisionRequest(agent=agent, world=request.world)
            resp = self.get_decision(dec_req)
            decisions.append(resp)
            if resp.source == "llm": llm_c += 1
            elif resp.source == "rule": rule_c += 1
            else: cache_c += 1
        return BatchDecisionResponse(decisions=decisions, total=len(decisions),
                                     llm_count=llm_c, rule_count=rule_c, cache_count=cache_c)

    def negotiate(self, request: NegotiationRequest) -> NegotiationResponse:
        """多智能体协商 - 评估和协调冲突"""
        self.negotiation_count += 1
        proposals_text = "\n".join([
            f"- {p.get('agent_name','?')}({p.get('role','?')}): 动作={p.get('action','?')}, "
            f"理由={p.get('reasoning','?')}, 信心={p.get('confidence',0.5):.1%}"
            for p in request.proposals
        ])
        prompt = NEGOTIATION_PROMPT.format(proposals=proposals_text)

        if self.llm.available:
            result = self.llm.chat("你是协商调解专家。", prompt, temperature=0.3, max_tokens=600)
            if result:
                return self._parse_negotiation(result)

        # Rule-based negotiation fallback
        return self._rule_negotiate(request.proposals)

    def _parse_negotiation(self, text: str) -> NegotiationResponse:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n"); cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        s = cleaned.find("{"); e = cleaned.rfind("}")
        if s >= 0 and e > s: cleaned = cleaned[s:e+1]
        try:
            data = json.loads(cleaned)
            return NegotiationResponse(
                conflicts=data.get("conflicts", []),
                resolutions=data.get("resolutions", []),
                recommendation=data.get("recommendation", "维持各方案"),
                reasoning=data.get("reasoning", ""))
        except json.JSONDecodeError:
            return NegotiationResponse(conflicts=[], resolutions=[],
                                       recommendation="维持各方案", reasoning=f"解析失败: {text[:100]}")

    def _rule_negotiate(self, proposals: List[Dict]) -> NegotiationResponse:
        conflicts = []
        resolutions = []
        actions = [p.get("action", "") for p in proposals]
        # 检查价格战冲突
        if "price_war" in actions and "expand" in actions:
            conflicts.append("企业扩张与竞品价格战冲突")
            resolutions.append("建议企业暂缓扩张，优先应对价格竞争")
        # 检查消费者减少消费与企业扩张冲突
        if "reduce_consumption" in actions and "expand" in actions:
            conflicts.append("消费减少与扩张冲突")
            resolutions.append("需求萎缩时不宜扩张，建议保守")
        # 检查政策收紧与企业创新冲突
        if "tighten" in actions and "innovate" in actions:
            conflicts.append("政策收紧不利于创新投入")
            resolutions.append("等待政策宽松再创新")
        if not conflicts:
            conflicts = ["无明显冲突"]
            resolutions = ["各方案可并行执行"]
        return NegotiationResponse(conflicts=conflicts, resolutions=resolutions,
                                   recommendation="按各智能体策略执行" if not conflicts or conflicts == ["无明显冲突"] else "优先解决冲突",
                                   reasoning="规则引擎协商分析")

    def nl_create_simulation(self, request: NLCreateRequest) -> NLCreateResponse:
        """自然语言创建仿真配置"""
        if self.llm.available:
            prompt = NL_CREATE_PROMPT.format(user_input=request.user_input)
            result = self.llm.chat("你是仿真配置解析专家。", prompt, temperature=0.3, max_tokens=800)
            if result:
                config = self._parse_nl_config(result)
                if config:
                    return NLCreateResponse(config=config, parsed=True,
                                            message=f"已解析仿真: {config.get('name', '未命名')}")
        # Rule-based fallback
        return self._rule_nl_create(request.user_input)

    def _parse_nl_config(self, text: str) -> Optional[Dict]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n"); cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        s = cleaned.find("{"); e = cleaned.rfind("}")
        if s >= 0 and e > s: cleaned = cleaned[s:e+1]
        try:
            return json.loads(cleaned)
        except: return None

    def _rule_nl_create(self, text: str) -> NLCreateResponse:
        """规则解析自然语言"""
        config = {
            "name": "自然语言仿真",
            "max_steps": 50,
            "agents": [
                {"role": "enterprise", "name": "核心企业A", "capital": 10000000, "strategy": "growth"},
                {"role": "competitor", "name": "竞争企业B", "capital": 8000000, "strategy": "aggressive"},
                {"role": "consumer", "name": "消费者群体", "capital": 500000, "strategy": "balanced"},
                {"role": "policy", "name": "政策制定者", "capital": 0, "strategy": "balanced"},
            ],
            "initial_state": {
                "market_price": {"product_a": 100, "product_b": 80, "raw_material": 50},
                "policy": {"tax_rate": 0.13, "subsidy": 0, "interest_rate": 0.035}
            }
        }
        # 简单关键词匹配
        if "竞争" in text or "价格战" in text:
            config["name"] = "竞争仿真"
            config["agents"][0]["strategy"] = "aggressive"
            config["agents"][1]["strategy"] = "aggressive"
        if "创新" in text:
            config["name"] = "创新驱动仿真"
            config["agents"][0]["strategy"] = "innovation"
        if "危机" in text or "衰退" in text:
            config["name"] = "危机应对仿真"
            config["initial_state"]["policy"]["interest_rate"] = 0.05
        if "长期" in text:
            config["max_steps"] = 100
        if "短期" in text or "快速" in text:
            config["max_steps"] = 20
        # 提取数字作为资本
        capital_match = re.search(r'资本[约为]?(\d+)[万]?', text)
        if capital_match:
            cap = int(capital_match.group(1))
            if cap < 100: cap *= 10000  # 万
            config["agents"][0]["capital"] = cap
        return NLCreateResponse(config=config, parsed=True,
                                message=f"规则解析仿真: {config['name']}")

    def _parse_decision(self, text: str, role: str, world: Dict) -> DecisionResponse:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n"); cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        
        # 尝试提取 JSON - 优先找包含 action 的 JSON 块
        import re
        # 1. 直接找 {"action":...} 格式
        json_match = re.search(r'\{[^{}]*"action"\s*:\s*"[^"]+?"[^{}]*\}', cleaned, re.DOTALL)
        if not json_match:
            # 2. 找嵌套一层的 JSON
            json_match = re.search(r'\{[^{}]*"action"\s*:\s*"[^"]+?"[^{}]*\{[^{}]*\}[^{}]*\}', cleaned, re.DOTALL)
        if not json_match:
            # 3. 兜底：找第一个 { 到最后一个 }
            start = cleaned.find("{"); end = cleaned.rfind("}")
            if start >= 0 and end > start:
                json_match = type('Match', (), {'group': lambda self, n=0: cleaned[start:end+1]})()
        
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                action = data.get("action", "hold")
                # 验证 action 是否在合法列表中
                valid_actions = {
                    "enterprise": ["expand", "cut_cost", "innovate", "price_adjust", "hold"],
                    "competitor": ["price_war", "differentiate", "hold", "expand", "innovate"],
                    "consumer": ["buy", "buy_more", "reduce_consumption", "substitute"],
                    "policy": ["subsidy", "tax_relief", "tighten", "stimulate", "observe"],
                }
                if action not in valid_actions.get(role, []):
                    # 从 reasoning 中尝试提取合法 action
                    for va in valid_actions.get(role, []):
                        if va in text.lower():
                            action = va; break
                    else:
                        action = "hold"
                return DecisionResponse(action=action, params=data.get("params", {}),
                                        reasoning=data.get("reasoning", ""), confidence=data.get("confidence", 0.5))
            except json.JSONDecodeError:
                pass
        
        # 最后尝试：从文本中直接提取合法 action 关键词
        valid_actions = {
            "enterprise": ["expand", "cut_cost", "innovate", "price_adjust", "hold"],
            "competitor": ["price_war", "differentiate", "hold", "expand", "innovate"],
            "consumer": ["buy", "buy_more", "reduce_consumption", "substitute"],
            "policy": ["subsidy", "tax_relief", "tighten", "stimulate", "observe"],
        }
        for action in valid_actions.get(role, []):
            if action in text.lower():
                return DecisionResponse(action=action, reasoning=f"从LLM推理中提取", confidence=0.4)
        
        return DecisionResponse(action="hold", reasoning=f"解析失败: {text[:80]}", confidence=0.3)

    def _rule_decision(self, role: str, agent: Dict, world: Dict) -> DecisionResponse:
        state = agent.get("state", {}); capital = agent.get("capital", 0)
        price_a = world.get("market_price", {}).get("product_a", 100)
        price_b = world.get("market_price", {}).get("product_b", 80)
        supply_a = world.get("supply", {}).get("product_a", 1000)
        demand_a = world.get("demand", {}).get("product_a", 900)
        sd_ratio = demand_a / max(supply_a, 0.01)

        if role == "enterprise":
            pm = state.get("profit_margin", 0.15)
            if capital > 8e6 and sd_ratio > 1.1: return DecisionResponse(action="expand", params={"investment": capital*0.2}, reasoning="资本充足且需求旺盛", confidence=0.6, source="rule")
            elif pm < 0.1: return DecisionResponse(action="cut_cost", params={"reduction": 0.15}, reasoning="利润率低", confidence=0.55, source="rule")
            elif capital > 5e6 and pm > 0.2: return DecisionResponse(action="innovate", params={"rd_investment": capital*0.1}, reasoning="利润率高，投入研发", confidence=0.5, source="rule")
            else: return DecisionResponse(action="hold", reasoning="维持观察", confidence=0.5, source="rule")
        elif role == "competitor":
            if price_a > price_b * 1.2: return DecisionResponse(action="price_war", params={"discount": 0.08}, reasoning="对手价格高", confidence=0.55, source="rule")
            elif capital > 6e6: return DecisionResponse(action="differentiate", params={"strategy": "quality"}, reasoning="差异化竞争", confidence=0.5, source="rule")
            else: return DecisionResponse(action="hold", reasoning="观察对手", confidence=0.5, source="rule")
        elif role == "consumer":
            sat = state.get("satisfaction", 0.5)
            if price_a < 80: return DecisionResponse(action="buy_more", params={"quantity": 200}, reasoning="价格低", confidence=0.55, source="rule")
            elif price_a > 120 or sat < 0.3: return DecisionResponse(action="reduce_consumption", params={"reduction": 0.3}, reasoning="价格高或满意度低", confidence=0.55, source="rule")
            elif sat > 0.6: return DecisionResponse(action="buy", params={"quantity": 100}, reasoning="满意度高", confidence=0.5, source="rule")
            else: return DecisionResponse(action="substitute", params={"target": "product_b"}, reasoning="寻求替代品", confidence=0.45, source="rule")
        elif role == "policy":
            if sd_ratio > 1.3: return DecisionResponse(action="tax_relief", params={"reduction": 0.02}, reasoning="供给过剩", confidence=0.7, source="rule")
            elif sd_ratio < 0.8: return DecisionResponse(action="subsidy", params={"amount": 500000}, reasoning="供给不足", confidence=0.7, source="rule")
            elif price_a/100 > 1.3: return DecisionResponse(action="tighten", params={"rate_increase": 0.005}, reasoning="通胀压力", confidence=0.65, source="rule")
            else: return DecisionResponse(action="observe", reasoning="市场均衡", confidence=0.7, source="rule")
        return DecisionResponse(action="hold", reasoning="未知角色", confidence=0.3, source="rule")

    def distill(self, request: DistillRequest) -> DistillResponse:
        log = request.simulation_log
        if not log: return DistillResponse(task_id=request.task_id, report="无数据")
        if self.llm.available:
            sample = log if len(log) <= 20 else log[:10] + log[-10:]
            log_text = json.dumps(sample, ensure_ascii=False, indent=2)
            # 获取跨仿真记忆
            memories = self.cross_memory.recall(tag="distill", limit=3)
            memory_text = "; ".join([m.get("lesson", "") for m in memories]) if memories else "无"
            system = """你是企业经营仿真蒸馏分析专家。分析仿真日志，识别因果，给出建议。
结合历史经验提供更精准的分析。
输出: {"report":"报告","causal_analysis":[],"recommendations":[],"metrics":{}}"""
            user = f"任务{request.task_id}，{len(log)}步，历史经验: {memory_text}\n日志:\n{log_text[:3000]}\n输出JSON:"
            result = self.llm.chat(system, user, temperature=0.3, max_tokens=2000)
            if result:
                resp = self._parse_distill(result, request)
                # 记录经验
                self.cross_memory.record(request.task_id, resp.report[:200], resp.metrics, "distill")
                return resp
        return self._rule_distill(request)

    def _parse_distill(self, text: str, request: DistillRequest) -> DistillResponse:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n"); cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        s = cleaned.find("{"); e = cleaned.rfind("}")
        if s >= 0 and e > s: cleaned = cleaned[s:e+1]
        try:
            data = json.loads(cleaned)
            return DistillResponse(task_id=request.task_id, report=data.get("report", text),
                                   causal_analysis=data.get("causal_analysis", []),
                                   recommendations=data.get("recommendations", []),
                                   metrics=data.get("metrics", {}))
        except json.JSONDecodeError:
            return DistillResponse(task_id=request.task_id, report=text, recommendations=["详见报告"])

    def _rule_distill(self, request: DistillRequest) -> DistillResponse:
        log = request.simulation_log; n = len(log)
        prices_a = [s.get("market_price", {}).get("product_a", 0) for s in log]
        supplies_a = [s.get("supply", {}).get("product_a", 0) for s in log]
        demands_a = [s.get("demand", {}).get("product_a", 0) for s in log]
        avg_p = sum(prices_a)/max(n,1); min_p = min(prices_a) if prices_a else 0; max_p = max(prices_a) if prices_a else 0
        vol = (max_p - min_p)/max(avg_p, 0.01)
        trend = "上涨" if len(prices_a) >= 5 and sum(prices_a[-5:])/5 > sum(prices_a[:5])/5 else "下跌" if len(prices_a) >= 5 else "稳定"
        causal = [{"step": s.get("step",i), "event": e.get("name",""), "type": e.get("type",""), "impact": e.get("impact",{})}
                  for i, s in enumerate(log) for e in s.get("events", [])]
        recs = []
        if avg_p > 120: recs.append("价格偏高，关注竞争压力")
        if vol > 0.3: recs.append("波动剧烈，建立风险对冲")
        if trend == "下跌": recs.append("价格下跌，优化成本")
        recs.extend(["监控供需平衡", "优化智能体策略"])
        stab = max(0.3, 1.0 - vol); eff = min(1.0, sum(demands_a)/max(sum(supplies_a),1))
        report = f"# 蒸馏报告\n\n- 步数: {n}\n- 均价: {avg_p:.2f}\n- 波动: {vol:.1%}\n- 趋势: {trend}\n- 事件: {len(causal)}\n- 效率: {eff:.1%}"
        metrics = {"total_steps": n, "avg_price": round(avg_p,2), "stability_index": round(stab,3),
                   "market_efficiency": round(eff,3), "price_volatility": round(vol,3),
                   "risk_level": "high" if vol > 0.3 else "medium" if vol > 0.15 else "low"}
        # 记录经验
        self.cross_memory.record(request.task_id, f"均价{avg_p:.0f} 波动{vol:.1%} 趋势{trend}", metrics, "distill")
        return DistillResponse(task_id=request.task_id, report=report, causal_analysis=causal[:30],
                               recommendations=recs, metrics=metrics)

    def replay_analysis(self, request: ReplayRequest) -> ReplayResponse:
        history = request.history
        if not history: return ReplayResponse(task_id=request.task_id, summary="无数据", key_moments=[], agent_trajectory={}, lessons=[])
        key_moments = []
        agent_actions: Dict[str, List[str]] = {}
        for i, step in enumerate(history):
            for e in step.get("events", []):
                key_moments.append({"step": step.get("step", i), "type": e.get("type",""), "event": e.get("name",""), "impact": e.get("impact",{})})
            if i > 0:
                prev = history[i-1].get("market_price", {}).get("product_a", 100)
                curr = step.get("market_price", {}).get("product_a", 100)
                if abs(curr - prev)/max(prev, 0.01) > 0.05:
                    key_moments.append({"step": step.get("step", i), "type": "price_shock", "event": f"价格突变: {prev:.1f}→{curr:.1f}"})
            # 记录智能体行为轨迹
            for a in step.get("agents", []):
                aid = a.get("id", "unknown")
                action = a.get("last_action", "hold")
                if aid not in agent_actions: agent_actions[aid] = []
                agent_actions[aid].append(f"Step{step.get('step',i)}: {action}")
        lessons = ["定期复盘，优化决策参数"]
        prices = [s.get("market_price", {}).get("product_a", 100) for s in history]
        if prices and max(prices)/max(min(prices), 0.01) > 1.5: lessons.append("价格波动大，需风险控制")
        if len(key_moments) > len(history) * 0.5: lessons.append("事件频繁，考虑降低事件概率")
        return ReplayResponse(task_id=request.task_id, summary=f"共{len(history)}步，{len(key_moments)}关键时刻",
                              key_moments=key_moments[:50], agent_trajectory=agent_actions, lessons=lessons)

    def rag_search(self, query: RAGQuery) -> List[Dict[str, Any]]:
        return [{"content": f"{query.query}市场增长趋势", "score": 0.92, "source": "行业报告"},
                {"content": f"{query.query}政策积极影响", "score": 0.88, "source": "政策文件"},
                {"content": f"{query.query}竞争加剧", "score": 0.85, "source": "调研"}][:query.top_k]

    def health_check(self) -> Dict[str, Any]:
        alerts = []
        if not self.llm.available: alerts.append({"level": "warning", "message": "LLM不可用"})
        cs = self.local_cache.stats()
        if cs["hit_rate"] > 0 and cs["hit_rate"] < 0.1: alerts.append({"level": "info", "message": f"缓存命中率低({cs['hit_rate']:.1%})"})
        ls = self.llm.stats()
        if ls.get("avg_latency", 0) > 10: alerts.append({"level": "warning", "message": f"LLM延迟高({ls['avg_latency']:.1f}s)"})
        return {"status": "healthy" if not any(a["level"]=="warning" for a in alerts) else "degraded",
                "alerts": alerts, "llm": ls, "cache": cs, "redis": self.redis.stats()}

    def stats(self) -> Dict[str, Any]:
        return {"uptime": time.strftime("%H:%M:%S", time.gmtime(time.time()-self.start_time)),
                "total_decisions": self.decision_count, "llm_decisions": self.llm_decision_count,
                "rule_decisions": self.rule_decision_count, "cache_hits": self.cache_hit_count,
                "negotiation_count": self.negotiation_count,
                "cache_stats": self.local_cache.stats(), "redis_stats": self.redis.stats(),
                "memory_stats": self.cross_memory.stats()}

# ==================== App ====================

VERSION = "1.5.0"

app = FastAPI(title="女娲 AI 智能体服务", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

llm_client = LLMClient(settings.LLM_BASE_URL, settings.LLM_API_KEY, settings.LLM_MODEL, settings.LLM_MAX_RETRIES, settings.LLM_TIMEOUT)
redis_cache = RedisCache(settings.REDIS_URL)
engine = NuwaAgentEngine(llm_client, redis_cache)

@app.get("/api/health")
async def health():
    h = engine.health_check()
    return {"status": h["status"], "service": "女娲 AI 智能体服务", "version": VERSION,
            "components": {"llm_agent": "running" if llm_client.available else "standby",
                           "rag_engine": "ready", "distill_engine": "ready", "cache": "running",
                           "negotiation": "ready", "nl_parser": "ready",
                           "cross_memory": "enabled",
                           "market_predict": "ready", "risk_analyzer": "ready",
                           "trade_advisor": "ready", "dashboard_ai": "ready",
                           "sse_stream": "ready",
                           "redis": "running" if redis_cache.available else "local_only"},
            "stats": engine.stats(), "health": h}

@app.post("/api/agent/decision", response_model=DecisionResponse)
async def get_decision(request: DecisionRequest): return engine.get_decision(request)

@app.post("/api/agent/batch", response_model=BatchDecisionResponse)
async def batch_decision(request: BatchDecisionRequest): return engine.batch_decision(request)

@app.post("/api/agent/negotiate", response_model=NegotiationResponse)
async def negotiate(request: NegotiationRequest): return engine.negotiate(request)

@app.post("/api/simulation/nl-create", response_model=NLCreateResponse)
async def nl_create_simulation(request: NLCreateRequest): return engine.nl_create_simulation(request)

@app.post("/api/distill/analyze", response_model=DistillResponse)
async def distill_analyze(request: DistillRequest): return engine.distill(request)

@app.post("/api/replay/analyze", response_model=ReplayResponse)
async def replay_analyze(request: ReplayRequest): return engine.replay_analysis(request)

@app.post("/api/rag/search")
async def rag_search(query: RAGQuery): return {"results": engine.rag_search(query), "total": len(engine.rag_search(query))}

@app.get("/api/agent/roles")
async def get_roles():
    return {"roles": [
        {"id": "enterprise", "name": "企业经营AI", "description": "经营决策、扩张收缩、创新投入"},
        {"id": "competitor", "name": "竞争对手AI", "description": "价格战、差异化、市场争夺"},
        {"id": "consumer", "name": "消费者群体AI", "description": "消费决策、效用最大化"},
        {"id": "policy", "name": "政策制定者AI", "description": "税收、补贴、货币政策"},
    ]}

@app.get("/api/agent/stats")
async def get_stats(): return {**engine.stats(), "llm_stats": llm_client.stats()}

@app.post("/api/cache/clear")
async def clear_cache():
    engine.local_cache.clear()
    return {"message": "缓存已清除", "stats": engine.local_cache.stats()}

@app.post("/api/memory/record")
async def record_memory(request: MemoryRecordRequest):
    engine.cross_memory.record(request.task_id, request.lesson, request.metrics, request.tag)
    return {"message": "经验已记录", "stats": engine.cross_memory.stats()}

@app.post("/api/memory/recall")
async def recall_memory(request: MemoryRecallRequest):
    results = engine.cross_memory.recall(request.query, request.tag, request.limit)
    return {"results": results, "total": len(results)}

@app.get("/api/memory/stats")
async def memory_stats():
    return engine.cross_memory.stats()

# ==================== v1.5.0: Market Prediction & Risk Analysis ====================

MARKET_PREDICT_PROMPT = """你是企业经营仿真的市场预测AI。
根据历史数据预测未来趋势。

历史价格: {price_history}
当前供需: 供给={supply}, 需求={demand}
政策: 税率={tax_rate}, 利率={interest_rate}
情绪: 贪婪={greed}, 恐惧={fear}, 信心={confidence}

输出JSON:
{{"price_forecast": [价格1, 价格2, 价格3, 价格4, 价格5], "trend": "up/down/flat", "confidence": 0.75, "key_factors": ["因素1", "因素2"], "risk_level": "low/medium/high"}}"""

RISK_ANALYZE_PROMPT = """你是企业经营仿真的风险预警AI。
分析当前市场状况，识别潜在风险。

市场数据: 价格={prices}, 供需比={sd_ratio}, 波动率={volatility}
智能体状态: {agent_states}
近期事件: {recent_events}
情绪指标: 贪婪={greed}, 恐惧={fear}, 波动={vol_score}

输出JSON:
{{"risk_level": "low/medium/high/critical", "risk_categories": [{{"type": "market/credit/operational/liquidity", "severity": 0.8, "description": "描述", "mitigation": "缓解措施"}}], "overall_score": 0.65, "alerts": ["预警1", "预警2"], "recommendations": ["建议1"]}}"""

TRADE_ADVICE_PROMPT = """你是企业经营仿真的交易顾问AI。
根据智能体状态和市场情况，给出交易建议。

卖方: {seller_name} 资本={seller_capital} 策略={seller_strategy}
买方: {buyer_name} 资本={buyer_capital} 策略={buyer_strategy}
商品: {item} 当前市价={market_price}
供需比: {sd_ratio}

输出JSON:
{{"should_trade": true, "suggested_price": 95.5, "suggested_quantity": 100, "seller_benefit": "描述", "buyer_benefit": "描述", "risk_warning": "风险提示"}}"""

DASHBOARD_SUMMARY_PROMPT = """你是企业经营仿真Dashboard的AI摘要生成器。
根据仿真数据生成简短的仪表盘摘要。

总步数: {total_steps}, 活跃智能体: {active_agents}
均价: {avg_price}, 波动: {volatility}, 趋势: {trend}
排行榜首位: {top_agent}, 总交易: {total_trades}
风险等级: {risk_level}, 通知: {notification_count}条

用2-3句话总结仿真状态，指出关键问题和建议。"""

class MarketPredictRequest(BaseModel):
    price_history: List[float] = []
    supply: float = 1000
    demand: float = 900
    tax_rate: float = 0.13
    interest_rate: float = 0.035
    sentiment: Dict[str, float] = {}

class MarketPredictResponse(BaseModel):
    price_forecast: List[float] = []
    trend: str = "flat"
    confidence: float = 0.5
    key_factors: List[str] = []
    risk_level: str = "low"

class RiskAnalyzeRequest(BaseModel):
    prices: List[float] = []
    sd_ratio: float = 1.0
    volatility: float = 0.1
    agent_states: List[Dict[str, Any]] = []
    recent_events: List[str] = []
    sentiment: Dict[str, float] = {}

class RiskAnalyzeResponse(BaseModel):
    risk_level: str = "low"
    risk_categories: List[Dict[str, Any]] = []
    overall_score: float = 0.5
    alerts: List[str] = []
    recommendations: List[str] = []

class TradeAdviceRequest(BaseModel):
    seller_name: str = ""
    seller_capital: float = 0
    seller_strategy: str = ""
    buyer_name: str = ""
    buyer_capital: float = 0
    buyer_strategy: str = ""
    item: str = "product_a"
    market_price: float = 100
    sd_ratio: float = 1.0

class TradeAdviceResponse(BaseModel):
    should_trade: bool = False
    suggested_price: float = 0
    suggested_quantity: int = 0
    seller_benefit: str = ""
    buyer_benefit: str = ""
    risk_warning: str = ""

class DashboardSummaryRequest(BaseModel):
    total_steps: int = 0
    active_agents: int = 0
    avg_price: float = 100
    volatility: float = 0.1
    trend: str = "flat"
    top_agent: str = ""
    total_trades: int = 0
    risk_level: str = "low"
    notification_count: int = 0

# ==================== v1.4.0: Chat Control & Evolution ====================

class ChatControlRequest(BaseModel):
    message: str
    task_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatControlResponse(BaseModel):
    response: str
    action: str
    data: Dict[str, Any]

class EvolutionAnalyzeRequest(BaseModel):
    task_id: str
    agent_id: Optional[str] = None

@app.post("/api/chat/control", response_model=ChatControlResponse)
async def chat_control(request: ChatControlRequest):
    """对话式仿真控制 - 用自然语言控制仿真"""
    msg = request.message.lower()
    action = "info"
    data = {}
    response_text = ""

    if any(w in msg for w in ["开始", "启动", "创建", "新建"]):
        action = "create"
        if "科技" in msg:
            data = {"sector": "tech", "name": "科技行业仿真", "max_steps": 20}
            response_text = "已为您创建科技行业仿真，高波动高增长模式。"
        elif "消费" in msg:
            data = {"sector": "consumer", "name": "消费品行业仿真", "max_steps": 30}
            response_text = "已创建消费品行业仿真，稳定需求低波动模式。"
        elif "金融" in msg:
            data = {"sector": "finance", "name": "金融行业仿真", "max_steps": 25}
            response_text = "已创建金融行业仿真，政策敏感中等波动。"
        else:
            data = {"sector": "default", "name": "标准经营仿真", "max_steps": 20}
            response_text = "已创建标准经营仿真。"
    elif any(w in msg for w in ["推演", "下一步", "继续", "步进"]):
        action = "step"
        nums = re.findall(r'(\d+)\s*步', msg)
        steps = int(nums[0]) if nums else 1
        data = {"steps": steps, "task_id": request.task_id}
        response_text = f"将执行{steps}步推演。"
    elif any(w in msg for w in ["切换", "赛道", "行业"]):
        action = "switch_sector"
        sector_map = {"科技": "tech", "消费": "consumer", "金融": "finance", "能源": "energy", "医疗": "healthcare"}
        for cn, en in sector_map.items():
            if cn in msg:
                data = {"sector_id": en, "task_id": request.task_id}
                response_text = f"已切换到{cn}赛道。"
                break
        if not data:
            response_text = "可选赛道: 科技/消费/金融/能源/医疗"
    elif any(w in msg for w in ["情绪", "市场情绪", "信心"]):
        action = "sentiment"
        data = {"task_id": request.task_id}
        response_text = "正在获取市场情绪数据。"
    elif any(w in msg for w in ["进化", "等级", "经验"]):
        action = "evolution"
        data = {"task_id": request.task_id, "agent_id": request.agent_id}
        response_text = "正在获取智能体进化数据。"
    elif any(w in msg for w in ["报告", "分析", "蒸馏"]):
        action = "distill"
        data = {"task_id": request.task_id}
        response_text = "正在生成蒸馏分析报告。"
    elif any(w in msg for w in ["交易", "买卖", "贸易"]):
        action = "trade"
        data = {"task_id": request.task_id}
        response_text = "正在获取交易建议。"
    elif any(w in msg for w in ["风险", "预警", "危险"]):
        action = "risk"
        data = {"task_id": request.task_id}
        response_text = "正在进行风险预警分析。"
    elif any(w in msg for w in ["预测", "预判", "走势"]):
        action = "predict"
        data = {"task_id": request.task_id}
        response_text = "正在进行市场走势预测。"
    elif any(w in msg for w in ["排行", "排名", "榜单"]):
        action = "leaderboard"
        data = {"task_id": request.task_id}
        response_text = "正在获取排行榜数据。"
    elif any(w in msg for w in ["财务", "收入", "利润"]):
        action = "finance"
        data = {"task_id": request.task_id}
        response_text = "正在获取财务数据。"
    elif any(w in msg for w in ["停止", "暂停", "结束"]):
        action = "stop"
        data = {"task_id": request.task_id}
        response_text = "仿真已暂停。"
    elif any(w in msg for w in ["状态", "概览", "总结"]):
        action = "status"
        data = {"task_id": request.task_id}
        response_text = "正在获取仿真状态概览。"
    else:
        # 通用问答 - 用 LLM 回复
        action = "chat"
        try:
            llm_resp = llm_client.call([
                {"role": "system", "content": "你是女娲AI仿真助手，帮助用户理解企业经营仿真。简短回答，50字以内。"},
                {"role": "user", "content": request.message}
            ], max_tokens=200)
            response_text = llm_resp if llm_resp else "我无法理解您的指令。试试: 创建仿真、推演3步、切换科技赛道、查看情绪。"
        except:
            response_text = "我无法理解您的指令。试试: 创建仿真、推演3步、切换科技赛道、查看情绪。"

    return ChatControlResponse(response=response_text, action=action, data=data)

@app.post("/api/agent/evolution-analyze")
async def evolution_analyze(request: EvolutionAnalyzeRequest):
    """分析智能体进化状态"""
    try:
        # 从 Go 后端获取进化数据
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:9090/api/agent/evolution/{request.task_id}", timeout=10)
            if resp.status_code == 200:
                evo_data = resp.json()
            else:
                evo_data = {"agents": [], "total": 0}
    except:
        evo_data = {"agents": [], "total": 0}

    # 用 LLM 分析进化趋势
    agents_info = []
    for a in evo_data.get("agents", []):
        if request.agent_id and a.get("id") != request.agent_id:
            continue
        agents_info.append(f"{a.get('name','?')}(Lv{a.get('level',1)}) 专精={a.get('specialization','?')} 特质={a.get('traits',{})}")

    if not agents_info:
        return {"analysis": "暂无进化数据", "suggestions": [], "agents": evo_data}

    try:
        analysis = llm_client.call([
            {"role": "system", "content": "分析企业经营仿真的智能体进化状态，给出简短建议。"},
            {"role": "user", "content": f"智能体状态:\n{chr(10).join(agents_info)}\n请分析进化趋势和给出建议。"}
        ], max_tokens=500)
    except:
        analysis = "分析暂时不可用"

    return {"analysis": analysis, "suggestions": ["继续推演积累经验", "调整策略促进进化"], "agents": evo_data}

# ==================== v1.5.0: Market Prediction & Risk APIs ====================

@app.post("/api/market/predict", response_model=MarketPredictResponse)
async def market_predict(request: MarketPredictRequest):
    """市场趋势预测"""
    sentiment = request.sentiment or {}
    if self_llm_available():
        prompt = MARKET_PREDICT_PROMPT.format(
            price_history=request.price_history[-20:],
            supply=request.supply, demand=request.demand,
            tax_rate=request.tax_rate, interest_rate=request.interest_rate,
            greed=sentiment.get("greed", 0.5), fear=sentiment.get("fear", 0.3),
            confidence=sentiment.get("confidence", 0.5))
        result = llm_client.chat("你是市场预测专家。", prompt, temperature=0.3, max_tokens=600)
        if result:
            parsed = _extract_json(result)
            if parsed:
                return MarketPredictResponse(
                    price_forecast=parsed.get("price_forecast", []),
                    trend=parsed.get("trend", "flat"),
                    confidence=parsed.get("confidence", 0.5),
                    key_factors=parsed.get("key_factors", []),
                    risk_level=parsed.get("risk_level", "low"))
    # Rule-based fallback
    prices = request.price_history
    if len(prices) >= 3:
        recent_trend = "up" if prices[-1] > prices[-3] else "down" if prices[-1] < prices[-3] else "flat"
        avg_p = sum(prices[-5:]) / len(prices[-5:])
        forecast = [avg_p * (1 + 0.02 * i * (1 if recent_trend == "up" else -1 if recent_trend == "down" else 0)) for i in range(1, 6)]
    else:
        recent_trend = "flat"
        forecast = [100 + i * 2 for i in range(5)]
    sd_ratio = request.demand / max(request.supply, 0.01)
    risk = "high" if sd_ratio > 1.5 or sd_ratio < 0.5 else "medium" if sd_ratio > 1.2 or sd_ratio < 0.8 else "low"
    return MarketPredictResponse(price_forecast=forecast, trend=recent_trend,
                                  confidence=0.4, key_factors=["供需变化", "政策调整"], risk_level=risk)

@app.post("/api/risk/analyze", response_model=RiskAnalyzeResponse)
async def risk_analyze(request: RiskAnalyzeRequest):
    """AI 风险预警分析"""
    sentiment = request.sentiment or {}
    if self_llm_available():
        agent_summary = "; ".join([f"{a.get('name','?')}资本{a.get('capital',0):.0f}" for a in request.agent_states[:5]])
        prompt = RISK_ANALYZE_PROMPT.format(
            prices=request.prices[-10:], sd_ratio=request.sd_ratio,
            volatility=request.volatility, agent_states=agent_summary,
            recent_events=", ".join(request.recent_events[:5]),
            greed=sentiment.get("greed", 0.5), fear=sentiment.get("fear", 0.3),
            vol_score=sentiment.get("volatility", 0.3))
        result = llm_client.chat("你是风险预警专家。", prompt, temperature=0.3, max_tokens=800)
        if result:
            parsed = _extract_json(result)
            if parsed:
                return RiskAnalyzeResponse(
                    risk_level=parsed.get("risk_level", "medium"),
                    risk_categories=parsed.get("risk_categories", []),
                    overall_score=parsed.get("overall_score", 0.5),
                    alerts=parsed.get("alerts", []),
                    recommendations=parsed.get("recommendations", []))
    # Rule-based fallback
    alerts = []; risk_cats = []; recs = []
    vol = request.volatility
    sd = request.sd_ratio
    if vol > 0.3:
        alerts.append("市场波动剧烈"); risk_cats.append({"type": "market", "severity": min(vol, 1.0), "description": "高波动率", "mitigation": "减少持仓"})
    if sd < 0.7:
        alerts.append("供给严重不足"); risk_cats.append({"type": "operational", "severity": 0.7, "description": "供需失衡", "mitigation": "增加供给"})
    if sd > 1.5:
        alerts.append("需求严重不足"); risk_cats.append({"type": "market", "severity": 0.6, "description": "产能过剩", "mitigation": "缩减产能"})
    if not alerts:
        alerts = ["市场运行正常"]
    level = "critical" if vol > 0.5 else "high" if vol > 0.3 or sd < 0.5 else "medium" if vol > 0.15 else "low"
    recs = ["持续监控"] if level == "low" else ["加强风控", "调整策略"]
    return RiskAnalyzeResponse(risk_level=level, risk_categories=risk_cats,
                                overall_score=min(vol + abs(1-sd)*0.3, 1.0),
                                alerts=alerts, recommendations=recs)

@app.post("/api/trade/advice", response_model=TradeAdviceResponse)
async def trade_advice(request: TradeAdviceRequest):
    """AI 交易建议"""
    if self_llm_available():
        prompt = TRADE_ADVICE_PROMPT.format(
            seller_name=request.seller_name, seller_capital=request.seller_capital,
            seller_strategy=request.seller_strategy,
            buyer_name=request.buyer_name, buyer_capital=request.buyer_capital,
            buyer_strategy=request.buyer_strategy,
            item=request.item, market_price=request.market_price,
            sd_ratio=request.sd_ratio)
        result = llm_client.chat("你是交易顾问。", prompt, temperature=0.4, max_tokens=500)
        if result:
            parsed = _extract_json(result)
            if parsed:
                return TradeAdviceResponse(
                    should_trade=parsed.get("should_trade", False),
                    suggested_price=parsed.get("suggested_price", request.market_price),
                    suggested_quantity=parsed.get("suggested_quantity", 0),
                    seller_benefit=parsed.get("seller_benefit", ""),
                    buyer_benefit=parsed.get("buyer_benefit", ""),
                    risk_warning=parsed.get("risk_warning", ""))
    # Rule-based fallback
    discount = 0.95 if request.sd_ratio > 1.0 else 1.05
    should = request.seller_capital > 1000000 and request.buyer_capital > 500000
    return TradeAdviceResponse(
        should_trade=should,
        suggested_price=round(request.market_price * discount, 2),
        suggested_quantity=50 if should else 0,
        seller_benefit="出清库存回笼资金" if should else "",
        buyer_benefit="低价采购降低成本" if should else "",
        risk_warning="供需不平衡，注意价格波动")

@app.post("/api/dashboard/summary")
async def dashboard_summary(request: DashboardSummaryRequest):
    """Dashboard AI 摘要"""
    if self_llm_available():
        prompt = DASHBOARD_SUMMARY_PROMPT.format(
            total_steps=request.total_steps, active_agents=request.active_agents,
            avg_price=request.avg_price, volatility=request.volatility,
            trend=request.trend, top_agent=request.top_agent,
            total_trades=request.total_trades, risk_level=request.risk_level,
            notification_count=request.notification_count)
        result = llm_client.chat("你是仪表盘摘要生成器。", prompt, temperature=0.5, max_tokens=300)
        if result:
            return {"summary": result.strip(), "generated_by": "llm"}
    # Rule-based fallback
    vol_desc = "剧烈波动" if request.volatility > 0.3 else "温和波动" if request.volatility > 0.1 else "平稳"
    summary = f"仿真已运行{request.total_steps}步，{request.active_agents}个智能体参与。市场{vol_desc}，趋势{request.trend}。"
    if request.risk_level in ("high", "critical"):
        summary += "当前风险较高，建议关注预警信息。"
    return {"summary": summary, "generated_by": "rule"}

# ==================== v1.5.0: SSE Streaming Decision ====================

from fastapi.responses import StreamingResponse

@app.post("/api/agent/decision-stream")
async def decision_stream(request: DecisionRequest):
    """SSE 流式决策 - 实时推送决策过程"""
    agent = request.agent
    world = request.world
    role = agent.get("role", "enterprise")

    def event_generator():
        sse_sep = "\n\n"
        # 1. 发送分析开始
        agent_name = agent.get("name", "智能体")
        msg1 = json.dumps({"phase": "analyzing", "message": f"正在分析{agent_name}的决策上下文..."}, ensure_ascii=False)
        yield f"data: {msg1}{sse_sep}"
        time.sleep(0.1)

        # 2. 发送市场状态
        price_a = world.get("market_price", {}).get("product_a", 100)
        msg2 = json.dumps({"phase": "market", "message": f"当前市场价格: {price_a:.1f}"}, ensure_ascii=False)
        yield f"data: {msg2}{sse_sep}"
        time.sleep(0.1)

        # 3. 获取决策
        decision = engine.get_decision(request)
        msg3 = json.dumps({"phase": "decision", "decision": decision.model_dump()}, ensure_ascii=False)
        yield f"data: {msg3}{sse_sep}"

        # 4. 完成
        msg4 = json.dumps({"phase": "done", "source": decision.source, "latency_ms": decision.latency_ms}, ensure_ascii=False)
        yield f"data: {msg4}{sse_sep}"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ==================== Helper ====================

def self_llm_available() -> bool:
    return llm_client.available

def _extract_json(text: str) -> Optional[Dict]:
    """从 LLM 输出中提取 JSON"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    s = cleaned.find("{"); e = cleaned.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(cleaned[s:e+1])
        except:
            pass
    return None

if __name__ == "__main__":
    logger.info("========================================")
    logger.info(f"  女娲 AI 智能体服务 v{VERSION}")
    logger.info("  MiroFish 企业经营数字孪生系统")
    logger.info("========================================")
    logger.info(f"  LLM: {settings.LLM_MODEL} 可用: {llm_client.available}")
    logger.info(f"  Redis: {'启用' if redis_cache.available else '本地模式'}")
    logger.info(f"  缓存: {settings.CACHE_MAX_SIZE}/{settings.CACHE_TTL}s")
    logger.info(f"  协商: 已就绪")
    logger.info(f"  跨仿真记忆: 已启用")
    logger.info(f"  自然语言建仿真: 已就绪")
    logger.info(f"  市场预测: 已就绪")
    logger.info(f"  风险预警: 已就绪")
    logger.info(f"  交易顾问: 已就绪")
    logger.info(f"  SSE流式决策: 已就绪")
    logger.info(f"  地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("========================================")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
