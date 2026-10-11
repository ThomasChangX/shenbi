"""Thread-safe truth file I/O (spec §3.2).

The concurrency model for skill dispatch is in-process ``ThreadPoolExecutor``
(threads). The correct synchronization primitive is therefore ``threading.Lock``
— NOT ``fcntl.flock``, which targets inter-process locking and leaves
``.lock`` files on disk. This module provides a path-keyed lock registry so
that writes to different truth files do not block each other, while
concurrent writes to the SAME file serialize.

A read-merge-write (e.g. upsert-markdown-row) is NOT atomic across threads
even though the final ``safe_write`` is atomic (temp + ``os.replace``): two
threads can each read the prior content and the second writer's merge loses
the first writer's row (spec §2.2 lost-update race). The per-path lock
serializes the whole read-merge-write transaction.

Wraps :func:`shenbi.safe_write.safe_write` with update-mode awareness:
- ``replace``: atomic overwrite (current snapshot files)
- ``upsert_yaml``: read existing YAML records, dedup by key_field, merge,
  re-serialize, write (structured data like hooks)
- ``upsert_markdown_row``: read existing markdown table/bullet rows, dedup by
  key column, merge new row, write (trend files read by escalation_bridge)

Supports both str-based (table-row format) and dict-based (bullet-row format)
data for ``replace`` and ``upsert_markdown_row`` modes.

Idempotency is based on NATURAL KEYS (chapter number, hook id), NOT substring
matching. truth_index.py already abandoned substring matching as the broken
approach; LLM prose is never byte-identical across runs so substring matching
yields false negatives (whitespace diffs) and false positives (short substrings
dropped). The proven pattern (formerly hook_planting.py) is: read structured data,
dedup by stable key, merge, write back).

Thread safety: in-process threading.Lock keyed by path (not fcntl.flock).
"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import yaml

from shenbi.exceptions import TruthFileParseError
from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# Module-level registry of per-path locks. Access to the registry dict itself
# is guarded by _REGISTRY_LOCK to avoid a race where two threads lazily create
# a lock for the same path and each stores its own (losing one). No lock files
# are written to disk — this is purely in-process.
_REGISTRY_LOCK = threading.Lock()
#: Bounded registry (spec #37 T607): long-running processes touching many
#: paths would otherwise grow the registry without limit. Entries carry a
#: refcount maintained under the registry guard — eviction only ever drops
#: refcount==0 entries (the locked()-snapshot race the spec rejected).
_PATH_LOCKS_MAX = 256
_PATH_LOCKS: dict[str, tuple[threading.Lock, int]] = {}


@contextmanager
def _path_lock(path: Path) -> Generator[None, None, None]:
    """Serialize same-path writers in-process AND cross-process (spec #37 T709).

    Layering: registry threading.Lock (in-process identity + refcount) then
    flock on ``<path>.lockfile`` (cross-process). Writers that honor this
    lockfile — including subprocess helpers that take it explicitly — are
    in the same mutual-exclusion domain (spec #37 T709). Subprocess writers
    that go through safe_write/locked_transact only (directory flock) are
    serialized with each other but NOT with per-path RMW sections; the
    docstring of each such site declares its lock domain. On
    flock-unavailable platforms this degrades to in-process-only.
    """
    import os
    import sys

    key = str(path)
    with _REGISTRY_LOCK:
        entry = _PATH_LOCKS.get(key)
        if entry is None:
            if len(_PATH_LOCKS) >= _PATH_LOCKS_MAX:
                for stale_key, (stale_lock, stale_rc) in list(_PATH_LOCKS.items()):
                    if stale_key != key and stale_rc == 0 and not stale_lock.locked():
                        del _PATH_LOCKS[stale_key]
                        if len(_PATH_LOCKS) < _PATH_LOCKS_MAX:
                            break
            entry = (threading.Lock(), 0)
            _PATH_LOCKS[key] = entry
        thread_lock, refcount = entry
        _PATH_LOCKS[key] = (thread_lock, refcount + 1)  # refcount acquired under guard
    lockfile = path.parent / (path.name + ".lockfile")
    fd: int | None = None
    try:
        with thread_lock:
            if sys.platform != "win32":
                try:
                    import fcntl

                    lockfile.parent.mkdir(parents=True, exist_ok=True)
                    fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
                    fcntl.flock(fd, fcntl.LOCK_EX)  # blocking; held by close
                except (ImportError, OSError):
                    if fd is not None:
                        os.close(fd)
                    fd = None  # degrade to in-process only
            yield
    finally:
        if fd is not None:
            os.close(fd)
        with _REGISTRY_LOCK:
            entry = _PATH_LOCKS.get(key)
            if entry is not None:
                thread_lock2, rc = entry
                _PATH_LOCKS[key] = (thread_lock2, max(0, rc - 1))


@contextmanager
def truth_file_flock(path: Path) -> Generator[None, None, None]:
    """Cross-process-only flock on ``<path>.lockfile`` (no in-process registry).

    For short-lived subprocess helpers (e.g. compute_drift CLI) writing
    truth/** files: taking the SAME lockfile as _path_lock puts them in the
    same mutual-exclusion domain as in-process RMW sections (spec #37 T709).
    """
    import os
    import sys

    if sys.platform == "win32":  # pragma: no cover — POSIX-authoritative
        yield
        return
    try:
        import fcntl

        lockfile = path.parent / (path.name + ".lockfile")
        lockfile.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
    except (ImportError, OSError):
        yield  # degrade to no cross-process exclusion (POSIX-authoritative)
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


#: Public alias: sibling modules (dispatch_helper staging route, checkpoint
#: commit merge) reuse the SAME per-path lock registry — a second registry
#: would not mutually exclude with write_truth_file's locking (SDD #21 R3).
path_lock = _path_lock


def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | dict[str, Any] | list[dict[str, Any]],
    *,
    mode: str = "replace",
    key_field: str | None = None,
) -> None:
    """Write to a truth file thread-safely, respecting update_mode.

    Args:
        project_dir: Root directory of the novel project.
        filename: Relative filename within ``truth/`` (e.g. ``resonance_trend.md``).
        new_data: Content to write. ``str`` for table-row format,
            ``dict[str, Any]`` for bullet-row format (key/value pairs),
            ``list[dict]`` for YAML records.
        mode: ``"replace"`` for atomic overwrite, ``"upsert_yaml"`` for
            structured-record key dedup, ``"upsert_markdown_row"`` for
            table/bullet-row key-column dedup.
        key_field: Natural key for dedup (e.g. ``"chapter"``, ``"id"``).
            Required for the upsert modes.

    Raises:
        ValueError: If mode is unrecognized or key_field missing for upsert.
        TruthFileParseError: In ``upsert_yaml`` mode, if the existing file's
            YAML frontmatter is corrupt/unreadable (fail-loud, T706) — the
            file is left untouched for repair instead of being collapsed.
    """
    if mode not in ("replace", "upsert_yaml", "upsert_markdown_row", "insert_markdown_row"):
        raise ValueError(
            f"Unknown mode '{mode}'; expected 'replace', 'upsert_yaml', 'upsert_markdown_row', "
            "or 'insert_markdown_row'"
        )

    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    path = truth_dir / filename

    lock = _path_lock(path)
    with lock:
        if mode == "replace":
            if isinstance(new_data, dict):
                # T712: render readable "- k: v" bullets, not a Python repr —
                # the repr was unreadable prose and unparseable on re-read.
                bullets = "\n".join(f"- {k}: {v}" for k, v in new_data.items())
                body = f"# {filename.removesuffix('.md')}\n\n{bullets}\n"
                safe_write(path, ensure_truth_frontmatter(filename, body).encode("utf-8"))
            else:
                content = new_data if isinstance(new_data, str) else str(new_data)
                # Creation forms are LLM-authored and may omit frontmatter —
                # presence is a program invariant (adjudication 004 surface).
                content = ensure_truth_frontmatter(filename, content)
                safe_write(path, content.encode("utf-8"))
            log.info("truth_file_written", path=str(path), mode=mode)
            return

        if mode == "upsert_markdown_row":
            if isinstance(new_data, dict):
                _upsert_markdown_bullet(path, filename, new_data, key_field)
            elif isinstance(new_data, str):
                existing = ensure_table_header(
                    filename, path.read_text(encoding="utf-8") if path.exists() else ""
                )
                merged = upsert_markdown_row(existing, new_data, key_field or "chapter")
                safe_write(path, merged)
                log.info("truth_file_markdown_row_upserted", file=filename)
            else:
                raise ValueError("upsert_markdown_row requires str or dict new_data")
            return

        if mode == "insert_markdown_row":
            # T701 (SDD #21 R1): insert-only semantics — if the key already
            # exists, skip (a richer row from another writer stays untouched);
            # otherwise append. The existence check runs INSIDE the per-path
            # lock so concurrent writer threads cannot interleave check and
            # write (check-then-act race). Unlike upsert_markdown_row this
            # never replaces an existing row: the framework placeholder row
            # must not clobber a skill's rich row (dimension scores, role,
            # confidence) written moments earlier in the same chapter.
            if not isinstance(new_data, str):
                raise ValueError("insert_markdown_row requires str new_data")
            existing = ensure_table_header(
                filename, path.read_text(encoding="utf-8") if path.exists() else ""
            )
            if has_markdown_row(existing, new_data, key_field or "chapter"):
                log.info(
                    "truth_file_markdown_row_insert_skipped", file=filename, key_field=key_field
                )
                return
            merged = upsert_markdown_row(existing, new_data, key_field or "chapter")
            safe_write(path, merged)
            log.info("truth_file_markdown_row_inserted", file=filename)
            return

        if mode == "upsert_yaml":
            if not isinstance(new_data, list):
                raise ValueError("upsert_yaml requires list[dict] new_data")
            if key_field is None:
                raise ValueError("upsert_yaml requires key_field")
            existing_records = _read_yaml_records(path)
            merged_records = _upsert_by_key(existing_records, new_data, key_field)
            yaml_content = _serialize_yaml_records(merged_records, filename)
            safe_write(path, yaml_content)
            log.info("truth_file_yaml_upserted", file=filename)


#: Canonical truth-file frontmatter — the program-side scaffolding guarantee
#: (phase3 second recurrence: adjudication 004 staged character_matrix lost
#: live's frontmatter at the keyed-merge commit, and the calibration writer
#: created resonance_anchors.md as a bare headerless table for 57 chapters).
#: Presence of A frontmatter block is the invariant; richer shells keep
#: their own (category/status/generated_at) untouched.
_TRUTH_FRONTMATTER = "---\ntype: truth\ncategory: state\nstatus: filled\n---\n"


def ensure_truth_frontmatter(filename: str, content: str) -> str:
    """Prepend the canonical truth frontmatter when *content* lacks one.

    Single helper behind every truth-file creation surface (keyed upsert
    create-path, staging merge base, whole-file replace/creation forms) —
    frontmatter presence is a program invariant, never the LLM's job.
    """
    if content.lstrip().startswith("---"):
        return content
    return _TRUTH_FRONTMATTER + content


#: Contract headers bootstrapped when a cumulative table file is CREATED by
#: the keyed upsert path. Probe2: the first resonance_trend row landed on an
#: empty base, producing a headerless file the longitudinal reader rejects
#: ("contract header row missing") — both writers (skill increment and the
#: framework's post-review persistence) route through the upsert, so the
#: create-path is the single bootstrap point.
_TABLE_HEADER_BOOTSTRAP: dict[str, str] = {
    "resonance_trend.md": (
        "| chapter | 类型 | 子项1 | 子项2 | 子项3 | 子项4 | overall | 档位 | human_overridden |"
    ),
    # probe17 ch1 step 7 (adjudication #006): bridge_tracker's sanctioned
    # first write is rows-only (the skill's write discipline forbids emitting
    # headers/titles) — the create-path bootstraps the 8-column contract
    # header the tracking procedure needs (状态/实际激活章/备注 columns).
    "bridge_tracker.md": (
        "| Bridge ID | 钩子内容 | 类型 | 带入卷 | 预期激活章 | 当前状态 | 实际激活章 | 备注 |"
    ),
    # Framework's own post-review persistence (confidence_calibration):
    # anchor outcome rows land via insert_markdown_row on a missing base —
    # unregistered meant 57 chapters of bare headerless rows (phase3).
    "resonance_anchors.md": "| chapter | high_conf_anchors | correct |",
    # batch #15 #44/#38: five single-table keyed files whose first rows-only
    # write can land on a missing/shell base (probe20: settle's rows-only
    # first write chained onto a status:initialized template). Headers pinned
    # to the writers' contract forms. #18-6 (probe24): the composite-key
    # files join the map — their contract keys (#50 角色A,角色B / F-4 章节,角色)
    # only ACTIVATE via the header (_key_columns degrades to first-column on
    # a headerless shell, collapsing same-chapter multi-row writes), and the
    # shells delegate table creation to settle while the increment discipline
    # says rows-only. audit_drift stays out (YAML-form owned by a
    # create_or_overwrite merger).
    "current_state.md": "| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |",
    "particle_ledger.md": "| 章节 | 变动项 | 收支 | 来源／用途 | 余额或备注 |",
    "subplot_board.md": "| 章节 | 支线 | 起始章 | 当前阶段 | 下一节点 |",
    "chapter_summaries.md": (
        "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |"
    ),
    "arc_payoff_trend.md": (
        "| volume | 弧情感交付 | 伏笔兑现质量 | 线索收束 | 期待债务结算 | 角色弧推进 | overall | confidence | human_overridden |"
    ),
    "emotional_arcs.md": "| 章节 | 角色 | 本章情感弧线 |",
    # character_matrix is dual-table (交互总表 + 信息边界 sections); the
    # keyed 交互总表 header is the one the append_dedup contract targets.
    "character_matrix.md": "| 角色A | 角色B | 关系性质 | 本章交互 | 变化 |",
    # Batch #27 (probe32 ch2 settle 4-attempt deadlock): pending_hooks was
    # the ONLY keyed truth table without a bootstrap header — genesis wrote
    # the hook registry onto the shell base as bare headerless rows, which
    # disabled the G4 lifecycle-column exemption (header-keyed) and framed
    # the foreshadowing-track's legal PLANTED→RELEVANT bump as a settle
    # stable-column rewrite. 8-column form = the lifecycle writer's own
    # contract shape (skills/shenbi-foreshadowing-lifecycle).
    "pending_hooks.md": (
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance | 升级曲线 |"
    ),
}


def ensure_table_header(filename: str, content: str) -> str:
    """Prepend the file's contract header when *content* starts with a bare
    data row (file creation) and a header is registered for *filename*.

    probe17 #32: the pre-existing discriminator ("chapter" not in the first
    line) was resonance-specific — any other registered header re-prepended
    on every call. Header-present (exact match anywhere) short-circuits, and
    the separator row is derived from the header's own column count.
    """
    header = _TABLE_HEADER_BOOTSTRAP.get(filename)
    # Frontmatter guarantee runs BEFORE the registered-header early-out:
    # unregistered truth files (resonance_anchors incident) must still gain
    # the canonical block on creation.
    if not content.lstrip().startswith("---"):
        content = ensure_truth_frontmatter(filename, content)
    if not header:
        return content
    separator = "|" + "---|" * (header.count("|") - 1)
    if not content.strip():
        return header + "\n" + separator
    if header in content:
        return content  # already bootstrapped
    # #38 extension (probe22 adjudication #006 P1-2): a frontmatter stub base
    # (``---`` first line, zero pipe rows) matched neither branch above, so
    # the first rows-only write chained onto a headerless shell and
    # _key_columns silently degraded composite keys to first-column. Headers
    # are the composite-key ACTIVATION condition — on a table-less base,
    # append the contract table where the rows will land (EOF).
    if all(split_table_cells(line) is None for line in content.split("\n")):
        return content.rstrip() + "\n\n" + header + "\n" + separator
    # Bare-first-row detection must see past a leading frontmatter block —
    # the block is scaffolding, not the first data line (a frontmatter-carrying
    # headerless base is the repair form: rows exist, header missing). The
    # header lands AFTER the block, keeping frontmatter first.
    fm_block, body = "", content
    if body.startswith("---"):
        close = body.find("\n---", 3)
        if close != -1:
            fm_block = body[: close + 4] + "\n"
            body = body[close + 4 :].lstrip("\n")
    first = next((line for line in body.split("\n") if line.strip()), "")
    if first.lstrip().startswith("|") and "chapter" not in first and "---" not in first:
        return fm_block + header + "\n" + separator + "\n" + body
    return content


_BULLET_ROW_RE = re.compile(r"^\s*-\s*(?P<key>.+?)\s*:(?P<rest>.*)$")

#: Hook-detail headings (``### MH01（名）`` / ``### MH-001 · 名``) mark
#: sections whose only legitimate mutations are named-field bullet updates
#: (probe3 P0: the only merge primitive for headed sections was whole-section
#: replacement, which made the LLM responsible for verbatim base
#: reproduction — 189 dropped lines on attempt1, then a 49152-token
#: whole-file retry on attempt2).
#:
#: probe15 (batch #10): the family MUST accept the genesis template's live
#: form ``MH02（钩子名）`` (no hyphen, id + name in one heading) — machinery
#: that rejects the framework's own pinned template form is a defect, and
#: the hyphen-only regex made the field-level merge unreachable for every
#: probe output (splitter grouped whole ``## 详情`` blocks into one unit;
#: scaffold headings fell to destructive section replacement).
_HOOK_HEADING_RE = re.compile(r"^(#{2,6})\s+((?:MH|H|CP)-?\d{1,4})\b")

#: Any hook heading line, for scanning a whole file's hook sections.
_HOOK_HEADING_BLOCK_RE = re.compile(r"^(#{2,6})\s+((?:MH|H|CP)-?\d{1,4})\b", re.MULTILINE)

#: A hook id embedded in a table cell (``| MH01（名） | …``).
_HOOK_ID_CELL_RE = re.compile(r"(?<![A-Za-z0-9-])(MH|CP)-?(\d{1,4})(?!\d)")

#: Outline-ledger section locator: heading level + 编号 token — ``## 第N卷：…``
#: (volume_map) and ``### A1: …`` (thread_map). Locating by token, not the
#: full heading line, keeps a RETITLED section replacing its old span instead
#: of appending a duplicate (the exact-match ``_replace_section`` seam).
_OUTLINE_SECTION_KEY_RE = re.compile(
    r"^(#{2,6})\s+(第[一二三四五六七八九十百千\d]+卷|[A-Za-z]+\d+)\b"
)

#: Thread-ledger detail-section heading (``### A1: 名称``). Same group
#: layout as the hook family: group(2) = the thread id token.
_THREAD_HEADING_RE = re.compile(r"^(#{2,6})\s+([ABC]\d{1,3})(?![0-9A-Za-z])")

#: Any thread heading line, for scanning a whole file's thread sections.
_THREAD_HEADING_BLOCK_RE = re.compile(r"^(#{2,6})\s+([ABC]\d{1,3})(?![0-9A-Za-z])", re.MULTILINE)

#: A thread id embedded in a table cell's first column (``| A1 | …``).
_THREAD_ID_CELL_RE = re.compile(r"(?<![A-Za-z0-9-])([ABC]\d{1,3})(?![0-9A-Za-z])")


def parse_thread_span(value: str) -> tuple[str, str]:
    """``第27章 - 第109章`` -> ("27", "109"); no chapter number -> ("", "").

    Shared by the 总览 row derivation and the ledger archival (B 批): the
    thread ledger's resolve chapter is the END of the 跨度 bullet. An
    OPEN-ENDED span (``第5章 - 全书末`` — the part after the separator has
    no chapter number) parses to ("", "") so neither the derivation nor
    the archival ever guesses at an end the text does not state.
    """
    parts = re.split(r"[-–—~～至]", value, maxsplit=1)
    if len(parts) == 2:
        nums_start = re.findall(r"\d+", parts[0])
        nums_end = re.findall(r"\d+", parts[1])
        if not nums_end:
            return "", ""
        return (nums_start[0] if nums_start else ""), nums_end[0]
    nums = re.findall(r"\d+", value)
    if not nums:
        return "", ""
    return nums[0], nums[-1]


def _replace_outline_section(existing: str, section: str) -> str | None:
    """Replace the section matched by heading level + 编号 token (or None).

    Same span/shrink/rhythm semantics as :func:`_replace_section`, but the
    locator is the token (``第N卷`` / thread id), so a retitled heading
    still targets its own section. None when *section* carries no outline
    locator or no live section matches (caller falls back).
    """
    first_line = next((l for l in section.split("\n") if l.strip()), "")
    km = _OUTLINE_SECTION_KEY_RE.match(first_line.strip())
    if km is None:
        return None
    level = len(km.group(1))
    token = km.group(2)
    lines = existing.split("\n")
    for i, line in enumerate(lines):
        lm = _OUTLINE_SECTION_KEY_RE.match(line.strip())
        if lm is None or len(lm.group(1)) != level or lm.group(2) != token:
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("#"):
                lvl = len(stripped) - len(stripped.lstrip("#"))
                if lvl <= level:
                    end = j
                    break
        old_span = "\n".join(lines[i:end])
        if len(section) < len(old_span) // 2:
            log.warning(
                "truth_section_replace_shrank",
                heading=line.strip()[:60],
                old_len=len(old_span),
                new_len=len(section),
            )
        new_lines = lines[:i] + section.split("\n") + lines[end:]
        out = "\n".join(new_lines)
        return re.sub(r"\n{3,}", "\n\n", out)
    return None


def touch_frontmatter_updated_at(text: str, iso_now: str) -> str:
    """Rewrite the frontmatter ``updated_at`` line (mechanical maintenance).

    Section-increment writers no longer emit frontmatter (scaffold is
    rejected) — the merge layer keeps the timestamp current instead, the
    same derivation discipline as the pool overview rows. No-op without a
    frontmatter or without an existing ``updated_at`` key (never invents
    frontmatter structure).
    """
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m is None:
        return text
    fm, body = m.group(1), text[m.end() :]
    if not re.search(r"^updated_at\s*[:：]", fm, re.MULTILINE):
        return text
    fm = re.sub(
        r"^(updated_at\s*[:：]\s*).*$",
        rf'\g<1>"{iso_now}"',
        fm,
        count=1,
        flags=re.MULTILINE,
    )
    return f"---\n{fm}\n---\n{body}"


def canon_hook_id(raw: str) -> str:
    """Canonical hook id: ``MH-001`` ≡ ``MH01`` ≡ ``mh1``.

    Family letters uppercased, hyphen dropped, leading zeros stripped, so
    live-form (genesis template), gate-example, and legacy heading keys all
    address the same hook. Non-family ids (``CH1-L1`` local hooks) pass
    through uppercased.
    """
    m = re.fullmatch(r"([A-Za-z]+)-?0*(\d+)", raw.strip())
    if not m:
        return raw.strip().upper()
    return f"{m.group(1).upper()}{m.group(2)}"


def is_hook_heading(text: str) -> bool:
    """True when *text* is a hook-keyed heading (``### MH01(名)``).

    Public seam over :data:`_HOOK_HEADING_RE` for cross-module consumers
    (dispatch_helper's increment splitter must keep hook sections
    independently routed — escalation #16).
    """
    return _HOOK_HEADING_RE.match(text.strip()) is not None


#: A registry table row whose first cell starts with a hook id (live form
#: ``| MH01（名） | … |`` or legacy ``| MH-001 | … |``).
_HOOK_ROW_IN_TABLE_RE = re.compile(r"^\|\s*(?:MH|H|CP)-?\d{1,4}(?=[\s（(｜|]|$)")


def base_has_hook_content(text: str) -> bool:
    """True when *text* already carries keyed hook content.

    Registry table rows or hook-keyed detail headings — the content the
    dispatch-side scaffold guard exists to protect from whole-file
    replacement (probe15). A base with NONE of it is a first-write target
    where the whole-file form is the sanctioned creation shape (genesis
    registry first-write, probe16 adjudication #001: the foreshadowing
    skill's genesis contract mandates the ``## 总览`` EXACT table, which no
    increment-only form can ever produce).
    """
    for line in text.split("\n"):
        s = line.strip()
        if _HOOK_ROW_IN_TABLE_RE.match(s):
            return True
        if s.startswith("#") and is_hook_heading(s):
            return True
    return False


#: A cell/body that is pure template placeholder — not data (#44).
_SHELL_CELL_PLACEHOLDER_RE = re.compile(r"[（(]?\s*(?:待填充|暂无|TODO|TBD)\s*[）)]?")
#: A whole line that ANNOUNCES itself as placeholder scaffolding
#: (``（待填充：...说明...）`` guidance notes included).
_SHELL_LINE_PLACEHOLDER_RE = re.compile(r"^\s*[（(]?(?:待填充|暂无)\b")
#: Headings whose body is instructional prose, never data.
_INSTRUCTIONAL_HEADING_RE = re.compile(r"格式约定|使用说明|填写说明|字段说明|^说明$")
#: Table rows made only of structure (header/separator) carry no data.
_TABLE_SEPARATOR_LINE_RE = re.compile(r"^[\s:|\-]+$")


def base_is_shell(text: str) -> bool:
    """True when *text* carries no real data worth protecting (batch #15 #44).

    probe20 (adjudication /tmp/probe20-adjudication-008.md): after the
    escalation-reject staging wipe, chapter-keyed truth bases were
    ``status: initialized`` templates while the re-dispatch feedback
    described a settled world — the model's whole-file creation was its only
    rational output, and a guard with no first-write exemption rejected it
    into a byte-identical retry death. SHELL means "nothing to protect":
    every line classifies as ignorable scaffolding (blank, frontmatter,
    heading, quote, structural table rows, placeholder cells/lines,
    instructional-section prose under 格式约定/说明 headings) or as REAL
    data (any data-table row, hook detail heading, data bullet, prose
    outside instructional sections). All-scaffolding = the whole-file
    creation form is sanctioned there.
    """
    if not text or not text.strip():
        return True
    lines = text.split("\n")
    i = 0
    n = len(lines)
    # Skip a LEADING frontmatter block (fenced key/value pairs, no data).
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].strip() == "---":
        i += 1
        while i < n and lines[i].strip() != "---":
            i += 1
        i += 1  # past the closing fence (or EOF)

    instructional = False
    for idx in range(i, n):
        line = lines[idx].strip()
        if not line:
            continue
        if line.startswith("#"):
            if _HOOK_HEADING_RE.match(line):
                return False  # a hook detail heading IS keyed content
            title = line.lstrip("#").strip()
            instructional = _INSTRUCTIONAL_HEADING_RE.search(title) is not None
            continue
        if line.startswith(">"):
            continue  # guidance quote
        if line.startswith("|"):
            if _TABLE_SEPARATOR_LINE_RE.fullmatch(line):
                continue
            # A table row directly above a separator row is the HEADER row —
            # structure, not data.
            nxt = idx + 1
            while nxt < n and not lines[nxt].strip():
                nxt += 1
            if nxt < n and _TABLE_SEPARATOR_LINE_RE.fullmatch(lines[nxt].strip()):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if any(c and not _SHELL_CELL_PLACEHOLDER_RE.fullmatch(c) for c in cells):
                return False  # a real data cell
            continue
        if line.startswith("-"):
            body = line.lstrip("-").strip()
            if _SHELL_LINE_PLACEHOLDER_RE.match(body) or _SHELL_CELL_PLACEHOLDER_RE.fullmatch(body):
                continue
            return False  # a data bullet
        # Prose
        if instructional or _SHELL_LINE_PLACEHOLDER_RE.match(line):
            continue
        return False
    return True


_COLON_BULLET_RE = re.compile(r"^-\s*([^:：\s][^:：]*)\s*[:：]")

#: pending_hooks per-hook bullets that legitimately mutate every chapter.
#: Single source of the hooks increment contract: the G4 checker's volatile
#: exemption, the dispatch prompt injection, and the settle
#: IncrementShapeError remediation text all render from these tuples.
#: phase3 escalation #1 (novel-xinghuo-phase3 ch1): the three sites had
#: drifted apart — no site's text banned ``plant_chapter`` and the settle
#: writer rewrote exactly that, three attempts in a row.
HOOKS_VOLATILE_FIELDS: tuple[str, ...] = ("lifecycle_state", "证据", "notes", "last_reinforced")

#: Every other named field in a hook detail block is base mass: stable
#: across settles, owned by the genesis/foreshadowing-track writer.
HOOKS_STABLE_FIELDS: tuple[str, ...] = (
    "type",
    "dimension",
    "plant_chapter",
    "resolve_chapter",
    "subtlety",
    "cultivation_interval",
    "max_distance",
    "escalation_curve",
    "trigger_condition",
    "resolve_condition",
    "depends_on",
)


def hooks_stable_fields_hint() -> str:
    """Slash-joined stable field names for the contract texts."""
    return "/".join(HOOKS_STABLE_FIELDS)


def table_header_registered(filename: str) -> bool:
    """Whether a truth target's keyed form is a registered table file.

    Phase3 esc#2: the user-prompt increment contract renders per-target
    sanctioned forms and must not reach into the registry dict directly
    (strict typecheck owns the private boundary); table-registered targets
    get the table-row form, everything else the section-increment form.
    """
    return filename in _TABLE_HEADER_BOOTSTRAP


def _canon_field_name(name: str) -> str:
    """Field ADDRESSING name: emphasis markers stripped.

    probe18 adjudication #005 (#35): genesis improvised a bold grammar
    (``- **notes**: …``) while the raw capture kept the stars — a bold
    increment name-matched a differently-styled live line and
    whole-line-replaced it. ``**notes**`` ≡ ``notes`` for targeting; the
    REPLACED line keeps the increment's own form (content strictness
    unchanged — G4 still gates the result).
    """
    return name.strip().strip("*").strip()


def _hook_section_bullet_merge(existing: str, unit: str) -> str | None:
    """Patch a hook section's named fields in place; None when inapplicable.

    Applicable when the unit's first non-empty line is a hook heading and
    every other non-empty line is a ``- name: value`` colon bullet — a pure
    field update. Each bullet replaces the section's first same-name bullet
    in place; names absent from the live section insert after its last
    bullet. Stable lines are never re-emitted, so they cannot be dropped or
    rewritten by construction. Section location: exact heading line first,
    else same heading level + hook id (a paraphrased title after the id
    still targets the live block instead of appending a duplicate section).
    Accumulating fields (证据/notes) must restate their full history in the
    increment — the writer's contract duty, not the merge's.
    """
    unit_lines = unit.split("\n")
    h_idx = next((i for i, l in enumerate(unit_lines) if l.strip()), None)
    if h_idx is None:
        return None
    heading = unit_lines[h_idx].strip()
    hm = _HOOK_HEADING_RE.match(heading)
    if not hm:
        return None
    level = len(hm.group(1))
    hook_id = canon_hook_id(hm.group(2))
    fields: list[tuple[str, str]] = []
    for line in unit_lines[h_idx + 1 :]:
        s = line.strip()
        if not s:
            continue
        fm = _COLON_BULLET_RE.match(s)
        if not fm:
            return None  # free-form content = section rewrite — legacy replace
        fields.append((_canon_field_name(fm.group(1)), line.rstrip()))
    if not fields:
        return None

    lines = existing.split("\n")
    target: int | None = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("#"):
            continue
        if s == heading:
            target = i
            break
        tm = _HOOK_HEADING_RE.match(s)
        if tm and len(tm.group(1)) == level and canon_hook_id(tm.group(2)) == hook_id:
            target = i
            break
    if target is None:
        return None  # unknown hook — caller appends the whole unit

    end = len(lines)
    for j in range(target + 1, len(lines)):
        s = lines[j].lstrip()
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            if lvl <= level:
                end = j
                break

    used = [False] * len(fields)
    for fi, (name, newline) in enumerate(fields):
        for j in range(target + 1, end):
            s = lines[j].strip()
            if not s.startswith("-"):
                continue
            fm = _COLON_BULLET_RE.match(s)
            if fm and _canon_field_name(fm.group(1)) == name:
                lines[j] = newline
                used[fi] = True
                break
    bullet_positions = [j for j in range(target + 1, end) if lines[j].strip().startswith("-")]
    insert_at = bullet_positions[-1] + 1 if bullet_positions else target + 1
    for fi, (name, newline) in enumerate(fields):
        if not used[fi]:
            lines.insert(insert_at, newline)
            insert_at += 1
    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    return out


#: Detail-section field → 总览 column key (header cell normalized by cutting
#: at the first full/half-width paren, lowercased). The overview table is a
#: DERIVED mirror of the detail sections — see :func:`sync_pool_overview_rows`.
_POOL_ROW_FIELD_COLS: dict[str, str] = {
    "lifecycle_state": "当前生命周期",
    "plant_chapter": "种植章",
    "resolve_chapter": "兑现章",
    "type": "类型",
    "subtlety": "微妙度",
    "max_distance": "max_distance",
    "escalation_curve": "升级曲线",
}


def _pool_col_key(header: str) -> str:
    """Normalize an overview header cell to its matching key."""
    h = header.strip()
    for cut in ("（", "("):
        idx = h.find(cut)
        if idx != -1:
            h = h[:idx]
    return h.strip().lower()


def _named_section_fields(
    text: str, heading_re: re.Pattern[str], canon: Callable[[str], str], entry_id: str
) -> tuple[str, dict[str, str]] | None:
    """The section heading display text + latest colon-bullet fields of
    *entry_id*'s section (first bullet per name), or None when the section
    is absent. Same section-location rule as
    :func:`_hook_section_bullet_merge` (exact heading, else heading level +
    id token via *canon*).
    """
    lines = text.split("\n")
    target: int | None = None
    level = 0
    heading = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("#"):
            continue
        hm = heading_re.match(s)
        if not hm:
            continue
        if canon(hm.group(2)) == entry_id:
            target = i
            level = len(hm.group(1))
            heading = s
            break
    if target is None:
        return None
    end = len(lines)
    for j in range(target + 1, len(lines)):
        s = lines[j].lstrip()
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            if lvl <= level:
                end = j
                break
    fields: dict[str, str] = {}
    for line in lines[target + 1 : end]:
        s = line.strip()
        fm = _COLON_BULLET_RE.match(s)
        if fm:
            fields.setdefault(_canon_field_name(fm.group(1)), s[fm.end() :].strip())
    return heading, fields


def _hook_section_field_values(text: str, hook_id: str) -> tuple[str, dict[str, str]] | None:
    """Hook-section variant of :func:`_named_section_fields`."""
    return _named_section_fields(text, _HOOK_HEADING_RE, canon_hook_id, hook_id)


def _thread_section_field_values(text: str, thread_id: str) -> tuple[str, dict[str, str]] | None:
    """Thread-section variant of :func:`_named_section_fields` (id as-is)."""
    return _named_section_fields(text, _THREAD_HEADING_RE, lambda s: s.strip(), thread_id)


def sync_pool_overview_rows(existing: str, hook_ids: set[str] | None = None) -> str:
    """Reconcile pending_hooks 总览 rows from the hook detail sections.

    GO① root fix (phase3 终报: the overview table froze ch15-36): track/
    resolve/settling are contract-forbidden from emitting overview rows
    (anti-whole-pool-rewrite) and lifecycle only covers its own chapter's
    hooks, so detail sections advanced while their overview rows silently
    went stale — and post-genesis planted hooks never got rows at all. This
    makes the merge layer derive the row mechanically whenever a hook
    section lands: the table becomes a derived mirror, with no LLM writer
    discipline load-bearing for the two representations staying in sync.

    *hook_ids* scopes the reconciliation (the merge path passes the one hook
    it just landed); ``None`` reconciles every section — the repair-tool
    entry. Sections without a row get one appended to the 总览 table; rows
    are never deleted here (orphan-row reporting belongs to the pool lint).
    The 兑现章 cell keeps an existing volume suffix (``107(五卷)``) when the
    numeric part already matches the derived resolve chapter. No-op (returns
    *existing*) when the file has no ``## 总览`` table or no header row.
    """
    m_ov = re.search(r"^##\s*总览\s*$", existing, re.MULTILINE)
    if m_ov is None:
        return existing
    m_det = re.search(r"^##\s*\S", existing[m_ov.end() :], re.MULTILINE)
    ov_end = m_ov.end() + (m_det.start() if m_det is not None else len(existing[m_ov.end() :]))
    ov_lines = existing[m_ov.end() : ov_end].split("\n")

    header_idx = next((i for i, l in enumerate(ov_lines) if l.strip().startswith("|")), None)
    if header_idx is None:
        return existing
    header_cells = split_table_cells(ov_lines[header_idx])
    if header_cells is None:
        return existing
    col_by_field: dict[str, int] = {}
    for fi, want in _POOL_ROW_FIELD_COLS.items():
        col_idx = next((i for i, c in enumerate(header_cells) if _pool_col_key(c) == want), None)
        if col_idx is not None:
            col_by_field[fi] = col_idx
    if not col_by_field:
        return existing

    sections: list[tuple[str, dict[str, str]]] = []
    for hm in _HOOK_HEADING_BLOCK_RE.finditer(existing):
        hid = canon_hook_id(hm.group(2))
        if hook_ids is not None and hid not in hook_ids:
            continue
        parsed = _hook_section_field_values(existing, hid)
        if parsed is None:
            continue
        sections.append(parsed)
    if not sections:
        return existing

    changed = False
    for heading, fields in sections:
        hid = canon_hook_id(_HOOK_HEADING_RE.match(heading).group(2))  # type: ignore[union-attr]
        row_idx: int | None = None
        row_cells: list[str] | None = None
        for i in range(header_idx + 1, len(ov_lines)):
            line = ov_lines[i].strip()
            if not line.startswith("|"):
                continue
            cells = split_table_cells(line)
            if cells is None or not cells:
                continue
            idm = _HOOK_ID_CELL_RE.search(cells[0])
            if idm is not None and canon_hook_id(f"{idm.group(1)}{idm.group(2)}") == hid:
                if _is_separator_row(cells):
                    continue
                row_idx = i
                row_cells = list(cells)
                break
        new_cells = row_cells if row_cells is not None else ["-"] * len(header_cells)
        while len(new_cells) < len(header_cells):
            new_cells.append("-")
        if row_cells is None:
            new_cells[0] = heading.lstrip("#").strip()
        for fi, col in col_by_field.items():
            if fi not in fields:
                continue
            val = fields[fi]
            old = new_cells[col].strip() if new_cells[col].strip() else "-"
            if fi == "resolve_chapter" and old != "-":
                num = old.split("（", 1)[0].split("(", 1)[0].strip()
                if num == val and ("（" in old or "(" in old):
                    val = old  # numeric part already matches — keep （卷） suffix
            new_cells[col] = val
        new_row = "| " + " | ".join(c.strip() for c in new_cells) + " |"
        if row_idx is not None:
            if ov_lines[row_idx].strip() != new_row:
                ov_lines[row_idx] = new_row
                changed = True
        else:
            last_row = max(
                (
                    i
                    for i in range(header_idx + 1, len(ov_lines))
                    if ov_lines[i].strip().startswith("|")
                ),
                default=header_idx,
            )
            ov_lines.insert(last_row + 1, new_row)
            changed = True
    if not changed:
        return existing
    log.info("truth_pool_overview_row_derived", hooks=len(sections))
    return existing[: m_ov.end()] + "\n".join(ov_lines) + existing[ov_end:]


#: Thread 总览 column derivation (B 批): detail-section field → 线索总览表
#: column key. 起始章/终点章 derive from the 跨度 bullet via
#: :func:`parse_thread_span`; 名称 comes from the heading (creation only);
#: 类型 has no section source (overview-only taxonomy) and is left as-is.
_THREAD_ROW_FIELD_COLS: dict[str, str] = {
    "状态": "状态",
    "优先级": "优先级",
    "max_gap": "max_gap",
}


def sync_thread_overview_rows(existing: str, thread_ids: set[str] | None = None) -> str:
    """Reconcile thread_map 线索总览表 rows from the thread detail sections.

    B 批, the GO① derivation mirrored onto the thread ledger: the weaver's
    increments are ``### <ID>: <名称>`` sections, and the overview row is a
    DERIVED mirror — no LLM writer discipline is load-bearing for the two
    representations staying in sync (the pool's ch15-36 overview freeze is
    the design precedent this prevents).

    *thread_ids* scopes the reconciliation (the merge path passes the one
    thread it just landed); ``None`` reconciles every section — the
    repair-tool entry. Sections carrying an ``archived_to`` tombstone bullet
    NEVER resurrect a row (ledger_archive owns the archived ids). Rows are
    never deleted here (orphan-row reporting belongs to the truth-pool
    lint). No-op (returns *existing*) without a ``## 线索总览表`` table or
    header row.
    """
    m_ov = re.search(r"^##\s*线索总览表\s*$", existing, re.MULTILINE)
    if m_ov is None:
        return existing
    m_det = re.search(r"^##\s*\S", existing[m_ov.end() :], re.MULTILINE)
    ov_end = m_ov.end() + (m_det.start() if m_det is not None else len(existing[m_ov.end() :]))
    ov_lines = existing[m_ov.end() : ov_end].split("\n")

    header_idx = next((i for i, l in enumerate(ov_lines) if l.strip().startswith("|")), None)
    if header_idx is None:
        return existing
    header_cells = split_table_cells(ov_lines[header_idx])
    if header_cells is None:
        return existing
    col_by_field: dict[str, int] = {}
    for fi, want in _THREAD_ROW_FIELD_COLS.items():
        col_idx = next((i for i, c in enumerate(header_cells) if _pool_col_key(c) == want), None)
        if col_idx is not None:
            col_by_field[fi] = col_idx
    col_start = next((i for i, c in enumerate(header_cells) if _pool_col_key(c) == "起始章"), None)
    col_end = next((i for i, c in enumerate(header_cells) if _pool_col_key(c) == "终点章"), None)
    col_name = next((i for i, c in enumerate(header_cells) if _pool_col_key(c) == "名称"), None)
    if not col_by_field:
        return existing

    sections: list[tuple[str, dict[str, str]]] = []
    for tm in _THREAD_HEADING_BLOCK_RE.finditer(existing):
        tid = tm.group(2).strip()
        if thread_ids is not None and tid not in thread_ids:
            continue
        parsed = _thread_section_field_values(existing, tid)
        if parsed is None:
            continue
        sections.append(parsed)
    if not sections:
        return existing

    changed = False
    for heading, fields in sections:
        hm = _THREAD_HEADING_RE.match(heading)
        if hm is None:
            continue
        tid = hm.group(2).strip()
        if "archived_to" in fields:
            continue
        row_idx: int | None = None
        row_cells: list[str] | None = None
        for i in range(header_idx + 1, len(ov_lines)):
            line = ov_lines[i].strip()
            if not line.startswith("|"):
                continue
            cells = split_table_cells(line)
            if cells is None or not cells:
                continue
            idm = _THREAD_ID_CELL_RE.search(cells[0])
            if idm is not None and idm.group(1) == tid:
                if _is_separator_row(cells):
                    continue
                row_idx = i
                row_cells = list(cells)
                break
        new_cells = row_cells if row_cells is not None else ["-"] * len(header_cells)
        while len(new_cells) < len(header_cells):
            new_cells.append("-")
        if row_cells is None:
            new_cells[0] = tid
            if col_name is not None:
                hm_name = re.split(r"[:：]", heading.lstrip("#").strip(), maxsplit=1)
                new_cells[col_name] = hm_name[1].strip() if len(hm_name) > 1 else "-"
        for fi, col in col_by_field.items():
            if fi in fields:
                new_cells[col] = fields[fi]
        start, end = parse_thread_span(fields.get("跨度", ""))
        if start and col_start is not None:
            new_cells[col_start] = start
        if end and col_end is not None:
            new_cells[col_end] = end
        new_row = "| " + " | ".join(c.strip() for c in new_cells) + " |"
        if row_idx is not None:
            if ov_lines[row_idx].strip() != new_row:
                ov_lines[row_idx] = new_row
                changed = True
        else:
            last_row = max(
                (
                    i
                    for i in range(header_idx + 1, len(ov_lines))
                    if ov_lines[i].strip().startswith("|")
                ),
                default=header_idx,
            )
            ov_lines.insert(last_row + 1, new_row)
            changed = True
    if not changed:
        return existing
    log.info("thread_overview_row_derived", threads=len(sections))
    return existing[: m_ov.end()] + "\n".join(ov_lines) + existing[ov_end:]


def _render_bullet_row(new_data: dict[str, Any], key_field: str) -> str:
    """Render a dict row as the ``- {key}: {k=v ...}`` bullet format."""
    key_val = str(new_data.get(key_field, ""))
    rest_fields = " ".join(f"{k}={v}" for k, v in new_data.items() if k != key_field)
    return f"- {key_val}: {rest_fields}" if rest_fields else f"- {key_val}:"


def _upsert_markdown_bullet(
    path: Path,
    filename: str,
    new_data: dict[str, Any],
    key_field: str | None,
) -> None:
    """Upsert a dict row into a bullet-format markdown truth file (T701 fix).

    SURGICAL line edit: the existing bullet line whose key equals the new
    row's ``key_field`` value is replaced in place (later duplicates of the
    same key are dropped); if no such line exists the new bullet is appended
    at the end of the file. Every other line — frontmatter, H1/H2 headings,
    prose, bullets for other keys — is preserved verbatim. The old
    implementation re-serialized the whole file as a bare bullet list,
    collapsing the file structure.
    """
    if key_field is None:
        raise ValueError("upsert_markdown_row requires key_field")
    key_val = str(new_data.get(key_field, ""))
    new_line = _render_bullet_row(new_data, key_field)

    if not path.exists():
        body = f"# {filename.removesuffix('.md')}\n\n{new_line}\n"
        safe_write(path, body.encode("utf-8"))
        log.info("truth_file_written", path=str(path), mode="upsert_markdown_row", rows=1)
        return

    if not key_val:
        # No natural key — preserve (append) and log rather than dedup-match
        # every other keyless row (symmetric with the T703 policy).
        log.warning("truth_bullet_upsert_empty_key", key_field=key_field)
        text = path.read_text(encoding="utf-8")
        merged = text.rstrip("\n") + "\n" + new_line + "\n"
        safe_write(path, merged.encode("utf-8"))
        return

    lines = path.read_text(encoding="utf-8").split("\n")
    replaced = False
    duplicates = 0
    kept: list[str] = []
    for line in lines:
        m = _BULLET_ROW_RE.match(line)
        if m and m.group("key").strip() == key_val:
            if not replaced:
                kept.append(new_line)  # first match: update in place
                replaced = True
            else:
                duplicates += 1  # historical duplicate rows are collapsed
        else:
            kept.append(line)
    if not replaced:
        # Append after the last non-empty line, keeping trailing blank lines.
        while kept and kept[-1] == "":
            kept.pop()
        kept.append(new_line)
        kept.append("")
    body = "\n".join(kept)
    if not body.endswith("\n"):
        body += "\n"
    safe_write(path, body.encode("utf-8"))
    if duplicates:
        log.warning("truth_bullet_upsert_duplicate_rows_dropped", key=key_val, count=duplicates)
    log.info(
        "truth_file_written",
        path=str(path),
        mode="upsert_markdown_row",
        replaced=replaced,
    )


def patch_markdown_table_cell(
    path: Path, key: str, key_field: str, cell_index: int, value: str
) -> bool:
    """Patch a single cell of an existing markdown table row (spec #33 T1b).

    Column location is positional (``cell_index``), not header-based: header
    placement is uncontrolled for append_dedup writers (spec #33 v8 ruling).
    ``key_field`` is logging-only observability (position, not header, rules).
    Rows shorter than ``cell_index + 1`` are padded with ``-`` placeholders.
    Key matching is exact whole-cell (consistent with upsert_markdown_row).
    Returns False when the file or the keyed row does not exist; header and
    separator rows are never patched; negative cell_index is rejected.
    Thread-safe via the per-path lock registry (same rationale as
    ``insert_markdown_row``). Preserves the file's CRLF/LF convention.
    """
    lock = _path_lock(path)
    with lock:
        if not path.exists():
            return False
        # Bytes + decode: read_text() would translate CRLF to LF (universal
        # newlines), silently rewriting the whole file's line endings.
        raw = path.read_bytes().decode("utf-8")
        had_crlf = "\r\n" in raw
        lines = raw.splitlines()
        for idx, line in enumerate(lines):
            cells = split_table_cells(line)
            if cells is None:
                continue
            if _is_separator_row(cells):
                continue
            # Header row: the immediately following line is a separator.
            if idx + 1 < len(lines):
                nxt = split_table_cells(lines[idx + 1])
                if nxt is not None and _is_separator_row(nxt):
                    continue
            # Exact whole-cell key match (consistent with upsert_markdown_row);
            # _norm_cell would collide "5-2" with "52".
            if cells[0] != key:
                continue
            while len(cells) <= cell_index:
                cells.append("-")
            if cell_index < 0:
                log.warning("truth_cell_patch_bad_index", cell_index=cell_index)
                return False
            cells[cell_index] = value
            lines[idx] = "| " + " | ".join(c.strip() for c in cells) + " |"
            sep = "\r\n" if had_crlf else "\n"
            safe_write(path, (sep.join(lines) + sep).encode("utf-8"))
            log.info(
                "truth_cell_patched",
                path=str(path),
                key=key,
                key_field=key_field,
                cell_index=cell_index,
            )
            return True
        return False


def split_table_cells(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a row.

    A table row starts and ends with ``|``. Cell boundaries are the pipes
    themselves, so a key is the FULL cell text — never the first whitespace
    token. This is the T702 fix: keys like ``第 1 章`` or ``Ch 1`` (containing
    spaces/CJK) must compare as whole cells, otherwise rows whose first
    *token* collides (``第`` == ``第``) wrongly dedup each other and whole
    families of rows get deleted.
    """
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or len(s) < 2:
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _norm_cell(cell: str) -> str:
    """Normalize a header cell for key-column matching (T713).

    ``Hook ID``, ``hook_id`` and ``hook-id`` all normalize to ``hookid`` so
    the contract ``key_field`` declaration can locate its column by header
    name.
    """
    return re.sub(r"[\s_-]+", "", cell.lower())


def _norm_key(cell: str) -> str:
    """Key-cell IDENTITY for row dedup: whitespace-insensitive only.

    Fixcheck ch3: two settle attempts emitted the same chapter key with
    different spacing (``第 3 章`` vs ``第3章``); exact-string comparison
    treated them as distinct keys and both rows landed in the same table.
    Header-COLUMN matching keeps the broader :func:`_norm_cell` form
    (case/dash-insensitive); row-key identity stays conservative here.
    """
    return re.sub(r"\s+", "", cell)


def _is_separator_row(cells: list[str]) -> bool:
    """True for a markdown table separator row (``| --- | :---: |``)."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def _key_columns(existing: str, key_spec: str) -> list[int]:
    """Locate the key column indices for a single OR composite key spec.

    Single-name specs keep the historical single-column semantics (T713:
    header-cell match positions the key column; first column otherwise; only
    the first table line is a header candidate, and only when followed by a
    separator row — a data row that merely *contains* the key word must not
    redirect the key column).

    Probe2 settle capacity fix: the character_matrix 交互表 keys rows on the
    (角色A, 角色B) TUPLE — a single-column key on 角色A would collapse every
    row sharing the same first character. A comma-separated *key_spec*
    (``"角色A,角色B"``) selects all named columns; the row key is the cell
    tuple. Rule: only the FIRST table line is a header candidate (same
    convention as the historical single-name lookup); when EVERY named column matches the
    header, those positions are the key; otherwise the spec degrades to the
    first column — so mixed-table increments (e.g. the 信息边界表 keyed on
    角色对) keep single-column semantics.
    """
    names = [n for n in (part.strip() for part in key_spec.split(",")) if n]
    lines = existing.split("\n")
    for idx, line in enumerate(lines):
        cells = split_table_cells(line)
        if cells is None:
            continue
        next_cells = next(
            (split_table_cells(l) for l in lines[idx + 1 :] if split_table_cells(l) is not None),
            None,
        )
        if next_cells is not None and not _is_separator_row(next_cells):
            return [0]  # first table line is a data row, not a header
        positions: list[int] = []
        for name in names:
            for i, cell in enumerate(cells):
                if cell and _norm_cell(cell) == _norm_cell(name):
                    positions.append(i)
                    break
            else:
                return [0]  # a named column is absent — degrade to first column
        return positions if positions else [0]
    return [0]


def _structural_table_lines(lines: list[str]) -> list[bool]:
    """Flag structural table lines: separator rows and header rows.

    A header row is a pipe row whose NEXT pipe row is a separator (markdown
    table convention). Headers and separators define table structure — they
    must never be removed or matched as data by the upsert (probe escalation
    #6: an increment re-emitting a ``| Hook ID | ... |`` header deleted the
    live 8-column registry header, leaving the table unparseable).
    """
    flags = [False] * len(lines)
    pipe_indices = [i for i, line in enumerate(lines) if split_table_cells(line) is not None]
    for pos, i in enumerate(pipe_indices):
        cells = split_table_cells(lines[i])
        if cells is not None and _is_separator_row(cells):
            flags[i] = True
            continue
        nxt = pipe_indices[pos + 1] if pos + 1 < len(pipe_indices) else None
        if nxt is not None:
            next_cells = split_table_cells(lines[nxt])
            if next_cells is not None and _is_separator_row(next_cells):
                flags[i] = True
    return flags


def _key_table_tail(lines: list[str], key_name: str) -> int | None:
    """Line index just past the last row of the table whose header carries
    *key_name* — the in-table insertion point for a new-key row.

    Composite specs (``"角色A,角色B"``) match by the SAME all-names rule as
    :func:`_key_columns`: every named column must be present in the header.
    F-1 (probe22 adjudication #009 R4): the tail lookup compared the WHOLE
    comma spec against single header cells, never matched, and a new-key row
    stranded at EOF instead of joining its table.

    None when no table's header matches (callers fall back to EOF append).
    """
    names = [n for n in (part.strip() for part in key_name.split(",")) if n]
    structural = _structural_table_lines(lines)
    for i, line in enumerate(lines):
        if not structural[i] or _is_separator_row(split_table_cells(line) or []):
            continue
        cells = split_table_cells(line) or []
        if all(any(c and _norm_cell(c) == _norm_cell(n) for c in cells) for n in names):
            # #18-3 (probe23): the tail walk used to treat ANY consecutive
            # pipe row as "still in this table" — character_matrix carries a
            # 5-col 交互表 and a 3-col 信息边界表 adjacent with no blank
            # line, and new 5-col rows walked THROUGH the 3-col region
            # (truth/character_matrix.md L26-29 interleave). The table ends
            # where a RUN of different-arity rows begins (the other table's
            # header + its rows); a LONE different-arity row is a ragged row
            # of THIS table (resonance_trend rows under a wider bootstrap
            # header) and does not end it. Separator rows pass unconditionally
            # so a new row can never split a header from its separator.
            arity = len(cells)
            tail = i
            j = i + 1
            while j < len(lines):
                row_cells = split_table_cells(lines[j])
                if row_cells is None:
                    break
                if _is_separator_row(row_cells):
                    tail = j
                    j += 1
                    continue
                if len(row_cells) != arity:
                    nxt = next(
                        (split_table_cells(lines[k]) for k in range(j + 1, len(lines))),
                        None,
                    )
                    if nxt is not None and len(nxt) == len(row_cells):
                        break  # a different-arity RUN — the next table
                    tail = j  # lone ragged row — still this table's row
                    j += 1
                    continue
                tail = j
                j += 1
            return tail + 1
    return None


def _replace_section(existing: str, section: str) -> str | None:
    """Replace the same-heading section in *existing* with *section*.

    The section span runs from the identical heading line to the next
    heading of the same or higher level (or EOF). Returns None when no
    matching heading exists (caller falls back to append).
    """
    lines = existing.split("\n")
    heading = next((l for l in section.split("\n") if l.strip()), "")
    if not heading:
        return None
    level = len(heading) - len(heading.lstrip("#"))
    for i, line in enumerate(lines):
        if line.strip() != heading:
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("#"):
                lvl = len(stripped) - len(stripped.lstrip("#"))
                if lvl <= level:
                    end = j
                    break
        # Observability (session30 调试①): wholesale replacement is the
        # designed compaction route for re-emitted sections, but a large
        # shrink was silent — the ch60 pool dropped 43% with no log line to
        # tell designed compaction from data loss.
        old_span = "\n".join(lines[i:end])
        if len(section) < len(old_span) // 2:
            log.warning(
                "truth_section_replace_shrank",
                heading=heading[:60],
                old_len=len(old_span),
                new_len=len(section),
            )
        # keep surrounding blank-line rhythm: replace the span, ensure a
        # single blank separator before the next heading
        new_lines = lines[:i] + section.split("\n") + lines[end:]
        out = "\n".join(new_lines)
        return re.sub(r"\n{3,}", "\n\n", out)
    return None


def upsert_markdown_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup a markdown table row by whole-cell key-column value (T702/T713).

    The key is the FULL text of the key cell (first cell by default, or the
    column whose header matches *key_name*), never a whitespace token. Rows
    whose key cell equals the new row's key are replaced by the new row
    IN PLACE — the pre-probe-#6 primitive removed the matched row and
    appended the replacement at EOF, so every update relocated its row out
    of the table and dangled it after trailing prose. Everything else
    (frontmatter, headers, separator rows, prose, rows with a different key)
    is preserved verbatim; header-shaped increment rows are skipped (a
    re-emitted ``| Hook ID | ... |`` header used to delete the live header).
    A non-table *new_row* — or one with no usable natural key — is appended
    without dedup so no data is silently dropped (data-preserving fallback,
    symmetric with T703).
    """
    new_cells = split_table_cells(new_row)
    if new_cells is None:
        # Not a table row — no key to dedup on. HEADED sections use REPLACE
        # semantics (probe, twice bitten: the first block-dedup version
        # skipped re-emitted same-heading sections whole, so approved
        # section updates could never reach live through the commit merge —
        # an empty shell that landed first blocked every later filled
        # version). Heading-less prose keeps the append/skip fallback.
        first_line = next((l for l in new_row.split("\n") if l.strip()), "")
        if not first_line:
            return existing
        if first_line.lstrip().startswith("#"):
            merged = _hook_section_bullet_merge(existing, new_row)
            if merged is not None:
                log.info("truth_hook_section_fields_patched", key_name=key_name)
            if merged is None:
                # Outline ledgers (volume_map / thread_map): locate by
                # heading level + 编号 token — retitles replace, not append.
                merged = _replace_outline_section(existing, new_row)
            if merged is None:
                replaced_section = _replace_section(existing, new_row)
                if replaced_section is not None:
                    merged = replaced_section
            if merged is None:
                merged = existing.rstrip() + "\n" + new_row
            # GO① derivation-on-write: a landed hook section mechanically
            # reflects into its 总览 row (only the hook-keyed pool target —
            # generic headed sections in other truth files stay untouched).
            if key_name == "hook_id":
                hm = _HOOK_HEADING_RE.match(first_line.strip())
                if hm is not None:
                    merged = sync_pool_overview_rows(merged, {canon_hook_id(hm.group(2))})
            # B 批: the same derivation for the thread ledger — a landed
            # ``### <ID>: <名称>`` section reflects into its 线索总览表 row.
            if key_name == "thread":
                tm = _THREAD_HEADING_RE.match(first_line.strip())
                if tm is not None:
                    merged = sync_thread_overview_rows(merged, {tm.group(2).strip()})
            return merged
        if any(l.strip() == first_line for l in existing.split("\n")):
            log.warning("truth_block_upsert_duplicate_skipped", key_name=key_name)
            return existing
        log.warning("truth_table_upsert_non_table_row", key_name=key_name)
        return existing.rstrip() + "\n" + new_row
    key_cols = _key_columns(existing, key_name)
    key_col = key_cols[0]
    if any(c >= len(new_cells) for c in key_cols):
        # New row lacks a key column — no natural key; append without dedup.
        log.warning("truth_table_upsert_row_missing_key_column", key_name=key_name, column=key_col)
        return existing.rstrip() + "\n" + new_row
    new_key_cells = [new_cells[c] for c in key_cols]
    if not any(cell.strip() for cell in new_key_cells):
        # Empty key cell(s) = no natural key; append without dedup rather
        # than letting all empty-key rows annihilate each other.
        log.warning("truth_table_upsert_empty_key", key_name=key_name)
        return existing.rstrip() + "\n" + new_row
    header_cells = (
        [key_name.split(",", maxsplit=1)[0].strip()]
        if len(key_cols) == 1
        else [n.strip() for n in key_name.split(",")]
    )
    if len(header_cells) == len(new_key_cells) and all(
        _norm_cell(nc) == _norm_cell(hc)
        for nc, hc in zip(new_key_cells, header_cells, strict=False)
    ):
        # The increment re-emitted this table's HEADER row. Headers are
        # structural: upserting one would delete the live header (key match)
        # and append a ragged copy at the tail (probe escalation #6).
        log.warning("truth_table_upsert_header_row_skipped", key_name=key_name)
        return existing

    lines = existing.split("\n")
    structural = _structural_table_lines(lines)
    result_lines: list[str] = []
    replaced = False
    matched = False
    for i, line in enumerate(lines):
        if not structural[i] and line.lstrip().startswith("|"):
            cells = split_table_cells(line)
            if (
                cells is not None
                and all(c < len(cells) for c in key_cols)
                and _norm_key("×".join(cells[c] for c in key_cols))
                == _norm_key("×".join(new_key_cells))
            ):
                matched = True
                # Shape guard (probe escalation #14): replace only when the
                # new row matches the old width or strictly ENRICHES it
                # (same cells + appended ones). A different-shape rewrite
                # (8-col registry row replaced by a 10-col status row)
                # corrupts the table — keep the old row; the update also
                # lives in the increment's detail sections.
                same_shape = len(cells) == len(new_cells)
                enrichment = len(new_cells) > len(cells) and new_cells[: len(cells)] == cells
                if not replaced and (same_shape or enrichment):
                    result_lines.append(new_row)  # replace at the row's position
                    replaced = True
                elif not replaced:
                    log.warning(
                        "truth_table_upsert_row_shape_mismatch_skipped",
                        key_name=key_name,
                        old_cols=len(cells),
                        new_cols=len(new_cells),
                    )
                    result_lines.append(line)
                # duplicate rows with the same key are dropped
                continue
        result_lines.append(line)
    if not matched:
        insert_at = _key_table_tail(lines, key_name)
        if insert_at is not None:
            result_lines.insert(insert_at, new_row)
        else:
            result_lines.append(new_row)  # no keyed table — EOF fallback
    return "\n".join(result_lines)


def has_markdown_row(existing: str, new_row: str, key_name: str) -> bool:
    """True if a table row with the new row's key already exists (SDD #21 R1).

    Uses the same whole-cell key-column semantics as
    :func:`upsert_markdown_row`. Rows that are not tables, lack the key
    column, or have an empty key count as "not present" (insert proceeds —
    symmetric with the data-preserving fallback in upsert).
    """
    new_cells = split_table_cells(new_row)
    if new_cells is None:
        return False
    key_cols = _key_columns(existing, key_name)
    if any(c >= len(new_cells) for c in key_cols):
        return False
    new_key = "×".join(new_cells[c] for c in key_cols)
    if not new_key.strip("× "):
        return False
    for line in existing.split("\n"):
        cells = split_table_cells(line)
        if cells is None or _is_separator_row(cells):
            continue
        if all(c < len(cells) for c in key_cols) and _norm_key(
            "×".join(cells[c] for c in key_cols)
        ) == _norm_key(new_key):
            return True
    return False


def _read_yaml_records(path: Path) -> list[dict[str, Any]]:
    """Read the YAML-fronted records list (e.g. frontmatter ``hooks:`` array).

    Fails LOUD on unreadable or malformed files (T706): the previous ``[]``
    fallback made the subsequent upsert treat the existing records as gone
    and collapse the whole file on rewrite. A missing file or a frontmatter
    block that simply carries no records key legitimately yields ``[]``.
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        # Frontmatter gate: the FIRST LINE must be exactly ``---``. A bare
        # ``startswith("---")`` prefix test also matched ``----`` thematic
        # breaks, misparsing frontmatter-less bodies as frontmatter and
        # raising TruthFileParseError on them (final review T4 M2).
        first_line = text.split("\n", 1)[0].rstrip("\r \t")
        if first_line != "---":
            return []
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise TruthFileParseError(
                "truth file frontmatter is unterminated (no closing ---)",
                path=str(path),
            )
        fm = yaml.safe_load(parts[1]) or {}
        if not isinstance(fm, dict):
            raise TruthFileParseError(
                "truth file frontmatter is not a YAML mapping",
                path=str(path),
                frontmatter_type=type(fm).__name__,
            )
        for key in ("hooks", "records", "items"):
            records = fm.get(key)
            if isinstance(records, list):
                return records
        return []
    except (yaml.YAMLError, OSError, ValueError) as exc:
        raise TruthFileParseError(
            "truth file could not be parsed during upsert read",
            path=str(path),
        ) from exc


def _upsert_by_key(
    existing: list[dict[str, Any]], new_records: list[dict[str, Any]], key_field: str
) -> list[dict[str, Any]]:
    """Merge records by key_field: new records replace existing ones with same key.

    Records WITHOUT the key field are preserved on BOTH sides (T703 fix: the
    new-record loop used to silently drop them, so an LLM record missing its
    id simply vanished while existing keyless records were kept — asymmetric).
    Keyless new records are kept and logged so the caller can notice; nothing
    is discarded.
    """

    def _add(rec: dict[str, Any]) -> None:
        if key_field in rec:
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
        else:
            marker = f"__nokey_{id(rec)}__"
            if marker not in by_key:
                order.append(marker)
            by_key[marker] = rec

    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rec in existing:
        _add(rec)
    for rec in new_records:
        if key_field not in rec:
            log.warning("truth_yaml_upsert_record_missing_key", key_field=key_field)
        _add(rec)
    return [by_key[k] for k in order if k in by_key]


def _serialize_yaml_records(records: list[dict[str, Any]], filename: str) -> str:
    """Serialize records back into the YAML-frontmatter + markdown-body format."""
    yaml_key = "hooks" if "hook" in filename else "records"
    fm = {yaml_key: records}
    front = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n\n"


#: Public alias for the separator-row predicate (used by the checkpoint-side
#: keyed merge; single source, no duplicate regex).
is_separator_row = _is_separator_row
