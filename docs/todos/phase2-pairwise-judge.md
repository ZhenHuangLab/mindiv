# Phase 2: 成对Judge (Pairwise Judge)

## 📋 概述

**目标**: 使用LLM作为judge,通过成对比较解决方案,锦标赛式选出最佳答案。

**重要性**: 评估推理过程而非仅看最终答案,适合复杂问题。

**预估时间**: 4-5天

**优先级**: 🟡 中 (补充方案)

---

## 🎯 交付物清单

- [ ] `pairwise_judge.py` - PairwiseJudgeReducer实现
- [ ] Tournament配对策略
- [ ] All-pairs配对策略
- [ ] Judge prompt设计
- [ ] 循环依赖检测和解决
- [ ] 平局处理机制
- [ ] Judge bias分析工具
- [ ] 单元测试和集成测试
- [ ] 使用文档

---

## 🔗 前置条件

- [x] Phase 0 已完成
- [x] BaseReducer抽象基类可用
- [x] Provider路由系统可用

---

## ✅ 详细任务清单

### Day 1: 配对策略实现

#### 任务 1.1: 实现Tournament配对
- [ ] 创建 `pairwise_judge.py`
- [ ] 实现 `PairwiseJudgeReducer(BaseReducer)` 类
- [ ] 实现 `_tournament_pairs(candidates)` 方法
  ```python
  def _tournament_pairs(self, candidates):
      """锦标赛配对: O(n log n)"""
      pairs = []
      current_round = candidates[:]
      
      while len(current_round) > 1:
          round_pairs = []
          for i in range(0, len(current_round)-1, 2):
              round_pairs.append((current_round[i], current_round[i+1]))
          pairs.extend(round_pairs)
          
          # 下一轮的候选
          current_round = []  # 将由judge结果填充
      
      return pairs
  ```
- [ ] 处理奇数个候选的情况
  - 最后一个候选直接晋级
- [ ] 编写测试

#### 任务 1.2: 实现All-pairs配对
- [ ] 实现 `_all_pairs(candidates)` 方法
  ```python
  def _all_pairs(self, candidates):
      """全配对: O(n²)"""
      pairs = []
      for i in range(len(candidates)):
          for j in range(i+1, len(candidates)):
              pairs.append((candidates[i], candidates[j]))
      return pairs
  ```
- [ ] 编写测试

#### 任务 1.3: 实现配对策略选择
- [ ] 实现 `_create_pairs(candidates, strategy)` 方法
  - 根据strategy选择配对方法
  - "tournament" → _tournament_pairs
  - "all_pairs" → _all_pairs
- [ ] 配置支持
  ```yaml
  pairwise_judge:
    strategy: "tournament"  # or "all_pairs"
  ```

**验收标准**:
- [ ] Tournament配对正确
- [ ] All-pairs配对正确
- [ ] 奇数候选处理正确
- [ ] 测试覆盖率 > 85%

---

### Day 2: Judge实现

#### 任务 2.1: 设计Judge Prompt
- [ ] 在 `prompts.py` 中设计 `JUDGE_PROMPT`
  ```
  You are an expert judge evaluating mathematical/reasoning solutions.
  
  Problem: {problem}
  
  Solution A:
  {solution_a}
  Reasoning: {reasoning_a}
  
  Solution B:
  {solution_b}
  Reasoning: {reasoning_b}
  
  Evaluate both solutions based on:
  1. Correctness of the final answer (40%)
  2. Rigor of the reasoning process (30%)
  3. Completeness of the proof/explanation (20%)
  4. Clarity and presentation (10%)
  
  Output JSON:
  {
    "winner": "A" | "B" | "tie",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation",
    "scores": {
      "A": {"correctness": 0-40, "rigor": 0-30, "completeness": 0-20, "clarity": 0-10},
      "B": {"correctness": 0-40, "rigor": 0-30, "completeness": 0-20, "clarity": 0-10}
    }
  }
  ```
- [ ] 添加示例
- [ ] 测试prompt

#### 任务 2.2: 实现单次Judge
- [ ] 实现 `_judge_pair(candidate_a, candidate_b, problem)` 方法
  - 构建messages with JUDGE_PROMPT
  - 随机化A/B顺序(减少bias)
  - 调用 `_call_llm_for_role("judge", messages)`
  - 解析JSON输出
  - 验证winner字段
  - 处理解析失败(重试最多3次)
- [ ] 实现A/B顺序随机化
  ```python
  if random.random() < 0.5:
      # 交换A和B
      candidate_a, candidate_b = candidate_b, candidate_a
      swap = True
  ```
- [ ] 如果swap,需要转换winner结果

#### 任务 2.3: 实现多次Judge
- [ ] 实现 `_judge_pair_multiple(candidate_a, candidate_b, problem, n=3)` 方法
  - 对同一对进行n次judge
  - 取多数结果
  - 平均confidence
  - 用于减少不一致性
- [ ] 配置支持
  ```yaml
  pairwise_judge:
    multiple_judges: 3  # 每对judge 3次
  ```

**验收标准**:
- [ ] Judge prompt设计合理
- [ ] 单次judge正常工作
- [ ] A/B随机化有效
- [ ] 多次judge逻辑正确
- [ ] 测试覆盖率 > 85%

---

### Day 3: 循环依赖处理

#### 任务 3.1: 实现循环检测
- [ ] 实现 `_detect_cycles(comparison_graph)` 方法
  - 使用DFS检测循环
  - 返回所有循环
  ```python
  def _detect_cycles(self, graph):
      """检测有向图中的循环"""
      visited = set()
      rec_stack = set()
      cycles = []
      
      def dfs(node, path):
          visited.add(node)
          rec_stack.add(node)
          path.append(node)
          
          for neighbor in graph.get(node, []):
              if neighbor not in visited:
                  dfs(neighbor, path[:])
              elif neighbor in rec_stack:
                  # 找到循环
                  cycle_start = path.index(neighbor)
                  cycles.append(path[cycle_start:])
          
          rec_stack.remove(node)
      
      for node in graph:
          if node not in visited:
              dfs(node, [])
      
      return cycles
  ```

#### 任务 3.2: 实现循环解决
- [ ] 实现 `_resolve_cycles(comparison_graph)` 方法
  - 策略1: 使用置信度打破循环
    - 找到循环中置信度最低的边
    - 移除该边
  - 策略2: 使用三方比较
    - 对循环中的候选进行三方judge
  - 策略3: Fallback到置信度投票
- [ ] 配置支持
  ```yaml
  pairwise_judge:
    cycle_resolution: "confidence" | "three_way" | "fallback"
  ```

#### 任务 3.3: 构建比较图
- [ ] 实现 `_build_comparison_graph(judge_results)` 方法
  - 从judge结果构建有向图
  - A > B → 边 A → B
  - 记录每条边的置信度

**验收标准**:
- [ ] 循环检测正确
- [ ] 循环解决有效
- [ ] 比较图构建正确
- [ ] 测试覆盖率 > 85%

---

### Day 4: 平局处理和Provider路由

#### 任务 4.1: 实现平局处理
- [ ] 实现 `_handle_tie(candidate_a, candidate_b)` 方法
  - 策略1: 选择置信度高的
  - 策略2: 随机选择
  - 策略3: 重新judge
  - 策略4: 都保留,进入下一轮
- [ ] 配置支持
  ```yaml
  pairwise_judge:
    tie_breaking: "confidence" | "random" | "re_judge" | "keep_both"
  ```

#### 任务 4.2: 实现Provider路由
- [ ] 支持judge专用provider
  ```yaml
  pairwise_judge:
    provider_routing:
      judge: "openai"  # 使用GPT-4作为judge
  ```
- [ ] 在_judge_pair中使用正确的provider
- [ ] 测试多provider配置

#### 任务 4.3: 实现主reduce方法
- [ ] 实现 `reduce(agent_results, problem)` 方法
  ```python
  async def reduce(self, agent_results, problem):
      # 1. 创建配对
      strategy = self.config.get("strategy", "tournament")
      
      if strategy == "tournament":
          winner = await self._tournament_reduce(agent_results, problem)
      elif strategy == "all_pairs":
          winner = await self._all_pairs_reduce(agent_results, problem)
      
      # 2. 构建ReducerResult
      return ReducerResult(
          final_answer=winner.final_solution,
          confidence=winner_confidence,
          metadata={...},
          token_usage=self._get_token_usage()
      )
  ```

#### 任务 4.4: 实现Tournament Reduce
- [ ] 实现 `_tournament_reduce(candidates, problem)` 方法
  - 多轮淘汰
  - 每轮: 配对 → judge → 选出胜者
  - 直到只剩一个候选

#### 任务 4.5: 实现All-pairs Reduce
- [ ] 实现 `_all_pairs_reduce(candidates, problem)` 方法
  - 所有配对都judge
  - 构建比较图
  - 检测和解决循环
  - 选择胜率最高的候选

**验收标准**:
- [ ] 平局处理正常工作
- [ ] Provider路由正确
- [ ] Tournament reduce正确
- [ ] All-pairs reduce正确
- [ ] 测试覆盖率 > 85%

---

### Day 5: Judge Bias分析和集成测试

#### 任务 5.1: 实现Judge Bias分析
- [ ] 创建 `tools/analyze_judge_bias.py`
- [ ] 分析A/B位置bias
  - 统计A胜率 vs B胜率
  - 应该接近50%
- [ ] 分析provider bias
  - 不同provider的judge结果是否一致
- [ ] 分析不一致性
  - 同一对多次judge的结果是否一致
- [ ] 生成分析报告

#### 任务 5.2: 集成测试
- [ ] 准备测试数据
  - 数学问题
  - 多个候选解决方案
  - 包含明显正确和错误的答案
- [ ] 端到端测试
  - Tournament策略
  - All-pairs策略
  - 不同tie_breaking配置
- [ ] 测试循环依赖场景
  - 构造A>B>C>A的情况
  - 验证循环解决正确

#### 任务 5.3: 性能测试
- [ ] 测试judge时间
  - 单次judge < 10s
- [ ] 测试tournament性能
  - O(n log n)复杂度验证
- [ ] 测试all-pairs性能
  - O(n²)复杂度验证
- [ ] 测试token使用量

#### 任务 5.4: 与方案1对比
- [ ] 在相同数据上运行方案1和方案2
- [ ] 对比准确性
- [ ] 对比成本
- [ ] 对比时间
- [ ] 生成对比报告

**验收标准**:
- [ ] Bias分析工具正常工作
- [ ] 所有集成测试通过
- [ ] 性能满足要求
- [ ] 对比报告完整

---

## 📝 技术规范

### PairwiseJudgeReducer接口
```python
class PairwiseJudgeReducer(BaseReducer):
    async def reduce(
        self,
        agent_results: List[AgentResult],
        problem: str
    ) -> ReducerResult:
        """主reduce方法"""
        pass
    
    async def _judge_pair(
        self,
        candidate_a: AgentResult,
        candidate_b: AgentResult,
        problem: str
    ) -> Dict[str, Any]:
        """成对比较"""
        pass
    
    async def _tournament_reduce(...) -> AgentResult:
        """锦标赛式reduce"""
        pass
    
    async def _all_pairs_reduce(...) -> AgentResult:
        """全配对reduce"""
        pass
    
    def _detect_cycles(...) -> List[List]:
        """检测循环"""
        pass
    
    def _resolve_cycles(...) -> Graph:
        """解决循环"""
        pass
```

### 配置Schema
```yaml
pairwise_judge:
  strategy: "tournament"  # or "all_pairs"
  tie_breaking: "confidence"  # or "random" | "re_judge" | "keep_both"
  multiple_judges: 1  # 每对judge几次
  cycle_resolution: "confidence"  # or "three_way" | "fallback"
  
  provider_routing:
    judge: "openai"  # Judge专用provider
```

---

## 🧪 测试要求

### 单元测试
- [ ] `test_pairwise_pairing.py` - 测试配对策略
- [ ] `test_pairwise_judge.py` - 测试judge逻辑
- [ ] `test_pairwise_cycles.py` - 测试循环处理
- [ ] 测试覆盖率 > 85%

### 集成测试
- [ ] `test_pairwise_integration.py` - 端到端测试
- [ ] 测试不同策略
- [ ] 测试循环场景

### 性能测试
- [ ] Tournament: O(n log n)
- [ ] All-pairs: O(n²)
- [ ] 单次judge < 10s

---

## ⚠️ 风险和注意事项

1. **Judge bias**: LLM可能偏好某种风格
   - 缓解: A/B随机化,多次judge

2. **不一致性**: 同一对比较可能得到不同结果
   - 缓解: 多次judge取多数

3. **成本爆炸**: All-pairs策略成本高
   - 缓解: 默认使用tournament,提供early stopping

4. **循环依赖**: 可能出现A>B>C>A
   - 缓解: Robust的循环检测和解决

---

## 📚 参考资料

- Agent-as-a-Judge论文
- thinkmesh judge实现
- mindiv Phase 0基础设施

---

## ✨ 完成标志

Phase 2完成的标志:
- [ ] 所有交付物已创建
- [ ] 所有单元测试通过 (覆盖率 > 85%)
- [ ] 集成测试通过
- [ ] Bias分析完成
- [ ] 文档完整
- [ ] 在真实问题上验证有效

---

**下一步**: 完成Phase 2后,可以进入Phase 4 (混合策略)

