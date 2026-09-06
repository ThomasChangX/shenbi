# C29 截断/采样/排序可观测性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一切输入截断、检查面采样、章号排序都留痕可审计（spec #43 C29，8 条 findings：F361/F330/F362/F459/F235/F326/F620 + T1615 观测）。

**Architecture:** 纯函数层加披露元数据（截断 meta / sampled 标志），调用方落 structlog WARN 并把披露字段写进 gate 结果 JSON；排序经单一 numeric 章号 key helper 替换三处字典序调用点。无新依赖、无 schema 破坏（gate 结果为加键）。

**Tech Stack:** Python 3.11+ / pydantic / structlog / pytest（fixtures 驱动，无真实 dispatch）。

## Global Constraints

- 全部 task 均为 **infra**（触及 `src/shenbi/pipeline/`、`gates/`、`trace/`）→ 协调者亲自实现，不分派 implementer 子 agent；每 task commit 后必须产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审）
- 框架纯度：`src/shenbi/` 禁 `print()`，用 structlog；gate 检查器保持纯函数幂等（写结果 JSON 字段可以，写文件不行）
- G0.9：新 fixture 一律由 `tests/fixtures/` 真实产物拼接/派生（测试内生成器），禁手写 mock 内容
- 验证命令走 `uv run` / `just`（与 CI 同构）；禁止真实 `shenbi-dispatch` / `pipeline` 子命令
- 状态字面量不新增（无新 Literal）；conventional commits

---

### Task 1: R1 截断标记协议 + 预算回补（F361 + F330 + F362）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:314-337`（`_budgeted_truncate`）及调用点 `:728`
- Modify: `src/shenbi/pipeline/audit_context_cache.py:96-98`（pending_hooks 截断）
- Test: `tests/pipeline/test_budgeted_truncate.py`（扩展；**既有 3 个测试须同步改写**——返回值从 dict 变 tuple，`result.get(...)`/`.values()` 全要改为解包后取 texts）

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class TruncateRecord:
      file: str
      original_len: int
      kept_len: int
      offset: int  # 0（现实现只做头部截取）

  def _budgeted_truncate(
      input_texts: dict[str, str], budget: int
  ) -> tuple[dict[str, str], list[TruncateRecord]]  # (texts_with_marker, records)
  ```
  标记格式：`"\n\n[TRUNCATED {kept}/{orig} chars]"`，**在 per-file cap 切片之后追加**（永不被切掉）。调用方对每条 record 发一条 structlog WARN（event `input_truncated`，含 file/original_len/kept_len）。

- [ ] **Step 0: 被动基线（spec 最小实证前置）**

Run: `grep -rn "input_over_budget_applying_priority_truncation\|\[\.\.\. truncated from" .superpowers tests/rounds 2>/dev/null | head -20`（若仓内无既有 round 日志 → 0 命中，记 deviation 供用户裁决，不阻塞——测试驱动的功能验收独立成立）

- [ ] **Step 1: 写失败测试**

```python
# tests/pipeline/test_budgeted_truncate.py 追加（同时改写既有 3 个测试为 tuple 解包；import 处补 `_INPUT_MAX_CHARS_TOTAL, _INPUT_MAX_CHARS_PER_FILE`）

def test_marker_survives_per_file_cap():
    """F361: 标记必须在 cap 切片之后追加，不可被 32K cap 切掉。"""
    huge = "A" * 60000  # allocation 会 > 32000 的超长文件
    texts, records = _budgeted_truncate({"chapter-N.md": huge}, _INPUT_MAX_CHARS_TOTAL)
    out = texts["chapter-N.md"]
    assert out.endswith("] chars]")  # 标记在末尾存活
    assert "[TRUNCATED " in out
    assert len(records) == 1 and records[0].original_len == 60000

def test_budget_surplus_redistributed():
    """F330: 短文件余量回补给被截断文件，且不越过 per-file cap。"""
    texts = {
        "chapter-N.md": "X" * 40000,      # HIGH，配额 16667 会被截
        "archive-notes.md": "Y" * 1000,   # LOW，配额 3333 只用 1000 → 余量 2333
    }
    out, records = _budgeted_truncate(texts, 20000)
    kept = records[0].kept_len
    # 纯按权重分配 = 16667；回补后必须超过它（16667 + 2333 ≈ 19000）
    assert kept > 17000
    # 回补不得越过 cap
    assert len(out["chapter-N.md"]) <= _INPUT_MAX_CHARS_PER_FILE + 64  # +标记长度余量

def test_no_truncation_no_records():
    texts = {"a.md": "short"}
    out, records = _budgeted_truncate(texts, 10000)
    assert records == [] and out == {"a.md": "short"}
```

（>32K 输入由测试内 `"A" * 60000` 合成字符构成——这是对纯函数的输入，非 skill 产物 fixture，G0.9 不适用；dispatch 集成面用 Step 4 structlog capture 断言。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_budgeted_truncate.py -q`
Expected: 新测试 FAIL（返回值仍是 dict、无标记存活保证）

- [ ] **Step 3: 实现**

```python
def _budgeted_truncate(input_texts: dict[str, str], budget: int) -> tuple[dict[str, str], list[TruncateRecord]]:
    if not input_texts:
        return {}, []
    weights = {name: _get_priority(name) for name in input_texts}
    total_weight = sum(weights.values())
    # Pass 1: proportional allocation
    alloc = {name: int(budget * w / total_weight) for name, w in weights.items()}
    kept: dict[str, int] = {}
    for name, content in input_texts.items():
        kept[name] = min(len(content), min(alloc[name], _INPUT_MAX_CHARS_PER_FILE))
    # Pass 2 (F330): redistribute surplus from files allocated more than they need
    surplus = sum(max(0, min(alloc[n], _INPUT_MAX_CHARS_PER_FILE) - kept[n]) for n in input_texts)
    # 补给循环：只补给仍被截的文件，按权重降序（HIGH 先得）
    for name in sorted(input_texts, key=lambda n: -weights[n]):
        need = min(len(input_texts[name]), _INPUT_MAX_CHARS_PER_FILE) - kept[name]
        if need > 0 and surplus > 0:
            give = min(need, surplus)
            kept[name] += give
            surplus -= give
    # Pass 3: build outputs — 标记在 cap 切片之后追加（F361 修复）
    result: dict[str, str] = {}
    records: list[TruncateRecord] = []
    for name, content in input_texts.items():
        k = kept[name]
        if k < len(content):
            result[name] = content[:k] + f"\n\n[TRUNCATED {k}/{len(content)} chars]"
            records.append(TruncateRecord(file=name, original_len=len(content), kept_len=k, offset=0))
        else:
            result[name] = content
    return result, records
```
调用点（dispatch_helper.py:723-741）改两处：
1. 超预算路径 `:728`：`input_texts, trunc_records = _budgeted_truncate(...)`，随后
   ```python
   for rec in trunc_records:
       log.warning("input_truncated", file=rec.file, original_len=rec.original_len, kept_len=rec.kept_len)
   ```
2. **欠预算路径 `:733-741`（F361 主形态——per-file cap 静默截断）**：dict comprehension 改为循环，超过 `_INPUT_MAX_CHARS_PER_FILE` 的文件走同一标记格式 + 同一 `input_truncated` WARN（抽一个模块内小 helper `_cap_single(text: str, fname: str) -> str` 复用标记与 log）。
摘除 `:314` 行过时的 `# pyright: ignore[reportUnusedFunction]`。audit_context_cache.py:97 改为：
```python
if len(raw) > 3000:
    ctx.pending_hooks = raw[:3000] + f"\n\n[TRUNCATED 3000/{len(raw)} chars]"
    log.warning("pending_hooks_truncated", original_len=len(raw))
else:
    ctx.pending_hooks = raw
```
（logger 已存在于模块 `:13` `log = get_logger(__name__)`，无需新增；`_summarize_if_large` 的旧标记同步改为新哨兵格式保持一致。）

- [ ] **Step 4: 跑测试确认通过 + structlog capture**

Run: `uv run pytest tests/pipeline/test_budgeted_truncate.py -q` → PASS；补一条用 `caplog`/structlog 捕获断言 `input_truncated` WARN 的测试（调 `_budgeted_truncate` 的调用方逻辑可经直接调用 helper 后手动复现 log 行，或对 `_summarize_if_large` 场景断言）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/audit_context_cache.py tests/pipeline/test_budgeted_truncate.py
git commit -m "feat: C29 R1 truncation marker protocol — cap-proof sentinel, surplus redistribution, WARN logs (F361/F330/F362)"
```

- [ ] **Step 6: audit-T1.md**（fresh-context 子 agent 全量重审本 task 改动文件）

---

### Task 2: R2 字符截取采样披露（F459 + F235）

**Files:**
- Create: helper 于 `src/shenbi/gates/shared.py`
- Modify: `src/shenbi/gates/g5.py:154,189`、`src/shenbi/gates/g6.py:224,234,291`、`src/shenbi/gates/g6_checks.py:37` 及 `_chapter_text(ch, 3000)` 两处调用（:70/:89，属 **G6.4 check_continuity** 双 pass——直接改 `_chapter_text` 内部走 `clip_with_disclosure` 并向调用方回传 sampled，聚合进 **G6.4** check dict；G6.10 `check_style_consistency` 读全文无字符截取，不在改面）（g5.py:187 属计数型采样，归 Task 3，不在本 task）
- Modify: `src/shenbi/gates/g4/genre_config.py:38-48`（全量错误计数）
- Modify: `src/shenbi/gates/g7.py:186-194`（G7.13 重跑分支透传 sampling_disclosed）
- Test: `tests/unit/gates/test_sampling_disclosure.py`（新建）

**Interfaces:**
- Produces（`src/shenbi/gates/shared.py`）:
  ```python
  def clip_with_disclosure(text: str, limit: int) -> tuple[str, bool]:
      """Return (text[:limit], sampled_flag). Pure, no side effects."""
  ```
  各 check dict 加键 `"input_sampled": True`（仅发生过截取时加；未截取不加，保持输出精简）。顶层 `sampling_disclosed` 机制：`GateResult` TypedDict（`src/shenbi/status.py:85`，total=False）加可选键 `sampling_disclosed: str`；`gate_G5`/`gate_G6` 在最终 `passed()/fail()` 前聚合 checks 计算 `"n/m checks ran on sampled input"`——实现方式：两个 gate 函数结尾改为先构造 `result: GateResult` dict、加键、再 `json.dumps`（不走 `passed()` 的固定形状；或给 `shared.py` 加可选参数 `extra: GateResult | None = None` 合并——实现时任选其一，禁止改 `passed()/fail()` 既有调用方语义）。schema 文档同步：`docs/framework/gates.md` 增补 `sampling_disclosed`/`input_sampled` 字段说明（C8 词表单源协同）。
- 消费方（dead-wire 防护，**接真实读方**）：`gates/g7.py:186-199`（G7.13 重跑 gate_G6 比对结果的真实消费点）——重跑循环中**收集**每次 `rerun.get("sampling_disclosed")` 非 None 的值（跨多个 marker 聚合，不只留最后一个），循环后**扩写既有** `c.append({"id": "G7.13", "s": PASS, "note": ...})` 的 note（g7.py:197-199）：拼接聚合到的全部 `sampling_disclosed`（**不新增第二条 G7.13 check**，避免重复 check dict）；`write_gate_marker` 持久化的 PASS JSON 自带该字段（操作员/G7 可见）。**不要接 audit_layer**（它只跑 G4，看不到该字段——plan review C3）。

- [ ] **Step 1: 失败测试** — 用 `tests/fixtures/chapter-10-draft.md` 拼接成 >5000 字临时文件（tmp_path + 真实产物内容复制，G0.9 合规），对 `clip_with_disclosure` 断言 `(prefix, True)`；对 `check_continuity`（g6_checks）传 chapter fixture 列表断言结果 violations 之外的 check 元数据含 `input_sampled`；genre_config 用真实 `tests/fixtures` 下 genre/JSON 配置构造 ValidationError 场景断言 mf 含 `+N more` 计数行
- [ ] **Step 2:** `uv run pytest tests/unit/gates/test_sampling_disclosure.py -q` → FAIL
- [ ] **Step 3:** 实现 helper + 六处 `[:3000]`/`[:5000]` 改 `text, sampled = clip_with_disclosure(...)`，check dict 条件加键；genre_config 改为：
  ```python
  errors = e.errors()
  for err in errors[:5]:
      mf.append(f"G4.gc.{Path(gc_path).name}:{err['loc']}: {err['msg']}")
  if len(errors) > 5:
      mf.append(f"G4.gc.{Path(gc_path).name}: +{len(errors) - 5} more errors (total {len(errors)})")
  ```
  gate_G5/gate_G6 顶层聚合 `"sampling_disclosed"` 摘要；audit_layer 接线如上
- [ ] **Step 4:** 同命令 → PASS
- [ ] **Step 5:** `git add` 列出的文件，commit `feat: C29 R2 sampling disclosure — clip_with_disclosure, input_sampled fields, genre-config full error count (F459/F235)`
- [ ] **Step 6:** audit-T2.md

---

### Task 3: R2b 计数型采样披露 + 采样策略成文（F459 补全面）

**Files:**
- Modify: `src/shenbi/gates/g5.py:147,152,187,199`、`src/shenbi/gates/g6.py:223,233,294`
- Create: `docs/framework/sampling-policy.md`
- Test: `tests/unit/gates/test_sampling_disclosure.py`（扩展）

**Interfaces:**
- Produces: check dict 键 `files_sampled: "3/12"`（输入文件型：g5:147/152/187、g6:223）；`findings_capped: "10/N"`（输出封顶型：g5:199 conflicts、g6:233 catchphrases、g6:294 constraints）。分母 N 为截取前列表全长。
- [ ] **Step 1:** 失败测试 — tmp_path 下由真实 fixture 复制 >12 个 outline md，跑 G5.3（经 `gate_G5` 或直接内层函数）断言 check 含 `files_sampled` 且分母正确
- [ ] **Step 2:** 跑 → FAIL
- [ ] **Step 3:** 实现：各截取点改 `lst[:n]` → 先 `total = len(lst); capped = lst[:n]`，check dict 加对应键；写 `docs/framework/sampling-policy.md`（表格：check id / 采样点 / 量 / 理由，覆盖 R2 的 [:3000]/[:5000] 与本 task 全部计数点）
- [ ] **Step 4:** 跑 → PASS
- [ ] **Step 5:** commit `feat: C29 R2b count-sampling disclosure + sampling policy doc`
- [ ] **Step 6:** audit-T3.md

---

### Task 4: R3 章号数值排序（F326）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（helper 定义）+ `src/shenbi/pipeline/cli.py:928`、`chapter_loop.py:391`、`src/shenbi/gates/g6.py:68`（g6 侧用**惰性 import**，先例 g6.py:124，避免把 pipeline 重依赖图拉进 gates 顶层）
- Test: `tests/unit/pipeline/test_chapter_sort.py`（新建）

**Interfaces:**
- Produces:
  ```python
  def chapter_sort_key(name_or_num: str | Path) -> tuple[int, str]:
      """`chapter-10.md` / `10` / Path → (10, 原字符串)；非数字稳定排后。"""
      import re
      s = str(name_or_num)
      m = re.search(r"(\d+)", s)
      return (int(m.group(1)), s) if m else (10**9, s)
  ```
  （`str()` 先转——g6.py:68 传入的是 Path 对象。）
- [ ] **Step 1:** 失败测试 — 用 `tests/fixtures/chapter-{2..10}-draft.md`（9 个真实稿全存在）文件名列表断言 `sorted(names, key=chapter_sort_key)` 为 2,3,…,10；对 `cmd_chapters` 构造含 `"10"`/`"2"` 键的 chapter_states（真实 state 数据结构，pydantic model 构造）断言输出顺序
- [ ] **Step 2:** → FAIL（现行字典序 10 在 2 前）
- [ ] **Step 3:** 三处 `sorted(...)` 加 `key=chapter_sort_key`（cli.py:928 对 items 的 key 元素取 `chapter_sort_key(kv[0])`；g6.py:68 `sorted(ch_dir.glob("chapter-*.md"), key=chapter_sort_key)`；chapter_loop.py:391 同理）
- [ ] **Step 4:** → PASS
- [ ] **Step 5:** commit `fix: C29 R3 numeric chapter sort across cli/audit-history/G6 traversal (F326)`
- [ ] **Step 6:** audit-T4.md

---

### Task 5: R4 replay 截断 WARN（F620）

**Files:**
- Modify: `src/shenbi/trace/replay.py:20-49`
- Test: `tests/unit/trace/test_replay.py`（扩展，沿用既有 TraceWriter fixture 构造法）

**Interfaces:** `replay(round_dir: Path) -> list[TraceEvent]` 签名不变；新增行为：torn line / signature gap 截断时 `log.warning("replay_truncated", path=str(path), kept_chars=keep_chars, dropped_chars=len(raw) - keep_chars, kept_events=len(out), drop_reason=reason)`（reason ∈ {"torn_line", "signature_gap"}；行号范围由 kept_chars/内容长度可推，如需精确可在循环中记最后有效行号），模块顶部 `from shenbi.logging import get_logger` + `log = get_logger(__name__)`（仓内规范 import，非 structlog 直引）。
- [ ] **Step 1:** 失败测试 — 复用既有 `test_replay_truncates_torn_tail` 构造法（TraceWriter 写合法链 + 追加撕裂行），structlog capture 断言 `replay_truncated` WARN 含 dropped_chars>0，且返回事件数正确
- [ ] **Step 2:** → FAIL
- [ ] **Step 3:** 实现（两个 `break` 点改为记录 reason 后 break，函数尾部 `if keep_chars < len(raw):` 处发 WARN 再 `safe_write`）
- [ ] **Step 4:** → PASS
- [ ] **Step 5:** commit `feat: C29 R4 replay truncation WARN with dropped-byte accounting (F620)`
- [ ] **Step 6:** audit-T5.md

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 标记/WARN/回补 | T1 | `uv run pytest tests/pipeline/test_budgeted_truncate.py -q` |
| 被动基线 | T1 Step 0 | grep 既有信号，输出记 progress.md |
| R2 input_sampled + schema 同步 | T2 | `uv run pytest tests/unit/gates/test_sampling_disclosure.py -q` + `just gate G6 <pipeline> <round> <project>` 抽查（fixture round） |
| R2b files_sampled + policy 文档 | T3 | 同上测试 + `ls docs/framework/sampling-policy.md` |
| R3 排序 | T4 | `uv run pytest tests/unit/pipeline/test_chapter_sort.py -q` + fixture round 下 `uv run shenbi-pipeline chapters` 人工核对 2..10 |
| R4 replay WARN | T5 | `uv run pytest tests/unit/trace/test_replay.py -q` |
| 簇级回归 | 全部 | `just check` 全绿 |

T1615：不在本簇修；注入量观测由 R1 的 `input_truncated` WARN（original_len 字段）提供最小可观测性，量化归 C10/C28。
