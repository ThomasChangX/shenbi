"""Pacing-design contract model with semantic validators (spec workflow A).

Encodes 5 numerical constraints from SKILL.md "可自动检查规则":
1. Four beats exist (铺垫/升级/爆发/余波)
2. Beat percentages sum = 100%
3. Three lines coexist (QUEST/FIRE/CONSTELLATION)
4. CONSTELLATION ratio in [15, 40] (hard-fail band; per-volume authoritative bands live in SKILL 按卷型表)
5. 6-12 scene types defined
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
        if const is not None and not 15 <= const <= 40:
            raise ValueError(f"CONSTELLATION ratio {const} outside [15, 40]")
        return self

    @model_validator(mode="after")
    def _scene_type_count(self) -> PacingDesign:
        if not 6 <= len(self.scene_types) <= 12:
            raise ValueError(f"expected 6-12 scene types, got {len(self.scene_types)}")
        return self

    @classmethod
    def from_markdown(cls, content: str) -> PacingDesign:
        """Parse rhythm_principles.md markdown into structured data.

        Parses the SKILL.md EXACT template's own table shapes FIRST — the
        legacy tight ``铺垫 30%`` shape only as fallback. The tight-only
        parser could not read the canonical four-beat rows (``| 铺垫
        (buildup) | 30% |`` — the parenthetical English breaks adjacency)
        nor the header-indexed three-line table, so a letter-perfect
        template output failed G4 (canary escalation #2, 2026-09-28).
        """
        beats: dict[str, float] = {}
        line_ratios: dict[str, float] = {}
        scene_types: list[str] = []

        rows = re.findall(r"^\|.*\|$", content, re.MULTILINE)

        # Beats — canonical four-beat table row: | 铺垫 (buildup) | 30% | …
        # (parenthetical English optional). Tight shape stays as fallback
        # for summary-line style outputs.
        for beat in ("铺垫", "升级", "爆发", "余波"):
            m = re.search(
                rf"^\|\s*{beat}\s*(?:\([^)]*\))?\s*\|\s*(\d+(?:\.\d+)?)\s*%",
                content,
                re.MULTILINE,
            ) or re.search(rf"{beat}\s*[|:：]?\s*(\d+(?:\.\d+)?)\s*%", content)
            if m:
                beats[beat] = float(m.group(1))

        # Line ratios — the contract's EXACT-columns table
        # | 卷 | QUEST% | FIRE% | CONSTELLATION% | 检查结果 |:
        # names live in the header, values in data cells. First data row
        # wins (presence + [15,40] band validators; per-volume banding is
        # a listed SKILL rule the model does not encode yet).
        line_idx: dict[str, int] = {}
        header_at: int | None = None
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if "QUEST%" in cells and "CONSTELLATION%" in cells:
                line_idx = {
                    "QUEST": cells.index("QUEST%"),
                    "FIRE": cells.index("FIRE%"),
                    "CONSTELLATION": cells.index("CONSTELLATION%"),
                }
                header_at = i
                break
        if header_at is not None:
            for row in rows[header_at + 1 :]:
                cells = [c.strip() for c in row.strip("|").split("|")]
                if len(cells) <= max(line_idx.values()):
                    continue
                vals: dict[str, float] = {}
                complete = True
                for name, idx in line_idx.items():
                    m = re.match(r"(\d+(?:\.\d+)?)\s*%", cells[idx])
                    if not m:
                        complete = False
                        break
                    vals[name] = float(m.group(1))
                if complete:
                    for name, v in vals.items():
                        line_ratios.setdefault(name, v)
        for line in ("QUEST", "FIRE", "CONSTELLATION"):
            if line not in line_ratios:
                m = re.search(rf"{line}\s*[|:：]?\s*(\d+(?:\.\d+)?)\s*%", content)
                if m:
                    line_ratios[line] = float(m.group(1))

        # Scene types — count data rows of the | 编号 | 类型 | … | table
        # (type names are genre-adaptive, so a fixed vocabulary undercounts;
        # strip parenthetical English from the stored name). The scan stops
        # at the next table's header row so later numeric-first tables
        # (卷节奏分配) are not miscounted as scene types.
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] == "编号" and cells[1] == "类型":
                for data_row in rows[i + 1 :]:
                    cells2 = [c.strip() for c in data_row.strip("|").split("|")]
                    if re.fullmatch(r"[-: ]+", cells2[0] or ""):
                        continue  # separator row inside/after this table
                    if not re.fullmatch(r"\d+", cells2[0] or ""):
                        break  # next table's header (non-numeric first cell)
                    if len(cells2) >= 2:
                        name = re.sub(r"（[^）]*）|\([^)]*\)", "", cells2[1]).strip() or cells2[1]
                        if name:
                            scene_types.append(name)
                break
        if not scene_types:
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
        )


Report = PacingDesign
