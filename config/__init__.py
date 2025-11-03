"""
Configuration module for mindiv.
"""
from typing import Optional
from .config import (
    Config,
    ModelConfig,
    ProviderConfig,
    load_config,
)

# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance.

    Returns:
        Global Config instance

    Raises:
        RuntimeError: If configuration not initialized
    """
    global _global_config

    if _global_config is None:
        # Try to load default configuration
        try:
            _global_config = load_config()
        except Exception:
            # Fallback to empty config
            _global_config = Config()

    return _global_config


def set_config(config: Config) -> None:
    """
    Set global configuration instance.

    Args:
        config: Config instance to set as global
    """
    global _global_config
    _global_config = config


__all__ = [
    "Config",
    "ModelConfig",
    "ProviderConfig",
    "load_config",
    "get_config",
    "set_config",
]

