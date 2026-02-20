# Algorithm Map — TODO

## Phase 0: Schema 定义 ✅

- [x] 定义 JSON Schema（三层：结构/内容/状态）
- [x] 创建 BPC 示例 JSON（符合 Schema）
- [ ] 编写生成规范 prompt（`prompts/generate-map.md`）← 待做

## Phase 1: 渲染器 ← 当前阶段

- [x] 改造现有 BPC HTML 原型为通用渲染器（读外部 JSON）
- [x] dagre 自动布局 + 形状裁剪（菱形/椭圆）+ 路径简化
- [x] 六维面板（overview/how/verify/code/refs/pitfalls）+ Markdown/KaTeX 渲染
- [x] 批注模式（流程图层 + 面板层，支持 resolve）
- [x] 状态追踪（process 节点状态点 + 验证结果只读展示 + 进度条）
- [ ] 反馈机制：点击「提交反馈」→ 生成精简 MD → 写入文件（HTTP POST）← 下一步
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
