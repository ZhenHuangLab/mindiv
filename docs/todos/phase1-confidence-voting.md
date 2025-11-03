# Phase 1: 置信度加权投票 (Confidence-Weighted Voting)

## 📋 概述

**目标**: 基于2025年SOTA论文"Confidence Improves Self-Consistency in LLMs",实现置信度加权的多数投票系统。

**重要性**: 成本效益最优的方案,可减少40%+计算成本,同时提升准确性。

**预估时间**: 4-5天

**优先级**: 🟡 中高 (为Phase 4做准备)

---

## 🎯 交付物清单

- [ ] `confidence_extractor.py` - 置信度提取模块
- [ ] `confidence_voting.py` - ConfidenceVotingReducer实现
- [ ] P(True)方法实现 (OpenAI/Claude)
- [ ] Verbal Confidence方法实现 (所有providers)
- [ ] 多Provider支持和Fallback机制
- [ ] Softmax归一化 + 温度缩放
- [ ] 加权投票逻辑
- [ ] 温度参数调优工具
- [ ] 单元测试和集成测试
- [ ] 使用文档

---

## 🔗 前置条件

- [x] Phase 0 已完成
- [x] BaseReducer抽象基类可用
- [x] AnswerNormalizer可用
- [x] Provider路由系统可用

---

## ✅ 详细任务清单

### Day 1: 答案归一化增强

#### 任务 1.1: 增强数值归一化
- [ ] 在 `normalizer.py` 中增强 `normalize_numeric()`
- [ ] 支持更多数值格式
  - 分数: "1/2" → "0.5"
  - 百分比: "50%" → "0.5"
  - 科学计数法: "1e-5" → "0.00001"
  - 带单位: "42 meters" → "42"
- [ ] 处理多个数值的情况
  - 提取第一个数值
  - 或提取最后一个数值(可配置)
- [ ] 编写测试用例

#### 任务 1.2: 增强LaTeX归一化
- [ ] 安装sympy依赖
- [ ] 实现LaTeX解析
  - 使用sympy.parsing.latex
  - 规范化表达式
  - 处理等价形式: "x^2" ≡ "x*x"
- [ ] 处理解析失败
  - Fallback到文本归一化
  - 记录失败案例
- [ ] 编写测试用例

#### 任务 1.3: 批量归一化优化
- [ ] 实现 `normalize_batch(answers)` 方法
- [ ] 缓存归一化结果
- [ ] 性能优化

**验收标准**:
- [ ] 支持所有常见答案格式
- [ ] 归一化准确率 > 95%
- [ ] 所有测试通过

---

### Day 2: 置信度提取 - OpenAI/Claude

#### 任务 2.1: 实现P(True)方法
- [ ] 创建 `confidence_extractor.py`
- [ ] 实现 `ConfidenceExtractor` 类
- [ ] 实现 `_extract_p_true(solution, problem, provider)` 方法
  - 构建P_TRUE_PROMPT
  - 调用LLM with `logprobs=True, max_tokens=1`
  - 提取"True"和"False"的logprobs
  - 计算P(True) = exp(logprob_true) / (exp(logprob_true) + exp(logprob_false))
  - 返回置信度 [0.0, 1.0]

#### 任务 2.2: OpenAI实现
- [ ] 实现OpenAI的logprobs提取
  ```python
  response = await openai.chat.completions.create(
      model="gpt-4",
      messages=messages,
      logprobs=True,
      top_logprobs=5,
      max_tokens=1
  )
  logprobs = response.choices[0].logprobs.content[0].top_logprobs
  ```
- [ ] 从logprobs中提取P(True)
- [ ] 处理"True"不在top_logprobs的情况
- [ ] 测试

#### 任务 2.3: Claude实现
- [ ] 调研Claude的logprobs支持
- [ ] 如果支持,实现类似OpenAI的逻辑
- [ ] 如果不支持,标记为fallback到verbal
- [ ] 测试

**验收标准**:
- [ ] P(True)方法在OpenAI上正常工作
- [ ] Claude支持情况明确
- [ ] 置信度值合理 [0.0, 1.0]
- [ ] 测试覆盖率 > 85%

---

### Day 3: 置信度提取 - Gemini和Fallback

#### 任务 3.1: Gemini支持调研
- [ ] 调研Gemini API的logprobs支持
- [ ] 如果支持,实现P(True)方法
- [ ] 如果不支持,使用verbal confidence
- [ ] 文档记录Gemini的支持情况

#### 任务 3.2: 实现Verbal Confidence方法
- [ ] 实现 `_extract_verbal(solution, problem, provider)` 方法
  - 构建CONFIDENCE_EXTRACTION_PROMPT
  - 要求LLM输出0-100的置信度
  - 解析输出,提取数值
  - 归一化到 [0.0, 1.0]
  - 处理解析失败(重试或默认0.5)

#### 任务 3.3: 实现Auto方法
- [ ] 实现 `extract(solution, problem, provider)` 方法
  - 根据provider自动选择方法
  - OpenAI: 优先P(True), fallback到verbal
  - Claude: 优先P(True), fallback到verbal
  - Gemini: 根据调研结果选择
  - 其他: verbal
- [ ] 实现fallback逻辑
  - 如果P(True)失败,自动尝试verbal
  - 记录fallback事件
  - 如果verbal也失败,返回默认置信度0.5

#### 任务 3.4: 批量提取优化
- [ ] 实现 `extract_batch(solutions, problem, provider)` 方法
- [ ] 并行调用LLM
- [ ] 性能优化

**验收标准**:
- [ ] 所有providers都有可用的置信度提取方法
- [ ] Fallback机制robust
- [ ] 批量提取性能优秀
- [ ] 测试覆盖率 > 85%

---

### Day 4: 加权投票实现

#### 任务 4.1: 实现ConfidenceVotingReducer
- [ ] 创建 `confidence_voting.py`
- [ ] 实现 `ConfidenceVotingReducer(BaseReducer)` 类
- [ ] 实现 `__init__(config, engine)` 方法
  - 初始化ConfidenceExtractor
  - 初始化AnswerNormalizer
  - 读取配置(temperature, method等)

#### 任务 4.2: 实现reduce方法
- [ ] 实现 `reduce(agent_results, problem)` 方法
  ```python
  async def reduce(self, agent_results, problem):
      # 1. 归一化所有答案
      normalized = [(normalizer.normalize(r.final_solution), r) 
                    for r in agent_results]
      
      # 2. 提取置信度
      confidences = await self._extract_confidences(agent_results, problem)
      
      # 3. 加权投票
      votes = self._weighted_vote(normalized, confidences)
      
      # 4. 选择最高权重的答案
      best_answer = max(votes, key=votes.get)
      
      # 5. 构建ReducerResult
      return ReducerResult(...)
  ```

#### 任务 4.3: 实现置信度提取
- [ ] 实现 `_extract_confidences(agent_results, problem)` 方法
  - 并行提取所有agent的置信度
  - 使用配置的method ("p_true" | "verbal" | "auto")
  - 使用配置的provider或默认provider
  - 记录token使用

#### 任务 4.4: 实现加权投票
- [ ] 实现 `_weighted_vote(normalized, confidences)` 方法
  ```python
  def _weighted_vote(self, normalized, confidences):
      # 按归一化答案分组
      votes = defaultdict(lambda: {"weight": 0.0, "results": []})
      for (norm_answer, result), conf in zip(normalized, confidences):
          votes[norm_answer]["weight"] += conf
          votes[norm_answer]["results"].append(result)
      
      # Softmax归一化 + 温度缩放
      temperature = self.config.get("temperature", 0.5)
      weights = {
          ans: math.exp(data["weight"] / temperature)
          for ans, data in votes.items()
      }
      total = sum(weights.values())
      normalized_weights = {ans: w/total for ans, w in weights.items()}
      
      return normalized_weights
  ```

#### 任务 4.5: 实现元数据记录
- [ ] 记录投票分布
- [ ] 记录原始置信度
- [ ] 记录归一化后的权重
- [ ] 记录token使用

**验收标准**:
- [ ] reduce方法正常工作
- [ ] 加权投票逻辑正确
- [ ] 元数据完整
- [ ] 测试覆盖率 > 85%

---

### Day 5: 温度调优和集成测试

#### 任务 5.1: 实现温度调优工具
- [ ] 创建 `tools/tune_temperature.py`
- [ ] 实现grid search
  - 温度范围: [0.1, 0.3, 0.5, 0.7, 1.0]
  - 在验证集上评估每个温度
  - 选择最佳温度
- [ ] 支持per-provider的温度配置
- [ ] 生成调优报告

#### 任务 5.2: Per-provider置信度校准
- [ ] 实现置信度校准
  - 不同provider的置信度可能不可比
  - 收集统计数据: provider → 平均置信度
  - 实现归一化: conf_calibrated = (conf - mean) / std
- [ ] 配置支持
  ```yaml
  confidence_voting:
    calibration:
      enabled: true
      provider_stats:
        openai: {mean: 0.7, std: 0.15}
        claude: {mean: 0.65, std: 0.2}
        gemini: {mean: 0.6, std: 0.18}
  ```

#### 任务 5.3: 集成测试
- [ ] 准备测试数据
  - 数学问题 (有明确答案)
  - 多个agent给出不同答案
  - 包含置信度信息
- [ ] 端到端测试
  - 从agent_results到final_answer
  - 验证答案正确性
  - 验证置信度合理性
- [ ] 测试不同配置
  - 不同temperature
  - 不同method (p_true vs verbal)
  - 不同provider

#### 任务 5.4: 性能测试
- [ ] 测试置信度提取时间
- [ ] 测试并行提取性能
- [ ] 测试token使用量
- [ ] 与原有synthesis对比

**验收标准**:
- [ ] 温度调优工具正常工作
- [ ] 置信度校准有效
- [ ] 所有集成测试通过
- [ ] 性能满足要求
- [ ] Token使用在预期范围内

---

## 📝 技术规范

### ConfidenceExtractor接口
```python
class ConfidenceExtractor:
    async def extract(
        self,
        solution: str,
        problem: str,
        provider: str
    ) -> float:
        """提取置信度,自动选择最佳方法"""
        pass
    
    async def _extract_p_true(...) -> float:
        """P(True)方法"""
        pass
    
    async def _extract_verbal(...) -> float:
        """Verbal confidence方法"""
        pass
    
    async def extract_batch(...) -> List[float]:
        """批量提取"""
        pass
```

### ConfidenceVotingReducer接口
```python
class ConfidenceVotingReducer(BaseReducer):
    async def reduce(
        self,
        agent_results: List[AgentResult],
        problem: str
    ) -> ReducerResult:
        """主reduce方法"""
        pass
    
    async def _extract_confidences(...) -> List[float]:
        """提取所有agent的置信度"""
        pass
    
    def _weighted_vote(...) -> Dict[str, float]:
        """加权投票"""
        pass
```

### 配置Schema
```yaml
confidence_voting:
  method: "auto"  # "p_true" | "verbal" | "auto"
  temperature: 0.5
  normalization: true
  
  provider_routing:
    confidence_extraction: "openai"  # 专用provider
  
  calibration:
    enabled: false
    provider_stats:
      openai: {mean: 0.7, std: 0.15}
      claude: {mean: 0.65, std: 0.2}
      gemini: {mean: 0.6, std: 0.18}
```

---

## 🧪 测试要求

### 单元测试
- [ ] `test_confidence_extractor.py` - 测试置信度提取
- [ ] `test_confidence_voting.py` - 测试加权投票
- [ ] 测试覆盖率 > 85%

### 集成测试
- [ ] `test_confidence_integration.py` - 端到端测试
- [ ] 测试不同provider
- [ ] 测试不同配置

### 性能测试
- [ ] 置信度提取时间 < 5s per agent
- [ ] 并行提取性能提升 > 3x
- [ ] Token使用合理

---

## ⚠️ 风险和注意事项

1. **Gemini logprobs不支持**: 可能只能用verbal方法
   - 缓解: 实现robust的verbal fallback

2. **置信度不准确**: 模型的置信度可能不可靠
   - 缓解: 温度调优,置信度校准

3. **归一化失败**: 复杂答案可能无法正确归一化
   - 缓解: 记录失败案例,fallback到原始答案

4. **不同provider置信度不可比**: 
   - 缓解: Per-provider校准

---

## 📚 参考资料

- CISC论文: "Confidence Improves Self-Consistency in LLMs" (arXiv:2502.06233v1)
- OpenAI logprobs文档
- thinkmesh majority reducer
- mindiv Phase 0基础设施

---

## ✨ 完成标志

Phase 1完成的标志:
- [ ] 所有交付物已创建
- [ ] 所有单元测试通过 (覆盖率 > 85%)
- [ ] 集成测试通过
- [ ] 性能测试通过
- [ ] 温度调优完成
- [ ] 文档完整
- [ ] 在真实问题上验证有效

---

**下一步**: 完成Phase 1后,可以进入Phase 4 (混合策略) 或继续Phase 2 (成对Judge)

