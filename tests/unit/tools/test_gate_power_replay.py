"""Spec #116 T1: gate-power replay tool unit tests (structural inputs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gate_power_replay import (
    ARM_TO_CANONICAL,
    STATE_FREE_IDS,
    TRUTH_DEPENDENT_IDS,
    collect,
    hook_window_attribution,
    narrative_window,
    summarise,
)

# 结构性合成章（AGENTS.md 允许：tmp_path 内联合法，非 fixture 冒充技能产物）
CH_WITH_HOOK = """---
name: 测试章
---

## PRE_WRITE_CHECK

- 本章字数: 200

## 第一章　测试

他推开门，看见院子里堆着柴。她还站在原地没动。

「你还欠着账。」他说。

门外的风吹进来，烛火晃了一下。到底谁在撒谎？41 人失踪，82 户报官。

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK

- [x] 自检完成: 是
- [x] 实际字数: 200
<!--META-END-->
"""


def _mk_project(tmp_path: Path, chapters: dict[str, str]) -> Path:
    (tmp_path / "chapters").mkdir()
    for name, text in chapters.items():
        (tmp_path / "chapters" / name).write_text(text, encoding="utf-8")
    return tmp_path


class TestCollect:
    def test_collect_all_pass_chapter_no_must_fix_key(self, tmp_path: Path) -> None:
        """C1 钉：passed() 无 must_fix 键——collect 不得 KeyError。"""
        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        rows = collect(rd, "chapter-*.md")  # 不抛 KeyError 即通过
        assert len(rows) == 1
        # NB1：合成章短于 3000 字下限且无场景标记——must_fix 必非空；只钉键存在性
        assert isinstance(rows[0]["must_fix"], list)

    def test_collect_passed_shape_json_without_must_fix_key(self, tmp_path, monkeypatch) -> None:
        """C1 病灶路径直测：monkeypatch g4 返回 passed() 形 JSON（无 must_fix 键）。"""
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        monkeypatch.setattr(
            gpr,
            "g4_chapter_drafting",
            lambda fps, rd=None, project_dir=None, repo_root=None: json.dumps(
                {"gate": "G4-chapter-drafting", "status": "PASS", "checks": [], "timestamp": "t"}
            ),
        )
        rows = gpr.collect(rd, "chapter-*.md")
        assert rows[0]["must_fix"] == []

    def test_collect_skips_non_pure_chapter_files(self, tmp_path: Path) -> None:
        rd = _mk_project(
            tmp_path,
            {"chapter-1.md": CH_WITH_HOOK, "chapter-1-pre-rev.md": CH_WITH_HOOK},
        )
        rows = collect(rd, "chapter-*.md")
        assert [r["file"] for r in rows] == ["chapter-1.md"]


class TestNarrativeWindow:
    def test_window_excludes_meta_and_hook_blocks(self) -> None:
        """C3 钉：窗口=三重预处理后的叙事段，POST 块不占窗口位。"""
        text = "第一段但在这里。\n\n第二段他还欠着账。\n\n" + (
            "<!--HOOK-BEGIN-->钩子台账<!--HOOK-END-->\n\n"
            "<!--META-BEGIN-->\n## POST_WRITE_SELF_CHECK\n\n- [x] 项\n<!--META-END-->"
        )
        paras = narrative_window(text)
        assert paras == ["第一段但在这里。", "第二段他还欠着账。"]

    def test_window_matches_gate_preprocessing_on_real_fixture(self) -> None:
        """真实 fixture 章上窗口归因与门判定双向一致（C3/I6 修订）。"""
        fixture = Path("tests/fixtures/chapters/chapter-1.md").resolve()
        if not fixture.is_file():
            pytest.skip("fixture chapters/chapter-1.md 不在盘")
        from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

        content = fixture.read_text(encoding="utf-8")
        attr = hook_window_attribution(content)
        res = json.loads(
            g4_chapter_drafting(
                [str(fixture)], str(fixture.parent), str(fixture.parent), repo_root=None
            )
        )
        hook_rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
        no_hook = any(m.startswith("G4.cd.no_hook:") for m in res.get("must_fix", []))
        hit = attr["has_q"] or bool(attr["singles"] or attr["multi"]) or attr["has_ledger"]
        if attr["window_cjk"] < 30:
            assert not hook_rows and not no_hook  # 窗口质量不足→两口径都不判
        else:
            # spec #118 T2 起 hook_rows 含 WARN 行（三态）：行存在 ⟺ 非 no_hook；
            # 旧「PASS⟺三臂任一」口径已由 TestHookMirrorGateEquivalence 接管
            assert bool(hook_rows) != no_hook
            if hook_rows:
                assert hit


class TestSummarise:
    def test_counts_and_arm_canonical_fold(self) -> None:
        rows = [
            {
                "file": "chapter-1.md",
                "checks": [
                    {"id": "G4.cd.chapter_end_hook", "s": "PASS"},
                    {"id": "G4.cd.voice_density", "s": "FAIL"},
                ],
                "must_fix": ["G4.cd.voice_density:chapter-1.md:1<2"],
            },
            {
                "file": "chapter-2.md",
                "checks": [
                    {"id": "G4.cd.chapter_end_hook", "s": "PASS"},
                    {"id": "G4.cd.protagonist_presence", "s": "PASS"},
                ],
                "must_fix": ["G4.cd.no_hook:chapter-2.md:窗口未检出"],
            },
        ]
        s = summarise(rows)
        assert s["G4.cd.chapter_end_hook"]["PASS"] == 2
        # M2：mf arm 回射 canonical 后计 FAIL（no_hook→chapter_end_hook）
        assert s["G4.cd.chapter_end_hook"]["FAIL"] == 1
        assert ARM_TO_CANONICAL["G4.cd.no_hook"] == "G4.cd.chapter_end_hook"
        assert ARM_TO_CANONICAL["G4.cd.protagonist_absent"] == "G4.cd.protagonist_presence"

    def test_must_fix_without_fail_row_counted_once(self) -> None:
        rows = [
            {
                "file": "chapter-1.md",
                "checks": [{"id": "X", "s": "FAIL"}],
                "must_fix": ["X:c1:m"],
            }
        ]
        s = summarise(rows)
        assert s["X"]["FAIL"] == 1  # 同章同 id 去重

    def test_firing_rate(self) -> None:
        s = summarise(
            [
                {"file": "c1", "checks": [{"id": "X", "s": "PASS"}], "must_fix": []},
                {"file": "c2", "checks": [{"id": "X", "s": "FAIL"}], "must_fix": ["X:c2:m"]},
            ]
        )
        assert s["_firing"]["X"] == pytest.approx(0.5)


class TestCaliberSplit:
    def test_state_free_and_truth_sets_partition(self) -> None:
        assert "cd.prop_handoff" in TRUTH_DEPENDENT_IDS  # I1：canonical=check 行裸形
        assert "cd.balance_value_drift" in TRUTH_DEPENDENT_IDS
        assert "G4.cd.hook_type_rotation" in TRUTH_DEPENDENT_IDS  # M3：读 plans 历史
        assert "G4.cd.payoff_density" in STATE_FREE_IDS  # M3：与 registry 对齐
        assert not (STATE_FREE_IDS & TRUTH_DEPENDENT_IDS)


class TestTruthArmBackmap:
    """I1 口径双形统一：truth 族 mf 臂（G4. 前缀包装形）回射 check 行裸形 canonical。"""

    def test_balance_counter_arms_fold_to_bare_truth_rows(self) -> None:
        """扩展后 mf 形不再以独立行存活——回射裸形并命中 truth 集（过滤面生效）。"""
        rows = [
            {
                "file": "chapter-1.md",
                "checks": [],
                "must_fix": [
                    "G4.cd.balance_value_drift:chapter-1.md:8文≠9文",
                    "G4.cd.counter.base_mismatch:chapter-1.md:「钱」基值错",
                ],
            }
        ]
        s = summarise(rows)
        assert "cd.balance_value_drift" in s and "G4.cd.balance_value_drift" not in s
        assert "cd.counter.base_mismatch" in s and "G4.cd.counter.base_mismatch" not in s
        # 回射后参与口径判定：裸形命中 truth 集 → --state-free-only 剔除这两行
        assert "cd.balance_value_drift" in TRUTH_DEPENDENT_IDS
        assert "cd.counter.base_mismatch" in TRUTH_DEPENDENT_IDS

    def test_prop_handoff_canonical_is_check_row_bare_form(self) -> None:
        """Check 行发射裸形 cd.prop_handoff——WARN 降级行与 mf 行同归一行。"""
        assert ARM_TO_CANONICAL["G4.cd.prop_handoff"] == "cd.prop_handoff"
        assert ARM_TO_CANONICAL["G4.cd.balance_value_drift"] == "cd.balance_value_drift"


class TestDeterminism:
    def test_same_input_same_report(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        assert gpr.render_report(rd, "chapter-*.md") == gpr.render_report(rd, "chapter-*.md")

    def test_no_write_into_project_dir(self, tmp_path: Path) -> None:
        import tools.gate_power_replay as gpr

        rd = _mk_project(tmp_path, {"chapter-1.md": CH_WITH_HOOK})
        before = sorted(p.name for p in (rd / "chapters").iterdir())
        gpr.render_report(rd, "chapter-*.md")
        assert sorted(p.name for p in (rd / "chapters").iterdir()) == before


class TestHookMirrorGateEquivalence:
    """Spec #118 T2/I-6：镜像↔门等价钉两例（镜像漂移=验收数字失真面）."""

    def test_mirror_gate_equivalence_single_only(self) -> None:
        from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

        fp = Path("tests/fixtures/gate-power/chapter-1-hook-single-only.md").resolve()
        attr = hook_window_attribution(fp.read_text(encoding="utf-8"))
        res = json.loads(
            g4_chapter_drafting([str(fp)], str(fp.parent), str(fp.parent), repo_root=None)
        )
        rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
        assert attr["gate_class"] == "single_only" and attr["single_char_only"]
        # hook 面断言收窄到 no_hook mf（裁片 fixture 可有其他无关 mf——如字数）
        assert rows and rows[0]["s"] == "WARN"
        assert not any(m.startswith("G4.cd.no_hook:") for m in res.get("must_fix", []))

    def test_mirror_gate_equivalence_hard_arms(self) -> None:
        from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

        fp = Path("tests/fixtures/gate-power/chapter-1-fatigue-flooded.md").resolve()
        attr = hook_window_attribution(fp.read_text(encoding="utf-8"))
        res = json.loads(
            g4_chapter_drafting([str(fp)], str(fp.parent), str(fp.parent), repo_root=None)
        )
        rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
        assert attr["gate_class"] == "hard"
        assert attr["has_q"] or attr["multi"] or attr["has_ledger"]
        assert rows and rows[0]["s"] == "PASS"

    def test_mirror_gate_wordlists_pinned(self) -> None:
        """Spec #118 T2/audit-T3 I-1：镜像↔门词表逐字一致钉＋20 词无损拆分钉.

        等价钉（三态映射）对词级漂移零执法——monkeypatch 实证丢词/清空仍绿；
        本钉补词表面（pattern 逐字节相等）。
        """
        import tools.gate_power_replay as gpr
        from shenbi.gates.g4.chapter_drafting import (
            HOOK_MULTI_TENSION_RE,
            HOOK_SINGLE_TENSION,
        )

        multi_alts = set(HOOK_MULTI_TENSION_RE.pattern.strip("()").split("|"))
        mirror_all = set(gpr.HOOK_TENSION_RE.pattern.strip("()").split("|"))
        single = set(HOOK_SINGLE_TENSION)
        # 多字臂词表 = 退役 20 词表 − 单字集（无损拆分：无丢失、无重叠）
        assert multi_alts == mirror_all - single
        assert not multi_alts & single
        # 镜像单字集与门单字集逐字一致
        assert single == set(gpr.SINGLE_CHAR_TENSION)
