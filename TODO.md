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

## Phase 2: CC-Commander 集成 ← 下一阶段

- [ ] PM 路由：识别复杂算法任务
- [ ] Terminal 新增 map_planning 状态
- [ ] CCC 文件服务渲染地图 HTML
- [ ] 端到端测试：BPC 案例全流程

## Phase 3: 迭代优化

- [ ] 子代理并行执行
- [ ] 知识获取管线（论文 PDF → MD）
- [ ] 地图版本控制（diff / merge）
