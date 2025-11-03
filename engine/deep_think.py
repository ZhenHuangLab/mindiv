from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio

from mindiv.providers.base import LLMProvider
from mindiv.engine.prompts import (
    DEEP_THINK_INITIAL_PROMPT,
    DEEP_THINK_VERIFY_PROMPT,
    DEEP_THINK_CORRECT_PROMPT,
    build_final_summary_prompt,
)
from mindiv.engine.verify import verify_with_llm, arithmetic_sanity_check
from mindiv.utils.messages import ensure_messages, extract_text
from mindiv.utils.token_meter import TokenMeter
from mindiv.utils.cache import PrefixCache


class DeepThinkEngine:
    """Single-agent iterative solver with verification and correction.
    - Stage-aware routing can be added via caller by switching model.
    - Uses provider-side prefix caching when supported (Responses API).
    """

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        problem_statement: Any,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        knowledge_context: Optional[str] = None,
        max_iterations: int = 20,
        required_successful_verifications: int = 3,
        max_errors_before_give_up: int = 10,
        model_stages: Optional[Dict[str, str]] = None,
        on_progress: Optional[callable] = None,
        enable_planning: bool = False,
        enable_parallel_check: bool = False,
        llm_params: Optional[Dict[str, Any]] = None,
        token_meter: Optional[TokenMeter] = None,
        prefix_cache: Optional[PrefixCache] = None,
        call_throttle_seconds: Optional[float] = None,
        rate_limiter: Optional[Any] = None,
        rate_limit_timeout: Optional[float] = None,
        rate_limit_strategy: str = "wait",
    ) -> None:
        self.provider = provider
        self.model = model
        self.problem_statement = problem_statement
        self.history = conversation_history or []
        self.knowledge_context = knowledge_context
        self.max_iterations = max_iterations
        self.required_successes = required_successful_verifications
        self.max_errors = max_errors_before_give_up
        self.model_stages = model_stages or {}
        self.on_progress = on_progress
        self.enable_planning = enable_planning
        self.enable_parallel_check = enable_parallel_check
        self.llm_params = llm_params or {}
        self.meter = token_meter or TokenMeter()
        self.cache = prefix_cache or PrefixCache()
        self.call_throttle_seconds = call_throttle_seconds
        self.rate_limiter = rate_limiter
        self.rate_limit_timeout = rate_limit_timeout
        self.rate_limit_strategy = rate_limit_strategy

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if self.on_progress:
            try:
                self.on_progress({"event": event, **payload})
            except Exception:
                pass

    async def _call_llm(self, messages: List[Dict[str, Any]], *, store: bool = True, previous_response_id: Optional[str] = None, stage: str = "initial") -> Dict[str, Any]:
        """Call provider; prefer Responses when available for prefix caching.
        Includes optional throttle/rate-limiter hooks for per-agent control.
        """
        # Optional rate-limit hooks (global limiter preferred)
        if self.rate_limiter:
            try:
                # If rate_limiter is a GlobalRateLimiter-like object, use key-based acquire
                acquire = getattr(self.rate_limiter, "acquire", None)
                if callable(acquire):
                    # Use provider+stage model as bucket key by default
                    key = None
                    try:
                        from mindiv.utils.rate_limiter import GlobalRateLimiter  # type: ignore
                        # Compose key as provider:model
                        key = GlobalRateLimiter.make_key(getattr(self.provider, "name", ""), self._stage_model(stage))
                    except Exception:
                        # Fallback simple key
                        key = f"{getattr(self.provider, 'name', '')}:{self._stage_model(stage)}"
                    await acquire(key=key, tokens=1.0, timeout=self.rate_limit_timeout, strategy=self.rate_limit_strategy)
                else:
                    maybe_coro = self.rate_limiter()
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro
            except Exception:
                # Fail-fast philosophy: do not hide limiter errors
                raise
        elif self.call_throttle_seconds and self.call_throttle_seconds > 0:
            await asyncio.sleep(self.call_throttle_seconds)

        if self.provider.capabilities.supports_responses:
            res = await self.provider.response(
                model=self._stage_model(stage),
                input_messages=messages,
                store=store,
                previous_response_id=previous_response_id,
                **self.llm_params,
            )
        else:
            res = await self.provider.chat(
                model=self._stage_model(stage),
                messages=messages,
                **self.llm_params,
            )
        # Record usage if present
        usage = res.get("usage") or {}
        self.meter.record(self.provider.name, self._stage_model(stage), usage)
        return res

    def _stage_model(self, stage: str) -> str:
        return self.model_stages.get(stage, self.model)


    async def _verify_solution(self, problem_text: str, solution_text: str) -> tuple[Dict[str, Any], bool]:
        """Run verification(s) possibly in parallel and return (log_entry, is_good)."""
        if self.enable_parallel_check:
            arith_task = asyncio.to_thread(arithmetic_sanity_check, solution_text)
            llm_task = verify_with_llm(self.provider, self._stage_model("verification"), problem_text, solution_text, **self.llm_params)
            arith_res, v = await asyncio.gather(arith_task, llm_task)
            # Aggregate result: require LLM says yes AND arithmetic not False
            verdict_text = v.get("verdict", "")
            is_good = ("yes" in verdict_text.lower()) and (arith_res is not False)
            v = {**v, "arith": arith_res}
            return v, is_good
        else:
            v = await verify_with_llm(self.provider, self._stage_model("verification"), problem_text, solution_text, **self.llm_params)
            verdict_text = v.get("verdict", "")
            is_good = "yes" in verdict_text.lower()
            return v, is_good

    async def run(self) -> Dict[str, Any]:
        successes = 0
        errors = 0
        solution_text: Optional[str] = None
        verifications: List[Dict[str, Any]] = []

        # Build initial messages with system prompt and optional knowledge
        system = DEEP_THINK_INITIAL_PROMPT + (f"\n\n### Knowledge ###\n{self.knowledge_context}\n" if self.knowledge_context else "")
        messages = [{"role": "system", "content": system}] + self.history + [{"role": "user", "content": self.problem_statement}]
        messages = ensure_messages(messages)

        # Provider-side prefix cache anchor (Responses only)
        cache_key = self.cache.compute_key(
            provider=self.provider.name,
            model=self._stage_model("initial"),
            system=system,
            knowledge=self.knowledge_context or "",
            history=self.history,
            params=self.llm_params,
        )
        prev_id = self.cache.get_response_id(cache_key)

        # Initial exploration
        self._emit("thinking", {"phase": "initial"})
        res = await self._call_llm(messages, store=True, previous_response_id=prev_id, stage="initial")
        response_id = res.get("response_id") or res.get("id")
        if response_id:
            self.cache.set_response_id(cache_key, response_id)
        solution_text = extract_text(res) or ""
        self._emit("solution", {"iteration": 0})

        # First verification (optionally parallel)
        v, is_good = await self._verify_solution(str(self.problem_statement), solution_text)
        verifications.append(v)
        successes += 1 if is_good else 0

        it = 1
        while it < self.max_iterations and successes < self.required_successes and errors < self.max_errors:
            # Correction step guided by verification feedback
            corr_msgs = [
                {"role": "system", "content": DEEP_THINK_CORRECT_PROMPT},
                {"role": "user", "content": f"Problem:\n{self.problem_statement}\n\nPrevious solution:\n{solution_text}\n\nVerifier feedback:\n{v.get('verdict','')}"},
            ]
            corr_msgs = ensure_messages(corr_msgs)
            self._emit("thinking", {"phase": "correction", "iteration": it})
            res2 = await self._call_llm(corr_msgs, store=False, stage="correction")
            new_solution = extract_text(res2) or solution_text
            solution_text = new_solution

            # Verify again (optionally parallel)
            v, is_good = await self._verify_solution(str(self.problem_statement), solution_text)
            verifications.append(v)
            if is_good:
                successes += 1
                errors = 0
            else:
                errors += 1
            it += 1

        summary_prompt = build_final_summary_prompt(str(self.problem_statement), solution_text or "")
        summ_res = await self._call_llm([{"role": "user", "content": summary_prompt}], store=False, stage="summary")
        summary_text = extract_text(summ_res) or ""

        return {
            "mode": "deep-think",
            "iterations": it,
            "successful_verifications": successes,
            "verification_logs": verifications,
            "final_solution": solution_text,
            "summary": summary_text,
        }

