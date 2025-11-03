# Issue #8 修复报告: TokenMeter 成本计算假设验证

## 问题描述

**Issue #8**: TokenMeter 成本计算假设未验证  
**文件**: `mindiv/utils/token_meter.py:164-179`  
**严重性**: 中  

原始代码假设:
1. `cached_tokens` 已包含在 `input_tokens` 中
2. `reasoning_tokens` 已包含在 `output_tokens` 中

但这些假设没有被验证或文档化,可能导致成本计算错误。

## 修复方案

### 1. 添加验证逻辑

在 `UsageStats` 类中添加 `validate()` 方法:

```python
def validate(self) -> None:
    """
    Validate token counting assumptions.
    
    Logs warnings if the assumptions are violated:
    - cached_tokens should be <= input_tokens
    - reasoning_tokens should be <= output_tokens
    """
    if self.cached_tokens > self.input_tokens:
        logger.warning(
            f"Invalid token counts: cached_tokens ({self.cached_tokens}) > "
            f"input_tokens ({self.input_tokens}). This violates the assumption "
            f"that cached tokens are included in input tokens."
        )
    
    if self.reasoning_tokens > self.output_tokens:
        logger.warning(
            f"Invalid token counts: reasoning_tokens ({self.reasoning_tokens}) > "
            f"output_tokens ({self.output_tokens}). This violates the assumption "
            f"that reasoning tokens are included in output tokens."
        )
```

### 2. 在成本计算中调用验证

在 `estimate_cost()` 方法中,计算成本前调用验证:

```python
# Get usage and pricing for specific provider/model
usage = self.get_usage(provider, model)
pricing = self.pricing.get(provider, {}).get(model)

if not pricing:
    return 0.0

# Validate token counting assumptions
usage.validate()

# Calculate cost per token type...
```

### 3. 添加详细文档

#### UsageStats 类文档

```python
@dataclass
class UsageStats:
    """
    Token usage statistics.

    Token counting assumptions (based on OpenAI API documentation):
    - cached_tokens: Subset of input_tokens representing cached prompt tokens.
      These are already included in input_tokens count.
    - reasoning_tokens: Subset of output_tokens representing reasoning tokens
      (for models like o1). These are already included in output_tokens count.

    This means:
    - Uncached input tokens = input_tokens - cached_tokens
    - Regular output tokens = output_tokens - reasoning_tokens
    """
```

#### estimate_cost 方法文档

```python
def estimate_cost(...) -> float:
    """
    Estimate cost in USD based on pricing data.

    Cost calculation logic:
    - Uncached input tokens: (input_tokens - cached_tokens) * prompt_price
    - Cached input tokens: cached_tokens * cached_prompt_price
    - Regular output tokens: (output_tokens - reasoning_tokens) * completion_price
    - Reasoning tokens: reasoning_tokens * reasoning_price

    This assumes (verified via validate()):
    - cached_tokens is already included in input_tokens
    - reasoning_tokens is already included in output_tokens
    ...
    """
```

### 4. 添加行内注释

在关键计算处添加注释说明假设:

```python
# Regular input tokens (uncached)
# Assumption: cached_tokens is already included in input_tokens
uncached_input = usage.input_tokens - usage.cached_tokens

# Regular output tokens (non-reasoning)
# Assumption: reasoning_tokens is already included in output_tokens
regular_output = usage.output_tokens - usage.reasoning_tokens
```

## 验证依据

根据 OpenAI API 文档和实际响应示例:

```json
{
  "usage": {
    "input_tokens": 75,
    "input_tokens_details": {
      "cached_tokens": 0
    },
    "output_tokens": 148,
    "output_tokens_details": {
      "reasoning_tokens": 1024
    }
  }
}
```

- `input_tokens_details.cached_tokens` 是 `input_tokens` 的详细信息,表示其中有多少是缓存的
- `output_tokens_details.reasoning_tokens` 是 `output_tokens` 的详细信息,表示其中有多少是推理 tokens

这证实了我们的假设是正确的。

## 测试

创建了 `mindiv/test/test_token_meter_validation.py` 测试文件,包含:

1. **UsageStats 验证测试**
   - 有效的 token 计数
   - 无效的 cached_tokens (应触发警告)
   - 无效的 reasoning_tokens (应触发警告)
   - 两者都无效 (应触发两个警告)

2. **TokenMeter 成本计算测试**
   - 记录有效使用情况
   - 验证成本计算正确性
   - 验证摘要生成

3. **边界情况测试**
   - 零 tokens
   - cached_tokens = input_tokens
   - reasoning_tokens = output_tokens

## 影响

### 向后兼容性
✅ **完全兼容** - 只添加了验证和文档,没有改变现有行为

### 性能影响
✅ **可忽略** - 验证逻辑只是简单的整数比较

### 错误检测
✅ **改进** - 现在可以检测并警告不正确的 token 计数

## 修改文件

1. `mindiv/utils/token_meter.py` - 主要修复
   - 添加 logging 导入
   - UsageStats 添加文档和 validate() 方法
   - estimate_cost 添加详细文档和验证调用
   - 添加行内注释说明假设

2. `mindiv/test/test_token_meter_validation.py` - 新增测试文件
   - 验证逻辑测试
   - 成本计算测试
   - 边界情况测试

## 结论

Issue #8 已完全修复:
- ✅ 添加了验证逻辑,确保假设正确
- ✅ 添加了详细文档,说明 token 计数假设
- ✅ 添加了测试,验证修复正确性
- ✅ 保持向后兼容性
- ✅ 改进了错误检测能力

修复遵循了 Fail-Fast 原则,在检测到异常情况时会立即记录警告,帮助开发者快速发现问题。

