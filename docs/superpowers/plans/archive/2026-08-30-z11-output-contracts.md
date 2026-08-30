# Z11 产物契约（SDD #20 · R1+R3）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 章节产物契约闭环——写入路径规范化 `# Chapter N:` 头 + G2 FAIL 级章节契约检查（含豁免清单）+ 存量 56 章批量修复；管线章节收尾处产物契约检查（progress.json 空壳 / token-ledger 缺席 → FAIL-CLOSED）。

**Architecture:** 契约正则单源化到 `gates/shared.py`（g2 与 dispatch_helper 共用）；写入侧规范化挂在 `dispatch_helper._write_one` 的章节写路径（写前内容规范化，post-snapshot 前完成，不干扰 write-audit）；产物契约检查为独立纯函数模块 `pipeline/product_contracts.py`，由 `chapter_loop._complete_chapter` 调用。

**Tech Stack:** Python 3.11+ / pytest / structlog / pathlib。spec：`docs/superpowers/specs/2026-08-14-z11-output-contracts-design.md`（R2 已移交 C22，不在本 plan）。

## Global Constraints

- `src/shenbi/` 禁 `print()`（structlog）；gate 检查器纯函数幂等无副作用（无 .bak）
- fixtures 只能是真实产物副本（G0.9/G0.11），路径 `tests/fixtures/`
- 禁真实 dispatch 验证（核心原则 8）；验证一律 `uv run`/`just`（CI 同构）
- 状态字面量/正则单源：META 与章节头正则唯一定义于 `src/shenbi/gates/shared.py`
- Conventional commits；每 task 产出 `.superpowers/sdd/audit-T<N>.md`

---

### Task 1: 契约正则单源 + 写入路径章节头规范化（R1a · infra，协调者亲实现）

**Files:**
- Modify: `src/shenbi/gates/shared.py`（新增 `META_BLOCK_RE`、`CHAPTER_HEADER_RE`）
- Modify: `src/shenbi/gates/g2.py:31`（`_META_RE` 改为从 shared 导入的别名，禁止双正则）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（`_write_one` 写前规范化 + 纯函数 `ensure_chapter_header`）
- Test: `tests/unit/gates/test_chapter_contract_re.py`（新增）、`tests/unit/pipeline/test_dispatch_helper.py`（追加）

**Interfaces:**
- Produces: `shenbi.gates.shared.META_BLOCK_RE: re.Pattern[str]`、`shenbi.gates.shared.CHAPTER_HEADER_RE: re.Pattern[str]`（`^#\s+Chapter\s+\d+`，MULTILINE）、`shenbi.gates.shared.CHAPTER_NUM_RE: re.Pattern[str]`（`chapter-(\d+)`，锚定 stem 用 match）`shenbi.pipeline.dispatch_helper.ensure_chapter_header(content: str, chapter_num: int) -> str`（幂等：已有合规头原样返回；缺失则在顶部插入 `# Chapter {n}:\n\n`，不动其余内容）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/gates/test_chapter_contract_re.py
import re

from shenbi.gates.shared import CHAPTER_HEADER_RE, META_BLOCK_RE


def test_chapter_header_re_matches_contract_form() -> None:
    assert CHAPTER_HEADER_RE.match("# Chapter 1:")
    assert CHAPTER_HEADER_RE.match("# Chapter 56: 星火")
    assert not CHAPTER_HEADER_RE.match("## Chapter 1")   # h2 不算
    assert not CHAPTER_HEADER_RE.match("Chapter 1")      # 无 # 前缀


def test_meta_block_re_is_single_source() -> None:
    assert META_BLOCK_RE.search("正文\n<!--META-BEGIN-->\nfoo\n<!--META-END-->\n尾")
    # 与 g2 既有 _META_RE 行为一致（DOTALL 跨行）
    from shenbi.gates.g2 import _META_RE
    assert _META_RE.pattern == META_BLOCK_RE.pattern
```

```python
# tests/unit/pipeline/test_dispatch_helper.py 追加
from shenbi.pipeline.dispatch_helper import ensure_chapter_header


def test_ensure_chapter_header_inserts_when_missing() -> None:
    body = "第一段正文。\n第二段。"
    out = ensure_chapter_header(body, 7)
    assert out == "# Chapter 7:\n\n第一段正文。\n第二段。"


def test_ensure_chapter_header_idempotent_when_present() -> None:
    body = "# Chapter 7: 标题\n\n正文。"
    assert ensure_chapter_header(body, 7) == body


def test_write_parsed_outputs_normalizes_chapter_header(tmp_path, monkeypatch):
    """集成：走 _write_parsed_outputs 真实写路径，chapter-3.md 缺头被规范化。"""
    from shenbi.pipeline import dispatch_helper as dh

    resp = "### FILE: chapters/chapter-3.md\n正文，无头。\n"
    paths = ["chapters/chapter-3.md"]
    dh._write_parsed_outputs(resp, paths, tmp_path, skill="shenbi-chapter-drafting")
    text = (tmp_path / "chapters" / "chapter-3.md").read_text(encoding="utf-8")
    assert text.startswith("# Chapter 3:")
```

- [ ] **Step 2: 跑测试确认失败**：`uv run pytest tests/unit/gates/test_chapter_contract_re.py tests/unit/pipeline/test_dispatch_helper.py -k 'chapter_header or chapter_contract or normalizes_chapter' -v` → FAIL（ImportError / assert）

- [ ] **Step 3: 实现**

```python
# src/shenbi/gates/shared.py 追加
#: Chapter-file contract anchors. SINGLE SOURCE for both the write-path
#: normalizer (pipeline.dispatch_helper) and the gate-side check (gates.g2).
META_BLOCK_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)
CHAPTER_HEADER_RE = re.compile(r"^#\s+Chapter\s+\d+", re.MULTILINE)
CHAPTER_NUM_RE = re.compile(r"chapter-(\d+)")
```

```python
# src/shenbi/gates/g2.py:31 改为
from shenbi.gates.shared import META_BLOCK_RE as _META_RE  # 单源别名，保持既有引用
```
（g2.py 文件内 `re.compile` 原行删除；确认 g2 无其他 `_META_RE` 重定义。）

```python
# src/shenbi/pipeline/dispatch_helper.py（llm_output_integrity 检查同区，_write_one 上方）
from shenbi.gates.shared import CHAPTER_HEADER_RE


def ensure_chapter_header(content: str, chapter_num: int) -> str:
    """Insert the contract chapter header if missing. Idempotent."""
    first_line = content.lstrip().split("\n", 1)[0]
    if CHAPTER_HEADER_RE.match(first_line):
        return content
    return f"# Chapter {chapter_num}:\n\n" + content
```
`_write_one` 中 `safe_write(full_path, content)` 前（else 整文件写分支）：文件名 `chapter-(\d+)` 且非 audit（`_CHAPTER_NUM_RE` 改为从 shared 导入的别名 `CHAPTER_NUM_RE`，与 G2 单源；`_is_audit_file` 本地复用）→ `content = ensure_chapter_header(content, int(m.group(1)))`。append_dedup 分支不涉及章节文件，不动。

- [ ] **Step 4: 跑测试确认通过**（同 Step 2 命令 → PASS）
- [ ] **Step 5: Commit** `git add src/shenbi/gates/shared.py src/shenbi/gates/g2.py src/shenbi/pipeline/dispatch_helper.py tests/unit/gates/test_chapter_contract_re.py tests/unit/pipeline/test_dispatch_helper.py && git commit -m "feat: single-source chapter-contract regexes + write-path header normalization (z11 R1a, F1301)"` → 产出 `.superpowers/sdd/audit-T1.md`

---

### Task 2: G2.chapter_contract FAIL 检查 + 豁免清单（R1b · infra，协调者亲实现）

**Files:**
- Create: `docs/framework/z11-chapter-exemptions.json`
- Create: `tests/fixtures/z11/chapter-40-no-meta.md`（真实 chapter-40.md 精确副本，G0.11 哈希一致）、`tests/fixtures/z11/chapter-41-with-meta.md`（真实含 META 章节副本）
- Modify: `src/shenbi/gates/g2.py`（chapter 分支新增 G2.13 检查）
- Modify: `src/shenbi/gates/shared.py`（`load_chapter_exemptions()`，只读）
- Test: `tests/unit/gates/test_g2_chapter_contract.py`

**Interfaces:**
- Consumes: Task 1 的 `CHAPTER_HEADER_RE`/`META_BLOCK_RE`
- Produces: `shenbi.gates.shared.load_chapter_exemptions() -> dict[str, set[int]]`（project→chapters；文件缺失返回空 dict，不 raise）；G2 检查 ID `G2.13`（file_type=="chapter" 时：头行合规 + META 命中或在豁免清单，否则 FAIL 进 `mf`）

- [ ] **Step 1: 建 fixtures（真实副本）**

```bash
mkdir -p tests/fixtures/z11 docs/framework
cp novel-output/xinghuo-ranqiong/chapters/chapter-40.md tests/fixtures/z11/chapter-40-no-meta.md
cp novel-output/xinghuo-ranqiong/chapters/chapter-41.md tests/fixtures/z11/chapter-41-with-meta.md
shasum -a 256 novel-output/xinghuo-ranqiong/chapters/chapter-40.md tests/fixtures/z11/chapter-40-no-meta.md  # 两行须一致，贴 progress.md
```

```json
// docs/framework/z11-chapter-exemptions.json（6 章缺 META 的既有事实，非伪造产物）
{
  "version": 1,
  "reason": "z11 F1302: chapters produced before META contract enforcement; META is LLM-generated and must not be hand-fabricated (G0.9)",
  "exemptions": [
    {"project": "xinghuo-ranqiong", "chapter": 2},
    {"project": "xinghuo-ranqiong", "chapter": 9},
    {"project": "xinghuo-ranqiong", "chapter": 12},
    {"project": "xinghuo-ranqiong", "chapter": 40},
    {"project": "xinghuo-ranqiong", "chapter": 44},
    {"project": "xinghuo-ranqiong", "chapter": 55}
  ]
}
```

- [ ] **Step 2: 写失败测试**

```python
# tests/unit/gates/test_g2_chapter_contract.py
import json
from pathlib import Path

from shenbi.gates.g2 import gate_G2
from shenbi.gates.shared import load_chapter_exemptions

FIX = Path("tests/fixtures/z11")


def test_exemptions_load() -> None:
    ex = load_chapter_exemptions()
    assert 40 in ex.get("xinghuo-ranqiong", set())


def test_g2_chapter_contract_meta_exemption_passes(tmp_path):
    # fixture 副本经 Task 3 前仍无头且无 META；路径不含 novel-output/xinghuo-ranqiong 段，
    # 复制到带项目段路径以测试豁免推导
    proj = tmp_path / "novel-output" / "xinghuo-ranqiong" / "chapters"
    proj.mkdir(parents=True)
    f = proj / "chapter-40.md"
    f.write_text("# Chapter 40:\n\n" + FIX.joinpath("chapter-40-no-meta.md").read_text(encoding="utf-8"), encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter", project_dir=str(tmp_path / "novel-output" / "xinghuo-ranqiong")))
    ids = [c["id"] for c in result.get("checks", [])]
    assert "G2.13" in ids  # 豁免命中 → PASS 记录


def test_g2_chapter_contract_fails_on_no_header_no_meta(tmp_path):
    proj = tmp_path / "novel-output" / "other" / "chapters"
    proj.mkdir(parents=True)
    f = proj / "chapter-99.md"
    f.write_text("无头无 META 正文。", encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter"))
    assert any(c["id"] == "G2.13" and c["s"] == "FAIL" for c in result.get("checks", []))


def test_g2_chapter_contract_passes_compliant(tmp_path):
    f = tmp_path / "chapter-41.md"
    body = FIX.joinpath("chapter-41-with-meta.md").read_text(encoding="utf-8")
    f.write_text("# Chapter 41:\n\n" + body, encoding="utf-8")
    result = json.loads(gate_G2(str(f), "chapter"))
    assert any(c["id"] == "G2.13" and c["s"] == "PASS" for c in result.get("checks", []))
    # fixture 若本身已有 META 命中即 PASS；无豁免需求
```

- [ ] **Step 3: 跑测试确认失败**（G2.13 不存在 → FAIL）
- [ ] **Step 4: 实现**

```python
# src/shenbi/gates/shared.py 追加
_EXEMPTIONS_PATH = Path(__file__).resolve().parents[2] / "docs" / "framework" / "z11-chapter-exemptions.json"


def load_chapter_exemptions() -> dict[str, set[int]]:
    """Read-only load of z11 chapter META exemptions. Missing file -> {}."""
    try:
        data = json.loads(_EXEMPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, set[int]] = {}
    for e in data.get("exemptions", []):
        out.setdefault(str(e.get("project", "")), set()).add(int(e.get("chapter", -1)))
    return out
```
（json 已在 shared.py 导入则复用，否则补 `import json`；路径解析须以 `parents[2]` 校验真实落位——实现时以仓库根实际相对层级为准并跑测试确认。）

```python
# src/shenbi/gates/g2.py — file_type == "chapter" 分支末尾（G2.12 之后）追加
        if file_type == "chapter":
            # G2.13 — chapter contract: header + META-or-exemption (z11 F1301/F1302)
            m = CHAPTER_NUM_RE.match(p.stem)  # 单源正则（自 shared 导入，锚定 stem，避免误配 decisions/plan/audit 名）
            first_line = content.lstrip().split("\n", 1)[0]
            header_ok = bool(CHAPTER_HEADER_RE.match(first_line)) if m else True
            project = ""
            pm = re.search(r"novel-output/([^/]+)/", str(p))
            if pm:
                project = pm.group(1)
            meta_ok = bool(_META_RE.search(content)) or (
                m is not None and int(m.group(1)) in load_chapter_exemptions().get(project, set())
            )
            if header_ok and meta_ok:
                checks.append({"id": "G2.13", "file": fp, "s": "PASS"})
            else:
                reasons = []
                if not header_ok:
                    reasons.append("missing '# Chapter N:' header")
                if not meta_ok:
                    reasons.append("missing META block (not exempted)")
                mf.append({"id": "G2.13", "file": fp, "s": "FAIL", "r": "; ".join(reasons)})
```
（`CHAPTER_HEADER_RE`、`CHAPTER_NUM_RE`、`load_chapter_exemptions` 自 shared 导入；`re` g2 已有；project 段提取 `novel-output/([^/]+)/` 为路径解析非契约正则，内联可。非 chapter-N 命名的 chapter 类型文件不判头，只判 META——以 `m is None` 时 header_ok=True 实现。）

- [ ] **Step 5: 跑测试确认通过** + 全量 `uv run pytest tests/unit/gates/ -q`。**已知回归面（plan 审查核实）**：tests/unit/gates/test_g2.py 约 34 处 `chapter-*.md` tmp fixture 无头无 META 且路径无 `novel-output/<project>/` 段（project=""，豁免不可达）——断言 `status=="PASS"` 的用例（test_g2.py:414/514/548 等）会被 G2.13 打红。处置：这些 tmp fixture 属「契约前旧形态」，逐个给 fixture 内容补 `# Chapter N:` 头 + `<!--META-BEGIN-->…<!--META-END-->` 块（不是加豁免、不是 monkeypatch 跳过）；仅当某用例语义就是测「无头文件」时，改其断言为期待 G2.13 FAIL。逐一核对语义后修，改动清单贴 audit-T2.md
- [ ] **Step 6: Commit** `git add src/shenbi/gates/shared.py src/shenbi/gates/g2.py docs/framework/z11-chapter-exemptions.json tests/fixtures/z11/ tests/unit/gates/test_g2_chapter_contract.py && git commit -m "feat: G2.13 chapter-contract check with exemption list (z11 R1b, F1301/F1302)"` → `audit-T2.md`

---

### Task 3: 存量 56 章批量修复（R1c · oneoff 脚本）

**Files:**
- Create: `tools/oneoff/insert_chapter_headers.py`
- Modify: `novel-output/xinghuo-ranqiong/chapters/chapter-{1..56}.md`（56 个，机器插入头行）

**Interfaces:**
- Consumes: Task 1 `ensure_chapter_header`

- [ ] **Step 1: 写脚本**

```python
"""One-off: insert contract chapter headers into existing novel-output chapters.

z11 SDD #20 R1c (F1301). Deterministic, no LLM. Delete after merge window or
keep under tools/oneoff/ as immutable history — never wire into CI/just.
"""
import sys
from pathlib import Path

from shenbi.pipeline.dispatch_helper import ensure_chapter_header

ROOT = Path("novel-output/xinghuo-ranqiong/chapters")


def main() -> int:
    changed = 0
    for f in sorted(ROOT.glob("chapter-*.md")):
        if "-plan" in f.stem or "-audit" in f.stem:
            continue
        num = int(f.stem.removeprefix("chapter-"))
        text = f.read_text(encoding="utf-8")
        new = ensure_chapter_header(text, num)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
            print(f"inserted: {f.name}")
    print(f"total changed: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 跑脚本 + 验收断言**

```bash
uv run python tools/oneoff/insert_chapter_headers.py
grep -l '^# Chapter ' novel-output/xinghuo-ranqiong/chapters/chapter-{1..56}.md 2>/dev/null | wc -l   # 期望 56
grep -rl '<!--META-BEGIN-->' novel-output/xinghuo-ranqiong/chapters/ | grep -v -E 'chapter-(2|9|12|40|44|55)\.md' | wc -l  # 期望 50（其余 6 章豁免）
uv run pytest tests/unit/gates/test_g2_chapter_contract.py -q   # PASS
```
注意：`ensure_chapter_header` 幂等，重复跑 changed=0。脚本输出与两条验收命令输出贴 progress.md `## 验收证据`。

- [ ] **Step 3: 抽验正文无损**——`git diff --stat novel-output/` 仅 56 章、每章 diff 仅首部 `+# Chapter N:`（+空行），无其他行变动；`git diff novel-output/xinghuo-ranqiong/chapters/chapter-1.md | head -10` 贴 progress.md
- [ ] **Step 4: Commit** `git add tools/oneoff/insert_chapter_headers.py novel-output/xinghuo-ranqiong/chapters/ && git commit -m "fix: batch-insert contract headers into 56 existing chapters (z11 R1c, F1301)"` → `audit-T3.md`

---

### Task 4: 产物契约检查 + 章节收尾接线（R3 · infra，协调者亲实现）

**Files:**
- Create: `src/shenbi/pipeline/product_contracts.py`
- Create: `tests/fixtures/z11/progress-shell-bad.json`（真实 progress.json 副本）、`tests/fixtures/z11/progress-complete-good.json`（真实副本 + ProgressDoc 合规字段）
- Modify: `src/shenbi/exceptions.py`（`ProductContractError(FrameworkError)`）、`src/shenbi/pipeline/chapter_loop.py`（`_complete_chapter` 接线）
- Test: `tests/unit/pipeline/test_product_contracts.py`

**Interfaces:**
- Produces: `shenbi.pipeline.product_contracts.check_product_contracts(project_dir: Path) -> list[str]`（纯函数，只读；返回违规描述清单）+ `ProductContractError`
- Consumes: `chapter_loop._complete_chapter(state, chapter)`（chapter_loop.py:1179 `return _complete_chapter(state, chapter)` 调用链）

- [ ] **Step 1: 建 fixtures**

```bash
cp novel-output/xinghuo-ranqiong/progress.json tests/fixtures/z11/progress-shell-bad.json
```
`progress-complete-good.json`：以真实副本为底，追加 **ProgressDoc 契约实际字段**（`src/shenbi/contracts/schemas/state.py:19`：`skills`、`completed_skill_names`；注意 `closure`/`total_chapters` 在 novel.json 不在 progress.json，不得发明键名）——最小合规形态 = 真实副本 + `"skills": {"shenbi-chapter-drafting": {"generative": {"status": "done"}}}` + `"completed_skill_names": ["shenbi-chapter-drafting"]`。空壳判定 = 键集 ⊆ {current_scorer_agent, scoring_history}。

- [ ] **Step 2: 写失败测试**

```python
# tests/unit/pipeline/test_product_contracts.py
import json
from pathlib import Path

import pytest

from shenbi.pipeline.product_contracts import check_product_contracts

FIX = Path("tests/fixtures/z11")
SCORER_KEYS = {"current_scorer_agent", "scoring_history"}


def _mk(tmp_path: Path, progress: dict | None, ledger_lines: list[str] | None) -> Path:
    if progress is not None:
        (tmp_path / "progress.json").write_text(json.dumps(progress, ensure_ascii=False), encoding="utf-8")
    if ledger_lines is not None:
        (tmp_path / "cost").mkdir()
        (tmp_path / "cost" / "token-ledger.jsonl").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    return tmp_path


def test_shell_progress_is_violation(tmp_path):
    bad = json.loads(FIX.joinpath("progress-shell-bad.json").read_text(encoding="utf-8"))
    v = check_product_contracts(_mk(tmp_path, bad, ["{}"]))
    assert any("progress" in x for x in v)


def test_complete_progress_plus_ledger_passes(tmp_path):
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    assert check_product_contracts(_mk(tmp_path, good, ["{}"])) == []


def test_missing_ledger_is_violation(tmp_path):
    good = json.loads(FIX.joinpath("progress-complete-good.json").read_text(encoding="utf-8"))
    v = check_product_contracts(_mk(tmp_path, good, None))
    assert any("token-ledger" in x for x in v)


def test_no_progress_file_no_violation(tmp_path):
    """project_dir 无 progress.json（未开始记账的目录）不报——检查只针对已进入章节收尾的项目。"""
    assert check_product_contracts(_mk(tmp_path, None, None)) == []


def test_complete_chapter_raises_on_contract_violation(tmp_path, monkeypatch):
    """接线验证：_complete_chapter 对空壳项目 raise ProductContractError。"""
    from shenbi.exceptions import ProductContractError
    from shenbi.pipeline import chapter_loop as cl

    (tmp_path / "progress.json").write_text(json.dumps(json.loads(FIX.joinpath("progress-shell-bad.json").read_text(encoding="utf-8"))), encoding="utf-8")
    state = ...  # 以既有 chapter_loop 测试的 state 构造方式为准（复制 tests/unit/pipeline/test_chapter_loop.py 中 _complete_chapter 相关用例的构造）
    with pytest.raises(ProductContractError):
        cl._complete_chapter(state, 1)
```
（最后一个用例的 state 构造在实现时对齐既有测试惯用法；若 `_complete_chapter` 直接用 `state.project_dir`，则 state 用最小 stub。）

- [ ] **Step 3: 跑测试确认失败**（模块不存在 → collection error）
- [ ] **Step 4: 实现**

```python
# src/shenbi/exceptions.py 追加（FrameworkError 子类区）
class ProductContractError(FrameworkError):
    """Pipeline product artifacts violate the output contract (z11 F1309/F1313)."""
```

```python
# src/shenbi/pipeline/product_contracts.py
"""Product-contract checks for pipeline output artifacts (z11 SDD #20 R3).

Pure, read-only, idempotent: returns a list of violation descriptions.
Wired into chapter completion (chapter_loop._complete_chapter) FAIL-CLOSED;
the fix bodies for F640/F302 live in specs #27/#36 — this module only detects.
"""
import json
from pathlib import Path

from structlog import get_logger

log = get_logger(__name__)

_SCORER_SHELL_KEYS = {"current_scorer_agent", "scoring_history"}


def check_product_contracts(project_dir: Path) -> list[str]:
    violations: list[str] = []
    progress = project_dir / "progress.json"
    if progress.exists():
        try:
            data = json.loads(progress.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"progress.json: invalid JSON"]
        if isinstance(data, dict) and set(data.keys()) <= _SCORER_SHELL_KEYS:
            violations.append(
                "progress.json: scorer-only shell, no progress fields (F1309)"
            )
    ledger = project_dir / "cost" / "token-ledger.jsonl"
    if progress.exists() and (not ledger.exists() or not ledger.read_text(encoding="utf-8").strip()):
        violations.append("cost/token-ledger.jsonl missing or empty (F1313)")
    if violations:
        log.warning("product_contract_violations", project_dir=str(project_dir), violations=violations)
    return violations
```

`chapter_loop._complete_chapter` 开头（在既有收尾逻辑前）：

```python
    from shenbi.exceptions import ProductContractError
    from shenbi.pipeline.product_contracts import check_product_contracts

    violations = check_product_contracts(Path(state.project_dir))
    if violations:
        raise ProductContractError("; ".join(violations))
```

- [ ] **Step 5: 跑本 task 测试 + 回归**：`uv run pytest tests/unit/pipeline/test_product_contracts.py tests/unit/pipeline/test_chapter_loop.py -q`。**已知风险**：既有测试若构造走到 `_complete_chapter` 的 tmp 项目（无 ledger/空 progress）会被新 FAIL 打红——属「契约前旧形态测试」，逐个核对：真实走 `_complete_chapter` 的用例在其 tmp 项目补最小合规产物（progress 含进度键 + cost/token-ledger.jsonl 一行），不是绕过检查（monkeypatch 跳过=违规，禁止）
- [ ] **Step 6: Commit** `git add src/shenbi/pipeline/product_contracts.py src/shenbi/exceptions.py src/shenbi/pipeline/chapter_loop.py tests/fixtures/z11/progress-*.json tests/unit/pipeline/test_product_contracts.py tests/unit/pipeline/test_chapter_loop.py && git commit -m "feat: product-contract checks wired into chapter completion, fail-closed (z11 R3, F1309/F1313)"` → `audit-T4.md`

---

### Task 5: 全量验收 + 阶段 7 门禁

- [ ] `just check` 全绿（含契约 lints、ruff、mypy、basedpyright、两段 pytest）
- [ ] 验收覆盖核对（贴 progress.md `## 验收证据`）：
  - R1「56/56 头 + META/豁免」= Task 3 Step 2 两条命令输出
  - R3「known-bad FAIL / known-good PASS / ledger 检查」= Task 4 Step 5 pytest 输出
- [ ] `ls .superpowers/sdd/audit-T*.md | wc -l` == 4

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 56/56 契约头 + META/豁免 | T1+T2+T3 | grep 计数 56 / 豁免 6；pytest test_g2_chapter_contract |
| R3 known-bad FAIL / good PASS / ledger | T4 | pytest test_product_contracts |
| R2 | — | 已移交 C22（spec #60），本 plan 不含 |
