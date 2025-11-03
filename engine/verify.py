"""
Verification utilities for DeepThink engine.
"""
import re
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


def arithmetic_sanity_check(solution_text: str) -> Optional[bool]:
    """
    Extract and validate mathematical answers from natural language solutions.

    This function attempts to extract numerical or symbolic answers from
    mathematical solutions that may contain natural language explanations,
    reasoning steps, and final answers. It uses multiple extraction strategies
    and validates the extracted answers using SymPy.

    Extraction strategies (in priority order):
    1. Explicitly marked answers (e.g., "Answer: 42", "Final answer: x=5")
    2. Equation assignments (e.g., "x = 42", "result = 3.14")
    3. Last line numerical values
    4. Mathematical expressions in the text

    Args:
        solution_text: Complete solution text from LLM, may contain natural language

    Returns:
        True: Valid answer extracted and verified
        False: Invalid answer detected (e.g., malformed expression, NaN, infinity)
        None: Unable to extract or verify (check not applicable)

    Examples:
        >>> arithmetic_sanity_check("Let's solve x+5=10. Therefore x=5. Answer: 5")
        True
        >>> arithmetic_sanity_check("The result is x = 42")
        True
        >>> arithmetic_sanity_check("This is a complex proof without clear answer.")
        None
    """
    import re

    try:
        import sympy as sp
    except ImportError:
        # SymPy not available, cannot perform check
        return None

    if not solution_text or not isinstance(solution_text, str):
        return None

    # Strategy 1: Extract explicitly marked answers
    # Patterns: "Answer:", "Final answer:", "Therefore", "Result:", "Solution:", etc.
    answer_patterns = [
        r"(?:final\s+)?answer\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"(?:the\s+)?result\s*(?:is\s+)?[:\-]?\s*(.+?)(?:\n|$)",
        r"(?:the\s+)?solution\s*(?:is\s+)?[:\-]?\s*(.+?)(?:\n|$)",
        r"therefore\s*[,:]?\s*(.+?)(?:\n|$)",
        r"thus\s+(?:we\s+(?:get|have)\s+)?(.+?)(?:\n|$)",
        r"so\s+(?:we\s+(?:get|have)\s+)?(.+?)(?:\n|$)",
    ]

    extracted_candidates = []

    for pattern in answer_patterns:
        matches = re.finditer(pattern, solution_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            candidate = match.group(1).strip()
            if candidate:
                extracted_candidates.append(candidate)

    # Strategy 2: Extract equation assignments (x = value, result = value)
    equation_pattern = r"(?:^|\n)\s*([a-zA-Z_]\w*)\s*=\s*([^\n]+?)(?:\n|$)"
    equation_matches = re.finditer(equation_pattern, solution_text, re.MULTILINE)
    for match in equation_matches:
        value = match.group(2).strip()
        if value:
            extracted_candidates.append(value)

    # Strategy 3: Extract last line if it looks like a numerical answer
    lines = [line.strip() for line in solution_text.split('\n') if line.strip()]
    if lines:
        last_line = lines[-1]
        # Check if last line is primarily numerical/mathematical
        if re.search(r'[\d\+\-\*/\^\(\)\.=]', last_line):
            # Remove common trailing punctuation
            last_line = re.sub(r'[.,;!?]+$', '', last_line)
            extracted_candidates.append(last_line)

    # Strategy 4: Extract standalone mathematical expressions
    # Look for expressions with operators but minimal natural language
    expr_pattern = r'(?:^|\s)([^\s]*[\d\w]+\s*[\+\-\*/\^=]\s*[^\s]+)(?:\s|$)'
    expr_matches = re.finditer(expr_pattern, solution_text)
    for match in expr_matches:
        expr = match.group(1).strip()
        # Filter out expressions with too many letters (likely natural language)
        letter_count = sum(1 for c in expr if c.isalpha())
        if letter_count < len(expr) * 0.5:  # Less than 50% letters
            extracted_candidates.append(expr)

    # Try to validate each candidate
    for candidate in extracted_candidates:
        result = _validate_mathematical_expression(candidate)
        if result is not None:
            return result

    # No valid answer found
    return None


def _validate_mathematical_expression(expr: str) -> Optional[bool]:
    """
    Validate a mathematical expression using SymPy.

    Args:
        expr: Mathematical expression string to validate

    Returns:
        True: Valid and reasonable expression
        False: Invalid or unreasonable (NaN, infinity, etc.)
        None: Cannot parse or validate
    """
    try:
        import sympy as sp
    except ImportError:
        return None

    if not expr or not isinstance(expr, str):
        return None

    # Clean up common formatting
    expr = expr.strip()

    # Handle equations (x = value) - extract the right side
    eq_match = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', expr)
    if eq_match:
        expr = eq_match.group(2).strip()

    # Remove common prefixes/suffixes
    expr = re.sub(r'^(?:is\s+|equals?\s+|=\s*)', '', expr, flags=re.IGNORECASE)
    expr = re.sub(r'[.,;!?]+$', '', expr)

    # Remove currency symbols and commas
    expr = expr.replace('$', '').replace(',', '')

    # Handle common text patterns
    expr = re.sub(r'\s+', ' ', expr).strip()

    # Check for text representations of infinity
    if expr.lower() in ['infinity', 'inf', '-infinity', '-inf']:
        return False

    # Skip if too much natural language
    words = expr.split()
    if len(words) > 10:  # Too many words, likely not a pure answer
        return None

    try:
        # Attempt to parse with SymPy
        parsed = sp.sympify(expr, evaluate=False)

        # Try to evaluate/simplify
        simplified = sp.simplify(parsed)

        # Check for infinity or NaN (both as numbers and symbols)
        if simplified == sp.oo or simplified == -sp.oo or simplified == sp.zoo:
            return False
        if simplified == sp.nan:
            return False

        # Check for problematic values
        if simplified.is_number:
            # Check for NaN, infinity
            if not simplified.is_finite:
                return False

            # Check for complex numbers with imaginary part
            if simplified.is_complex and not simplified.is_real:
                # Complex answers are valid in some contexts
                return True

            return True

        # Symbolic expression (e.g., "x + 1", "sqrt(2)")
        # Valid if it can be simplified without errors
        return True

    except (sp.SympifyError, ValueError, TypeError, AttributeError):
        # Cannot parse or validate
        return None
    except Exception:
        # Unexpected error, treat as unable to validate
        return None

