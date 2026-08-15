"""C32 R1 回归（F529+F501）：_matches_declared fnmatch + parametric 展开接通。

spec: docs/superpowers/specs/2026-08-16-c32-write-audit-mechanism-design.md

- F529: 裸 glob 契约（truth/*.md 等 10 技能 11 条，Z5-review-r3 机械提取）的
  合法写入不得误判"未声明写入"→ rc=2
- F501/F528: parametric 契约（audits/escalation-N-report.md 类）经 chapter/ctx
  展开接通——audit_writes 透传调用方（dispatch_with_write_audit）已解析的
  chapter/PathContext，declared 面与 watch 面同源
- 生产实证复现: novel-output/test-validation/write-audit.jsonl 的 3 次
  GATE_FAIL（worldbuilding blocked=true）重放为 PASS
- 真阳性保留: 不匹配任何 declared 形态（精确/parametric glob/裸 glob）的
  写入路径仍判"未声明写入"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.audit._shared import derive_output_files
from shenbi.audit.snapshot import parametric_globs, snapshot_tree
from shenbi.audit.write_audit import _matches_declared, audit_writes
from shenbi.contracts import ContractError, load_contract
from shenbi.contracts.paths import resolve_chapter_path
from shenbi.gates.shared import PROJECT, SKILLS

PROD_TREE = PROJECT / "novel-output" / "test-validation"
PROD_WRITE_AUDIT = PROD_TREE / "write-audit.jsonl"


def _truth_md(state: str = "PLANTED") -> str:
    """记录级一致的 truth 文件内容（YAML 记录 vs 派生表同 state → 无 drift）。"""
    return (
        "## 活跃伏笔\n\n"
        "| Hook ID | 类型 | 状态 |\n|---|---|---|\n| h1 | GENUINE | " + state + " |\n\n"
        f"## hooks\n\n- id: h1\n  state: {state}\n  type: GENUINE\n"
    )


def _glob_contract_writes() -> list[tuple[str, str]]:
    """全仓 SKILL.md frontmatter 机械提取 writes/updates 含 * 的契约面。

    F529 契约面单一来源：不从手写清单构造，直接扫描真实 frontmatter。
    """
    cases: list[tuple[str, str]] = []
    for d in sorted(SKILLS.iterdir()):
        if not (d / "SKILL.md").exists():
            continue
        try:
            c = load_contract(d.name)
        except ContractError:
            continue  # meta 技能（using-shenbi 等）无 contract 块
        cases += [(d.name, p) for p in [*c["writes"], *c["updates"]] if "*" in p]
    return cases


# —— F529：契约面清单钉住（Z5-review-r3 记录 10 技能 11 条裸 glob）——


def test_glob_contract_inventory_matches_z5_review_r3() -> None:
    cases = _glob_contract_writes()
    assert len(cases) == 11
    assert {skill for skill, _ in cases} == {
        "shenbi-worldbuilding",
        "shenbi-truth-sync",
        "shenbi-sequel-writing",
        "shenbi-character-design",
        "shenbi-character-extraction",
        "shenbi-canon-import",
        "shenbi-import-analysis",
        "shenbi-short-packaging",
        "shenbi-snapshot-manage",
    }


@pytest.mark.parametrize(
    ("skill", "pattern"),
    _glob_contract_writes(),
    ids=[f"{s}:{p}" for s, p in _glob_contract_writes()],
)
def test_glob_contract_write_matches_declared(skill: str, pattern: str) -> None:
    """每条裸 glob 契约的合法写入路径必须被 _matches_declared 认定。

    N/NNN 占位符先按章号解析——与 audit_writes 链路同构（_declared_patterns
    经 derive_output_files 解析后才进 matcher）；端到端解析由
    test_snapshot_manage_glob_write_resolves_chapter 覆盖。
    """
    chapter = 3
    declared = resolve_chapter_path(pattern, chapter)
    written = declared.replace("*", "glob-sample")
    assert _matches_declared(written, [declared], parametric_globs())


def test_glob_star_crosses_directories_fnmatch_semantics() -> None:
    """钉住匹配语义：fnmatch 的 * 跨目录（spec R1 决策）。"""
    assert _matches_declared("truth/state.md", ["truth/*.md"], {})
    assert _matches_declared("truth/sub/x.md", ["truth/*.md"], {})
    # 通配不越前缀、不跨扩展名
    assert not _matches_declared("truth/state.json", ["truth/*.md"], {})
    assert not _matches_declared("characters/x.md", ["characters/major/*.md"], {})


def test_exact_and_parametric_branches_unchanged() -> None:
    """既有两分支回归：精确相等 + parametric 键经注册表 glob 映射。"""
    assert _matches_declared("novel.json", ["novel.json"], {})
    g = parametric_globs()
    assert _matches_declared("audits/escalation-5-report.md", ["audits/escalation-N-report.md"], g)


# —— F529 端到端：glob 契约技能的合法写入审计 PASS ——


def test_worldbuilding_truth_glob_write_passes(tmp_path: Path) -> None:
    watch = derive_output_files("shenbi-worldbuilding")
    assert "truth/*.md" in watch
    pre = snapshot_tree(tmp_path, watch)
    t = tmp_path / "truth" / "bridge_tracker.md"
    t.parent.mkdir(parents=True)
    t.write_text(_truth_md(), encoding="utf-8")
    post = snapshot_tree(tmp_path, watch)
    res = audit_writes("shenbi-worldbuilding", pre, post)
    assert res.violations == ()
    assert res.drift == ()
    assert "truth/bridge_tracker.md" in res.checked_files


def test_snapshot_manage_glob_write_resolves_chapter(tmp_path: Path) -> None:
    watch = derive_output_files("shenbi-snapshot-manage", 3)
    assert "snapshots/chapter-003/*" in watch
    pre = snapshot_tree(tmp_path, watch)
    m = tmp_path / "snapshots" / "chapter-003" / "manifest.json"
    m.parent.mkdir(parents=True)
    m.write_text("{}", encoding="utf-8")
    post = snapshot_tree(tmp_path, watch)
    res = audit_writes("shenbi-snapshot-manage", pre, post, chapter=3)
    assert res.violations == ()


# —— 真阳性保留：未声明路径仍 FAIL ——


def test_undeclared_write_outside_glob_still_blocked() -> None:
    """通配符放宽后未声明写入检测仍可真阳性（F520 方向不回退）。"""
    res = audit_writes("shenbi-worldbuilding", {}, {"code/rogue.py": "x"})
    assert any("未声明写入" in v for v in res.violations)
    # 扩展名不匹配 glob（truth/*.md 不覆盖 .json）
    res2 = audit_writes("shenbi-worldbuilding", {}, {"truth/rogue.json": "{}"})
    assert any("未声明写入" in v for v in res2.violations)


# —— F501/F528：parametric 契约经 chapter/ctx 展开接通 ——


def test_parametric_contract_resolves_with_chapter(tmp_path: Path) -> None:
    watch = derive_output_files("shenbi-escalation-review", 5)
    assert watch == ["audits/escalation-5-report.md"]
    pre = snapshot_tree(tmp_path, watch)
    f = tmp_path / "audits" / "escalation-5-report.md"
    f.parent.mkdir(parents=True)
    f.write_text("# escalation report\n", encoding="utf-8")
    post = snapshot_tree(tmp_path, watch)
    # chapter 透传后 declared 面与 watch 面同源 → 合法写入 PASS
    res = audit_writes("shenbi-escalation-review", pre, post, chapter=5)
    assert res.violations == ()
    # 不透传 chapter 时 declared 丢失 parametric 模式（F501 现状边界，钉住）
    res_no_ctx = audit_writes("shenbi-escalation-review", pre, post)
    assert any("未声明写入" in v for v in res_no_ctx.violations)


# —— 生产实证复现：3 次 GATE_FAIL 场景重放为 PASS ——


def _prod_blocked_rows() -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in PROD_WRITE_AUDIT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [r for r in rows if r.get("blocked")]


def test_production_gate_fail_rows_exist() -> None:
    rows = _prod_blocked_rows()
    assert len(rows) == 3
    assert all(r["skill"] == "shenbi-worldbuilding" for r in rows)
    # 生产行的 violations 恰为 2 个 truth/*.md 展开文件（Z5-review-r3 记录形状）
    for r in rows:
        assert [v.split("未声明写入: ", 1)[1].split("（")[0] for v in r["violations"]] == [
            "truth/bridge_tracker.md",
            "truth/character_matrix.md",
        ]


@pytest.mark.parametrize(
    "row",
    _prod_blocked_rows(),
    ids=[f"{r['skill']}#{i}" for i, r in enumerate(_prod_blocked_rows())],
)
def test_production_gate_fail_row_replays_pass(row: dict[str, Any]) -> None:
    """单次生产 GATE_FAIL（rc=2）重放：观测面用生产行 checked_files，内容用真实树。

    truth/bridge_tracker.md 在后续章被删除，用记录级一致内容替代（G0.9：形状
    来自真实产物行，内容来自真实树或真实产物同构内容）。
    """
    skill = row["skill"]
    snap: dict[str, str | None] = {}
    for rel in row["checked_files"]:
        p = PROD_TREE / rel
        snap[rel] = p.read_text(encoding="utf-8") if p.exists() else _truth_md()
    res = audit_writes(skill, snap, snap)
    assert sorted(res.checked_files) == sorted(row["checked_files"])
    assert res.violations == ()
