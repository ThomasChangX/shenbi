# Spec #116 门禁判别力仪表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 G4 确定性门禁建判别力仪表——离线回放工具＋恒真登记＋WARN→FAIL 哨兵＋七项标定提案＋真实章变异负例红测，全程不改任何门行为。

**Architecture:** 四件新增（tools/ 三脚本＋docs/ 两文档＋fixtures/ 变异负例）＋两处既有文件小改（justfile 配方、invariants.md 分工行）。回放工具克隆 `tools/replay_severity_vocab.py` 形态（argparse＋`--out`＋只读）；归因/变异共用一个「叙事窗口提取」helper（复刻门的三重预处理——测量面=执法面）；登记 lint 持 CHECK_REGISTRY 单源（chapter_drafting.py 单文件 AST 扫描＋显式补充项，#88 inventory 仅作交叉参考）；哨兵只读已提交 baseline 文档（CI 无语料依赖）；变异器维护者侧生成裁片 fixture（G0.9 provenance 头）。

**Tech Stack:** Python 3.11+（stdlib only：argparse/ast/json/re/pathlib/datetime）、pytest、just。零 LLM、零新依赖。

## Global Constraints（spec 逐字复制——每 task 隐含包含）

- 「本件只建仪表与提案，**不改任何门行为**——T3 的每项标定提案交用户逐项裁定；不考虑在飞项目（vol1 只回放报告，不重跑不改产物）；零付费派发（确定性回放零成本）」（用户裁定 2026-11-15）
- 「纯确定性、零 LLM、**不写被测项目目录**（报告经 `--out` 落 `reports/`）」（T1）
- 「**分类标签必须人工裁定，不得由仪表自动断言**」（§3 风险）
- 「单书语料（B5 边界）：baseline 只对 vol1 成立」（§3 风险）
- 「变异前后文件 mtime 不变（项目只读）；G0.9 provenance 头合规；变异副本只进测试目录，不得写项目」（T4）
- 「禁止用 full 口径做判别力结论」（§3 风险）
- 无代码行为改动：`git diff` 仅 tools/tests/docs/justfile（T3 判据）——**src/shenbi/ 零改动**
- 域约束：SDD 全流程禁为「验证」目的触发真实 LLM dispatch（`shenbi-dispatch`/`pipeline init|resume|review`）
- commit pathspec 保护：所有 commit 显式列文件路径，禁 `git add -A`/`git add .`

## 测试层级与 fixture 声明（plan 加项）

- 全部测试 = **T1 层**（unit/structural）；验收 2 的 50 章回放为维护者侧实跑（证据贴 progress.md `## 验收证据`），不进 CI——CI 无 `novel-*` 语料（`.gitignore` `/novel-*`）
- 结构性 unit 输入（合成章/窗口布局）按 AGENTS.md 允许 inline/tmp_path 构造；**真实章变异 fixture**（Task 2/3 产物）带 G0.9 provenance 头，只进 `tests/fixtures/gate-power/`
- F947：无任何验收依赖真实 LLM dispatch 或手写 mock——全部确定性可离线复验

## 关键源码事实（审查已核——实现者不得偏离）

- `passed()` JSON **无 `must_fix` 键**（shared.py:652-667；仅 `fail()` 有）→ 一切 `res["must_fix"]` 必须写 `res.get("must_fix", [])`（C1）
- protagonist FAIL 真名 `G4.cd.protagonist_absent`（chapter_drafting.py:478）；无 `characters/protagonist.md` 时 check 行 **SKIP**（:1243-1252）；`cd.major_chars`/`cd.minor_chars` 属 character_design.py（他门），`cd.micro_hook_run` 需 memo_v3＋project_dir（:1352, :1552）（C2）
- 门叙事窗口预处理序（:728-731）：剥 `<!--HOOK-*->` 块 → `META_BLOCK_RE.sub`（shared.py:42 公开）→ `strip_scene_markers`（shared.py:56 公开）→ split 段 → `[-8:]`——归因/变异必须走同一序（C3）
- `tests/fixtures/g4-id-inventory.json` 是扁平清单（含 character_design 的 `cd.major_chars` 等、缺变量发射的 `cd.protagonist_absent`）——**不得作 registry 集合等式的一源**，仅交叉参考（C4）
- `TRANSITION_SPECIFIC = ["不过","此时","突然","终于","于是"]`（shared.py:911）；计数先数「然」再减化合物（:914-934）——注入词必须取自此面（I5）
- `META_NARRATIVE` 7 词闭集（shared.py:902-910：让人感悟/引人深思/由此可见/综上所述/值得注意的是/不禁感慨/不由得想到）——meta 注入载荷取闭集词（I1）
- `cd.post_wordcount_precision` 只有 WARN 臂（post_declarations.py:133-155 返回 warns；:950-953 固定 WARN 行）（I2）
- `_check_content_uniqueness` 对 `Path(rd)/"project-output"/"chapters"` 跨章比对＋指纹是集合（:1084-1113, :443-457）——章内复制不可见（I3）
- voice_density must_fix 需 `ctx.memo_v2`（:1410；memo 来自 `project_dir/plans/chapter-N-plan.md` :699-702）；scene_hook_match 需 plan 文本（:717-722）；hook_type_rotation 需 `declared_history(project_dir)`（:555-569）（I4）
- `check_prop_handoffs` 实签名 `(text: str, memo_text: str, props, known_names=None, owner_aliases=None)`（:149-155）（M5）；`check_counter_reconciliation(text, memo_text, counters, *, fp="")`（:255）

---

### Task 1: 回放仪表 `tools/gate_power_replay.py` ＋ `just gate-power`

**Files:**
- Create: `tools/gate_power_replay.py`
- Modify: `justfile`（新配方 `gate-power`，置于 `lint:` 配方之后独立段落）
- Test: `tests/unit/tools/test_gate_power_replay.py`

**Interfaces:**
- Consumes: `g4_chapter_drafting(fps: list[str], rd: str | None, project_dir: str | None, repo_root: str | None) -> str`（chapter_drafting.py:1505；JSON 顶层 `{gate, status, timestamp, checks}`，FAIL 时另有 `blocked_action/must_fix`）；`shared.py` 公开件：`count_transition_words(content: str) -> int`（:914）、`strip_narrative_body`（:398）、`count_similes(content: str) -> dict[str, Any]`（:449）、`META_BLOCK_RE`（:42）、`strip_scene_markers`（:56）；`ending_archetype_of(text: str) -> str | None`（chapter_drafting.py:519）
- Produces（Task 4/5 消费）:
  - CLI：`uv run python tools/gate_power_replay.py PROJECT_DIR [--out PATH] [--pattern "chapter-*.md"] [--state-free-only]` → markdown 报告（同输入同输出；`timestamp` 字段不入报告）
  - 模块级：`collect(project_dir: Path, pattern: str) -> list[dict]`、`summarise(rows) -> dict[str, dict]`（含 `_firing`）、`narrative_window(content: str) -> list[str]`（**共用叙事窗口 helper**——C3 修订核心，Task 2 变异器 import 复用）、`hook_window_attribution(content: str) -> dict`、`ARM_TO_CANONICAL: dict[str, str]`（M2 回射表）、`STATE_FREE_IDS`/`TRUTH_DEPENDENT_IDS`

- [ ] **Step 1: 写失败测试**（`tests/unit/tools/test_gate_power_replay.py`）

```python
"""Spec #116 T1: gate-power replay tool unit tests (structural inputs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gate_power_replay import (
    ARM_TO_CANONICAL,
    STATE_FREE_IDS,
    TRUTH_DEPENDENT_IDS,
    collect,
    hook_window_attribution,
    narrative_window,
    summarise,
)

# 结构性合成章（AGENTS.md 允许：tmp_path 内联合法，非 fixture 冒充技能产物）
CH_WITH_HOOK = """---
name: 测试章
---

## PRE_WRITE_CHECK

- 本章字数: 200

## 第一章　测试

他推开门，看见院子里堆着柴。她还站在原地没动。

「你还欠着账。」他说。

门外的风吹进来，烛火晃了一下。到底谁在撒谎？41 人失踪，82 户报官。

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK

- [x] 自检完成: 是
- [x] 实际字数: 200
<!--META-END-->
"""


def _mk_project(tmp_path: Path, chapters: dict[str, str]) -> Path:
    (tmp_path / "chapters").mkdir()
    for name, text in chapters.items():
        (tmp_path / "chapters" / name).write_text(text, encoding="utf-8")
    return tmp_path


class TestCollect:
    def test_collect_all_pass_chapter_no_must_fix_key(self, tmp_path: Path) -> None:
        """C1 钉：passed() 无 must_fix 键——collect 不得 KeyError。"""
        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        rows = collect(rd, "chapter-*.md")  # 不抛 KeyError 即通过
        assert len(rows) == 1
        # NB1：合成章短于 3000 字下限且无场景标记——must_fix 必非空；只钉键存在性
        assert isinstance(rows[0]["must_fix"], list)

    def test_collect_passed_shape_json_without_must_fix_key(self, tmp_path, monkeypatch) -> None:
        """C1 病灶路径直测：monkeypatch g4 返回 passed() 形 JSON（无 must_fix 键）。"""
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        monkeypatch.setattr(
            gpr,
            "g4_chapter_drafting",
            lambda fps, rd=None, project_dir=None, repo_root=None: json.dumps(
                {"gate": "G4-chapter-drafting", "status": "PASS", "checks": [], "timestamp": "t"}
            ),
        )
        rows = gpr.collect(rd, "chapter-*.md")
        assert rows[0]["must_fix"] == []

    def test_collect_skips_non_pure_chapter_files(self, tmp_path: Path) -> None:
        rd = _mk_project(
            tmp_path,
            {"chapter-1.md": CH_WITH_HOOK, "chapter-1-pre-rev.md": CH_WITH_HOOK},
        )
        rows = collect(rd, "chapter-*.md")
        assert [r["file"] for r in rows] == ["chapter-1.md"]


class TestNarrativeWindow:
    def test_window_excludes_meta_and_hook_blocks(self) -> None:
        """C3 钉：窗口=三重预处理后的叙事段，POST 块不占窗口位。"""
        text = "第一段但在这里。\n\n第二段他还欠着账。\n\n" + (
            "<!--HOOK-BEGIN-->钩子台账<!--HOOK-END-->\n\n"
            "<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n- [x] 项\n<!--META-END-->"
        )
        paras = narrative_window(text)
        assert paras == ["第一段但在这里。", "第二段他还欠着账。"]

    def test_window_matches_gate_preprocessing_on_real_fixture() -> None:
        """真实 fixture 章上窗口归因与门判定双向一致（C3/I6 修订）。"""
        fixture = Path("tests/fixtures/chapters/chapter-1.md")
        if not fixture.is_file():
            pytest.skip("fixture chapters/chapter-1.md 不在盘")
        from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

        content = fixture.read_text(encoding="utf-8")
        attr = hook_window_attribution(content)
        res = json.loads(
            g4_chapter_drafting(
                [str(fixture)], str(fixture.parent), str(fixture.parent), repo_root=None
            )
        )
        hook_rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
        no_hook = any(m.startswith("G4.cd.no_hook:") for m in res.get("must_fix", []))
        hit = attr["has_q"] or bool(attr["singles"] or attr["multi"]) or attr["has_ledger"]
        if attr["window_cjk"] < 30:
            assert not hook_rows and not no_hook  # 窗口质量不足→两口径都不判
        else:
            assert bool(hook_rows) != no_hook  # PASS 行与 no_hook mf 互斥
            if hook_rows:
                assert hit  # PASS ⟺ 三臂任一命中


class TestSummarise:
    def test_counts_and_arm_canonical_fold(self) -> None:
        rows = [
            {
                "file": "chapter-1.md",
                "checks": [
                    {"id": "G4.cd.chapter_end_hook", "s": "PASS"},
                    {"id": "G4.cd.voice_density", "s": "FAIL"},
                ],
                "must_fix": ["G4.cd.voice_density:chapter-1.md:1<2"],
            },
            {
                "file": "chapter-2.md",
                "checks": [
                    {"id": "G4.cd.chapter_end_hook", "s": "PASS"},
                    {"id": "G4.cd.protagonist_presence", "s": "PASS"},
                ],
                "must_fix": ["G4.cd.no_hook:chapter-2.md:窗口未检出"],
            },
        ]
        s = summarise(rows)
        assert s["G4.cd.chapter_end_hook"]["PASS"] == 2
        # M2：mf arm 回射 canonical 后计 FAIL（no_hook→chapter_end_hook）
        assert s["G4.cd.chapter_end_hook"]["FAIL"] == 1
        assert ARM_TO_CANONICAL["G4.cd.no_hook"] == "G4.cd.chapter_end_hook"
        assert ARM_TO_CANONICAL["G4.cd.protagonist_absent"] == "G4.cd.protagonist_presence"

    def test_must_fix_without_fail_row_counted_once(self) -> None:
        rows = [
            {
                "file": "chapter-1.md",
                "checks": [{"id": "X", "s": "FAIL"}],
                "must_fix": ["X:c1:m"],
            }
        ]
        s = summarise(rows)
        assert s["X"]["FAIL"] == 1  # 同章同 id 去重

    def test_firing_rate(self) -> None:
        s = summarise(
            [
                {"file": "c1", "checks": [{"id": "X", "s": "PASS"}], "must_fix": []},
                {"file": "c2", "checks": [{"id": "X", "s": "FAIL"}], "must_fix": ["X:c2:m"]},
            ]
        )
        assert s["_firing"]["X"] == pytest.approx(0.5)


class TestCaliberSplit:
    def test_state_free_and_truth_sets_partition(self) -> None:
        assert "G4.cd.prop_handoff" in TRUTH_DEPENDENT_IDS
        assert "cd.balance_value_drift" in TRUTH_DEPENDENT_IDS
        assert "G4.cd.hook_type_rotation" in TRUTH_DEPENDENT_IDS  # M3：读 plans 历史
        assert "G4.cd.payoff_density" in STATE_FREE_IDS  # M3：与 registry 对齐
        assert not (STATE_FREE_IDS & TRUTH_DEPENDENT_IDS)


class TestDeterminism:
    def test_same_input_same_report(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        assert gpr.render_report(rd, "chapter-*.md") == gpr.render_report(rd, "chapter-*.md")

    def test_no_write_into_project_dir(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        before = sorted(p.name for p in (rd / "chapters").iterdir())
        gpr.render_report(rd, "chapter-*.md")
        assert sorted(p.name for p in (rd / "chapters").iterdir()) == before
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.gate_power_replay'`

- [ ] **Step 3: 实现 `tools/gate_power_replay.py`**

克隆 `tools/replay_severity_vocab.py` 形态（shebang＋docstring 引用 spec＋argparse＋`--out`＋stderr 报告去向）。核心骨架（实现者照抄后补全报告排版与注释）：

```python
#!/usr/bin/env python3
"""Spec #116 T1: offline G4 discriminative-power replay (zero LLM, read-only).

克隆 tools/replay_severity_vocab.py 形态（#105 先例）。对项目章集逐章调用
g4_chapter_drafting，聚合 per-check PASS/WARN/FAIL/SKIP 计数、firing rate、
触发归因；双口径（state-free / truth 依赖，附录 A 口径列锚）＋ simile
narrative-only 对照列（r2/M7）。不写被测项目目录；报告经 --out 落盘或 stdout。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import (
    ending_archetype_of,
    g4_chapter_drafting,
)
from shenbi.gates.shared import (
    META_BLOCK_RE,
    count_similes,
    count_transition_words,
    strip_narrative_body,
    strip_scene_markers,
)

# 附录 A 口径列（spec r2）＋ M3 对齐（hook_type_rotation 读 plans 历史 → truth 依赖）
TRUTH_DEPENDENT_IDS = frozenset(
    {
        "G4.cd.prop_handoff",
        "cd.balance_value_drift",
        "cd.balance_value_drift.bundle",
        "cd.counter",
        "cd.counter.plan_conflict",
        "cd.counter.base_mismatch",
        "cd.counter.prose_mismatch",
        "G4.cd.hook_type_rotation",
    }
)
STATE_FREE_IDS = frozenset(
    {
        "G4.pre_check",
        "G4.post_check",
        "G4.transition",
        "G4.fatigue",
        "G4.meta",
        "G4.word_count",
        "G4.cd.scene_count",
        "G4.cd.scene_concreteness",
        "G4.cd.scene_hook_match",  # NB5：回 state-free——对齐附录 A（读 plans 声明，非 truth oracle）
        "G4.cd.chapter_end_hook",
        "G4.cd.protagonist_presence",
        "G4.cd.surge",
        "G4.cd.simile_band",
        "G4.cd.voice_density",
        "G4.cd.golden_slot",
        "G4.cd.content_uniqueness",
        "G4.cd.quote_verbatim",
        "G4.cd.payoff_density",
        "cd.post_quote_verbatim",
        "cd.post_transition_cross",
        "cd.post_wordcount_precision",
        "G4.cd.ending_diversity",
    }
)

# M2：mf-only 失败臂 → canonical 门行回射（Task 4 registry fail_arms 同源）
ARM_TO_CANONICAL: dict[str, str] = {
    "G4.cd.no_hook": "G4.cd.chapter_end_hook",
    "G4.cd.protagonist_absent": "G4.cd.protagonist_presence",
    "G4.cd.no_visual_scene": "G4.cd.scene_concreteness",
    "G4.cd.content_overlap": "G4.cd.content_uniqueness",
}

# 归因再推导（锚：chapter_drafting.py:728-731 预处理序＋:1178-1235 三臂——
# narrative_window 与门同序是 C3 修订核心；漂移由一致性测试双向校验兜底）
HOOK_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)
SINGLE_CHAR_TENSION = frozenset("但却还仍瞒藏账欠谜")
_Q_RE = re.compile(r"[？?]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def narrative_window(content: str) -> list[str]:
    """与门同序的叙事段面（剥 HOOK 块→META 块→场景标记→split）。"""
    text = re.sub(r"<!--HOOK-BEGIN-->.*?<!--HOOK-END-->", "", content, flags=re.DOTALL)
    text = META_BLOCK_RE.sub("", text)
    text = strip_scene_markers(text)
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def hook_window_attribution(content: str) -> dict[str, object]:
    """Re-derive the end-hook window arms (diagnostic only, gate verdict 不变)."""
    paras = narrative_window(content)
    # NB3：与门同滤（chapter_drafting.py:1179——[-8:] 后再滤标题/引用/清单行）
    window = [p for p in paras[-8:] if not p.startswith(("#", "##", ">", "---", "- [ ]"))]
    text = "".join(window)
    hits = set(HOOK_TENSION_RE.findall(text))
    has_q = bool(_Q_RE.search(text))
    has_ledger = len(re.findall(r"\d+", text)) >= 2
    return {
        "window_cjk": len(_CJK_RE.findall(text)),
        "has_q": has_q,
        "multi": sorted(hits - SINGLE_CHAR_TENSION),
        "singles": sorted(hits & SINGLE_CHAR_TENSION),
        "has_ledger": has_ledger,
        "single_char_only": (not has_q)
        and (not has_ledger)
        and bool(hits & SINGLE_CHAR_TENSION)
        and not (hits - SINGLE_CHAR_TENSION),
    }


def _pure_chapter(stem: str) -> bool:
    return re.fullmatch(r"chapter-\d+", stem) is not None


def collect(project_dir: Path, pattern: str = "chapter-*.md") -> list[dict]:
    chapters = sorted(p for p in (project_dir / "chapters").glob(pattern) if _pure_chapter(p.stem))
    rows: list[dict] = []
    for p in chapters:
        res = json.loads(
            g4_chapter_drafting([str(p)], str(project_dir), str(project_dir), repo_root=None)
        )
        # C1：passed() 无 must_fix 键
        rows.append({"file": p.name, "checks": res["checks"], "must_fix": res.get("must_fix", [])})
    return rows
```

`summarise(rows)`：per id 聚合 `checks` 行 s 计数；must_fix 行 id（首 `:` 前缀）先经 `ARM_TO_CANONICAL` 回射再计入 canonical 行 FAIL（同章同 id 与 check 行 FAIL 去重）；`_firing[id] = (FAIL+WARN 非 0 章数)/总章数`。`render_report(project_dir, pattern)`：markdown——per-check 表（canonical id｜口径｜PASS｜WARN｜FAIL｜SKIP｜firing rate）＋归因节（hook：`narrative_window` 尾 8 段统计 single_char_only 章数、`还`/`账` 命中章数；protagonist：`characters/protagonist.md` frontmatter `name:`＋`他` 再推导、总数中位/最小；transition：`count_transition_words(strip_narrative_body(content))` 中位；ending：`ending_archetype_of` None 计数；simile 双口径 `count_similes(content)` vs `count_similes(strip_narrative_body(content))` per_1000 均值）；`--state-free-only` 剔除 TRUTH_DEPENDENT_IDS 行。`main()` 同 replay_severity_vocab（project_dir＋`--out`＋`--pattern`＋`--state-free-only`）。

- [ ] **Step 4: justfile 配方**

在 `lint:` 配方定义之后（`type:` 之前）加：

```just
# Spec #116 T1: offline gate discriminative-power replay (zero LLM, read-only)
gate-power DIR *ARGS:
    uv run python tools/gate_power_replay.py {{DIR}} {{ARGS}}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py -v`
Expected: 全 PASS（含 `test_window_matches_gate_preprocessing_on_real_fixture`——若 SKIP 须在 task report 记原因，不许静默）

- [ ] **Step 6: 真实章冒烟（维护者侧，CI 外）**

Run: `uv run python tools/gate_power_replay.py novel-xinghuo-vol1 --out /tmp/gate-power-smoke.md && head -30 /tmp/gate-power-smoke.md`
Expected: 报告生成；`G4.cd.chapter_end_hook` 50 PASS；`G4.cd.voice_density` FAIL=14；`find novel-xinghuo-vol1 -newer /tmp/gate-power-smoke.md | wc -l` = 0（项目只读）

- [ ] **Step 7: Commit**

```bash
git add tools/gate_power_replay.py tests/unit/tools/test_gate_power_replay.py justfile
git commit -m "feat: spec #116 T1 gate-power 离线判别力回放仪表+just 配方"
```

---

### Task 2: 变异引擎＋最低子集三红测（hook/protagonist/transition）

**Files:**
- Create: `tools/gen_gate_power_fixtures.py`
- Create: `tests/fixtures/gate-power/chapter-1-hook-killed.md`（生成产物，提交）
- Create: `tests/fixtures/gate-power/chapter-1-protagonist-vanished.md`
- Create: `tests/fixtures/gate-power/chapter-1-transition-flooded.md`
- Create: `tests/fixtures/gate-power/characters/protagonist.md`（frontmatter `name: 那罕`——C2 前置物；provenance 头注明衍生自真实 protagonist.md 的 name 行）
- Create: `tests/fixtures/gate-power/README.md`（provenance 说明＋公开 repo 内容政策声明）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`

**Interfaces:**
- Consumes: Task 1 `narrative_window`（C3：变异与归因共用窗口面）；源章 = 维护者盘上 `novel-xinghuo-vol1/chapters/chapter-1.md`（生成时一次性读）
- Produces（Task 3/4 消费）: CLI `uv run python tools/gen_gate_power_fixtures.py SOURCE OUT --mutation NAME [--full]`；`MUTATIONS: dict[str, Callable[[str], str]]`（Task 3 扩展同注册表）；裁片算子 `excerpt_tail(text, keep=3)`（I7：frontmatter＋叙事尾窗段）；fixture 头部 G0.9 provenance 格式：

```markdown
<!--
provenance: real-output-mutation (G0.9)
source: novel-xinghuo-vol1/chapters/chapter-1.md (章 1, gitignored 项目)
mutation: hook_killed (tools/gen_gate_power_fixtures.py, spec #116 T4)
excerpt: frontmatter + 叙事尾窗 (M4 裁片; --full 时记全章裁定)
generated: 2026-11-19 (维护者侧一次性; 确定性: 同源同输出)
-->
```

- [ ] **Step 1: 写失败测试**（`tests/unit/gates/g4/test_gate_power_negatives.py`）

```python
"""Spec #116 T4: real-chapter mutation → gate FAIL red tests (prose face)."""

from __future__ import annotations

import json
from pathlib import Path

FIX_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "gate-power"  # NB2：parents[3]=tests/


def _g4(fixture_name: str) -> dict:
    fp = str(FIX_DIR / fixture_name)
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    return json.loads(g4_chapter_drafting([fp], str(FIX_DIR), str(FIX_DIR), repo_root=None))


def test_hook_killed_real_chapter_fails_hook_gate() -> None:
    """真实章变异→FAIL：章尾窗口张力全部抹除（spec 验收 5 最低子集之一）。"""
    res = _g4("chapter-1-hook-killed.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.no_hook:") for m in mf), mf[:3]


def test_protagonist_vanished_real_chapter_fails_presence_gate() -> None:
    """C2：真臂=protagonist_absent（major_chars 属他门；SKIP 需 characters 前置物）。"""
    res = _g4("chapter-1-protagonist-vanished.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.protagonist_absent:") for m in mf), mf[:3]


def test_transition_flooded_real_chapter_fails_transition_gate() -> None:
    res = _g4("chapter-1-transition-flooded.md")
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.transition:") for m in mf), mf[:3]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: FAIL with `FileNotFoundError`（fixture 未生成）

- [ ] **Step 3: 实现变异引擎 `tools/gen_gate_power_fixtures.py`**

```python
#!/usr/bin/env python3
"""Spec #116 T4: deterministic real-chapter mutator → negative-example fixtures.

维护者侧一次性运行（源=gitignored 项目章）；产物提交 tests/fixtures/gate-power/。
确定性：同源同输出（无 RNG）；裁片（M4/I7）：frontmatter＋被测叙事尾窗段。
窗口面与门同序（import Task 1 narrative_window——测量面=执法面，C3）。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # repo 根——统一 tools. 包身份（NB 系）
from tools.gate_power_replay import narrative_window  # noqa: E402 (同目录工具互引)

PROVENANCE_TMPL = (
    "<!--\nprovenance: real-output-mutation (G0.9)\nsource: {source} (gitignored 项目真实产物)\n"
    "mutation: {name} (tools/gen_gate_power_fixtures.py, spec #116 T4)\n"
    "excerpt: {excerpt_note}\n"
    "generated: {today} (维护者侧一次性; 确定性: 同源同输出)\n-->\n\n"
)

_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)
# I5：注入词必须取自 count_transition_words 计数面（shared.py:911 TRANSITION_SPECIFIC）
_TRANSITION_FILLERS = ["不过，", "此时，", "突然，", "终于，", "于是，"]


def _frontmatter_end(paras: list[str]) -> int:
    if not paras or not paras[0].startswith("---"):
        return 0
    for i, p in enumerate(paras[1:], start=1):
        if p.strip() == "---":
            return i + 1
    return 0


def excerpt_tail(text: str, keep_after: int = 3) -> str:
    """I7 裁片：frontmatter＋叙事尾窗段（变异落点在尾窗内）。"""
    paras = text.split("\n\n")
    fm = paras[: _frontmatter_end(paras)]
    narrative = narrative_window(text)
    tail = narrative[-(8 + keep_after) :]
    return "\n\n".join(fm + tail)


def hook_killed(text: str) -> str:
    """章尾窗口（narrative_window 尾 8 段）张力词→中性、删？与数字串。"""
    paras = narrative_window(text)
    head, tail = paras[:-8], paras[-8:]
    out = []
    for p in tail:
        p = _TENSION_RE.sub("就", p)
        p = re.sub(r"[？?]", "。", p)
        p = re.sub(r"\d+", "数", p)
        out.append(p)
    return "\n\n".join(head + out)


def protagonist_vanished(text: str) -> str:
    """主角名→术赤；「他」全替换（含「」归属位）→ total < 3。"""
    text = text.replace("那罕", "术赤")
    text = text.replace("他", "此人")  # C2：归属位一并替换（「他」单独即 ≥3）
    return text


def transition_flooded(text: str) -> str:
    """narrative 段首注入计数面连接词（不过/此时/突然/终于/于是）。"""
    paras = text.split("\n\n")
    out = []
    i = 0
    for p in paras:
        s = p.strip()
        if s and not s.startswith(("#", ">", "---", "- [", "<!--")):
            out.append(_TRANSITION_FILLERS[i % len(_TRANSITION_FILLERS)] + p)
            i += 1
        else:
            out.append(p)
    return "\n\n".join(out)


MUTATIONS: dict[str, Callable[[str], str]] = {
    "hook_killed": hook_killed,
    "protagonist_vanished": protagonist_vanished,
    "transition_flooded": transition_flooded,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--mutation", required=True, choices=sorted(MUTATIONS))
    parser.add_argument("--full", action="store_true", help="不裁片（默认裁片 M4）")
    args = parser.parse_args()
    src = args.source.read_text(encoding="utf-8")
    mutated = MUTATIONS[args.mutation](src)
    note = (
        "全章（裁片不足以承载该变异——README 记裁定）"
        if args.full
        else "frontmatter + 叙事尾窗 (M4 裁片)"
    )
    if not args.full:
        mutated = excerpt_tail(mutated)
    header = PROVENANCE_TMPL.format(
        source=str(args.source),
        name=args.mutation,
        excerpt_note=note,
        today=date.today().isoformat(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(header + mutated, encoding="utf-8")
    print(f"{args.out} <- {args.source} [{args.mutation}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**裁片×变异顺序**：变异先作用全文、再 `excerpt_tail` 裁片——hook/transition 变异落点恰在尾窗；protagonist 变异影响全文计数，若裁片后残留计数仍 ≥3（前文未进裁片即无所谓——裁片即全文的可判面：`g4_chapter_drafting` 只见裁片文本，计数=裁片内计数）——**protagonist/transition 默认 `--full` 生成**（裁片截断会破坏「全章计数」语义），hook 默认裁片；README 记此裁定。

- [ ] **Step 4: 维护者侧生成 fixture（含 C2 前置物）**

```bash
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-hook-killed.md --mutation hook_killed
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-protagonist-vanished.md --mutation protagonist_vanished --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-transition-flooded.md --mutation transition_flooded --full
```

`tests/fixtures/gate-power/characters/protagonist.md` 手工落盘（C2：`_load_protagonist_names` 非 SKIP 前提）：

```markdown
---
provenance: real-output-derivative (G0.9)
source: novel-xinghuo-vol1/characters/protagonist.md name 行
---
name: 那罕
```

**红测必须真实红三查**（每 fixture 生成后逐个执行并贴输出）：
1. hook：g4 于 fixture → must_fix 含 `G4.cd.no_hook`；若仍 PASS＝裁片后窗口 <30 CJK → `--full` 重生成（记裁定）
2. protagonist：must_fix 含 `G4.cd.protagonist_absent`（SKIP＝characters/ 前置物未落；PASS＝裁片内残留计数——`--full`）
3. transition：`uv run python -c "from shenbi.gates.shared import count_transition_words, strip_narrative_body; print(count_transition_words(strip_narrative_body(open('<fixture>').read())))"` → 计数 > max(5, wc//1000)（I5：先验计数面，不猜）

只读验证：生成前后 `find novel-xinghuo-vol1 -newermt "$(date -v-1M '+%Y-%m-%d %H:%M:%S')" | wc -l` 一致。写 `tests/fixtures/gate-power/README.md`：来源/算子/再生成命令/裁片与 `--full` 裁定说明＋**公开 repo 内容政策声明（M4/I7）**——「本 repo 为 public；变异 fixture 为真实章（frontmatter＋被测窗或全章，逐 fixture 注明）的确定性变换，不脱敏——对齐 `tests/fixtures/` 既有 vol1 衍生先例（cross-chapter-regression 等）；若用户裁定需脱敏，后续批占位符替换非被测文本再生成（本 README 即该出口的登记位）」。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add tools/gen_gate_power_fixtures.py tests/fixtures/gate-power/ tests/unit/gates/g4/test_gate_power_negatives.py
git commit -m "test: spec #116 T4 变异引擎+hook/protagonist/transition 真实章负例红测（验收5最低子集）"
```

---

### Task 3: 其余 in-scope 门变异负例全覆盖

**Files:**
- Modify: `tools/gen_gate_power_fixtures.py`（MUTATIONS 扩展）
- Create: `tests/fixtures/gate-power/`（下表每变异一 fixture＋前置物：`plans/chapter-1-plan.md`（v4 memo——voice_density/scene_hook/quote_verbatim/hook_type_rotation 消费）、`project-output/chapters/chapter-0.md`＋被测 `chapter-1-duplicated.md` 本体入驻同目录（I3：`_check_content_uniqueness` 基数门槛 `len(project-output/chapters/*.md) > 1`——被测章＋比对章共 2 文件，glob 排除自身后与 chapter-0 比对；红测的 `_g4("project-output/chapters/chapter-1-duplicated.md")` 传 FIX_DIR 为 rd））
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（追加）

**Interfaces:**
- Consumes: Task 2 `MUTATIONS`/`_g4`/`--full`；Task 1 `narrative_window`
- Produces: 覆盖矩阵（Task 4 CHECK_REGISTRY `t4_evidence` 列引用测试名）

**plans fixture**（v4 形：`plan_format: v4`＋『』锚定引句＋voice_density 声口要求行＋场景钩声明——先 grep `_check_scene_hook`（:1070）与 `voice_density_min`（:1403）实际读取行形再落盘；provenance 头注明衍生自真实 plan 的行形）。

**FAIL 组变异规格**（确定性变换→期望 mf id；行号已核）：

| mutation | 变换 | 期望 mf id | 前置物 |
|---|---|---|---|
| `scene_visuals_stripped` | 尾窗段视觉动词/对白删（→静态陈述） | `G4.cd.no_visual_scene`（:1149） | — |
| `scene_markers_removed` | 删场景标记行 | `G4.cd.scene_count:…<2`（:1058） | **默认 `--full`**（NB6 同因） |
| `fatigue_flooded` | narrative 段尾追加「他心中暗道。」×9 | `G4.fatigue:…>8`（:997，阈值 8） | —（实词 grep `_fatigue_word_list` :968-989 核对，避开 #93 erratum 子串碰撞） |
| `meta_injected` | 插入「由此可见：这一切早有注定。」＋「综上所述」段 | `G4.meta:…`（:1022；载荷取 META_NARRATIVE 7 词闭集——I1） | — |
| `word_count_truncated` | 正文截断至 <带下限 | `G4.word_count`（mf 形态 grep :1027-1052） | —（带值 grep genre-config word_band） |
| `post_removed` | 删 META 块（含 POST） | `G4.post_check:…`（:911） | **默认 `--full`**（NB6：裁片本身不含 POST——裁片模式红来自副作用非变异；README 注因果） |
| `pre_removed` | 删 `## PRE_WRITE_CHECK` 段 | `G4.pre_check:…`（:902） | **默认 `--full`**（同 NB6） |
| `voice_stripped` | 口癖短语（这笔我先记下/折旧完了/此账必有还之日/行，先算账）→中性语 | `G4.cd.voice_density:…` | `plans/chapter-1-plan.md` v2+（memo_v2 声口要求行——:1410/:1397-1424；实弹 14/50 已 FAIL，变异证下界） |
| `hookdecl_mismatched` | plan 场景钩声明改「悬念」vs 章尾实拍 | `G4.cd.scene_hook_match:…`（:1077） | plans fixture 钩声明行（grep :717-722 读取形） |
| `post_quote_broken` | POST 引句改一字 | mf 组合形（grep `_pq_id` 邻 :884-910） | — |
| `post_transition_lied` | POST 转折申报与正文不符 | mf 组合形（:956 邻 `_ptc_id`） | — |
| `content_duplicated` | **从 chapter-0 复制段落 append 至章尾**、段数按 `k/(m+k) > 0.40` 指纹占比取（实现时按 fixture 实际段数 m 计算 k，先跑三查验证） | `G4.cd.content_overlap:…`（:1104） | 被测章落 `project-output/chapters/chapter-1-duplicated.md`＋比对章 `chapter-0.md` 同目录（I3：跨章＋集合指纹＋基数门槛 len>1 三条件齐；复制段必须 append 章尾否则被裁片截掉） |

**WARN-only 组（负例=断言 check 行 s==WARN；surge/post_wordcount 实勘无 mf 臂）**：`surge_killed`（长句切短→`G4.cd.surge` WARN——:1261-1288）、`simile_flooded`（堆比喻 per_1000>4→`G4.cd.simile_band` WARN）、`golden_emptied`（金句位值→无→WARN）、`post_wordcount_lied`（POST 实际字数改半→`cd.post_wordcount_precision` WARN——I2）、`ending_repeated`（helper 级：`ending_archetype_of` 三连续同型断言——fixture 两前置章＋被测章）。

**helper 级红测**（需 truth/历史上下文，调公共函数；构造性输入 inline）：

| gate | 调用（实签名） | 期望 |
|---|---|---|
| prop_handoff | `check_prop_handoffs(text, memo_text, props, known_names=None, owner_aliases=None)`（:149） | 声明交接而 prose 无交接语境 → issue 含 `cd.prop_handoff` |
| counter 家族 | `check_counter_reconciliation(text, memo_text, counters, *, fp="")`（:255） | plan/prose 数值矛盾 → issue |
| balance | 实勘：facts oracle 缺席即 WARN skip（:642-656/:773-781）——红测断言 SKIP 路径＋登记「负例=附录 A 实弹 7 FAIL 已证」 | SKIP 路径断言 |
| quote_verbatim | 全管线：plans fixture `plan_format: v4`＋缺『』锚定 | `G4.cd.quote_verbatim:…`（:1195-1206） |
| hook_type_rotation | 全管线：`declared_history(project_dir)` 需 hooks 历史——fixture 目录落最小 hooks 台账（grep :555-569 读取形后构造）＋两章同钩型 | `G4.cd.hook_type_rotation:…`（:577-582） |

- [ ] **Step 1: 逐门 grep 实锚**（每变异：消息形态/读取行形 grep 输出贴 task report——先验自检如实）
- [ ] **Step 2: 每变异=失败测试→生成 fixture＋前置物→红测转绿**（Task 2 循环复用；每 4-5 个一组 commit；**红测必须真实红检查同 Task 2 Step 4 三查**）
- [ ] **Step 3: 全量跑**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: 全 PASS（预计 20+ 用例）

- [ ] **Step 4: Commit（分组）**

```bash
git add tools/gen_gate_power_fixtures.py tests/fixtures/gate-power/ tests/unit/gates/g4/test_gate_power_negatives.py
git commit -m "test: spec #116 T4 全门变异负例覆盖（散文面+声明面+WARN-only 触发）"
```

---

### Task 4: 恒真登记＋哨兵 lint `tools/lint_gate_power_baseline.py`

**Files:**
- Create: `tools/lint_gate_power_baseline.py`
- Create: `docs/framework/gate-power-baseline.md`
- Modify: `justfile`（`lint:` 配方内 `lint_invariant_coverage` 行后加一行）
- Modify: `docs/framework/invariants.md`（门检列段加分工声明）
- Test: `tests/unit/tools/test_lint_gate_power_baseline.py`

**Interfaces:**
- Consumes: Task 1 `ARM_TO_CANONICAL`/口径常量（registry 与之同源对齐——M3；import 防双源漂移）；Task 2/3 红测名（evidence 列）；#88 `tests/fixtures/g4-id-inventory.json` **仅交叉参考**（C4：不作集合等式一源）
- Produces: 退出码契约 0=绿／1=FAIL（registry↔AST 漂移、baseline 行缺/多、分类值域外、非 discriminating 缺证据、ESCALATION_DATE 后 unclassified-0-点火）；WARN 级=stderr 行＋exit 0；`CHECK_REGISTRY: dict[str, dict]`（canonical→{fail_arms, warn_only, 口径}）

- [ ] **Step 1: 写失败测试**

```python
"""Spec #116 T2: vacuity registry sentinel lint tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import tools.lint_gate_power_baseline as lint

HEADER = (
    "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _write_baseline(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "gate-power-baseline.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_registry_matches_static_sources() -> None:
    """C4 修订：registry∪arms == chapter_drafting.py 单文件扫描 ∪ 显式补充。"""
    drift = lint.registry_drift()
    assert drift == [], drift


def test_missing_baseline_row_is_fail(tmp_path: Path) -> None:
    p = _write_baseline(tmp_path, HEADER)
    assert lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=True) == 1


def test_unclassified_zero_firing_warns_before_escalation(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    rc = lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=False)
    assert rc == 0  # WARN 级：exit 0


def test_unclassified_zero_firing_fails_after_escalation(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    assert lint.lint_file(p, today=lint.ESCALATION_DATE, require_full_registry=False) == 1


def test_decorative_without_evidence_fails(tmp_path: Path) -> None:
    body = HEADER + (
        "| `G4.cd.meta` | state-free | 0% | decorative |  | 50 章 @ d (r) 0 点火 | — |\n"
    )
    p = _write_baseline(tmp_path, body)
    assert lint.lint_file(p, today=lint.PRE_ESCALATION, require_full_registry=False) == 1


def test_classification_vocab_closed() -> None:
    assert lint.VALID_CLASSIFICATIONS == frozenset(
        {"unclassified", "floor-untested", "decorative", "discriminating", "retired"}
    )


def test_escalation_anchor_documented() -> None:
    """M1：升格锚=回填日+30 天（2026-11-19+30），模块常量注释与 baseline 头节同时声明。"""
    assert lint.ESCALATION_DATE == date(2026, 12, 19)
    assert lint.PRE_ESCALATION == date(2026, 11, 19)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_lint_gate_power_baseline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 lint＋registry＋baseline 骨架**

`registry_drift()`（C4 修订）：对 `src/shenbi/gates/g4/chapter_drafting.py` **单文件**双扫描——(a) `re.findall(r'"id":\s*"(G4\.[a-zA-Z0-9_.]+)"', src)`（check 行 dict id）∪ (b) `re.findall(r'(?:mf|c)\.(?:append|extend)\(\s*f"(G4\.[a-zA-Z0-9_.]+):', src)`（mf 首常量 id）；**前缀归一**：扫描产出统一剥 `G4.` 前缀后与裸形 registry 比较。**显式补充面（NB4 预列，免 drift 测试烧实现者一轮）**：`EXPLICIT_SUPPLEMENT`（扫描不可见的组合/变量发射臂）= `{cd.protagonist_absent, cd.prop_handoff, cd.counter, cd.counter.plan_conflict, cd.counter.base_mismatch, cd.counter.prose_mismatch, cd.balance_value_drift, cd.balance_value_drift.bundle, cd.post_quote_verbatim, cd.post_transition_cross}`；`SCAN_EXCLUDE`（非检查的错误/杂臂）= `{file_not_found}`；扫描侧多出的 `cd.quote_type`/`cd.micro_hook_run` **进 registry 行**（真实 in-scope 检查——micro_hook_run 需 memo_v3，回放面记 SKIP；quote_type 为引号型检查行）。两侧集合相等（多=未登记→FAIL；少=死键→FAIL）。**不**读 g4-id-inventory.json 作等式源（含 character_design 交叉污染且缺 protagonist_absent——C4 实证）；存在时打印交叉参考 diff 到 stderr（信息行，不执法）。

`ESCALATION_DATE = date(2026, 12, 19)`（注释：锚=baseline 回填日 2026-11-19＋30 天=一个完整裁定周期，spec r2/I5「分类义务清偿后」以该日历日近似；若 Task 5 实跑日晚于 11-19，按「实跑日＋30 天」改此常量并在 task report 记录）。`PRE_ESCALATION = date(2026, 11, 19)`。

`lint_file(path, today, require_full_registry=True)`：解析 baseline 表——`require_full_registry` 时行集==registry canonical 集；分类值域 `VALID_CLASSIFICATIONS`；非 discriminating 行证据列非空（`—` 仅 unclassified 允许，unclassified 证据列允许填红测链接供裁定参考）；unclassified 且「最近回放数」列含 `0 点火`：today≥ESCALATION_DATE → exit 1，否则 stderr WARN＋exit 0。

`CHECK_REGISTRY` 骨架（18 逻辑行=附录 A 全行＋content_uniqueness/quote_type/micro_hook_run 附录外行（NB4：后两者为扫描侧真实 in-scope 检查，回放面记 SKIP/0 观测）；canonical 集=STATE_FREE_IDS∪TRUTH_DEPENDENT_IDS（import Task 1 常量）；fail_arms=ARM_TO_CANONICAL 反转＋EXPLICIT_SUPPLEMENT 归并；warn_only=True：surge/simile_band/golden_slot/ending_diversity/post_wordcount_precision/post_quote_verbatim）。

`docs/framework/gate-power-baseline.md` 骨架：头节（义务声明＋口径定义＋分类四值语义＋「分类必须人工裁定」＋升格锚声明「2026-11-19 回填＋30 天→2026-12-19」）＋全 registry 行表（分类全 `unclassified`、最近回放数 `—`——Task 5 回填；hook/protagonist/transition 三行证据列填 Task 2 红测路径）。

`justfile` `lint:` 内 `uv run python tools/lint_invariant_coverage.py` 行后加 `uv run python tools/lint_gate_power_baseline.py`。

`docs/framework/invariants.md` 门检列段加：「点火率/恒真分类登记见 `docs/framework/gate-power-baseline.md`（spec #116）——本表管不变量维度覆盖，彼表管判别力，check-id 对账由 `tools/lint_gate_power_baseline.py` 执行（分母=chapter_drafting.py AST 单源，非本表）」。

- [ ] **Step 4: 跑测试＋lint 本体冒烟**

Run: `uv run pytest tests/unit/tools/test_lint_gate_power_baseline.py -v && uv run python tools/lint_gate_power_baseline.py; echo "exit=$?"`
Expected: 测试全 PASS；lint 本体在骨架（全 unclassified＋回放数 `—`）下 exit 0（`—` 不触发 WARN——WARN 只对显式 `0 点火` 行；回填后进入 WARN 首态）

- [ ] **Step 5: Commit**

```bash
git add tools/lint_gate_power_baseline.py docs/framework/gate-power-baseline.md docs/framework/invariants.md justfile tests/unit/tools/test_lint_gate_power_baseline.py
git commit -m "feat: spec #116 T2 恒真登记+哨兵 lint（单文件 AST registry+分类证据义务+升格日期锚）"
```

---

### Task 5: 标定提案文档＋50 章回放回填

**Files:**
- Create: `docs/framework/gate-calibration-proposals.md`
- Create: `reports/2026-11-19-gate-power-vol1.md`（Task 1 工具实跑产物）
- Modify: `docs/framework/gate-power-baseline.md`（「最近回放数」列回填）
- Modify: `tools/lint_gate_power_baseline.py`（仅当 Step 3 校正升格锚时）

**Interfaces:**
- Consumes: Task 1 `just gate-power`；Task 2/3 红测；附录 A＋两份 Goodhart 报告数字
- Produces: 提案文档（用户裁定入口）；baseline 回填后哨兵进入 WARN 首态

- [ ] **Step 1: 维护者侧 50 章回放（验收 2 实跑）**

Run: `uv run python tools/gate_power_replay.py novel-xinghuo-vol1 --out reports/2026-11-19-gate-power-vol1.md`
Expected: 报告数字与附录 A 一致（10 散文门 50/50、voice_density FAIL=14、prop_handoff=11、simile WARN=28、ending None=47）；命令与输出摘录贴 progress.md `## 验收证据`

- [ ] **Step 2: 写提案文档**（七项×四栏；每项现状数字必须来自 Task 1 报告/附录 A/两 Goodhart 报告——逐项带数字，禁空泛）

结构：每项 `### <门名>`＋四栏表（现状（数字）/提案（≥1 具体选项）/红测（指向 Task 2/3 测试或「落地批补」）/回滚（单 commit 条件））；voice_density 首项（vol1 14/50 must_fix＋Goodhart r2 15/18——阈值重标定或「逐字口癖在场」与「密度下限」两级拆分）；hook（15/50 单字-only＋`还`=38/`账`=38 与账房腔同词表——多字/结构臂或词表不相交）；protagonist（中位 93 vs 阈值 3＋名字表重复 `:495`/`:508`——去重＋重标定）；transition（中位 0 vs 阈值 5——retire 或重标定；化合物 3 次负结果）；scene_concreteness/surge/fatigue/meta（逐项分类＋负例链接）；simile（56% WARN——路由/降报告行）；ending archetype（47/50 None——扩分类器或退役哨兵）。

- [ ] **Step 3: baseline 回填**

「最近回放数」列填 `50 章 @ 2026-11-19（reports/2026-11-19-gate-power-vol1.md）`＋0 点火行加 `0 点火` 标记；Run: `uv run python tools/lint_gate_power_baseline.py; echo exit=$?` → exit 0＋stderr 多行 WARN（首态设计内——分类待用户裁定）；输出贴 task report。**升格锚校正**：若本 Step 实跑日≠2026-11-19，同步改 lint `ESCALATION_DATE` 注释与 baseline 头节锚声明（M1）。

- [ ] **Step 4: 全量验收（AC1 实跑=M4 修订）**

Run: `just check`
Expected: 全绿（含新 lint 行；哨兵 WARN 行在 stderr 不影响 exit 0）

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py tests/unit/tools/test_lint_gate_power_baseline.py tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add docs/framework/gate-calibration-proposals.md reports/2026-11-19-gate-power-vol1.md docs/framework/gate-power-baseline.md tools/lint_gate_power_baseline.py
git commit -m "docs: spec #116 T3 七项标定提案+T1/T2 50 章回放回填（哨兵进入 WARN 首态）"
```

---

## AC 覆盖表

| spec 验收 | task | 证据 |
|---|---|---|
| 1. T1-T4 判据全绿 | 1-5 | 各 task 测试＋Task 5 Step 4 `just check` |
| 2. gate-power 50 章可复现＋双口径＋simile 对照列 | 1（实现）＋5（实跑） | reports/2026-11-19-gate-power-vol1.md |
| 3. 登记覆盖分母＋WARN 哨兵＋升格判据测试 | 4 | test_lint_gate_power_baseline.py（7 用例含升格/证据义务/分母漂移） |
| 4. 七项提案＋回滚条件交裁 | 5 | gate-calibration-proposals.md |
| 5. hook/protagonist/transition 三项真实章可捕获 | 2 | test_gate_power_negatives.py 首三测 |

## 复杂度/test_kind 总表

| task | 复杂度 | test_kind | 层级 |
|---|---|---|---|
| 1 回放仪表 | leaf（tools/ 单文件，非 infra 模块） | tdd_red_green | T1 |
| 2 变异引擎＋三红测 | leaf | tdd_red_green（负例=红即 FAIL 证明） | T1 |
| 3 全门覆盖 | leaf（大；逐门 grep 实锚后小步循环） | regression_guard（红测钉住「能失败」） | T1 |
| 4 登记＋哨兵 | leaf | tdd_red_green | T1 |
| 5 提案＋回填 | leaf（docs 为主） | characterization（报告数字对齐附录 A） | T1 |
