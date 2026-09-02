"""T5: shenbi-score exit code 契约(spec #38 F976)。

G0.9 说明:rubric/scores.json 为框架自产 JSON 非 skill 产物,沿仓内既有惯例
(tests/unit/test_scoring.py:41 sample_rubric)tmp_path 构造。
"""

import json
import sys
from pathlib import Path

RUBRIC_MD = """# Rubric

| # | 维度 | 权重 |
|---|------|------|
| 1 | 质量 | 100% |
"""


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    rubric = tmp_path / "rubric.md"
    rubric.write_text(RUBRIC_MD, encoding="utf-8")
    scores = tmp_path / "scores.json"
    # parse_scores_dict 期望平铺 string-keyed dict
    scores.write_text(json.dumps({"1": 95}), encoding="utf-8")
    return rubric, scores


def test_main_returns_zero(tmp_path, monkeypatch, capsys) -> None:
    """F976:main() 成功路径返回 int 0(原返回 dict → sys.exit(dict) rc=1)。"""
    from shenbi.scoring import main

    rubric, scores = _setup(tmp_path)
    monkeypatch.setattr(sys, "argv", ["shenbi-score", str(rubric), str(scores)])
    rc = main()
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["final_score"] == 95


def test_console_script_exit_zero(tmp_path) -> None:
    """端到端:console script(sys.exit(main()))语义下成功路径 exit 0。"""
    import subprocess
    from pathlib import Path as PathLocal

    script = PathLocal(sys.executable).parent / "shenbi-score"
    if not script.exists():  # Windows/布局差异兜底
        script = PathLocal(sys.executable).parents[1] / "bin" / "shenbi-score"
    rubric, scores = _setup(tmp_path)
    r = subprocess.run(
        [str(script), str(rubric), str(scores)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    json.loads(r.stdout)
