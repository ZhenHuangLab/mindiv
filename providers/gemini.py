"""
Google Gemini provider adapter.
Supports systemInstruction and thinkingConfig for thinking models.
"""
from typing import Dict, Any, List, Optional, AsyncIterator
import httpx
from .base import LLMProvider, ProviderCapabilities
from ..config import ProviderConfig


class GeminiProvider:
    """Google Gemini provider adapter."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Gemini provider.
        
        Args:
            config: Provider configuration
        """
        self._config = config
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={"Content-Type": "application/json"},
        )
        self._capabilities = ProviderCapabilities(
            supports_responses=False,
            supports_streaming=config.supports_streaming,
            supports_vision=True,
            supports_thinking=True,
            supports_caching=False,
        )
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "gemini"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities."""
        return self._capabilities
    
    def _build_url(self, model: str, stream: bool = False) -> str:
        """Build API URL for Gemini."""
        method = "streamGenerateContent" if stream else "generateContent"
        return f"{self._config.base_url}/models/{model}:{method}?key={self._config.api_key}"
    
    def _convert_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert OpenAI-style messages to Gemini format.
        
        Returns:
            (system_instruction, contents)
        """
        system_instruction = None
        contents = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Gemini uses systemInstruction for system messages
                system_instruction = content if isinstance(content, str) else str(content)
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content if isinstance(content, str) else str(content)}],
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content if isinstance(content, str) else str(content)}],
                })
        
        return system_instruction, contents
    
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
        Send chat request to Gemini.
        
        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream (not supported in this method)
            **kwargs: Additional parameters (e.g., thinking_budget)
        
        Returns:
            Response dictionary with 'content' and 'usage'
        """
        if stream:
            raise ValueError("Use chat_stream() for streaming requests")
        
        system_instruction, contents = self._convert_messages(messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        
        # Add thinking config if specified
        thinking_budget = kwargs.get("thinking_budget")
        if thinking_budget:
            payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": thinking_budget,
            }
        
        url = self._build_url(model, stream=False)
        
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract content
        content = ""
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        content += part["text"]
        
        # Extract usage
        usage = {}
        if "usageMetadata" in data:
            metadata = data["usageMetadata"]
            usage["input_tokens"] = metadata.get("promptTokenCount", 0)
            usage["output_tokens"] = metadata.get("candidatesTokenCount", 0)
        
        return {
            "content": content,
            "usage": usage,
            "finish_reason": "stop",
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
        Send streaming chat request to Gemini.
        
        Args:
            model: Model identifier
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Yields:
            Response chunks with 'delta'
        """
        system_instruction, contents = self._convert_messages(messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        
        thinking_budget = kwargs.get("thinking_budget")
        if thinking_budget:
            payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": thinking_budget,
            }
        
        url = self._build_url(model, stream=True)
        
        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if not line:
                    continue
                # Parse JSON chunk
                try:
                    import json
                    data = json.loads(line)
                    # Optional usage metadata
                    if isinstance(data, dict) and "usageMetadata" in data:
                        meta = data.get("usageMetadata") or {}
                        usage = {
                            "input_tokens": meta.get("promptTokenCount", 0),
                            "output_tokens": meta.get("candidatesTokenCount", 0),
                        }
                        yield {"usage": usage}
                        continue

                    if "candidates" in data and data["candidates"]:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                if "text" in part:
                                    yield {
                                        "delta": part["text"],
                                        "finish_reason": None,
                                    }
                except Exception:
                    continue

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
        """Gemini does not support responses API."""
        raise NotImplementedError("Gemini does not support responses API")
    
    async def close(self) -> None:
        """Close the client."""
        await self._client.aclose()

