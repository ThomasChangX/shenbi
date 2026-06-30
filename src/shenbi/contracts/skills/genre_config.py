"""Genre-config contract model (spec workflow A batch 1).

Encodes the 9 checkable rules from shenbi-genre-config SKILL.md
"可自动检查的计数规则" table as Pydantic validators.
Field set verified against real fixture (8 camelCase keys).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class GenreConfig(BaseModel):
    """Validated genre-config.json structure.

    Rules (from SKILL.md "可自动检查的计数规则"):
    1. approval.decision must be "approved" or "rejected"
    2. fatigueWords.禁用 count <= 50
    3. Every 禁用 word must have >= 1 replacement
    4. Every 慎用 word must have >= 1 replacement
    5. chapterTypes count must be 6-10
    6. auditDimensions count must be 5-10
    7. Every disabled auditDimension must have a customRules reason
    """

    model_config = {"extra": "ignore"}

    approval: dict[str, Any] = Field(default_factory=dict)
    audit_dimensions: dict[str, bool] = Field(default_factory=dict, alias="auditDimensions")
    chapter_types: dict[str, Any] = Field(default_factory=dict, alias="chapterTypes")
    custom_rules: list[dict[str, Any]] = Field(default_factory=list, alias="customRules")
    fatigue_words: dict[str, Any] = Field(default_factory=dict, alias="fatigueWords")
    pacing: dict[str, Any] = Field(default_factory=dict)
    updated: str = ""
    version: str = ""

    @model_validator(mode="after")
    def _approval_decision_valid(self) -> GenreConfig:
        decision = self.approval.get("decision", "")
        if decision and decision not in ("approved", "rejected"):
            raise ValueError(
                f"approval.decision must be 'approved' or 'rejected', got '{decision}'"
            )
        return self

    @model_validator(mode="after")
    def _fatigue_word_count(self) -> GenreConfig:
        banned = self.fatigue_words.get("禁用", [])
        if isinstance(banned, list) and len(banned) > 50:
            raise ValueError(f"禁用词数 {len(banned)} > 50")
        return self

    @model_validator(mode="after")
    def _banned_words_have_replacements(self) -> GenreConfig:
        banned = self.fatigue_words.get("禁用", [])
        replacements = self.fatigue_words.get("替换建议", {})
        if isinstance(banned, list) and isinstance(replacements, dict):
            for word in banned:
                opts = replacements.get(word, [])
                if not opts:
                    raise ValueError(f"禁用词 '{word}' 无替换建议")
        return self

    @model_validator(mode="after")
    def _cautioned_words_have_replacements(self) -> GenreConfig:
        cautioned = self.fatigue_words.get("慎用", [])
        replacements = self.fatigue_words.get("替换建议", {})
        if isinstance(cautioned, list) and isinstance(replacements, dict):
            for word in cautioned:
                opts = replacements.get(word, [])
                if not opts:
                    raise ValueError(f"慎用词 '{word}' 无替换建议")
        return self

    @model_validator(mode="after")
    def _chapter_type_count(self) -> GenreConfig:
        count = len(self.chapter_types)
        if not 6 <= count <= 10:
            raise ValueError(f"chapterTypes count {count} not in [6, 10]")
        return self

    @model_validator(mode="after")
    def _audit_dimension_count(self) -> GenreConfig:
        count = len(self.audit_dimensions)
        if not 5 <= count <= 10:
            raise ValueError(f"auditDimensions count {count} not in [5, 10]")
        return self

    @model_validator(mode="after")
    def _disabled_dimensions_have_rules(self) -> GenreConfig:
        disabled = [k for k, v in self.audit_dimensions.items() if v is False]
        if disabled and self.custom_rules:
            rule_texts = " ".join(
                str(r.get("description", "")) + str(r.get("id", "")) for r in self.custom_rules
            )
            for dim in disabled:
                if dim not in rule_texts:
                    raise ValueError(
                        f"auditDimension '{dim}' set to false but no customRules reason found"
                    )
        return self


Report = GenreConfig
