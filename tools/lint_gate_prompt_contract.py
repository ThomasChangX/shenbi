"""Gate 词表 ⇄ prompt 契约 lint（spec #95 T1，修 R1/R2）.

CHECK_ENUM_REGISTRY 驱动（枚举检查清单从常量注册表派生，禁手列函数清单）：
每个有枚举判定的检查，其 SKILL.md 必须含 verbatim 模板块——

1. 合法值逐行列出（每个值独占一行，允许 `- 值`/裸行/`| 值 |` 表格形）
2. 「只许单值」明示（禁斜杠/组合形）
3. 一个最小正例行（`chapter_role: <单值>` 形）
4. 禁斜杠分组教学形：任意两个合法值的 `a/b` 复合不得出现在 SKILL 正文
   （R1 根因：把「档位分组」写成「可用值」，模型照抄所见）

check-id 专属附加要求走 EXTRA_REQUIREMENTS（defer 锚模板+数据形正例，R2）。
退出码：0=全 PASS；1=findings（CI 面）。
"""

from __future__ import annotations

import re
import sys
from itertools import permutations
from pathlib import Path

from shenbi.contracts.enums import CHECK_ENUM_REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent

# check-id → 附加要求（(要求名, 判定函数(skill_text) -> bool)）
_DEFER_ANCHOR_RE = re.compile(r"至第[一二三四五六七八九十\d]+卷·KR\d+")


def _has_defer_template(text: str) -> bool:
    return "至第N卷·KRn" in text and bool(_DEFER_ANCHOR_RE.search(text))


EXTRA_REQUIREMENTS: dict[str, dict[str, object]] = {
    # R2：锚模板说明 + 数据形最小正例（00145/00167 实证——模型抄数据形最稳）
    "cp.chapter_role": {
        "defer_anchor_template_and_data_form_exemplar": _has_defer_template,
    },
}

_VALUE_LINE_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _value_line_re(value: str) -> re.Pattern[str]:
    if value not in _VALUE_LINE_RE_CACHE:
        _VALUE_LINE_RE_CACHE[value] = re.compile(
            rf"^\s*(?:>\s*)?(?:[-*]|\|)?\s*[`*]*{re.escape(value)}[`*]*\s*(?:\|)?\s*$",
            re.MULTILINE,
        )
    return _VALUE_LINE_RE_CACHE[value]


def lint_skill(
    check_id: str, const_name: str, skill_rel: str, values: tuple[str, ...]
) -> list[str]:
    """Lint one registry entry's SKILL for the verbatim template block."""
    findings: list[str] = []
    skill_path = REPO_ROOT / skill_rel
    if not skill_path.is_file():
        return [f"[{check_id}] SKILL not found: {skill_rel}"]
    text = skill_path.read_text(encoding="utf-8")

    for value in values:
        if not _value_line_re(value).search(text):
            findings.append(
                f"[{check_id}] verbatim 逐行清单缺值行: {value!r}（const={const_name}）"
            )
    if "只许单值" not in text:
        findings.append(f"[{check_id}] 缺「只许单值」明示（禁斜杠/组合形）")
    exemplar = re.search(rf"chapter_role[:：]\s*{re.escape(values[0])}\b", text)
    if exemplar is None:
        findings.append(f"[{check_id}] 缺最小正例行（`chapter_role: {values[0]}` 形）")
    # 禁斜杠分组教学形：任两合法值复合 `a/b`
    for a, b in permutations(values, 2):
        composite = f"{a}/{b}"
        if composite in text:
            findings.append(
                f"[{check_id}] 斜杠分组教学形残留: {composite!r}（R1 根因——档位分组被写成可用值）"
            )
    for req_name, judge in EXTRA_REQUIREMENTS.get(check_id, {}).items():
        if not judge(text):  # pyright: ignore[reportCallIssue]
            findings.append(f"[{check_id}] 附加要求未满足: {req_name}")
    return findings


def main() -> int:
    """Entry: lint every registry entry; non-zero exit on findings."""
    import shenbi.contracts.enums as enums_mod  # noqa: PLC0415 — after _VALUE cache setup

    all_findings: list[str] = []
    for check_id, (const_name, skill_rel) in CHECK_ENUM_REGISTRY.items():
        values = getattr(enums_mod, const_name, None)
        if values is None:
            all_findings.append(f"[{check_id}] registry 常量不存在: {const_name}")
            continue
        all_findings.extend(lint_skill(check_id, const_name, skill_rel, values))

    if all_findings:
        for f in all_findings:
            print(f, file=sys.stderr)
        print(f"gate-prompt contract lint: {len(all_findings)} findings", file=sys.stderr)
        return 1
    print("gate-prompt contract lint: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
