# Spec #30 decisions-chain 契约链修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 decisions-sidecar 契约链四层断裂：路由（T1）、G4 文件集（T2）、G2/G4 容错收敛（T3/T6）、producer 声明（T4）、P2.5 矩阵四源一致（T5）、AGENTS.md 条款（T7）。

**Architecture:** T1 采用**文件名分区**（阶段 3 审查 I1 裁决）：`gate_G2` 在 `file_type="decisions"` 时按后缀分流——`.json` 走 decisions 分支，`.md` 落入通用路径并按 chapter 检查——CLI `shenbi-validate G2 <files> <type>` 协议零变更（镜像 G4 `decisions_validator.py:176-181` 复合分区的既有先例）。T2 在 `_resolve_g4_files` 按契约 writes 追加 decisions sidecar。T3/T6 使 G4 读侧采用与 G2 相同的 raw_decode 截断恢复（恢复仅产 FAIL+诊断，不静默放行），配 15 例 G2/G4 对撞回归。

**Tech Stack:** Python 3.11+ / pydantic DecisionsDoc / pytest / just（CI 同构验证）。

## Global Constraints

- 契约 schema 版本号保持 `shenbi-decisions-v1` 不动（spec 回滚条款）
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`；gate 检查器纯函数幂等无副作用
- 验证命令一律 `just`/`uv run`；fixture 只用真实产物或其精确副本（G0.9），来源 `novel-output/xinghuo-ranqiong`（145 个真实 decisions.json，基线重测 2026-08-31：ok=5 / bad_json=83 / bad_schema=57）
- 改 SKILL.md 契约段后必须 `just generate` 同步（deps.json/docs diff 为空）；禁止手改生成物
- 全部 task 为 **infra**（gates/g4、dispatcher、pipeline、contracts、skills 契约面）→ 协调者亲自实现，逐 task TDD + fresh-context 重审（audit-T<N>.md）
- WARN-then-FAIL 滚动已从 spec 风险条款降级删除（阶段 3 I2 裁决）：pipeline 路径本就跳过非管道 G2（executor.py:221-227），爆炸面限于非管道 dispatch；task 内以只读盘点测试代替

## 任务依赖图

T1（g2 路由）→ 独立；T2（G4 文件集）依赖 T1 的分区语义命名对齐；T3（G4 读侧恢复）→ T6（对撞测试）依赖 T1+T3；T4（producer 声明）依赖 T5（P2.5 矩阵定稿）；T5/T7 文档回写依赖 T1/T3 的最终行为。

---

### Task 1: G2 逐产物分区（T101/F438/F205）

**Files:**
- Modify: `src/shenbi/gates/g2.py:78-169`（decisions 分支）
- Test: `tests/test_g2_decisions_partition.py`（新建）
- Fixture: `tests/fixtures/decisions/`（新建，真实产物副本，见步骤 1）

**Interfaces:**
- Produces: `gate_G2` 行为变更——`file_type="decisions"` 时 `.md` 文件落入 G2.4-G2.10 通用检查（chapter 语义）；`.json` 走 G2.dec 分支。签名不变：`gate_G2(file_paths: str | list[str] | None, file_type: str = "chapter", round_dir: str | None = None, project_dir: str | None = None) -> str`

- [ ] **Step 1: 建 fixture（真实产物副本，G0.9）**

从生产树复制三类真实样本（不手写）：

```bash
mkdir -p tests/fixtures/decisions
# 合法样本（5 个 ok 之一）
uv run python - <<'EOF'
import json
from pathlib import Path
from shenbi.contracts.schemas.decisions import DecisionsDoc
src = sorted(Path("novel-output").rglob("*decisions*.json"))
out = Path("tests/fixtures/decisions")
n = 0
for f in src:
    try:
        DecisionsDoc.model_validate(json.loads(f.read_text()))
        (out / "valid-chapter-decisions.json").write_text(f.read_text())
        n += 1
        break
    except Exception:
        continue
print("copied valid:", n)
EOF
# 尾随/拼接样本：按失败形态确定性筛选（json.loads 抛错但 raw_decode 可提取首对象）
uv run python - <<'EOF'
import json
from pathlib import Path
from json import JSONDecoder
src = sorted(Path("novel-output").rglob("*decisions*.json"))
out = Path("tests/fixtures/decisions")
for f in src:
    raw = f.read_text()
    try:
        json.loads(raw)
        continue  # 合法 JSON，非尾随形态
    except json.JSONDecodeError:
        try:
            obj, _ = JSONDecoder().raw_decode(raw)
            if isinstance(obj, dict) and "$schema" in obj:
                (out / "trailing-sample.json").write_text(raw)
                print("copied trailing:", f)
                break
        except json.JSONDecodeError:
            continue
EOF
```

并复制一份真实章节草稿作 .md 主产物：`cp novel-output/xinghuo-ranqiong/chapters/chapter-2.md tests/fixtures/decisions/`（路径以实际存在为准；同时生成 copy-then-degrade 违规版 `chapter-too-short.md` = 同文件截断至 < CHAPTER_WORD_FLOOR 字）。

- [ ] **Step 2: 写失败测试**

```python
# tests/test_g2_decisions_partition.py
"""T101: decisions-双产物技能的 .md 主产物不得绕过 G2 章节检查。"""
import json
from pathlib import Path
from shenbi.gates.g2 import gate_G2

FIX = Path(__file__).parent / "fixtures" / "decisions"

def _res(files, ftype="decisions"):
    return json.loads(gate_G2([str(f) for f in files], ftype))

def test_md_gets_chapter_checks_under_decisions_type():
    r = _res([FIX / "chapter-too-short.md"])
    # FAIL 条目落 "must_fix"（shared.py fail() 结构，阶段 5 审查 I4 已核实）
    assert any(c.get("id") == "G2.6" and c.get("s") == "FAIL" for c in r["checks"] + r["must_fix"])

def test_json_still_gets_decisions_branch():
    r = _res([FIX / "valid-chapter-decisions.json"])
    assert any(c.get("id") == "G2.dec" and c.get("s") == "PASS" for c in r["checks"])

def test_dual_product_round_violating_chapter_fails():
    """验收 2 前半：含违规章节的双产物 round，G2 对 .md FAIL。"""
    r = _res([FIX / "chapter-too-short.md", FIX / "valid-chapter-decisions.json"])
    assert r["status"] != "PASS"
```

（`checks`/`mf` 的实际返回键以 gate_G2 现有 JSON 结构为准，实现前先打印一次真实输出校正断言字段名。）

- [ ] **Step 3: 跑测试确认 FAIL**

Run: `uv run pytest tests/test_g2_decisions_partition.py -v` — 期望 test_md_gets_chapter_checks 与 dual_product FAIL（现状 .md 被 continue 跳过 → PASS）。

- [ ] **Step 4: 实现（eff_type 机制，阶段 5 审查 C1 裁决）**

chapter 检查的门条件是 `file_type == "chapter"`（g2.py:223 G2.6-G2.9、:338 G2.13），仅删 decisions 分支的 `continue` 不足以让 .md 落入 G2.6。改为在循环体内先算逐文件有效类型：

```python
        # Per-file partition (T101): .json sidecars keep the decisions branch;
        # the .md main artifact is validated with chapter semantics instead of
        # bypassing G2.4-G2.10 (formerly a silent skip — spec #30 T1).
        eff_type = file_type
        if file_type == "decisions":
            if fp.endswith(".json"):
                ... existing G2.dec.4/.1/.2/.3 logic, ending in `continue` ...
            eff_type = "chapter"  # .md main artifact falls through as chapter
```

随后把 g2.py:223 与 :338 的 `if file_type == "chapter":` 改为 `if eff_type == "chapter":`（G2.4/G2.5/G2.10/G2.12 等后缀驱动检查不动，天然对 .md 生效）。同时删除 g2.py:84-89 的失实注释（「.md validated by their own file_type gate」——该 gate 不存在）。

- [ ] **Step 5: 跑测试确认 PASS + 回归**

Run: `uv run pytest tests/test_g2_decisions_partition.py -v`（PASS）&& `uv run pytest tests/ -k "g2" -x -q`（无回归）。

- [ ] **Step 6: Commit + audit**

`git add src/shenbi/gates/g2.py tests/test_g2_decisions_partition.py tests/fixtures/decisions/ && git commit -m "fix: G2 per-file partition — decisions-skill .md main artifacts no longer bypass G2.4+ (spec #30 T1, T101/F438/F205)"` → 产出 `.superpowers/sdd/audit-T1.md`（fresh-context 重审）。

---

### Task 2: G4 文件集接入 decisions sidecar（F434/T103/F795）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:600-619`（`_resolve_g4_files`）
- Test: `tests/test_g4_files_decisions.py`（新建）

**Interfaces:**
- Consumes: `load_contract(skill) -> dict`（`shenbi.contracts`，含 `writes`/`updates`）；`resolve_chapter_path(path, chapter)`（chapter_loop 既有）
- Produces: `_resolve_g4_files` 返回值新增 decisions sidecar 路径（staging 步骤带 `staging/` 前缀），G4.dec marker 不再 `{"s":"SKIP","r":"no files"}`

- [ ] **Step 1: 写失败测试**

```python
"""F434: chapter-drafting 双产物 step 的 decisions sidecar 必须进 G4 文件列表。"""
from pathlib import Path
from shenbi.pipeline.chapter_loop import _resolve_g4_files

def _mk_step(**kw):  # 真实 ChapterStep dataclass，字段以 chapter_loop 定义为准
    from shenbi.pipeline.chapter_loop import ChapterStep
    base = dict(output_path="chapters/chapter-{chapter}.md",
                skill="shenbi-chapter-drafting", uses_staging=False)
    base.update(kw)
    return ChapterStep(**base)  # 缺省字段以 dataclass 默认值补齐，实现前核对构造签名

def test_decisions_sidecar_in_g4_files(tmp_path):
    ch = tmp_path / "chapters"; ch.mkdir()
    (ch / "chapter-2.md").write_text("# 第二章\n正文" * 50)
    (ch / "chapter-2-decisions.json").write_text('{"$schema": "shenbi-decisions-v1"}')
    files = _resolve_g4_files(tmp_path, _mk_step(), chapter=2)
    assert any(str(f).endswith("chapters/chapter-2-decisions.json") for f in files)
    assert any(str(f).endswith("chapters/chapter-2.md") for f in files)

def test_state_settling_glob_not_short_circuited(tmp_path):
    """C2 回归：契约扩展不得短路 state-settling 的 staging/truth/*.md glob。"""
    st = tmp_path / "staging" / "truth"; st.mkdir(parents=True)
    (st / "current_state.md").write_text("x")
    (tmp_path / "staging" / "truth" / "state-settling-decisions.json").write_text("{}")
    step = _mk_step(output_path="", skill="shenbi-state-settling", uses_staging=True)
    files = _resolve_g4_files(tmp_path, step, chapter=2)
    assert any("current_state.md" in str(f) for f in files)          # .md 不丢
    assert any("state-settling-decisions.json" in str(f) for f in files)  # sidecar 追加

def test_revision_and_nonchapter_sidecars(tmp_path):
    """I2：chapter-revision / genre-config sidecar 的追加行为不破坏复合分区。"""
    ch = tmp_path / "chapters"; ch.mkdir()
    (ch / "chapter-3-revision.md").write_text("y")
    (ch / "chapter-3-revision-decisions.json").write_text("{}")
    step = _mk_step(output_path="chapters/chapter-{chapter}-revision.md",
                    skill="shenbi-chapter-revision")
    files = _resolve_g4_files(tmp_path, step, chapter=3)
    assert any("revision-decisions.json" in str(f) for f in files)
```

- [ ] **Step 2: 确认 FAIL** — `uv run pytest tests/test_g4_files_decisions.py -v`

- [ ] **Step 3: 实现**

在 `_resolve_g4_files` 内重构为「先解析主清单、后追加契约 sidecar」（阶段 5 审查 C2 裁决——契约扩展只追加，绝不短路 state-settling glob）：

```python
def _resolve_g4_files(project_dir: Path, step: ChapterStep, chapter: int) -> list[str]:
    single = _resolve_g4_path(project_dir, step, chapter)
    files = [single] if single else []

    # State-settling writes multiple truth files to staging/ (unchanged, runs
    # BEFORE sidecar expansion so contract expansion can't short-circuit it)
    if step.uses_staging and "state-settling" in step.skill:
        from shenbi.pipeline.checkpoint import STAGING_DIR
        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.exists():
            files.extend(
                f"{STAGING_DIR}/truth/{p.name}" for p in staging_truth.glob("*.md")
            )

    # F434: contract-declared decisions sidecars join the G4 file list so
    # G4.dec actually runs for dual-product skills instead of SKIP. Existence-
    # gated to avoid spurious FAILs; composite G4 re-partitions by suffix.
    try:
        from shenbi.contracts import load_contract, ContractError
        c = load_contract(step.skill)
    except (ContractError, ImportError):
        c = None
    if c:
        for out in c["writes"]:
            if "decisions" not in Path(out).name:
                continue
            resolved = resolve_chapter_path(out, chapter)
            from shenbi.pipeline.checkpoint import STAGING_DIR
            cand = f"{STAGING_DIR}/{resolved}" if step.uses_staging else resolved
            if (project_dir / cand).exists() and cand not in files:
                files.append(cand)
    return sorted(set(files)) if files else []
```

- [ ] **Step 4: PASS + 回归** — `uv run pytest tests/test_g4_files_decisions.py -v && uv run pytest tests/ -k "g4" -x -q`

- [ ] **Step 5: 验收 2 后半实测** — 构造临时 project_dir（复制 Task 1 fixture 双产物 + 最小 pipeline-state），断言 G4 marker 含 `G4.dec` 且 `s != "SKIP"`；命令与输出粘贴 progress.md。

- [ ] **Step 6: Commit + audit-T2.md** — `fix: route decisions sidecars into G4 file set (spec #30 T2, F434/T103/F795)`

---

### Task 3: G4 读侧 raw_decode 恢复对齐（T3 残余 + T6 前半）

**Files:**
- Modify: `src/shenbi/gates/g4/decisions_validator.py:91-118`（G4.dec 读侧）
- Test: `tests/test_g4_decisions_recovery.py`（新建）

**Interfaces:**
- Consumes: g2.py 既有 raw_decode 截断恢复口径（`g2.py:115-139`）
- Produces: G4 对尾随/拼接 JSON 产出结构化 `G4.dec.4`/`G4.dec.1` FAIL（含截断诊断），与 G2 同文件判定一致；不静默放行

- [ ] **Step 1: 失败测试**

```python
"""T104 前半：同一损坏 decisions.json，G2 与 G4 判定必须一致。"""
from shenbi.gates.g2 import gate_G2
# G4 判定入口以 decisions_validator 现有导出为准（run/validate 函数签名实现前核对）

def test_trailing_json_g2_g4_agree(fixture_path):
    g2 = json.loads(gate_G2([str(fixture_path)], "decisions"))
    g4 = _run_g4_decisions(fixture_path)   # 以真实入口替换
    assert _verdict(g2) == _verdict(g4)    # 两者都 FAIL 且 reason 类别相同
```

- [ ] **Step 2: FAIL 确认** → **Step 3: 实现**（G4 读侧改为与 g2 相同的 `raw_decode` 首对象提取 + `count('"$schema"')>1` 拼接检测，恢复出的对象仍须过 `DecisionsDoc.model_validate`；提取失败/拼接 → FAIL 带诊断，绝不放行）→ **Step 4: PASS + `pytest -k "decisions" -x -q` 回归** → **Step 5: Commit + audit-T3.md**（`fix: G4.dec read side adopts G2 raw_decode recovery policy (spec #30 T3/T6, T104)`）

---

### Task 4: P2.5 矩阵四源一致 + 错误消息（F212/F431/T108/F908）

**Files:**
- Modify: `src/shenbi/contracts/schemas/decisions.py:42`（错误消息补 medium）
- Modify: `docs/framework/decisions-schema.md:64-88`（P2.5 表补 medium 行、severity 枚举补 medium）
- Test: `tests/test_decisions_p25_medium.py`（新建）

- [ ] **Step 1: 失败测试** — 断言 medium 无 rationale 的 ValidationError message 含 `"medium"`；
- [ ] **Step 2: FAIL** → **Step 3: 错误消息改为 `"rationale REQUIRED for medium/high-severity or manual_override"`；decisions-schema.md severity 节补 `- medium (rationale required)` 行、P2.5 表补 medium 行** → **Step 4: PASS** → **Step 5: Commit + audit-T4.md**（`fix: P2.5 rationale matrix four-source alignment — medium row (spec #30 T5, F212/F431/T108/F908)`）

---

### Task 5: producer 声明补全 + 四源对账 lint（F439/T106）

**Files:**
- Modify: 6 个生产技能 SKILL.md（chapter-drafting/chapter-revision/context-composing/genre-config/market-radar/short-drafting）——writes 段后嵌 decisions 输出模板（必填字段 `$schema/skill/chapter/produced_at` + selections/adjustments 骨架）
- Create: `tools/lint_decisions_sources.py`（**三源**对账，阶段 5 审查 I1 裁决——第四源「实产样本」由 Task 6 对撞语料测试承担，lint 不依赖它：decisions-schema.md 技能清单 ↔ truth-files.yaml kind=decisions ↔ SKILL.md writes 含 decisions）
- Modify: `justfile`（**`check` recipe 内单列一行**，镜像 `tools/lint_status_strings.py` 在 justfile:15 的挂法；非只挂 lint-contracts）
- Test: `tests/test_lint_decisions_sources.py`

- [ ] **Step 1: 失败测试**（lint 对齐的 skill 集断言 + SKILL.md 含 `produced_at` 模板字段断言）
- [ ] **Step 2: FAIL** → **Step 3: 实现**（SKILL.md 模板段用统一片段；lint 脚本输出三方清单 diff，退出码非 0 即不一致）→ **Step 4: `just generate` 后 deps.json/docs diff 为空；`just lint-contracts` 绿** → **Step 5: Commit + audit-T5.md**（`feat: decisions producer declarations + four-source reconciliation lint (spec #30 T4, F439/T106)`）

---

### Task 6: G2/G4 对撞回归 15 例（T104）

**Files:**
- Test: `tests/test_g2_g4_decisions_collision.py`（新建，参数化 15 例）

**Interfaces:**
- Consumes: Task 1/3 后的 gate_G2 与 G4.dec 判定入口
- Fixture: `tests/fixtures/decisions/corpus/`（15 个真实损坏样本副本：从 novel-output 83 bad_json + 57 bad_schema 中各取代表 + 5 ok，选取以覆盖不同损坏形态——多对象拼接/截断/前缀散文/缺必填/枚举越表/rationale 缺失）

- [ ] **Step 1: 选样复制（G0.9 真实副本）并写参数化测试** — 每例断言 G2 与 G4 verdict 一致（同为 PASS 或同为 FAIL 且 reason 类别一致）
- [ ] **Step 2: FAIL/不一致暴露** → **Step 3: 修残余分歧（在 Task 3 基础上补漏）** → **Step 4: 全 15 例 PASS** → **Step 5: Commit + audit-T6.md**（`test: 15-case G2/G4 decisions collision regression suite (spec #30 T6, T104)`）

---

### Task 7: AGENTS.md decisions 条款对齐（T107）

**Files:**
- Modify: `AGENTS.md:63-73`——G2 描述改为「per-file 分区：.json 走 G2.dec，.md 走章节检查」；P2.5 条款补 medium；四源对账 lint 提及
- Test: 无独立测试（docs）；核验 `grep -n "medium" AGENTS.md docs/framework/decisions-schema.md src/shenbi/contracts/schemas/decisions.py` 三处一致

- [ ] **Step 1: 修改** → **Step 2: 核验命令粘贴 progress.md** → **Step 3: Commit + audit-T7.md**（`docs: align AGENTS.md decisions-sidecar clause with final rulings (spec #30 T7, T107)`）

---

### Task 8: spec 定稿修订 + 全量验收

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-decisions-chain-fix.md`——回写阶段 3 裁决（I1 文件名分区形状、I2 WARN 模式删除、I3 基线数字 5/83/57）、`Status: Revised 2026-08-31`（本分支内修订，随主 PR 合并）

**Steps:**
- [ ] 回写 spec 三处裁决 + 验收 1 改 fixtures 口径、验收 2 补「copy-then-degrade 真实产物」措辞（Minor 4）
- [ ] 逐条跑 spec 验收 1-4（fixtures 全量 DecisionsDoc 校验 100% 通过口径、G2 .md FAIL、G4.dec 非 SKIP、15 例对撞、`just check`），输出粘贴 progress.md `## 验收证据`
- [ ] Commit + audit-T8.md（`docs(spec): revise spec #30 per phase-3 rulings and verified baselines`）

## Self-Review

- 覆盖：17 簇成员 → T1(F205/F438/T101) T2(F434/T103/F795) T3+T6(F237 残余/F791/T104) T5→Task4(F212/F431/F908/T108) T4→Task5(F439/T106) T7→Task7(T107) F1102→Task6 语料基线。验收 1→Task6+8；验收 2→Task1/2；验收 3→Task6；验收 4→阶段 7。无孤儿。
- 无占位符：代码块均为实现形状，标注「以现有结构为准」处为核对指令非延后实现。
- 类型一致：`_resolve_g4_files` 返回 `list[str]`；gate_G2 签名不变。

## 终审（阶段 8）M 项处置记录 · 2026-08-31

- 终审一轮 0C/3I/4M：I1（staged_decisions_targets 静默吞 ContractError）、I2（两处内联 sidecar glob 未走共享机制）、I3（phase_runner.py 陈旧注释）、M4（重复 import）→ 均已修（commit fc899236）
- M5 case16 为 copy-then-degrade 构造（真实副本+尾随块），T104 判别用例，**不修（by design）**
- M6 parse_decisions_payload 内 "FAIL" 字面量沿袭被替换的 g2 旧内联形态，**不修（既有模式）**
- M7 plan 原写 sorted(set(files))，实现为插入序+dedupe guard，行为等价且保留主产物优先序，**不修（实现更优）**
- 终审二轮 0C/0I/2M(新)：M1 契约驱动提交比旧 glob 严格（未声明 sidecar 会被清场丢弃）——by design（契约单源），观察缺口遗留；M2 本处置块
