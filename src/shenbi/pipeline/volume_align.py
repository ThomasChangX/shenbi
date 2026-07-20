"""Volume alignment checker -- deterministic pre-planning step (ADD-1)."""

import re
from pathlib import Path


def extract_chapter_node(volume_map_path: Path, chapter: int) -> dict[str, str] | None:
    """Extract the chapter node from volume_map.md."""
    if not volume_map_path.exists():
        return None

    text = volume_map_path.read_text(encoding="utf-8")
    pattern = rf"##\s+Chapter\s+{chapter}[:\s]*(.+?)(?=\n##\s+Chapter|\Z)"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        # Try alternate pattern: ### Chapter N
        pattern = rf"###\s+Chapter\s+{chapter}[:\s]*(.+?)(?=\n###\s+Chapter|\Z)"
        match = re.search(pattern, text, re.DOTALL)

    if match:
        return {"desc": match.group(1).strip()}
    return None


def extract_key_terms(text: str) -> list[str]:
    """Extract key terms from text (Chinese 2-6 chars + English 3+ chars)."""
    # Chinese character sequences (2-6 chars)
    cn_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    # English words (3+ chars), excluding common stop words
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "chapter",
        "volume",
        "node",
        "role",
        "content",
        "character",
    }
    eng_words = re.findall(r"[a-zA-Z]{3,}", text)
    eng_terms = [w for w in eng_words if w.lower() not in stop_words]

    return list(set(cn_terms + eng_terms))


def check_volume_alignment(project_dir: Path, chapter: int, plan_text: str) -> list[str]:
    """Verify chapter plan aligns with volume_map. Non-blocking -- WARN only."""
    vm_path = project_dir / "outline" / "volume_map.md"
    node = extract_chapter_node(vm_path, chapter)

    issues: list[str] = []
    if not node:
        return issues

    key_terms = extract_key_terms(node["desc"])
    if not key_terms:
        return issues

    match_count = sum(1 for t in key_terms if t in plan_text)
    match_rate = match_count / len(key_terms) if key_terms else 0

    if match_rate < 0.3:
        issues.append(
            f"Volume alignment WARNING: only {match_rate:.0%} "
            f"key terms from volume_map present in plan"
        )

    return issues
