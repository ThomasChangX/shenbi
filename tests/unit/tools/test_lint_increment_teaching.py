"""Spec #99 Task 4 Step 6: existence-lint green face + tamper red tests."""

from __future__ import annotations

import pytest


def _run() -> int:
    import tools.lint_increment_teaching as mod

    return mod.main()


@pytest.mark.unit
def test_green_on_current_tree() -> None:
    assert _run() == 0


@pytest.mark.unit
def test_tamper_red_missing_exclusion_clause(tmp_path, monkeypatch, capsys) -> None:
    import tools.lint_increment_teaching as mod

    (tmp_path / "skills/shenbi-state-settling").mkdir(parents=True)
    skill = tmp_path / "skills/shenbi-state-settling" / "SKILL.md"
    skill.write_text("铁律 0 旧版内容（本节尚未迁移）\n", encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", tmp_path)
    (tmp_path / "src/shenbi/pipeline").mkdir(parents=True)
    (tmp_path / "src/shenbi/pipeline/chapter_loop.py").write_text(
        "## 第2章状态增量\n", encoding="utf-8"
    )
    (tmp_path / "src/shenbi/pipeline/dispatch_helper.py").write_text(
        "block per chapter twin N+1 OTHER chapter keyed-upsert replaceable unit\n",
        encoding="utf-8",
    )
    rc = mod.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "缺 `排除条款`" in err and "缺 `自陈补全（第N章原句）`" in err


@pytest.mark.unit
def test_tamper_red_spaced_example_returns(tmp_path, monkeypatch, capsys) -> None:
    import tools.lint_increment_teaching as mod

    (tmp_path / "skills/shenbi-state-settling").mkdir(parents=True)
    (tmp_path / "skills/shenbi-state-settling/SKILL.md").write_text(
        "排除条款 keyed-upsert 可整体替换单元 自陈补全（第N章原句）\n", encoding="utf-8"
    )
    (tmp_path / "src/shenbi/pipeline").mkdir(parents=True)
    (tmp_path / "src/shenbi/pipeline/chapter_loop.py").write_text(
        '"## 第 2 章状态增量"\n', encoding="utf-8"
    )
    (tmp_path / "src/shenbi/pipeline/dispatch_helper.py").write_text(
        "block per chapter twin N+1 OTHER chapter keyed-upsert replaceable unit\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main() == 1
    assert "空格形示例回流" in capsys.readouterr().err
