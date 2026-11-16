"""spec #106 T6: offline replay tool (AC2/AC3 evidence)."""

from pathlib import Path

from tools.resonance_floor_replay import replay_floors

VOL1_SCORED = {
    1: 78,
    2: 74,
    3: 76,
    4: 78,
    5: 79,
    7: 79,
    9: 80,
    11: 79,
    12: 81,
    13: 79,
    14: 77,
    15: 80,
    16: 77,
    17: 79,
    18: 81,
    19: 86,
}


def _seed(tmp_path: Path) -> None:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True)
    rows = [f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |" for c, s in VOL1_SCORED.items()]
    header = (
        "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
        " | overall | confidence | human_overridden |"
    )
    sep = (
        "|---------|--------------|---------|-----------|---------|---------"
        "|---------|-----------|------------------|"
    )
    (truth / "resonance_trend.md").write_text(
        "\n".join([header, sep, *rows]) + "\n", encoding="utf-8"
    )


def test_replay_ignites_ch14_ch16_and_respects_cold_start(tmp_path):
    _seed(tmp_path)
    rows = replay_floors(tmp_path)
    by_ch = {int(r["chapter"]): r for r in rows}  # type: ignore[arg-type]
    ignited = [ch for ch, r in by_ch.items() if r["would_route"]]
    assert ignited == [14, 16]
    assert all(not by_ch[ch]["would_route"] for ch in by_ch if ch <= 11)  # 冷启动边界
    assert by_ch[14]["floor"] == 78.0 and by_ch[16]["floor"] == 77.75
    assert (
        by_ch[17]["floor"] == 77.0 and by_ch[17]["would_route"] is False
    )  # 众数 79 章不命中（AC3c）
    assert by_ch[19]["would_route"] is False  # 高分带不命中


def test_diff_route_writes_nothing(tmp_path, monkeypatch):
    """audit-T6 C1 red-green anchor: --diff-route must leave the project
    directory byte-identical (the wired side runs in a throwaway sandbox —
    _route_revision_after_resonance writes pre-rev backups, which must never
    land in the real project).
    """
    import hashlib

    _seed(tmp_path)
    audits = tmp_path / "audits"
    audits.mkdir()
    (audits / "chapter-14-resonance.md").write_text(
        "```verdict\n判定: 通过\n共振: 77/100\n```\n", encoding="utf-8"
    )
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    (ch_dir / "chapter-14.md").write_text("# 第十四章\n\n正文。", encoding="utf-8")

    def _tree_digest(root: Path) -> dict[str, str]:
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    before = _tree_digest(tmp_path)
    from tools.resonance_floor_replay import main as replay_main

    assert replay_main([str(tmp_path), "--diff-route"]) == 0
    assert _tree_digest(tmp_path) == before  # 零新增/零改动（含 pre-rev 备份不落盘）
