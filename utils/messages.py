"""
Message utilities for handling multi-modal content and message normalization.
"""
from typing import List, Dict, Any, Union, Optional


MessageContent = Union[str, List[Dict[str, Any]]]


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize message format across different providers.
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Normalized messages
    """
    normalized = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Ensure content is in the right format
        if isinstance(content, str):
            normalized.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Multi-modal content
            normalized.append({"role": role, "content": content})
        else:
            # Fallback: convert to string
            normalized.append({"role": role, "content": str(content)})
    
    return normalized


def extract_text_content(content: MessageContent) -> str:
    """
    Extract plain text from message content (handles multi-modal).
    
    Args:
        content: Message content (string or list of content parts)
    
    Returns:
        Plain text string
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        # Extract text from multi-modal content
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif "text" in part:
                    text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(text_parts)
    
    return str(content)


def build_message(role: str, content: MessageContent) -> Dict[str, Any]:
    """
    Build a message dictionary.
    
    Args:
        role: Message role ('system', 'user', 'assistant')
        content: Message content
    
    Returns:
        Message dictionary
    """
    return {"role": role, "content": content}


def build_system_message(content: str) -> Dict[str, Any]:
    """Build a system message."""
    return build_message("system", content)


def build_user_message(content: MessageContent) -> Dict[str, Any]:
    """Build a user message."""
    return build_message("user", content)


def build_assistant_message(content: str) -> Dict[str, Any]:
    """Build an assistant message."""
    return build_message("assistant", content)


def merge_system_prompts(*prompts: Optional[str]) -> str:
    """
    Merge multiple system prompts into one.
    
    Args:
        *prompts: Variable number of system prompts (None values are filtered)
    
    Returns:
        Merged system prompt
    """
    valid_prompts = [p for p in prompts if p]
    return "\n\n".join(valid_prompts)


def append_knowledge_context(system_prompt: str, knowledge: Optional[str]) -> str:
    """
    Append knowledge context to system prompt.
    
    Args:
        system_prompt: Base system prompt
        knowledge: Knowledge context to append
    
    Returns:
        System prompt with knowledge context
    """
    if not knowledge:
        return system_prompt
    
    return (
        f"{system_prompt}\n\n"
        f"### Available Knowledge Base ###\n\n"
        f"{knowledge}\n\n"
        f"### End of Knowledge Base ###"
    )


def format_conversation_history(
    messages: List[Dict[str, Any]],
    max_messages: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Format conversation history, optionally limiting to recent messages.

    Args:
        messages: List of messages
        max_messages: Maximum number of recent messages to keep

    Returns:
        Formatted message list
    """
    if max_messages is not None and len(messages) > max_messages:
        # Keep system message if present, then most recent messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        if system_msgs:
            return system_msgs + other_msgs[-max_messages:]
        else:
            return other_msgs[-max_messages:]

    return messages


def ensure_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure messages are in the correct format.
    Alias for normalize_messages for backward compatibility.

    Args:
        messages: List of message dictionaries

    Returns:
        Normalized messages
    """
    return normalize_messages(messages)


def extract_text(response: Dict[str, Any]) -> str:
    """
    Extract text from various response formats.

    Args:
        response: Response dictionary from provider

    Returns:
        Extracted text content
    """
    # Try common response formats
    if "content" in response:
        return str(response["content"])

    if "output_text" in response:
        return str(response["output_text"])

    if "choices" in response and response["choices"]:
        choice = response["choices"][0]
        if "message" in choice:
            return str(choice["message"].get("content", ""))
        if "text" in choice:
            return str(choice["text"])

    if "text" in response:
        return str(response["text"])

    # Fallback: convert entire response to string
    return str(response)

