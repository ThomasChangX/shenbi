"""REGISTRY 自动发现 + 过渡期 truth-files.yaml bootstrap。C1 修复：单一注册表。

v2 C1: truth-files.yaml 真实结构是 concepts/globs/patterns（非 files），
每条 concept 是 {name, kind}。bootstrap 读 concepts。
"""

from __future__ import annotations

import importlib
import pkgutil

import yaml
from pydantic import BaseModel

from shenbi.gates.shared import PROJECT, SKILLS

_TRUTH_FILES_YAML = PROJECT / "docs" / "framework" / "truth-files.yaml"


def bootstrap_registry() -> dict[str, str]:
    """Read truth-files.yaml concepts for unmigrated skill file vocabulary.

    Reserved for the transition-period integration (later pillars will wire
    contract.py's 4 tools to call this). Not called by production code yet.
    v2 C1: 真实结构 concepts:[{name,kind}]，非 files:[{path,kind}]。
    返回 {name: kind}。
    """
    if not _TRUTH_FILES_YAML.exists():
        return {}
    data = yaml.safe_load(_TRUTH_FILES_YAML.read_text(encoding="utf-8")) or {}
    out: dict[str, str] = {}
    for entry in data.get("concepts", []):  # v2: concepts 非 files
        name = entry.get("name")  # v2: name 非 path
        if name:
            out[name] = entry.get("kind", "truth")
    return out


def _discover_skill_models() -> dict[str, type[BaseModel]]:
    """自动发现 contracts/skills/*.py 导出的 Report 类。

    约定：每模块有 Report(BaseModel) 子类。
    """
    from shenbi.contracts import skills as skills_pkg  # 局部 import 避免循环

    out: dict[str, type[BaseModel]] = {}
    for mod_info in pkgutil.iter_modules(skills_pkg.__path__):
        if mod_info.ispkg or mod_info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"shenbi.contracts.skills.{mod_info.name}")
        report_cls = getattr(mod, "Report", None)
        if isinstance(report_cls, type) and issubclass(report_cls, BaseModel):
            out[f"shenbi-{mod_info.name.replace('_', '-')}"] = report_cls
    return out


REGISTRY: dict[str, type[BaseModel]] = _discover_skill_models()


def load_skill_contract(skill: str) -> type[BaseModel] | None:
    """已迁移返回 Pydantic 模型；未迁移返回 None（contract.py 仍负责）。"""
    return REGISTRY.get(skill)


def known_skill_names() -> set[str]:
    """Authoritative skill-name set — single source for gate registries (judgement 5).

    Scans skills/ for directories with a SKILL.md. Owned by the contract layer
    so G0 coverage, G4 checker sets, and the contract registry all derive from
    one place.
    """
    if not SKILLS.exists():
        return set()
    return {d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists()}
