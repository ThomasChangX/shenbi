# Spec #81 observability-net P1 Implementation Plan

**Status**: Done (PR #258 · 2026-10-29 — 9/9 tasks, audits converged, just check green pre-merge and post-merge)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P1 observability layer — dispatch archiving with content-addressed blobs, additive trace fields (loop_id/feedback_ref/archive_path) + RETRY event, escape-hatch fail-fast, and the observe_report skeleton — per spec `docs/superpowers/specs/2026-10-28-spec81-observability-net.md` (rev5).

**Architecture:** A new `src/shenbi/observability/` package (archive.py + escape.py) owns all writes; `_build_skill_prompt` gains raw-disk snapshot capture and the escape-hatch counter (shared API/IDE path); `_dispatch_via_api` gains state threading and per-return-path archive calls; `chapter_loop` gains RETRY emission and the post-dispatch `escape_hatch_drift` check; `tools/observe_report.py` reads only. Gates stay pure (writers = dispatch path, readers = loop/checkpoint).

**Tech Stack:** Python 3.11+ / pathlib / structlog / pydantic TraceWriter / pytest tmp_path. No new dependencies.

## Global Constraints

- **复杂度**：本 plan 全部 task 为 **infra**（触及 `src/shenbi/pipeline/`、`src/shenbi/observability/`、`src/shenbi/trace/`）——协调者亲自实现，不分派 implementer 子 agent；每 task 后 fresh-context 审查产 `audit-T<N>.md`。
- **F947 离线纪律**：全部验收离线可执行（tmp_path 结构语料 + monkeypatch 假流式客户端）；SDD 全程禁真实 dispatch。结构记录（archive/trace/ledger 形态）按 AGENTS.md 允许 tmp_path/inline 构造（非 skill 产物 fixture 冒充）。
- **G3.4**：P1 无评分场景（无 LLM 产物生成），无 G3.4 子 agent 需求——在此显式声明。
- **门检纯度**：`src/shenbi/observability/` 写侧仅由派发路径调用；`escape_hatch_drift` 读侧在 chapter_loop（读文件不写）。
- **框架纯度**：无 `print()`（ruff T20 零豁免）；structlog；pathlib；状态字面量不新增裸串（本 plan 不新增 gate 状态词——`escape_hatch_drift` 是 check id 不是状态字面量；RETRY 是 trace action 自由串，`action: str` 无枚举约束，`contracts/enums.py` 不动）。
- **fail-safe 纪律**：归档失败绝不阻断派发（同 `_persist_failed_write_output` docstring :3370-3371）。
- **环境同构**：一切验证走 `uv run pytest` / `just`。
- **spec 引用的行号锚点**（实施时以 grep 复核为准，偏移不作为豁免理由）：`_dispatch_via_api` :3399；reads 循环磁盘读入 :852；`filter_to_fields` 调用 :1100；`_strip_meta_for_non_drafting` :1119；`raw_inputs[key] = content` :1120；builder 返回 :1491；trace docstring :3125-3126；主步派发 chapter_loop :4019；`dispatch_skill` :4066（API 路丢 state :4121-4129）。

## File Structure

```
src/shenbi/observability/            # 新包——全部观测写侧
├── __init__.py                      # re-export
├── archive.py                       # blob store / seq / quota / stats / write_dispatch_archive
└── escape.py                        # escape-hatch 计数器 + drift 检查（读侧纯函数）
src/shenbi/pipeline/dispatch_helper.py   # 修改：builder 5 元组 + raw 捕获 + 计数器调用 + 归档接线 + state 透传
src/shenbi/pipeline/chapter_loop.py      # 修改：RETRY 事件 + escape_hatch_drift 检查 + 波 state 透传
src/shenbi/pipeline/parallel_dispatch.py # 修改：_dispatch_with_retry 传 state
tools/observe_report.py                  # 新建：四表 + 覆盖行 + WARN 汇总（只读）
justfile                                 # 修改：observe-report target
tests/unit/observability/test_archive.py            # T1
tests/unit/observability/test_escape.py             # T3/T7
tests/unit/pipeline/test_dispatch_snapshot.py       # T2
tests/unit/pipeline/test_dispatch_archive_wiring.py # T4/T5
tests/unit/pipeline/test_chapter_loop_retry_event.py # T6
tests/unit/tools/test_observe_report.py             # T8
```

---

### Task 1: observability archive 模块（blob store / seq / quota / stats / 落档）

**Files:**
- Create: `src/shenbi/observability/__init__.py`, `src/shenbi/observability/archive.py`
- Test: `tests/unit/observability/test_archive.py`

**Interfaces:**
- Consumes: `shenbi.pipeline.truth_io.truth_file_flock(path)`（跨进程 flock，:123）；`shenbi.safe_write.safe_write`（**注意：模块在 `src/shenbi/safe_write.py`，非 `pipeline/` 下**——dispatch_helper.py:86 同源导入）。
- Produces（后续 task 依赖的精确签名）:
  - `archive_enabled() -> bool`（`SHENBI_ARCHIVE_DISPATCH != "0"`）
  - `quota_bytes() -> int`（env `SHENBI_ARCHIVE_QUOTA_BYTES`，默认 1GiB）
  - `sha256_of(text: str) -> str`（返回 `"sha256:<hex>"`）
  - `put_blob(project_dir: Path, content: str) -> str`（**无条件返回 digest**——配额跳过时 bump stats + WARN + 只跳内容写，哈希照进档（spec §1「档与哈希照写」：熔断降级=可验证不可复现，digest 不能丢）；同内容幂等；写盘 temp+rename 防撕裂 blob——内容寻址文件名即完整性声明，撕裂=静默腐蚀解引用）
  - `next_seq(project_dir: Path) -> int`（flock 下 max+1，跨重启续号；与档写共用一个 flock scope 时撞名结构性不可能，stats 键防御性保留）
  - `bump_stats(project_dir: Path, key: str) -> None`（key ∈ {archive_write_failed, archive_quota_skip, archive_seq_collision}；文件 `observability/archive-stats.json`）
  - `@dataclass ArchiveFrame`（skill/chapter/attempt/model/system_prompt/user_prompt/reads_manifest/raw_reads/skill_contract_sha256/loop_id/feedback_ref）
  - `write_dispatch_archive(project_dir: Path, frame: ArchiveFrame, *, finish_reason: str | None, response_text: str | None, usage: dict[str, Any] | None) -> Path | None`
  - `skill_contract_sha(skill: str) -> str | None`（SKILL.md 内容 sha256；找不到返回 None。**注：spec §1 措辞「git blob SHA」，此处取内容 sha256 为溯源等价简化（drift 检测同强），digest 格式与全库一致——记 spec-deviations**）

- [ ] **Step 1: 写失败测试**（tests/unit/observability/test_archive.py）

```python
"""Spec #81 §1 archive layer unit tests (offline, tmp_path structural corpora)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.observability import archive as ar


class TestBlobStore:
    def test_put_blob_content_addressed_idempotent(self, tmp_path: Path):
        d1 = ar.put_blob(tmp_path, "同内容")
        d2 = ar.put_blob(tmp_path, "同内容")
        assert d1 == d2 and d1.startswith("sha256:")
        blob = tmp_path / "observability" / "blobs" / d1.split(":", 1)[1]
        assert blob.read_text(encoding="utf-8") == "同内容"

    def test_quota_breaker_skips_blob_keeps_hash_and_counts(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_QUOTA_BYTES", "200")  # KB 级实测形态（spec §7.5 离线）
        d1 = ar.put_blob(tmp_path, "x" * 150)  # 150B 落盘
        d2 = ar.put_blob(tmp_path, "y" * 400)  # 150+400 > 200 → 跳内容写
        assert d2.startswith("sha256:")  # 哈希照返（spec §1）
        blob2 = tmp_path / "observability" / "blobs" / d2.split(":", 1)[1]
        assert not blob2.exists()  # 内容确实没写
        assert (tmp_path / "observability" / "blobs" / d1.split(":", 1)[1]).exists()
        stats = json.loads((tmp_path / "observability" / "archive-stats.json").read_text())
        assert stats["archive_quota_skip"] == 1

    def test_archive_disabled_env(self, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
        assert ar.archive_enabled() is False


class TestSeq:
    def test_next_seq_monotonic_across_files(self, tmp_path: Path):
        d = tmp_path / "observability" / "dispatches"
        d.mkdir(parents=True)
        (d / "00003-x-ch001-a1.json").write_text("{}", encoding="utf-8")
        assert ar.next_seq(tmp_path) == 4  # 跨重启续号


class TestWriteArchive:
    def _frame(self, **kw):
        base = dict(
            skill="shenbi-chapter-drafting",
            chapter=20,
            attempt=1,
            model="m",
            system_prompt="SYS",
            user_prompt="USER",
            reads_manifest=[
                {
                    "path": "truth/current_state.md",
                    "mode": "fields",
                    "fields": ["系统演化阶段"],
                    "matched_all": False,
                }
            ],
            raw_reads={"truth/current_state.md": "# 原文"},
            skill_contract_sha256="sha256:abc",
            loop_id=3,
            feedback_ref=None,
        )
        base.update(kw)
        return ar.ArchiveFrame(**base)

    def test_success_record_shape_and_dereference(self, tmp_path: Path):
        path = ar.write_dispatch_archive(
            tmp_path,
            self._frame(),
            finish_reason="stop",
            response_text="RESP",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert path is not None and path.exists()
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["seq"] == 1 and rec["skill_contract_sha256"] == "sha256:abc"
        assert rec["user_prompt_blob"] == ar.sha256_of("USER")
        # 字节级复现：解引用 == 原文（spec §6 P1 离线验收）
        blob = tmp_path / "observability" / "blobs" / rec["user_prompt_blob"].split(":", 1)[1]
        assert blob.read_text(encoding="utf-8") == "USER"
        assert rec["reads"][0]["resolved_fields"] == []  # 未命中如实记空
        assert rec["reads"][0]["blob"] == ar.sha256_of("# 原文")  # 磁盘原文（非过滤视图）
        assert "00001-shenbi-chapter-drafting-ch020-a1" in path.name

    def test_genesis_ch000_and_failure_nullable(self, tmp_path: Path):
        path = ar.write_dispatch_archive(
            tmp_path, self._frame(chapter=None), finish_reason=None, response_text=None, usage=None
        )
        assert "ch000" in path.name
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["response_blob"] is None and rec["finish_reason"] is None
```

- [ ] **Step 2: 跑测确认失败** — `uv run pytest tests/unit/observability/test_archive.py -v` → FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 archive.py**（要点；完整实现按测试驱动补齐）

```python
"""Dispatch archive layer (spec #81 §1): content-addressed blobs + per-dispatch records.

Write side is the dispatch path ONLY (fail-safe: an archive failure never
masks the dispatch outcome — same discipline as _persist_failed_write_output).
Readers (observe_report, dispatch_replay in P2) never write here.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.pipeline.truth_io import truth_file_flock

log = get_logger(__name__)

_OBS = "observability"
_DEFAULT_QUOTA = 1024 * 1024 * 1024
_STATS = "archive-stats.json"


def archive_enabled() -> bool: ...
def quota_bytes() -> int: ...
def sha256_of(text: str) -> str: ...


def put_blob(project_dir: Path, content: str) -> str:
    digest = sha256_of(content)
    blob = project_dir / _OBS / "blobs" / digest.split(":", 1)[1]
    if blob.exists():
        return digest
    if _bytes_under_management(project_dir) + len(content.encode()) > quota_bytes():
        bump_stats(project_dir, "archive_quota_skip")
        log.warning("archive_quota_skip")
        return digest  # 哈希照返（spec §1「档与哈希照写」）——只跳内容写
    blob.parent.mkdir(parents=True, exist_ok=True)
    safe_write(
        blob, content.encode("utf-8")
    )  # 原子写唯一入口（safe_write.py:1 自述；bytes|str 皆收）
    _account_bytes(project_dir, len(content.encode()))
    return digest
```

`_bytes_under_management`：stats 文件内 `{"bytes": int}` 运行字节账；每 50 次 put_blob 抽样 `du` 校准（`_calibrate`）。`next_seq`：`truth_file_flock(stats 文件)` 下 glob dispatches 取 max。`write_dispatch_archive`：frame → 档 dict（schema 按 spec §1 JSON，加 `resolved_fields`（manifest `fields` 中实际命中者——由调用方在 manifest 构建时已可判定，未命中记 `[]`）、`"source": "disk"|"cache"` 可选键）；档名 `{seq:05d}-{skill}-ch{N:03d}-a{attempt}.json`（chapter=None → ch000）；写档撞名 → `bump_stats("archive_seq_collision")` + WARN 跳过；`safe_write` 落盘；异常 → `bump_stats("archive_write_failed")` + WARN + 返回 None（**不抛**）。`skill_contract_sha(skill)`：`skills/<skill>/SKILL.md` 字节 sha256。

- [ ] **Step 4: 跑测过** — `uv run pytest tests/unit/observability/test_archive.py -v` → PASS
- [ ] **Step 5: Commit** — `git add src/shenbi/observability/ tests/unit/observability/test_archive.py && git commit -m "feat(observability): spec #81 T1 — dispatch archive module (blobs/seq/quota/stats)"`

---

### Task 2: `_build_skill_prompt` 磁盘原文快照（5 元组返回）+ `resolved_fields` 可导出

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:852 读盘点后捕获；:1100 filter 调用点；:1491 返回）、`src/shenbi/contracts/fields.py`（`filter_to_fields` 扩 3 元组返回——**仅此一个生产调用方**，grep 已核：dispatch_helper.py:1100 唯一）
- Test: `tests/unit/pipeline/test_dispatch_snapshot.py`、`tests/unit/contracts/test_fields.py`（3 元组适配）；**filter 3 元组爆破面另三文件**：`tests/unit/pipeline/test_field_filtering.py`（6 位）、`tests/unit/pipeline/test_read_contract_reality_lock.py`、`tests/unit/contracts/test_chapter_planning_contract.py:42`（后者的目录不在 Step 4 命令里——Step 4 以 `tests/unit/contracts` 整目录跑兜住）；builder 5 元组爆破面实measure：`grep -rln "_build_skill_prompt" tests/` 约 23 文件 55 位（tests/pipeline/ 10 文件：spec6_prompt_slimming、dispatch_helper_cap_raise、trigger_context、dispatch_helper_system_stability、dispatch_helper_keys、audit_context_cache、dispatch_reads_injection、closure_context、dispatch_helper_xml、meta_view_coordinates；tests/unit/pipeline/ 13 文件：layerb_live、staging_commit、dispatch_helper、dispatch_ingestion_guard、retry_accounting、token_ledger_guard(:69/:163 双位)、read_extractors_slicing、dispatch_helper_read_suppression、append_dedup_increment_injection、dispatch_usage_capture、style_seed、helper_injection、estimate_rows）

**Interfaces:**
- Produces:
  - `_build_skill_prompt(...) -> tuple[str, str, list[str], list[dict[str, Any]], dict[str, str]]`（第 5 元 = `raw_disk_reads: dict[contract_path -> 磁盘原文]`）；**磁盘分支捕获点在 :852 `content = full_path.read_text(...)` 之后、任何 extractor/filter/strip 之前；缓存命中分支（:847-849，不走 :852）在其取值点捕获**。
  - `filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool, list[str]]`（第 3 元 = `resolved_fields` 实际命中声明字段名——spec §1 示例「resolved_fields 非空 + matched_all=false」的部分命中形态由此可导；manifest 旧 `matched_all` 语义不变）。
  - **两条缓存路径都捕获**（I9，语义钉死 R3-M2：**选 (a) 新增 manifest 条目**）：循环内 shared_context `raw_files` 命中位（:847-849，已有 manifest 条目）与循环后 `_INJECT_FROM_CACHE` 合并位（:1126-1150，**今日无 manifest 条目——本批为其新增条目**，`source: "cache"` 标注；缓存注入 read 是模型实见读面，trace reads 可见性是加性语义增益而非破坏——并入 deviation ② 记档）。归档侧规则：manifest 条目无 raw 对应时该条目跳 blob（无 KeyError，如实少档）。

- [ ] **Step 1: 失败测试**

```python
"""Spec #81 §1: raw disk snapshot captured pre-filter/pre-strip (O-2 semantics)."""

from __future__ import annotations

from pathlib import Path

from shenbi.contracts import OutputKind


def test_raw_snapshot_is_disk_original_not_filtered_view(tmp_path: Path, monkeypatch):
    # 脚手架形态取自 tests/unit/pipeline/test_dispatch_helper.py::
    # test_multi_file_prompt_includes_schema_reminder（builder 直调 + mock 契约）
    mock_contract = {
        "kind": OutputKind.ARTIFACT,
        "reads": ["style/style_profile.md"],  # builder 只吃字符串 reads（:807-817）
        "read_fields": {"style/style_profile.md": ["文风基准"]},  # fields 走 sidecar
        "writes": ["chapters/chapter-1.md"],
        "updates": [],
    }
    monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: mock_contract)
    target = tmp_path / "style" / "style_profile.md"
    target.parent.mkdir(parents=True)
    # 一节命中契约字段、一节不命中——fields 过滤视图必然丢第二节（:1100 filter_to_fields）
    target.write_text("## 文风基准\n命中内容\n## 漂移节\n独有内容\n", encoding="utf-8")

    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    system_prompt, user_prompt, output_paths, reads_manifest, raw_reads = _build_skill_prompt(
        "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
    )

    key = next(k for k in raw_reads if "style_profile" in k)
    assert "漂移节" in raw_reads[key]  # 磁盘原文保留未命中节（pre-filter 捕获）
    assert "漂移节" not in user_prompt  # 注入面仍是过滤视图（行为不变）
    fields_entry = next(r for r in reads_manifest if r.get("mode") == "fields")
    assert fields_entry["matched_all"] is True  # 命中节在，声明字段全中
    assert fields_entry["resolved_fields"] == [
        "文风基准"
    ]  # 3 元组新返回（部分命中形态见 test_fields）
```

（若 mock 契约的 reads dict 形态与 loader 实际解析有出入，以 `tests/unit/pipeline/test_dispatch_layerb_live.py` 的 fields 声明写法为准修正——断言核心不变：`raw_reads` 含未命中节、`user_prompt` 不含。）

- [ ] **Step 2: 确认失败**（4 元组解包 TypeError）
- [ ] **Step 3: 实现**：:852 后加 `raw_disk_reads: dict[str, str]` 收集（函数头初始化）；`filter_to_fields` 扩 3 元组（`_filter_md`/`_filter_json` 内部收集命中字段名，`match_field` 逐声明字段判定的循环已在）；两条缓存路径同步收集（raw_files 命中位 + `_INJECT_FROM_CACHE` 合并位）并给 manifest 条目加 `"source": "cache"`；:1491 返回 5 元组；两调用点（:3443 API 收用、:3822 IDE `_` 弃用）+ **全部 ~23 测试文件 stub 更新为 5 元组 / 3 元组 filter**（上列爆破面清单逐一过）。
- [ ] **Step 4: 跑新测试 + 全 dispatch/pipeline/contracts 测试面** — `uv run pytest tests/unit/pipeline tests/unit/contracts tests/pipeline -q` → 全 PASS（**不以 3 个文件为限**——爆破面在 T9 `just check` 才爆 = 返工）
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T2 — pre-filter raw disk snapshot, builder 5-tuple`

---

### Task 3: 逃逸舱计数器（写侧，共享路径，常开）

**Files:**
- Create: `src/shenbi/observability/escape.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（reads 循环后一次调用）
- Test: `tests/unit/observability/test_escape.py`

**Interfaces:**
- Produces:
  - `update_escape_hatch_state(project_dir: Path, reads_manifest: list[dict[str, Any]]) -> None`——键 `(path, tuple(fields))`；fields 模式条目 `matched_all=False` 连击 +1、`True` 复位清键；flock 于状态文件 `observability/escape-hatch-state.json`；**不受 `SHENBI_ARCHIVE_DISPATCH` 门控**（常开）。
  - `escape_hatch_drift_check(project_dir: Path) -> list[dict[str, Any]]`——纯读：streak ≥3 的键列表，条目形 `{"key": "<path>|<fields-joined>", "path": ..., "fields": [...], "streak": n, "first_ts": ..., "last_ts": ...}`（T7 消费 `key`/`streak`）；文件缺失 → `[]`（absent PASS）；半写 JSON 解析失败 → `[]` + WARN。

- [ ] **Step 1: 失败测试**（键隔离/复位/缺失三语义 + 常开）

```python
def test_three_consecutive_misses_keyed_by_path_fields(tmp_path: Path):
    manifest = [
        {
            "path": "style/style_profile.md",
            "mode": "fields",
            "fields": ["文风基准"],
            "matched_all": False,
        }
    ]
    for _ in range(2):
        ar_escape.update_escape_hatch_state(tmp_path, manifest)
    assert ar_escape.escape_hatch_drift_check(tmp_path) == []
    ar_escape.update_escape_hatch_state(tmp_path, manifest)  # 第 3 次
    drift = ar_escape.escape_hatch_drift_check(tmp_path)
    assert len(drift) == 1 and drift[0]["streak"] == 3


def test_interleaved_different_fields_do_not_reset_each_other(tmp_path: Path):
    # O-1 交错读语义：同文件不同 fields 声明互不干扰（spec §3 键论证）
    m1 = [{"path": "p", "mode": "fields", "fields": ["A"], "matched_all": False}]
    m2 = [{"path": "p", "mode": "fields", "fields": ["B"], "matched_all": True}]
    for _ in range(3):
        ar_escape.update_escape_hatch_state(tmp_path, m1)
        ar_escape.update_escape_hatch_state(tmp_path, m2)  # B 命中只复位 B
    assert len(ar_escape.escape_hatch_drift_check(tmp_path)) == 1  # A 键仍满 3


def test_matched_resets_streak(tmp_path: Path):
    m = [{"path": "p", "mode": "fields", "fields": ["A"], "matched_all": False}]
    ar_escape.update_escape_hatch_state(tmp_path, m)
    ar_escape.update_escape_hatch_state(tmp_path, m)
    # 同键命中 → 连击复位
    ar_escape.update_escape_hatch_state(
        tmp_path, [{"path": "p", "mode": "fields", "fields": ["A"], "matched_all": True}]
    )
    assert ar_escape.escape_hatch_drift_check(tmp_path) == []
    ar_escape.update_escape_hatch_state(tmp_path, m)  # 复位后从 1 重新起算
    assert ar_escape.escape_hatch_drift_check(tmp_path) == []


def test_absent_state_file_is_pass(tmp_path: Path):
    assert ar_escape.escape_hatch_drift_check(tmp_path) == []


def test_counter_runs_even_when_archive_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
    m = [{"path": "p", "mode": "fields", "fields": ["A"], "matched_all": False}]
    for _ in range(3):
        ar_escape.update_escape_hatch_state(tmp_path, m)
    assert len(ar_escape.escape_hatch_drift_check(tmp_path)) == 1  # 计数器照常落盘
```

- [ ] **Step 2-4: 红→实现→绿**（state 文件形态 `{"streaks": {"<path>|<fields-joined>": {"streak": n, "first_ts": ..., "last_ts": ...}}}`；flock 经 `truth_file_flock`）
- 接线：`_build_skill_prompt` reads 循环完成后（manifest 齐时）调 `update_escape_hatch_state(project_dir, reads_manifest)`——try/except 吞异常仅 WARN（builder 不得因观测态崩溃）。**接线缝必须有 executable 验证（R3-I1，dead-wire 防线——token-ledger 双重门控事故同款教训）**：

```python
def test_builder_wiring_renamed_heading_fires_drift(tmp_path: Path, monkeypatch):
    """§7.2 离线验收的端到端形态：真跑 builder ×3，非合成计数器状态。"""
    mock_contract = {  # 同 T2 脚手架形态
        "kind": OutputKind.ARTIFACT,
        "reads": ["style/style_profile.md"],
        "read_fields": {"style/style_profile.md": ["漂移前标题"]},  # 契约声明旧字段
        "writes": ["chapters/chapter-1.md"],
        "updates": [],
    }
    monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: mock_contract)
    target = tmp_path / "style" / "style_profile.md"
    target.parent.mkdir(parents=True)
    target.write_text("## 漂移后标题\n内容\n", encoding="utf-8")  # 人为制造字段漂移
    for _ in range(3):
        dh._build_skill_prompt("shenbi-chapter-drafting", tmp_path, "draft ch1", 1)
    assert len(esc.escape_hatch_drift_check(tmp_path)) == 1  # 3 次派发内 FAIL 链条成立
```

- [ ] **Step 5: Commit** — `feat(observability): spec #81 T3 — escape-hatch counter (path,fields) keyed, always-on`

---

### Task 4: `_dispatch_via_api` 归档接线 + state 透传（loop_id/feedback_ref/archive_path）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（签名 + ArchiveFrame + 返回路径清单 + trace 加性字段 + `dispatch_skill` :4121-4129 透传恢复）
- Test: `tests/unit/pipeline/test_dispatch_archive_wiring.py`

**Interfaces:**
- Consumes: T1 `write_dispatch_archive/ArchiveFrame/put_blob/archive_enabled`、T2 第 5 元组。
- Produces:
  - `_dispatch_via_api(skill, project_dir, prompt, uses_staging=False, shared_context=None, outputs_override=None, state: Any = None) -> DispatchResult`
  - `_emit_dispatch_trace(..., loop_id: int | None = None, feedback_ref: str | None = None, archive_path: str | None = None)`（payload 可选键）
  - 归档插桩点 = **返回路径清单**（spec §1 rev4）：成功 :3767 + 九失败位（timeout :3507 / generic :3526 / empty-resend :3597 / content_filter :3618 / length-ceiling :3637 / cap-raise-resend :3669 / persistent-length :3682 / post-cap-filter :3691 / write-failure 族 ×4 :3720-3747）；prompt-build 失败 :3456 不落档不计 stats。

- [ ] **Step 1: 失败测试**（复用 `test_token_ledger_guard.py` 的 `_dispatch_with_fake_client` 模式——注意其 `_build_skill_prompt` patch 改 5 元组）

```python
"""Spec #81 §2/§1 wiring tests — fake streaming client pattern copied from
tests/unit/pipeline/test_token_ledger_guard.py::_dispatch_with_fake_client."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from shenbi.observability import archive as ar
from shenbi.pipeline import dispatch_helper as dh


def _content_chunk(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _usage_chunk(p: int, c: int) -> SimpleNamespace:
    return SimpleNamespace(choices=[], usage=SimpleNamespace(
        prompt_tokens=p, completion_tokens=c, total_tokens=p + c))


def _dispatch_fake(monkeypatch, tmp_path, *, chunks=None, state=None,
                   skill="shenbi-chapter-drafting", prompt="prompt ch1"):
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    out = "chapters/chapter-1.md"
    stream = chunks or [_content_chunk(f"### FILE: {out}\nbody\n"), _usage_chunk(100, 50)]
    with (
        patch("openai.OpenAI") as mock_openai,
        patch(
            "shenbi.pipeline.dispatch_helper._build_skill_prompt",
            return_value=("sys", "user", [out], [],
                          {"style/style_profile.md": "# 原文"}),
        ),
    ):
        mock_openai.return_value.chat.completions.create.return_value = stream
        result = dh._dispatch_via_api(skill, tmp_path, prompt, state=state)
    return result


def _load_archive(tmp_path: Path) -> dict:
    files = list((tmp_path / "observability" / "dispatches").glob("*.json"))
    assert len(files) == 1, f"expected exactly 1 archive, got {len(files)}"
    return json.loads(files[0].read_text(encoding="utf-8"))


def test_success_writes_archive_with_loop_id_and_feedback(tmp_path, monkeypatch):
    state = SimpleNamespace(chapter_loop=SimpleNamespace(
        retry_budget_consumed={"ch1-shenbi-chapter-drafting": 7},
        retry_feedback={"ch1-shenbi-chapter-drafting": "上一轮反馈"}))
    result = _dispatch_fake(monkeypatch, tmp_path, state=state)
    assert result.success
    rec = _load_archive(tmp_path)
    assert rec["loop_id"] == 7 and rec["feedback_ref"] == ar.sha256_of("上一轮反馈")
    blob = tmp_path / "observability" / "blobs" / rec["feedback_ref"].split(":", 1)[1]
    assert blob.read_text(encoding="utf-8") == "上一轮反馈"
    assert rec["response_blob"] == ar.sha256_of(result.stdout)

def test_no_state_means_null_loop_id_feedback(tmp_path, monkeypatch):
    result = _dispatch_fake(monkeypatch, tmp_path)  # state=None（8/13 无 state 调用点兼容）
    assert result.success
    rec = _load_archive(tmp_path)
    assert rec["loop_id"] is None and rec["feedback_ref"] is None

def test_timeout_failure_branch_archives_with_null_response(tmp_path, monkeypatch):
    import httpx

    def _raise(*a, **k):
        raise httpx.TimeoutException("t")

    monkeypatch.setattr(dh, "_call_llm_streaming_with_retry", _raise)
    result = _dispatch_fake(monkeypatch, tmp_path)
    assert not result.success
    rec = _load_archive(tmp_path)
    assert rec["response_blob"] is None and rec["finish_reason"] is None
    assert rec["usage"] is None or rec["usage"] == {}   # 失败分支 usage 豁免

def test_write_failure_branch_archives_despite_no_trace(tmp_path, monkeypatch):
    # 令输出写盘抛 DispatchWriteFailureError（patch _write_parsed_outputs）
    # 断言：归档仍在（六类无 trace 返回位代表）且 trace.jsonl 无该派发 DISPATCH 事件

def test_trace_payload_carries_additive_fields(tmp_path, monkeypatch):
    # 成功路径后读 trace.jsonl：DISPATCH payload 含 loop_id/archive_path（trace 面预置一事件成链）

def test_prompt_build_failure_no_archive_no_stats(tmp_path, monkeypatch):
    # patch _build_skill_prompt 抛异常 → dispatches/ 空、archive-stats 不计 write_failed

def test_archive_write_failure_never_blocks_dispatch(tmp_path, monkeypatch):
    # patch shenbi.observability.archive.write_dispatch_archive 抛 RuntimeError
    # → dispatch 照常成功 + stats archive_write_failed +1 + WARN（fail-safe 纪律）
```

- [ ] **Step 2-4: 红→实现→绿**。实现要点：
  - prompt build 后构 frame：`raw_reads`（T2 第 5 元）、`skill_contract_sha(skill)`、`loop_id`/`feedback_ref`（`state` 非空时惰性 `from shenbi.pipeline.chapter_loop import _retry_key`；key=`_retry_key(chapter if chapter is not None else 1, skill)`；loop_id=`retry_budget_consumed.get(key, 0)`；feedback 文本非空才 `put_blob`——受 `archive_enabled()` 门控）、`attempt=usage_acc.get("attempts", 1)`（API 级尝试数——作用域内唯一 attempt 源，spec §1 示例 attempt:1 与 loop_id:3 分立即此语义）。
  - 返回位插桩：本地闭包 `def _archive(finish_reason, response_text, usage, ...) -> str | None`（内调 `write_dispatch_archive`，try/except → WARN+stats；返回 archive_path 供 trace）。九失败位 + 成功位各一次调用；成功位在 `_emit_dispatch_trace` 之前调用并把返回的 `archive_path`、`loop_id`、`feedback_ref` 传入 trace。timeout/generic/content_filter 三个已有 trace 的失败位同样传入。**timeout/generic 失败位 `usage` 未绑定**（:3481 元组解包未完成）——闭包实参取 `usage_acc.get("usage")`，不引用未绑定名（M11）。
  - `dispatch_skill` API 路（:4121-4129）补 `state=state` 透传；同批更新其 docstring（:4102-4105「state only toggles instrumentation」措辞过期——API 路现在消费 state 产 loop_id/feedback_ref）（M15）。
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T4 — archive wiring at return-path inventory + state threading`

---

### Task 5: 并行评审波 state 透传

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py`（`_dispatch_with_retry` :92 + 波入口签名）、`src/shenbi/pipeline/chapter_loop.py`（波入口调用点）
- Test: `tests/unit/pipeline/test_dispatch_archive_wiring.py`（追加类）

**Interfaces:**
- Produces: 波派发链 state 透传——**两个入口都改**（I7）：`parallel_dispatch.dispatch_reviews_parallel(tasks, on_task_complete, state: Any = None)`（:235，submit :264）→ `_dispatch_with_retry(task, semaphore, state: Any = None)`（:92）→ `dispatch_skill(..., state=state)`；**串行子波同批**：`chapter_loop._dispatch_serial_reviews(serial_tasks, project_dir, state: Any = None)`（:3356，调用位 :3577/:3618）→ 同透传——WRITE_SHARED 串行评审成员否则仍无 state（review-group 人口的最大子集，正是 rev4 钉死要盖的族）。chapter_loop 两个波调用点（:3572/:3610）把 state 传入 `dispatch_reviews_parallel`。

- [ ] **Step 1: 失败测试**——monkeypatch `dispatch_skill` 捕获 kwargs：(a) `_dispatch_with_retry` 收 state 后透传；(b) `_dispatch_serial_reviews` 收 state 后透传。
- [ ] **Step 2-4: 红→实现→绿**（`_dispatch_with_retry` 加 `state: Any = None` 形参并传入其 `dispatch_skill` 调用 :120-126；`ReviewTask` 不动（parallel_dispatch.py:44——state 是波级共享非任务级））。
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T5 — parallel wave state threading (loop_id coverage)`

---

### Task 6: RETRY 事件（chapter_loop 两缝）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_handle_failure` 重派批准位 + 监控回卷位 :3925-3956）
- Test: `tests/unit/pipeline/test_chapter_loop_retry_event.py`

**Interfaces:**
- Produces: 新模块级 helper `_emit_retry_event(project_dir: Path, *, chapter: int | None, skill: str, reason: dict[str, Any], loop_id: int) -> None`——**先守卫** `(project_dir / "trace.jsonl").exists()` 否则静默返回（同 `_emit_dispatch_trace` :3128-3131 纪律——`TraceWriter.append` 会自建 trace 面（writer.py:102-104），不守卫 = RETRY 静默造面）；守卫过后 `TraceWriter(project_dir).append(actor="chapter-loop", actor_role="SYSTEM", action="RETRY", target=f"ch{chapter}", skill=skill, payload={"chapter": chapter, "skill": skill, "reason": reason, "loop_id": loop_id})`。
- reason 结构化 + **发射位钉死（M14）**：G4 硬败块的**两个分支**——`per_chapter_review_enabled` 真 → `_handle_failure` 路径（:4140-4144 前）、假 → 直接 auto-retry 路径（:4145-4156）各发一次；监控回卷位（:3925-3955）。G4 位 reason = `{"kind": "g4_hard", "check_ids": [...hard_fails], "loop": loop_id}`；**回卷位按现存数据形态钉**：该位只有预格式 `issues: list[str]`（`scene_splitter.validate_split` 产物，如 `"word_band:ch2:total_chars 1995 不在带 [2800,4000]"`），spec §2 示例的数值差值 dict 不存在于该作用域——P1 reason = `{"kind": "monitor_rewind", "chapter": N, "issues": [...原串]}`（消费方 observe_report 失败簇按 kind 聚类不受影响）；**数值化差值形态记 spec-deviations 延后**（scene_splitter 结构化暴露属独立小改，不顺手膨胀 T6 scope）。

- [ ] **Step 1: 失败测试**——tmp_path 造 trace.jsonl（先手 TraceWriter 落一 INIT 事件成链），monkeypatch 触发 `_handle_failure` 重派路径，断言 trace 尾部出现 `action=="RETRY"` 且 payload 结构化；监控位同理（直调 `_emit_retry_event` 断言形态 + 回卷路径集成断言）；**无 trace 文件时断言不创建**（守卫测试——空 tmp_path 直调 helper 后 `trace.jsonl` 不存在）。
- [ ] **Step 2-4: 红→实现→绿**。
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T6 — RETRY trace event (structured loop re-dispatch reasons)`

---

### Task 7: `escape_hatch_drift` fail-fast 读侧（派发后相位检查）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（:4019 `result = dispatch_skill(...)` 之后、state-settling 失败分支之前）
- Test: `tests/unit/observability/test_escape.py`（追加）

**Interfaces:**
- Consumes: T3 `escape_hatch_drift_check`；`shenbi.audit.record.record_audit_outcome(round_dir, skill, result)`；`shenbi.pipeline.machine.set_checkpoint(state, CheckpointType.ESCALATION, chapter=..., context=...)`。
- Produces: helper `_check_escape_hatch_drift(state, project_dir, chapter) -> bool`（True=已设 checkpoint 应停步）。

- [ ] **Step 1: 失败测试**

```python
def test_drift_fail_escalates_without_retry_charge(tmp_path, monkeypatch):
    # 造 streak=3 状态文件
    from shenbi.observability import escape as esc

    m = [
        {
            "path": "style/style_profile.md",
            "mode": "fields",
            "fields": ["文风基准"],
            "matched_all": False,
        }
    ]
    for _ in range(3):
        esc.update_escape_hatch_state(tmp_path, m)
    state = _minimal_chapter_state()  # SimpleNamespace(chapter_loop=SimpleNamespace(
    #   retry_budget_consumed={"ch1-s": 2}, retry_counts={}),
    #   pending_checkpoint=None)
    raised = cl._check_escape_hatch_drift(state, tmp_path, chapter=5)
    assert raised is True
    # (a) ESCALATION checkpoint 已设
    assert state.pending_checkpoint.type.value == "escalation"  # 按 CheckpointType 实际形态断言
    # (b) 零充语义：retry 计数原值未动
    assert state.chapter_loop.retry_budget_consumed == {"ch1-s": 2}
    assert state.chapter_loop.retry_counts == {}
    # (c) GATE_FAIL 双产物（write-audit.jsonl + trace），(d) gate-markers/ 无新文件
    assert any(
        json.loads(l)["blocked"] for l in (tmp_path / "write-audit.jsonl").read_text().splitlines()
    )
    assert "GATE_FAIL" in (tmp_path / "trace.jsonl").read_text()
    assert not (tmp_path / "gate-markers").exists() or not any(
        (tmp_path / "gate-markers").iterdir()
    )


def test_drift_absent_passes(tmp_path):
    state = _minimal_chapter_state()
    assert cl._check_escape_hatch_drift(state, tmp_path, chapter=5) is False


def test_two_misses_no_checkpoint(tmp_path):
    # streak=2 <3 → 不触发（O-2 复演防护的窗）
    m = [
        {
            "path": "style/style_profile.md",
            "mode": "fields",
            "fields": ["文风基准"],
            "matched_all": False,
        }
    ]
    esc.update_escape_hatch_state(tmp_path, m)
    esc.update_escape_hatch_state(tmp_path, m)
    assert cl._check_escape_hatch_drift(_minimal_chapter_state(), tmp_path, chapter=5) is False
```

（`_minimal_chapter_state` 与 CheckpointType 断言形态在实施时对齐 `tests/unit/pipeline/` 既有 state 脚手架——`test_retry_taxonomy.py` 的 state 构造是现成参照；`...` 处即两次 `update_escape_hatch_state` 调用，同上族写法。）

- [ ] **Step 2-4: 红→实现→绿**。实现：:4019 后插

```python
if _check_escape_hatch_drift(state, project_dir, chapter):
    return True  # escalation checkpoint raised, pause for human
```

`_check_escape_hatch_drift`：`drift = escape_hatch_drift_check(project_dir)`；非空 → `record_audit_outcome(project_dir, "escape-hatch", AuditResult(skill="escape-hatch", violations=tuple(f"escape_hatch_drift: {d['key']} streak={d['streak']}" for d in drift), drift=(), checked_files=()))` + `set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter, context="逃逸舱字段漂移：契约 fields 与文件标题连续失配 ≥3——producer 模板漂移，需人工对齐（spec #81 §3）")` → True；**不触任何 retry 计数**（零充 = 从不调用 `_handle_failure`/不手充 budget）。`AuditResult` 从 `shenbi.audit._shared` 导入（`skill` 是无默认值首字段，tuple 型容器字段——:31-39）。**检出时延注记（R3-M3）**：并行评审波块（:3487）与草稿后块（:3743）先于 :4019 派发位 return——波内累积的漂移要到下一串行派发（通常下一章 drafting）才浮出，晚于理想 3 派发窗；此为相位检查归属（spec §3 rev2 钉死）的已知代价，运行侧验收读数时勿误判为缺陷。
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T7 — escape_hatch_drift fail-fast (zero-charge escalation)`

---

### Task 8: `tools/observe_report.py` 四表 + 覆盖行 + WARN 汇总

**Files:**
- Create: `tools/observe_report.py`；Modify: `justfile`
- Test: `tests/unit/tools/test_observe_report.py`

**Interfaces:**
- Consumes: `trace.jsonl`（DISPATCH payload loop_id/reads + RETRY + GATE_FAIL）、`cost/token-ledger.jsonl`（attempt==1 行 = 每派发恰一行）、`observability/dispatches/*.json`、`observability/escape-hatch-state.json`、`observability/archive-stats.json`。
- Produces: `build_report(project_dir: Path) -> str`（markdown）；CLI `uv run python tools/observe_report.py <project_dir>`；justfile `observe-report *args: uv run python tools/observe_report.py "$@"`。

- [ ] **Step 1: 失败测试**（tmp_path 结构语料：3 派发 ledger/trace/archive 三源交叉）

```python
def test_four_tables_and_coverage_row(tmp_path: Path):
    _seed_corpus(tmp_path)
    md = build_report(tmp_path)
    for header in ("## 膨胀曲线", "## Loop depth", "## 失败簇", "## 逃逸舱", "## 归档覆盖"):
        assert header in md
    assert "ledger=3" in md and "archive=3" in md  # 覆盖行对账（attempt=1 口径）
    assert "monitor_rewind" in md  # 失败簇聚类
    assert "archive_quota_skip=0" in md  # WARN 三键汇总行


def test_dedup_ratio_and_blob_existence(tmp_path: Path):
    _seed_corpus(tmp_path)  # 2 档共用同一 system_prompt blob → 去重率 <1、存在比例 100%
    md = build_report(tmp_path)
    assert "去重率" in md and "blob" in md


def test_missing_surfaces_degrade_to_explicit_note(tmp_path: Path):
    # 无 observability/ 的既有项目：报告头明示「无归档（特性前项目）」不炸
    (tmp_path / "trace.jsonl").write_text("", encoding="utf-8")
    md = build_report(tmp_path)
    assert "无归档" in md
```

`_seed_corpus` 构造（tmp_path 结构语料）：ledger 3 行（2 skill，全部 `attempt=1`、`estimated=false`）；trace.jsonl 经 TraceWriter 落 2 DISPATCH（其一 payload `loop_id=4` + reads `matched_all=false` ×1）+ 1 RETRY（payload **与 T6 实发形态对齐**：`reason={"kind": "monitor_rewind", "chapter": 2, "issues": ["word_band:ch2:total_chars 1995 不在带 [2800,4000]"]}`——勿用 spec §2 示例的数值 dict 形态，那是 deviation ③ 延后项）；dispatches/ 3 档（其一 `response_blob` 指向真实存在的 blob 文件、两档共用同一 `system_prompt_blob`）；escape-hatch-state.json 一键 streak=2；archive-stats.json 三键 0/0/0。

- [ ] **Step 2-4: 红→实现→绿**。四表：
  1. **膨胀曲线**：ledger 按 (skill, chapter) prompt_tokens 均值走势行；
  2. **Loop depth**：trace DISPATCH payload `loop_id` 每 (skill, chapter) max + RETRY 计数；
  3. **失败簇**：RETRY payload reason 按 `kind` 聚类 + 失败派发数；
  4. **逃逸舱**：trace reads `matched_all=false` 计数 per path + 当前 streaks。
  覆盖行：`ledger attempt=1 行数 vs dispatches 档数` + blob 存在性（档内全部 blob 指针 → blobs/ 存在比例）+ 去重率（引用字节/实存字节）。WARN 行：archive-stats 三键分计。tools/ 脚本可 `print`（AGENTS.md T20 仅限 `src/shenbi/`）。
- [ ] **Step 5: Commit** — `feat(observability): spec #81 T8 — observe_report four tables + coverage row`

---

### Task 9: P1 离线验收整合（可执行化跑批）

**Files:**
- Test: 上述各测试文件的验收映射注释 + 本 task 无新代码（跑批 + 记录）。
- 无新实现——此 task 把 spec §6/§7 离线验收逐条跑一遍并粘 progress.md。

- [ ] **Step 1: 跑验收映射**

| spec 验收条 | 可执行验证 | 所在 |
|---|---|---|
| §6 P1 归档写档+blob 去重+字节复现 | `uv run pytest tests/unit/observability/test_archive.py -v`（dereference 断言）+ `test_dispatch_archive_wiring.py` | T1/T4 |
| §6 P1 fail-fast 三触发+四元组语义 | `uv run pytest tests/unit/observability/test_escape.py -v`（3 次 FAIL/交错隔离/复位/缺失 PASS） | T3/T7 |
| §7.1 [P1 离线] 四表+覆盖行对账一致 | `uv run pytest tests/unit/tools/test_observe_report.py -v` | T8 |
| §7.2 [P1 离线] 漂移制造 → FAIL | `test_escape.py::test_drift_fail_escalates_without_retry_charge` + `test_escape.py::test_builder_wiring_renamed_heading_fires_drift`（端到端：真跑 builder ×3 对改名标题 → drift 非空） | T7+T3 |
| §7.5 [P1 离线] KB 级熔断实测 | `test_archive.py::test_quota_breaker_skips_blob_keeps_hash_and_counts` | T1 |
| 运行侧条目（vol1 续跑字节复现/5 章窗口/≤80MB） | **不在 SDD 边界**（spec §6 运行验证阶段） | — |

- [ ] **Step 2: `just check` 全绿**
- [ ] **Step 3: 验收输出粘 progress.md `## 验收证据`**

---

## 验收覆盖表（spec §7 ↔ task）

见 Task 9 表（P1 期交付 1/2/5 离线形态；3/4 为 P2 期定义，spec §7 已分期标注）。

## 执行说明

- 全 task = infra → **协调者亲自实现**（SDD leaf/infra 分流；T8/T9 保守归类 infra——消费 T1/T4/T6 产物格式，协调者做免接口漂移），每 task commit 后 fresh-context 审查子 agent 产 `audit-T<N>.md`，无之不得开 T<N+1>。
- 每 task TDD 红→绿→commit；偏差当轮记 `spec-deviations.md` `### T<N>` 段。
- **预登记 deviations（实施时照记）**：① T1 `skill_contract_sha` 取内容 sha256 非 git blob SHA（溯源等价，格式统一）；② T2 `resolved_fields` 进 manifest + `_INJECT_FROM_CACHE` 注入 read **新增 manifest 条目**（`source: "cache"`）——spec §1 措辞「manifest 不动」；两者皆加性（trace reads 可见性增益），无破坏；③ T6 回卷位 reason 取现存 `issues: list[str]` 形态，数值化差值 dict 延后。
- 既有测试 stub 爆破面（T2）：`grep -rn "_build_skill_prompt\|filter_to_fields" tests/` 双清单列全，逐一更新——漏一个 = 阶段 7 `just check` 红。
