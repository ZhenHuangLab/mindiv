"""
OpenAI provider adapter.
Supports both chat completions and responses API with prefix caching.
"""
from typing import Dict, Any, List, Optional, AsyncIterator
import openai
from openai import AsyncOpenAI
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


class OpenAIProvider:
    """OpenAI provider adapter with chat and responses API support."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize OpenAI provider.
        
        Args:
            config: Provider configuration
        """
        self._config = config
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self._capabilities = ProviderCapabilities(
            supports_responses=config.supports_responses,
            supports_streaming=config.supports_streaming,
            supports_vision=True,
            supports_thinking=True,
            supports_caching=True,
        )
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities."""
        return self._capabilities
    
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
        Send chat completion request.

        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream (not supported in this method)
            **kwargs: Additional parameters

        Returns:
            Response dictionary with 'content' and 'usage'

        Raises:
            ProviderAuthError: Authentication failed
            ProviderRateLimitError: Rate limit exceeded
            ProviderTimeoutError: Request timeout
            ProviderInvalidRequestError: Invalid request parameters
            ProviderNotFoundError: Model or resource not found
            ProviderServerError: Server error
            ProviderError: Other provider errors
        """
        if stream:
            raise ValueError("Use chat_stream() for streaming requests")

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        params.update(kwargs)

        try:
            response = await self._client.chat.completions.create(**params)
        except openai.AuthenticationError as e:
            raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
        except openai.RateLimitError as e:
            raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
        except (openai.APITimeoutError, openai.Timeout) as e:
            raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
        except openai.BadRequestError as e:
            raise ProviderInvalidRequestError(self.name, f"Invalid request: {str(e)}", e)
        except openai.NotFoundError as e:
            raise ProviderNotFoundError(self.name, f"Model not found: {str(e)}", e)
        except openai.InternalServerError as e:
            raise ProviderServerError(self.name, f"Server error: {str(e)}", e, status_code=500)
        except openai.APIError as e:
            raise ProviderError(self.name, f"API error: {str(e)}", e)
        except Exception as e:
            raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)

        # Extract content and usage
        content = response.choices[0].message.content or ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        # Add cached tokens if available
        if response.usage and hasattr(response.usage, "prompt_tokens_details"):
            details = response.usage.prompt_tokens_details
            if details and hasattr(details, "cached_tokens"):
                usage["input_tokens_details"] = {
                    "cached_tokens": details.cached_tokens or 0,
                }

        return {
            "content": content,
            "usage": usage,
            "finish_reason": response.choices[0].finish_reason,
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
        Send streaming chat completion request.

        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            Response chunks with 'delta'

        Raises:
            ProviderAuthError: Authentication failed
            ProviderRateLimitError: Rate limit exceeded
            ProviderTimeoutError: Request timeout
            ProviderInvalidRequestError: Invalid request parameters
            ProviderNotFoundError: Model or resource not found
            ProviderServerError: Server error
            ProviderError: Other provider errors
        """
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        params.update(kwargs)

        try:
            stream = await self._client.chat.completions.create(**params)
        except openai.AuthenticationError as e:
            raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
        except openai.RateLimitError as e:
            raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
        except (openai.APITimeoutError, openai.Timeout) as e:
            raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
        except openai.BadRequestError as e:
            raise ProviderInvalidRequestError(self.name, f"Invalid request: {str(e)}", e)
        except openai.NotFoundError as e:
            raise ProviderNotFoundError(self.name, f"Model not found: {str(e)}", e)
        except openai.InternalServerError as e:
            raise ProviderServerError(self.name, f"Server error: {str(e)}", e, status_code=500)
        except openai.APIError as e:
            raise ProviderError(self.name, f"API error: {str(e)}", e)
        except Exception as e:
            raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)

        async for chunk in stream:
            # Try to surface usage when available (some SDKs expose usage on final chunk)
            usage_obj = getattr(chunk, "usage", None)
            if usage_obj:
                try:
                    usage = {
                        "input_tokens": getattr(usage_obj, "prompt_tokens", 0) or getattr(usage_obj, "input_tokens", 0) or 0,
                        "output_tokens": getattr(usage_obj, "completion_tokens", 0) or getattr(usage_obj, "output_tokens", 0) or 0,
                    }
                    # Cached tokens
                    if hasattr(usage_obj, "prompt_tokens_details"):
                        details = getattr(usage_obj, "prompt_tokens_details")
                        if details and hasattr(details, "cached_tokens"):
                            usage["input_tokens_details"] = {"cached_tokens": getattr(details, "cached_tokens", 0) or 0}
                    # Reasoning tokens
                    if hasattr(usage_obj, "completion_tokens_details"):
                        details = getattr(usage_obj, "completion_tokens_details")
                        if details and hasattr(details, "reasoning_tokens"):
                            usage["output_tokens_details"] = {"reasoning_tokens": getattr(details, "reasoning_tokens", 0) or 0}
                    yield {"usage": usage}
                except Exception:
                    pass
                continue

            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta is not None and delta != "":
                yield {
                    "delta": delta,
                    "finish_reason": chunk.choices[0].finish_reason if chunk.choices else None,
                }
    
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
        """
        Send response API request (with prefix caching support).
        
        Args:
            model: Model identifier
            input_messages: Input messages
            temperature: Sampling temperature
            max_output_tokens: Maximum output tokens
            previous_response_id: Previous response ID for caching
            store: Whether to store for future caching
            **kwargs: Additional parameters
        
        Returns:
            Response with 'content', 'usage', 'response_id'
        """
        if not self._capabilities.supports_responses:
            raise NotImplementedError("Provider does not support responses API")
        
        params = {
            "model": model,
            "input": input_messages,
            "temperature": temperature,
        }
        
        if max_output_tokens is not None:
            params["max_output_tokens"] = max_output_tokens
        
        if previous_response_id is not None:
            params["previous_response_id"] = previous_response_id
        
        if store:
            params["store"] = True
        
        params.update(kwargs)

        try:
            response = await self._client.responses.create(**params)
        except openai.AuthenticationError as e:
            raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
        except openai.RateLimitError as e:
            raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
        except (openai.APITimeoutError, openai.Timeout) as e:
            raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
        except openai.BadRequestError as e:
            raise ProviderInvalidRequestError(self.name, f"Invalid request: {str(e)}", e)
        except openai.NotFoundError as e:
            raise ProviderNotFoundError(self.name, f"Model not found: {str(e)}", e)
        except openai.InternalServerError as e:
            raise ProviderServerError(self.name, f"Server error: {str(e)}", e, status_code=500)
        except openai.APIError as e:
            raise ProviderError(self.name, f"API error: {str(e)}", e)
        except Exception as e:
            raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)

        # Extract content and structured output
        content = ""
        raw_output = None
        output_parsed = None

        if hasattr(response, "output_text"):
            content = response.output_text or ""

        # Prefer exposing raw output list when available
        if hasattr(response, "output") and response.output:
            def _safe_dump(x: Any, depth: int = 0, max_depth: int = 10, visited: Optional[set] = None) -> Any:
                """
                Safely dump object to dict, preventing infinite recursion.

                Args:
                    x: Object to dump
                    depth: Current recursion depth
                    max_depth: Maximum recursion depth
                    visited: Set of visited object IDs to detect circular references

                Returns:
                    Serializable representation of the object
                """
                if visited is None:
                    visited = set()

                # Prevent infinite recursion
                if depth > max_depth:
                    return f"<max_depth_exceeded: {type(x).__name__}>"

                obj_id = id(x)
                if obj_id in visited:
                    return f"<circular_ref: {type(x).__name__}>"

                try:
                    # Try Pydantic model_dump
                    if hasattr(x, "model_dump"):
                        visited.add(obj_id)
                        result = x.model_dump()
                        visited.remove(obj_id)
                        return result

                    # Try to_dict
                    if hasattr(x, "to_dict"):
                        visited.add(obj_id)
                        result = x.to_dict()
                        visited.remove(obj_id)
                        return result

                    # Handle primitives
                    if isinstance(x, (dict, list, str, int, float, bool)) or x is None:
                        return x

                    # Recursively dump object attributes
                    visited.add(obj_id)
                    result = {
                        k: _safe_dump(v, depth + 1, max_depth, visited)
                        for k, v in vars(x).items()
                        if not callable(v) and not k.startswith("_")
                    }
                    visited.remove(obj_id)
                    return result
                except Exception as e:
                    return f"<dump_error: {type(x).__name__}: {str(e)}>"

            raw_output = [_safe_dump(item) for item in response.output]
            # If content not yet set, aggregate texts from parts
            if not content:
                try:
                    for item in response.output:
                        if hasattr(item, "content"):
                            for part in item.content:
                                if hasattr(part, "text") and part.text:
                                    content += part.text
                except Exception:
                    pass

        # Extract output_parsed if present (JSON/tool structured output)
        if hasattr(response, "output_parsed"):
            try:
                op = response.output_parsed
                if op is not None:
                    if hasattr(op, "model_dump"):
                        output_parsed = op.model_dump()
                    elif hasattr(op, "to_dict"):
                        output_parsed = op.to_dict()
                    else:
                        output_parsed = op
            except Exception:
                output_parsed = None

        # Extract usage
        usage: Dict[str, Any] = {}
        if hasattr(response, "usage") and response.usage:
            usage["input_tokens"] = getattr(response.usage, "input_tokens", 0)
            usage["output_tokens"] = getattr(response.usage, "output_tokens", 0)

            # Cached tokens
            if hasattr(response.usage, "input_tokens_details"):
                details = response.usage.input_tokens_details
                if details:
                    usage["input_tokens_details"] = {
                        "cached_tokens": getattr(details, "cached_tokens", 0),
                    }

            # Reasoning tokens
            if hasattr(response.usage, "output_tokens_details"):
                details = response.usage.output_tokens_details
                if details:
                    usage["output_tokens_details"] = {
                        "reasoning_tokens": getattr(details, "reasoning_tokens", 0),
                    }

        # Extract response ID for caching
        response_id = getattr(response, "id", None)

        result: Dict[str, Any] = {
            "content": content,
            "usage": usage,
            "response_id": response_id,
            "provider": self.name,
        }
        if raw_output is not None:
            result["raw_output"] = raw_output
        if output_parsed is not None:
            result["output_parsed"] = output_parsed
        return result
    
    async def close(self) -> None:
        """Close the client."""
        await self._client.close()

