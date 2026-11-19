#!/usr/bin/env python3
"""Spec #116 T1: offline G4 discriminative-power replay (zero LLM, read-only).

克隆 tools/replay_severity_vocab.py 形态（#105 先例）。对项目章集逐章调用
g4_chapter_drafting，聚合 per-check PASS/WARN/FAIL/SKIP 计数、firing rate、
触发归因；双口径（state-free / truth 依赖，附录 A 口径列锚）＋ simile
narrative-only 对照列（r2/M7）。不写被测项目目录；报告经 --out 落盘或 stdout。
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from shenbi.gates.g4.chapter_drafting import (
    ending_archetype_of,
    g4_chapter_drafting,
)
from shenbi.gates.shared import (
    META_BLOCK_RE,
    count_similes,
    count_transition_words,
    strip_narrative_body,
    strip_scene_markers,
)

# 附录 A 口径列（spec r2）＋ M3 对齐（hook_type_rotation 读 plans 历史 → truth 依赖）。
# I1 口径双形统一（spec #116 Task 4 审查移交）：canonical id 统一取 check 行发射形
# （truth 族 check 行均为裸形 cd.*——mf 臂的 G4. 前缀是 f"G4.{issue}" 包装产物，
# 经 ARM_TO_CANONICAL 回射）。cd.balance_value_drift.bundle 已裁除：门族唯一发射点
# 在 state_settling.py:305（settle 面束级升格，聚合章级 cd.balance_value_drift WARN），
# g4_chapter_drafting 单文件回放面零发射——非本章门分母行，作 dead 键删除并在此记裁定
# （shadow.py 路由键不受影响）；其 mf 串经 ARM_TO_CANONICAL 回射父行 cd.balance_value_drift。
TRUTH_DEPENDENT_IDS = frozenset(
    {
        "cd.prop_handoff",
        "cd.balance_value_drift",
        "cd.counter",
        "cd.counter.plan_conflict",
        "cd.counter.base_mismatch",
        "cd.counter.prose_mismatch",
        "G4.cd.hook_type_rotation",
    }
)
STATE_FREE_IDS = frozenset(
    {
        "G4.pre_check",
        "G4.post_check",
        "G4.transition",
        "G4.fatigue",
        "G4.meta",
        "G4.word_count",
        "G4.cd.scene_count",
        "G4.cd.scene_concreteness",
        # NB5：回 state-free——对齐附录 A（读 plans 声明，非 truth oracle）
        "G4.cd.scene_hook_match",
        "G4.cd.chapter_end_hook",
        "G4.cd.protagonist_presence",
        "G4.cd.surge",
        "G4.cd.simile_band",
        "G4.cd.voice_density",
        "G4.cd.golden_slot",
        "G4.cd.content_uniqueness",
        "G4.cd.quote_verbatim",
        "G4.cd.payoff_density",
        "cd.post_quote_verbatim",
        "cd.post_transition_cross",
        "cd.post_wordcount_precision",
        "G4.cd.ending_diversity",
        # 附录外行归位（I1：真实 in-scope 检查，两集合原均缺）——读 memo 声明
        # （plans 面）非 truth oracle → state-free；micro_hook_run 需 memo_v3，
        # v3 前置物缺席的语料回放面记 SKIP
        "G4.cd.quote_type",
        "G4.cd.micro_hook_run",
    }
)

# M2＋I1 口径双形统一：mf 发射臂 → canonical 门行回射（Task 4 registry fail_arms 同源）。
# 前四条＝mf-only 失败臂（无独立 check 行）；truth/post 族＝f"G4.{issue}" 变量包装臂
# 回射 check 行裸形（G4.cd.balance_value_drift→cd.balance_value_drift、
# G4.cd.counter.*→cd.counter.* 等），使 mf 形与 check 行形在口径判定/过滤下同归一行。
ARM_TO_CANONICAL: dict[str, str] = {
    "G4.cd.no_hook": "G4.cd.chapter_end_hook",
    "G4.cd.protagonist_absent": "G4.cd.protagonist_presence",
    "G4.cd.no_visual_scene": "G4.cd.scene_concreteness",
    "G4.cd.content_overlap": "G4.cd.content_uniqueness",
    "G4.cd.prop_handoff": "cd.prop_handoff",
    "G4.cd.balance_value_drift": "cd.balance_value_drift",
    # settle 面束级升格臂（state_settling.py）——回射父行，不占回放分母
    "G4.cd.balance_value_drift.bundle": "cd.balance_value_drift",
    "G4.cd.counter": "cd.counter",
    "G4.cd.counter.plan_conflict": "cd.counter.plan_conflict",
    "G4.cd.counter.base_mismatch": "cd.counter.base_mismatch",
    "G4.cd.counter.prose_mismatch": "cd.counter.prose_mismatch",
    "G4.cd.post_quote_verbatim": "cd.post_quote_verbatim",
    "G4.cd.post_transition_cross": "cd.post_transition_cross",
}

# 归因再推导（锚：chapter_drafting.py:728-731 预处理序＋:1178-1235 三臂——
# narrative_window 与门同序是 C3 修订核心；漂移由一致性测试双向校验兜底）
HOOK_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)
SINGLE_CHAR_TENSION = frozenset("但却还仍瞒藏账欠谜")
_Q_RE = re.compile(r"[？?]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# 账目钩臂阈（锚 chapter_drafting.py:1222——窗口内 ≥2 个独立数字串才算账目行）
_LEDGER_MIN_RUNS = 2


def narrative_window(content: str) -> list[str]:
    """与门同序的叙事段面（剥 HOOK 块→META 块→场景标记→split）."""
    text = re.sub(r"<!--HOOK-BEGIN-->.*?<!--HOOK-END-->", "", content, flags=re.DOTALL)
    text = META_BLOCK_RE.sub("", text)
    text = strip_scene_markers(text)
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def hook_window_attribution(content: str) -> dict[str, Any]:
    """Re-derive the end-hook window arms (diagnostic only, gate verdict 不变)."""
    paras = narrative_window(content)
    # NB3：与门同滤（chapter_drafting.py:1179——[-8:] 后再滤标题/引用/清单行）
    window = [p for p in paras[-8:] if not p.startswith(("#", "##", ">", "---", "- [ ]"))]
    text = "".join(window)
    hits = set(HOOK_TENSION_RE.findall(text))
    has_q = bool(_Q_RE.search(text))
    has_ledger = len(re.findall(r"\d+", text)) >= _LEDGER_MIN_RUNS
    return {
        "window_cjk": len(_CJK_RE.findall(text)),
        "has_q": has_q,
        "multi": sorted(hits - SINGLE_CHAR_TENSION),
        "singles": sorted(hits & SINGLE_CHAR_TENSION),
        "has_ledger": has_ledger,
        "single_char_only": (not has_q)
        and (not has_ledger)
        and bool(hits & SINGLE_CHAR_TENSION)
        and not (hits - SINGLE_CHAR_TENSION),
    }


def _pure_chapter(stem: str) -> bool:
    return re.fullmatch(r"chapter-\d+", stem) is not None


def collect(project_dir: Path, pattern: str = "chapter-*.md") -> list[dict]:
    """Run g4_chapter_drafting per pure chapter (chapter-NN.md) and keep raw rows."""
    # I1 顺手修：project_dir 一并 resolve——门内 truth/particle_ledger.md 等
    # 相对拼接面与章路径同坑（相对 project_dir 会漏读 truth 前置物）
    project_root = project_dir.resolve()
    chapters = sorted(p for p in (project_root / "chapters").glob(pattern) if _pure_chapter(p.stem))
    rows: list[dict] = []
    for p in chapters:
        # 绝对路径直入 resolve_input_path（相对 fp 会被 rd 再拼一次 → file_not_found）
        pf = p.resolve()
        res = json.loads(
            g4_chapter_drafting([str(pf)], str(project_root), str(project_root), repo_root=None)
        )
        # C1：passed() 无 must_fix 键
        rows.append({"file": p.name, "checks": res["checks"], "must_fix": res.get("must_fix", [])})
    return rows


def summarise(rows: list[dict]) -> dict[str, dict]:
    """Aggregate per-check status counts + firing rate over collect() rows.

    must_fix 行 id（首 ``:`` 前缀）先经 ARM_TO_CANONICAL 回射再计入 canonical
    行 FAIL（M2）；同章同 id 与 check 行 FAIL 去重。``_firing[id]`` =
    (该 id FAIL/WARN 章数)/(总章数)。
    """
    counts: dict[str, dict[str, int]] = {}
    fired: dict[str, set[str]] = {}

    def _bump(cid: str, status: str) -> None:
        bucket = counts.setdefault(cid, {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0})
        bucket[status] += 1

    for row in rows:
        fpath = str(row.get("file", ""))
        check_fail_ids: set[str] = set()
        for chk in row.get("checks", []) or []:
            cid = str(chk.get("id", ""))
            status = str(chk.get("s", ""))
            if status not in ("PASS", "WARN", "FAIL", "SKIP"):
                continue
            _bump(cid, status)
            if status in ("FAIL", "WARN"):
                fired.setdefault(cid, set()).add(fpath)
                if status == "FAIL":
                    check_fail_ids.add(cid)
        mf_seen: set[str] = set()
        for mf in row.get("must_fix", []) or []:
            arm = str(mf).split(":", 1)[0]
            canonical = ARM_TO_CANONICAL.get(arm, arm)
            if canonical in check_fail_ids or canonical in mf_seen:
                continue
            mf_seen.add(canonical)
            _bump(canonical, "FAIL")
            fired.setdefault(canonical, set()).add(fpath)

    total = len(rows)
    firing = {cid: len(chs) / total for cid, chs in fired.items()} if total else {}
    return {**counts, "_firing": firing}


def _caliber(cid: str) -> str:
    if cid in STATE_FREE_IDS:
        return "state-free"
    if cid in TRUTH_DEPENDENT_IDS:
        return "truth"
    return "—"


def _protagonist_names(project_dir: Path) -> list[str]:
    """Re-derive the gate's protagonist roster (frontmatter name + 他)."""
    protag = project_dir / "characters" / "protagonist.md"
    if not protag.is_file():
        return []
    names: list[str] = []
    m = re.search(r"^name:\s*(.+)$", protag.read_text(encoding="utf-8"), re.MULTILINE)
    if m:
        names.append(m.group(1).strip())
    if "他" not in names:
        names.append("他")
    return names


def render_report(
    project_dir: Path, pattern: str = "chapter-*.md", state_free_only: bool = False
) -> str:
    """Deterministic markdown report (no timestamp — same input, same output)."""
    rows = collect(project_dir, pattern)
    summary = summarise(rows)
    chapters = sorted(p for p in (project_dir / "chapters").glob(pattern) if _pure_chapter(p.stem))
    contents = [p.read_text(encoding="utf-8") for p in chapters]

    lines = [
        "# spec #116 gate-power replay report",
        "",
        f"- 项目: {project_dir}",
        f"- 章数（分母，纯章形 chapter-NN.md）: {len(rows)}",
        f"- 口径过滤: {'state-free only' if state_free_only else '全量（双口径列）'}",
        "",
        "## Per-check 判别力",
        "",
        "| canonical id | 口径 | PASS | WARN | FAIL | SKIP | firing |",
        "|---|---|---|---|---|---|---|",
    ]
    for cid, bucket in summary.items():
        if cid == "_firing":
            continue
        if state_free_only and cid in TRUTH_DEPENDENT_IDS:
            continue
        rate = summary["_firing"].get(cid, 0.0)
        lines.append(
            f"| {cid} | {_caliber(cid)} | {bucket['PASS']} | {bucket['WARN']}"
            f" | {bucket['FAIL']} | {bucket['SKIP']} | {rate:.2f} |"
        )

    # 触发归因（诊断再推导——门判定本身不变）
    lines += ["", "## 触发归因（诊断再推导，不改门判定）", ""]
    single_only_n = 0
    hai_n = 0
    zhang_n = 0
    for c in contents:
        attr = hook_window_attribution(c)
        if attr["single_char_only"]:
            single_only_n += 1
        if "还" in attr["singles"]:
            hai_n += 1
        if "账" in attr["singles"]:
            zhang_n += 1
    lines += [
        "### hook（narrative_window 尾 8 段三臂）",
        "",
        f"- single_char_only 章数: {single_only_n}（仅单字张力词命中——最弱臂）",
        f"- 「还」命中章数: {hai_n}",
        f"- 「账」命中章数: {zhang_n}",
        "",
    ]
    names = _protagonist_names(project_dir)
    if names and contents:
        totals = [sum(c.count(n) for n in names) for c in contents]
        lines += [
            "### protagonist（name frontmatter＋他 再推导）",
            "",
            f"- 名单: {'、'.join(names)}",
            f"- 出现总数中位: {statistics.median(totals)} / 最小: {min(totals)}",
            "",
        ]
    else:
        lines += [
            "### protagonist",
            "",
            "- SKIP：无 characters/protagonist.md（与门 SKIP 口径一致）",
            "",
        ]
    if contents:
        trans = [count_transition_words(strip_narrative_body(c)) for c in contents]
        ending_none = sum(1 for c in contents if ending_archetype_of(c) is None)
        sim_raw = [count_similes(c)["per_1000"] for c in contents]
        sim_narr = [count_similes(strip_narrative_body(c))["per_1000"] for c in contents]
        lines += [
            "### transition（narrative 口径）",
            "",
            f"- 每章计数中位: {statistics.median(trans)}",
            "",
            "### ending（ending_archetype_of）",
            "",
            f"- None（未归类收束）章数: {ending_none}",
            "",
            "### simile 双口径（r2/M7 对照列）",
            "",
            f"- raw 口径 per_1000 均值: {sum(sim_raw) / len(sim_raw):.2f}",
            f"- narrative-only 口径 per_1000 均值: {sum(sim_narr) / len(sim_narr):.2f}",
            "",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Replay g4_chapter_drafting over a project and render the power report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="report path (default stdout)")
    parser.add_argument(
        "--pattern",
        default="chapter-*.md",
        help="chapter-filename glob (default chapter-*.md)",
    )
    parser.add_argument(
        "--state-free-only",
        action="store_true",
        help="drop truth-dependent check rows from the report",
    )
    args = parser.parse_args()

    report = render_report(args.project_dir, args.pattern, state_free_only=args.state_free_only)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"report -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
