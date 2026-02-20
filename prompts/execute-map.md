# 算法地图执行规范

本文档是 Claude Code 按算法地图逐节点实现代码的执行协议。适用于 Build 阶段——地图 JSON 已经过用户审核确认，进入编码实施。

## 前提条件

- 算法地图 JSON 已生成并通过用户审核（Plan 阶段完成）
- JSON 中的 `graph`、`contents`、`verify` 已填写完整
- 所有 `state.nodes` 状态为 `not_started`（或部分已完成，断点续做）

## 上下文恢复

新对话开始时，执行以下步骤恢复项目状态：

```
1. 读取算法地图 JSON
2. 扫描 state.nodes，分类：
   - verified：已完成的节点（绿色）
   - in_progress：discussing / theory_ok / implemented（正在做）
   - not_started：待做
3. 找到当前断点：
   - 有 in_progress 节点 → 从该节点继续
   - 全部 not_started → 从拓扑排序第一个 process 节点开始
   - 全部 verified → Build 阶段完成
4. 向用户汇报：已完成 X/Y 节点，下一个是 [节点名]
```

上下文恢复应在 **10 秒内完成**——这是算法地图相比自然语言 plan 的核心优势。

## 节点选择：拓扑排序

按图的依赖关系确定执行顺序：

```
1. 从 graph.edges 构建有向图
2. 拓扑排序所有 process 节点（跳过 terminal/decision/auxiliary）
3. 从中找到【前驱全部 verified】的下一个可执行节点
4. 如果有多个可执行节点 → 按 id 编号顺序选最小的
```

**关键规则**：
- 只有 `process` 节点需要逐步实现，`decision` 和 `auxiliary` 的逻辑嵌在主流程代码中
- 前驱节点指的是图中通过 `edges` 直接连接的上游 `process` 节点（跳过中间的 decision/auxiliary）
- 不能跳过未 verified 的前驱节点

## 单节点执行循环

每个 `process` 节点的完整执行流程：

### Phase A：理解（5 分钟）

```
1. 读 contents[node_id].overview
   → 理解这步做什么、输入输出、数学模型
2. 读 contents[node_id].how
   → 理解实现思路、核心逻辑、设计决策
3. 读 contents[node_id].verify
   → 理解前置条件、核心验证、后置条件
4. 读 contents[node_id].refs
   → 查看参考资料（如有）
5. 检查上游节点的 post 条件
   → 确认本节点的 pre 条件都能被覆盖
```

**不要急着写代码。** 先向用户确认理解是否正确（一句话概括即可）。

### Phase B：实现 + Checkpoint

```
1. 创建源码文件（按 code.files 中的路径）
2. 实现核心逻辑
3. 确保代码与 overview/how 中描述的接口一致
4. 保存 checkpoint：将本节点的输出数据写入 _checkpoints/<node_id>.json
```

**Checkpoint 机制**：

每个节点实现完成后，将其输出（即 post 条件对应的实际数据）序列化保存：

```
_checkpoints/
├── 01_initialize.json    ← {dist: {...}, pq: [...], visited: []}
├── 02_extract_min.json   ← {node: "B", distance: 1, visited: ["A","B"]}
├── 03_relax.json         ← {dist_after: {...}, pq_after: [...]}
└── ...
```

Checkpoint 的作用：
- 下游节点的输入数据来自上游 checkpoint（接口数据可追溯）
- Auditor 使用 checkpoint 数据独立验证（Builder 无法篡改上游数据）
- 调试时可以从任意 checkpoint 恢复，不必从头跑

**实现原则**：
- 一个节点一次提交，不要跨节点混合实现
- 接口（函数签名、输入输出格式）必须与 verify 中的 check 描述兼容
- 遇到 how 中未说明的细节，先问用户，不要擅自决定

### Phase C：独立审查（Audit）

Builder 完成实现并保存 checkpoint 后，标记状态为 `implemented`，然后启动独立的 **Audit 子 Agent** 进行审查。

**核心原则：写代码的和审查代码的不能是同一个 Agent。**

Builder 通过 CC 的 Task 工具启动 Audit 子 Agent，传入以下信息：

```
Audit 子 Agent 的输入：
  1. 当前节点的 verify 字段（pre/core/post 完整内容）
  2. 上游节点的 checkpoint 数据路径
  3. 当前节点的源码文件路径
  4. 当前节点的 checkpoint 数据路径
  5. 上下游节点的 verify.post 和 verify.pre（用于链式信任检查）
```

Audit 子 Agent 按以下三层顺序执行审查：

#### 第一层：审指标

```
审查 verify 字段本身的质量：
  1. pre 条件是否被上游节点的 post 条件完整覆盖？
     → 逐条对比：上游 post 列表 vs 本节点 pre 列表
     → 发现缺口 → 批注："节点 X 的 post 未覆盖本节点 pre 第 N 条"
  2. core 验证是否直击本质？
     → 是否抓住了"这步对不对"的数学/逻辑判据？
     → 能否区分正确实现和错误实现？（"输出非空"这种永远通过的不算）
     → 不求数量多，但每条都必须有鉴别力
  3. post 条件是否足够支撑下游？
     → 检查下游节点的 pre，本节点 post 能否保证
  4. 验证描述是否具体可执行？
     → "结果正确" 太模糊，应有具体的 check 表达式
```

如果指标有问题：批注打回，Builder 补充 verify 后重新提交。
如果指标没问题：进入第二层。

#### 第二层：审数据

```
用 checkpoint 数据执行 verify 测试：
  1. 读取上游 checkpoint 作为输入
  2. 按 verify.pre 逐条断言（输入数据满足前置条件）
  3. 按 verify.core 逐条执行测试
     → cmd 已填写 → 直接执行
     → cmd 为空 → 按 method 描述编写测试并执行
  4. 读取本节点 checkpoint 作为输出
  5. 按 verify.post 逐条断言（输出数据满足后置条件）
  6. 记录每条验证的 true/false 到 verify_results
```

验证等级优先级：
- `L1`（单元级）必须全部通过
- `L2`（集成级）需要上下游代码就绪后执行
- `L3`（端到端）推迟到所有节点完成后统一执行

#### 第三层：审代码

```
阅读当前节点的源码（通常几十行）：
  1. 实现逻辑是否与 overview/how 描述一致？
  2. 有没有 hardcode 特定测试用例的值？
  3. 有没有绕过验证的特殊处理？
  4. 有没有只在特定输入下正确的逻辑？
  5. 代码风格和接口是否与上下游一致？
```

#### 审查结果

```
三层全部通过 → Auditor 返回 "PASS"，Builder 标记 verified
任一层不通过 → Auditor 返回 "FAIL" + 具体批注
  → 指标问题 → Builder 补充 verify 字段
  → 数据问题 → Builder 修代码
  → 代码问题 → Builder 重构
  → 修完后重新提交 Audit
```

#### Audit 子 Agent Prompt 模板

启动 Audit 子 Agent 时使用以下 prompt 结构：

```
你是算法地图的独立审查员（Auditor）。你的职责是审查 Builder 提交的节点实现。

## 审查对象
- 节点：{node_id} — {node_title}
- 源码：{code_file_paths}
- Checkpoint：{checkpoint_path}
- 上游 Checkpoint：{upstream_checkpoint_path}

## 验证标准
{verify 字段完整内容，含 pre/core/post}

## 上游节点的 post 条件
{upstream_post 内容}

## 下游节点的 pre 条件
{downstream_pre 内容}

## 你的任务（按顺序）

### 1. 审指标
检查 verify 标准本身是否完整、链式信任是否对接、边界情况是否覆盖。
有问题就列出，返回 FAIL。

### 2. 审数据
读取 checkpoint 数据，按 verify 标准逐条执行测试。
编写测试代码并运行，报告每条的 pass/fail。

### 3. 审代码
阅读源码，检查有无 hardcode、投机取巧、逻辑漏洞。

## 输出格式
返回 JSON：
{
  "result": "PASS" 或 "FAIL",
  "criteria_review": "指标审查意见（ok 或具体问题）",
  "verify_results": { "pre": [...], "core": [...], "post": [...] },
  "code_review": "代码审查意见（ok 或具体问题）",
  "annotations": ["需要打回的批注列表，为空则无"]
}
```

### Phase D：调试（如需要）

当 Audit 返回 FAIL 时：

```
1. 读 Audit 返回的具体批注
2. 分类处理：
   - 指标问题 → 补充 verify 字段（pre/core/post）
   - 数据问题 → 定位失败的测试，修改实现代码
   - 代码问题 → 按批注重构代码
3. 重新保存 checkpoint
4. 重新提交 Audit（再次启动子 Agent）
5. 最多 3 轮。如果仍 FAIL：
   - 记录问题到 pitfalls 字段
   - 告知用户，讨论是否调整方案
```

### Phase E：状态更新

Audit 返回 PASS 后，立即更新 JSON：

```json
{
  "state": {
    "nodes": {
      "<node_id>": {
        "status": "verified",
        "verify_results": {
          "pre":  [true, true, true],
          "core": [true, true, true, true],
          "post": [true, true, true]
        }
      }
    }
  }
}
```

同时更新 `contents[node_id]`：
- `code.files`：填入实际创建的源码文件路径
- `code.snippet`：填入核心代码片段
- `pitfalls`：如有踩坑记录，填入

更新 `meta.updated` 为当前日期。

### Phase F：自然断点

**每个节点完成后是天然的对话断点。** 此时：
- JSON 已保存最新状态
- 用户可以刷新浏览器查看进度（状态点变绿）
- 即使对话中断，新对话读 JSON 即可无缝继续
- 向用户汇报：完成 X/Y 节点，下一个是 [节点名]

## 反馈集成

用户可能在 Build 过程中通过渲染器提交批注。

```
1. 检查是否存在 .feedback.md（与地图 JSON 同目录）
2. 如果存在，读取内容
3. 按 [node:id] 和 [Tab] 标记定位到对应节点和维度
4. 处理反馈：
   - 结构性反馈（加/删节点、改边）→ 修改 graph，告知用户
   - 内容性反馈（改描述、补验证）→ 修改 contents
   - 实现性反馈（改代码）→ 修改代码并重跑验证
5. 修改完成后删除或清空 .feedback.md
```

## 状态流转规则

每个 process 节点的状态严格按以下顺序流转：

```
not_started → discussing → theory_ok → implemented → verified
```

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| `not_started` | 未开始 | 初始状态 |
| `discussing` | 理解中 | 开始读 overview/how |
| `theory_ok` | 方案确认 | 用户确认理解无误 |
| `implemented` | 已实现 | 代码写完，等待验证 |
| `verified` | 已验证 | pre + core(L1) + post 全部通过 |

**不允许跳过中间状态。** 每次状态变更都写回 JSON。

## L2/L3 集成验证

单节点的 L1 验证在节点内完成。跨节点的 L2/L3 验证在以下时机执行：

```
L2 验证时机：
  - 当一个节点的所有直接上下游都 verified 时
  - 例如：环节 2（求解 RMP）verified 后，跑环节 2 和环节 3 的 L2 集成测试

L3 验证时机：
  - 所有 process 节点 verified 后
  - 跑端到端测试（完整算法流程）
```

## 并行执行（多终端场景）

当多个 CC 终端并行工作时：

```
1. 总管读 JSON，找出所有可并行节点（无依赖关系的 process 节点）
2. 每个终端分配一个节点，按单节点循环执行
3. 终端完成后更新 JSON 状态
4. 总管检查是否有新的可执行节点被解锁
5. 重复直到所有节点 verified
```

**并行锁**：同一时间只有一个终端可以写 JSON。总管协调写入顺序。

## 完成标准

Build 阶段完成的标志：

```
- [ ] 所有 process 节点状态为 verified
- [ ] 所有 L1 验证通过
- [ ] 所有 L2 验证通过（跨节点集成）
- [ ] L3 端到端测试通过
- [ ] 每个节点的 code.files 和 code.snippet 已填充
- [ ] pitfalls 已记录所有踩坑经验
- [ ] meta.updated 已更新
```

## 速查：单节点执行清单

```
□ 读 overview + how + verify + refs      ← Phase A
□ 确认理解，用户同意后开始
□ 实现代码 + 保存 checkpoint              ← Phase B
□ 标记 implemented，启动 Audit 子 Agent   ← Phase C
  □ 审指标（verify 完整性 + 链式信任）
  □ 审数据（checkpoint → pre/core/post）
  □ 审代码（hardcode / 投机取巧检查）
□ Audit PASS → 更新 state: verified       ← Phase E
□ Audit FAIL → 按批注修复 → 重新提交      ← Phase D
□ 更新 code.files + code.snippet
□ 更新 pitfalls（如有）
□ 汇报进度，准备下一个节点                  ← Phase F
```
