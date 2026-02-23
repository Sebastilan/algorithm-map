# 算法地图执行规范

CC 按算法地图逐节点实现代码的协议。用户输入 `/map build`，CC 读取本规范后自动执行。

## 核心原则

1. **逐节点验证**：实现一个、验证一个、确认一个，bug 不过夜
2. **三方制衡**：Planner 定标准（verify.core）、Builder 写代码跑数值、Reviewer 审代码逻辑
3. **链式数据流**：上游 checkpoint 就是下游输入，自动形成测试链
4. **断点续做**：新 CC 窗口读 JSON 即可从上次断点继续，无需人工引导

## 自动化流程

```python
def map_build(project_dir):
    map_json = read("algorithm-map.json")
    nodes = scan_state(map_json)

    if all_verified(nodes):
        print("Build 已完成")
        return

    for node in topological_sort(process_nodes):
        if node.status == "verified":
            continue

        # --- 单节点循环 ---
        implement(node)                    # 读 contents → 写代码 → 存 checkpoint
        self_test(node)                    # Builder 跑 verify.core 中的 L1
        review_result = code_review(node)  # Reviewer 子 Agent（Sonnet）审代码
        if review_result.flagged:
            fix_and_retry(node)            # 改代码 → 重新自检 → 重新审查
        set_status(node, "verified")

        # region 完成 → L2
        if region_complete(node):
            run_L2(region)

    # 全部完成 → L3
    run_L3(benchmark)
```

## 单节点循环

### 步骤 1：实现

```
1. 读 contents[node_id].overview  → 理解做什么
2. 读 contents[node_id].how       → 理解怎么做
3. 读上游 checkpoint               → 知道输入数据长什么样
4. 写代码（按 code.files 路径）
5. 保存 checkpoint：
   _checkpoints/<node_id>.json = {
     "node_id": "...",
     "input_from": "上游 node_id",
     "output": { 本节点的输出数据 }
   }
6. set_status(node_id, "implemented")
```

**Checkpoint 是数据流的快照**，不是测试数据。它的作用：
- 下游节点实现时可以直接读取上游输出，理解接口
- 验证失败时，沿 checkpoint 链定位故障节点
- 新对话恢复时，不必重跑已完成的节点

### 步骤 2：自检（Builder 跑 L1）

Builder 自己执行 verify.core 中 `level: "L1"` 的验证项。这些验证项是 Plan 阶段定义的。

- **通过** → 继续步骤 3（代码审查）
- **失败** → 改代码，重跑，直到通过
- **认为期望值有误** → 标记争议（`"dispute": "理由"`），不改期望值，继续往下走

### 硬暂停触发条件

以下任一条件触发时，CC **必须停止当前节点工作**，向用户输出诊断信息并等待决策。不得自行跳过或静默处理。

| # | 触发条件 | 说明 |
|---|---------|------|
| 1 | **L1 连续失败 3 次** | 同一验证项修复 3 轮仍不通过，说明实现思路可能有根本问题 |
| 2 | **实现思路与 how 本质偏离** | how 描述的是算法 A，实际写了算法 B（如 how 说"标签算法解 ESPPRC"，实际写了"Dijkstra 近似"） |
| 3 | **需要修改上游节点的 post 条件** | 说明 Plan 本身有缺陷，当前节点无法在现有契约下完成 |

**触发时必须输出**：

```
⚠️ 硬暂停：[触发条件编号和名称]
当前节点：{node_id}
问题描述：...
已尝试的方案：...
建议选项：A) ... / B) ... / C) 用户指示
```

等待用户回复后再继续。

### 步骤 3：代码审查（Reviewer 子 Agent）

L1 自检通过后，启动 Reviewer 子 Agent。**使用 Sonnet 模型，审查模板固定不可改**。

Builder 只填三个变量（`{node_id}`、`{how}`、`{code_files}`），审查逻辑锁死：

```
Task(subagent_type="general-purpose", model="sonnet", prompt="""
你是代码审查员。只读代码，不跑测试，不改代码。

## 审查对象
节点：{node_id}
算法规格（how）：
{contents[node_id].how}

实现文件：{code_files}

## 检查清单（逐项回答 ✓ 或 ✗ + 证据）
1. 算法结构是否匹配 how 描述的步骤
2. 核心计算是真实计算还是硬编码/stub
3. 有无针对特定输入的 if 特判
4. 有无被跳过/注释掉的关键步骤
5. 数据来源是上游 checkpoint 还是凭空构造
6. 若此节点是 region 最后一个 process 节点，L2 验证是否已触发

## 输出格式
CLEAN — 无问题
或
FLAG — [问题编号] 具体描述 + 代码位置
""")
```

- **CLEAN** → 节点标记 verified
- **FLAG** → Builder 查看具体问题 → 修复代码 → 重新走自检 + 审查

## 分层验证

Plan 阶段设计了三层验证（verify.core 中的 level 字段），Build 阶段按节奏执行：

| 层级 | 触发时机 | 内容 |
|------|---------|------|
| **L1** | 每个节点实现后 | 单节点功能验证（Builder 自检 + Reviewer 审代码） |
| **L2** | region 所有节点 verified 后 | 集成验证（如 CG 循环 LP 值 == Gurobi 直接求解值） |
| **L3** | 全部节点 verified 后 | 端到端 benchmark 验证 |

L2 验证项在 region 最后一个 process 节点的 verify.core（`level: "L2"`）中。
L3 验证项在全图最后一个 process 节点的 verify.core（`level: "L3"`）中。

### Region 进度追踪

每个节点 verified 后，CC **必须**输出该节点所属 region 的进度：

```
✅ {node_id} verified
   Region "{region_label}": {X}/{Y} nodes verified
```

当 region 所有 process 节点 verified 时，**自动触发 L2 验证**，不需要 CC 自行判断 region 边界——直接读 JSON 的 `graph.regions` 确定。

**Reviewer 额外检查项**：Reviewer 审查清单中增加一条——"L2 是否在 region 完成时按时触发"。如果 Builder 跳过了 L2，Reviewer 应 FLAG。

## Benchmark 算例

地图 JSON 的 `meta.benchmark` 字段定义 L3 验证用算例：

```json
{
  "meta": {
    "benchmark": {
      "file": "data/E-n13-k4.vrp",
      "known_optimal": 247,
      "source": "CVRPLIB"
    }
  }
}
```

**选择标准**：
- 小规模（< 20 节点），几秒钟能跑完
- 有公认最优值（文献/CVRPLIB/TSPLIB）
- 能触发算法的关键分支（如 B&B 需要实际分支的算例）

**没有 benchmark 时**：要求用户提供，或在第一个节点实现后搜索合适的标准算例。

## 诊断流程（验证失败时）

### L1 失败

直接在当前节点修复，不涉及其他节点。

### L2 失败

沿 region 内的 checkpoint 链逐步检查：

```
1. 依次检查 region 内各节点的 checkpoint 数据合理性
2. 用 verify.pre/post 条件逐节点验证
3. 找到第一个不合理的 checkpoint → 对应节点有 bug
4. 回退该节点状态 → 修复 → 重跑 L1 + 审查 → 重跑 L2
```

### L3 失败

沿全局 checkpoint 链逐 region 定位。先找到故障 region，再在 region 内定位故障节点。

## Plan 变更规则

Build 过程中可能发现 Plan 的内容需要调整：

| 变更类型 | 处理方式 |
|---------|---------|
| **how 细节调整** | Builder 直接更新 JSON 的 contents.how |
| **verify 期望值有误** | 标记争议，不擅自修改，继续往下走 |
| **节点需要拆分/新增** | 暂停 Build，走 `/map upgrade` |
| **流程结构变更** | 暂停 Build，走 `/map upgrade` |

原则：**内容层 Builder 可调，结构层必须走 upgrade**。

## 并行策略（可选）

当地图中存在同一拓扑层级的独立节点时，可以用 Task 子 Agent 并行实现。

**前提**：
- 共同上游节点已 verified
- 项目基础设施已建立（数据结构、工具函数）
- 两个节点不修改同一文件

**做法**：
- 用 Task 工具为每个独立节点启动子 Agent
- 每个子 Agent 完成实现 + 自检
- 所有子 Agent 完成后，主 Agent 逐个启动 Reviewer

**默认串行，并行是可选加速项。** 大多数算法图的节点有线性依赖，并行机会不多。

## 状态管理

### 状态流转

```
not_started → implemented → verified
```

### JSON 更新

使用 `map_utils.py` 工具（首次 build 时创建）：

```python
from map_utils import set_status, set_verified, save_checkpoint

# 实现完成
set_status("04_pricing", "implemented")

# L1 自检 + 审查通过后
set_verified("04_pricing",
    pre=[True, True],
    core=[True, True],
    post=[True, True])
```

### map_utils.py 模板

```python
"""算法地图状态更新工具。"""
import json
from pathlib import Path

MAP_PATH = Path(__file__).parent / "algorithm-map.json"

def load_map():
    with open(MAP_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_map(data):
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def set_status(node_id, status):
    data = load_map()
    data["state"]["nodes"][node_id]["status"] = status
    save_map(data)

def set_verified(node_id, pre, core, post, code_files=None, snippet=""):
    data = load_map()
    node = data["state"]["nodes"][node_id]
    node["status"] = "verified"
    node["verify_results"] = {"pre": pre, "core": core, "post": post}
    if code_files:
        data["contents"][node_id]["code"]["files"] = code_files
    if snippet:
        data["contents"][node_id]["code"]["snippet"] = snippet
    save_map(data)

def save_checkpoint(node_id, output_data):
    path = Path(__file__).parent / "_checkpoints" / f"{node_id}.json"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
```

## 上下文恢复（新对话）

```
1. 读 algorithm-map.json
2. 扫描 state.nodes：
   - 全部 verified → "Build 已完成"
   - 有 implemented 但未 verified → 跑 L1 自检 + Reviewer 审查
   - 有 not_started → 继续实现
3. 读 _checkpoints/ → 了解已完成节点的输出数据
4. 继续流程（无需人工引导）
```

## 反馈集成

用户可能通过渲染器提交批注（`.feedback.md`）：

```
检查 .feedback.md → 按 [node:id] 定位 → 处理反馈 → 清空文件
```

## 速查

```
/map build 自动流程：
  读 JSON → 拓扑序 → 逐节点（实现 → L1 自检 → Reviewer 审代码 → verified）
  → region 完成跑 L2 → 全部完成跑 L3

单节点：读 how → 读 checkpoint → 写代码 → 自检 L1 → Reviewer（Sonnet）→ verified

三方制衡：Planner 定标准 / Builder 写代码跑数值 / Reviewer 审代码逻辑

诊断：沿 checkpoint 链定位故障节点 → 修复 → 重验

Plan 变更：内容层直接改，结构层走 /map upgrade
```
