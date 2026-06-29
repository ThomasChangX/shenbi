"""写所有权审计编排（spec 支柱四 Tier B N1 粒度表）。

按文件格式分派：JSON→field；markdown truth→record；chapter/report→file。
对 OWNERSHIP 内文件调 check_write_ownership；对其余文件做 file-level 声明写入检查。
cross-section drift（pending_hooks.md YAML vs 派生表）一并检测（判据 12）。
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from shenbi.audit.snapshot import compute_file_change, parametric_globs
from shenbi.contracts.ownership import check_write_ownership, get_ownership
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records


@dataclass(frozen=True)
class AuditResult:
    skill: str
    violations: tuple[str, ...]
    drift: tuple[str, ...]
    checked_files: tuple[str, ...]


def _declared_patterns(skill: str) -> list[str]:
    """技能契约的 writes+updates（项目相对路径）。"""
    from shenbi.dispatcher.executor import derive_output_files

    try:
        return derive_output_files(skill)
    except Exception:
        return []


def _matches_declared(relpath: str, declared: list[str], globs: dict[str, str]) -> bool:
    for pat in declared:
        if pat == relpath:
            return True
        g = globs.get(pat)
        if g and fnmatch.fnmatch(relpath, g):
            return True
    return False


def audit_writes(
    skill: str, pre: dict[str, str | None], post: dict[str, str | None]
) -> AuditResult:
    """按 N1 粒度表编排写所有权审计，返回 AuditResult。"""
    violations: list[str] = []
    drift_issues: list[str] = []
    declared = _declared_patterns(skill)
    globs = parametric_globs()
    checked: list[str] = []
    for rel in sorted(set(pre) | set(post)):
        change = compute_file_change(rel, pre.get(rel), post.get(rel))
        checked.append(rel)
        # cross-section drift（markdown truth：YAML vs 派生表），仅 post 存在时
        post_content = post.get(rel)
        if rel.endswith(".md") and post_content is not None:
            recs = parse_records(post_content)
            md = parse_markdown_table(post_content)
            drift_issues.extend(detect_cross_section_drift(recs, md))
        v = check_write_ownership(skill, change)
        if v:
            violations.extend(v)
            continue
        # 无 OWNERSHIP 条目 → file-level 声明写入检查
        if get_ownership(skill, rel) is None:
            if not _matches_declared(rel, declared, globs):
                violations.append(f"未声明写入: {rel}（不在 {skill} 契约 writes/updates）")
    return AuditResult(
        skill=skill,
        violations=tuple(violations),
        drift=tuple(drift_issues),
        checked_files=tuple(checked),
    )
