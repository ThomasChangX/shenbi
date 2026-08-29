"""z11 R3: product-contract checks wired into chapter completion (SDD #20, F1309/F1313)."""

import json
from pathlib import Path

import pytest

from shenbi.pipeline.product_contracts import check_product_contracts

FIX = Path("tests/fixtures/z11")


def _mk(tmp_path: Path, progress: dict[str, object] | None, ledger_lines: list[str] | None) -> Path:
    if progress is not None:
        (tmp_path / "progress.json").write_text(
            json.dumps(progress, ensure_ascii=False), encoding="utf-8"
        )
    if ledger_lines is not None:
        (tmp_path / "cost").mkdir()
        (tmp_path / "cost" / "token-ledger.jsonl").write_text(
            "\n".join(ledger_lines) + "\n", encoding="utf-8"
        )
    return tmp_path


def test_shell_progress_is_violation(tmp_path: Path) -> None:
    bad = json.loads(FIX.joinpath("progress-shell-bad.json").read_text(encoding="utf-8"))
    v = check_product_contracts(_mk(tmp_path, bad, ["{}"]))
    assert any("progress" in x for x in v)


def test_complete_progress_plus_ledger_passes(tmp_path: Path) -> None:
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    assert check_product_contracts(_mk(tmp_path, good, ["{}"])) == []


def test_missing_ledger_is_violation(tmp_path: Path) -> None:
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    v = check_product_contracts(_mk(tmp_path, good, None))
    assert any("token-ledger" in x for x in v)


def test_empty_ledger_is_violation(tmp_path: Path) -> None:
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    v = check_product_contracts(_mk(tmp_path, good, []))
    assert any("token-ledger" in x for x in v)


def test_no_progress_file_no_violation(tmp_path: Path) -> None:
    """A project dir without progress.json (bookkeeping not started) is not checked."""
    assert check_product_contracts(_mk(tmp_path, None, None)) == []


def test_complete_chapter_raises_on_contract_violation(tmp_path: Path) -> None:
    """Wiring: _complete_chapter fail-closes on a scorer-shell project (F1309)."""
    from shenbi.exceptions import ProductContractError
    from shenbi.pipeline.chapter_loop import _complete_chapter
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "progress.json").write_text(
        FIX.joinpath("progress-shell-bad.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.current_chapter = 1
    with pytest.raises(ProductContractError):
        _complete_chapter(state, 1)


def test_unreadable_artifacts_are_violations_not_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR #83/#84 review: OSError on progress/ledger reads fails closed as violations."""
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    # ledger exists with content so the emptiness check reaches read_text (and raises)
    _mk(tmp_path, good, ["{}"])

    real_read_text = Path.read_text

    def _raise_oserror(self: Path, *a: object, **k: object) -> str:
        if self.name in {"progress.json", "token-ledger.jsonl"}:
            raise OSError("io broken")
        return real_read_text(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", _raise_oserror)
    v = check_product_contracts(tmp_path)
    assert any("progress.json: unreadable" in x for x in v)
    assert any("token-ledger" in x for x in v)
