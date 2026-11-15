# Spec #105 审计发现契约硬化（audit-finding-contract）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** severity 词表单源化（对齐 enums.Severity 登记域，六消费点行为保持换装）+ 词表外 fail-loud（G4.av.vocab 三段式判别器）+ 派发完整性语义拆分（审计派发前置预检+G4.av.dispatch_integrity）+ 反馈与聚合卫生（EXAMPLES 补键/聚合条目级 severity/ending 窗 3→10）。

**Architecture:** 新 `src/shenbi/contracts/severity.py` 作为 severity 传感/词表单源（Literal 形常量对齐 status-vocab 登记域 + 运行时元组 + 四锚定形态正则 + 三尾巴），六消费点全部 import 换装并以差分基线钉死行为保持；`llm_output_integrity.check_audit_severity_vocab` 以「形态槽位通配捕获+统一后处理管线（upper 归一→判别器→legend 拆分豁免→查表）」实现词表外 fail-loud，双点位接线（dispatch_helper is_audit 首线+generic.py pwi）；审计派发前置预检复用 #51 ghost-chain guard 控制流与 escalation reads 三态语义；聚合渲染与纵向 parser 同步升级双格式容差。

**Tech Stack:** Python 3.11+/pathlib/re/structlog/pytest；G0/G4 门禁框架；AST lint（#88/#89 先例 `_pattern_arg`）。

**Spec↔Task 映射**：spec T1→plan T1-T3（登记域+模块 / 换装+差分 / AST lint）；spec T2→plan T4；spec T3→plan T5；spec T4→plan T6-T8（EXAMPLES / 聚合渲染 / ending 窗）。本 plan 全部 task 为 **infra**（协调者亲自实现，v7.1 单模型裁定）。

## Global Constraints

- `src/shenbi/` 禁 `print()`（ruff T20 零豁免）——用户面文本走 `shenbi.cli_utils.echo`，日志走 structlog；`tools/` 脚本可用 print（先例：check_fixture_mirror.py）但 lint 工具输出走 exit code+stderr。
- gate/checker 纯函数幂等、无副作用（G4.av.* 两 checker 只读文件）。
- 测试环境同构：一切验证走 `just`/`uv run`；fixtures 只能是真实 skill 输出（G0.9）——vol1 语料副本**逐字节复制**（不加头），provenance 走 sidecar `tests/fixtures/audits/PROVENANCE.md`（G0.11 MIRROR_MAP 不触及）。
- 差分基线先冻结后换装（#99 先例）；换装 commit 前基线文件必须已在盘。
- conventional commits：`feat:`/`chore:`/`test:`/`docs:`。
- 每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 重审）；无 audit 不得开下一 task。
- **对 spec r2.6 的两处已裁定偏离（r3-MC 注记，执行期记入 spec-deviations.md）**：①spec T1 称「四锚定形态（bracket/bold/cell/key）编译正则单源」——plan 收缩为 bracket/bold 两锚定（cell/key 由 audit_aggregate 本地组合重建，行为保持且免零消费符号——YAGNI）；②spec (b) 面称「provenance 头注明来源章」——plan 改 PROVENANCE.md sidecar（逐字节副本保差分基线纯净，G0.11 MIRROR_MAP 不触及）。

---

### Task 1: severity 单源模块 + status-vocab 登记域先行（spec T1 前置）

**Files:**
- Modify: `docs/framework/status-vocab.md`（AuditSeverity 行后新增两行）
- Create: `src/shenbi/contracts/severity.py`
- Modify: `tests/unit/tools/test_status_vocab_registry.py:19`（计数锁 47→49）
- Test: `tests/unit/contracts/test_severity.py`（新建）

**Interfaces:**
- Consumes: `shenbi.contracts.enums.Severity`（enums.py:9 `Literal["BLOCKING","CRITICAL","MINOR"]`）
- Produces（后续 task 全部依赖）:
  - `RoutingTier: Literal["BLOCKING", "CRITICAL"]`（Literal 形常量——registry 行符号）
  - `AggregateVocab: Literal[Severity, "WARNING", "ERROR"]`（PEP 586 展平）
  - `ROUTING_TIERS: tuple[str, ...]`、`AGGREGATE_VOCAB: tuple[str, ...]`（`get_args` 派生运行时元组）
  - `ROUTING_HARD_TIER_ALIASES: tuple[str, ...] = ("ERROR",)`
  - `SEV_ENUM_TAIL: str`（= revision_router.py:90 `_SEV_ENUM_TAIL` 原文迁入）
  - `NEGATION_PAYLOAD_TAIL: str`、`QUOTED_VALUE_TAIL: str`（:102/:120 原文迁入）
  - `BLOCKING_BRACKET_LABEL_RE`/`BLOCKING_BOLD_LABEL_RE`: `re.Pattern[str]`——BLOCKING 标签锚定（bracket 含复合标签后缀；T5 dispatch_integrity 真消费）——r2-M5 YAGNI 收缩（audit-T4 轮 2：泛用四形态锚定删除，避免零消费死面：**不建 CELL_ANCHOR_RE/KEY_ANCHOR_RE**——cell/key 传感由 audit_aggregate 换装时本地从 AGGREGATE_VOCAB 组合重建（行为保持），单源模块只建有生产消费方的锚定）
  - `SECTION_HEADER_RE`: `re.Pattern[str]`——`^## (BLOCKING|CRITICAL|MINOR|WARNING|ERROR) Findings`（元组组合，含 MINOR——修 report_longitudinal:558 缺词）
  - `CJK_SEVERITY_WORDS: frozenset[str] = frozenset({"严重","高","重大","中","低","警告"})`
  - `KEY_NAME_TOKENS: frozenset[str] = frozenset({"SEVERITY", "严重度"})`
  - `ROUTING_BLOCKING_BRACKET_WORDS: tuple[str, ...] = ("BLOCKING",)` 与 `ROUTING_CRITICAL_BRACKET_WORDS: tuple[str, ...] = ("CRITICAL", "ERROR")`（**bracket 形词组单源**——CRITICAL 形必须只含 CRITICAL|ERROR，混入 BLOCKING=行为变更，I-1 修正）
  - `AGGREGATE_VOCAB_SET: frozenset[str] = frozenset(AGGREGATE_VOCAB)`（T4 管线查表消费——I-2 缝隙闭合：T1 即定义）

- [ ] **Step 1: 失败测试先行**——`tests/unit/contracts/test_severity.py`：

```python
"""Spec #105 T1: severity single-source module (registry-aligned)."""

from typing import get_args


def test_routing_tier_literal_and_runtime_tuple():
    from shenbi.contracts.severity import ROUTING_TIERS, RoutingTier

    assert get_args(RoutingTier) == ("BLOCKING", "CRITICAL")
    assert ROUTING_TIERS == ("BLOCKING", "CRITICAL")


def test_aggregate_vocab_flattens_and_supersedes_severity():
    from shenbi.contracts.enums import Severity
    from shenbi.contracts.severity import AGGREGATE_VOCAB, AggregateVocab

    assert get_args(AggregateVocab) == ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR")
    assert AGGREGATE_VOCAB == ("BLOCKING", "CRITICAL", "MINOR", "WARNING", "ERROR")
    assert set(get_args(Severity)) <= set(AGGREGATE_VOCAB)  # 子集断言


def test_hard_tier_aliases_excluded_from_tier_values():
    from shenbi.contracts.severity import ROUTING_HARD_TIER_ALIASES, RoutingTier

    assert ROUTING_HARD_TIER_ALIASES == ("ERROR",)
    assert "ERROR" not in get_args(RoutingTier)  # registry 值集相等契约


def test_anchored_forms_match_in_vocab_words_only():
    from shenbi.contracts.severity import (
        AGGREGATE_VOCAB,
        BOLD_ANCHOR_RE,
        BRACKET_ANCHOR_RE,
    )

    assert BRACKET_ANCHOR_RE.search("- [MINOR] something")
    assert not BRACKET_ANCHOR_RE.search("- [MAJOR] something")  # 词表外不入传感域
    assert BOLD_ANCHOR_RE.search("**BLOCKING**")
    assert BOLD_ANCHOR_RE.search("**CRITICAL**")  # M-10: bold 形全词断言
    for w in AGGREGATE_VOCAB:
        assert BRACKET_ANCHOR_RE.search(f"- [{w}] x")


def test_section_header_re_includes_minor():
    from shenbi.contracts.severity import SECTION_HEADER_RE

    assert SECTION_HEADER_RE.match("## MINOR Findings (3)")
    assert SECTION_HEADER_RE.match("## ERROR Findings (1)")
    assert not SECTION_HEADER_RE.match("## Resonance 报告")
```

- [ ] **Step 2: 跑测确认失败**——`uv run pytest tests/unit/contracts/test_severity.py -x -q`（ModuleNotFoundError: shenbi.contracts.severity）
- [ ] **Step 3: 落 `src/shenbi/contracts/severity.py`**——要点：模块 docstring 声明「severity 传感/词表单源（spec #105 T1）——登记域 RoutingTier/AggregateVocab 见 docs/framework/status-vocab.md」；常量与正则全部按 Interfaces 块定义；**bracket/bold 两锚定形态正则以元组组合构造**（r3-I2：cell/key 传感不建模块锚定——audit_aggregate 换装时本地从 AGGREGATE_VOCAB 组合重建，行为保持；注释引用迁出来源 audit_aggregate.py:46-47/revision_router.py:127-146 保留原 probe 教训注释的压缩版）；`SECTION_HEADER_RE` 用 `re.M`；`AGGREGATE_VOCAB_SET = frozenset(AGGREGATE_VOCAB)` 同模块落定（T4 查表消费——I-2）。
- [ ] **Step 4: 跑测通过**——`uv run pytest tests/unit/contracts/test_severity.py -q` 全绿
- [ ] **Step 5: status-vocab.md 新增两行**——在 AuditSeverity 行（:21）后插入（5 列格式严格对齐邻行）：

```markdown
| RoutingTier | shenbi.contracts.severity.RoutingTier | BLOCKING\|CRITICAL | 审计产出（escalation 路由两档；legacy `[ERROR]` 硬档别名=ROUTING_HARD_TIER_ALIASES，不入值集——audit_layer 消费别名非值集，r2-M8 写准） | revision_router、chapter_loop、parallel_dispatch |
| AggregateVocab | shenbi.contracts.severity.AggregateVocab | BLOCKING\|CRITICAL\|MINOR\|WARNING\|ERROR | 审计产出（聚合面；WARNING/ERROR 为 legacy 词） | audit_aggregate、report_longitudinal |
```

同时把 :21 AuditSeverity 行「消费点」列的失实声明（`escalation 路由（regex 域大小写归一后比对，revision_router.py、parallel_dispatch.py）`）改为 `审计产出 severity 三档（T2 fail-loud 校验域）`——死线消费声明修真。
- [ ] **Step 6: 计数锁 47→49**——`tests/unit/tools/test_status_vocab_registry.py:19` `assert len(rows) == 47` → `== 49`；跑 `uv run pytest tests/unit/tools/test_status_vocab_registry.py -q` 全绿（若 reconcile 面报 RoutingTier/AggregateVocab 解析失败：确认 severity.py 的 Literal 是模块级 `Name = Literal[...]` 直接赋值——`_enum_or_literal_values` 经 `_resolve_via_import`+`__args__` 解析，勿用函数内定义或 tuple 直接赋值）。
- [ ] **Step 7: lint 面自证**——`uv run python tools/lint_status_strings.py`（若其为 just check 内 lint 则跑对应 just 目标）确认 `_registry_union()` 扩集无红、`_unregistered_code_domains` 无新 unregistered。
- [ ] **Step 8: Commit**

```bash
git add docs/framework/status-vocab.md src/shenbi/contracts/severity.py \
  tests/unit/contracts/test_severity.py tests/unit/tools/test_status_vocab_registry.py
git commit -m "feat: spec #105 T1a — contracts/severity.py 单源模块+status-vocab RoutingTier/AggregateVocab 双行登记（47→49）"
```

---

### Task 2: fixtures 扩容 + 差分基线 + 六消费点换装（spec T1 换装）

**Files:**
- Create: `tests/fixtures/audits/`（vol1 真实审计逐字节副本 ~10 份）+ `tests/fixtures/audits/PROVENANCE.md`
- Create: `tools/gen_severity_diff_baseline.py`
- Create: `tests/baselines/severity-swap/`（基线 JSON）
- Modify: `src/shenbi/pipeline/revision_router.py:90-146`（尾巴与双正则换装）
- Modify: `src/shenbi/pipeline/audit_aggregate.py:34-79`（_SEV_WORDS 与锚定族换装）
- Modify: `src/shenbi/pipeline/chapter_loop.py:672-683`（_BLOCKING_MARKER_RE 换装）
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:365-386`（consolidator 正则换装）
- Modify: `src/shenbi/pipeline/audit_layer.py:38`（_ERROR_LABEL_RE 换装）
- Modify: `tools/report_longitudinal.py:558`（节头正则换装+MINOR 修复）
- Test: `tests/unit/pipeline/test_severity_swap_differential.py`（新建）

**Interfaces:**
- Consumes: Task 1 全部符号。
- Produces: 六消费点全部 import 单源符号（**无本地交替词表**——单词字面量分支[key/bold 单词面、table-bold、单字标签]按行为保持设计保留，M-11 措辞归真）；`gen_severity_diff_baseline.py <corpus_dir> <out_json>` CLI。

- [ ] **Step 1: 语料选章**——按 r2.6 矩阵（文件数口径）选覆盖 union 的 ~10 份（每词≥1、每锚定形态≥1、含 heading 形 `## BLOCKING` 与 `## FAIL` 若语料有——用 grep 实测定稿；**真空洞组合仅 CRITICAL bold 与 ERROR bracket**，MINOR cell 22 份/CRITICAL cell 3 份语料实有必选）。执行期用：

```bash
grep -rlE '^\s*-\s*\[MINOR\]' novel-xinghuo-vol1/audits/chapter-*.md | head -2
grep -rl '\*\*WARNING\*\*' novel-xinghuo-vol1/audits/chapter-*.md | head -2
grep -rl '| CRITICAL |' novel-xinghuo-vol1/audits/chapter-*.md | head -2
grep -rlE '^#{1,3}\s*##?\s*(BLOCKING|CRITICAL|FAIL)\b' novel-xinghuo-vol1/audits/chapter-*.md | head -2
grep -rl '\*\*ERROR\*\*' novel-xinghuo-vol1/audits/chapter-*.md | head -2
grep -rl '| MINOR |' novel-xinghuo-vol1/audits/chapter-*.md | head -2
```

- [ ] **Step 2: 逐字节复制**（不加头）+ `tests/fixtures/audits/PROVENANCE.md`（每行：文件名｜来源章｜复制日期 2026-11-15｜G0.9 真实 skill 输出声明）。
- [ ] **Step 3: 写差分生成器 `tools/gen_severity_diff_baseline.py`**——遍历 corpus 目录每份 .md，跑五传感并记录逐文件结果 JSON：

```python
#!/usr/bin/env python3
"""Spec #105 T1: freeze five-sensor outputs on the audit corpus (pre/post swap differential, #99 precedent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def sensor_outputs(content: str) -> dict[str, object]:
    """Five sensors over one audit file's content (pre-swap call sites, kept stable)."""
    from shenbi.pipeline import audit_aggregate, audit_layer, chapter_loop, revision_router

    units, _ctx = audit_aggregate.extract_finding_units("x.md", content)
    return {
        "router_blocking": bool(revision_router._SEVERITY_BLOCKING_RE.search(content)),
        "router_critical": bool(revision_router._SEVERITY_CRITICAL_RE.search(content)),
        "loop_marker": bool(chapter_loop._BLOCKING_MARKER_RE.search(content)),
        "error_label": bool(audit_layer._ERROR_LABEL_RE.search(content)),
        "consolidator_blocking": _consolidator_blocking_equiv(content),  # M-7: consolidator 传感键
        "aggregate_units": [[u.severity, u.text, list(u.reporters)] for u in units],
    }


def main() -> int:
    corpus, out = Path(sys.argv[1]), Path(sys.argv[2])
    result = {
        p.name: sensor_outputs(p.read_text(encoding="utf-8"))
        for p in sorted(corpus.glob("*.md"))
        if p.name != "PROVENANCE.md"
    }
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

注（M-7）：consolidator 正则是 `consolidate_review_results`（parallel_dispatch.py:303）**函数内局部编译**（:375-386）——生成器以模块级等价式 `_consolidator_blocking_equiv(content)` 记录第六键 `consolidator_blocking`（与换装前 blocking_re 逐字符等价——三形态+`_enum_tail`/QUOTED_VALUE_TAIL/NEGATION_PAYLOAD_TAIL 三尾巴，import severity 单源组合）；T2 换装后该键重跑仍须逐文件一致。
- [ ] **Step 4: 冻结换装前基线**——`uv run python tools/gen_severity_diff_baseline.py tests/fixtures/audits tests/baselines/severity-swap/baseline.json`，**先 commit 基线**：

```bash
git add tools/gen_severity_diff_baseline.py tests/fixtures/audits tests/baselines/severity-swap/baseline.json
git commit -m "test: spec #105 T1b — 审计语料 fixtures 扩容（union 覆盖）+五传感差分基线冻结（换装前）"
```

- [ ] **Step 5: 六消费点换装**（全部 import 单源，行为逐字节保持——正则文本不变，词表来源换装）：
  - `revision_router.py`:90-146——删 `_SEV_ENUM_TAIL`/`NEGATION_PAYLOAD_TAIL`/`QUOTED_VALUE_TAIL` 本地定义（:90/:102/:120），改 `from shenbi.contracts.severity import NEGATION_PAYLOAD_TAIL, QUOTED_VALUE_TAIL, SEV_ENUM_TAIL as _SEV_ENUM_TAIL, ROUTING_BLOCKING_BRACKET_WORDS, ROUTING_CRITICAL_BRACKET_WORDS`；`_SEVERITY_BLOCKING_RE` bracket 分支词组 `'|'.join(ROUTING_BLOCKING_BRACKET_WORDS)`（=单词 BLOCKING）、`_SEVERITY_CRITICAL_RE` bracket 分支 `'|'.join(ROUTING_CRITICAL_BRACKET_WORDS)`（=原文 `CRITICAL|ERROR` 逐字符一致——**禁用 `(*ROUTING_TIERS, *ALIASES)` 展开：会混入 BLOCKING 致 `- [BLOCKING]` 行误命中 CRITICAL 传感=行为变更**，I-1 修正）；bold/key 分支词面用 f-string 插值单条词（单词字面量非交替，不触 lint）。
  - `audit_aggregate.py`:34-79——删 `_SEV_WORDS` 本地定义，锚定族四正则（:46/:47/:51/:58-61）从 `AGGREGATE_VOCAB`/`SEV_ENUM_TAIL`/`QUOTED_VALUE_TAIL` 组合；`_KEY_RE` 的 `_ENUM_TAIL` 换源。
  - `chapter_loop.py`:672-683——`_BLOCKING_MARKER_RE` heading 分支 `(?:BLOCKING|CRITICAL|FAIL)` 改 `re.compile(r"(?:^#{0,3}\s*##?\s*(?:" + "|".join((*ROUTING_TIERS, "FAIL")) + r")\b)" r"|(?:\|\s*\*\*BLOCKING\*\*)" rf"|(?:^\s*-\s*\[(?:{'|'.join((*ROUTING_TIERS, *ROUTING_HARD_TIER_ALIASES))})\]" rf"{NEGATION_PAYLOAD_TAIL})", re.M)`——**与原正则逐字符等价**（拼开结果相同）；table-bold 分支单词字面量保留。
  - `parallel_dispatch.py`:365-386——`_enum_tail` 本地定义（:367）删，换 `SEV_ENUM_TAIL` import；blocking_re bracket 词组用 `ROUTING_BLOCKING_BRACKET_WORDS`、critical_re 用 `ROUTING_CRITICAL_BRACKET_WORDS`（与 router 同款 I-1 修正——禁 TIERS∪ALIASES 展开）。
  - `audit_layer.py`:38——`_ERROR_LABEL_RE` 改 `re.compile(r"^\s*-\s*\[(" + "|".join(ROUTING_HARD_TIER_ALIASES) + r")\]", re.M)`（单字标签 import 证明覆盖——lint 豁免口注记于此注释内）。
  - `tools/report_longitudinal.py`:558——节头正则改 `SECTION_HEADER_RE`（**行为变更点：MINOR 修复——差分单列，见 Step 6 测试豁免注记**）。
- [ ] **Step 6: 差分测试 `tests/unit/pipeline/test_severity_swap_differential.py`**：

```python
"""Spec #105 T1b: six-consumer swap is behavior-preserving (differential vs frozen baseline, #99 precedent)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]  # r2-M6: tests/unit/pipeline/ → repo 根是 parents[3]
CORPUS = REPO / "tests/fixtures/audits"
BASELINE = REPO / "tests/baselines/severity-swap/baseline.json"


def _current_outputs() -> dict:
    out = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/gen_severity_diff_baseline.py"),
            str(CORPUS),
            "/dev/stdout",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    )
    return json.loads(out.stdout)


def test_five_sensors_match_frozen_baseline():
    frozen = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = _current_outputs()
    assert current == frozen, "换装后五传感输出与冻结基线逐项不一致（spec T1 差分判据失败）"


def test_longitudinal_section_header_now_includes_minor():
    # 行为变更单列（spec T1 判据(c)：longitudinal MINOR 修复=设计内行为变更，不入差分面）
    from shenbi.contracts.severity import SECTION_HEADER_RE

    assert SECTION_HEADER_RE.match("## MINOR Findings (2)")
```

（生成器写 `/dev/stdout` 支持在 Step 3 落实；若 CI 环境不可写 /dev/stdout，改 `tempfile` 中转——执行期落定。）
- [ ] **Step 7: 跑差分+全量相关测试**——`uv run pytest tests/unit/pipeline/test_severity_swap_differential.py tests/unit/contracts/test_severity.py -q`；`uv run pytest tests/unit/pipeline/ -q -k "audit or aggregate or router or dispatch"`（既有传感相关测试零回归）。
- [ ] **Step 8: grep 判据**——`git grep -nE "BLOCKING\|CRITICAL" -- src/shenbi/pipeline tools/` 输出仅剩注释/docstring 与组合构造行（换装前 7 处代码行交替→后 0 交替）；粘贴输出进 progress.md。
- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/revision_router.py src/shenbi/pipeline/audit_aggregate.py \
  src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/parallel_dispatch.py \
  src/shenbi/pipeline/audit_layer.py tools/report_longitudinal.py \
  tests/unit/pipeline/test_severity_swap_differential.py
git commit -m "feat: spec #105 T1b — 六消费点 severity 传感换装（行为保持差分全绿，longitudinal MINOR 修复单列）"
```

---

### Task 3: AST lint——severity 交替字面量单源守卫（spec T1 lint）

**Files:**
- Create: `tools/lint_severity_single_source.py`
- Test: `tests/unit/tools/test_lint_severity_single_source.py`（新建）

**Interfaces:**
- Consumes: 无（AST 扫描独立）。
- Produces: `tools/lint_severity_single_source.py`（exit 0/1）；接入 `just check` lint 面（justfile 既有 lint 链追加一行，与 lint_chapter_num_single_source 同列）。

- [ ] **Step 1: 失败测试**——红测构造：tmp_path 写一个含 `re.compile(r"BLOCKING|CRITICAL")` 的 .py（模拟 pipeline 模块路径），断言 lint 判违例；白测：同文件仅 `re.compile("|".join(ROUTING_TIERS))` 通过；单源模块 `contracts/severity.py` 自身豁免。测试以函数级调用 lint 的 `check_tree`/`main`（参照 `tests/unit/tools/` 下 lint_chapter_num_single_source 同款测试结构——执行期读 `tools/lint_chapter_num_single_source.py` 全文与对应测试照搬骨架）。
- [ ] **Step 2: 确认失败**——`uv run pytest tests/unit/tools/test_lint_severity_single_source.py -q`（ModuleNotFoundError）
- [ ] **Step 3: 实现 lint**——骨架照 `lint_chapter_num_single_source.py`（#89 T2 先例）：`_pattern_arg` 只认 `ast.Constant` 字符串（positional 或 `pattern=`）；`RE_FUNCS = ("compile","search","match","fullmatch","findall","sub","subn","split")`；违例判据=pattern 字符串含「≥2 个 severity 词的交替」（`BLOCKING|CRITICAL` 等五词任意两词以上以 `|` 相连——精确判据：`re.search(r"(BLOCKING|CRITICAL|MINOR|WARNING|ERROR)(\|)+", pat)` 且全串提取的交替词数 ≥2）；允许文件=`src/shenbi/contracts/severity.py`；扫描域=`src/shenbi/pipeline`+`src/shenbi/contracts`+`tools`；输出违例清单 exit 1。**r5-M3 自引用陷阱**：lint 自身的违例探测**禁用携带五词交替字面量的 re.* 调用**（tools/ 在扫描域内——照抄字面式会判己违例首跑即红）——探测器用元组 join 构造或 #89 先例的纯字符串包含判定。
- [ ] **Step 4: justfile 接线**——`just check` 的 lint 链（与 lint_chapter_num_single_source 同一 recipe 行/相邻行）追加 `tools/lint_severity_single_source.py`；`just -n check` 语法自证 + 跑一次全绿。
- [ ] **Step 5: 全量验证**——`uv run pytest tests/unit/tools/test_lint_severity_single_source.py -q` + `just check`（若 check 全量慢，跑 lint 面子配方）。
- [ ] **Step 6: Commit**

```bash
git add tools/lint_severity_single_source.py tests/unit/tools/test_lint_severity_single_source.py justfile
git commit -m "feat: spec #105 T1c — severity 交替字面量 AST lint（单源模块外零容忍，#88/#89 先例骨架）"
```

---

### Task 4: check_audit_severity_vocab + 双点位接线 + vol1 回放（spec T2）

**Files:**
- Modify: `src/shenbi/pipeline/llm_output_integrity.py`（新增 `check_audit_severity_vocab(path: Path, forms: tuple[str, ...] = PRODUCTION_VOCAB_FORMS) -> list[str]`）
- Create: `tools/replay_severity_vocab.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py:2968-2973`（is_audit 块追加发射）
- Modify: `src/shenbi/gates/g4/generic.py:252-260`（G4.av. 分支按 id 三路由）
- Test: `tests/unit/pipeline/test_check_audit_severity_vocab.py`（新建）

**Interfaces:**
- Consumes: `AGGREGATE_VOCAB`/`CJK_SEVERITY_WORDS`/`KEY_NAME_TOKENS`（Task 1）。（QUOTED_VALUE_TAIL 不入本 task——r4-I1：引号防御走 gap 类，tail 前瞻在通配捕获下可回溯绕过）
- Produces:
  - `check_audit_severity_vocab(path: Path, forms: tuple[str, ...] = PRODUCTION_VOCAB_FORMS) -> list[str]`——issue 形态 `G4.av.vocab:{path.name} — 词表外严重度 "{token}"（{form} 形）：用 BLOCKING/CRITICAL/MINOR 重写本条`
  - `tools/replay_severity_vocab.py <project_dir> [--pattern 'chapter-*-*.md'] [--forms all|key] [--out FILE]`——回放报告（命中/清洗清单/误伤候选计数）

- [ ] **Step 1: 失败测试（红七绿十三全清单）**——`tests/unit/pipeline/test_check_audit_severity_vocab.py` 用 tmp_path 写文件逐条断言（红：`- [MAJOR] x`／`**BLOCKER**`／`严重度: 严重`／`严重度: 高`／`严重度: 高。`（尾部标点——r2-M2 捕获污染剥离的验收钉：不剥则 CJK 精确等值不命中=静默漏报）／`- [major]`／`Severity: MAJOR`；绿：`[MINOR]`／`- [minor]`／prose "major"／`severity:BLOCKING/CRITICAL/MINOR`／`**严重度**：BLOCKING / CRITICAL / MINOR`／`**判定**`+`**章节**`+`- [读者回报]`+`- [MINOR·观察]`／`**严重度**` 裸 key／`**Severity**`）：

```python
"""Spec #105 T2: G4.av.vocab — out-of-vocab severity is a hard, discriminated gate."""

from pathlib import Path

import pytest

from shenbi.pipeline.llm_output_integrity import check_audit_severity_vocab


def _issues(tmp_path: Path, content: str) -> list[str]:
    f = tmp_path / "chapter-9-x.md"
    f.write_text(content, encoding="utf-8")
    return check_audit_severity_vocab(f)


@pytest.mark.parametrize(
    "content",
    [
        "- [MAJOR] 节奏断裂",
        "**BLOCKER** 全章失控",
        "严重度: 严重",
        "严重度: 高",
        "严重度: 高。",  # r3-I1: 尾部标点剥离红钉（进 parametrize 非 prose）
        "- [major] 节奏断裂",
        "Severity: MAJOR",
    ],
)
def test_out_of_vocab_red(tmp_path, content):
    assert any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content))


@pytest.mark.parametrize(
    "content",
    [
        "- [MINOR] 措辞建议",
        "- [minor] 措辞建议",
        "本章有一点 major 问题。",
        "severity:BLOCKING/CRITICAL/MINOR",
        "**严重度**：BLOCKING / CRITICAL / MINOR",
        "**判定**: 通过",
        "**章节**: 第 9 章",
        "- [读者回报] 回报偏弱",
        "- [MINOR·观察] 观察",
        "**严重度**",
        "**Severity**",
        '"severity": "low"',  # M-5: 引号值绿测（r4-I1 gap 类防御验收钉——非 QUOTED_VALUE_TAIL，r5-M2 归因更正）
        "严重度: ERROR（对应 BLOCKING）",  # r2-M2: 括注剥离——剥后 ERROR∈词表 PASS（不剥=误报）
    ],
)
def test_in_vocab_or_exempt_green(tmp_path, content):
    assert not any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content))
```

- [ ] **Step 2: 确认失败**——ImportError。
- [ ] **Step 3: 实现 checker**（纯函数幂等，path 形与同族同构）：
  - 捕获正则（模块级预编译）：bracket `re.compile(r"^\s*-\s*\[([\w·\-]+)\]", re.M)`；bold `re.compile(r"\*\*([\w\-]+)\*\*")`；key `re.compile(r"\*{0,2}(?:severity|严重度)\*{0,2}[^\w"']{0,6}([^\s"']+)", re.IGNORECASE)`（**r4-I1 钉死——引号防御用 gap 类排除引号而非尾部负向前瞻**：tail 前瞻 `(?!"...)` 放在可回溯通配捕获组后必然被回溯绕过——`([^\s"]+)` 捕 `low` 后前瞻见 `"` 失败→回溯交还一字符捕 `lo`→`LO` 过判别器→FAIL 误伤（与 spec C1' 证伪 `_SEV_ENUM_TAIL` 照搬路径同机制）；gap 类 `[^\w"']{0,6}` 不吃引号（r5-M2 写全：防御面含单双引号）→`"severity": "low"` 全线无匹配→PASS，`severity: MAJOR`/`**严重度**：BLOCKING` 行为不变；`severity: "BLOCKING"` 引号值=传感侧 #18-1 同判（非声明）→PASS 语义一致）。
  - **统一后处理管线**（模块内私有函数 `_vocab_violation(token: str) -> bool`；checker docstring 注记两条 r2.6 挂账：①捕获污染剥离规则 ②key-名豁免形态域[形态无关生效、动机仅 bold 裸 key——残余面 #117 收编]）：
    1. **捕获污染剥离（r2.6 plan 注记落位，I-3）**：`token = re.sub(r"[（(][^）)]*[）)]?\s*$", "", token)` 剥括注后缀（`ERROR（对应 BLOCKING）`→`ERROR`），再 `.rstrip("。．.,，;；:：!！?？")` 剥尾部标点（`严重度：高。`→`高`——不剥则 CJK 精确等值不命中=静默漏报，恰是本件根因形态）
    2. `token = token.upper()`
    3. key-名豁免：`if token in KEY_NAME_TOKENS: return False`
    4. 判别器：`ascii_hit = token.isascii() and token.isupper() and len(token) >= 2`；`cjk_hit = token in CJK_SEVERITY_WORDS`（归一后 CJK 词 upper 不变，集合成员精确等值）；`if not (ascii_hit or cjk_hit): return False`
    5. legend 拆分豁免：`parts = re.split(r"[/／、,，]", token)`；`if all(p in AGGREGATE_VOCAB_SET for p in parts): return False`（`AGGREGATE_VOCAB_SET` 已在 T1 severity.py 落定，此处 import）
    6. `return token not in AGGREGATE_VOCAB_SET`
  - cell 形不建；散文豁免=仅锚定形捕获（正则天然保证）。
  - docstring 注明 spec #105 T2 与「禁从传感正则推导」原因。
- [ ] **Step 4: 测试绿**——`uv run pytest tests/unit/pipeline/test_check_audit_severity_vocab.py -q`（含补的 `"severity": "low"` 绿测）。
- [ ] **Step 5: 回放工具 `tools/replay_severity_vocab.py`**——遍历 `<project_dir>/audits/` 章审计形——**判据与 `_is_audit_file` 完全对齐（r2-I1）：`audits/` 域 + `chapter-NN-<dim>` 形 + 仅排除 `.aggregate.md`，不排除 `-resonance.md`**（生产 is_audit 块对 resonance 同样生效——completeness/line_refs 现状即跑 resonance；回放排除 resonance 则 shadow 闸门永远测不到 46 份生产触达文件=闸门完整性缺口），跑 checker，输出 markdown 报告：命中清单（file:line:token:form）+总数+分母（生产触达/aggregate 差集/escalation 差集——`_is_audit_file` 同判据本地复刻，不 import 私有）。
- [ ] **Step 6: vol1 回放（shadow 闸门）**——`uv run python tools/replay_severity_vocab.py novel-xinghuo-vol1 --forms key --out /tmp/spec105-vocab-replay.md`（r2.7：生产 key 形域）；人工核命中条目全为真词表外违规（key 形预期 0——语料零命中）；**零误伤→接线 FAIL；有误伤→停，记 BLOCKING deviation 报备**。默认 ALL 形态回放（#116 采集面）预期 198 全误伤，属已知。报告关键数字粘贴 progress.md。
- [ ] **Step 7: 接线双点位**：
  - `dispatch_helper.py` is_audit 块（:2970-2973）追加 `issues += check_audit_severity_vocab(full_path, forms=PRODUCTION_VOCAB_FORMS)`（r2.7 key-only）（import 入既有 from-import 列表 :71-78 位置——M-8 行号修正）。
  - `generic.py:252` G4.av. 分支改按 finding id 三路由：`stale_line_ref`→check_audit_line_refs；`vocab`→check_audit_severity_vocab；`dispatch_integrity`（Task 5 落地后）→对应 checker；未识别 G4.av. 前缀→`return True`（保守放行，log warning）。**M-9**：现行 chapter-gone 早退（:257-259）仅 `stale_line_ref` 路由保留——vocab/dispatch_integrity 不依赖 chapter 文件，继承早退会在章文件删除后把其 finding 误判 stale 吞掉。本 task 先落前两条+未识别放行；Task 5 补第三条。
- [ ] **Step 8: 集成测试**——既有 dispatch G4 流测试（grep `check_audit_completeness` 在 tests/ 的调用面）追加一条：写含 `严重度: 严重`（r2.7 key 形）的审计文件到 tmp project → 走该集成路径断言 issue 发射；generic pwi 路由测试：构造 `G4.av.vocab:...` finding → pwi 复核命中。
- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/llm_output_integrity.py tools/replay_severity_vocab.py \
  src/shenbi/pipeline/dispatch_helper.py src/shenbi/gates/g4/generic.py \
  tests/unit/pipeline/test_check_audit_severity_vocab.py
git commit -m "feat: spec #105 T2 — G4.av.vocab 词表外 fail-loud（三段式判别器+双点位接线+vol1 回放 shadow 闸过）"
```

---

### Task 5: 审计派发前置预检 + G4.av.dispatch_integrity（spec T3）

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py`（新增 `missing_audit_reads(project_dir, skill, chapter) -> list[str]`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:3907+`（`_run_audit_wave_step` 头部预检）
- Modify: `src/shenbi/pipeline/llm_output_integrity.py`（新增 `check_audit_dispatch_integrity(path: Path) -> list[str]`）
- Modify: `src/shenbi/gates/g4/generic.py`（Task 4 预留的第三路由落位）
- Test: `tests/unit/pipeline/test_audit_readiness.py`（新建）

**Interfaces:**
- Consumes: `load_contract(skill) -> Contract`（contracts/loader.py:295）；`OPTIONAL_READS`（dispatch_helper.py:509）；`#51 ghost-chain guard` 控制流（chapter_loop.py:3836-3862）；escalation reads 三态语义（revision_router.py:268-303——语义复刻非代码复用）。
- Produces:
  - `missing_audit_reads(project_dir: Path, skill: str, chapter: int | None) -> list[str]`——缺失 required reads 的 resolved 路径清单（OPTIONAL fnmatch 剔除/produces[writes∪updates] 剔除/glob 展开/其余 .exists() 判）
  - `check_audit_dispatch_integrity(path: Path) -> list[str]`——issue 形态 `G4.av.dispatch_integrity:{path.name} — 派发完整性签名 BLOCKING（框架 bug 非正文缺陷）：报告判无效，须修框架不应由审计员表达`；签名=（`` `chapters/``/``plans/``/``truth/`` 前缀路径 token，反引号包裹优先）∧（`重跑|补齐|补入`）合取，**仅 BLOCKING 锚定行**（用 severity.BRACKET_ANCHOR_RE/BOLD 锚定判定行内含 BLOCKING 词表内词）。

- [ ] **Step 1: 失败测试**——三组：
  1. `missing_audit_reads` 单测：tmp project + stub contract（monkeypatch `load_contract` 返回 `{"reads": ["chapters/chapter-N.md", "truth/current_state.md", "characters/*.md"], "writes": ["audits/chapter-N-x.md"], "updates": []}`；OPTIONAL_READS monkeypatch 空或缺省）→ 缺 chapters 文件时返回含该路径、glob 有匹配时 characters 不缺、writes 产物（audits/...）不算缺。
  2. **零派发红测**（`_must_not_dispatch` 先例 tests/pipeline/test_redispatch_g4_and_draft_precheck.py:113（`_must_not_dispatch` def 行——r2-M3 校准）——执行期读该文件照搬 monkeypatch `dispatch_helper.dispatch_skill` 手法）：构造 wave 内某审计技能 required read 缺失 → `_run_audit_wave_step` 不派任何 LLM（monkeypatch 派发函数断言零调用）+ escalation checkpoint 置位。
  3. `check_audit_dispatch_integrity` 红绿：红=``- [BLOCKING] 派发完整性：请补齐 `chapters/chapter-40.md` 与 `plans/chapter-40-plan.md` 后重跑本维度``（chapter-40-reader-pull.md:44 原文）→ issue；红2=``- [BLOCKING] 输入缺失：请补入 `chapters/chapter-10.md` 后重跑``；绿=``- [BLOCKING] 字数不足，请补齐至 3200 字``（无路径 token）→ 无 issue；绿2=`- [MINOR] 派发完整性相关表述`（非 BLOCKING 行）→ 无 issue。
- [ ] **Step 2: 确认失败**。
- [ ] **Step 3: 实现 `missing_audit_reads`**（audit_layer.py）——语义按 revision_router.py:268-303 三态复刻：`_entry_file` 剥 dict 形 read；`resolved = str(rel).replace("chapter-N", f"chapter-{chapter}")`（chapter None 时保持 N 字面——与 :276-282 同）；produces 剔除；`any(fnmatch(resolved, pat) for pat in OPTIONAL_READS.get(skill, []))` 剔除；`"*" in resolved` 时 `Path(project_dir).glob(...)` 命中即非缺；其余 `.exists()` 判缺失。docstring 注明 spec #105 T3 与 M1 作用域（仅审计派发面）。
- [ ] **Step 4: 实现 `check_audit_dispatch_integrity`**（llm_output_integrity.py）——逐行扫：行含 BLOCKING 锚定（bracket `- [BLOCKING]` 或 bold 词表内 BLOCKING——用 severity 单源锚定形，r3-I2：无 key 形）∧ 行内 `` `(chapters|plans|truth)/[^`]+` `` 反引号路径（无反引号时裸路径 `(?:chapters|plans|truth)/\S+\.(?:md|yaml|json)` 兜底）∧ 行内 `重跑|补齐|补入` → issue（每文件首条即断——幂等）。
- [ ] **Step 5: wave 预检接线**——`_run_audit_wave_step` 函数头（state/project_dir 就绪后、任何派发前）：

```python
missing: dict[str, list[str]] = {}
for skill in wave_skills:  # 该 wave 的审计技能名册（执行期以函数内实际变量名落定）
    gaps = missing_audit_reads(project_dir, skill, chapter)
    if gaps:
        missing[skill] = gaps
if missing:
    log.error("audit_reads_missing_precheck", chapter=chapter, missing=missing)
    set_checkpoint(
        state,
        CheckpointType.ESCALATION,
        chapter=chapter,
        context=f"审计派发前置预检（spec #105 T3）：{missing}——required reads 缺失，"
        "禁止派发 LLM 表达输入缺失（派发完整性语义拆分）。请人工核查输入产物后重试。",
    )
    return True
```

（**预检名册（I-4 结构修正）**：`_run_audit_wave_step`（:3916）为双 wave 结构——预检圈定=core wave 名册 ∪ `get_active_genre_audits(genre_config)`（genre 圈——签名收 Mapping 非 project_dir，r2-M4 校准；genre-config.json 现由 chapter_loop:4009-4011 加载——**须将该加载+名册装配上提到 wave-1 派发之前**）∪ 串行分区成员（`_partition_review_wave` 输出）；预检置于**名册装配完成后、任一 `dispatch_*` 调用前**；**零派发红测两变体**（core 技能缺 read + genre 圈技能缺 read——I-4 自认「只圈 core 不被测试捕获」，genre 变体即钉住该结构）；**bundle 模式**：`bundle_chapters`（:1472）可返 `[N, N+1]`——预检循环按 `wave_chapters` 展开逐章查（r2-M7：follower 章输入缺失不漏检）——只圈 core wave 会漏 genre 审计派发的欠覆盖且不被任何测试捕获。`set_checkpoint` 签名 machine.py:69（chapter/context kwargs）；#51 同款 `return True` 停步语义。）
- [ ] **Step 6: generic 第三路由落位**——`G4.av.dispatch_integrity` → `check_audit_dispatch_integrity`（Task 4 的未识别放行分支前插入）。
- [ ] **Step 7: 全部测试绿**——`uv run pytest tests/unit/pipeline/test_audit_readiness.py tests/unit/pipeline/test_check_audit_severity_vocab.py -q` + `uv run pytest tests/pipeline -q`（零派发红测所在既有套件零回归）。
- [ ] **Step 8: vol1 回放差集**——`uv run python tools/replay_severity_vocab.py novel-xinghuo-vol1 --out /tmp/spec105-di-replay.md`（工具扩展：同时跑 dispatch_integrity checker 或单独小跑）——预期命中 ch10/12/14/16/20/40 实弹族（这些是历史框架 bug 产物，非误伤）；**非实弹族命中=误伤→停，记 BLOCKING deviation 报备**（r3-M4：与 T4 Step 6 同款停机分支）；粘贴计数进 progress.md。
- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/audit_layer.py src/shenbi/pipeline/chapter_loop.py \
  src/shenbi/pipeline/llm_output_integrity.py src/shenbi/gates/g4/generic.py \
  tests/unit/pipeline/test_audit_readiness.py
git commit -m "feat: spec #105 T3 — 审计派发前置预检（#51 控制流先例）+G4.av.dispatch_integrity 签名合取兜底"
```

---

### Task 6: G4_FORMAT_EXAMPLES 名册差集 + 补键（spec T4a）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:882+`（G4_FORMAT_EXAMPLES 补三键）
- Test: `tests/unit/pipeline/test_g4_format_examples_roster.py`（新建）

**Interfaces:**
- Consumes: g4 checker 名册（`src/shenbi/gates/g4/` 各 checker 的 id 发射面）；`_enrich_g4_feedback`（chapter_loop.py:1120）。
- Produces: EXAMPLES 新键 `G4.cp.scene_budget`/`G4.av.vocab`/`G4.av.dispatch_integrity`。

- [ ] **Step 1: 名册差集盘点（一次性 diff）**——`grep -rhoE "G4\.[a-z0-9_.]+" src/shenbi/gates/g4/ | sort -u`（M-12：**不带闭引号**——f-string 连续形 id 后随 `:` 非引号，带闭引号低估差集） vs `uv run python -c "from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES; print('\n'.join(sorted(G4_FORMAT_EXAMPLES)))"`——差集落 plan deviation/progress.md（哪些族无示例=known gap，本 task 只补首批三键，其余登记不强补）。
- [ ] **Step 2: 失败测试**——`test_g4_format_examples_roster.py`：断言三键在册 + 示例文案含期望格式关键词（scene_budget 例含「场景预算节」与表格/带域形态——文案从 `src/shenbi/gates/g4/chapter_planning.py:612-706` checker 期望结构提炼：`| 场景 | 类型 | 字数带 | 配对性 |` 型行）；断言示例非空字符串。
- [ ] **Step 3: 补三键**——`G4.cp.scene_budget`（对照 escalation-35-report.md:33-37 兜底行形态写「期望格式」）；`G4.av.vocab`（示例：「严重度条目改写：`- [BLOCKING]`/`- [CRITICAL]`/`- [MINOR]` 三选一锚定形，禁用词表外语」）；`G4.av.dispatch_integrity`（示例：「该 finding 属框架 bug——不写派发完整性 BLOCKING，输入缺失由框架预检拦截；审计员只审计正文」）。
- [ ] **Step 4: 判据验证**——`git grep -n "scene_budget" src/shenbi/pipeline/chapter_loop.py` 命中 EXAMPLES；`uv run pytest tests/unit/pipeline/test_g4_format_examples_roster.py -q` 绿。
- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_g4_format_examples_roster.py
git commit -m "feat: spec #105 T4a — G4_FORMAT_EXAMPLES 补 scene_budget/vocab/dispatch_integrity 三键+名册差集盘点"
```

---

### Task 7: aggregate 条目级 severity + longitudinal parser 同步（spec T4b）

**Files:**
- Modify: `src/shenbi/pipeline/audit_aggregate.py:167-176`（render 条目行）
- Modify: `tools/report_longitudinal.py:547-567`（`_parse_aggregate_sections` 双格式容差）
- Test: `tests/pipeline/test_audit_aggregate.py`（既有套件追加——integration 目录，M-8 修正）/`tests/unit/tools/test_report_longitudinal.py`（追加或新建）

**Interfaces:**
- Consumes: `SECTION_HEADER_RE`（Task 1）；`write_audit_aggregate`（audit_aggregate.py:195+——r2-M3 校准：:157 是 render_aggregate）。
- Produces: render 条目行 `- **{sev}** · {text}`；parser 兼容新旧两格式。

- [ ] **Step 1: 失败测试**——render 测试：构造 FindingUnit(severity="MINOR", text="x") → 输出含 `- **MINOR** · x` 且节头保留 `## MINOR Findings`；parser 红绿：新格式 `- **BLOCKING** · 文本` → FindingUnit("BLOCKING", "文本")（前缀剥离）；旧格式 `- 文本` 在 BLOCKING 节 → FindingUnit("BLOCKING", "文本")（双格式容差）；`- 报告方: ...` 行仍跳过。
- [ ] **Step 2: 实现 render**——:175 `parts.append(f"- {u.text}")` →（r2-M3 校准：:174 是 for 行） `parts.append(f"- **{u.severity}** · {u.text}")`（报告方行不变）。
- [ ] **Step 3: 实现 parser 双格式**——`_parse_aggregate_sections` 条目行解析：`m = re.match(r"^-\s*\*\*([A-Z]+)\*\*\s*·\s*(.+)$", s)` 命中→（校验 m.group(1)==sev 或以其为准——**以条目级为准**，与节头不一致时条目级胜出并保留）；未命中→现行为 `s.lstrip("- ").strip()`；节头判定换 `SECTION_HEADER_RE`（已在 Task 2 换装——此处仅确认行为）。
- [ ] **Step 4: 下游消费差分**——`git grep -rn "aggregate.md" -- src/ tools/ tests/ | grep -v test_` 列全消费面；对每面确认新旧格式兼容（report_longitudinal 已改；其余面 grep 确认无 `- {text}` 形态解析依赖——若发现新解析点，同批改并加测试）。
- [ ] **Step 5: 全绿**——`uv run pytest tests/pipeline/test_audit_aggregate.py tests/unit/tools/test_report_longitudinal.py -q`。
- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/audit_aggregate.py tools/report_longitudinal.py \
  tests/pipeline/test_audit_aggregate.py tests/unit/tools/test_report_longitudinal.py
git commit -m "feat: spec #105 T4b — aggregate 条目级 severity 渲染+longitudinal parser 双格式容差同步"
```

---

### Task 8: ending_constraints 注入窗 3→10（spec T4c）

**Files:**
- Modify: `src/shenbi/pipeline/review_checklist.py:530-548`（窗口+守卫+docstring+注释）
- Test: 既有 `tests/` 中 `_get_recent_ending_types`/ending_constraints 相关测试（grep 定位，追加/更新断言）

**Interfaces:**
- Consumes: 无新依赖。
- Produces: 注入块 ending_constraints 列表长度 10（SKILL.md:166 文案零改动即重新为真）。

- [ ] **Step 1: 定位既有测试**——`grep -rn "_get_recent_ending_types\|ending_constraints" tests/`——更新断言（M-6 修正）：chapter≥11 且前章全在盘时长度 10；chapter=10 返回 []（守卫 `< 11` 先挡）；chapter=11 缺一章时长度 10 含一个 `"missing"`（:546-547 现行为）。
- [ ] **Step 2: 实现**——`if chapter < 4` → `if chapter < 11`（注释 `(need 3 prior chapters)` → `(need 10 prior chapters)`）；`range(3, 0, -1)` → `range(10, 0, -1)`；docstring `last 3 chapters` → `last 10 chapters`。**SKILL.md 零改动**（判据：文案零改动即重新为真）。
- [ ] **Step 3: 绿**——`uv run pytest -q -k "ending"`（或定位到的测试文件）。
- [ ] **Step 4: Commit**

```bash
git add src/shenbi/pipeline/review_checklist.py tests/
git commit -m "feat: spec #105 T4c — ending_constraints 注入窗 3→10（chapter<11 守卫连带，SKILL 文案零改动归真）"
```

---

## Self-Review

1. **Spec coverage**：spec T1（T1a 登记+模块/T1b 换装+差分三层/T1c lint）✓；T2（T4：判别器三段式+双点位+回放 shadow）✓；T3（T5：预检+dispatch_integrity+零派发红测）✓；T4（T6 EXAMPLES/T7 渲染+parser/T8 ending 窗）✓；验收 2 差分（T2b）/验收 3 bug-hunt 由 T4 红测+T5 零派发承载/验收 4 G3.4 ≥94 由阶段 6 收官评分承载。
2. **Placeholder scan**：两处「执行期落定」均为**事实锚定指令**（T5 wave 技能名册变量/T2 gen stdout 中转——r5-M1 更正：parallel_dispatch 函数名一项已随 r4-M1 空桩删除而消亡），非行为留白——实现时 grep 落定并记 deviation。
3. **Type consistency**：`check_audit_severity_vocab(path: Path, forms: tuple[str, ...] = PRODUCTION_VOCAB_FORMS) -> list[str]` 与 dispatch_helper/generic 调用面一致；`missing_audit_reads(project_dir, skill, chapter)` 与 wave 预检调用一致；severity.py 符号名在 T1/T2/T4/T5/T7 间一致（`AGGREGATE_VOCAB_SET`/`ROUTING_*_BRACKET_WORDS` 在 T1 Interfaces/Step 3 落定——r2 修正：初稿 Self-Review 误称「已含」，实为漏列，已在 T1 补齐）。
