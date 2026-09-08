# Spec #57 C19 T4 快照词面定稿 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把快照词面按 #26 路径 3 后的现实定稿——skill 目录布局正名、crash_recovery 紧急平铺登记、manifest.json 改 drift 标记——并完成声明/词表/磁盘三面对账与遗留处置。

**Architecture:** 纯治理改动（yaml 词表 + 测试断言 + 镜像映射 + 磁盘清理 + 缺失报告），零 src/ 新写方、零 SKILL.md 契约变更（snapshot-manage/sequel-writing 的目录布局声明已正确，是 yaml 追上契约）。全部 infra 类（触及 contracts 域），协调者亲自实现。

**Tech Stack:** truth-files.yaml 词表、pytest、just（lint-contracts/generate/check）。

## Global Constraints

- G0.9：`tests/fixtures/` 禁手造 mock；tmp_path 单测自建输入豁免
- 改 yaml 后必须 `just lint-contracts` 绿 + `just generate` 同步；禁手改生成物。生成物 diff 纪律：**首次**改 yaml 概念名/kind 后的生成物 diff（index.json/dependency-dag.json/deps.json 的 D20 条目）属预期——核对仅限 D20 相关后随 task commit；此后重复跑 `just generate` diff 须为空（幂等）。
- pathspec commit：显式列文件，禁 `git add -A`
- SDD 全程禁真实 dispatch（核心原则 8）——F1154 用显式缺失报告而非现场产出
- Conventional commits；无 print；pathlib

---

### Task 1: truth-files.yaml D20 词面定稿 + 消费测试同步 + chapter_loop manifest 词面清理

**Files:**
- Modify: `docs/framework/truth-files.yaml:72-83`（concepts 区 D20 注释块与两个 snapshot 登记）+ `:115-117`（第二处 deprecation 注记）+ `:144-146`（globs 注释）
- Modify: `tests/unit/contracts/test_registry_pipeline_producers.py:31-51`（D20 常量与两测试）+ `:22`（PIPELINE_PRODUCED 不变）
- Modify: `src/shenbi/pipeline/chapter_loop.py:1690-1701`（_load_manifest docstring/skeleton）

**Interfaces:**
- Produces: yaml 概念名 `snapshots/chapter-N-emergency.md`（kind: snapshot, producer: pipeline）；`snapshots/manifest.json` kind 从 snapshot → config；目录布局概念维持 glob 覆盖（glob `snapshots/chapter-*/*` 保留）

- [ ] **Step 1: 写失败测试（更新 producer 测试断言）**

`tests/unit/contracts/test_registry_pipeline_producers.py` 中：

```python
# 替换 D20 常量段（原 31-51 行注释+两常量）：
# D20 snapshot vocabulary — finalized spec #57 T4:
# - skill domain: snapshots/chapter-NNN/ (snapshot-manage writes, sequel-writing
#   reads) — covered by glob `snapshots/chapter-*/*`, no concept entry needed.
# - emergency domain: snapshots/chapter-N-emergency.md (crash_recovery
#   _snapshot_chapter_files, label always "emergency") — registered concept.
D20_EMERGENCY_FLATFILE = "snapshots/chapter-N-emergency.md"
D20_SKILL_DIR_WRITE = "snapshots/chapter-NNN/*"
```

`test_d20_real_flatfile_registered` 改为：

```python
def test_d20_emergency_flatfile_registered() -> None:
    # D20: crash_recovery emergency snapshot must be a registered concept
    # (the only src/ snapshot writer after spec #26 path 3).
    reg = load_registry()
    concept = _concept(reg, D20_EMERGENCY_FLATFILE)
    assert concept is not None, f"{D20_EMERGENCY_FLATFILE} not registered (D20)"
    assert concept.kind == "snapshot"
    assert concept.producer == "pipeline"
```

`test_d20_fictional_dir_concept_deprecated` 改为（语义反转：目录布局正名但走 glob、无概念条目）：

```python
def test_d20_skill_dir_no_concept_entry_needed() -> None:
    # D20 (spec #57 T4): the skill-domain directory layout snapshots/chapter-NNN/
    # is legitimate (snapshot-manage writes, sequel-writing reads) and is
    # covered by the glob `snapshots/chapter-*/*`; it intentionally has no
    # per-file concept entry.
    reg = load_registry()
    assert _concept(reg, D20_SKILL_DIR_WRITE) is None
    assert _concept(reg, "snapshots/manifest.json") is not None
    assert any(getattr(g, "pattern", g) == "snapshots/chapter-*/*"
               for g in getattr(reg, "globs", [])), "skill-domain glob missing"
```
（`reg.globs` 的字段名以 `src/shenbi/contracts/loader.py` 实际注册表结构为准，执行时先核对再落笔；若 registry 不暴露 globs，退化为对 yaml 文本的断言。）

同时更新该测试文件头部 docstring/注释中的旧词面（"fictional"、"D20 real flatfile snapshots/chapter-NNN-*.md"）为新定稿词面。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/contracts/test_registry_pipeline_producers.py -v`
Expected: `test_d20_emergency_flatfile_registered` FAIL（concept 未注册）；`test_d20_skill_dir_no_concept_entry_needed` 此时已 PASS（概念本就缺席/已注册——其价值在锁定正名后语义，防回潮）

- [ ] **Step 3: 改 yaml（词面定稿）**

`docs/framework/truth-files.yaml` concepts 区（原 72-83 行，**按内容锚点定位**——匹配自 `# D20: flatfile snapshots/chapter-NNN-*.md` 注释起至 `- {name: snapshots/manifest.json, kind: snapshot, producer: pipeline}` 行止的整块；行号仅供参照）替换为：

```yaml
  # D20 snapshot vocabulary — finalized (spec #57 T4, post #26 path 3):
  # - skill domain: snapshots/chapter-NNN/ directory snapshots, written by
  #   shenbi-snapshot-manage and read by shenbi-sequel-writing (the designated
  #   rollback mechanism); covered by glob `snapshots/chapter-*/*`.
  # - emergency domain: flat snapshots/chapter-N-emergency.md written by
  #   crash_recovery._snapshot_chapter_files (label always "emergency").
  - {name: snapshots/chapter-N-emergency.md, kind: snapshot, producer: pipeline}
  # pipeline-written files (no skill producer):
  # drift marker only (chapter_loop._update_last_drift_manifest writes
  # last_drift_chapter); NOT a snapshot index.
  - {name: snapshots/manifest.json, kind: config, producer: pipeline}
```

第二处：patterns 区 115-117 行的 `# D20: snapshots/chapter-NNN/manifest.json parametric removed (fictional directory concept deprecated). The real flatfile snapshots/chapter-NNN-*.md is a literal` 注记整段删除（纯注释，不附属于任何登记行）。

globs 区（原 144-146 行）收窄为与新登记一一对应（宽 glob `snapshots/chapter-*-*.md` 匹配的时间戳文件已随 Task 2 清退，emergency 由收窄 glob 覆盖）：

```yaml
  - {pattern: snapshots/chapter-*/*}   # D20: skill-domain directory snapshots
  - {pattern: snapshots/chapter-*-emergency.md}  # D20: crash_recovery emergency flatfile
  - {pattern: snapshots/*.json}
```

patterns 区（105 行起的 parametric 映射区，按文件内既有格式；同区 115-117 行过时 D20 注记整段删除）追加：

```yaml
  - {parametric: snapshots/chapter-N-emergency.md, glob: snapshots/chapter-*-emergency.md}
```

- [ ] **Step 4: 清理 chapter_loop manifest 词面**

`src/shenbi/pipeline/chapter_loop.py:1690-1701`：`_load_manifest` docstring 由「snapshot manifest …chapters」改为 drift 标记语义；返回骨架 `{"chapters": {}}` 改为 `{"last_drift_chapter": 0}`；检查 `_load_manifest`/`_update_last_drift_manifest` 全部调用方对 `chapters` 键的依赖（grep `manifest["chapters"]`/`.get("chapters")`——预期零命中，命中则该处属旧写方死代码一并清理）。`_save_manifest` docstring 的 "snapshot manifest" 改 "drift marker manifest"。

- [ ] **Step 5: 跑测试 + lint**

Run: `uv run pytest tests/unit/contracts/ tests/pipeline/ -q && just lint-contracts && just generate && git diff --stat -- docs/framework/truth-files.index.json docs/framework/dependency-dag.json tests/tiers/deps.json generated/`
Expected: 测试全 PASS；lint 绿。生成物 diff **属预期**（概念改名 + kind 翻转必然反映到 truth-files.index.json / dependency-dag.json 的 D20 条目）——核对 diff 内容仅限 D20 相关（新概念名、manifest kind、无其他意外条目），核对后并入 Step 6 commit。注意 index.json 中 `snapshots/chapter-NNN/manifest.json` 条目来自 snapshot-manage SKILL 契约，**不应**随本次 yaml 改动消失。

- [ ] **Step 6: Commit**

```bash
git add docs/framework/truth-files.yaml tests/unit/contracts/test_registry_pipeline_producers.py src/shenbi/pipeline/chapter_loop.py
# 如 Step 5 生成物有 diff，此处追加 docs/framework/truth-files.index.json docs/framework/dependency-dag.json tests/tiers/deps.json
git commit -m "fix: C19 T4 快照词面定稿 — yaml D20 三裁决 + drift 标记改kind + manifest 词面清理 (spec #57)"
```

### Task 2: g0.py MIRROR_MAP 摘除 + novel-output 快照遗留处置 + F1154 缺失报告

**Files:**
- Modify: `src/shenbi/gates/g0.py:18-23`（MIRROR_MAP 摘两条）
- Delete: `novel-output/xinghuo-ranqiong/snapshots/`（51 个 `chapter-NNN-<ts>.md` + 旧 chapters 索引 manifest.json）
- Create: `tests/fixtures/snapshots/F1154-ABSENCE.md`

**Interfaces:**
- Consumes: Task 1 定稿词面
- Produces: fixtures/snapshots/chapter-025/manifest.md 维持现状（C16 F779 已裁决 grandfathered：provenance 声明 synthetic-sample + checksums 真实）；缺失报告为其合法性注记

- [ ] **Step 1: 摘 MIRROR_MAP 两条**

`src/shenbi/gates/g0.py` 删除：

```python
    "tests/fixtures/snapshot-dir/chapter-005-20260715T232231.md": (
        "novel-output/xinghuo-ranqiong/snapshots/chapter-005-20260715T232231.md"
    ),
    "tests/fixtures/snapshot-dir/chapter-006-20260715T234925.md": (
        "novel-output/xinghuo-ranqiong/snapshots/chapter-006-20260715T234925.md"
    ),
```

并在 MIRROR_MAP 上方注释加一行：`# spec #57 T4: timestamped snapshot mirrors removed — upstream writer class deleted (#26 path 3); fixtures retained in tests/fixtures/snapshot-dir as real historical outputs.`

- [ ] **Step 2: 删除 novel-output snapshots 遗留**

```bash
grep -rln "novel-output/xinghuo-ranqiong/snapshots" src/ tools/ skills/
# 预期：g0.py 改后零命中——tests/fixtures 与 docs/audit-runs 中的命中是
# 内容级 provenance/历史证据引用（非路径依赖），不在清扫范围、不得改动
git rm -r novel-output/xinghuo-ranqiong/snapshots/
```

处置记录（进 PR 描述 + `.superpowers/sdd/progress.md` 验收证据段——工作态不入库）：51 个时间戳平铺快照 + 1 个旧 chapters 索引 manifest.json，全部出自已移除的 chapter_loop 时间戳写方（现行 crash_recovery 只写 `chapter-N-emergency.md`，现行 manifest.json 语义为 drift 标记）；git history 保留全量历史；镜像副本 chapter-005/006 留存于 tests/fixtures/snapshot-dir。

- [ ] **Step 2b: 清理 artifact-lint-exemptions.json 死条目**

`tools/artifact-lint-exemptions.json` 中 `timestamp` check 下指向 `xinghuo-ranqiong/snapshots/` 的**全部**豁免条目（11 条：chapter-{007,008,009,010,017,019,039,040,041,042,046}-*.md）随文件删除成为死条目——按 path 前缀 `xinghuo-ranqiong/snapshots/` 全量摘除（以 grep 实际命中为准，不硬编码计数）并并入 Step 5 commit；处置记录注明。

- [ ] **Step 3: F1154 缺失报告**

创建 `tests/fixtures/snapshots/F1154-ABSENCE.md`：

```markdown
# F1154 — snapshot-manage manifest fixture 缺失报告（spec #57 T4）

仓库不存在 shenbi-snapshot-manage 的真实 manifest 产物可作 fixture（G0.9 禁手造、
SDD 核心原则 8 禁现场 dispatch 取证）。`tests/fixtures/snapshots/chapter-025/manifest.md`
为 spec #54 (C16 F779) 已裁决的 grandfathered 样本：frontmatter provenance 显式声明
"hand-authored snapshot manifest; checksums are real sha256"（synthetic-sample），
checksums 为 tests/fixtures/chapters/ 真实文件 sha256。
t1-skill 场景（shenbi-snapshot-manage / shenbi-sequel-writing）引用该 fixture。
布局冻结后（本 spec item 9）如未来产出真实 snapshot-manage manifest，应替换本样本
并删除本报告。
```

- [ ] **Step 4: 验证**

Run: `uv run pytest tests/unit/security/test_t1201_forged_verdict.py tests/unit/security/test_f308_escape.py tests/unit/security/test_r5_annotation.py tests/pipeline/test_g4_directory.py tests/unit/text/cjk/test_quote_pair_count.py tests/unit/gates/ -q && uv run python tools/check_fixture_mirror.py && uv run python -c "from shenbi.gates.g0 import MIRROR_MAP; assert not any('novel-output/xinghuo-ranqiong/snapshots' in v for v in MIRROR_MAP.values()), MIRROR_MAP; print('MIRROR_MAP novel-output-snapshot-free:', len(MIRROR_MAP), 'entries')"`
Expected: 测试全 PASS；check_fixture_mirror.py exit 0；断言输出 MIRROR_MAP novel-output-snapshot-free（F780 的 tests/fixtures/snapshots 镜像条目保留，不在此断言域）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g0.py tests/fixtures/snapshots/F1154-ABSENCE.md tools/artifact-lint-exemptions.json
git commit -m "chore: C19 T4 遗留处置 — MIRROR_MAP 摘除2条 + novel-output 51快照清退 + 豁免死条目清理 + F1154 缺失报告 (spec #57)"
```

### Task 3: 全域对账核验（docs 面清扫 + 验收执行）

**Files:**
- Modify: 命中的 docs/ 说明文件（grep 决定，预期 `docs/framework/` 下描述 snapshots 的段落）

**Interfaces:**
- Consumes: Task 1/2 产物

- [ ] **Step 1: docs 面清扫**

```bash
git grep -ln "chapter-NNN-\*\|snapshots/chapter-NNN\|fictional" docs/ | grep -v specs/ | grep -v plans/ | grep -v audit-runs/
```
`docs/superpowers/audit-runs/` 是时点审计证据，**豁免词面对账、禁止改动**（命中仅记录不修）。其余命中文件逐个核对：D20 词面与新定稿一致（目录=skill 域、emergency 平铺、manifest=drift 标记）；过时描述（如仍称 manifest.json 为快照索引、仍称目录概念 fictional）就地修正。

- [ ] **Step 1b: 声明面↔词表对账（验收 2 前半）**

```bash
sed -n 1,25p skills/shenbi-snapshot-manage/SKILL.md; sed -n 1,22p skills/shenbi-sequel-writing/SKILL.md
```
核对：snapshot-manage writes `snapshots/chapter-NNN/*` + `snapshots/chapter-NNN/manifest.json`、sequel-writing reads `snapshots/chapter-NNN/*`——均被 yaml glob `snapshots/chapter-*/*` 覆盖；SKILL.md 本身**零改动**（契约已正确），如发现偏差则修 SKILL 并跑 `just lint-contracts && just generate`。

- [ ] **Step 2: 验收 1 执行**

Run: `grep -inE "supersed|fictional|deprecated" docs/framework/truth-files.yaml`
Expected: 仅命中与快照 D20 无关的行（若有）；D20 区零命中

- [ ] **Step 3: 验收 2/4 执行**

Run: `just lint-contracts && just generate && git diff --exit-code -- docs/framework/truth-files.index.json docs/framework/dependency-dag.json tests/tiers/deps.json generated/ && echo generated-clean`；`uv run pytest tests/unit/contracts/ tests/pipeline/ tests/unit/security/ -q`
（生成物清洁检查限定在生成物路径——Step 1 的 docs 手改如未 commit 属预期脏区，不算失败）
Expected: lint 绿、生成物零改动、测试全绿

- [ ] **Step 4: just check 全量**

Run: `just check`
Expected: exit 0（全量 collected、cov≥85、last 3 passed——以 exit code 为准）

- [ ] **Step 5: Commit（如有 docs 改动）**

```bash
git add <pathspec 列出的 docs 文件>
git commit -m "docs: C19 T4 docs 面词面对账 (spec #57)"
```
（无命中改动则本 task 无 commit，核验输出记 progress.md）

- [ ] **Step 6: 起草验收 5 对照说明**

起草「本 spec 与 #26 路径 3 验收对照」段落（#26 移除了差分子系统并指定 snapshot-manage 为回滚机制；本 spec T4 将其词面正名并对账三面）——存入 `.superpowers/sdd/progress.md` 验收证据段，出 PR 时贴入 PR 描述。
