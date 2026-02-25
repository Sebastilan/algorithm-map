# Algorithm Map — TODO

## Phase 0: Schema 定义 ✅

- [x] 定义 JSON Schema（三层：结构/内容/状态）
- [x] 创建 BPC 示例 JSON（符合 Schema）

## Phase 1: 渲染器 ✅

- [x] 改造现有 BPC HTML 原型为通用渲染器（读外部 JSON）
- [x] dagre 自动布局 + 形状裁剪（菱形/椭圆）+ 路径简化
- [x] 六维面板（overview/how/verify/code/refs/pitfalls）+ Markdown/KaTeX 渲染
- [x] 批注模式（流程图层 + 面板层，支持 resolve）
- [x] 状态追踪（process 节点状态点 + 验证结果只读展示 + 进度条）
- [x] 反馈机制：点击「提交反馈」→ 生成精简 MD → 写入文件（HTTP POST）
- [ ] 手机端适配测试（降优先级，能用就行）

## Phase 1.5: 协议层 ✅

核心：让 CC 能生成和执行算法地图，而不只是渲染它。

- [x] 生成规范 prompt（`prompts/generate-map.md`）
- [x] 执行规范 prompt（`prompts/execute-map.md`）
- [x] 包装为 CC 技能 `/map`（plan / build / view）
- [x] 更新 `docs/vision.md`（补充已实现部分）
- [x] BPC 实战验证：`/map build` 完成全部 9 节点 + 4 轮审计 + 159 测试
  - 项目：`CCA/bpc-solver/`
  - 发现并修复 B&B 列池 bug（子节点丢失父节点 CG 列）
  - 测试实例设计：T3（integer at root）+ T4（forcing branching）

## Phase 1.6: 协议迭代（ALNS 测试驱动）✅

- [x] ALNS-CVRP 测试 `/map plan`，发现"5步散文→JSON"模式的系统性问题
- [x] 重构 `generate-map.md`：5步连续 → 两阶段增量构建（Phase A 骨架 + Phase B 验证）
- [x] 新增算法类型分类验证指南（确定性/随机/数值迭代/数据处理）
- [x] 新增 `/map upgrade` 子命令（升级已有地图节点/新增节点）
- [x] 重构 `execute-map.md`：benchmark-only → 逐节点分层验证（L1→L2→L3）
- [x] 新增三方制衡：Builder 自检数值 + Reviewer（Sonnet）审代码逻辑
- [x] Plan 变更规则：内容层 Builder 可调，结构层走 `/map upgrade`
- [x] 同步更新 `/map` 技能副本（references/ + SKILL.md）

## Phase 1.7: Plan 技能优化（CVRP B&P 测试驱动）✅

3 轮 CVRP Branch-and-Price 测试迭代，plan 质量和流程均已达标。

- [x] 移除 BPC/CVRP 硬编码示例，提升 CC 友好度
- [x] B4 交付：渲染器 URL → standalone HTML + `[SHARE:]` 审阅链接
- [x] export_standalone.py：JSON 嵌入 render.html 生成自包含 HTML
- [x] L3 位置规则：处理终端节点无 post 的情况
- [x] L2/L3 边界：禁止在 region L2 写端到端验证
- [x] 决策节点：require post assertions
- [x] JSON 内容统一用中文 + 禁止 CC 读取 HTML 文件
- [x] B1/B2/B3 并行化：Task 工具并行启动，主 CC 合并写入
- [x] 测试结果：28 项核心验证（20 L1 + 7 L2 + 1 L3），2 组互补手算实例

## Phase 1.8: Execute 技能优化 ← 当前阶段

- [ ] 分析 `execute-map.md` 现有问题（基于 BPC 实战经验）
- [ ] 测试并迭代优化

## Phase 2: CC-Commander 集成

- [ ] PM 路由：识别复杂算法任务
- [ ] Terminal 新增 map_planning 状态
- [ ] CCC 文件服务渲染地图 HTML
- [ ] 端到端测试：BPC 案例全流程

## Phase 3: 迭代优化

- [ ] 子代理并行执行
- [ ] 知识获取管线（论文 PDF → MD）
- [ ] 地图版本控制（diff / merge）
