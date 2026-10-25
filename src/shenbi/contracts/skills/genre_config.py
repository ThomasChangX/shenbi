"""Genre-config contract model (spec workflow A batch 1).

Encodes the 9 checkable rules from shenbi-genre-config SKILL.md
"可自动检查的计数规则" table as Pydantic validators.
Field set verified against real fixture (8 camelCase keys).
"""

from __future__ import annotations

from typing import Any

from typing import get_args

from shenbi.contracts.enums import ApprovalDecision
from shenbi.contracts.ownership import GENRE_KEYS
from pydantic import BaseModel, Field, field_validator, model_validator

# Single-source keyset authority (F214): 8 required = GENRE_KEYS minus the
# optional tropeInventory / chapter_word blocks (chapter_word baseline is
# writer-mandated since 3bfc4a3b; pre-baseline real outputs lack it).
# spec #72: primary_platform is optional too — legacy/pre-#72 configs and
# historical fixtures carry no platform declaration; consumers fall back.
_OPTIONAL_TOP_KEYS = frozenset(
    {"tropeInventory", "chapter_word", "primary_platform", "market_params"}
)
_REQUIRED_TOP_KEYS = tuple(sorted(k for k in GENRE_KEYS if k not in _OPTIONAL_TOP_KEYS))


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
    8. approval.decision is required (no approval = invalid config)
    9. Top-level keyset = 8 required keys + optional tropeInventory/chapter_word/primary_platform (spec #72)/market_params (spec #73)
    """

    model_config = {"extra": "ignore"}

    approval: dict[str, Any] = Field(default_factory=dict)
    audit_dimensions: dict[str, bool] = Field(default_factory=dict, alias="auditDimensions")
    chapter_types: dict[str, Any] = Field(default_factory=dict, alias="chapterTypes")
    custom_rules: list[dict[str, Any]] = Field(default_factory=list, alias="customRules")
    fatigue_words: dict[str, Any] = Field(default_factory=dict, alias="fatigueWords")
    pacing: dict[str, Any] = Field(default_factory=dict)
    market_params: dict[str, dict[str, int]] = Field(default_factory=dict)
    # spec #73: optional market-parameter block — see _market_params_structure
    primary_platform: str = ""  # spec #72: qidian|fanqie; "" = undeclared (legacy)
    updated: str = ""
    version: str = ""

    @field_validator("primary_platform")
    @classmethod
    def _primary_platform_enum(cls, v: str) -> str:
        if v and v not in {"qidian", "fanqie"}:
            raise ValueError(f"primary_platform must be qidian|fanqie, got '{v}'")
        return v

    @field_validator("market_params")
    @classmethod
    def _market_params_structure(cls, v: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
        """Spec #73 三态：块缺席 PASS（可选）；块在场须三必键齐且值域合法。

        - payoff_density: window∈[1,10], min>=1（接线 #78 频次窗）
        - emotion_band: window∈[1,3], min>=1（接线 #78 下限）
        - hook_grading: max_consecutive_micro∈[1,3]（接线 #78 轮换门）
        - voice_density_min / meme_quota / quote_type_quota: 数值域 #76 定档
          （voice_density_min∈[0,5] / meme_quota∈[1,20] /
          quote_type_quota∈[0,10] 可选——缺省代入在 lint 消费端）
        """
        if not v:
            return v
        required = ("payoff_density", "emotion_band", "hook_grading")
        for key in required:
            if key not in v:
                raise ValueError(f"market_params: missing sub-key '{key}'")
        pd = v["payoff_density"]
        if not 1 <= pd.get("window", -1) <= 10 or pd.get("min", 0) < 1:
            raise ValueError(f"market_params.payoff_density: window∈[1,10]/min>=1, got {pd}")
        eb = v["emotion_band"]
        if not 1 <= eb.get("window", -1) <= 3 or eb.get("min", 0) < 1:
            raise ValueError(f"market_params.emotion_band: window∈[1,3]/min>=1, got {eb}")
        hg = v["hook_grading"]
        if not 1 <= hg.get("max_consecutive_micro", -1) <= 3:
            raise ValueError(f"market_params.hook_grading: max_consecutive_micro∈[1,3], got {hg}")
        # spec #76 数值域定档（#73 遗留债务清偿）：
        # - voice_density_min.min_per_chapter ∈ [0,5]
        # - meme_quota.per_volume ∈ [1,20]
        # - quote_type_quota.burning_per_volume ∈ [0,10]（可选键；缺省代入
        #   属 lint 消费端——validator 保持无副作用）
        vdm = v.get("voice_density_min")
        if vdm is not None and not 0 <= vdm.get("min_per_chapter", -1) <= 5:
            raise ValueError(f"market_params.voice_density_min: min_per_chapter∈[0,5], got {vdm}")
        mq = v.get("meme_quota")
        if mq is not None and not 1 <= mq.get("per_volume", -1) <= 20:
            raise ValueError(f"market_params.meme_quota: per_volume∈[1,20], got {mq}")
        qtq = v.get("quote_type_quota")
        if qtq is not None and not 0 <= qtq.get("burning_per_volume", -1) <= 10:
            raise ValueError(
                f"market_params.quote_type_quota: burning_per_volume∈[0,10], got {qtq}"
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def _top_level_keyset(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for key in data:
            if key not in GENRE_KEYS:
                raise ValueError(
                    f"unknown top-level key '{key}' (allowed: 8 required + optional tropeInventory/chapter_word/primary_platform/market_params)"
                )
        missing = [k for k in _REQUIRED_TOP_KEYS if k not in data]
        if missing:
            raise ValueError(f"missing required top-level keys: {missing}")
        return data

    @model_validator(mode="after")
    def _approval_decision_valid(self) -> GenreConfig:
        decision = self.approval.get("decision", "")
        if decision and decision not in get_args(ApprovalDecision):
            raise ValueError(
                f"approval.decision must be one of {get_args(ApprovalDecision)}, got '{decision}'"
            )
        if not self.approval or not self.approval.get("decision"):
            raise ValueError("approval.decision is required (rule 8)")
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
        if disabled:  # F216: empty customRules must not skip the check
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
