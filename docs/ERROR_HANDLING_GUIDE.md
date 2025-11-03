# 错误处理指南

## 概述

mindiv 实现了统一的错误处理系统，确保所有 provider 返回一致的错误格式和正确的 HTTP 状态码。

## 异常类层次结构

```
Exception
└── ProviderError (基础异常)
    ├── ProviderAuthError (401)
    ├── ProviderRateLimitError (429)
    ├── ProviderTimeoutError (504)
    ├── ProviderInvalidRequestError (400)
    ├── ProviderNotFoundError (404)
    └── ProviderServerError (502/500+)
```

## 异常类详解

### ProviderError

基础异常类，所有 provider 错误都继承自此类。

**属性**:
- `provider: str` - Provider 名称 (如 'openai', 'anthropic', 'gemini')
- `message: str` - 人类可读的错误消息
- `original_error: Optional[Exception]` - 原始异常对象
- `status_code: int` - HTTP 状态码
- `error_code: str` - 机器可读的错误码
- `details: Dict[str, Any]` - 额外的错误详情

**方法**:
- `to_dict() -> Dict[str, Any]` - 转换为字典格式

**示例**:
```python
from mindiv.providers.exceptions import ProviderError

error = ProviderError(
    provider="openai",
    message="API request failed",
    status_code=502,
    error_code="api_error",
    details={"retry_after": 60}
)
```

### ProviderAuthError

认证失败错误 (HTTP 401)。

**使用场景**:
- 无效的 API key
- API key 过期
- 权限不足

**示例**:
```python
from mindiv.providers.exceptions import ProviderAuthError

raise ProviderAuthError(
    provider="openai",
    message="Invalid API key"
)
```

### ProviderRateLimitError

速率限制错误 (HTTP 429)。

**使用场景**:
- 超过 API 调用频率限制
- 超过配额限制

**示例**:
```python
from mindiv.providers.exceptions import ProviderRateLimitError

raise ProviderRateLimitError(
    provider="anthropic",
    message="Rate limit exceeded",
    details={"retry_after": 60}
)
```

### ProviderTimeoutError

请求超时错误 (HTTP 504)。

**使用场景**:
- 网络超时
- API 响应超时

**示例**:
```python
from mindiv.providers.exceptions import ProviderTimeoutError

raise ProviderTimeoutError(
    provider="gemini",
    message="Request timeout after 30s"
)
```

### ProviderInvalidRequestError

无效请求错误 (HTTP 400)。

**使用场景**:
- 无效的参数
- 缺少必需参数
- 参数格式错误

**示例**:
```python
from mindiv.providers.exceptions import ProviderInvalidRequestError

raise ProviderInvalidRequestError(
    provider="openai",
    message="Invalid temperature value: must be between 0 and 2"
)
```

### ProviderNotFoundError

资源未找到错误 (HTTP 404)。

**使用场景**:
- 模型不存在
- 资源 ID 不存在

**示例**:
```python
from mindiv.providers.exceptions import ProviderNotFoundError

raise ProviderNotFoundError(
    provider="openai",
    message="Model 'gpt-5' not found"
)
```

### ProviderServerError

服务器错误 (HTTP 500+)。

**使用场景**:
- Provider 内部错误
- 服务不可用

**示例**:
```python
from mindiv.providers.exceptions import ProviderServerError

raise ProviderServerError(
    provider="anthropic",
    message="Internal server error",
    status_code=500
)
```

## Provider 实现指南

### 在 Provider 中捕获和转换错误

每个 provider 应该捕获其特定的异常并转换为统一的 `ProviderError` 子类。

**OpenAI Provider 示例**:
```python
import openai
from mindiv.providers.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

try:
    response = await self._client.chat.completions.create(**params)
except openai.AuthenticationError as e:
    raise ProviderAuthError(self.name, f"Invalid API key: {str(e)}", e)
except openai.RateLimitError as e:
    raise ProviderRateLimitError(self.name, f"Rate limit exceeded: {str(e)}", e)
except openai.APITimeoutError as e:
    raise ProviderTimeoutError(self.name, f"Request timeout: {str(e)}", e)
```

**Gemini Provider 示例** (使用 httpx):
```python
import httpx
from mindiv.providers.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
)

try:
    response = await self._client.post(url, json=payload)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    status_code = e.response.status_code
    if status_code == 401:
        raise ProviderAuthError(self.name, "Authentication failed", e)
    elif status_code == 429:
        raise ProviderRateLimitError(self.name, "Rate limit exceeded", e)
    elif status_code >= 500:
        raise ProviderServerError(self.name, "Server error", e, status_code=status_code)
except httpx.TimeoutException as e:
    raise ProviderTimeoutError(self.name, "Request timeout", e)
```

## API 层错误处理

API 层应该捕获 `ProviderError` 并转换为 HTTP 响应。

**示例**:
```python
from fastapi import HTTPException
from mindiv.providers.exceptions import ProviderError

try:
    result = await provider.chat(...)
    return result
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
```

## 错误响应格式

### 标准错误响应

```json
{
  "error": {
    "message": "Invalid API key",
    "type": "auth_error",
    "code": "auth_error",
    "provider": "openai"
  }
}
```

### Streaming 错误响应

在 SSE stream 中:
```
data: {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error", "code": "rate_limit_error", "provider": "anthropic"}}

data: [DONE]
```

## 最佳实践

1. **始终保留原始异常**: 将原始异常传递给 `original_error` 参数，便于调试
2. **提供清晰的错误消息**: 错误消息应该清晰地说明问题和可能的解决方案
3. **使用正确的异常类型**: 根据错误类型选择合适的异常类
4. **添加有用的详情**: 使用 `details` 参数提供额外信息 (如 `retry_after`)
5. **按照从具体到一般的顺序捕获异常**: 先捕获具体的异常类型，最后捕获通用异常

## 测试

运行错误处理测试:
```bash
pytest mindiv/test/test_error_handling.py -v
```

## 参考

- [OpenAI API 错误码](https://platform.openai.com/docs/guides/error-codes)
- [Anthropic API 错误处理](https://docs.anthropic.com/claude/reference/errors)
- [HTTP 状态码](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

