# 算法地图生成规范

## 适用场景

- 算法有多步骤、分支/循环结构
- 预计代码超 500 行或跨多轮对话
- 用户不读代码，靠验证建立信任

## 前置条件

需求已在对话中讨论清楚。CC 是技术方案制定者，用户是审核者。**不问问题，直接出图。** 除非需求不清楚，可以向用户发问。

## 执行纪律

**一口气执行 A1→B4，只在最后出图。不写散文再翻译。**

| 步骤组 | 做什么 | JSON 产物 |
|--------|--------|----------|
| **A1-A4** | 理解算法 → 节点方案 → 写 JSON 骨架 | graph + contents + verify 留空 |
| **B1-B4** | 示例数据 → 接口 → 验证设计 → 校验 | verify + test_instance 完整 |

**核心原则**：
- **连续执行不暂停**：A1 到 B4 一口气跑完，中间不等用户确认。唯一停点：B4 校验通过后出图
- **增量写文件**：A4 写 JSON 骨架，B1-B4 读文件补充验证，不依赖对话记忆
- **对话从简**：对话中只输出步骤号 + 一行进展。禁止在对话中输出大段伪代码、方案表格、JSON 片段
- **CC 读 JSON，用户看 HTML**：CC 始终读写 `algorithm-map.json`。用户看 standalone HTML（交互式流程图）。**禁止把 JSON 内容贴到对话中让用户看**

**调研控制**：
- **默认用自身知识**——CC 的训练数据覆盖绝大多数经典算法，直接用即可
- **不要"为了确认"而调研**——只在"确实不知道关键实现细节"时才搜索
- **禁止启动 Task 子 Agent 做调研**——如需搜索，在主对话中用 WebSearch，单次聚焦，3 分钟内完成
- 如果用户提供了论文/参考资料，直接读取，不要自己去搜

---

## Phase A：骨架

### A1. 理解算法，输出伪代码

- **输入**：对话上下文中的需求共识
- **输出**：对话中输出一行算法概要（几步、几层循环、关键模块），标注 `=== A1 ===`
- 伪代码是后续节点分解的基础——在脑中想清楚，但**不在对话中输出完整伪代码**（直接写入各节点 `how` 字段）
- 如果自身知识不足，拒绝编造臆想，可以网上搜索

### A2. 逐节点确定方案

- **输入**：A1 的伪代码
- **环境探查（必做，限 1 条命令）**：`pip list` 看全貌，根据结果选型。**禁止凭默认假设选型，也禁止逐个 `pip show` 挨个查。**
- **方法**：结合环境探查结果和自身知识，为每个节点选定方案。只在确实不知道关键细节时才搜索
- **输出**：对话中简要列出各节点的选定方案和一句话理由，标注 `=== A2 节点方案 ===`
- 不要在对话中输出详细伪代码——详细实现直接写入 JSON 的 contents.how
- **`how` 字段格式**：用代码块（```python）或结构化伪代码，禁止散文叙述夹 Unicode 数学符号（渲染器对散文格式的公式支持差）
- **选经典方案，不追前沿**。Plan 阶段目标是"跑通"，不是"最优"。前沿优化留给 build 之后。经过验证的、业界常用的、稳定的方案就是最好的选择

### A3. 判断算法类型

对话中标注 `=== A3 算法类型：xxx ===`。这个判断决定 Phase B 的验证策略。

| 类型 | 特征 | 验证核心思路 |
|------|------|-------------|
| **确定性精确算法** | 有数学最优保证（LP/MIP/DP/精确 B&B） | 精确比对 + 交叉求解器 |
| **随机/启发式算法** | 含随机性，无最优保证（ALNS/GA/SA/蒙特卡洛） | 固定种子精确验证 + 统计性质 + 多次运行 |
| **数值迭代算法** | 迭代逼近（梯度下降/牛顿法/迭代求解器） | 单步精确比对 + 收敛速度 + 精度容差 |
| **数据处理流水线** | 变换序列（ETL/特征工程） | 变换正确性 + 数据完整性 + 端到端比对 |

### A4. 生成 JSON 骨架

将 A1-A3 的产物写入 `algorithm-map.json`：

**填充内容**：
- `meta`：标题、日期、benchmark 信息
- `graph`：完整的 nodes + edges + regions
- `contents`：每个 process/decision 节点填写 title / overview / how / refs / pitfalls
- `verify`：**留空**（`{"pre":[], "core":[], "post":[]}`），Phase B 填充
- `state`：所有 process 节点 → `not_started`
- `code`：留空

**转换规则**：
- 函数调用 → `process` 节点
- if/else → `decision` 节点（整体一个节点，不拆分各分支）
- while 范围 / 逻辑模块 → `region`（必须填 `id` + `semantic`，`verify` 留空待 Phase B）
- 起止 → `terminal` 节点

**节点粒度**：一个 process ≈ 一个可独立测试的函数。简单赋值合并到相邻 process。auxiliary 仅用于图上不可缺少的中间标注，不承载实现逻辑。只有 process 和含判断逻辑的 decision 需要填 contents。

**填写算法蓝图**（`meta.blueprint`）：
- `core_idea`：2-3 句话说清算法的核心逻辑
- `data_flow`：模块间数据流向
- `key_assumptions`：算法成立的前提条件

**A4 自检**：
- 所有 edge 的 from/to 引用了存在的 node id
- decision 节点的出边有 label
- regions 中的 node id 都存在，每个 region 有 `id` 和 `semantic`
- `meta.blueprint` 三个字段均已填写

**收尾**：写入 JSON 后直接进入 B1，不暂停。

---

## Phase B：验证

**读取 A4 写入的 JSON 文件**继续工作（不依赖对话记忆）。

### B1. 设计数据结构 + 构造示例数据

- 设计节点间传递的数据结构，对话中简要输出
- 构造最小规模示例数据：
  - **必须能触发所有分支路径**——逐个 decision 节点检查，确保示例数据能让每个分支都被走到。如果单个示例不够，构造多个互补示例
  - 有已知正确答案（手算 / 枚举 / 标准算例）
  - 优先用行业标准测试数据，没有再自造
- 写入 JSON `meta.test_instance`（Markdown 格式）

### B2. 定义接口

为每个 process/decision 节点填写 `verify.pre` 和 `verify.post`：
- 格式：`{"desc": "条件描述", "check": "断言表达式"}`
- **每个节点至少 1 条 post 断言**（包括 decision 节点——断言判定条件本身的合法性）
- 逐条边检查：上游 post 能保证下游 pre

### B3. 识别关键点 + 设计验证

**不是每个环节都需要写测试。** 先识别关键点，再按关键性分级设计验证。

#### 第一步：标记关键性

逐节点、逐 region 判定是否"关键"，在对话中输出判定表，标注 `=== B3 关键点识别 ===`。

**节点关键性**——命中任一条即为关键：

| 标准 | 说明 |
|------|------|
| 非平凡算法 | 不是 API 调用 / 数据搬运，有自己的算法逻辑 |
| 已知易错 | 文献或经验中反复出 bug 的实现 |
| 接口耦合 | 一个约束 / 状态跨多个模块生效 |
| 静默出错 | 错了不崩溃，结果悄悄变差（最危险） |

**Region 关键性**——命中任一条即为关键：

| 标准 | 说明 |
|------|------|
| 有循环 | 迭代收敛类逻辑，终止条件可能有误 |
| 有交叉约束 | 子模块间通过共享状态耦合 |
| 可独立验证 | 存在不经过内部节点的独立验证路径 |

**将判定结果写入 JSON**：节点 `contents.xx.critical = true/false`，region `graph.regions[].critical = true/false`。B4 校验时从 JSON 读取，不依赖对话记忆。

**普通节点/region（`critical: false`）不写 core 测试**，只写 post 断言（`check` 表达式）。出错时 CC 靠报错信息自行修复。

#### 第二步：按关键性设计验证

**格式**（严格遵守，禁止写成字符串数组）：
- pre/post 每项：`{"desc": "条件描述", "check": "断言表达式"}`
- core 每项：`{"desc": "验证描述", "level": "L1", "method": "验证方法", "cmd": "pytest test_xxx.py -k 'test_name'"}`

**cmd 字段要求**：每条 core 验证项**必须**填写 `cmd` 字段。Plan 阶段填写测试意图 + 命令模板，Build 阶段补全实现。

**安放规则**：

| 对象 | 关键 | 普通 |
|------|------|------|
| 节点 | verify.core 写 L1 测试用例（含 cmd） | verify.core 留空，只写 post 断言 |
| Region | verify.core 写 L2 交叉验证（含 cmd） | verify.core 留空，只写 post 断言 |
| 全图 | 最后一个 process 节点写 L3（含 cmd）。若最后一步是 terminal，往前找最近的 process | — |

#### 第三步：关键 region 的 L2 设计（必做三步）

1. **一句话总结 region 语义** → 写入 `region.semantic`（描述 region 的输入→输出等价关系）

2. **找独立验证路径**：有没有一种**不经过 region 内部节点**的方式得到同样结果？
   - 精确算法：用独立求解器直接求解（如 Gurobi 直接解完整 LP）
   - 启发式：统计性质（收敛趋势、分布检验）
   - 数据流：端到端输入→输出比对
   - **如果找不到独立路径**：至少验证 region 输出满足的数学性质（如单调性、界的合法性）

3. **查下方算法类型表**，选择具体策略 → 写入 `region.verify.core`

**质量底线**：关键点的验证必须能区分正确实现和错误实现。禁止"输出非空"、"格式正确"这类永远通过的验证。

**L2 与 L3 的边界**：L2 验证 region 内部逻辑的正确性（用独立路径交叉验证），L3 验证整个算法端到端的结果。**禁止在 region L2 中写端到端基准测试**——那是 L3 的职责。

#### 按算法类型的验证设计指南

**确定性精确算法**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | 示例数据 → 精确比对期望值 | |
| L2 | 独立求解器交叉验证 | |
| L3 | 标准 benchmark 已知最优 | |

**随机/启发式算法**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | **固定种子 → 确定化 → 精确比对**。用极端参数消除随机选择（如 p=100 使概率选择确定化） | worst_removal(p=100) 移除 cost 最大的客户 |
| L2 | **统计性质测试**：分布、收敛趋势、单调性 | 轮盘赌 weights=[1,3,1]，10000 次采样，idx=1 频率 ∈ [0.55, 0.65] |
| L3 | **多次运行统计**：N 次运行报告 best/avg/worst。阈值需论证（引用文献 gap 或预实验） | |

**数值迭代算法**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | 单步迭代输入→输出精确比对 | 一步梯度下降：x_new == x - lr * grad |
| L2 | 收敛速度在理论上界内 | 强凸函数 100 步内 loss < 1e-6 |
| L3 | 最终精度在容差内 | 解与解析解误差 < 1e-8 |

**数据处理流水线**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | 单步变换输入→输出比对 | normalize(col) → mean≈0, std≈1 |
| L2 | 数据完整性检查 | 合并后行数 == 左表行数 |
| L3 | 端到端输出与参考输出比对 | 最终特征矩阵 == 参考输出 |

### B4. 校验 + 出图

更新 JSON 文件后，执行校验：

1. **JSON 合法**：json.load 正常解析
2. **边引用完整**：所有 edge from/to 对应存在的 node id
3. **Post→Pre 衔接**：逐条边检查上游 post 能保证下游 pre
4. **关键点有 core**：所有 `critical: true` 的节点 verify.core 至少 1 项（L1）；所有 `critical: true` 的 region verify.core 至少 1 项（L2）。`critical: false` 的至少有 post 断言
5. **State 完整**：所有 process 节点在 state.nodes 中有条目

校验通过后，生成 standalone HTML 并交付：

```bash
python C:/Users/ligon/CCA/algorithm-map/tools/export_standalone.py algorithm-map.json
```

输出交付：

```
=== Plan 完成 ===
[SHARE:algorithm-map.html的绝对路径]
请审阅完整地图（节点方案 + 验证设计）。
```

**这是 `/map plan` 的唯一交付点。** 之前所有步骤连续执行，到这里才停下等用户。
**交付的是 standalone HTML**（内嵌 JSON 的交互式流程图），不是渲染器 URL。

---

## JSON 骨架

```json
{
  "version": "0.1.0",
  "meta": { "title": "", "phase": "plan", "created": "", "updated": "",
            "blueprint": { "core_idea": "", "data_flow": "", "key_assumptions": "" },
            "benchmark": { "file": "", "known_optimal": null, "source": "" },
            "test_instance": "示例数据完整文本（Markdown）" },
  "graph": {
    "nodes": [{ "id": "01_xxx", "label": "步骤名", "type": "process" }],
    "edges": [{ "from": "start", "to": "01_xxx" }],
    "regions": [{
      "id": "main_loop", "label": "主循环", "semantic": "一句话描述 region 的输入→输出等价关系",
      "critical": true,
      "nodes": ["01_xxx"],
      "verify": { "pre": [], "core": [{"desc": "L2 交叉验证", "level": "L2", "method": "独立路径验证", "cmd": "pytest ..."}], "post": [] }
    }]
  },
  "contents": {
    "01_xxx": {
      "title": "", "overview": "", "how": "",
      "critical": false,
      "verify": {
        "pre":  [{"desc": "条件描述", "check": "断言表达式"}],
        "core": [],
        "post": [{"desc": "条件描述", "check": "断言表达式"}]
      },
      "code": { "files": [], "snippet": "" }, "refs": "", "pitfalls": ""
    }
  },
  "state": {
    "nodes": { "01_xxx": { "status": "not_started",
      "verify_results": { "pre": [], "core": [], "post": [] } } }
  }
}
```

## 升级已有地图（`/map upgrade`）

目标项目已有 `algorithm-map.json` 且部分/全部节点已 build 完成，用户要求升级某个节点的实现方案或新增节点。

### U1. 读取现有地图 + 理解升级需求

- 读取目标项目的 `algorithm-map.json`
- 对话中简要输出当前地图结构（节点列表 + 各节点状态）
- 确认用户意图：升级哪个节点 / 新增什么节点 / 新方案是什么

### U2. 影响分析

判断升级类型和影响范围：

| 类型 | 描述 | 影响范围 | 示例 |
|------|------|---------|------|
| **接口不变** | 只改内部实现，pre/post 不变 | 仅当前节点 | |
| **接口变更** | post 条件变化，影响下游 pre | 当前节点 + 下游受影响节点 | 增加时间窗 → Data 结构变化 → 多节点连锁 |
| **新增节点** | 添加新 process 节点 | 新节点 + 相邻节点的边调整 | 新增 cluster_removal 算子 |

对话中输出影响分析，标注 `=== U2 影响分析 ===`：
- 将修改的节点列表
- 将重置状态的节点列表
- 不受影响的节点列表
- 如果影响范围 > 3 个节点，提醒用户确认再继续

### U3. 修改地图

**升级已有节点**：
- 更新 contents（how / overview / refs / pitfalls 中受影响的部分）
- 更新 verify.core（新方案可能需要新的验证项）
- 如果 post 变了，检查并更新下游节点的 pre

**新增节点**：
- graph.nodes 添加节点
- graph.edges 添加/调整边（如果插在两个已有节点之间，删旧边加两条新边）
- graph.regions 按需更新
- 填写完整 contents（title / overview / how / verify / refs / pitfalls）
- state.nodes 添加条目（not_started）

**状态重置**：
- 被修改的节点 → `not_started`，verify_results 清空
- 接口变更时，下游受影响的节点也重置
- **未受影响的节点保持原状态不动**——这是升级的核心价值：不破坏已验证的部分

### U4. 校验 + 出图

同 B4 校验流程。额外检查：
- 新增的边引用合法
- 重置的节点 state 正确

生成 standalone HTML 并输出变更摘要：

```bash
python C:/Users/ligon/CCA/algorithm-map/tools/export_standalone.py algorithm-map.json
```

```
=== 升级完成 ===
修改节点：05_destroy（shaw_removal → RL-based removal）
新增节点：无
重置节点：05_destroy
未受影响：01_parse, 02_init_sol, 03_init_weights, ...（保持 verified）
[SHARE:algorithm-map.html的绝对路径]
请审阅变更，确认后用 /map build 重建受影响的节点。
```

---

## 处理用户反馈

用户通过审阅系统批注后，反馈消息自动发回对话。CC 读取反馈，按节点修改 JSON，重新生成 standalone HTML 并 `[SHARE:]` 交付。
