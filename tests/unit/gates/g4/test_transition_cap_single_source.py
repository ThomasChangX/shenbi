"""Spec #118 T4/I-2: transition-cap constant single-source pin + recalibration red test."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import TRANSITION_CAP_PER_1000

# 本文件在 tests/unit/gates/g4/ 下——parents[3]=tests/，repo 根须取 parents[4]
# （plan 审查 I-2 修正：parents[3] 会 cwd 到 tests/ 使 grep 空输出断言虚设）。
REPO = Path(__file__).resolve().parents[4]


def test_cap_constant_pinned() -> None:
    assert TRANSITION_CAP_PER_1000 == 1.0


def test_no_bare_copies_outside_single_source() -> None:
    out = (
        subprocess.run(
            ["grep", "-rn", "-E", "TRANSITION_CAP_PER_1000\\s*=\\s*[0-9.]+", "src/", "tools/"],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        .stdout.strip()
        .splitlines()
    )
    assert all("chapter_drafting.py" in ln for ln in out), out


def test_density_caliber_recaptured(tmp_path: Path) -> None:
    """Recalibration red test (I-5): old-band-inside/new-cap-outside chapter.

    tc=4, wc~2008: old max(5,2)=5 PASSes vs new density 1.99>1.0 FAILs
    (constructed structural input, G0.9-allowed).
    """
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    ch = d / "chapter-1.md"
    # wc (word_count_md narrative CJK) ~2000: 50 CJK x 40 paras; tc=4: four
    # paragraph-leading transition words (count_transition_words face).
    paras = [f"第{i}段" + "字" * 48 + "。" for i in range(40)]
    paras[3] = "不过，" + paras[3]
    paras[11] = "此时，" + paras[11]
    paras[19] = "突然，" + paras[19]
    paras[27] = "终于，" + paras[27]
    ch.write_text("---\n---\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
    res = json.loads(g4_chapter_drafting([str(ch)], str(d), str(d), repo_root=None))
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.transition:") for m in mf), mf[:3]  # 新封顶下 1.99>1.0 FAIL
