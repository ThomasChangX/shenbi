"""Wiring tests: aggregate is refreshed before every revision dispatch."""

from pathlib import Path

import pytest

from shenbi.pipeline import chapter_loop
from shenbi.pipeline.audit_aggregate import aggregate_path
from shenbi.pipeline.state import PipelineState

FIX = Path("tests/fixtures/audits/chapter-1-consistency.md")


def test_generic_step_writes_aggregate_before_revision_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    # 必须用 character 维度文件名（_any_audit_has_findings 只扫固定 atype
    # 清单，含 character 不含 consistency），且需含 BLOCKING/FAIL 字样才
    # 触发条件步——在 tmp 副本末尾追加（fixture 文件本身不动）
    body = FIX.read_text(encoding="utf-8")
    (audit_dir / "chapter-1-character.md").write_text(
        body + "\n| P3 | 测试注入 | **BLOCKING** |\n", encoding="utf-8"
    )
    calls: list[str] = []

    class _Result:
        success = True
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_dispatch(skill, project_dir, prompt, **kwargs):
        calls.append(skill)
        # dispatch_skill 是子进程边界 mock；聚合必须发生在它之前
        assert aggregate_path(Path(project_dir), 1).exists(), (
            "aggregate must exist before shenbi-chapter-revision dispatch"
        )
        return _Result()

    monkeypatch.setattr(chapter_loop, "dispatch_skill", _fake_dispatch)
    state = PipelineState()
    state.project_dir = str(tmp_path)
    state.chapter_loop.current_chapter = 1
    # 定位 Step 16（shenbi-chapter-revision）
    idx = next(
        i for i, s in enumerate(chapter_loop.CHAPTER_STEPS) if s.skill == "shenbi-chapter-revision"
    )
    state.chapter_loop.step_index = idx
    # 派发后的 G4/步进处理在 tmp_path 下可能走重试/checkpoint 分支——
    # 断言只依赖 fake-dispatch 闭包（派发时聚合已存在）与 calls 记录，
    # 返回值不约束
    chapter_loop.run_chapter_step(state, tmp_path)
    assert "shenbi-chapter-revision" in calls
