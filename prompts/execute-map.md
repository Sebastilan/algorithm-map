# 算法地图执行规范

CC 按算法地图自动实现代码的协议。用户输入 `/map build`，CC 读取本规范后自动执行到底。

## 核心原则

1. **Benchmark 驱动**：用已知最优值的标准算例验证，不手动设计测试实例
2. **链式数据流**：上游节点的输出就是下游节点的输入，checkpoint 自动形成测试链
3. **一条断言胜过百条表面检查**：`solver(benchmark) == known_optimal` 通过即全部正确
4. **全自动**：新 CC 窗口读 JSON 即可断点续做，无需人工引导

## 自动化流程

```python
def map_build(project_dir):
    # 1. 上下文恢复
    map_json = read("algorithm-map.json")
    nodes = scan_state(map_json)  # {verified, implemented, not_started}
    benchmark = map_json["meta"]["benchmark"]  # {file, known_optimal}

    if all_verified(nodes):
        print("Build 已完成")
        return

    # 2. 实现所有未完成的 process 节点
    for node in topological_sort(process_nodes):
        if node.status == "verified":
            continue
        implement_node(node)  # 读 contents → 写代码 → 保存 checkpoint
        set_status(node, "implemented")

    # 3. 端到端验证
    result = run_pipeline(benchmark["file"])
    if result == benchmark["known_optimal"]:
        for node in process_nodes:
            set_status(node, "verified")
        print(f"PASS — {benchmark['file']}: {result}")
    else:
        diagnose(benchmark)  # checkpoint 链定位故障节点
```

## Benchmark 算例

地图 JSON 的 `meta.benchmark` 字段定义验证用算例：

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

## 单节点实现

对每个 process 节点，按顺序执行：

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
- 端到端验证失败时，沿 checkpoint 链定位故障节点
- 新对话恢复时，不必重跑已完成的节点

## 并行策略

### 节点并行（独立节点同时构建）
```
1. 拓扑排序 → 按依赖层级分组
2. 同一层级的节点无依赖关系 → 用 Task 工具启动子 Agent 并行实现
3. 每个子 Agent 负责一个节点：读 contents → 写代码 → 保存 checkpoint
4. 所有节点实现完毕后统一做端到端验证
```

### 管线并行（实现与验证重叠）
```
当前节点 implemented → 立刻启动端到端测试（可能部分通过）
同时开始实现下一个节点
端到端测试的反馈可以及时纠正正在实现的节点
```

### 子 Agent 使用模板
```
Task(subagent_type="general-purpose", prompt="""
你负责实现算法地图节点 {node_id}。

项目目录：{project_dir}
上游 checkpoint：{upstream_checkpoint_path}

节点内容：
{contents[node_id].overview}
{contents[node_id].how}

请：
1. 创建 {code.files} 中列出的文件
2. 实现核心逻辑
3. 保存 checkpoint 到 _checkpoints/{node_id}.json
""")
```

## 端到端验证

所有 process 节点 implemented 后执行：

```python
def verify_end_to_end(benchmark):
    result = solve(benchmark["file"])

    if result == benchmark["known_optimal"]:
        return "PASS"

    # FAIL → 诊断
    return diagnose(benchmark)
```

**验证通过**：所有 process 节点标记 `verified`，更新 JSON。

**验证失败**：进入诊断流程。

## 诊断流程（端到端失败时）

沿 checkpoint 链逐步定位故障节点：

```
1. 从第一个节点开始，依次检查 checkpoint 数据的合理性：
   - 节点 01 的 checkpoint：距离矩阵对称？需求 > 0 且 ≤ Q？
   - 节点 02 的 checkpoint：LP 有可行解？obj > 0？
   - 节点 03 的 checkpoint：对偶值非负？维度正确？
   - 节点 04 的 checkpoint：返回列容量合法？RC < 0？
   - ...
2. 找到第一个不合理的 checkpoint → 对应节点有 bug
3. 修复该节点 → 重跑端到端验证
4. 重复直到 PASS
```

关键：**诊断用的检查项就是 verify.pre/post 里的条件**——这些条件终于发挥了它的真正作用：不是日常验证，而是故障定位。

## 状态管理

### 状态流转

```
not_started → implemented → verified
```

简化为三个状态。中间的 `discussing` / `theory_ok` 在自动化流程中没有意义。

### JSON 更新

使用 `map_utils.py` 工具（首次 build 时创建）：

```python
from map_utils import set_status, set_verified, save_checkpoint

# 实现完成
set_status("04_pricing", "implemented")

# 端到端验证通过后
set_verified("04_pricing",
    pre=[True, True, True],
    core=[True],  # 端到端验证 = 一条 core
    post=[True, True, True])
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
   - 有 implemented 但未 verified → 跑端到端验证
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
  读 JSON → 找 benchmark → 拓扑序实现节点 → 端到端验证 → 更新状态

单节点：读 overview/how → 读上游 checkpoint → 写代码 → 存 checkpoint

验证：solve(benchmark) == known_optimal

失败：沿 checkpoint 链逐节点检查 → 找到故障节点 → 修复 → 重跑
```
