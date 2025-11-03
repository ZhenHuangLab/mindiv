from typing import Any, Dict, List, Tuple

"""
Semantic mapping utilities to normalize tool_use/tool_result across providers
into an OpenAI Responses-compatible typed output format.

Target schema examples (subset):
- tool_use:   {"type":"tool_use", "id":"call_abc", "name":"fn", "parameters":{...}}
- tool_result:{"type":"tool_result", "tool_use_id":"call_abc", "content":[{"type":"output_text","text":"..."}], "is_error": False}

This module is intentionally provider-agnostic and best-effort: if a field name
varies across providers, we map common aliases. Unknown fields are preserved in
an optional "details" object to avoid information loss.
"""

_TEXT_LIKE_KEYS = ("text", "output_text", "content", "result", "data", "message")


def _to_output_text_parts(value: Any) -> List[Dict[str, Any]]:
    """Convert arbitrary value into OpenAI typed content parts list.
    Strings -> [{type: output_text, text: value}]
    Dict/List -> wrap as a single JSON block represented as text (non-lossy best-effort)
    Other -> stringified.
    """
    if value is None:
        return []
    if isinstance(value, list):
        # If already typed parts (list of dicts with 'type'), pass through
        if all(isinstance(x, dict) and "type" in x for x in value):
            return value  # assume already normalized
        # Otherwise dump as JSON string
        try:
            import json
            return [{"type": "output_text", "text": json.dumps(value, ensure_ascii=False)}]
        except Exception:
            return [{"type": "output_text", "text": str(value)}]
    if isinstance(value, dict):
        # If it's already a typed part
        if "type" in value and any(k in value for k in ("text", "content")):
            return [value]
        try:
            import json
            return [{"type": "output_text", "text": json.dumps(value, ensure_ascii=False)}]
        except Exception:
            return [{"type": "output_text", "text": str(value)}]
    # Primitive
    return [{"type": "output_text", "text": str(value)}]


def _extract_first_textish(d: Dict[str, Any]) -> Any:
    for k in _TEXT_LIKE_KEYS:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _normalize_tool_use(part: Dict[str, Any]) -> Dict[str, Any]:
    # Common aliases across providers
    pid = part.get("id") or part.get("call_id") or part.get("tool_call_id") or part.get("tool_use_id")
    name = part.get("name") or part.get("tool_name") or (part.get("function") or {}).get("name")
    params = (
        part.get("parameters")
        or part.get("input")
        or part.get("arguments")
        or part.get("args")
        or (part.get("function") or {}).get("arguments")
    )
    norm: Dict[str, Any] = {
        "type": "tool_use",
        "id": pid or None,
        "name": name or "",
        "parameters": params if isinstance(params, (dict, list)) else ({} if params is None else {"value": params}),
    }
    # Preserve unknowns
    extras = {k: v for k, v in part.items() if k not in {"type", "id", "call_id", "tool_call_id", "tool_use_id", "name", "tool_name", "parameters", "input", "arguments", "args", "function"}}
    if extras:
        norm["details"] = extras
    return norm


def _normalize_tool_result(part: Dict[str, Any]) -> Dict[str, Any]:
    ref_id = part.get("tool_use_id") or part.get("call_id") or part.get("tool_call_id") or part.get("id")
    is_error = bool(part.get("is_error", False) or part.get("error", False))
    # Determine content
    content = None
    if "content" in part:
        content = part["content"]
    else:
        # Heuristic: pick first text-like key
        content = _extract_first_textish(part)
    norm: Dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": ref_id or "",
        "content": _to_output_text_parts(content),
    }
    if is_error:
        norm["is_error"] = True
    extras = {k: v for k, v in part.items() if k not in {"type", "tool_use_id", "call_id", "tool_call_id", "id", "content", "is_error", "error"} and k not in _TEXT_LIKE_KEYS}
    if extras:
        norm["details"] = extras
    return norm


def normalize_output_items(provider: str, output: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a provider's response.output list to OpenAI-typed format.
    For items of type 'message', we pass through but normalize inner content parts
    that represent tool_use/tool_result. For top-level tool objects (some providers),
    we normalize to typed tool_use/tool_result items.
    """
    normalized: List[Dict[str, Any]] = []
    for item in output:
        try:
            itype = item.get("type") if isinstance(item, dict) else None
            if itype in ("message", None):
                # Pass-through message, but normalize inner parts
                msg = dict(item) if isinstance(item, dict) else {"type": "message", "role": "assistant", "content": []}
                content = msg.get("content")
                parts: List[Any]
                if isinstance(content, list):
                    parts = content
                elif content is None:
                    parts = []
                else:
                    parts = [content]
                new_parts: List[Dict[str, Any]] = []
                for p in parts:
                    if isinstance(p, dict) and p.get("type") in ("tool_use", "function_call", "function.tool_call"):
                        new_parts.append(_normalize_tool_use(p))
                    elif isinstance(p, dict) and p.get("type") in ("tool_result", "function_result"):
                        new_parts.append(_normalize_tool_result(p))
                    else:
                        # Keep original text parts; coerce to typed if needed
                        if isinstance(p, dict) and "type" in p:
                            new_parts.append(p)
                        else:
                            new_parts.extend(_to_output_text_parts(p))
                msg["content"] = new_parts
                # Ensure role exists
                if not msg.get("role"):
                    msg["role"] = "assistant"
                if not msg.get("type"):
                    msg["type"] = "message"
                normalized.append(msg)
            elif itype in ("tool_use", "function_call", "function.tool_call"):
                normalized.append(_normalize_tool_use(item))
            elif itype in ("tool_result", "function_result"):
                normalized.append(_normalize_tool_result(item))
            else:
                # Unknown item type: pass-through
                normalized.append(item)
        except Exception:
            normalized.append(item)
    return normalized


def collect_output_text(output: List[Dict[str, Any]]) -> str:
    """Aggregate plain text from typed output for convenience output_text."""
    buf: List[str] = []
    for item in output:
        try:
            if item.get("type") == "message":
                for part in item.get("content", []) or []:
                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
                        t = part.get("text")
                        if isinstance(t, str):
                            buf.append(t)
        except Exception:
            continue
    return "".join(buf)

