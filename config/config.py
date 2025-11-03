"""
Configuration management for mindiv.
Handles loading and validation of YAML configuration files.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import yaml


def _replace_env_vars(data: Any) -> Any:
    """
    Recursively replace ${VAR_NAME} or $VAR_NAME with environment variable values.

    Args:
        data: Configuration data (dict, list, str, or primitive)

    Returns:
        Data with environment variables replaced

    Examples:
        >>> os.environ["TEST_KEY"] = "secret"
        >>> _replace_env_vars("${TEST_KEY}")
        'secret'
        >>> _replace_env_vars({"key": "${TEST_KEY}"})
        {'key': 'secret'}
    """
    if isinstance(data, str):
        # Replace ${VAR_NAME} or $VAR_NAME with environment variable
        # Pattern matches:
        # - ${VAR_NAME} (preferred, more explicit)
        # - $VAR_NAME (must start with letter or underscore, followed by alphanumeric or underscore)
        pattern = r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)'

        def replacer(match):
            var_name = match.group(1) or match.group(2)
            value = os.environ.get(var_name)
            if value is None:
                # Keep original if env var not found
                return match.group(0)
            return value

        return re.sub(pattern, replacer, data)

    elif isinstance(data, dict):
        return {k: _replace_env_vars(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [_replace_env_vars(item) for item in data]

    # Return primitives unchanged
    return data


@dataclass
class RateLimitDefaults:
    """Global default rate limit configuration (system-wide)."""
    qps: Optional[float] = None
    burst: Optional[int] = None
    timeout: Optional[float] = None
    strategy: str = "wait"  # 'wait' or 'fail'
    window_limit: Optional[int] = None
    window_seconds: Optional[float] = None
    bucket_template: str = "{provider}:{model}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitDefaults":
        return cls(
            qps=data.get("qps"),
            burst=data.get("burst"),
            timeout=data.get("timeout"),
            strategy=data.get("strategy", "wait"),
            window_limit=data.get("window_limit"),
            window_seconds=data.get("window_seconds"),
            bucket_template=data.get("bucket_template", "{provider}:{model}"),
        )


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    provider_id: str
    base_url: str
    api_key: str
    supports_responses: bool = False
    supports_streaming: bool = True
    timeout: int = 300
    max_retries: int = 3

    @classmethod
    def from_dict(cls, provider_id: str, data: Dict[str, Any]) -> "ProviderConfig":
        """Create ProviderConfig from dictionary."""
        return cls(
            provider_id=provider_id,
            base_url=data.get("base_url", ""),
            api_key=data.get("api_key", ""),
            supports_responses=data.get("supports_responses", False),
            supports_streaming=data.get("supports_streaming", True),
            timeout=data.get("timeout", 300),
            max_retries=data.get("max_retries", 3),
        )


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    
    model_id: str
    name: str
    provider: str
    model: str
    level: str  # "deepthink" or "ultrathink"
    
    # Engine parameters
    max_iterations: int = 30
    required_verifications: int = 3
    max_errors: int = 10
    enable_planning: bool = False
    enable_parallel_check: bool = False
    
    # UltraThink parameters
    num_agents: Optional[int] = None
    parallel_run_agents: int = 3
    
    # Stage-specific models
    stage_models: Dict[str, str] = field(default_factory=dict)
    
    # Rate limiting
    rpm: Optional[int] = None
    
    @classmethod
    def from_dict(cls, model_id: str, data: Dict[str, Any]) -> "ModelConfig":
        """Create ModelConfig from dictionary."""
        return cls(
            model_id=model_id,
            name=data.get("name", model_id),
            provider=data["provider"],
            model=data["model"],
            level=data.get("level", "deepthink"),
            max_iterations=data.get("max_iterations", 30),
            required_verifications=data.get("required_verifications", 3),
            max_errors=data.get("max_errors", 10),
            enable_planning=data.get("enable_planning", False),
            enable_parallel_check=data.get("enable_parallel_check", False),
            num_agents=data.get("num_agents"),
            parallel_run_agents=data.get("parallel_run_agents", 3),
            stage_models=data.get("stage_models", {}),
            rpm=data.get("rpm"),
        )
    
    def get_stage_model(self, stage: str) -> str:
        """Get model for a specific stage, fallback to default model."""
        return self.stage_models.get(stage, self.model)


@dataclass
class Config:
    """Global configuration for mindiv."""

    # System settings
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: Optional[str] = None
    log_level: str = "INFO"

    # Rate limit defaults (system-wide)
    rate_limit: RateLimitDefaults = field(default_factory=RateLimitDefaults)

    # Providers and models
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    models: Dict[str, ModelConfig] = field(default_factory=dict)

    # Pricing data
    pricing: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: Path, pricing_path: Optional[Path] = None) -> "Config":
        """Load configuration from YAML files."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"Empty configuration file: {config_path}")

        # Replace environment variables in configuration
        data = _replace_env_vars(data)

        # Load system settings
        system = data.get("system", {})
        rl_defaults = RateLimitDefaults.from_dict(system.get("rate_limit", {}))

        # Load providers
        providers = {}
        for provider_id, provider_data in data.get("providers", {}).items():
            providers[provider_id] = ProviderConfig.from_dict(provider_id, provider_data)

        # Load models
        models = {}
        for model_id, model_data in data.get("models", {}).items():
            models[model_id] = ModelConfig.from_dict(model_id, model_data)

        # Load pricing if provided
        pricing = {}
        if pricing_path and pricing_path.exists():
            with open(pricing_path, "r", encoding="utf-8") as f:
                pricing = yaml.safe_load(f) or {}
            # Replace environment variables in pricing data
            pricing = _replace_env_vars(pricing)

        return cls(
            host=system.get("host", "0.0.0.0"),
            port=system.get("port", 8000),
            api_key=system.get("api_key"),
            log_level=system.get("log_level", "INFO"),
            rate_limit=rl_defaults,
            providers=providers,
            models=models,
            pricing=pricing,
        )

    def get_provider(self, provider_id: str) -> ProviderConfig:
        """Get provider configuration by ID."""
        if provider_id not in self.providers:
            raise ValueError(f"Provider not found: {provider_id}")
        return self.providers[provider_id]
    
    def get_model(self, model_id: str) -> ModelConfig:
        """Get model configuration by ID."""
        if model_id not in self.models:
            raise ValueError(f"Model not found: {model_id}")
        return self.models[model_id]
    
    def list_models(self) -> List[str]:
        """List all available model IDs."""
        return list(self.models.keys())
    
    def get_pricing(self, provider: str, model: str) -> Optional[Dict[str, Any]]:
        """Get pricing information for a provider/model combination."""
        provider_pricing = self.pricing.get(provider, {})
        return provider_pricing.get(model)


def load_config(
    config_path: Optional[Path] = None,
    pricing_path: Optional[Path] = None,
) -> Config:
    """
    Load configuration from YAML files.
    
    Args:
        config_path: Path to config.yaml (defaults to mindiv/config/config.yaml)
        pricing_path: Path to pricing.yaml (defaults to mindiv/config/pricing.yaml)
    
    Returns:
        Loaded Config instance
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    
    if pricing_path is None:
        pricing_path = Path(__file__).parent / "pricing.yaml"
    
    return Config.from_yaml(config_path, pricing_path)

