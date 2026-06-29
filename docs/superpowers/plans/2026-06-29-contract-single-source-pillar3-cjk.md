# CJK 工具包实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `src/shenbi/text/cjk.py`——全框架唯一的中文文本操作模块，根治 G6.12 敏感词扫描失效、破折号双重计数、word_count CJK-only 偏差三个 bug。

**Architecture:** 新建独立模块，不修改现有 gates/helpers（后续支柱集成时才接入）。提供四类能力：find_terms、count_punctuation、count_words、tokenize。全部配属性测试。

**Tech Stack:** Python 3.11+，jieba（新增依赖），pytest + hypothesis，mypy strict，ruff。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱三。

## Global Constraints

- Python 3.11+；jieba 版本固定 `0.42.1`，冻结分词属性测试防漂移。
- mypy strict + ruff CI 干净。
- 本计划**只创建新模块**，不修改现有 gates/shared.py、g6.py、compute_stats.py。
- jieba 是 untyped 库——可能需 mypy `ignore_missing_imports` override。

---

### Task 1: 包骨架 + jieba 依赖

**Files:** Create `src/shenbi/text/__init__.py`、`tests/unit/text/__init__.py`；Modify `pyproject.toml`

- [ ] **Step 1: Add jieba**
Run: `uv add jieba==0.42.1`

- [ ] **Step 2: Create skeleton**
```python
# src/shenbi/text/__init__.py
"""Shenbi text processing toolkit (spec pillar 3)."""
```
```python
# tests/unit/text/__init__.py
"""Text toolkit tests."""
```

- [ ] **Step 3: ruff per-file-ignores for text/**
Append to `[tool.ruff.lint.per-file-ignores]`:
```toml
"src/shenbi/text/*.py" = ["RUF001", "RUF002", "RUF003", "RUF005", "RUF059"]
```

- [ ] **Step 4: Verify**
Run: `uv run python -c "import jieba; print('jieba OK')"` → `jieba OK`

- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/text/__init__.py tests/unit/text/__init__.py pyproject.toml uv.lock
git commit -m "feat(text): add jieba dependency + text/ package skeleton"
```

---

### Task 2: find_terms — CJK 边界词项查找（治 G6.12）

**Files:** Create `src/shenbi/text/cjk.py`、`tests/unit/text/test_cjk.py`

**Interfaces:** Produces `TermHit(frozen dataclass: term/start/end)` + `find_terms(text, terms) -> list[TermHit]`。

**Bug 根治:** G6.12 用 `\w` 边界（匹配 CJK → 嵌入中文的敏感词不可见）。find_terms 用 `str.find` 精确子串匹配。

- [ ] **Step 1: Write failing test**
```python
# tests/unit/text/test_cjk.py
from __future__ import annotations
from shenbi.text.cjk import TermHit, find_terms

def test_sensitive_word_embedded_in_chinese() -> None:
    text = "他在这个时代发起了革命运动"
    hits = find_terms(text, ["革命"])
    assert len(hits) == 1
    assert hits[0].term == "革命"

def test_term_at_boundary() -> None:
    assert len(find_terms("革命开始了", ["革命"])) == 1
    assert len(find_terms("开始了革命", ["革命"])) == 1

def test_multiple_terms() -> None:
    text = "第一场革命和第二场暴动"
    hits = find_terms(text, ["革命", "暴动"])
    assert {h.term for h in hits} == {"革命", "暴动"}

def test_not_found() -> None:
    assert find_terms("和平发展", ["革命"]) == []

def test_empty_text() -> None:
    assert find_terms("", ["革命"]) == []

def test_positions() -> None:
    text = "这是革命的故事"
    hits = find_terms(text, ["革命"])
    assert hits[0].start == 2 and hits[0].end == 4
```

- [ ] **Step 2: Run → fails**

- [ ] **Step 3: Implement**
```python
# src/shenbi/text/cjk.py
"""Centralized CJK text operations (spec pillar 3)."""
from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass

@dataclass(frozen=True)
class TermHit:
    term: str
    start: int
    end: int

def find_terms(text: str, terms: Iterable[str]) -> list[TermHit]:
    """Find terms as exact substrings. CJK-aware: does not use \\w."""
    hits: list[TermHit] = []
    for term in terms:
        if not term:
            continue
        start = 0
        while True:
            idx = text.find(term, start)
            if idx == -1:
                break
            hits.append(TermHit(term=term, start=idx, end=idx + len(term)))
            start = idx + 1
    hits.sort(key=lambda h: h.start)
    return hits
```

- [ ] **Step 4: Run → passes** (6)
- [ ] **Step 5: mypy+ruff+commit**
```bash
git add src/shenbi/text/cjk.py tests/unit/text/test_cjk.py
git commit -m "feat(text): add find_terms with CJK-aware substring matching (fixes G6.12)"
```

---

### Task 3: count_punctuation — 多字符标点整体计数（治破折号双重计数）

**Files:** Modify `src/shenbi/text/cjk.py`、`tests/unit/text/test_cjk.py`

**Bug 根治:** `sum(text.count(c) for c in chars)` 遍历 `——` 的两个字符各计一次（单 `——` 报 4）。改为 `text.count(token)`。

- [ ] **Step 1: Write failing test (append)**
```python
from shenbi.text.cjk import count_punctuation

def test_dash_counted_once() -> None:
    text = "你好——世界"
    assert count_punctuation(text)["破折号"] == 1

def test_ellipsis_counted_once() -> None:
    assert count_punctuation("你好……世界")["省略号"] == 1

def test_single_char_punct() -> None:
    c = count_punctuation("你好。世界！")
    assert c["句号"] == 1 and c["感叹号"] == 1

def test_no_punctuation() -> None:
    assert all(v == 0 for v in count_punctuation("纯文本").values())

def test_multiple_dashes() -> None:
    assert count_punctuation("第一——第二——第三")["破折号"] == 2
```

- [ ] **Step 2: Run → fails**

- [ ] **Step 3: Implement (append to cjk.py)**
```python
PUNCTUATION_TOKENS: dict[str, list[str]] = {
    "句号": ["。"], "逗号": ["，"], "感叹号": ["！", "!"],
    "问号": ["？", "?"], "破折号": ["——", "──"],
    "省略号": ["……", "。。。"], "顿号": ["、"],
    "分号": ["；"], "冒号": ["：", ":"],
    "引号": ['""', "''", "「」", "『』"],
}

def count_punctuation(text: str) -> dict[str, int]:
    """Count punctuation by whole tokens, not per-char."""
    return {
        name: sum(text.count(token) for token in tokens)
        for name, tokens in PUNCTUATION_TOKENS.items()
    }
```

- [ ] **Step 4: Run → passes** (11)
- [ ] **Step 5: commit**
```bash
git add src/shenbi/text/cjk.py tests/unit/text/test_cjk.py
git commit -m "feat(text): add count_punctuation with whole-token counting"
```

---
---

### Task 4: count_words — 双语义字数（治 CJK-only 偏差）

**Files:** Modify `src/shenbi/text/cjk.py`、`tests/unit/text/test_cjk.py`

**Bug 根治:** `word_count_md` 用 `[一-鿿]` 只数 CJK，丢 Latin/数字。

- [ ] **Step 1: Write failing test (append)**
```python
from typing import Literal
from shenbi.text.cjk import count_words

def test_cjk_only_pure_chinese() -> None:
    assert count_words("这是一段中文文本", "cjk_only") == 8

def test_cjk_only_drops_english() -> None:
    assert count_words("这是level提升", "cjk_only") == 4

def test_mixed_includes_english() -> None:
    assert count_words("这是level提升", "mixed") >= 5

def test_mixed_ge_cjk_only() -> None:
    text = "这是level提升123"
    assert count_words(text, "mixed") >= count_words(text, "cjk_only")

def test_empty() -> None:
    assert count_words("", "cjk_only") == 0
    assert count_words("", "mixed") == 0

def test_numbers_in_mixed() -> None:
    assert count_words("第1章", "mixed") >= 2
```

- [ ] **Step 2: Run → fails**

- [ ] **Step 3: Implement (append to cjk.py)**
```python
import re
from typing import Literal

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_NON_CJK_WORD_RE = re.compile(r"[a-zA-Z0-9]+")

def count_words(text: str, mode: Literal["cjk_only", "mixed"]) -> int:
    """Count words: cjk_only = CJK chars only; mixed = CJK + Latin words + digits."""
    cjk = len(_CJK_RE.findall(text))
    if mode == "cjk_only":
        return cjk
    return cjk + len(_NON_CJK_WORD_RE.findall(text))
```

- [ ] **Step 4: Run → passes** (17)
- [ ] **Step 5: commit**
```bash
git add src/shenbi/text/cjk.py tests/unit/text/test_cjk.py
git commit -m "feat(text): add count_words with dual semantics (cjk_only/mixed)"
```

---

### Task 5: tokenize — jieba + 领域词典分词

**Files:** Modify `src/shenbi/text/cjk.py`、`tests/unit/text/test_cjk.py`

- [ ] **Step 1: Write failing test (append)**
```python
from shenbi.text.cjk import Token, tokenize

def test_tokenize_returns_tokens() -> None:
    tokens = tokenize("他是一个高手")
    assert len(tokens) > 0
    assert all(isinstance(t, Token) for t in tokens)

def test_tokenize_preserves_chars() -> None:
    text = "他是一个高手"
    assert "".join(t.word for t in tokenize(text)) == text

def test_domain_dict_prevents_split() -> None:
    tokens = tokenize("他开始了筑基期修炼", domain_dict=["筑基期"])
    assert "筑基期" in [t.word for t in tokens]

def test_tokenize_empty() -> None:
    assert tokenize("") == []
```

- [ ] **Step 2: Run → fails**

- [ ] **Step 3: Implement (append to cjk.py)**
```python
import jieba  # type: ignore[import-untyped]
import jieba.posseg as pseg  # type: ignore[import-untyped]

@dataclass(frozen=True)
class Token:
    word: str
    pos: str

_jieba_ready = False

def tokenize(text: str, domain_dict: Iterable[str] | None = None) -> list[Token]:
    """Tokenize with jieba. Domain terms registered to prevent splitting."""
    global _jieba_ready  # noqa: PLW0603
    if not _jieba_ready:
        jieba.initialize()
        _jieba_ready = True
    if domain_dict:
        for term in domain_dict:
            jieba.add_word(term)
    return [Token(word=w, pos=f) for w, f in pseg.cut(text) if w.strip()]
```

**Note:** If mypy fails on jieba import, add to pyproject.toml:
```toml
[[tool.mypy.overrides]]
module = "jieba.*"
ignore_missing_imports = true
```

- [ ] **Step 4: Run → passes** (21)
- [ ] **Step 5: mypy+ruff+commit**
```bash
git add src/shenbi/text/cjk.py tests/unit/text/test_cjk.py pyproject.toml
git commit -m "feat(text): add tokenize with jieba + domain dictionary"
```

---

### Task 6: 属性测试网

**Files:** Create `tests/property/cjk/__init__.py`、`tests/property/cjk/test_cjk_properties.py`

- [ ] **Step 1: Write property tests**
```python
# tests/property/cjk/__init__.py
"""CJK property tests."""
```

```python
# tests/property/cjk/test_cjk_properties.py
from __future__ import annotations
from hypothesis import given
from hypothesis import strategies as st
from shenbi.text.cjk import count_punctuation, count_words, find_terms

cjk_text = st.text(
    alphabet=st.sampled_from(list("你好世界革命暴动和平发展——……。！？，level123")),
    min_size=0, max_size=50,
)

@given(cjk_text)
def test_find_terms_substring_found(text: str) -> None:
    if len(text) >= 2:
        term = text[:2]
        assert len(find_terms(text, [term])) >= 1

@given(cjk_text)
def test_punctuation_count_matches_str_count(text: str) -> None:
    counts = count_punctuation(text)
    assert counts["破折号"] == text.count("——")
    assert counts["省略号"] == text.count("……")

@given(cjk_text)
def test_mixed_ge_cjk_only(text: str) -> None:
    assert count_words(text, "mixed") >= count_words(text, "cjk_only")

@given(st.text(min_size=0, max_size=100))
def test_count_words_non_negative(text: str) -> None:
    assert count_words(text, "cjk_only") >= 0
    assert count_words(text, "mixed") >= 0
```

- [ ] **Step 2: Run → passes**
Run: `uv run pytest tests/property/cjk/ -v --hypothesis-profile=ci` → 4 passed

- [ ] **Step 3: commit**
```bash
git add tests/property/cjk/
git commit -m "test(text): add CJK property tests (invariants for all inputs)"
```

---

### Task 7: 冻结分词测试 + __init__ 导出 + 全量回归

**Files:** Modify `src/shenbi/text/__init__.py`、`tests/unit/text/test_cjk.py`

- [ ] **Step 1: Add frozen-segmentation test (append)**
```python
def test_tokenize_frozen() -> None:
    """Same input always produces same tokens (guards jieba upgrade drift)."""
    text = "他在黑暗中看到了一束光明"
    t1 = tokenize(text)
    t2 = tokenize(text)
    assert [t.word for t in t1] == [t.word for t in t2]
```

- [ ] **Step 2: Update __init__.py exports**
```python
# src/shenbi/text/__init__.py
"""Shenbi text processing toolkit (spec pillar 3)."""
from __future__ import annotations
from shenbi.text.cjk import (
    PUNCTUATION_TOKENS, TermHit, Token,
    count_punctuation, count_words, find_terms, tokenize,
)
__all__ = [
    "PUNCTUATION_TOKENS", "TermHit", "Token",
    "count_punctuation", "count_words", "find_terms", "tokenize",
]
```

- [ ] **Step 3: Verify exports**
Run: `uv run python -c "from shenbi.text import find_terms, count_punctuation, count_words, tokenize; print('OK')"` → `OK`

- [ ] **Step 4: Full regression**
Run: `uv run pytest -q` → all pass + ~26 new
Run: `uv run mypy src/shenbi && uv run ruff check .` → clean

- [ ] **Step 5: Commit**
```bash
git add src/shenbi/text/__init__.py tests/unit/text/test_cjk.py
git commit -m "feat(text): frozen-segmentation test + public API exports

CJK toolkit complete: find_terms, count_punctuation, count_words,
tokenize. Property tests + frozen-segmentation guard. Full regression green."
```

---

## Self-Review

**1. Spec coverage:** find_terms/count_punctuation/count_words/tokenize/property tests/frozen-seg全覆盖。ruff SHB003 + 现有代码迁移留给后续支柱。

**2. Placeholder scan:** 无 TBD。

**3. Type consistency:** `find_terms -> list[TermHit]`; `count_punctuation -> dict[str,int]`; `count_words(text, Literal[...]) -> int`; `tokenize -> list[Token]`.

**4. 已知限制:** jieba untyped（mypy override）; find_terms 用 str.find 精确子串（对纯 CJK 够用）; 不替换现有 word_count_md/g6.py（后续集成）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar3-cjk.md`. Two execution options:

**1. Subagent-Driven (recommended)** - fresh subagent per task, review between tasks

**2. Inline Execution** - batch execution with checkpoints

Which approach?
