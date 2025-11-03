"""
Verification utilities for DeepThink engine.
"""
from typing import Any, Dict, Optional


async def verify_with_llm(provider: Any, model: str, problem_text: str, solution_text: str, **llm_params) -> Dict[str, Any]:
    """
    Verify a solution using an LLM with structured outputs.

    Args:
        provider: LLM provider instance
        model: Model identifier
        problem_text: Problem statement
        solution_text: Solution to verify
        **llm_params: Additional LLM parameters

    Returns:
        Dictionary with structured verification result: {"verdict": "pass|fail|unsure", ...}
    """
    from mindiv.engine.prompts import DEEP_THINK_VERIFY_PROMPT
    from mindiv.utils.messages import ensure_messages, extract_text
    import json
    from typing import Any as _Any, Dict as _Dict, Optional as _Optional

    ALLOWED_VERDICTS = {"pass", "fail", "unsure"}

    def _build_response_format() -> _Dict[str, _Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "verification_result",
                "schema": {
                    "type": "object",
                    "properties": {
                        "verdict": {"type": "string", "enum": ["pass", "fail", "unsure"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                        "issues": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["verdict"],
                    "additionalProperties": False,
                },
            },
        }

    def _validate(obj: _Any) -> _Dict[str, _Any]:
        if not isinstance(obj, dict):
            raise ValueError("verification result is not an object")
        verdict = str(obj.get("verdict", "")).strip().lower()
        if verdict not in ALLOWED_VERDICTS:
            raise ValueError("invalid verdict")
        out: _Dict[str, _Any] = {"verdict": verdict}
        conf = obj.get("confidence", None)
        try:
            if conf is not None:
                conf_f = float(conf)
                if 0.0 <= conf_f <= 1.0:
                    out["confidence"] = conf_f
        except Exception:
            pass
        reasons = obj.get("reasons", None)
        if isinstance(reasons, list):
            out["reasons"] = [str(x) for x in reasons if isinstance(x, (str, int, float))]
        issues = obj.get("issues", None)
        if isinstance(issues, list):
            out["issues"] = [str(x) for x in issues if isinstance(x, (str, int, float))]
        return out

    # Build messages
    base_messages = [
        {"role": "system", "content": DEEP_THINK_VERIFY_PROMPT},
        {"role": "user", "content": f"Problem:\n{problem_text}\n\nSolution:\n{solution_text}"},
    ]
    base_messages = ensure_messages(base_messages)

    parsed: _Optional[_Dict[str, _Any]] = None

    # Prefer Responses API with JSON schema
    if provider.capabilities.supports_responses:
        params = {
            "model": model,
            "input_messages": base_messages,
            "response_format": _build_response_format(),
        }
        params.update(llm_params)
        res = await provider.response(**params)
        candidate = res.get("output_parsed")
        if candidate is None:
            try:
                candidate = json.loads(extract_text(res))
            except Exception:
                candidate = None
        if candidate is not None:
            try:
                parsed = _validate(candidate)
            except Exception:
                parsed = None
    else:
        # Fallback for providers without Responses API: JSON-only strict output
        json_guard = (
            "Return ONLY a single-line minified JSON object matching the schema: "
            '{"verdict":"pass|fail|unsure","confidence":0.0,"reasons":[],"issues":[]}. '
            "No extra text or explanation."
        )
        messages = ensure_messages([
            {"role": "system", "content": DEEP_THINK_VERIFY_PROMPT},
            {"role": "user", "content": f"Problem:\n{problem_text}\n\nSolution:\n{solution_text}\n\n{json_guard}"},
        ])
        chat_params = {"model": model, "messages": messages}
        chat_params.update(llm_params)
        res = await provider.chat(**chat_params)
        try:
            candidate = json.loads(extract_text(res))
            parsed = _validate(candidate)
        except Exception:
            parsed = None

    if parsed is None:
        # Fail-fast on unparseable outputs
        return {"verdict": "fail", "error": "verification_output_unparseable"}

    return parsed


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

