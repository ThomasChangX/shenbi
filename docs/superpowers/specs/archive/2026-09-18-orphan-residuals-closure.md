> **Date:** 2026-09-18 | **Status:** Done (PR #234 · 2026-09-18 · 曾为 Design (Revised 2026-09-18)：三面裁决——面 1 修复方案操作化、面 2 裁决 remove、面 3 裁决不做) | **Severity:** 🟠 P1（最高面 F513 P1）| **方法:** 孤儿残留收口（spec #40 收官 pass 登记；本 pass 实施并关闭）
> **系列:** 2026-08-15 审计修复 · 收官 pass 登记 | **依赖:** 无（三面证据已由收官 pass 勘定）| **范围:** legacy CLI 写审计快照根、curated 层零消费者、离线可执行模式 | **核心洞察:** 三个被已闭 spec 循环移交（C30↔C37）、被无目标尾注悬置（#44 T1108）、或被 Rejected spec 遗留（C32→#46 的 F513 残留）的面——每面都有实证行号，但无人认领

# 孤儿残留收口（orphan-residuals-closure）

## 元信息

- 登记来源：spec #40 收官 pass（2026-09-18）价值门驳斥复核 + 四轮设计审查裁定
- ledger 关联行：08-15 F519（纠偏后 re-homed）、08-14 F513（re-homed，状态 specced）、08-15 F311（curated 面 re-homed）、08-15 T1108（移交目标钉本 spec）
- 修订沿革：2026-09-18 阶段 3 设计审查（1C/4I/3M）全部实锤后修订——C1 wire 选项架构倒置（assemble→curate 环）+ 验收 grep 空转、I2 第三掩蔽点、I3 run_g2 传参未裁决、I4 快照根未操作化、I5 remove 范围不全；轮 2（0C/3I/6M）再折三处单行残留（dispatch_helper 孪生 docstring、chapter_loop「replaced by curation」注释/事件、pyproject BLE001 豁免）及 M 级清理项；轮 3（0C/1I/3M）折入三处裸 curation 措辞（cli.py:1042、chapter_loop:162/:282）并换单一权威验收判据 `grep -rn "curation" src/` 归零

## 1. F519/F513 · legacy CLI 路由写审计快照根错位

- **证据**：`src/shenbi/dispatcher/executor.py:31-32`（`PROJECT_DIR = REPO_ROOT`）、`:309`/`:334`（`snapshot_tree(PROJECT_DIR, watch)`）；legacy 路由仍被 `src/shenbi/dispatcher/cli.py:11` 引用；掩蔽测试**三处**：`tests/unit/dispatcher/test_executor_audit.py:18`/`:42` 与 `tests/unit/audit/test_write_audit_drift_attribution.py:65`（以 `monkeypatch.setattr(ex, "PROJECT_DIR", …)` 掩蔽根错位；第三处 fixture 布局还把被观察文件放在 `root/truth/` 而派发 `round_dir=tmp_path/"round"`——两树分离）。生产面（`dispatch_helper._with_write_audit` Tier B wrapper）已正确以派发项目目录为根——残留面限 legacy 回退路由
- **沿革**：08-14 F513（P1）→ C32 边界注记指向 spec #46 收口 → #46 Rejected → 08-15 F519 复查仍开 → 2026-09-07 #48 价值门误注「已修」（仅验生产面）→ 收官 pass 纠偏并 re-home 本 spec
- **可达性**（价值门升级发现）：legacy 路由非死代码——`dispatch_helper.py:2883` 以 `["uv","run","shenbi-dispatch",…]` 为 pipeline **Tier-3 回退路由**（`SHENBI_LLM_API_KEY` 缺席且无 IDE CLI 时触发；`rd = round_dir or project_dir` 见 :2868），且 `pyproject.toml:58` console script、`justfile` `just dispatch` 均直达
- **修复方向（操作化定稿）**：
  1. **快照根 = `dispatch_with_write_audit` 的既有 `round_dir` 参数**（即 CLI argv[3]），不新增 CLI 参数。依据：Tier-3 调用传 `rd = round_dir or project_dir`（dispatch_helper.py:2868），codex 以 `-C str(round_dir)` 执行（modes/codex.py:118-121）→ skill 写盘落点就是 argv[3] 树；快照该树与 F513 原始口径（「快照 round_dir 而非 PROJECT_DIR」）及生产面语义（快照派发写树）双重一致
  2. **`executor.py` 的 `REPO_ROOT`/`PROJECT_DIR` 模块常量整体删除**（`:309`/`:334` 改 `snapshot_tree(round_dir, watch)`；`:287` docstring 同步改写，删除 F519 残留自述）。无等价形态保留——常量保留即掩蔽续存。**孪生残留同步清理**：`dispatch_helper.py:2659-2662` `_with_write_audit` docstring 中「the legacy route snapshots the framework repo root instead, F519, out of scope here」句在修复后失实——改写为两路由同根（round_dir/写树）的现势描述
  3. **`run_g2`（executor.py:148）不再传 `str(PROJECT_DIR)`**：G2 CLI 第 5 参本就可省（gates/cli.py:106 `pd = arg(3, None)`），省略后 `gate_G2(project_dir=None)` → `_is_important_chapter` 恒 False——与现行事实行为精确等价（framework 根下无 `outline/`/`plans/`，该判定今天就是恒 False）。**重要章激活（传 round_dir 使带 outline 的回合生效更高字数下限）是独立产品决策，不随本修复夹带**；如需激活另立裁决
  4. **揭除三处掩蔽**：`test_executor_audit.py` 两处删 `monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)` 行（fixture 已在 `round_dir=tmp_path` 下，语义不变）；`test_write_audit_drift_attribution.py` 删 setattr 并**重排 fixture**——被观察的 `truth/pending_hooks.md` 移到派发 `round_dir` 树下（快照根随修复变为 round_dir）
- **验收（可执行）**：`uv run pytest tests/unit/dispatcher/ tests/unit/audit/ -q` 全绿；`grep -rn "PROJECT_DIR" src/shenbi/dispatcher/executor.py` 零命中（常量整体删除，非改值）；`grep -rn "PROJECT_DIR" tests/unit/dispatcher/ tests/unit/audit/` 零命中（三处掩蔽全揭）；`grep -rn "framework repo root\|F519" src/shenbi/pipeline/dispatch_helper.py` 零命中（孪生 docstring 清理）；新增回归断言：不 monkeypatch 任何模块常量，构造 round_dir 树内越权写 → rc=2 GATE_FAIL（证明真实根生效）；`just check` 全绿（覆盖 run_g2 mock 测 test_dispatcher_executor.py 与 _audit_watch_paths 测 test_trigger_context.py 等面 1 触碰面的全量回归）

## 2. F311 · curated 层零消费者 — 裁决：**remove**

- **证据**：`src/shenbi/pipeline/chapter_loop.py:1562-1566`、`src/shenbi/pipeline/cli.py:1077-1080` 构造 `context/chapter-N-curated.md` 路径——全仓 grep 零读方（仅写方 + 测试）；chapter-drafting SKILL.md 读的是 assembled `chapter-N-context.md`（:14/:44/:54）非 curated 文件。错位与落盘面已随 C30 修复（PR #120 链 + Gap 2）
- **沿革**：C30 spec #44 尾注「curated 零消费者面若 C37 R0 裁决删除则随 C37 关闭」↔ C37 归档「F311 面…已在 C30 处置」——循环移交，从未裁决
- **裁决：remove（option b），2026-09-18 阶段 3 设计审查裁定**。理由（逐项核销 curated 层三个增量）：
  1. **P1-P7 分层无增量**：drafting skill 经 Layer B 字段级契约读已先取章节备忘要点（SKILL.md reads `plans/chapter-N-plan.md` fields 1/3/6/8 派发侧过滤），而 curated 的 P1 注入加载**全量** plan 文本（context_curation.py:144-154）——token 上劣于既有过滤读；assembled 平文件本身已按 rerank 权重排序（context_assemble.py:204-219/:254）
  2. **结局多样性无增量**：`review_checklist.py:470-502` 用同一 `ENDING_PATTERNS` 做审查侧分类——审查面已有，重复
  3. **钩子债简报面向审查非创作**：plan 第 3 节（该兑现的/暂不掀的）才是 drafting 面钩子指令；MH*/H* 简报是 review 面输入
  4. **wire 成本不成比例**：要么为 drafting 加第二个 ~12K 字符上下文读（近似翻倍派发 token），要么换读目标作废 assembled 契约/G1 声明/字段过滤/decisions 配对——本仓头号失败模式即 dead-wire，不为近零增量做契约翻搅
  5. 原设计意图（curated 替代 `shenbi-context-composing` LLM 调用）在 remove 后不回退——该 LLM 调用早已被替代，remove 只消除无人消费的死输出
- **remove 范围（全量清单）**：
  - `chapter_loop.py`：`_run_context_curation`（:1547-1576）+ 调用点（:2988-2989）；**「replaced by curation」注释与日志事件**（:3000-3003——注释改「replaced by deterministic assembly in step 4」语义、事件名 `context_composing_replaced_by_curation` → `context_composing_replaced_by_assembly`；跳过分支本身保留，skill `shenbi-context-composing` 仍在 skills/ 注册、步骤仍需短路标记 done；事件名全仓无其他消费者）；**步骤表与迁移表注释**（:162「merged context-assemble + curation」→ assembly-only 现势、:282「context assembly + curation merged」同改）
  - `pipeline/cli.py`：backfill 块 curated 面（:1069 import、:1077-1080 写入）+ docstring 全节改写（:1042 首行「assembly + curation」与 :1046 curate_context 签名列举一并去 curation 措辞）+ **随之孤立的 `safe_write` import（:1070，ruff F401——`write_context_file` 内部自带 safe_write）**
  - `context_curation.py`：**整模块删除**（`curate_context`/`Section`/reorder/render/ending-diversity/hook-debt helpers）；`ENDING_PATTERNS`（:52-58）**迁往 `review_checklist.py`**（唯一存活消费者，原 :25 import 改本地定义、字典逐字保留——值为调参正则；:470/:474 注释同步；`__all` 可选补列）
  - `truth_readers.py:33` docstring：下游读者清单去 `context_curation`（G6.7 + truth_index + chapter_loop `_check_conditional_resolve`（:1587-1589）**三方**仍在，`read_pending_hooks` 无 dead-wire）
  - `records/writer.py:5` docstring：`read by pipeline/context_curation.py` 引用更新
  - `gates/g4/context_composing.py:77-78` 注释：「context-composing curates the pre-assembled output」措辞随 remove 失实——改为 assembly 现势（checker 本体与 route-based 格式校验保留）
  - `pyproject.toml:150`：`"src/shenbi/pipeline/context_curation.py" = ["BLE001"]` per-file 豁免随模块删除而删行
  - 测试：删 `tests/unit/pipeline/test_context_curation.py`；`test_context_persistence.py` 去 curated 两测（:61-102，保留 assembly 持久化测）；`test_truth_readers.py:114` docstring 三消费者措辞校对（改后仍三方：G6.7/truth_index/chapter_loop）
  - 生成物：`tests/tiers/deps.json` 经 `just generate` 重生成（禁手改；模块删除后先 generate 再跑验收 grep）
  - docs/superpowers/{plans,specs}/archive/ 与 docs/superpowers/audit-runs/ 历史件引用**不动**（append-only 先例；audit-runs 为不可变审计史）
- **验收（可执行）**：`grep -rn "chapter-.*-curated" src/` 零命中；**`grep -rn "curation" src/` 零命中**（单一权威判据——涵盖 curate_context/context_curation 引用与 curation 词面残留：已对 main HEAD 全枚举核验现存 22 处 / 6 文件（truth_readers、chapter_loop、context_curation 模块本体、review_checklist、pipeline/cli、records/writer），全部在清单项内灭亡；范围注记：context_assemble.py「curated context package」与 sync_contracts.py「curated expected_outputs」为通用英语形容词、非本层残留，不在判据内）；`grep -n "curates" src/shenbi/gates/g4/context_composing.py` 零命中（:77 注释改写定向判据）；`grep -n "context_curation" pyproject.toml` 零命中；`grep -n "ENDING_PATTERNS" src/shenbi/pipeline/review_checklist.py` 本地定义 + 消费双命中；`uv run pytest tests/unit/pipeline/ tests/unit/records/ tests/unit/gates/ -q` 全绿；`just generate` 幂等 diff 为空；`just check` 全绿（ruff F401 面机械覆盖）

## 3. T1108 · 离线可执行模式 — 裁决：**不做**

- **证据**：ledger 行（08-15 T1108）——「pipeline 无离线可执行模式，运行时主路径无法免计费审计（internal 硬拒绝无 LLM、replay 是签名校验非派发 stub）」；spec #44 尾注移交「独立设计裁决」未指名目标
- **裁决：不做（记录理由关闭），2026-09-18 阶段 3 设计审查裁定**。理由：
  1. **免计费审计的既有 seam 已覆盖诉求**：(a) 单元/T2 测试在 dispatch 边界 monkeypatch（路由含 legacy 子进程路径由 mock `subprocess.run` 覆盖——tests/unit/pipeline/test_dispatch_helper.py:13/:32）；(b) `trace/replay.py` 签名链完整性；(c) **决定性先例**：`tests/test_run_pipeline_smoke.py:28-50` 以 PATH 上假 `uv` stub 回放罐头 `pipeline resume` 输出，零生产代码改动即得主路径离线冒烟——「无法免计费审计」的前提在该技术面前不成立
  2. **stub 模式是纯测试用途的新生产面**（mode 模块 + detect_mode/dispatch_skill 路由 + env 守卫 + 测试），且带误用风险（env 泄漏 → 合成产物被当真实产物）；与「新增的每个函数/gate/桥必须有生产调用方」的死线纪律冲突
  3. **质量模型不可满足**：T1/T3 评分须真实独立子代理（G3.4），离线 E2E 至多是接线冒烟——PATH-stub 已等价提供
  4. 复活条件（成文）：若未来出现 `pipeline run --dry-run` **产品**功能需求，另立 spec 重裁；在此之前认可的离线技术 = test_run_pipeline_smoke.py 的 PATH-stub 模式
- **验收（可执行）**：08-15 ledger T1108 行按裁决关闭（closed (spec #67 裁决：不做——三既有 seam + PATH-stub 先例 + G3.4 不可满足 + 误用风险；复活条件成文)）；spec 本节即裁决记录

## 边界

- 本 spec 不含：T1608 save_state 增量化（#44 Done 终态全量写，增量收益未裁决——产品裁决后另立，记 spec #40 §9 deviation）、C28 token 架构（29% 冗余，同前）
- ledger 关联四行的终态回写随本 pass 实施完成后进行：F519/F311/T1108 关闭、F513 specced→closed
