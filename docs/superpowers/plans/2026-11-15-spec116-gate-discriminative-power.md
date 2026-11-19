# Spec #116 门禁判别力仪表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 G4 确定性门禁建判别力仪表——离线回放工具＋恒真登记＋WARN→FAIL 哨兵＋七项标定提案＋真实章变异负例红测，全程不改任何门行为。

**Architecture:** 四件新增（tools/ 三脚本＋docs/ 两文档＋fixtures/ 变异负例）＋两处既有文件小改（justfile 配方、invariants.md 分工行）。回放工具克隆 `tools/replay_severity_vocab.py` 形态（argparse＋`--out`＋只读）；登记 lint 持 CHECK_REGISTRY 单源（AST 双源校验防漂移）；哨兵只读已提交 baseline 文档（CI 无语料依赖）；变异器维护者侧生成裁片 fixture（G0.9 provenance 头）。

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

---

### Task 1: 回放仪表 `tools/gate_power_replay.py` ＋ `just gate-power`

**Files:**
- Create: `tools/gate_power_replay.py`
- Modify: `justfile`（新配方 `gate-power`，置于 `lint:` 配方之后独立段落）
- Test: `tests/unit/tools/test_gate_power_replay.py`

**Interfaces:**
- Consumes: `shenbi.gates.g4.chapter_drafting.g4_chapter_drafting(fps: list[str], rd: str | None, project_dir: str | None, repo_root: str | None) -> str`（JSON：`{blocked_action, checks, gate, must_fix, status, timestamp}`；check 行 `{id, file, s, ...}`，s ∈ PASS/WARN/FAIL/SKIP 字符串）；`shenbi.gates.shared.count_transition_words(content: str) -> int`（shared.py:914）；`shenbi.gates.shared.strip_narrative_body(content: str) -> str`（shared.py:398）；`shenbi.gates.shared.count_similes(content: str) -> dict[str, Any]`（shared.py:449）；`shenbi.gates.g4.chapter_drafting.ending_archetype_of(text: str) -> str | None`
- Produces（Task 4/5 消费）:
  - CLI：`uv run python tools/gate_power_replay.py PROJECT_DIR [--out PATH] [--pattern "chapter-*.md"] [--state-free-only]` → markdown 报告（同输入同输出，timestamp 字段不入报告）
  - 模块级函数（Task 1 自测与 Task 5 复用）：`collect(project_dir: Path, pattern: str) -> list[dict]`（逐章聚合行）、`summarise(rows: list[dict]) -> dict[str, dict]`（per-check PASS/WARN/FAIL/SKIP 计数＋firing_rate）、`HOOK_TENSION_RE`/`SINGLE_CHAR_TENSION`/`STATE_FREE_IDS`/`TRUTH_DEPENDENT_IDS` 常量

- [ ] **Step 1: 写失败测试**（`tests/unit/tools/test_gate_power_replay.py`）

```python
"""Spec #116 T1: gate-power replay tool unit tests (structural inputs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gate_power_replay import (
    STATE_FREE_IDS,
    TRUTH_DEPENDENT_IDS,
    collect,
    summarise,
)

# 结构性合成章（AGENTS.md 允许：tmp_path 内联合法，非 fixture 冒充技能产物）
CH_WITH_HOOK = """---
name: 测试章
---

## 第一章　测试

他推开门，看见院子里堆着柴。她还站在原地没动。

「你还欠着账。」他说。

门外的风吹进来，烛火晃了一下。到底谁在撒谎？41 人失踪，82 户报官。

<!-- PRE
- 本章字数: 200
-->

<!-- POST
- [x] 自检完成: 是
- [x] 实际字数: 200
-->
"""


def _mk_project(tmp_path: Path, chapters: dict[str, str]) -> Path:
    (tmp_path / "chapters").mkdir()
    for name, text in chapters.items():
        (tmp_path / "chapters" / name).write_text(text, encoding="utf-8")
    return tmp_path


class TestCollect:
    def test_collect_returns_per_chapter_rows(self, tmp_path: Path) -> None:
        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        rows = collect(rd, "chapter-*.md")
        assert len(rows) == 1
        row = rows[0]
        assert row["file"] == "chapter-1.md"
        assert isinstance(row["checks"], list)  # g4 原始 check 行
        assert isinstance(row["must_fix"], list)

    def test_collect_skips_non_pure_chapter_files(self, tmp_path: Path) -> None:
        rd = _mk_project(
            tmp_path,
            {"chapter-1.md": CH_WITH_HOOK, "chapter-1-pre-rev.md": CH_WITH_HOOK},
        )
        rows = collect(rd, "chapter-*.md")
        assert [r["file"] for r in rows] == ["chapter-1.md"]


class TestSummarise:
    def test_counts_pass_warn_fail_per_check(self) -> None:
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
                    {"id": "G4.cd.voice_density", "s": "PASS"},
                ],
                "must_fix": [],
            },
        ]
        s = summarise(rows)
        assert s["G4.cd.chapter_end_hook"] == {"PASS": 2, "WARN": 0, "FAIL": 0, "SKIP": 0}
        # must_fix 行与 FAIL check 行同源去重（同章同 id 计 1 次 FAIL）
        assert s["G4.cd.voice_density"] == {"PASS": 1, "WARN": 0, "FAIL": 1, "SKIP": 0}

    def test_firing_rate(self) -> None:
        s = summarise(
            [
                {
                    "file": "chapter-1.md",
                    "checks": [{"id": "X", "s": "PASS"}],
                    "must_fix": [],
                },
                {
                    "file": "chapter-2.md",
                    "checks": [{"id": "X", "s": "FAIL"}],
                    "must_fix": ["X:c2:m"],
                },
            ]
        )
        assert s["_firing"]["X"] == pytest.approx(0.5)


class TestCaliberSplit:
    def test_state_free_and_truth_sets_partition_appendix(self) -> None:
        # 附录 A 口径列锚（spec r2）：truth 依赖 = prop_handoff/balance 家族
        assert "G4.cd.prop_handoff" in TRUTH_DEPENDENT_IDS
        assert "cd.balance_value_drift" in TRUTH_DEPENDENT_IDS
        assert "G4.cd.chapter_end_hook" in STATE_FREE_IDS
        assert not (STATE_FREE_IDS & TRUTH_DEPENDENT_IDS)


class TestDeterminism:
    def test_same_input_same_report(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        r1 = gpr.render_report(rd, "chapter-*.md")
        r2 = gpr.render_report(rd, "chapter-*.md")
        assert r1 == r2  # timestamp 不入报告

    def test_no_write_into_project_dir(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        before = sorted(p.name for p in (rd / "chapters").iterdir())
        gpr.render_report(rd, "chapter-*.md")
        after = sorted(p.name for p in (rd / "chapters").iterdir())
        assert before == after
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.gate_power_replay'`

- [ ] **Step 3: 实现 `tools/gate_power_replay.py`**

克隆 `tools/replay_severity_vocab.py` 形态（shebang＋docstring 引用 spec＋argparse＋`--out`＋stderr 报告去向）。核心实现要点（完整写出，实现者照抄后微调）：

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
    count_similes,
    count_transition_words,
    strip_narrative_body,
)

# 附录 A 口径列（spec r2）：truth 依赖 = 读 truth/ledger 现值的对账家族
TRUTH_DEPENDENT_IDS = frozenset(
    {
        "G4.cd.prop_handoff",
        "cd.balance_value_drift",
        "cd.counter",
        "cd.counter.plan_conflict",
        "cd.counter.base_mismatch",
        "cd.counter.prose_mismatch",
        "cd.balance_value_drift.bundle",
    }
)
# state-free = 本章内容可判定（散文形态门）。分母全集由报告按「观测 id ∪ 已知清单」呈现。
STATE_FREE_IDS = frozenset(
    {
        "G4.pre_check",
        "G4.post_check",
        "G4.transition",
        "G4.fatigue",
        "G4.meta",
        "G4.word_count",
        "G4.cd.scene_count",
        "G4.cd.scene_hook_match",
        "G4.cd.scene_concreteness",
        "G4.cd.chapter_end_hook",
        "G4.cd.protagonist_presence",
        "G4.cd.surge",
        "G4.cd.simile_band",
        "G4.cd.voice_density",
        "G4.cd.golden_slot",
        "G4.cd.content_uniqueness",
        "G4.cd.hook_type_rotation",
        "G4.cd.quote_verbatim",
        "cd.post_quote_verbatim",
        "cd.post_transition_cross",
        "cd.post_wordcount_precision",
        "G4.cd.ending_diversity",
    }
)

# 归因再推导（锚：chapter_drafting.py _check_chapter_end_hook 窗口与三臂——
# 漂移由 Task 1 一致性测试对 fixture 章双向校验兜底）
HOOK_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)
SINGLE_CHAR_TENSION = frozenset("但却还仍瞒藏账欠谜")
_Q_RE = re.compile(r"[？?]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_SKIP_PREFIXES = ("#", "##", ">", "---", "- [ ]")


def _pure_chapter(stem: str) -> bool:
    return re.fullmatch(r"chapter-\d+", stem) is not None


def hook_window_attribution(content: str) -> dict[str, object]:
    """Re-derive the end-hook window arms (diagnostic only, gate verdict 不变)."""
    paras = [p for p in content.split("\n\n") if p.strip()]
    window = [p for p in paras[-8:] if not p.startswith(_SKIP_PREFIXES)]
    text = "".join(window)
    has_q = bool(_Q_RE.search(text))
    hits = set(HOOK_TENSION_RE.findall(text))
    multi = sorted(hits - SINGLE_CHAR_TENSION)
    singles = sorted(hits & SINGLE_CHAR_TENSION)
    has_ledger = len(re.findall(r"\d+", text)) >= 2
    single_only = (not has_q) and (not has_ledger) and singles and not multi
    return {
        "window_cjk": len(_CJK_RE.findall(text)),
        "has_q": has_q,
        "multi": multi,
        "singles": singles,
        "has_ledger": has_ledger,
        "single_char_only": single_only,
    }


def collect(project_dir: Path, pattern: str = "chapter-*.md") -> list[dict]:
    chapters = sorted(p for p in (project_dir / "chapters").glob(pattern) if _pure_chapter(p.stem))
    fps = [str(p) for p in chapters]
    rows: list[dict] = []
    # 逐章调用（窗口检查读 project_dir 兄弟章，批调与单章调用等价）
    for fp, name in zip(fps, (p.name for p in chapters), strict=True):
        res = json.loads(
            g4_chapter_drafting([fp], str(project_dir), str(project_dir), repo_root=None)
        )
        rows.append({"file": name, "checks": res["checks"], "must_fix": res["must_fix"]})
    return rows
```

`summarise(rows)`：per id 聚合 `checks` 行的 s 计数；must_fix 行的 id（`G4.xxx` 前缀到第一个 `:`）若该章该 id 无 FAIL check 行则计 FAIL（去重同章同 id）；输出 `_firing[id] = FAIL/WARN 非 0 章数 / 总章数`。`render_report(project_dir, pattern)`：组装 markdown——头部（项目/章数/日期由 `--out` 侧写入，报告体本身无时间戳）、per-check 表（id｜口径｜PASS｜WARN｜FAIL｜SKIP｜firing rate）、归因节（hook 单字-only 章数与 `还`/`账` 命中章数、protagonist 名字表与总数中位/最小——名字表从 `characters/protagonist.md` frontmatter `name:` 再推导＋`他`、transition 中位、ending None 计数、simile 双口径 `count_similes(content)` vs `count_similes(strip_narrative_body(content))` per-1000 均值）、`--state-free-only` 剔除 TRUTH_DEPENDENT_IDS 行并标注。`main()`：argparse 同 replay_severity_vocab（project_dir 位置参数＋`--out`＋`--pattern`＋`--state-free-only`），`--out` 时写文件＋stderr 打印去向，否则 stdout。

- [ ] **Step 4: justfile 配方**

在 `lint:` 配方定义之后（`type:` 之前）加：

```just
# Spec #116 T1: offline gate discriminative-power replay (zero LLM, read-only)
gate-power DIR *ARGS:
    uv run python tools/gate_power_replay.py {{DIR}} {{ARGS}}
```

- [ ] **Step 5: 跑测试确认通过＋一致性兜底测试**

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py -v`
Expected: PASS 全绿

追加一致性测试（同文件）：对 `tests/fixtures/chapter-9-draft.md`（真实产物 fixture）跑 `collect`，断言 hook 归因再推导与门 PASS 判定不矛盾（`chapter_end_hook` check 行为 PASS ⟺ 窗口三臂任一命中——若 fixture 章窗口 <30 CJK 则该断言跳过）：

```python
def test_hook_attribution_consistent_with_gate_verdict() -> None:
    from pathlib import Path
    from tools.gate_power_replay import collect, hook_window_attribution

    fixture = Path("tests/fixtures/chapter-9-draft.md")
    rows = collect(fixture.parent, "chapter-9-draft.md")
    attr = hook_window_attribution(fixture.read_text(encoding="utf-8"))
    hook_rows = [c for r in rows for c in r["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
    if attr["window_cjk"] < 30:
        pytest.skip("window below 30-CJK mass — gate leaves window unchecked")
    if hook_rows:
        hit = attr["has_q"] or bool(attr["singles"] or attr["multi"]) or attr["has_ledger"]
        assert hook_rows[0]["s"] == ("PASS" if hit else "FAIL")
```

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py -v` → PASS

- [ ] **Step 6: 真实章冒烟（维护者侧，CI 外）**

Run: `uv run python tools/gate_power_replay.py novel-xinghuo-vol1 --out /tmp/gate-power-smoke.md && head -30 /tmp/gate-power-smoke.md`
Expected: 报告生成；`G4.cd.chapter_end_hook` 50 PASS；`G4.cd.voice_density` FAIL=14；不写 `novel-xinghuo-vol1/` 任何文件（`git status novel-xinghuo-vol1` 无变化——gitignored，用 `find novel-xinghuo-vol1 -newer /tmp/gate-power-smoke.md | wc -l` 验证为 0）

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
- Create: `tests/fixtures/gate-power/README.md`（provenance 说明：来源章/变异算子/再生成命令）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`

**Interfaces:**
- Consumes: Task 1 无依赖；源章 = 维护者盘上 `novel-xinghuo-vol1/chapters/chapter-1.md`（生成时一次性读，产物提交后 CI 不再需要源）
- Produces（Task 3/4 消费）: CLI `uv run python tools/gen_gate_power_fixtures.py SOURCE CHAPTER_OUT --mutation NAME`；mutation 名注册表 `MUTATIONS: dict[str, Callable[[str], str]]`（Task 3 扩展同注册表）；fixture 头部格式（G0.9 provenance）：

```markdown
<!--
provenance: real-output-mutation (G0.9)
source: novel-xinghuo-vol1/chapters/chapter-1.md (章 1, 2026-10 产物, gitignored 项目)
mutation: hook_killed (tools/gen_gate_power_fixtures.py, spec #116 T4)
generated: 2026-11-19 (维护者侧一次性生成; 确定性: 同源同输出)
-->
```

- [ ] **Step 1: 写失败测试**（`tests/unit/gates/g4/test_gate_power_negatives.py`）

```python
"""Spec #116 T4: real-chapter mutation → gate FAIL red tests (prose face)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX_DIR = Path("tests/fixtures/gate-power")


def _g4(fixture_name: str) -> dict:
    fp = str(FIX_DIR / fixture_name)
    return json.loads(
        __import__(
            "shenbi.gates.g4.chapter_drafting", fromlist=["g4_chapter_drafting"]
        ).g4_chapter_drafting([fp], str(FIX_DIR), str(FIX_DIR), repo_root=None)
    )


def test_hook_killed_real_chapter_fails_hook_gate() -> None:
    """真实章变异→FAIL：章尾窗口张力全部抹除（spec 验收 5 最低子集之一）。"""
    res = _g4("chapter-1-hook-killed.md")
    assert any(m.startswith("G4.cd.no_hook:") for m in res["must_fix"]), res["must_fix"][:3]


def test_protagonist_vanished_real_chapter_fails_presence_gate() -> None:
    res = _g4("chapter-1-protagonist-vanished.md")
    # 名字全换＋「他」密度降到阈值下 → cd.major_chars/minor_chars 族 must_fix
    assert any(
        m.startswith(("G4.cd.major_chars:", "G4.cd.minor_chars:", "G4.cd.micro_hook_run:"))
        for m in res["must_fix"]
    ), res["must_fix"][:3]


def test_transition_flooded_real_chapter_fails_transition_gate() -> None:
    res = _g4("chapter-1-transition-flooded.md")
    assert any(m.startswith("G4.transition:") for m in res["must_fix"]), res["must_fix"][:3]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: FAIL with `FileNotFoundError`（fixture 未生成）

- [ ] **Step 3: 实现变异引擎 `tools/gen_gate_power_fixtures.py`**

```python
#!/usr/bin/env python3
"""Spec #116 T4: deterministic real-chapter mutator → negative-example fixtures.

维护者侧一次性运行（源=gitignored 项目章）；产物提交 tests/fixtures/gate-power/。
确定性：同源同输出（无 RNG）；裁片=保留 frontmatter＋被测窗口±3 段（M4 入库边界）。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

PROVENANCE_TMPL = (
    "<!--\nprovenance: real-output-mutation (G0.9)\n"
    "source: {source} (gitignored 项目真实产物)\n"
    "mutation: {name} (tools/gen_gate_power_fixtures.py, spec #116 T4)\n"
    "generated: {today} (维护者侧一次性; 确定性: 同源同输出)\n-->\n\n"
)

_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)


def hook_killed(text: str) -> str:
    """章尾窗口（末 8 段）张力词→中性字、删？与数字串 → no_hook。"""
    paras = [p for p in text.split("\n\n") if p.strip()]
    head, tail = paras[:-8], paras[-8:]
    out = []
    for p in tail:
        p = _TENSION_RE.sub("就", p)
        p = re.sub(r"[？?]", "。", p)
        p = re.sub(r"\d+", "数", p)
        out.append(p)
    return "\n\n".join(head + out)


def protagonist_vanished(text: str) -> str:
    """主角名→「术赤」、代词「他」→「此人」（降密度到阈值下）。"""
    text = text.replace("那罕", "术赤")
    text = re.sub(r"(?<![])」])他(?!们)", "此人", text)
    return text


def transition_flooded(text: str) -> str:
    """段首注入转折连接词 → transition 密度超 max(5, wc//1000)。"""
    paras = [p for p in text.split("\n\n") if p.strip()]
    fillers = ["然而，", "但是，", "不过，", "于是，", "因此，"]
    out = []
    for i, p in enumerate(paras):
        if not p.startswith(("#", "##", ">", "---", "- [ ]", "<!--")):
            out.append(fillers[i % len(fillers)] + p)
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
    args = parser.parse_args()
    src = args.source.read_text(encoding="utf-8")
    mutated = MUTATIONS[args.mutation](src)
    header = PROVENANCE_TMPL.format(
        source=str(args.source), name=args.mutation, today=date.today().isoformat()
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(header + mutated, encoding="utf-8")
    print(f"{args.out} <- {args.source} [{args.mutation}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 维护者侧生成三 fixture（实跑命令记录进 audit）**

```bash
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-hook-killed.md --mutation hook_killed
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-protagonist-vanished.md --mutation protagonist_vanished
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-transition-flooded.md --mutation transition_flooded
```

验证只读：`find novel-xinghuo-vol1 -newermt "$(date -v-1M '+%Y-%m-%d %H:%M:%S')" | wc -l` 与生成前一致（mtime 不变）；生成后逐个检查 fixture 头部 provenance 六要素齐全。写 `tests/fixtures/gate-power/README.md`（来源/算子/再生成命令/为何裁片合规）。

**公开 repo 内容政策声明（M4 残余收口，随 PR 交用户过目）**：本 repo 为 public；变异 fixture 为真实章裁片的确定性变换产物（frontmatter＋被测窗口段），不脱敏——理由：`tests/fixtures/` 已有大量 vol1 原文衍生先例（cross-chapter-regression 等），本批不改变既有边界；若用户裁定需脱敏，后续批以占位符替换非被测文本再生成（README 记此出口）。

注意：transition 阈值=`max(5, wc//1000)`——chapter-1 正文约 3,000+ 字 → 阈值≥5；注入≥8 个连接词必超。若实跑红测仍 PASS（如 narrative 剥离后连接词被 strip_narrative_body 排除），实现者须检查注入位置在 narrative 段（非 PRE/POST 块内），调整 filler 注入为段首而非块内——红测必须真实红。

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
- Modify: `tools/gen_gate_power_fixtures.py`（MUTATIONS 注册表扩展）
- Create: `tests/fixtures/gate-power/`（下列每变异一个 fixture；全部同一源章 chapter-1.md 除注明）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（追加）

**Interfaces:**
- Consumes: Task 2 `MUTATIONS` 注册表与 `_g4` 测试助手
- Produces: 覆盖矩阵（登记 lint Task 4 的 CHECK_REGISTRY `t4_evidence` 列引用这些测试名）

**变异规格**（每项=确定性变换→期望 must_fix id；实现进 MUTATIONS）：

| mutation | 变换 | 期望 FAIL id | 备注 |
|---|---|---|---|
| `scene_visuals_stripped` | 窗口段视觉动词/对白删除（换为静态陈述） | `G4.cd.no_visual_scene`（mf :1149 已钉） | 全管线 |
| `scene_markers_removed` | 删场景标记行 | `G4.cd.scene_count:…<2`（mf :1058 已钉） | 全管线 |
| `fatigue_flooded` | narrative 段尾追加「他心中暗道。」「他眸光一凝。」×9 | `G4.fatigue:…>8`（mf :997 阈值 8 已钉；FATIGUE 词表实锚 chapter_drafting.py `_fatigue_word_list`——实现时 grep 实词核对，避开 #93 erratum 子串碰撞教训） | 全管线 |
| `meta_injected` | 插入「作者按：本章说明…」段 | `G4.meta:…`（mf :1022 已钉） | 全管线 |
| `word_count_truncated` | 正文截断至 <带下限 | `G4.word_count`（mf 形态实现时 grep :1027-1052 段） | 全管线；带值 grep genre-config word_band |
| `post_removed` | 删 POST 块 | `G4.post_check:…`（mf :911 已钉） | 全管线 |
| `pre_removed` | 删 PRE 块 | `G4.pre_check:…`（mf :902 已钉） | 全管线 |
| `voice_stripped` | 口癖短语（这笔我先记下/折旧完了…）替换中性语 | `G4.cd.voice_density` | 已 14/50 实弹 FAIL——变异证明下界 |
| `hookdecl_mismatched` | memo/POST 钩声明改「悬念」vs 章尾实拍 | `G4.cd.scene_hook_match:…`（mf :1077 已钉） | 声明位 grep `_check_scene_hook`（:1070）读源 |
| `post_wordcount_lied` | POST 实际字数改半 | `G4.cd.post_wordcount_precision`（mf 组合形 `G4.{_ptc_id}` 邻 :940 段；check 行 id `cd.post_wordcount_precision` WARN） | 全管线 |
| `post_quote_broken` | POST 引句改一字 | `G4.cd.post_quote_verbatim`（同上组合形；check 行 WARN） | 全管线 |
| `post_transition_lied` | POST 转折数申报与正文不符 | `G4.cd.post_transition_cross`（mf :956 邻段组合形） | 全管线 |
| `content_duplicated` | 复制章内三段重复 | `G4.cd.content_overlap:…`（mf :1104 已钉） | 全管线 |

**WARN-only 组（负例=触发 WARN，非 FAIL；surge 实勘为 WARN-only——`_check_surge` :1261-1288 无 mf 路径）**：`surge_killed`（长句切短 → surge WARN）、`simile_flooded`（堆比喻 per_1000>4 → simile WARN）、`golden_emptied`（金句位值→无 → golden WARN）、`ending_repeated`（helper 级调 `ending_archetype_of` 断言三连续同型存在）。与 `G4.cd.simile_band`/`G4.cd.ending_diversity`/`G4.cd.surge`/`G4.cd.golden_slot` 一并进 Task 4 CHECK_REGISTRY `warn_only=True`。

**helper 级红测**（需 plan/truth 上下文，无法全管线——直接调公共检查函数，构造性输入 inline 允许）：

| gate | 调用 | 期望 |
|---|---|---|
| prop_handoff | `check_prop_handoffs(prose, plan_lines, prev…)→grep 签名 chapter_drafting.py:149` | 交接语境缺失 → issue 含 `cd.prop_handoff` |
| counter 家族 | `check_counter_reconciliation(...)→grep 签名 :255` | plan/prose 数值矛盾 → issue |
| balance | `check 逻辑在 `_check_balance_drift`（私有）——构造 CheckContext 不可行则改为：fixture 章「章首首现余额」值改错＋`_load_oracle` SKIP 时的 WARN 路径断言（先 grep 该函数依赖，若 truth oracle 缺席则 SKIP——此时 helper 级测 SKIP 路径＋登记「truth 依赖，负例=实弹 7 FAIL 已证」（附录 A），红测退为 SKIP 路径断言） | 见备注 |
| quote_verbatim | v4 memo 缺『』锚定形态 | `G4.cd.quote_verbatim`（全管线：fixture 章 memo 声明 `plan_format: v4`——先 grep memo 来源 `_check_chapter_end_hook` ctx.memo_text） |
| hook_type_rotation | 两 fixture 章同钩型 | `G4.cd.hook_type_rotation`（全管线：declared_history 读 project_dir——fixture 目录内两章＋历史声明，先 grep `declared_history`） |

**WARN-only 排除登记**（out-of-scope obs #2 裁定进 plan）：`G4.cd.simile_band`、`G4.cd.ending_diversity` 不做 FAIL 负例（代码无 must_fix 路径）——Task 4 CHECK_REGISTRY 标 `warn_only=True`，T4 义务记「WARN-only——负例=触发 WARN」，各加一条触发 WARN 的变异红测（`simile_flooded`：堆比喻到 per_1000>4；`ending_repeated`：三连续同型——helper 级调 `ending_archetype_of` 断言同型链存在即可）。

- [ ] **Step 1: 逐门 grep 实锚消息 id/签名**（实现者第一步；每个 grep 输出贴 task report——防「先验自检如实」复辙）
- [ ] **Step 2: 每变异=失败测试→生成 fixture→红测转绿**（Task 2 循环复用；每 4-5 个一组 commit）
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
- Modify: `justfile`（`lint:` 配方内加一行，置于 `lint_invariant_coverage` 之后）
- Modify: `docs/framework/invariants.md`（门检列段落加一行分工声明）
- Test: `tests/unit/tools/test_lint_gate_power_baseline.py`

**Interfaces:**
- Consumes: `tests/fixtures/g4-id-inventory.json`（#88 id 清单——消息 id 面）；Task 2/3 红测名（evidence 列）
- Produces: `lint_gate_power_baseline.py` 退出码契约：0=绿／1=FAIL 级（registry↔AST 漂移、baseline 行缺、分类值域外、非 discriminating 缺证据、ESCALATION_DATE 后 unclassified-0-点火）／WARN 级（ESCALATION_DATE 前 unclassified 且最近回放 0 点火）= stderr 警告行＋exit 0；`CHECK_REGISTRY: dict[str, dict]`（单源：canonical id→{fail_arms, warn_only, 口径}）

- [ ] **Step 1: 写失败测试**

```python
"""Spec #116 T2: vacuity registry sentinel lint tests."""

from __future__ import annotations

from pathlib import Path

import tools.lint_gate_power_baseline as lint


def _write_baseline(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "gate-power-baseline.md"
    p.write_text(body, encoding="utf-8")
    return p


GOOD_ROW = (
    "| `G4.cd.chapter_end_hook` | state-free | 0-10% | unclassified | — | "
    "50 章 @ 2026-11-19（reports/2026-11-19-gate-power-vol1.md） | 15/50 仅单字 |\n"
)


def test_registry_matches_static_sources() -> None:
    """registry∪fail_arms == AST 扫描（c.append dict id）∪ inventory cd/generic 面。"""
    drift = lint.registry_drift()
    assert drift == [], drift


def test_missing_baseline_row_is_fail(tmp_path: Path) -> None:
    p = _write_baseline(
        tmp_path, "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n|---|\n"
    )
    assert lint.lint_file(p, today=lint.ESCALATION_DATE.replace(year=2026)) == 1


def test_unclassified_zero_firing_warns_before_escalation(tmp_path: Path) -> None:
    body = "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n|---|\n"
    body += "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    p = _write_baseline(tmp_path, body)
    rc = lint.lint_file(p, today=lint.PRE_ESCALATION)
    assert rc == 0  # WARN 级：exit 0


def test_unclassified_zero_firing_fails_after_escalation(tmp_path: Path) -> None:
    body = "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n|---|\n"
    body += "| `G4.cd.surge` | state-free | 0% | unclassified | — | 50 章 @ d (r) 0 点火 | — |\n"
    p = _write_baseline(tmp_path, body)
    assert lint.lint_file(p, today=lint.ESCALATION_DATE) == 1


def test_decorative_without_evidence_fails() -> None:
    body = "# t\n\n| check | 口径 | 期望点火带 | 分类 | 证据 | 最近回放数 | 归因 |\n|---|\n"
    body += "| `G4.cd.meta` | state-free | 0% | decorative | | 50 章 @ d (r) 0 点火 | — |\n"
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = _write_baseline(Path(td), body)
        assert lint.lint_file(p, today=lint.PRE_ESCALATION) == 1


def test_classification_vocab_closed() -> None:
    assert lint.VALID_CLASSIFICATIONS == frozenset(
        {"unclassified", "floor-untested", "decorative", "discriminating", "retired"}
    )
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_lint_gate_power_baseline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 lint＋registry＋baseline 骨架**

`tools/lint_gate_power_baseline.py` 要点：CHECK_REGISTRY 从 appendix A 18 逻辑行派生（每行：canonical id＋fail arms＋warn_only 标志＋口径）；`registry_drift()` 双源校验——(a) AST 扫 `src/shenbi/gates/g4/chapter_drafting.py` 的 `c.append({"id": "G4.xxx"...})` dict id（文本级 `re.findall(r'"id":\s*"(G4\.[a-z_.]+)"'`）∪ (b) `tests/fixtures/g4-id-inventory.json` 的 cd./post./generic 键（映射回 `G4.` 前缀），与 registry∪arms 集合相等（多=未登记新门→FAIL；少=死键→FAIL）。`ESCALATION_DATE = date(2026, 12, 19)`（一个完整裁定周期；`PRE_ESCALATION = date(2026, 11, 19)` 常量供测试）。`lint_file(path, today)`：解析 baseline 表——行集==registry 集；分类值域；非 discriminating 行证据列非空（`—` 仅 unclassified 允许）；unclassified 且「最近回放数」列含 `0 点火` 且 today≥ESCALATION_DATE → exit 1，否则 stderr WARN＋exit 0。

`docs/framework/gate-power-baseline.md` 骨架：头节（义务声明＋口径定义＋分类四值语义＋「分类必须人工裁定」）＋18+ 行表（分类全 `unclassified`、最近回放数暂 `—`——Task 5 回填；hook/protagonist/transition 三行证据列填 Task 2 红测路径）。

`justfile` `lint:` 内 `uv run python tools/lint_invariant_coverage.py` 行后加 `uv run python tools/lint_gate_power_baseline.py`。

`docs/framework/invariants.md` 门检列段加：「点火率/恒真分类登记见 `docs/framework/gate-power-baseline.md`（spec #116）——本表管不变量维度覆盖，彼表管判别力，check-id 对账由 `tools/lint_gate_power_baseline.py` 执行」。

- [ ] **Step 4: 跑测试＋just lint 冒烟**

Run: `uv run pytest tests/unit/tools/test_lint_gate_power_baseline.py -v && uv run python tools/lint_gate_power_baseline.py; echo "exit=$?"`
Expected: 测试全 PASS；lint 本体在 baseline 骨架（全 unclassified＋回放数 `—`）下 exit 0（`—` 不触发 WARN——WARN 只对显式 `0 点火` 行；回填后才会 WARN，为设计内首态——若实现者发现此设计使 WARN 永不触发则改为 `—` 也 WARN（today<ESCALATION 时），并在 task report 记录裁定）

- [ ] **Step 5: Commit**

```bash
git add tools/lint_gate_power_baseline.py docs/framework/gate-power-baseline.md docs/framework/invariants.md justfile tests/unit/tools/test_lint_gate_power_baseline.py
git commit -m "feat: spec #116 T2 恒真登记+哨兵 lint（AST 双源 registry+分类证据义务+升格日期）"
```

---

### Task 5: 标定提案文档＋50 章回放回填

**Files:**
- Create: `docs/framework/gate-calibration-proposals.md`
- Create: `reports/2026-11-19-gate-power-vol1.md`（Task 1 工具实跑产物）
- Modify: `docs/framework/gate-power-baseline.md`（「最近回放数」列回填）

**Interfaces:**
- Consumes: Task 1 `just gate-power`；Task 2/3 红测；附录 A＋两份 Goodhart 报告数字
- Produces: 提案文档（用户裁定入口）；baseline 回填后哨兵进入 WARN 首态

- [ ] **Step 1: 维护者侧 50 章回放（验收 2 实跑）**

Run: `uv run python tools/gate_power_replay.py novel-xinghuo-vol1 --out reports/2026-11-19-gate-power-vol1.md`
Expected: 报告数字与附录 A 一致（10 散文门 50/50、voice_density FAIL=14、prop_handoff=11、simile WARN=28、ending None=47）；命令与输出摘录贴 progress.md `## 验收证据`

- [ ] **Step 2: 写提案文档**（七项×四栏；每项现状数字必须来自 Task 1 报告/附录 A/两 Goodhart 报告——逐项带数字，禁空泛）

结构：每项 `### <门名>`＋`| 栏 | 内容 |` 四行表（现状（数字）/提案（≥1 具体选项）/红测（指向 Task 2/3 测试或「落地批补」）/回滚（单 commit 条件））；voice_density 首项（vol1 14/50 must_fix＋r2 15/18——阈值重标定或信号两级拆分）；hook（15/50 单字-only＋`还`=38/`账`=38 与账房腔同词表——多字/结构臂或词表不相交）；protagonist（中位 93 vs 阈值 3＋名字表重复 `:495`/`:508`——去重＋重标定）；transition（中位 0 vs 阈值 5——retire 或重标定；化合物 3 次负结果）；scene_concreteness/surge/fatigue/meta（逐项分类＋负例链接）；simile（56% WARN——路由/降报告行）；ending archetype（47/50 None——扩分类器或退役哨兵）。

- [ ] **Step 3: baseline 回填**

「最近回放数」列填 `50 章 @ 2026-11-19（reports/2026-11-19-gate-power-vol1.md）`＋0 点火行加 `0 点火` 标记；跑 `uv run python tools/lint_gate_power_baseline.py; echo exit=$?` → exit 0＋stderr 多行 WARN（首态设计内——分类待用户裁定）；此输出贴 task report。

- [ ] **Step 4: 全量验收命令（AC1/2/3/5 实跑）**

Run: `uv run pytest tests/unit/tools/test_gate_power_replay.py tests/unit/tools/test_lint_gate_power_baseline.py tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add docs/framework/gate-calibration-proposals.md reports/2026-11-19-gate-power-vol1.md docs/framework/gate-power-baseline.md
git commit -m "docs: spec #116 T3 七项标定提案+T1/T2 50 章回放回填（哨兵进入 WARN 首态）"
```

---

## AC 覆盖表

| spec 验收 | task | 证据 |
|---|---|---|
| 1. T1-T4 判据全绿 | 1-5 | 各 task 测试＋`just check` |
| 2. gate-power 50 章可复现＋双口径＋simile 对照列 | 1（实现）＋5（实跑） | reports/2026-11-19-gate-power-vol1.md |
| 3. 登记覆盖分母＋WARN 哨兵＋升格判据测试 | 4 | test_lint_gate_power_baseline.py（5 用例含升格） |
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
