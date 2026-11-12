"""Spec #95 T3: matrix_scoped extractor — cast-scoped rows replace blind head+tail."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.read_extractors import extract_matrix_scoped

FIXTURES = Path(__file__).resolve().parents[3] / "tests/fixtures/spec95/00189-reads"


def _matrix_content() -> str:
    raw = (FIXTURES / "02-staging__truth__character_matrix.md").read_bytes()
    return raw.split(b"-->" + b"\n", 1)[1].decode("utf-8")


def _project(tmp_path: Path, cast_cell: str) -> Path:
    # staging-first grounding face: settle reads the staged summaries twin
    st = tmp_path / "staging" / "truth"
    st.mkdir(parents=True, exist_ok=True)
    (st / "chapter_summaries.md").write_text(
        "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |\n"
        "|---|---|---|---|---|---|\n"
        f"| 第 41 章 | 事件 | {cast_cell} | — | — | — |\n",
        encoding="utf-8",
    )
    (tmp_path / "truth").mkdir(exist_ok=True)
    (tmp_path / "truth" / "chapter_summaries.md").write_text("placeholder\n", encoding="utf-8")
    return tmp_path


def test_keeps_cast_rows_and_chapter_blocks(tmp_path: Path) -> None:
    cast = "那罕（林烽）、义仓差人（未具名）"  # matrix 名「林烽」在别名括注中
    out = extract_matrix_scoped(_project(tmp_path, cast), 41, _matrix_content())
    assert "[extractor:matrix_scoped]" in out
    assert "| 角色A | 角色B |" in out  # 键结构样例（表头）
    assert "林烽" in out
    assert "已按本章出场角色裁剪" in out  # 省略披露哨兵
    assert len(out) < len(_matrix_content()) // 3  # 大幅收敛（中段盲截替代）


def test_non_cast_pair_row_dropped(tmp_path: Path) -> None:
    synthetic = (
        "---\ntype: truth\n---\n# 角色交互矩阵\n\n"
        "| 角色A | 角色B | 关系性质 | 本章交互 | 变化 |\n|---|---|---|---|---|\n"
        "| 林烽 | 义仓差人 | 登记 | 面验 | 第 41 章 |\n"
        "| 老驼 | 帖木哥 | 旧识 | 路遇 | 第 12 章 |\n"
    )
    out = extract_matrix_scoped(_project(tmp_path, "那罕（林烽）"), 41, synthetic)
    assert "义仓差人" in out  # cast 对保留
    assert "老驼" not in out  # 无关对被裁


def test_chapter_status_blocks_kept_for_settle_pair(tmp_path: Path) -> None:
    # audit-T7 I2: 合成含 N/N+1 状态块的 matrix，钉死双块保留（真实 00189 fixture
    # 无 ch41/42 块——旧断言第三析取支恒被哨兵命中，名不副实）
    synthetic = (
        "---\ntype: truth\n---\n# 角色交互矩阵\n\n"
        "| 角色A | 角色B | 关系性质 | 本章交互 | 变化 |\n|---|---|---|---|---|\n"
        "| 林烽 | 义仓差人 | 登记 | 面验 | 第 41 章 |\n\n"
        "## 第 40 章状态增量\n\n旧块（非束伴，应裁）。\n\n"
        "## 第41章状态增量\n\n本章块保留。\n\n"
        "## 第 42 章状态增量\n\n束伴章块保留。\n"
    )
    out = extract_matrix_scoped(_project(tmp_path, "那罕（林烽）"), 41, synthetic)
    assert "第41章状态增量" in out and "本章块保留" in out
    assert "第 42 章状态增量" in out and "束伴章块保留" in out
    assert "旧块（非束伴，应裁）" not in out


def test_extractor_wired_into_prompt_success_path(tmp_path, monkeypatch) -> None:
    """audit-T7 I1: C1 regression guard - success-path wiring sentinel via build_skill_prompt."""
    import shenbi.pipeline.dispatch_helper as dh

    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |\n"
        "|---|---|---|---|---|---|\n"
        "| 第 41 章 | 事件 | 那罕（林烽） | — | — | — |\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "character_matrix.md").write_text(
        "---\ntype: truth\n---\n\n# 角色交互矩阵\n\n"
        "| 角色A | 角色B | 关系性质 | 本章交互 | 变化 |\n|---|---|---|---|---|\n"
        "| 林烽 | 义仓差人 | 登记 | 面验 | 第 41 章 |\n"
        "| 老驼 | 帖木哥 | 旧识 | 路遇 | 第 12 章 |\n",
        encoding="utf-8",
    )
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-state-settling", tmp_path, "settle ch41", chapter=41
    )
    assert "[extractor:matrix_scoped]" in user_prompt
    assert "已按本章出场角色裁剪" in user_prompt
    assert "老驼" not in user_prompt


def test_no_chapter_or_no_cast_degrades_loud(tmp_path: Path) -> None:
    assert extract_matrix_scoped(_project(tmp_path, "林烽"), None, _matrix_content()) == ""
    # summaries 缺本章行 → cast 无从得知 → ""（loud fulltext + WARN 降级契约）
    st = tmp_path / "staging" / "truth"
    st.mkdir(parents=True, exist_ok=True)
    (st / "chapter_summaries.md").write_text("| 章节 | 事件 |\n|---|---|\n", encoding="utf-8")
    assert extract_matrix_scoped(tmp_path, 41, _matrix_content()) == ""
