"""Tests for enriched G4 retry feedback."""

from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES, _enrich_g4_feedback


def test_enrich_adds_format_example_for_known_check():
    """Known check IDs get format example appended."""
    failures = ["G4.rr.verdict:chapter-1-resonance.md:no_valid_verdict"]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "判定: 通过" in result
    assert "G4.rr.verdict" in result


def test_enrich_adds_detail_table_example():
    """G4.rr.detail_table gets the scoring table format example."""
    failures = ["G4.rr.detail_table:chapter-2-resonance.md:missing_['裁判理由']"]
    result = _enrich_g4_feedback(failures)

    assert "评分明细表格式" in result
    assert "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |" in result


def test_enrich_adds_evidence_example():
    """G4.rr.evidence gets the file:line reference example."""
    failures = ["G4.rr.evidence:chapter-3-resonance.md:no_file_line_ref"]
    result = _enrich_g4_feedback(failures)

    assert "chapter-N.md L45-52" in result or "文件和行号" in result


def test_enrich_handles_unknown_checks():
    """Unknown check IDs get generic feedback without format examples."""
    failures = ["G4.unknown_check:file.md:some_issue"]
    result = _enrich_g4_feedback(failures)

    assert "G4.unknown_check" in result
    # Should not crash or add examples for unknown checks


def test_enrich_handles_multiple_failures():
    """Multiple failures all get documented with their examples."""
    failures = [
        "G4.rr.verdict:ch1-res.md:no_valid_verdict",
        "G4.rr.evidence:ch1-res.md:no_file_line_ref",
    ]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "文件和行号" in result or "chapter-N.md" in result


def test_enrich_word_count_has_actionable_example():
    """G4.word_count (probe7 ch1: three attempts at 1767<2000 all ran on the
    generic fallback) gets concrete expansion guidance: the total-chars
    口径 and in-scene expansion direction, not format boilerplate.
    """
    failures = ["G4.word_count:chapters/chapter-1.md:1767<2000"]
    result = _enrich_g4_feedback(failures)

    assert GENERIC_FALLBACK not in result
    assert "字符" in result
    # expansion direction: enrich existing scenes, not padding/new scenes
    assert "扩" in result


def test_enrich_no_hook_has_window_caliber():
    """G4.cd.no_hook (probe13 ch1: three attempts all ran on the generic
    fallback) gets the merged-window caliber and a rewrite direction, not
    format boilerplate.
    """
    failures = ["G4.cd.no_hook:chapters/chapter-1.md:96字合并窗口未检出疑问句/张力词"]
    result = _enrich_g4_feedback(failures)

    assert GENERIC_FALLBACK not in result
    assert "章尾" in result
    assert "张力词" in result


# ---------------------------------------------------------------------------
# G4.dec schema-shape failures (probe4/5: missing/extra_forbidden dominated
# the genre-config must_fix list and only received the generic fallback line)
# ---------------------------------------------------------------------------

GENERIC_FALLBACK = "(请重新生成此检查的输出以达到标准格式)"


def test_enrich_dec_missing_has_complete_legal_example():
    """G4.dec.missing gets a complete legal selections/adjustments example,
    not the generic fallback.
    """
    failures = [
        "G4.dec.missing:genre-config-decisions.json:selections.0.selected: Field required",
        "G4.dec.missing:genre-config-decisions.json:adjustments.0.issue_id: Field required",
    ]
    result = _enrich_g4_feedback(failures)

    assert GENERIC_FALLBACK not in result
    # Complete legal entry shape (not just an enum list)
    assert '"target":' in result
    assert '"selected": [' in result
    assert '"basis":' in result
    assert '"issue_id":' in result
    assert '"handling":' in result


def test_enrich_dec_extra_forbidden_has_closed_set_example():
    """G4.dec.extra_forbidden names the closed field sets so the model can
    drop invented keys.
    """
    failures = [
        "G4.dec.extra_forbidden:x-decisions.json:selections.0.id: Extra inputs are not permitted",
    ]
    result = _enrich_g4_feedback(failures)

    assert GENERIC_FALLBACK not in result
    assert "只允许" in result or "仅允许" in result or "闭集" in result
    # The example must itself be closed-set clean (no invented keys inside it)


def test_enrich_dec_literal_error_has_complete_legal_example():
    """G4.dec.literal_error ships a complete legal entry with real enum
    values filled in, not just the enum list.
    """
    failures = [
        "G4.dec.literal_error:x-decisions.json:selections.0.basis: Input should be "
        "'adjacent_to_target_chapter', 'arc_relevance', 'volume_scope' or 'manual_override'",
    ]
    result = _enrich_g4_feedback(failures)

    assert '"basis": "arc_relevance"' in result or '"basis": "volume_scope"' in result


def test_dec_example_json_is_schema_valid():
    """The embedded G4.dec example must parse and validate against the
    shenbi-decisions-v1 pydantic schema (keeps feedback honest as the
    schema evolves).
    """
    import json

    from shenbi.contracts.schemas.decisions import DecisionsDoc

    for check_id in ("G4.dec.missing", "G4.dec.extra_forbidden", "G4.dec.literal_error"):
        text = G4_FORMAT_EXAMPLES[check_id]
        # Extract the fenced/inline JSON object (first '{' ... matching brace)
        start = text.index("{")
        depth = 0
        end = start
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        payload = json.loads(text[start:end])
        DecisionsDoc.model_validate(payload)
