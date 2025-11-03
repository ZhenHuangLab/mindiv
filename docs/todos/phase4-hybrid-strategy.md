# Phase 4: 混合策略 (Hybrid Strategy)

## 📋 概述

**目标**: 结合方案1(置信度投票)和方案2/3(Judge/对抗评判),实现两阶段自适应策略。

**重要性**: 平衡效率和质量,简单问题快速返回,复杂问题深度评估。

**预估时间**: 5-6天

**优先级**: 🟢 中低 (组合优势)

---

## 🎯 交付物清单

- [ ] `hybrid.py` - HybridReducer实现
- [ ] 两阶段协调逻辑
- [ ] 决策系统(何时使用Stage 2)
- [ ] 结果传递和合并
- [ ] 阈值调优工具
- [ ] 成本分析工具
- [ ] 单元测试和集成测试
- [ ] 使用文档

---

## 🔗 前置条件

- [x] Phase 0 已完成
- [x] Phase 1 已完成 (ConfidenceVotingReducer)
- [x] Phase 2 或 Phase 3 已完成 (PairwiseJudgeReducer 或 AdversarialJudgeReducer)

---

## ✅ 详细任务清单

### Day 1: 决策逻辑设计

#### 任务 1.1: 设计决策条件
- [ ] 创建 `hybrid.py`
- [ ] 实现 `HybridReducer(BaseReducer)` 类
- [ ] 设计决策条件
  - 条件1: 置信度差距小
    - `top1_conf - top2_conf < threshold`
  - 条件2: 最高置信度不够高
    - `top1_conf < minimum_confidence`
  - 条件3: 投票分散
    - `vote_ratio < minimum_vote_ratio`
  - 条件4: 候选数量多
    - `len(candidates) > max_candidates_for_stage1`

#### 任务 1.2: 实现决策方法
- [ ] 实现 `_should_use_stage2(stage1_result, config)` 方法
  ```python
  def _should_use_stage2(self, stage1_result, config):
      """决定是否需要Stage 2"""
      top_k = stage1_result.metadata.get("top_k", [])
      
      if len(top_k) == 1:
          return False, "single_candidate"
      
      top1 = top_k[0]
      top2 = top_k[1]
      
      # 检查各个条件
      reasons = []
      
      if (top1["confidence"] - top2["confidence"]) < config["threshold"]:
          reasons.append("confidence_gap_small")
      
      if top1["confidence"] < config["minimum_confidence"]:
          reasons.append("low_confidence")
      
      vote_dist = stage1_result.metadata.get("vote_distribution", {})
      top1_votes = vote_dist.get(top1["answer"], 0)
      if top1_votes < config["minimum_vote_ratio"]:
          reasons.append("votes_dispersed")
      
      if len(reasons) > 0:
          return True, reasons
      
      return False, "confident"
  ```

#### 任务 1.3: 配置Schema设计
- [ ] 设计配置结构
  ```yaml
  hybrid:
    # Stage 1配置
    stage1_reducer: "confidence_voting"
    stage1:
      temperature: 0.5
      method: "auto"
    
    # Stage 2配置
    stage2_reducer: "pairwise_judge"  # or "adversarial"
    stage2:
      strategy: "tournament"
      # ... stage2特定配置
    
    # 决策阈值
    top_k: 3
    threshold: 0.3
    minimum_confidence: 0.6
    minimum_vote_ratio: 0.5
    
    # 成本控制
    cost_budget: 5.0
  ```

**验收标准**:
- [ ] 决策逻辑清晰合理
- [ ] 配置系统完整
- [ ] 测试覆盖率 > 85%

---

### Day 2: Stage 1集成

#### 任务 2.1: 集成ConfidenceVotingReducer
- [ ] 在HybridReducer中初始化Stage 1 reducer
  ```python
  def __init__(self, config, engine):
      super().__init__(config, engine)
      
      # 初始化Stage 1 reducer
      stage1_config = config.get("stage1", {})
      self.stage1_reducer = ConfidenceVotingReducer(stage1_config, engine)
  ```

#### 任务 2.2: 实现Stage 1执行
- [ ] 实现 `_run_stage1(agent_results, problem)` 方法
  ```python
  async def _run_stage1(self, agent_results, problem):
      """执行Stage 1: 置信度投票"""
      self._emit("hybrid.stage1_start", {})
      
      result = await self.stage1_reducer.reduce(agent_results, problem)
      
      # 提取top-k候选
      vote_dist = result.metadata.get("vote_distribution", {})
      sorted_answers = sorted(
          vote_dist.items(),
          key=lambda x: x[1],
          reverse=True
      )
      
      top_k = []
      for answer, weight in sorted_answers[:self.config["top_k"]]:
          # 找到对应的agent_result
          candidates = [
              r for r in agent_results
              if self.normalizer.normalize(r.final_solution) == answer
          ]
          if candidates:
              top_k.append({
                  "answer": answer,
                  "confidence": weight,
                  "candidates": candidates
              })
      
      result.metadata["top_k"] = top_k
      
      self._emit("hybrid.stage1_complete", {
          "top_k_count": len(top_k),
          "top1_confidence": top_k[0]["confidence"] if top_k else 0
      })
      
      return result
  ```

#### 任务 2.3: 测试Stage 1集成
- [ ] 测试Stage 1正常执行
- [ ] 测试top-k提取正确
- [ ] 测试元数据完整

**验收标准**:
- [ ] Stage 1集成正常工作
- [ ] Top-k提取正确
- [ ] 测试覆盖率 > 85%

---

### Day 3: Stage 2集成

#### 任务 3.1: 支持多种Stage 2 Reducer
- [ ] 实现Stage 2 reducer初始化
  ```python
  def __init__(self, config, engine):
      # ... Stage 1初始化
      
      # 初始化Stage 2 reducer
      stage2_mode = config.get("stage2_reducer", "pairwise_judge")
      stage2_config = config.get("stage2", {})
      
      if stage2_mode == "pairwise_judge":
          self.stage2_reducer = PairwiseJudgeReducer(stage2_config, engine)
      elif stage2_mode == "adversarial":
          self.stage2_reducer = AdversarialJudgeReducer(stage2_config, engine)
      else:
          raise ValueError(f"Unknown stage2_reducer: {stage2_mode}")
  ```

#### 任务 3.2: 实现Stage 2执行
- [ ] 实现 `_run_stage2(top_k_candidates, problem)` 方法
  ```python
  async def _run_stage2(self, top_k_candidates, problem):
      """执行Stage 2: 精细评估"""
      self._emit("hybrid.stage2_start", {
          "candidate_count": len(top_k_candidates)
      })
      
      # 准备候选列表
      candidates = []
      for item in top_k_candidates:
          candidates.extend(item["candidates"])
      
      # 调用Stage 2 reducer
      result = await self.stage2_reducer.reduce(candidates, problem)
      
      self._emit("hybrid.stage2_complete", {})
      
      return result
  ```

#### 任务 3.3: 测试Stage 2集成
- [ ] 测试PairwiseJudgeReducer集成
- [ ] 测试AdversarialJudgeReducer集成
- [ ] 测试候选传递正确

**验收标准**:
- [ ] 两种Stage 2 reducer都能正常工作
- [ ] 候选传递正确
- [ ] 测试覆盖率 > 85%

---

### Day 4: 结果传递和元数据合并

#### 任务 4.1: 实现主reduce方法
- [ ] 实现 `reduce(agent_results, problem)` 方法
  ```python
  async def reduce(self, agent_results, problem):
      # Stage 1: 置信度投票
      stage1_result = await self._run_stage1(agent_results, problem)
      
      # 决策: 是否需要Stage 2?
      use_stage2, reason = self._should_use_stage2(
          stage1_result,
          self.config
      )
      
      if not use_stage2:
          # 直接返回Stage 1结果
          stage1_result.metadata["hybrid_decision"] = {
              "used_stage2": False,
              "reason": reason
          }
          return stage1_result
      
      # Stage 2: 精细评估
      top_k = stage1_result.metadata["top_k"]
      stage2_result = await self._run_stage2(top_k, problem)
      
      # 合并元数据
      stage2_result.metadata["hybrid_decision"] = {
          "used_stage2": True,
          "reason": reason
      }
      stage2_result.metadata["stage1"] = stage1_result.metadata
      
      # 合并token使用
      for key, value in stage1_result.token_usage.items():
          stage2_result.token_usage[key] = \
              stage2_result.token_usage.get(key, 0) + value
      
      return stage2_result
  ```

#### 任务 4.2: 实现元数据合并
- [ ] 设计元数据结构
  ```python
  {
    "hybrid_decision": {
      "used_stage2": True,
      "reason": ["confidence_gap_small", "low_confidence"],
      "stage1_top1_confidence": 0.65,
      "stage1_top2_confidence": 0.62
    },
    "stage1": {
      "vote_distribution": {...},
      "confidences": [...],
      ...
    },
    "stage2": {
      # Stage 2特定的元数据
      ...
    }
  }
  ```
- [ ] 实现合并逻辑
- [ ] 确保信息完整

#### 任务 4.3: 实现决策轨迹记录
- [ ] 记录每个决策点
  - 为什么使用/不使用Stage 2
  - Stage 1的结果
  - Stage 2的结果(如果使用)
- [ ] 支持导出决策轨迹

**验收标准**:
- [ ] 主reduce方法正常工作
- [ ] 元数据合并完整
- [ ] 决策轨迹清晰
- [ ] 测试覆盖率 > 85%

---

### Day 5: 阈值调优工具

#### 任务 5.1: 实现阈值调优
- [ ] 创建 `tools/tune_hybrid_thresholds.py`
- [ ] 实现grid search
  ```python
  async def tune_thresholds(validation_set):
      """在验证集上调优阈值"""
      param_grid = {
          "threshold": [0.1, 0.2, 0.3, 0.4, 0.5],
          "minimum_confidence": [0.5, 0.6, 0.7, 0.8],
          "minimum_vote_ratio": [0.3, 0.4, 0.5, 0.6]
      }
      
      best_params = None
      best_score = 0
      
      for params in itertools.product(*param_grid.values()):
          config = dict(zip(param_grid.keys(), params))
          
          # 在验证集上评估
          score = await evaluate_config(config, validation_set)
          
          if score > best_score:
              best_score = score
              best_params = config
      
      return best_params, best_score
  ```

#### 任务 5.2: 实现成本-准确性分析
- [ ] 分析不同阈值下的:
  - Stage 2触发率
  - 平均成本
  - 准确率
  - 成本-准确性权衡
- [ ] 生成Pareto前沿图
  - X轴: 成本
  - Y轴: 准确率
  - 每个点: 一组阈值配置

#### 任务 5.3: 实现自适应阈值
- [ ] 根据问题类型自动调整阈值
  - 数学问题: 更严格的阈值
  - 开放性问题: 更宽松的阈值
- [ ] 配置支持
  ```yaml
  hybrid:
    adaptive_thresholds: true
    problem_type_thresholds:
      math:
        threshold: 0.2
        minimum_confidence: 0.7
      reasoning:
        threshold: 0.3
        minimum_confidence: 0.6
  ```

**验收标准**:
- [ ] 调优工具正常工作
- [ ] 成本-准确性分析清晰
- [ ] 自适应阈值有效
- [ ] 文档完整

---

### Day 6: 集成测试和成本分析

#### 任务 6.1: 端到端测试
- [ ] 准备测试数据
  - 简单问题(应该只用Stage 1)
  - 复杂问题(应该触发Stage 2)
  - 边界情况
- [ ] 测试完整流程
  - 验证决策正确
  - 验证结果准确
  - 验证元数据完整

#### 任务 6.2: 成本分析
- [ ] 统计Stage 2触发率
  ```python
  def analyze_stage2_trigger_rate(results):
      total = len(results)
      triggered = sum(1 for r in results 
                      if r.metadata["hybrid_decision"]["used_stage2"])
      return triggered / total
  ```
- [ ] 分析成本分布
  - Stage 1 only的平均成本
  - Stage 1 + Stage 2的平均成本
  - 总体平均成本
- [ ] 与单独使用方案1/2/3对比
  - 准确性对比
  - 成本对比
  - 时间对比

#### 任务 6.3: 性能测试
- [ ] 测试Stage 1时间
- [ ] 测试Stage 2时间
- [ ] 测试总体时间
- [ ] 测试并发性能

#### 任务 6.4: 生成分析报告
- [ ] 创建可视化报告
  - Stage 2触发率图
  - 成本分布图
  - 准确性对比图
  - 成本-准确性权衡图
- [ ] 导出为HTML/PDF

**验收标准**:
- [ ] 所有集成测试通过
- [ ] 成本分析完整
- [ ] 性能满足要求
- [ ] 报告清晰易读

---

## 📝 技术规范

### HybridReducer接口
```python
class HybridReducer(BaseReducer):
    async def reduce(
        self,
        agent_results: List[AgentResult],
        problem: str
    ) -> ReducerResult:
        """主reduce方法"""
        pass
    
    async def _run_stage1(...) -> ReducerResult:
        """执行Stage 1"""
        pass
    
    async def _run_stage2(...) -> ReducerResult:
        """执行Stage 2"""
        pass
    
    def _should_use_stage2(...) -> Tuple[bool, Union[str, List[str]]]:
        """决定是否使用Stage 2"""
        pass
```

### 配置Schema
```yaml
hybrid:
  stage1_reducer: "confidence_voting"
  stage1:
    temperature: 0.5
  
  stage2_reducer: "pairwise_judge"  # or "adversarial"
  stage2:
    strategy: "tournament"
  
  top_k: 3
  threshold: 0.3
  minimum_confidence: 0.6
  minimum_vote_ratio: 0.5
  
  adaptive_thresholds: false
  problem_type_thresholds: {}
  
  cost_budget: 5.0
```

---

## 🧪 测试要求

### 单元测试
- [ ] `test_hybrid_decision.py` - 测试决策逻辑
- [ ] `test_hybrid_stage1.py` - 测试Stage 1集成
- [ ] `test_hybrid_stage2.py` - 测试Stage 2集成
- [ ] 测试覆盖率 > 85%

### 集成测试
- [ ] `test_hybrid_integration.py` - 端到端测试
- [ ] 测试不同配置组合
- [ ] 测试边界情况

### 性能测试
- [ ] Stage 2触发率在合理范围
- [ ] 成本低于单独使用Stage 2
- [ ] 准确性接近或超过单独使用Stage 2

---

## ⚠️ 风险和注意事项

1. **复杂度高**: 组合两个reducer增加复杂度
   - 缓解: 详细文档,清晰的接口

2. **阈值敏感**: 不同问题可能需要不同阈值
   - 缓解: 提供调优工具,自适应阈值

3. **两阶段不一致**: Stage 2可能选出Stage 1排名低的候选
   - 缓解: 记录并分析这种情况

4. **成本不可预测**: Stage 2触发率影响成本
   - 缓解: 成本估算,成本上限

---

## 📚 参考资料

- Phase 1: ConfidenceVotingReducer
- Phase 2: PairwiseJudgeReducer
- Phase 3: AdversarialJudgeReducer
- mindiv Phase 0基础设施

---

## ✨ 完成标志

Phase 4完成的标志:
- [ ] 所有交付物已创建
- [ ] 所有单元测试通过 (覆盖率 > 85%)
- [ ] 集成测试通过
- [ ] 阈值调优完成
- [ ] 成本分析完成
- [ ] 文档完整
- [ ] 在真实问题上验证有效

---

**下一步**: 完成Phase 4后,进入Phase 5 (集成测试和优化)

