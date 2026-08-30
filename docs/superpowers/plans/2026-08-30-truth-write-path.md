# Truth 写路径（SDD #21 · R1+R2+R3）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** truth 文件写读路径三处根因修复——R1 resonance_trend 框架写者 insert-only + 9 列对齐；R2 pending_hooks 单一表感知解析源 `truth_readers.read_pending_hooks` 三方接线；R3 staging 双写者 last-writer-wins（链式合并基 + per-path lock + sidecar 化 commit 增量重放）+ 一次性 staging 清理。

**Architecture:** R1 在 `truth_io` 新增 `insert_markdown_row` mode（锁内原子判定 key 存在即跳过，消除 check-then-act 竞态），`chapter_loop` 只换 mode；R2 新模块 `src/shenbi/pipeline/truth_readers.py` 为唯一解析源，`context_curation._read_pending_hooks`、`gates/g6.py` G6.7、`truth_index._index_hooks`(body 源) 改调它；R3 改 `dispatch_helper._route_append_dedup_write` staging 分支（链式基+锁+sidecar read-merge-write）、`pipeline/checkpoint.commit_staging`（sidecar 元数据 + live 优先行级合并）、oneoff 清理工具。

**Tech Stack:** Python 3.11+ / pytest / structlog / pathlib。spec：`docs/superpowers/specs/2026-08-14-truth-write-path-design.md`（R4 已剔除——PR #43 已修）。

## Global Constraints

- `src/shenbi/` 禁 `print()`（structlog）；gate 检查器纯函数幂等无副作用
- fixtures 只能是真实产物副本（G0.9/G0.11），路径 `tests/fixtures/`
- 禁真实 dispatch 验证（核心原则 8）；验证一律 `uv run`/`just`（CI 同构）
- 解析失败显式标记（缺字段用 `None` + log，禁字符串 "unknown" 砸下游 int 比较、禁默认值/silence=999 造假）；单一解析源禁第二套格式
- Conventional commits；每 task 产出 `.superpowers/sdd/audit-T<N>.md`
- 全部 infra task 协调者亲实现（SDD leaf/infra 分流）

---

### Task 1: R1 — resonance_trend insert-only mode + 9 列对齐 + 存量归一

**Files:**
- Modify: `src/shenbi/pipeline/truth_io.py`（`write_truth_file` 新增 `mode="insert_markdown_row"`：`_path_lock` 锁内 `_key_column` 定位 + 逐行找 key，存在则跳过返回、不存在走 upsert 追加；`has_markdown_row` 辅助函数一并导出供测试/oneoff 用）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_build_resonance_trend_row` :1384-1403 改 9 列；调用点 :3169-3188 换 `mode="insert_markdown_row"`；docstring 同步改「Key column is {N}」）
- Add: `tools/oneoff/normalize_resonance_trend.py`（旧 `Ch{N}` 7 列行 → `{N}` 9 列；幂等；**先于框架写者切换部署到真实数据**——insert 模式匹配 `Ch{N}` 旧键会漏判，oneoff 先跑消除窗口）
- Test: `tests/unit/pipeline/test_truth_io.py`（追加 insert mode：key 存在跳过 / 不存在插入 / 与 upsert 幂等共存）、`tests/unit/pipeline/test_resonance_persistence.py`（**改存量 3 处 `Ch5` 断言** + 追加：skill 富行不被框架占位行覆盖 / 占位行 9 列断言 `len(cells)==9` / 两写者先后同章仅一行）

**Interfaces:**
- Produces: `shenbi.pipeline.truth_io.write_truth_file(mode="insert_markdown_row")`、`has_markdown_row(...)`；框架占位行 = `| {N} | - | - | - | - | - | {overall} | - |  |`（第 7 列 overall 位置不变，escalation_bridge cells[6] 兼容；第 8 列 `-`、第 9 列空格）

**验收（spec R1）:** 两写者同章先后写入后同章仅一行且保留 skill 富行；oneoff 对真实文件运行后无 `Ch{N}` 残留。

---

### Task 2: R2 — truth_readers 单一解析源 + 三方接线

**Files:**
- Add: `src/shenbi/pipeline/truth_readers.py`（`read_pending_hooks(project_dir: Path) -> list[dict]`：字段 id/state/last_reinforced/plant_chapter/max_distance，**缺省一律 `None`**（消费方 `isinstance(int)` 过滤+log，禁字符串 unknown）；裁决规则按 spec——生命周期表后状态为准、呈现列交叉校验、`A→B(批注)` 归一化取箭头后段、frontmatter `last_chapter` 为 last_reinforced **上界**、`max_distance(14)` 列名嵌入解析、缺表行 None）
- Modify: `src/shenbi/pipeline/context_curation.py`（`_read_pending_hooks` :362-390 改调 truth_readers，删 frontmatter-only 逻辑，docstring 更新；消费方 chapter_loop.py:1479-1490 P0-9 计算加 None 过滤）
- Modify: `src/shenbi/gates/g6.py`（G6.7 :115-135 改调 truth_readers；`??` 假块与 `- id:` 分块逻辑删除，None 字段显式跳过计数，禁混入 unresolved）
- Modify: `src/shenbi/pipeline/truth_index.py`（`_index_hooks` body 源 :207-218 改调 truth_readers；**双源裁决：truth_readers 结果优先，frontmatter 源仅补 truth_readers 未覆盖的 hook 或缺失字段**，extra 标 `source`）
- Fixture: 复用/核对现有 `tests/fixtures/truth-pending_hooks.md` 与 `pending-hooks-example.md`（若非当前真实格式则替换为真实副本并记 G0.11 哈希），避免第三份漂移
- Test: `tests/unit/pipeline/test_truth_readers.py`（新增：真实 fixture 解析 ≥7 条含非空 state / 转移串归一化 / 上界语义 / 缺表行 None）、`tests/unit/pipeline/test_context_curation.py`（追加非空消费；核对既有 `[]` 语义用例仅 missing-file 场景保留）、`tests/unit/gates/test_g6.py`（**重写 5 处旧 `## hooks`/`- id:` yaml-list fixture 为表格格式**或改引用真实 fixture——unresolved/high_hook_density/max_distance_exceeded 断言随之更新为真实语义）

**验收（spec R2）:** 真实文件解析出 ≥7 条含非空 state 的记录；context_curation/G6.7/truth_index 三方经同一解析源非空消费。

---

### Task 3: R3 核心 — staging 链式合并 + per-path lock + sidecar 化 commit

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（`_route_append_dedup_write` staging 分支 :1184-1200：合并基 = staging 文件存在则 staging（否则 live）；read-merge-write 包进 `truth_io._path_lock`（per-path、**仅进程内互斥——ThreadPoolExecutor 场景足够，跨进程为非目标**）；staging 写入时同步维护 sidecar `staging/.staging-meta.json`——**read→dict.update→write merge 语义，禁覆盖**，记录各 target 的 update_mode/key_field；sidecar 位于 `staging/` 根，`cli.py:378-380` 的 `staging/truth/*.md` glob 不会误拾）
- Modify: `src/shenbi/pipeline/checkpoint.py`（`commit_staging` :32-56：读 sidecar，有 append_dedup 条目的目标以 live 为基、staging 仅补 live 缺失 key 的行（同 key 冲突 live 胜）；无 sidecar/无条目保持现整文件行为）
- Test: `tests/unit/pipeline/test_dispatch_helper.py`（追加：链式基保留先写者增量 / sidecar merge 不覆盖已有条目）、`tests/unit/pipeline/test_checkpoint.py` 与 `tests/unit/pipeline/test_staging_commit.py`（追加：commit 不抹 live 新增行 / live 优先裁决；**核对既有整文件 copy + FileNotFoundError 语义断言并同步**）、`tests/unit/pipeline/test_staging_concurrency.py`（新增：**ThreadPool 并发两写者**各写不同 key 增量后两增量均在）

**验收（spec R3.1-3）:** 并发两写者同章都写后 staging 两写者增量均在；commit 不抹 live 新增行。

---

### Task 4: R3.4 — staging 残留一次性清理 oneoff

**Files:**
- Add: `tools/oneoff/clean_staging_residue.py`（判据三分支：`staging/plans/chapter-N-plan.md` 仅当 `plans/` 已有对应已提交版本才删；`staging/truth/*` 有 sidecar key_field 条目 → diff live、staging 独有 key 行经 truth_io upsert 重放进 live 后删；**无条目/无 key（自由文本 truth 文件）→ 不自动重放，dry-run 输出标记「需人工 diff」，禁默认整文件覆盖**；默认 dry-run，`--apply` 生效）
- Test: `tests/unit/tools/test_clean_staging_residue.py`（新增：plans 已提交才删 / staging 独有行先重放 / 无条目标记人工 / dry-run 不动盘）
- 对真实 repo 运行 dry-run → 人工核对输出 → --apply

**验收（spec R3.4）:** `staging/plans/` 清空；staging 独有表格数据已重放进 live；自由文本残留显式列清单待人工裁决；无数据丢失。
