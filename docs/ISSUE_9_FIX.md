# Issue 9 修复: 统一错误处理系统

## 问题描述

在 Issue 9 中发现各个 provider 的错误处理不统一:
- OpenAI provider 直接抛出原始异常 (如 `openai.AuthenticationError`)
- Anthropic provider 直接抛出原始异常 (如 `anthropic.APIError`)
- Gemini provider 使用 httpx，抛出 `httpx.HTTPStatusError`
- API 层只是简单捕获 `Exception` 并转换为 `HTTPException`，没有区分错误类型
- 缺少统一的错误格式和错误码映射

## 解决方案

### 1. 创建统一的异常类层次结构

创建了 `mindiv/providers/exceptions.py`，定义了以下异常类:

- **ProviderError** - 基础异常类
  - `provider`: Provider 名称
  - `message`: 错误消息
  - `original_error`: 原始异常
  - `status_code`: HTTP 状态码
  - `error_code`: 错误码
  - `details`: 额外详情

- **ProviderAuthError** - 认证错误 (401)
- **ProviderRateLimitError** - 速率限制错误 (429)
- **ProviderTimeoutError** - 超时错误 (504)
- **ProviderInvalidRequestError** - 无效请求 (400)
- **ProviderNotFoundError** - 资源未找到 (404)
- **ProviderServerError** - 服务器错误 (500+)

### 2. Provider 层错误转换

#### OpenAI Provider
捕获并转换以下异常:
- `openai.AuthenticationError` → `ProviderAuthError`
- `openai.RateLimitError` → `ProviderRateLimitError`
- `openai.APITimeoutError/Timeout` → `ProviderTimeoutError`
- `openai.BadRequestError` → `ProviderInvalidRequestError`
- `openai.NotFoundError` → `ProviderNotFoundError`
- `openai.InternalServerError` → `ProviderServerError`
- `openai.APIError` → `ProviderError`

#### Anthropic Provider
捕获并转换以下异常:
- `anthropic.AuthenticationError` → `ProviderAuthError`
- `anthropic.RateLimitError` → `ProviderRateLimitError`
- `anthropic.APITimeoutError` → `ProviderTimeoutError`
- `anthropic.BadRequestError` → `ProviderInvalidRequestError`
- `anthropic.NotFoundError` → `ProviderNotFoundError`
- `anthropic.InternalServerError` → `ProviderServerError`
- `anthropic.APIError` → `ProviderError`

#### Gemini Provider
根据 HTTP 状态码转换异常:
- `httpx.HTTPStatusError` (401/403) → `ProviderAuthError`
- `httpx.HTTPStatusError` (429) → `ProviderRateLimitError`
- `httpx.HTTPStatusError` (400) → `ProviderInvalidRequestError`
- `httpx.HTTPStatusError` (404) → `ProviderNotFoundError`
- `httpx.HTTPStatusError` (500+) → `ProviderServerError`
- `httpx.TimeoutException` → `ProviderTimeoutError`
- `httpx.RequestError` → `ProviderError`

### 3. API 层统一错误处理

修改了 `chat.py` 和 `responses.py`，实现:

1. **捕获 ProviderError 及其子类**，返回结构化错误:
```json
{
  "error": {
    "message": "错误消息",
    "type": "错误类型",
    "code": "错误码",
    "provider": "provider名称"
  }
}
```

2. **正确的 HTTP 状态码映射**:
   - `ProviderAuthError` → 401
   - `ProviderInvalidRequestError` → 400
   - `ProviderNotFoundError` → 404
   - `ProviderRateLimitError` → 429
   - `ProviderTimeoutError` → 504
   - `ProviderServerError` → 502
   - `ProviderError` → 502

3. **Streaming 错误处理**: 在 event stream 中发送结构化错误事件

## 修改的文件

1. **新增文件**:
   - `mindiv/providers/exceptions.py` - 统一异常类定义

2. **修改文件**:
   - `mindiv/providers/openai.py` - 添加错误处理
   - `mindiv/providers/anthropic.py` - 添加错误处理
   - `mindiv/providers/gemini.py` - 添加错误处理
   - `mindiv/api/v1/chat.py` - 改进错误处理
   - `mindiv/api/v1/responses.py` - 改进错误处理

## 优势

1. **统一的错误格式** - 所有 provider 返回一致的错误结构
2. **更好的错误分类** - 根据错误类型返回正确的 HTTP 状态码
3. **保留原始错误信息** - 便于调试和日志记录
4. **符合 OpenAI API 规范** - 错误格式与 OpenAI API 一致
5. **便于扩展** - 易于添加新的错误类型和 provider

## 测试建议

1. 测试各种错误场景:
   - 无效的 API key
   - 速率限制
   - 网络超时
   - 无效的请求参数
   - 不存在的模型

2. 验证错误响应格式和状态码

3. 测试 streaming 模式下的错误处理

## 向后兼容性

- 所有修改都是向后兼容的
- 现有的功能不受影响
- 只是改进了错误处理和错误格式

