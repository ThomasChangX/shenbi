"""写所有权审计编排（spec 支柱四 Tier B N1 粒度表）。

按文件格式分派：JSON→field；markdown truth→record；chapter/report→file。
对 OWNERSHIP 内文件调 check_write_ownership；对其余文件做 file-level 声明写入检查。
cross-section drift（pending_hooks.md YAML vs 派生表）一并检测（判据 12）。
"""

from __future__ import annotations

import fnmatch

from shenbi.audit._shared import AuditResult
from shenbi.audit.snapshot import compute_file_change, parametric_globs
from shenbi.contracts.ownership import check_write_ownership, get_ownership
from shenbi.contracts.paths import PathContext
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records

_WILDCARDS = "*?["


def _declared_patterns(
    skill: str, chapter: int | None = None, ctx: PathContext | None = None
) -> list[str]:
    """技能契约的 writes+updates（项目相对路径）。

    chapter/ctx 透传 derive_output_files，使 parametric 契约
    （audits/escalation-N-report.md 类）与 watch 面（_audit_watch_paths）
    同源展开——不透传时 parametric 模式因占位符不可解析而被静默丢弃（F501）。
    """
    try:
        from shenbi.audit._shared import derive_output_files

        return derive_output_files(skill, chapter, ctx=ctx)
    except Exception:
        return []


def _matches_declared(relpath: str, declared: list[str], globs: dict[str, str]) -> bool:
    for pat in declared:
        if pat == relpath:
            return True
        g = globs.get(pat)
        if g and fnmatch.fnmatch(relpath, g):
            return True
        # F529（C32 R1）：契约裸 glob（truth/*.md 等 10 技能 11 条）——按 fnmatch
        # 语义匹配（* 跨目录），与 snapshot 侧 _expand_patterns 的观测面对齐；
        # 此前只有精确相等/parametric 键两分支，裸 glob 恒 False → 合法写入
        # 误判"未声明写入"（3 次生产 GATE_FAIL，Z5-review-r3）。
        if any(ch in pat for ch in _WILDCARDS) and fnmatch.fnmatch(relpath, pat):
            return True
    return False


def audit_writes(
    skill: str,
    pre: dict[str, str | None],
    post: dict[str, str | None],
    chapter: int | None = None,
    ctx: PathContext | None = None,
) -> AuditResult:
    """按 N1 粒度表编排写所有权审计，返回 AuditResult。

    chapter/ctx 用于展开 parametric 声明（与 dispatch_with_write_audit 的
    watch 面同源）；缺省 None 时 parametric 模式不出现在 declared（genesis）。
    """
    violations: list[str] = []
    drift_issues: list[str] = []
    declared = _declared_patterns(skill, chapter, ctx)
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
