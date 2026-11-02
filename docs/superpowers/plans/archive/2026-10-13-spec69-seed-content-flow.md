# spec #69 seed 内容流恢复与传递性收尾 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **本项目例外（SDD v6 leaf/infra 分流）**：本 plan 全部 task 触及 infra 模块（pipeline/gates/contracts），由协调者亲自实现（不分派 implementer 子 agent）；每 task 完成后 fresh-context 审查子 agent 产出 `.superpowers/sdd/audit-T<N>.md`（SDD 阶段 6 铁律，无 audit-T<N>.md 不得开始 T<N+1>）。

**Goal:** F886 断流根治——pipeline init 写出的 `genesis-context/*.md` seed 片段经契约 reads 通道接入五个 genesis 技能派发 prompt；顺带清偿孤儿 reads / 配角节 / 丢弃键 WARN / G0.2 节锚定 / F368 残余 / NovelConfig 死 schema / 4.3 六项裁决固化。

**Architecture:** 契约声明式接线（frontmatter `reads:` 声明具体片段路径 + `sync_contracts` 再生成 + SKILL 正文同步句），注册表 globs 段一行加法使具体路径过 loader `resolves()` 强制；框架代码改动 = seed_parser（T2/T3）+ g0（T4）+ chapter_loop（T5）三处小面 + cli.py 注释一处 + novel.py 删除（T6）。零新框架机制。

**Tech Stack:** Python 3.11+ / pydantic 契约层 / pytest（uv run 同构）/ structlog。

**Spec:** `docs/superpowers/specs/2026-10-13-spec69-seed-content-flow.md`（v2.4，commit 39801d3c）。§1/§2 钉死内容 plan 照抄不发明。

## Global Constraints（每 task 隐含包含）

- 验证一律 `uv run`（与 CI `uv run --frozen` 同构）；系统 python 结果不算证据
- `src/shenbi/` 禁 `print()`（structlog）；gate 检查器纯函数幂等；pathlib 文件 IO
- 契约改动三联动：frontmatter + `uv run python -m shenbi.sync_contracts` 再生成 + SKILL 正文同步；生成物（deps.json/docs/framework//skills/ AUTO 段）随同 commit，禁手改生成物
- **触及 src/shenbi/ 任何文件的任务 commit 前跑 `bash tests/lock-tool-hashes.sh`**（R3 全树活锁；sync_contracts 不再锁此段）
- commit 走 pathspec 显式列文件（禁 `git add -A`），Conventional Commits
- G0.9：scenario 输入引用 `tests/fixtures/` 真实产物或测试内字面量（先例 `tests/unit/pipeline/conftest.py::sample_seed_content`；spec v2.1 消歧——本 plan 的丰富版 seed 一律测试内字面量，不落 tests/fixtures/）
- 核心原则 8：全程禁真实 dispatch / pipeline 子命令取证；LLM 产物验收用离线组装测试表达（F947）
- 无评分场景 → G3.4 独立评分不适用（本 plan 全部为确定性结构测试）

## 验收覆盖表（spec §3 → task → 可执行验证）

| spec 验收 | task | 验证命令 |
|---|---|---|
| §3.1 `just check` 全绿 | T9 | `just check` → EXIT=0 |
| §3.2 G5 delta 钉死 | T9 | `uv run pytest tests/unit/gates/test_g5.py -k genesis_context -v`（新测试断言四对+spillover）+ `uv run python -c`（gate_G5 直跑，genesis 相 missing 键集合比对）|
| §3.3 T0/T1 契约+组装测试 | T1/T2 | `uv run pytest tests/pipeline/test_dispatch_reads_injection.py -v` |
| §3.3 T2 配角节 | T3 | `uv run pytest tests/unit/pipeline/test_seed_parser.py -k "Supporting or RichSeed" -v`；`uv run pytest tests/unit/pipeline/test_e2e.py -k "supporting or rich_seed" -v`（两条分跑）|
| §3.3 T3 丢弃键 WARN | T4 | `uv run pytest tests/unit/pipeline/test_seed_parser.py -k dropped -v` |
| §3.3 T4 G0.2 节锚定 | T5 | `uv run pytest tests/unit/gates/test_g0.py -k "target_words or basic_info" -v` |
| §3.3 T5 两测 | T6 | `uv run pytest tests/unit/pipeline/test_chapter_close_retry_sweep.py -v` |
| §3.3 T6 代码面 grep 零命中 | T7 | `grep -r NovelConfig --include='*.py' src/ tests/ tools/` → 空输出 |
| §3.4 丰富版 seed fixture 化 | T3 | `uv run pytest tests/unit/pipeline/test_seed_parser.py -k rich_seed -v`（十节合计 <100K + 各节 <32K 断言）|
| §3.5 T7 验收（六项裁决齐全） | T8 | spec §2 T7 对照检查（commit message 记录）+ `grep -n "4.3" docs/getting-started/first-novel.md`（预期空/无关）|
| §3.6 挂账闭合 | T6/T8 | T6: c37-triage F368 行更新；T8: F886 行 + findings-ledger + cli.py 注释 |
| §3.7 顺序注记 | —（本 spec 交付后用户动作，plan 不含）| — |

---

### Task 1: 注册表加法 + character-design 孤儿路径修正（spec T0）

**Files:**
- Modify: `docs/framework/truth-files.yaml`（globs 段 +1 行；concepts 段 −2 行）
- Modify: `skills/shenbi-character-design/SKILL.md:10-11`（frontmatter reads）+ 正文 44-45/105-106/201-203 + 权威序句
- Test: `tests/pipeline/test_dispatch_reads_injection.py`（character-design 用例改 staging 路径）
- Regen: `uv run python -m shenbi.sync_contracts`（AUTO 段 + deps.json + docs/framework/truth-files.index.json）

**Interfaces:**
- Produces: `genesis-context/chapter_outline.md`/`genesis-context/three_act.md` 成为 loader 可解析的合法 read 路径（globs 行）——Task 2 五技能接线复用该前提
- Consumes: 无（先行件）

**复杂度:** infra（契约 + 注册表）· **test_kind:** tdd_red_green · **层级:** T1 单测（离线组装，F947）

- [ ] **Step 1: 写失败测试**——`tests/pipeline/test_dispatch_reads_injection.py` 的 character-design 用例（:28-41）改为：

```python
(
    (
        "shenbi-character-design",  # F809 — nested placement: the dispatcher's
        # stdlib glob has no recursive=True, so `**` is single-level
        # (characters/<dir>/*.md), matching characters/major/alice.md.
        # spec #69 T0: outline/ orphan reads re-anchored to genesis-context/.
        [
            "world/story_bible.md",
            "world/rules.md",
            "genesis-context/chapter_outline.md",
            "genesis-context/three_act.md",
            "characters/major/alice.md",
        ],
        [
            "genesis-context/chapter_outline.md",
            "genesis-context/three_act.md",
            "characters/major/alice.md",
        ],
        [],
    ),
)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_dispatch_reads_injection.py -k "character-design" -v`
Expected: FAIL（`expected input not injected: genesis-context/chapter_outline.md`——契约 reads 仍指 outline/ 旧路径；`-k` 用连字符形态匹配 parametrize id）

- [ ] **Step 3: 实施最小改动**

1. `docs/framework/truth-files.yaml` globs 段（:149 起的 `globs:` 列表）末尾加：

```yaml
  - {pattern: genesis-context/*.md}  # spec #69: seed fragments (concepts :91 twin; loader resolves + dag_key canonicalize)
```

2. 同文件 concepts 段删除两行（:103-104）：

```yaml
  - {name: outline/chapter_outline.md, kind: outline, producer: skill}
  - {name: outline/three_act.md, kind: outline, producer: skill}
```

（陈旧登记：producer: skill 但全仓零写方；T0 后零读者，保留转 R2 orphan-concept WARN）

3. `skills/shenbi-character-design/SKILL.md:10-11` frontmatter 两行改为：

```yaml
  - genesis-context/chapter_outline.md
  - genesis-context/three_act.md
```

4. 正文同步（4 处行带）：:44-45「No character explicitly named in `genesis-context/chapter_outline.md` or `genesis-context/three_act.md` may be omitted.」；:105-106「identified from `genesis-context/chapter_outline.md` and `genesis-context/three_act.md`」；:201/:203 两行 `outline/…` → `genesis-context/…`。（:35 Reads 摘要行在 AUTO-GENERATED 段内，Step 5 再生成自动覆盖，不入手改清单）

5. 正文 AUTO 段后加权威序句（spec §1）：

```markdown
**Seed 片段（genesis-context/）**：`genesis-context/chapter_outline.md` 与 `genesis-context/three_act.md` 是人类伙伴 seed 原文（开篇章纲/三幕结构节）的逐字片段。权威序：上游 truth（story_bible/rules 等）> seed 片段；冲突时以上游为准，若据此调整须在产出档案内以「seed 意向与 truth 冲突的处理记录」小节披露（含一句理由）。
```

- [ ] **Step 4: 再生成 + 全量相关测试**

Run: `uv run python -m shenbi.sync_contracts && uv run pytest tests/pipeline/test_dispatch_reads_injection.py tests/unit/contracts -q && git diff --stat`
Expected: 注入测试 PASS；contracts 面零回归；diff 含 SKILL.md AUTO 段 + deps.json + docs/framework/truth-files.index.json（两 concept 键消失）

- [ ] **Step 5: Commit（pathspec + R3 无涉及——本 task 不触 src/shenbi/，锁面无漂移）**

```bash
git add docs/framework/truth-files.yaml skills/shenbi-character-design/SKILL.md tests/pipeline/test_dispatch_reads_injection.py docs/framework/truth-files.index.json tests/tiers/deps.json docs/skills 2>/dev/null || git add docs/framework/truth-files.yaml skills/shenbi-character-design/SKILL.md tests/pipeline/test_dispatch_reads_injection.py
git commit -m "feat(contracts): spec69 T0——character-design 孤儿 reads 锚定 genesis-context + 注册表 globs 加法"
```

（实际生成物路径以 Step 4 `git status` 为准逐一列名）

---

### Task 2: 五技能 genesis-context 接线（spec T1，主体）

**Files:**
- Modify: `skills/shenbi-worldbuilding/SKILL.md`、`skills/shenbi-story-architecture/SKILL.md`、`skills/shenbi-faction-builder/SKILL.md`、`skills/shenbi-volume-outlining/SKILL.md`（frontmatter reads + 正文句）
- Test: `tests/pipeline/test_dispatch_reads_injection.py`（四技能新用例 + 契约声明断言 + 缺文件可选性测试）
- Regen: `uv run python -m shenbi.sync_contracts`

**Interfaces:**
- Consumes: Task 1 的 globs 行（loader resolves 前提）
- Produces: 五技能 reads 含各自片段路径（T1 表映射，见各技能步骤）；后续 T3 在 character-design 追加 supporting

**复杂度:** infra（契约）· **test_kind:** tdd_red_green · **层级:** T1 单测（离线组装，F947）

- [ ] **Step 1: 写失败测试**——`tests/pipeline/test_dispatch_reads_injection.py` 追加：

```python
#: spec #69 T1: genesis-context fragments wired into the five genesis skills.
GENESIS_FRAGMENT_CASES = [
    # (skill, staged fragment files, expected-injected subset)
    (
        "shenbi-worldbuilding",
        ["genesis-context/world_rules.md", "novel.json"],
        ["genesis-context/world_rules.md"],
    ),
    (
        "shenbi-story-architecture",
        [
            "genesis-context/three_act.md",
            "genesis-context/plot_lines.md",
            "genesis-context/surface_conflict.md",
            "genesis-context/personal_conflict.md",
            "genesis-context/deep_conflict.md",
            "novel.json",
        ],
        [
            "genesis-context/three_act.md",
            "genesis-context/plot_lines.md",
            "genesis-context/surface_conflict.md",
            "genesis-context/personal_conflict.md",
            "genesis-context/deep_conflict.md",
        ],
    ),
    (
        "shenbi-faction-builder",
        ["genesis-context/forces.md", "novel.json"],
        ["genesis-context/forces.md"],
    ),
    (
        "shenbi-volume-outlining",
        ["genesis-context/chapter_outline.md", "novel.json"],
        ["genesis-context/chapter_outline.md"],
    ),
]


@pytest.mark.parametrize("skill,files,expected", GENESIS_FRAGMENT_CASES)
def test_genesis_fragment_injected(tmp_path: Path, skill, files, expected):
    for rel in files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(MARK, encoding="utf-8")
    _, user_prompt, _, reads_manifest = _build_skill_prompt(
        skill=skill, project_dir=tmp_path, prompt="genesis", chapter=None
    )
    for key in expected:
        assert key in user_prompt, f"{skill}: expected fragment not injected: {key}"
        # spec §3.3 reads_manifest 面: injection is recorded (dispatch_helper
        # 4th return; entries carry {"path": key, "mode": "full", ...}).
        assert any(e.get("path") == key for e in reads_manifest), (
            f"{skill}: {key} missing from reads_manifest"
        )


@pytest.mark.parametrize(
    "skill,fragment",
    [
        ("shenbi-worldbuilding", "genesis-context/world_rules.md"),
        ("shenbi-character-design", "genesis-context/chapter_outline.md"),
        ("shenbi-character-design", "genesis-context/three_act.md"),
        ("shenbi-story-architecture", "genesis-context/three_act.md"),
        ("shenbi-story-architecture", "genesis-context/plot_lines.md"),
        ("shenbi-story-architecture", "genesis-context/surface_conflict.md"),
        ("shenbi-story-architecture", "genesis-context/personal_conflict.md"),
        ("shenbi-story-architecture", "genesis-context/deep_conflict.md"),
        ("shenbi-faction-builder", "genesis-context/forces.md"),
        ("shenbi-volume-outlining", "genesis-context/chapter_outline.md"),
    ],
)
def test_genesis_fragment_declared(skill, fragment):
    """spec §3.3 T0/T1: contract-load face asserts the fragment path in reads."""
    from shenbi.contracts.loader import load_contract

    assert fragment in load_contract(skill)["reads"]


def test_genesis_fragments_optional_legacy_project(tmp_path: Path):
    """spec §1 缺文件语义: no fragments staged (USER-mode legacy) -> prompt
    assembles fine, no fragment keys, no failure."""
    for skill in (
        "shenbi-worldbuilding",
        "shenbi-character-design",
        "shenbi-story-architecture",
        "shenbi-faction-builder",
        "shenbi-volume-outlining",
    ):
        _, user_prompt, _, _ = _build_skill_prompt(
            skill=skill, project_dir=tmp_path, prompt="genesis", chapter=None
        )
        assert "genesis-context/" not in user_prompt
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_dispatch_reads_injection.py -k "genesis_fragment or genesis_fragments" -v`
Expected: FAIL（`expected fragment not injected` / `assert ... in reads` 不成立——尚未接线）

- [ ] **Step 3: 实施接线（四技能 frontmatter + 正文句）**

frontmatter `reads:` 追加（保持既有顺序，片段插在 novel.json 后）：

- worldbuilding：`+ - genesis-context/world_rules.md`
- story-architecture：`+ - genesis-context/three_act.md` `+ - genesis-context/plot_lines.md` `+ - genesis-context/surface_conflict.md` `+ - genesis-context/personal_conflict.md` `+ - genesis-context/deep_conflict.md`
- faction-builder：`+ - genesis-context/forces.md`
- volume-outlining：`+ - genesis-context/chapter_outline.md`

各技能 AUTO 段后加正文句（模板，`<片段列>` 按技能填）：

```markdown
**Seed 片段（genesis-context/）**：`<片段列>` 是人类伙伴 seed 原文的逐字片段（人类原始意向输入）。权威序：上游已产出 truth > seed 片段；冲突时以上游为准，若据此调整须在本技能产出文件内以「seed 意向与 truth 冲突的处理记录」小节披露（含一句理由）。
```

volume-outlining 额外加一句（spec T7 卷数偏好裁决）：「章节大纲节散文中的卷数偏好为软约束；`outline/volume_map.md` 为结构权威。」

- [ ] **Step 4: 再生成 + 测试**

Run: `uv run python -m shenbi.sync_contracts && uv run pytest tests/pipeline/test_dispatch_reads_injection.py -v && uv run pytest tests/unit/contracts -q`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-worldbuilding/SKILL.md skills/shenbi-story-architecture/SKILL.md skills/shenbi-faction-builder/SKILL.md skills/shenbi-volume-outlining/SKILL.md tests/pipeline/test_dispatch_reads_injection.py
# + 生成物（deps.json/docs/framework//docs/skills 以 git status 实况列名）
git commit -m "feat(contracts): spec69 T1——genesis-context 片段接入五 genesis 技能 reads"
```

---

### Task 3: 配角可选节（spec T2）+ 丰富版 seed 软约束锚点（spec §3.4 前半）

**Files:**
- Modify: `src/shenbi/pipeline/seed_parser.py:241`（genesis_context 字典加 supporting 键）
- Modify: `skills/shenbi-character-design/SKILL.md`（reads + supporting + 正文「点名角色不可漏」扩句）
- Test: `tests/unit/pipeline/test_seed_parser.py`（parse 面 + 丰富版锚点）、`tests/unit/pipeline/test_e2e.py`（init 写盘面）

**Interfaces:**
- Consumes: Task 1/2 的接线通道
- Produces: `SeedData.genesis_context["supporting"]: str`（空串 = 节缺席）；`genesis-context/supporting.md` 写盘（值非空时）

**复杂度:** infra（pipeline 模块）· **test_kind:** tdd_red_green · **层级:** T1（test_e2e 的 init 用例为 T1 级 CLI 单测，非 T2 链）

- [ ] **Step 1: 写失败测试**

`tests/unit/pipeline/test_seed_parser.py` 追加（沿用现有 tmp_path 写 seed 文件的风格）：

```python
class TestSupportingSection:
    """spec #69 T2: 配角设定 optional section."""

    def test_supporting_section_parsed(self, tmp_path):
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n"
            "## 配角设定\n- 阿萱：女主挚友，药庐传人\n\n## 主角设定\n- 名字: 测试\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert "阿萱" in data.genesis_context["supporting"]

    def test_supporting_section_absent_defaults_empty(self, tmp_path):
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n## 主角设定\n- 名字: 测试\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert data.genesis_context["supporting"] == ""


class TestRichSeedSoftBounds:
    """spec §3.4: 丰富软约束锚点——各节 < 32K、十节合计 < ~100K（字面量 seed，
    G0.9 先例 conftest.sample_seed_content；不落 tests/fixtures/）。"""

    RICH_SECTIONS = {
        "基本信息": "- 类型: 玄幻\n- 目标字数: 2000000\n- 目标章节数: 600\n",
        "主角设定": "- 测试主角 " * 200 + "\n",
        "配角设定": "- 测试配角 " * 100 + "\n",
        "世界观设定": "- 测试规则 " * 400 + "\n",
        "势力/组织": "- 测试势力 " * 200 + "\n",
        "核心冲突": "- 表层冲突: 测试\n- 个人冲突: 测试\n- 深层冲突: 测试\n",
        "情节线": "- 测试情节线 " * 200 + "\n",
        "章节大纲": "- 第1章 测试 " * 200 + "\n",
        "三幕结构": "- 第一幕 测试 " * 100 + "\n",
        "叙事技巧": "- 展示讲述比: 0.6\n",
    }

    def test_rich_seed_within_soft_bounds(self, tmp_path):
        body = "\n".join(f"## {h}\n{c}" for h, c in self.RICH_SECTIONS.items())
        seed = tmp_path / "seed.md"
        seed.write_text(f"# 丰富测试书\n\n{body}\n", encoding="utf-8")
        data = parse_seed(seed)
        fragments = {k: v for k, v in data.genesis_context.items() if v}
        assert len(fragments) == 10  # 十节全产出（含 supporting）
        for name, text in fragments.items():
            assert len(text) < 32000, name
        assert sum(len(t) for t in fragments.values()) < 100000
```

`tests/unit/pipeline/test_e2e.py` 的 init 用例后追加：

```python
def test_init_writes_supporting_fragment(
    self, tmp_path: Path, sample_seed_content: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec #69 T2: 配角设定节 -> genesis-context/supporting.md 写盘；缺省不写。"""
    seed_file = tmp_path / "seed.md"
    with_supporting = sample_seed_content + "\n## 配角设定\n- 阿萱：女主挚友\n"
    seed_file.write_text(with_supporting, encoding="utf-8")
    project_dir = tmp_path / "novel-a"
    main(["init", str(seed_file), "--project-dir", str(project_dir)])
    assert (project_dir / "genesis-context" / "supporting.md").exists()
    assert "阿萱" in (project_dir / "genesis-context" / "supporting.md").read_text(encoding="utf-8")

    seed_file2 = tmp_path / "seed2.md"
    seed_file2.write_text(sample_seed_content, encoding="utf-8")
    project_dir2 = tmp_path / "novel-b"
    main(["init", str(seed_file2), "--project-dir", str(project_dir2)])
    assert not (project_dir2 / "genesis-context" / "supporting.md").exists()


def test_init_writes_all_fragments_from_rich_seed(self, tmp_path: Path) -> None:
    """spec §3.4 后半: 丰富版 seed 经真实 init 写方断言十片段全部写盘
    （测试内字面量，G0.9 先例 sample_seed_content；不落 tests/fixtures/）。"""
    sections = [
        ("基本信息", "- 类型: 玄幻\n- 目标字数: 2000000\n"),
        ("主角设定", "- 测试主角 " * 200 + "\n"),
        ("配角设定", "- 测试配角 " * 100 + "\n"),
        ("世界观设定", "- 测试规则 " * 400 + "\n"),
        ("势力/组织", "- 测试势力 " * 200 + "\n"),
        ("核心冲突", "- 表层冲突: 测试\n- 个人冲突: 测试\n- 深层冲突: 测试\n"),
        ("情节线", "- 测试情节线 " * 200 + "\n"),
        ("章节大纲", "- 第1章 测试 " * 200 + "\n"),
        ("三幕结构", "- 第一幕 测试 " * 100 + "\n"),
        ("叙事技巧", "- 展示讲述比: 0.6\n"),
    ]
    body = "\n".join(f"## {h}\n{c}" for h, c in sections)
    seed_file = tmp_path / "rich-seed.md"
    seed_file.write_text(f"# 丰富测试书\n\n{body}\n", encoding="utf-8")
    project_dir = tmp_path / "novel-rich"
    main(["init", str(seed_file), "--project-dir", str(project_dir)])
    for name in (
        "protagonist",
        "supporting",
        "world_rules",
        "forces",
        "surface_conflict",
        "personal_conflict",
        "deep_conflict",
        "plot_lines",
        "chapter_outline",
        "three_act",
    ):
        assert (project_dir / "genesis-context" / f"{name}.md").exists(), name
```

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/pipeline/test_seed_parser.py -k "Supporting or RichSeed" -v && uv run pytest tests/unit/pipeline/test_e2e.py -k "supporting or rich_seed" -v`
Expected: FAIL（KeyError/无 supporting 键 / 9!=10 / 文件不存在——两命令分跑，`-k` 不跨文件共享）

- [ ] **Step 3: 最小实现**

`seed_parser.py` genesis_context 字典（:232-242）`"three_act"` 行后加：

```python
        "supporting": _extract_section(text, "Supporting Cast|配角设定|配角"),
```

`skills/shenbi-character-design/SKILL.md`：frontmatter reads 在 `genesis-context/three_act.md` 后加 `- genesis-context/supporting.md`；正文「点名角色不可漏」两处（:44-45 句与 :201-203 清单）各扩 supporting 一句：「seed `配角设定`（`genesis-context/supporting.md`）点名的配角同理不可漏」；权威序句的片段列补 supporting。

- [ ] **Step 4: 再生成 + 测试 + R3 再锁**

Run: `uv run python -m shenbi.sync_contracts && uv run pytest tests/unit/pipeline/test_seed_parser.py tests/unit/pipeline/test_e2e.py tests/pipeline/test_dispatch_reads_injection.py -q && bash tests/lock-tool-hashes.sh`
Expected: 全 PASS；deps.json `_tool_hashes` 的 seed_parser 条目更新

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/seed_parser.py skills/shenbi-character-design/SKILL.md tests/unit/pipeline/test_seed_parser.py tests/unit/pipeline/test_e2e.py tests/tiers/deps.json
# + 其余生成物按 git status 列名
git commit -m "feat(pipeline): spec69 T2——配角可选节解析 + supporting 片段接线 + 丰富软约束锚点"
```

---

### Task 4: 丢弃键 WARN（spec T3）

**Files:**
- Modify: `src/shenbi/pipeline/seed_parser.py`（Basic Info / Narrative 两解析循环各加 dropped 收集与一次汇总 WARN）
- Test: `tests/unit/pipeline/test_seed_parser.py`

**Interfaces:**
- Produces: structlog 事件 `seed_key_dropped`（字段 `section`/`keys`，一次汇总）

**复杂度:** infra · **test_kind:** tdd_red_green · **层级:** T1

- [ ] **Step 1: 写失败测试**

```python
class TestDroppedKeyWarning:
    """spec #69 T3: non-whitelist keys surface once via seed_key_dropped.

    structlog binds stderr (PrintLoggerFactory(sys.stderr)) — caplog CANNOT
    capture it; capsys must (precedent: tests/unit/pipeline/
    test_dispatch_skill_write_audit.py:281-292, 明文「caplog 捕不到 structlog，
    必须 capsys」)."""

    @staticmethod
    def _configure() -> None:
        from shenbi.logging import configure_logging

        configure_logging()

    def test_basic_info_unknown_key_warns(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n- 灵感来源: 某剧\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        err = capsys.readouterr().err
        assert err.count("seed_key_dropped") == 1  # 一次汇总，不逐键刷屏
        assert "灵感来源" in err

    def test_narrative_unknown_key_warns(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n"
            "## 叙事技巧\n- 展示讲述比: 0.6\n- 叙事人称: 第一人称\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        err = capsys.readouterr().err
        assert err.count("seed_key_dropped") == 1
        assert "叙事人称" in err

    def test_all_whitelisted_no_warning(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n## 叙事技巧\n- 展示讲述比: 0.6\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        assert "seed_key_dropped" not in capsys.readouterr().err
```

（capsys + 测试内 `configure_logging()` 照抄 test_dispatch_skill_write_audit.py:279-293 先例——structlog PrintLoggerFactory 直写 stderr，caplog 结构性不可用）

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/pipeline/test_seed_parser.py -k dropped -v` → FAIL（无事件）

- [ ] **Step 3: 最小实现**

Basic Info 循环（`parse_seed` 内）改为（Narrative 循环同构，section 名换）：

```python
    dropped_basic: list[str] = []
    for item in _parse_list_items(basic):
        kv = _split_key_value(item)
        if kv is None:
            continue
        key, value = kv
        key_norm = key.lower().replace(" ", "_")

        if key_norm in ("genre", "类型", "题材"):
            ...
        elif ...（既有分支不动）:
            ...
        else:
            dropped_basic.append(key)
    if dropped_basic:
        # spec #69 T3: surface silently-dropped seed keys once per section.
        log.warning("seed_key_dropped", section="Basic Info|基本信息", keys=dropped_basic)
```

- [ ] **Step 4: 测试 + R3 再锁**

Run: `uv run pytest tests/unit/pipeline/test_seed_parser.py -q && bash tests/lock-tool-hashes.sh`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/seed_parser.py tests/unit/pipeline/test_seed_parser.py tests/tiers/deps.json
git commit -m "feat(pipeline): spec69 T3——seed 非白名单键 seed_key_dropped WARN（每节一次汇总）"
```

---

### Task 5: G0.2 目标字数节锚定（spec T4）

**Files:**
- Modify: `src/shenbi/gates/g0.py:354-356`（G0.2 匹配域改为基本信息节优先）
- Test: `tests/unit/gates/test_g0.py`

**Interfaces:**
- Consumes: `shenbi.pipeline.seed_parser._extract_section(text, section_name) -> str`（函数内 lazy import，g6.py:70 先例同形）
- Produces: G0.2 匹配域 = 基本信息节；节缺席回退全文（legacy 兼容）

**复杂度:** infra（gates）· **test_kind:** tdd_red_green · **层级:** T1

- [ ] **Step 1: 写失败测试**

`tests/unit/gates/test_g0.py` 在 `TestG0ErrorPaths` 类（:137 起，`test_g02_*` 既有用例所在）之后新增 `TestG02` 类：

```python
from shenbi.status import GateStatus


class TestG02:
    """spec #69 T4: G0.2 目标字数基本信息节锚定。"""

    def test_g02_takes_basic_info_value_over_earlier_decoy(self, tmp_path: Path) -> None:
        """spec #69 T4: 正文他节先出现「目标字数：」时 G0.2 仍取基本信息节值。"""
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 世界观设定\n本系列目标字数：500 字的短篇集设定。\n\n"
            "## 基本信息\n- 类型: 玄幻\n- 目标字数: 1200000\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g02 = next(c for c in result["checks"] if c["id"] == "G0.2")
        assert g02["s"] == GateStatus.PASS  # StrEnum == JSON 串 "PASS"
        assert g02["target_words"] == 1200000

    def test_g02_falls_back_to_fulltext_when_section_absent(self, tmp_path: Path) -> None:
        """Legacy 兼容：基本信息节缺席时回退全文首匹配（现行行为保持）。"""
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 主角设定\n- 目标字数：800000\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G0(seed_file=str(seed)))
        g02 = next(c for c in result["checks"] if c["id"] == "G0.2")
        assert g02["s"] == GateStatus.PASS
        assert g02["target_words"] == 800000
```

（`gate_G0(seed_file, round_dir) -> str` 返回 JSON 字符串——用 test_g0.py:14-15 既有 `_result_dict`（json.loads）解包；`GateStatus` 已在代码块顶部 import，StrEnum 与 JSON 串比较成立）

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/gates/test_g0.py -k "g02_takes_basic_info_value_over_earlier_decoy or g02_falls_back_to_fulltext_when_section_absent" -v`
Expected: 第一测 FAIL（`assert 500 == 1200000`——G0.2 取到全文首匹配 500）；第二测 PASS（legacy 回退行为保持）

- [ ] **Step 3: 最小实现**

`g0.py` G0.2 段改为：

```python
    # G0.2 — target_words extraction (spec #69 T4: anchor to the Basic Info
    # section first so prose elsewhere can't shadow the declared value;
    # fall back to full text for section-less legacy seeds).
    from shenbi.pipeline.seed_parser import _extract_section

    basic = _extract_section(content, "Basic Info|基本信息")
    domain = basic if basic.strip() else content
    m = re.search(r"目标字数[：:]\s*(\d+)", domain)
```

（其后 fail/PASS 分支不动）

- [ ] **Step 4: 测试（新 + 既有 G0.2 全组）+ R3 再锁**

Run: `uv run pytest tests/unit/gates/test_g0.py -v && bash tests/lock-tool-hashes.sh`
Expected: 全 PASS（既有 :29-66 用例零回归）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g0.py tests/unit/gates/test_g0.py tests/tiers/deps.json
git commit -m "fix(gates): spec69 T4——G0.2 目标字数基本信息节锚定（lazy import seed_parser）"
```

---

### Task 6: F368 章节关闭清扫（spec T5）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_complete_chapter` :1463 起加清扫）+ `docs/superpowers/audit-runs/2026-08-15/c37-triage.md:27`（F368 行注记）
- Test: `tests/unit/pipeline/test_chapter_close_retry_sweep.py`（新建）

**Interfaces:**
- Consumes: `state.chapter_loop.retry_feedback: dict[str, str]`（键形 `f"ch{chapter}-{skill}"`，:956-958）
- Produces: 章节关闭时该章全部 retry_feedback 键清除（`_complete_chapter` 副作用——注意：此为既有状态推进函数内的既有模式，非 gate 检查器，幂等性约束不适用）

**复杂度:** infra（chapter_loop 状态机）· **test_kind:** regression_guard（成功即清已由 canary pop 落地并被 test_cli.py:1222/:1230 元测试钉住；本 task 为关闭时兜底清扫）· **层级:** T1

- [ ] **Step 1: 写失败测试**（`tests/unit/pipeline/test_chapter_close_retry_sweep.py` 新建，state 构造先例 `test_cost_report_auto.py:36-52`）：

```python
"""spec #69 T5 (F368 residual): chapter-close sweep of retry_feedback keys."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from shenbi.pipeline import chapter_loop
from shenbi.pipeline.state import PipelineState


def _state(tmp_path, retry_feedback: dict[str, str]):
    return SimpleNamespace(
        project_dir=str(tmp_path),
        chapter_loop=SimpleNamespace(
            chapter_states={},
            current_chapter=1,
            step_index=0,
            current_step="",
            per_chapter_review_enabled=False,
            retry_feedback=retry_feedback,
        ),
    )


def _run(tmp_path, state, chapter: int) -> None:
    import shenbi.pipeline.product_contracts as pc

    orig = pc.check_product_contracts
    pc.check_product_contracts = lambda pd: []
    try:
        with (
            patch.object(chapter_loop, "_check_world_file_freshness", return_value=None),
            patch.object(chapter_loop, "_print_timing_summary", return_value=None),
            patch.object(chapter_loop, "print_token_summary", return_value=None),
        ):
            chapter_loop._complete_chapter(cast(PipelineState, state), chapter)
    finally:
        pc.check_product_contracts = orig


def test_chapter_close_clears_all_chapter_keys(tmp_path):
    """失败→遗留（含 legacy 键形）→ 章节关闭 → 该章全部键消失。"""
    state = _state(
        tmp_path,
        {
            "ch1-shenbi-review-resonance": "fb",
            "ch1-shenbi-chapter-drafting": "fb2",  # legacy 键形（:1197 同构）
            "ch10-shenbi-review-resonance": "keep",
        },
    )
    _run(tmp_path, state, 1)
    assert "ch1-shenbi-review-resonance" not in state.chapter_loop.retry_feedback
    assert "ch1-shenbi-chapter-drafting" not in state.chapter_loop.retry_feedback


def test_chapter_close_does_not_touch_other_chapters(tmp_path):
    """dash 终结使 ch1- 前缀不误伤 ch10-*（spec §2 T5.1 安全性）。"""
    state = _state(tmp_path, {"ch10-shenbi-review-resonance": "keep", "ch2-x": "keep2"})
    _run(tmp_path, state, 1)
    assert state.chapter_loop.retry_feedback == {
        "ch10-shenbi-review-resonance": "keep",
        "ch2-x": "keep2",
    }
```

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/pipeline/test_chapter_close_retry_sweep.py -v` → 第一测 FAIL（键残留）

- [ ] **Step 3: 最小实现**

`_complete_chapter` 内、`cs.status = ChapterStatus.COMPLETE` 之后加：

```python
    # F368 residual (spec #69 T5): chapter-close sweep — a finished chapter's
    # corrective feedback must not leak into later dispatch cycles. The dash
    # terminator in _retry_key scopes the prefix (ch1- never matches ch10-).
    prefix = f"ch{chapter}-"
    for stale in [k for k in state.chapter_loop.retry_feedback if k.startswith(prefix)]:
        state.chapter_loop.retry_feedback.pop(stale)
```

`docs/superpowers/audit-runs/2026-08-15/c37-triage.md:27` F368 行注记列追加：「成功即清已由 probe23 #18-4 与 canary pop 落地（chapter_loop.py:3276/:3477），残余=章节关闭清扫，随 spec #69 T5 closed」

- [ ] **Step 4: 测试 + R3 再锁**

Run: `uv run pytest tests/unit/pipeline/test_chapter_close_retry_sweep.py tests/unit/pipeline/test_cost_report_auto.py -q && bash tests/lock-tool-hashes.sh`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_close_retry_sweep.py docs/superpowers/audit-runs/2026-08-15/c37-triage.md tests/tiers/deps.json
git commit -m "fix(pipeline): spec69 T5——F368 残余章节关闭清扫 + c37-triage 行更新"
```

---

### Task 7: NovelConfig 删除（spec T6）

**Files:**
- Delete: `src/shenbi/contracts/schemas/novel.py`
- Regen: `uv run python -m shenbi.sync_contracts`（若 index/生成物涉及）

**Interfaces:** 无消费者（零导入者已验证：src/tests/tools 仅自身命中；schemas/__init__ 无 re-export）

**复杂度:** infra（contracts）· **test_kind:** characterization（删除后全量回归确认零依赖）· **层级:** T1

- [ ] **Step 1: 删除 + 验证**

```bash
git rm src/shenbi/contracts/schemas/novel.py
grep -r NovelConfig --include='*.py' src/ tests/ tools/ ; echo "exit=$?"
```
Expected: grep 空输出 exit=1（spec §3.3 T6 验收面；docs/spec 历史引用不阻碍——append-only）

- [ ] **Step 2: 全量回归**

Run: `uv run python -m shenbi.sync_contracts && uv run pytest tests/unit/contracts -q && uv run pytest tests/ -q -x --ignore=tests/tiers 2>/dev/null | tail -3`
Expected: 零 ImportError / 零 NovelConfig 引用失败

- [ ] **Step 3: R3 再锁 + Commit**

```bash
bash tests/lock-tool-hashes.sh   # 死条目随 rglob 全量重写清除
git add src/shenbi/contracts/schemas/novel.py tests/tiers/deps.json
git commit -m "chore(contracts): spec69 T6——删除零导入者 NovelConfig 死 schema（F240 执行）"
```

（`git rm` 已暂存删除；再锁后 deps.json 一并提交）

---

### Task 8: 文档收口（spec T7 + §3.6 挂账闭合）

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/c37-triage.md:44`（F886 行 closed 注 spec #69）
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md:571`（F886 行状态注 spec #69 执行）
- Modify: `src/shenbi/pipeline/cli.py:834-837`（F886 注释改写）→ **触发 R3 再锁**
- 核对: `docs/getting-started/first-novel.md`（预期空操作）

**Interfaces:** 无代码接口；纯文档 + 注释

**复杂度:** leaf（文档）· **test_kind:** 不适用（文档核对）· **层级:** —

- [ ] **Step 1: 台账与注释**

c37-triage F886 行状态列 `defer` → `closed (spec #69)`，注记列追加「seed 内容流恢复随 spec #69 落地（genesis 五技能 reads 接线）」；findings-ledger F886 行状态 cell 追加 `→ executed (spec #69)`。cli.py 注释块改为：

```python
    # Persist each genesis section as its own prompt fragment. Since spec #69
    # these are consumed: the five genesis skills declare the fragment paths
    # in their contract reads (worldbuilding/character-design/
    # story-architecture/faction-builder/volume-outlining) — see
    # truth-files.yaml globs + skills/*/SKILL.md.
```

- [ ] **Step 2: first-novel.md 核对**

Run: `grep -n "4\.3\|疲劳词\|每章目标字数\|canon" docs/getting-started/first-novel.md`
Expected: 无 4.3 失真表述（空或无关命中）——结果记入 commit message；T7 六项裁决权威记录 = spec §2 T7（随归档长期可查）

- [ ] **Step 3: R3 再锁 + Commit**

```bash
bash tests/lock-tool-hashes.sh
git add docs/superpowers/audit-runs/2026-08-15/c37-triage.md docs/superpowers/audit-runs/2026-08-15/findings-ledger.md src/shenbi/pipeline/cli.py tests/tiers/deps.json
git commit -m "docs(spec): spec69 T7/挂账闭合——F886/F368 台账 closed + cli 注释改写 + first-novel 核对(空操作)"
```

---

### Task 9: G5 delta 验收测试 + 终锁 + just check 收口（spec §3.1/§3.2）

**Files:**
- Test: `tests/unit/gates/test_g5.py`（追加 genesis-context delta 组）

**Interfaces:**
- Consumes: `shenbi.gates.g5.gate_G5(phase_name, round_dir, project_dir)`（gates/cli.py:197 调用形）+ `tests/tiers/deps.json` prereqs

**复杂度:** infra（gates 测试面）· **test_kind:** regression_guard（delta 钉死）· **层级:** T1

- [ ] **Step 1: 写 delta 断言测试**（追加到 test_g5.py；按该文件既有 gate_G5 调用形对齐）：

```python
GENESIS_CTX_TARGET_PAIRS = {
    ("shenbi-power-system", "shenbi-faction-builder"),
    ("shenbi-location-builder", "shenbi-character-design"),
    ("shenbi-relationship-map", "shenbi-story-architecture"),
    ("shenbi-story-architecture", "shenbi-volume-outlining"),
}


class TestGenesisContextDelta:
    """spec #69 §3.2: G5.2 delta 钉死——新 missing 键恰为 genesis-context/*.md，
    genesis 相恰四对 + architecture 相 spillover 一对，无其他波及。pair 源 =
    deps.json prerequisites（非 GENESIS_STEPS）。gate_G5 返回 JSON 串，
    以 test_g5.py:14 同款 json.loads 解包。"""

    @pytest.mark.parametrize(
        "phase,target_pairs",
        [
            ("genesis", GENESIS_CTX_TARGET_PAIRS),
            ("architecture", {("shenbi-story-architecture", "shenbi-volume-outlining")}),
        ],
    )
    def test_delta_is_exactly_target_pairs(self, tmp_path, phase, target_pairs):
        result = json.loads(gate_G5(phase_name=phase, round_dir=None, project_dir=tmp_path))
        g52 = [c for c in result["checks"] if c.get("id") == "G5.2"]
        hit = {
            tuple(c["pair"].split("->"))
            for c in g52
            if "genesis-context/*.md" in c.get("missing", [])
        }
        assert hit == target_pairs
```

- [ ] **Step 2: 跑测试**（T1-T2 已落地，此为验收钉死——预期直接 PASS；若 FAIL 说明接线面与 delta 预测不符，回查）

Run: `uv run pytest tests/unit/gates/test_g5.py -k TestGenesisContextDelta -v`
Expected: 接线落地后 PASS ×2；执行前（现状）RED——`hit == set()` ≠ target_pairs

- [ ] **Step 2b: gate_G5 直跑取证（progress.md 验收证据用）**

```bash
uv run python -c "
import json, tempfile
from shenbi.gates.g5 import gate_G5
with tempfile.TemporaryDirectory() as td:
    r = json.loads(gate_G5(phase_name='genesis', round_dir=None, project_dir=td))
pairs = sorted(
    c['pair'] for c in r['checks']
    if c.get('id') == 'G5.2' and 'genesis-context/*.md' in c.get('missing', [])
)
n_missing = sum(len(c.get('missing', [])) for c in r['checks'] if c.get('id') == 'G5.2')
print('genesis-context pairs:', pairs)
print('genesis phase total missing keys:', n_missing)
"
```
Expected（接线后）：pairs 恰四对（power-system→faction-builder / location-builder→character-design / relationship-map→story-architecture / story-architecture→volume-outlining）；total missing = 30（baseline 26 + 4）

- [ ] **Step 3: 终锁 + just check**

```bash
bash tests/lock-tool-hashes.sh
just check
```
Expected: `All checks passed!` EXIT=0（含 G5/g5 测试、契约 lint、R3 面全绿）

- [ ] **Step 4: Commit**

```bash
git add tests/unit/gates/test_g5.py tests/tiers/deps.json
git commit -m "test(gates): spec69 §3.2——G5.2 genesis-context delta 钉死（四对+spillover）"
```

---

## Self-Review 结论

1. **Spec coverage**：§2 T0→Task 1、T1→Task 2、T2→Task 3、T3→Task 4、T4→Task 5、T5→Task 6、T6→Task 7、T7+§3.6→Task 8、§3.1/§3.2→Task 9、§3.4 前半→Task 3（丰富锚点 + 十片段 init 写盘）、后半（人工探针）= 交付后用户动作不入 plan、§3.7 = 交付后动作。§1 全部机制约束（globs 加法/缺文件语义/权威序句/截断事实/R3 再锁）逐条落在对应 task。无缺口。
2. **Placeholder scan**：无 TBD/「适当处理」类占位；所有代码步骤给出实际代码。
3. **Type consistency**：`genesis_context["supporting"]`（Task 3 产 / Task 3 测消费）；`seed_key_dropped` 事件名 Task 4 产测一致；`_extract_section` 签名（Task 5 消费 = seed_parser 现签名）；retry 键形 Task 6 测试与 `_retry_key` 现实现一致；`_build_skill_prompt` 四元组第四位 = `reads_manifest`（Task 2 断言消费）。

## 已裁决偏离（Plan 审查轮 1 修复记录 · 2026-10-13）

- **C1 修复**：Task 4 测试机制从 caplog 改为 capsys + 测试内 `configure_logging()`（structlog PrintLoggerFactory 直写 stderr，caplog 结构性不可用——先例 test_dispatch_skill_write_audit.py:281-292；spec §3.3 T3 的「caplog 断言」措辞本身有误，plan 以代码级正确形态为准）
- **I1 修复**：Task 5/9 测试经 `_result_dict`/`json.loads` 解包 gate 的 JSON 字符串返回（gate_G0 -> str、gate_G5 -> str）+ `GateStatus` 显式 import（StrEnum == JSON 串成立）
- **I2 修复**：`-k` 选择器钉正（`character-design` 连字符形态 / `TestGenesisContextDelta` 类名 / 两测全名）
- **I3 修复**：Task 2 注入测试补 reads_manifest 第四返回值断言（spec §3.3 三要素闭合）
- **M1 修复**：Task 3 Step 2 双 `-k` 拆两条命令；**M3 修复**：Task 9 补 Step 2b gate_G5 直跑取证；**M4 修复**：Task 3 补 `test_init_writes_all_fragments_from_rich_seed`（十片段写盘）
- **M2 已裁决偏离（显式记录）**：spec T5.3 字面两测（「失败→重试→成功→键消失；章节关闭→该章全部键消失」）中第一测的功能面由既有元测试 test_cli.py:1222/:1230（源码断言 `retry_feedback.pop` 在两站点）代理 + Task 6 关闭兜底清扫测试覆盖键生命周期闭合；理由：成功即清（probe23 #18-4/canary pop）已落地且被钉住，本 task 的增量是关闭清扫。**M5 已裁决**：rich_seed 各节 1-2K 远离 32K/100K 边界——锚点目的是「软约束可表达」非截断回归检测（截断在 dispatch 层，属 Task 2 组装测试面之外、交付后探针观测项）
