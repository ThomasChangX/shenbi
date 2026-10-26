# ---------------------------------------------------------------------------
# regen v3 F7 (2026-10-27): POV derivation must strip dialogue spans
# ---------------------------------------------------------------------------
def test_pov_derivation_ignores_dialogue_first_person() -> None:
    """A dialogue-heavy third-person chapter must derive 他, not mixed: the
    density count includes 「」 spans today, so a child character's 我-heavy
    dialogue flipped a 他-narrated chapter to mixed and failed the POV
    invariant (regen v3 ch4: 那珂's lines).
    """
    from shenbi.gates.g4.cross_chapter import derive_pov_mode

    text = "\n".join(
        [
            "他蹲在井台对面补鞋底。",
            "「我娘哼，我也会哼。」那珂说，「我娘叫我阿禾。」",
            "他问她：「后头有词吗？」",
            "「有。我娘说，灯要人点。」",
            "他把鞋底翻了个面。他没答上来。他看着她走远。",
        ]
    )
    assert derive_pov_mode(text) == "他"
