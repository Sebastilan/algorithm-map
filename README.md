# Algorithm Map

面向 AI 编程时代的算法管理协议：让不写代码的人能可靠地驾驭复杂代码。

## 它是什么

一套标准化的算法描述格式（JSON Schema）+ 配套工具链：

- **JSON Schema** — 定义算法地图的数据结构（图拓扑 + 六维节点内容 + 运行状态）
- **HTML 渲染器** — 将 JSON 渲染为可交互的流程图，支持批注和状态追踪
- **生成规范** — 指导 AI（Claude Code 等）输出合规的地图 JSON
- **示例** — BPC 列生成算法作为参考实现

## 核心思想

```
不看代码，看验证。验证通过 = 代码可信。
```

把复杂算法拆成环节，为每个环节定义三层验证（前置条件 → 核心验证 → 后置条件）。所有验证通过 = 整条链路可信。任何验证失败 = 精确定位到问题环节。

## 架构

```
AI 生成 JSON ──→ 静态渲染器（HTML）──→ 用户审阅批注 ──→ 反馈 MD ──→ AI 读取
     ↑                不进对话上下文              ↓
     └──────────── 修改 JSON 重新渲染 ←──────────┘
```

**关键设计**：渲染器是预部署的静态 HTML，永远不进入 AI 对话上下文。AI 只生成紧凑的 JSON 数据，读取精简的反馈 MD，保持上下文窗口精简。

## 三个阶段

1. **施工蓝图（Plan）** — AI 生成地图 JSON，人在手机/平板上审阅批注
2. **施工现场（Build）** — AI 按地图逐环节实现，每个环节跑验证
3. **成品交付（Deliver）** — 地图自动变成完整的算法文档

## 快速开始

```bash
# 启动本地 HTTP 服务器（file:// 无法 fetch JSON）
cd algorithm-map
python -m http.server 8765

# 浏览器打开渲染器
# http://localhost:8765/renderer/render.html
# 点击「加载 JSON」选择 examples/bpc-phase1.json
```

## 项目结构

```
schema/              JSON Schema 定义
renderer/            JSON → HTML 渲染器（单文件，dagre 布局 + Markdown/KaTeX）
prompts/             AI 生成地图的 prompt 规范（待编写）
examples/            示例地图 JSON
docs/                愿景文档
```

## 与 CC-Commander 集成

算法地图作为 CC-Commander 的一种 plan 格式，通过 JSON 协议对接。详见 [愿景文档](docs/vision.md)。
