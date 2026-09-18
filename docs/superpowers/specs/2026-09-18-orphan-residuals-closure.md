> **Date:** 2026-09-18 | **Status:** Design | **Severity:** 🟠 P1（最高面 F513 P1）| **方法:** 孤儿残留收口（spec #40 收官 pass 登记，仅登记不实施——先例：2026-09-11 维护 pass 登记 #66）
> **系列:** 2026-08-15 审计修复 · 收官 pass 登记 | **依赖:** 无（三面证据已由收官 pass 勘定）| **范围:** legacy CLI 写审计快照根、curated 层零消费者、离线可执行模式 | **核心洞察:** 三个被已闭 spec 循环移交（C30↔C37）、被无目标尾注悬置（#44 T1108）、或被 Rejected spec 遗留（C32→#46 的 F513 残留）的面——每面都有实证行号，但无人认领

# 孤儿残留收口（orphan-residuals-closure）

## 元信息

- 登记来源：spec #40 收官 pass（2026-09-18）价值门驳斥复核 + 四轮设计审查裁定
- ledger 关联行：08-15 F519（纠偏后 re-homed）、08-14 F513（re-homed，状态 specced）、08-15 F311（curated 面 re-homed）、08-15 T1108（移交目标钉本 spec）

## 1. F519/F513 · legacy CLI 路由写审计快照根错位

- **证据**：`src/shenbi/dispatcher/executor.py:31-32`（`PROJECT_DIR = REPO_ROOT`）、`:309`/`:334`（`snapshot_tree(PROJECT_DIR, watch)`）；legacy 路由仍被 `dispatcher/cli.py:11` 引用；`tests/unit/dispatcher/test_executor_audit.py:18`/`:42` 以 `monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)` 掩蔽该根错位。生产面（`dispatch_helper` Tier B wrapper）已正确以派发项目目录为根——残留面限 legacy 回退路由
- **沿革**：08-14 F513（P1）→ C32 边界注记指向 spec #46 收口 → #46 Rejected → 08-15 F519 复查仍开 → 2026-09-07 #48 价值门误注「已修」（仅验生产面）→ 收官 pass 纠偏并 re-home 本 spec
- **修复方向**：legacy 路由快照根对齐派发项目目录（与生产面同语义）；揭除测试掩蔽
- **验收（可执行）**：`uv run pytest tests/unit/dispatcher/ -q` 全绿；新增/改写断言不 monkeypatch `PROJECT_DIR` 也能以项目目录为快照根；`grep -n "PROJECT_DIR = REPO_ROOT" src/shenbi/dispatcher/executor.py` 零命中（或附裁决注记的等价形态）

## 2. F311 · curated 层零消费者（wire-or-remove 裁决）

- **证据**：`src/shenbi/pipeline/chapter_loop.py:1562`、`src/shenbi/pipeline/cli.py:1078-1080` 构造 `context/chapter-N-curated.md` 路径——全仓 grep 零读方（仅写方 + 测试）。错位与落盘面已随 C30 修复（PR #120 链 + Gap 2）
- **沿革**：C30 spec #44 尾注「curated 零消费者面若 C37 R0 裁决删除则随 C37 关闭」↔ C37 归档「F311 面…已在 C30 处置」——循环移交，从未裁决
- **修复方向**：二选一裁决——(a) wire：context assembly 消费 curated 层（P 分层编排生效）；(b) remove：连写方一并清理（死输出面消除）。裁决落本 spec 修订，禁止无裁决收尾
- **验收（可执行）**：裁决记录落 spec 修订头；(a) 路径 `grep -rn "curated" src/shenbi/pipeline/context_assemble.py` 出现读方 + 对应 T1 测试；或 (b) 路径 `grep -rn "chapter-.*-curated" src/shenbi/` 零命中 + 清理回归测试

## 3. T1108 · 离线可执行模式（设计裁决）

- **证据**：ledger 行（08-15 T1108）——「pipeline 无离线可执行模式，运行时主路径无法免计费审计（internal 硬拒绝无 LLM、replay 是签名校验非派发 stub）」；spec #44 尾注移交「独立设计裁决」未指名目标
- **修复方向**：三选一裁决——做（离线 stub 派发面 + T1 测试）/ 不做（记录理由关闭）/ DEFER（依赖条件成文）
- **验收（可执行）**：裁决记录落 spec 修订头；若「做」：离线 stub 的 T1 测试绿 + `just check` 绿；若「不做/DEFER」：ledger 行按裁决关闭/注记

## 边界

- 本 spec 不含：T1608 save_state 增量化（#44 Done 终态全量写，增量收益未裁决——产品裁决后另立，记 spec #40 §9 deviation）、C28 token 架构（29% 冗余，同前）
- 实施由后续独立 SDD run 承担（/sdd-next 队列）
