#!/usr/bin/env python3
"""Prose↔declaration closure lint (spec #58 C20 T1).

R1 body→decl: every file path referenced in a SKILL.md body (outside the
AUTO-GENERATED contract block) must be covered by the frontmatter contract
via a six-level match: exact (both sides offset-canonicalized) / declaration
as glob (``N``→``*`` fnmatch) / bare-basename vs any declared basename /
skill-bundle reference (a file physically living under ``skills/*/``) /
registry vocabulary (truth-files.yaml concepts, parametric globs, globs) /
named allowlist entry (category + one-line reason each).

R2 decl→body: every declared writes/updates target must appear in the real
prose (steps/headers/output sections) — evidence inside the AUTO-GENERATED
``## 数据契约`` summary block does NOT count (the F812/F871/F872 shape: the
filename sits in the generated summary while no producing step exists).

Failure semantics: default WARN (print, exit 0); ``--fail`` exits 1 on any
violation; ``--list-exempt`` prints the meta exemptions and allowlist.

Known limitation (deliberate, spec T1.1 note): basename matching pools
reads+writes+updates, so a READ reference that only matches a WRITE
declaration passes — the F836 regression shape is covered instead by the
behavioral dispatch assertions (tests/pipeline/test_dispatch_reads_injection.py).
Also deliberate: fnmatch is not path-aware, so a concrete ref under a ``**``
declaration (e.g. ``characters/alice.md`` vs ``characters/**/*.md``) does NOT
match — mirroring the dispatcher's non-recursive glob semantics; such refs
surface as violations for explicit adjudication.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shenbi import sync_contracts
from shenbi.contracts.loader import load_registry
from shenbi.pipeline.dispatch_helper import _strip_autogen_blocks
from tools.lint_contracts import META_SKILLS

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"

# Body reference extraction: relative paths (multi-segment, may carry glob
# metachars and offset placeholders), or bare .md/.json filenames. Loose on
# purpose — matches are post-filtered to file-shaped refs (extension/glob).
_SEG = r"[A-Za-z0-9_.*\[\]{}()N-]+"
_LOOSE_REF_RE = re.compile(rf"(?:[A-Za-z0-9_-]+/)+(?:{_SEG}/)*{_SEG}|[\w{{}}()N-]+\.(?:md|json)\b")
# Offset forms — prose ``(N-3)`` and declared ``{N-3}`` canonicalize to ``N``.
_OFFSET_FORMS = re.compile(r"[({]N[+-]\d+[)}]")

#: (category, "skill:ref-pattern" fnmatch, one-line reason)
ALLOWLIST: tuple[tuple[str, str, str], ...] = (
    ("skill-bundle", "*:anti-ai-reference.md", "捆绑参考文件, dispatcher 不注入 (T1.1 裁决 b)"),
    (
        "anti-example",
        "shenbi-context-composing:chapters/chapter-*.md",
        "anti-rationalization 反例行引用, 非真实读依赖",
    ),
    (
        "anti-example",
        "shenbi-foundation-review:characters/villain.md",
        "证据引用格式的示例路径, 非真实读依赖",
    ),
    (
        "anti-example",
        "shenbi-book-spine-init:author_intent.md",
        "铁律 1 显式否定引用(创世层不读此文件), 非读依赖——reads 补声明即死声明",
    ),
    (
        "repo-docs",
        "shenbi-chapter-drafting:docs/framework/chapter-file-format.md",
        "仓库框架文档引用, 开发者参考, dispatcher 不注入",
    ),
    (
        "repo-docs",
        "shenbi-chapter-revision:docs/framework/status-vocab.md",
        "仓库框架文档引用, 开发者参考, dispatcher 不注入",
    ),
    (
        "anti-example",
        "shenbi-foreshadowing-track:foreshadowing_ledger.md",
        "DEPRECATED 技能残文幻影(已被 foreshadowing-lifecycle 取代, 不派发)",
    ),
    (
        "anti-example",
        "shenbi-review-anti-ai:checklist.md",
        "否定引用(原文件已随 spec #33 T2 死资产清理删除), 非读依赖",
    ),
)


def _canonical(path: str) -> str:
    return _OFFSET_FORMS.sub("N", path)


def _prose(skill_file_text: str) -> str:
    """Strip declaration surfaces from a SKILL.md text.

    Frontmatter + AUTO-GENERATED blocks removed — declarations are not
    prose evidence (the F812 shape hides behind exactly this confusion).
    """
    text = _strip_autogen_blocks(skill_file_text)
    fm = re.match(r"^---\n.*?\n---\n", text, flags=re.DOTALL)
    return text[fm.end() :] if fm else text


def _trim_unbalanced(ref: str) -> str:
    # Paren-wrapped DOT-label enumerations yield fragments like ``(novel.json``
    # — strip an unbalanced leading/trailing paren; balanced forms
    # (``chapter-(N-3).md``) pass through untouched.
    if ref.startswith("(") and ")" not in ref:
        ref = ref[1:]
    if ref.endswith(")") and "(" not in ref:
        ref = ref[:-1]
    # Markdown bold / code-span residue: ``**path**`` and ``{path}`` tails.
    return ref.rstrip("*}{")


def _body_refs(body: str) -> set[str]:
    # Filter AFTER trimming: bold/code-span residue (``**mode-name**``) loses
    # its ``*`` tail in the trim and must then drop out as a non-file token.
    return {
        ref
        for m in _LOOSE_REF_RE.findall(body)
        if (ref := _trim_unbalanced(m)).endswith((".md", ".json")) or "*" in ref
    }


def _contract_paths(contract: Mapping[str, object], keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for key in keys:
        for entry in contract.get(key, []):
            out.append(entry["file"] if isinstance(entry, dict) else entry)
    return out


def _registry_patterns(reg) -> list[str]:
    patterns = [str(g.pattern) for g in reg.globs]
    patterns.extend(str(p.glob) for p in reg.patterns)
    patterns.extend(c.name for c in reg.concepts)
    return patterns


def _declared_covers(cref: str, base: str, declared: list[str]) -> bool:
    for d in declared:
        cd = _canonical(d)
        if cref == cd:
            return True
        if fnmatch.fnmatch(cref, cd.replace("N", "*")):
            return True
        # Bare-basename normalization (T1.1 a) — BARE refs only: a ref with a
        # directory must match its own directory, cross-dir drift is quarry.
        # The declared basename may itself be a glob (``truth/*.md``), so a
        # prose shorthand like ``pending_hooks.md`` matches the writer's own
        # declared glob.
        if "/" not in cref and fnmatch.fnmatch(base, Path(cd).name):
            return True
    return False


def _covered(
    ref: str,
    declared: list[str],
    skill: str,
    reg_patterns: Sequence[str],
    skills_root: Path,
) -> bool:
    """Six-level match: declared / skill-bundle / registry / allowlist."""
    cref = _canonical(ref)
    base = Path(cref).name
    return (
        _declared_covers(cref, base, declared)
        # b: skill-bundle reference — own dir OR a sibling skill's dir
        # (cross-skill reference docs like hook-types.md physically live in
        # one skill's dir while several prose bodies cite them).
        or ("/" not in cref and any(skills_root.glob(f"*/{base}")))  # b
        or any(fnmatch.fnmatch(cref, pat) for pat in reg_patterns)  # c
        or any(fnmatch.fnmatch(f"{skill}:{cref}", pat) for _c, pat, _r in ALLOWLIST)
    )


def find_violations(
    contracts: Mapping[str, Mapping[str, object]] | None = None,
    skills_dir: Path | None = None,
    reg_patterns: Sequence[str] | None = None,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Return ``(r1_violations, r2_violations)``.

    r1 — ``(skill, ref, "R1_UNDECLARED")`` per body ref not covered.
    r2 — ``(skill, target)`` per declared write/update with no real prose step.
    """
    contracts = sync_contracts.load_all_contracts() if contracts is None else contracts
    skills = skills_dir if skills_dir is not None else SKILLS_DIR
    if reg_patterns is None:
        reg_patterns = _registry_patterns(load_registry())

    r1: list[tuple[str, str, str]] = []
    r2: list[tuple[str, str]] = []
    for skill, contract in contracts.items():
        if skill in META_SKILLS:
            continue
        skill_file = skills / skill / "SKILL.md"
        if not skill_file.exists():
            continue
        body = _prose(skill_file.read_text(encoding="utf-8"))
        # Canonicalize BOTH sides for R2 — a declared ``{N-3}`` write must
        # match prose that says ``(N-3)`` (same canonical key).
        cbody = _OFFSET_FORMS.sub("N", body)
        declared = _contract_paths(contract, ("reads", "writes", "updates"))
        for ref in sorted(_body_refs(body)):
            if not _covered(ref, declared, skill, reg_patterns, skills):
                r1.append((skill, ref, "R1_UNDECLARED"))
        for target in _contract_paths(contract, ("writes", "updates")):
            cd = _canonical(target)
            if Path(cd).name not in cbody and cd not in cbody:
                r2.append((skill, target))
    return r1, r2


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the prose-closure lint.

    Default WARN (print, exit 0); --fail exits 1 on violations;
    --list-exempt prints the meta exemptions and allowlist entries.
    """
    args = sys.argv[1:] if argv is None else argv
    if "--list-exempt" in args:
        for name in sorted(META_SKILLS):
            print(f"meta-exempt: {name}")
        for cat, pat, reason in ALLOWLIST:
            print(f"allowlist[{cat}]: {pat} — {reason}")
        return 0
    r1, r2 = find_violations()
    for skill, ref, rule in r1:
        print(f"{rule}: skill={skill} ref={ref}", file=sys.stderr)
    for skill, target in r2:
        print(f"R2_NO_BODY_STEP: skill={skill} target={target}", file=sys.stderr)
    if r1 or r2:
        print(f"total: {len(r1)} R1 + {len(r2)} R2", file=sys.stderr)
    if "--fail" in args and (r1 or r2):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
