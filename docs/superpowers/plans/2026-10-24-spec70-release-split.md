# spec #70 release-split 发布切分层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 确定性发布切分工具——把已收束章节按番茄/起点档位切成发布就绪的更，账本对账、幂等增量、published 冻结。

**Architecture:** 单文件工具 `tools/release_split.py`（纯确定性、零 LLM、零管线写面），import `shenbi.gates.shared` 的 strip/count 口径函数；产物只落 `publish/<platform>/`。算法 = 约束窗口选择（下限进选择约束、单遍、不可行降档重启），spec §3.2/§3.3 为唯一权威。

**Tech Stack:** Python 3.11+ 标准库（argparse/json/re/hashlib/dataclasses/pathlib/datetime），pytest（`@pytest.mark.unit`），uv run。

## Global Constraints

- **零 `src/shenbi/` 改动**：`strip_narrative_body`/`total_chars_md_text` 只 import（`src/shenbi/gates/shared.py:168/:205`）
- **口径**：章级 gate 用 `total_chars_md_text`；更级 `chars = len(re.sub(r"\s","",切片))`（不重跑 strip）；全部度量 = 非空白字符；窗口算术整数精确式 `half = (15*B)//(100*m)`，端点按精确有理数（交叉相乘）比较
- **exit 码**：argparse 用法错 = 2；结构畸形/冻结冲突/账本生命周期 = 1（stderr 消息，异常类 `ReleaseSplitError`）
- **闭集**：`SCENE_TRANSITION_WORDS` 恰 16 词（spec §3.2 枚举），词表外不认
- **ruff**：`pyproject.toml [tool.ruff.lint.per-file-ignores]` 加 `tools/release_split.py` 与 `tests/unit/tools/test_release_split.py` 两条 `["RUF001","RUF002","RUF003"]`（CJK 全角标点是数据面，`lint_truth_pool.py` 同款先例）
- **basedpyright strict** 覆盖 `tests/`（新测试文件全类型注解）；`tools/` 不在其面
- **fixtures**：`tests/fixtures/publish/chapter-{1..5}.md` = 真产物副本 + YAML frontmatter（`provenance: real-output` + `source: novel-xinghuo-vol1/chapters/chapter-N.md`）；**禁入 MIRROR_MAP**
- **G0.9 双轨**：真实产物断言走 fixtures；结构性用例（对抗布局/账本状态）测试内构造（tmp_path/字面量）
- **conventional commits**；每 task 一个 commit（pathspec 显式列文件）
- **验收锚（仿真定稿，rev6 spec §5）**：fanqie ch1-4 = 13 更（4/3/3/3：ch1 [2029,2237,2003,2193]、ch2 [2322,2746,2966]、ch3 [2211,2237,2737]、ch4 [2224,2581,2972]）；+ch5 = 16（ch5 [2059,2007,2429]）；qidian ch1-5 = 3/3/3/3/3（ch1 [2483,2875,3104]）；恒等式 `Σ 更.chars == gate − H1行非空白`（ch1-5 逐章：8476−14、8049−15、7200−15、7792−15、6517−22）

---

### Task 1: 章解析层 + fixtures + ruff 豁免 + 模块骨架

**Files:**
- Create: `tools/release_split.py`
- Create: `tests/unit/tools/test_release_split.py`
- Create: `tests/fixtures/publish/chapter-{1..5}.md`（5 个副本）
- Modify: `pyproject.toml`（[tool.ruff.lint.per-file-ignores] 两条目）

**Interfaces:**
- Consumes: `shenbi.gates.shared.strip_narrative_body` / `total_chars_md_text`
- Produces（后续 task 依赖的精确签名）:
  - `nonws(s: str) -> int`
  - `class ReleaseSplitError(RuntimeError)`
  - `@dataclass(frozen=True) class ChapterInput: path: Path; number: int; title: str; gate_chars: int; h1_nonws: int; paragraphs: tuple[str, ...]`
  - `@dataclass(frozen=True) class Tier: floor: int; target: int; soft: int`
  - `TIERS: dict[str, Tier]`
  - `CHAPTER_FILE_RE = re.compile(r"^chapter-(\d+)\.md$")`
  - `select_chapter_files(chapters_dir: Path) -> list[Path]`
  - `parse_chapter(path: Path) -> ChapterInput`

- [ ] **Step 1: 建 fixtures（真产物副本 + provenance 头）**

```bash
mkdir -p tests/fixtures/publish
for n in 1 2 3 4 5; do
  printf -- '---\nprovenance: real-output\nsource: novel-xinghuo-vol1/chapters/chapter-%s.md\n---\n\n' "$n" > tests/fixtures/publish/chapter-$n.md
  cat novel-xinghuo-vol1/chapters/chapter-$n.md >> tests/fixtures/publish/chapter-$n.md
done
```

- [ ] **Step 2: pyproject.toml 加 RUF 豁免**

`[tool.ruff.lint.per-file-ignores]` 段（`"tools/lint_truth_pool.py"` 条目后）加：

```toml
# spec #70 release-split: scene word list + fullwidth predicate chars are the
# data, not drift (same category as lint_truth_pool).
"tools/release_split.py" = ["RUF001", "RUF002", "RUF003"]
"tests/unit/tools/test_release_split.py" = ["RUF001", "RUF002", "RUF003"]
```

- [ ] **Step 3: 写失败测试（解析层）**

`tests/unit/tools/test_release_split.py`：

```python
"""spec #70 release-split unit tests (T1: chapter parsing layer)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.release_split import (
    CHAPTER_FILE_RE,
    ChapterInput,
    ReleaseSplitError,
    TIERS,
    nonws,
    parse_chapter,
    select_chapter_files,
)

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests" / "fixtures" / "publish"

# gate chars / h1 nonws / paragraph count (non-zero-nonws) for ch1-5
EXPECTED = {
    1: (8476, 14, None),  # paragraph count asserted >= only (exact not pinned)
    2: (8049, 15, None),
    3: (7200, 15, None),
    4: (7792, 15, None),
    5: (6517, 22, None),
}
TITLES = {1: "明白纸", 2: "城破那日", 3: "两本册子", 4: "一升二合", 5: "例在，人在"}


@pytest.mark.unit
def test_tiers_pinned() -> None:
    assert TIERS["fanqie"] == (2000, 2200, 2400)  # type: ignore[comparison-overlap]
    assert TIERS["qidian"] == (2000, 2700, 3000)


@pytest.mark.unit
def test_chapter_file_regex() -> None:
    assert CHAPTER_FILE_RE.match("chapter-1.md")
    assert CHAPTER_FILE_RE.match("chapter-10.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-pre-rev.md")
    assert not CHAPTER_FILE_RE.match("chapter-1-decisions.json")
    assert not CHAPTER_FILE_RE.match("chapter-1-revision-decisions.json")


@pytest.mark.unit
def test_select_orders_numerically_and_rejects_dup(tmp_path: Path) -> None:
    d = tmp_path / "chapters"
    d.mkdir()
    for name in ("chapter-10.md", "chapter-2.md", "chapter-1.md"):
        (d / name).write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    files = select_chapter_files(d)
    assert [f.name for f in files] == ["chapter-1.md", "chapter-2.md", "chapter-10.md"]
    (d / "chapter-01.md").write_text("# Chapter 1:\n\n# t\n\n正文", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="同章号"):
        select_chapter_files(d)


@pytest.mark.unit
def test_parse_real_fixtures() -> None:
    for n, (gate, h1n, _pc) in EXPECTED.items():
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        assert isinstance(ch, ChapterInput)
        assert ch.number == n
        assert ch.title == TITLES[n]
        assert ch.gate_chars == gate
        assert ch.h1_nonws == h1n
        # identity: gate - h1 == sum of paragraph nonws
        assert ch.gate_chars - ch.h1_nonws == sum(nonws(p) for p in ch.paragraphs)
        # zero-nonws paragraphs dropped; every paragraph has content
        assert all(nonws(p) > 0 for p in ch.paragraphs)
        # no H1 lines, no META wrappers survive into paragraphs
        assert not any(p.startswith("# ") for p in ch.paragraphs)
        assert not any("META-BEGIN" in p or "PRE_WRITE_CHECK" in p for p in ch.paragraphs)
        # ch5 duplicate title H1 stripped (3 H1 lines total)
        if n == 5:
            assert ch.h1_nonws == 22


@pytest.mark.unit
def test_parse_ch5_duplicate_h1_outside_wrapper() -> None:
    ch = parse_chapter(FIX / "chapter-5.md")
    body = "\n\n".join(ch.paragraphs)
    assert "例在，人在" in ch.title
    # the stray duplicate H1 line (line 22 of the source) must not survive
    assert not re.search(r"^# ", body, flags=re.MULTILINE)


@pytest.mark.unit
def test_parse_structural_errors(tmp_path: Path) -> None:
    no_h1 = tmp_path / "chapter-1.md"
    no_h1.write_text("# Chapter 1:\n\n正文一段。", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="第二个 H1"):
        parse_chapter(no_h1)
    empty = tmp_path / "chapter-2.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="空"):
        parse_chapter(empty)
    no_paras = tmp_path / "chapter-3.md"
    no_paras.write_text("# Chapter 3:\n\n# 题\n\n<!--META-BEGIN-->\n## PRE_WRITE_CHECK\nx\n<!--META-END-->\n", encoding="utf-8")
    with pytest.raises(ReleaseSplitError, match="正文段"):
        parse_chapter(no_paras)
```

- [ ] **Step 4: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: FAIL（ModuleNotFoundError: tools.release_split）

- [ ] **Step 5: 实现模块骨架**

`tools/release_split.py`：

```python
"""spec #70 release-split: deterministic publish-layer chapter splitting.

Reads only ``chapters/chapter-N.md``; writes only ``publish/<platform>/``.
No LLM, no pipeline faces. 口径 reused from shenbi.gates.shared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.gates.shared import strip_narrative_body, total_chars_md_text

SCHEMA_ID = "shenbi-releases-v1"

# Closed scene-transition word list (spec §3.2) — the single source.
SCENE_TRANSITION_WORDS: frozenset[str] = frozenset(
    {
        "翌日", "次日", "清晨", "天亮", "黄昏", "入夜",
        "夜半", "午夜", "到了", "走进", "回到", "出门",
        "动身", "起程", "转场", "天明",
    }
)

_TENSION_END_CHARS = frozenset({"？", "！"})
_DIALOGUE_START_CHARS = frozenset({"“", "「", "『"})
_SHORT_OBJECT_SENTENCE_MAX = 40

CHAPTER_FILE_RE = re.compile(r"^chapter-(\d+)\.md$")
_H1_RE = re.compile(r"^# ", re.MULTILINE)
_PARA_SPLIT_RE = re.compile(r"\n\s*\n")


class ReleaseSplitError(RuntimeError):
    """Structural input / freeze / ledger-lifecycle error (exit 1)."""


@dataclass(frozen=True)
class Tier:
    floor: int  # 硬下限（不可越）
    target: int  # 目标
    soft: int  # 软上限（可微越）


TIERS: dict[str, Tier] = {
    "fanqie": Tier(floor=2000, target=2200, soft=2400),
    "qidian": Tier(floor=2000, target=2700, soft=3000),
}


def nonws(s: str) -> int:
    """Non-whitespace char count — the spec's unified metric."""
    return len(re.sub(r"\s", "", s))


@dataclass(frozen=True)
class ChapterInput:
    path: Path
    number: int
    title: str
    gate_chars: int
    h1_nonws: int
    paragraphs: tuple[str, ...]


def select_chapter_files(chapters_dir: Path) -> list[Path]:
    """Numeric-ascending chapter files; rejects empty dir and duplicate numbers."""
    if not chapters_dir.is_dir():
        raise ReleaseSplitError(f"chapters/ 目录不存在: {chapters_dir}")
    picked: dict[int, Path] = {}
    for f in sorted(chapters_dir.iterdir()):
        m = CHAPTER_FILE_RE.match(f.name)
        if not (m and f.is_file()):
            continue
        num = int(m.group(1))
        if num in picked:
            raise ReleaseSplitError(f"同章号重复文件: chapter-{num}（{picked[num].name} 与 {f.name}）")
        picked[num] = f
    if not picked:
        raise ReleaseSplitError(f"chapters/ 内零匹配章: {chapters_dir}")
    return [picked[n] for n in sorted(picked)]


def parse_chapter(path: Path) -> ChapterInput:
    """Strip (shared 口径) → extract ALL H1 lines → split paragraphs.

    Structural errors: empty file / no second H1 / no surviving paragraphs.
    """
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ReleaseSplitError(f"章文件为空: {path.name}")
    m = CHAPTER_FILE_RE.match(path.name)
    if m is None:  # pragma: no cover - callers go through select_chapter_files
        raise ReleaseSplitError(f"文件名不匹配: {path.name}")
    body = strip_narrative_body(raw)
    h1_lines = [ln for ln in body.splitlines() if ln.startswith("# ")]
    if len(h1_lines) < 2:
        raise ReleaseSplitError(f"章文件无第二个 H1（章题提取失败）: {path.name}")
    title = h1_lines[1].lstrip("#").strip()
    for h in h1_lines:
        body = body.replace(h, "", 1)
    paras = tuple(p for p in _PARA_SPLIT_RE.split(body) if nonws(p) > 0)
    if not paras:
        raise ReleaseSplitError(f"剥离后无正文段: {path.name}")
    return ChapterInput(
        path=path,
        number=int(m.group(1)),
        title=title,
        gate_chars=total_chars_md_text(raw),
        h1_nonws=sum(nonws(h) for h in h1_lines),
        paragraphs=paras,
    )
```

- [ ] **Step 6: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add tools/release_split.py tests/unit/tools/test_release_split.py tests/fixtures/publish/ pyproject.toml
git commit -m "feat(release-split): T1 章解析层——strip/H1/段落切分 + ch1-5 真产物夹具 + RUF 豁免"
```

---

### Task 2: 打分谓词、质量四档、中文序数

**Files:**
- Modify: `tools/release_split.py`（追加）
- Modify: `tests/unit/tools/test_release_split.py`（追加）

**Interfaces:**
- Consumes: `nonws`, `SCENE_TRANSITION_WORDS`（T1）
- Produces:
  - `@dataclass(frozen=True) class CutSignals: score: int; tension: bool; scene: bool; waist: bool`
  - `classify_pair(prev: str, next: str | None) -> CutSignals`（`next=None` = 章末假想切点：张力谓词可触发，场景/腰斩不可）
  - `tier_of(sig: CutSignals) -> str`（返回 `"tension"|"scene"|"plain"|"weak"`）
  - `chinese_ordinal(k: int) -> str`（1→一 … 10→十 … 21→二十一；1-99）

- [ ] **Step 1: 写失败测试**

追加到 `tests/unit/tools/test_release_split.py`：

```python
from tools.release_split import CutSignals, chinese_ordinal, classify_pair, tier_of


@pytest.mark.unit
def test_tension_predicates_stack_to_six() -> None:
    # (a) ends ？, (b) <=40 chars, (c) starts “ — all three fire: +6
    sig = classify_pair("“会吗？”", "他走了。")
    assert (sig.score, sig.tension, sig.scene, sig.waist) == (6, True, False, False)
    # only (b): plain short sentence +2, no scene word after
    sig2 = classify_pair("他放下笔。", "他又拿起来了。")
    assert sig2.score == 2 and sig2.tension and not sig2.scene and not sig2.waist
    # no predicates at all
    sig3 = classify_pair("他放下笔，走到窗前，看着院子里那棵老槐树在风里晃了很久才停。", "他站了很久。")
    assert sig3.score == 0 and not sig3.tension and not sig3.scene and not sig3.waist


@pytest.mark.unit
def test_scene_and_waist_predicates() -> None:
    # next starts with scene word: +1; prev starts with scene word: -2
    sig = classify_pair("他睡了。", "翌日清晨，城里来了消息。")
    assert sig.score == 1 and sig.scene and not sig.tension and not sig.waist
    sig_w = classify_pair("翌日他去了码头。", "码头空着。")
    assert sig_w.score == -2 and sig_w.waist and not sig_w.tension and not sig_w.scene
    # both fire on adjacent scene openings: +1 - 2 (+0 tension) = -1
    sig_both = classify_pair("入夜风起了。", "次日船到了。")
    assert sig_both.score == -1 and sig_both.scene and sig_both.waist
    # scene prefix overlap harmless (starts-with, closed list)
    assert classify_pair("他睡了。", "入夜时分睡不着的是另一个人这句话不在词表前缀歧义里。").scene is False


@pytest.mark.unit
def test_end_of_chapter_imaginary_cut() -> None:
    # next=None: tension predicates live, scene/waist dead
    sig = classify_pair("“会吗？”", None)
    assert sig.score == 6 and sig.tension and not sig.scene and not sig.waist


@pytest.mark.unit
def test_four_tiers_by_predicate_firing() -> None:
    def sig(score: int, tension: bool, scene: bool, waist: bool) -> CutSignals:
        return CutSignals(score=score, tension=tension, scene=scene, waist=waist)

    assert tier_of(sig(6, True, False, False)) == "tension"
    assert tier_of(sig(2, True, True, True)) == "tension"  # tension dominates
    assert tier_of(sig(1, False, True, False)) == "scene"
    assert tier_of(sig(0, False, False, False)) == "plain"
    assert tier_of(sig(-2, False, False, True)) == "weak"
    assert tier_of(sig(-1, False, True, True)) == "scene"  # scene fired, tension didn't


@pytest.mark.unit
def test_chinese_ordinals() -> None:
    digits = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
    for k in range(1, 10):
        assert chinese_ordinal(k) == digits[k - 1]
    assert chinese_ordinal(10) == "十"
    assert chinese_ordinal(11) == "十一"
    assert chinese_ordinal(20) == "二十"
    assert chinese_ordinal(21) == "二十一"
    assert chinese_ordinal(99) == "九十九"
    with pytest.raises(ValueError):
        chinese_ordinal(0)
    with pytest.raises(ValueError):
        chinese_ordinal(100)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v -k "tension or scene or ordinal or tier or imaginary"`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现**

追加到 `tools/release_split.py`：

```python
@dataclass(frozen=True)
class CutSignals:
    score: int
    tension: bool
    scene: bool
    waist: bool


def classify_pair(prev: str, next: str | None) -> CutSignals:
    """Closed-set scoring of a cut between prev and next paragraphs.

    ``next=None`` is the end-of-chapter imaginary cut: tension predicates
    live, scene/waist predicates are dead (no following paragraph).
    """
    pn = re.sub(r"\s", "", prev)
    score = 0
    tension = False
    if pn and pn[-1] in _TENSION_END_CHARS:
        score += 2
        tension = True
    if len(pn) <= _SHORT_OBJECT_SENTENCE_MAX:
        score += 2
        tension = True
    if pn and pn[0] in _DIALOGUE_START_CHARS:
        score += 2
        tension = True
    scene = False
    waist = False
    if next is not None:
        fn = re.sub(r"\s", "", next)
        if any(fn.startswith(w) for w in SCENE_TRANSITION_WORDS):
            score += 1
            scene = True
        if any(pn.startswith(w) for w in SCENE_TRANSITION_WORDS):
            score -= 2
            waist = True
    return CutSignals(score=score, tension=tension, scene=scene, waist=waist)


def tier_of(sig: CutSignals) -> str:
    """Quality tier by predicate firing (spec §3.4): tension > scene > plain/weak."""
    if sig.tension:
        return "tension"
    if sig.scene:
        return "scene"
    if sig.waist:
        return "weak"
    return "plain"


_CN_DIGITS = "零一二三四五六七八九"


def chinese_ordinal(k: int) -> str:
    """1..99 → 一 … 九十九 (per-chapter release ordinal, spec §4)."""
    if not 1 <= k <= 99:
        raise ValueError(f"中文序数仅支持 1-99: {k}")
    tens, ones = divmod(k, 10)
    parts: list[str] = []
    if tens >= 1:
        parts.append("十" if tens == 1 else _CN_DIGITS[tens] + "十")
    if ones >= 1:
        parts.append(_CN_DIGITS[ones])
    return "".join(parts)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: 全部 passed（T1+T2）

- [ ] **Step 5: Commit**

```bash
git add tools/release_split.py tests/unit/tools/test_release_split.py
git commit -m "feat(release-split): T2 打分谓词闭集+四档归类+中文序数"
```

---

### Task 3: 切分算法——n 公式 + 约束窗口选择 + 降档重启

**Files:**
- Modify: `tools/release_split.py`（追加）
- Modify: `tests/unit/tools/test_release_split.py`（追加）

**Interfaces:**
- Consumes: `Tier`, `classify_pair`, `CutSignals`, `nonws`（T1/T2）
- Produces:
  - `initial_n(gate_chars: int, tier: Tier) -> int`（§2：`<2×floor` → 1；否则 `ceil(gate/soft)`，`gate/n < floor` 则 n−1）
  - `plan_releases(ch: ChapterInput, n: int, tier: Tier) -> tuple[list[tuple[int, int]], int]` → `(groups, m)`——groups 为 `[(start_para, end_para_exclusive), ...]`（长度 m；m=1 → `[(0, len(paras))]` = 塌缩/单更）

- [ ] **Step 1: 写失败测试**

追加：

```python
from tools.release_split import initial_n, plan_releases


@pytest.mark.unit
def test_initial_n_formula_edges() -> None:
    fq = TIERS["fanqie"]
    qd = TIERS["qidian"]
    assert initial_n(1999, fq) == 1        # < 2×floor → 单更
    assert initial_n(3999, fq) == 1        # 单更（软上限 +66% 合法形态）
    assert initial_n(4000, fq) == 2        # 2×2000 恰可分
    assert initial_n(4801, fq) == 3        # ceil=3 → 1600<2000 → 2
    assert initial_n(4802, fq) == 2
    assert initial_n(10000, fq) == 5       # 5×2000 恰
    assert initial_n(10001, fq) == 5
    assert initial_n(10400, fq) == 5
    assert initial_n(12500, fq) == 6
    assert initial_n(7792, fq) == 3        # ch4 回退分支：ceil=4 → 1948<2000 → 3
    assert initial_n(7200, fq) == 3        # 恰 3×2400
    assert initial_n(2999, qd) == 1
    assert initial_n(3000, qd) == 1        # qidian 单更恰软上限
    assert initial_n(6001, qd) == 3        # qidian 回退分支不可达：ceil(6001/3000)=3 → 2000.33 ≥2000


def _mk_ch(paras: list[str], gate: int | None = None, h1: int = 0) -> ChapterInput:
    body = sum(nonws(p) for p in paras)
    return ChapterInput(
        path=Path("chapter-0.md"), number=0, title="t",
        gate_chars=gate if gate is not None else body + h1,
        h1_nonws=h1, paragraphs=tuple(paras),
    )


@pytest.mark.unit
def test_plan_releases_real_fixtures_fanqie() -> None:
    """仿真定稿回归锚（spec §5 rev6）——从 spec 文本独立复现的数字。"""
    fq = TIERS["fanqie"]
    expected = {
        1: [2029, 2237, 2003, 2193],
        2: [2322, 2746, 2966],   # 初始 n=4，选择第 2 步可行域空 → 降档 m=3
        3: [2211, 2237, 2737],
        4: [2224, 2581, 2972],   # §2 回退 7792→3
        5: [2059, 2007, 2429],
    }
    for n, sizes in expected.items():
        ch = parse_chapter(FIX / f"chapter-{n}.md")
        groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
        got = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
        assert m == len(sizes), f"ch{n}: m={m} != {len(sizes)}"
        assert got == sizes, f"ch{n}: {got} != {sizes}"
        assert all(x >= fq.floor for x in got)


@pytest.mark.unit
def test_plan_releases_qidian_anchors() -> None:
    qd = TIERS["qidian"]
    ch1 = parse_chapter(FIX / "chapter-1.md")
    groups, m = plan_releases(ch1, initial_n(ch1.gate_chars, qd), qd)
    got = [sum(nonws(p) for p in ch1.paragraphs[s:e]) for s, e in groups]
    assert (m, got) == (3, [2483, 2875, 3104])


@pytest.mark.unit
def test_plan_releases_razor_slack_downgrade() -> None:
    """构造 razor-slack：body 8040 三巨段（边界 2680/5360）——m=4 时首带
    [2000, 2040] 无候选 → 降档 4→3（真 ch2 同机制，此处受控验证）。"""
    fq = TIERS["fanqie"]
    paras = ["字" * 2680, "句" * 2680, "词" * 2680]
    ch = _mk_ch(paras, gate=8055, h1=15)  # ceil(8055/2400)=4, 8055/4=2013>=2000
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 3
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2680, 2680, 2680]
    assert all(x >= fq.floor for x in sizes)


@pytest.mark.unit
def test_plan_releases_collapse_to_forced_single() -> None:
    """构造 4500 = 1200/2100/1200：m=2 两候选皆出可行域 → 塌缩 m=1。"""
    fq = TIERS["fanqie"]
    a = "字" * 1200
    b = "句" * 2100
    c = "词" * 1200
    ch = _mk_ch([a, b, c], gate=4500)
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 1
    assert groups == [(0, 3)]


@pytest.mark.unit
def test_plan_releases_single_release_short_chapter() -> None:
    fq = TIERS["fanqie"]
    ch = _mk_ch(["短章" * 300], gate=1199)  # body 600 < 2×floor
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 1 and groups == [(0, 1)]


@pytest.mark.unit
def test_plan_releases_scoring_moves_cut() -> None:
    """同窗候选打分差改变切点：窗口内三候选，张力段边界（+6）胜过 0 分与 +2 分者。"""
    fq = TIERS["fanqie"]
    a = "他" * 2050          # 普通长段：无张力谓词（>40、不以引号开头、不以？！收尾）
    t = "“会吗？”"            # 张力 +6（？！收尾 + ≤40 + 引号开头）
    f = "灯苗矮下去又立起来。"  # +2（≤40）
    b = "词" * 2051
    ch = _mk_ch([a, t, f, b])  # body = 2050+5+10+2051 = 4116, gate 同
    # n=2（ceil(4116/2400)=2, 4116/2=2058>=2000）；t_1=2058, half=(15*4116)//200=308
    # 窗口 [1750, 2366]：边界 2050(0 分)/2055(+6)/2065(+2) → 选 2055
    groups, m = plan_releases(ch, initial_n(ch.gate_chars, fq), fq)
    assert m == 2
    sizes = [sum(nonws(p) for p in ch.paragraphs[s:e]) for s, e in groups]
    assert sizes == [2055, 2061]
    assert all(x >= fq.floor for x in sizes)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v -k "initial_n or plan_releases"`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现**

追加到 `tools/release_split.py`：

```python
def initial_n(gate_chars: int, tier: Tier) -> int:
    """§2: size-single first, then ceil(gate/soft) with single floor fallback."""
    if gate_chars < 2 * tier.floor:
        return 1
    n = -(-gate_chars // tier.soft)  # ceil
    if gate_chars / n < tier.floor:
        n -= 1
    return max(n, 1)


def plan_releases(ch: ChapterInput, n: int, tier: Tier) -> tuple[list[tuple[int, int]], int]:
    """Constrained-window selection (spec §3.2) → paragraph-index groups + m."""
    paras = ch.paragraphs
    sizes = [nonws(p) for p in paras]
    body = sum(sizes)
    # prefix[j] = non-ws chars before boundary j (after paragraphs 0..j-1)
    prefix: list[int] = [0]
    for s in sizes:
        prefix.append(prefix[-1] + s)

    if n < 2 or len(paras) < 2:
        return [(0, len(paras))], 1

    floor = tier.floor
    m = n
    while True:
        cuts: list[int] = []  # chosen boundary indices (paragraph boundaries, 1..len-1)
        infeasible = False
        for i in range(1, m):
            lo = (prefix[cuts[-1]] if cuts else 0) + floor
            hi = body - floor * (m - i)
            # exact-rational window: t_i = i*body/m; half = (15*body)//(100*m)
            half = (15 * body) // (100 * m)
            ib = i * body
            in_win: list[tuple[int, int]] = []  # (boundary j, position)
            feasible: list[tuple[int, int]] = []
            for j in range(1, len(paras)):
                p = prefix[j]
                if lo <= p <= hi:
                    feasible.append((j, p))
                    # closed interval: p*m >= ib - half*m and p*m <= ib + half*m
                    if p * m >= ib - half * m and p * m <= ib + half * m:
                        in_win.append((j, p))
            if not feasible:
                m -= 1
                if m < 2:
                    return [(0, len(paras))], 1
                infeasible = True
                break
            if in_win:
                best = max(
                    in_win,
                    key=lambda jp: (classify_pair(paras[jp[0] - 1], paras[jp[0]]).score, -jp[1]),
                )
            else:
                # fallback: feasible candidate nearest to target (exact rational), tie → earlier
                best = min(feasible, key=lambda jp: (abs(jp[1] * m - ib), jp[1]))
            cuts.append(best[0])
        if not infeasible:
            groups: list[tuple[int, int]] = []
            start = 0
            for c in cuts:
                groups.append((start, c))
                start = c
            groups.append((start, len(paras)))
            return groups, m
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: 全部 passed（真实夹具锚 13/16/15 的章级数字逐一命中）

- [ ] **Step 5: Commit**

```bash
git add tools/release_split.py tests/unit/tools/test_release_split.py
git commit -m "feat(release-split): T3 约束窗口选择算法——整数精确窗口+降档重启+塌缩单更（ch1-5 仿真锚全中）"
```

---

### Task 4: 账本与产物——releases.json v1、发布文件、更题

**Files:**
- Modify: `tools/release_split.py`（追加）
- Modify: `tests/unit/tools/test_release_split.py`（追加）

**Interfaces:**
- Consumes: T1-T3 全部
- Produces:
  - `build_release_text(paras: tuple[str, ...] | list[str]) -> str`（`\n\n` 连接 + 尾恰一 `\n`）
  - `content_hash_of(text: str) -> str`（sha256(UTF-8 bytes) 十六进制前 16）
  - `default_title_pattern(chapter_title: str, ordinal: str | None) -> str`
  - `render_title(pattern: str, chapter_title: str, ordinal: str | None) -> str`（占位符恰 `{章题}`/`{中文序数}`；未知占位符 → `ReleaseSplitError`）
  - `chapter_flags(gate: int, body: int, m: int) -> list[str]`（§3.3 矩阵：`gate<4000` 尺寸路径先占；`m==1` → forced-single）
  - `split_chapter(ch: ChapterInput, tier: Tier, title_pattern: str | None) -> dict[str, Any]`（章级账本条目：chapter/gate_chars/stripped_chars/flags/releases[{seq 占位 0,file 占位,chars,range,cut_quality,head,tail,title,content_hash,published:False}]）——seq/file 由 T5 全局编排后回填

- [ ] **Step 1: 写失败测试**

追加：

```python
import hashlib

from tools.release_split import (
    build_release_text,
    chapter_flags,
    content_hash_of,
    render_title,
    split_chapter,
)


@pytest.mark.unit
def test_release_text_byte_composition() -> None:
    text = build_release_text(["第一段。", "第二段。"])
    assert text == "第一段。\n\n第二段。\n"
    h = content_hash_of(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    assert len(h) == 16


@pytest.mark.unit
def test_render_title_rules() -> None:
    assert render_title(None, "明白纸", "一") == "明白纸（一）"
    assert render_title(None, "明白纸", None) == "明白纸"
    assert render_title("{中文序数}·{章题}", "明白纸", "二") == "二·明白纸"
    with pytest.raises(ReleaseSplitError, match="占位符"):
        render_title("{foo}", "明白纸", "一")
    with pytest.raises(ReleaseSplitError, match="中文序数"):
        render_title("{中文序数}", "明白纸", None)  # 单更无序数


@pytest.mark.unit
def test_chapter_flags_matrix() -> None:
    # size-single >= 2000 (gate < 4000)
    assert chapter_flags(gate=3999, body=3985, m=1) == ["single-release"]
    # size-single < 2000 → + floor-violation
    assert chapter_flags(gate=1999, body=1985, m=1) == ["single-release", "floor-violation"]
    # single-paragraph chapter >= 4000 → forced-single (size rule does not fire)
    assert chapter_flags(gate=5000, body=4980, m=1) == ["forced-single"]
    # single-paragraph < 4000 → size rule owns it
    assert chapter_flags(gate=2500, body=2480, m=1) == ["single-release"]
    # multi-paragraph collapsed to m=1 → forced-single
    assert chapter_flags(gate=4500, body=4480, m=1) == ["forced-single"]
    # partial downgrade 4→3 → no flag
    assert chapter_flags(gate=8100, body=8080, m=3) == []


@pytest.mark.unit
def test_split_chapter_entry_shape() -> None:
    fq = TIERS["fanqie"]
    ch = parse_chapter(FIX / "chapter-1.md")
    entry = split_chapter(ch, fq, None)
    assert entry["chapter"] == 1
    assert entry["gate_chars"] == 8476
    assert entry["stripped_chars"] == 14
    assert entry["flags"] == []
    rels = entry["releases"]
    assert len(rels) == 4
    assert [r["chars"] for r in rels] == [2029, 2237, 2003, 2193]
    assert entry["gate_chars"] - entry["stripped_chars"] == sum(r["chars"] for r in rels)
    r0 = rels[0]
    assert r0["range"] == [0, 2029]
    assert r0["title"] == "明白纸（一）"
    assert r0["published"] is False
    assert r0["head"] and len(r0["head"]) <= 12
    assert r0["tail"] and len(r0["tail"]) <= 12
    # byte composition + hash consistency (file bytes == _text)
    for r in rels:
        s, e = r["_paras"]
        assert r["content_hash"] == content_hash_of(build_release_text(ch.paragraphs[s:e]))
    # cut_quality: real ch1 cuts all classify tension (spec §5 note)
    assert all(r["cut_quality"] == "tension" for r in rels)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v -k "byte or title or flags or entry_shape"`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现**

追加到 `tools/release_split.py`：

```python
_TITLE_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_ALLOWED_PLACEHOLDERS = frozenset({"章题", "中文序数"})


def build_release_text(paras: tuple[str, ...] | list[str]) -> str:
    """Paragraphs joined with blank line + exactly one trailing newline."""
    return "\n\n".join(paras) + "\n"


def content_hash_of(text: str) -> str:
    """sha256 of the release FILE bytes (UTF-8), first 16 hex chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def render_title(pattern: str | None, chapter_title: str, ordinal: str | None) -> str:
    """Default `{章题}（{中文序数}）`; single 更 → bare title."""
    if pattern is None:
        return chapter_title if ordinal is None else f"{chapter_title}（{ordinal}）"

    def _sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key == "章题":
            return chapter_title
        if key == "中文序数":
            if ordinal is None:
                raise ReleaseSplitError("单更无 {中文序数}，标题模式不可含该占位符")
            return ordinal
        raise ReleaseSplitError(f"--title-pattern 含未知占位符: {{{key}}}")

    return _TITLE_PLACEHOLDER_RE.sub(_sub, pattern)


def chapter_flags(gate: int, body: int, m: int) -> list[str]:
    """§3.3 flags matrix — size rule owns all gate<4000 chapters first."""
    if gate < 4000:  # < 2×floor, both tiers share floor=2000
        flags = ["single-release"]
        if body < 2000:
            flags.append("floor-violation")
        return flags
    if m == 1:
        return ["forced-single"]
    return []


def split_chapter(ch: ChapterInput, tier: Tier, title_pattern: str | None) -> dict[str, Any]:
    """Per-chapter ledger entry (seq/file left as placeholders for T5)."""
    n = initial_n(ch.gate_chars, tier)
    groups, m = plan_releases(ch, n, tier)
    body = sum(nonws(p) for p in ch.paragraphs)
    flags = chapter_flags(ch.gate_chars, body, m)
    offset = 0
    releases: list[dict[str, Any]] = []
    for k, (s, e) in enumerate(groups):
        text = build_release_text(ch.paragraphs[s:e])
        chars = nonws(text)
        ordinal = None if m == 1 else chinese_ordinal(k + 1)
        # cut_quality: 更 k = its terminating cut (cut k); 末更 = imaginary
        # end-cut (tension predicates live, scene/waist dead)
        sig = (
            classify_pair(ch.paragraphs[e - 1], ch.paragraphs[e])
            if e < len(ch.paragraphs)
            else classify_pair(ch.paragraphs[e - 1], None)
        )
        flat = nonws_head_tail(text)
        releases.append(
            {
                "seq": 0,  # assigned globally in T5
                "file": "",  # assigned globally in T5
                "chars": chars,
                "range": [offset, offset + chars],
                "cut_quality": tier_of(sig),
                "head": flat[0],
                "tail": flat[1],
                "title": render_title(title_pattern, ch.title, ordinal),
                "content_hash": content_hash_of(text),
                "published": False,
                "_paras": (s, e),
                "_text": text,
            }
        )
        offset += chars
    return {
        "chapter": ch.number,
        "gate_chars": ch.gate_chars,
        "stripped_chars": ch.gate_chars - sum(r["chars"] for r in releases),
        "flags": flags,
        "releases": releases,
    }


def nonws_head_tail(text: str) -> tuple[str, str]:
    """First/last ≤12 non-ws chars of the slice, single-line."""
    flat = re.sub(r"\s", "", text)
    return flat[:12], flat[-12:]
```

（`_paras`/`_text` 为临时键：T5 写盘用 `_text`，账本序列化剥离全部 `_` 前缀键。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add tools/release_split.py tests/unit/tools/test_release_split.py
git commit -m "feat(release-split): T4 账本条目——字节构成/content_hash/更题/flags 矩阵/四档映射"
```

---

### Task 5: CLI、幂等/冻结/生命周期、孤儿清理、平台隔离

**Files:**
- Modify: `tools/release_split.py`（追加 run_split/main）
- Modify: `tests/unit/tools/test_release_split.py`（追加）

**Interfaces:**
- Consumes: T1-T4 全部；`json`/`argparse`/`sys`
- Produces:
  - `load_ledger(platform_dir: Path, platform: str) -> dict[str, Any] | None`（无文件 → None；畸形 JSON/schema 不符/platform 不符 → `ReleaseSplitError`）
  - `run_split(project_dir: Path, platform: str, title_pattern: str | None, renumber_published: bool) -> int`
  - `main(argv: list[str] | None = None) -> int`（argparse：positional project_dir、`--platform {fanqie,qidian}` 缺省 fanqie、`--title-pattern`、`--renumber-published`）
  - `if __name__ == "__main__": sys.exit(main())`

- [ ] **Step 1: 写失败测试（CLI 子进程 + 生命周期）**

追加：

```python
import json
import shutil
import subprocess
import sys


def _run_tool(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "release_split.py"), str(project), *args],
        capture_output=True, text=True, cwd=REPO,
    )


def _proj(tmp_path: Path, chapters: tuple[int, ...] = (1, 2, 3, 4)) -> Path:
    p = tmp_path / "proj"
    (p / "chapters").mkdir(parents=True)
    for n in chapters:
        shutil.copy(FIX / f"chapter-{n}.md", p / "chapters" / f"chapter-{n}.md")
    return p


@pytest.mark.unit
def test_cli_first_run_fanqie_13_releases(tmp_path: Path) -> None:
    p = _proj(tmp_path)
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 0, r.stderr
    ledger = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    assert ledger["schema"] == "shenbi-releases-v1"
    assert ledger["platform"] == "fanqie"
    total = sum(len(c["releases"]) for c in ledger["chapters"])
    assert total == 13
    per_ch = {c["chapter"]: len(c["releases"]) for c in ledger["chapters"]}
    assert per_ch == {1: 4, 2: 3, 3: 3, 4: 3}
    files = sorted((p / "publish" / "fanqie" / "releases").glob("release-*.md"))
    assert [f.name for f in files] == [f"release-{i:04d}.md" for i in range(1, 14)]
    # seq == file NNNN, global ascending by chapter then order
    seqs = [r["seq"] for c in ledger["chapters"] for r in c["releases"]]
    assert seqs == list(range(1, 14))
    # every release file bytes hash matches ledger
    for c in ledger["chapters"]:
        for r in c["releases"]:
            fp = p / "publish" / "fanqie" / "releases" / r["file"]
            assert r["content_hash"] == content_hash_of(fp.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_cli_with_ch5_16_and_qidian_isolation(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2, 3, 4, 5))
    assert _run_tool(p).returncode == 0  # default fanqie
    fq = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    assert sum(len(c["releases"]) for c in fq["chapters"]) == 16
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 0, r.stderr
    qd = json.loads((p / "publish" / "qidian" / "releases.json").read_text(encoding="utf-8"))
    assert qd["platform"] == "qidian"
    assert {c["chapter"]: len(c["releases"]) for c in qd["chapters"]} == {1: 3, 2: 3, 3: 3, 4: 3, 5: 3}
    # fanqie ledger untouched by qidian run
    fq2 = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    assert fq2["platform"] == "fanqie" and sum(len(c["releases"]) for c in fq2["chapters"]) == 16


@pytest.mark.unit
def test_cli_idempotent_rerun_semantic(tmp_path: Path) -> None:
    p = _proj(tmp_path)
    assert _run_tool(p).returncode == 0
    first = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    files1 = {f.name: f.read_text(encoding="utf-8") for f in (p / "publish" / "fanqie" / "releases").glob("*.md")}
    assert _run_tool(p).returncode == 0
    second = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    files2 = {f.name: f.read_text(encoding="utf-8") for f in (p / "publish" / "fanqie" / "releases").glob("*.md")}
    assert files1 == files2
    assert {k: v for k, v in first.items() if k != "generated_at"} == {
        k: v for k, v in second.items() if k != "generated_at"
    }


@pytest.mark.unit
def test_cli_freeze_content_drift_hard_error(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    assert _run_tool(p).returncode == 0
    led_path = p / "publish" / "fanqie" / "releases.json"
    led = json.loads(led_path.read_text(encoding="utf-8"))
    led["chapters"][0]["releases"][0]["published"] = True  # ch1 更1 冻结
    led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")
    # frozen chapter re-settled → content-hash drift → hard error, no escape
    ch1 = p / "chapters" / "chapter-1.md"
    ch1.write_text(
        ch1.read_text(encoding="utf-8").replace(
            "星象局誊写所在西廊尽头", "星象局誊写所在西廊尽头，多出来的一句。"  # 首段内容变化 → 更1 哈希必变
        ),
        encoding="utf-8",
    )
    r = _run_tool(p, "--renumber-published")
    assert r.returncode == 1 and "哈希" in r.stderr  # 逃生口不覆盖内容漂移


@pytest.mark.unit
def test_cli_freeze_seq_drift_and_renumber_escape(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    assert _run_tool(p).returncode == 0
    led_path = p / "publish" / "fanqie" / "releases.json"
    led = json.loads(led_path.read_text(encoding="utf-8"))
    # ch2 更1（seq 5）冻结；上游 ch1 扩写后 4 更 → 5 更 → ch2 顺延漂移
    ch2_entry = next(c for c in led["chapters"] if c["chapter"] == 2)
    ch2_entry["releases"][0]["published"] = True
    led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")
    ch1 = p / "chapters" / "chapter-1.md"
    # 追加 7×290=2030 字 → gate 8476+2030=10506 → n=ceil=5、10506/5=2101>=2000 稳 5 更
    # （body 10492 对 5×2000 松弛 492，真实密集段落可行域非空，不降档）→ ch2 顺延漂移
    ch1.write_text(ch1.read_text(encoding="utf-8") + "\n\n" + "结尾补的一段。" * 290, encoding="utf-8")
    r = _run_tool(p)
    assert r.returncode == 1 and "漂移" in r.stderr
    r2 = _run_tool(p, "--renumber-published")
    assert r2.returncode == 0, r2.stderr
    led2 = json.loads(led_path.read_text(encoding="utf-8"))
    pub = [rl for c in led2["chapters"] for rl in c["releases"] if rl["published"]]
    assert len(pub) == 1  # published flag preserved across renumber
    ch1_new = next(c for c in led2["chapters"] if c["chapter"] == 1)
    assert len(ch1_new["releases"]) == 5


@pytest.mark.unit
def test_cli_vanished_chapter_lifecycle(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    assert _run_tool(p).returncode == 0
    # unfrozen chapter vanishes → drop + renumber
    (p / "chapters" / "chapter-1.md").unlink()
    r = _run_tool(p)
    assert r.returncode == 0, r.stderr
    led = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    assert [c["chapter"] for c in led["chapters"]] == [2]
    # frozen chapter vanishes → exit 1
    p2 = _proj(tmp_path / "p2", (1, 2))
    assert _run_tool(p2).returncode == 0
    lp = p2 / "publish" / "fanqie" / "releases.json"
    led2 = json.loads(lp.read_text(encoding="utf-8"))
    led2["chapters"][0]["releases"][0]["published"] = True
    lp.write_text(json.dumps(led2, ensure_ascii=False, indent=2), encoding="utf-8")
    (p2 / "chapters" / "chapter-1.md").unlink()
    r2 = _run_tool(p2)
    assert r2.returncode == 1 and "冻结" in r2.stderr


@pytest.mark.unit
def test_cli_orphan_cleanup(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    assert _run_tool(p).returncode == 0
    rel_dir = p / "publish" / "fanqie" / "releases"
    orphan = rel_dir / "release-9999.md"
    orphan.write_text("stale", encoding="utf-8")
    r = _run_tool(p)
    assert r.returncode == 0, r.stderr
    assert not orphan.exists()
    # referenced files all survive
    led = json.loads((p / "publish" / "fanqie" / "releases.json").read_text(encoding="utf-8"))
    for c in led["chapters"]:
        for rl in c["releases"]:
            assert (rel_dir / rl["file"]).exists()


@pytest.mark.unit
def test_cli_ledger_lifecycle_errors(tmp_path: Path) -> None:
    p = _proj(tmp_path)
    pub = p / "publish" / "fanqie"
    pub.mkdir(parents=True)
    (pub / "releases.json").write_text("{not json", encoding="utf-8")
    r = _run_tool(p)
    assert r.returncode == 1 and "releases" in r.stderr
    (pub / "releases.json").write_text(json.dumps({"schema": "other-v9"}), encoding="utf-8")
    r2 = _run_tool(p)
    assert r2.returncode == 1
    (pub / "releases.json").write_text(
        json.dumps({"schema": "shenbi-releases-v1", "platform": "qidian"}), encoding="utf-8"
    )
    r3 = _run_tool(p)  # fanqie target vs qidian ledger
    assert r3.returncode == 1 and "platform" in r3.stderr


@pytest.mark.unit
def test_cli_structural_exit_codes(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    r = _run_tool(empty)
    assert r.returncode == 1 and "chapters" in r.stderr
    r2 = subprocess.run(
        [sys.executable, str(REPO / "tools" / "release_split.py"), str(empty), "--platform", "nope"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r2.returncode == 2  # argparse usage error
    no2nd = tmp_path / "p2"
    (no2nd / "chapters").mkdir(parents=True)
    (no2nd / "chapters" / "chapter-1.md").write_text("# Chapter 1:\n\n正文。", encoding="utf-8")
    r3 = _run_tool(no2nd)
    assert r3.returncode == 1 and "H1" in r3.stderr
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v -k "cli"`
Expected: FAIL（ImportError: run_split/main 未定义）

- [ ] **Step 3: 实现 run_split/main**

追加到 `tools/release_split.py`：

```python
def load_ledger(platform_dir: Path, platform: str) -> dict[str, Any] | None:
    path = platform_dir / "releases.json"
    if not path.exists():
        return None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ReleaseSplitError(f"releases.json 畸形 JSON: {e}") from e
    if ledger.get("schema") != SCHEMA_ID:
        raise ReleaseSplitError(f"releases.json schema 不符: {ledger.get('schema')!r} != {SCHEMA_ID!r}")
    if ledger.get("platform") != platform:
        raise ReleaseSplitError(
            f"releases.json platform 不符: {ledger.get('platform')!r} != {platform!r}"
        )
    return ledger


def run_split(
    project_dir: Path,
    platform: str,
    title_pattern: str | None,
    renumber_published: bool,
) -> int:
    tier = TIERS[platform]
    files = select_chapter_files(project_dir / "chapters")
    chapters = [parse_chapter(f) for f in files]

    platform_dir = project_dir / "publish" / platform
    rel_dir = platform_dir / "releases"
    rel_dir.mkdir(parents=True, exist_ok=True)
    old = load_ledger(platform_dir, platform)

    # ---- project new ledger ----
    entries: list[dict[str, Any]] = [split_chapter(ch, tier, title_pattern) for ch in chapters]
    by_number = {e["chapter"]: e for e in entries}
    seq = 0
    for e in entries:
        for r in e["releases"]:
            seq += 1
            r["seq"] = seq
            r["file"] = f"release-{seq:04d}.md"

    # ---- freeze / lifecycle validation against old ledger ----
    if old is not None:
        old_by_number = {c["chapter"]: c for c in old.get("chapters", [])}
        for cnum, oc in old_by_number.items():
            pub_rels = [r for r in oc.get("releases", []) if r.get("published")]
            if cnum not in by_number:
                if pub_rels:
                    raise ReleaseSplitError(f"在册章 chapter-{cnum} 已消失且含冻结条目（人工账本手术）")
                continue  # unfrozen vanished → dropped, renumber flows
            new_entry = by_number[cnum]
            if not pub_rels:
                continue
            if len(new_entry["releases"]) < len(pub_rels):
                raise ReleaseSplitError(f"chapter-{cnum} 重切后更数少于冻结更数")
            for k, pr in enumerate(pub_rels):
                nr = new_entry["releases"][k]
                if nr["content_hash"] != pr["content_hash"]:
                    raise ReleaseSplitError(
                        f"chapter-{cnum} 更 {k + 1} 内容哈希漂移于冻结条目（无逃生口，人工账本手术）"
                    )
                if (nr["seq"], nr["file"]) != (pr["seq"], pr["file"]) and not renumber_published:
                    raise ReleaseSplitError(
                        f"chapter-{cnum} 更 {k + 1} 冻结序号/路径漂移: "
                        f"{pr['seq']}/{pr['file']} → {nr['seq']}/{nr['file']}"
                        f"（--renumber-published 逃生口需人工确认平台侧同步改名）"
                    )
                nr["published"] = True

    # ---- write products ----
    totals_rels = [r for e in entries for r in e["releases"]]
    for e in entries:
        for r in e["releases"]:
            (rel_dir / r["file"]).write_text(r["_text"], encoding="utf-8")
    # orphan cleanup: delete files referenced by NO entry of the new ledger
    referenced = {r["file"] for r in totals_rels}
    for f in rel_dir.glob("release-*.md"):
        if f.name not in referenced:
            f.unlink()

    ledger: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "platform": platform,
        "generated_at": datetime.now(UTC).isoformat(),
        "chapters": [
            {
                "chapter": e["chapter"],
                "gate_chars": e["gate_chars"],
                "stripped_chars": e["stripped_chars"],
                "flags": e["flags"],
                "releases": [
                    {k: v for k, v in r.items() if not k.startswith("_")}
                    for r in e["releases"]
                ],
            }
            for e in entries
        ],
        "totals": {
            "releases": len(totals_rels),
            "chars": sum(r["chars"] for r in totals_rels),
            "min_chars": min((r["chars"] for r in totals_rels), default=0),
            "max_chars": max((r["chars"] for r in totals_rels), default=0),
            "cut_quality": {
                q: sum(1 for r in totals_rels if r["cut_quality"] == q)
                for q in ("tension", "scene", "plain", "weak")
            },
            "flags": {
                f: sum(1 for e in entries if f in e["flags"])
                for f in ("single-release", "forced-single", "floor-violation")
            },
        },
    }
    (platform_dir / "releases.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    t = ledger["totals"]
    print(
        f"release-split[{platform}]: chapters={len(entries)} releases={t['releases']} "
        f"chars={t['chars']} min={t['min_chars']} max={t['max_chars']} "
        f"quality={t['cut_quality']} flags={t['flags']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release-split",
        description="发布切分层：已收束章节 → 平台档位发布更（spec #70，纯确定性）",
    )
    parser.add_argument("project_dir", type=Path, help="项目目录（含 chapters/）")
    parser.add_argument("--platform", choices=sorted(TIERS), default="fanqie")
    parser.add_argument("--title-pattern", default=None, help="更题模式（占位符 {章题}/{中文序数}）")
    parser.add_argument("--renumber-published", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_split(args.project_dir, args.platform, args.title_pattern, args.renumber_published)
    except ReleaseSplitError as e:
        print(f"release-split: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

（写盘直接用 `r["_text"]`——split_chapter 已按字节构成备好；账本序列化的 `if not k.startswith("_")` 剥离临时键。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v`
Expected: 全部 passed（约 25 个用例）

- [ ] **Step 5: Commit**

```bash
git add tools/release_split.py tests/unit/tools/test_release_split.py
git commit -m "feat(release-split): T5 CLI+幂等/冻结三元/顺延重编/孤儿清理/平台隔离/账本生命周期"
```

---

### Task 6: 接线（justfile + AGENTS.md）+ 全量门禁 + 试点验收

**Files:**
- Modify: `justfile`（volume-budget 目标后）
- Modify: `AGENTS.md`（Key Commands 一行 + Testing 节一句）

**Interfaces:**
- Consumes: T5 的 `main`
- Produces: `just release-split <dir> [--platform fanqie|qidian]` 入口

- [ ] **Step 1: justfile 目标**（`volume-budget` 目标之后）

```make
# Release split: settled chapters -> platform-sized publish updates (spec #70)
release-split *args:
    uv run python tools/release_split.py "$@"
```

- [ ] **Step 2: AGENTS.md 两处**

Key Commands 清单（`just volume-budget` 行后）加：

```
- `just release-split <dir> [--platform fanqie|qidian]` — 发布切分层：已收束章节 → 平台档位发布更（`publish/<platform>/`，spec #70）
```

Testing 节「Fixtures under `tests/fixtures/` are exclusively real skill outputs...」句后加：

```
Structural unit-test cases (adversarial paragraph layouts, ledger states) may construct inputs inline or via tmp_path — G0.9 forbids fixtures impersonating real skill outputs, not constructed structural inputs.
```

- [ ] **Step 3: 全量门禁**

Run: `just check`
Expected: EXIT=0（ruff/RUF 豁免生效、basedpyright strict 过、契约 lint 不受影响、两段 pytest 全绿）

- [ ] **Step 4: 试点验收（spec §5）**

```bash
PILOT=$(mktemp -d)/proj && mkdir -p "$PILOT/chapters"
for n in 1 2 3 4; do cp novel-xinghuo-vol1/chapters/chapter-$n.md "$PILOT/chapters/"; done
just release-split "$PILOT" --platform fanqie
```

Expected: stdout `releases=13`；`"$PILOT/publish/fanqie/releases.json"` totals.releases == 13；ch1 [2029,2237,2003,2193] 等 §5 锚逐一命中（人工抽查切点阅读感 = 交付后人工步骤，记录进 progress.md）。

- [ ] **Step 5: Commit**

```bash
git add justfile AGENTS.md
git commit -m "feat(release-split): T6 接线——just 目标 + AGENTS.md 命令清单/Testing 澄清 + 试点 13 更验收"
```

---

## 验收覆盖表（spec §5 测试面 → task）

| spec 验收 | task | 验证命令 |
|---|---|---|
| §2 n 公式（含 ch4 回退） | T3 | `pytest -k initial_n` |
| 输入正则排除 | T1 | `pytest -k regex` |
| 带内约束（双档 ≥2000，flags 豁免） | T3/T5 | `pytest -k plan_releases_real`（assert all ≥ floor）+ `cli_first_run` |
| 对账恒等（ch5 三 H1） | T1/T4 | `pytest -k parse_real or entry_shape` |
| 零非空白段丢弃 | T1 | `pytest -k parse_real`（all nonws>0） |
| 降档重启（razor-slack + ch2 真产物锚） | T3 | `pytest -k downgrade` |
| 塌缩 forced-single（4500 构造） | T3 | `pytest -k collapse` |
| flags 矩阵全枚举 | T4/T5 | `pytest -k flags` |
| 单更形态 | T3/T4 | `pytest -k short_chapter or flags` |
| 字节构成 + content_hash 复算 | T4/T5 | `pytest -k byte or first_run` |
| range/head/tail 断言 | T4 | `pytest -k entry_shape` |
| published 三元冻结拒绝 | T5 | `pytest -k freeze` |
| 冻结×顺延冲突 + `--renumber-published` | T5 | `pytest -k renumber` |
| 顺延重编 happy path | T5 | `pytest -k vanished`（删 ch1 后 ch2 重编号） |
| 孤儿清理 | T5 | `pytest -k orphan` |
| 账本生命周期（畸形/schema/platform/消失） | T5 | `pytest -k lifecycle` |
| 幂等重跑（语义比较） | T5 | `pytest -k idempotent` |
| 平台分档隔离 | T5 | `pytest -k isolation` |
| 畸形输入错误契约（exit 1/2） | T1/T5 | `pytest -k structural or exit_codes` |
| 更题生成（缺省/pattern/序数≥10） | T2/T4 | `pytest -k ordinal or title` |
| 打分四档 + 平手确定性 | T2/T3 | `pytest -k tier or scoring_moves` |
| 试点 13 更（§5 仿真定稿） | T6 | 试点命令 stdout + totals |
| G0.9 fixtures（provenance 三态头） | T1 | 文件头 + `just check`（contract/purity lint 面） |

## F947 合规声明

全部验收离线可复验：真实产物断言走 `tests/fixtures/publish/` 副本；无任何真实 LLM dispatch、无 pipeline 子命令、无手写「冒充真实产物」fixture。
