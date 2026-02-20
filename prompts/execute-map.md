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

### Phase B：实现

```
1. 创建源码文件（按 code.files 中的路径）
2. 实现核心逻辑
3. 确保代码与 overview/how 中描述的接口一致
```

**实现原则**：
- 一个节点一次提交，不要跨节点混合实现
- 接口（函数签名、输入输出格式）必须与 verify 中的 check 描述兼容
- 遇到 how 中未说明的细节，先问用户，不要擅自决定

### Phase C：验证

按 **pre → core → post** 顺序执行验证。

#### 1. 前置条件验证（pre）

```
对 verify.pre 中每一项：
  - 如果上游节点已 verified → pre 条件应自动满足
  - 写一个简单的断言测试确认
  - 记录结果到 state.nodes[id].verify_results.pre
```

#### 2. 核心验证（core）

```
对 verify.core 中每一项：
  - 读 method 字段，理解验证策略
  - 如果 cmd 已填写 → 直接执行该命令
  - 如果 cmd 为空 → 按 method 编写测试，填入 cmd 字段
  - 执行测试
  - 全部通过 → 记录 true
  - 失败 → 进入调试循环（见下文）
```

**验证等级优先级**：
- `L1`（单元级）必须全部通过才能继续
- `L2`（集成级）需要上下游代码就绪后执行
- `L3`（端到端）可以推迟到所有节点完成后统一执行

#### 3. 后置条件验证（post）

```
对 verify.post 中每一项：
  - 按 check 字段编写断言
  - 验证通过 → 下游节点的 pre 条件有保障
```

### Phase D：调试（如需要）

当核心验证失败时：

```
1. 读错误信息，定位失败原因
2. 检查是实现 bug 还是验证标准写错了
   - 实现 bug → 修代码 → 重跑测试
   - 验证标准有误 → 告知用户，协商修改 verify 字段
3. 最多调试 3 轮。如果仍失败：
   - 记录问题到 pitfalls 字段
   - 告知用户，讨论是否调整方案
4. 不要悄悄降低验证标准来通过测试
```

### Phase E：状态更新

验证全部通过后，立即更新 JSON：

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
□ 实现代码                                ← Phase B
□ 跑 pre 验证                             ← Phase C
□ 跑 core 验证（L1 必过）
□ 跑 post 验证
□ 更新 state（status: verified）           ← Phase E
□ 更新 code.files + code.snippet
□ 更新 pitfalls（如有）
□ 汇报进度，准备下一个节点                  ← Phase F
```
