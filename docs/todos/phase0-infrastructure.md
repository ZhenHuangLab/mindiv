# Phase 0: 基础设施 (Infrastructure)

## 📋 概述

**目标**: 建立统一的Reducer架构,为4个方案提供共享基础设施。

**重要性**: 这是整个多模式Reducer系统的基石,必须先完成才能开始实现各个方案。

**预估时间**: 3-4天

**优先级**: 🔴 最高 (必须先完成)

---

## 🎯 交付物清单

- [ ] `mindiv/engine/reducers/` 目录结构
- [ ] `base.py` - BaseReducer抽象基类
- [ ] `types.py` - 类型定义 (ReducerResult, AgentResult等)
- [ ] `normalizer.py` - 答案归一化工具
- [ ] `prompts.py` - 所有reducer相关的prompts
- [ ] Provider路由系统
- [ ] UltraThinkEngine集成点
- [ ] 单元测试
- [ ] 文档

---

## 🔗 前置条件

- [x] mindiv项目基础架构已完成
- [x] UltraThinkEngine已实现
- [x] 多provider支持已实现
- [x] Token metering系统已实现

---

## ✅ 详细任务清单

### Day 1: 核心类型和基类设计

#### 任务 1.1: 创建目录结构
- [ ] 创建 `mindiv/engine/reducers/` 目录
- [ ] 创建 `mindiv/engine/reducers/__init__.py`
- [ ] 创建 `mindiv/engine/reducers/tests/` 测试目录

#### 任务 1.2: 实现 `types.py`
- [ ] 定义 `AgentResult` dataclass
  - `agent_id: str`
  - `final_solution: str`
  - `reasoning: str`
  - `metadata: Dict[str, Any]`
- [ ] 定义 `ReducerResult` dataclass
  - `final_answer: str`
  - `confidence: float`
  - `metadata: Dict[str, Any]`
  - `token_usage: Dict[str, int]`
  - `intermediate_results: Optional[List[Dict]]`
  - `decision_trace: Optional[List[str]]`
- [ ] 定义 `ProviderConfig` dataclass
- [ ] 定义异常类: `CostBudgetExceededError`, `ReducerError`
- [ ] 编写类型注解和docstrings

#### 任务 1.3: 实现 `base.py` - BaseReducer抽象基类
- [ ] 定义 `BaseReducer` 抽象类
- [ ] 实现 `__init__(config, engine)` 方法
- [ ] 实现抽象方法 `reduce()` 签名
- [ ] 实现 `_call_llm(messages, provider, **kwargs)` 方法
- [ ] 实现 `_call_llm_for_role(role, messages, **kwargs)` 方法
- [ ] 实现 `_get_provider_for_role(role)` 方法
- [ ] 实现 `_emit(event, data)` 方法
- [ ] 实现 `_get_token_usage()` 方法
- [ ] 实现成本预算检查逻辑
- [ ] 编写完整的docstrings

**验收标准**:
- [ ] 所有方法都有类型注解
- [ ] 所有方法都有docstrings
- [ ] Provider路由逻辑正确
- [ ] 成本预算检查正常工作

---

### Day 2: 答案归一化工具

#### 任务 2.1: 实现 `normalizer.py`
- [ ] 实现 `AnswerNormalizer` 类
- [ ] 实现 `normalize(answer, answer_type="auto")` 方法
- [ ] 实现 `_detect_type(answer)` 方法
  - 检测是否为数值
  - 检测是否为LaTeX
  - 默认为文本
- [ ] 实现 `normalize_numeric(answer)` 方法
  - 正则提取数值: `[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?`
  - 规范化: 去除尾随零
  - 处理科学计数法
- [ ] 实现 `normalize_latex(answer)` 方法
  - 使用sympy解析LaTeX
  - 规范化表达式
  - 处理解析失败的情况
- [ ] 实现 `normalize_text(answer)` 方法
  - 转小写
  - 去除空格
  - 去除标点(可选)
- [ ] 实现 `normalize_batch(answers)` 批量归一化

#### 任务 2.2: 编写归一化测试
- [ ] 测试数值归一化
  - "2.0" → "2"
  - "3.14159" → "3.14159"
  - "1e-5" → "1e-5"
  - "The answer is 42" → "42"
- [ ] 测试LaTeX归一化
  - "\\frac{1}{2}" → 规范化形式
  - "x^2 + 2x + 1" → 规范化形式
- [ ] 测试文本归一化
  - "Hello World" → "helloworld"
  - "Yes" → "yes"
- [ ] 测试边界情况
  - 空字符串
  - 无法解析的输入
  - 混合格式

**验收标准**:
- [ ] 所有测试通过
- [ ] 覆盖率 > 90%
- [ ] 处理所有边界情况

---

### Day 3: Prompts和Provider路由

#### 任务 3.1: 实现 `prompts.py`
- [ ] 定义 `CONFIDENCE_EXTRACTION_PROMPT`
- [ ] 定义 `P_TRUE_PROMPT`
- [ ] 定义 `JUDGE_PROMPT` (为Phase 2准备)
- [ ] 定义 `GRADER_INITIAL_PROMPT` (为Phase 3准备)
- [ ] 定义 `GRADER_FINAL_PROMPT` (为Phase 3准备)
- [ ] 定义 `CRITIC_PROMPT` (为Phase 3准备)
- [ ] 定义 `DEFENDER_PROMPT` (为Phase 3准备)
- [ ] 所有prompt都使用f-string格式,支持变量替换
- [ ] 添加prompt使用说明和示例

#### 任务 3.2: 增强Provider路由系统
- [ ] 在 `BaseReducer` 中实现fallback逻辑
  - 如果指定provider失败,尝试默认provider
  - 记录fallback事件
- [ ] 实现provider可用性检查
- [ ] 实现provider成本估算
- [ ] 添加provider路由的日志记录

#### 任务 3.3: 编写Provider路由测试
- [ ] 测试正常路由
- [ ] 测试fallback机制
- [ ] 测试provider不可用的情况
- [ ] 测试成本预算超限

**验收标准**:
- [ ] 所有prompts格式正确
- [ ] Provider路由逻辑健壮
- [ ] Fallback机制正常工作
- [ ] 所有测试通过

---

### Day 4: UltraThinkEngine集成

#### 任务 4.1: 修改 `ultra_think.py`
- [ ] 导入reducer模块
  ```python
  from .reducers import (
      BaseReducer,
      ConfidenceVotingReducer,
      PairwiseJudgeReducer,
      AdversarialJudgeReducer,
      HybridReducer
  )
  ```
- [ ] 在 `UltraThinkEngine.__init__()` 中添加 `_init_reducer()` 调用
- [ ] 实现 `_init_reducer()` 方法
  - 读取配置中的 `reducer.mode`
  - 根据mode实例化对应的reducer
  - 如果mode为"synthesis"或未指定,设置reducer为None
- [ ] 修改 `_synthesize_results()` 方法
  - 如果 `self.reducer` 存在,使用reducer
  - 否则使用原有的synthesis逻辑(向后兼容)
  - 转换agent_results格式为AgentResult列表
  - 调用 `reducer.reduce()`
  - 更新token usage
  - 返回final_answer
- [ ] 实现 `_legacy_synthesis()` 方法
  - 将原有的synthesis逻辑移到这里
  - 保持向后兼容

#### 任务 4.2: 配置系统更新
- [ ] 在配置schema中添加reducer配置
  ```yaml
  ultra_think:
    reducer:
      mode: "synthesis" | "confidence_voting" | "pairwise_judge" | "adversarial" | "hybrid"
      provider_routing:
        default: "claude"
        # ... 其他角色配置
      cost_budget: 10.0
      # ... 各方案特定配置
  ```
- [ ] 添加配置验证
- [ ] 添加配置文档

#### 任务 4.3: 集成测试
- [ ] 测试reducer为None时的向后兼容性
- [ ] 测试配置加载
- [ ] 测试reducer初始化
- [ ] 测试_synthesize_results调用reducer
- [ ] 测试token usage更新

**验收标准**:
- [ ] 向后兼容性保持
- [ ] 配置系统正常工作
- [ ] 所有集成测试通过
- [ ] 文档完整

---

## 📝 技术规范

### 目录结构
```
mindiv/engine/reducers/
├── __init__.py              # 导出所有公共接口
├── base.py                  # BaseReducer抽象基类
├── types.py                 # 类型定义
├── normalizer.py            # 答案归一化
├── prompts.py               # Prompt模板
├── confidence_extractor.py  # (Phase 1)
├── confidence_voting.py     # (Phase 1)
├── pairwise_judge.py        # (Phase 2)
├── adversarial_judge.py     # (Phase 3)
├── hybrid.py                # (Phase 4)
└── tests/
    ├── test_base.py
    ├── test_types.py
    ├── test_normalizer.py
    └── test_integration.py
```

### BaseReducer接口
```python
class BaseReducer(ABC):
    """所有reducer的抽象基类"""
    
    @abstractmethod
    async def reduce(
        self, 
        agent_results: List[AgentResult],
        problem: str
    ) -> ReducerResult:
        """主reduce方法,子类必须实现"""
        pass
    
    async def _call_llm_for_role(
        self,
        role: str,
        messages: List[Dict],
        **kwargs
    ) -> Any:
        """为特定角色调用LLM,支持provider路由"""
        pass
```

---

## 🧪 测试要求

### 单元测试
- [ ] `test_types.py` - 测试所有数据类型
- [ ] `test_normalizer.py` - 测试归一化逻辑
- [ ] `test_base.py` - 测试BaseReducer的非抽象方法
- [ ] 测试覆盖率 > 85%

### 集成测试
- [ ] `test_integration.py` - 测试与UltraThinkEngine的集成
- [ ] 测试配置加载
- [ ] 测试向后兼容性

---

## ⚠️ 风险和注意事项

1. **向后兼容性**: 必须确保不破坏现有的synthesis功能
   - 缓解: 保留原有逻辑,通过配置选择是否使用reducer

2. **Provider API差异**: 不同provider的API可能不一致
   - 缓解: 在BaseReducer中统一封装,处理差异

3. **成本控制**: Reducer可能导致额外的LLM调用
   - 缓解: 实现成本预算检查,超限时抛出异常

4. **类型安全**: Python的类型系统较弱
   - 缓解: 使用dataclass和类型注解,运行mypy检查

---

## 📚 参考资料

- mindiv现有代码: `mindiv/engine/ultra_think.py`
- thinkmesh参考实现: `/Users/zhenhuang/Programs/thinkmesh/src/thinkmesh/reduce/`
- Python dataclass文档: https://docs.python.org/3/library/dataclasses.html
- Python ABC文档: https://docs.python.org/3/library/abc.html

---

## ✨ 完成标志

Phase 0完成的标志:
- [ ] 所有交付物已创建
- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 代码review通过
- [ ] 文档完整
- [ ] 可以开始Phase 1/2/3/4的开发

---

**下一步**: 完成Phase 0后,根据优先级进入Phase 3 (对抗性评判)

