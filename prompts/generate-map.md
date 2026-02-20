# 算法地图生成规范

本文档是 Claude Code 生成算法地图 JSON 的规范。遵循此规范可产出符合 schema 的 JSON，渲染器可直接渲染为交互式流程图。

## 什么时候用算法地图

**用**：
- 算法有多个步骤、存在分支/循环/并行结构
- 用户不写代码，需要通过验证来确认正确性
- 预计实现代码超过 500 行，或跨越多轮对话
- 算法来自论文/教科书，需要分步理解和实现

**不用**：
- 简单的线性脚本（几十行就能搞定）
- 纯 CRUD / 配置类任务
- 用户自己能读懂代码

## 生成流程

### 第一步：厘清算法

与用户对话，搞清楚以下信息。不急着生成 JSON，先在文字层面达成共识。

```
必须弄清的问题：
1. 这个算法解决什么问题？输入什么、输出什么？
2. 算法的整体策略是什么？（穷举？分治？迭代？）
3. 有哪些关键步骤？哪些地方有分支或循环？
4. 停止条件是什么？
5. 有参考论文或开源实现吗？
6. 目标编程语言和依赖（如 Gurobi、PyTorch）？
```

### 第二步：画流程图（graph 层）

确定节点和连接关系。先用文字列出来让用户确认，再转 JSON。

**节点类型选择：**

| 类型 | 用途 | 形状 | 举例 |
|------|------|------|------|
| `terminal` | 起止点 | 椭圆 | "开始"、"输出结果" |
| `process` | 核心步骤 | 圆角矩形 | "求解 RMP"、"定价子问题" |
| `decision` | 判断分支 | 菱形 | "负 RC 列?"、"整数解?" |
| `auxiliary` | 辅助操作 | 小矩形 | "更新 UB"、"剪枝" |

**设计原则：**
- `process` 节点是主角，每个都有详细的六维内容和验证体系
- `decision` 用于分支判断，label 用问句，边上标"是/否"
- `auxiliary` 用于简单操作（不值得专门写验证的），不生成状态点
- `terminal` 只用于起止
- 节点 id 用蛇形命名：`01_initialize`、`04_pricing`
- 核心步骤带编号前缀：`01_`、`02_`……辅助节点不编号
- 节点数量：通常 8-15 个（太少说明拆得不够细，太多说明把细节塞进了流程图）

**区域（regions）：**
- 用于标注循环或逻辑分组
- 同一个节点可以属于多个区域（如"列生成循环"嵌套在"分支定界"内）

### 第三步：填内容（contents 层）

为每个 `process` 和 `decision` 类型的核心节点填写六维内容。`terminal` 和 `auxiliary` 通常不需要。

**六维内容模板：**

#### overview（概述）
```markdown
### 一句话
[这步做什么，一句话说清]

### 输入 → 输出
- **输入**：[具体的数据和格式]
- **输出**：[具体的数据和格式]

### 为什么需要
[这步在整体算法中的角色，删掉会怎样]

### 数学模型（如有）
$$...$$
```

#### how（实现方法）
```markdown
### 算法思路
[用人话说明白核心逻辑]

### 核心逻辑
1. [步骤 1]
2. [步骤 2]
...

### 设计决策
- [为什么选择这个方案而非另一个]
```

#### verify（验证 — 见下文详细说明）

#### code（代码）
```json
{
  "files": ["src/module.py"],
  "snippet": "```python\n# 核心实现片段\n```"
}
```
规划阶段 `files` 和 `snippet` 可以为空，Build 阶段填充。

#### refs（参考）
```markdown
### 关键参考
- **论文/书名**：具体哪部分有用
- **开源实现**：链接 + 说明
```

#### pitfalls（踩坑）
规划阶段为空字符串 `""`，Build 阶段遇到问题时填充。

### 第四步：设计验证体系（核心）

**这是算法地图的灵魂。** 验证体系决定了用户能否在不读代码的情况下信任结果。

#### 三层验证结构

```
前置条件 (pre)  → 本步骤启动前，上游给的输入必须满足什么
核心验证 (core) → 本步骤的实现本身是否正确
后置条件 (post) → 本步骤的输出，下游消费时可以依赖什么保证
```

#### 链式信任规则

**环节 A 的后置条件 必须覆盖 环节 B 的前置条件**（当 A→B 有边时）。

```
环节 A post: "输出 X 满足条件 P"
    ‖ 这两个必须能对上
环节 B pre:  "输入 X 满足条件 P"
```

生成时逐对检查：沿着每条边，确认上游 post 能保证下游 pre。如果对不上，要么补上遗漏的 post，要么上游的实现有设计缺陷。

#### pre / post 格式

```json
{
  "desc": "距离矩阵对称且非负",
  "check": "dist[i][j] == dist[j][i], dist[i][i] == 0"
}
```
- `desc`：人能读懂的条件描述
- `check`：可执行的断言表达式或验证方法（供 AI 写测试时参考）

#### core 格式

```json
{
  "desc": "T3 穷举验证：返回列确实是 RC 最小的",
  "level": "L1",
  "method": "3 客户实例穷举所有路径，比对 pricing 返回结果",
  "cmd": "pytest test_pricing.py::test_t3_exhaustive -v"
}
```
- `level`：`L1` 单元级（必过），`L2` 集成级，`L3` 端到端
- `method`：验证策略说明
- `cmd`：可执行的测试命令（Build 阶段填，Plan 阶段可留空）

#### 验证设计原则

1. **抓本质，不堆数量**：找到这一步"对不对"的数学/逻辑判据，用最少的检查覆盖它。一条直击要害的验证胜过十条表面指标
2. **小实例对答案**：构造一个足够小的算例（3-5 节点/变量），用已知最优解或暴力求解作为 ground truth，比对算法输出。例如列生成本质是松弛 MIP——小算例上直接求解、比对最优值即可
3. **可执行优先**：每个验证项最终都要能跑，纯文字描述不够
4. **黑盒优先**：尽量通过输入输出验证，不依赖内部状态
5. **pre/post 要互相能接上**：这是链式信任的基础

> **反面教材**：不要为了凑数写 "输出格式正确"、"变量非空"、"运行无报错" 这类几乎永远通过的验证。好的验证应该能区分正确实现和错误实现。

### 第五步：初始化状态（state 层）

规划阶段所有节点状态为 `not_started`，验证结果为空数组。

```json
"state": {
  "nodes": {
    "01_initialize": {
      "status": "not_started",
      "verify_results": { "pre": [], "core": [], "post": [] }
    }
  },
  "annotations": { "flow": [], "node": [] }
}
```

## JSON 格式速查

```json
{
  "version": "0.1.0",
  "meta": {
    "title": "算法名称",
    "phase": "Phase 1: ...",
    "project": "项目路径（可选）",
    "created": "YYYY-MM-DD",
    "updated": "YYYY-MM-DD",
    "benchmark": {
      "file": "data/instance.vrp",
      "known_optimal": 247,
      "source": "CVRPLIB / TSPLIB / 文献"
    }
  },
  "graph": {
    "nodes": [
      { "id": "start", "label": "开始", "type": "terminal" },
      { "id": "01_step_name", "label": "1. 步骤名", "sub": "副标题", "type": "process" },
      { "id": "check_xxx", "label": "条件?", "type": "decision" },
      { "id": "aux_action", "label": "辅助动作", "type": "auxiliary" }
    ],
    "edges": [
      { "from": "start", "to": "01_step_name" },
      { "from": "check_xxx", "to": "01_step_name", "label": "是" }
    ],
    "regions": [
      { "label": "主循环", "nodes": ["01_step_name", "check_xxx"] }
    ]
  },
  "contents": {
    "01_step_name": {
      "title": "1. 步骤名",
      "overview": "Markdown...",
      "how": "Markdown...",
      "verify": {
        "pre":  [{ "desc": "...", "check": "..." }],
        "core": [{ "desc": "...", "level": "L1", "method": "...", "cmd": "" }],
        "post": [{ "desc": "...", "check": "..." }]
      },
      "code": { "files": [], "snippet": "" },
      "refs": "",
      "pitfalls": ""
    }
  },
  "state": { "..." }
}
```

**字段约束：**
- `id`：只能用 `[a-z0-9_]`
- `type`：只能是 `process` / `decision` / `terminal` / `auxiliary`
- `level`：只能是 `L1` / `L2` / `L3`
- `status`：只能是 `not_started` / `discussing` / `theory_ok` / `implemented` / `verified`
- Markdown 字段中 LaTeX 用 `$...$`（行内）和 `$$...$$`（块级）

## 生成后自检

生成 JSON 后，逐项检查：

- [ ] 所有 `from`/`to` 引用的 id 都存在于 `nodes` 中
- [ ] 每个 `process` 节点在 `contents` 中都有内容
- [ ] 每条 A→B 边：A 的 post 能覆盖 B 的 pre
- [ ] 每个 `process` 节点的 core 验证直击正确性本质（不求多，但必须能区分对错）
- [ ] `state.nodes` 包含了所有在 `contents` 中出现的节点
- [ ] `regions` 中引用的节点 id 都存在
- [ ] JSON 可通过 `python -m json.tool` 校验
- [ ] Markdown 字段中没有未转义的特殊字符影响 JSON 解析

## 处理用户反馈

用户通过渲染器批注后会生成 `.feedback.md`，格式如下：

```markdown
# Feedback: 算法名
- Date: 2026-02-20T15:30:00
- Source: ../examples/xxx.json
- Annotations: 5

## Flow
- [node:01_initialize] 这里应该加一步数据预处理

## 1. 初始化
- [Overview] "初始列集合" → 需要说明什么是初始列
- [Verify] "T3 穷举验证" → 加上边界情况
```

收到反馈后：
1. 读取 `.feedback.md`
2. 按节点定位到 JSON 中对应位置
3. 修改内容（增删节点、修改文字、补充验证）
4. 重新写入 JSON
5. 告知用户刷新浏览器查看
