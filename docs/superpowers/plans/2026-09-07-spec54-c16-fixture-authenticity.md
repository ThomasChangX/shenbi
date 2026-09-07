# C16 fixture 真实性与 G0.9 执法（spec #54）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 G0.9 从"声称 fixtures exclusively real"变成存在性闭包 + provenance 三态执法（WARN→FAIL 分波滚出），清理 fixture 库造假面（复制体/角色滥用/伪造快照/虚构锚点），bug-hunt 证据内容级闭合。

**Architecture:** 执法集中在 `src/shenbi/gates/g0_purity.py` 新增三个纯函数检查（G0.17/G0.18/G0.19）+ `src/shenbi/gates/g0.py` G0.11 缺侧显式报告；滚出状态用 `g0_purity.py` 内常量 `ENFORCEMENT_WAVES`（P0/P1/P2 → "fail" | "warn"）；基线由 `tools/gen_provenance_baseline.py` 产出（gate 只读）；bug-hunt 证据闭包独立 `tools/check_bug_hunt_evidence.py`（进 pre-commit）。fixture 清理与锚点重建全部以 `novel-output/xinghuo-ranqiong/` 为唯一真实样本源。

**Tech Stack:** Python 3.11+, pathlib, re, hashlib, pytest（无新依赖；禁 LLM dispatch）。

## Global Constraints

- gate 检查器纯函数、幂等、无副作用（AGENTS.md；基线写盘只在 tools/ 生成器）
- provenance 三态字面量 `real-output | upstream-copy | synthetic-sample` 唯一定义于 `g0_purity.py` 常量 `PROVENANCE_STATES`
- 载体：`.md` 用 frontmatter `provenance:`/`source:`；非 md 用同目录 `<name>.provenance.json`（`{"provenance": "...", "source": "..."}`）；载体文件自身豁免扫描
- 白名单首版仅 `report-example.txt`（豁免"真实产物角色"不豁免标注）
- FAIL 执法面 = pytest 断言 `GateStatus.FAIL`（gates CLI 退出码 legacy 恒 0）
- fixture 删除/替换独立 commit；scenario 文本改动逐条可 grep 复核
- 验证一律 `uv run`/`just`（与 CI 同构）

**复杂度分类：全部 4 个 task 均为 infra（gates/ + 契约面 + 全库 fixture 面）→ 协调者亲自实现。**

---

### Task 1: G0.17/G0.18/G0.19 执法 + G0.11 缺侧报告 + 基线生成器（T0+T1）

**Files:**
- Modify: `src/shenbi/gates/g0_purity.py`（新增 ~180 行：常量 + 3 检查函数）
- Modify: `src/shenbi/gates/g0.py:510-527`（G0.11 缺侧 continue → 显式 WARN 清单）
- Create: `tools/gen_provenance_baseline.py`
- Test: `tests/unit/gates/test_g0_purity_enforcement.py`（新建）
- Test: `tests/unit/gates/test_g0.py`（G0.11 缺侧用例追加）

**Interfaces (Produces, 供后续 task/CI 依赖):**
```python
# g0_purity.py
PROVENANCE_STATES: frozenset[str]  # {"real-output","upstream-copy","synthetic-sample"}
PROVENANCE_WHITELIST: frozenset[str]  # {"tests/fixtures/report-example.txt"}
ENFORCEMENT_WAVES: dict[str, str]  # {"P0":"warn","P1":"warn","P2":"warn"} 初始全 warn
def check_scenario_reference_closure(t1_skill_dir: Path, project_root: Path) -> list[dict[str, Any]]
    # id "G0.17": 三 test_type 场景引用的 tests/fixtures/<p> 全部存在；缺失 → wave["P0"]=="fail" ? FAIL : WARN
    # 扫描目标含 `_template/`（F751 正是模板场景的缺陷——`_` 前缀跳过惯例在本组新检查中不适用；仅载体文件豁免）
def check_fixture_provenance(t1_skill_dir: Path, fixtures_dir: Path) -> list[dict[str, Any]]
    # id "G0.18": 被消费 fixture 的 provenance 载体存在且三态合法；违规 → wave["P1"] 判定
def check_variant_bypass(t1_skill_dir: Path, fixtures_dir: Path) -> list[dict[str, Any]]
    # id "G0.19": fixtures 内未被场景引用的「变体旁路」文件不豁免 provenance；相似判据定死：与任一被引用文件 stem 共享前 2 个 `-` 分段（如 foo-example 与 foo-example-variant）；违规 → wave["P2"] 判定
def load_provenance(fixture_path: Path) -> str | None  # frontmatter 或 sidecar 解析（非法 YAML → 返回 None 并计数）
```

- [ ] **Step 1: 写失败测试**（红灯三类 + WARN 模式 + 升级守卫；测试名钉死：`test_closure_zero_violations`、`test_promotion_guard`、`test_negative_missing_path`、`test_negative_no_provenance`、`test_negative_fake_generated_by`、`test_carrier_self_exempt`、`test_variant_bypass_detects_unreferenced`）
  - `test_g0_purity_enforcement.py`：tmp_path 构造 (a) scenario 引用不存在 fixture → `check_scenario_reference_closure` 返回 `s==GateStatus.WARN`（P0 波 warn 态）；把 `ENFORCEMENT_WAVES["P0"]="fail"`（monkeypatch）→ FAIL。(b) 消费中 fixture 无 provenance → WARN；非法三态（`provenance: hand-made note`）→ 计入违规。(c) 变体文件 `foo-example-variant.md` 无引用无 provenance → G0.19 WARN。(d) 载体豁免：`x.provenance.json` 不进扫描目标。(e) 升级守卫：`wave=="fail"` 且现场计数>0 时结果为 FAIL；计数==0 时 PASS——同函数内由计数驱动，无静态基线读取。
  - `test_g0.py` 追加：MIRROR_MAP 侧缺文件（tmp monkeypatch PROJECT）→ G0.11 输出含 `missing:` 的 WARN 而非静默 continue。
- [ ] **Step 2: 跑测试确认失败** `uv run pytest tests/unit/gates/test_g0_purity_enforcement.py -x -q` → FAIL (ImportError/AttributeError)
- [ ] **Step 3: 实现 g0_purity.py 三检查 + gate_G0 接线**（G0.17/18/19 追加进 gate_G0 的 checks；G0.11 改造：缺侧收集 `missing_sides` 列表 → 非空输出 WARN `f"missing mirror side: {detail}"`，双侧存在才比哈希）
- [ ] **Step 4: 跑测试通过** `uv run pytest tests/unit/gates/ -q` 全绿
- [ ] **Step 5: 基线生成器** `tools/gen_provenance_baseline.py`：CLI 无参，全量跑三检查的计数逻辑，写 `tests/fixtures/provenance-baseline.json`（`{"generated_at": iso, "G0.17": n, "G0.18": n, "G0.19": n, "violations": {check: [file,...]}}`）；gate 侧只读该文件做 delta 报告（new-since-baseline 计数入 note；**文件缺失容忍**：fresh clone 无基线 → note "no baseline"，绝不 FAIL/报错）。生成并提交首版基线。
- [ ] **Step 6: 全量回归 + commit** `uv run just check`；commit `feat: G0.17-19 fixture provenance enforcement + G0.11 missing-side report + baseline generator (spec54 T0/T1)`

### Task 2: bug-hunt 证据闭包 + 文法迁移（T1.2 + T2.9b）

**Files:**
- Create: `tools/check_bug_hunt_evidence.py`
- Modify: `.pre-commit-config.yaml`（新增 hook，WARN 阶段 `--warn-only`）
- Modify: `tests/tiers/t1-skill/*/bug-hunt/{input/scenario.md,expected/expected-output.md}`（含 `_template`；文法迁移 + 证据修复，清单执行时 `grep -rl expected-output tests/tiers` 现推导）
- Test: `tests/unit/tools/test_check_bug_hunt_evidence.py`

**Interfaces:**
```python
# tools/check_bug_hunt_evidence.py
# 证据行文法: 行含 `tests/fixtures/<file>` 且含 `L<digits>` 或 8+ 字符锚文本
def parse_evidence_lines(text: str) -> list[tuple[str, str | None, str | None]]  # (fixture_rel, lineno, anchor)
def verify_scenario(skill_bug_hunt_dir: Path, fixtures_root: Path) -> list[str]  # 违规描述
# CLI: python tools/check_bug_hunt_evidence.py [--warn-only]; 退出码 0/1；pre-commit 阶段用 --warn-only
# 扫描目标含 `_template/`（F751 主战场）；遍历 bug-hunt 目录树不跳过 `_` 前缀
```

- [ ] **Step 1: 失败测试**：tmp_path 构造 scenario 引用 fixture + expected-output.md 三行——命中 / 行号越界 / 锚文本不存在 → verify_scenario 返回 2 违规
- [ ] **Step 2: 确认失败 → 实现 → 通过**（同 TDD 循环）
- [ ] **Step 3: 全库现状扫描定迁移清单**：`uv run python tools/check_bug_hunt_evidence.py` 输出违规全集（即 F751/F752/F754/T806 实际面），记入 progress.md 验收证据
- [ ] **Step 4: 迁移存量 expected-output.md**：违规条目逐条改写——scenario 改指真实存在且含植入缺陷的 fixture（优先 novel-output/xinghuo-ranqiong 副本入库）或缺陷表改述为 fixture 真实内容；location-builder 自引用行（F752）改为两个互异 fixture
- [ ] **Step 5: 复扫 0 违规 + commit**：`uv run python tools/check_bug_hunt_evidence.py` 输出 `0 violations`；commit `fix: bug-hunt evidence content-level closure + expected-output grammar migration (spec54 F751/F752/F754/T806)`

### Task 3: fixture 库治理（T2 其余 + F790）

**Files:**
- Modify/Create/Delete: `tests/fixtures/**`（draft 族删除、三胞胎替换、F753 改指、F779/F780 快照重建、MIRROR_MAP、F785-787、F763、F790）
- Modify: `src/shenbi/gates/g0.py`（MIRROR_MAP 增补）、`tools/check_fixture_mirror.py:12`（过期注释）
- Modify: `tests/tiers/t1-skill/shenbi-snapshot-manage/**`（"11 truth files" → 动态表述）、受影响测试断言

- [ ] **Step 1: 现推导三清单**（全库 grep，输出贴 progress.md）：draft 族逐文件引用扫描（chapter-7-draft 有 test_quote_pair_count.py:113 消费者、chapter-2-draft 有 2 消费者——有消费者者改指真实副本，零引用者删）；example 三胞胎消费者（≥7 处含尺寸敏感 test_sampling_disclosure.py）；report-example 误用场景（≥31 引用，逐场景判角色）
- [ ] **Step 2: 三胞胎替换**：`chapter-{7,8,9}-example.md` ← `novel-output/xinghuo-ranqiong/chapters/chapter-{7,8,9}.md` 逐字节副本 + frontmatter `provenance: real-output`/`source: novel-output/...`；尺寸敏感断言按实尺寸重推导；`tests/baselines/gate-outputs/` 走 `uv run bash tests/regenerate-baselines.sh` **全量重生成**（Task 1 gate_G0 输出已变，G0.json 同步陈旧，全量重生成属预期 churn）
- [ ] **Step 3: draft 族处置**：零引用者删除（独立 commit）；有消费者者——测试改指三胞胎真实副本或保留 + provenance 标注
- [ ] **Step 4: F753 误用场景改指**：违法场景改指各技能真实产物 fixture（从 novel-output 复制 + provenance）；report-example.txt 加 sidecar `upstream-copy` 标注；import 源引用保留
- [ ] **Step 5: 快照族**：chapter-025 manifest 用真实快照 checksums 重建（provenance 标注）；F780 四对镜像登记 MIRROR_MAP；check_fixture_mirror.py:12 注释修正；pre-commit fixture-mirror hook 已存在即 CI 接线完成（F1012 协同面在本仓已就绪则记 deviation 不重复接线）
- [ ] **Step 6: 词表/配置/常数**：stop_words_zh.txt 零消费者 → 删除（F785）；sensitive_words.txt 与 scenario 声称对齐扩容（F786，消费者 g6.py:495）；genre-config-example.json 从 novel-output/xinghuo-ranqiong/genre-config.json 重导（F787）；"11 truth files" → 从 docs/framework/truth-files.yaml 计数动态表述（F763，涉及 snapshot-manage 6 文件）；T807/T808 随 Step 2/4 对账修正；F790 qidian fixture 降级 synthetic-sample 或删
- [ ] **Step 7: 每类独立 commit + 全量回归**：`uv run just check` 全绿、skip 数不增（对照 main 基线 522 skipped）；**每类内容替换 commit 内复跑 `uv run python tools/check_bug_hunt_evidence.py` 必须 `0 violations`**（Task 2 闭包不被本 task 打破——破坏即同 commit 修复）；provenance 违规计数对照 Task 1 基线递减（贴 progress.md）

### Task 4: calibration 锚点重建 + G0.14 重锁 + T4（F947/F1154）

**Files:**
- Modify: `tests/fixtures/calibration/**`（28 文件：27 锚点 + README）
- Modify: `tests/tiers/deps.json`（`_calibration_hashes.combined` 重锁，走 `tests/lock-tool-hashes.sh`）
- Modify: `docs/superpowers/specs/*.md`（F947 验收离线化改写，pattern 清单见 spec AC8）
- Modify: `docs/superpowers/single-model-sdd-prompt.md`（writing-plans 约定：plan 阶段不改写即 BLOCKED——加一句）

- [ ] **Step 1: 锚点逐个处置**：excerpt 能在 novel-output/xinghuo-ranqiong 章节中溯源的 → 替换为真实 excerpt + `source:` 字段（file+line）；不可溯源 → `provenance: synthetic-sample` 降级标注；schema（README）加 source 字段定义（T805）；引文行号虚构（T806）随替换消灭
- [ ] **Step 2: lock 脚本规范化对齐 + G0.14 重锁**：先给 `tests/lock-tool-hashes.sh` calibration 循环补 CRLF→LF 归一（与 g0.py:111 `read_bytes().replace(b"\r\n", b"\n")` 逐字一致——当前脚本哈希原始字节，仅因现存文件皆 LF 巧合通过，重写 28 文件后任何 CRLF 混入即锁出 gate 必拒哈希）；`uv run bash tests/lock-tool-hashes.sh` → deps.json 新 combined 哈希；`uv run just gate G0 tests/fixtures/canary-3-chapter-seed.md` 的 G0.14 分支 PASS
- [ ] **Step 3: F947 扫描改写**：`git grep -nE "真实 LLM dispatch|真实 dispatch|现场 dispatch|live dispatch|real dispatch" docs/superpowers/specs/` 命中集逐条改写为 fixtures 回放/结构断言形式（不含本 spec 自身对禁令的引用）；single-model-sdd-prompt.md 加 BLOCKED 规则一句
- [ ] **Step 4: F1154 裁决**：#57 (C19) 未冻结 → 不实施，PR 描述显式记 BLOCKED（宁留显式缺失）
- [ ] **Step 5: 终态验收 + commit**：AC1-AC8 逐条跑（见验收覆盖表）贴 progress.md；commit `fix: calibration anchor rebuild + G0.14 relock + spec acceptance offline-ization (spec54 T3/T4)`

---

## 验收覆盖表（spec AC → task → 验证命令）

| AC | Task | 命令 |
|---|---|---|
| 1 | T1 | `uv run pytest tests/unit/gates/test_g0_purity_enforcement.py -q`（tmp_path 负样本三类 FAIL 用例）+ `uv run just gate G0 tests/fixtures/canary-3-chapter-seed.md` PASS |
| 2 | T2 | `uv run python tools/check_bug_hunt_evidence.py` → `0 violations` |
| 3 | T1+T3 | `uv run python tools/gen_provenance_baseline.py`（扫真实库，验收时三计数须为 0）+ `uv run pytest -q tests/unit/gates/test_g0_purity_enforcement.py::test_closure_zero_violations`（回归守卫）+ hash 去重脚本（`uv run python -c "import hashlib,pathlib,collections;..."` 输出 0 组，MIRROR_MAP 显式镜像除外） |
| 4 | T1 | `test_g0_purity_enforcement.py::test_promotion_guard`（warn 态 + 计数>0 → 非 FAIL） |
| 5 | T4 | `uv run just gate G0 ...` G0.14 PASS（新哈希）+ `! grep -L -e "source:" -e "provenance: synthetic-sample" $(find tests/fixtures/calibration/arc-payoff tests/fixtures/calibration/resonance -name '*.md')` 输出为空（27 锚点每条带 source 或显式降级标注） |
| 6 | T3 | `uv run just check` 全绿且 skip 数不增（基线采集：执行前在 main 跑 `uv run pytest -q -n auto -m "not last" 2>&1 | tail -3` 记录 skipped 数，对照 522）+ 被删 fixture `git grep <name>` 0 残留 |
| 7 | — | #18 R1-R4 对照表写入 PR 描述（协调者执行） |
| 8 | T4 | F947 grep 命中集（除禁令引用）= 0；F1154 BLOCKED 注记 |

**test_kind:** Task 1 = tdd_red_green；Task 2 = tdd_red_green + 迁移面 regression_guard；Task 3 = regression_guard（行为保持的库治理）；Task 4 = regression_guard + 红灯重锁验证。评分场景：无（纯机械面，无 LLM 产物评分，G3.4 不适用）。

## Self-Review

- 覆盖：spec T0→Task1、T1→Task1/2、T2.4/4b→Task3 S1-3、T2.5→T3 S4、T2.6→T3 S5、T2.7→T3 S1/S3、T2.8→T3 S6、T2.9→T3 S6、T2.9b→Task2、T3→Task4、T4.12→Task4 S3、T4.13→Task4 S4（BLOCKED）、F790→T3 S6、F750 deferred（spec 记载）。AC1-8 全映射。✓
- 占位符：无 TBD；"清单现推导"是 spec 强制的执行时推导非占位。✓
- 类型一致：PROVENANCE_STATES/ENFORCEMENT_WAVES/load_provenance 在 Task1 定义、Task3/4 消费。✓
