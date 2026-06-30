"""共享工作树 FS 快照 + diff（spec 支柱四 Tier B 写侧拓扑）。

真实顺序执行拓扑：dispatch 前 snapshot(pre) → dispatch → snapshot(post) → audit diff。
快照按技能声明的写入面（writes/updates，含 parametric）展开为实际文件取内容，
避免 round_dir 内 scores/progress 噪音。markdown truth 用 records.parser 做记录级 diff；
JSON 用顶层键 field diff。
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

from shenbi.contracts.ownership import FileChange
from shenbi.records.parser import parse_records


@functools.lru_cache(maxsize=1)
def parametric_globs() -> dict[str, str]:
    """truth-files.yaml patterns: parametric to glob (single source, spec 5.3).

    Franklin Important: not cached (lru_cache removed) — truth-files.yaml can
    change across rounds in a long-running process, and stale globs cause
    false negatives (newly-truth files unwatched).
    """
    from shenbi.contract import load_registry

    reg = load_registry()
    return {str(p["parametric"]): str(p["glob"]) for p in reg.get("patterns", [])}


def _expand_patterns(root: Path, patterns: list[str]) -> list[str]:
    """把声明写入模式（exact/parametric/glob）展开为 root 下实际存在的相对路径。"""
    globs = parametric_globs()
    actual: set[str] = set()
    for pat in patterns:
        glob_pat = globs.get(pat)
        if glob_pat:
            for f in Path(root).glob(glob_pat):
                if f.is_file():
                    actual.add(f.relative_to(root).as_posix())
        elif "*" in pat:
            for f in Path(root).glob(pat):
                if f.is_file():
                    actual.add(f.relative_to(root).as_posix())
        else:
            actual.add(pat)  # exact（不存在则 snapshot 读为 None）
    return sorted(actual)


def snapshot_tree(root: Path, watch_patterns: list[str]) -> dict[str, str | None]:
    """对 root 下 watch_patterns 展开后的实际文件取 UTF-8 内容；不存在 → None。

    每次（pre/post）都重新展开，使 dispatch 新写的文件出现在 post 而不在 pre → added。
    """
    out: dict[str, str | None] = {}
    for rel in _expand_patterns(root, watch_patterns):
        p = Path(root) / rel
        out[rel] = p.read_text(encoding="utf-8") if p.exists() else None
    return out


def _changed_top_keys(pre: str, post: str) -> tuple[str, ...]:
    try:
        a, b = json.loads(pre), json.loads(post)
    except (json.JSONDecodeError, TypeError):
        return ()
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return ()
    keys: set[str] = set()
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            keys.add(k)
    return tuple(sorted(keys))


def _diff_records(
    pre: list[dict[str, Any]], post: list[dict[str, Any]]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, frozenset[str]], ...]]:
    pre_by = {str(r.get("id")): r for r in pre}
    post_by = {str(r.get("id")): r for r in post}
    new_ids = tuple(i for i in post_by if i not in pre_by)
    del_ids = tuple(i for i in pre_by if i not in post_by)
    mod: list[tuple[str, frozenset[str]]] = []
    for rid, rec in post_by.items():
        if rid in pre_by:
            changed = frozenset(
                k for k in set(pre_by[rid]) | set(rec) if pre_by[rid].get(k) != rec.get(k)
            )
            if changed:
                mod.append((rid, changed))
    return new_ids, del_ids, tuple(mod)


def compute_file_change(relpath: str, pre: str | None, post: str | None) -> FileChange:
    """由 pre/post 内容算 FileChange（按文件格式选粒度）。"""
    if pre is None and post is not None:
        return FileChange(relpath=relpath, status="added")
    if pre is not None and post is None:
        return FileChange(relpath=relpath, status="deleted")
    if pre == post:
        return FileChange(relpath=relpath, status="modified")
    if relpath.endswith(".json") and pre is not None and post is not None:
        return FileChange(
            relpath=relpath, status="modified", changed_top_keys=_changed_top_keys(pre, post)
        )
    if relpath.endswith(".md") and pre is not None and post is not None:
        new_ids, del_ids, mod = _diff_records(parse_records(pre), parse_records(post))
        return FileChange(
            relpath=relpath,
            status="modified",
            new_record_ids=new_ids,
            deleted_record_ids=del_ids,
            modified_record_keys=mod,
        )
    return FileChange(relpath=relpath, status="modified")
