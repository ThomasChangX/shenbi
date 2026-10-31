"""spec #79 T2: regen-accept aggregator — tri-state exit + three new checks."""

from __future__ import annotations

import json
from pathlib import Path

from tools.regen_accept import (
    _norm_records,
    check_blind_recognition,
    check_emotion_proxy,
    run_accept,
)


def _mk_g4_rec(status: str = "PASS", timestamp: str = "2026-01-01T00:00:00Z") -> dict[str, object]:
    return {
        "gate": "G4",
        "timestamp": timestamp,
        "result": {"gate": "g", "status": status, "timestamp": timestamp, "checks": []},
    }


def _mk_project(tmp_path: Path, *, chapters: int = 2) -> Path:
    p = tmp_path / "proj"
    p.mkdir()
    (p / "chapters").mkdir()
    (p / "plans").mkdir()
    for n in range(1, chapters + 1):
        (p / "chapters" / f"chapter-{n}.md").write_text(f"# 第{n}章\n\n正文", encoding="utf-8")
    (p / "pipeline-manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "gates": {
                    "chapter_loop": {
                        "1": {
                            "pipeline-scene-split": {
                                "G4": _mk_g4_rec(),
                                "G4.xc": _mk_g4_rec(),
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return p


def test_empty_baseline_is_data_error(tmp_path: Path) -> None:
    """Post-quarantine ch0 baseline: no manifest/chapters -> exit 2."""
    p = tmp_path / "empty"
    p.mkdir()
    assert run_accept(p, through=5) == 2
    # manifest present but zero chapters is also a data error
    (p / "pipeline-manifest.json").write_text("{}", encoding="utf-8")
    assert run_accept(p, through=5) == 2


def test_fail_rows_exit_one(tmp_path: Path) -> None:
    p = _mk_project(tmp_path)
    # through=2 but ch2 has no G4.xc record -> criterion 1 FAIL -> exit 1
    assert run_accept(p, through=2) == 1


def test_manifest_dict_list_normalization_latest_wins() -> None:
    """Dict single-run and list multi-run forms reduce latest-by-timestamp."""
    manifest = {
        "gates": {
            "chapter_loop": {
                "1": {
                    "shenbi-chapter-drafting": {
                        # list form: old PASS then newer FAIL — latest wins
                        "G4": [
                            _mk_g4_rec("PASS", "2026-01-01T00:00:00Z"),
                            _mk_g4_rec("FAIL", "2026-01-02T00:00:00Z"),
                        ]
                    },
                    "shenbi-chapter-planning": {
                        # dict form: single record
                        "G4": _mk_g4_rec("PASS", "2026-01-03T00:00:00Z"),
                    },
                }
            }
        }
    }
    recs = _norm_records(manifest)
    assert recs[(1, "shenbi-chapter-drafting", "G4")]["result"]["status"] == "FAIL"
    assert recs[(1, "shenbi-chapter-planning", "G4")]["result"]["status"] == "PASS"


def test_emotion_proxy_cold_streak_and_hot_short_circuit(tmp_path: Path) -> None:
    p = tmp_path / "proj"
    (p / "plans").mkdir(parents=True)
    tones = ["喜", "平", "平", "平", "悲", "惧", "怒", "平", "喜"]
    for n, tone in enumerate(tones, start=1):
        golden = "燃" if tone == "悲" else "静"
        (p / "plans" / f"chapter-{n}-plan.md").write_text(
            f"# 计划\n\n- emotion_tone: {tone}\n- 本章金句位: {golden}｜白描｜段末\n",
            encoding="utf-8",
        )
    # ch5 悲 short-circuited by 燃: worst cold streak = ch2-4 平 (3) <= 3 -> PASS
    v = check_emotion_proxy(p, through=9)
    assert v.status == "PASS", v.detail
    # drop the 燃 from ch5 -> ch2-6 平平平悲惧 = 5 consecutive cold > 3 -> FAIL
    ch5 = p / "plans" / "chapter-5-plan.md"
    ch5.write_text("# 计划\n\n- emotion_tone: 悲\n- 本章金句位: 静｜白描｜段末\n", encoding="utf-8")
    v = check_emotion_proxy(p, through=9)
    assert v.status == "FAIL", v.detail


def _mk_card(cdir: Path, slug: str, name: str, catchphrases: list[str]) -> None:
    import yaml

    front = yaml.safe_dump(
        {"name": name, "voice_profile": {"catchphrases": catchphrases}},
        allow_unicode=True,
        sort_keys=False,
    )
    (cdir / f"{slug}.md").write_text(f"---\n{front}---\n# {name}\n", encoding="utf-8")


def test_blind_recognition_threshold_and_sample_floor(tmp_path: Path) -> None:
    p = tmp_path / "proj"
    (p / "characters" / "major").mkdir(parents=True)
    (p / "chapters").mkdir(parents=True)
    _mk_card(p / "characters" / "major", "a", "甲", ["甲的口头禅"])
    _mk_card(p / "characters" / "major", "b", "乙", ["乙的口头禅"])
    _mk_card(p / "characters" / "major", "c", "丙", ["丙的口头禅"])
    _mk_card(p / "characters" / "major", "d", "丁", ["丁的口头禅"])
    # only 4 cards with markers -> FAIL on card floor (<5)
    (p / "chapters" / "chapter-1.md").write_text(
        "甲的口头禅。甲说：「甲的口头禅」\n\n乙说：「乙的口头禅」", encoding="utf-8"
    )
    v = check_blind_recognition(p, through=1)
    assert v.status == "FAIL" and "5" not in v.detail.split("（")[0], v.detail
    assert "角色卡" in v.detail or "对白样本" in v.detail

    _mk_card(p / "characters" / "major", "e", "戊", ["戊的口头禅"])
    # 5 cards, but only 4 roles sampled in chapter text -> sample floor FAIL
    v = check_blind_recognition(p, through=1)
    assert v.status == "FAIL" and "对白样本" in v.detail, v.detail

    # five roles each with an argmax-correct quote line -> PASS
    (p / "chapters" / "chapter-1.md").write_text(
        "甲的口头禅。甲说：「甲的口头禅」\n\n"
        "乙的口头禅。乙说：「乙的口头禅」\n\n"
        "丙的口头禅。丙说：「丙的口头禅」\n\n"
        "丁的口头禅。丁说：「丁的口头禅」\n\n"
        "戊的口头禅。戊说：「戊的口头禅」",
        encoding="utf-8",
    )
    v = check_blind_recognition(p, through=1)
    assert v.status == "PASS", v.detail

    # spec #83 T7 语义修正：零命中段=不可归属，不入分母（原「计错」使 4/5 对
    # 任何 token 族结构性不可达）——甲保持 1/1，不因无 token 对白受罚
    (p / "chapters" / "chapter-2.md").write_text("甲说：「随便讲点什么。」", encoding="utf-8")
    v = check_blind_recognition(p, through=2)
    assert v.status == "PASS", v.detail

    # 误归属仍计错：甲的对白携带乙的 token（token 不含卡名——含名会成双名段跳过）
    (p / "chapters" / "chapter-3.md").write_text(
        "甲说：「北风卷地，再说一遍北风卷地。」", encoding="utf-8"
    )
    # 乙卡追加第二 token（保既有样本可归属——五卡仍全带标记者）
    (p / "characters" / "major" / "b.md").write_text(
        "---\nname: 乙\nvoice_profile:\n  catchphrases: ['乙的口头禅', '北风卷地']\n---\n",
        encoding="utf-8",
    )
    v = check_blind_recognition(p, through=3)
    assert v.status == "FAIL" and "甲=1/2" in v.detail, v.detail


def test_emotion_proxy_wordlist_external_counts_cold(tmp_path: Path) -> None:
    """Spec #82 (r3): wordlist-external tones (安/暖/快) count as cold —
    the ch5/12/15 escape hatch is closed by the shared predicate.
    """
    p = tmp_path / "proj"
    (p / "plans").mkdir(parents=True)
    tones = ["悲", "安", "暖", "快", "悲"]  # 安/暖/快 wordlist-external → cold
    for n, tone in enumerate(tones, start=1):
        (p / "plans" / f"chapter-{n}-plan.md").write_text(
            f"# 计划\n\n- emotion_tone: {tone}\n- 本章金句位: 静｜白描｜段末\n",
            encoding="utf-8",
        )
    # 燃 no longer rescues wordlist-external tones (branch ① priority):
    # 5 consecutive cold > 3 → FAIL (the old code saw 安/暖/快 as warm → PASS)
    v = check_emotion_proxy(p, through=5)
    assert v.status == "FAIL", v.detail


def test_emotion_proxy_sliding_window_ignores_early_cold(tmp_path: Path) -> None:
    """Spec #82 (r6): the check slides over the last 10 chapters — a cold
    run entirely outside the window must not fail the through=late check.
    """
    p = tmp_path / "proj"
    (p / "plans").mkdir(parents=True)
    for n in range(1, 21):
        tone = "悲" if n <= 6 else "喜"  # cold run ch1-6 outside the ch11-20 window
        (p / "plans" / f"chapter-{n}-plan.md").write_text(
            f"# 计划\n\n- emotion_tone: {tone}\n- 本章金句位: 静｜白描｜段末\n",
            encoding="utf-8",
        )
    v = check_emotion_proxy(p, through=20)
    assert v.status == "PASS", v.detail
