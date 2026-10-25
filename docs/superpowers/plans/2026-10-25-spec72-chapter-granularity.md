# Spec #72 平台章粒度改革 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成管线从 7600 字/1316 章改为 3200 字原生章（~3125 章）：双章 bundle 派发、staging 簇 + `===CH:n===`/`<!--SCENE-->` 标记、确定性拆分步 `pipeline-scene-split`、G4 场景/钩校验扩展、修订后重验、release_split v2 声明式切分、地板/天花板/口径统一。

**Architecture:** 场景标记耐久化于终稿章文件（无 sidecar，覆写总设计 §2.2 显式声明）；拆分器 `scene_splitter` 是标记谓词/解析/打包的单源模块，被 chapter_loop 新步、G4.cd/G4.cp、release_split v2 三方消费；planning 备忘新增场景预算两型声明（G4.cp 预检可打包性）；审计按簇派发报告保持逐章。

**Tech Stack:** Python 3.11+ / pydantic（契约）/ pytest（构造输入 G0.9 结构性豁免）/ 既有 pipeline 基建（staging/checkpoint/manifest/parallel_dispatch）。

## Global Constraints（spec rev5.2 逐字约束——每个 task 隐含包含）

- `chapter_word`: **default=3200, min=2800, max=4000**（total_chars_md_text 口径）；`fanqie_update: {min: 1800, max: 2800}`（`chapter_word` 子键）；顶层新键 `primary_platform: "qidian"`（枚举 qidian|fanqie，**optional**，缺席回退 v1 默认 fanqie）
- `novel.json`: `target_total_chapters` 1400→**3300**（保量：0.95×3200=3040 ≥ 10M/3300≈3030.3）；`total_chapters` 不手改
- 字数带校验一律 `total_chars_md_text` 口径 + 剥标记行；`chapter_word_floor()` 改读 **min**，回退链 **min→default→CHAPTER_WORD_FLOOR(3000)**
- 场景两型域：独立型 **[1800,2000]** ∪ 配对型 **[900,1400]**；灰域 [1400,1800) 熔断；2 场景章=两独立型；3 场景章=三配对型（和≥2800）或一独两配
- 标记谓词单源：`line.strip() == "<!--SCENE-->"`；CH 标记 `^===CH:(\d+)===$`（仅 staging 簇）
- 新步名 **`pipeline-scene-split`**；`PIPELINE_STEPS_VERSION` 2→**3**
- 已收束（v2 打包域）：manifest `gates.chapter_loop.<ch>.<skill>.<gate>` 每键 **latest record == PASS** 且该章 **`pipeline-scene-split` G4 键存在**（follower 章无 drafting 键属预期不排除）；`--through` 收窄不豁免
- G0.9：测试输入 = tmp_path 构造（结构性豁免）；**禁改 `tests/fixtures/` 仓库文件**；禁真实 dispatch（F947 全离线）
- 框架纪律：structlog 非 print / pathlib / gate 检查器纯函数幂等 / conventional commits / 状态字面量 enums.py 单源（拆分失败=既有 `FailureClass.DETERMINISTIC_GATE`）
- 存量隔离：不对 `novel-xinghuo-vol1` 现存 10 章跑 G2/G4/G6；每 task commit 后产 `.superpowers/sdd/audit-T<N>.md`

---

### Task 1: 常量与契约配置面（genre-config 四站 + novel.json）

**复杂度: infra**（契约 schema 变更）· **test_kind: tdd_red_green**

**Files:**
- Modify: `novel-xinghuo-vol1/genre-config.json`（chapter_word 块 + 新子键）
- Modify: `novel-xinghuo-vol1/novel.json:8`（target_total_chapters）
- Modify: `src/shenbi/contracts/ownership.py:39-52`（GENRE_KEYS + primary_platform）
- Modify: `src/shenbi/contracts/skills/genre_config.py:21-22,45-64`（_OPTIONAL_TOP_KEYS + GenreConfig 字段）
- Modify: `skills/shenbi-genre-config/SKILL.md:122-126`（模板）、`:317`、`:323`、`:416`（闭键集行）
- Test: `tests/unit/contracts/test_genre_config_platform.py`（新建）

**Interfaces:**
- Produces: `GenreConfig.primary_platform: str = ""`（optional，空=未声明）；`GenreConfig.chapter_word` 保持 `dict[str, Any]`（`fanqie_update` 子键免建模）；GENRE_KEYS 含 `primary_platform`（11 键）
- Produces: 项目面常量（3200/2800/4000/1800/2800/qidian/3300）——T2/T3/T8 全部读配置，不硬编码

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/contracts/test_genre_config_platform.py
"""spec #72 T1: primary_platform optional top-level key + fanqie_update sub-block."""
import pytest
from shenbi.contracts.skills.genre_config import GenreConfig
from shenbi.contracts.ownership import GENRE_KEYS

def _base() -> dict:
    return {
        "approval": {"decision": "approved"},
        "auditDimensions": {},
        "chapterTypes": {},
        "customRules": [],
        "fatigueWords": {"禁用": []},
        "pacing": {},
        "updated": "",
        "version": "1",
        "chapter_word": {"default": 3200, "min": 2800, "max": 4000,
                         "fanqie_update": {"min": 1800, "max": 2800}},
    }

@pytest.mark.unit
def test_primary_platform_in_genre_keys() -> None:
    assert "primary_platform" in GENRE_KEYS
    assert len(GENRE_KEYS) == 11

@pytest.mark.unit
def test_optional_key_absent_still_valid() -> None:
    cfg = GenreConfig.model_validate(_base())
    assert cfg.primary_platform == ""

@pytest.mark.unit
def test_primary_platform_enum() -> None:
    data = _base() | {"primary_platform": "qidian"}
    assert GenreConfig.model_validate(data).primary_platform == "qidian"
    with pytest.raises(Exception):
        GenreConfig.model_validate(_base() | {"primary_platform": "zongheng"})

@pytest.mark.unit
def test_fanqie_update_subkey_unmodelled_passes() -> None:
    # chapter_word 子键不受顶层闭键集约束（spec 施工面 1）
    GenreConfig.model_validate(_base())  # fanqie_update 已在 _base 的 chapter_word 内

@pytest.mark.unit
def test_unknown_top_level_key_rejected() -> None:
    with pytest.raises(Exception):
        GenreConfig.model_validate(_base() | {"platforms": {}})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/contracts/test_genre_config_platform.py -v`
Expected: FAIL（GENRE_KEYS 10 键 / 无 primary_platform 字段）

- [ ] **Step 3: 实现**

`ownership.py` GENRE_KEYS 增 `"primary_platform",`（注释行同步「真实 11 顶层键」）。`genre_config.py`：
```python
_OPTIONAL_TOP_KEYS = frozenset({"tropeInventory", "chapter_word", "primary_platform"})
# ...
class GenreConfig(BaseModel):
    # ... 既有字段后增：
    primary_platform: str = ""  # spec #72: qidian|fanqie; "" = undeclared (legacy)

    @field_validator("primary_platform")
    @classmethod
    def _platform_enum(cls, v: str) -> str:
        if v and v not in {"qidian", "fanqie"}:
            raise ValueError(f"primary_platform must be qidian|fanqie, got '{v}'")
        return v
```
（`_REQUIRED_TOP_KEYS` 由 GENRE_KEYS − _OPTIONAL_TOP_KEYS 派生，自动维持 8 必填。）

`novel-xinghuo-vol1/genre-config.json` chapter_word 块整体替换：
```json
"chapter_word": {
  "default": 3200,
  "min": 2800,
  "max": 4000,
  "fanqie_update": { "min": 1800, "max": 2800 },
  "note": "每章目标字数（total_chars 口径，剥 SCENE 标记行）。#72 双平台：起点粒度原生生成（primary_platform=qidian，2800-4000 带，default=3200）；番茄发布层以场景为原子组更（fanqie_update 1800-2800，见 release_split v2）。1800 更下限为 #72 用户决策（旧检索口径的 2000 红线系 2200 单档时代，双平台决策取代）。章数数学：ceil(10000000/3200)=3125；保量校验 default×0.95=3040 ≥ target/target_total_chapters=10000000/3300≈3030.3（分母=预算章数 3300，允许 5.6% 余量，同旧 1400 vs 1316 口径）。G2/G4 每章硬地板读 min（2800），天花板读 max（4000）；G0.3 ceil / volume_budget implied / G6.1 期望读 default。"
}
```
顶层增 `"primary_platform": "qidian",`。`novel-xinghuo-vol1/novel.json` 的 `"target_total_chapters": 1400` → `3300`（`total_chapters: 1316` 不动——volume-budget `--apply` 通道，重排归 #74）。

`skills/shenbi-genre-config/SKILL.md`：模板 chapter_word 块 :122-126 数值改 3200/2800/4000 + fanqie_update 子键 + note 按上段口径重写；`:317`/`:323` 「9 必填（含 tropeInventory）」订正为「8 必填（tropeInventory/chapter_word/primary_platform 可选）」；`:416` 「顶层仅十键」→「顶层仅十一键」并补 `primary_platform` 行。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/contracts/test_genre_config_platform.py -v`
Expected: 5 PASS

- [ ] **Step 5: 既有面回归 + 提交**

Run: `uv run pytest tests/unit/contracts/ -q && just lint-contracts`
Expected: 全绿（fixture 无 primary_platform → optional 不破）。现有断言 GENRE_KEYS 键数的测试若有（grep `GENRE_KEYS` tests/）同步期望值。
Commit: `feat(contracts): spec72 T1——primary_platform 可选键四站落地 + 项目面 3200/3300 常量`

---

### Task 2: 地板/天花板/口径统一（gates 三站点 + loop 边界 + 消息字符串）

**复杂度: infra** · **test_kind: tdd_red_green（新语义）+ characterization（既有断言更新）**

**Files:**
- Modify: `src/shenbi/gates/shared.py:130-152`（chapter_word_floor）
- Modify: `src/shenbi/gates/g2.py:185-218`（G2.6/G2.7 口径与键）
- Modify: `src/shenbi/gates/g4/length_normalizing.py:44,70-75`
- Modify: `src/shenbi/pipeline/chapter_loop.py:1379-1406`（_check_word_count_bounds）、`:754-758`（消息）
- Modify: `src/shenbi/pipeline/volume_budget.py:303-318`（word_floor min）、`:316-317`（消息）
- Test: `tests/unit/gates/test_word_band_unified.py`（新建）；更新既有地板断言用例（grep 定位）

**Interfaces:**
- Consumes: T1 项目面配置
- Produces: `chapter_word_floor(project_dir) -> int`（min 回退链）；`chapter_word_min_max` 不变；G2.7 天花板 = `chapter_word_max(project_dir)`（新薄封装或直接 `chapter_word_min_max()[1]`，缺省回退 `CHAPTER_WORD_CEILING` 既有常量）
- Produces: `strip_scene_markers(text: str) -> str`（T3 提供后被本 task 的口径消费——**实现顺序上本 task 先落 min/total_chars 切换，标记剥离在 T3 接线**；本 task 的测试输入不含标记行）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/gates/test_word_band_unified.py
"""spec #72 T2: floor=min / ceiling=max / total_chars 口径 四联一致性."""
import json
from pathlib import Path

from shenbi.gates.shared import chapter_word_floor, total_chars_md_text


def _project(tmp_path: Path, cw: dict) -> Path:
    (tmp_path / "genre-config.json").write_text(
        json.dumps({"chapter_word": cw}), encoding="utf-8")
    return tmp_path


def _chapter(tmp_path: Path, n: int, chars: int) -> Path:
    # 构造 n 个全角字符段（total_chars 口径 = 非空白字符数）
    p = tmp_path / f"chapter-{n}.md"
    body = "灯" * chars
    p.write_text(f"# 第{n}章：题\n\n{body}\n", encoding="utf-8")
    return p
```
用例（各自独立 test）：`floor_reads_min`（cw default=3200/min=2800 → floor==2800）；`floor_fallback_default`（无 min → 3200）；`floor_fallback_constant`（无 chapter_word → 3000）；G2 四联——构造 2800/2799/4000/4001 total_chars 章，`g2_chapter_check`（或对应入口，实现时按 `g2.py` 的公开函数名）在 2800/4000 过、2799/4001 挂 G2.6/G2.7（期望消息含 `>= 2800` / `<= 4000`）；G4.ln 同带（构造归一化报告章，2800 过 / 2799 挂 `G4.ln.below_floor` / 4001 挂 `above_ceiling`）。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/test_word_band_unified.py -v`
Expected: FAIL（floor 返回 default=3200；G2.7 ceiling 4500/10000）

- [ ] **Step 3: 实现**

`shared.py`：
```python
def chapter_word_floor(project_dir: str | Path | None) -> int:
    """Per-chapter hard floor = genre-config ``chapter_word.min`` (spec #72
    口径统一: band lower edge). Fallback chain min -> default -> constant."""
    cw = _chapter_word_block(project_dir)  # 既有读取逻辑提取/复用
    for key in ("min", "default"):
        v = cw.get(key) if cw else None
        try:
            if v and int(v) > 0:
                return int(v)
        except (TypeError, ValueError):
            continue
    return CHAPTER_WORD_FLOOR
```
`g2.py`（G2.6/G2.7 段）：`wc = word_count_md(p)` → `wc = total_chars_md_text(content)`（读取行随之上移）；`ceiling = CHAPTER_WORD_CEILING if is_important else ...` → `_mn, mx = chapter_word_min_max(project_dir); ceiling = mx if mx else CHAPTER_WORD_CEILING`（`_is_important_chapter` 双档与 `CHAPTER_WORD_CEILING` 常量降级为缺省回退；docstring 注明 #72 大章退役）。`length_normalizing.py:44` `word_count_md(pf)` → `total_chars_md_text(content)`；:70-75 的 floor 已来自 `chapter_word_floor`（自动随 min）。`_check_word_count_bounds`：计数行改 `total_chars_md_text(chapter_text)`。两处消息字符串：volume_budget.py:316-317 `chapter_word.default` → `chapter_word.min`（变量 `word_default` → `word_floor`，取值改 `chapter_word_floor`）；chapter_loop.py:756 「地板值 = genre-config chapter_word.default」→「地板值 = genre-config chapter_word.min」。

- [ ] **Step 4: 全量跑 + 既有断言更新**

Run: `uv run pytest tests/unit/gates/ tests/unit/pipeline/ -q`
既有断言更新（characterization，期望值从配置语义重推，禁改 fixture 文件）：probe17/chapter-118 快照相关地板断言（floor 现= min 值）；G2.6 CJK 口径用例。Expected: 全绿。
Run: `uv run pytest tests/unit/tools/test_release_split.py -q`（v1 尚未动——38 用例须仍绿，floor/min_max 消费未变其行为）。

- [ ] **Step 5: 提交**

`feat(gates): spec72 T2——地板=min 天花板=max 口径统一 total_chars（G2.6/2.7/G4.ln/loop 边界/两处消息）`

---

### Task 3: scene_splitter 模块（标记谓词单源 + 拆分/校验/打包）

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Create: `src/shenbi/pipeline/scene_splitter.py`
- Test: `tests/unit/pipeline/test_scene_splitter.py`（新建）

**Interfaces:**
- Produces:
```python
SCENE_MARKER = "<!--SCENE-->"
CH_MARKER_RE: re.Pattern[str]            # ^===CH:(\d+)===$
def is_scene_marker_line(line: str) -> bool   # line.strip() == SCENE_MARKER
def strip_scene_markers(text: str) -> str     # 删独占标记行
def count_scene_markers(text: str) -> int
def chapter_total_chars(text: str) -> int     # total_chars_md_text(strip_scene_markers(text))——不带 META 的裸口径，与 G4.cd 终验同式
@dataclass(frozen=True)
class SceneSpan: index: int; size: int; last_line: str   # last_line=末非空行原文
@dataclass(frozen=True)
class SplitChapter: number: int; title: str; body: str; scenes: tuple[SceneSpan, ...]
@dataclass(frozen=True)
class BundleChapters: chapters: tuple[SplitChapter, ...]   # 1-2 章
def parse_scene_declarations(memo_text: str) -> list[tuple[int, int, str, str]]
    # [(场景序号, 字数, 型别"独立型"|"配对型", 钩原文), ...]；空表=备忘无场景块
def split_bundle(bundle_text: str) -> BundleChapters      # SceneSplitError = 标记缺失/格式坏
def validate_split(ch: SplitChapter, band: tuple[int, int]) -> list[str]
    # 违规清单：字数带/场景数<2/灰域/组合约束（2 场景须两独；3 场景须 3 配或 1+2 配且和∈带）
def pack_scenes(sizes: list[int], update_band: tuple[int, int]) -> list[list[int]] | None
    # 贪心组相邻场景：每组和∈update_band；不可打包→None（单源，G4.cp 预检与 v2 共用）
class SceneSplitError(RuntimeError)
```
- Consumes: `shenbi.gates.shared.total_chars_md_text`

- [ ] **Step 1: 写失败测试**（tmp_path 构造，G0.9 结构豁免）

构造 bundle 文本 fixture 构造器（测试内 inline）：
```python
def _bundle(n1: int, n2: int | None, scenes: dict[int, list[int]]) -> str:
    parts = []
    for n in ([n1, n2] if n2 else [n1]):
        parts.append(f"===CH:{n}===\n# 第{n}章\n# {TITLES[n]}\n\n## PRE_WRITE_CHECK\n\n- x\n\n<!--SCENE-->\n\n" )
        # 每场景：size 个「灯」+ 末行钩原文，场景间 <!--SCENE-->
        ...
    return "\n".join(parts)
```
用例：`split_two_chapters`（双章、标记剥离 CH 保留 SCENE、title=第二 H1）；`missing_ch_marker_raises`；`scene_count_below_two`；`gray_zone_scene_1450`；`band_2799_and_2800`（chapter_total_chars 口径）；`composition_2scene_must_be_2A`（2 场景 2×1300 → 组合违例）；`pack_scenes_pairs_in_band`（[950,950]→[[950,950]]）；`pack_scenes_cross_2800_none`（[950,1950]→None）；`pack_scenes_greedy_multi`；`parse_scene_declarations_roundtrip`（`- 场景1: 1900字｜独立型｜收束钩：abc。`）。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_scene_splitter.py -v` → ModuleNotFoundError

- [ ] **Step 3: 实现 scene_splitter.py**

要点（实现体）：CH 段切分按 `CH_MARKER_RE` 全行匹配；每章段提取第二 H1 为题（章内 H1 全部从正文剥除——对齐 release_split v1 语义）；`<!--SCENE-->` 行保留于 `body`、剥除后计 size/last_line；`validate_split` 组合约束按 Global Constraints；`pack_scenes` 贪心：顺扫 sizes，当前组和 < update_band[0] 则继续吸收；吸收后 > update_band[1] 则先尝试关组（组内 ≥min 才关，否则失败 None）；单场景 > max 直接 None。`parse_scene_declarations` regex：`^-\s*场景(\d+):\s*(\d+)字｜(独立型|配对型)｜收束钩：(.+?)\s*$`（MULTILINE）。全程 pathlib/无 print/纯函数（读文本入参，不落盘——落盘在 T4 步进器）。

- [ ] **Step 4: 跑测试确认通过 + 提交**

Run: `uv run pytest tests/unit/pipeline/test_scene_splitter.py -v` → 全 PASS
Commit: `feat(pipeline): spec72 T3——scene_splitter 单源模块（标记谓词/拆分/两型域校验/贪心打包/备忘场景声明解析）`

---

### Task 4: chapter_loop 双章 bundle 步进 + pipeline-scene-split 步

**复杂度: infra（协调者亲自实现）** · **test_kind: tdd_red_green（T2 集成面）**

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`：CHAPTER_STEPS（:143-264）、PIPELINE_STEPS_VERSION（:277-282）、`_resolve_g4_files`（:1026-1067）、staging 提交批次（CHAPTER_MEMO checkpoint 处）、post-draft 内联块（:3731-3744）、游标推进（:1536 邻域）
- Modify: `tests/pipeline/test_resume_anchor.py:95-112`（快照）
- Test: `tests/pipeline/test_bundle_stepping.py`（新建，T2 层）

**Interfaces:**
- Consumes: T3 `scene_splitter` 全 API；T2 floor/口径
- Produces: CHAPTER_STEPS 16 步（step 4 后插 `pipeline-scene-split`）；`_bundle_chapters(project_dir, chapter) -> list[int]`（1-2 章，卷界 singleton：`parse_volume_spans` 判 chapter+1 是否越当前卷 end）；拆分步执行函数 `_run_scene_split_step(project_dir, chapters) -> None`（拆分+晋升 decisions+逐章 G4.cd 终验+manifest 按章记录）；`PIPELINE_STEPS_VERSION = 3`

- [ ] **Step 1: 写失败测试**

`tests/pipeline/test_bundle_stepping.py`（tmp_path 项目布局构造：genre-config（3200 带）/novel.json/outline/volume_map.md（含 `## 卷一（第 1-4 章）` 头）/staging bundle 双章 2800+3100 字带标记与双 H1/PRE/POST/双 decisions sidecar）：
- `test_steps_version_3_and_16_skills`：`PIPELINE_STEPS_VERSION == 3`；skill 元组 = 既有 15 + `"pipeline-scene-split"`（插在 shenbi-chapter-drafting 后）
- `test_split_step_promotes_both_chapters`：跑 `_run_scene_split_step` → `chapters/chapter-{N,N+1}.md` 存在（CH 剥除/SCENE 保留/双 H1 在）、decisions 两份晋升、`staging/` 簇被 commit（clear 后 chapters/ 内文件在）
- `test_manifest_records_per_chapter`：manifest `gates.chapter_loop` 下 N 与 N+1 各有 `pipeline-scene-split` 键
- `test_bundle_atomic_and_singleton_at_volume_end`：`_bundle_chapters` 在卷末（N=4，卷界 1-4）返回 `[4]`；中段返回 `[N, N+1]`
- `test_crash_replay_idempotent`：连续两次 `_run_scene_split_step` 产物字节一致
- `test_drafting_step_no_md_output_path`：CHAPTER_STEPS 中 shenbi-chapter-drafting 的 `output_path == ""` 且 `uses_staging is True`
- 快照更新：`test_steps_version_pin` 断言 version==3 + 16 元组

- [ ] **Step 2: 跑测试确认失败** → Module/AttributeError

- [ ] **Step 3: 实现**（要点）

① 步表：step4 drafting 改 `uses_staging=True, output_path=""`；其后插：
```python
ChapterStep(5, "pipeline-scene-split", "scene-split", step_type="checkpoint"),
```
原 5-15 顺延 6-16；`PIPELINE_STEPS_VERSION = 3`；`:277-282` 注释块补 #72 变更行。② `_bundle_chapters`：读 `outline/volume_map.md`，`parse_volume_spans` 找 chapter 所在卷，`chapter + 1 > 卷.end` → `[chapter]`，否则 `[chapter, chapter + 1]`。③ planning/drafting 步执行时以 bundle 首章为派发锚（prompt 含两章号），完成时 `state.add_step_done` 对 bundle 内**每章**记 `shenbi-chapter-planning`/`shenbi-chapter-drafting`；step3 context 组装对两章各产 `context/chapter-{n}-context.md`（`calls_context_assembly` 机制循环两章跑）。④ `_run_scene_split_step`：定位 staging 簇（bundle 首章 N）→ `split_bundle` → `validate_split`（带自配置）→ 写 `chapters/chapter-{n}.md`（safe_write）→ 晋升 `staging/chapter-{n}-decisions.json` → `commit_staging(project_dir, [章文件们+decisions们])` → 对每章 `run_gate_g4("shenbi-chapter-drafting", [章文件], project_dir, chapter=n, phase="chapter_loop")`（manifest 按 n 记录）→ 失败 raise（外层按 `FailureClass.DETERMINISTIC_GATE` 归类熔断重派）。⑤ CHAPTER_MEMO 提交批次：commit 目标从 `[step.output_path]` 扩为 bundle 双备忘 + `staged_decisions_targets` 双 sidecar。⑥ post-draft 内联块触发键改 `"pipeline-scene-split" == step.skill`，函数体内对 bundle 各章各跑一遍 `_check_volume_map_alignment`/`_run_post_draft_extract`/`_run_g4_checks`/`_check_word_count_bounds`。⑦ 游标推进（:1536）：`current_chapter = chapter + len(bundle_chapters)`（按 bundle 实际章数步进）。⑧ `_resolve_g4_files`：drafting 步的 decisions 候选增 `{N+1}` brace 解析（`resolve_chapter_path` 对 bundle 首章与次章各解析一次）。

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/pipeline/test_bundle_stepping.py tests/pipeline/test_resume_anchor.py -v` → PASS
Run: `uv run pytest tests/pipeline/ -q`（既有步进/恢复测试若因步序号引用破裂——steps_done 按名键控应无碍；破裂处按新步序修期望）

- [ ] **Step 5: 提交**

`feat(pipeline): spec72 T4——双章 bundle 步进 + pipeline-scene-split 拆分晋升步（卷界单章簇/manifest 按章记录/内联块重挂/游标按 bundle 步进）`

---

### Task 5: SKILL 契约面 + 注册同步

**复杂度: leaf（SKILL.md 文本 + 注册表）· **test_kind: regression_guard（lint 面）

**Files:**
- Modify: `skills/shenbi-chapter-planning/SKILL.md`（契约 writes + 正文双备忘协议 + 场景预算块）
- Modify: `skills/shenbi-chapter-drafting/SKILL.md`（契约 writes + 簇产物协议 + 标记/解剖/钩落款）
- Modify: `skills/shenbi-chapter-revision/SKILL.md`（updates 合同增标记保护条款）
- Modify: `docs/framework/truth-files.yaml` + `site/framework/`（镜像）：staging 簇条目、`chapters/chapter-N.md` `producer: pipeline`、`patterns:` 增 `{N+1}` 形态
- Modify: `docs/framework/decisions-schema.md`（`{N+1}` brace 变体行，如新增）

**Interfaces:**
- Consumes: T4 步名/路径约定（`staging/chapter-N-bundle.md`、`chapters/chapter-{N+1}-decisions.json`）
- Produces: 契约 lint 三绿 + `just generate` diff 空

- [ ] **Step 1: 改 SKILL 契约**

planning writes 增：
```yaml
  - file: plans/chapter-{N+1}-plan.md
    mode: create_or_overwrite
  - file: plans/chapter-{N+1}-plan-decisions.json
    mode: create_or_overwrite
```
正文增「双章 bundle 协议」节：一次派发两份独立备忘（卷末单章簇退化单备忘）；备忘新增场景预算块（精确形态，供 T3 解析器与 G4.cp/G4.cd）：
```
### 场景预算与收束钩（#72 粒度契约）
- 场景1: 1900字｜独立型｜收束钩：<钩原文一行>
- 场景2: 1350字｜配对型｜收束钩：<钩原文一行>
- 章尾钩：<章末句原文>
```
两型规则与组合约束表（照 Global Constraints 原文）；灰域禁令。
drafting writes 改：`chapters/chapter-N.md` → `staging/chapter-N-bundle.md`（mode create_or_overwrite）+ 增 `chapters/chapter-{N+1}-decisions.json`；正文增「场景簇产物协议」：`===CH:n===` 行起章、每章完整解剖（双 H1 其二为题/PRE/正文含 `<!--SCENE-->` 独占行/POST）、每场景末行=备忘声明的收束钩原文逐字、每章末尾落备忘章尾钩。
revision SKILL updates 合同增条款：修订不得删除/挪动 `<!--SCENE-->` 标记行与场景末钩行（G4 复验将 diff pre-rev 备份）。

- [ ] **Step 2: 注册同步**

truth-files.yaml：`chapters/chapter-N.md` 行加 `producer: pipeline`；增 `- {name: staging/chapter-N-bundle.md, kind: chapter, producer: skill}`（staging 族既有条目形态对齐）；`patterns:` 增 `{parametric: "plans/chapter-{N+1}-plan.md", glob: plans/chapter-*-plan.md}`、`{parametric: "chapters/chapter-{N+1}-decisions.json", glob: chapters/chapter-*-decisions.json}`；`site/framework/` 镜像同步（保留 provenance 头）。

- [ ] **Step 3: 验证**

Run: `just lint-contracts && just generate && git diff --exit-code`（生成物 diff 为空；若 generate 改写 deps.json/docs/skills 属正常生成——检查后 add）
Run: `uv run python tools/lint_decisions_sources.py`（如 #72 册需登记 decisions 变体，同步 decisions-schema.md 后跑）

- [ ] **Step 4: 提交**

`feat(skills): spec72 T5——planning/drafting 双章契约与场景预算协议 + revision 标记保护条款 + 注册三源同步`

---

### Task 6: G4 扩展（cd 场景数/钩匹配 + cp 可打包性预检）

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（场景检查族 + 两站点剥标记 + 指纹剥标记）
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（G4.cp 预检）
- Test: `tests/unit/gates/g4/test_scene_checks.py`（新建）

**Interfaces:**
- Consumes: T3 `scene_splitter`（is_scene_marker_line/strip_scene_markers/parse_scene_declarations/pack_scenes/count_scene_markers）
- Produces: G4.cd 新检查 `G4.cd.scene_count`（每章 ≥2，读章文件标记）与 `G4.cd.scene_hook_match`（备忘场景钩声明 ↔ 章文件各场景末行，谓词：声明剥空白 ⊆ 末非空行）；G4.cp 新检查 `G4.cp.scene_budget_packable`（两型域 + 组合约束 + `pack_scenes(前章末实际场景序列+本 bundle 声明序列)` 非 None；首 bundle 跳过跨章段）

- [ ] **Step 1: 写失败测试**（tmp_path 构造章/备忘）：`scene_count_pass_fail`（2 场景过/1 场景挂）；`hook_match_verbatim_pass`（声明原文=场景末行子串过）；`hook_match_drift_fail`；`gray_zone_fails_cp`；`composition_violation_fails_cp`；`cross_chapter_unpackable_fails_cp`（前章章文件场景 [950,950,950] 尾 + 本章声明首场景 1950 → FAIL）；`first_bundle_skips_cross_chapter`；`marker_lines_excluded_from_counts`（含标记行章的 word_count/疲劳窗不受标记行污染——构造对照）。

- [ ] **Step 2: 跑确认失败** → 新检查 id 不存在

- [ ] **Step 3: 实现**：chapter_drafting.py 段面（:388-392）与 word_count/章尾窗读文本处先 `strip_scene_markers`；content_uniqueness（:354）指纹前剥标记；新两检查按 Interfaces 谓词（读 `plans/chapter-{n}-plan.md` 场景声明块 + 章文件标记段）。chapter_planning.py 增预检：解析两备忘声明；前章输入 = `chapters/chapter-{N-1}.md` 标记派生实际 sizes（N=1 跳过）；`validate` 组合约束 + `pack_scenes(prev_tail + 声明 sizes, (1800, 2800))`——None → must_fix。检查器保持纯函数幂等。

- [ ] **Step 4: 跑通过 + 回归**（`uv run pytest tests/unit/gates/ -q`；既有 G4.cd 用例不含标记文本，剥标记为幂等 noop）

- [ ] **Step 5: 提交** `feat(gates): spec72 T6——G4.cd 场景数/钩声明匹配 + G4.cp 场景预算两型域与跨章可打包性预检 + 标记行计数豁免三站点`

---

### Task 7: 修订后重验（标记 diff + 场景检查 + 字数带复检）

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（step15 修订完成点后插重验块；沿用既有 pre-rev 备份 :2088-2111）
- Test: `tests/pipeline/test_revision_revalidate.py`（新建）

**Interfaces:**
- Consumes: T3/T6（is_scene_marker_line/场景检查族/字数带口径）
- Produces: `_revalidate_revised_chapter(project_dir, chapter) -> list[str]`（空=过）；非空 → 修订步按既有重派路径回派（消息携带违例清单）

- [ ] **Step 1: 写失败测试**：`marker_deleted_fails`（修订后删 1 标记行 → 违例含「标记」）；`marker_reordered_fails`；`hook_line_rewritten_fails`（场景末行改写致匹配失败）；`band_drift_fails`（merge_prose 缩到 2700）；`clean_revision_passes`（仅改场景内部散文、标记/钩行/带不动）。

- [ ] **Step 2-4: 红绿实现**：重验 = (a) 标记行序列 diff（`[ln for ln in lines if is_scene_marker_line(ln)]` 前后等长同序 + 各场景钩行号锚不前移）vs `chapters/chapter-{n}-pre-rev.md`；(b) G4.cd 场景检查族复跑（T6 函数复用）；(c) `chapter_total_chars` ∈ band。挂 → raise/返回违例并入修订重派反馈。

- [ ] **Step 5: 提交** `feat(pipeline): spec72 T7——修订后标记 diff+场景检查+字数带重验接线`

---

### Task 8: release_split v2（声明式场景切分 + 已收束窗口 + 启发式退役）

**复杂度: infra** · **test_kind: tdd_red_green（38 用例重写为 v2 套件）**

**Files:**
- Modify: `tools/release_split.py`（大改：保留 CLI 骨架/冻结/账本/`--title-pattern`/`--renumber-published`；切分核换声明式）
- Rewrite: `tests/unit/tools/test_release_split.py`（38 → v2 套件；`tests/fixtures/publish/` 真实 fixture 仅用于仍成立的面：题提取/冻结/账本生命周期/CLI——其正文无标记，切分面用 tmp_path 构造）

**Interfaces:**
- Consumes: T3（strip_scene_markers/pack_scenes/SceneSpan 解析）、T1（primary_platform/fanqie_update 配置读取）
- Produces: v2 行为——起点档 1 章=1 更（重题直发，双 H1 题机制不变，标记剥离）；番茄档：已收束章集合（manifest latest-per-key PASS + 每章 `pipeline-scene-split` 键，`get_gate_result` gate_manifest.py:154-169 复用）内场景序列 → `pack_scenes`（band 自 `chapter_word.fanqie_update`，缺省回退 2000-2800? **否**——缺 genre-config 时 exit 1 报缺配置）→ 更文件（每更以场景收束钩收尾、剥标记）；`--through N` = 1..N ∩ 已收束；`--platform` 缺省读 `primary_platform`（无键回退 fanqie）；不可打包 = exit 1 报 offending 清单（防御性）；SCENE_TRANSITION_WORDS/TIERS/plan_releases/classify_pair/CutSignals 退役删除

- [ ] **Step 1: 重写测试套件**（v2 语义用例）：`qidian_one_chapter_one_update`；`fanqie_packs_scenes_declared_hooks`（构造 3 场景章×2 已收束章 → 更全部落于场景边界、每更末行=钩原文、每更 1800-2800、跨章组更用例）；`unsettled_chapter_excluded`（manifest 有 FAIL latest / 无 split 键 → 不入打包域）；`follower_chapter_settles_via_split_key`（无 drafting 键有 split 键 → 入域）；`through_narrows_not_forces`；`platform_default_from_config`；`unpackageable_defensive_exit1`；`markers_stripped_both_tiers`；`freeze_unchanged_semantics`（既有冻结三元用例保留迁移）；`title_pattern_kept`。

- [ ] **Step 2: 跑确认失败**（v1 实现下新语义用例红）

- [ ] **Step 3: 实现 v2**：`parse_chapter` 增标记段解析（复用 T3：场景切分 + 各段 last_line）；settled 窗口函数 `settled_chapters(project_dir) -> list[int]`（manifest 读 + 谓词）；打包核调 `pack_scenes`；更文本渲染（剥标记/H1、拼场景段、唯一尾换行——沿用 v1 §4 字节合成纪律）；CLI `--platform default=None` → config → fanqie；退役块删除（保留 `CHAPTER_FILE_RE`/冻结/账本）。

- [ ] **Step 4: 全套跑 + 提交**

Run: `uv run pytest tests/unit/tools/test_release_split.py -v` → 全 PASS
Commit: `feat(release-split): spec72 T8——v2 声明式场景切分（已收束窗口/primary_platform 缺省/防御性熔断/启发式退役）`

---

### Task 9: 审计按簇派发（报告工件保持逐章）

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:3010-3121`（两波 prompt/output_paths/savepoint）
- Modify: 各审计 skill SKILL.md writes 增 `{N+1}` brace 报告形态 + 簇 path-context 载荷行约定（`skills/shenbi-review-*/SKILL.md`——以 `audit_report_paths` 实际消费面为准）
- Test: `tests/pipeline/test_audit_cluster.py`（新建）

**Interfaces:**
- Consumes: T4 bundle 步进（bundle 章集）
- Produces: 波派发 `ReviewTask` per skill 覆盖 bundle 两章：`prompt=f"Execute {skill} for chapters {n},{m}. Project dir: ..."`；`output_paths = audit_report_paths(n,...)+audit_report_paths(m,...)`；`_wave_savepoint` 闭包对两章各 `add_audit_result`；write-audit `AmbiguousChapterError` 路径以 path-context 载荷行（`dispatch_helper.py:3955-3972` 既有机制）承载双章

- [ ] **Step 1: 失败测试**：`cluster_prompt_covers_both`（构造 state/chapter_steps 断言派发 prompt 含两章号）；`reports_written_per_chapter`（两章报告路径都在 output_paths）；`savepoint_records_both_chapters`（on_complete 后两章 `wave_completed` 皆含该 skill）；`write_audit_accepts_cluster_declared`（构造双章声明 writes + 双报告落盘 → 无「未声明写入」）。

- [ ] **Step 2-4: 红绿实现**（审计波入口以 bundle 章集参数化；G3 记账两章各落——`_get_audit_history` 按章读取形态不变）+ 回归 `uv run pytest tests/pipeline/ -q`

- [ ] **Step 5: 提交** `feat(pipeline): spec72 T9——审计两波按簇派发双章报告，savepoint 双章记账`

---

### Task 10: 验收覆盖表全跑 + 收尾

**复杂度: infra** · **test_kind: regression_guard**

**Files:** 无新文件（验证 + 文档同步：AGENTS.md release-split 行如需 `--through` 提及则一行补注）

- [ ] **Step 1: 逐条验收**（spec §4 → 命令，输出贴 progress.md `## 验收证据`）
  1. 拆分器确定性/校验全绿 → `uv run pytest tests/unit/pipeline/test_scene_splitter.py -v`
  2. G4 逐章 + 标记缺失负例 → `uv run pytest tests/unit/gates/g4/test_scene_checks.py -v`
  3. 番茄切分钩 100%/零中切/跨章组更/防御负例 → `uv run pytest tests/unit/tools/test_release_split.py -v`
  4. `just check` 全绿；章数预算幂等 → `uv run python -m shenbi.pipeline.volume_budget novel-xinghuo-vol1` 连跑两次输出一致（`re_budget_pending` 属设计内预期红——断言其存在且幂等，不作为失败）
  5. 四联带测试 → `uv run pytest tests/unit/gates/test_word_band_unified.py -v`
  6. 3300 口径 → `uv run pytest tests/unit/contracts/test_genre_config_platform.py -v` + `ceil(10000000/3200)==3125` 断言在 T2 用例内
  7. bundle 原子/恢复重放 → `uv run pytest tests/pipeline/test_bundle_stepping.py -v`
  8. 卷界奇偶 → 同上 singleton 用例
  9. 修订重验负例 → `uv run pytest tests/pipeline/test_revision_revalidate.py -v`
- [ ] **Step 2: G3.4 声明**——本 spec 无 LLM 产物评分场景（全离线结构性验证），无需独立评分子 agent（spec §4 测试层级映射声明）
- [ ] **Step 3: `just check` 完整跑**（阶段 7 门禁，输出进 progress.md）
- [ ] **Step 4: 提交** `chore(spec72): T10 验收覆盖表全跑收尾`

---

## 验收覆盖表（spec §4 ↔ task ↔ 命令）

| spec 验收 | task | 命令 |
|---|---|---|
| 拆分器确定性拆分+校验全绿 | T3/T4 | pytest test_scene_splitter + test_bundle_stepping |
| G4 逐章通过+标记缺失熔断负例 | T6 | pytest test_scene_checks |
| 番茄切分 100% 落钩+零中切+跨章组更+防御负例 | T8 | pytest test_release_split |
| just check 全绿 | T10 | `just check` |
| 章数预算重排幂等 | T10 | volume_budget 连跑两次 diff 一致 |
| 2800/2799 四联 | T2 | pytest test_word_band_unified |
| 4000/4001 天花板 | T2 | 同上 |
| 3300 口径三断言 | T1/T2 | pytest test_genre_config_platform |
| bundle 原子性 crash 重放 | T4 | pytest test_bundle_stepping |
| 卷界单章簇 | T4 | 同上 |
| 修订重验两负例+带复检 | T7 | pytest test_revision_revalidate |
| 拆分器场景域负例（灰域 1450）+ cp 预检负例 | T3/T6 | pytest test_scene_splitter + test_scene_checks |

## Self-Review

- 覆盖：spec 施工面 1(T1/T2) 2(T5/T6) 3(T5) 3b(T4/T9) 4(T3/T4) 5(T6) 6(T8) 7(T2) 8(T9) 9(T7) + 同步清单(T5) + 验收(T10) ✓
- 无占位符：G4 入口函数名（g2 chapter 检查公开名）实现时以 `grep "^def " src/shenbi/gates/g2.py` 现场对齐——已读区段为准（G2.6/G2.7 在 `g2_chapter_check` 主循环内联，测试直接走该入口）
- 类型一致：`SplitChapter/BundleChapters/SceneSpan/pack_scenes` 在 T3 定义、T4/T6/T8 消费同名同参 ✓
