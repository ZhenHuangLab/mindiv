"""
Planning utilities for UltraThink engine.
"""
from typing import Any
from mindiv.utils.messages import ensure_messages, extract_text


async def generate_plan(provider: Any, model: str, problem: Any, **llm_params) -> str:
    """
    Generate a high-level plan for solving the problem.

    Args:
        provider: LLM provider instance
        model: Model identifier
        problem: Problem statement
        **llm_params: Additional LLM parameters

    Returns:
        Generated plan as string
    """
    from mindiv.engine.prompts import ULTRA_THINK_PLAN_PROMPT

    messages = [
        {"role": "system", "content": ULTRA_THINK_PLAN_PROMPT},
        {"role": "user", "content": str(problem)},
    ]
    messages = ensure_messages(messages)

    if provider.capabilities.supports_responses:
        res = await provider.response(
            model=model,
            input_messages=messages,
            **llm_params,
        )
    else:
        res = await provider.chat(
            model=model,
            messages=messages,
            **llm_params,
        )

    return extract_text(res)

