#!/usr/bin/env python3
"""Spec #116 T2: vacuity registry sentinel lint（恒真登记＋分类证据义务）.

对 `docs/framework/gate-power-baseline.md` 执法，分母单源 = 对
`src/shenbi/gates/g4/chapter_drafting.py` 的**单文件**双扫描（C4 修订——
不读 #88 g4-id-inventory.json 作等式源：该清单含 character_design 交叉
污染且缺 protagonist_absent；存在时仅打印交叉参考 diff 到 stderr，不执法）：

1. **registry↔AST 漂移**：扫描产出（check 行 dict id ∪ mf 首常量 id，剥
   ``G4.`` 前缀、经 ARM_TO_CANONICAL 回射 canonical）∪ EXPLICIT_SUPPLEMENT
   （扫描不可见的变量/裸形发射臂）− SCAN_EXCLUDE == registry canonical 集
   （STATE_FREE_IDS ∪ TRUTH_DEPENDENT_IDS，import 自 tools/gate_power_replay
   ——防双源漂移）。多=未登记→FAIL；少=死键→FAIL。
2. **baseline 行集**：require_full_registry 时表行集==registry 集（缺→FAIL）；
   表内 registry 外行→FAIL（恒多）。
3. **分类值域**：分类列 ∈ VALID_CLASSIFICATIONS（值域外→FAIL）。
4. **证据义务**：非 discriminating 行证据列非空且非「—」（「—」仅
   unclassified 允许；unclassified 允许填红测链接供裁定参考）→FAIL。
5. **升格判据**：unclassified 且最近回放数含「0 点火」的行——today ≥
   ESCALATION_DATE → FAIL；此前 stderr WARN＋exit 0（WARN 级不阻断）。

分类标签全部由人工裁定（spec 风险节：判别力≠正确性，0 点火可能是 floor
有效也可能是门坏——仪表不得自动断言），本 lint 只强制「登记在册＋义务
可见」，不替人分类。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # repo 根——统一 tools. 包身份（gen_gate_power_fixtures.py 先例）
from tools.gate_power_replay import (
    ARM_TO_CANONICAL,
    STATE_FREE_IDS,
    TRUTH_DEPENDENT_IDS,
)

REPO = Path(__file__).resolve().parents[1]
GATE_SOURCE = REPO / "src" / "shenbi" / "gates" / "g4" / "chapter_drafting.py"
BASELINE_DOC = REPO / "docs" / "framework" / "gate-power-baseline.md"
INVENTORY_JSON = REPO / "tests" / "fixtures" / "g4-id-inventory.json"

# M1 升格锚 = baseline 回填日 2026-11-19 ＋ 30 天（一个完整裁定周期；spec r2/I5
# 「分类义务清偿后」以该日历日近似）。若 Task 5 实跑日晚于 2026-11-19，按
# 「实跑日＋30 天」改此常量并在 task report 记录（docs/framework/
# gate-power-baseline.md 头节同步声明）。
ESCALATION_DATE = date(2026, 12, 19)
PRE_ESCALATION = date(2026, 11, 19)

VALID_CLASSIFICATIONS = frozenset(
    {"unclassified", "floor-untested", "decorative", "discriminating", "retired"}
)

# NB4 预列显式补充面：扫描不可见的组合/变量发射臂（f"G4.{issue}" 变量形、
# helper 内裸形 f-string、无 G4. 前缀的 check 行）。两处实现者裁定：
# - cd.post_wordcount_precision 系 NB4 预列缺项（WARN-only 裸形 check 行，
#   chapter_drafting.py:952——与 post_quote_verbatim 同形，扫描双正则均不可见）；
# - cd.balance_value_drift.bundle 已裁除（I1：唯一发射点 state_settling.py:305
#   settle 面，非本章门分母——登记保留无回放面，删；mf 串经 ARM_TO_CANONICAL
#   回射父行 cd.balance_value_drift）。
EXPLICIT_SUPPLEMENT = frozenset(
    {
        "cd.protagonist_absent",  # helper 内 f-string（protagonist_issues 列表，mf.extend 收）
        "cd.prop_handoff",  # check 行裸形（:776）＋ check_prop_handoffs 变量臂
        "cd.counter",  # check 行裸形（:806/:817）＋ check_counter_reconciliation 变量臂
        "cd.counter.plan_conflict",  # check_counter_reconciliation helper 内 f-string
        "cd.counter.base_mismatch",  # 同上
        "cd.counter.prose_mismatch",  # 同上
        "cd.balance_value_drift",  # check 行裸形（:862/:885）＋ post_declarations helper 臂
        "cd.post_quote_verbatim",  # check 行裸形（:925）＋ check_post_quote_verbatim 臂
        "cd.post_transition_cross",  # check_post_transition_cross helper 臂（无 check 行）
        "cd.post_wordcount_precision",  # WARN-only check 行裸形（:952，NB4 预列缺项）
    }
)

# 非检查的错误/杂臂——扫描可见但不入 registry（行属 file-not-found 错误面）。
SCAN_EXCLUDE = frozenset({"file_not_found"})

# 双扫描正则（brief 权威形）：(a) check 行 dict id；(b) mf/c append/extend 首常量 id。
_SCAN_CHECK_RE = re.compile(r'"id":\s*"(G4\.[a-zA-Z0-9_.]+)"')
_SCAN_MF_RE = re.compile(r'(?:mf|c)\.(?:append|extend)\(\s*f"(G4\.[a-zA-Z0-9_.]+):')

_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_ROW_ID = re.compile(r"^`([^`]+)`$")
# 主表 schema 表头——头节其余表（分类语义表等）不属执法面
_BASELINE_HEADER = ("check", "口径", "期望点火带", "分类", "证据", "最近回放数", "归因")
_BASELINE_COLUMNS = len(_BASELINE_HEADER)
_IDX_CLASSIFICATION, _IDX_EVIDENCE, _IDX_REPLAY = 3, 4, 5
_ZERO_FIRING_MARK = "0 点火"


def _bare(cid: str) -> str:
    """Strip the ``G4.`` prefix (scan output and registry constants join the bare domain)."""
    return cid[len("G4.") :] if cid.startswith("G4.") else cid


# 别名表单源（I1）：registry 侧 canonical id 与发射臂回射共用 ARM_TO_CANONICAL，
# 本工具仅在裸形域取同一映射——mf 臂形（含 truth 族 G4. 包装形）回射 check 行形。
_ARM_ALIAS_BARE: dict[str, str] = {_bare(k): _bare(v) for k, v in ARM_TO_CANONICAL.items()}


def _canon(bare_id: str) -> str:
    """Map a bare id through the alias table (no_hook→chapter_end_hook etc.)."""
    return _ARM_ALIAS_BARE.get(bare_id, bare_id)


def registry_canonical_ids() -> frozenset[str]:
    """Registry canonical bare-id全集（Task 1 常量单源 import，防双源漂移）."""
    return frozenset(_canon(_bare(c)) for c in STATE_FREE_IDS | TRUTH_DEPENDENT_IDS)


def registry_drift(gate_source: Path = GATE_SOURCE) -> list[str]:
    """C4 修订：registry∪arms == chapter_drafting.py 单文件扫描∪显式补充.

    漂移双向红：扫描侧多出=未登记 check；registry 侧多出=死键（无发射面）。
    """
    src = gate_source.read_text(encoding="utf-8")
    scanned = set(_SCAN_CHECK_RE.findall(src)) | set(_SCAN_MF_RE.findall(src))
    scan_side = {_canon(_bare(c)) for c in scanned if _bare(c) not in SCAN_EXCLUDE}
    scan_side |= {_canon(_bare(c)) for c in EXPLICIT_SUPPLEMENT}

    registry_ids = [_bare(c) for c in STATE_FREE_IDS | TRUTH_DEPENDENT_IDS]
    drift: list[str] = []
    if len(set(registry_ids)) != len(registry_ids):
        # 裸形碰撞=常量集自身漂移（前缀形/裸形重复登记同一行）
        dupes = sorted({c for c in registry_ids if registry_ids.count(c) > 1})
        drift.append(f"registry bare-form collision: {', '.join(dupes)}")
    registry_side = frozenset(_canon(c) for c in registry_ids)
    drift.extend(
        f"unregistered check (scan-side only): {c}" for c in sorted(scan_side - registry_side)
    )
    drift.extend(
        f"dead registry key (no emission surface): {c}" for c in sorted(registry_side - scan_side)
    )
    return drift


# WARN-only 行（发射面仅 WARN，无 FAIL 臂——brief 指定六行；裸形域，与
# CHECK_REGISTRY 键同域）
_WARN_ONLY_IDS = frozenset(
    {
        "cd.surge",
        "cd.simile_band",
        "cd.golden_slot",
        "cd.ending_diversity",
        "cd.post_wordcount_precision",
        "cd.post_quote_verbatim",
    }
)


def _caliber(canonical: str) -> str:
    """口径列（M3）——CHECK_REGISTRY 键为裸形，常量集混前缀/裸形，双形查."""
    prefixed = f"G4.{canonical}"
    if canonical in STATE_FREE_IDS or prefixed in STATE_FREE_IDS:
        return "state-free"
    if canonical in TRUTH_DEPENDENT_IDS or prefixed in TRUTH_DEPENDENT_IDS:
        return "truth"
    return "—"


def _fail_arms(canonical: str) -> list[str]:
    """发射该 canonical 行 FAIL 的 mf 臂形（ARM_TO_CANONICAL 反转，发射形保留）."""
    return sorted(arm for arm, target in ARM_TO_CANONICAL.items() if _bare(target) == canonical)


# CHECK_REGISTRY：canonical → {fail_arms, warn_only, 口径}（骨架——分类义务在
# baseline 表，不在本表；本表是 lint 的 registry 分母与元数据单源）。
CHECK_REGISTRY: dict[str, dict] = {
    canonical: {
        "fail_arms": _fail_arms(canonical),
        "warn_only": canonical in _WARN_ONLY_IDS,
        "口径": _caliber(canonical),
    }
    for canonical in sorted(registry_canonical_ids())
}


def _parse_rows(doc: Path) -> list[tuple[str, list[str]]]:
    """Parse the main registry table -> [(bare check id, cells)].

    仅识别表头恰为 _BASELINE_HEADER 的表（头节分类语义等辅助表不属执法面）；
    非数据行（表头/分隔/散文/空行终止表）跳过。
    """
    rows: list[tuple[str, list[str]]] = []
    in_table = False
    for line in doc.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(_SEPARATOR_CELL.fullmatch(c) for c in cells if c):
            continue
        if tuple(cells) == _BASELINE_HEADER:
            in_table = True
            continue
        if not in_table:
            continue
        m = _ROW_ID.fullmatch(cells[0]) if cells else None
        if m is None:
            continue
        rows.append((m.group(1), cells))
    return rows


def _row_findings(row_id: str, cells: list[str], today: date) -> tuple[list[str], list[str]]:
    """单行检查 -> (FAIL 消息, WARN 消息)（行已知在 registry 内且列数合规）."""
    label = f"`{row_id}`"
    classification = cells[_IDX_CLASSIFICATION]
    evidence = cells[_IDX_EVIDENCE]
    replay = cells[_IDX_REPLAY]
    fails: list[str] = []
    warns: list[str] = []
    if classification not in VALID_CLASSIFICATIONS:
        fails.append(f"FAIL invalid classification {classification!r}: {label}")
    # 证据义务：非 discriminating 须有实证据；「—」仅 unclassified 允许
    if classification not in ("discriminating", "unclassified") and evidence in ("", "—"):
        fails.append(f"FAIL non-discriminating lacks evidence: {label}")
    # 升格判据：unclassified＋显式「0 点火」——锚前 WARN，锚后 FAIL
    if classification == "unclassified" and _ZERO_FIRING_MARK in replay:
        if today >= ESCALATION_DATE:
            fails.append(f"FAIL unclassified 0-firing past escalation {ESCALATION_DATE}: {label}")
        else:
            warns.append(f"WARN unclassified 0-firing awaiting adjudication: {label}")
    return fails, warns


def lint_file(path: Path, today: date = PRE_ESCALATION, require_full_registry: bool = True) -> int:
    """Lint one baseline doc；0=绿，1=FAIL；WARN 级=stderr 行＋exit 0."""
    failed = False

    drift = registry_drift()
    for d in drift:
        print(f"FAIL registry drift: {d}", file=sys.stderr)
    if drift:
        return 1

    if not path.is_file():
        print(f"FAIL baseline doc absent: {path}", file=sys.stderr)
        return 1

    registry = registry_canonical_ids()
    seen: set[str] = set()
    for row_id, cells in _parse_rows(path):
        label = f"`{row_id}`"
        if len(cells) < _BASELINE_COLUMNS:
            print(f"FAIL malformed row (needs {_BASELINE_COLUMNS} cells): {label}", file=sys.stderr)
            failed = True
            continue
        canonical = _canon(_bare(row_id))
        if canonical not in registry:
            print(f"FAIL row not in registry: {label}", file=sys.stderr)
            failed = True
            continue
        if canonical in seen:
            print(f"FAIL duplicate row: {label}", file=sys.stderr)
            failed = True
            continue
        seen.add(canonical)
        fails, warns = _row_findings(row_id, cells, today)
        for msg in fails + warns:
            print(msg, file=sys.stderr)
        failed = failed or bool(fails)

    if require_full_registry:
        for canonical in sorted(registry - seen):
            print(f"FAIL missing baseline row: `{canonical}`", file=sys.stderr)
            failed = True

    return 1 if failed else 0


def _inventory_cross_reference() -> None:
    """#88 清单交叉参考（信息行，不执法——C4：不作集合等式一源）."""
    if not INVENTORY_JSON.is_file():
        return
    ids = set(json.loads(INVENTORY_JSON.read_text(encoding="utf-8")).get("ids", []))
    inv_side = {_canon(_bare(i)) for i in ids if i.startswith(("cd.", "G4."))}
    registry_side = registry_canonical_ids()
    print(
        "info g4-id-inventory cross-ref: only-in-inventory="
        f"{sorted(inv_side - registry_side)} only-in-registry="
        f"{sorted(registry_side - inv_side)}",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the vacuity-registry sentinel over the baseline doc."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=BASELINE_DOC)
    args = parser.parse_args(argv)

    _inventory_cross_reference()
    return lint_file(args.path, today=date.today(), require_full_registry=True)


if __name__ == "__main__":
    raise SystemExit(main())
