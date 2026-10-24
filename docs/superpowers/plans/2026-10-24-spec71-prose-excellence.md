# 默认文笔惊艳度层（spec #71）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付正向文笔资产层——句长落差/意象母题/金句工艺进指令层（style_seed v2）与测量环（奔涌率+比喻密度+per_chapter），G4.cd 三 WARN 确定性闸，金句-母题传导链机器侧闭合，anchors 自锚定环，破折号预算制，drafting 温度 0.90。

**Architecture:** 单信源原则贯穿——句切分与比喻计数统一落 `gates/shared.py`（既有依赖方向 skill_utils→gates 不变，compute_stats re-export 保 API）；三 WARN 谓词纯函数、`GateStatus.WARN` 进 checks 不进 must_fix（chapter_planning.py:98 先例）；传导链断点在 `load_volume_context` 白名单（机器侧增一行提取）+ drafting PRE/POST 新行（WARN 级、无 backfill 义务——历史项目目录已删）。

**Tech Stack:** Python 3.11+ / pytest / structlog / pathlib；验证走 `just`/`uv run`（与 CI `uv run --frozen` 同构）。

## Global Constraints

- spec：`docs/superpowers/specs/2026-10-24-spec71-prose-excellence.md`（五轮设计审查定稿 f73ccce0）——本 plan 的权威需求源
- 五道硬闸数值一律不动（转折词/AI 标记词/fatigueWords/字数契约/段落下限）；唯一红线变更 = 破折号全禁转预算（≤2/章，解释补充用法仍全禁）
- gate 检查器纯函数幂等、无副作用；`src/shenbi/` 无 `print()`（structlog）；pathlib 文件 I/O
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`；新 WARN id（`G4.cd.surge` 等）是 `id` 键值非 `s` 键——lint_status_strings 无冲突
- 契约变更后 `just lint-contracts` 绿 + `just generate` 派生物幂等（deps.json/docs/skills/index.json——**勿手编 index.json**）
- G0.9：fixtures 只能真实产物；结构性单测用例 inline 构造合法
- F947：全部验收离线（构造输入 + fixtures 驱动测试），零真实 dispatch
- commit 规范：Conventional Commits；**pathspec commit**（禁 `git add -A`）
- 既有依赖方向红线：gates 层零 skill_utils 导入（segment_sentences 迁入 shared 后由 compute_stats 反向 import——方向不变）

---

### Task 1: 单信源基座——segment_sentences 迁入 gates/shared.py + count_similes 新增

**复杂度: infra**（跨模块迁移 + 两消费方契约）· **test_kind: tdd_red_green（count_similes）+ characterization（segment_sentences 迁移行为不变）**

**Files:**
- Modify: `src/shenbi/gates/shared.py`（新增 `SIMILE_MARKERS` 常量 + `QUOTE_PAIR` + `segment_sentences` + `_non_dialogue_text` + `count_similes`；**新增一行 cjk import（现状零 cjk 导入——只 import `find_quote_spans`，`dialogue_char_ratio` 是 T3 的 chapter_drafting.py 自己用的，不进 shared 以免 F401）**）
- Modify: `pyproject.toml`（`src/shenbi/gates/*.py` 的 ruff per-file-ignores 补 `"RUF002"`——中文 docstring 标点；`src/shenbi/skill_utils/**/*.py` 已含同款先例；迁移的 segment_sentences docstring 与两个新 docstring 均触发）
- Modify: `src/shenbi/skill_utils/style_learning/compute_stats.py:20-99`（删 `QUOTE_PAIR`/`segment_sentences` 本体，改 import + re-export）
- Test: `tests/unit/gates/test_shared_prose_primitives.py`（新建）

**Interfaces:**
- Consumes: `find_quote_spans(text: str) -> list[tuple[int, int]]`（cjk.py:60，已存在）、`strip_narrative_body(content: str) -> str`（shared.py:168，已存在）
- Produces（T2/T3 消费，签名一字不差）:
  - `segment_sentences(text: str) -> list[tuple[str, int]]`（原样迁移，行为零变化）
  - `count_similes(content: str) -> dict[str, Any]` → `{"count": int, "non_dialogue_chars": int, "per_1000": float}`——内部先 `strip_narrative_body`（剥五类命名节含 PRE/POST 裸 H2 + META 包裹）再 `find_quote_spans` 剥引号内文字，闭集 `("像", "仿佛", "宛如", "宛若", "恰似", "如同", "似的")` 子串计数于非对白文本；`non_dialogue_chars` = 剥引号后非空白字符数；`per_1000 = round(count * 1000 / non_dialogue_chars, 1)`（0 字时 0.0）

- [ ] **Step 1: 写失败测试（count_similes 三态 + 迁移行为锚）**

```python
"""spec #71 T1: prose primitives single-source in gates/shared.py."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import QUOTE_PAIR, count_similes, segment_sentences

pytestmark = pytest.mark.unit


def test_segment_sentences_migration_anchor() -> None:
    """迁移行为锚：与 compute_stats 时代逐字一致（含 F668 引号内不切/F628 ；切分）。

    char_count 含句末标点（非空白字符数口径）：「然后走了。」= 5。
    """
    text = "他说「今天不错。真的。」然后走了。\n新起一行。"
    sents = segment_sentences(text)
    # 引号内句号不切分 → 「今天不错。真的。」整体一句（12 非空白含引号）
    # + "然后走了。"（5，含句号）+ "新起一行。"（5，含句号）
    assert [c for _, c in sents] == [12, 5, 5]


def test_segment_sentences_reexport_from_compute_stats() -> None:
    """re-export 兼容：既有外部 import 方（test_compute_stats.py）不破。"""
    from shenbi.skill_utils.style_learning import compute_stats

    assert compute_stats.segment_sentences is segment_sentences
    assert compute_stats.QUOTE_PAIR is QUOTE_PAIR


def test_count_similes_basic_and_domain() -> None:
    """计数于非对白域 + strip_narrative_body 域：对白内喻词不计、PRE 自检行不喂饱。"""
    prose = (
        "剑光像一匹扯开的白绢。\n\n"
        "「你别管，这事就像天塌了。」他说。\n\n"
        "远处的山宛如一头伏兽。\n"
    )
    result = count_similes(prose)
    # 对白句（引号内）的「像」不计：只计 剑光像 + 宛如 = 2
    assert result["count"] == 2
    # non_dialogue_chars = 剥引号后非空白（含 H1/标点）——「你别管，这事就像天塌了。」整句剥除
    assert result["non_dialogue_chars"] > 0
    assert result["per_1000"] == round(2 * 1000 / result["non_dialogue_chars"], 1)


def test_count_similes_strips_post_checklist() -> None:
    """R3-C1 回归锚：裸 H2 POST 摘录行（喻词密度最高文本）不得进分子。"""
    content = (
        "## POST_WRITE_SELF_CHECK\n\n"
        "- [ ] 金句位: 他像一棵被雷劈过的树站在那里。\n\n"
        "# 第1章 题目\n\n他像一棵被雷劈过的树站在那里。\n"
    )
    result = count_similes(content)
    # POST 节剥除 → 只数正文 1 处「像」（若不剥 = 2）
    assert result["count"] == 1


def test_count_similes_empty_and_boundaries() -> None:
    assert count_similes("")["count"] == 0
    assert count_similes("")["per_1000"] == 0.0
    # 全对白文本：非对白域 0 字 → per_1000 = 0.0（防除零）
    assert count_similes("「像不像？」")["per_1000"] == 0.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/test_shared_prose_primitives.py -v`
Expected: FAIL（`ImportError: cannot import name 'count_similes'`）

- [ ] **Step 3: 实现——迁移 + 新增**

`src/shenbi/gates/shared.py`（**现状零 cjk 导入**——新增一行 import）：

```python
from shenbi.text.cjk import find_quote_spans
```

在 `META_BLOCK_RE = ...`（:35）附近新增：

```python
# spec #71: simile closed set — substring counting on the non-dialogue domain.
SIMILE_MARKERS: tuple[str, ...] = ("像", "仿佛", "宛如", "宛若", "恰似", "如同", "似的")
```

在 `strip_narrative_body` 之后新增（`QUOTE_PAIR` 常量与 `segment_sentences` 函数体从 `compute_stats.py:22`（QUOTE_PAIR）与 `:46-99`（segment_sentences 含 docstring）**逐字复制迁移**——本 plan 刻意不重复函数体以避免双源漂移，迁移 = 纯 cut-paste 零语义变化，docstring 补一行「迁自 compute_stats.py（spec #71 单信源化）」）：

```python
def _non_dialogue_text(content: str) -> str:
    """PRE/POST 裸 H2 节 + META 包裹剥除后，再剥引号内文字的正文（spec #71 §4.2）。"""
    body = strip_narrative_body(content)
    pieces: list[str] = []
    last = 0
    for start, end in find_quote_spans(body):
        pieces.append(body[last:start])
        last = end
    pieces.append(body[last:])
    return "".join(pieces)


def count_similes(content: str) -> dict[str, Any]:
    """比喻闭集子串计数于非对白域（spec #71 §4.2）。

    分子分母同域：计数与非对白字数都取自 _non_dialogue_text——
    含对白的 total_chars_md_text 分母会把 35-55% 对白占比的测值
    系统性下移约半，带界 [2,4] 与模板写作者语义错位。
    """
    nd = _non_dialogue_text(content)
    non_dialogue_chars = len(nd.replace("\n", "").replace(" ", ""))
    count = sum(nd.count(marker) for marker in SIMILE_MARKERS)
    per_1000 = round(count * 1000 / non_dialogue_chars, 1) if non_dialogue_chars else 0.0
    return {"count": count, "non_dialogue_chars": non_dialogue_chars, "per_1000": per_1000}
```

`src/shenbi/skill_utils/style_learning/compute_stats.py`：删 :20-99 的 `SENT_ENDS`（保留——段落数还用）/`QUOTE_PAIR`/`segment_sentences` 本体，改为：

```python
from shenbi.gates.shared import (  # 单源别名（z11 F1301 扩展，spec #71）
    META_BLOCK_RE,
    QUOTE_PAIR,  # noqa: F401  # re-export 兼容：模块体不再使用，保留给既有 import 方（tests/unit/skill_utils/test_compute_stats.py:24）
    segment_sentences,
)
```

（`META_BLOCK_RE` 既有 import 合并进同一括号；`SENT_ENDS` 若仍被 `segment_paragraphs` 使用则保留原定义。**T2 落地时此括号再扩 `count_similes, strip_narrative_body`**——见 T2 Step 3。）

`pyproject.toml` ruff per-file-ignores：找到 `src/shenbi/gates/*.py` 条目（现状含 B007/RUF001/RUF003 类），**补 `"RUF002"`**（形态对照 `src/shenbi/skill_utils/**/*.py` 的既有条目）。

- [ ] **Step 4: 跑新旧测试确认全绿（迁移零行为变化）**

Run: `uv run pytest tests/unit/gates/test_shared_prose_primitives.py tests/unit/skill_utils/test_compute_stats.py -v`
Expected: 全 PASS（test_compute_stats 既有用例不因迁移失败）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/shared.py src/shenbi/skill_utils/style_learning/compute_stats.py pyproject.toml tests/unit/gates/test_shared_prose_primitives.py
git commit -m "feat: spec #71 T1 单信源基座——segment_sentences+QUOTE_PAIR 迁入 gates/shared + count_similes 非对白域闭集计数"
```

---

### Task 2: compute_stats 升级——奔涌率 + simile 块 + per_chapter 按章映射

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/skill_utils/style_learning/compute_stats.py`（`compute_sentence_stats` 增 `ge35_ratio`；`compute_all_stats` 增 `simile` 块 + `per_chapter` 映射）
- Test: `tests/unit/skill_utils/test_compute_stats.py`（增用例）

**Interfaces:**
- Consumes: T1 的 `count_similes`/`segment_sentences`（re-export）；既有 `compute_ttr(text) -> dict`；`cjk.dialogue_char_ratio(text) -> float`
- Produces（T8 profile 模板消费）:
  - `compute_sentence_stats` 返回 dict 增键 `"ge35_ratio": float`（≥35 字句数 / 句总数，round 4 位；空句列表时既有行为是整 dict 早退为 `{}`——ge35_ratio 随之缺席，保持既有契约不特判）
  - `compute_all_stats` 返回 dict 增两键：
    - `"simile": count_similes(combined_raw)`（**注意：喂原始 combined（META 剥除前）——count_similes 内部自剥**；F634 的 `META_BLOCK_RE.sub` 保留给其余统计）
    - `"per_chapter": {filename: {"total_chars": int, "mean_sentence_len": float, "ttr": float, "dialogue_ratio": float, "ge35_ratio": float}}`——每章独立：`total_chars` = 剥 META 后非空白；`mean_sentence_len` = 该章 segment_sentences 均长 round 1；`ttr` = `compute_ttr(章文本)["global_ttr"]`；`dialogue_ratio` = `round(dialogue_char_ratio(章文本), 4)`；`ge35_ratio` = 该章 ≥35 句占比 round 4

- [ ] **Step 1: 写失败测试**

```python
def test_ge35_ratio_in_sentence_stats() -> None:
    sents = [("短句。", 3), ("这是一条足够长的奔涌句，铺陈蓄势一路推到尽头。", 24), ("x" * 40, 40)]
    stats = compute_sentence_stats(sents)
    assert stats["ge35_ratio"] == round(1 / 3, 4)


def test_compute_all_stats_simile_block() -> None:
    texts = {"chapter-1.md": "他像一棵树。山宛如伏兽。"}
    stats = compute_all_stats(texts)
    assert stats["simile"]["count"] == 2
    assert stats["simile"]["per_1000"] > 0


def test_per_chapter_mapping() -> None:
    """§10 数据基座：多章输入 → 每章独立五列（spec #71 R4-C2）。"""
    surge = "这是一条足够长足够长足够长的句子，铺陈蓄势一路推到三十五字以上的奔涌尽头，再补几个字。"  # ≥40 非空白 ≥35
    assert len(surge.replace(" ", "")) >= 35
    texts = {
        "chapter-1.md": "他走了。" + surge,
        "chapter-2.md": "短。更短。对话也短。",
    }
    stats = compute_all_stats(texts)
    pc = stats["per_chapter"]
    assert set(pc) == {"chapter-1.md", "chapter-2.md"}
    for cols in pc.values():
        assert set(cols) == {"total_chars", "mean_sentence_len", "ttr", "dialogue_ratio", "ge35_ratio"}
    assert pc["chapter-1.md"]["ge35_ratio"] > 0.0
    assert pc["chapter-2.md"]["ge35_ratio"] == 0.0
    assert pc["chapter-1.md"]["total_chars"] > pc["chapter-2.md"]["total_chars"]


def test_per_chapter_ignores_meta_blocks() -> None:
    """裸 H2 PRE/POST 节不计入章统计（与 simile 块同域——spec §4.2 主旨）。"""
    texts = {
        "chapter-1.md": (
            "## PRE_WRITE_CHECK\n\n- [ ] 奔涌句: " + "长" * 40 + "\n\n"
            "# 第1章\n\n正文短句。\n\n## POST_WRITE_SELF_CHECK\n\n- [ ] 金句位: " + "金" * 40 + "\n"
        )
    }
    pc = compute_all_stats(texts)["per_chapter"]
    # 裸 H2 自检节剥除 → 只剩正文 4 字；若只剥 META 包裹，自检行 40 字会进字数
    assert pc["chapter-1.md"]["total_chars"] < 10
    assert pc["chapter-1.md"]["ge35_ratio"] == 0.0  # 自检长行不得白送假奔涌句
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/skill_utils/test_compute_stats.py -v -k "ge35 or simile_block or per_chapter"`
Expected: FAIL（KeyError: 'ge35_ratio' / 'simile' / 'per_chapter'）

- [ ] **Step 3: 实现**

`compute_sentence_stats`（histogram 循环后、return 前增）：

```python
    ge35 = sum(1 for l in lengths if l >= 35)
```

return dict 增 `"ge35_ratio": round(ge35 / n, 4)`。

`compute_all_stats` 增（**per_chapter 的章文本剥域用 `strip_narrative_body`（裸 H2 PRE/POST 也剥——真实 fixtures 以裸 H2 形态为主（chapter-{2,3,4,10}-draft.md 等），自检长行不得白送假奔涌句；与 `simile` 块同域**）；`combined` 现行构造不动）：

```python
    per_chapter: dict[str, dict[str, Any]] = {}
    for fname, raw in texts.items():
        ch = strip_narrative_body(raw)
        ch_sents = segment_sentences(ch)
        lens = [c for _, c in ch_sents]
        ch_total = len(ch.replace("\n", "").replace(" ", ""))
        per_chapter[fname] = {
            "total_chars": ch_total,
            "mean_sentence_len": round(sum(lens) / len(lens), 1) if lens else 0.0,
            "ttr": compute_ttr(ch)["global_ttr"],
            "dialogue_ratio": round(dialogue_char_ratio(ch), 4),
            "ge35_ratio": round(
                sum(1 for l in lens if l >= 35) / len(lens), 4
            ) if lens else 0.0,
        }
```

return dict 增 `"simile": count_similes(combined_raw)`（`combined_raw` = join 后未剥 META 的原文——在现行 `combined = META_BLOCK_RE.sub(...)` 之前取 `"\n\n".join(texts.values())` 的引用）与 `"per_chapter": per_chapter`。**import 面同步扩**（T1 的 gates.shared 括号加两名 + cjk 一行）：

```python
from shenbi.gates.shared import (  # 单源别名（z11 F1301 扩展，spec #71）
    META_BLOCK_RE,
    QUOTE_PAIR,  # noqa: F401
    count_similes,
    segment_sentences,
    strip_narrative_body,
)
from shenbi.text.cjk import dialogue_char_ratio
```

- [ ] **Step 4: 跑测试确认通过 + 全文件回归**

Run: `uv run pytest tests/unit/skill_utils/test_compute_stats.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/style_learning/compute_stats.py tests/unit/skill_utils/test_compute_stats.py
git commit -m "feat: spec #71 T2 compute_stats 奔涌率+simile 块+per_chapter 按章映射（§10 五列数据基座）"
```

---

### Task 3: G4.cd 三 WARN 谓词（surge / simile_band / golden_slot）

**复杂度: infra**（g4 gate 面）· **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`g4_chapter_drafting` 循环内 word_count 检查后增三 WARN 块）
- Test: `tests/unit/gates/g4/test_chapter_drafting.py`（**并入既有文件**——已存在；复用其 fixture/helper 形态，新用例追加）

**Interfaces:**
- Consumes: T1 `count_similes`/`segment_sentences`（from `shenbi.gates.shared`）；`cjk.dialogue_char_ratio`；`total_chars_md_text`（既有 import）
- Produces: checks 列表新 id——`G4.cd.surge` / `G4.cd.simile_band` / `G4.cd.golden_slot`，`"s": GateStatus.WARN`（进 `c` 不进 `mf`——WARN 不阻拦，落 manifest checks 供试点 jq 归集）

- [ ] **Step 1: 写失败测试（三态：触发/不触发/边界）**

```python
"""spec #71 T3: G4.cd prose-excellence WARN predicates (three-state)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
from shenbi.gates.shared import count_similes

pytestmark = pytest.mark.unit

_PRE = (
    "<!--META-BEGIN-->\n## PRE_WRITE_CHECK\n\n"
    "- 本章核心任务: x\n- 本章金句位: 对比｜渡口告别\n- 本章母题物象: 灯 + 风中残焰\n"
    "<!--META-END-->\n\n"
)
_POST = (
    "<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n"
    "- [ ] 金句位: 账上得有数。账上得有过磅这一下。（落位后 2 句内收）\n"
    "<!--META-END-->\n"
)


def _chapter(tmp_path: Path, body: str, pre: str = _PRE, post: str = _POST) -> Path:
    fp = tmp_path / "chapter-1.md"
    fp.write_text(f"{pre}# 第1章 灯\n\n{body}\n\n{post}", encoding="utf-8")
    return fp


def _warn_ids(result_json: str) -> dict[str, str]:
    data = json.loads(result_json)
    return {
        ch["id"]: ch["s"]
        for ch in data.get("checks", [])
        if ch["id"].startswith("G4.cd.surge")
        or ch["id"].startswith("G4.cd.simile")
        or ch["id"].startswith("G4.cd.golden")
    }


def test_surge_warn_triggers_when_below_quota(tmp_path: Path) -> None:
    body = "短句。又短。再短。"  # 0 句 ≥35
    result = g4_chapter_drafting([str(_chapter(tmp_path, body))])
    assert _warn_ids(result).get("G4.cd.surge") == "WARN"


def test_surge_pass_when_quota_met(tmp_path: Path) -> None:
    surge = "他把那盏灯从案上端起来又放下，来回三次，直到油芯里的火苗被门缝挤进来的风压得很低很低，低到几乎要缩进灯座里去。"
    assert len(surge.replace(" ", "")) >= 35
    result = g4_chapter_drafting([str(_chapter(tmp_path, surge + "短句。" * 10))])
    assert _warn_ids(result).get("G4.cd.surge") == "PASS"


def test_surge_dialogue_sentences_excluded(tmp_path: Path) -> None:
    """引号占比 ≥50% 的对白句不算叙述奔涌句。"""
    quoted = "「" + "长" * 40 + "。」"  # 全对白 41 字
    result = g4_chapter_drafting([str(_chapter(tmp_path, quoted))])
    assert _warn_ids(result).get("G4.cd.surge") == "WARN"


def test_simile_band_boundary_and_out(tmp_path: Path) -> None:
    # 带内：filler ~278 非空白字 + 1 喻词 → per_1000 ≈ 3.5 ∈ (2,4)
    filler = "他往前走，尘土在脚下起落。" * 21
    in_band = "山像伏兽。" + filler
    result = g4_chapter_drafting([str(_chapter(tmp_path, in_band))])
    assert _warn_ids(result).get("G4.cd.simile_band") == "PASS"
    # 低位（干燥）：0 喻词 → 0.0 < 2 → WARN
    result = g4_chapter_drafting([str(_chapter(tmp_path, filler))])
    assert _warn_ids(result).get("G4.cd.simile_band") == "WARN"
    # 恰在下带界：500 非空白 + 1 喻词 → per_1000 == 2.0 → PASS（闭区间）
    edge_low = "山像伏兽。" + "他往前走。" * 99  # 5 + 5×99 = 500 非空白
    assert count_similes(edge_low)["per_1000"] == 2.0
    result = g4_chapter_drafting([str(_chapter(tmp_path, edge_low))])
    assert _warn_ids(result).get("G4.cd.simile_band") == "PASS"
    # 恰在上带界：250 非空白 + 1 喻词 → per_1000 == 4.0 → PASS（闭区间）
    edge_high = "山像伏兽。" + "他往前走。" * 49  # 5 + 5×49 = 250 非空白
    assert count_similes(edge_high)["per_1000"] == 4.0
    result = g4_chapter_drafting([str(_chapter(tmp_path, edge_high))])
    assert _warn_ids(result).get("G4.cd.simile_band") == "PASS"
    # 高位（堆砌）：16 喻词 / ~121 非空白 → per_1000 ≈ 132 > 4 → WARN
    piled = "山像伏兽，像伏兽中的伏兽。" * 8 + "他走了。" * 3
    result = g4_chapter_drafting([str(_chapter(tmp_path, piled))])
    assert _warn_ids(result).get("G4.cd.simile_band") == "WARN"


def test_surge_quota_two_boundary(tmp_path: Path) -> None:
    """spec §6.1 锚例：≥6000 字章配额 2——恰 2 处达标 / 1 处触发。"""
    surge = (
        "他把那盏灯从案上端起来又放下，来回三次，直到油芯里的火苗被门缝挤进来的风"
        "压得很低很低，低到几乎要缩进灯座里去。"
    )
    assert len(surge.replace(" ", "")) >= 35
    # filler 19 非空白字/句 × 320 = 6080 非空白（≥6000 → 配额 2）
    filler = "夜色沉下去，他数着更漏，一更一更地挨。" * 320
    assert len(filler.replace(" ", "")) + len(surge) >= 6000
    two = g4_chapter_drafting([str(_chapter(tmp_path, surge + "短句。他再想。" + surge + filler))])
    assert _warn_ids(two).get("G4.cd.surge") == "PASS"  # 2 处 ≥ quota 2
    one = g4_chapter_drafting([str(_chapter(tmp_path, surge + filler))])
    assert _warn_ids(one).get("G4.cd.surge") == "WARN"  # 1 处 < quota 2


def test_golden_slot_full_tates(tmp_path: Path) -> None:
    # 完整 PRE/POST → PASS
    result = g4_chapter_drafting([str(_chapter(tmp_path, "正文。"))])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "PASS"
    # PRE 行值空（去 [] 后空串）→ WARN
    empty_pre = _PRE.replace("- 本章金句位: 对比｜渡口告别", "- 本章金句位: []")
    result = g4_chapter_drafting([str(_chapter(tmp_path, "正文。", pre=empty_pre))])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "WARN"
    # PRE 行值为「无」→ WARN
    none_pre = _PRE.replace("- 本章金句位: 对比｜渡口告别", "- 本章金句位: 无")
    result = g4_chapter_drafting([str(_chapter(tmp_path, "正文。", pre=none_pre))])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "WARN"
    # 全角冒号容错 → PASS
    wide_pre = _PRE.replace("- 本章金句位: 对比｜渡口告别", "- 本章金句位：对比｜渡口告别")
    result = g4_chapter_drafting([str(_chapter(tmp_path, "正文。", pre=wide_pre))])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "PASS"
    # POST 金句摘录缺失 → WARN
    result = g4_chapter_drafting([str(_chapter(tmp_path, "正文。", post=""))])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "WARN"


def test_bare_h2_forms_supported(tmp_path: Path) -> None:
    """裸 H2 形态（无 META 包裹）同样受检——真实 fixtures 实证形态。"""
    fp = tmp_path / "chapter-2.md"
    fp.write_text(
        "## PRE_WRITE_CHECK\n\n- 本章金句位: 对比｜灯\n\n# 第2章\n\n短句。\n\n"
        "## POST_WRITE_SELF_CHECK\n\n- [ ] 金句位: 白天漏灰，夜里漏光。\n",
        encoding="utf-8",
    )
    result = g4_chapter_drafting([str(fp)])
    assert _warn_ids(result).get("G4.cd.golden_slot") == "PASS"
```

（若该 path 既有 `test_chapter_drafting.py`，用例并入并复用其 fixture helper——以仓库现状为准。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/g4/ -v -k "surge or simile or golden"`
Expected: FAIL（`_warn_ids` 返回空 dict——id 不存在）

- [ ] **Step 3: 实现（g4_chapter_drafting 循环内、word_count 块后新增）**

（**helpers 提升到循环体之外**（`g4_chapter_drafting` 函数顶部、`for fp in fps` 之前——循环体内定义会触发 ruff B023）：

```python
    _GOLDEN_PRE_RE = re.compile(r"^\s*-\s*本章金句位\s*[:：]\s*(.*)$", re.MULTILINE)
    _GOLDEN_POST_RE = re.compile(r"^\s*-\s*\[.\]\s*金句位\s*[:：]\s*(.+)$", re.MULTILINE)
    _EMPTY_VALUES = frozenset({"", "无", "N/A", "待定"})
```

循环体内（word_count 块后新增）：）

```python
        # spec #71 prose-excellence WARN predicates (WARN-level: recorded in
        # checks for the pipeline manifest, never in must_fix).
        narrative = strip_narrative_body(content)
        sents = segment_sentences(narrative)
        narrative_surge = sum(
            1
            for sent, slen in sents
            if slen >= 35 and dialogue_char_ratio(sent) < 0.5
        )
        surge_quota = max(1, total // 3000)  # 复用 :324 已算的 total（total_chars_md_text 同值）
        if narrative_surge < surge_quota:
            c.append(
                {
                    "id": "G4.cd.surge",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": f"narrative surge sentences {narrative_surge} < quota {surge_quota}",
                }
            )
        else:
            c.append(
                {
                    "id": "G4.cd.surge",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "surge": narrative_surge,
                    "quota": surge_quota,
                }
            )

        simile_stats = count_similes(content)
        if 2.0 <= simile_stats["per_1000"] <= 4.0:
            c.append(
                {
                    "id": "G4.cd.simile_band",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "per_1000": simile_stats["per_1000"],
                }
            )
        else:
            c.append(
                {
                    "id": "G4.cd.simile_band",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": (
                        f"simile density {simile_stats['per_1000']}/千字 outside "
                        "[2,4] (low = dry, high = pile-up; 俗套喻体抽检归审计)"
                    ),
                    "per_1000": simile_stats["per_1000"],
                }
            )

        pre_block = re.search(
            r"## PRE_WRITE_CHECK.*?(?=## |# |<!--META|\Z)", content, re.DOTALL
        )
        post_block = re.search(
            r"## POST_WRITE_SELF_CHECK.*?(?=## |# |<!--META|\Z)", content, re.DOTALL
        )

        golden_issues: list[str] = []
        pre_val: str | None = None
        if pre_block:
            m = _GOLDEN_PRE_RE.search(pre_block.group(0))
            if m:
                pre_val = m.group(1)
        if pre_val is None or pre_val.strip().strip("[]").strip() in _EMPTY_VALUES:
            golden_issues.append("PRE lacks non-empty 金句位 line")
        post_ok = False
        if post_block:
            if _GOLDEN_POST_RE.search(post_block.group(0)):
                post_ok = True
        if not post_ok:
            golden_issues.append("POST lacks 金句 excerpt line")
        if golden_issues:
            c.append(
                {
                    "id": "G4.cd.golden_slot",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "; ".join(golden_issues),
                }
            )
        else:
            c.append({"id": "G4.cd.golden_slot", "file": fp, "s": GateStatus.PASS})
```

import 区扩展 `from shenbi.gates.shared import (...)` 增 `count_similes`, `segment_sentences`；增 `from shenbi.text.cjk import dialogue_char_ratio`。（`re` 已 import。）

- [ ] **Step 4: 跑测试 + 既有 G4.cd 回归**

Run: `uv run pytest tests/unit/gates/g4/ -v`
Expected: 全 PASS（既有 drafting 用例不断言清单全集，新 WARN 不打红任何既有断言；若有失败按 Anti-Rationalization 处理——不删既有断言，修谓词）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/unit/gates/g4/
git commit -m "feat: spec #71 T3 G4.cd 三 WARN——surge 配额/simile 双向带/golden_slot PRE+POST（全角冒号容错+空值操作化）"
```

---

### Task 4: 传导链机器侧——load_volume_context 增行提取 + OPTIONAL_READS

**复杂度: infra**（pipeline 派发面）· **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/pipeline/_shared.py:363`（`load_volume_context` 增「金句、母题物象与梗位」行提取）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:533-538`（`OPTIONAL_READS["shenbi-chapter-drafting"]` 增 `"style/anchors.md"`）
- Test: `tests/unit/pipeline/test_context_assemble.py`（增用例——`project_with_volume_map` fixture :252 先例）+ `tests/unit/pipeline/test_dispatch_helper.py`（OPTIONAL_READS 增断言）

**Interfaces:**
- Consumes: `load_volume_context(project_dir: Path, chapter: int) -> str` 既有六分支提取；`OPTIONAL_READS: dict[str, list[str]]`
- Produces: `load_volume_context` 返回文本新增一段 `**金句、母题物象与梗位**: …`（卷区段头部元数据区原文行；行缺失时不追加——旧卷纲无该行零破坏）；drafting reads `style/anchors.md` 缺席不再 G1 阻断

- [ ] **Step 1: 写失败测试**

test_context_assemble.py 增：

```python
def test_load_volume_context_includes_quote_motif_line(
    project_with_volume_map: Path,
) -> None:
    """spec #71 T4: 卷头部金句母题行进提取面（断链闭合机器侧落点）。"""
    vm = project_with_volume_map / "outline" / "volume_map.md"
    vm_text = vm.read_text(encoding="utf-8")
    # 注入 spec #71 扩名行（卷区段头部、### Key Results 之前）——若 fixture
    # 卷区段已含该行则跳过注入
    if "金句、母题物象与梗位" not in vm_text:
        vm.write_text(
            vm_text.replace(
                "### Key Results",
                "**金句、母题物象与梗位**: [金句出场点｜灯-残焰母题每卷变奏｜卷末彩蛋]\n\n### Key Results",
                1,
            ),
            encoding="utf-8",
        )
    from shenbi.pipeline._shared import load_volume_context

    ctx = load_volume_context(project_with_volume_map, 1)
    assert "金句、母题物象与梗位" in ctx
    assert "灯-残焰母题" in ctx


def test_load_volume_context_old_volume_map_unchanged(
    project_with_volume_map: Path,
) -> None:
    """旧卷纲（无该行）零破坏——行缺失时不追加空段。"""
    from shenbi.pipeline._shared import load_volume_context

    vm = project_with_volume_map / "outline" / "volume_map.md"
    if "金句、母题物象与梗位" in vm.read_text(encoding="utf-8"):
        pytest.skip("fixture already carries the line")
    ctx = load_volume_context(project_with_volume_map, 1)
    assert ctx  # 既有六分支输出不受影响
    assert "金句、母题物象与梗位" not in ctx
```

test_dispatch_helper.py 增（对齐既有 OPTIONAL_READS 测试族形态）：

```python
def test_optional_reads_includes_anchors() -> None:
    """spec #71: anchors 前 12 章缺席是常态（首次重测才生成），不阻断 G1。"""
    from shenbi.pipeline.dispatch_helper import OPTIONAL_READS

    assert "style/anchors.md" in OPTIONAL_READS["shenbi-chapter-drafting"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_dispatch_helper.py -v -k "quote_motif or anchors or optional_reads_includes"`
Expected: FAIL（AssertionError——提取面不含该行 / OPTIONAL_READS 无键）

- [ ] **Step 3: 实现**

`_shared.py` `load_volume_context`——卷 section 匹配后（`vol_section` 取得处）增：

```python
    # spec #71: volume-header quote/motif/gag line (金句、母题物象与梗位).
    # Old volume maps without the line are unaffected (no append on miss).
    if vol_section:
        qm_match = re.search(
            r"^\*\*金句、母题物象与梗位\*\*\s*[:：]\s*(.+)$",
            vol_section,
            re.MULTILINE,
        )
        if qm_match:
            parts.append(f"**金句、母题物象与梗位:** {qm_match.group(1).strip()}\n")
```

（插入位置钉死：**`vol_section` 赋值行（现行 :411）之后、张力曲线提取块（:413-417）之前**——`vol_section` 在 Objective 提取之后才定义，勿插在其前；`re` 已在模块内 import。）

`dispatch_helper.py` OPTIONAL_READS drafting 列表（`"style/style_directives.md",` 行后）增：

```python
        # spec #71: self-anchored exemplar file — absent until the first
        # style-learning re-measure (ch12/volume boundary) produces it.
        "style/anchors.md",
```

- [ ] **Step 4: 跑测试确认通过 + 两文件全量回归**

Run: `uv run pytest tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: spec #71 T4 传导链机器侧——load_volume_context 增金句母题行提取 + OPTIONAL_READS 接 anchors.md"
```

---

### Task 5: style_seed 模板 v2 重写

**复杂度: leaf** · **test_kind: tdd_red_green（快照断言改写）**

**Files:**
- Modify: `src/shenbi/pipeline/style_seed.py`（`DEFAULT_STYLE_DIRECTIVES` 全文替换为 spec §2 模板 + docstring 叙事更新）
- Test: `tests/unit/pipeline/test_style_seed.py`（既有快照断言改 + 新节断言；write-if-absent 两测不动）

**Interfaces:**
- Consumes: 无
- Produces: `DEFAULT_STYLE_DIRECTIVES` v2 全文（spec §2 逐字——含「节奏与句法/意象与修辞/金句/对白/叙述配比/章型微调」六节）；`seed_style_directives` 语义零变化

- [ ] **Step 1: 改测试（红）**

test_style_seed.py 的 `test_seed_writes_default_when_absent` 增节断言，**并同步改既有 v1 字面断言**（:67-68 附近的 prompt-injection 断言族）：

```python
    # 既有 :67「叙述句目标带：10-20 字/句」断言 → v2 基带
    # 既有 :68「文风目标（通用默认模板）」标题断言 → v2 标题（若两断言在其他测试内，同批改）
    assert "叙述句基带：12-25 字/句" in DEFAULT_STYLE_DIRECTIVES
    assert "文风目标（通用默认模板 v2）" in DEFAULT_STYLE_DIRECTIVES
    for section in ("节奏与句法", "意象与修辞", "金句", "对白/叙述配比"):
        assert f"## {section}" in DEFAULT_STYLE_DIRECTIVES
    # v2 重锚锚点（spec §2）
    assert "奔涌长句" in DEFAULT_STYLE_DIRECTIVES
    assert "每千字 2-4 处" in DEFAULT_STYLE_DIRECTIVES
    assert "白天漏灰，夜里漏光" in DEFAULT_STYLE_DIRECTIVES
    assert "≥16 字" not in DEFAULT_STYLE_DIRECTIVES  # 伪长句定义已删
    assert "10-20" not in DEFAULT_STYLE_DIRECTIVES  # v1 基带已换
```

（先 `grep -n "10-20\|通用默认模板" tests/unit/pipeline/test_style_seed.py` 定位全部 v1 字面断言——**逐一改为 v2 对应字面；改的是断言里的字面子串，断言目标（DEFAULT_STYLE_DIRECTIVES 或 user_prompt 注入证明）一律保留**——注入证明测试是 load-bearing，只换字面不删断言。）

（既有 `test_seed_never_clobbers_user_edits` 的 write-if-absent 语义零改动——只有字面断言随模板更新。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_style_seed.py -v`
Expected: FAIL（"金句" 节不存在）

- [ ] **Step 3: 实现——DEFAULT_STYLE_DIRECTIVES 替换为 spec §2 模板代码块全文（逐字复制）+ 模块 docstring 更新**

docstring 变更点：`session31 Q1` 叙事补 `spec #71 v2（六人共性带重锚：基带 12-25/奔涌收割配额/比喻双向带/金句三写法/母题行）`。

- [ ] **Step 4: 跑测试确认通过（含注入证明测试）**

Run: `uv run pytest tests/unit/pipeline/test_style_seed.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/style_seed.py tests/unit/pipeline/test_style_seed.py
git commit -m "feat: spec #71 T5 style_seed 模板 v2——六人共性带重锚（12-25 基带/奔涌收割/比喻双向带/金句三写法/母题行）"
```

---

### Task 6: drafting SKILL 面 + anti-ai-reference 破折号预算行

**复杂度: leaf**（SKILL 文档面 + 契约 frontmatter）· **test_kind: regression_guard（lint-contracts + 快照类断言）**

**Files:**
- Modify: `skills/shenbi-chapter-drafting/SKILL.md`（frontmatter reads 增 `style/anchors.md`；创作原则 5 升级/7 反向档/10 新增；PRE 两行；POST 两项；输出格式模板同步）
- Modify: `skills/shenbi-chapter-drafting/anti-ai-reference.md:10`（破折号行改预算制）
- Test: 契约面由 `just lint-contracts` + `just generate` 幂等守（无独立 pytest——SKILL 文字面无行为测试先例；PRE/POST 行格式已由 T3 谓词测试锁定）

**Interfaces:**
- Consumes: T3 谓词的行格式（`- 本章金句位: [对比/反差/口诀化｜落点场景]`、`- 本章母题物象: [卷纲物象 + 本章变奏]`、POST `- [ ] 金句位: [原句摘录]`）
- Produces: drafting 契约 reads 含 `style/anchors.md`（T8 的 style-learning writes 形成闭环——**两契约必须同批落地否则 ORPHAN_READ 红**：本 task 先加 reads 会让 lint_contract_graph 报 drafting 读无生产者——执行顺序上 T6 与 T8 的契约行在同一 `just check` 前完成即可；若单 task commit 后跑 lint-contracts，安排 T8 紧随或本 task 先不加、挪到 T8——**选择：reads 行放 T8 与 writes 同批**，本 task 只改文字面，避免中间态 lint 红）

- [ ] **Step 1: SKILL.md 文字面改动（无 TDD——文档面，验收靠 lint + T3 谓词）**

1. 创作原则 5「对话指纹」：`**对话指纹** — 角色说话必须匹配 voice_profile` → 增 `；关键对白三层结构：信息／关系变化／潜台词至少推进其一（潜台词三法：答非所问／一语双关／反话克制）`
2. 创作原则 7 高潮档：`高潮拍允许短句连排后接一句收束长句` → `高潮 = 斩截与咏叹交替——短句连排后允许 1-2 句 ≥35 字咏叹长句（反向档）`
3. 新增原则 10：`10. **落差工艺** — 长句蓄势短句收割；三叠句刀刃使用（高潮/悲拍每章 ≤1 处）；点染收尾——章尾情绪落物象不落陈述`
4. PRE_WRITE_CHECK 清单与输出格式模板：`- 感官锚:` 行后增两行（见 Interfaces；同时更新 :133 输出格式模板与 :90 自检表清单保持三处同步）
5. POST_WRITE_SELF_CHECK：`- [ ] 微粒钩:` 行后增 `- [ ] 奔涌句: 每场景 ≥1 句 ≥35 字 = [场景1: 原句摘录 / 场景2: …]` 与 `- [ ] 金句位: [原句摘录]（落位后 2 句内收；摘不出原句 = 未达标，先补再输出）`（自检表 :154 与输出格式 :133 两处同步）

anti-ai-reference.md:10：

```markdown
| 破折号 "——" | 每章 ≤2 处：仅限咏叹收束（长句末尾情绪延宕）与对话打断（话被截断）；解释补充用法（"他深吸一口气——这不可能"类）仍然全禁——改用句号断句或冒号引出 |
```

- [ ] **Step 2: 验证——G4.cd 谓词与新行格式匹配（T3 测试已锁）+ 手动 smoke**

Run: `uv run pytest tests/unit/gates/g4/ -k "golden or surge" -v`
Expected: PASS（谓词-模板格式一致性由 T3 测试结构保证）

Run: `uv run python -c "import re; t=open('skills/shenbi-chapter-drafting/SKILL.md').read(); assert '- 本章金句位: [对比/反差/口诀化｜落点场景]' in t; assert '- 本章母题物象: [卷纲物象 + 本章变奏]' in t; assert re.search(r'## 10|10\. \*\*落差工艺', t); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-chapter-drafting/SKILL.md skills/shenbi-chapter-drafting/anti-ai-reference.md
git commit -m "feat: spec #71 T6 drafting SKILL 原则 5/7/10 + PRE 母题金句两行 + POST 奔涌金句两项 + anti-ai 破折号预算行"
```

---

### Task 7: 传导链 SKILL 面——planning 备忘两行 + volume-outlining 行扩名

**复杂度: leaf** · **test_kind: regression_guard（lint + T4 机器侧测试闭环）**

**Files:**
- Modify: `skills/shenbi-chapter-planning/SKILL.md`（备忘段 1 模板增 `**金句位**: [对比/反差/口诀化｜落点场景]`、`**母题物象**: [卷纲物象 + 本章变奏]` 两行——对齐既有 `**payoff 拍**:` 加粗行式；**插点：段 1 内 `**payoff 拍**` 行之后、段 2 之前**）
- Modify: `skills/shenbi-volume-outlining/SKILL.md`（:132 `金句与梗位行` 扩名「金句、母题物象与梗位」+ 新增母题物象指定语；:157 模板行 `**金句与梗位**: [...]` → `**金句、母题物象与梗位**: [金句出场点（对齐 seed 金句库排期）｜母题物象（每卷 1-2 个核心物象 + 变奏提示）｜梗位复用｜卷末彩蛋]`；:298 自检行同步）

**Interfaces:**
- Consumes: T4 `load_volume_context` 提取行名（`金句、母题物象与梗位`——SKILL 行名与提取 regex 一字对齐）
- Produces: planning 备忘段 1 两行（T6 drafting PRE 行的上游对接口——`从备忘段 1 读`）

- [ ] **Step 1: 文字面改动（无独立 pytest——G4.cp sections 检查 8 段计数不变、quote_line regex 兼容已验）**

volume-outlining :132 段落改写：`**金句、母题物象与梗位行（P2-6，G4.vo.quote_line WARN 级）**：每卷区段带一行——本卷金句出场点（对齐 seed 金句库的排期）/ 母题物象（每卷指定 1-2 个核心物象，卷内每章 ≥1 次变奏复现、语境须不同）/ 梗位复用（跨章复用的记号）/ 卷末彩蛋。金句是传播资产；母题物象是卷的意象脊柱（六人共性带：画面靠具象名词）。`

- [ ] **Step 2: 验证——quote_line regex 对扩名行命中 + lint**

Run: `uv run python -c "import re; assert re.search('金句|梗位|彩蛋', '**金句、母题物象与梗位**: [x]'); print('ok')"`
Expected: `ok`

Run: `just lint-contracts`
Expected: 绿（两 SKILL 未动 reads/writes）

- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-chapter-planning/SKILL.md skills/shenbi-volume-outlining/SKILL.md
git commit -m "feat: spec #71 T7 传导链 SKILL 面——planning 备忘段 1 金句位/母题物象两行 + volume-outlining 行扩名"
```

---

### Task 8: style-learning 面 + drafting reads 契约闭环 + truth 注册

**复杂度: infra**（契约三源 + 生成物）· **test_kind: regression_guard（lint + generate 幂等）+ tdd_red_green（温度断言）**

**Files:**
- Modify: `skills/shenbi-style-learning/SKILL.md`（统计指标目录节 `### 1.`/`### 5.` 增两指标条目；profile 输出模板 §1 表增「≥35 字句占比」行、§6 表增「比喻密度（处/千字）」行、§10 表增「≥35 字句占比」列；铁律 2 增 anchors 例外条款；输出节增 anchors.md 产出说明 + 最小骨架；frontmatter writes 增 `style/anchors.md`）
- Modify: `skills/shenbi-chapter-drafting/SKILL.md`（frontmatter reads 增 `style/anchors.md`——与 style-learning writes 同批，ORPHAN_READ 闭环）
- Modify: `docs/framework/truth-files.yaml`（style 族增 `- {name: style/anchors.md, kind: style}`）
- Modify: `executor_config.toml` drafting overrides 段（`[overrides."shenbi-chapter-drafting"]` 下 `temperature = 0.85` 行（:10，段头 :9）→ `temperature = 0.90` + 行尾注释 `# spec #71: anti-RLHF-mean-reversion（回退判据见 spec §5.2）`）
- Test: `tests/unit/pipeline/test_executor_config.py`（新建或并入既有 config 测试——温度值断言）+ 契约面 `just generate` 幂等

**Interfaces:**
- Consumes: T2 `per_chapter`（§10 五列数据基座）、`simile` 块（§6 比喻密度行）、`ge35_ratio`（§1 行）
- Produces: `style/anchors.md` 注册为 truth concept（kind: style）；drafting↔style-learning 契约闭环

- [ ] **Step 1: 写温度断言测试（红）**

```python
"""spec #71 T8: drafting temperature single-arm change (0.85 → 0.90)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_drafting_temperature_is_090() -> None:
    cfg = tomllib.loads((_REPO_ROOT / "executor_config.toml").read_text(encoding="utf-8"))
    assert cfg["overrides"]["shenbi-chapter-drafting"]["temperature"] == 0.90
```

Run: `uv run pytest tests/unit/pipeline/test_executor_config.py -v` → Expected: FAIL（== 0.85）

- [ ] **Step 2: SKILL.md + 契约 + 配置实现**

1. style-learning frontmatter `writes:` 增 `- file: style/anchors.md\n    mode: create_or_overwrite`（对齐 style_profile.md 行式）
2. drafting frontmatter `reads:` 增 `- style/anchors.md`（对齐 `style/style_directives.md` 行式）
3. 铁律 2 改：`**统计而非评判** — 输出"是什么"，不输出"好不好"（**例外：anchors.md**——自锚定范文环是该技能唯一下沉到产物的评判面，选取标准半操作化见输出节）`
4. 统计指标目录 `### 1. 句长分布` 增 `- ≥35 字句占比（奔涌率）`；`### 5. 修辞模式` 增 `- 比喻密度（闭集计数/非对白域千字）`
5. profile 输出模板 §1 表增 `| ≥35 字句占比 | N% |`；§6 表增 `| 比喻密度 | N 处/千字 |`；§10 表头改 `| 章 | 字数 | 句长均值 | TTR | 对白占比 | ≥35 字句占比 |`（数据源 = compute_stats per_chapter——五列全部有脚本生产者）
6. 输出节增 anchors 小节（spec §4.3 全文照搬：重测时机/三类段各 ≥1/≤300 字/出处章号+示范点指认/最小骨架/整文件重写/铁律例外引用）
7. truth-files.yaml style 族增 `- {name: style/anchors.md, kind: style}`
8. executor_config.toml drafting temperature 0.90 + 注释

- [ ] **Step 3: 契约三源同步验证**

Run: `just generate && git status --short`
Expected: 生成物 diff（**真实路径**：`tests/tiers/deps.json` + `docs/framework/truth-files.index.json` + `skills/*/SKILL.md` body view——首次再生成含 anchors 键）——**确认后二次运行 diff 为空（幂等）**

Run: `just lint-contracts && uv run python tools/lint_registry_reconcile.py`
Expected: 双绿（ORPHAN_READ 闭环：drafting reads anchors.md ← style-learning writes；index.json concept 键 ⊆ yaml concepts）

- [ ] **Step 4: 温度测试转绿 + 全量回归**

Run: `uv run pytest tests/unit/pipeline/test_executor_config.py tests/unit/skill_utils/ -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-style-learning/SKILL.md skills/shenbi-chapter-drafting/SKILL.md docs/framework/truth-files.yaml executor_config.toml tests/unit/pipeline/test_executor_config.py
git commit -m "feat: spec #71 T8 style-learning 测量面+anchors 产出 + drafting reads 契约闭环 + truth 注册 + 温度 0.90"
```

（**生成物** `tests/tiers/deps.json`、`docs/framework/truth-files.index.json`、以及 `skills/*/SKILL.md` 自身的 body view 再渲染（sync_contracts `render_body_into` 直写 SKILL.md——若 diff 出现且非本 task 手改内容，一并 pathspec add）——它们是 `just generate` 的合法产物，勿手编。）

---

### Task 9: 破折号执法面 + 框架文档 + 全批验收

**复杂度: leaf** · **test_kind: regression_guard（文档面 + 全批 just check）**

**Files:**
- Modify: `skills/shenbi-review-group-craft/SKILL.md` 检查 3（`3. 破折号检测` → 预算口径全文）
- Modify: `skills/shenbi-review-anti-ai/SKILL.md` 检查 3（同口径改写 + reference-only 注记）**+ :99 示例表行与 :105 BLOCKING 修复示例行**（全禁口径残留——同文件矛盾即照抄源）
- Modify: `docs/framework/style-directives.md`（**§2 :20「叙述句 10-20 字」→ 12-25**；§3 标准结构小节列 v2 六节名 + **§3 内嵌示例模板体整块替换为单一信源指向**：「示例全文见 `style_seed.py` 的 `DEFAULT_STYLE_DIRECTIVES`（pipeline-init 播种模板，v2）」——避免文档与播种模板双源漂移；:58 破折号条款改预算制表述）
- Test: 全批 `just check`（阶段 7 权威门禁）

**Interfaces:**
- Consumes: spec §5.1 预算口径（>2 = ERROR；≤2 解释补充用法 = ERROR；合法 ≤2 = pass；计数 `——`/`──`）
- Produces: 框架变更记录（本 spec 即「解除破折号禁令须走框架变更」条款的变更载体）

- [ ] **Step 1: 文字面改动**

group-craft 检查 3：

```markdown
3. 破折号检测 — 预算制（spec #71）：每章 ≤2 处 `——`/`──`。仅两种合法用法：咏叹收束（长句末尾情绪延宕）、对话打断（话被截断）。>2 处 = ERROR；≤2 处但属解释补充用法（"他深吸一口气——这不可能"类）= ERROR；合法用法 ≤2 = pass
```

review-anti-ai 检查 3 同口径 + 行尾 `(reference-only：本技能已 RETIRED，活执法面在 review-group-craft 检查 3——此文件仅存档参考)`；:99 示例行改 `| 3 | 破折号 | ERROR | 第3段 3 处"——"（>2 预算）或解释补充用法 |`；:105 改 `[BLOCKING/CRITICAL] 破折号预算违例（3 处 >2 或属解释补充用法）：删多余处或改句号断句；合法咏叹/打断用法 ≤2 处保留`。

style-directives.md：§3「标准结构」小节列 v2 六节名（节奏与句法/意象与修辞/金句/对白/叙述配比/章型微调）；:58 条款改：

```markdown
也就是说：想要长句文风，写「句长目标带 12-25 字」可以；破折号已转**预算制**（每章 ≤2 处、仅限咏叹收束与对话打断，解释补充用法全禁——spec #71 框架变更），项目配置不得再放宽预算。
```

- [ ] **Step 2: 全批门禁（阶段 7 预跑）**

Run: `just check`
Expected: EXIT=0（lint 全面 + 两段 pytest + coverage ≥85）

- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-review-group-craft/SKILL.md skills/shenbi-review-anti-ai/SKILL.md docs/framework/style-directives.md
git commit -m "feat: spec #71 T9 破折号活执法面预算口径 + 框架文档同步（style-directives v2 结构/预算条款）"
```

---

## 验收覆盖表（spec §6 → task → 可执行验证）

| spec 验收条目 | Task | 验证命令 |
|---|---|---|
| §6.1 compute_stats 奔涌率/比喻密度构造断言 | T1/T2 | `uv run pytest tests/unit/gates/test_shared_prose_primitives.py tests/unit/skill_utils/test_compute_stats.py -v` |
| §6.1 re-export 兼容断言 | T1 | `test_segment_sentences_reexport_from_compute_stats` |
| §6.1 per_chapter 按章映射断言 | T2 | `test_per_chapter_mapping` + `test_per_chapter_ignores_meta_blocks` |
| §6.1 G4.cd 三 WARN 三态（7145 字章 2 处达标/1 处触发；密度 2.0/4.0 带界；PRE 空值触发） | T3 | `uv run pytest tests/unit/gates/g4/ -k "surge or simile or golden" -v` |
| §6.1 load_volume_context 新行提取（加粗形态） | T4 | `test_load_volume_context_includes_quote_motif_line`（fixtures 驱动 test_context_assemble.py） |
| §6.1 OPTIONAL_READS 缺席容忍 | T4 | `test_optional_reads_includes_anchors` |
| §6.1 executor_config 温度 0.90 值断言 | T8 | `test_drafting_temperature_is_090` |
| §6.1 style_seed 快照断言 + write-if-absent 幂等 | T5 | `uv run pytest tests/unit/pipeline/test_style_seed.py -v` |
| §6.1 契约面 lint_registry_reconcile + lint-contracts + just generate 幂等 | T8 | `just lint-contracts && uv run python tools/lint_registry_reconcile.py && just generate`（二次 diff 空） |
| §6.1 PRE/POST 新行 G4 机械检查（META 提取复用 shared） | T3 | `test_bare_h2_forms_supported` + golden_slot 全态 |
| §2 模板 v2 全文（六节/锚点句/伪长句删除） | T5 | `test_seed_writes_default_when_absent` 扩展断言 |
| §3 drafting 原则 5/7/10 + PRE/POST | T6 | smoke 断言命令（Step 2）+ T3 谓词锁格式 |
| §4.1 传导链（volume 扩名/planning 两行/机器侧提取） | T4/T7 | T4 pytest + T7 regex smoke |
| §4.2 测量闭环（§1/§6/§10/目录节/反馈环语义） | T2/T8 | T2 pytest + `just check`（SKILL 文字面 lint） |
| §4.3 anchors（writes/铁律例外/骨架/OPTIONAL_READS） | T4/T8 | T4 pytest + lint-contracts 闭环 |
| §4.4 三 WARN 谓词口径（含全角冒号/空值/strip 域/分母） | T1/T3 | T1/T3 pytest 全态 |
| §5.1 破折号预算（anti-ai/group-craft/review-anti-ai/style-directives 四站点） | T6/T9 | 文字面 smoke + `just check` |
| §5.2 温度 0.90 + 回退判据注记 | T8 | `test_drafting_temperature_is_090` |
| §8 truth 注册 | T8 | `lint_registry_reconcile`（index.json concept ⊆ yaml） |

**F947 声明**：全部验收离线——构造输入 + tests/fixtures 真实产物驱动（chapter-*-draft.md 裸 H2 形态锚），零真实 dispatch、零 pipeline 子命令。
**G3.4 声明**：本 spec 无 LLM 产物评分场景（试点评分归卷一 v2 首跑，非本批），无 G3.4 调度需求。
