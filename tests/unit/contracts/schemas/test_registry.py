# tests/unit/contracts/schemas/test_registry.py
from pathlib import Path

import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.registry import (
    RegistryConcept,
    RegistryGlob,
    RegistryKind,
    RegistryPattern,
    TruthFilesRegistry,
)

REAL_YAML = Path(__file__).resolve().parents[4] / "docs" / "framework" / "truth-files.yaml"


def _load_real():
    import yaml

    return yaml.safe_load(REAL_YAML.read_text(encoding="utf-8"))


class TestRealYamlLoads:
    def test_loads_real_truth_files_yaml(self):
        reg = TruthFilesRegistry.model_validate(_load_real())
        assert len(reg.concepts) > 50  # 61 concepts

    def test_real_yaml_has_patterns_and_globs(self):
        reg = TruthFilesRegistry.model_validate(_load_real())
        assert len(reg.patterns) > 0
        assert len(reg.globs) > 0

    def test_real_yaml_default_version(self):
        # real file has NO version key; model defaults to 1 and accepts it.
        reg = TruthFilesRegistry.model_validate(_load_real())
        assert reg.version == 1


class TestConceptDefaults:
    def test_producer_default_skill(self):
        c = RegistryConcept(name="x.md", kind="truth")
        assert c.producer == "skill"

    def test_producer_override(self):
        c = RegistryConcept(name="x.md", kind="truth", producer="pipeline")
        assert c.producer == "pipeline"

    def test_kind_literal_all_16(self):
        # all 16 real kinds must be accepted
        kinds = [
            "benchmark",
            "chapter",
            "character",
            "config",
            "context",
            "decisions",
            "import",
            "outline",
            "plan",
            "reference",
            "report",
            "short",
            "snapshot",
            "style",
            "truth",
            "world",
        ]
        for k in kinds:
            RegistryConcept.model_validate({"name": f"x-{k}.md", "kind": k})  # all accepted

    def test_kind_invalid_rejected(self):
        with pytest.raises(ValidationError):
            RegistryConcept.model_validate({"name": "x.md", "kind": "bogus"})

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            RegistryConcept.model_validate({"name": "x.md", "kind": "truth", "extra": "nope"})


class TestRegistryValidation:
    def test_empty_concepts_rejected(self):
        with pytest.raises(ValidationError):
            TruthFilesRegistry.model_validate({"concepts": []})

    def test_unsupported_version_rejected(self):
        with pytest.raises(ValidationError):
            TruthFilesRegistry.model_validate(
                {"version": 2, "concepts": [{"name": "x.md", "kind": "truth"}]}
            )

    def test_minimal_valid(self):
        reg = TruthFilesRegistry.model_validate({"concepts": [{"name": "x.md", "kind": "truth"}]})
        assert reg.concepts[0].name == "x.md"
        assert reg.patterns == []
        assert reg.globs == []

    def test_extra_top_level_rejected(self):
        with pytest.raises(ValidationError):
            TruthFilesRegistry.model_validate(
                {"concepts": [{"name": "x.md", "kind": "truth"}], "bogus": 1}
            )


class TestPatternGlob:
    def test_pattern_extra_rejected(self):
        with pytest.raises(ValidationError):
            RegistryPattern.model_validate({"parametric": "x", "glob": "y", "extra": 1})

    def test_glob_extra_rejected(self):
        with pytest.raises(ValidationError):
            RegistryGlob.model_validate({"pattern": "x", "extra": 1})


def test_registry_kind_is_literal_alias():
    # RegistryKind must be a typing alias usable for downstream annotations.
    import typing

    assert typing.get_args(RegistryKind)  # non-empty args
