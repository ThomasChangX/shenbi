"""读面契约×现实锁（P0：phase3 trace 实证 158/158 逃生舱失配）。

phase3 的 trace.jsonl 实证：chapter-planning 对 current_state /
chapter_summaries / pending_hooks / review_report 的 dict-form ``fields:``
读 158/158 全部失配——实存文件无声明 H2（写侧早已按表格/弧块结构演进），
字段过滤全程走「逃生舱全文件 + 预算截断」兜底。118 章勉强存活，中跑
（450 章外推 current_state ≈800K chars）会让截断成为上下文主导策略。

本锁把该缺陷族从运行时兜底前移到 CI：

1. **fields 锁**：所有 dict-form ``fields:`` 声明若指向稳定路径文件
   （非逐章生成），必须在 chapter-118 真实快照（G0.9）上
   ``filter_to_fields`` 全命中。稳定路径文件无快照 = FAIL（声明字段
   必须配套快照，防止新的「声明从未对照现实」）。
2. **extractor 锁**：所有 ``extractor:`` 声明在对应快照上必须产出
   非空且有界视图（远小于全档），窗口类还须锚定最新章/末弧。

逐章生成路径（plans/ context/ chapters/ audits/）由 SKIP_PREFIXES
豁免：同一管线既是写者也是读者，结构由 G4 模板钉死。
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from shenbi.contracts.fields import filter_to_fields
from shenbi.contracts.loader import Contract, load_contract
from shenbi.gates.shared import SKILLS
from shenbi.pipeline import read_extractors

pytestmark = pytest.mark.unit

SNAPSHOT = Path(__file__).resolve().parents[2] / "fixtures" / "snapshots" / "chapter-118"

#: 逐章/逐弧生成的路径前缀——写读同源、G4 模板钉死，不适用快照锁。
SKIP_PREFIXES = ("plans/", "context/", "chapters/", "audits/", "truth/arcs/")

#: 契约路径 → chapter-118 真实快照。稳定路径文件被 fields/extractor
#: 声明即必须入册（入册即被锁）。
FIXTURE_MAP = {
    "truth/chapter_summaries.md": SNAPSHOT / "truth" / "chapter_summaries.md",
    "truth/current_state.md": SNAPSHOT / "truth" / "current_state.md",
    "truth/pending_hooks.md": SNAPSHOT / "truth" / "pending_hooks.md",
    "truth/book_spine.md": SNAPSHOT / "truth" / "book_spine.md",
    "truth/book_strata.md": SNAPSHOT / "truth" / "book_strata.md",
    "truth/volume_summaries.md": SNAPSHOT / "truth" / "volume_summaries.md",
    "truth/character_matrix.md": SNAPSHOT / "truth" / "character_matrix.md",
    "style/style_profile.md": SNAPSHOT / "style" / "style_profile.md",
    "foundation/review_report.md": SNAPSHOT / "foundation" / "review_report.md",
    "genre-config.json": SNAPSHOT / "genre-config.json",
    "novel.json": SNAPSHOT / "novel.json",
    "world/power_system.md": SNAPSHOT / "world" / "power_system.md",
    "outline/thread_map.md": SNAPSHOT / "outline" / "thread_map.md",
    "outline/volume_map.md": SNAPSHOT / "outline" / "volume_map.md",
    "outline/story_frame.md": SNAPSHOT / "outline" / "story_frame.md",
}

#: 需要 plans/audits 接地才有产出的提取器（本锁无接地环境）——
#: 各自的单测已有合成接地覆盖；volume_chapter 读取 outline 全目录
#: 由派发侧专用机械服务，不属 extract_* 函数族。
SKIP_EXTRACTORS = frozenset({"hooks_audit_scoped", "volume_chapter"})


def _iter_skill_contracts() -> list[tuple[str, Contract]]:
    from shenbi.contracts.loader import ContractError

    out: list[tuple[str, Contract]] = []
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        try:
            out.append((skill_md.parent.name, load_contract(skill_md.parent.name)))
        except ContractError:
            continue  # meta 技能（无 contract: 块）不属读面锁范围
    return out


def _is_stable(path: str) -> bool:
    return not path.startswith(SKIP_PREFIXES)


def test_every_stable_fields_read_matches_chapter118_reality() -> None:
    """字段锁：稳定路径声明必须在真实快照上全命中（无逃生舱）。"""
    failures: list[str] = []
    checked = 0
    for skill, contract in _iter_skill_contracts():
        for path, fields in (contract.get("read_fields") or {}).items():
            if not _is_stable(path):
                continue
            fixture = FIXTURE_MAP.get(path)
            if fixture is None:
                failures.append(f"{skill}: {path} 声明 fields 但无快照入册（加 FIXTURE_MAP）")
                continue
            if not fixture.exists():
                failures.append(f"{skill}: 快照缺失 {fixture}")
                continue
            content = fixture.read_text(encoding="utf-8")
            _, matched = filter_to_fields(content, fields, str(fixture))
            checked += 1
            if not matched:
                failures.append(f"{skill}: {path} 字段失配 {fields}（逃生舱回退）")
    assert not failures, "\n".join(failures)
    assert checked >= 10, f"锁覆盖面异常收缩: {checked}"


def test_every_stable_extractor_read_yields_bounded_view() -> None:
    """提取器锁：快照上必须非空、有界（<95% 全档）。"""
    failures: list[str] = []
    checked = 0
    for skill, contract in _iter_skill_contracts():
        for path, name in (contract.get("read_extractors") or {}).items():
            if not _is_stable(path) or name in SKIP_EXTRACTORS:
                continue
            fixture = FIXTURE_MAP.get(path)
            if fixture is None:
                continue  # extract_ 函数族外的机械（如 volume_chapter）不在此锁
            fn = getattr(read_extractors, f"extract_{name}", None)
            if fn is None:
                continue
            content = fixture.read_text(encoding="utf-8")
            kwargs: dict[str, object] = {}
            sig = inspect.signature(fn)
            if "chapter" in sig.parameters:
                kwargs["chapter"] = 118
            view = fn(content, **kwargs)
            checked += 1
            if not view:
                failures.append(f"{skill}: {path} 提取器 {name} 在快照上返回空")
            elif len(view) > 0.95 * len(content):
                # 0.95 而非更低：character_matrix 在 ch118 尺度合法收敛到
                # 78%（session32 实测 -23%，无界增量占比随章数增大）。
                failures.append(
                    f"{skill}: {path} 提取器 {name} 视图未收敛 ({len(view)}/{len(content)})"
                )
    assert not failures, "\n".join(failures)
    assert checked >= 5, f"锁覆盖面异常收缩: {checked}"


def test_recent_windows_anchor_newest_unit() -> None:
    """窗口语义锚定：chapter-keyed 表保留最新章行；弧账本保留末弧。"""
    summaries = FIXTURE_MAP["truth/chapter_summaries.md"].read_text(encoding="utf-8")
    view = read_extractors.extract_recent_increments(summaries)
    assert "第 118 章" in view, "chapter_summaries 窗口丢了最新章行"

    state = FIXTURE_MAP["truth/current_state.md"].read_text(encoding="utf-8")
    view = read_extractors.extract_recent_increments(state)
    assert "第 118 章" in view, "current_state 窗口丢了最新章行"

    strata = FIXTURE_MAP["truth/book_strata.md"].read_text(encoding="utf-8")
    view = read_extractors.extract_book_strata_current(strata)
    assert "第4大弧" in view and "第1大弧" not in view, "book_strata 窗口未取末弧"
