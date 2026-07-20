"""G2: output validation gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from shenbi.contracts.schemas.adapt import decisions_err_to_g2_failures
from shenbi.contracts.schemas.decisions import DecisionsDoc
from shenbi.gates.shared import (
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    bak_path,
    fail,
    jload,
    passed,
    word_count_md,
    yload,
)

_META_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)


def gate_G2(
    file_paths: str | list[str] | None,
    file_type: str = "chapter",
    round_dir: str | None = None,
    project_dir: str | None = None,
) -> str:
    """G2: Write verification. file_type: chapter|report|truth"""
    checks: list[dict[str, Any]] = []
    mf: list[dict[str, Any]] = []
    fps: list[str]
    if isinstance(file_paths, str):
        fps = [p.strip() for p in file_paths.split(",") if p.strip()]
    elif file_paths is None:
        fps = []
    else:
        fps = list(file_paths)
    for fp in fps:
        p = Path(fp)
        # G2.1 — exists
        if not p.exists():
            mf.append({"id": "G2.1", "file": fp, "s": "FAIL", "r": "not found"})
            continue
        # G2.2 — non-empty
        if p.stat().st_size == 0:
            mf.append({"id": "G2.2", "file": fp, "s": "FAIL", "r": "empty"})
            continue
        checks.append({"id": "G2.1", "file": fp, "s": "PASS"})
        checks.append({"id": "G2.2", "file": fp, "s": "PASS"})

        # G2.3 — UTF-8
        try:
            content = p.read_text(encoding="utf-8")
            checks.append({"id": "G2.3", "file": fp, "s": "PASS"})
        except Exception:
            mf.append({"id": "G2.3", "file": fp, "s": "FAIL"})
            continue

        # G2.dec — decisions.json validation (M4)
        # Schema/rationale rules now live in DecisionsDoc (Task 5); this branch
        # only handles JSON-syntax (G2.dec.1) and delegates the rest to the
        # contract layer. The numeric IDs G2.dec.{1,2,3} are preserved by the
        # decisions_err_to_g2_failures adapter.
        if file_type == "decisions":
            # Skip non-JSON files — the decisions branch only validates JSON.
            # Skills like chapter-drafting/context-composing produce BOTH a .md
            # artifact and a sidecar decisions.json; when file_type="decisions"
            # is applied uniformly to all outputs, the .md must not be parsed as
            # JSON (it would FAIL G2.dec.1). .md files are validated by their own
            # file_type gate instead.
            if not fp.endswith(".json"):
                continue  # skip .md files — decisions branch only validates JSON
            # G2.dec.4 — multi-JSON concatenation detection (MUST run BEFORE json.loads())
            # (G4 retry feedback can cause LLM to concatenate old + new JSON under
            # one ### FILE: marker. This catches it early.)
            #
            # CRITICAL ORDERING: json.loads() raises JSONDecodeError on concatenated JSON
            # ("Extra data" error), so this check must execute first. If we placed it
            # after data = json.loads(content), the line above would raise before the
            # check is ever reached, making the check dead code.
            if content.count('"$schema"') > 1:
                mf.append(
                    {
                        "id": "G2.dec.4",
                        "file": fp,
                        "s": "FAIL",
                        "r": f"multiple JSON objects concatenated ({content.count(chr(34) + '$schema' + chr(34))} schemas found)",
                    }
                )
                continue  # skip the json.loads() below for this file — it would raise

            # G2.dec.1 — valid JSON (with multi-JSON concatenation recovery)
            # Multi-JSON detection runs BEFORE json.loads(): if raw_decode()
            # succeeds where json.loads() fails (due to concatenated JSON objects),
            # extract only the first complete object and warn about truncation.
            data: Any = None
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Recovery: attempt raw_decode() to extract first complete JSON object
                decoder = json.JSONDecoder()
                try:
                    clean_data, end_pos = decoder.raw_decode(content)
                    if isinstance(clean_data, dict):
                        data = clean_data
                        remaining = content[end_pos:].strip()
                        if remaining:
                            log.warning(
                                "g2_decisions_multi_json_truncated",
                                file=fp,
                                original_len=len(content),
                                recovered_len=end_pos,
                                remaining_preview=remaining[:200],
                            )
                        else:
                            # Trailing whitespace only — borderline valid, accept
                            log.info(
                                "g2_decisions_json_trailing_ws_recovered",
                                file=fp,
                                original_len=len(content),
                                cleaned_len=end_pos,
                            )
                    else:
                        mf.append(
                            {
                                "id": "G2.dec.1",
                                "file": fp,
                                "s": "FAIL",
                                "r": f"recovered non-object JSON: {type(clean_data).__name__}",
                            }
                        )
                        continue
                except json.JSONDecodeError:
                    mf.append({"id": "G2.dec.1", "file": fp, "s": "FAIL", "r": "invalid JSON"})
                    continue
            if not isinstance(data, dict):
                mf.append(
                    {
                        "id": "G2.dec.1",
                        "file": fp,
                        "s": "FAIL",
                        "r": f"expected JSON object, got {type(data).__name__}",
                    }
                )
                continue
            # G2.dec.2/.3 — schema version, required keys, P2.5 rationale (DecisionsDoc)
            try:
                DecisionsDoc.model_validate(data)
                checks.append({"id": "G2.dec", "file": fp, "s": "PASS"})
            except ValidationError as e:
                mf.extend(decisions_err_to_g2_failures(e, fp))
            continue  # CRITICAL: skip G2.4-G2.10 (word count etc.) for JSON decisions

        # G2.4 — JSON syntax (if JSON file)
        if fp.endswith(".json"):
            try:
                jload(fp)
                checks.append({"id": "G2.4", "file": fp, "s": "PASS"})
            except (json.JSONDecodeError, OSError):
                mf.append({"id": "G2.4", "file": fp, "s": "FAIL"})

        # G2.5 — YAML frontmatter (only for structured data files, not creative prose)
        # truth/, outline/, plans/, snapshots/ files must have frontmatter.
        # Creative output (chapters/, world/, review reports) is exempt.
        if fp.endswith(".md"):
            _parts = set(Path(fp).parts)
            must_have = any(
                d in _parts for d in ["truth", "outline", "plans", "snapshots"]
            ) or fp.endswith(("plan.md", "memo.md", "map.md"))
            try:
                fm = yload(fp)
                has_fm = bool(fm)
                if must_have and not has_fm:
                    mf.append(
                        {
                            "id": "G2.5",
                            "file": fp,
                            "s": "FAIL",
                            "r": "structured data file requires YAML frontmatter",
                        }
                    )
                else:
                    checks.append(
                        {
                            "id": "G2.5",
                            "file": fp,
                            "s": "PASS",
                            "has_frontmatter": has_fm,
                            "required": must_have,
                        }
                    )
            except Exception:
                if must_have:
                    mf.append({"id": "G2.5", "file": fp, "s": "FAIL", "r": "YAML parse error"})
                else:
                    checks.append(
                        {
                            "id": "G2.5",
                            "file": fp,
                            "s": "SKIP",
                            "r": "YAML parse error on non-structured file",
                        }
                    )

        # Chapter-specific checks
        if file_type == "chapter":
            wc = word_count_md(fp)

            # G2.6 — word count >= floor
            if wc < CHAPTER_WORD_FLOOR:
                mf.append(
                    {
                        "id": "G2.6",
                        "file": fp,
                        "s": "FAIL",
                        "expected": f">= {CHAPTER_WORD_FLOOR}",
                        "actual": wc,
                        "resolution": "run length-normalizing --mode expand",
                    }
                )
            else:
                checks.append({"id": "G2.6", "file": fp, "s": "PASS", "word_count": wc})

            # G2.7 — word count ceiling
            is_important = _is_important_chapter(fp, project_dir or "")
            ceiling = CHAPTER_WORD_CEILING if is_important else int(CHAPTER_WORD_FLOOR * 1.5)
            if wc > ceiling:
                mf.append(
                    {
                        "id": "G2.7",
                        "file": fp,
                        "s": "FAIL",
                        "expected": f"<= {ceiling}",
                        "actual": wc,
                        "is_important": is_important,
                    }
                )
            else:
                checks.append(
                    {
                        "id": "G2.7",
                        "file": fp,
                        "s": "PASS",
                        "ceiling": ceiling,
                        "is_important": is_important,
                    }
                )

            # G2.8 — PRE_WRITE_CHECK
            if "## PRE_WRITE_CHECK" not in content:
                mf.append({"id": "G2.8", "file": fp, "s": "FAIL"})
            else:
                checks.append({"id": "G2.8", "file": fp, "s": "PASS"})

            # G2.9 — POST_WRITE_SELF_CHECK
            if "## POST_WRITE_SELF_CHECK" not in content:
                mf.append({"id": "G2.9", "file": fp, "s": "FAIL"})
            else:
                checks.append({"id": "G2.9", "file": fp, "s": "PASS"})

        # G2.10 — template placeholder detection (10% threshold, chapter files only)
        lines = content.split("\n")
        if len(lines) > 0:
            placeholder_ratio = sum(1 for l in lines if "待填充" in l) / len(lines)
            if placeholder_ratio > 0.1:
                mf.append(
                    {
                        "id": "G2.10",
                        "file": fp,
                        "s": "FAIL",
                        "r": f"template placeholder: {placeholder_ratio:.0%}",
                    }
                )
            else:
                checks.append({"id": "G2.10", "file": fp, "s": "PASS"})

        # G2.11 — truth files: .bak comparison (line-by-line diff)
        if file_type == "truth" and round_dir:
            bak = Path(bak_path(fp))
            if bak.exists():
                import difflib

                old_lines = bak.read_text(encoding="utf-8").splitlines(keepends=True)
                new_lines = content.splitlines(keepends=True)
                diff = list(
                    difflib.unified_diff(old_lines, new_lines, fromfile=str(bak), tofile=fp)
                )
                # Only removals (lines starting with -) are violations
                removals = [l for l in diff if l.startswith("-") and not l.startswith("---")]
                if removals:
                    mf.append(
                        {
                            "id": "G2.11",
                            "file": fp,
                            "s": "FAIL",
                            "r": f"{len(removals)} lines removed from truth file",
                            "removed_lines": removals[:5],
                        }
                    )
                else:
                    checks.append({"id": "G2.11", "file": fp, "s": "PASS"})

        # G2.12 — file completeness (sentence-final punctuation, chapter files only)
        last = content.strip().split("\n")[-1].strip() if content.strip() else ""
        sentence_enders = ("。", "！", "？", "…", "」", "』", '"', "）", ")", "---")
        ends_ok = last.endswith(sentence_enders) or last.startswith("#")
        if not ends_ok and last:
            checks.append({"id": "G2.12", "file": fp, "s": "WARN", "r": "may be truncated"})
        else:
            checks.append({"id": "G2.12", "file": fp, "s": "PASS"})

        # G2.meta_ratio: WARN when META block proportion > 50%
        meta_checks, meta_failures = _check_meta_ratio(p)
        checks.extend(meta_checks)
        if meta_failures:
            for f in meta_failures:
                checks.append({"id": "G2.meta_ratio", "file": fp, "s": "WARN", "r": f})

    if mf:
        return fail(
            "G2",
            checks,
            "scoring",
            [x["id"] + ":" + x.get("file", "") for x in mf],
        )
    return passed("G2", checks)


def _check_meta_ratio(
    file_path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Check META block proportion in chapter files.

    Returns (checks, failures). WARN-level: triggers when META block
    content exceeds 50% of total file size (indicates planning bloat).
    """
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    if not file_path.exists() or file_path.suffix != ".md":
        return checks, failures

    content = file_path.read_text(encoding="utf-8")
    total_chars = len(content)

    meta_chars = sum(len(m.group(0)) for m in _META_RE.finditer(content))

    if total_chars == 0:
        return checks, failures

    ratio = meta_chars / total_chars

    if meta_chars > 0:
        checks.append(
            {
                "id": "G2.meta_ratio",
                "s": "WARN" if ratio > 0.5 else "PASS",
                "ratio": f"{ratio:.1%}",
                "meta_chars": meta_chars,
                "total_chars": total_chars,
            }
        )

        if ratio > 0.5:
            failures.append(f"G2.meta_ratio:{ratio:.1%}_meta_exceeds_50%_threshold")

    return checks, failures


def _is_important_chapter(fp: str, project_dir: str) -> bool:
    """Check if a chapter is flagged as important.
    Sources: (a) volume_map.md annotations (爆发段/高潮/卷首/卷末)
             (b) chapter-N-plan.md section 1 '重要章' marker
    """
    if not project_dir:
        return False
    ch_num = re.search(r"chapter-(\d+)", str(fp))
    if not ch_num:
        return False
    n = int(ch_num.group(1))

    pd = Path(project_dir)

    # (a) volume_map.md annotations
    vm = pd / "outline" / "volume_map.md"
    if vm.exists():
        vm_text = vm.read_text(encoding="utf-8")
        patterns = [rf"第{n}章.*(?:爆发|高潮|卷首|卷末|开篇|收官)"]
        if any(re.search(p, vm_text) for p in patterns):
            return True

    # (b) chapter-N-plan.md section 1 "重要章" marker
    plan = pd / "plans" / f"chapter-{n}-plan.md"
    if plan.exists():
        plan_text = plan.read_text(encoding="utf-8")
        # Read only up to section 2 (## 2.)
        first_section = plan_text.split("## 2.")[0] if "## 2." in plan_text else plan_text[:500]
        if "重要章" in first_section:
            return True

    return False
