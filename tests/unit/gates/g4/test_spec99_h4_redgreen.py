"""Spec #99 T2：H4 假阳性死锁红绿测试（束7 blob 物化回放）。

断言全部写**期望行为**——束7 现场（live ch47/48 块系空格形标题、重派 staged
为生产合并快照）下这些断言在严格正则（`state_settling.py:322` 不容数字两侧
空格）现行实现上为红；Task 3（④ 单源化容错正则+bundle 孪生豁免+写径归一）
落地后转绿。证据链=spec T2(a) 改前红/改后绿。

fixtures/spec99/ = 束7 dispatch 工件复制件（G0.9 真实产物；SHA256SUMS 裸形
清单，`cd tests/fixtures/spec99 && shasum -c SHA256SUMS` 全 OK）：
- 00264-dispatch.json（a1 重派）+ 其 user_prompt/response blob
- live = 00264 prompt 中 `truth/character_matrix.md` 的 untrusted-source 段
  （matrix_scoped 提取面：含空格形 `## 第 47 章状态增量`/`## 第 48 章状态增量`；
  清理提取面注记行+html 实体后作为 live 基座）
- staged = 00264 response 增量经**生产写路径本体**（`_route_append_dedup_write`）
  对 live 合并的快照——G4 实际所见的 staging 形态（dispatch_helper
  `_route_append_dedup_write` docstring：merged against live, merged snapshot
  written to staging）
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pytest

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec99"

_MATRIX_KEY = "角色A,角色B"  # skills/shenbi-state-settling SKILL.md writes 声明


def _dispatch(n: str) -> dict[str, Any]:
    return json.loads((FIX / f"{n}-dispatch.json").read_text(encoding="utf-8"))


def _blob(ref: str) -> str:
    h = ref.replace("sha256:", "")
    return (FIX / f"{h}.txt").read_text(encoding="utf-8")


def _live_matrix() -> str:
    """束7 现场 live 基座（00264 prompt 的 matrix_scoped 提取段，清注记+实体）。"""
    d = _dispatch("00264")
    prompt = _blob(d["user_prompt_blob"])
    m = re.search(
        r'<untrusted-source path="truth/character_matrix\.md">(.*?)</untrusted-source>',
        prompt,
        re.S,
    )
    assert m, "fixture 回归：00264 prompt blob 中 character_matrix 段缺失"
    live = re.sub(r"^&gt; \[extractor:[^\n]*$", "", m.group(1), flags=re.M)
    return html.unescape(live)


def _staged_increment() -> str:
    """束7 a1 重派增量（00264 response manifest 的 matrix 输出，含改写形自陈）。"""
    d = _dispatch("00264")
    manifest = json.loads(_blob(d["response_blob"]))
    files = manifest.get("files") or []
    entry = next(
        (f for f in files if isinstance(f, dict) and "character_matrix" in f.get("path", "")),
        None,
    )
    assert entry is not None, "fixture 回归：00264 response manifest 无 character_matrix 条目"
    return entry["content"]


def _materialize(tmp_path: Path, *, twin_rewrite: bool = False, volume_map: bool = False) -> Path:
    """物化束7 现场：live 基座 + 生产写路径合并的 staging 快照 + sidecar。

    twin_rewrite=True 时增量追加对 live 孪生 48 块的**真实**改写（块体内实际
    bullet 行加后缀——probe31 keyed-upsert 语义面）；volume_map=True 时补
    outline/volume_map.md（span 覆盖 47-48，供 bundle 孪生豁免信号源）。
    """
    from shenbi.pipeline.dispatch_helper import _route_append_dedup_write

    live = _live_matrix()
    inc = _staged_increment()
    if twin_rewrite:
        m = re.search(r"(## 第 48 章状态增量\n)(.*?)(?=\n## |\Z)", live, re.S)
        assert m, "fixture 回归：live 48 块缺失"
        bullet = next(
            (l for l in m.group(2).split("\n") if l.strip().startswith("- ")),
            None,
        )
        assert bullet is not None, "fixture 回归：live 48 块体内无 bullet 行可改写"
        twin_block = m.group(1) + m.group(2).replace(bullet, bullet + "（孪生章合法更新）", 1)
        inc = f"{inc}\n{twin_block}"

    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "character_matrix.md").write_text(live, encoding="utf-8")
    _route_append_dedup_write(
        tmp_path, "staging/truth/character_matrix.md", inc, key_field=_MATRIX_KEY
    )
    (tmp_path / "staging" / "truth" / "state-settling-decisions.json").write_text(
        json.dumps({"chapter": 47}), encoding="utf-8"
    )
    if volume_map:
        (tmp_path / "outline").mkdir(exist_ok=True)
        (tmp_path / "outline" / "volume_map.md").write_text(
            "## 第二卷：利息与图章（第 37–86 章）\n#### KR1: 渡 3 债务征服\n",
            encoding="utf-8",
        )
    return tmp_path / "staging" / "truth" / "character_matrix.md"


def _gate_must_fix(tmp_path: Path, pf: Path) -> list[str]:
    from shenbi.gates.g4.state_settling import g4_state_settling

    out = json.loads(g4_state_settling([str(pf)], rd=str(tmp_path), project_dir=str(tmp_path)))
    return out.get("must_fix", [])


def _short_reason(mf: list[str]) -> str:
    return "; ".join(m[-90:] for m in mf if "content_dropped" in m)


SELF_LINE = "- 自陈: 「我描的。描了十一年，就记下这么一家。」"


@pytest.mark.unit
def test_spaced_own_block_exempt():
    """④前红：严格正则不容空格→47 own-block 未被剥离，自陈行残留基底质量比对。"""
    from shenbi.gates.g4.state_settling import _strip_increment_section

    stripped = _strip_increment_section(_live_matrix(), 47)
    assert SELF_LINE not in stripped, "空格形 own-block 未豁免（H4）：期望④落地后自陈行随 47 块剥离"


@pytest.mark.unit
def test_materialized_chain_no_drop(tmp_path: Path):
    """整链回放：束7 现场 staged（生产合并快照）/live 过 gate——期望无
    content_dropped（own-block 合法替换）。④前红（现行豁免失效→自陈短句行
    被判丢，即束7 a2 反馈 content_dropped:1行 现场）。
    """
    pf = _materialize(tmp_path)
    mf = _gate_must_fix(tmp_path, pf)
    assert not any("content_dropped" in m for m in mf), (
        f"H4 假阳性现场复现：own-block 合法替换被误判——{_short_reason(mf)}"
    )


@pytest.mark.unit
def test_write_path_increment_heading_normalized():
    """写径归一：重派标题形（无空格）与 live 形（空格）不一致时增量族替换仍
    命中（非 None 且含替换文本），不得失配退化为 EOF 追加重复块。④前红。
    """
    from shenbi.pipeline.truth_io import _replace_section

    live = _live_matrix()
    section = "## 第47章状态增量\n- 测试: 增量族标题形差异下的替换\n"
    merged = _replace_section(live, section)
    assert merged is not None, "增量族标题形失配→None→EOF 追加重复块隐患"
    assert "- 测试: 增量族标题形差异下的替换" in merged


@pytest.mark.unit
def test_bundle_twin_block_exempt(tmp_path: Path):
    """Bundle 孪生豁免（C1）：sidecar=47+volume_map 覆盖 47-48 时，staged 对
    live 48 块的合法更新不得判 content_dropped。④前红（现行无孪生豁免——
    且空格形下 47 豁免亦失效，双面红）。
    """
    pf = _materialize(tmp_path, twin_rewrite=True, volume_map=True)
    mf = _gate_must_fix(tmp_path, pf)
    assert not any("content_dropped" in m for m in mf), (
        f"bundle 孪生块合法更新被误判——{_short_reason(mf)}"
    )
