"""
Base provider interface for LLM providers.
Defines the contract that all provider adapters must implement.
"""
from typing import Protocol, Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass


@dataclass
class ProviderCapabilities:
    """Capabilities supported by a provider."""
    
    supports_responses: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_thinking: bool = False
    supports_caching: bool = False


class LLMProvider(Protocol):
    """
    Protocol defining the interface for LLM providers.
    All provider adapters must implement this interface.
    """
    
    @property
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic', 'gemini')."""
        ...
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities."""
        ...
    
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
        Send a chat completion request.
        
        Args:
            model: Model identifier
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Response dictionary with 'content', 'usage', and other metadata
        
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If the API call fails
        """
        ...
    
    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a streaming chat completion request.
        
        Args:
            model: Model identifier
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Yields:
            Response chunks with 'delta' and other metadata
        
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If the API call fails
        """
        ...
    
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
        Send a response API request (OpenAI-specific, for prefix caching).
        
        Args:
            model: Model identifier
            input_messages: Input messages
            temperature: Sampling temperature
            max_output_tokens: Maximum output tokens
            previous_response_id: Previous response ID for caching
            store: Whether to store the response for future caching
            **kwargs: Additional parameters
        
        Returns:
            Response dictionary with 'content', 'usage', 'response_id', etc.
        
        Raises:
            NotImplementedError: If provider doesn't support responses API
            ValueError: If parameters are invalid
            RuntimeError: If the API call fails
        """
        ...
    
    async def close(self) -> None:
        """Close any open connections or resources."""
        ...

