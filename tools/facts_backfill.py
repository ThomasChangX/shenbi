#!/usr/bin/env python3
"""Backfill facts seeds + memo declaration lines + registry stale-row rewrites.

spec #80 T13 (plan_craft_backfill precedent: dry-run default, ``--apply``
writes, 「历史补录」 marker, idempotent). Seed truth source per spec §1.3
(rev2 I6): the repaired chapter canon (counters) + registry 对账面/owner
columns (identity/props). The three known-stale prose cells (《鉴录》row
「两个名字/第三个名字」、name_registry 赵三行「第三个名字」、登记名「临」
备注「全卷一致」) are REWRITE TARGETS, never seed sources. Registry rewrites
are surgical exact-string replacements — never whole-file regeneration
(rev5 R4-I2: 72 行 settle prose is not re-derivable, protected).

Determinism guards: every derived value is anchored to a parsed canon
pattern; a missing anchor refuses the face (no invented values).

Usage: uv run python tools/facts_backfill.py --project <dir> [--apply]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.facts.enums import FactsDim
from shenbi.facts.schemas import FACTS_SCHEMA, FactsFile
from shenbi.facts.store import save_facts
from shenbi.gates.g4.cross_chapter import cn_amount

# ── canon constants（修复后正典派生的键映射——registry 括注形态 → facts 键）──

CANON_PROPS_KEY_MAP = {
    "火纹骨哨（老驼所授·主线）": "火纹骨哨",
    "火纹骨哨（帖木哥所持·旧线）": "火纹骨哨·帖木哥支",
}
IDENTITY_KEY = "主角"
COUNTER_NAME = "鉴录名数"
MIN_TABLE_COLS = 3
NOTE_COL = 2
CH_COUNTER_PLAN = 9
CH_COPY_DELIVERY = 20
COPY_KEY = "火纹骨哨·帖木哥支"
# pipe 声明行 owner 位的注记词（audit-T13 I-1）——非 owner 值，跳过
ANNOTATION_HEADS = frozenset({"无", "纯提及", "自持", "暂持"})

_CH_TOTAL = re.compile(r"第一页([一二两三四五六七八九十\d]{1,5})个名字")
_CH_ADD_ORDINAL = re.compile(r"添第([一二两三四五六七八九十\d]{1,5})个名字")
_PIPE_LINE = re.compile(r"^[-*]\s*物象[：:]\s*(.+)$", re.MULTILINE)
_FROM_CH = re.compile(r"第\s*(\d+)\s*章")

_REGISTRY_REWRITES: tuple[tuple[str, str], ...] = (
    # prop_registry《鉴录》行（pre-fix 计数 → 修复后正典）
    (
        "第一页两个名字写得规矩，翻到第三页写第三个名字「赵三",
        "第一页三个名字写得规矩，翻到第三页写第四个名字「赵三",
    ),
    # name_registry 赵三行
    ("夜写入《鉴录》第三个名字", "夜写入《鉴录》第四个名字"),
    # name_registry 登记名「临」备注（与 narration_name 相悖的注记重写；
    # 登记名行本身在对账比较面外——spec §1.3 rev5 R4-I2）
    (
        "| 登记名 | 临 | 全卷一致（#74 项 4） |",
        "| 登记名 | 临 | 正字；籍册/公文用"
        "——叙事名自第 3 章起为旌名那罕（truth/facts/identity.json） |",
    ),
)


@dataclass
class Seeds:
    """Derived three-dim seed payloads (None face = refused/skipped)."""

    props: dict[str, dict[str, object]] | None = None
    props_ops: list[dict[str, object]] = field(default_factory=list)
    counters: dict[str, dict[str, object]] | None = None
    identity: dict[str, dict[str, object]] | None = None
    notes: list[str] = field(default_factory=list)


def _cn(raw: str) -> int | None:
    """两-normalized cn_amount wrapper (colloquial 2 outside its vocabulary)."""
    return cn_amount("二" + raw[1:] if raw.startswith("两") else raw)


def _table_rows(text: str) -> list[list[str]]:
    """Data rows of every markdown table; each block's first row = header (skipped)."""
    rows: list[list[str]] = []
    in_table = False
    for line in text.splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < MIN_TABLE_COLS or all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if not in_table:
            in_table = True
            continue  # header row — audit-T13 C1: never a fact
        rows.append(cells)
    return rows


def _derive_props(project: Path, seeds: Seeds) -> None:
    reg = project / "truth" / "prop_registry.md"
    if not reg.is_file():
        seeds.notes.append("props: prop_registry.md 缺席——跳过")
        return
    facts: dict[str, dict[str, object]] = {}
    copy_row_events = ""
    for cells in _table_rows(reg.read_text("utf-8")):
        key_raw, owner_raw = cells[0], cells[1]
        key = CANON_PROPS_KEY_MAP.get(key_raw, re.sub(r"（[^）]*）", "", key_raw).strip())
        owner = re.sub(r"（.*", "", owner_raw).strip()
        if not key or not owner or owner == "无":
            continue
        facts[key] = {"entity": key, "owner": owner}
        if key == COPY_KEY:
            copy_row_events = cells[NOTE_COL] if len(cells) > NOTE_COL else ""
    seeds.props = facts
    # ch20 副本交付拍 op 追补（canon 锚=registry 帖木哥支行 第20章+交+那罕）
    if facts.get(COPY_KEY) and "第20章" in copy_row_events and "那罕" in copy_row_events:
        seeds.props_ops.append(
            {
                "op": "acquire",
                "prop": COPY_KEY,
                "to": "那罕",
                "evidence": "chapters/chapter-20.md L218",
                "chapter": 20,
            }
        )
    else:
        seeds.notes.append("props: 帖木哥支 ch20 交付锚缺席——ops_log 不追补")


def _derive_counters(project: Path, seeds: Seeds) -> None:
    ch9 = project / "chapters" / "chapter-9.md"
    if not ch9.is_file():
        seeds.notes.append("counters: chapters/chapter-9.md 缺席——跳过")
        return
    text = ch9.read_text("utf-8")
    total_m = _CH_TOTAL.search(text)
    add_m = _CH_ADD_ORDINAL.search(text)
    if not total_m or not add_m:
        seeds.notes.append("counters: ch9 计数锚（第一页N个名字/添第N个名字）缺席——拒派生")
        return
    pre, final = _cn(total_m.group(1)), _cn(add_m.group(1))
    if pre is None or final is None or pre + 1 != final:
        seeds.notes.append(f"counters: 锚不自洽（total={pre}, add={final}）——拒派生")
        return
    seeds.counters = {COUNTER_NAME: {"name": COUNTER_NAME, "value": final}}


def _derive_identity(project: Path, seeds: Seeds) -> None:
    reg = project / "truth" / "name_registry.md"
    if not reg.is_file():
        seeds.notes.append("identity: name_registry.md 缺席——跳过")
        return
    aliases: list[str] = []
    narration = ""
    from_ch: int | None = None
    for cells in _table_rows(reg.read_text("utf-8")):
        cat, name = cells[0], cells[1]
        note = cells[NOTE_COL] if len(cells) > NOTE_COL else ""
        if cat == "别名":
            aliases.append(name)
        elif cat == "旌名":
            narration = name
            m = _FROM_CH.search(note)
            from_ch = int(m.group(1)) if m else None
    if not narration or not aliases or from_ch is None:
        seeds.notes.append("identity: 别名/旌名/生效章锚不全——拒派生")
        return
    seeds.identity = {
        IDENTITY_KEY: {"narration_name": narration, "from_ch": from_ch, "aliases": aliases}
    }


def derive_seeds(project: Path) -> Seeds:
    """Run all three derivation faces (spec §1.3 canon anchors)."""
    seeds = Seeds()
    _derive_props(project, seeds)
    _derive_counters(project, seeds)
    _derive_identity(project, seeds)
    return seeds


def _canonical_present(memo: str, line: str) -> bool:
    key = line.split("@", 1)[0].lstrip("- ").strip()
    op = line.split("@", 1)[1].split(":", 1)[0]
    return re.search(rf"[-*]\s*{re.escape(key)}@{op}[：:]", memo) is not None


def normalize_pipe_lines(memo: str) -> list[str]:
    """既有 `- 物象: X|owner` 声明行键形态归一（11/24 备忘先例）."""
    out: list[str] = []
    for m in _PIPE_LINE.finditer(memo):
        for piece in re.split(r"[；;]", m.group(1)):
            pm = re.match(r"\s*([^|｜]+?)\s*[|｜]\s*(.+?)\s*$", piece)
            if not pm:
                continue
            key, owner_expr = pm.group(1), pm.group(2)
            head = re.sub(r"[（(].*", "", owner_expr).strip()
            if head in ANNOTATION_HEADS:
                # 注记形态（无/纯提及/自持…）非 owner 值——产出 hold 行会反咬
                # cp.prop_decl 硬败（audit-T13 I-1：声明持有者「纯提及」≠ facts
                # 现态 owner）。无可声明即跳过。
                continue
            tm = re.match(r"([^（(→]+?)\s*→\s*(.+?)(?:[（(].*)?$", owner_expr)
            if tm:
                out.append(f"- {key}@transfer: {tm.group(1)}→{re.sub(r'[（(].*', '', tm.group(2))}")
            else:
                out.append(f"- {key}@hold: {head}")
    return out


def plan_memo_backfill(
    memo: str,
    counter_line: str | None = None,
    prop_lines: list[str] | None = None,
) -> str:
    """追加「历史补录」声明块；已有规范行的目标零追加（幂等）."""
    targets: list[str] = []
    if counter_line and counter_line not in memo:
        targets.append(counter_line)
    for line in prop_lines or []:
        if not _canonical_present(memo, line):
            targets.append(line)
    if not targets:
        return memo
    block = "\n<!-- 历史补录（spec #80 T13）：facts 声明行回填 -->\n" + "\n".join(targets) + "\n"
    return memo.rstrip("\n") + "\n" + block


def registry_rewrites(text: str) -> str:
    """Apply the three surgical stale-row replacements (idempotent)."""
    for old, new in _REGISTRY_REWRITES:
        text = text.replace(old, new)
    return text


def _apply_seeds(project: Path, seeds: Seeds) -> int:
    """Write-if-absent the three facts files (FactsFile schema validated)."""
    actions = 0
    payloads = {
        FactsDim.PROPS: (seeds.props, seeds.props_ops),
        FactsDim.COUNTERS: (seeds.counters, []),
        FactsDim.IDENTITY: (seeds.identity, []),
    }
    for dim, (facts, ops) in payloads.items():
        target = project / "truth" / "facts" / f"{dim.value}.json"
        if facts is None:
            continue
        if target.is_file():
            print(f"write(truth/facts/{dim.value}.json): SKIP 已存在（幂等）")
            continue
        save_facts(
            project,
            FactsFile.model_validate(
                {"$schema": FACTS_SCHEMA, "dim": dim, "facts": facts, "ops_log": ops}
            ),
        )
        actions += 1
        print(f"write(truth/facts/{dim.value}.json): {len(facts)} facts")
    return actions


def _apply_memos(project: Path, seeds: Seeds, apply: bool) -> int:
    """Append 历史补录 declaration blocks (counter ch9-only; pipe 归一; ch20 copy)."""
    actions = 0
    plans_dir = project / "plans"
    if not plans_dir.is_dir():
        return actions
    counter_line = None
    if seeds.counters and COUNTER_NAME in seeds.counters:
        pre = int(seeds.counters[COUNTER_NAME]["value"]) - 1  # type: ignore[index,operator]
        counter_line = f"- 计数: {COUNTER_NAME} {pre}+1"
    for plan in sorted(plans_dir.glob("chapter-*-plan.md")):
        mnum = re.match(r"chapter-(\d+)-plan\.md", plan.name)
        if not mnum:
            continue
        n = int(mnum.group(1))
        text = plan.read_text("utf-8")
        prop_lines = normalize_pipe_lines(text)
        if n == CH_COPY_DELIVERY and seeds.props and COPY_KEY in seeds.props:
            prop_lines.append(f"- {COPY_KEY}@acquire: 那罕")
        line = counter_line if n == CH_COUNTER_PLAN else None
        new_text = plan_memo_backfill(text, counter_line=line, prop_lines=prop_lines)
        if new_text != text:
            print(f"memo({plan.name}): +声明行")
            if apply:
                plan.write_text(new_text, "utf-8")
            actions += 1
    return actions


def _apply_registries(project: Path, apply: bool) -> int:
    """Surgical stale-row rewrites; untouched rows byte-preserved."""
    actions = 0
    for reg_name in ("prop_registry.md", "name_registry.md"):
        reg = project / "truth" / reg_name
        if not reg.is_file():
            continue
        new_text = registry_rewrites(reg.read_text("utf-8"))
        if new_text != reg.read_text("utf-8"):
            print(f"registry({reg_name}): 陈旧行重写")
            if apply:
                reg.write_text(new_text, "utf-8")
            actions += 1
    return actions


def main(argv: list[str] | None = None) -> int:
    """CLI entry: report faces; --apply writes (default dry-run zero-write)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="落盘（默认 dry-run 零写入）")
    ns = parser.parse_args(argv if argv is not None else None)
    project: Path = ns.project

    seeds = derive_seeds(project)
    for face in ("props", "counters", "identity"):
        val = getattr(seeds, face)
        print(f"seeds.{face}: {'n=' + str(len(val)) if val else 'SKIP/REFUSED'}")
    for note in seeds.notes:
        print(f"  note: {note}")

    actions = 0
    if ns.apply:
        actions += _apply_seeds(project, seeds)
    actions += _apply_memos(project, seeds, ns.apply)
    actions += _apply_registries(project, ns.apply)
    print(f"facts_backfill: {'APPLIED' if ns.apply else 'DRY-RUN'}, actions={actions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
