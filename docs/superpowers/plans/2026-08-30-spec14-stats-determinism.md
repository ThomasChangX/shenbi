# Plan · spec #14 stats-determinism（收窄 9 条独有残留）

> **Date:** 2026-08-30 | **Spec:** `docs/superpowers/specs/2026-08-14-stats-determinism-design.md` | **裁决:** GO（收窄）
> **收窄依据:** 阶段 1 驳斥复核——6 条被 #32 语义覆盖移交（F604/F613/F608/F621/F645/F659/F661），F648 已修半且残余为接受语义；本 plan 实施 9 条独有残留
> **复杂度:** leaf（三模块均 skill_utils 下纯函数，无 pipeline/gates/contracts 触点）
> **分支:** `fix/spec-14-stats-determinism`

## 阶段 3 审查 Important 项的处置（前置设计决定）

1. **F634 基线陈旧过渡**：本修复改变 linguistic 度量语义（META 剥离、；切句、引号感知）。基线由 `establish_baseline`（chapter_loop.py:2090 前置引导，前 3 章）用**同一代码**计算——新建基线自洽。已存项目基线在旧语义下计算，修复后首跑可能产生一次过渡性 WARN；severity 分级（detect_drift）已容忍比值漂移，不引入迁移机制（YAGNI）。此语义变化随 PR 描述向用户披露。
2. **META_BLOCK_RE 单源**：沿用 pipeline 既有先例（scr_extractor.py:51、dispatch_helper.py:157 的 `from shenbi.gates.shared import META_BLOCK_RE as _META_RE  # 单源别名（z11 F1301）`），不复制正则、不搬常量（避免 gates↔text 反向重构扩散）。
3. **F668+F628 合并实现**：segment_sentences 重写为带引号状态机（“”「」『』开合跟踪；引号内 。！？ 不切；\n 仍切），边界集加入 ；。`_short_chain_chars`（linguistic_drift.py:94）的正则副本**明确不动**——其口径归 #32（F653 左锚）裁决，本 plan 只做 spec 声明的 segment_sentences 域。
4. 死代码 `RHETORICAL`（compute_stats.py:37-41，零引用）在 T1 顺带删除（audit 建议，防第三份边界集副本）。

## Tasks

### T1 · compute_stats.py 分句/修辞域（F628+F668+F633+F656+F652反复+F663 + 删 RHETORICAL）

- `test_kind: tdd_red_green`（新逻辑）；层级 T1
- 实际签名（源码复制）：
  - `def segment_sentences(text: str) -> list[tuple[str, int]]`
  - `def segment_paragraphs(text: str) -> list[dict[str, Any]]`（docstring 修正为 double-newline）
  - `def detect_rhetoric(text: str) -> dict[str, int]`
  - `def compute_ttr(text: str) -> dict[str, Any]`
- 改动：
  1. `segment_sentences`：字符循环改为维护引号状态。配对权威集对齐 cjk.py:54：`“”`、`‘’`、`「」`、`『』` 定向配对（开集 `“ ‘ 「 『`，闭集 `” ’ 」 』`），ASCII `"` 为 toggle（再次出现即闭合）。引号开启期间 `。！？；` 不终结句子；`\n` 无条件终结（未平衡引号的段落级逃逸）；文本结束即收尾。边界集 `"。！？；\n"`（+；统一 SENT_ENDS 口径，F628）
  2. `segment_paragraphs` docstring 修正为「按空行（连续换行）切分」（F633）
  3. `detect_rhetoric` 排比：比较用完整句长（`sent` 的 char_count，不用 `[:20]`）（F656）
  4. `detect_rhetoric` 反复：3/4/5-gram **位置区间**去重——按长度降序处理，长短语满足条件（≥3 次出现且相邻间隔<100）即计数并消费其出现区间；短 gram 出现若落入已消费区间则跳过。计数 = 去重后独立反复短语数（F652 反复语义；位置区间法避免「文首 5-gram 与文末独立 4-gram」误合并）
  5. `compute_ttr` 空输入早退补齐 `content_ttr`/`total_chars`（值 0）（F663）
  6. 删除死代码 `RHETORICAL` dict
- 测试（tests/unit/skill_utils/test_compute_stats.py 扩展）：
  - `；` 切句计数；引号内 `。` 不劈句（`“……。”他说。` → 2 句而非 3+）；引号跨 `；`
  - **未平衡引号**（`“……。后续无闭引号\n第二段`）→ `\n` 逃逸切分，不产生全文一句
  - ASCII `"` toggle：`"……。"他说。` 同样不劈句
  - 长句（>20 字）三连不等长不误判排比；等长中句判排比
  - 5 字重复短语 `反复 == 1`（不再 ×3 计）；文首 5-gram 重复 + 文末独立 4-gram 重复 → `反复 == 2`
  - 空/纯标点输入 `compute_ttr` 返回全键
- 验收命令：`uv run pytest tests/unit/skill_utils/test_compute_stats.py -q`

### T2 · linguistic_drift F605 守卫 + F634 META 剥离（两入口）

- `test_kind: tdd_red_green`；层级 T1
- 实际签名：
  - `def compute_linguistic_metrics(text: str, project_dir: Path | str | None = None) -> dict[str, float]`（linguistic_drift.py:98）
  - `def compute_all_stats(texts: dict[str, str]) -> dict[str, Any]`（compute_stats.py:~330，入参为文件名→文本 dict，内部 join——META 剥离作用于 join 后的合并文本）
- 改动：
  1. `load_drift_config`：`system_terms` 顶层 `isinstance(..., list)` 守卫——非 list（含裸字符串，防 `list("参数")` 逐字符化）→ 回退默认词表；元素级过滤非 str；空列表**保留空**（语义：显式无系统词），由调用点跳过正则、`system_term_density = 0.0`（F605。注意现状 bug 是空正则每位置匹配 → 密度暴涨 ~1000‰，红测按此理解）
  2. 两入口开头 `text = META_BLOCK_RE.sub("", text)`（单源别名 import，见设计决定 2）（F634）
- 测试（tests/unit/skill_utils/drift_detection/test_linguistic_drift.py + test_compute_stats.py）：
  - genre-config `system_terms: []` → density 0.0（tmp config 注入，走真实 load_drift_config）；`system_terms: "参数"`（裸字符串）→ 回退默认
  - `tests/fixtures/z11/chapter-41-with-meta.md` 真实语料：META 块内词不计入任何度量（断言剥前后 density 差）
  - 真实语料复核命令化：新增参数化测试遍历 `tests/fixtures/chapter-*-draft.md`（glob），跑 `compute_all_stats` + `compute_linguistic_metrics` 无异常且键集完整（G0.9：输入全为真实产物）
- 验收命令：`uv run pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py tests/unit/skill_utils/test_compute_stats.py -q`

### T3 · compute_pattern F667 词表外 pattern 保留

- `test_kind: tdd_red_green`；层级 T1
- 实际签名：`def compute_consecutive(patterns: list[str]) -> dict[str, int]`（compute_pattern.py:57）、`main()` 内 `max_consecutive`（:~205）
- 改动：`compute_consecutive` 结果键 = `sorted(set(patterns))`（含词表外如 未分类）；`main()` 的 `max_consecutive` 行同口径（消除 audit 指出的键集不一致）。`compute_entropy` **不动**（F647 归 #32）
- 既有测试更新（预期重构性打红）：`test_compute_consecutive_returns_zero_for_empty` 及断言「词表内未出现键 → 0」的用例（test_compute_pattern.py:18-21、:153 一带）改为断言键不存在/键集 == 输入集合
- 测试：patterns 含 `"未分类"` 连续 4 → `consecutive["未分类"] == 4` 且 warnings 覆盖；max_consecutive 行含未分类
- 验收命令：`uv run pytest tests/unit/skill_utils/test_compute_pattern.py -q`

## 验收覆盖表（spec「全部子项有单测；真实 chapter 语料统计复核」）

| 收窄子项 | Task | 验证 |
|---|---|---|
| F605/F656/F628/F633/F652反复/F663/F668 | T1 | test_compute_stats.py 新单测 |
| F634 | T2 | z11 真实 fixture 语料断言 + 单测 |
| F667 | T3 | test_compute_pattern.py |
| 真实语料复核 | T2 | tests/fixtures/z11/chapter-41-with-meta.md + tests/fixtures/chapter-*-draft.md 全 stats 跑通无异常 |
| 全量回归 | 阶段7 | `just check` |

## G3.4 声明

本 plan 全部为确定性纯函数单测，无 LLM 生成场景，不涉及 dispatch 评分，G3.4 不适用。

## 移交注记（随归档写入 spec）

F604/F613/F608/F621/F645/F659/F661 六条语义归活跃 spec #32（drift/CJK 度量簇 C6）；remediation-master:98「supersede → C7(+C6)」中 C7 部分失准（C7=#33 只管接线），归档时勘误。
