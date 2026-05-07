#!/usr/bin/env python3
"""
女娲 AI 智能体服务 v1.2.0
MiroFish 企业经营数字孪生系统 - AI 决策引擎

增强: 批量决策、Redis缓存、仿真复盘、精细Prompt、健康监控
"""

import os, time, json, logging, hashlib
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
                            c = choices[0].get("delta", {}).get("content", "")
                            if c: full_content.append(c)
                    except json.JSONDecodeError: continue
            return "".join(full_content)
        else:
            try:
                data = resp.json()
                choices = data.get("choices", [])
                if choices: return choices[0].get("message", {}).get("content", "")
            except: pass
            return text

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
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

    def stats(self) -> Dict[str, Any]:
        avg_lat = self.total_latency / max(self.call_count, 1)
        return {"available": self.available, "model": self.model, "calls": self.call_count,
                "failures": self.fail_count, "avg_latency": round(avg_lat, 2)}

# ==================== Prompt Templates ====================

ROLE_PROMPTS = {
    "enterprise": {
        "system": """你是企业经营AI决策助手，负责核心企业A的经营战略决策。
决策选项: expand(扩张)/cut_cost(削减)/innovate(创新)/price_adjust(调价)/hold(维持)
输出: {"action":"动作","params":{},"reasoning":"理由","confidence":0.8}""",
        "user": """为【{agent_name}】决策: 资本={capital:.0f} 策略={strategy}
收入={revenue:.0f} 成本={cost:.0f} 利润率={profit_margin:.1%}
市场: 价格A={price_a:.1f} 供需比={sd_ratio:.2f} 税率={tax_rate:.1%}
事件: {events}
输出JSON:""",
    },
    "competitor": {
        "system": """你是竞争企业B的AI决策助手。
决策选项: price_war(价格战)/differentiate(差异化)/hold(维持)/expand(扩张)/innovate(创新)
输出: {"action":"动作","params":{},"reasoning":"理由","confidence":0.7}""",
        "user": """为【{agent_name}】竞争决策: 资本={capital:.0f}
对手价={price_a:.1f} 我方价={price_b:.1f} 价比={price_ratio:.2f}
事件: {events}
输出JSON:""",
    },
    "consumer": {
        "system": """你是消费者群体AI决策助手。
决策选项: buy/buy_more/reduce_consumption/substitute
输出: {"action":"动作","params":{},"reasoning":"理由","confidence":0.6}""",
        "user": """消费决策: 资金={capital:.0f} 价格A={price_a:.1f} B={price_b:.1f}
购买力={purchasing_power:.1f} 满意度={satisfaction:.1%}
事件: {events}
输出JSON:""",
    },
    "policy": {
        "system": """你是政策制定者AI决策助手，负责宏观经济调控。
决策选项: subsidy(补贴)/tax_relief(减税)/tighten(收紧)/stimulate(刺激)/observe(观察)
输出: {"action":"动作","params":{},"reasoning":"理由","confidence":0.85}""",
        "user": """政策决策 (第{step}轮): 通胀={inflation:.2f} 供需比={sd_ratio:.2f}
价格A={price_a:.1f} 信心={market_confidence:.1%}
税率={tax_rate:.1%} 利率={interest_rate:.2%}
事件: {events}
输出JSON:""",
    },
}

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

# ==================== Nuwa Agent Engine ====================

class NuwaAgentEngine:
    def __init__(self, llm_client: LLMClient, redis_cache: RedisCache):
        self.llm = llm_client
        self.redis = redis_cache
        self.local_cache = LRUCache(settings.CACHE_MAX_SIZE, settings.CACHE_TTL)
        self.start_time = time.time()
        self.decision_count = 0
        self.llm_decision_count = 0
        self.rule_decision_count = 0
        self.cache_hit_count = 0

    def _world_hash(self, world: Dict) -> str:
        key_data = json.dumps({"step": world.get("step", 0), "price": world.get("market_price", {})}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

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

        common = {"agent_name": agent.get("name", "Unknown"), "capital": agent.get("capital", 0),
                  "strategy": agent.get("strategy", ""), "step": world.get("step", 0),
                  "price_a": price_a, "price_b": price_b,
                  "supply_a": supply_a, "demand_a": demand_a,
                  "sd_ratio": demand_a / max(supply_a, 0.01),
                  "tax_rate": policy.get("tax_rate", 0.13), "interest_rate": policy.get("interest_rate", 0.035),
                  "subsidy": policy.get("subsidy", 0), "events": events_str}

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
            result = self.llm.chat(system_prompt, user_prompt, temperature=0.7, max_tokens=300)
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

    def _parse_decision(self, text: str, role: str, world: Dict) -> DecisionResponse:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n"); cleaned = "\n".join(lines[1:]) if len(lines) > 2 else cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        start = cleaned.find("{"); end = cleaned.rfind("}")
        if start >= 0 and end > start: cleaned = cleaned[start:end+1]
        try:
            data = json.loads(cleaned)
            return DecisionResponse(action=data.get("action", "hold"), params=data.get("params", {}),
                                    reasoning=data.get("reasoning", ""), confidence=data.get("confidence", 0.5))
        except json.JSONDecodeError:
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
            system = """你是企业经营仿真蒸馏分析专家。分析仿真日志，识别因果，给出建议。
输出: {"report":"报告","causal_analysis":[],"recommendations":[],"metrics":{}}"""
            user = f"任务{request.task_id}，{len(log)}步，日志:\n{log_text[:3000]}\n输出JSON:"
            result = self.llm.chat(system, user, temperature=0.3, max_tokens=2000)
            if result: return self._parse_distill(result, request)
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
        return DistillResponse(task_id=request.task_id, report=report, causal_analysis=causal[:30],
                               recommendations=recs, metrics={"total_steps": n, "avg_price": round(avg_p,2),
                               "stability_index": round(stab,3), "market_efficiency": round(eff,3),
                               "price_volatility": round(vol,3),
                               "risk_level": "high" if vol > 0.3 else "medium" if vol > 0.15 else "low"})

    def replay_analysis(self, request: ReplayRequest) -> ReplayResponse:
        history = request.history
        if not history: return ReplayResponse(task_id=request.task_id, summary="无数据", key_moments=[], agent_trajectory={}, lessons=[])
        key_moments = []
        for i, step in enumerate(history):
            for e in step.get("events", []):
                key_moments.append({"step": step.get("step", i), "type": e.get("type",""), "event": e.get("name",""), "impact": e.get("impact",{})})
            if i > 0:
                prev = history[i-1].get("market_price", {}).get("product_a", 100)
                curr = step.get("market_price", {}).get("product_a", 100)
                if abs(curr - prev)/max(prev, 0.01) > 0.05:
                    key_moments.append({"step": step.get("step", i), "type": "price_shock", "event": f"价格突变: {prev:.1f}→{curr:.1f}"})
        lessons = ["定期复盘，优化决策参数"]
        prices = [s.get("market_price", {}).get("product_a", 100) for s in history]
        if prices and max(prices)/max(min(prices), 0.01) > 1.5: lessons.append("价格波动大，需风险控制")
        return ReplayResponse(task_id=request.task_id, summary=f"共{len(history)}步，{len(key_moments)}关键时刻",
                              key_moments=key_moments[:50], agent_trajectory={}, lessons=lessons)

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
                "cache_stats": self.local_cache.stats(), "redis_stats": self.redis.stats()}

# ==================== App ====================

app = FastAPI(title="女娲 AI 智能体服务", version="1.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

llm_client = LLMClient(settings.LLM_BASE_URL, settings.LLM_API_KEY, settings.LLM_MODEL, settings.LLM_MAX_RETRIES, settings.LLM_TIMEOUT)
redis_cache = RedisCache(settings.REDIS_URL)
engine = NuwaAgentEngine(llm_client, redis_cache)

@app.get("/api/health")
async def health():
    h = engine.health_check()
    return {"status": h["status"], "service": "女娲 AI 智能体服务", "version": "1.2.0",
            "components": {"llm_agent": "running" if llm_client.available else "standby",
                           "rag_engine": "ready", "distill_engine": "ready", "cache": "running",
                           "redis": "running" if redis_cache.available else "local_only"},
            "stats": engine.stats(), "health": h}

@app.post("/api/agent/decision", response_model=DecisionResponse)
async def get_decision(request: DecisionRequest): return engine.get_decision(request)

@app.post("/api/agent/batch", response_model=BatchDecisionResponse)
async def batch_decision(request: BatchDecisionRequest): return engine.batch_decision(request)

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

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  女娲 AI 智能体服务 v1.2.0")
    logger.info("  MiroFish 企业经营数字孪生系统")
    logger.info("========================================")
    logger.info(f"  LLM: {settings.LLM_MODEL} 可用: {llm_client.available}")
    logger.info(f"  Redis: {'启用' if redis_cache.available else '本地模式'}")
    logger.info(f"  缓存: {settings.CACHE_MAX_SIZE}/{settings.CACHE_TTL}s")
    logger.info(f"  地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("========================================")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
