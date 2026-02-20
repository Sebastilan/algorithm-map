# 算法地图生成规范

## 适用场景

- 算法有多步骤、分支/循环结构
- 预计代码超 500 行或跨多轮对话
- 用户不读代码，靠验证建立信任

## 前置条件

需求已在对话中讨论清楚。CC 是技术方案制定者，用户是审核者。**不问问题，直接出图。** 除非需求不清楚，可以向用户发问。

## 执行纪律

**两阶段增量构建 JSON，不写散文再翻译。**

| 阶段 | 做什么 | JSON 产物 | 结束动作 |
|------|--------|----------|---------|
| **Phase A** | 理解算法 → 节点方案 → 写 JSON | graph 完整 + contents 主体 + verify 留空 | 渲染器 URL → **用户审阅流程图** |
| **Phase B** | 示例数据 → 接口 → 验证设计 → 校验 | verify 完整 + meta.test_instance 完整 | 校验通过 → **用户审阅完整地图** |

**核心原则**：
- **增量写文件**：每阶段产物直接写入 JSON 文件。Phase B 读取 Phase A 写的文件继续工作，不依赖对话记忆
- **对话从简**：对话中只输出简要说明（标注步骤号），详细内容直接进 JSON
- **每阶段内连续执行不暂停**，阶段之间等待用户确认

**调研控制**：
- **默认用自身知识**——CC 的训练数据覆盖绝大多数经典算法，直接用即可
- **不要"为了确认"而调研**——只在"确实不知道关键实现细节"时才搜索
- **禁止启动 Task 子 Agent 做调研**——如需搜索，在主对话中用 WebSearch，单次聚焦，3 分钟内完成
- 如果用户提供了论文/参考资料，直接读取，不要自己去搜

---

## Phase A：骨架

### A1. 理解算法，输出伪代码

- **输入**：对话上下文中的需求共识
- **输出**：对话中输出伪代码（Python 风格，注释标注逻辑分组），标注 `=== A1 伪代码 ===`
- 这是最重要的一步——伪代码是后续所有工作的基础
- 如果自身知识不足，拒绝编造臆想，可以网上搜索

伪代码示例：

```python
def BPC(instance):
    data = initialize(instance)
    columns = initial_columns(data)
    UB = greedy(data)

    queue = [root_node]
    while queue:                         # --- B&B 主循环 ---
        node = queue.pop()
        while True:                      # --- 列生成循环 ---
            obj, x = solve_RMP(columns, node.bounds)
            duals = extract_duals()
            new_col = pricing(duals, data)
            if new_col.rc >= 0: break    # CG 收敛
            columns.add(new_col)
        if is_integer(x):                # 整数解 → 更新上界
            UB = min(UB, obj)
        elif obj < UB:                   # 分数解 → 分支
            children = branch(node, x)
            queue.extend(children)
    return best_solution
```

### A2. 逐节点确定方案

- **输入**：A1 的伪代码
- **方法**：用自身知识为每个节点选定方案。只在确实不知道关键细节时才搜索（不要"为了确认"而搜索）
- **输出**：对话中简要列出各节点的选定方案和一句话理由，标注 `=== A2 节点方案 ===`
- 不要在对话中输出详细伪代码——详细实现直接写入 JSON 的 contents.how
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
- while 范围 → `region`
- 起止 → `terminal` 节点

**节点粒度**：一个 process ≈ 一个可独立测试的函数。简单赋值合并到相邻 process。auxiliary 仅用于图上不可缺少的中间标注，不承载实现逻辑。只有 process 和含判断逻辑的 decision 需要填 contents。

**A4 自检**：
- 所有 edge 的 from/to 引用了存在的 node id
- decision 节点的出边有 label
- regions 中的 node id 都存在

**收尾**：写入 JSON，启动渲染器，输出 URL：

```
=== Phase A 完成 ===
渲染器 URL: http://localhost:8765/renderer/render.html?src=...
请审阅流程图结构，确认后继续 Phase B。
```

---

## Phase B：验证

**从文件读取 Phase A 生成的 JSON**（不依赖对话记忆）。

### B1. 设计数据结构 + 构造示例数据

- 设计节点间传递的数据结构，对话中简要输出
- 构造最小规模示例数据：
  - 能触发所有分支路径
  - 有已知正确答案（手算 / 枚举 / 标准算例）
  - 优先用行业标准测试数据，没有再自造
- 写入 JSON `meta.test_instance`（Markdown 格式）

### B2. 定义接口

为每个 process/decision 节点填写 `verify.pre` 和 `verify.post`：
- 格式：`{"desc": "条件描述", "check": "断言表达式"}`
- 逐条边检查：上游 post 能保证下游 pre

### B3. 设计分层验证

**根据 A3 的算法类型**，为每个节点设计 `verify.core`。

**格式**（严格遵守，禁止写成字符串数组）：
- pre/post 每项：`{"desc": "条件描述", "check": "断言表达式"}`
- core 每项：`{"desc": "验证描述", "level": "L1", "method": "验证方法"}`

**安放规则**：
- L1 → 各 process 节点的 verify.core
- L2 → region 最后一个 process 节点的 verify.core（level: "L2"）
- L3 → 全图最后一个 **process** 节点的 verify.core（level: "L3"）

**质量底线**：禁止"输出非空"、"格式正确"、"运行无报错"这类永远通过的验证。好的验证能区分正确实现和错误实现。

#### 按算法类型的验证设计指南

**确定性精确算法**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | 示例数据 → 精确比对期望值 | solve_RMP → obj == 51.0 |
| L2 | 独立求解器交叉验证 | CG 循环 LP 值 == Gurobi LP 值 |
| L3 | = 标准 benchmark 已知最优 | BPC(E-n13-k4) == 247 |

**随机/启发式算法**：

| 层级 | 策略 | 示例 |
|------|------|------|
| L1 | **固定种子 → 确定化 → 精确比对**。用极端参数消除随机选择（如 p=100 使概率选择确定化） | worst_removal(p=100) 移除 cost 最大的客户 |
| L2 | **统计性质测试**：分布、收敛趋势、单调性 | 轮盘赌 weights=[1,3,1]，10000 次采样，idx=1 频率 ∈ [0.55, 0.65] |
| L3 | **多次运行统计**：N 次运行报告 best/avg/worst。阈值需论证（引用文献 gap 或预实验） | ALNS(E-n13-k4) 10 次，best ≤ 255，avg ≤ 265 |

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
4. **Verify 非空**：所有 process 节点的 verify.core 至少 1 项
5. **State 完整**：所有 process 节点在 state.nodes 中有条目

校验通过后，更新渲染器文件，输出 URL：

```
=== Phase B 完成 ===
渲染器 URL: http://localhost:8765/renderer/render.html?src=...
请审阅完整地图（节点方案 + 验证设计）。
```

---

## JSON 骨架

```json
{
  "version": "0.1.0",
  "meta": { "title": "", "phase": "plan", "created": "", "updated": "",
            "benchmark": { "file": "", "known_optimal": null, "source": "" },
            "test_instance": "示例数据完整文本（Markdown）" },
  "graph": {
    "nodes": [{ "id": "01_xxx", "label": "步骤名", "type": "process" }],
    "edges": [{ "from": "start", "to": "01_xxx" }],
    "regions": [{ "label": "主循环", "nodes": ["01_xxx"] }]
  },
  "contents": {
    "01_xxx": {
      "title": "", "overview": "", "how": "",
      "verify": {
        "pre":  [{"desc": "条件描述", "check": "断言表达式"}],
        "core": [{"desc": "验证描述", "level": "L1", "method": "验证方法"}],
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
| **接口不变** | 只改内部实现，pre/post 不变 | 仅当前节点 | greedy_insertion → regret-3 insertion |
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

输出变更摘要：

```
=== 升级完成 ===
修改节点：05_destroy（shaw_removal → RL-based removal）
新增节点：无
重置节点：05_destroy
未受影响：01_parse, 02_init_sol, 03_init_weights, ...（保持 verified）
渲染器 URL: http://localhost:8765/renderer/render.html?src=...
请审阅变更，确认后用 /map build 重建受影响的节点。
```

---

## 处理用户反馈

用户在渲染器批注后生成 `.feedback.md`，读取后按节点修改 JSON，告知用户刷新浏览器。
