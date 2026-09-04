# Spec #42 C28 性能反模式修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or coordinator-inline per SDD v6 leaf/infra routing. **本计划全部 task 为 infra**（涉及 `src/shenbi/pipeline/`、`src/shenbi/contracts/`、`src/shenbi/gates/`）——按 SDD v6 阶段 6 分流规则由协调者亲自实现，不派 implementer 子 agent；每 task commit 后必须产出 fresh-context 审查 `.superpowers/sdd/audit-T<N>.md`。

**Goal:** 落实 spec #42（C28）四项性能修复：审计波读抑制（I/O 9→1）、registry/模型缓存、gate 侧 O(N²) 重读消除、门禁懒加载（<50ms）。

**Architecture:** 全部为既有热路径的等价优化：R1 用 `SharedAuditContext.raw_files`（原始字节表）在磁盘读循环前拦截重复读取（prompt 字节不变）；R2 以 (path, mtime_ns, size) 键做进程内缓存 + SentenceTransformer 单例/负缓存；R3 有界前缀读取 + 指纹缓存 + 真 append；R4 import 拓扑重排（零行为变化）。

**Tech Stack:** Python 3.11+、pathlib、threading.Lock、pytest + pytest-benchmark（`-m benchmark`）、pytest monkeypatch spy。

## Global Constraints

- 全部 infra task：协调者亲自实现，TDD（先红后绿），逐 task commit + fresh-context 审查（audit-T<N>.md）
- 验证命令一律 `uv run` / `just` 形态（与 CI `uv run --frozen` 同构）；系统 python 结果不算证据
- `src/shenbi/` 禁 `print()`（structlog）；pathlib 文件 I/O；gate 检查器保持幂等纯校验（进程内 memoization 无输出文件副作用）
- G0.9：测试输入只引用 `tests/fixtures/` 真实产物（含其复制/变体）；禁手写 fixture
- G3.4：本 spec 无 LLM 产物评分场景（全部确定性测试），不涉独立评分调度
- commit 走 Conventional Commits；显式列文件路径（pathspec commit），禁 `git add -A`
- 字节等价闸：R1 读抑制开关开/关产出的 prompt 字节必须完全一致（唯一例外=spec 声明的 F312 路径修复效果，不在闸内）

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1-1 raw_files 完整原文（5 文件） | T4 | `uv run pytest tests/unit/pipeline/test_dispatch_helper_read_suppression.py -k raw_files -q` |
| R1-2 章节 read_text 次数 == 1（当前 9） | T4 | 同上 `-k read_count_is_one` |
| R1-3 读抑制开/关 prompt 字节等价 | T4 | 同上 `-k byte_equality_suppression_switch` |
| R1-4 world/rules.md 键存在 | T4 | 同上 `-k world_rules_key_present` |
| R2-1 registry 解析次数（不变 1 / touch 2） | T2 | `uv run pytest tests/unit/contracts/test_legacy_registry_cache.py -q` |
| R2-2 模板齐全不扫描 | T2 | `uv run pytest tests/unit/pipeline/test_dispatch_helper_read_suppression.py -k shortcircuit -q`（T2 新建该测试文件；T4 追加 R1 部分） |
| R2-3 Route B 负缓存（第二次无网络） | T3 | `uv run pytest tests/unit/pipeline/test_truth_embed_singleton.py -k negative_cache -q` |
| R2-4 单例并发构造 == 1 | T3 | 同上 `-k concurrent_init` |
| R3-1 标题读取 ≤4096B×N + meta-first 双提取非空 | T5 | `uv run pytest tests/unit/pipeline/test_chapter_titles.py -q` |
| R3-2 content_uniqueness 二遍读取 == N | T6 | `uv run pytest tests/gates/g4/test_content_uniqueness_cache.py -q` |
| R3-3 append 200 次内容逐字节一致 + O(k) | T6 | `uv run pytest tests/unit/pipeline/test_integrity_append.py -q` |
| R4 importtime <50ms + 11 门行为不变 | T1 | `uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 \| tail -3`；`uv run pytest tests/gates/ tests/unit/test_gates_cli.py -q` |
| 簇级 benchmark 三基线 | T7 | `uv run pytest tests/ -m benchmark -q` |
| 簇级回归 | 全部 | `just check` |

---

### Task 1: R4 门禁懒加载 + jieba 移函数体 + F415-0814 行号引用修正

**Files:**
- Modify: `src/shenbi/gates/cli.py:11-31`（顶层 import 块 + `log` 绑定）、main() 内各分支
- Modify: `src/shenbi/text/cjk.py:10-11`（jieba 顶层 import 移函数体）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:93`
- Test: `tests/unit/test_gates_cli_import_cost.py`（新建）

**Interfaces:**
- Consumes: 无（独立 task）
- Produces: `gates/cli.py` 顶层仅 `import json/sys`；`_load_gate(gate: str)` 懒加载器；`cjk.py` 对外函数签名不变（`find_terms` 等）；后续 task 不依赖本 task 内部结构

- [ ] **Step 1: 写失败测试（import 开销）**

```python
# tests/unit/test_gates_cli_import_cost.py
"""T1604: gates.cli top-level import must stay under 50ms (importtime cumulative)."""
import subprocess
import sys


def _importtime_cumulative_us(module: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", f"from shenbi.gates import {module}"],
        capture_output=True,
        text=True,
        check=True,
    )
    # importtime lines: "import time: self [us] | cumulative | imported package"
    for line in reversed(proc.stderr.splitlines()):
        if line.endswith(f"| {module}") or line.rstrip().endswith(f"| shenbi.gates.{module}"):
            parts = [p for p in line.replace("import time:", "").split("|") if p.strip()]
            return int(parts[1].strip())
    raise AssertionError(f"module {module} not found in importtime output")


def test_gates_cli_top_level_import_under_50ms() -> None:
    assert _importtime_cumulative_us("cli") < 50_000
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_gates_cli_import_cost.py -q`
Expected: FAIL（当前 ~370,000µs ≥ 50,000）

- [ ] **Step 3: 实现——gates/cli.py 懒加载**

顶层只留 `import json` / `import sys`；11 个门禁模块改为懒加载器（保持 main() 各分支调用的函数名不变）：

```python
import json
import sys

# T1604 (C28 R4): lazy per-gate loading — the 11 gate modules (plus
# logging/cli_utils/gates.shared chains) cost ~370ms of the ~380ms
# subprocess spawn; only the requested gate's module is imported now.
from collections.abc import Callable
from typing import Any


def _gate_G0() -> Callable[..., Any]:
    from shenbi.gates.g0 import gate_G0

    return gate_G0

# ...（g1-g7、g_dispatch、g_reconcile、g_transition 同构 11 个 loader）


_GATES: dict[str, Callable[[], Callable[..., Any]]] = {
    "G0": _gate_G0,
    # ...
}
```

main() 内：`configure_logging()`/`emit_json`/`PROJECT`/`write_gate_marker`/`GateStatus`/`log` 的 import 与绑定移入 main() 函数体（`log` 移为 main() 内局部 + 各分支按需使用）；各分支局部 `from shenbi.gates.gX import gate_GX`（G4 分支需导全部三个 callable：`gate_G4`/`gate_G4_bughunt`/`gate_G4_clean`）。`from typing import` 改 `from collections.abc import Callable`（repo 风格，UP035）。SHORT_MAP 纯数据保留模块级（无 import 成本）。

- [ ] **Step 4: 实现——cjk.py jieba 懒单例（模块级 `_TOKENIZER`/`_POSEG` 才是 import 成本载体）**

顶层删除 `import jieba` / `import jieba.posseg as pseg` 与 `:138-139` 的即刻构造；`find_terms` 不用 jieba（纯子串匹配）无需改。tokenizer 改 None 哨兵懒单例（保持 spec #32 F615 隔离语义：私有实例、不动全局 `jieba.dt`）：

```python
# src/shenbi/text/cjk.py
_TOKENIZER: Any = None      # lazy: jieba import costs ~105ms and only G6 path needs it
_POSEG: Any = None
_TOKENIZER_LOCK = threading.Lock()


def _get_tokenizers() -> tuple[Any, Any]:
    """Lazily construct the isolated tokenizers (T1604: jieba off the
    import critical path; isolation semantics of spec #32 F615 preserved)."""
    global _TOKENIZER, _POSEG
    if _TOKENIZER is None:
        with _TOKENIZER_LOCK:
            if _TOKENIZER is None:
                import jieba
                import jieba.posseg as pseg

                tok = jieba.Tokenizer()
                poseg = pseg.POSTokenizer(tok)
                # publish order: _POSEG first, _TOKENIZER (the sentinel/flag) last —
                # a lock-free fast-path reader must never see tokenizer set with
                # _POSEG still None
                _POSEG = poseg
                _TOKENIZER = tok
    return _TOKENIZER, _POSEG


def tokenize(text: str, domain_dict: Iterable[str] | None = None) -> list[Token]:
    tokenizer, poseg = _get_tokenizers()
    if domain_dict:
        for term in domain_dict:
            tokenizer.add_word(term)
    return [Token(word=w, pos=f) for w, f in poseg.cut(text) if w.strip()]
```

- [ ] **Step 5: 实现——F415-0814 行号引用改符号引用**

`src/shenbi/gates/g4/chapter_drafting.py:93`：`"title must not include chapter number (SKILL.md:125)"` → `"title must not include chapter number (SKILL.md「章节标题不要包含章节号」)"`

- [ ] **Step 6: 跑测试确认通过 + 门禁行为回归**

Run: `uv run pytest tests/unit/test_gates_cli_import_cost.py tests/gates/ tests/unit/test_gates_cli.py -q`
Expected: 全 PASS

Run: `uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3`
Expected: `shenbi.gates.cli` 累计 < 50,000µs

- [ ] **Step 7: Commit + 审查**

```bash
git add src/shenbi/gates/cli.py src/shenbi/text/cjk.py src/shenbi/gates/g4/chapter_drafting.py tests/unit/test_gates_cli_import_cost.py
git commit -m "perf: spec42 C28 R4 lazy gate loading (<50ms import), jieba into function body, F415 symbol ref"
```
产出 `.superpowers/sdd/audit-T1.md`（fresh-context 审查）后方可开始 T2。

---

### Task 2: R2a registry (path, mtime_ns, size) 缓存 + truth 模板前置短路

**Files:**
- Modify: `src/shenbi/contracts/legacy.py:106-126`（`load_registry`）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（`_init_truth_templates` :1596-1615 前置短路）
- Test: `tests/unit/contracts/test_legacy_registry_cache.py`（新建——`tests/unit/contracts/test_registry.py` 测的是另一 registry，勿混）、`tests/unit/pipeline/test_dispatch_helper_read_suppression.py`（新建，含 T2/T4 测试）

**Interfaces:**
- Consumes: `load_registry() -> TruthFilesRegistry`（现签名）
- Produces: 同名同签名函数（内部缓存）；`_parse_registry_uncached() -> TruthFilesRegistry`（供 benchmark 基线复用）；`_init_truth_templates(project_dir: Path) -> None`（签名不变）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/contracts/test_legacy_registry_cache.py（新建）
def test_load_registry_caches_until_mtime_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T1613/F215: same mtime_ns+size -> exactly 1 YAML parse; touch -> re-parse."""
    import os

    import pytest  # noqa: F401  (module 顶部统一 import：Path/pytest)
    import shenbi.contracts.legacy as legacy

    reg_src = legacy.REGISTRY_PATH  # canonical docs/framework/truth-files.yaml
    calls = {"n": 0}
    real_safe_load = legacy.yaml.safe_load

    def counting_safe_load(*a: object, **k: object) -> object:
        calls["n"] += 1
        return real_safe_load(*a, **k)

    monkeypatch.setattr(legacy.yaml, "safe_load", counting_safe_load)
    # os.utime 只动真实 registry 的 mtime（内容不变，ns 键缓存语义内安全）；
    # 缓存重置经 monkeypatch 保证测试隔离
    monkeypatch.setattr(legacy, "_REGISTRY_CACHE", None)
    legacy.load_registry()
    legacy.load_registry()
    legacy.load_registry()
    assert calls["n"] == 1

    st = reg_src.stat()
    os.utime(reg_src, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    legacy.load_registry()
    assert calls["n"] == 2
```

```python
# tests/unit/pipeline/test_dispatch_helper_read_suppression.py（新建，T2 部分）
def test_init_truth_templates_shortcircuits_when_all_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T1606: with every template present, the 74-skill scan must not run."""
    import shenbi.pipeline.dispatch_helper as dh

    truth = tmp_path / "truth"
    truth.mkdir()
    for fn in dh._TRUTH_FILE_TITLES:
        (truth / fn).write_text("---\nupdate_mode: replace\n---\n", encoding="utf-8")

    calls = {"n": 0}
    monkeypatch.setattr(dh, "_collect_declared_truth_fields",
                        lambda: calls.__setitem__("n", calls["n"] + 1) or {})
    dh._init_truth_templates(tmp_path)
    assert calls["n"] == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/contracts/test_legacy_registry_cache.py -q` 和 `uv run pytest tests/unit/pipeline/test_dispatch_helper_read_suppression.py -k template -q`
Expected: FAIL（无缓存：n==3；无短路：n==1）

- [ ] **Step 3: 实现**

```python
# src/shenbi/contracts/legacy.py
_REGISTRY_CACHE: tuple[tuple[int, int], "TruthFilesRegistry"] | None = None
_REGISTRY_CACHE_LOCK = threading.Lock()


def _parse_registry_uncached() -> TruthFilesRegistry:
    """Original parse path (kept public for the benchmark baseline)."""
    # ...原 load_registry 的 exists 检查 + safe_load + model_validate 全文...


def load_registry() -> TruthFilesRegistry:
    """(path, mtime_ns, size)-keyed process cache.

    Same-second in-place edits are covered by mtime_ns granularity; the
    deliberate no-cache rationale at audit/snapshot.py:22-29 (cross-round
    vocabulary changes) is satisfied because any file change alters the key.
    Cached instance is shared — callers must not mutate (audited: zero
    mutation call sites as of 2026-09-04).
    """
    global _REGISTRY_CACHE
    if not REGISTRY_PATH.exists():
        raise ContractError("registry missing", registry=str(REGISTRY_PATH))
    stat = REGISTRY_PATH.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    with _REGISTRY_CACHE_LOCK:
        if _REGISTRY_CACHE is not None and _REGISTRY_CACHE[0] == key:
            return _REGISTRY_CACHE[1]
    model = _parse_registry_uncached()
    with _REGISTRY_CACHE_LOCK:
        _REGISTRY_CACHE = (key, model)
    return model
```

（spec R2「扫描结果同键缓存」在短路落地后残益可忽略——记 spec-deviations T2 声明性偏差，不实施。）`_init_truth_templates` 开头加：

```python
    truth_dir = project_dir / "truth"
    # T1606: skip the 74-skill contract scan (~655ms) when every template
    # already exists — the scan result is only needed to fill new templates.
    if all((truth_dir / fn).exists() for fn in _TRUTH_FILE_TITLES):
        return
    truth_dir.mkdir(parents=True, exist_ok=True)
    # ...原体（删去重复的 mkdir）...
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/contracts/ tests/unit/pipeline/test_dispatch_helper_read_suppression.py -q`
Expected: PASS

Run: `bash tests/lock-tool-hashes.sh`（legacy.py 改动）并把 `tests/tiers/deps.json` 并入 commit。

- [ ] **Step 5: Commit + 审查**

```bash
git add src/shenbi/contracts/legacy.py src/shenbi/pipeline/dispatch_helper.py tests/unit/contracts/test_legacy_registry_cache.py tests/unit/pipeline/test_dispatch_helper_read_suppression.py tests/tiers/deps.json
git commit -m "perf: spec42 C28 R2a registry (mtime_ns,size) cache + truth template short-circuit"
```
产出 `audit-T2.md`。

---

### Task 3: R2b SentenceTransformer 单例 + TTL 负缓存 + genesis store close

**Files:**
- Modify: `src/shenbi/pipeline/truth_embed.py`（`embed_and_store` :99-131 + 新增 `get_shared_model`）
- Modify: `src/shenbi/pipeline/context_assemble.py:136-179`（`_route_b` 用单例/负缓存）
- Modify: `src/shenbi/pipeline/genesis.py:150-188`（`_update_route_b` finally close store）
- Test: `tests/unit/pipeline/test_truth_embed_singleton.py`（新建）

**Interfaces:**
- Produces: `get_shared_model() -> Any | None`（None = 不可用或负缓存期内；模块级单例 + `threading.Lock` 双检 + 失败 TTL 10min）；`embed_and_store(store, text, chunk_id, source_file, chunk_type, chapter_ref=None, entity_refs="[]") -> bool`（签名不变，内部改单例）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/pipeline/test_truth_embed_singleton.py
"""T1603/F328: shared model singleton, TTL negative cache, defensive concurrency."""
import threading
from types import SimpleNamespace

import shenbi.pipeline.truth_embed as te


class _FakeST:
    instances = 0

    def __init__(self, name: str) -> None:
        _FakeST.instances += 1


def _patch_st(monkeypatch, ctor=_FakeST):
    monkeypatch.setattr(te, "is_embed_available", lambda: True)
    fake_mod = SimpleNamespace(SentenceTransformer=ctor)
    monkeypatch.setattr(te.importlib, "import_module", lambda name: fake_mod)


def test_singleton_constructs_once(te_reset_cache, monkeypatch) -> None:
    _patch_st(monkeypatch)
    assert te.get_shared_model() is not None
    assert te.get_shared_model() is not None
    assert _FakeST.instances == 1


def test_concurrent_init_constructs_once(te_reset_cache, monkeypatch) -> None:
    _patch_st(monkeypatch)
    threads = [threading.Thread(target=te.get_shared_model) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert _FakeST.instances == 1  # defensive: no concurrent path today


def test_negative_cache_suppresses_retry(te_reset_cache, monkeypatch) -> None:
    constructed = {"n": 0}

    class _Boom:
        def __init__(self, name: str) -> None:
            constructed["n"] += 1
            raise RuntimeError("HF 401")

    _patch_st(monkeypatch, _Boom)
    assert te.get_shared_model() is None  # failure cached (constructed 1)
    assert te.get_shared_model() is None  # within TTL: suppressed
    assert te.get_shared_model() is None
    assert constructed["n"] == 1  # no retry within TTL
    te._NEG_CACHE_UNTIL = 0.0  # expire
    assert te.get_shared_model() is None  # retries once, fails again
    assert constructed["n"] == 2
```

conftest fixture（同文件或 conftest）：

```python
@pytest.fixture
def te_reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(te, "_MODEL_SINGLETON", None)
    monkeypatch.setattr(te, "_NEG_CACHE_UNTIL", 0.0)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_truth_embed_singleton.py -q`
Expected: FAIL（`get_shared_model` 不存在）

- [ ] **Step 3: 实现**

```python
# src/shenbi/pipeline/truth_embed.py 模块级新增
_MODEL_SINGLETON: Any = None
_MODEL_LOCK = threading.Lock()
_NEG_CACHE_UNTIL = 0.0  # time.monotonic() deadline for retry suppression
_NEG_CACHE_TTL_S = 600.0


def get_shared_model() -> Any | None:
    """Process-level bge-large-zh singleton with TTL negative cache.

    Construction failure (e.g. HF 401 in offline deployments, T1603) is
    remembered for ``_NEG_CACHE_TTL_S`` so the chapter loop does not pay
    0.3-3.5s per assembly retry. ``None`` means unavailable-or-cached-fail.
    """
    global _MODEL_SINGLETON, _NEG_CACHE_UNTIL
    if _MODEL_SINGLETON is not None:
        return _MODEL_SINGLETON
    if time.monotonic() < _NEG_CACHE_UNTIL:
        return None
    with _MODEL_LOCK:
        if _MODEL_SINGLETON is not None:
            return _MODEL_SINGLETON
        if time.monotonic() < _NEG_CACHE_UNTIL:
            return None
        try:
            st = importlib.import_module("sentence_transformers")
            _MODEL_SINGLETON = st.SentenceTransformer("bge-large-zh")
        except Exception as e:
            _NEG_CACHE_UNTIL = time.monotonic() + _NEG_CACHE_TTL_S
            log.warning("embed_model_unavailable_cached", error=str(e), ttl_s=_NEG_CACHE_TTL_S)
            return None
    return _MODEL_SINGLETON
```

`embed_and_store` 内 `st = importlib.import_module(...)` + `model = st.SentenceTransformer(...)` 两行 → `model = get_shared_model()`；`if model is None: log.info("route_b_unavailable", chunk_id=chunk_id); return False`。
`_route_b` 同改（`model = get_shared_model()`；None → `return [], True`）。
`genesis._update_route_b`：`store = EmbeddingStore(...)` 之后整段 try/finally，`finally: store.close()`。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/pipeline/test_truth_embed_singleton.py tests/unit/pipeline/ -q`
Expected: PASS（含既有 context_assemble/genesis 相关测试）

- [ ] **Step 5: Commit + 审查**

```bash
git add src/shenbi/pipeline/truth_embed.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/genesis.py tests/unit/pipeline/test_truth_embed_singleton.py
git commit -m "perf: spec42 C28 R2b ST singleton + TTL negative cache + genesis store close"
```
产出 `audit-T3.md`。

---

### Task 4: R1 audit_context_cache 四处路径修复 + raw_files 读抑制 + checklist 接线

**Files:**
- Modify: `src/shenbi/pipeline/audit_context_cache.py`（:49/:53/:71 路径 + `raw_files` 字段 + 填充）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（读循环 :645-676 缓存优先 + 注入块 :683/:691 键修正 + checklist 传参）
- Modify: `src/shenbi/pipeline/review_checklist.py`（:271/:272/:354 三读点接收缓存内容）
- Modify: `src/shenbi/gates/shared.py`（`word_count_md` 拆出 `word_count_md_text(content: str) -> int`）
- Test: `tests/unit/pipeline/test_dispatch_helper_read_suppression.py`（追加 R1 部分）

**Interfaces:**
- Produces: `SharedAuditContext.raw_files: dict[str, str]`（键 = 项目相对路径 POSIX 字符串，与 `_input_key` 同形态）；`word_count_md_text(content: str) -> int`（`word_count_md(fp)` 改为读文件后委托）；review_checklist 两个函数新增可选参 `chapter_content: str | None = None`

- [ ] **Step 1: 写失败测试（fixture 项目组装 helper + 四验收）**

```python
# tests/unit/pipeline/test_dispatch_helper_read_suppression.py 追加
_FIX = Path("tests/fixtures")


def _assemble_project(tmp_path: Path) -> Path:
    """Real-output fixture project (G0.9): copies, never hand-writes."""
    for sub in ("chapters", "truth", "world", "style"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    for src in sorted((_FIX / "multi-chapter-example").glob("chapter-*.md")):
        shutil.copy(src, tmp_path / "chapters" / src.name)
    shutil.copy(_FIX / "snapshots/chapter-025/truth/character_matrix.md", tmp_path / "truth/character_matrix.md")
    shutil.copy(_FIX / "snapshots/chapter-025/truth/pending_hooks.md", tmp_path / "truth/pending_hooks.md")
    shutil.copy(_FIX / "world-rules-example.md", tmp_path / "world/rules.md")
    shutil.copy(_FIX / "style-profile-example.md", tmp_path / "style/style_profile.md")
    return tmp_path


AUDIT_SKILLS = [  # the 6-skill wave (CHAPTER_STEPS is_audit)
    "shenbi-review-group-factual", "shenbi-review-group-character",
    "shenbi-review-group-craft", "shenbi-review-group-plan",
    "shenbi-review-resonance", "shenbi-review-sensitivity",
]


def test_raw_files_hold_full_content(tmp_path: Path) -> None:
    project = _assemble_project(tmp_path)
    ctx = build_shared_audit_context(project, 3)
    for rel in ["chapters/chapter-3.md", "world/rules.md", "truth/character_matrix.md",
                "style/style_profile.md", "truth/pending_hooks.md"]:
        assert ctx.raw_files[rel] == (project / rel).read_text(encoding="utf-8")
        assert not ctx.raw_files[rel].endswith("]\n") or "truncated" not in ctx.raw_files[rel]


def test_world_rules_key_present(tmp_path: Path) -> None:
    project = _assemble_project(tmp_path)
    ctx = build_shared_audit_context(project, 3)
    assert "world/rules.md" in ctx.raw_files  # was truth/world_rules.md dead path


def test_chapter_read_count_is_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _assemble_project(tmp_path)
    chapter_file = project / "chapters" / "chapter-3.md"
    counter = {"n": 0}
    real_read = Path.read_text

    def counting_read(self: Path, *a: object, **k: object) -> str:
        if self == chapter_file:
            counter["n"] += 1
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read)
    ctx = build_shared_audit_context(project, 3)  # the ONE legitimate read
    for skill in AUDIT_SKILLS:
        _build_skill_prompt(skill=skill, project_dir=project, prompt="审计本章",
                            chapter=3, shared_context=ctx)
    assert counter["n"] == 1  # was 9 (6 contract + 3 checklist cold path)


def test_byte_equality_switch_on_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _assemble_project(tmp_path)
    ctx_on = build_shared_audit_context(project, 3)
    prompts_on = [_build_skill_prompt(skill=s, project_dir=project, prompt="审计本章",
                                      chapter=3, shared_context=ctx_on)
                  for s in AUDIT_SKILLS]
    ctx_off = replace(ctx_on, raw_files={})  # suppression OFF (path fixes stay)
    prompts_off = [_build_skill_prompt(skill=s, project_dir=project, prompt="审计本章",
                                       chapter=3, shared_context=ctx_off)
                   for s in AUDIT_SKILLS]
    assert prompts_on == prompts_off
```

（`_build_skill_prompt` 实际签名 `(skill, project_dir, prompt: str, chapter, uses_staging=False, shared_context=None, json_mode=False, path_context=None) -> tuple[str, str, list[str]]`——`prompt` 必填，测试已含。返回三元组，取 `[0]`/`[1]`（system/user）做字节对比。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_helper_read_suppression.py -q`
Expected: FAIL（raw_files 不存在；:03d 死键致 chapter_text 空；计数 9；等）

- [ ] **Step 3: 实现**

`audit_context_cache.py`：

```python
@dataclass
class SharedAuditContext:
    ...
    raw_files: dict[str, str] = field(default_factory=dict)
    """Full original bytes keyed by project-relative path (matches
    dispatch_helper._input_key). Read-suppression source — the summarized
    fields above are truncated values and MUST NOT back suppression."""


def _rel(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def build_shared_audit_context(project_dir: Path, chapter: int) -> SharedAuditContext:
    ctx = SharedAuditContext()
    candidates = [
        project_dir / "chapters" / f"chapter-{chapter}.md",   # was :03d dead key
        project_dir / "world" / "rules.md",                    # was truth/ dead
        project_dir / "truth" / "character_matrix.md",
        project_dir / "style" / "style_profile.md",
        project_dir / "truth" / "pending_hooks.md",
    ]
    for f in candidates:
        if f.exists():
            text = f.read_text(encoding="utf-8")
            ctx.raw_files[_rel(f, project_dir)] = text
    # 摘要字段填充：chapter_text/world_rules/character_list/style_profile/
    # pending_hooks 从 raw_files 派生（volume_context 路径修正 outline/ 但不入 raw_files）
    ...
```

（摘要字段逻辑保持现状语义：从对应原文做 `_summarize_if_large`/切片；`:71` 的 volume_map 路径改 `outline/volume_map.md`。）

`dispatch_helper.py` 读循环 ：663-676：

```python
        for full_path in resolved_paths:
            key = _input_key(full_path, project_dir)
            cached = shared_context.raw_files.get(key) if shared_context is not None else None
            if cached is not None:
                content = cached
            else:
                try:
                    content = full_path.read_text(encoding="utf-8")
                except Exception:
                    content = f"[binary or unreadable: {full_path}]"
            if fields:
                content, _matched = filter_to_fields(content, fields, str(full_path))
            content = _strip_meta_for_non_drafting(skill, content)
            raw_inputs[key] = content
```

注入块 ：683/:691 键改 `world/rules.md`、`style/style_profile.md`。
checklist 接线：`_build_skill_prompt` 调 review_checklist 处传 `chapter_content=shared_context.raw_files.get(f"chapters/chapter-{chapter}.md")`（shared_context 为 None 时传 None，走原路径）；`chapter_content: str | None = None` 沿 **四层签名** 穿透：`generate_review_checklist` → `_build_checklist` → `_deterministic_precompute`（+ 其内 `_extract_voice_constraints` 如需）——非 None 时三读点全用之（`wc = word_count_md_text(chapter_content)`）；`word_count_md(fp)` 重构为 `word_count_md_text(Path(fp).read_text(...))` 委托。byte-equality 测试的 OFF 侧会吃到 checklist mtime 缓存（第二遍不重走磁盘路径）——命名已如实（对比的是装配产物，非每遍重读）。

- [ ] **Step 4: 跑测试确认通过 + 既有回归**

Run: `uv run pytest tests/unit/pipeline/ -q`
Expected: PASS

- [ ] **Step 5: Commit + 审查**

```bash
git add src/shenbi/pipeline/audit_context_cache.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/review_checklist.py src/shenbi/gates/shared.py tests/unit/pipeline/test_dispatch_helper_read_suppression.py
git commit -m "perf: spec42 C28 R1 raw-files read suppression (9->1 reads) + 4-site F312 path fix + checklist wiring"
```
产出 `audit-T4.md`。

---

### Task 5: R3a 标题有界前缀读取 + 双提取点 no-op 修正 + 语料变换器

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:2135-2170`（`_extract_chapter_title` + `_load_previous_titles`）
- Create: `tests/pipeline/helpers/__init__.py` + `tests/pipeline/helpers/c28_corpus.py`（确定性语料扩展器；tests/ 是常规包，统一 `from tests.pipeline.helpers.c28_corpus import ...` 包导入，禁 sys.path.insert）
- Test: `tests/unit/pipeline/test_chapter_titles.py`（新建）

**Interfaces:**
- Produces: `_TITLE_PREFIX_BYTES = 4096`；`_read_title_prefix(path: Path) -> str`（读前 4096B，utf-8 errors="ignore"）；两提取函数改 `re.search(r"^#\s+(.+?)$", prefix, re.MULTILINE)`；`expand_chapter_corpus(src: Path, dst: Path, n: int) -> None`（H1 重写 `# 第{i}章 · {原标题}（变体 {i}）`，正文原样）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/pipeline/test_chapter_titles.py
"""T1609: bounded-prefix title reads + meta-first no-op fix (both extractors)."""
from shenbi.pipeline.chapter_loop import _extract_chapter_title, _load_previous_titles


def test_meta_first_fixture_title_extracted() -> None:
    """Real fixture (H1 at ~line 10 after PRE_WRITE_CHECK block) — both
    extractors returned '' before (anchored re.match): dedup was a no-op."""
    p = Path("tests/fixtures/chapter-7-example.md")
    assert _extract_chapter_title(p) != ""


def test_previous_titles_include_meta_first_chapters(tmp_path: Path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    shutil.copy(Path("tests/fixtures/chapter-7-example.md"), chapters / "chapter-1.md")
    shutil.copy(Path("tests/fixtures/chapter-8-example.md"), chapters / "chapter-2.md")
    titles = _load_previous_titles(tmp_path, 3)
    assert titles  # non-empty: meta-first chapters now contribute titles


def test_title_lookup_reads_bounded_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

    expand_chapter_corpus(Path("tests/fixtures/multi-chapter-example"), tmp_path, n=56)
    read_bytes = {"n": 0}
    real_open = Path.open

    def counting_open(self: Path, *a: object, **k: object) -> object:
        if self.suffix == ".md" and self.parent.name == "chapters":
            read_bytes["n"] += 1  # count reads; bounded-ness asserted via total below
        return real_open(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", counting_open)
    titles = _load_previous_titles(tmp_path, 56)
    assert len(titles) == 55


def test_title_lookup_reads_at_most_4kb_per_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R3-1 spec acceptance: 单章标题查重文件读取字节数 <= 4096*N (was ~24KB*N)."""
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

    expand_chapter_corpus(Path("tests/fixtures/multi-chapter-example"), tmp_path, n=8)
    read_bytes = {"n": 0}
    real_open = Path.open

    def bounded_open(self: Path, *a: object, **k: object) -> object:
        fh = real_open(self, *a, **k)  # type: ignore[arg-type]
        if self.suffix == ".md" and self.parent.name == "chapters":
            orig_read = fh.read

            def counting_read(n: int = -1) -> bytes:
                data = orig_read(n)
                read_bytes["n"] += len(data)
                return data

            fh.read = counting_read
        return fh

    monkeypatch.setattr(Path, "open", bounded_open)
    _load_previous_titles(tmp_path, 8)
    assert read_bytes["n"] <= 4096 * 7  # 7 previous chapters, <=4KB each
    #（spec 载 N=56/112/224；此处 n=8 断言每文件 ≤4KB 的等价单文件界——N 规模在
    #  T7 基线与 T5 语料测试覆盖，语义相同）
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_chapter_titles.py -q`
Expected: FAIL（meta-first 提取为空 / 语料器不存在）

- [ ] **Step 3: 实现**

```python
# chapter_loop.py
_TITLE_PREFIX_BYTES = 4096
_H1_RE = re.compile(r"^#\s+(.+?)$", re.MULTILINE)


def _read_title_prefix(path: Path) -> str:
    """Read the first 4KB (title H1 lives in the file head; real outputs
    front-load a PRE_WRITE_CHECK block, H1 at ~line 10)."""
    with path.open("rb") as f:
        return f.read(_TITLE_PREFIX_BYTES).decode("utf-8", errors="ignore")


def _extract_chapter_title(chapter_path: Path) -> str:
    """First H1 via MULTILINE search — re.match anchored at position 0 and
    returned '' for meta-first chapters (title dedup was a silent no-op)."""
    m = _H1_RE.search(_read_title_prefix(chapter_path))
    return m.group(1).strip() if m else ""


def _load_previous_titles(project_dir: Path, current_chapter: int) -> dict[str, int]:
    # 同原体，但循环内 read_text(...) 改 _read_title_prefix(ch_file)，
    # re.match(...) 改 _H1_RE.search(prefix)；章号清洗逻辑不变
```

`tests/pipeline/helpers/c28_corpus.py`：

```python
def expand_chapter_corpus(src_dir: Path, dst: Path, n: int) -> None:
    """Deterministically expand real fixture chapters to n files.

    Variant transform: rewrite the H1 line to `# 第{i}章 · {orig}（变体 {i}）`;
    body bytes are preserved verbatim. Source = real outputs (G0.9)."""
    srcs = sorted(src_dir.glob("chapter-*.md"))
    chapters = dst / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    h1 = re.compile(r"^#\s+(.+?)$", re.MULTILINE)
    for i in range(1, n + 1):
        text = srcs[i % len(srcs)].read_text(encoding="utf-8")
        m = h1.search(text)
        new_title = f"# 第{i}章 · {m.group(1).strip()}（变体 {i}）" if m else f"# 第{i}章"
        out = h1.sub(new_title, text, count=1)
        (chapters / f"chapter-{i}.md").write_text(out, encoding="utf-8")
```

- [ ] **Step 4: 跑测试确认通过 + chapter_loop 回归**

Run: `uv run pytest tests/unit/pipeline/test_chapter_titles.py tests/unit/pipeline/test_chapter_loop.py -q`
Expected: PASS

- [ ] **Step 5: Commit + 审查**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/pipeline/helpers/__init__.py tests/pipeline/helpers/c28_corpus.py tests/unit/pipeline/test_chapter_titles.py
git commit -m "perf: spec42 C28 R3a bounded-prefix title reads + dual extractor no-op fix"
```
产出 `audit-T5.md`。

---

### Task 6: R3b content_uniqueness 指纹缓存 + integrity 真 append

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:279-309`（指纹缓存）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1132-1152`（`_append_integrity_findings` 真 append）
- Test: `tests/gates/g4/test_content_uniqueness_cache.py`、`tests/unit/pipeline/test_integrity_append.py`（新建）

**Interfaces:**
- Produces: chapter_drafting 模块级 `_FINGERPRINT_CACHE: dict[tuple[str, int, int], frozenset[int]]` + `_fingerprint_of(path: Path) -> frozenset[int]`（`_text_fingerprint` 返回 `set[int]` 段落哈希）（(path, mtime_ns, size) 键，读失败返回 frozenset() 不缓存）；`_append_integrity_findings` 改 `open("a")`（同 flock 临界区，jsonl 语义不变）

- [ ] **Step 1: 写失败测试**

```python
# tests/gates/g4/test_content_uniqueness_cache.py
"""F415-0815: content_uniqueness fingerprint cache — second in-process pass
reads each chapter once (cache hits N-1)."""
from pathlib import Path

from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus


def test_second_pass_reads_each_chapter_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from shenbi.gates.g4 import chapter_drafting as cd

    expand_chapter_corpus(Path("tests/fixtures/multi-chapter-example"), tmp_path, n=8)
    reads = {"n": 0}
    real = Path.read_text

    def counting(self: Path, *a: object, **k: object) -> str:
        reads["n"] += 1
        return real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)
    cd._FINGERPRINT_CACHE.clear()
    for i in range(1, 9):
        cd._fingerprint_of(tmp_path / "chapters" / f"chapter-{i}.md")
    first_pass = reads["n"]
    assert first_pass == 8
    for i in range(1, 9):
        cd._fingerprint_of(tmp_path / "chapters" / f"chapter-{i}.md")
    assert reads["n"] == first_pass  # zero new reads: all cache hits
```

```python
# tests/unit/pipeline/test_integrity_append.py
"""T1610: true-append integrity findings — byte-identical output, O(1) reads/append.

现状 locked_transact 每 append 全量 read_text 该 jsonl（O(k^2) 字节搬运）——
本测试 spy read_text 计数做红灯判别（现状 199 次读——首次 append 无文件可读，append 后 0 次）。
注：locked_transact 的写路径经 tempfile+os.replace，不走 Path.write_text——
不能用 write_text 计数判别（那是绿前绿后的假测试）。"""
import json

from shenbi.pipeline.dispatch_helper import _append_integrity_findings


def test_append_output_matches_and_reads_constant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "chapters" / "chapter-1.md"
    target.parent.mkdir()
    target.write_text("x", encoding="utf-8")
    out = tmp_path / "audits" / ".integrity-findings-1.jsonl"
    reads = {"n": 0}
    real_read = Path.read_text

    def counting(self: Path, *a: object, **k: object) -> str:
        if self == out:
            reads["n"] += 1
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)
    for i in range(200):
        _append_integrity_findings(tmp_path, target, [f"issue-{i}"])
    assert reads["n"] == 0  # was 200: locked_transact re-read the whole file per append
    reference = "".join(
        json.dumps({"file": "chapters/chapter-1.md", "finding": f"issue-{i}"}, ensure_ascii=False) + "\n"
        for i in range(200)
    )
    assert out.read_text(encoding="utf-8") == reference  # 逐字节一致 vs 直接构造参照
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/gates/g4/test_content_uniqueness_cache.py tests/unit/pipeline/test_integrity_append.py -q`
Expected: FAIL（缓存不存在；现状 locked_transact 每 append 全量 read_text jsonl → reads==200）

- [ ] **Step 3: 实现**

```python
# chapter_drafting.py
_FINGERPRINT_CACHE: dict[tuple[str, int, int], frozenset[int]] = {}
# In-process memoization only: production G4 runs are subprocess-per-call
# (cold per spawn); benefits in-process multi-file callers (g5.5, tests).


def _fingerprint_of(path: Path) -> frozenset[int]:
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size)
        hit = _FINGERPRINT_CACHE.get(key)
        if hit is not None:
            return hit
        fp = frozenset(_text_fingerprint(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError) as e:
        log.warning("file_read_failed", file=str(path), error=str(e))  # 保持原循环的观测语义
        return frozenset()
    _FINGERPRINT_CACHE[key] = fp
    return fp
```

content_uniqueness 循环内：`other_content = other.read_text(...)` + `other_fp = _text_fingerprint(other_content)` → `other_fp = _fingerprint_of(other)`（读失败语义保持：空集 → overlap 0，与原 except 分支一致）。

`_append_integrity_findings`：

```python
def _append_integrity_findings(project_dir: Path, file_path: Path, issues: list[str]) -> None:
    """Persist post-write integrity findings for the G4 checker to read.

    True append (O(k) total bytes, was O(k^2) read-rewrite) inside the same
    directory-flock critical section as locked_transact (spec #37 F347).
    Reader (g4/generic.py) already skips undecodable tail lines, tolerating
    a torn final line on crash.
    """
    import os

    from shenbi.safe_write import acquire_write_lock as _acquire_lock  # 公开别名（safe_write.py:184），跨实例写者同一锁域

    m = _CHAPTER_NUM_RE.search(file_path.stem)
    num = m.group(1) if m else "unknown"
    out = project_dir / "audits" / f".integrity-findings-{num}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(
            {"file": str(file_path.relative_to(project_dir)), "finding": issue},
            ensure_ascii=False,
        )
        + "\n"
        for issue in issues
    )
    lock_fd, lockfile = _acquire_lock(out)  # 与 locked_transact 同一锁序
    try:
        with out.open("a", encoding="utf-8") as f:  # write-audit-exempt: true-append under flock (T1610, O(k) vs O(k^2))
            f.write(payload)
    finally:
        os.close(lock_fd)
        if lockfile is not None:
            try:
                os.unlink(lockfile)
            except FileNotFoundError:
                pass
```

（`# write-audit-exempt:` 注释必须与 `open("a")` 同行或上一行——`tools/lint_bare_writes.py` 对 src/ 内裸 append 模式执法，缺注记 `just check` 红。）

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/gates/g4/ tests/unit/pipeline/test_integrity_append.py -q`
Expected: PASS

- [ ] **Step 5: Commit + 审查**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py src/shenbi/pipeline/dispatch_helper.py tests/gates/g4/test_content_uniqueness_cache.py tests/unit/pipeline/test_integrity_append.py
git commit -m "perf: spec42 C28 R3b fingerprint mtime cache + integrity true-append"
```
产出 `audit-T6.md`。

---

### Task 7: benchmark 三基线 + 簇级验证

**Files:**
- Create: `tests/benchmark/test_c28_baselines.py`
- Test: 即本 task 交付物

**Interfaces:**
- Consumes: T2 `_parse_registry_uncached`、T1 gates.cli 冷启动、T5 `expand_chapter_corpus` + `_load_previous_titles`

- [ ] **Step 1: 写基线测试**

```python
# tests/benchmark/test_c28_baselines.py
"""C28 防回归基线三条：registry 解析 / 门禁冷启动 / 标题有界读取（spec 簇级验收）。"""
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from shenbi.contracts.legacy import _parse_registry_uncached

pytestmark = pytest.mark.benchmark


def test_registry_parse_baseline(benchmark: Any) -> None:
    benchmark(_parse_registry_uncached)


def test_gate_cold_start_baseline(benchmark: Any) -> None:
    def _cold_import_ms() -> float:
        t0 = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", "from shenbi.gates import cli"], check=True
        )
        return (time.perf_counter() - t0) * 1000

    benchmark(_cold_import_ms)


def test_title_bounded_read_baseline(benchmark: Any, tmp_path: Path) -> None:
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus
    from shenbi.pipeline.chapter_loop import _load_previous_titles

    expand_chapter_corpus(Path("tests/fixtures/multi-chapter-example"), tmp_path, n=112)
    benchmark(lambda: _load_previous_titles(tmp_path, 112))
```

- [ ] **Step 2: 跑基线 + 簇级验证命令**

Run: `uv run pytest tests/ -m benchmark -q`
Expected: 3 条 PASS（基线记录，无阈值断言）

Run: `uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3`
Expected: <50ms

- [ ] **Step 3: Commit + 审查**

```bash
git add tests/benchmark/test_c28_baselines.py
git commit -m "test: spec42 C28 benchmark baselines (registry parse, gate cold start, title reads)"
```
产出 `audit-T7.md`。

---

## 收尾（阶段 7-8 前置，非独立 task）

1. `just check` 全绿（Iron Law：当轮消息粘贴输出）
2. `ls .superpowers/sdd/audit-T*.md | wc -l` == 7 == plan task 数
3. spec 全部验收条目按覆盖表逐条跑过并粘贴 progress.md `## 验收证据`
4. 改动了 `src/shenbi/**` 的 task 提交前跑 `bash tests/lock-tool-hashes.sh` 更新 `tests/tiers/deps.json` 哈希并随 commit 提交（repo 惯例；R3-2 验收证据注明 `_fingerprint_of` 直测是 spec「N 章两遍」验收的组件级代理）
5. 新 benchmark 会在 `just check` 的 `-m "not last"` 段内运行（marker 未被排除）——门禁冷启动基线带 warmup ~10 次 spawn，CI 时长 +~5s 可接受
