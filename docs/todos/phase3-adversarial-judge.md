# Phase 3: 对抗性评判 (Adversarial Judging) ⭐

## 📋 概述

**目标**: 实现基于CourtEval/DEBATE框架的对抗性评判系统,使用Grader/Critic/Defender三角色进行多轮对抗评估。

**重要性**: 🌟 **用户特别感兴趣的方案** - 这是最复杂但也最有潜力的方案,适合科研级难题解决。

**预估时间**: 7-8天

**优先级**: 🔴 高 (用户优先级)

---

## 🎯 交付物清单

- [ ] `adversarial_judge.py` - AdversarialJudgeReducer实现
- [ ] Grader角色实现(初始评分 + 最终裁决)
- [ ] Critic角色实现
- [ ] Defender角色实现
- [ ] 多轮对抗逻辑
- [ ] 多Provider角色分配系统
- [ ] 并行化评估
- [ ] 完整的元数据记录
- [ ] 科研级增强功能
- [ ] 单元测试和集成测试
- [ ] 使用文档

---

## 🔗 前置条件

- [x] Phase 0 已完成
- [x] BaseReducer抽象基类可用
- [x] Provider路由系统可用
- [x] 答案归一化工具可用

---

## ✅ 详细任务清单

### Day 1: 角色Prompt设计和验证

#### 任务 1.1: 设计Grader Prompts
- [ ] 设计 `GRADER_INITIAL_PROMPT`
  - 评分标准: Correctness (40%), Rigor (30%), Completeness (20%), Clarity (10%)
  - 输出格式: JSON with scores, strengths, weaknesses
  - 添加示例输入输出
- [ ] 设计 `GRADER_FINAL_PROMPT`
  - 综合Critic和Defender的意见
  - 输出: final_score, score_change, accepted/rejected arguments
  - 添加示例
- [ ] 在 `prompts.py` 中实现
- [ ] 编写prompt单元测试

#### 任务 1.2: 设计Critic Prompt
- [ ] 设计 `CRITIC_PROMPT`
  - 找出逻辑错误、缺失步骤、不合理假设
  - 评估Grader的bias
  - 输出: critical_issues列表,每个issue包含type, severity, evidence
  - 添加"be fair, don't nitpick"指令
- [ ] 在 `prompts.py` 中实现
- [ ] 编写prompt单元测试

#### 任务 1.3: 设计Defender Prompt
- [ ] 设计 `DEFENDER_PROMPT`
  - 回应每个criticism
  - 三种回应类型: acknowledge, refute, clarify
  - 输出: responses列表,每个response包含argument和evidence
  - 添加"be honest"指令
- [ ] 在 `prompts.py` 中实现
- [ ] 编写prompt单元测试

#### 任务 1.4: Prompt验证
- [ ] 使用真实问题测试每个prompt
- [ ] 验证JSON输出格式正确
- [ ] 验证角色行为符合预期
- [ ] 调整prompt直到满意

**验收标准**:
- [ ] 所有prompts格式正确,支持变量替换
- [ ] 输出JSON格式稳定可解析
- [ ] 角色行为符合设计意图
- [ ] 有完整的使用示例

---

### Day 2: Grader实现

#### 任务 2.1: 实现初始评分
- [ ] 创建 `adversarial_judge.py`
- [ ] 实现 `AdversarialJudgeReducer(BaseReducer)` 类
- [ ] 实现 `_initial_grading(candidate, problem)` 方法
  - 构建messages with GRADER_INITIAL_PROMPT
  - 调用 `_call_llm_for_role("grader", messages)`
  - 解析JSON输出
  - 验证分数范围(0-100)
  - 处理解析错误(重试最多3次)
- [ ] 实现分数验证逻辑
  - 检查total_score = correctness + rigor + completeness + clarity
  - 检查各项分数在合理范围内

#### 任务 2.2: 实现最终裁决
- [ ] 实现 `_final_judgment(initial, critic, defender)` 方法
  - 构建messages with GRADER_FINAL_PROMPT
  - 包含initial_evaluation, critic_output, defender_output
  - 调用 `_call_llm_for_role("final_grader", messages)`
  - 解析JSON输出
  - 验证score_change合理性
  - 记录accepted/rejected arguments

#### 任务 2.3: 编写Grader测试
- [ ] 测试初始评分
  - 正常情况
  - JSON解析失败的情况
  - 分数不合理的情况
- [ ] 测试最终裁决
  - 正常情况
  - 综合多方意见的情况
- [ ] Mock LLM调用,测试逻辑

**验收标准**:
- [ ] Grader能正确评分
- [ ] JSON解析robust
- [ ] 错误处理完善
- [ ] 测试覆盖率 > 85%

---

### Day 3: Critic实现

#### 任务 3.1: 实现Critic挑战
- [ ] 实现 `_critic_challenge(candidate, problem, grading)` 方法
  - 构建messages with CRITIC_PROMPT
  - 包含solution, reasoning, grader_evaluation
  - 调用 `_call_llm_for_role("critic", messages)`
  - 解析critical_issues列表
  - 验证每个issue的格式
  - 按severity排序issues

#### 任务 3.2: 实现Critic配置
- [ ] 支持配置Critic的"攻击性"
  - `aggressiveness: "low" | "medium" | "high"`
  - 影响prompt中的指令强度
- [ ] 支持配置Critic的关注点
  - `focus: ["logical_errors", "missing_steps", "assumptions", "grader_bias"]`
  - 动态调整prompt
- [ ] 实现分数调整范围限制
  - 默认: -50 to 0
  - 可配置

#### 任务 3.3: 编写Critic测试
- [ ] 测试正常挑战
- [ ] 测试不同aggressiveness级别
- [ ] 测试不同focus配置
- [ ] 测试分数调整范围
- [ ] Mock LLM调用

**验收标准**:
- [ ] Critic能找出合理的问题
- [ ] 配置系统正常工作
- [ ] 不会过度批判
- [ ] 测试覆盖率 > 85%

---

### Day 4: Defender实现

#### 任务 4.1: 实现Defender辩护
- [ ] 实现 `_defender_response(candidate, problem, grading, critic)` 方法
  - 构建messages with DEFENDER_PROMPT
  - 包含solution, grader_evaluation, critic_output
  - 调用 `_call_llm_for_role("defender", messages)`
  - 解析responses列表
  - 验证每个response对应一个criticism
  - 分类response_type

#### 任务 4.2: 实现Defender配置
- [ ] 支持配置Defender的"防御性"
  - `defensiveness: "low" | "balanced" | "high"`
- [ ] 支持配置Defender的策略
  - `strategy: "evidence_based" | "logical" | "comprehensive"`
- [ ] 实现分数调整范围限制
  - 默认: -20 to +20
  - 可配置

#### 任务 4.3: 编写Defender测试
- [ ] 测试正常辩护
- [ ] 测试不同defensiveness级别
- [ ] 测试不同strategy
- [ ] 测试response与criticism的对应
- [ ] Mock LLM调用

**验收标准**:
- [ ] Defender能有效辩护
- [ ] 配置系统正常工作
- [ ] 不会盲目辩护
- [ ] 测试覆盖率 > 85%

---

### Day 5: 多轮对抗逻辑

#### 任务 5.1: 实现单轮对抗
- [ ] 实现 `_evaluate_candidate(candidate, problem)` 方法
  - 调用_initial_grading
  - 调用_critic_challenge
  - 调用_defender_response
  - 调用_final_judgment
  - 返回完整的evaluation结果
- [ ] 实现元数据记录
  - 记录每个阶段的输出
  - 记录分数变化
  - 记录token使用

#### 任务 5.2: 实现多轮对抗
- [ ] 实现 `_multi_round_adversarial(candidate, problem, rounds)` 方法
  - 循环执行rounds轮
  - 每轮: Critic → Defender → Grader更新
  - 记录每轮的分数变化
  - 实现收敛检测
    - 如果分数变化 < 5,提前终止
    - 如果分数震荡,提前终止
  - 返回最终评分和完整历史

#### 任务 5.3: 实现主reduce方法
- [ ] 实现 `reduce(agent_results, problem)` 方法
  - 对每个candidate调用_evaluate_candidate
  - 选择最高分的candidate
  - 构建ReducerResult
  - 包含完整的元数据

#### 任务 5.4: 编写多轮对抗测试
- [ ] 测试单轮对抗
- [ ] 测试多轮对抗
- [ ] 测试收敛检测
- [ ] 测试分数震荡处理
- [ ] 端到端测试

**验收标准**:
- [ ] 单轮对抗正常工作
- [ ] 多轮对抗逻辑正确
- [ ] 收敛检测有效
- [ ] 元数据完整
- [ ] 测试覆盖率 > 85%

---

### Day 6: Provider路由和并行化

#### 任务 6.1: 实现多Provider角色分配
- [ ] 配置schema设计
  ```yaml
  adversarial:
    provider_routing:
      grader: "claude"
      critic: "gemini"
      defender: "openai"
      final_grader: "claude"
  ```
- [ ] 在每个角色方法中使用正确的provider
- [ ] 实现provider fallback
  - 如果指定provider失败,使用默认provider
  - 记录fallback事件
- [ ] 测试多provider配置

#### 任务 6.2: 实现并行化评估
- [ ] 使用asyncio.gather并行评估所有candidates
  ```python
  evaluations = await asyncio.gather(*[
      self._evaluate_candidate(result, problem)
      for result in agent_results
  ])
  ```
- [ ] 确保并行调用的安全性
- [ ] 测试并行性能提升

#### 任务 6.3: 成本控制
- [ ] 实现成本预算检查
  - 在每次LLM调用前检查
  - 超限时抛出CostBudgetExceededError
- [ ] 实现early stopping
  - 如果某个candidate分数 > 90,跳过其他
  - 可配置阈值
- [ ] 实现"lite"模式
  - 只对top-k candidates进行对抗评判
  - 其他使用简单评分

**验收标准**:
- [ ] 多provider配置正常工作
- [ ] 并行化提升性能
- [ ] 成本控制有效
- [ ] Early stopping正常工作

---

### Day 7: 集成测试和调试

#### 任务 7.1: 端到端测试
- [ ] 准备测试数据
  - 数学问题
  - 编程问题
  - 推理问题
- [ ] 测试完整流程
  - 从agent_results到final_answer
  - 验证结果正确性
  - 验证元数据完整性
- [ ] 测试不同配置
  - 不同rounds
  - 不同provider组合
  - 不同aggressiveness/defensiveness

#### 任务 7.2: 性能测试
- [ ] 测试单个candidate的评估时间
- [ ] 测试并行评估的性能
- [ ] 测试token使用量
- [ ] 测试成本

#### 任务 7.3: 错误处理测试
- [ ] 测试LLM调用失败
- [ ] 测试JSON解析失败
- [ ] 测试provider不可用
- [ ] 测试成本超限
- [ ] 验证所有错误都被正确处理

**验收标准**:
- [ ] 所有端到端测试通过
- [ ] 性能满足要求
- [ ] 错误处理robust
- [ ] 无明显bug

---

### Day 8: 科研级增强

#### 任务 8.1: 专家模式
- [ ] 实现问题类型检测
  - 数学问题
  - 编程问题
  - 物理问题
  - 其他
- [ ] 为每种类型定制prompt
  - 数学: "You are a mathematics professor..."
  - 编程: "You are a senior software engineer..."
  - 物理: "You are a physics researcher..."
- [ ] 配置系统支持
  ```yaml
  expert_mode: true
  expert_mapping:
    math: "custom prompt"
    coding: "custom prompt"
  ```

#### 任务 8.2: 多样性奖励
- [ ] 实现多样性检测
  - 如果不同provider的Grader给出相似分数,增加置信度
- [ ] 实现diversity_bonus
  - 配置: `diversity_bonus: 0.1`
  - 如果3个不同provider都给出80+分,bonus +10%

#### 任务 8.3: 元评估
- [ ] 实现Critic质量评估
  - Critic找到的问题是否真实存在?
  - 记录Critic的准确率
- [ ] 实现Defender质量评估
  - Defender的辩护是否有效?
  - 记录Defender的成功率
- [ ] 生成元评估报告

#### 任务 8.4: 完整轨迹记录
- [ ] 记录所有LLM调用
  - Prompt
  - Response
  - Token使用
  - 时间戳
- [ ] 生成可视化报告
  - 分数变化曲线
  - 对抗过程图
  - Token使用分布
- [ ] 支持导出为JSON/HTML

**验收标准**:
- [ ] 专家模式正常工作
- [ ] 多样性奖励有效
- [ ] 元评估提供有价值的insights
- [ ] 轨迹记录完整
- [ ] 报告清晰易读

---

## 📝 技术规范

### AdversarialJudgeReducer接口
```python
class AdversarialJudgeReducer(BaseReducer):
    async def reduce(
        self, 
        agent_results: List[AgentResult],
        problem: str
    ) -> ReducerResult:
        """主reduce方法"""
        pass
    
    async def _evaluate_candidate(
        self,
        candidate: AgentResult,
        problem: str
    ) -> Dict[str, Any]:
        """对单个candidate进行对抗性评判"""
        pass
    
    async def _initial_grading(...) -> Dict:
        """Grader初始评分"""
        pass
    
    async def _critic_challenge(...) -> Dict:
        """Critic挑战"""
        pass
    
    async def _defender_response(...) -> Dict:
        """Defender辩护"""
        pass
    
    async def _final_judgment(...) -> Dict:
        """Grader最终裁决"""
        pass
```

### 配置Schema
```yaml
adversarial:
  rounds: 1  # 对抗轮数
  expert_mode: false
  diversity_bonus: 0.0
  
  provider_routing:
    grader: "claude"
    critic: "gemini"
    defender: "openai"
    final_grader: "claude"
  
  critic:
    aggressiveness: "medium"
    focus: ["logical_errors", "missing_steps"]
  
  defender:
    defensiveness: "balanced"
    strategy: "evidence_based"
  
  grader:
    strictness: "medium"
    weight_reasoning: 0.7
    weight_answer: 0.3
  
  cost_control:
    budget: 10.0
    early_stopping_threshold: 90
    lite_mode: false
    lite_mode_top_k: 3
```

---

## 🧪 测试要求

### 单元测试
- [ ] `test_adversarial_grader.py` - 测试Grader
- [ ] `test_adversarial_critic.py` - 测试Critic
- [ ] `test_adversarial_defender.py` - 测试Defender
- [ ] `test_adversarial_multi_round.py` - 测试多轮对抗
- [ ] 测试覆盖率 > 85%

### 集成测试
- [ ] `test_adversarial_integration.py` - 端到端测试
- [ ] 测试不同配置组合
- [ ] 测试多provider场景

### 性能测试
- [ ] 测试单candidate评估时间 < 30s
- [ ] 测试并行评估性能提升 > 2x
- [ ] 测试token使用在预期范围内

---

## ⚠️ 风险和注意事项

1. **成本过高**: 对抗评判需要多次LLM调用
   - 缓解: 实现lite模式,early stopping,成本预算

2. **角色崩溃**: LLM可能不遵守角色设定
   - 缓解: 强化prompt,验证输出,重试机制

3. **过度批判**: Critic可能过于挑剔
   - 缓解: 在prompt中加入"be fair",限制分数调整范围

4. **不收敛**: 多轮对抗可能不收敛
   - 缓解: 设置最大轮数,检测震荡,提前终止

5. **JSON解析失败**: LLM输出可能不是有效JSON
   - 缓解: 重试机制,fallback到文本解析

---

## 📚 参考资料

- CourtEval论文: "When AIs Judge AIs" (arXiv:2508.02994v1)
- DEBATE框架
- thinkmesh judge实现
- mindiv Phase 0基础设施

---

## ✨ 完成标志

Phase 3完成的标志:
- [ ] 所有交付物已创建
- [ ] 所有单元测试通过 (覆盖率 > 85%)
- [ ] 集成测试通过
- [ ] 性能测试通过
- [ ] 科研级增强功能完成
- [ ] 代码review通过
- [ ] 文档完整
- [ ] 在真实问题上验证有效

---

**下一步**: 完成Phase 3后,可以进入Phase 1 (置信度投票) 或 Phase 2 (成对Judge)

