# Algorithm Map — TODO

## Phase 0: Schema 定义 ← 当前阶段

- [x] 定义 JSON Schema（三层：结构/内容/状态）
- [x] 创建 BPC 示例 JSON（符合 Schema）
- [ ] 编写生成规范 prompt ← 当前步骤

## Phase 1: 渲染器

- [ ] 改造现有 BPC HTML 原型为通用渲染器（读外部 JSON）
- [ ] 接入 cc-commander feedback bridge 批注机制
- [ ] 手机端适配测试

## Phase 2: CC-Commander 集成

- [ ] PM 路由：识别复杂算法任务
- [ ] Terminal 新增 map_planning 状态
- [ ] 执行器：按 JSON 拓扑逐节点实现 + 验证
- [ ] 端到端测试：BPC 案例全流程

## Phase 3: 迭代优化

- [ ] 子代理并行执行
- [ ] 知识获取管线（论文 PDF → MD）
- [ ] 地图版本控制（diff / merge）
