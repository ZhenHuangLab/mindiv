"""
UltraThink: Multi-agent parallel exploration with synthesis.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
import json

from mindiv.providers.base import LLMProvider
from mindiv.engine.prompts import (
    ULTRA_THINK_PLAN_PROMPT,
    GENERATE_AGENT_PROMPTS_PROMPT,
    SYNTHESIZE_RESULTS_PROMPT,
    build_final_summary_prompt,
)
from mindiv.engine.deep_think import DeepThinkEngine
from mindiv.utils.messages import ensure_messages, extract_text
from mindiv.utils.token_meter import TokenMeter
from mindiv.utils.cache import PrefixCache


class UltraThinkEngine:
    """
    Multi-agent parallel exploration engine.
    
    Workflow:
    1. Generate a high-level plan
    2. Create N agent configurations with diverse approaches
    3. Run N DeepThink agents in parallel
    4. Synthesize results into a unified solution
    5. Generate user-facing summary
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        problem_statement: Any,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        knowledge_context: Optional[str] = None,
        num_agents: int = 3,
        max_iterations_per_agent: int = 10,
        required_verifications_per_agent: int = 2,
        model_stages: Optional[Dict[str, str]] = None,
        on_progress: Optional[callable] = None,
        llm_params: Optional[Dict[str, Any]] = None,
        token_meter: Optional[TokenMeter] = None,
        prefix_cache: Optional[PrefixCache] = None,
        parallel_agents: Optional[int] = None,
        enable_parallel_check: bool = False,
        rate_limiter: Optional[Any] = None,
        rate_limit_timeout: Optional[float] = None,
        rate_limit_strategy: str = "wait",
    ) -> None:
        """
        Initialize UltraThink engine.
        
        Args:
            provider: LLM provider
            model: Base model identifier
            problem_statement: Problem to solve
            conversation_history: Optional conversation context
            knowledge_context: Optional knowledge base
            num_agents: Number of parallel agents
            max_iterations_per_agent: Max iterations for each agent
            required_verifications_per_agent: Required verifications per agent
            model_stages: Stage-specific model routing
            on_progress: Progress callback
            llm_params: LLM parameters
            token_meter: Token usage tracker
            prefix_cache: Prefix cache manager
        """
        self.provider = provider
        self.model = model
        self.problem_statement = problem_statement
        self.history = conversation_history or []
        self.knowledge_context = knowledge_context
        self.num_agents = num_agents
        self.max_iterations_per_agent = max_iterations_per_agent
        self.required_verifications_per_agent = required_verifications_per_agent
        self.model_stages = model_stages or {}
        self.on_progress = on_progress
        self.llm_params = llm_params or {}
        self.meter = token_meter or TokenMeter()
        self.cache = prefix_cache or PrefixCache()
        self.parallel_agents = parallel_agents if parallel_agents and parallel_agents > 0 else self.num_agents
        self.enable_parallel_check = enable_parallel_check
        self.rate_limiter = rate_limiter
        self.rate_limit_timeout = rate_limit_timeout
        self.rate_limit_strategy = rate_limit_strategy
    
    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit progress event."""
        if self.on_progress:
            try:
                self.on_progress({"event": event, **payload})
            except Exception:
                pass
    
    def _stage_model(self, stage: str) -> str:
        """Get model for specific stage."""
        return self.model_stages.get(stage, self.model)
    
    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        stage: str = "planning",
    ) -> Dict[str, Any]:
        """Call LLM for planning/synthesis stages."""
        messages = ensure_messages(messages)
        
        res = await self.provider.chat(
            model=self._stage_model(stage),
            messages=messages,
            **self.llm_params,
        )
        
        # Record usage
        usage = res.get("usage") or {}
        self.meter.record(self.provider.name, self._stage_model(stage), usage)
        
        return res
    
    async def _generate_plan(self) -> str:
        """Generate high-level plan for problem decomposition."""
        self._emit("planning", {"phase": "generate_plan"})
        
        messages = [
            {"role": "system", "content": ULTRA_THINK_PLAN_PROMPT},
            {"role": "user", "content": str(self.problem_statement)},
        ]
        
        res = await self._call_llm(messages, stage="planning")
        plan = extract_text(res)
        
        self._emit("plan_generated", {"plan": plan})
        return plan
    
    async def _generate_agent_configs(self, plan: str) -> List[Dict[str, Any]]:
        """Generate agent configurations based on plan."""
        self._emit("planning", {"phase": "generate_agents"})
        
        prompt = GENERATE_AGENT_PROMPTS_PROMPT.format(num_agents=self.num_agents)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Plan:\n{plan}\n\nProblem:\n{self.problem_statement}"},
        ]
        
        res = await self._call_llm(messages, stage="planning")
        config_text = extract_text(res)
        
        # Parse agent configurations
        try:
            # Try to extract JSON array
            configs = json.loads(config_text)
            if not isinstance(configs, list):
                raise ValueError("Expected JSON array")
        except Exception:
            # Fallback: create simple configs
            configs = [
                {
                    "agentId": f"agent-{i+1}",
                    "approach": f"Approach {i+1}",
                    "specificPrompt": f"Solve using method {i+1}",
                }
                for i in range(self.num_agents)
            ]
        
        self._emit("agents_configured", {"num_agents": len(configs)})
        return configs
    
    async def _run_agent(
        self,
        agent_id: str,
        agent_prompt: str,
        agent_model: Optional[str] = None,
        agent_llm_params: Optional[Dict[str, Any]] = None,
        throttle_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run a single DeepThink agent."""
        self._emit("agent_start", {"agent_id": agent_id})
        
        # Augment problem with agent-specific guidance
        augmented_problem = f"{self.problem_statement}\n\n### Agent Guidance ###\n{agent_prompt}"
        
        # Create DeepThink engine for this agent
        model_to_use = agent_model or self.model
        merged_params: Dict[str, Any] = {**self.llm_params, **(agent_llm_params or {})}
        engine = DeepThinkEngine(
            provider=self.provider,
            model=model_to_use,
            problem_statement=augmented_problem,
            conversation_history=self.history,
            knowledge_context=self.knowledge_context,
            max_iterations=self.max_iterations_per_agent,
            required_successful_verifications=self.required_verifications_per_agent,
            model_stages=self.model_stages,
            on_progress=lambda evt: self._emit("agent_progress", {"agent_id": agent_id, **evt}),
            enable_parallel_check=self.enable_parallel_check,
            llm_params=merged_params,
            token_meter=self.meter,
            prefix_cache=self.cache,
            call_throttle_seconds=throttle_seconds,
            rate_limiter=self.rate_limiter,
            rate_limit_timeout=self.rate_limit_timeout,
            rate_limit_strategy=self.rate_limit_strategy,
        )
        
        result = await engine.run()
        
        self._emit("agent_complete", {"agent_id": agent_id})
        return {
            "agent_id": agent_id,
            "result": result,
        }
    
    async def _synthesize_results(
        self,
        agent_results: List[Dict[str, Any]],
    ) -> str:
        """Synthesize multiple agent results into unified solution."""
        self._emit("synthesis", {"phase": "synthesize"})
        
        # Build synthesis prompt with all agent solutions
        solutions_text = "\n\n---\n\n".join([
            f"### {r['agent_id']} ###\n{r['result'].get('final_solution', '')}"
            for r in agent_results
        ])
        
        messages = [
            {"role": "system", "content": SYNTHESIZE_RESULTS_PROMPT},
            {
                "role": "user",
                "content": f"Problem:\n{self.problem_statement}\n\nAgent Solutions:\n{solutions_text}",
            },
        ]
        
        res = await self._call_llm(messages, stage="synthesis")
        synthesis = extract_text(res)
        
        self._emit("synthesis_complete", {})
        return synthesis
    
    async def run(self) -> Dict[str, Any]:
        """
        Run UltraThink workflow.
        
        Returns:
            Result dictionary with synthesis and summary
        """
        # Step 1: Generate plan
        plan = await self._generate_plan()
        
        # Step 2: Generate agent configurations
        agent_configs = await self._generate_agent_configs(plan)
        
        # Step 3: Run agents in parallel
        self._emit("agents_running", {"num_agents": len(agent_configs)})
        
        # Concurrency control
        sem = asyncio.Semaphore(max(1, int(self.parallel_agents)))

        async def _run_with_limit(agent_id: str, agent_prompt: str, agent_model: Optional[str], agent_llm_params: Optional[Dict[str, Any]], throttle_seconds: Optional[float]):
            async with sem:
                return await self._run_agent(
                    agent_id=agent_id,
                    agent_prompt=agent_prompt,
                    agent_model=agent_model,
                    agent_llm_params=agent_llm_params,
                    throttle_seconds=throttle_seconds,
                )

        tasks = []
        for i, config in enumerate(agent_configs):
            agent_id = config.get("agentId", f"agent-{i}")
            agent_prompt = config.get("specificPrompt", "")
            agent_model = config.get("model") or config.get("modelOverride")
            agent_llm_params = config.get("llm_params") or config.get("llmParams")
            # Simple rate limit hook: throttle seconds or derived from qps
            throttle_seconds = None
            qps = None
            try:
                qps = float(config.get("qps")) if config.get("qps") else None
            except Exception:
                qps = None
            if qps and qps > 0:
                throttle_seconds = 1.0 / qps
            if throttle_seconds is None:
                try:
                    ts = config.get("throttleSeconds")
                    if ts is not None:
                        throttle_seconds = float(ts)
                except Exception:
                    throttle_seconds = None
            tasks.append(_run_with_limit(agent_id, agent_prompt, agent_model, agent_llm_params, throttle_seconds))

        agent_results = await asyncio.gather(*tasks)
        
        # Step 4: Synthesize results
        synthesis = await self._synthesize_results(agent_results)
        
        # Step 5: Generate final summary
        self._emit("summary", {"phase": "final"})
        summary_prompt = build_final_summary_prompt(str(self.problem_statement), synthesis)
        summary_res = await self._call_llm(
            [{"role": "user", "content": summary_prompt}],
            stage="summary",
        )
        summary = extract_text(summary_res)
        
        return {
            "mode": "ultra-think",
            "plan": plan,
            "num_agents": len(agent_configs),
            "agent_results": agent_results,
            "synthesis": synthesis,
            "summary": summary,
        }

