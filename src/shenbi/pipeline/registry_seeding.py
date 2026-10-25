"""Spec #75 registry seeding: characters/ -> truth/name_registry.md bootstrap.

Deterministic one-shot volume-level initial value; per-chapter rolling
updates belong to state-settling.
CLI: python -m shenbi.pipeline.registry_seeding <project_dir>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.cli_utils import echo
from shenbi.safe_write import safe_write


def seed_name_registry(project_dir: Path) -> Path:
    """Seed the volume-level name_registry initial value from characters/.

    Registers the invariant name rows (登记名 + pronoun whitelist + 禁用名).
    The 登记名 prefers an explicit ``登记名:`` field on the protagonist card
    (the #74 项 4 layout); the bootstrap value holds until that lands. An
    existing registry is never overwritten — rolling updates belong to
    state-settling.
    """
    registered = "临"  # bootstrap (#74 项 4 lands the card field)
    proto = project_dir / "characters" / "protagonist.md"
    if proto.is_file():
        m = re.search(
            r"^\s*登记名[：:]\s*(\S{1,4})", proto.read_text(encoding="utf-8"), re.MULTILINE
        )
        if m:
            registered = m.group(1)
    lines = [
        "# 主角称谓字典（name_registry）",
        "",
        "| 类别 | 名 | 备注 |",
        "|---|---|---|",
        f"| 登记名 | {registered} | 全卷一致（#74 项 4） |",
        "| 代词白名单 | 他 | 叙述代词 |",
        "| 禁用名 | 灯 | 保留给末世女主（#74 项 3 化名纪律） |",
    ]
    target = project_dir / "truth" / "name_registry.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        echo("name_registry 已存在——跳过（卷层 overwrite 归 settling）", err=True)
        return target
    safe_write(target, "\n".join(lines).encode("utf-8"))
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed spec-#75 truth registries.")
    parser.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    target = seed_name_registry(args.project_dir)
    echo(f"seeded: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
