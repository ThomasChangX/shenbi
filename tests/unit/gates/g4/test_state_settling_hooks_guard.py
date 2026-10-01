"""Content-preservation guard for STAGED pending_hooks (probe2 ch2 settle).

Probe2 (2026-10-01): the settle writer damaged truth/pending_hooks.md twice
(ch1 hand-repaired at review, ch2 rejected) while G4 passed both times — the
matrix-only guard never ran on pending_hooks, whose only check was a token
``"state" in content``. Damage classes caught here: dropped MH detail lines
(type/埋设/trigger/resolve/depends_on), overwritten per-chapter increment
sections, and ``>``→``&gt;`` escape corruption of annotation lines.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.state_settling import g4_state_settling

_LIVE_HOOKS = """---
type: truth
category: state
status: initialized
---

# 伏笔池

## 种子伏笔
| ID | 伏笔内容 | 埋设位置 | 计划回收 | 状态 |
| H-001 | 童谣 | 第一至三章 | 中后段 | 未回收 |

## 跨卷主钩子（MH-*）
| MH-001 | GENUINE | CHARACTER | 石镐 | 第7章 | 第50章 | PLANTED |

### MH-012 地脉衰竭
- type: GENUINE ｜ dimension: INFORMATION ｜ lifecycle_state: PLANTED
- 埋设: 第1卷第10章（汲取塔停机夜）
- trigger_condition: 塔群熔毁后地脉波形不再恢复（第39章）
- resolve_condition: 第44章完整真相
- subtlety: 0.65 ｜ cultivation_interval: 5
- depends_on: []
- notes: 续接 H-003

## 状态变更总览（第1章）
### H-001 童谣
- lifecycle_state: PLANTED → RELEVANT（第1章）
- trigger_condition: 第三个地名被说出
- notes: 第1章仅环境音
"""

_STAGED_OK = (
    _LIVE_HOOKS.replace("- notes: 续接 H-003", "- notes: 续接 H-003；第2章余味加深").replace(
        "### MH-012 地脉衰竭\n- type: GENUINE ｜ dimension: INFORMATION ｜ lifecycle_state: PLANTED",
        "### MH-012 地脉衰竭\n- type: GENUINE ｜ dimension: INFORMATION ｜ lifecycle_state: PLANTED → RELEVANT（第2章）",
    )
    + """
## 状态变更总览（第2章）
### MH-012 地脉衰竭
- lifecycle_state: PLANTED → RELEVANT（第2章）
- 证据: chapters/chapter-2.md L10-12
"""
)


def _project(tmp_path: Path, live: str, staged: str) -> Path:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "staging" / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "pending_hooks.md").write_text(live, encoding="utf-8")
    staged_path = tmp_path / "staging" / "truth" / "pending_hooks.md"
    staged_path.write_text(staged, encoding="utf-8")
    return tmp_path


def _run(project: Path) -> tuple[str, list[str]]:
    import json

    raw = g4_state_settling(["staging/truth/pending_hooks.md"], str(project), str(project))
    result = json.loads(raw)
    return result["status"], result.get("must_fix", [])


class TestHooksContentPreservation:
    def test_volatile_field_updates_pass(self, tmp_path):
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, _STAGED_OK))
        assert status == "PASS", mf

    def test_dropped_mh_detail_lines_fail(self, tmp_path):
        staged = (
            _STAGED_OK.replace("- 埋设: 第1卷第10章（汲取塔停机夜）\n", "")
            .replace("- trigger_condition: 塔群熔毁后地脉波形不再恢复（第39章）\n", "")
            .replace("- resolve_condition: 第44章完整真相\n", "")
            .replace("- depends_on: []\n", "")
        )
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, staged))
        assert status == "FAIL"
        assert any("hooks_structure" in m and "content_dropped" in m for m in mf), mf

    def test_overwritten_increment_section_fails(self, tmp_path):
        staged = _STAGED_OK.replace(
            """## 状态变更总览（第1章）
### H-001 童谣
- lifecycle_state: PLANTED → RELEVANT（第1章）
- trigger_condition: 第三个地名被说出
- notes: 第1章仅环境音""",
            """## 状态变更总览（第1章）
### H-002 档案
- lifecycle_state: PLANTED（第2章）
- notes: 本章重写""",
        )
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, staged))
        assert status == "FAIL"
        assert any("hooks_structure" in m for m in mf), mf

    def test_missing_hooks_file_still_fails(self, tmp_path):
        import json

        raw = g4_state_settling(["staging/truth/pending_hooks.md"], str(tmp_path), str(tmp_path))
        result = json.loads(raw)
        assert result["status"] == "FAIL"
        assert any("not_found" in m for m in result["must_fix"])


class TestEscapeCorruption:
    def test_gt_escape_corruption_flagged(self, tmp_path):
        live = (
            "# 角色交互矩阵\n\n> 信任度列由 relationship-map 给出推定初值。\n\n## 一、信任度矩阵\n"
        )
        staged = live.replace("> 信任度列", "&gt; 信任度列")
        project = tmp_path
        (project / "truth").mkdir(parents=True, exist_ok=True)
        (project / "staging" / "truth").mkdir(parents=True, exist_ok=True)
        (project / "truth" / "character_matrix.md").write_text(live, encoding="utf-8")
        (project / "staging" / "truth" / "character_matrix.md").write_text(staged, encoding="utf-8")
        import json

        raw = g4_state_settling(["staging/truth/character_matrix.md"], str(project), str(project))
        result = json.loads(raw)
        assert result["status"] == "FAIL"
        assert any("escape_corruption" in m for m in result["must_fix"]), result["must_fix"]


class TestHookRowStableColumnPreservation:
    """Probe2 ch1/ch2: H-001/H-005 SEED rows had their stable planning
    columns (伏笔内容/埋设位置/计划回收) replaced with per-chapter
    reinforcement notes while the status column stayed plausible — the
    whole-row table exemption made this G4-invisible twice. Same-key rows
    may legitimately change ONLY the final (status) column.
    """

    def test_seed_row_stable_columns_rewritten_fails(self, tmp_path):
        staged = _LIVE_HOOKS.replace(
            "| H-001 | 童谣 | 第一至三章 | 中后段 | 未回收 |",
            "| H-001 | 童谣 | 第 1 章：棚外孩童哼唱 | 未回收 | last_reinforced=第 1 章 |",
        )
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, staged))
        assert status == "FAIL"
        assert any("hook_row" in m and "H-001" in m for m in mf), mf

    def test_seed_row_status_column_update_passes(self, tmp_path):
        staged = _LIVE_HOOKS.replace(
            "| H-001 | 童谣 | 第一至三章 | 中后段 | 未回收 |",
            "| H-001 | 童谣 | 第一至三章 | 中后段 | 已回收 |",
        )
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, staged))
        assert status == "PASS", mf

    def test_mh_overview_row_rewritten_fails(self, tmp_path):
        staged = _LIVE_HOOKS.replace(
            "| MH-001 | GENUINE | CHARACTER | 石镐 | 第7章 | 第50章 | PLANTED |",
            "| MH-001 | GENUINE | CHARACTER | 石镐的腿伤 | 第1卷第7-8章 | 第5卷第50章 | RELEVANT |",
        )
        status, mf = _run(_project(tmp_path, _LIVE_HOOKS, staged))
        assert status == "FAIL"
        assert any("hook_row" in m and "MH-001" in m for m in mf), mf
