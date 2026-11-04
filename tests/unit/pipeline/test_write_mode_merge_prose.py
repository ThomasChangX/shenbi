"""Spec #95 T6a: merge_prose write-mode branch — fail-loud + base merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError


def _project(tmp_path: Path) -> Path:
    (tmp_path / "chapters").mkdir(exist_ok=True)
    (tmp_path / "chapters" / "chapter-9.md").write_text(
        "# 第9章\n<!--SCENE-->\n场景一原文。\n<!--SCENE-->\n场景二原文。\n",
        encoding="utf-8",
    )
    return tmp_path


def _payload(patches: dict[str, str]) -> str:
    parts = []
    for no, text in patches.items():
        parts.append(f"场景{no}：\n{text}\n")
    return "\n".join(parts)


def _write_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patches: dict[str, str] | None = None,
    payload_override: str | None = None,
) -> None:
    import shenbi.pipeline.dispatch_helper as dh

    project = _project(tmp_path)
    import shenbi.contracts as contracts_mod

    orig = contracts_mod.load_contract

    def _fake_contract(skill_name: str) -> object:
        if skill_name == "shenbi-chapter-revision":
            return {"write_semantics": {"chapters/chapter-9.md": {"mode": "merge_prose"}}}
        return orig(skill_name)

    monkeypatch.setattr(contracts_mod, "load_contract", _fake_contract)
    payload = payload_override if payload_override is not None else _payload(patches or {})
    dh._write_parsed_outputs(
        "",
        ["chapters/chapter-9.md"],
        project,
        skill="shenbi-chapter-revision",
        parsed={"chapters/chapter-9.md": payload},
    )


def test_merge_prose_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shenbi.pipeline.dispatch_helper as dh

    project = _project(tmp_path)
    out = project / "staging" / "chapters" / "chapter-9.md"
    out.parent.mkdir(parents=True)
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        dh.log,
        "info",
        lambda event, **kw: events.append((event, dict(kw))),
    )
    # 走公共入口 _write_parsed_outputs（parsed 面 + semantics 由契约加载器注入）
    import shenbi.contracts as contracts_mod

    orig = contracts_mod.load_contract

    def _fake_contract(skill_name: str) -> object:
        if skill_name == "shenbi-chapter-revision":
            return {"write_semantics": {"chapters/chapter-9.md": {"mode": "merge_prose"}}}
        return orig(skill_name)

    monkeypatch.setattr(contracts_mod, "load_contract", _fake_contract)
    dh._write_parsed_outputs(
        "",
        ["chapters/chapter-9.md"],
        project,
        skill="shenbi-chapter-revision",
        parsed={
            "chapters/chapter-9.md": _payload({"2": "替换后的场景二。加长扩写以过尺寸守卫。" * 5})
        },
    )
    written = [p for e, kw in events if e == "output_written" for p in [kw.get("path")]]
    assert any("chapter-9" in str(p) for p in written)
    assert any(kw.get("mode") == "merge_prose" for e, kw in events if e == "output_written")
    final = (project / "chapters" / "chapter-9.md").read_text(encoding="utf-8")
    assert "替换后的场景二。" in final and "场景一原文。" in final  # 未列场景保留


def test_unmatched_scene_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    project = _project(tmp_path)
    with pytest.raises(IncrementShapeError, match="场景定位键未匹配"):
        _write_merge(tmp_path, monkeypatch, {"7": "不存在"})


def test_empty_patch_list_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    project = _project(tmp_path)
    with pytest.raises(IncrementShapeError, match="场景级替换清单"):
        _write_merge(tmp_path, monkeypatch, payload_override="全文重写形（无场景段）")
