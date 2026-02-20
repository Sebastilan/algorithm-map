# Algorithm Map — 项目规范

## 项目概述

**算法地图**（Algorithm Map）是一套面向 AI 编程时代的算法管理协议和工具链。核心思想：用结构化的交互式流程图替代纯文字 plan，通过分层验证体系建立对 AI 生成代码的信任链。

- **协议**：JSON Schema 定义算法地图的标准数据格式
- **渲染器**：JSON → 可交互 HTML（支持批注、状态追踪）
- **生成规范**：CC 生成合规 JSON 的 prompt 模板
- **执行规范**：CC 按图逐节点实现代码的执行协议
- **CC 技能**：`/map` 技能（plan / build / view 三个子命令）
- **示例**：BPC（Branch-Price-Cut）作为参考实现

## 当前阶段

Phase 1.5 完成。渲染器 + 反馈桥 + 生成/执行规范 + `/map` 技能全部就绪。下一步：Phase 2（CC Commander 集成）或实际项目验证。

## 项目结构

```
algorithm-map/
├── schema/              # JSON Schema 定义
├── renderer/            # JSON → HTML 渲染器
├── prompts/             # CC 生成/执行地图的 prompt 规范
│   ├── generate-map.md  # Plan 阶段：生成地图 JSON
│   └── execute-map.md   # Build 阶段：逐节点实现 + 验证
├── examples/            # 示例地图 JSON
├── docs/                # 愿景文档、设计说明
└── server.py            # 开发服务器（静态文件 + POST /api/feedback）

CC 技能（项目外）：
~/.claude/skills/map/
├── SKILL.md             # 技能主文件（/map plan|build|view）
└── references/          # 引用生成/执行规范
```

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据格式 | JSON | AI 可直接生成和解析，人通过 HTML 渲染阅读 |
| 三层分离 | 结构/内容/状态 | 结构定型后少改；内容在规划阶段填充；状态在执行阶段更新 |
| 渲染方式 | 单 HTML 文件 | 零依赖，需 HTTP 服务器（file:// 无法 fetch JSON） |
| 批注机制 | 渲染器内置 → 导出反馈 MD | 点击「提交反馈」→ 生成精简 MD → AI 直接读取 |
| 架构模式 | 静态查看器 + JSON 数据 | 渲染器不进对话上下文，AI 只生成 JSON + 读反馈 MD，保持上下文精简 |

## 文档联动

| 触发事件 | 必须更新 |
|---------|---------|
| Schema 字段变更 | `schema/algorithm-map.schema.json` + `examples/bpc-phase1.json` + `docs/vision.md`（如涉及） |
| 新增示例地图 | `examples/` + `README.md` 示例列表 |
| 渲染器功能变更 | `renderer/` + `TODO.md` |
| 协议/规范变更 | `prompts/` 对应文件 + `TODO.md` |
| 任务完成/新增 | `TODO.md` |
| 踩坑/重要决策 | 本文件「经验沉淀」段 |

## 与 cc-commander 的关系

算法地图是独立协议，cc-commander 是消费者之一。集成点：
- PM 判断复杂算法任务时触发地图流程
- Terminal 新增 `map_planning` 状态
- 文件服务渲染地图 HTML + 注入 feedback bridge
- 执行器按 JSON 拓扑顺序逐节点实现 + 验证

集成在 cc-commander 侧完成，本项目只提供 schema + 渲染器 + 规范。

## 经验沉淀

### 渲染器开发（2026-02-20）
- **file:// 不能 fetch**：浏览器 CORS 限制，必须通过 HTTP 服务器访问（`python -m http.server 8765`）
- **KaTeX CDN 版本**：0.16.11 不存在于 cdnjs，用 0.16.9
- **dagre 布局后处理**：dagre 按矩形包围盒连线，菱形/椭圆需要 clipToShape() 后处理裁剪到真实边界
- **路径简化**：dagre 产生近共线中间点导致微弯，simplifyPath() 用垂直距离阈值 5px 消除
- **批注模式命中区域**：不能直接加粗可见边线（stroke-width:12 导致箭头变形），正确做法是加一层透明 .edge-hit 覆盖层
- **验证项只读**：checkbox 改为 ⬜/✅ 图标展示，验证结果由自动化流程写入 state，不允许手动勾选
- **状态点只在 process 节点显示**：decision/terminal/auxiliary 节点不需要执行状态标识
- **静态查看器模式**：渲染器预部署不进上下文，AI 只生成 JSON + 读反馈 MD → 上下文窗口精简（已记录为全局知识）
- **Feedback Bridge**：`server.py` 替代 `python -m http.server`，新增 POST /api/feedback 写 `.feedback.md`；渲染器 `submitFeedback()` POST 失败时 fallback 到剪贴板复制，兼容纯静态服务器

### 协议层设计（2026-02-20）
- **三层输出**：思想层（愿景文章）> 规范层（schema + prompts）> 工具层（渲染器 + 技能）。思想最有价值，工具会过时
- **执行粒度是单节点**：每个 process 节点是一个完整的理解→实现→验证→状态更新循环，也是天然的对话断点
- **技能引用而非复制规范**：`/map` 技能的 references/ 包含完整规范副本，确保技能自包含，不依赖仓库路径变动
- **地图 JSON 放目标项目内**：不放 algorithm-map 仓库里，而是放在使用地图的目标项目根目录，确保项目自包含
- **localStorage vs JSON state 权威源**：渲染器 localStorage 只保存用户本地批注；statuses 和 verifyChecks 以 JSON 为权威源（Build 阶段 AI 直接写 JSON）。之前 localStorage 会完全覆盖 JSON state 导致刷新后看不到 AI 更新的状态

### 独立审查机制设计（2026-02-20）
- **Builder/Auditor 分离**：同一 AI 写代码又自测存在"狐狸看鸡窝"问题。解决方案：Builder 实现代码后，通过 CC Task 工具启动独立 Audit 子 Agent 审查
- **三层审查顺序**：审指标（verify 标准本身是否完整）→ 审数据（用 checkpoint 跑测试）→ 审代码（读源码查投机取巧）。指标层最先，因为标准有问题则后续审查无意义
- **Checkpoint 是反作弊核心**：每个节点输出序列化到 `_checkpoints/<node_id>.json`，下游节点的输入来自上游 checkpoint，Builder 无法篡改上游数据。成本几乎为零，价值极高
- **盲测不做**：为复杂算法生成有意义的测试数据本身极难，投入产出比不合理。checkpoint + 代码审查已足够
- **链式信任检查**：Auditor 不只看当前节点，还验证上游 post 是否覆盖本节点 pre、本节点 post 是否支撑下游 pre。防止信任链断裂
