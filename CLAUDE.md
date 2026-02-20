# Algorithm Map — 项目规范

## 项目概述

**算法地图**（Algorithm Map）是一套面向 AI 编程时代的算法管理协议和工具链。核心思想：用结构化的交互式流程图替代纯文字 plan，通过分层验证体系建立对 AI 生成代码的信任链。

- **协议**：JSON Schema 定义算法地图的标准数据格式
- **渲染器**：JSON → 可交互 HTML（支持批注、状态追踪）
- **生成规范**：CC 生成合规 JSON 的 prompt 模板
- **示例**：BPC（Branch-Price-Cut）作为参考实现

## 当前阶段

Phase 0: Schema 定义 ← 当前

## 项目结构

```
algorithm-map/
├── schema/              # JSON Schema 定义
├── renderer/            # JSON → HTML 渲染器
├── prompts/             # CC 生成地图的 prompt 规范
├── examples/            # 示例地图 JSON
└── docs/                # 愿景文档、设计说明
```

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据格式 | JSON | AI 可直接生成和解析，人通过 HTML 渲染阅读 |
| 三层分离 | 结构/内容/状态 | 结构定型后少改；内容在规划阶段填充；状态在执行阶段更新 |
| 渲染方式 | 单 HTML 文件 | 零依赖，手机浏览器直接打开，便于通过 cc-commander 推送 |
| 批注机制 | 复用 cc-commander feedback bridge | 已有成熟方案，不重复造轮 |

## 文档联动

| 触发事件 | 必须更新 |
|---------|---------|
| Schema 字段变更 | `schema/algorithm-map.schema.json` + `examples/bpc-phase1.json` + `docs/vision.md`（如涉及） |
| 新增示例地图 | `examples/` + `README.md` 示例列表 |
| 渲染器功能变更 | `renderer/` + `TODO.md` |
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

（随项目推进记录）
