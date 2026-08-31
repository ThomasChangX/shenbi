# Spec #35 threshold-config-coherence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 15 条 C9 LIVE findings——阈值单源、genre-config 契约补全、SKILL 阈值矛盾裁决、常量去污染、阈值对账 lint。

**Architecture:** 所有数值阈值收进 `src/shenbi/contracts/thresholds.py`；评分分档枚举定稿 PASS/CONDITIONAL/MARGINAL/FAIL；genre-config 补 approval 必填与键集校验；SKILL.md 矛盾按权威节单源化；新增 allowlist 驱动的对账 lint（WARN-only）接入 just check。

**Tech Stack:** Python 3.11+ / Pydantic v2 / StrEnum / pytest；验证一律 `uv run`。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-threshold-config-coherence-fix.md`（v3，15 条 LIVE）

## Global Constraints

- 状态字面量单一信源：枚举唯一定义于 `src/shenbi/status.py` / `contracts/enums.py`；`tools/lint_status_strings.py` 红即 Critical
- `src/shenbi/` 禁 `print()`（structlog）；pathlib；gate 检查器纯函数幂等
- G0.9：不手造 fixture 文件；scenario 输入只引用 `tests/fixtures/` 真实产物；内存 dict 变体不是 fixture
- commit 用 Conventional Commits；pathspec 显式列文件，禁 `git add -A`
- 验证命令走 `uv run` / `just`（与 CI `uv run --frozen` 同构）

---

### Task 1: 阈值分档单源 + 枚举定稿（F134/F411）

**复杂度: infra · test_kind: tdd_red_green · 层级: T1**

**Files:**
- Modify: `src/shenbi/contracts/thresholds.py`（加两个分档常量）
- Modify: `src/shenbi/status.py:74-80`（ScoreClassification 成员重命名）
- Modify: `src/shenbi/scoring.py:228-235`（classify 读常量）
- Modify: `src/shenbi/gates/g3.py:164,169`（两处 `threshold = 90` → `TEST_PASS`）
- Test: `tests/unit/test_status.py`、`tests/unit/test_scoring.py`（classify 相关）

**Interfaces:**
- Produces: `thresholds.CONDITIONAL_MIN: int = 75`、`thresholds.MARGINAL_MIN: int = 60`；`ScoreClassification` 成员 `PASS = "PASS"` / `CONDITIONAL = "CONDITIONAL"` / `MARGINAL = "MARGINAL"` / `FAIL = "FAIL"`；`classify(score) -> ScoreClassification` 签名不变

- [ ] **Step 1: 写失败测试**（tests/unit/test_scoring.py 追加/改写）

```python
from shenbi.contracts.thresholds import CONDITIONAL_MIN, MARGINAL_MIN, TEST_PASS
from shenbi.status import ScoreClassification


def test_classify_band_vocabulary_single_source():
    assert classify(95) is ScoreClassification.PASS
    assert classify(TEST_PASS) is ScoreClassification.PASS
    assert classify(89) is ScoreClassification.CONDITIONAL
    assert classify(CONDITIONAL_MIN) is ScoreClassification.CONDITIONAL
    assert classify(74) is ScoreClassification.MARGINAL
    assert classify(MARGINAL_MIN) is ScoreClassification.MARGINAL
    assert classify(59) is ScoreClassification.FAIL
```

```python
# tests/unit/test_status.py：旧成员名断言（62-63 行附近）改为
def test_score_classification_values():
    assert {s.value for s in ScoreClassification} == {"PASS", "CONDITIONAL", "MARGINAL", "FAIL"}
```

- [ ] **Step 2: 跑测试确认红**：`uv run pytest tests/unit/test_scoring.py tests/unit/test_status.py -q` → FAIL（AttributeError PASS / CONDITIONAL_MIN）
- [ ] **Step 3: 实现**

```python
# thresholds.py 追加
CONDITIONAL_MIN: int = 75  # conditional band floor (75-89)
MARGINAL_MIN: int = 60  # marginal band floor (60-74)
```

```python
# status.py ScoreClassification 替换为
class ScoreClassification(StrEnum):
    """classify() bucket for a final score."""

    PASS = "PASS"
    CONDITIONAL = "CONDITIONAL"
    MARGINAL = "MARGINAL"
    FAIL = "FAIL"
```

```python
# scoring.py classify 替换为（顶部 import 已有 TEST_PASS，补两个）
from shenbi.contracts.thresholds import CONDITIONAL_MIN, MARGINAL_MIN, TEST_PASS

def classify(score: float | int) -> ScoreClassification:
    if score >= TEST_PASS:
        return ScoreClassification.PASS
    if score >= CONDITIONAL_MIN:
        return ScoreClassification.CONDITIONAL
    if score >= MARGINAL_MIN:
        return ScoreClassification.MARGINAL
    return ScoreClassification.FAIL
```

```python
# g3.py 两处（:164、:169）
threshold = TEST_PASS  # pipeline mode: individual-pass line (94 is tier advancement)
```
（g3.py 顶部 import 行补 TEST_PASS；保留注释说明 90 个体线 vs 94 晋级线分层）

- [ ] **Step 4: 跑测试确认绿**：`uv run pytest tests/unit/test_scoring.py tests/unit/test_status.py -q` → PASS；旧词表全部站点同步——`test_status.py:62-63,73`（枚举断言 + STATUS_STRING_LITERALS 派生）、`tests/unit/test_scoring.py:453-458,580,596`（如断言旧成员/旧值则按新词表改写）；再 `uv run pytest -n auto -m "not last" -q` 全量回归（重点：g3 测试若有断言 90 字面量需同步）
- [ ] **Step 5: Commit**：`git add src/shenbi/contracts/thresholds.py src/shenbi/status.py src/shenbi/scoring.py src/shenbi/gates/g3.py tests/unit/test_scoring.py tests/unit/test_status.py && git commit -m "fix: single-source score bands — enum PASS/CONDITIONAL/MARGINAL/FAIL + thresholds constants (F134/F411)"`

### Task 2: 68 份 rubric 分档线 codemod（F760）

**复杂度: leaf · test_kind: regression_guard · 层级: T1（机械化文档对齐）**

**Files:**
- Modify: `tests/tiers/t1-skill/*/rubric.md`（68 份，含 `_template`）

**Interfaces:** 无代码接口；产出断言 `git grep -c "75-89: PASS" tests/tiers` → 0

- [ ] **Step 1: codemod（一次性 python，不留库文件）**

```bash
uv run python - <<'EOF'
from pathlib import Path
old = "90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL"
new = "90-100: PASS | 75-89: CONDITIONAL | 60-74: MARGINAL | 0-59: FAIL"
n = 0
for p in Path("tests/tiers").rglob("rubric.md"):
    t = p.read_text(encoding="utf-8")
    if old in t:
        p.write_text(t.replace(old, new), encoding="utf-8"); n += 1
    elif "75-89" in t:
        print("MANUAL:", p)
print("rewritten:", n)
EOF
```
Expected: `rewritten: 68`，无 MANUAL 行
- [ ] **Step 2: 断言**：`git grep -c "75-89: PASS" tests/tiers` → exit 1（零命中）；`git grep -rn "PASS (acceptable)" tests/ src/` → 零命中
- [ ] **Step 3: 回归**：`uv run pytest tests/unit -q`（rubric 模板被测试消费则同步过）
- [ ] **Step 4: Commit**：`git add tests/tiers && git commit -m "test: align 68 rubric band lines to PASS/CONDITIONAL/MARGINAL vocabulary (F760)"`

### Task 3: genre-config 契约补全（F232/F214/F822）

**复杂度: infra · test_kind: tdd_red_green · 层级: T1**

**Files:**
- Modify: `src/shenbi/contracts/skills/genre_config.py`（approval 必填 + 键集校验）
- Modify: `src/shenbi/config/config_coherence.py:278`（rollback glob 补裸 .bak）
- Modify: `skills/shenbi-genre-config/SKILL.md:77,296,302,193,224`
- Test: `tests/unit/gates/g4/test_genre_config.py`

**Interfaces:**
- Produces: `GenreConfig` 新增校验——approval 缺失/空 → ValueError；顶层键集 ⊆ `_GENRE_KEYS` 且 8 必填键全在 → 否则 ValueError。`_GENRE_KEYS` 从 `shenbi.contracts.ownership` import（如循环依赖则在 genre_config 内 `from shenbi.contracts.ownership import _GENRE_KEYS as GENRE_KEYS` re-export 公共名 `GENRE_KEYS`）

- [ ] **Step 1: 写失败测试**（tests/unit/gates/g4/test_genre_config.py 追加；基础 dict 取自真实 fixture 的内存变体——G0.9：不落盘新 fixture 文件）

```python
import json
from pathlib import Path
import pytest
from shenbi.contracts.skills.genre_config import GenreConfig

FIXTURE = Path("tests/fixtures/genre-config-example.json")

def _real_config() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))

def test_approval_required():
    cfg = _real_config()
    cfg.pop("approval")
    with pytest.raises(ValueError, match="approval"):
        GenreConfig.model_validate(cfg)
    cfg["approval"] = {}
    with pytest.raises(ValueError, match="approval"):
        GenreConfig.model_validate(cfg)

def test_keyset_bounded():
    cfg = _real_config()
    cfg["rogueKey"] = 1
    with pytest.raises(ValueError, match="rogueKey"):
        GenreConfig.model_validate(cfg)

def test_eight_required_keys_present():
    cfg = _real_config()
    cfg.pop("pacing")  # 必填不可缺（approval 缺失已由 test_approval_required 覆盖）
    with pytest.raises(ValueError):
        GenreConfig.model_validate(cfg)

def test_trope_inventory_optional():
    cfg = _real_config()
    cfg.pop("tropeInventory")
    assert GenreConfig.model_validate(cfg)

def test_keyset_authority_is_ownership():
    from shenbi.contracts.ownership import _GENRE_KEYS
    from shenbi.contracts.skills import genre_config as gc
    assert set(gc._REQUIRED_TOP_KEYS) == _GENRE_KEYS - {"tropeInventory"}

def test_real_fixture_still_valid():
    assert GenreConfig.model_validate(_real_config())
```

- [ ] **Step 2: 红**：`uv run pytest tests/unit/gates/g4/test_genre_config.py -q` → 新增 3 条 FAIL（approval/keyset 现在放行）
- [ ] **Step 3: 实现**（genre_config.py 追加两个 model_validator）

```python
# 模块级（genre_config.py 顶部 class 之前）：
from shenbi.contracts.ownership import _GENRE_KEYS  # 单一键集权威源（F214：禁止平行定义）

_REQUIRED_TOP_KEYS = tuple(
    k for k in _GENRE_KEYS if k != "tropeInventory"
)  # 8 必填 = _GENRE_KEYS 减可选 tropeInventory

# class GenreConfig 内：
    @model_validator(mode="before")
    @classmethod
    def _top_level_keyset(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for key in data:
            if key not in _GENRE_KEYS:
                raise ValueError(f"unknown top-level key '{key}' (allowed: 8 required + optional tropeInventory)")
        missing = [k for k in _REQUIRED_TOP_KEYS if k not in data]
        if missing:
            raise ValueError(f"missing required top-level keys: {missing}")
        return data

    @model_validator(mode="after")
    def _approval_required(self) -> GenreConfig:
        if not self.approval or not self.approval.get("decision"):
            raise ValueError("approval.decision is required (rule 8: no approval = no valid config)")
        return self
```
（docstring "Rules" 列表补 8. approval 必填、9. 顶层键集 = 8 必填 + 1 可选 tropeInventory；model_config 的 `extra="ignore"` 保留——键集校验在 before validator 显式报错而非静默忽略）

```python
# config_coherence.py rollback glob（:278 附近）
    for bak in [*project_dir.glob("genre-config.json.bak.*"), *project_dir.glob("genre-config.json.bak")]:
        bak.unlink()
```

SKILL.md（shenbi-genre-config）：
- :296 「顶层字段数：恰好 8 个（…）」→「顶层字段：8 必填（version, updated, fatigueWords, pacing, chapterTypes, auditDimensions, customRules, approval）+ 1 可选（tropeInventory）」
- :302 表中 `= 8` 行 → `8 必填 + 1 可选`
- :77 与 :193/:224 备份指示统一为 `genre-config.json.bak`（裸后缀，与代码侧 paths.py:35/gates/shared.py 一致）

- [ ] **Step 4: 绿**：`uv run pytest tests/unit/gates/g4/test_genre_config.py tests/unit/test_config_governance.py -q` → PASS（若既有测试用 8 键无 approval 的 dict 构造，按新规则补 approval 键——那是测试数据修正不是放松断言）；`just lint-contracts` 绿（SKILL.md 改动若涉 writes/reads 需 `just generate` 同步，本 task 只改正文与示例，预期无生成物 diff）
- [ ] **Step 5: Commit**：`git add src/shenbi/contracts/skills/genre_config.py src/shenbi/config/config_coherence.py skills/shenbi-genre-config/SKILL.md tests/unit/gates/g4/test_genre_config.py && git commit -m "fix: genre-config contract — approval required + keyset bound + rollback glob bare-.bak (F232/F214/F822)"`

### Task 4: CONSTELLATION 裁决（F213/F846）

**复杂度: infra · test_kind: characterization（带区间放宽断言）· 层级: T1**

**Files:**
- Modify: `src/shenbi/contracts/skills/pacing_design.py`（validator [15,40] + docstring）
- Modify: `skills/shenbi-pacing-design/SKILL.md:91,176,187,199,257`
- Test: `tests/unit/contracts/test_pacing_design.py`（如无则新建于同路径）

**Interfaces:** `_constellation_range` 语义变为 `[15, 40]`（错误消息同步）；docstring 规则 4 改 "[15, 40]（按卷型设计波段，硬失败带）"、规则 5 改 "6-12 scene types"

- [ ] **Step 1: 失败测试**

```python
import pytest
from shenbi.contracts.skills.pacing_design import PacingDesign

def _base(const_ratio: float) -> dict:
    return {
        "beats": {"铺垫": 25, "升级": 30, "爆发": 25, "余波": 20},
        "line_ratios": {"QUEST": 50, "FIRE": 20, "CONSTELLATION": const_ratio},
        "scene_types": [f"s{i}" for i in range(8)],
    }

def test_constellation_hard_band_covers_kaijuan():
    assert PacingDesign.model_validate(_base(38))   # 开卷 30-40 合法
    assert PacingDesign.model_validate(_base(15))
    assert PacingDesign.model_validate(_base(40))
    with pytest.raises(ValueError, match=r"\[15, 40\]"):
        PacingDesign.model_validate(_base(41))
    with pytest.raises(ValueError, match=r"\[15, 40\]"):
        PacingDesign.model_validate(_base(14))
```

- [ ] **Step 2: 红**（38/40 现在被 [15,35] 拒 → FAIL）
- [ ] **Step 3: 实现**：`pacing_design.py` `_constellation_range` 中 `15 <= const <= 35` → `15 <= const <= 40`，错误消息 `outside [15, 40]`；模块 docstring 第 4 条 `[20, 30]` → `[15, 40]（硬失败带；按卷型权威波段见 SKILL 按卷型表）`、第 5 条 `Exactly 8 scene types` → `6-12 scene types`
- SKILL.md:91 `CONSTELLATION 15-25%` 行改为指向按卷型表：`CONSTELLATION 见下方「目标比值（按卷型）」表`；:176 `低于 20% 或高于 30% 触发警告` → `低于 15% 或高于 40% 触发警告`（与硬失败带一致，卷内细分以按卷型表为准）；:187 `15-30%` → 指向按卷型表；:257 `15-30% | < 10% 或 > 40%` 行的 CONSTELLATION 列同步指向按卷型表口径；:~199 「恰好 8 种场景类型」→「6-12 种场景类型」
- [ ] **Step 4: 绿**：`uv run pytest tests/unit/contracts/ -q`；`just lint-contracts`（SKILL 正文改动无生成物 diff）；grep 断言：`grep -c "低于 20% 或高于 30%" skills/shenbi-pacing-design/SKILL.md` → 0、`grep -c "15-30%" skills/shenbi-pacing-design/SKILL.md` → 0
- [ ] **Step 5: Commit**：`git add src/shenbi/contracts/skills/pacing_design.py skills/shenbi-pacing-design/SKILL.md tests/unit/contracts/test_pacing_design.py && git commit -m "fix: CONSTELLATION hard band [15,40] + per-volume authoritative table sync (F213/F846)"`

### Task 5: SKILL 矛盾裁决余项（F818/F806/F808/F820/F843/F875）

**复杂度: leaf（纯文档裁决）· test_kind: regression_guard（grep 断言）· 层级: T1**

**Files（全部 Modify）:**
- `skills/shenbi-foreshadowing-resolve/SKILL.md` + `skills/shenbi-foreshadowing-resolve/chase-power.md`（F818）
- `skills/shenbi-chapter-pattern/SKILL.md`（F806）
- `skills/shenbi-chapter-revision/SKILL.md:116` + `revision-modes.md:3`（F808 计数面）
- `skills/shenbi-foreshadowing-track/lifecycle-states.md`（F820）
- `skills/shenbi-review-highpoint/SKILL.md`（F843）
- `skills/shenbi-volume-outlining/SKILL.md`（F875）

**裁决表（权威 = 铁律/常量表/明细表，其余副本同步）：**

| Finding | 权威口径 | 改动 |
|---|---|---|
| F818 | 常量表 GREEN_MAX=50 / RED_NOW=100 / FORCE_NEXT_CHAPTER=200 | :124 区间判定改 `GREEN < 50, YELLOW 50-99, RED ≥ 100`；:85 计算示例与 :120 兑现表内 `CP = 80` 的 `RED` 标签改 `YELLOW`（兑现表全表审计同标签）、`5.6 (GREEN)`→`(GREEN)`；:66 铁律 1 改 `CP ≥ 100（RED）→ 下章必须兑现至少一条；CP ≥ 200 → 强制推进`；**chase-power.md:21-24 分档同步**为 `GREEN < 50, YELLOW 50-99, RED ≥ 100, ≥200 强制推进`（消除第三套体系） |
| F806 | :330-338 五档明细表（权威，逐值照抄） | :109-111 三档改为五档一致口径：`> 2.5 优秀 / 2.0-2.5 健康 / 1.5-2.0 轻度单调 / 1.0-1.5 中度单调 / ≤ 1.0 严重单调`（打开 :330-338 核对后逐字同步） |
| F808 | revision-modes.md 六种枚举 | SKILL.md:116 `三种模式` → `六种模式（见 revision-modes.md）` |
| F820 | lifecycle SKILL 六态机 | lifecycle-states.md 状态机补 `DORMANT`、`ACTIVE` 两态及转移边（与 shenbi-foreshadowing-lifecycle/SKILL.md:43-79 对齐） |
| F843 | 铁律 3（缺即 error） | :85 `缺一段 = warning；缺两段 = error` → `缺任一段 = error（铁律 3）` |
| F875 | EXACT 清单（≥3）+ 张力铺垫 15-25% | :66 `至少 1 个实体钩子` → `至少 3 个实体钩子`；:100 `10-20%` → `15-25%`（与 :175/184 一致） |

- [ ] **Step 1: 逐文件按裁决表编辑**（打开每处 file:line 核对上下文后改）
- [ ] **Step 2: grep 断言**（每条实跑）：
  - `grep -c "缺一段 = warning" skills/shenbi-review-highpoint/SKILL.md` → 0
  - `grep -c "三种模式" skills/shenbi-chapter-revision/SKILL.md` → 0
  - `grep -c "DORMANT" skills/shenbi-foreshadowing-track/lifecycle-states.md` → ≥1
  - `grep -c "至少 1 个实体钩子" skills/shenbi-volume-outlining/SKILL.md` → 0
  - `grep -c "GREEN < 20" skills/shenbi-foreshadowing-resolve/SKILL.md skills/shenbi-foreshadowing-resolve/chase-power.md` → 0；`grep -c "RED > 200\|RED ≥ 200" skills/shenbi-foreshadowing-resolve/chase-power.md` → 0（CP 分档单一体系，spec 验收 5 断言）
- [ ] **Step 3: 契约面回归**：`just lint-contracts && just generate`（生成物 diff 必须为空；SKILL 正文改动不触 writes/reads）
- [ ] **Step 4: Commit**：`git add skills/shenbi-foreshadowing-resolve/SKILL.md skills/shenbi-chapter-pattern/SKILL.md skills/shenbi-chapter-revision/SKILL.md skills/shenbi-chapter-revision/revision-modes.md skills/shenbi-foreshadowing-track/lifecycle-states.md skills/shenbi-review-highpoint/SKILL.md skills/shenbi-volume-outlining/SKILL.md && git commit -m "docs(skills): adjudicate threshold contradictions to single authoritative values (F818/F806/F808/F820/F843/F875)"`

### Task 6: 常量去污染（F443）

**复杂度: infra · test_kind: tdd_red_green · 层级: T1**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:141,162,332`
- Test: `tests/unit/gates/g4/test_chapter_drafting.py`（既有文件追加；既有用例 :154/:165-166 显式传名单，预期不受默认回退变更影响）

**Interfaces:** `_load_protagonist_names(project_dir: str) -> list[str]` 无数据时返回 `[]`；调用侧空名单 → 记 `{"id": "G4.cd.protagonist_presence", "file": fp, "s": GateStatus.SKIP, "r": "no protagonist data"}` 并跳过检查（gate 纯度保持：只追加检查项，无文件副作用）

- [ ] **Step 1: 失败测试**

```python
from shenbi.gates.g4.chapter_drafting import _load_protagonist_names

def test_no_protagonist_data_returns_empty(tmp_path):
    assert _load_protagonist_names(str(tmp_path)) == []

def test_no_hardcoded_fallback_names():
    # F443: 框架默认值不得携带项目专属主角名
    import inspect
    from shenbi.gates.g4 import chapter_drafting
    assert "林烽" not in inspect.getsource(chapter_drafting)
```

- [ ] **Step 2: 红**：现返回 `["林烽", "他"]` → FAIL
- [ ] **Step 3: 实现**：
  - :141 `return ["林烽", "他"]` → `return []`
  - :162 `names = ["林烽", "他"]` → 删除该行（走 `if not names: return []` 语义）
  - :162 后 `if "他" not in names: names.append("他")` 保留（有名单时补通用代词，非项目专属）
  - :332 `_load_protagonist_names(str(project_root)) if project_dir else ["林烽", "他"]` → `_load_protagonist_names(str(project_root)) if project_dir else []`
  - :334 起：`if not protagonist_names:` 分支新增 `c.append({"id": "G4.cd.protagonist_presence", "file": fp, "s": GateStatus.SKIP, "r": "no protagonist data"})` + `continue` 等价结构（保持该文件既有 check 追加风格）
  - 既有测试若依赖默认名 `林烽` 构造断言：改为测试内显式传入名单（真实数据路径不变）
- [ ] **Step 4: 绿**：`uv run pytest tests/unit/gates/g4/ -q`；`git grep -rn "林烽" src/` → exit 1
- [ ] **Step 5: Commit**：`git add src/shenbi/gates/g4/chapter_drafting.py tests/unit/gates/g4/ && git commit -m "fix: remove project-specific protagonist fallback, SKIP when no data (F443)"`

### Task 7: 阈值对账 lint（T5，allowlist WARN-only）

**复杂度: infra · test_kind: tdd_red_green · 层级: T1**

**Files:**
- Create: `tools/lint_threshold_reconciliation.py`
- Create: `tools/threshold_allowlist.json`
- Modify: `justfile` check recipe（追加一行）
- Test: `tests/unit/tools/test_lint_threshold_reconciliation.py`

**Interfaces:**
- `lint_threshold_reconciliation.py`：读 allowlist `{ "entries": [ {"skill": "shenbi-pacing-design", "pattern": "CONSTELLATION", "file": "skills/shenbi-pacing-design/SKILL.md", "checker": "src/shenbi/contracts/skills/pacing_design.py", "bounds": [15, 40]} ] }`；对每条：在 file 中找 pattern 附近的 `\d+-\d+` 区间，若存在且与 bounds 不一致 → 打 WARN（结构化输出），**exit 0 恒成立**（WARN-only 首周期）；allowlist 条目 file/checker 任一缺失 → WARN
- 初始 allowlist 至少含：CONSTELLATION 按卷型表行（`pattern` 锚定开卷 30-40 行，bounds [15,40] 为各卷型并集；Task 4 已把散点行改为指针，扫描窗口须命中按卷型表行而非指针行）

- [ ] **Step 1: 失败测试**

```python
import json, subprocess, sys
from pathlib import Path

def test_lint_warns_on_mismatch(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    allow = tmp_path / "a.json"
    allow.write_text(json.dumps({"entries": [{
        "skill": "shenbi-pacing-design", "pattern": "CONSTELLATION",
        "file": "skills/shenbi-pacing-design/SKILL.md",
        "checker": "src/shenbi/contracts/skills/pacing_design.py",
        "bounds": [999, 1000]}]}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(root / "tools/lint_threshold_reconciliation.py"),
                        "--allowlist", str(allow)], capture_output=True, text=True)
    assert r.returncode == 0            # WARN-only
    assert "WARN" in r.stdout

def test_lint_clean_on_repo_allowlist():
    root = Path(__file__).resolve().parents[3]
    r = subprocess.run([sys.executable, str(root / "tools/lint_threshold_reconciliation.py")],
                       capture_output=True, text=True, cwd=root)
    assert r.returncode == 0
```

- [ ] **Step 2: 红**（脚本不存在 →非零退出）
- [ ] **Step 3: 实现**：argparse `--allowlist`（默认 `tools/threshold_allowlist.json`）；正则 `(\d+)\s*[-–]\s*(\d+)\s*%?` 在 pattern 行 ±3 行窗口内取区间；区间与 bounds 无交集 → `print(f"WARN threshold_drift skill={...} file={...} found={lo}-{hi} expected={bounds}")`；无区间或文件缺 → WARN；**不 sys.exit(1)**；写 `tools/threshold_allowlist.json`（CONSTELLATION [15,40] + genre-config 顶层键 8/9 口径一条可选）
- justfile check recipe 在 `lint_helper_usage.py` 行后追加：`    uv run python tools/lint_threshold_reconciliation.py`
- [ ] **Step 4: 绿 + 全量**：`uv run pytest tests/unit/tools/ -q`；`uv run python tools/lint_threshold_reconciliation.py` → exit 0（WARN-only 恒 exit 0；WARN 仅在映射条目漂移时出现）；`just check`
- [ ] **Step 5: Commit**：`git add tools/lint_threshold_reconciliation.py tools/threshold_allowlist.json justfile tests/unit/tools/test_lint_threshold_reconciliation.py && git commit -m "feat: allowlist-driven threshold reconciliation lint, WARN-only, wired to just check (T5)"`

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 F232 内存变体校验 | T3 | `uv run pytest tests/unit/gates/g4/test_genre_config.py -q` |
| 2 F411/F134 | T1+T2 | `git grep -n "= 90" src/shenbi/gates/g3.py`（0）；`git grep -c "75-89: PASS" tests/tiers`（0） |
| 3 T5 lint exit 0 | T7 | `uv run python tools/lint_threshold_reconciliation.py` |
| 4 F443 | T6 | `git grep -rn "林烽" src/`（0） |
| 5 T4 同步断言 | T4+T5 | Task 5 Step 2 grep 组 + `grep -n "15-25%" skills/shenbi-pacing-design/SKILL.md` 仅按卷型表语境 |
| 6 just check | 全部 | `just check` |

无评分场景 → 无 G3.4 调度需求。
