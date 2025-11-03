from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindiv.config import get_config
from mindiv.providers.registry import resolve_model_and_provider
from mindiv.providers.exceptions import (
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderServerError,
)

router = APIRouter()


class ResponseInput(BaseModel):
    # Accept either raw text or structured messages; normalize downstream
    role: Optional[str] = None
    content: Any


class ResponsesRequest(BaseModel):
    model: str
    input: Union[List[ResponseInput], str]
    store: Optional[bool] = True
    previous_response_id: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    extra_body: Optional[Dict[str, Any]] = None


@router.post("/v1/responses")
async def responses(req: ResponsesRequest) -> Dict[str, Any]:
    cfg = get_config()
    resolved = resolve_model_and_provider(cfg, req.model)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Unknown model id: {req.model}")
    provider, provider_name, model_name = resolved

    if not provider.capabilities.supports_responses:
        raise HTTPException(status_code=400, detail=f"Provider {provider_name} does not support Responses API")

    # Normalize input to messages format
    if isinstance(req.input, str):
        input_messages = [{"role": "user", "content": req.input}]
    else:
        input_messages = [{"role": i.role or "user", "content": i.content} for i in req.input]

    try:
        out = await provider.response(
            model=model_name,
            input_messages=input_messages,
            temperature=req.temperature or 1.0,
            max_output_tokens=req.max_output_tokens,
            previous_response_id=req.previous_response_id,
            store=req.store or False,
            **(req.extra_body or {}),
        )
        return to_openai_response(model_name, out)
    except ProviderError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": {
                    "message": e.message,
                    "type": e.error_code,
                    "code": e.error_code,
                    "provider": e.provider,
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "internal_error",
                }
            }
        )



# OpenAI-compatible mapping for Responses API with tool_use/tool_result normalization
def to_openai_response(model_name: str, out: Dict[str, Any]) -> Dict[str, Any]:
    import time, uuid
    from mindiv.utils.tool_mapping import normalize_output_items, collect_output_text

    response_id = out.get("response_id") or f"resp-{uuid.uuid4().hex}"
    usage = out.get("usage") or {}

    # Prefer raw structured output if provider exposed it
    raw_output = out.get("raw_output")
    if isinstance(raw_output, list) and raw_output:
        # Best-effort: detect provider name hint if present
        provider_hint = out.get("provider") or out.get("_provider") or ""
        output = normalize_output_items(str(provider_hint), raw_output)
        content = out.get("content") or collect_output_text(output)
    else:
        # Fallback: synthesize a simple message output
        content = out.get("content") or ""
        output = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
            }
        ]

    resp: Dict[str, Any] = {
        "id": response_id,
        "object": "response",
        "created": int(time.time()),
        "model": model_name,
        "output_text": content,
        "output": output,
        "usage": usage,
    }

    # Include parsed output if present
    if out.get("output_parsed") is not None:
        resp["output_parsed"] = out.get("output_parsed")

    return resp
