# Config Governance Bypass Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 8 config-governance bypass vectors (F606/F611/F631/F643/F666/F638/F635/F614) of spec `docs/superpowers/specs/2026-08-14-config-governance-design.md` (fix design R1-R5).

**Architecture:** One shared dimension resolver (`resolve_audit_dimensions`) used by write side (Rule 1), G0 read side, and runtime activation; criticality-split missing-key semantics; G0 loud-fails malformed shapes instead of crashing; the genre-config TriggerStep update path gains snapshot → composite-G4 (filename-partitioned) → diff-governance (`govern_genre_config_change`) → all-stage rollback; both governance entry points become two-phase (validate-all-then-commit).

**Tech Stack:** Python 3.11+, pydantic (DecisionsDoc), pytest; all validation via `uv run pytest` / `just check` (CI-isomorphic).

**复杂度:** all tasks = infra（协调者亲自实现，不分派）

## Global Constraints

- 禁 `print()` 于 `src/shenbi/`（structlog）；pathlib 文件 I/O；gate 检查器纯函数幂等
- fixtures 只能引用真实产物：bypass 变体在测试内**程序化派生**自 `tests/fixtures/genre-config-example.json`（G0.9，禁手写 fixture）
- 改 SKILL.md 契约后跑 `just generate`，生成物（deps.json/docs）禁手改；`just lint-contracts` 须绿
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`，新代码禁裸状态字符串
- conventional commits；commit 显式列文件路径（禁 `git add -A`）
- 验证命令一律 `uv run` / `just`（系统 python 不算证据）

---

### Task 1: 共享 resolver + 写侧 Rule 1/2 统一重写 + 两阶段提交（R1 写侧 + R3 + R5）

**Files:**
- Modify: `src/shenbi/config/thresholds.py`（新增 `resolve_audit_dimensions`）
- Modify: `src/shenbi/config/config_coherence.py`（Rule 1/2 重写 + 两阶段）
- Test: `tests/unit/config/test_config_coherence.py`（扩充）

**Interfaces:**
- Produces: `resolve_audit_dimensions(config: Mapping[str, Any]) -> tuple[dict[str, Any], bool]`（(合并维度 dict, malformed)；camelCase `auditDimensions` 优先、snake_case `audit_dimensions` 仅补充 camelCase 未出现的键；任一键形存在但非 dict → ({}, True)）——Task 2 的 G0 读侧与 audit_layer 复用
- Produces: `update_genre_config(project_dir: Path, changes: dict[str, Any], rationale: str) -> None`（签名不变；语义升级）

- [ ] **Step 1: 写失败测试（resolver 合并/malformed 语义）**

追加到 `tests/unit/config/test_thresholds.py`：

```python
from shenbi.config.thresholds import resolve_audit_dimensions


class TestResolveAuditDimensions:
    def test_camel_case_only(self):
        dims, malformed = resolve_audit_dimensions({"auditDimensions": {"texture": True}})
        assert dims == {"texture": True} and malformed is False

    def test_snake_case_fallback(self):
        dims, malformed = resolve_audit_dimensions({"audit_dimensions": {"texture": False}})
        assert dims == {"texture": False} and malformed is False

    def test_merge_camel_wins(self):
        cfg = {"auditDimensions": {"texture": True}, "audit_dimensions": {"era": True}}
        dims, malformed = resolve_audit_dimensions(cfg)
        assert dims == {"texture": True, "era": True} and malformed is False

    def test_both_absent_means_empty_not_malformed(self):
        dims, malformed = resolve_audit_dimensions({"version": "1.0"})
        assert dims == {} and malformed is False

    def test_scalar_camel_is_malformed(self):
        dims, malformed = resolve_audit_dimensions({"auditDimensions": False})
        assert dims == {} and malformed is True

    def test_valid_camel_plus_scalar_snake_is_malformed(self):
        cfg = {"auditDimensions": {"texture": True}, "audit_dimensions": 0}
        dims, malformed = resolve_audit_dimensions(cfg)
        assert dims == {} and malformed is True
```

- [ ] **Step 2: 跑测试确认失败**

`uv run pytest tests/unit/config/test_thresholds.py -q` → Expected: FAIL `ImportError: cannot import name 'resolve_audit_dimensions'`

- [ ] **Step 3: 实现 resolver（thresholds.py 末尾）**

```python
def resolve_audit_dimensions(config: Mapping[str, object]) -> tuple[dict[str, object], bool]:
    """Merge camelCase/snake_case audit-dimension maps, single source for all consumers.

    camelCase ``auditDimensions`` wins on key collision; snake_case
    ``audit_dimensions`` only contributes keys camelCase lacks. Any present
    but non-dict key shape makes the whole thing malformed (fail-safe).
    Returns (merged_dims, malformed).
    """
    camel = config.get("auditDimensions")
    snake = config.get("audit_dimensions")
    if (camel is not None and not isinstance(camel, dict)) or (
        snake is not None and not isinstance(snake, dict)
    ):
        return {}, True
    merged: dict[str, object] = {}
    if isinstance(snake, dict):
        merged.update(snake)
    if isinstance(camel, dict):
        merged.update(camel)
    return merged, False
```

（`from collections.abc import Mapping` 加到文件头 imports。）

- [ ] **Step 4: 跑测试确认通过**

`uv run pytest tests/unit/config/test_thresholds.py -q` → PASS

- [ ] **Step 5: 写失败测试（写侧 4 向量拦截 + 两阶段）**

追加到 `tests/unit/config/test_config_coherence.py`（fixture 派生模式）：

```python
import copy
import json

import pytest

from shenbi.config.config_coherence import AUDIT_TRAIL_NAME, ConfigError, update_genre_config

_LONG = "x" * 55  # >= RATIONALE_MIN_CHARS


def _real_config(tmp_path):
    """Copy of the real genre-config fixture (G0.9: no hand-crafted mocks)."""
    src = Path(__file__).parents[2] / "fixtures" / "genre-config-example.json"
    cfg = json.loads(src.read_text(encoding="utf-8"))
    (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


class TestRule1BypassVectors:
    def test_whole_key_object_overwrite_blocked(self, tmp_path):
        cfg = _real_config(tmp_path)
        victim = {k: False for k in ("texture", "antiAi", "continuity")}
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions": victim}, rationale="none")

    def test_falsy_zero_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions.texture": 0}, rationale="none")

    def test_snake_case_key_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(
                tmp_path, {"audit_dimensions.texture": False}, rationale="none"
            )

    def test_malformed_scalar_change_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"auditDimensions": False}, rationale=_LONG)

    def test_valid_disable_with_rationale_passes(self, tmp_path):
        _real_config(tmp_path)
        update_genre_config(tmp_path, {"auditDimensions.texture": False}, rationale=_LONG)
        trail = (tmp_path / AUDIT_TRAIL_NAME).read_text(encoding="utf-8")
        assert '"key": "auditDimensions.texture"' in trail


class TestRule2TypeGuard:
    def test_float_below_trigger_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": 59.5}, rationale=_LONG)

    def test_string_floor_blocked(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(tmp_path, {"resonance_global_floor": "50"}, rationale=_LONG)

    def test_float_above_trigger_ok(self, tmp_path):
        _real_config(tmp_path)
        update_genre_config(tmp_path, {"resonance_global_floor": 60.0}, rationale=_LONG)


class TestTwoPhaseCommit:
    def test_mixed_batch_leaves_no_phantom_trail(self, tmp_path):
        _real_config(tmp_path)
        with pytest.raises(ConfigError):
            update_genre_config(
                tmp_path,
                {"auditDimensions.dialogue": False, "auditDimensions.texture": False},
                rationale="short",
            )
        assert not (tmp_path / AUDIT_TRAIL_NAME).exists()
        # config unchanged too
        cfg = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert cfg["auditDimensions"]["dialogue"] is True
```

（`from pathlib import Path` 若未导入则加。）

- [ ] **Step 6: 跑测试确认失败**

`uv run pytest tests/unit/config/test_config_coherence.py -q` → 红相用例：4 个 bypass 向量 + `test_mixed_batch_leaves_no_phantom_trail` + Rule 2 的 float/str 拦截。注：`test_valid_disable_with_rationale_passes`（dotted-key texture: False + 长 rationale）与 `test_float_above_trigger_ok`（60.0）今日已绿——回归锚，非红相。

- [ ] **Step 7: 重写 update_genre_config 校验逻辑**

`config_coherence.py`：imports 增 `import copy` 与 `resolve_audit_dimensions`；新增模块常量与 helper：

```python
_AUDIT_DIM_ROOTS = frozenset({"auditDimensions", "audit_dimensions"})


def _touches_audit_dimensions(key: str) -> bool:
    return key.split(".")[0] in _AUDIT_DIM_ROOTS


def _validate_changes(
    old_config: dict[str, Any],
    staged: dict[str, Any],
    changes: dict[str, Any],
    rationale: str,
) -> None:
    """Validate ALL changes against the staged (all-applied) config. Raises ConfigError.

    注：snake_case 键写入与既有 camelCase 键并存时 camel-wins 合并会使该写入
    成为静默 no-op（校验评估的是 camel 值）——本函数不另行告警，属声明的合并语义。
    """
    if any(_touches_audit_dimensions(k) for k in changes):
        old_dims, _old_bad = resolve_audit_dimensions(old_config)
        merged, malformed = resolve_audit_dimensions(staged)
        if malformed:
            raise ConfigError(
                "auditDimensions must be an object mapping dimension -> bool, "
                "got a scalar/list value; refusing to apply."
            )
        # delta 语义（audit-T1 定稿）：禁用企图 = 显式 falsy 值，或整键覆写
        # 显式移除已声明键；新旧皆缺失 = 无变化（缺失=启用，仅整文件 diff 路径管辖）
        for dim in AUDIT_SAFETY_MATRIX:
            if not is_critical_audit_dimension(dim):
                continue
            was_enabled = old_dims.get(dim, True) is True
            explicit_falsy = dim in merged and merged[dim] is not True
            explicit_removal = dim in old_dims and dim not in merged
            if (
                was_enabled
                and (explicit_falsy or explicit_removal)
                and len(rationale) < RATIONALE_MIN_CHARS
            ):
                raise ConfigError(
                    f"Cannot disable critical audit '{dim}' without "
                    f">= {RATIONALE_MIN_CHARS} char rationale explaining the "
                    f"alternative detection mechanism. detects: "
                    f"{AUDIT_SAFETY_MATRIX[dim]['detects']}"
                )
    for key, new_value in changes.items():
        if key == "resonance_global_floor":
            if isinstance(new_value, bool) or not isinstance(new_value, (int, float)):
                raise ConfigError(
                    f"floor_not_numeric:resonance_global_floor={new_value!r} "
                    f"(expected int/float, got {type(new_value).__name__})"
                )
            if new_value < DEFAULT_THRESHOLDS.resonance_revision_trigger:
                raise ConfigError(
                    f"floor_too_low:resonance_global_floor={new_value} < revision trigger "
                    f"{DEFAULT_THRESHOLDS.resonance_revision_trigger}. Floors below the "
                    f"trigger allow degraded chapters to pass without revision."
                )
```

`update_genre_config` 主体改为两阶段：

```python
    config = _load_config(project_dir)

    # Phase 1: stage all changes on a copy and validate — no side effects yet (F614).
    staged = copy.deepcopy(config)
    for key, new_value in changes.items():
        _set_nested(staged, key, new_value)
    _validate_changes(config, staged, changes, rationale)

    # Phase 2: commit — write config, then append trail entries.
    entries = [(key, _get_nested(config, key), value) for key, value in changes.items()]
    safe_write(
        project_dir / "genre-config.json",
        json.dumps(staged, ensure_ascii=False, indent=2),
    )
    for key, old_value, new_value in entries:
        _append_audit_trail(project_dir, key, old_value, new_value, rationale)
        log.info(
            "config_changed", key=key, old=old_value, new=new_value, rationale=rationale
        )
```

同时更新模块 docstring：注明生产更新路径为 `govern_genre_config_change`（Task 5），本函数为库 API。

- [ ] **Step 8: 全量跑该文件测试确认通过**

`uv run pytest tests/unit/config/ -q --no-cov` → PASS（含存量用例；存量 `{"resonance_global_floor": 70}` int 用例不受影响）

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/config/thresholds.py src/shenbi/config/config_coherence.py tests/unit/config/test_thresholds.py tests/unit/config/test_config_coherence.py
git commit -m "fix: unified Rule 1/2 with shared resolver + two-phase commit (spec 13 R1/R3/R5 write side)"
```

---

### Task 2: G0 读侧统一（R1 读侧 + R2 + R3 读侧）+ audit_layer critical 默认启用

**Files:**
- Modify: `src/shenbi/gates/g0_config_coherence.py`
- Modify: `src/shenbi/gates/g0.py`（cc 调用点传 floor）
- Modify: `src/shenbi/pipeline/audit_layer.py`（`get_active_genre_audits`）
- Test: `tests/unit/gates/test_g0_config_coherence.py`、`tests/unit/pipeline/test_audit_layer.py`

**Interfaces:**
- Consumes: `resolve_audit_dimensions`（Task 1）
- Produces: `check_config_coherence(project_dir, *, resonance_global_floor: int | float | None = None) -> list[str]`——`G0.cc.malformed_audit_dimensions` / `G0.cc.critical_audit_disabled:<dim>`（键存在且 `is not True`）/ floor 检查带类型守卫
- Produces: `get_active_genre_audits` 语义：critical 维度（texture）`get(dim_key, True)`；判活统一 `value is True`

- [ ] **Step 1: 写失败测试（G0 读侧）**

追加到 `tests/unit/gates/test_g0_config_coherence.py`：

```python
class TestGovernanceReadSide:
    def _write(self, tmp_path, dims):
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"version": "1.0", "auditDimensions": dims}), encoding="utf-8"
        )

    def test_scalar_audit_dimensions_loud_fail_not_crash(self, tmp_path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"auditDimensions": False}), encoding="utf-8"
        )
        issues = check_config_coherence(tmp_path)
        assert any("malformed_audit_dimensions" in i for i in issues)

    def test_falsy_zero_flagged(self, tmp_path):
        self._write(tmp_path, {"texture": 0})
        issues = check_config_coherence(tmp_path)
        assert any("critical_audit_disabled:texture" in i for i in issues)

    def test_truthy_one_flagged(self, tmp_path):
        self._write(tmp_path, {"texture": 1})
        issues = check_config_coherence(tmp_path)
        assert any("critical_audit_disabled:texture" in i for i in issues)

    def test_snake_case_flagged(self, tmp_path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"audit_dimensions": {"texture": False}}), encoding="utf-8"
        )
        issues = check_config_coherence(tmp_path)
        assert any("critical_audit_disabled:texture" in i for i in issues)

    def test_missing_critical_not_flagged(self, tmp_path):
        self._write(tmp_path, {"dialogue": True})
        issues = check_config_coherence(tmp_path)
        assert not any("critical_audit_disabled" in i for i in issues)

    def test_float_floor_below_trigger_flagged(self, tmp_path):
        issues = check_config_coherence(tmp_path, resonance_global_floor=59.5)
        assert any("floor_too_low" in i for i in issues)

    def test_string_floor_flagged_not_crash(self, tmp_path):
        issues = check_config_coherence(tmp_path, resonance_global_floor="50")  # type: ignore[arg-type]
        assert any("floor_invalid_type" in i for i in issues)
```

（`json`、`check_config_coherence` 按 conftest 既有导入方式补。）

- [ ] **Step 2: 跑测试确认失败**

`uv run pytest tests/unit/gates/test_g0_config_coherence.py -q --no-cov` → 真红用例：`test_scalar_audit_dimensions_loud_fail_not_crash`（AttributeError）、`test_falsy_zero_flagged`、`test_truthy_one_flagged`、`test_snake_case_flagged`、`test_string_floor_flagged_not_crash`（TypeError）。注：`test_float_floor_below_trigger_flagged`（59.5）与 `test_missing_critical_not_flagged` 今日已绿——它们是回归锚，非红相（勿误判）。

- [ ] **Step 3: 改 checker**

`g0_config_coherence.py` Check 3 替换为（**保留既有 `isinstance(config, dict)` 守卫**——顶层非 dict（如 list）不得让 `.get` 抛 AttributeError 逃出 g0.py 的窄 except，F666 同类守卫）：

```python
        from shenbi.config.thresholds import resolve_audit_dimensions

        if not isinstance(config, dict):
            malformed = True  # 顶层非 dict（如 list）也属 malformed——响亮失败而非静默空过
            audit_dims: dict[str, object] = {}
        else:
            audit_dims, malformed = resolve_audit_dimensions(config)
        if malformed:
            issues.append(
                "G0.cc.malformed_audit_dimensions — auditDimensions must be an "
                "object mapping dimension -> bool; got a scalar/list value. "
                "All genre audits are effectively disabled by this shape."
            )
        else:
            for dim, detects in _CRITICAL_DIMENSIONS.items():
                # Key absent = enabled (criticality-split semantics); any
                # present-but-not-True value counts as disabling (0/null/""/1).
                if dim in audit_dims and audit_dims[dim] is not True:
                    cannot_disable = AUDIT_SAFETY_MATRIX[dim].get(
                        "cannot_disable_without", "explicit human approval"
                    )
                    issues.append(
                        f"G0.cc.critical_audit_disabled:{dim} — disabling this "
                        f"removes: {detects}. This is a quality safety net. "
                        f"Cannot disable without {cannot_disable}."
                    )
```

（import 移到文件头与 thresholds 其他 import 并列。）Check 1 & 2 前置类型守卫：

```python
    if resonance_global_floor is not None:
        if isinstance(resonance_global_floor, bool) or not isinstance(
            resonance_global_floor, (int, float)
        ):
            issues.append(
                f"G0.cc.floor_invalid_type:resonance_global_floor="
                f"{resonance_global_floor!r} ({type(resonance_global_floor).__name__}) — "
                f"expected int/float"
            )
        else:
            ...既有 threshold_mismatch / floor_too_low 两检查不变...
```

签名从 `int | float | None = None` 放宽（现 `int | None`；str 场景仅在防御性守卫测试中出现，测试侧以 `# type: ignore[arg-type]` 传入；mypy 只跑 src/，basedpyright 认 type: ignore）。

- [ ] **Step 4: g0.py 调用点补线（floor 死线）**

`g0.py` cc 循环内（现 `cc_issues = check_config_coherence(project_dir)` 处）：

```python
            floor: int | float | None = None
            state_path = project_dir / "pipeline-state.json"
            if state_path.exists():
                try:
                    state_data = json.loads(state_path.read_text(encoding="utf-8"))
                    raw_floor = state_data.get("config", {}).get(
                        "resonance_global_floor"
                    )
                    if isinstance(raw_floor, (int, float)) and not isinstance(raw_floor, bool):
                        floor = raw_floor
                except (OSError, json.JSONDecodeError):
                    log.debug("g0_state_read_failed_for_floor", path=str(state_path))
            cc_issues = check_config_coherence(project_dir, resonance_global_floor=floor)
```

- [ ] **Step 5: 写失败测试（audit_layer critical 缺失=启用 + is True 判活）**

追加到 `tests/unit/pipeline/test_audit_layer.py`：

```python
class TestCriticalitySplitActivation:
    def test_missing_texture_still_activates(self):
        # Derived from the real fixture's auditDimensions shape (G0.9).
        active = get_active_genre_audits({"auditDimensions": {"dialogue": True}})
        assert "shenbi-review-texture" in active

    def test_truthy_one_does_not_activate(self):
        active = get_active_genre_audits({"auditDimensions": {"texture": 1, "dialogue": True}})
        assert "shenbi-review-texture" not in active

    def test_snake_case_still_honored(self):
        active = get_active_genre_audits({"audit_dimensions": {"dialogue": True}})
        assert "shenbi-review-dialogue" in active
```

- [ ] **Step 6: 跑测试确认失败**

`uv run pytest tests/unit/pipeline/test_audit_layer.py -q --no-cov` → `test_missing_texture_still_activates` FAIL（现状缺失=不激活）

- [ ] **Step 7: 改 get_active_genre_audits**

```python
def get_active_genre_audits(genre_config: Mapping[str, object]) -> list[str]:
    audit_dims, malformed = resolve_audit_dimensions(genre_config)
    if malformed:
        return []

    def _live(dim_key: str) -> bool:
        if dim_key in _CRITICAL_GENRE_DIMS:
            return audit_dims.get(dim_key, True) is True
        return audit_dims.get(dim_key, False) is True

    return sorted(
        skill
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items()
        if dim_key not in _CORE_CIRCLE_KEYS and _live(dim_key)
    )
```

`_CRITICAL_GENRE_DIMS` 模块级常量（`audit_layer.py` 顶部，imports 加 `from shenbi.config.thresholds import resolve_audit_dimensions`）：

```python
#: Critical dims that appear in the genre activation matrix (texture only —
#: antiAi/continuity are core-circle keys). Missing = enabled (criticality split).
_CRITICAL_GENRE_DIMS = frozenset(
    d for d in ("texture",) if d in GENRE_ACTIVATION_MATRIX
)
```

- [ ] **Step 8: 全量相关测试**

`uv run pytest tests/unit/gates/test_g0_config_coherence.py tests/unit/gates/test_g0.py tests/unit/pipeline/test_audit_layer.py tests/unit/config/ -q --no-cov` → PASS（存量 G0/audit_layer 用例无回归）

g0.py floor 补线另加直测（`tests/unit/gates/test_g0.py` 追加，沿用该文件既有 tmp 项目构造方式）：

```python
def test_g0_cc_reads_state_floor(tmp_path, monkeypatch):
    """g0.py cc loop passes PipelineState floor (was dead — spec 13 R1 read side)."""
    import shenbi.gates.g0 as g0_mod

    monkeypatch.setattr(g0_mod, "PROJECT", tmp_path)  # gate_G0 扫 PROJECT/novel-output
    proj = tmp_path / "novel-output" / "p1"
    proj.mkdir(parents=True)
    (proj / "genre-config.json").write_text("{}", encoding="utf-8")
    (proj / "pipeline-state.json").write_text(
        json.dumps({"config": {"resonance_global_floor": 55}}), encoding="utf-8"
    )
    result = gate_G0(...)  # 按该文件既有 gate_G0 调用签名
    assert "floor_too_low:resonance_global_floor=55" in json.dumps(result)
```

（gate_G0 调用签名按 test_g0.py 既有用例照抄；红相 = 修 g0.py 前结果中无该 issue。）

Task 4 注记（g2 免改声明）：spec R4 列的 g2.py 触点无需改代码——g2 decisions 分支整体委托 `DecisionsDoc.model_validate`（g2.py:160），schema 放宽自动覆盖；在 spec-deviations 记一句防审查误报。

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/gates/g0_config_coherence.py src/shenbi/gates/g0.py src/shenbi/pipeline/audit_layer.py tests/unit/gates/test_g0_config_coherence.py tests/unit/pipeline/test_audit_layer.py
git commit -m "fix: G0 read-side unified semantics — malformed loud-fail, is-not-True, criticality split, floor wiring (spec 13 R1/R2/R3 read side)"
```

---

### Task 3: G4 组合 checker 按文件名分区 + 反向注册规范化（R4a′）

**Files:**
- Modify: `src/shenbi/gates/g4/decisions_validator.py`（g4_decisions 收窄 + make_composite_checker 分区）
- Modify: `src/shenbi/gates/g4/generic.py:333`（反向注册规范化）+ `:310`（genre-config 组合注册）
- Test: `tests/unit/gates/g4/`（新增/扩充）

**Interfaces:**
- Produces: `make_composite_checker` 分区规则 = `*-decisions.json` → decisions checker；其余（含 `.md` 与非-decisions `.json`）→ existing checker
- Produces: `gate_G4("shenbi-genre-config", ["genre-config.json", "genre-config-decisions.json"], ...)` 组合校验（config 走 GenreConfig 模型、sidecar 走 DecisionsDoc）

- [ ] **Step 1: 写失败测试**

`tests/unit/gates/g4/test_composite_partition.py`（新文件；sidecar 用**今日可过 DecisionsDoc 的形态**（含 chapter: 1），路由断言锚定 per-file check 条目而非顶层 result 名——`g4_decisions([])` 的 SKIP 也含 "G4-decisions" 字样，顶层断言是空洞的）：

```python
"""Filename-partition semantics of make_composite_checker (spec 13 R4a')."""
import json

from shenbi.gates.g4.decisions_validator import make_composite_checker


def _structural_stub(fps, rd, project_dir, repo_root):
    """Records what the structural slot received; per-file PASS entries."""
    from shenbi.gates.shared import passed as _p

    return _p(
        "stub-structural",
        [{"id": f"stub-structural:{fp}", "s": "PASS"} for fp in (fps or [])],
    )


_VALID_SIDECAR = {
    "$schema": "shenbi-decisions-v1",
    "skill": "shenbi-genre-config",
    "chapter": 1,
    "selections": [],
    "adjustments": [],
    "produced_at": "2026-08-29T00:00:00",
}


class TestFilenamePartition:
    def test_non_decisions_json_routes_to_structural(self, tmp_path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"version": "1.0", "auditDimensions": {"texture": True}}),
            encoding="utf-8",
        )
        from shenbi.gates.g4.decisions_validator import g4_decisions

        composite = make_composite_checker(_structural_stub, g4_decisions)
        result = composite(["genre-config.json"], str(tmp_path), None, None)
        data = json.loads(result)
        # structural stub saw the file; decisions checker saw none (SKIP not FAIL)
        assert any("genre-config.json" in c.get("id", "") for c in data["checks"])
        assert data["status"] == "PASS"

    def test_decisions_json_routes_to_decisions_checker(self, tmp_path):
        (tmp_path / "genre-config-decisions.json").write_text(
            json.dumps(_VALID_SIDECAR), encoding="utf-8"
        )
        from shenbi.gates.g4.decisions_validator import g4_decisions

        composite = make_composite_checker(_structural_stub, g4_decisions)
        result = composite(["genre-config-decisions.json"], str(tmp_path), None, None)
        data = json.loads(result)
        # decisions checker validated the sidecar (per-file PASS entry)
        assert any(
            c.get("file") == "genre-config-decisions.json" and c.get("s") == "PASS"
            for c in data["checks"]
        )
        # structural stub saw nothing
        assert all("genre-config-decisions" not in c.get("id", "") for c in data["checks"])
```

（Task 4 落地后 sidecar 的 chapter 可为 null；本测试用 chapter: 1 与 Task 4 解耦。）

（stub checker 以本地小函数实现：structural stub 断言收到的 fps、decisions 用真 `g4_decisions`；具体 stub 代码在实现时按 `G4CheckerFn` 四参签名写，返回 `passed(...)`。）

追加到 `tests/unit/gates/test_g4_signatures.py`（或同级新用例）：

```python
def test_chapter_revision_registration_order():
    """generic.py:333 must register (structural, decisions) — not reversed (spec 13)."""
    import inspect

    import shenbi.gates.g4.generic as g

    src = inspect.getsource(g)
    assert 'make_composite_checker(g4_decisions, g4_chapter_revision)' not in src
    assert 'make_composite_checker(g4_chapter_revision, g4_decisions)' in src
```

- [ ] **Step 2: 跑测试确认失败** → FAIL（现行分区按扩展名；generic.py:333 反向）

- [ ] **Step 3: 实现**

`make_composite_checker` 内分区替换：

```python
        # Partition by filename: *-decisions.json → decisions checker;
        # everything else (incl. non-decisions .json like genre-config.json)
        # → existing/structural checker. Structural checkers that receive a
        # .json they cannot parse must fail loudly on their own terms —
        # audited per-consumer (spec 13 R4a').
        decisions_files = [fp for fp in fps if fp.endswith("-decisions.json")]
        other_files = [fp for fp in fps if not fp.endswith("-decisions.json")]

        existing_result = existing_checker(other_files, rd, project_dir, repo_root)
        decisions_result = decisions_checker(decisions_files, rd, project_dir, repo_root)
```

`g4_decisions` 的 `.json` 跳过改为 `-decisions.json` 匹配（`if not fp.endswith("-decisions.json"): continue`），注释同步。`generic.py:333` 改 `make_composite_checker(g4_chapter_revision, g4_decisions)`；`:310` 改 `make_composite_checker(g4_genre_config, g4_decisions)`。**显式行为变更注记**：旧分区把非-.md/.json 的 "other" 文件送双 checker，新分区只送 existing/structural checker（decisions checker 不再看 other）——记入 spec-deviations 并纳入下述消费者审计。逐一核对其余 4 个 composite（chapter-drafting/planning/context-composing/state-settling）现存 G4 调用文件集（grep 调用方 + triggers/chapter_loop 传参）确认仅 `.md` + `*-decisions.json`、无 other 文件——记录到 spec-deviations。

- [ ] **Step 4: 跑 g4 全量**

`uv run pytest tests/unit/gates/g4 tests/unit/gates/test_g4_signatures.py -q --no-cov` → PASS（含存量 chapter-revision 用例——其 .md 现在正确走结构 checker、sidecar 走 DecisionsDoc；有存量断言依赖旧错乱路由则按新语义修正测试并记 deviation）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/decisions_validator.py src/shenbi/gates/g4/generic.py tests/unit/gates/g4/test_composite_partition.py tests/unit/gates/test_g4_signatures.py
git commit -m "fix: composite G4 filename partition + normalize reversed chapter-revision registration (spec 13 R4a')"
```

---

### Task 4: decisions schema chapter 可空 + genre-config skill sidecar 契约（R4 前置）

**Files:**
- Modify: `src/shenbi/contracts/schemas/decisions.py:76`（`chapter: int | None = None`）
- Modify: `docs/framework/decisions-schema.md`（chapter 可空说明）
- Modify: `skills/shenbi-genre-config/SKILL.md`（契约 writes + 正文指引：禁用 critical 维度须产 manual_override selection + 50-100 字 rationale）
- Test: `tests/unit/gates/test_g4_decisions.py`、`tests/unit/contracts/`（若有无_decisions schema 直测则就地）
- Regenerate: `just generate`（deps.json/docs 同步）

**Interfaces:**
- Produces: `DecisionsDoc.chapter: int | None`（None = 非章节型 skill，如 shenbi-genre-config）
- Produces: skill 契约 `writes: [genre-config-decisions.json]`（kind 不变 artifact）

- [ ] **Step 1: 写失败测试**

```python
def test_decisions_doc_chapter_optional():
    doc = DecisionsDoc.model_validate(
        {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-genre-config",
            "selections": [
                {
                    "target": "auditDimensions.texture",
                    "selected": ["disabled"],
                    "basis": "manual_override",
                    "rationale": "替代检测机制：每卷手动感官密度复查，由人工按 checklist 执行",
                }
            ],
            "produced_at": "2026-08-29T00:00:00",
        }
    )
    assert doc.chapter is None
```

- [ ] **Step 2: 确认失败** → FAIL（chapter missing）

- [ ] **Step 3: 实现 schema 放宽 + 文档 + skill 契约**

`decisions.py`: `chapter: int | None = None`（docstring 一句：非章节型 skill 省略）。`decisions-schema.md` 对应字段说明加「可空——非章节型 skill（如 genre-config 更新）省略」。

`SKILL.md` frontmatter：

```yaml
  writes:
  - file: genre-config-decisions.json
    mode: create_or_overwrite
```

正文「铁律」后新增一节：

```markdown
## 决策留痕（decisions sidecar）

每次配置变更输出 `genre-config-decisions.json`（schema `shenbi-decisions-v1`，
非章节型：无 chapter 字段）。禁用/删除 critical 审计维度（texture/antiAi/continuity）
时，必须包含一条 `selections[]` 条目：`basis: manual_override`，rationale 为
50-100 字的合并变更理由（说明替代检测机制）——治理层据此放行，缺失或不足
50 字整次更新被拒绝回滚。
```

跑 `just generate` + `just lint-contracts`，确认生成物 diff 只含预期同步。

- [ ] **Step 4: 跑测试 + 契约门**

`uv run pytest tests/unit/gates/test_g4_decisions.py tests/unit/contracts -q --no-cov` → PASS；`just lint-contracts` 绿；`just check-contracts-sync`（或 `just check` 的 contract-sync 段）diff 为空

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/schemas/decisions.py docs/framework/decisions-schema.md skills/shenbi-genre-config/SKILL.md <generated files>
git commit -m "feat: decisions chapter optional for non-chapter skills + genre-config decisions sidecar contract (spec 13 R4 prerequisite)"
```

---

### Task 5: 治理接线 govern_genre_config_change + snapshot/全阶段回滚（R4 + R5 生产路径）

**Files:**
- Modify: `src/shenbi/config/config_coherence.py`（新增 `govern_genre_config_change`）
- Modify: `src/shenbi/pipeline/triggers.py`（genre_config_update step 专用钩子）
- Test: `tests/unit/config/test_config_coherence.py`、`tests/unit/pipeline/test_triggers.py`

**Interfaces:**
- Consumes: `resolve_audit_dimensions`、`ConfigError`、`_append_audit_trail`、`RATIONALE_MIN_CHARS`
- Produces: `govern_genre_config_change(project_dir: Path, old_config: dict[str, Any], new_config: dict[str, Any], rationale: str) -> None`——diff 中 critical 维度被禁用/删除且 rationale <50 字 → `ConfigError`（无副作用）；通过 → 追加 audit trail（rationale >500 字 ConfigError）

- [ ] **Step 1: 写失败测试（govern 函数单测）**

```python
from shenbi.config.config_coherence import govern_genre_config_change


class TestGovernGenreConfigChange:
    def _pair(self, tmp_path):
        cfg = _real_config(tmp_path)  # Task 1 的 helper
        # 真实 fixture 的 texture 本为 false（含 rationale 的真实禁用案例）；
        # 治理测试需要 enabled→disabled 方向，先翻 True（spec R2 fixture 注记）
        cfg["auditDimensions"]["texture"] = True
        (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return cfg, copy.deepcopy(cfg)

    def test_disable_critical_without_rationale_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="short")

    def test_delete_critical_key_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        del new["auditDimensions"]["texture"]
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="short")

    def test_rationale_over_500_rejected(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        with pytest.raises(ConfigError):
            govern_genre_config_change(tmp_path, old, new, rationale="y" * 501)

    def test_valid_change_appends_trail(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["auditDimensions"]["texture"] = False
        govern_genre_config_change(tmp_path, old, new, rationale=_LONG)
        trail = (tmp_path / AUDIT_TRAIL_NAME).read_text(encoding="utf-8")
        assert '"key": "auditDimensions.texture"' in trail

    def test_no_dim_change_no_trail(self, tmp_path):
        old, new = self._pair(tmp_path)
        new["updated"] = "2026-08-30"
        govern_genre_config_change(tmp_path, old, new, rationale="routine date bump")
        assert not (tmp_path / AUDIT_TRAIL_NAME).exists()
```

- [ ] **Step 2: 确认失败** → FAIL（ImportError）

- [ ] **Step 3: 实现 govern_genre_config_change（config_coherence.py）**

```python
_TRAIL_RATIONALE_MAX_CHARS = 500


def govern_genre_config_change(
    project_dir: Path,
    old_config: dict[str, Any],
    new_config: dict[str, Any],
    rationale: str,
) -> None:
    """Govern a whole-file genre-config overwrite (production update path).

    Compares resolved audit dimensions old vs new; any critical dimension
    disabled or deleted requires a >=RATIONALE_MIN_CHARS rationale (F635/F643).
    Appends one trail entry per governed dimension change on success. Raises
    ConfigError with no side effects on violation (two-phase, F614).
    """
    if len(rationale) > _TRAIL_RATIONALE_MAX_CHARS:
        raise ConfigError(
            f"rationale exceeds {_TRAIL_RATIONALE_MAX_CHARS} chars; produce one "
            f"merged 50-100 char rationale instead"
        )
    old_dims, _old_bad = resolve_audit_dimensions(old_config)
    new_dims, new_bad = resolve_audit_dimensions(new_config)
    if new_bad:
        raise ConfigError(
            "auditDimensions must be an object mapping dimension -> bool; "
            "refusing ungoverned overwrite."
        )
    changed: list[tuple[str, Any, Any]] = []
    for dim in AUDIT_SAFETY_MATRIX:
        if not is_critical_audit_dimension(dim):
            continue
        # diff 语境：删除 critical 键 = 禁用企图（spec R2——与运行侧「缺失=启用」
        # 是有意的语义分裂：diff 看「显式移除」，运行看「终局是否仍护网」）
        new_v = new_dims.get(dim, False)
        old_v = old_dims.get(dim, False)
        if new_v is not True and old_v is True:
            if len(rationale) < RATIONALE_MIN_CHARS:
                raise ConfigError(
                    f"Cannot disable critical audit '{dim}' without "
                    f">= {RATIONALE_MIN_CHARS} char rationale explaining the "
                    f"alternative detection mechanism."
                )
            changed.append((f"auditDimensions.{dim}", old_v, new_v))
    for key, old_v, new_v in changed:
        _append_audit_trail(project_dir, key, old_v, new_v, rationale)
```

（`_real_config`/`copy` 已在 Task 1 就位。残余注记：`_append_audit_trail` 自身中途失败的 partial-trail 是接受的残余风险——R5 幻影条目保证已接线于 update_genre_config 的两阶段与 govern 的先校验后追加，追加循环自身 IO 失败不在本 spec 语义内。整键覆写产生的单条 trail 的 old/new 为整个 dict——注释说明即可，grep 键名仍可行。）

- [ ] **Step 4: 跑单测** → PASS

- [ ] **Step 5: 写失败测试（触发器集成：快照/回滚/接线）**

`tests/unit/pipeline/test_triggers.py` 追加（沿用该文件既有 `@patch`/TriggerResult 构造模式；**两个 helper 需新建**，勿在存量里找：`FIXTURE = Path(__file__).parents[2] / "fixtures" / "genre-config-example.json"`；`_genre_config_trigger_result()` 返回 `TriggerResult(genre_config_update=True)` 按 test_triggers.py 既有 dataclass 构造）。monkeypatch `dispatch_skill` 与 `run_gate_g4` 为可控 stub——管线级单测对 dispatch 的 stub 是既有测试模式，非 LLM 产物 mock。第一支测试写**短 rationale 的 sidecar**（真实 skill 输出形态：<50 字被拒），与「无 sidecar」支区分：

```python
class TestGenreConfigGovernanceWiring:
    def test_rejected_update_rolls_back(self, tmp_path, monkeypatch):
        # old config on disk with texture: true
        cfg = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cfg["auditDimensions"]["texture"] = True
        (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        bad = copy.deepcopy(cfg)
        bad["auditDimensions"]["texture"] = False
        # sidecar 存在但 rationale < 50 字（真实 skill 输出形态）
        sidecar = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-genre-config",
            "selections": [
                {
                    "target": "auditDimensions.texture",
                    "selected": ["disabled"],
                    "basis": "manual_override",
                    "rationale": "太短了",
                }
            ],
            "produced_at": "2026-08-29T00:00:00",
        }

        def fake_dispatch(skill, project_dir, prompt):
            (Path(project_dir) / "genre-config.json").write_text(
                json.dumps(bad), encoding="utf-8"
            )
            (Path(project_dir) / "genre-config-decisions.json").write_text(
                json.dumps(sidecar), encoding="utf-8"
            )
            return SimpleNamespace(success=True)

        monkeypatch.setattr("shenbi.pipeline.triggers.dispatch_skill", fake_dispatch)
        monkeypatch.setattr(
            "shenbi.pipeline.triggers.run_gate_g4",
            lambda *a, **k: {"status": "PASS", "checks": []},  # dict（run_gate_g4 返回 dict）
        )
        # build a TriggerResult whose only step is the genre_config_update step
        result = _genre_config_trigger_result()  # helper per既有构造
        state = PipelineState.default(str(tmp_path))
        ok = run_triggered_skills(state, tmp_path, chapter=6, result=result)
        assert ok is False
        assert state.last_trigger_failure["stage"] == "governance"
        # rolled back: on-disk config == old
        now = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert now["auditDimensions"]["texture"] is True
        assert not (tmp_path / "config-change-log.jsonl").exists()

    def test_sidecar_missing_rolls_back(self, tmp_path, monkeypatch):
        """无 sidecar → rationale 空 → governance ConfigError → 回滚 + last_trigger_failure。"""
        cfg = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cfg["auditDimensions"]["texture"] = True
        (tmp_path / "genre-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        bad = copy.deepcopy(cfg)
        bad["auditDimensions"]["texture"] = False

        def fake_dispatch(skill, project_dir, prompt):
            (Path(project_dir) / "genre-config.json").write_text(
                json.dumps(bad), encoding="utf-8"
            )
            return SimpleNamespace(success=True)

        monkeypatch.setattr("shenbi.pipeline.triggers.dispatch_skill", fake_dispatch)
        monkeypatch.setattr(
            "shenbi.pipeline.triggers.run_gate_g4",
            lambda *a, **k: {"status": "PASS", "checks": []},
        )
        result = _genre_config_trigger_result()
        state = PipelineState.default(str(tmp_path))
        ok = run_triggered_skills(state, tmp_path, chapter=6, result=result)
        assert ok is False
        now = json.loads((tmp_path / "genre-config.json").read_text(encoding="utf-8"))
        assert now["auditDimensions"]["texture"] is True
        assert not (tmp_path / "config-change-log.jsonl").exists()
```

- [ ] **Step 6: 确认失败** → FAIL（现状无治理钩子，ok 可能为 True 或失败但无回滚）

- [ ] **Step 7: 实现 triggers.py 钩子**

`run_triggered_skills` 循环内，G4 段前后插入 genre_config_update 专用逻辑（示意，落位与既有代码风格对齐）：

```python
        is_gc_update = step.category == "genre_config_update"
        gc_snapshot: str | None = None
        if is_gc_update:
            gc_path = project_dir / "genre-config.json"
            gc_snapshot = gc_path.read_text(encoding="utf-8") if gc_path.exists() else None

        disp = dispatch_skill(...)  # 既有
        if not disp.success:
            ...既有 last_trigger_failure...
            if is_gc_update:
                _rollback_genre_config(project_dir, gc_snapshot)
            return False

        g4_files = [g4_file] if g4_file else []
        if is_gc_update:
            # 固定文件名，无需 resolve_contract_path（记 deviation：spec 的「同 output_path 待遇」
            # 对该无 token 字面名等价直传）
            g4_files.append("genre-config-decisions.json")
        g4 = run_gate_g4(step.skill, g4_files, project_dir)
        if not _gate_passed(g4):
            ...既有 last_trigger_failure(stage="g4")...
            if is_gc_update:
                _rollback_genre_config(project_dir, gc_snapshot)
            return False

        if is_gc_update:
            from shenbi.config.config_coherence import ConfigError, govern_genre_config_change

            gc_path = project_dir / "genre-config.json"
            old_cfg = json.loads(gc_snapshot) if gc_snapshot else {}
            new_cfg = (
                json.loads(gc_path.read_text(encoding="utf-8")) if gc_path.exists() else {}
            )
            rationale = _read_genre_config_rationale(project_dir)  # sidecar selections[] manual_override 合并
            try:
                govern_genre_config_change(project_dir, old_cfg, new_cfg, rationale)
            except ConfigError as exc:
                log.error("genre_config_governance_rejected", error=str(exc))
                state.last_trigger_failure = {
                    "chapter": chapter,
                    "skill": step.skill,
                    "mode": getattr(step, "mode", None),
                    "stage": "governance",
                    "timestamp": _iso_now(),
                }
                _rollback_genre_config(project_dir, gc_snapshot)
                return False
```

模块级 helpers：

```python
def _rollback_genre_config(project_dir: Path, snapshot: str | None) -> None:
    """Restore the pre-dispatch config; remove stale sidecar/bak artifacts (spec 13 R4c)."""
    gc_path = project_dir / "genre-config.json"
    if snapshot is not None:
        safe_write(gc_path, snapshot)
    else:
        # dispatch 前无配置：被拒的新配置也不得留盘（R4c 不变量）
        gc_path.unlink(missing_ok=True)
    for stale in project_dir.glob("genre-config-decisions.json"):
        stale.unlink()
    for bak in project_dir.glob("genre-config.json.bak.*"):
        bak.unlink()


def _read_genre_config_rationale(project_dir: Path) -> str:
    sidecar = project_dir / "genre-config-decisions.json"
    if not sidecar.exists():
        return ""
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    parts = [
        s.get("rationale") or ""
        for s in data.get("selections", [])
        if isinstance(s, dict) and s.get("basis") == "manual_override"
    ]
    return " ".join(p.strip() for p in parts if p.strip())
```

（imports：`json`、`safe_write` 按 triggers.py 既有导入情况补。）

- [ ] **Step 8: 全量相关测试**

`uv run pytest tests/unit/pipeline/test_triggers.py tests/unit/config/ -q --no-cov` → PASS（存量 triggers 用例不受影响——非 genre_config_update step 不走新分支）

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/config/config_coherence.py src/shenbi/pipeline/triggers.py tests/unit/config/test_config_coherence.py tests/unit/pipeline/test_triggers.py
git commit -m "feat: wire genre-config update path through diff governance with snapshot/rollback (spec 13 R4/R5)"
```

---

## 验收覆盖表（spec → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| R1 4 向量拦截（F611/F631/F666/F606） | T1+T2 | `uv run pytest tests/unit/config/test_config_coherence.py tests/unit/gates/test_g0_config_coherence.py -q` |
| R1 G0 标量 FAIL 非 AttributeError | T2 | `test_scalar_audit_dimensions_loud_fail_not_crash` |
| R2 删除 critical 键不静默停用 | T5 | `test_delete_critical_key_rejected` + `test_missing_texture_still_activates`（T2） |
| R3 snake_case 拦截 | T1+T2 | `test_snake_case_key_blocked` / `test_snake_case_flagged` |
| R4 更新产 audit trail / 无 rationale 拒绝+回滚 | T5 | `test_valid_change_appends_trail` / `test_rejected_update_rolls_back` |
| R5 混合批次无幻影 trail | T1 | `test_mixed_batch_leaves_no_phantom_trail` |

每 task 完成后跑其 Step 中命令并粘贴输出到 progress.md `## 验收证据`；全部 task 后跑 `just check`。
