# mindiv Bug 修复清单

## 🔴 严重 Bug (立即修复)

### [ ] Bug #1: DeepThinkEngine 返回类型注解错误
**文件**: `mindiv/engine/deep_think.py`  
**行号**: 126  
**当前代码**:
```python
async def _verify_solution(self, problem_text: str, solution_text: str) -> (Dict[str, Any], bool):
```

**修复代码**:
```python
async def _verify_solution(self, problem_text: str, solution_text: str) -> tuple[Dict[str, Any], bool]:
```

**测试**:
```python
# 运行 mypy 类型检查
mypy mindiv/engine/deep_think.py
```

---

### [ ] Bug #2: PrefixCache response_id 未持久化
**文件**: `mindiv/utils/cache.py`  
**行号**: 44-45, 138-164  

**问题**: response_id 只存储在内存字典中,服务重启后丢失

**修复步骤**:

1. 修改 `set_response_id` 方法:
```python
def set_response_id(self, prefix_key: str, response_id: str) -> None:
    """Store response ID for provider-side caching (persisted to disk)."""
    if not self.enabled:
        return
    
    # Store in disk cache with prefix
    cache_key = f"response_id:{prefix_key}"
    self._disk_cache.set(cache_key, response_id, expire=self.ttl)
```

2. 修改 `get_response_id` 方法:
```python
def get_response_id(self, prefix_key: str) -> Optional[str]:
    """Get cached response ID for provider-side caching (from disk)."""
    if not self.enabled:
        return None
    
    cache_key = f"response_id:{prefix_key}"
    return self._disk_cache.get(cache_key)
```

3. 移除内存字典:
```python
# 删除这一行:
# self._response_id_cache: Dict[str, str] = {}
```

4. 更新 `clear` 方法:
```python
def clear(self) -> None:
    """Clear all cached data."""
    self._disk_cache.clear()
    # 移除: self._response_id_cache.clear()
```

**测试**:
```python
# 测试持久化
cache = PrefixCache()
cache.set_response_id("test_key", "resp_123")
cache.close()

# 重新创建实例
cache2 = PrefixCache()
assert cache2.get_response_id("test_key") == "resp_123"
```

---

### [ ] Bug #3: OpenAIProvider._safe_dump 可能无限递归
**文件**: `mindiv/providers/openai.py`  
**行号**: 229-239  

**修复代码**:
```python
def _safe_dump(x: Any, depth: int = 0, max_depth: int = 10, visited: Optional[set] = None) -> Any:
    """Safely dump object to dict, preventing infinite recursion."""
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
```

**测试**:
```python
# 测试循环引用
class Node:
    def __init__(self):
        self.next = None

a = Node()
b = Node()
a.next = b
b.next = a  # 循环引用

result = _safe_dump(a)
assert "<circular_ref" in str(result)
```

---

### [ ] Bug #4: Config 未实现环境变量替换
**文件**: `mindiv/config/config.py`  
**行号**: 135-175  

**修复步骤**:

1. 添加环境变量替换函数:
```python
import os
import re
from typing import Any

def _replace_env_vars(data: Any) -> Any:
    """
    Recursively replace ${VAR_NAME} with environment variable values.
    
    Args:
        data: Configuration data (dict, list, str, or primitive)
    
    Returns:
        Data with environment variables replaced
    """
    if isinstance(data, str):
        # Replace ${VAR_NAME} or $VAR_NAME with environment variable
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
    
    return data
```

2. 在 `from_yaml` 方法中应用:
```python
@classmethod
def from_yaml(cls, config_path: Path, pricing_path: Optional[Path] = None) -> "Config":
    """Load configuration from YAML files."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Empty configuration file: {config_path}")

    # Replace environment variables
    data = _replace_env_vars(data)
    
    # ... rest of the method
```

**测试**:
```python
import os
os.environ["TEST_API_KEY"] = "sk-test-123"

config_data = {
    "providers": {
        "openai": {
            "api_key": "${TEST_API_KEY}"
        }
    }
}

result = _replace_env_vars(config_data)
assert result["providers"]["openai"]["api_key"] == "sk-test-123"
```

---

## 🟡 中等优先级问题

### [ ] Issue #5: 移除 UltraThink JSON fallback
**文件**: `mindiv/engine/ultra_think.py`  
**行号**: 153-167  

**修复**:
```python
# Parse agent configurations
try:
    configs = json.loads(config_text)
    if not isinstance(configs, list):
        raise ValueError("Expected JSON array of agent configs")
    if len(configs) == 0:
        raise ValueError("Agent configs array is empty")
except json.JSONDecodeError as e:
    raise RuntimeError(
        f"Failed to parse agent configs as JSON: {e}\n"
        f"Raw LLM output:\n{config_text}"
    )
except Exception as e:
    raise RuntimeError(f"Invalid agent configs: {e}")
```

---

### [ ] Issue #6: 改进验证结果解析
**文件**: `mindiv/engine/deep_think.py`  
**行号**: 133-134, 139-140  

**选项 1: 更健壮的字符串解析**
```python
def _parse_verification_verdict(verdict_text: str) -> bool:
    """Parse verification verdict from LLM response."""
    text = verdict_text.lower().strip()
    
    # Check for explicit yes/no at start
    if text.startswith("yes"):
        return True
    if text.startswith("no"):
        return False
    
    # Check for common patterns
    if "correct" in text or "valid" in text:
        return True
    if "incorrect" in text or "invalid" in text or "error" in text:
        return False
    
    # Default to conservative (not good)
    return False

# Usage:
is_good = _parse_verification_verdict(v.get("verdict", ""))
```

**选项 2: 使用结构化输出 (推荐)**
```python
# In verify_with_llm, add response_format parameter
llm_params_with_format = {
    **llm_params,
    "response_format": {
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "is_correct": {"type": "boolean"},
                "reasoning": {"type": "string"},
                "errors": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["is_correct", "reasoning"]
        }
    }
}

# Parse JSON response
result = json.loads(text)
is_good = result.get("is_correct", False)
```

---

### [ ] Issue #7: 重构 engines.py 重复代码
**文件**: `mindiv/api/v1/engines.py`  

**创建共享函数**:
```python
def _configure_rate_limiter(
    cfg: Config,
    req_rate_limit: Optional[RateLimitConfig],
    provider_name: str,
    model_name: str,
) -> tuple[Optional[Any], Optional[float], str]:
    """
    Configure rate limiter from request and config defaults.
    
    Returns:
        (rate_limiter, timeout, strategy)
    """
    from mindiv.utils.rate_limiter import get_global_rate_limiter
    
    rl_defaults = getattr(cfg, "rate_limit", None)
    
    # Merge request with defaults
    qps = req_rate_limit.qps if req_rate_limit and req_rate_limit.qps is not None else getattr(rl_defaults, "qps", None)
    burst = req_rate_limit.burst if req_rate_limit and req_rate_limit.burst is not None else getattr(rl_defaults, "burst", None)
    window_limit = req_rate_limit.window_limit if req_rate_limit and req_rate_limit.window_limit is not None else getattr(rl_defaults, "window_limit", None)
    window_seconds = req_rate_limit.window_seconds if req_rate_limit and req_rate_limit.window_seconds is not None else getattr(rl_defaults, "window_seconds", None)
    timeout = req_rate_limit.timeout if req_rate_limit and req_rate_limit.timeout is not None else getattr(rl_defaults, "timeout", None)
    strategy = (req_rate_limit.strategy if req_rate_limit and req_rate_limit.strategy else getattr(rl_defaults, "strategy", "wait")) or "wait"
    template = getattr(rl_defaults, "bucket_template", "{provider}:{model}") if rl_defaults else "{provider}:{model}"
    
    rate_limiter = None
    if any(v is not None for v in (qps, burst, window_limit, window_seconds)):
        gl = get_global_rate_limiter()
        bucket_key = _compose_bucket_key(template, provider_name, model_name, req_rate_limit.bucket_key if req_rate_limit else None)
        
        if qps is not None and burst is not None:
            await gl.configure_bucket(bucket_key, qps=float(qps), burst=int(burst))
        if window_limit is not None and window_seconds is not None:
            await gl.configure_window(bucket_key, limit=int(window_limit), window_seconds=float(window_seconds))
        
        rate_limiter = gl
    
    return rate_limiter, timeout, strategy

# Usage in endpoints:
rate_limiter, timeout, strategy = await _configure_rate_limiter(cfg, req.rate_limit, provider_name, model_name)
```

---

### [ ] Issue #9: 统一错误处理
**文件**: `mindiv/providers/base.py` (新建)  

**创建统一异常类**:
```python
class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(
        self,
        provider: str,
        message: str,
        original_error: Optional[Exception] = None,
        status_code: Optional[int] = None,
    ):
        self.provider = provider
        self.message = message
        self.original_error = original_error
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")

class ProviderAuthError(ProviderError):
    """Authentication error."""
    pass

class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass

class ProviderTimeoutError(ProviderError):
    """Request timeout."""
    pass
```

**在各 Provider 中使用**:
```python
# In OpenAIProvider.chat:
try:
    response = await self._client.chat.completions.create(**params)
except openai.AuthenticationError as e:
    raise ProviderAuthError(self.name, "Invalid API key", e, 401)
except openai.RateLimitError as e:
    raise ProviderRateLimitError(self.name, "Rate limit exceeded", e, 429)
except openai.Timeout as e:
    raise ProviderTimeoutError(self.name, "Request timeout", e, 504)
except Exception as e:
    raise ProviderError(self.name, f"Unexpected error: {str(e)}", e)
```

---

## ⚠️ 低优先级改进

### [ ] Issue #10: 改进缓存键序列化
**文件**: `mindiv/utils/cache.py`  

**使用更健壮的序列化**:
```python
import pickle
import base64

def compute_key(self, ...) -> str:
    components = {...}
    
    try:
        # Try JSON first (human-readable)
        serialized = json.dumps(components, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # Fallback to pickle for complex objects
        serialized = base64.b64encode(pickle.dumps(components)).decode()
    
    return hashlib.sha256(serialized.encode()).hexdigest()
```

---

### [ ] Issue #13: 添加配置验证
**文件**: `mindiv/config/config.py`  

**添加验证方法**:
```python
def validate(self) -> None:
    """Validate configuration."""
    errors = []
    
    # Validate providers
    for provider_id, provider_config in self.providers.items():
        if not provider_config.api_key:
            errors.append(f"Provider '{provider_id}' missing API key")
        if not provider_config.base_url:
            errors.append(f"Provider '{provider_id}' missing base_url")
    
    # Validate models
    for model_id, model_config in self.models.items():
        if model_config.provider not in self.providers:
            errors.append(f"Model '{model_id}' references unknown provider '{model_config.provider}'")
    
    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

# Call in from_yaml:
config = cls(...)
config.validate()
return config
```

---

## 📋 测试清单

### [ ] 单元测试
- [ ] DeepThinkEngine 基本流程
- [ ] UltraThinkEngine 基本流程
- [ ] PrefixCache 持久化
- [ ] TokenMeter 成本计算
- [ ] 环境变量替换
- [ ] 错误处理

### [ ] 集成测试
- [ ] OpenAI Provider (需要 API key)
- [ ] Anthropic Provider (需要 API key)
- [ ] Gemini Provider (需要 API key)
- [ ] 端到端 DeepThink 流程
- [ ] 端到端 UltraThink 流程

### [ ] 性能测试
- [ ] 并发请求处理
- [ ] 速率限制正确性
- [ ] 缓存命中率

---

## ✅ 完成标准

每个 Bug/Issue 修复后需要:
1. [ ] 代码修改完成
2. [ ] 添加/更新单元测试
3. [ ] 通过所有测试
4. [ ] 更新相关文档
5. [ ] Code review 通过

