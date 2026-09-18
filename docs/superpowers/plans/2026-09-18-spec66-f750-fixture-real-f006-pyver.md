# SDD #66 F750 真实 fixture 化 + F0-06 python 三元统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `tests/integration/test_gate_cli.py` 的手捏 worldbuilding 项目替换为 git 历史真实产物的 upstream-copy fixtures（三类载体形态），并把 pyproject 的 mypy python_version 从 3.12 统一到 3.11。

**Architecture:** 素材从 `git show d120a444^:novel-output/xinghuo-ranqiong/<path>` 取回（生产树已出库 PR #217，内容自 2026-07-20 未变）；fixture 载体按 spec 三形态处方（truth+protagonist 单块合并、story_bible/rules 前置单块、novel.json sidecar）；测试 helper 退化为目录组装（拷贝）；G4 worldbuilding 在真实 fixture 下仍 PASS（边界压线：story_bible 恰 4 节、rules 恰 10 条、locations 恰 5 个——**payload 零扰动**）。F0-06 为 pyproject 单行改值。

**Tech Stack:** Python 3.11+ / pytest / unittest / shutil / pyYAML frontmatter / uv + just。

## Global Constraints（spec 边界，逐 task 隐含）

- **不动 `src/` 生产代码**（spec 边界节）
- **不改 ledger 状态**（F750/F0-06 两行由 SDD 份在归档时回写 closed）
- payload 与 `git show d120a444^:...` 逐字节一致（唯一 frontmatter 级新造 = chapter_summaries 重建块）；`source:` 值整体加引号（防 YAML `: ` 事故）
- 空行约定：前置块/重建块与 payload 间空一行
- `.provenance.json` sidecar 只留 fixtures 侧，不拷入 tmp project
- G3.4 评分：**N/A**——本 spec 无 LLM 评分场景（全部离线验收，核心原则 8 合规）
- F947 规则：验收已全部离线化（fixtures 驱动 + 静态断言），无需改写

## 实际签名（从源码复制）

```python
# tests/integration/test_gate_cli.py:27（现状，Task 2 改写其体）
def _make_worldbuilding_project(self, base_dir):
    """... Returns the path to a file that can be passed as the G4 file argument."""

# src/shenbi/gates/g0_purity.py:65
def load_provenance(fixture_path: Path) -> str | None

# 标准库
shutil.copy2(src: Path | str, dst: Path | str) -> Path
```

**复杂度**：Task 1/2/3 全部 **leaf**（测试文件 + fixtures + 配置；零 src/ 改动、零契约/并发/infra 模块）——但按 SDD 单模型现实由协调者亲自实现（上下文已长）。

**test_kind**：Task 1 = `tdd_red_green`（守卫测试先红后绿）；Task 2 = `regression_guard`（行为保持：G4 PASS + marker 写盘不变，输入换真品）；Task 3 = `regression_guard`（配置统一，mypy/basedpyright 无新报错）。

**测试层级与 fixture**：Task 1 守卫测试 = **T1 unit**（`tests/unit/gates/test_xinghuo_fixture_tree.py`，引用 `tests/fixtures/xinghuo-ranqiong/*`）；Task 2 = **T1 integration**（`tests/integration/test_gate_cli.py`，引用 xinghuo-ranqiong 树 + 既有 `tests/fixtures/genre-config-example.json` + `tests/fixtures/world/locations/locations.md`——均为真实产物/upstream 副本，G0.9 合规）。

**CI 浅克隆约束**：ci.yml 的 quality job 用 actions/checkout 默认 fetch-depth=1——**永久测试禁止依赖 `git show`**（守卫测试只查载体在场）；字节保真验证（AC#4）是一次性验收命令，在全克隆上跑（本地/实施者）。

---

### Task 1: xinghuo-ranqiong fixture 树（8 文件 + sidecar + 守卫测试）

**Files:**
- Create: `tests/fixtures/xinghuo-ranqiong/novel.json`（830B verbatim）
- Create: `tests/fixtures/xinghuo-ranqiong/novel.json.provenance.json`
- Create: `tests/fixtures/xinghuo-ranqiong/world/story_bible.md`（10,045B payload + 前置块）
- Create: `tests/fixtures/xinghuo-ranqiong/world/rules.md`（4,289B payload + 前置块）
- Create: `tests/fixtures/xinghuo-ranqiong/truth/current_state.md`（10,292B payload + 合并块）
- Create: `tests/fixtures/xinghuo-ranqiong/truth/character_matrix.md`（3,711B payload + 合并块）
- Create: `tests/fixtures/xinghuo-ranqiong/truth/emotional_arcs.md`（4,566B payload + 合并块）
- Create: `tests/fixtures/xinghuo-ranqiong/truth/chapter_summaries.md`（5,955B body + 重建块）
- Create: `tests/fixtures/xinghuo-ranqiong/characters/protagonist.md`（7,977B payload + 合并块）
- Test: `tests/unit/gates/test_xinghuo_fixture_tree.py`

**Interfaces:**
- Consumes: `shenbi.gates.g0_purity.load_provenance`（既有）
- Produces: fixture 树路径约定 `tests/fixtures/xinghuo-ranqiong/<原项目相对路径>`（Task 2 的组装循环依赖此布局）；守卫测试 `test_xinghuo_fixture_tree_complete_with_carriers`

- [x] **Step 1: 写守卫测试（先红）**

创建 `tests/unit/gates/test_xinghuo_fixture_tree.py`（对齐 test_g0_purity.py 风格：future annotations、`@pytest.mark.unit`、line-length ≤100）：

```python
"""Carrier guard for the xinghuo-ranqiong upstream-copy fixture tree (spec #66 F750).

Byte-fidelity vs git history (d120a444^) is a one-off acceptance command run
on a full clone (spec AC#4) — CI quality workflows use shallow clones
(fetch-depth=1), so this permanent guard checks tree completeness and
provenance carriers only, with no git dependency.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g0_purity import load_provenance

# tests/unit/gates/<file>.py → parents[3] = repo root（对齐 test_g0.py:317 先例）
FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "xinghuo-ranqiong"
EXPECTED_FILES = frozenset(
    {
        "novel.json",
        "world/story_bible.md",
        "world/rules.md",
        "truth/current_state.md",
        "truth/character_matrix.md",
        "truth/emotional_arcs.md",
        "truth/chapter_summaries.md",
        "characters/protagonist.md",
    }
)


@pytest.mark.unit
def test_xinghuo_fixture_tree_complete_with_carriers() -> None:
    files = {
        p.relative_to(FIXTURE_ROOT).as_posix()
        for p in FIXTURE_ROOT.rglob("*")
        if p.is_file() and p.suffix in (".md", ".json") and not p.name.endswith(".provenance.json")
    }
    assert files == EXPECTED_FILES
    for rel in sorted(EXPECTED_FILES):
        assert load_provenance(FIXTURE_ROOT / rel) == "upstream-copy", rel
```

- [x] **Step 2: 跑测试确认红**

Run: `uv run pytest tests/unit/gates/test_xinghuo_fixture_tree.py -v`
Expected: FAIL（`files == EXPECTED_FILES` 断言失败——树不存在，files 为空集）

- [x] **Step 3: 生成 fixture 树**

以下命令逐条在 repo 根跑（前置单块/合并块用 python 注入；`<CARRIER>` 行见下）：

```bash
mkdir -p tests/fixtures/xinghuo-ranqiong/world tests/fixtures/xinghuo-ranqiong/truth tests/fixtures/xinghuo-ranqiong/characters

# (a) novel.json —— verbatim + sidecar
git show 'd120a444^:novel-output/xinghuo-ranqiong/novel.json' > tests/fixtures/xinghuo-ranqiong/novel.json
printf '%s\n' '{"provenance": "upstream-copy", "source": "git history d120a444^:novel-output/xinghuo-ranqiong/novel.json (verbatim; production tree removed in PR #217)"}' > tests/fixtures/xinghuo-ranqiong/novel.json.provenance.json

# (b) 前置单块 × 2（story_bible / rules——源无 frontmatter）
for rel in world/story_bible.md world/rules.md; do
  git show "d120a444^:novel-output/xinghuo-ranqiong/$rel" | python3 -c "
import sys
src = sys.stdin.read()
rel = '$rel'
carrier = (
    'provenance: upstream-copy\n'
    'source: \"git history d120a444^:novel-output/xinghuo-ranqiong/' + rel
    + ' (payload verbatim; production tree removed in PR #217)\"\n'
)
sys.stdout.write('---\n' + carrier + '---\n\n' + src)
" > "tests/fixtures/xinghuo-ranqiong/$rel"
done

# (c) 单块合并 × 4（truth 三件 + protagonist——源自带 frontmatter，provenance/source 插为前两键）
for rel in truth/current_state.md truth/character_matrix.md truth/emotional_arcs.md characters/protagonist.md; do
  git show "d120a444^:novel-output/xinghuo-ranqiong/$rel" | python3 -c "
import re, sys
src = sys.stdin.read()
rel = '$rel'
carrier = (
    'provenance: upstream-copy\n'
    'source: \"git history d120a444^:novel-output/xinghuo-ranqiong/' + rel
    + ' (frontmatter keys merged with provenance carrier; body verbatim; production tree removed in PR #217)\"\n'
)
m = re.match(r'^---\n(.*?)\n---\n', src, re.DOTALL)
assert m, rel + ': expected frontmatter'
sys.stdout.write('---\n' + carrier + m.group(1) + '\n---\n' + src[m.end():])
" > "tests/fixtures/xinghuo-ranqiong/$rel"
done

# (d) chapter_summaries 重建块（源无 frontmatter，块内容全指定）
git show 'd120a444^:novel-output/xinghuo-ranqiong/truth/chapter_summaries.md' | python3 -c "
import sys
src = sys.stdin.read()
block = '''---
provenance: upstream-copy
source: \"git history d120a444^:novel-output/xinghuo-ranqiong/truth/chapter_summaries.md (frontmatter reconstructed per template contract; body verbatim; production tree removed in PR #217)\"
title: 章节摘要
project: 星火燃穹
type: chapter_summaries
category: truth
status: active
---

'''
sys.stdout.write(block + src)
" > tests/fixtures/xinghuo-ranqiong/truth/chapter_summaries.md
```

- [x] **Step 4: 跑守卫测试确认绿**

Run: `uv run pytest tests/unit/gates/test_xinghuo_fixture_tree.py -v`
Expected: PASS（1 passed）

- [x] **Step 5: 跑 spec AC#3（载体真树断言）**

Run（repo 根）:
```bash
uv run python -c "from pathlib import Path; from shenbi.gates.g0_purity import load_provenance; ps=[p for p in Path('tests/fixtures/xinghuo-ranqiong').rglob('*') if p.is_file() and p.suffix in ('.md','.json') and not p.name.endswith('.provenance.json')]; assert ps and all(load_provenance(p) for p in ps), ps"
```
Expected: 无输出、exit 0

- [x] **Step 6: 跑 spec AC#4（字节保真一次性验证，全克隆）**

Run（repo 根；spec 验收节命令的功能等价形式——注释省略）:
```bash
uv run python -c "
import re, subprocess, sys
from pathlib import Path
def body(t):
    m = re.match(r'^---\r?\n.*?\r?\n---\r?\n', t, re.DOTALL)
    return t[m.end():].lstrip('\r\n') if m else t
ok = True
for rel in ['world/story_bible.md','world/rules.md','truth/current_state.md','truth/character_matrix.md','truth/emotional_arcs.md','truth/chapter_summaries.md','characters/protagonist.md','novel.json']:
    fx = Path('tests/fixtures/xinghuo-ranqiong', rel).read_text(encoding='utf-8')
    src = subprocess.run(['git','show',f'd120a444^:novel-output/xinghuo-ranqiong/{rel}'],capture_output=True,text=True,encoding='utf-8').stdout
    if rel.endswith('.json'):
        ok &= fx == src; continue
    same = body(fx) == body(src)
    print(rel, 'body-bytes:', same)
    ok &= same
fx = Path('tests/fixtures/world/locations/locations.md').read_text(encoding='utf-8')
src = subprocess.run(['git','show','d120a444^:novel-output/xinghuo-ranqiong/world/locations.md'],capture_output=True,text=True,encoding='utf-8').stdout
print('world/locations.md (existing fixture) body-bytes:', body(fx) == body(src))
ok &= body(fx) == body(src)
sys.exit(0 if ok else 1)"
```
Expected: 8 行 `body-bytes: True`（7 个循环 .md + 1 行 locations 既有件；novel.json 走 json 分支静默比较无输出行）、exit 0

- [x] **Step 7: 体积抽查（防意外截断）**

Run: `find tests/fixtures/xinghuo-ranqiong -type f -name '*.md' -o -type f -name '*.json' | xargs wc -c | sort -k2`
Expected（payload + 实测载体增量，审查者 verbatim 复算）：story_bible = 10,218、rules = 4,456、current_state = 10,504、character_matrix = 3,926、emotional_arcs = 4,779、chapter_summaries = 6,277、protagonist = 8,192、novel.json = 830（sidecar 另计）

- [x] **Step 8: Commit**

```bash
git add tests/fixtures/xinghuo-ranqiong tests/unit/gates/test_xinghuo_fixture_tree.py
git commit -m "feat(spec66): xinghuo-ranqiong upstream-copy fixture tree + carrier guard (F750 T1)"
```

### Task 2: test_gate_cli.py helper 改目录组装

**Files:**
- Modify: `tests/integration/test_gate_cli.py:27-97`（`_make_worldbuilding_project` 函数体整体替换；模块头加 FIXTURES 常量）

**Interfaces:**
- Consumes: Task 1 的 `tests/fixtures/xinghuo-ranqiong/` 树 + 既有 `tests/fixtures/genre-config-example.json`、`tests/fixtures/world/locations/locations.md`
- Produces: 不变——`_make_worldbuilding_project(self, base_dir) -> str`（返回 `base/world/story_bible.md` 路径供 G4 file 参数）；仅内部实现换

- [x] **Step 1: 改写 helper（characterization——现有测试就是规格，先跑基线）**

Run: `uv run pytest tests/integration/test_gate_cli.py -v`
Expected: **19 passed**（基线绿——改动是输入替换不是行为变更）

- [x] **Step 2: 替换 :27-97 函数体**

在模块头 `TESTS = Path(__file__).resolve().parent.parent`（:12）之后加：

```python
FIXTURES = TESTS / "fixtures"
XINGHUO = FIXTURES / "xinghuo-ranqiong"
```

`_make_worldbuilding_project` 整体替换为（docstring 注记 F750 出处与 G0.9 合规性）：

```python
    def _make_worldbuilding_project(self, base_dir):
        """Assemble a worldbuilding project from real-product fixtures.

        Content comes from tests/fixtures/ (xinghuo-ranqiong upstream
        copies of the real novel-output products, F750 / spec #66);
        only directory assembly lives here. G4 worldbuilding PASS on
        this assembly is boundary-tight (story_bible exactly 4 sections,
        rules exactly 10, locations exactly 5) — do not edit fixture
        payloads.

        Returns the path to a file that can be passed as the G4 file argument.
        """
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)
        shutil.copy2(XINGHUO / "novel.json", base / "novel.json")
        shutil.copy2(FIXTURES / "genre-config-example.json", base / "genre-config.json")
        world = base / "world"
        world.mkdir(parents=True, exist_ok=True)
        shutil.copy2(XINGHUO / "world" / "story_bible.md", world / "story_bible.md")
        shutil.copy2(XINGHUO / "world" / "rules.md", world / "rules.md")
        shutil.copy2(FIXTURES / "world" / "locations" / "locations.md", world / "locations.md")
        truth = base / "truth"
        truth.mkdir(parents=True, exist_ok=True)
        for name in (
            "current_state.md",
            "character_matrix.md",
            "emotional_arcs.md",
            "chapter_summaries.md",
        ):
            shutil.copy2(XINGHUO / "truth" / name, truth / name)
        characters = base / "characters"
        characters.mkdir(parents=True, exist_ok=True)
        shutil.copy2(XINGHUO / "characters" / "protagonist.md", characters / "protagonist.md")
        # G4 worldbuilding derives project_dir from the file path
        return str(world / "story_bible.md")
```

注意：`json` import 仍被文件其余测试使用（基线 :108 起的 marker/scoring/phase 类）——保留；`shutil` 已在 :6 import。

- [x] **Step 3: 跑集成测试确认仍绿（spec AC#2）**

Run: `uv run pytest tests/integration/test_gate_cli.py -v`
Expected: **19 passed**（关键：`test_g4_pass_writes_marker` PASS——真品过 G4）

- [x] **Step 4: 跑 spec AC#1（捏造文本清除）**

Run: `grep -n "Content here\|这是一个宏大而复杂的世界\|name: Test\|天机城" tests/integration/test_gate_cli.py`
Expected: 零命中、exit 1

- [x] **Step 5: Commit**

```bash
git add tests/integration/test_gate_cli.py
git commit -m "fix(spec66): gate CLI integration test uses real-product fixtures (F750 T2)"
```

### Task 3: F0-06 pyproject python_version 统一 3.11

**Files:**
- Modify: `pyproject.toml:379`（`python_version = "3.12"` → `"3.11"`；:8 与 :398 不动）

**Interfaces:**
- Consumes: 无
- Produces: 无（配置值）

- [x] **Step 1: 改值**

`pyproject.toml` `[tool.mypy]` 段 `python_version = "3.12"` → `python_version = "3.11"`（仅此一处）。

- [x] **Step 2: 跑 spec 验收 grep**

Run: `grep -n "python_version\|pythonVersion\|requires-python" pyproject.toml`
Expected: 三行——`:8:requires-python = ">=3.11"`、`:379:python_version = "3.11"`、`:398:pythonVersion = "3.11"`（3.11 基准一致）

- [x] **Step 3: uv lock 校验（pyproject 已改，按 SDD 阶段 7 规则必跑）**

Run: `uv lock --check`
Expected: exit 0（非依赖区改动，锁无漂移）

- [x] **Step 4: 快速门禁（mypy/basedpyright 面 + 新守卫测试 + 全量 just check——覆盖 F0-06 AC#2）**

Run: `uv run mypy src/shenbi/ && uv run basedpyright && uv run pytest tests/unit/gates/test_xinghuo_fixture_tree.py tests/integration/test_gate_cli.py -v`
Expected: mypy `Success: no issues found in 193 source files`；basedpyright `0 errors`；**20 passed**（1 守卫 + 19 集成）

Run: `just check`
Expected: **EXIT=0**（全 lint 面 + ruff format + mypy 3.11 + basedpyright + 两段 pytest——F0-06 AC#2 在 plan 内闭环，不待阶段 7）

- [x] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "chore(spec66): unify mypy python_version to 3.11 floor (F0-06 T3)"
```

---

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 命令（本 plan 步骤） |
|---|---|---|
| F750 AC#1 捏造文本零命中 | T2 Step 4 | `grep -n "Content here\|这是一个宏大而复杂的世界\|name: Test\|天机城" tests/integration/test_gate_cli.py` → exit 1 |
| F750 AC#2 集成全绿 | T2 Step 3 | `uv run pytest tests/integration/test_gate_cli.py -v` → 19 passed |
| F750 AC#3 载体合规真树断言 | T1 Step 5 | AC#3 python -c → exit 0（守卫测试 T1 Step 4 为永久化） |
| F750 AC#4 字节保真 | T1 Step 6 | AC#4 python -c（功能等价）→ 8 行 body-bytes True + novel.json 静默字节一致 + exit 0 |
| F0-06 AC#1 三处一致 | T3 Step 2 | grep 三行 3.11 基准 |
| F0-06 AC#2 just check 全绿 | T3 Step 4（阶段 7 复跑） | `just check` → EXIT=0（含 mypy 3.11/basedpyright/两段 pytest/全 lint 面） |

## Self-Review 记录

- **Spec 覆盖**：spec §1 修复（映射表 10 行 → T1 生成命令 a-d + T2 组装）、§2 修复（T3）、边界（零 src/ 改动 ✓、ledger 不动 ✓）、全部 6 条验收 → 上表 ✓
- **占位符扫描**：无 TBD/「适当处理」；所有代码步骤给全文；生成命令逐文件可执行 ✓
- **类型/名字一致性**：`FIXTURES`/`XINGHUO` 常量 T2 定义即 T2 使用；守卫测试 `EXPECTED_FILES` 与 T1 生成文件集一一对应；`load_provenance` 签名自源码复制 ✓
- **CI 浅克隆**：永久测试零 git 依赖（AC#4 一次性）✓
