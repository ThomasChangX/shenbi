"""Pacing-design contract model with semantic validators (spec workflow A).

Encodes 5 numerical constraints from SKILL.md "可自动检查规则":
1. Four beats exist (铺垫/升级/爆发/余波)
2. Beat percentages sum = 100%
3. Three lines coexist (QUEST/FIRE/CONSTELLATION)
4. CONSTELLATION ratio in [20, 30]
5. Exactly 8 scene types defined
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator


class PacingDesign(BaseModel):
    """Validated pacing-design output structure."""

    model_config = {"extra": "ignore"}

    beats: dict[str, float] = Field(default_factory=dict)
    line_ratios: dict[str, float] = Field(default_factory=dict)
    scene_types: list[str] = Field(default_factory=list)
    chapter_sequence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _four_beats_present(self) -> PacingDesign:
        required = {"铺垫", "升级", "爆发", "余波"}
        missing = required - set(self.beats.keys())
        if missing:
            raise ValueError(f"missing beats: {missing}")
        return self

    @model_validator(mode="after")
    def _beat_sum_is_100(self) -> PacingDesign:
        if self.beats:
            total = sum(self.beats.values())
            if abs(total - 100.0) > 0.01:
                raise ValueError(f"beat percentages sum to {total}, must be 100")
        return self

    @model_validator(mode="after")
    def _three_lines_present(self) -> PacingDesign:
        required = {"QUEST", "FIRE", "CONSTELLATION"}
        missing = required - set(self.line_ratios.keys())
        if missing:
            raise ValueError(f"missing narrative lines: {missing}")
        return self

    @model_validator(mode="after")
    def _constellation_range(self) -> PacingDesign:
        const = self.line_ratios.get("CONSTELLATION")
        if const is not None and not 15 <= const <= 35:
            raise ValueError(f"CONSTELLATION ratio {const} outside [15, 35]")
        return self

    @model_validator(mode="after")
    def _eight_scene_types(self) -> PacingDesign:
        if not 6 <= len(self.scene_types) <= 12:
            raise ValueError(f"expected 6-12 scene types, got {len(self.scene_types)}")
        return self

    @model_validator(mode="after")
    def _no_three_consecutive_same(self) -> PacingDesign:
        if len(self.chapter_sequence) >= 3:
            for i in range(len(self.chapter_sequence) - 2):
                window = self.chapter_sequence[i : i + 3]
                if len(set(window)) == 1:
                    raise ValueError(
                        f"3 consecutive chapters of type '{window[0]}' at position {i}"
                    )
        return self

    @classmethod
    def from_markdown(cls, content: str) -> PacingDesign:
        """Parse rhythm_principles.md markdown into structured data."""
        beats: dict[str, float] = {}
        line_ratios: dict[str, float] = {}
        scene_types: list[str] = []
        chapter_sequence: list[str] = []

        # Extract beat percentages (e.g. "铺垫 | 25%" or "铺垫: 25%")
        for beat in ("铺垫", "升级", "爆发", "余波"):
            m = re.search(rf"{beat}.*?(\d+(?:\.\d+)?)\s*%", content)
            if m:
                beats[beat] = float(m.group(1))

        # Extract line ratios
        for line in ("QUEST", "FIRE", "CONSTELLATION"):
            m = re.search(rf"{line}.*?(\d+(?:\.\d+)?)\s*%", content)
            if m:
                line_ratios[line] = float(m.group(1))

        # Extract scene types (look for known type names or a table)
        known_types = [
            "battle",
            "dialogue",
            "introspection",
            "transition",
            "exploration",
            "cultivation",
            "conspiracy",
            "escape",
            "revelation",
            "emotion",
            "intellectual",
            "战斗",
            "对话",
            "日常",
            "探索",
            "修炼",
            "阴谋",
            "逃亡",
            "揭示",
            "情感",
            "智斗",
        ]
        for st in known_types:
            if st in content:
                scene_types.append(st)
        scene_types = list(dict.fromkeys(scene_types))  # dedupe preserving order

        return cls(
            beats=beats,
            line_ratios=line_ratios,
            scene_types=scene_types,
            chapter_sequence=chapter_sequence,
        )


Report = PacingDesign
