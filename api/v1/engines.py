from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindiv.config import get_config
from mindiv.providers.registry import resolve_model_and_provider
from mindiv.utils.token_meter import TokenMeter
from mindiv.utils.cache import PrefixCache
from mindiv.engine.deep_think import DeepThinkEngine
from mindiv.engine.ultra_think import UltraThinkEngine

router = APIRouter()


def _compose_bucket_key(template: str, provider_name: str, model_name: str, override: Optional[str]) -> str:
    if override:
        return override
    try:
        return template.format(provider=provider_name, model=model_name)
    except Exception:
        return f"{provider_name}:{model_name}"


class RateLimitConfig(BaseModel):
    qps: Optional[float] = Field(None, description="Tokens per second for token bucket (approx per-call = 1 token)")
    burst: Optional[int] = Field(None, description="Burst capacity (max tokens)")
    timeout: Optional[float] = Field(None, description="Max wait seconds; None means no explicit limit")
    strategy: Optional[str] = Field("wait", description="'wait' to queue, 'fail' to 429-like fail-fast")
    bucket_key: Optional[str] = Field(None, description="Override limiter bucket key; default provider:model")
    window_limit: Optional[int] = Field(None, description="Fixed-window max events per window_seconds")
    window_seconds: Optional[float] = Field(None, description="Fixed window size in seconds")


class DeepThinkRequest(BaseModel):
    model: str = Field(..., description="Configured model id")
    problem: Any
    history: Optional[List[Dict[str, Any]]] = None
    knowledge_context: Optional[str] = None
    max_iterations: int = 20
    required_verifications: int = 3
    enable_planning: bool = False
    enable_parallel_check: bool = False
    llm_params: Dict[str, Any] = {}
    rate_limit: Optional[RateLimitConfig] = None


@router.post("/mindiv/deepthink")
async def deepthink(req: DeepThinkRequest) -> Dict[str, Any]:
    cfg = get_config()
    resolved = resolve_model_and_provider(cfg, req.model)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Unknown model id: {req.model}")
    provider, provider_name, model_name = resolved

    # Get pricing data from config
    pricing_data = cfg.pricing if hasattr(cfg, 'pricing') else {}

    meter = TokenMeter(pricing=pricing_data)
    cache = PrefixCache()

    # Configure global rate limiter (merge request with config defaults)
    rate_limiter = None
    from mindiv.utils.rate_limiter import get_global_rate_limiter
    rl_defaults = getattr(cfg, "rate_limit", None)
    rl_req = req.rate_limit
    # Derive effective values
    qps = rl_req.qps if rl_req and rl_req.qps is not None else getattr(rl_defaults, "qps", None)
    burst = rl_req.burst if rl_req and rl_req.burst is not None else getattr(rl_defaults, "burst", None)
    window_limit = rl_req.window_limit if rl_req and rl_req.window_limit is not None else getattr(rl_defaults, "window_limit", None)
    window_seconds = rl_req.window_seconds if rl_req and rl_req.window_seconds is not None else getattr(rl_defaults, "window_seconds", None)
    timeout = rl_req.timeout if rl_req and rl_req.timeout is not None else getattr(rl_defaults, "timeout", None)
    strategy = (rl_req.strategy if rl_req and rl_req.strategy else getattr(rl_defaults, "strategy", "wait")) or "wait"
    template = getattr(rl_defaults, "bucket_template", "{provider}:{model}") if rl_defaults else "{provider}:{model}"

    if any(v is not None for v in (qps, burst, window_limit, window_seconds)):
        gl = get_global_rate_limiter()
        bucket_key = _compose_bucket_key(template, getattr(provider, "name", ""), model_name, rl_req.bucket_key if rl_req else None)
        if qps is not None and burst is not None:
            await gl.configure_bucket(bucket_key, qps=float(qps), burst=int(burst))
        if window_limit is not None and window_seconds is not None:
            await gl.configure_window(bucket_key, limit=int(window_limit), window_seconds=float(window_seconds))
        rate_limiter = gl

    engine = DeepThinkEngine(
        provider=provider,
        model=model_name,
        problem_statement=req.problem,
        conversation_history=req.history or [],
        knowledge_context=req.knowledge_context,
        max_iterations=req.max_iterations,
        required_successful_verifications=req.required_verifications,
        enable_planning=req.enable_planning,
        enable_parallel_check=req.enable_parallel_check,
        llm_params=req.llm_params,
        token_meter=meter,
        prefix_cache=cache,
        rate_limiter=rate_limiter,
        rate_limit_timeout=(req.rate_limit.timeout if req.rate_limit and req.rate_limit.timeout is not None else getattr(cfg.rate_limit, "timeout", None)),
        rate_limit_strategy=((req.rate_limit.strategy or "wait") if req.rate_limit else getattr(cfg.rate_limit, "strategy", "wait")),
    )

    result = await engine.run()
    summary = meter.summary()

    return {
        "result": result,
        "usage": summary.get("total_usage", {}),
        "cost_usd": summary.get("total_cost_usd", 0.0),
        "detailed_usage": summary.get("by_provider", {}),
    }


class UltraThinkRequest(BaseModel):
    model: str
    problem: Any
    num_agents: int = 4
    parallel_agents: int = 2
    history: Optional[List[Dict[str, Any]]] = None
    knowledge_context: Optional[str] = None
    max_iterations: int = 10
    required_verifications: int = 2
    enable_parallel_check: bool = False
    llm_params: Dict[str, Any] = {}
    rate_limit: Optional[RateLimitConfig] = None


@router.post("/mindiv/ultrathink")
async def ultrathink(req: UltraThinkRequest) -> Dict[str, Any]:
    cfg = get_config()
    resolved = resolve_model_and_provider(cfg, req.model)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Unknown model id: {req.model}")
    provider, provider_name, model_name = resolved

    # Get pricing data from config
    pricing_data = cfg.pricing if hasattr(cfg, 'pricing') else {}

    meter = TokenMeter(pricing=pricing_data)
    cache = PrefixCache()

    # Configure global rate limiter (merge request with config defaults)
    rate_limiter = None
    from mindiv.utils.rate_limiter import get_global_rate_limiter
    rl_defaults = getattr(cfg, "rate_limit", None)
    rl_req = req.rate_limit
    qps = rl_req.qps if rl_req and rl_req.qps is not None else getattr(rl_defaults, "qps", None)
    burst = rl_req.burst if rl_req and rl_req.burst is not None else getattr(rl_defaults, "burst", None)
    window_limit = rl_req.window_limit if rl_req and rl_req.window_limit is not None else getattr(rl_defaults, "window_limit", None)
    window_seconds = rl_req.window_seconds if rl_req and rl_req.window_seconds is not None else getattr(rl_defaults, "window_seconds", None)
    timeout = rl_req.timeout if rl_req and rl_req.timeout is not None else getattr(rl_defaults, "timeout", None)
    strategy = (rl_req.strategy if rl_req and rl_req.strategy else getattr(rl_defaults, "strategy", "wait")) or "wait"
    template = getattr(rl_defaults, "bucket_template", "{provider}:{model}") if rl_defaults else "{provider}:{model}"

    if any(v is not None for v in (qps, burst, window_limit, window_seconds)):
        gl = get_global_rate_limiter()
        bucket_key = _compose_bucket_key(template, getattr(provider, "name", ""), model_name, rl_req.bucket_key if rl_req else None)
        if qps is not None and burst is not None:
            await gl.configure_bucket(bucket_key, qps=float(qps), burst=int(burst))
        if window_limit is not None and window_seconds is not None:
            await gl.configure_window(bucket_key, limit=int(window_limit), window_seconds=float(window_seconds))
        rate_limiter = gl

    engine = UltraThinkEngine(
        provider=provider,
        model=model_name,
        problem_statement=req.problem,
        conversation_history=req.history or [],
        knowledge_context=req.knowledge_context,
        num_agents=req.num_agents,
        max_iterations_per_agent=req.max_iterations,
        required_verifications_per_agent=req.required_verifications,
        llm_params=req.llm_params,
        token_meter=meter,
        prefix_cache=cache,
        parallel_agents=req.parallel_agents,
        enable_parallel_check=req.enable_parallel_check,
        rate_limiter=rate_limiter,
        rate_limit_timeout=(req.rate_limit.timeout if req.rate_limit and req.rate_limit.timeout is not None else getattr(cfg.rate_limit, "timeout", None)),
        rate_limit_strategy=((req.rate_limit.strategy or "wait") if req.rate_limit else getattr(cfg.rate_limit, "strategy", "wait")),
    )

    result = await engine.run()
    summary = meter.summary()

    return {
        "result": result,
        "usage": summary.get("total_usage", {}),
        "cost_usd": summary.get("total_cost_usd", 0.0),
        "detailed_usage": summary.get("by_provider", {}),
    }

