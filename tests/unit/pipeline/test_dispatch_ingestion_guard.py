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
from shenbi.pipeline.truth_io import _TABLE_HEADER_BOOTSTRAP

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


#: probe16 genesis step 9 (2026-10-02, adjudication /tmp/probe16-adjudication-001.md):
#: the foreshadowing-lifecycle skill's GENESIS-mode contract mandates the
#: whole-file registry form (## 总览 EXACT 8-col table — "无表头或自创列序 =
#: 整个钩子池对 truth 索引不可见，属不合格输出"), while the batch #10 guard
#: banned frontmatter/H1/## for hook_id targets unconditionally. Three-way
#: contradiction (guard × genesis contract × G4.fl.chapter_refs) — no output
#: shape could pass; the probe died at step 9. Root cause: the guard's
#: scaffold ban protects EXISTING hook content from replacement; a base with
#: zero hook rows/headings is a FIRST-WRITE target where the whole-file form
#: IS the sanctioned creation shape (probe15's registry landed exactly this
#: way before the guard existed).
_TEMPLATE_BASE = """---
type: truth
category: state
status: initialized
---

# 伏笔池

> 此文件由 state-settling 首次运行时填充实际数据。

（待填充：已埋设伏笔、埋设章节、计划回收章节、当前状态。）
"""

_WHOLE_FILE_FORM = """---
type: truth
category: state
status: initialized
---

# 伏笔池

> 创世模式产出：master hooks 全部初始化为 PLANTED。

## 总览
| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
| MH01（米缸底下的三份抄本） | PLANTED | 7 | 85（五卷） | ITEM | 0.5 | 14 | STAIRCASE |
| MH02（星火残梦与那句听不清的话） | PLANTED | 1 | 98（五卷） | INFORMATION | 0.6 | 14 | RISING |

## 详情

### MH01（米缸底下的三份抄本）

- hook_id: MH01
- type: ITEM
- plant_ch: 7

### MH02（星火残梦与那句听不清的话）

- hook_id: MH02
- type: INFORMATION
- plant_ch: 1
"""


class TestFirstWriteExemption:
    def test_genesis_first_write_allows_whole_file_form(self, tmp_path):
        """Empty-of-hooks base (worldbuilding template) + whole-file registry
        form = sanctioned creation, merged to exactly the contract shape:
        one frontmatter block, one H1, the 待填充 placeholder gone, the
        ## 总览 table with header + rows, detail sections present.
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "pending_hooks.md").write_text(_TEMPLATE_BASE, encoding="utf-8")
        out = _write_parsed_outputs(
            response=f"### FILE: truth/pending_hooks.md\n{_WHOLE_FILE_FORM}\n",
            output_paths=["truth/pending_hooks.md"],
            project_dir=project,
            skill="shenbi-foreshadowing-lifecycle",
        )
        assert "truth/pending_hooks.md" in out
        merged = (project / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert merged.count("---\ntype: truth") == 1, "frontmatter must not duplicate"
        assert merged.count("# 伏笔池") == 1, "H1 must not duplicate"
        assert "待填充" not in merged, "template placeholder must not survive creation"
        assert "## 总览" in merged
        assert "| MH01（米缸底下的三份抄本） |" in merged
        assert "| MH02（星火残梦与那句听不清的话） |" in merged
        assert "### MH01（米缸底下的三份抄本）" in merged
        assert "### MH02（星火残梦与那句听不清的话）" in merged

    def test_populated_hook_base_still_rejects_whole_file_form(self, tmp_path):
        """The exemption is bounded by base state: once hook rows/sections
        exist, the scaffold ban resumes (probe15 destruction vector).
        """
        project = _project(tmp_path)  # live base carries MH02 row + section
        with pytest.raises(IncrementShapeError):
            _write(project, _WHOLE_FILE_FORM)

    def test_chapter_key_targets_never_exempt(self, tmp_path):
        """FILLED chapter-keyed bases keep the unconditional guard — their
        writers' contracts are increment-only (probe15 destruction vector).

        (The SHELL-base half of the old contract was reversed by batch #15
        #44: see TestShellFirstWriteCreationRoute below.)
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "character_matrix.md").write_text(
            "# 角色矩阵\n## 交互总表\n| 角色A | 角色B | 关系 |\n| 苏烬 | 石九 | 盟友 |\n",
            encoding="utf-8",
        )
        with pytest.raises(IncrementShapeError):
            _write(
                project,
                "# 角色矩阵\n## 第 1 章状态增量\n### 苏烬\n- 位置: 赤锈谷\n",
                rel="staging/truth/character_matrix.md",
            )


#: probe20 regression (adjudication /tmp/probe20-adjudication-008.md): the
#: two diagnostics/failed-write-shenbi-state-settling-20261003T01*.md dumps.
#: After the escalation-reject staging wipe, truth bases were
#: status:initialized templates (quote + （待填充） sections, zero data) while
#: the re-dispatch feedback described a settled world. The model's whole-file
#: creation was its only rational output; the chapter-key guard rejected it
#: twice and the queue retried byte-identical. #44: a SHELL base sanctions the
#: creation form — routed as a base-replacing creation write, never fed into
#: the keyed-upsert merge.
_SHELL_STATE_BASE = """---
type: truth
category: state
status: initialized
generated_at: 2026-10-02T22:55:40Z
---

# 当前世界状态

> 此文件由 state-settling 首次运行时填充实际数据。

## 时间锚

（待填充）

## 势力态势

（待填充）
"""

_CREATION_FORM_STATE = """---
type: truth
category: state
status: filled
generated_at: 2026-10-03T01:31:49Z
---

# 当前世界状态

| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |
|------|------|--------|---------|---------|-----------|
| 第1章 | 三号采灵场井下 | 落潮夜 | 瞒报老刘 | 查点丁口 | 老刘之死 |
"""


class TestShellFirstWriteCreationRoute:
    def test_shell_base_creation_form_routed_as_creation_not_merge(self, tmp_path):
        """probe20's exact package must LAND: staged file equals the package
        verbatim (creation replaces the shell), live base untouched, and the
        result is indistinguishable from what a clean first-write produces.
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        out = _write_parsed_outputs(
            response=f"### FILE: staging/truth/current_state.md\n{_CREATION_FORM_STATE}\n",
            output_paths=["staging/truth/current_state.md"],
            project_dir=project,
            skill="shenbi-state-settling",
        )
        assert "staging/truth/current_state.md" in out
        staged = (project / "staging" / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert staged.rstrip("\n") == _CREATION_FORM_STATE.rstrip("\n"), (
            "creation route writes the package verbatim (parser normalizes the trailing newline)"
        )
        live = (project / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert live == _SHELL_STATE_BASE, "live base untouched until checkpoint commit"

    def test_live_path_shell_creation_also_routed(self, tmp_path):
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        out = _write_parsed_outputs(
            response=f"### FILE: truth/current_state.md\n{_CREATION_FORM_STATE}\n",
            output_paths=["truth/current_state.md"],
            project_dir=project,
            skill="shenbi-review-resonance",
        )
        assert "truth/current_state.md" in out
        live = (project / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert "| 第1章 |" in live

    def test_rows_only_on_shell_base_keeps_merge_path(self, tmp_path):
        """The exemption ADDS the creation route; rows-only increments on a
        shell base keep the existing keyed merge (probe18/19/20 first-settle
        behavior). On a MISSING base the staging create path bootstraps the
        contract header (#38); on a section-template shell the row simply
        lands at the merge position — the banner (#47) is what steers the
        model to the creation form for template shells.
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        # Missing base: bootstrap + row merge.
        row = "| 第1章 | 三号采灵场井下 | 落潮夜 | 瞒报老刘 | 查点丁口 | 老刘之死 |"
        out = _write(project, row, rel="staging/truth/current_state.md")
        assert "staging/truth/current_state.md" in out
        staged = (project / "staging" / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert row in staged
        assert _TABLE_HEADER_BOOTSTRAP["current_state.md"] in staged, (
            "staging-branch create path must bootstrap the contract header (#38)"
        )
        # Section-template shell: row lands through the keyed merge.
        project2 = tmp_path / "p2"
        (project2 / "truth").mkdir(parents=True)
        (project2 / "truth" / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        out2 = _write(project2, row, rel="staging/truth/current_state.md")
        assert "staging/truth/current_state.md" in out2
        staged2 = (project2 / "staging" / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert row in staged2
        assert "## 时间锚" in staged2, "template sections ride through the merge"

    def test_filled_live_base_blocks_staging_creation_defense(self, tmp_path):
        """#39-family defense: a shell STAGED base over a FILLED live base is
        an abnormal divergence — the creation route must refuse (it would
        silently replace live data at commit) and name both states.
        """
        project = tmp_path
        staged = project / "staging" / "truth"
        staged.mkdir(parents=True)
        (staged / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_CREATION_FORM_STATE, encoding="utf-8")
        with pytest.raises(IncrementShapeError) as ei:
            _write(project, _CREATION_FORM_STATE, rel="staging/truth/current_state.md")
        assert "FILLED" in str(ei.value)


class TestSplitPackageBaseStateFeedback:
    def test_rejection_names_per_target_base_states(self, tmp_path):
        """A multi-target skill whose package is rejected on a FILLED target
        must tell the model WHICH targets are shells (creation sanctioned)
        and which are filled (rows-only) — the probe20 deadlock was feedback
        describing a world the bases did not carry.
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_CREATION_FORM_STATE, encoding="utf-8")
        (project / "truth" / "particle_ledger.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        with pytest.raises(IncrementShapeError) as ei:
            _write(project, _CREATION_FORM_STATE, rel="staging/truth/current_state.md")
        msg = str(ei.value)
        assert "truth/current_state.md=FILLED" in msg
        assert "truth/particle_ledger.md=SHELL" in msg


class TestStagingBranchHeaderBootstrap:
    def test_resonance_trend_first_row_via_staging_gets_header(self, tmp_path):
        """#38: the staging merge branch must call ensure_table_header — the
        live write path bootstrapped (probe2) but staged first writes landed
        headerless until commit. resonance_trend belongs to the
        review-resonance contract (its dispatch is not staging-gated; the
        router's staging branch still applies when the path is staged).
        """
        project = tmp_path
        (project / "truth").mkdir(parents=True)
        row = "| 1 | L1 | L2 | L3 | L4 | L5 | 82 | 良好 | false |"
        out = _write_parsed_outputs(
            response=f"### FILE: staging/truth/resonance_trend.md\n{row}\n",
            output_paths=["staging/truth/resonance_trend.md"],
            project_dir=project,
            skill="shenbi-review-resonance",
        )
        assert "staging/truth/resonance_trend.md" in out
        staged = (project / "staging" / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
        assert _TABLE_HEADER_BOOTSTRAP["resonance_trend.md"] in staged


class TestBaseStateBanner:
    """#47: the dispatch prompt carries a machine-computed per-target base
    state banner — the model knows the sanctioned form BEFORE emitting, so
    feedback and guard can never again contradict each other.
    """

    def test_settle_prompt_carries_per_target_base_states(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        (project / "truth" / "particle_ledger.md").write_text(
            _CREATION_FORM_STATE, encoding="utf-8"
        )
        _sys_p, user_p, _paths, _ = _build_skill_prompt(
            "shenbi-state-settling",
            project,
            "settle chapter 1",
            chapter=1,
            uses_staging=True,
        )
        assert "基座态" in user_p
        assert "truth/current_state.md" in user_p and "SHELL" in user_p
        assert "truth/particle_ledger.md" in user_p and "FILLED" in user_p


class TestDispatchTraceReadsManifest:
    """#34: the DISPATCH trace persists WHAT the LLM saw per read — mode
    (full/fields), declared fields, filter match — so a post-mortem can
    tell a filtered-read miss from a full-text escape-hatch fallback.
    """

    def test_builder_returns_manifest_with_field_modes(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        project = tmp_path
        (project / "truth").mkdir(parents=True)
        (project / "truth" / "current_state.md").write_text(_SHELL_STATE_BASE, encoding="utf-8")
        _s, _u, _p, manifest = _build_skill_prompt(
            "shenbi-state-settling",
            project,
            "settle chapter 1",
            chapter=1,
            uses_staging=True,
        )
        by_path = {m["path"]: m for m in manifest}
        assert any("current_state" in p for p in by_path), "injected read must be manifested"
        cur = next(m for p, m in by_path.items() if "current_state" in p)
        assert cur["mode"] in ("full", "fields")
        if cur["mode"] == "fields":
            assert "fields" in cur and "matched_all" in cur
