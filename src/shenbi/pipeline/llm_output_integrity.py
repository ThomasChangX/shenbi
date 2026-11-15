"""Unified LLM-output integrity checks for the dispatch write path.

Spec: 2026-07-19 output-structural-integrity-beyond-json-design (merged Spec 19
+ former Spec 20).

This module is the single source of truth for the pattern catalog and the five
check functions invoked from ``dispatch_helper.write_parsed_outputs``. The
former Specs 19/20 maintained overlapping pattern lists; they are de-duplicated
here, split by detection mode:

  * ``WRITE_FAILURE_PATTERNS`` — the LLM reports it cannot write. These trip
    only under the dominance rule (start-of-content OR matched region >50% of
    output) so a chapter that merely *mentions* a sandbox in dialogue does not.
  * ``LEAKAGE_PATTERNS`` — model meta-commentary in prose (NOT a write failure).
  * ``VERDICT_MARKERS`` / ``PREAMBLE_MARKERS`` — audit-completeness signals.

All check functions return ``list[str]`` issue strings tagged
``G4.<group>.<rule>`` so the G4 composite-checker registry can route severity.
"""

from __future__ import annotations

import re
from pathlib import Path

# --- Write-failure signatures: the LLM reports it cannot write. ---
# These supersede the broader standalone patterns from the former specs
# (e.g. bare `由于沙箱限制`, `can't be updated.*sandbox`) which are now covered
# by the more specific entries below.
WRITE_FAILURE_PATTERNS: list[str] = [
    r"由于沙箱限制.*?(?:无法|不能).*?(?:写|写入)",
    r"(?:can't|cannot|unable to).*?(?:write|update|create).*?(?:file|sandbox|read-only)",
    r"read-only sandbox",
    r"Use the existing.*?from input",
    r"was already provided via.*?markers",
    r"I (?:cannot|can't|could not) (?:write|create|update) (?:the )?(?:file|output)",
]

# --- Model meta-commentary leakage in prose (NOT a write failure). ---
LEAKAGE_PATTERNS: list[str] = [
    r"Now the .* JSON",
    r"Let me write",
    r"schema:",
    r"Here's a summary of the revision",
    r"修订执行摘要",
    r"Revision complete",
    r"All \d+ files have been",
]

# --- Audit completeness markers ---
VERDICT_MARKERS: list[str] = ["判定", "结论", "verdict", "通过", "阻断", "PASS", "BLOCK"]
PREAMBLE_MARKERS: list[str] = ["现在执行", "inputs confirmed", "now executing", "开始审计"]

#: Minimum audit size in bytes — real audits comfortably exceed this floor.
_AUDIT_MIN_BYTES = 200

#: Retry-prompt suffix confirming write capability.
RETRY_WRITE_CONFIRMATION = (
    "CRITICAL: You have filesystem write access in this environment. "
    "Output the complete file content directly — do not explain, apologize, "
    "or reference sandbox limitations. Previous attempt failed with: '{signature}'."
)

# Pre-compile for performance.
_WRITE_FAILURE_RES = [re.compile(p, re.IGNORECASE) for p in WRITE_FAILURE_PATTERNS]
_LEAKAGE_RES = [re.compile(p, re.IGNORECASE) for p in LEAKAGE_PATTERNS]
_LINE_REF_RE = re.compile(r"L(\d+)(?:-(\d+))?")


def detect_write_failure(content: str) -> tuple[bool, str | None]:
    """Check if content is a write-failure diagnostic instead of file content.

    False-positive mitigation (spec §3.2): a pattern only counts as a failure
    when it appears at the START of the content OR the matched span sits within
    a region that comprises >50% of the total output. A chapter that merely
    *mentions* a sandbox in passing is NOT a failure.

    Returns ``(is_failure, matched_pattern_or_None)``.
    """
    total_len = max(len(content), 1)
    for rx in _WRITE_FAILURE_RES:
        match = rx.search(content)
        if not match:
            continue
        start, end = match.span()
        # Case 1: pattern at the very start (ignoring leading whitespace).
        at_start = content[:start].strip() == ""
        # Case 2: the region from first non-empty char to end of match covers
        # more than half the output — i.e. the diagnostic dominates rather
        # than being embedded in real content.
        dominant = end > total_len * 0.5
        if at_start or dominant:
            return True, match.group(0)
    return False, None


def check_prose_leakage(path: Path) -> list[str]:
    """Detect model meta-commentary leakage in prose files.

    Returns ``G4.pi.model_leakage`` issues (one per distinct pattern) and a
    single ``G4.pi.unfinished_ending`` issue if the file ends with a trailing
    punctuation character indicating mid-thought truncation.
    """
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    for rx in _LEAKAGE_RES:
        matches = rx.findall(text)
        if matches:
            issues.append(
                f"G4.pi.model_leakage:{path.name} — found '{matches[0]}' pattern "
                f"({len(matches)} occurrences). Chapter file contains model "
                f"meta-commentary, not prose."
            )

    last_500 = text[-500:].strip()
    if last_500 and last_500[-1] in ":,；：，":
        issues.append(
            f"G4.pi.unfinished_ending:{path.name} — file ends with "
            f"'{last_500[-20:]}' — truncated mid-thought"
        )

    return issues


def check_markdown_fence_balance(path: Path) -> list[str]:
    """Verify Markdown code fences are balanced in prose files."""
    text = path.read_text(encoding="utf-8")
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        return [
            f"G4.pi.fence_imbalance:{path.name} — odd number of ``` markers "
            f"({fence_count}). Orphan code fence — file was likely extracted "
            f"incorrectly."
        ]
    return []


def check_audit_completeness(path: Path) -> list[str]:
    """Verify audit files contain an actual verdict, not just a preamble."""
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    # #18-8a (probe24): the foreshadowing-LIFECYCLE step writes its tracking
    # report to ``audits/chapter-N-foreshadowing.md`` — a lifecycle report,
    # not an audit verdict document. Demanding 判定 from it journaled a
    # permanent G4.ac.no_verdict that re-failed every later dispatch of the
    # chapter through the sticky findings journal.
    if text.lstrip().startswith("# Foreshadowing Lifecycle Report"):
        return []

    if len(text) < _AUDIT_MIN_BYTES:
        issues.append(
            f"G4.ac.too_short:{path.name} — audit file is {len(text)} bytes, likely aborted stub"
        )

    has_verdict = any(marker in text for marker in VERDICT_MARKERS)
    if not has_verdict:
        issues.append(
            f"G4.ac.no_verdict:{path.name} — audit file contains no verdict/conclusion marker"
        )

    has_only_preamble = any(marker in text for marker in PREAMBLE_MARKERS) and not has_verdict
    if has_only_preamble:
        issues.append(
            f"G4.ac.aborted_stub:{path.name} — audit file contains only "
            f"execution preamble, no results"
        )

    return issues


def check_audit_line_refs(path: Path, chapter_path: Path) -> list[str]:
    """Verify audit line references point to valid lines in the chapter."""
    if not chapter_path.exists():
        return []  # Chapter missing is handled elsewhere.

    audit_text = path.read_text(encoding="utf-8")
    chapter_lines = chapter_path.read_text(encoding="utf-8").split("\n")
    max_line = len(chapter_lines)

    issues: list[str] = []
    for start_str, end_str in _LINE_REF_RE.findall(audit_text):
        start = int(start_str)
        end = int(end_str) if end_str else start
        if end > max_line:
            issues.append(
                f"G4.av.stale_line_ref:{path.name} — references L{start}-{end} "
                f"but chapter has only {max_line} lines. Audit ran against a "
                f"different version of the chapter."
            )
    return issues


#: batch #15 #33: raw absolute-year forms (Chinese numerals or digits) that
#: only the worldbuilding anchor registry (world/story_bible.md 世界史时间线)
#: may carry — every other genesis producer references anchors BY NAME or
#: with relative phrasing. probe15: four layers of mutually exclusive year
#: numbers burned four genesis adjudication rounds.
_YEAR_NUMERAL = r"[一两二三四五六七八九十百千万零零○0-9]+"
RAW_YEAR_RE = re.compile(_YEAR_NUMERAL + r"\s*年(?:前|后|来)")

#: Zones that legitimately carry absolute years and are exempt from the scan:
#: the anchor registry's own home file, the reviewer report (quotes),
#: benchmark anchors, style zone, and snapshots.
_YEAR_SCAN_EXEMPT_PARTS: tuple[str, ...] = (
    "story_bible",
    "foundation/",
    "benchmarks/",
    "style/",
    "snapshots/",
)


def check_year_anchors(path: Path) -> list[str]:
    """Flag raw absolute-year forms in a producer output (#33).

    Returns ``G4.ys.raw_year:<file> — L<n>:「<match>」…`` findings with line
    citations; exempt zones return empty. The sanctioned forms are anchor
    NAMES from world/story_bible.md's 世界史时间线 or relative phrasing
    (「净场之后」); the retry feedback teaches exactly that.
    """
    rel = str(path)
    if any(part in rel for part in _YEAR_SCAN_EXEMPT_PARTS):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    findings: list[str] = []
    for ln, line in enumerate(text.split("\n"), 1):
        for m in RAW_YEAR_RE.finditer(line):
            findings.append(
                f"G4.ys.raw_year:{path.name} — L{ln}:「{m.group(0)}」"
                "——绝对年数只登记于 world/story_bible.md 世界史时间线；"
                "引用锚名或相对表述"
            )
    return findings


# --- Spec #105 T2: out-of-vocab severity gate (G4.av.vocab). ---
#
# 校验正则与传感正则语义显式分离：传感正则（contracts.severity，词表内
# 锚定计数）只捕词表内词——复用它们做校验则 fail-loud 永不触发。本检查用
# 形态槽位通配捕获 + 统一后处理管线（见 _vocab_violation）。
#
# r2.6 挂账注记两条：
# 1. 捕获污染剥离规则(管线第 1 步)——`ERROR(对应 BLOCKING)` 括注后缀与
#    `严重度：高。` 尾部标点不剥则 CJK 精确等值不命中=静默漏报（本件根因
#    形态）；残余面（括注内嵌真词表外词）#117 发现级 parser 收编。
# 2. key-名豁免形态域——现实现形态无关(任意锚定形捕获 SEVERITY/严重度
#    token 均放行），动机仅 bold 裸 key 形；残余面同归 #117。
#
# key 形引号防御用 gap 类排除引号([^\w"'] 不吃引号——"severity": "low"
# 全线无匹配）而非尾部负向前瞻：tail 前瞻放在可回溯通配捕获组后必然被
# 回溯绕过(捕 low 后前瞻见引号失败→回溯交还一字符捕 lo→误伤; 与 spec
# C1' 证伪 _SEV_ENUM_TAIL 照搬路径同机制——plan r4-I1 实测钉死）。
from shenbi.contracts.severity import (
    AGGREGATE_VOCAB_SET,
    CJK_SEVERITY_WORDS,
    KEY_NAME_TOKENS,
)

_VOCAB_BRACKET_RE = re.compile(r"^\s*-\s*\[([\w·\-]+)\]", re.M)
_VOCAB_BOLD_RE = re.compile(r"\*\*([\w\-]+)\*\*")
_VOCAB_KEY_RE = re.compile(
    r"\*{0,2}(?:severity|严重度)\*{0,2}[^\w\"']{0,6}([^\s\"']+)", re.IGNORECASE
)
#: 捕获污染剥离：括注后缀（`ERROR（对应 BLOCKING）`→`ERROR`）+ 尾部标点。
_POLLUTION_PAREN_RE = re.compile(r"[（(][^）)]*[）)]?\s*$")
_TRAILING_PUNCT = "。．.,，;；:：!！?？"
#: legend 拆分分隔符（模板形 `severity:BLOCKING/CRITICAL/MINOR` 全段∈词表=文档行非声明）。
_LEGEND_SPLIT_RE = re.compile(r"[/／、,，]")


def _vocab_violation(token: str) -> bool:
    """Unified post-processing pipeline; True = out-of-vocab violation.

    1. 捕获污染剥离(括注后缀+尾部标点) 2. upper 归一前置(`- [major]` 小写
    词表外写法必须进判别器——后置则静默漏放) 3. key-名豁免 4. 判别器
    (ASCII: isascii+isupper+len>=2, 禁止裸 isupper——`MINOR·观察`.isupper()
    返 True, CJK 不参与大小写; CJK: 精确等值七词族, 禁止子串/前缀——
    `**严重度**` 裸 key 75 份误伤面) 5. legend 拆分豁免(全段∈词表)
    6. 查表。
    """
    token = _POLLUTION_PAREN_RE.sub("", token).rstrip(_TRAILING_PUNCT)
    token = token.upper()
    if token in KEY_NAME_TOKENS:
        return False
    ascii_hit = token.isascii() and token.isupper() and len(token) >= 2
    cjk_hit = token in CJK_SEVERITY_WORDS
    if not (ascii_hit or cjk_hit):
        return False
    parts = _LEGEND_SPLIT_RE.split(token)
    if all(p in AGGREGATE_VOCAB_SET for p in parts):
        return False
    return token not in AGGREGATE_VOCAB_SET


def check_audit_severity_vocab(path: Path) -> list[str]:
    """Flag anchored-form severity tokens outside the aggregate vocabulary.

    散文提及(非锚定形)不报; cell 形 v1 不建(| PASS | / | 通过 | / 置信度
    | HIGH | 同形歧义面——词表外 cell 待 #116 标定数据后议)。
    """
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    seen: set[tuple[int, str]] = set()
    for form, regex in (
        ("bracket", _VOCAB_BRACKET_RE),
        ("bold", _VOCAB_BOLD_RE),
        ("key", _VOCAB_KEY_RE),
    ):
        for m in regex.finditer(text):
            token = m.group(1)
            if not _vocab_violation(token):
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            key = (line_no, token)
            if key in seen:
                continue
            seen.add(key)
            issues.append(
                f"G4.av.vocab:{path.name} — L{line_no}:词表外严重度「{token}」"
                f"（{form} 形）：用 BLOCKING/CRITICAL/MINOR 重写本条"
            )
    return issues


# --- Spec #105 T3: dispatch-integrity signature gate (G4.av.dispatch_integrity). ---
#
# 次防线定位：主防线=审计派发前置预检（chapter_loop._run_audit_wave_step 头部，
# #51 ghost-chain guard 控制流先例——不依赖措辞）。本兜底 pattern 自认是又一则
# 手拼匹配、措辞改写可绕（spec 对抗回放 ④c）；签名合取（路径 token ∧ 重跑/补齐
# 措辞，反引号形态优先——实弹族 ch10/12/14/16/20/40 全部反引号形态）压掉
# 「内容 finding 引用裸路径+补齐措辞」的误伤面（r2.2 I5）。仅 BLOCKING 锚定行。

_DI_BACKTICK_PATH_RE = re.compile(r"`(?:chapters|plans|truth)/[^`]+`")
_DI_BARE_PATH_RE = re.compile(r"(?:chapters|plans|truth)/\S+\.(?:md|yaml|json)")
_DI_ACTION_RE = re.compile(r"重跑|补齐|补入")


def check_audit_dispatch_integrity(path: Path) -> list[str]:
    """Invalidate reports whose BLOCKING payload is a dispatch-integrity complaint.

    Dispatch-integrity signatures in a BLOCKING payload mean a framework bug
    (spec #105 T3): the report is invalid and the framework must be fixed,
    never expressed by the auditor.
    """
    from shenbi.contracts.severity import BOLD_ANCHOR_RE, BRACKET_ANCHOR_RE

    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for ln, line in enumerate(text.split("\n"), 1):
        blocking_hit = "BLOCKING" in line and (
            BRACKET_ANCHOR_RE.search(line) or BOLD_ANCHOR_RE.search(line)
        )
        if not blocking_hit:
            continue
        has_path = _DI_BACKTICK_PATH_RE.search(line) or _DI_BARE_PATH_RE.search(line)
        if has_path and _DI_ACTION_RE.search(line):
            issues.append(
                f"G4.av.dispatch_integrity:{path.name} — L{ln}:派发完整性签名 BLOCKING"
                "（框架 bug 非正文缺陷）：该报告判无效，须修框架不应由审计员表达"
            )
    return issues
