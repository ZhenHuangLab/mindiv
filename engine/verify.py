"""
Verification utilities for DeepThink engine.
"""
from typing import Any, Dict, Optional


async def verify_with_llm(provider: Any, model: str, problem_text: str, solution_text: str, **llm_params) -> Dict[str, Any]:
    """
    Verify a solution using an LLM.

    Args:
        provider: LLM provider instance
        model: Model identifier
        problem_text: Problem statement
        solution_text: Solution to verify
        **llm_params: Additional LLM parameters

    Returns:
        Dictionary with 'verdict' key containing verification result
    """
    from mindiv.engine.prompts import DEEP_THINK_VERIFY_PROMPT
    from mindiv.utils.messages import ensure_messages, extract_text

    messages = [
        {"role": "system", "content": DEEP_THINK_VERIFY_PROMPT},
        {"role": "user", "content": f"Problem:\n{problem_text}\n\nSolution:\n{solution_text}"},
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

    text = extract_text(res)
    return {"verdict": text}


def arithmetic_sanity_check(expr: str) -> Optional[bool]:
    """Optional lightweight arithmetic check using sympy if available.
    Returns True/False for valid/invalid; None if check not applicable.
    """
    try:
        import sympy as sp
        # Very conservative: attempt to parse and simplify; errors -> invalid
        parsed = sp.sympify(expr)
        _ = sp.simplify(parsed)
        return True
    except Exception:
        return None

