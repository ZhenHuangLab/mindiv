"""
Anthropic Claude provider adapter.
Supports messages API with streaming and prompt caching.
"""
from typing import Dict, Any, List, Optional, AsyncIterator
import anthropic
from anthropic import AsyncAnthropic
from .base import LLMProvider, ProviderCapabilities
from .exceptions import (
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderServerError,
)
from ..config import ProviderConfig


class AnthropicProvider:
    """Anthropic Claude provider adapter."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.
        
        Args:
            config: Provider configuration
        """
        self._config = config
        self._client = AsyncAnthropic(
            base_url=config.base_url if config.base_url else None,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self._capabilities = ProviderCapabilities(
            supports_responses=False,
            supports_streaming=config.supports_streaming,
            supports_vision=True,
            supports_thinking=True,
            supports_caching=True,
        )
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities."""
        return self._capabilities
    
    def _convert_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert OpenAI-style messages to Anthropic format.
        
        Returns:
            (system, messages)
        """
        system = None
        converted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Anthropic uses separate system parameter
                system = content if isinstance(content, str) else str(content)
            elif role in ("user", "assistant"):
                converted.append({
                    "role": role,
                    "content": content if isinstance(content, str) else str(content),
                })
        
        return system, converted
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Send chat request to Anthropic.
        
        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream (not supported in this method)
            **kwargs: Additional parameters
        
        Returns:
            Response dictionary with 'content' and 'usage'
        """
        if stream:
            raise ValueError("Use chat_stream() for streaming requests")
        
        system, converted_messages = self._convert_messages(messages)
        
        params = {
            "model": model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        
        if system:
            params["system"] = system
        
        params.update(kwargs)

        try:
            response = await self._client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
        except anthropic.BadRequestError as e:
            raise ProviderInvalidRequestError(self.name, f"Invalid request: {str(e)}", e)
        except anthropic.NotFoundError as e:
            raise ProviderNotFoundError(self.name, f"Model not found: {str(e)}", e)
        except anthropic.InternalServerError as e:
            raise ProviderServerError(self.name, f"Server error: {str(e)}", e, status_code=500)
        except anthropic.APIError as e:
            raise ProviderError(self.name, f"API error: {str(e)}", e)
        except Exception as e:
            raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)

        # Extract content and raw typed blocks
        content = ""
        raw_output: List[Dict[str, Any]] = []
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "text" and hasattr(block, "text"):
                text_val = block.text or ""
                content += text_val
                raw_output.append({"type": "text", "text": text_val})
            elif btype == "tool_use":
                raw_output.append({
                    "type": "tool_use",
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", ""),
                    "parameters": getattr(block, "input", {}) or {},
                })
            elif btype == "tool_result":
                raw_output.append({
                    "type": "tool_result",
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "content": [{"type": "output_text", "text": getattr(block, "content", "") or ""}],
                })

        # Extract usage
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0),
            "output_tokens": getattr(response.usage, "output_tokens", 0),
        }

        # Add cached tokens if available (Anthropic prompt caching)
        if hasattr(response.usage, "cache_read_input_tokens"):
            usage["input_tokens_details"] = {
                "cached_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
            }

        return {
            "content": content,
            "usage": usage,
            "finish_reason": response.stop_reason or "stop",
            "raw_output": raw_output,
            "provider": self.name,
        }
    
    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send streaming chat request to Anthropic.
        
        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Yields:
            Response chunks with 'delta'
        """
        system, converted_messages = self._convert_messages(messages)
        
        params = {
            "model": model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        
        if system:
            params["system"] = system
        
        params.update(kwargs)

        try:
            stream_context = self._client.messages.stream(**params)
        except anthropic.AuthenticationError as e:
            raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
        except anthropic.BadRequestError as e:
            raise ProviderInvalidRequestError(self.name, f"Invalid request: {str(e)}", e)
        except anthropic.NotFoundError as e:
            raise ProviderNotFoundError(self.name, f"Model not found: {str(e)}", e)
        except anthropic.InternalServerError as e:
            raise ProviderServerError(self.name, f"Server error: {str(e)}", e, status_code=500)
        except anthropic.APIError as e:
            raise ProviderError(self.name, f"API error: {str(e)}", e)
        except Exception as e:
            raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)

        async with stream_context as stream:
            async for event in stream:
                if hasattr(event, "delta") and hasattr(event.delta, "text"):
                    yield {
                        "delta": event.delta.text,
                        "finish_reason": None,
                    }
                elif hasattr(event, "type") and event.type == "message_stop":
                    # Emit finish chunk
                    yield {
                        "delta": "",
                        "finish_reason": "stop",
                    }
                    # Try to emit usage summary if available
                    msg = getattr(event, "message", None)
                    usage_obj = getattr(msg, "usage", None) if msg else None
                    if usage_obj is not None:
                        usage = {
                            "input_tokens": getattr(usage_obj, "input_tokens", 0),
                            "output_tokens": getattr(usage_obj, "output_tokens", 0),
                        }
                        if hasattr(usage_obj, "cache_read_input_tokens"):
                            usage["input_tokens_details"] = {"cached_tokens": getattr(usage_obj, "cache_read_input_tokens", 0)}
                        yield {"usage": usage}
    
    async def response(
        self,
        model: str,
        input_messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        previous_response_id: Optional[str] = None,
        store: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Anthropic does not support responses API."""
        raise NotImplementedError("Anthropic does not support responses API")
    
    async def close(self) -> None:
        """Close the client."""
        await self._client.close()

