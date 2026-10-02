r"""Pre-merge ingestion guard for append_dedup truth increments (probe15 P1, batch #10 #20).

probe15 ch1 settle (3x G4.ss rejects → escalation): the model's
pending_hooks package re-emitted the whole-file scaffold — frontmatter,
``# 伏笔池``, a rewritten genesis quote, ``## 总览(本章改动行)``,
``## 总览`` + header + unchanged rows, ``## 详情`` — on top of its otherwise
correct per-hook ``### MHxx(名)`` bullet blocks. The merge machinery has
no way to treat that scaffold as non-destructive: the H1-led unit hit
``_replace_section`` whose span-to-EOF replacement destroyed the live base
(242 < 317 lines, 204 base lines dropped). G4 caught the damage only
POST-merge; the retry feedback never named the banned forms, so three
attempts converged nowhere.

The guard rejects the package machine-side, BEFORE any merge write, with
feedback naming the banned forms and the sanctioned increment shapes —
riding the existing dispatch-failure retry channel.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

_LIVE_HOOKS = """---
type: truth
category: state
status: initialized
---

# 伏笔池

## 总览
| Hook ID（钩子名） | 当前生命周期 | 种植章 |
| MH02（星火残梦与那句听不清的话） | PLANTED | 1 |

## 详情

### MH02（星火残梦与那句听不清的话）

- hook_id: MH02
- type: INFORMATION
- last_reinforced: 0
"""


def _project(tmp_path: Path) -> Path:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "pending_hooks.md").write_text(_LIVE_HOOKS, encoding="utf-8")
    (tmp_path / "truth" / "character_matrix.md").write_text(
        "# 角色矩阵\n## 交互总表\n| 角色A | 角色B | 关系 |\n", encoding="utf-8"
    )
    return tmp_path


def _write(tmp_path: Path, block: str, rel: str = "staging/truth/pending_hooks.md"):
    return _write_parsed_outputs(
        response=f"### FILE: {rel}\n{block}\n",
        output_paths=[rel],
        project_dir=tmp_path,
        skill="shenbi-state-settling",
    )


class TestScaffoldRejected:
    def test_frontmatter_h1_and_h2_scaffold_rejected_with_named_forms(self, tmp_path):
        package = (
            "---\ntype: truth\ncategory: state\n---\n\n"
            "# 伏笔池\n\n> 逐章模式（--mode default）第1章增量。\n\n"
            "## 总览（本章改动行）\n"
            "| CH1-L1（原主留下的半张活计签） | PLANTED | 1 |\n\n"
            "### MH02（星火残梦与那句听不清的话）\n- last_reinforced: 第 1 章\n"
        )
        with pytest.raises(IncrementShapeError) as ei:
            _write(_project(tmp_path), package)
        msg = str(ei.value)
        for named in ("frontmatter", "## 总览", "### MH"):
            assert named in msg, f"feedback must name the banned/sanctioned forms: {named}"

    def test_h2_scaffold_alone_rejected_for_hook_id_targets(self, tmp_path):
        package = "## 详情\n\n### MH02（星火残梦与那句听不清的话）\n- last_reinforced: 第 1 章\n"
        with pytest.raises(IncrementShapeError):
            _write(_project(tmp_path), package)

    def test_rejection_writes_nothing(self, tmp_path):
        project = _project(tmp_path)
        staged = project / "staging" / "truth" / "pending_hooks.md"
        with pytest.raises(IncrementShapeError):
            _write(project, "# 伏笔池\n> 重写说明\n")
        assert not staged.exists(), "a rejected package must not partially land in staging"


class TestCleanIncrementsPass:
    def test_hook_bullet_increment_merges(self, tmp_path):
        project = _project(tmp_path)
        package = (
            "### MH02（星火残梦与那句听不清的话）\n- last_reinforced: 第 1 章\n\n"
            "### CH1-L1（原主留下的半张活计签）\n- hook_id: CH1-L1\n- lifecycle_state: PLANTED\n"
        )
        out = _write(project, package)
        assert "staging/truth/pending_hooks.md" in out
        staged = (project / "staging" / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "- last_reinforced: 第 1 章" in staged
        assert "### CH1-L1（原主留下的半张活计签）" in staged
        # live base preserved through the merge
        assert "# 伏笔池" in staged
        assert "- hook_id: MH02" in staged

    def test_chapter_key_increment_section_allowed(self, tmp_path):
        """The character_matrix increment section (``## 第N章状态增量``) is a
        CONTRACT-SANCTIONED ## heading for chapter-keyed targets — the guard
        must not blanket-ban ## outside hook_id files.
        """
        project = _project(tmp_path)
        package = (
            "| 苏烬 | 石九 | 点人方 ↔ 被点方 | 第 1 章 |\n\n"
            "## 第 1 章状态增量\n### 苏烬\n- 位置: 赤锈谷\n"
        )
        out = _write(project, package, rel="staging/truth/character_matrix.md")
        assert "staging/truth/character_matrix.md" in out
        staged = (project / "staging" / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        assert "## 第 1 章状态增量" in staged
        assert "## 交互总表" in staged

    def test_h1_rejected_for_chapter_key_targets_too(self, tmp_path):
        project = _project(tmp_path)
        package = "# 角色矩阵\n## 第 1 章状态增量\n### 苏烬\n- 位置: 赤锈谷\n"
        with pytest.raises(IncrementShapeError):
            _write(project, package, rel="staging/truth/character_matrix.md")
