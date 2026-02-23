# 算法地图执行规范（监工模式）

监工 CC 读取本规范后，调度 Worker CC 并行实现算法地图中的各节点。监工负责调度、验证、审查；Worker 负责写代码和提交。

## 核心原则

1. **逐节点验证**：实现一个、验证一个、确认一个，bug 不过夜
2. **三方制衡**：Planner 定标准（verify.core）、Worker 写代码跑数值、Reviewer（Sonnet 子 Agent）审代码逻辑
3. **链式数据流**：上游 checkpoint 就是下游输入，自动形成测试链
4. **断点续做**：新对话读 map JSON + getStatusSnapshot 即可从上次断点继续
5. **监工不写业务代码**：监工只调度、验证、审查，不碰目标项目的业务逻辑

## 自动化流程

```python
def map_build(project_dir):
    # 监工 CC 执行
    map_json = loadMap("algorithm-map.json")
    validated = validateMap(map_json)
    verified = {id for id, s in getStatusSnapshot() if s == "verified"}

    while verified < all_process_nodes:
        batch = nextBatch(graph, verified)        # foreman/graph.mjs

        # 文件冲突检查 → 有冲突的强制串行
        batch = resolve_conflicts(batch)

        for node_id in batch[:max_parallel]:
            task = buildNodeTask(map_json, node_id, cwd)
            dispatch(task)                         # spawn Worker

        # 轮询等待
        for node_id in dispatched:
            wait_for_commit(node_id)               # git log 检测
            run_L1(node_id)                        # verify.mjs
            review(node_id)                        # Sonnet 子 agent 审代码
            if review.flagged:
                send_fix_to_worker(node_id)        # spawn send-wait
            setNodeVerified(path, node_id, results) # map-state.mjs
            verified.add(node_id)

        # region 完成 → L2
        for region in affected_regions:
            if isRegionComplete(graph, state, region.label):
                run_L2(region)

    run_L3(benchmark)
    generate_report()
```

## 角色分工

### Worker 职责

1. 读 contents[node_id].overview → 理解做什么
2. 读 contents[node_id].how → 理解怎么做
3. 读上游 checkpoint → 知道输入数据长什么样
4. 写代码（按 code.files 路径）
5. 保存 checkpoint：
   ```
   _checkpoints/<node_id>.json = {
     "node_id": "...",
     "input_from": "上游 node_id",
     "output": { 本节点的输出数据 }
   }
   ```
6. 跑 L1 自检（verify.core 中 level: "L1" 的验证项）
7. **必须 commit**（不 push）

### 监工职责

1. 通过 foreman 拓扑排序确定 batch
2. 文件冲突检查（同一文件不允许多 Worker 并行改）
3. 调 spawn 启动 Worker
4. 轮询检测 Worker 完成（git log）
5. 启动 Reviewer 子 Agent 审查代码
6. 通过 foreman 更新 map state
7. 触发 L2/L3 验证

**Checkpoint 是数据流的快照**，不是测试数据。它的作用：
- 下游节点实现时可以直接读取上游输出，理解接口
- 验证失败时，沿 checkpoint 链定位故障节点
- 新对话恢复时，不必重跑已完成的节点

## L1 自检

Worker 自己执行 verify.core 中 `level: "L1"` 的验证项。

- **通过** → 监工启动 Reviewer
- **失败** → Worker 改代码，重跑，直到通过
- **认为期望值有误** → 标记争议（`"dispute": "理由"`），不改期望值，继续往下走

### 硬暂停触发条件

以下任一条件触发时，**必须停止当前节点工作**，输出诊断信息并等待用户决策。不得自行跳过或静默处理。

| # | 触发条件 | 说明 |
|---|---------|------|
| 1 | **L1 连续失败 3 次** | 同一验证项修复 3 轮仍不通过，说明实现思路可能有根本问题 |
| 2 | **实现思路与 how 本质偏离** | how 描述的是算法 A，实际写了算法 B |
| 3 | **需要修改上游节点的 post 条件** | 说明 Plan 本身有缺陷，当前节点无法在现有契约下完成 |

**触发时必须输出**：

```
硬暂停：[触发条件编号和名称]
当前节点：{node_id}
问题描述：...
已尝试的方案：...
建议选项：A) ... / B) ... / C) 用户指示
```

等待用户回复后再继续。

## 代码审查（Reviewer 子 Agent）

L1 自检通过后，监工启动 Reviewer 子 Agent。**使用 Sonnet 模型，审查模板固定不可改**。

监工只填三个变量（`{node_id}`、`{how}`、`{code_files}`），审查逻辑锁死：

```
Task(subagent_type="general-purpose", model="sonnet", prompt="""
你是代码审查员。只读代码，不跑测试，不改代码。

## 审查对象
节点：{node_id}
算法规格（how）：
{contents[node_id].how}

实现文件：{code_files}

## 检查清单（逐项回答 OK 或 FLAG + 证据）
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

- **CLEAN** → 监工标记节点 verified
- **FLAG** → 监工通过 spawn send-wait 让 Worker 修复 → 重新走自检 + 审查

## 分层验证

Plan 阶段设计了三层验证（verify.core 中的 level 字段），Build 阶段按节奏执行：

| 层级 | 触发时机 | 内容 |
|------|---------|------|
| **L1** | 每个节点实现后 | 单节点功能验证（Worker 自检 + Reviewer 审代码） |
| **L2** | region 所有节点 verified 后 | 集成验证（如 CG 循环 LP 值 == Gurobi 直接求解值） |
| **L3** | 全部节点 verified 后 | 端到端 benchmark 验证 |

L2 验证项在 region 最后一个 process 节点的 verify.core（`level: "L2"`）中。
L3 验证项在全图最后一个 process 节点的 verify.core（`level: "L3"`）中。

### Region 进度追踪

每个节点 verified 后，监工输出该节点所属 region 的进度：

```
{node_id} verified
   Region "{region_label}": {X}/{Y} nodes verified
```

当 region 所有 process 节点 verified 时，**自动触发 L2 验证**——直接读 JSON 的 `graph.regions` 确定边界。

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
- 能触发算法的关键分支

**没有 benchmark 时**：要求用户提供，或在第一个节点实现后搜索合适的标准算例。

## 诊断流程（验证失败时）

### L1 失败

Worker 直接在当前节点修复，不涉及其他节点。

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
| **how 细节调整** | Worker 直接更新 JSON 的 contents.how |
| **verify 期望值有误** | 标记争议，不擅自修改，继续往下走 |
| **节点需要拆分/新增** | 暂停 Build，走 `/map upgrade` |
| **流程结构变更** | 暂停 Build，走 `/map upgrade` |

原则：**内容层 Worker 可调，结构层必须走 upgrade**。

## 并行策略（默认）

监工通过 foreman 的 `orchestrate.mjs` 自动按拓扑层级并行调度。`nextBatch()` 返回当前可并行的节点集合。

**冲突处理**：
- 同一文件被多个节点引用 → 强制串行（`checkFileOverlap` 检测）
- 同 region 内有线性依赖的节点 → 按拓扑序串行

**资源限制**：
- `--max-parallel` 参数控制并行上限（默认 3）
- 16GB 机器实测 3 个 Opus Worker 是安全上限

## 状态管理

### 状态流转

```
not_started → implemented → verified
```

### 状态更新

状态更新由监工通过 foreman 模块完成：

```bash
# 更新节点状态
node src/map-state.mjs <map.json> set <nodeId> <status>

# 查看状态快照
node src/map-state.mjs <map.json> snapshot
```

foreman 源码路径：`C:/Users/ligon/CCA/cc-foreman/src/`

- `map-state.mjs` — 原子读写 map JSON state
- `graph.mjs` — 拓扑排序、nextBatch、isRegionComplete
- `orchestrate.mjs` — 编排主循环（dry-run 查看分派计划）
- `verify.mjs` — 验收标准验证框架
- `dispatch.mjs` — 任务分派（生成 prompt → 调 spawn）

## 上下文恢复（新对话）

```
1. 监工读 algorithm-map.json
2. 调 getStatusSnapshot() 获取当前进度：
   - 全部 verified → "Build 已完成"
   - 有 implemented 但未 verified → 跑 Reviewer 审查
   - 有 not_started → 继续调度
3. 读 _checkpoints/ → 了解已完成节点的输出数据
4. 继续编排循环（无需人工引导）
```

## 反馈集成

用户可能通过渲染器提交批注（`.feedback.md`）：

```
检查 .feedback.md → 按 [node:id] 定位 → 处理反馈 → 清空文件
```

## 速查

```
/map build 监工模式流程：
  读 JSON → getStatusSnapshot → nextBatch → dispatch Workers
  → 轮询 git log → verify.mjs L1 → Reviewer（Sonnet）→ setNodeVerified
  → region 完成跑 L2 → 全部完成跑 L3

角色分离：
  监工 = 调度 + 验证 + 审查（不写业务代码）
  Worker = 读 how → 写代码 → 存 checkpoint → L1 自检 → commit

三方制衡：Planner 定标准 / Worker 写代码跑数值 / Reviewer 审代码逻辑

诊断：沿 checkpoint 链定位故障节点 → 修复 → 重验

Plan 变更：内容层直接改，结构层走 /map upgrade

状态管理：node src/map-state.mjs <map.json> set <nodeId> <status>
```
