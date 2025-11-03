# UltraThink多模式Reducer实施计划总览

## 📋 项目概述

本项目旨在为mindiv的UltraThink引擎实现**4种SOTA的多agent结果综合方案**,使mindiv成为科研级难题解决框架。

### 核心目标
- ✅ **准确性优先**: 提升最终答案质量,减少LLM bias和错误
- ✅ **鲁棒性**: 处理多agent不一致,冲突解决
- ✅ **成本效率**: 在保证质量的前提下优化成本
- ✅ **多Provider支持**: OpenAI/Claude/Gemini全支持,可混合使用
- ✅ **科研价值**: 可对比不同方案,发表论文

---

## 🎯 4种Reducer方案

### 方案1: 置信度加权投票 (Confidence-Weighted Voting)
- **文件**: `phase1-confidence-voting.md`
- **时间**: 4-5天
- **优势**: 成本效益最优,SOTA支持(CISC 2025)
- **适用**: 数学/编程等有明确答案的问题
- **核心技术**: P(True)方法,Softmax归一化,温度缩放

### 方案2: 成对Judge (Pairwise Judge)
- **文件**: `phase2-pairwise-judge.md`
- **时间**: 4-5天
- **优势**: 评估推理过程,适合复杂问题
- **适用**: 需要评估推理质量的场景
- **核心技术**: Tournament配对,LLM-as-a-Judge,循环检测

### 方案3: 对抗性评判 (Adversarial Judge) ⭐
- **文件**: `phase3-adversarial-judge.md`
- **时间**: 7-8天
- **优势**: 最高质量,多视角评估,用户特别感兴趣
- **适用**: 科研级难题,需要最高准确性
- **核心技术**: Grader/Critic/Defender角色,多轮对抗,元评估

### 方案4: 混合策略 (Hybrid Strategy)
- **文件**: `phase4-hybrid-strategy.md`
- **时间**: 5-6天
- **优势**: 平衡效率和质量,自适应
- **适用**: 混合场景,成本敏感
- **核心技术**: 两阶段架构,自适应阈值,成本控制

---

## 📅 实施时间线

### 总时间: 28-35天

```
Phase 0: 基础设施 (3-4天)
  ↓
Phase 3: 对抗性评判 (7-8天) ⭐ 用户优先
  ↓
Phase 1: 置信度投票 (4-5天)
  ↓
Phase 2: 成对Judge (4-5天)
  ↓
Phase 4: 混合策略 (5-6天)
  ↓
Phase 5: 集成测试 (5-7天)
```

### 为什么这个顺序?
1. **Phase 0必须先完成** - 提供所有方案需要的基础设施
2. **Phase 3优先** - 用户特别感兴趣,科研价值最高
3. **Phase 1次之** - 为Phase 4做准备
4. **Phase 2补充** - 提供另一种Judge方案
5. **Phase 4组合** - 结合前面的方案
6. **Phase 5收尾** - 全面测试和优化

---

## 📂 文件结构

### TODO文件
- `phase0-infrastructure.md` - 基础设施 (BaseReducer, types, normalizer等)
- `phase1-confidence-voting.md` - 置信度加权投票
- `phase2-pairwise-judge.md` - 成对Judge
- `phase3-adversarial-judge.md` - 对抗性评判 ⭐
- `phase4-hybrid-strategy.md` - 混合策略
- `phase5-integration-testing.md` - 集成测试和优化

### 代码结构 (计划)
```
mindiv/engine/reducers/
├── __init__.py
├── base.py                    # BaseReducer抽象基类
├── types.py                   # ReducerResult, AgentResult等
├── normalizer.py              # 答案归一化
├── prompts.py                 # 所有prompts
├── confidence_extractor.py    # 置信度提取
├── confidence_voting.py       # 方案1
├── pairwise_judge.py          # 方案2
├── adversarial_judge.py       # 方案3 ⭐
├── hybrid.py                  # 方案4
└── tests/
    ├── test_base.py
    ├── test_normalizer.py
    ├── test_confidence_voting.py
    ├── test_pairwise_judge.py
    ├── test_adversarial_judge.py
    ├── test_hybrid.py
    └── integration/
        └── test_reducers_integration.py
```

---

## 🚀 快速开始

### 1. 查看当前Phase
```bash
# 查看Phase 0的详细计划
cat mindiv/docs/todos/phase0-infrastructure.md
```

### 2. 开始实施
每个Phase的TODO文件都包含:
- ✅ 详细的任务清单 (可勾选)
- 📝 技术规范和代码示例
- 🧪 测试要求
- ⚠️ 风险和注意事项
- ✨ 完成标志

### 3. 跟踪进度
在每个TODO文件中:
- 完成任务后勾选 `- [x]`
- 记录遇到的问题
- 更新预估时间

---

## 📊 关键指标

### 质量指标
- 测试覆盖率: > 85%
- 准确率提升: 目标 > 10%
- Bias减少: 目标 > 20%

### 性能指标
- 置信度提取: < 5s per agent
- 成对Judge: < 10s per pair
- 对抗评判: < 30s per candidate
- 并行化加速: > 2x

### 成本指标
- 方案1成本: 基准
- 方案2成本: < 3x基准
- 方案3成本: < 5x基准
- 方案4成本: < 2x基准 (自适应)

---

## 🎓 科研价值

### 可研究的问题
1. 不同聚合策略对准确性的影响
2. 多provider ensemble的价值
3. 对抗性评判的有效性
4. 置信度校准方法
5. 成本-准确性权衡

### 可发表的内容
- 4种方案的对比研究
- 多provider混合使用的效果
- 对抗性评判框架的设计
- 在数学/推理benchmark上的评估结果

### Benchmark
- MATH dataset
- GSM8K
- IMO problems
- 自定义难题集

---

## 🔧 技术亮点

### 1. Provider路由
```yaml
provider_routing:
  default: "claude"
  confidence_extraction: "openai"  # OpenAI的logprobs更好
  judge: "gpt-4"                   # GPT-4作为judge
  grader: "claude-opus"            # Claude作为grader
  critic: "gpt-4"                  # GPT-4作为critic
  defender: "gemini-pro"           # Gemini作为defender
```

### 2. 答案归一化
- 数值归一化: "1/2" → "0.5"
- LaTeX归一化: 使用sympy
- 文本归一化: 小写,去空格

### 3. 置信度提取
- P(True)方法: 使用logprobs
- Verbal方法: 直接询问
- Auto方法: 自动选择最佳

### 4. 对抗性评判
- Grader: 初步评分
- Critic: 找问题
- Defender: 辩护
- Grader: 最终裁决

---

## 📚 参考资料

### 学术论文
1. **Confidence Improves Self-Consistency in LLMs** (2025) - CISC方法
2. **When AIs Judge AIs: Agent-as-a-Judge** (2024) - LLM评判框架
3. **CourtEval** - 对抗性评判
4. **DEBATE** - Devil's advocate

### 参考项目
- **thinkmesh** - reduce_majority和reduce_judge
- **MACM** - consensus-based judging
- **DeepAgent** - majority voting
- **IMO25** - parallel execution

### 技术文档
- OpenAI logprobs API
- Claude API
- Gemini API
- mindiv现有架构

---

## ⚠️ 重要提醒

### 实施原则
1. **测试驱动**: 先写测试,再写代码
2. **增量开发**: 每个Phase独立可测试
3. **文档同步**: 代码和文档同步更新
4. **性能优先**: 持续profiling和优化
5. **成本意识**: 记录和优化token使用

### 风险管理
1. **Provider限制**: 某些provider可能不支持logprobs
   - 缓解: 实现fallback机制
2. **成本爆炸**: 对抗评判可能很贵
   - 缓解: 成本上限,early stopping
3. **不一致性**: 不同reducer可能给出不同答案
   - 缓解: 详细记录,分析原因
4. **复杂度**: 4个方案增加维护成本
   - 缓解: 统一接口,充分测试

---

## 🎯 成功标准

### Phase 0-4完成标志
- [ ] 所有4个reducer实现完成
- [ ] 所有单元测试通过 (覆盖率 > 85%)
- [ ] 基本集成测试通过
- [ ] 配置系统完整
- [ ] 基本文档完成

### Phase 5完成标志
- [ ] 完整的测试套件 (覆盖率 > 85%)
- [ ] 性能满足要求
- [ ] 科研级评估完成
- [ ] 完整的文档
- [ ] 代码review通过
- [ ] 版本发布

### 最终目标
- [ ] mindiv成为SOTA的科研级难题解决框架
- [ ] 在benchmark上验证有效
- [ ] 可发表论文
- [ ] 开源社区认可

---

## 📞 联系和支持

如有问题或建议,请:
1. 查看对应Phase的TODO文件
2. 查看技术文档
3. 查看参考资料
4. 提出issue或讨论

---

**让我们开始这个激动人心的旅程,打造世界级的多agent协作系统!** 🚀

---

*最后更新: 2025-11-03*
*版本: v1.0*

