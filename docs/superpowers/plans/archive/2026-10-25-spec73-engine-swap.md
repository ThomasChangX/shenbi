# Spec #73 大纲引擎置换与市场参数 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 四代入引擎从修辞变机制（story_frame 四引擎规则节）+ 市场参数进 genre-config schema（market_params 顶层新键四站 + G4 三态结构校验）+ rhythm_principles 收紧（铺垫 15-25%/拍表全表/单循环 19-36 章换算/每拍重量下限）。

**Architecture:** 双轨交付（#72 惯例）——框架面（schema 四站 + G4 校验 + 测试）进 PR；项目面（story_frame/genre-config/rhythm_principles 三文件内容）工作树交付（/novel-*/ gitignored），验收走本地 lint + 自查清单。四引擎规则文本以总设计 §1.1-1.5 为 normative 合同。

**Tech Stack:** pydantic（契约）/ pytest（tmp_path 构造 G0.9）/ 既有 GENRE_KEYS 四站模式（#72 primary_platform 先例）。

## Global Constraints（spec rev2 逐字约束）

- `market_params` 顶层新键（optional——存量 fixture 全兼容）；**三态校验语义：顶层缺块 PASS / 块内缺子键 FAIL / 越域 FAIL**
- 子键五项：`payoff_density {"window":3,"min":1}`（window∈[1,10]、min≥1）/ `emotion_band {"window":1,"min":1}` / `hook_grading {"max_consecutive_micro":2}`（[1,3]）/ `voice_density_min` + `meme_quota`（#76 定档前仅类型级校验）
- GENRE_KEYS 11→12 四站全清单：ownership.py（含 :4/:37 stale）+ genre_config.py + SKILL.md（:418 十一键→十二/:319 +3 可选→4/模板块）+ test_genre_config_platform:38 + test_ownership 键集 + test_genre_config.py:179-186 减集 + 顺手 stale 两处（test_dispatch_skill_write_audit:203/test_write_audit_diff_predicate:15）
- 拍表全表：铺垫 目标 20%（15-25）/升级 35%（30-45）/爆发 25%（20-30）/余波 20%（15-25）——两文件以此收敛
- 单循环 8-15→**19-36**（19=8×7600÷3200 精确；36=⌈35.625⌉）三处联动：rhythm :10/:17/:166 + genre-config pacing minChaptersPerCycle/maxChaptersPerCycle
- 红线四条自查：预知红线（含「救人靠组织」）/他人之死不可逆/账单不销账/rule-007 边界（智识小胜=世界内成果，不计现代知识碾压）
- 项目面 sidecar：`genre-config-decisions.json`（P2.5：medium 级调整带 rationale）
- 禁真实 dispatch；测试 tmp_path 构造；conventional commits

---

### Task 1: market_params schema 四站 + G4 三态结构校验

**复杂度: infra** · **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/contracts/ownership.py:4,:37,:40-54`（GENRE_KEYS 12 键 + stale 注释）
- Modify: `src/shenbi/contracts/skills/genre_config.py:23,:39,:49-67`（_OPTIONAL_TOP_KEYS + market_params 字段 + per-key 结构校验器）
- Modify: `skills/shenbi-genre-config/SKILL.md`（模板 market_params 块 + :319 可选计数 + :418 十二键 + :325 规则行 + :39/:69 站内枚举扫尾）
- Modify: `tests/unit/contracts/test_genre_config_platform.py:38`（12 键）/ `tests/unit/contracts/test_ownership.py`（键集）/ `tests/unit/gates/g4/test_genre_config.py:179-186`（减集 4 键）/ 顺手 stale 两处
- Test: `tests/unit/contracts/test_market_params.py`（新建）

**Interfaces:**
- Produces: `GenreConfig.market_params: dict[str, dict[str, int]] = {}`（optional 空缺省）+ `_market_params_structure` validator（块在场时逐键校验：payoff_density window∈[1,10]/min≥1；emotion_band 同式；hook_grading max_consecutive_micro∈[1,3]；voice_density_min/meme_quota 仅 dict+int 类型级）
- G4 面：`g4/genre_config.py` 复用 `model_validate`——三态由 schema 层承载（G4 断言 FAIL 消息含键名）

- [ ] **Step 1: 失败测试**

```python
# tests/unit/contracts/test_market_params.py
"""spec #73 T1: market_params 三态校验 + 四站键数。"""

import pytest
from shenbi.contracts.ownership import GENRE_KEYS
from shenbi.contracts.skills.genre_config import GenreConfig
from tests.unit.contracts.test_genre_config_platform import _base


@pytest.mark.unit
def test_genre_keys_twelve() -> None:
    assert "market_params" in GENRE_KEYS and len(GENRE_KEYS) == 12


@pytest.mark.unit
def test_absent_block_passes() -> None:
    GenreConfig.model_validate(_base())  # 顶层缺块 PASS（可选）


@pytest.mark.unit
def test_full_block_passes() -> None:
    cfg = GenreConfig.model_validate(
        _base()
        | {
            "market_params": {
                "payoff_density": {"window": 3, "min": 1},
                "emotion_band": {"window": 1, "min": 1},
                "hook_grading": {"max_consecutive_micro": 2},
                "voice_density_min": {"min_per_chapter": 2},
                "meme_quota": {"per_volume": 3},
            }
        }
    )
    assert cfg.market_params["payoff_density"]["window"] == 3


@pytest.mark.unit
def test_missing_subkey_fails() -> None:
    with pytest.raises(Exception, match="payoff_density"):
        GenreConfig.model_validate(
            _base()
            | {
                "market_params": {
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 2},
                    "voice_density_min": {"min_per_chapter": 2},
                    "meme_quota": {"per_volume": 3},
                }
            }
        )  # payoff_density 缺


@pytest.mark.unit
def test_out_of_range_fails() -> None:
    with pytest.raises(Exception, match="window"):
        GenreConfig.model_validate(
            _base()
            | {
                "market_params": {
                    "payoff_density": {"window": 99, "min": 1},
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 2},
                    "voice_density_min": {"min_per_chapter": 2},
                    "meme_quota": {"per_volume": 3},
                }
            }
        )
    with pytest.raises(Exception, match="max_consecutive_micro"):
        GenreConfig.model_validate(
            _base()
            | {
                "market_params": {
                    "payoff_density": {"window": 3, "min": 1},
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 9},
                    "voice_density_min": {"min_per_chapter": 2},
                    "meme_quota": {"per_volume": 3},
                }
            }
        )


@pytest.mark.unit
def test_g4_three_state_via_real_checker(tmp_path):
    # G4 genre_config 走 model_validate：三态经真实 checker 面
    from shenbi.gates.g4.genre_config import g4_genre_config
    import json

    base = _base()
    gc_ok = tmp_path / "genre-config.json"
    gc_ok.write_text(
        json.dumps(
            base
            | {
                "market_params": {
                    "payoff_density": {"window": 3, "min": 1},
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 2},
                    "voice_density_min": {"min_per_chapter": 2},
                    "meme_quota": {"per_volume": 3},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r = g4_genre_config([str(gc_ok)], rd=str(tmp_path))
    assert "market_params" not in r
    gc_bad = tmp_path / "genre-config-bad.json"
    gc_bad.write_text(
        json.dumps(
            base
            | {
                "market_params": {
                    "payoff_density": {"window": 99, "min": 1},
                    "emotion_band": {"window": 1, "min": 1},
                    "hook_grading": {"max_consecutive_micro": 2},
                    "voice_density_min": {"min_per_chapter": 2},
                    "meme_quota": {"per_volume": 3},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r2 = g4_genre_config([str(gc_bad)], rd=str(tmp_path))
    assert "market_params" in r2 or "window" in r2
```

（`g4_genre_config` 签名以 `src/shenbi/gates/g4/genre_config.py` 实际为准——实现时打开核对参数序。）

- [ ] **Step 2: 红** → `uv run pytest tests/unit/contracts/test_market_params.py -q`
- [ ] **Step 3: 实现四站**（ownership/genre_config/SKILL 模板+四行/三测试断言更新+两 stale 顺带）
- [ ] **Step 4: 绿 + 回归** → `uv run pytest tests/unit/contracts/ tests/unit/gates/g4/test_genre_config.py -q` + `just lint-contracts && just generate`（diff 空）
- [ ] **Step 5: 提交** `feat(contracts): spec73 T1——market_params 顶层新键四站 + G4 三态结构校验（无在途 artifacts 受影响：optional 键 + 存量 fixture 全兼容）`

---

### Task 2: 项目面三文件（story_frame 四引擎节 / genre-config 值 / rhythm 收紧）

**复杂度: infra（创作内容协调者亲自写）** · **test_kind: regression_guard（项目面文件 gitignored——验证走本地 lint + 结构断言脚本）**

**Files（全部工作树，/novel-*/ gitignored）:**
- Modify: `novel-xinghuo-vol1/outline/story_frame.md`（新增「段5：四代入引擎规则」——§1.1-1.4 normative 合同全承载 + 可测试锚点）
- Modify: `novel-xinghuo-vol1/genre-config.json`（market_params 五值 + pacing 19/36 + approval 块整体重写）
- Create: `novel-xinghuo-vol1/genre-config-decisions.json`（P2.5 rationale sidecar）
- Modify: `novel-xinghuo-vol1/outline/rhythm_principles.md`（:10/:17/:166 → 19-36 + 拍表 20/35/25/20 + 铺垫 15-25% + 每拍重量下限条款）

**Interfaces:**
- Consumes: T1 schema（market_params 五值须过 G4 三态）
- Produces: story_frame 段5 四引擎规则（每引擎可测试锚点：轮回代价=记忆三级排序+首渡已扣费声明；预知=节点/细节二分清单+变现起步金额（几十文级）+信用滚动句；欲望=卷一四级阶梯（每级 want/进度/deadline——章号留 #74）；成长=四轴定义+卷末结算清单三件套）

- [ ] **Step 1: story_frame 段5**（总设计 §1.1-1.4 全文在案——四引擎各一节，规则成文可测试；红线三句嵌入；「救人靠组织」入预知红线行）
- [ ] **Step 2: genre-config** market_params 五值（payoff_density 3/1、emotion_band 1/1、hook_grading 2、voice_density_min {"min_per_chapter": 2}、meme_quota {"per_volume": 3}——与 #76/#78 预期一致）+ pacing minChaptersPerCycle 19/maxChaptersPerCycle 36 + approval 块重写（3200/12 键 + 本次变更说明）+ sidecar（P2.5 rationale）
- [ ] **Step 3: rhythm_principles** 三处 19-36 + 拍表四行（20/35/25/20 + 带 15-25/30-45/20-30/15-25）+ 每拍重量下限条款
- [ ] **Step 4: 本地验证** → `uv run pytest tests/unit/contracts/test_market_params.py -q` + G4 对项目 genre-config 实弹：`uv run python -m shenbi.gates.cli G4 shenbi-genre-config novel-xinghuo-vol1/genre-config.json novel-xinghuo-vol1`（PASS）+ 红线四条自查清单落 progress.md
- [ ] **Step 5: 提交**（框架面若有余量改动；项目面不进 git——验证输出贴 progress.md）

---

### Task 3: 验收收尾

**复杂度: infra** · **test_kind: regression_guard**

- [ ] **Step 1: spec §3 验收逐条**（三文件落地抽查 grep 锚点；红线四条自查；G4 三态用例绿；本地 lint PASS）输出贴 progress.md `## 验收证据`
- [ ] **Step 2: `just check` 完整跑**（阶段 7 门禁）
- [ ] **Step 3: G3.4 声明**——无 LLM 产物评分场景（规则文本为协调者创作，非 dispatch 产物；结构性验证全离线）
- [ ] **Step 4: 提交** `chore(spec73): T3 验收收尾`

---

## 验收覆盖表

| spec §3 | task | 命令 |
|---|---|---|
| 三文件重写落地+可测试锚点 | T2 | grep 锚点清单（progress.md 验收证据） |
| 红线四条自查 | T2/T3 | 自查清单（含 rule-007 边界句） |
| 市场参数 schema lint 可校验 | T1 | pytest test_market_params（三态 6 用例）+ G4 实弹 |

## Self-Review

- 覆盖：spec 2.1(T2)/2.2(T1+T2)/2.3(T2)/2.4(双轨)/2.5(所有权声明——无施工，验收核对) ✓
- g4_genre_config 签名实现时核对（plan 已标注）；pacing 19/36 消费方 grep（minChaptersPerCycle）在 T2 Step 4 实弹覆盖
