r"""Hooks increment contract: single-source stable-field set (phase3 esc#1).

novel-xinghuo-phase3 ch1 settle escalated after three G4.ss.hooks_structure
fails:
the model rewrote ``- plant_chapter`` bullets on existing hooks (and 65
content lines were reported dropped, 59 of them phantom cross-section
mismatches). Root cause layer 1: the dispatch prompt's stable-line ban
list, the G4 remediation text, and the IncrementShapeError sanctioned text
each enumerated a DIFFERENT subset of the stable fields — none contained
``plant_chapter``, which is exactly where the model trespassed.

These tests pin the contract to one shared constant and to the texts the
model actually sees.
"""

from __future__ import annotations

from shenbi.gates.g4.state_settling import _check_hooks_structure
from shenbi.pipeline.truth_io import HOOKS_STABLE_FIELDS, HOOKS_VOLATILE_FIELDS

_LIVE = """---
type: truth
category: state
---

# 伏笔池

## 详情

### MH05（余孽册的三本册子）

- hook_id: MH05
- type: ITEM
- plant_chapter: 2
- resolve_chapter: 102
- depends_on: 无

### MH06（圣冕的旧账与血授之说）

- hook_id: MH06
- type: MYSTERY
- plant_chapter: 2
- resolve_chapter: 96
- depends_on: MH05
"""

# The ONLY legitimate mutation: MH05 plant_chapter rewritten 2 -> 1.
_STAGED_ONE_REAL_LOSS = _LIVE.replace(
    "- hook_id: MH05\n- type: ITEM\n- plant_chapter: 2",
    "- hook_id: MH05\n- type: ITEM\n- plant_chapter: 1",
)


class TestSharedStableSet:
    def test_covers_every_field_the_merge_must_preserve(self):
        # phase3 esc#1: plant_chapter/resolve_chapter/subtlety were missing
        # from the prompt-side ban list; dimension/cultivation_interval/
        # max_distance/escalation_curve were missing from EVERY list.
        for field in (
            "type",
            "dimension",
            "plant_chapter",
            "resolve_chapter",
            "subtlety",
            "cultivation_interval",
            "max_distance",
            "escalation_curve",
            "trigger_condition",
            "resolve_condition",
            "depends_on",
        ):
            assert field in HOOKS_STABLE_FIELDS, field

    def test_stable_and_volatile_are_disjoint(self):
        assert not set(HOOKS_STABLE_FIELDS) & set(HOOKS_VOLATILE_FIELDS)


class TestRemediationTextNamesFullStableSet:
    def test_failure_message_spells_out_every_stable_field(self, tmp_path):
        live = tmp_path / "truth" / "pending_hooks.md"
        staged = tmp_path / "staging" / "truth" / "pending_hooks.md"
        live.parent.mkdir(parents=True)
        staged.parent.mkdir(parents=True)
        live.write_text(_LIVE, encoding="utf-8")
        staged.write_text(_STAGED_ONE_REAL_LOSS, encoding="utf-8")
        findings = _check_hooks_structure(staged)
        joined = "\n".join(findings)
        for field in ("plant_chapter", "resolve_chapter", "subtlety"):
            assert field in joined, f"remediation must name the stable field: {field}"


class TestNoCrossSectionCascade:
    def test_same_value_line_in_later_hook_no_phantom_drops(self, tmp_path):
        """Live MH05 and MH06 both carry ``- plant_chapter: 2``.

        Old matcher: live MH05's rewritten plant_chapter line matched
        STAGED MH06's same-value line, the pointer jumped a section ahead,
        and every subsequent un-matched line cascaded into the count —
        reporting lines that were never touched (phase3 esc#1: 6 real
        violations inflated to 65). Section-scoped matching must report
        exactly the one real loss.
        """
        live = tmp_path / "truth" / "pending_hooks.md"
        staged = tmp_path / "staging" / "truth" / "pending_hooks.md"
        live.parent.mkdir(parents=True)
        staged.parent.mkdir(parents=True)
        live.write_text(_LIVE, encoding="utf-8")
        staged.write_text(_STAGED_ONE_REAL_LOSS, encoding="utf-8")
        findings = _check_hooks_structure(staged)
        joined = "\n".join(findings)
        assert "content_dropped:1行" in joined, findings
        assert "- plant_chapter: 2" in joined  # the real loss is the sample
        assert "- resolve_chapter: 102" not in joined  # untouched, must not appear
        assert "- hook_id: MH06" not in joined  # untouched, must not appear
