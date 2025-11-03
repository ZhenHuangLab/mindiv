from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindiv.config import get_config
from mindiv.providers.registry import resolve_model_and_provider

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model ID configured in config.models")
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    extra_body: Optional[Dict[str, Any]] = None


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest) -> Any:
    from fastapi.responses import StreamingResponse
    import json, time, uuid

    cfg = get_config()
    model_id = req.model
    resolved = resolve_model_and_provider(cfg, model_id)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Unknown model id: {model_id}")

    provider, provider_name, model_name = resolved

    if req.stream:
        if not getattr(provider, "capabilities", None) or not provider.capabilities.supports_streaming:
            raise HTTPException(status_code=400, detail=f"Provider {provider_name} does not support streaming")

        async def event_stream():
            stream_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())
            usage_sent = False
            try:
                # Initial role chunk for compatibility
                role_chunk = {
                    "id": stream_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"

                async for chunk in provider.chat_stream(
                    model=model_name,
                    messages=[m.model_dump() for m in req.messages],
                    temperature=req.temperature or 1.0,
                    max_tokens=req.max_tokens,
                    **(req.extra_body or {}),
                ):
                    # Optional usage summary from provider
                    if isinstance(chunk, dict) and "usage" in chunk and isinstance(chunk["usage"], dict):
                        usage_sent = True
                        usage_payload = {
                            "id": stream_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [],
                            "usage": chunk["usage"],
                        }
                        yield f"data: {json.dumps(usage_payload, ensure_ascii=False)}\n\n"
                        continue

                    delta = chunk.get("delta") or ""
                    finish_reason = chunk.get("finish_reason")
                    payload = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": delta} if delta else {},
                            "finish_reason": finish_reason,
                        }],
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except Exception as e:
                # Emit an error event then terminate
                err = {"error": str(e)}
                yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
            finally:
                # End of stream marker
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        out = await provider.chat(
            model=model_name,
            messages=[m.model_dump() for m in req.messages],
            temperature=req.temperature or 1.0,
            max_tokens=req.max_tokens,
            **(req.extra_body or {}),
        )
        return to_openai_chat_completion(model_name, out)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"provider.{provider_name} error: {e}")



# OpenAI-compatible mapping
def to_openai_chat_completion(model_name: str, out: Dict[str, Any]) -> Dict[str, Any]:
    import time, uuid
    content = out.get("content") or ""
    finish_reason = out.get("finish_reason")
    usage_in = out.get("usage") or {}
    prompt_tokens = usage_in.get("input_tokens") or usage_in.get("prompt_tokens") or 0
    completion_tokens = usage_in.get("output_tokens") or usage_in.get("completion_tokens") or 0
    usage_out: Dict[str, Any] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    # Map token details if present
    if isinstance(usage_in.get("input_tokens_details"), dict):
        usage_out["prompt_tokens_details"] = {
            k: usage_in["input_tokens_details"].get(k, 0)
            for k in ("cached_tokens",)
        }
    if isinstance(usage_in.get("output_tokens_details"), dict):
        # OpenAI returns completion_tokens_details with reasoning_tokens for some models
        otd = usage_in["output_tokens_details"]
        usage_out["completion_tokens_details"] = {
            k: otd.get(k, 0) for k in ("reasoning_tokens",)
        }
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage_out,
    }
