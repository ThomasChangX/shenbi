"""Generate per-platform plugin manifests from master.json.

Single source of truth: plugins/master.json
Output: 4 platform manifests (.claude-plugin/, .codex-plugin/,
.cursor-plugin/, .opencode/).
"""

import json
import sys
from pathlib import Path
from typing import Any, cast

import structlog

from shenbi.safe_write import safe_write

log = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
MASTER_PATH = REPO_ROOT / "plugins" / "master.json"

REQUIRED_FIELDS = {"name", "version", "description", "author", "skills", "platforms"}


def load_master() -> dict[str, Any]:
    """Load master.json with upfront structural validation."""
    if not MASTER_PATH.exists():
        raise FileNotFoundError(f"Master plugin file not found: {MASTER_PATH}")
    data = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{MASTER_PATH}: expected JSON object, got {type(data).__name__}")
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"{MASTER_PATH}: missing required fields: {sorted(missing)}")
    return cast(dict[str, Any], data)


def _common_header(master: dict[str, Any]) -> dict[str, Any]:
    """Fields shared by all JSON platforms, in canonical key order."""
    return {
        "name": master["name"],
        "version": master["version"],
        "description": master["description"],
        "author": master["author"],
    }


def gen_claude(master: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    out = _common_header(master)
    out["skills"] = master["skills"]
    return out


def gen_codex(master: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    fields = config.get("fields", {})
    out = _common_header(master)
    out["marketplace"] = fields["marketplace"]
    out["type"] = fields["type"]
    out["skills"] = master["skills"]
    return out


def gen_cursor(master: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    fields = config.get("fields", {})
    out = _common_header(master)
    out["pluginRoot"] = fields["pluginRoot"]
    out["skills"] = master["skills"]
    out["hooks"] = fields["hooks"]
    return out


def _js_string(s: str) -> str:
    """Escape a Python string for a JS single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def gen_opencode(master: dict[str, Any], config: dict[str, Any]) -> str:
    """OpenCode uses an ES module (export default) with single-quoted strings."""
    lines = [
        "export default {",
        f"  name: '{_js_string(str(master['name']))}',",
        f"  version: '{_js_string(str(master['version']))}',",
        f"  description: '{_js_string(str(master['description']))}',",
        f"  author: '{_js_string(str(master['author']))}',",
        "  skills: [",
    ]
    for skill in master["skills"]:
        lines.append(f"    '{_js_string(str(skill))}',")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("  ]")
    lines.append("};")
    return "\n".join(lines) + "\n"


GENERATORS: dict[str, tuple[str, Any]] = {
    "claude-code": ("json", gen_claude),
    "codex-cli": ("json", gen_codex),
    "cursor": ("json", gen_cursor),
    "opencode-js": ("js", gen_opencode),
}


def generate_all() -> int:
    """Generate all platform manifests from master.json."""
    master = load_master()

    for platform_name, config in master["platforms"].items():
        fmt = config["format"]
        output_path = REPO_ROOT / config["output"]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt not in GENERATORS:
            log.error("unknown_format", format=fmt, platform=platform_name)
            return 1

        output_type, generator = GENERATORS[fmt]
        content = generator(master, config)

        if output_type == "json":
            safe_write(output_path, json.dumps(content, indent=2, ensure_ascii=False) + "\n")
        else:
            safe_write(output_path, content)

        log.info("generated", path=str(output_path.relative_to(REPO_ROOT)))

    return 0


def main() -> int:
    return generate_all()


if __name__ == "__main__":
    sys.exit(main())
