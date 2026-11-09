# spec #84 T0-14 章头归一接线与在盘修复 · Addendum Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `ensure_chapter_header` 归一能力接进全部章正文写路径（晋升+修订），归一中文数字形，修复在盘 ch39-50 章头，落地 `just chapter-headers` 断言，并完成 spec #84 Task 10 收口验收与归档。

**Architecture:** 归一规则内嵌 `_insert_zh_header`（区域判据单源，r7 禁配对式 META 定位）；公有包装 `normalize_chapter_header(content, chapter_num, project_root)` 统一 style 解析，三调用点（dispatch 直写 :3126 / 晋升 chapter_loop:1568 / merge_prose :3106）共用；断言工具 `tools/lint_chapter_headers.py` 从 src 导入共享正则（零复制）；在盘修复 dogfood 归一器本体。

**Tech Stack:** Python 3.11+ / pytest（unit+integration 标记）/ just / structlog（src 内禁 print，ruff T20 零豁免）。

## Global Constraints

- `src/shenbi/` 内禁 `print()`（ruff T20 零豁免）——用户可见文本走 `shenbi.cli_utils.echo`，日志走 structlog；`tools/` 输出风格镜像 `tools/lint_truth_pool.py` 现行惯例（`sys.stdout.write` + exit 1）
- 文件 I/O 用 `pathlib.Path`；章正文写盘一律走 `shenbi.safe_write.safe_write`
- 测试 docstring 用英文；测试内联构造输入（G0.9：结构性输入允许内联/tmp_path；**禁止**引用 gitignored `novel-xinghuo-vol1/` 路径）
- english **分支语义**与 dispatch 直写路径行为不变（既有测试 :1044 钉住）；晋升/merge_prose 为**新接线**——english 项目在这两路上获得 F1301 头注入（Task 3 Step 2 红测钉住该新行为）
- **leaf/infra 分类**：Task 1/2/3 全 infra（pipeline 核心模块 dispatch_helper/chapter_loop + 其工具链）→ 协调者亲自实现（TDD），不分派 implementer 子 agent
- Conventional commits：`fix:`（归一/接线）/ `feat:`（断言工具）；commit 显式列文件路径（pathspec 纪律）
- 本 plan 的行号锚为 2026-11-10 main=3b60895f 快照：dispatch_helper 注入器 `_ZH_CHAPTER_LINE_RE` :2011 / `_insert_zh_header` :2037 / `ensure_chapter_header` :2067 / merge_prose 写盘 :3104-3112 / else 分支注入 :3125-3131；chapter_loop `_run_scene_split_step` 写盘 :1566-1571；执行时以符号 re-anchor 为准

---

### Task 1: 归一规则内嵌 `_insert_zh_header` + 公有包装

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:2011 常量区、:2037-2064 `_insert_zh_header`、:2067-2084 `ensure_chapter_header` 后新增公有函数）
- Test: `tests/unit/pipeline/test_dispatch_helper.py`（spec#84 zh 形态族 :984-1027 就近扩展）

**Interfaces:**
- Produces: `normalize_chapter_header(content: str, chapter_num: int, project_root: Path) -> str`（公有，Task 3/4 三调用点用）
- Produces: 公有正则 `ZH_CHAPTER_LINE_RE`（`^# 第[0-9]+章$` MULTILINE，原 `_ZH_CHAPTER_LINE_RE` 改名）、`ZH_CHAPTER_LINE_CJK_RE`（`^# 第[一二三四五六七八九十百千零〇]+章$` MULTILINE）——Task 2 工具导入单源

- [ ] **Step 1: 写红测**（追加到 zh 形态族；英文 docstring）

```python
def test_insert_zh_header_normalizes_cjk_numeral_in_place() -> None:
    from shenbi.pipeline.dispatch_helper import ensure_chapter_header

    body = "<!--META-END-->\n\n# 第四十一章\n\n# 勾名\n\n正文。"
    out = ensure_chapter_header(body, 41, style="two_line_zh")
    assert "# 第41章" in out
    assert "第四十一章" not in out
    assert "# 勾名" in out  # 章题不动


def test_insert_zh_header_strips_cjk_line_when_arabic_present() -> None:
    from shenbi.pipeline.dispatch_helper import ensure_chapter_header

    body = "<!--META-END-->\n\n# 第41章\n\n# 第四十一章\n\n# 勾名\n\n正文。"
    out = ensure_chapter_header(body, 41, style="two_line_zh")
    assert out.count("# 第41章") == 1
    assert "第四十一章" not in out


def test_insert_zh_header_strips_english_header_residue() -> None:
    from shenbi.pipeline.dispatch_helper import ensure_chapter_header

    body = "# Chapter 41:\n\n# 第41章\n\n# 勾名\n\n正文。"
    out = ensure_chapter_header(body, 41, style="two_line_zh")
    assert "Chapter 41" not in out
    assert out.count("# 第41章") == 1


def test_insert_zh_header_replaces_english_line_when_no_zh() -> None:
    import re as _re

    from shenbi.pipeline.dispatch_helper import ensure_chapter_header

    body = "# Chapter 41: 旧题\n\n# 勾名\n\n正文。"
    out = ensure_chapter_header(body, 41, style="two_line_zh")
    # Full-line assertion: the canonical line must be line-anchored complete —
    # a substring assert would pass even with the old title glued on (C1).
    assert _re.search(r"^# 第41章$", out, _re.MULTILINE)
    assert "Chapter 41" not in out
    assert "旧题" not in out
    assert "# 勾名" in out


@pytest.mark.parametrize(
    "body",
    [
        "<!--META-END-->\n\n# 第四十一章\n\n# 勾名\n\n正文。",
        "<!--META-END-->\n\n# 第41章\n\n# 第四十一章\n\n# 勾名\n\n正文。",
        "# Chapter 41: 旧题\n\n# 勾名\n\n正文。",
        "<!--META-END-->\n\n# Chapter 41:\n\n# 第41章\n\n# 勾名\n\n正文。",
    ],
)
def test_normalize_chapter_header_converges_idempotent(body: str, tmp_path: Path) -> None:
    """Convergence pin: normalizing twice equals once, for every dirty form."""
    from shenbi.pipeline.dispatch_helper import normalize_chapter_header

    (tmp_path / "genre-config.json").write_text(
        '{"chapter_word": {"chapter_header_style": "two_line_zh"}}', encoding="utf-8"
    )
    once = normalize_chapter_header(body, 41, tmp_path)
    assert normalize_chapter_header(once, 41, tmp_path) == once
    assert once.count("# 第41章") == 1
    assert "第四十一章" not in once and "Chapter" not in once


def test_insert_zh_header_arabic_present_pure_is_byte_identical() -> None:
    from shenbi.pipeline.dispatch_helper import ensure_chapter_header

    body = "<!--META-END-->\n\n# 第41章\n\n# 勾名\n\n正文。"
    assert ensure_chapter_header(body, 41, style="two_line_zh") == body


def test_normalize_chapter_header_wrapper_resolves_style(tmp_path: Path) -> None:
    from shenbi.pipeline.dispatch_helper import normalize_chapter_header

    (tmp_path / "genre-config.json").write_text(
        '{"chapter_word": {"chapter_header_style": "two_line_zh"}}', encoding="utf-8"
    )
    body = "# 第四十二章\n\n# 过站\n\n正文。"
    out = normalize_chapter_header(body, 42, tmp_path)
    assert "# 第42章" in out and "第四十二章" not in out
```

- [ ] **Step 2: 跑红**：`uv run pytest tests/unit/pipeline/test_dispatch_helper.py -k "zh_header or normalize_chapter" -q` → 新测 FAIL（ImportError normalize_chapter_header / 断言失败）
- [ ] **Step 3: 最小实现**——① `_ZH_CHAPTER_LINE_RE` 改名 `ZH_CHAPTER_LINE_RE`（模块内 2 处用点同步）；常量区追加：

```python
ZH_CHAPTER_LINE_CJK_RE = re.compile(r"^# 第[一二三四五六七八九十百千零〇]+章$", re.MULTILINE)
# English-contract header as a per-LINE residue scanner. Derived from the
# CHAPTER_HEADER_RE prefix contract but LINE-ANCHORED both ends: the shared
# pattern has no "$" and its "\s+" can cross newlines — as a line scanner it
# would truncate "# Chapter 41: 旧题" at the colon (title glued onto the
# replacement) and mis-delete across lines (plan review C1). [ \t] not \s.
EN_CHAPTER_HEADER_LINE_RE = re.compile(r"^#[ \t]+Chapter[ \t]+\d+:[^\n]*$", re.MULTILINE)
```

② `_insert_zh_header` 头部插入区域归一段（marker 解析后、既有零动作判定重构为下述规则；保留原 docstring 并补归一语义）：

```python
def _normalize_zh_number_lines(region: str, chapter_num: int) -> str:
    """Converge any region to exactly one Arabic ``# 第N章`` line (spec #84
    T0-14 I-3): Arabic present -> strip CJK-numeral + English-residue lines;
    else first CJK (then English) line replaced in place, remaining stripped."""
    if ZH_CHAPTER_LINE_RE.search(region):
        new = ZH_CHAPTER_LINE_CJK_RE.sub("", region)
        new = EN_CHAPTER_HEADER_LINE_RE.sub("", new)
        if new != region:
            log.info("chapter_header_normalized", kind="strip_residue", chapter=chapter_num)
        return new
    cjk = list(ZH_CHAPTER_LINE_CJK_RE.finditer(region))
    en = list(EN_CHAPTER_HEADER_LINE_RE.finditer(region))
    first = cjk[0] if cjk else (en[0] if en else None)
    if first is None:
        return region
    region = region[: first.start()] + f"# 第{chapter_num}章" + region[first.end() :]
    region = ZH_CHAPTER_LINE_CJK_RE.sub("", region)
    region = EN_CHAPTER_HEADER_LINE_RE.sub("", region)
    log.info("chapter_header_normalized", kind="replace_numeral", chapter=chapter_num)
    return region
```

（`_insert_zh_header` 两分支 region 取得后先过 `_normalize_zh_number_lines(region, chapter_num)`，再走既有「阿码在→零动作/无→首空行插入」——归一后阿码已在则自然零动作；无 marker 分支 region=全文。）

③ `ensure_chapter_header` 后新增公有包装：

```python
def normalize_chapter_header(content: str, chapter_num: int, project_root: Path) -> str:
    """Single normalization entry for EVERY chapter-prose write path (spec
    #84 T0-14 / 手工通道纪律): resolves chapter_header_style from the
    project's genre-config, delegates to ensure_chapter_header. Idempotent
    for compliant content; english default keeps F1301 semantics."""
    return ensure_chapter_header(content, chapter_num, style=_chapter_header_style(project_root))
```

- [ ] **Step 4: 跑绿**：同 Step 2 命令 → 全 PASS；再跑全文件 `uv run pytest tests/unit/pipeline/test_dispatch_helper.py -q` 零翻转（改名后的既有用点若有测试直接 import 私有名需同步——grep 确认）
- [ ] **Step 5: Commit**：`git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py && git commit -m "fix: _insert_zh_header 内嵌中文数字/英文残留归一（阿码恰一行收敛）+公有 normalize_chapter_header 包装——spec #84 T0-14 I-3/M-2/M-6"`

### Task 2: 断言工具 + just target + 驱动 prompt 替换

**Files:**
- Create: `tools/lint_chapter_headers.py`
- Modify: `justfile`（lint 工具族 target 区，pool-lint :109 附近）
- Modify: `docs/regen-vol2-driver-prompt.md:48-57`（内联 bash 断言**替换**为 just 调用——I-2，一弱一强双权威禁止）+ `:5` 措辞改「直写/晋升/修订写盘」三路
- Test: `tests/unit/tools/test_lint_chapter_headers.py`（新建；先确认 `tests/unit/tools/` 目录与 `__init__` 惯例，无则按既有最近 Tests 平铺惯例落位）

**Interfaces:**
- Consumes: `ZH_CHAPTER_LINE_RE` / `ZH_CHAPTER_LINE_CJK_RE` / `EN_CHAPTER_HEADER_LINE_RE`（Task 1 公有导出）；`gates.shared.CHAPTER_HEADER_RE`
- Produces: `main(argv: list[str]) -> int`（0=全绿 / 1=有违例）；CLI：`lint_chapter_headers.py <project_dir>`（无选项——唯一消费方是 just target 与驱动 prompt 的裸调用，M3 YAGNI）

- [ ] **Step 1: 写红测**（tmp_path 构造结构性输入——G0.9 允许面；英文 docstring）

```python
"""Structural tests for the chapter-header form assertion tool (spec #84 T0-14)."""

from pathlib import Path


def _write(dir_: Path, name: str, text: str) -> None:
    d = dir_ / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


GOOD = "<!--META-END-->\n\n# 第37章\n\n# 过期四十一天\n\n正文。"
# On-disk adjacency mirrored: ch39/40 carry the date H1 directly adjacent to
# the title H1 (no blank line between them) — keep fixtures faithful (M5).
CH39_FORM = "<!--META-END-->\n\n# 第39章\n\n# 正月廿六\n# 数目另议\n\n正文。"  # 3 H1
CH40_FORM = "<!--META-END-->\n\n# 正月廿八\n# 还不起\n\n正文。"  # 无章号
CH41_FORM = "<!--META-END-->\n\n# 第四十一章\n\n# 勾名\n\n正文。"  # 中文数字
EN_RESIDUE = "<!--META-END-->\n\n# Chapter 41:\n\n# 第41章\n\n# 勾名\n\n正文。"


def test_good_chapter_passes(tmp_path, capsys) -> None: ...
def test_three_h1_flagged(tmp_path, capsys) -> None: ...  # CH39_FORM -> exit 1, cites 恰一行非章号
def test_missing_number_flagged(tmp_path, capsys) -> None: ...  # CH40_FORM
def test_cjk_numeral_flagged(tmp_path, capsys) -> None: ...  # CH41_FORM
def test_english_residue_flagged(tmp_path, capsys) -> None: ...  # EN_RESIDUE
def test_backups_and_sidecars_excluded(
    tmp_path, capsys
) -> None: ...  # chapter-9-pre-rev.md / chapter-9-decisions.json 脏内容不触发
```

（`...` 处按既有 tools 测试断言风格补全：`main([str(tmp_path)]) == 0/1` + stdout 关键词断言；实现面用 stem fullmatch `chapter-\d+` 选文件，禁黑名单）

- [ ] **Step 2: 跑红** → ModuleNotFoundError
- [ ] **Step 3: 实现工具**（输出惯例先读 `tools/lint_truth_pool.py` 头 40 行镜像；src 导入共享正则，禁复制 pattern）：

```python
"""Chapter-header form assertion for a novel project (spec #84 T0-14).

Per chapters/chapter-<N>.md (stem fullmatch chapter-\d+ — -pre-rev backups
and decisions sidecars are naturally excluded):
  1. exactly one  ^# 第[0-9]+章$              (Arabic chapter-number line)
  2. zero         ^# 第[一二三四五六七八九十百千零〇]+章$   (CJK-numeral line)
  3. zero         English-contract header line  (^# Chapter N:)
  4. exactly two  ^# -lines total               (number line + single title)

Exit 0 = all green; exit 1 = one report line per violating file.
Regexes are single-sourced from shenbi.pipeline.dispatch_helper (M-1).
"""
```

- [ ] **Step 4: justfile target**（lint 工具族区）：

```make
# Chapter-header form assertion (spec #84 T0-14): just chapter-headers <dir>
chapter-headers *args:
    uv run python tools/lint_chapter_headers.py "$@"
```

- [ ] **Step 5: 驱动 prompt 替换**：`docs/regen-vol2-driver-prompt.md` :48-57 整块内联 bash 循环删除，替换为 `just chapter-headers novel-xinghuo-vol1`（→ exit 0，四条件全章强制说明一行）；:5「管线写路径自动按两行式中文章头规范化」改为「管线写路径（直写/晋升/修订三路）自动按两行式中文章头规范化」
- [ ] **Step 6: 跑绿**：`uv run pytest tests/unit/tools/test_lint_chapter_headers.py -q` 全 PASS；`just chapter-headers novel-xinghuo-vol1` 亲跑 → **预期 exit 1 且恰报 12 章**（ch39/40/41-50；ch37/38 与 ch1-36 零误报）——工具检出力校准，输出粘 progress.md 验收证据
- [ ] **Step 7: Commit**：`git add tools/lint_chapter_headers.py tests/unit/tools/test_lint_chapter_headers.py justfile docs/regen-vol2-driver-prompt.md && git commit -m "feat: just chapter-headers 章头形态断言工具（四条件/全章/单源正则）+卷二驱动 prompt 内联断言替换——spec #84 T0-14 I-2/M-1/M-3"`

### Task 3: 两处写路径接线（晋升 + merge_prose）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1566-1571`（晋升写盘循环）+ import 块 :57-63 增 `normalize_chapter_header`
- Modify: `src/shenbi/pipeline/dispatch_helper.py`：merge_prose 分支 :3104-3112（size 守卫后、safe_write 前）+ else 分支 :3125-3131 改用包装（style 解析单源）
- Test: `tests/pipeline/test_bundle_stepping.py`（`_project` :54-63 补 two_line_zh 镜像生产）+ 新增 english 形晋升测试；`tests/unit/pipeline/test_write_mode_merge_prose.py`（新增基座带病头用例）

**Interfaces:**
- Consumes: `normalize_chapter_header`（Task 1）
- Produces: 晋升/修订写盘产物章头恒合规（不变量：每条章正文写路径过同一归一入口）

- [ ] **Step 1: 红测①（晋升 zh 归一）**——先扩 `_w`（:28-52）加头形覆盖形参 `header: str | None = None`（None=现行 `f"# 第{n}章"`；传 `f"# 第{n}章"` 以外的形态供 CJK 用例），再新增：

```python
@pytest.mark.integration
def test_split_step_normalizes_cjk_numeral_header(tmp_path: Path) -> None:
    _project(tmp_path)  # two_line_zh 已在 _project 内（本 task Step 3 改）
    # bundle CH1 体用中文数字头形（`# 第一章`）——其余按既有 bundle 形状
    _bundle_with_header(tmp_path, 1, header="# 第一章")  # _w 扩展形的薄包装
    issues = _run_scene_split_step(tmp_path, 1)
    assert issues == []
    text = (tmp_path / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
    assert re.search(r"^# 第1章$", text, re.MULTILINE)
    assert "第一章" not in text
```

- [ ] **Step 2: 红测②（english 形前插钉住）**——config-less tmp 项目（不写 genre-config）+ bundle 体无任何头 → 晋升后文件顶有 `# Chapter 1:`（F1301 语义在晋升路径生效=I-1 裁决的 english 侧钉子）
- [ ] **Step 3: 改 `_project`**：genre-config dict 增 `"chapter_header_style": "two_line_zh"`（镜像生产；既有断言零破坏——bundle 体自带阿码头，归一零动作）
- [ ] **Step 4: 红测③（merge_prose）**——test_write_mode_merge_prose 新增：基座含 `# 第四十五章` 中文数字形 + 合法场景替换清单 → 落盘结果含 `# 第45章` 不含中文数字形
- [ ] **Step 5: 跑红**（三处）
- [ ] **Step 6: 接线实现**：

```python
# chapter_loop.py 晋升循环（:1566-1571）
for ch in bundle.chapters:
    target = project_dir / "chapters" / f"chapter-{ch.number}.md"
    body = normalize_chapter_header(ch.body, ch.number, project_dir)
    safe_write(target, body.encode("utf-8"))
```

```python
# dispatch_helper.py merge_prose 分支（size 守卫后）
new_text = res.new_text
if _is_chapter_prose_write(rel_path):
    new_text = normalize_chapter_header(
        new_text, int(Path(rel_path).stem.split("-")[1]), project_root
    )
safe_write(full_path, new_text, allowed_roots=(project_root,))
# 后续 len(res.new_text) 日志字段同步用 len(new_text)
```

else 分支 :3125-3131 内联三行（style 解析+调用）改一行 `content = normalize_chapter_header(content, int(...), project_root)`（行为等价，单源）
- [ ] **Step 7: 跑绿**：三处新测 + 零翻转跑面扩列（M1——两个真实 `_run_scene_split_step` 调用方，english 缺省行为变更最敏感下游）：`uv run pytest tests/pipeline/test_bundle_stepping.py tests/pipeline/test_xc_wiring.py tests/unit/pipeline/test_write_mode_merge_prose.py tests/unit/pipeline/test_dispatch_helper.py tests/unit/tools/test_release_split.py -q`
- [ ] **Step 8: Commit**：`git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_bundle_stepping.py tests/unit/pipeline/test_write_mode_merge_prose.py && git commit -m "fix: 章头归一接入晋升与 merge_prose 写路径——每条章正文写路径过同一归一入口（spec #84 T0-14；english 缺省行为在两新路径钉住）"`

### Task 4: 在盘修复 ch39-50 + 绿跑（本地 gitignored 面，无 commit）

**Files:**
- Modify（本地，gitignored）: `novel-xinghuo-vol1/chapters/chapter-{39..50}.md`
- Write: `novel-xinghuo-vol1/vol1-ledger.md`（T0-14 记录行——与 Task 5 收口节同批写）

- [ ] **Step 1: ch39 删日期 H1 行** `# 正月廿六`（保留 `# 第39章`+`# 数目另议`；Edit 精确行级操作）
- [ ] **Step 2: ch40 日期 H1 原位替换**：`# 正月廿八` → `# 第40章`（M-5：保结构，落位即注入器插入位）
- [ ] **Step 3: ch41-50 dogfood 归一器**：

```bash
uv run python -c "
from pathlib import Path
from shenbi.pipeline.dispatch_helper import normalize_chapter_header
from shenbi.safe_write import safe_write
root = Path('novel-xinghuo-vol1')
for n in range(41, 51):
    p = root / 'chapters' / f'chapter-{n}.md'
    t = p.read_text(encoding='utf-8')
    out = normalize_chapter_header(t, n, root)
    if out != t:
        safe_write(p, out.encode('utf-8'))
        print(n, 'normalized')
"
```

- [ ] **Step 4: 章题↔plan 声明一致性核**：`grep -n "章题\|标题" novel-xinghuo-vol1/plans/chapter-39-plan.md novel-xinghuo-vol1/plans/chapter-40-plan.md`——ch39 期望「数目另议」、ch40 期望「还不起」；不一致→记 deviation 不擅改
- [ ] **Step 5: 绿跑**：`just chapter-headers novel-xinghuo-vol1` → exit 0（ch1-50 全绿）+ `git status novel-xinghuo-vol1` 确认无意外扩散；输出粘 progress.md
- [ ] **Step 6: 字数带边距抽查**：ch39/40 头行字符变动对 G2/G4 字数的影响核（两章头行变更 ±5 字级）——`uv run pytest tests/pipeline -q` 全绿即充（管线字数为结构校验，非在盘重算；如发现带边距章挂账记录）

### Task 5: Task 10 Step 3-4 收口验收 + 台账（本地 gitignored 面）

**Files:**
- Write: `novel-xinghuo-vol1/vol1-ledger.md`（「卷二开卷运行」节追加收口小节）

- [ ] **Step 1: 读 ledger 「卷二开卷运行」节 :344 至节尾（当前 :480——含束8/9 与 #101 分叉落点，I2）**——逐项裁定 spec 验收 3：①三件套全中（热开篇/自选目标出口/章尾热钩——束1-4 记录+裁决 #02-#09 及束4 生产验收窗节）②断供钩清偿表（七三一编号卡 ch37-42 推进/老驼纸条并轨/帖木哥归否 ch37-48/第三哨挂起锚/萤饼债+春天之约 KR/罚单处置/笔迹链挂起锚——记录+正文 grep 双证）③shadow 促转零误伤（:384 促转节——hook_max_age/volume_opening_protocol 已转正、连续 2 束 WARN 零误伤判定记录）
- [ ] **Step 2: 正文 grep 补证**（断供钩表实体在章内落点——`grep -n "七三一\|编号卡" novel-xinghuo-vol1/chapters/chapter-3[7-9].md chapter-4[0-2].md` 等；只取证不判内容）
- [ ] **Step 3: 台账收口小节落盘**（T0-14 修复记录 12 章清单+断言工具+接线三路+验收 3 四项裁定+G3.4 r4 挂账复述+束4-9 解冻对账）——记录在案即 spec Task 10 Step 4「台账卷二开卷节」完成
- [ ] **Step 4: memory 断点更新**（I3——spec 验收 4 后半件）：会话记忆断点更新至「卷二开卷协议就位+T0-14 闭环」（auto-memory 于 Task 7 Step 4 终态块同批更新，此处登记归属防漏）
- [ ] **Step 5: 残余不闭合项登记**：任何验收 3 子项不能从在册证据闭合→progress.md 挂账（不扩面自修——对齐 G3.4 P2=7 挂账先例）

### Task 6: 阶段 7-11 门禁与 PR（代码批）

- [ ] **Step 1: task 审计**——Task 1/2/3 各 commit 后 fresh-context 审计（audit-T1/T2/T3.md；同文件族小批可并一审计+deviation 登记，先例 spec #100 批审计）
- [ ] **Step 2: `just check`**（权威真理源）全绿输出粘 progress.md；`uv lock --check`（本批未动 pyproject/uv.lock 则免）
- [ ] **Step 3: 阶段 8 终审**——audit_loop(scope=全 branch 改动, sha_range=(main, HEAD))，C/I 全清
- [ ] **Step 4: PR**——`gh pr create`（fix/spec-84-header-promotion）；PR 描述含价值裁决摘要+deviations+验收证据；CI 全绿后 `gh pr merge --squash --delete-branch`；评论/注解按 AGENTS §PR Review Protocol（先收集全部再修、逐条 reply+GraphQL resolve）
- [ ] **Step 5: post-merge**——main HEAD 复跑 `just check` 粘 progress.md；`git checkout main && git pull && git branch -D fix/spec-84-header-promotion && git remote prune origin`

### Task 7: 阶段 12 归档批（docs PR）

**Files:**
- Modify: `docs/superpowers/specs/2026-10-30-spec84-vol1-repair-vol2-launch.md`（r14 修订 + `Status: Done (PR #N)`）→ move `docs/superpowers/specs/archive/`
- Modify: `docs/superpowers/plans/2026-11-01-spec84-vol1-repair-vol2-launch.md` + 本 addendum plan → `docs/superpowers/plans/archive/`
- Modify: `docs/superpowers/specs/INDEX.md`（删 #84 行；**顺带修 L134-138 #100 无头残句**——同文件缺陷补完归档移除；头行「活跃 spec 数」12→11 复核）+ `docs/superpowers/plans/INDEX.md`

- [ ] **Step 1: spec r14**——执行状态块重写：T0-14 真相（r13 立项未落码→本批落地：归一/接线三路/12 章修复/断言工具）+ 束4-9 解冻对账（ch43-50 在盘，#95/#98/#99/#100 验收场）+ §3 验收 3 文件集口径改「`just chapter-headers` 全在册章绿」+ 失实声明修正注记
- [ ] **Step 2: 归档移动**（specs/plans 双库分置）+ INDEX 删行 + #100 残句清理 + plans/INDEX 同步；`git grep 2026-10-30-spec84` 仅在 archive/
- [ ] **Step 3: 归档 PR**：`docs(archive): spec84 vol1-repair-vol2-launch done (PR #N)`——分支+PR+CI 全绿（docs workflow 对 docs-only 最严：mkdocs --strict 链接校验，移动后查文件内相对链接）+ `gh pr merge --squash --delete-branch` + 本地 `-D` + prune
- [ ] **Step 4: progress.md 最终状态块**（merged PR #N×2）+ 完成报告（含 #97 待归档提醒）

---

## Self-Review 记录

- 覆盖：T0-14 四工作面（归一 Task 1/接线 Task 3/修复 Task 4/断言 Task 2）+ 复核新增 merge_prose（Task 3）+ I-1（english 钉子 Task 3 Step 2）/I-2（Task 2 Step 5）/I-3（Task 1）/I-4（Task 7 Step 1）+ Task 10 Step 3-4（Task 5）+ 归档（Task 7）——无缺口
- 占位扫描：Task 2 Step 1 测试体 `...` 为断言风格占位（实现时按既有 tools 测试补全，非语义 TBD）；Task 3 Step 1 bundle 构造复用文件内既有 helper——其余步骤全部实码
- 类型一致：`normalize_chapter_header(content: str, chapter_num: int, project_root: Path) -> str` 三调用点与包装定义一致；正则公有名 Task 1 产出=Task 2 消费
