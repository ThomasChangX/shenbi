# spec #82 retention-engine-net 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把商业节奏执法面从「声明存在」升级为「分布＋兑现＋验真」——完成时声明快照层（T0）+ 跨章序列门四键/引句锚定（T1）+ 钩龄门/挂起预算（T2）+ 卷纲三槽与卷二回填（T3）+ 收尾多样性/七型轮换（T4）+ 检查点四行必答（T5）+ 金手指供给下限（T6）+ retention_anchor 参数化（T7）。

**Architecture:** 一切跨章序列判定的数据基座是 `chapter_states[n].declared` 完成时快照（不读可变 plan）；planning 门（G4.cp）读快照+当章 plan 声明做滑窗判定；regen-accept 验收面保留 plan 读取（卷一历史回放）；shadow WARN 事件走 #81 trace 面（action="WARN"），门检查器保持纯函数——shadow 降级与 trace 发射都在调用侧（chapter_loop）。全部新 FAIL 门默认 shadow:true。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（uv run 同构 CI）。

## Global Constraints

- 状态字面量单一信源：`plan_format` 版本集常量（`PF_LEGAL`/`PF_GE_V2`/`PF_GE_V3`）唯一定义于 `src/shenbi/contracts/enums.py`
- 冷谓词单一信源：`cold_chapter()` 有序三分支唯一定义于 `src/shenbi/text/recall_weight.py`，三消费方（G4.cp 门 / regen-accept / T0 写入校验）共用
- gate 检查器纯函数幂等、无副作用（AGENTS.md）；shadow 降级 + trace WARN 发射在 chapter_loop 调用侧
- `src/shenbi/` 无 `print()`（structlog）；conventional commits；`just generate` 后 deps.json/docs diff 为空；契约改动走 `just lint-contracts`
- 新配置键三源同批：validator（contracts/skills/genre_config.py）+ SKILL 模板（skills/shenbi-genre-config/SKILL.md）+ 在飞项目数据补丁（novel-xinghuo-vol1/genre-config.json，gitignored 运行时写入不进 git）
- G0.9：scenario 输入只用真实产物副本（plans/chapter-36-plan.md、truth/pending_hooks.md、outline/volume_map.md、chapters/*.md 拷贝进 tests/fixtures/spec82/）或 tmp_path 构造结构输入；禁止手写「伪产物」fixture
- F947：不触发真实 dispatch；全部验收离线可执行
- 全部新 FAIL 门默认 `shadow: true`（market_params 键内子键）；shadow WARN 事件 action="WARN" 落 trace
- **契约升级声明（AGENTS.md 纪律，随 Task 1 commit message 携带）**：v4 模板新增必填行（章尾钩型/引句锚定）为 breaking 契约变更——「无既有工件受影响」：卷一 36 章已完结零重跑、在飞运行停 ch37 planning（plan 未生成，恢复即出 v4 plan，零回填）；**v4 兼容三件必须先于该运行恢复落地**（spec r7/N1）
- task 顺序=依赖顺序：T1(v4 兼容) 先于 T2(快照) 与 T3(序列门)——快照/门消费 v4 声明行；T4(verbatim) 依赖 T1；T6(轮换门) 依赖 T2 快照；T8(◆回填) 先于 T9(core_motif_touch 门) 可跑红测

**跨 spec 联动项归属（v7 Plan rubric 要求显式登记）：**
- **#83 T1 verbatim 判定器共基**：本计划 Task 5 建 `src/shenbi/gates/g4/quote_verbatim.py`（plan 审查 M2——原误写 Task 4）（`quote_in_chapter()`），#83 T1 后续复用同一判定器（其 spec r2 L42「勿各造一份」）
- **#83 T5 follower 快照同点位**：本计划 Task 2 的 `_snapshot_declared()` 单章函数即 seam——#83 T5 批量写全 bundle status 时循环调用同一函数；本批不实现 #83 T5 的 status 写全（其 scope）

**验收覆盖表（spec §10 → task → 验证命令）**

| spec 验收 | task | 验证 |
|---|---|---|
| 1 全部新门红测→绿 + just check exit 0 + shadow 位 + 催转 lint | T1-T10 | `just check`；各 task 测试文件（催转=T10 `test_shadow_promotion_lint.py`） |
| 1' shadow WARN 逐束落盘前置 | T3 | `uv run pytest tests/unit/trace/test_warn_action.py -q` |
| 2 卷二首 10 章实弹（离线可执行部分：ch21-36 断供标本回放=T9/轮换 absent 语义=T7/留存锚窗口=T10） | T7/T9/T10 | 对应测试；实弹部分=运行侧边界（#81 先例；R3/M3 列对齐） |
| 3 检查点四行必答首跑对账 | T10 | 文档 diff 审读（docs-only）；「首跑对账」本身=运行侧边界（#81 F947 先例，非本批离线判据） |
| 4 G3.4 卷二段评 ≥85/86 | — | 运行侧边界，SDD 代码交付不含（#81 先例） |
| 5 词表外零洗白 | T2/T5 | `test_wordlist_external_tone_warns_and_kept_raw`（T2 实名）+ `test_regen_accept_2c_sliding.py` 词表外用例 |

---

### Task 1: plan_format v4 兼容（版本集常量六处 + planning SKILL v4 模板行）

**复杂度: infra**（协调者亲实现）｜ **test_kind: tdd_red_green + regression_guard**（既有 v3 门不熄火=回归守卫）

**Files:**
- Modify: `src/shenbi/contracts/enums.py`（版本集常量）
- Modify: `src/shenbi/gates/g4/chapter_planning.py:123`（scene_budget 正则）、`:244-259`（合法值/voice_line/payoff_axis）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:920`（v2 门 `v[23]`）、`:925`（v3 正则）
- Modify: `skills/shenbi-chapter-planning/SKILL.md:217-235`（v4 模板节）
- Test: `tests/unit/gates/g4/test_plan_format_v4.py`（新）；`tests/unit/gates/g4/test_spec76_voice_quote.py:96-99`（真值表翻转改写）

**Interfaces:**
- Produces（后续 task 与 #83 依赖）: `enums.PF_LEGAL: tuple[str, ...] = ("v1","v2","v3","v4")`；`enums.PF_GE_V2: frozenset[str]`；`enums.PF_GE_V3: frozenset[str]`；planning SKILL v4 模板新行 `章尾钩型: <七型之一>`（Task 2/6 摄取）与 `章尾张力拍: [微|章|大]｜『<章尾句原文引句>』`（Task 4 摄取）
- Consumes: 既有 `_pf_val` 解析（chapter_planning.py:244）

- [ ] **Step 1: 红测——v4 memo 现状 illegal/静默豁免**

```python
# tests/unit/gates/g4/test_plan_format_v4.py
from pathlib import Path
import pytest
from shenbi.gates.g4.chapter_planning import g4_chapter_planning

V4_BODY = """plan_format: v4
emotion_tone: 悲
留存锚: 非锚章
**payoff 拍**: 类型｜轴(债)｜量
章尾张力拍: 章｜『他数到第三遍，门被推开一半。』
章尾钩型: 悬念钩
"""

def _run(tmp_path: Path, body: str) -> str:
    p = tmp_path / "plans" / "chapter-37-plan.md"
    p.parent.mkdir(parents=True)
    p.write_text(body, encoding="utf-8")
    return g4_chapter_planning([str(p)], rd=None, project_dir=str(tmp_path))  # 源码 :55 签名——返回 fail()/passed() 的 JSON 报告串（must_fix 为数组；子串断言即可，勿做行解析——plan 审查 M1）

def test_v4_is_legal_token(tmp_path):
    out = _run(tmp_path, V4_BODY)
    assert "invalid_token" not in out

def test_v4_memo_scene_budget_still_enforced(tmp_path):
    out = _run(tmp_path, V4_BODY)  # 无场景预算节
    assert "scene_budget" in out   # 现状 v3\b 不匹配 v4 → 静默豁免（红）

def test_v4_memo_voice_line_required(tmp_path):
    out = _run(tmp_path, V4_BODY)  # 无声口要求行
    assert "voice" in out.lower()  # 现状 in ("v2","v3") 不认 v4（红）

def test_v4_memo_payoff_axis_required(tmp_path):
    body = V4_BODY.replace("**payoff 拍**: 类型｜轴(债)｜量\n", "**payoff 拍**: 类型\n")  # 保留行去轴——missing_payoff_beat 版本无关会遮蔽假红（plan 审查 I5）
    out = _run(tmp_path, body)
    assert "payoff_axis" in out    # 现状 :259 =="v3" 不认 v4（真红）；改后 PF_GE_V3 认 v4（绿）
```

Run: `uv run pytest tests/unit/gates/g4/test_plan_format_v4.py -q` → **预期 FAIL（红）**

- [ ] **Step 2: enums.py 版本集常量**

```python
# src/shenbi/contracts/enums.py 追加
#: plan_format 版本集（spec #82 r7/F2——六处消费点单一信源；v4 ⊇ v3 ⊇ v2）
PF_LEGAL: tuple[str, ...] = ("v1", "v2", "v3", "v4")
PF_GE_V2: frozenset[str] = frozenset({"v2", "v3", "v4"})
PF_GE_V3: frozenset[str] = frozenset({"v3", "v4"})
```

- [ ] **Step 3: 六处消费点改集合/常量**

chapter_planning.py：`:123` `re.search(r"plan_format[：:]\s*v3\b", ...)` → `r"plan_format[：:]\s*v[3-9]\b"`；`:247` `not in ("v1","v2","v3")` → `not in PF_LEGAL`；`:251` `in ("v2","v3")` → `in PF_GE_V2`；`:259` `== "v3"` → `in PF_GE_V3`。chapter_drafting.py：`:920` `v[23]` → `v[2-9]`（**v2 门——不得 v[3-9]，会把 v2 memo 踢出 #76 族**）；`:925` `v3\s*$` → `v[3-9]\s*$`。import 从 enums。

- [ ] **Step 4: 改写 test_spec76_voice_quote.py:96-99 真值表**

v4 从 invalid 翻转为 legal（parametrize 移除 v4→invalid 行，加 v4→valid 行）；:121 的 v2 density 测试保持绿（regression_guard：v2 不被误删）。

- [ ] **Step 5: planning SKILL v4 模板节**

`skills/shenbi-chapter-planning/SKILL.md` :219 版本令牌段与 :235 模板区追加：合法值加 v4；**v4 ⊇ v3** 另加两行义务——`章尾钩型: <悬念钩|危机钩|情感钩|反转钩|账目钩|信物钩|对位钩>`（七型词表，G4.cp 存在性+词表校验）+ 章尾张力拍升级形态 `章尾张力拍: [微|章|大]｜『<章尾句原文引句>』`（引句锚定，Task 4 门回查正文）。SKILL 属技能契约——改后跑 `just lint-contracts && just generate`（deps.json/docs diff 必须为空）。

- [ ] **Step 6: 绿 + 提交**

Run: `uv run pytest tests/unit/gates/g4/test_plan_format_v4.py tests/unit/gates/g4/test_spec76_voice_quote.py -q` → PASS；`just lint-contracts && just generate` diff 空。
`git add` 显式列文件；`git commit -m "feat: spec82 T1 plan_format v4——版本集常量六处+SKILL v4 模板（钩型/引句锚定行）"`

---

### Task 2: T0 完成时声明快照层（declared 字段 + leader/follower 写入 + 词表校验 + 节点标记集摄取）

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/pipeline/state.py:143-150`（ChapterState.declared 字段）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_complete_chapter` :2034-2095 束感知快照写入；新函数 `_snapshot_declared`）
- Test: `tests/unit/pipeline/test_snapshot_declared.py`（新）
- Fixture: `tests/fixtures/spec82/`（chapter-36-plan.md、chapter-2-plan.md 真实副本 + volume_map.md 节选副本——G0.11 哈希一致或注明节选）

**Interfaces:**
- Produces: `ChapterState.declared: dict[str, Any]`（六键：`emotion_tone`/`张力拍档位`/`章尾钩型`/`payoff档`/`金句位燃`/`节点标记集: list[str]`）；模块级 `_snapshot_declared(project_dir: Path, chapter: int) -> dict[str, Any]`（#83 T5 seam：其批量循环将调用本函数）；`DECLARED_WORDLISTS: dict[str, frozenset[str]]`
- Consumes: Task 1 的 v4 声明行（钩型）；`bundle_chapters()`（chapter_loop.py:1294）；volume_map ◆ 标记（`_node_markers` 解析，两代 KR 形态无关——标记在节点行内）

- [ ] **Step 1: 红测**

```python
# tests/unit/pipeline/test_snapshot_declared.py 核心红测
def test_snapshot_frozen_after_plan_rewrite(tmp_path, monkeypatch):
    # leader ch37 完成 → 快照在；改写 plans/chapter-37-plan.md 的 emotion_tone
    # 再对 ch38 跑 _snapshot_declared(37) —— 不再被调用：断言 chapter_states["37"].declared 不变
    ...
def test_follower_snapshot_written(tmp_path):
    # 束 [37,38]：_complete_chapter(37) 后 37 与 38 两键都有 declared（#83 T5 seam 证明）
    ...
def test_wordlist_external_tone_warns_and_kept_raw(...):
    # emotion_tone: 安 → WARN 日志 + declared["emotion_tone"]=="安"（消费者按冷谓词处理）
    ...
def test_real_fixture_six_keys_captured(...):
    # plan 审查 C1 绿测：对 tests/fixtures/spec82/chapter-36-plan.md 真实副本跑
    # _snapshot_declared → 六键捕获断言：emotion_tone=="悲"、张力拍档位=="章"、
    # payoff档=="中"、金句位燃 truthy、章尾钩型 absent（v3 plan 无该行）、节点标记集按 volume_map ch36 行
    ...
def test_node_markers_ingested(...):
    # 真实卷一行（plan R2/M1'——ch37/38 行 Task 8 回填前不存在，勿引）：ch8 节点行含「轮回触点◆」
    # → declared["节点标记集"] == ["轮回触点◆"]（fixture=volume_map 卷一节选真实副本）；
    # 另一断言：ch22 行摄 ["萤回触◆"]（多标记类型共存场景）
    ...
```

Run: `uv run pytest tests/unit/pipeline/test_snapshot_declared.py -q` → 红（declared 字段不存在）

- [ ] **Step 2: state.py 字段**

```python
@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: ChapterStatus = ChapterStatus.PENDING
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0
    audit_retry_count: int = 0
    # spec #82 T0: completion-time declared-label snapshot (sequence gates
    # read this, never the mutable plan file; post-gate plan rewrites by
    # _REDO_RE_DISPATCH must not rewrite history)
    declared: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 3: `_snapshot_declared` + `_complete_chapter` 写入**

```python
DECLARED_WORDLISTS: dict[str, frozenset[str]] = {
    "emotion_tone": frozenset({"悲", "喜", "怒", "惧", "平"}),
    "张力拍档位": frozenset({"微", "章", "大"}),
    "payoff档": frozenset({"小", "中", "大"}),
    "章尾钩型": frozenset({"悬念钩", "危机钩", "情感钩", "反转钩", "账目钩", "信物钩", "对位钩"}),
}

def _snapshot_declared(project_dir: Path, chapter: int) -> dict[str, Any]:
    """完成时声明快照（spec #82 T0）——只读 plan 与 volume_map，纯函数。"""
    d: dict[str, Any] = {}
    plan = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if plan.is_file():
        text = plan.read_text(encoding="utf-8")
        for key, pat in (
            ("emotion_tone", r"^emotion_tone[：:]\s*(\S+)"),
            ("张力拍档位", r"^[-* ]*\*{0,2}章尾张力拍\*{0,2}[：:]\s*\[?(微|章|大)"),  # 兼容 **章尾张力拍**: 加粗形态（ch36:78 实存——plan 审查 M6）
            ("payoff档", r"\*{0,2}payoff\s*拍\*{0,2}[：:].*?(小|中|大)兑现"),  # 真实形态 32/36 份：类型｜轴(债)｜中兑现——量[：:]形态 0 命中（plan 审查 C1）
            ("章尾钩型", r"^章尾钩型[：:]\s*(\S+)"),
        ):
            m = re.search(pat, text, re.MULTILINE)
            if m:
                val = m.group(1).strip()
                d[key] = val
                if key in DECLARED_WORDLISTS and val not in DECLARED_WORDLISTS[key]:
                    log.warning("snapshot_wordlist_external", chapter=chapter, key=key, value=val)
        d["金句位燃"] = bool(re.search(r"^金句位[：:]\s*燃", text, re.MULTILINE))
    markers: list[str] = []
    vm = project_dir / "outline" / "volume_map.md"
    if vm.is_file():
        for line in vm.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*第(\d+)章", line)
            if m and int(m.group(1)) == chapter:
                markers = re.findall(r"[一-龥A-Za-z]+◆", line)
                break
    d["节点标记集"] = markers
    return d
```

`_complete_chapter` 在 `cs.status = ChapterStatus.COMPLETE` 后追加（束感知、幂等）：

```python
    # spec #82 T0: freeze declared labels for every bundle member at
    # completion (leader + followers share one completion moment; #83 T5
    # will route its batch status write through the same per-chapter fn).
    for member in bundle_chapters(project_dir, chapter):
        mkey = str(member)
        mcs = state.chapter_loop.chapter_states.setdefault(mkey, ChapterState())
        if not mcs.declared:
            mcs.declared = _snapshot_declared(project_dir, member)
```

- [ ] **Step 4: 绿 + 提交**

Run: `uv run pytest tests/unit/pipeline/test_snapshot_declared.py -q` → PASS
`git commit -m "feat: spec82 T0 完成时声明快照层——leader/follower 写入+词表校验 WARN+节点标记集摄取"`

---

### Task 3: genre-config 新键三源 + emotion_band 退役 + shadow WARN trace 事件

**复杂度: infra** ｜ **test_kind: tdd_red_green + characterization**（emotion_band 退役对存量=characterization：含旧键照过）

**Files:**
- Modify: `src/shenbi/contracts/skills/genre_config.py:67-130`（validator）
- Modify: `skills/shenbi-genre-config/SKILL.md:123/:326`
- Modify: `src/shenbi/trace/event.py`（action 白名单若枚举——加 "WARN"）；`src/shenbi/pipeline/chapter_loop.py`（shadow 降级点，见 Step 3）
- Runtime write（不进 git）: `novel-xinghuo-vol1/genre-config.json`
- Test: `tests/unit/contracts/test_genre_config_spec82_keys.py`（新）；`tests/unit/trace/test_warn_action.py`（新）

**Interfaces:**
- Produces: validator 接受 `cold_streak_cap:{max:int, shadow:bool=True}`、`hot_hook_floor:{window:int=10,min:int=1,shadow:bool}`、`payoff_magnitude_floor:{window:int=6,min:"中"|int,shadow:bool}`（min 允许 str——Pydantic 字段类型放宽 `int|float|str`）、`temperature_profile:{window:int=10,hot_ratio_min:float=0.2}`（WARN 级、无 shadow 位）、`hook_max_age:{max:int=8, shadow:bool=True}`（dict 形态——shadow 子键有归宿，plan 审查 I2；spec L146 已同步；Task 6 消费侧读 `.max`）、`hook_rotation:{shadow:bool=True}`（plan R2/I3'——轮换门独立键）、`quote_anchor:{shadow:bool=True}`（R3/I2——引句锚定门）、`retention_anchor:{from_ch:int=1, to_ch:int|float|None=None, shadow:bool=True}`（R3/I2——spec F8 同纪律；**注解须加 `|None`**，R3/M4：实测今注解下 to_ch null 仍 ValidationError，str 放宽不够）、`hook_defer_budget:{per_volume:int=3}`、`retention_anchor:{from_ch:int=1,to_ch:int|None=None}`（null 容忍）；`pacing.core_motif_touch:{max_gap:int=6,shadow:bool}`；`emotion_band` 从 required 移除（子键多余仍容忍——存量兼容）
- Consumes: Task 1（无）；shadow 降级接口（shadow.py）供 Task 4/5/6/7/9/10 门消费——R3/M5：快照标记解析内联于 `_snapshot_declared`，无独立 `_node_markers` 函数

- [ ] **Step 1: 红测**（**含转正方向红测（plan R2/I2'）**：`shadow:false` 的门 must_fix 保持 HARD 不降级 + 未登记检查 id 不降级 + `cp.` 前缀 id 正确命中映射；现状三态：纯数值新键=静默忽略不拒、`to_ch:null`/`min:"中"`=Pydantic 类型层拒——红测锚这两类拒；emotion_band 退役后**含旧键** PASS（子键多余容忍，characterization）＋**无 emotion_band 键** PASS（M5——`:88 eb = v["emotion_band"]` 无守卫直取现状 KeyError，须同批移除））

- [ ] **Step 2: validator 域扩展 + required 元组去 emotion_band**（数值域注释同步三态现实：纯数值新键=静默忽略不拒、null/字符串=类型层拒——故必须显式域定义）

- [ ] **Step 3: shadow WARN trace 事件 + 调用侧降级**

trace/event.py：实测 `action: str` 自由字符串（`_SIGNED_FIELDS` :24 无枚举）——**无需改**。chapter_loop 插入点（plan R2/C1'——**主位=:4201-4284 序列步 G4 消费点**：`g4 = run_gate_g4(step.skill, ...)` :4203 对每个已派发步（含 shenbi-chapter-planning）跑门，`must_fix = g4.get("must_fix", [])` :4210 进 `_classify_g4_failures` :829——未匹配检查 id 保守默认 HARD→retry→RetryExhaustedError；**降级必须在 :4210 must_fix 列表进分类器之前拦截，且路由钉死（plan R3/I1——两条朴素接线都死）**：降级项**进 WARN 通道**（log + trace WARN 事件），从分类器输入中剔除；若剔除后剩余 must_fix 为空且 g4 未 PASS → **视同 PASS-with-warnings 路由**（复刻 :4207 的 retry_feedback 清空，**不得**落入 :4212-4215 的 `G4.generic_failure` 合成 HARD 兜底——shadow 首束单门 FAIL 恰是该兜底的触发场景）；同语义钉 :3907（`if not _gate_passed(g4)` 前全降级→按 PASS 分支走）与 :1370（scene-split 无 state 在围——降级器签名读 project_dir 不读 state，见 M1 修订）；否则 shadow 门在 ch37 planning 首束硬阻塞——冷连击历史依赖重规划修不动）；次位=:1370-1383（scene-split G4.cd）与 :3898-3917 与 **cli.py:218-227 `_re_dispatch_g4_must_fix`（plan R3/I3——checkpoint 重派成功后全量重跑 G4.cp 的第四消费点：历史依赖型 shadow FAIL 在此确定性复发，不降级则 RE_DISPATCH_RETRY_CAP=3 耗尽后 redo 静默废弃）**；`_run_g4_checks` :3230 只跑 title/hook_fulfillment 两窄检查**不接**；`shenbi-validate G4` CLI 面保持裸 FAIL 属预期（shadow 是管线运行时概念）：

落位：**新模块 `src/shenbi/gates/g4/shadow.py`**（gates 侧纯辅助，自包含前缀提取——勿跨模块 import chapter_loop 私有 `_extract_check_id`；R3/M1）：

```python
# src/shenbi/gates/g4/shadow.py
import re

def _check_id(item: str) -> str:
    m = re.match(r"G4\.([a-z_.]+)", item)
    return m.group(1) if m else item.split(":", maxsplit=1)[0].replace("G4.", "")

GATE_TO_SHADOW_KEY: dict[str, tuple[str, str]] = {  # plan R2/I2'——键=带前缀检查 id（_extract_check_id :851 产出 `cp.cold_streak_window` 形态，勿用裸名）；值=(配置块, 键)；缺映射=None→**不降级**（fail-safe 方向：未登记门保持 HARD 可见，静默降级才是事故）
    "cp.cold_streak_window": ("market_params", "cold_streak_cap"),
    "cp.hot_hook_window": ("market_params", "hot_hook_floor"),
    "cp.payoff_magnitude": ("market_params", "payoff_magnitude_floor"),
    "cp.hook_age": ("market_params", "hook_max_age"),
    "cd.hook_type_rotation": ("market_params", "hook_rotation"),   # plan R2/I3'：轮换门独立键 hook_rotation:{shadow:bool}（嵌套 hook_grading.rotation 会被 Pydantic dict[str,dict[str,int|float]] 拒）
    "cp.core_motif_touch": ("pacing", "core_motif_touch"),        # pacing 块——降级器须读两块（R2/I2'c）
    "cd.quote_verbatim": ("market_params", "quote_anchor"),          # plan R3/I2——引句锚定门独立 shadow 键 {shadow:bool}
    "cp.missing_retention_anchor": ("market_params", "retention_anchor"),  # 现存发射 id（:379）——spec F8「同 shadow 纪律」落地：键形加 shadow 子键
}

def apply_shadow(project_dir: Path, item: str) -> str | None:
    """shadow:true 时 FAIL→WARN 降级判定（纯函数——门检查器与降级器都无副作用；
    trace WARN 事件由调用侧在降级确认后发射）。返回降级后文案或 None（不降级）。"""
    from shenbi.config.genre_loader import read_genre_config  # 按 genre_config.py 邻域实名核对
    cfg = read_genre_config(str(project_dir)) or {}
    loc = GATE_TO_SHADOW_KEY.get(_check_id(item))
    if loc is None:
        return None  # 未登记门不降级（fail-safe：保持 HARD 可见）
    block, key = loc
    entry = (cfg.get(block) or {}).get(key, {})
    if not (isinstance(entry, dict) and entry.get("shadow", True) is True):
        return None  # shadow:false（已转正）或键缺席→不降级
    return f"[shadow] {item}（shadow 试运行——零误伤后转正）"
    if not (isinstance(cfg, dict) and cfg.get("shadow", True) is True):
        return None
    from shenbi.trace.event import ...  # 既有 writer 按 #81 面
    # trace WARN 事件：action="WARN", payload={gate_id, issue, chapter}
    return f"[shadow] {issue}（shadow 试运行——零误伤后转正）"
```

- [ ] **Step 4: SKILL 模板三源同步 + 项目数据补丁**

SKILL.md :123 模板键集与 :326「三键块」文本改新键集（emotion_band 移除、新键列入）；`just lint-contracts && just generate` diff 空。运行时写入 `novel-xinghuo-vol1/genre-config.json`（python json 更新**九处**（R3/M2 计数订正）：market_params 八键（七键+`hook_rotation`+`quote_anchor`+`retention_anchor.shadow` 子键并入）+pacing.core_motif_touch，全部 shadow:true）＋校验（M8 具体命令，函数名按 :55 邻域实名核对）：

    uv run python -c "import json;from pathlib import Path;from shenbi.contracts.skills.genre_config import _market_params_structure as v; cfg=json.load(open('novel-xinghuo-vol1/genre-config.json')); v(cfg.get('market_params'))"

——输出贴 progress（gitignored 文件不 commit）。

- [ ] **Step 5: 绿 + 提交**

---

### Task 4: T1 序列门四键 + 冷谓词共享常量 + micro_hook_run 快照迁移

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/text/recall_weight.py`（`cold_chapter()` 常量）
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（`cold_streak_window`/`hot_hook_window`/`payoff_magnitude`/`temperature_profile` 四检查）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:928-957`（micro_hook_run 改读快照）
- Test: `tests/unit/gates/g4/test_spec82_sequence_gates.py`（新）

**Interfaces:**
- Produces: `cold_chapter(tone: str | None, golden_hot: bool) -> bool`（有序三分支：①tone∉五值词表→True ②tone∈{悲,惧,平} 且非 golden_hot→True ③否则 False）；四门检查函数（G4.cp 注册形态与 emotion_tone 同——mf/c 列表）
- Consumes: Task 2 快照（`chapter_states[n].declared`，经 state 传入或从 state 序列化文件读——按 G4.cp 现有 project_dir 模式从 `pipeline-state.json` 读）；Task 3 键

- [ ] **Step 1: 红测**（spec T1 TDD 全清单）
```python
@pytest.mark.parametrize("tones,expected", [
    (["悲","惧","平","悲"], "FAIL"),      # 四连冷 > cap 3
    (["悲","悲","惧","喜"], "PASS"),       # 三连冷+暖
    (["平"]*9 + ["平"], "FAIL_hot"),       # 10 章窗零「大」
    (["安"], "COLD"),                      # 词表外→冷（分支①）
    (["悲"], "WARM"),                      # 悲+金句位燃→暖（分支②例外）
])
def test_cold_chapter_branches(tones, expected): ...
def test_ten_window_no_big_hook_fails(...): ...
def test_six_window_all_small_payoff_fails(...): ...
def test_hot_ratio_below_floor_warns(...): ...          # WARN 级
def test_first_three_chapters_exempt(...): ...
def test_config_absent_degrades_to_warn(...): ...        # scene_budget 版本门先例
def test_bootstrap_window_shorter_than_window_no_floor(...): ...  # r6/N6：窗内已生成章数<window 不判 floor（R3/M7 补红测）
def test_plan_rewrite_after_completion_keeps_verdict(...): ...  # 改 plan 判定不变（快照）
def test_min_key_is_consumed(...): ...                   # payoff min 消费断言（反 payoff_density 前车之鉴）
def test_shadow_flag_demotes_fail(...): ...              # Task 3 _apply_shadow 接线
```
Run → 红
- [ ] **Step 2: `cold_chapter` 实现**（recall_weight.py，常量+分支，_COLD_TONES 保留为内部）
- [ ] **Step 3: 四门实现**（chapter_planning.py；滑窗=快照历史（前 N-1 章已完备章）+当章 plan 声明；跨卷只取本卷已生成章——`bundle_chapters` 同源的 volume span 判定复用；配置缺席退 WARN；全部 FAIL 门经调用侧 `_apply_shadow`）
- [ ] **Step 4: micro_hook_run 改读快照**（chapter_drafting.py:928-957——`_tiers` 改从 pipeline-state declared 取，快照缺席章（卷一历史）回退现 plan 解析路径并记 WARN——I2 双面声明的一部分）
- [ ] **Step 5: 绿 + 提交**

---

### Task 5: verbatim 判定器 + 引句锚定门 + check_emotion_proxy 滑窗化

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Create: `src/shenbi/gates/g4/quote_verbatim.py`（#83 T1 共基）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`quote_verbatim` 门——drafting 后正文在盘时回查）
- Modify: `tools/regen_accept.py:192-217`（滑窗化+词表外堵口）
- Test: `tests/unit/gates/g4/test_quote_verbatim.py`；`tests/unit/tools/test_regen_accept_2c_sliding.py`
- Fixture: `tests/fixtures/spec82/chapter-1.md`、`chapter-6.md` 真实副本（#83 证据句：ch1「却不知道明天城就破了」不在正文=红测；ch6「册子认得人」在正文）

**Interfaces:**
- Produces: `strip_to_prose(chapter_text: str) -> str`（剥 META 块/场景分隔）、`quote_in_chapter(quote: str, chapter_text: str) -> bool`（逐字子串，strip 后）
- Consumes: Task 1 v4 张力拍引句形态；Task 4 `cold_chapter`

- [ ] **Step 1: 红测**（ch1/ch6 实证句夹具：引句在→PASS、不在→FAIL、v3 memo→SKIP；proxy 滑窗：10 章滚动窗 worst、词表外安→冷斩不断连击、金句位燃例外保留）
- [ ] **Step 2: 实现 quote_verbatim.py**
- [ ] **Step 3: G4.cd.quote_verbatim 门**（v4 memo 张力拍行 `『(.+?)』` 提取→回查本章正文；缺引句形态→FAIL「引句锚定缺失」）
- [ ] **Step 4: proxy 滑窗化**（`for n in range(max(1, through-9), through+1)` 窗；`tone in _COLD_TONES` → `cold_chapter(tone, hot)`；历史 memo 缺席→该章跳过不 FAIL——卷一 ch1-36 全量回放兼容）
- [ ] **Step 5: 绿 + 提交**

---

### Task 6: T2 钩龄门 + 挂起锚校验 + advance 条文化 + 章级钩注册半边

**复杂度: infra**（truth 解析 + SKILL 契约）｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（`hook_age` 门）
- Modify: `tools/lint_volume_nodes.py`（挂起锚存在性子检查——两代 KR 形态+中文卷号归一）
- Modify: `skills/shenbi-state-settling/SKILL.md`（advance 条文化一行）
- Modify: `skills/shenbi-review-foreshadowing/SKILL.md`（章级钩注册完整性 checkpoint——blocking 形态）
- Test: `tests/unit/gates/g4/test_hook_age.py`；`tests/unit/tools/test_volume_nodes_defer_anchor.py`
- Fixture: `tests/fixtures/spec82/pending_hooks.md` 真实副本（MH02 last_reinforced 35/MH03 36/多 bullet 结构）；volume_map 副本（两代 KR 形态段）

**Interfaces:**
- Produces: `parse_last_reinforced(hooks_text: str) -> dict[str, int]`（per-hook max 章；**真实格式 `第 35 章` 数字两侧有空格**——:48/:69/:88 实测，正则 `第\s*(\d+)\s*章` 容忍，plan 审查 M7）；`parse_relevant_hooks(hooks_text: str) -> set[str]`（总览 当前生命周期 RELEVANT）；`resolve_defer_anchor(anchor: str, vm_text: str) -> bool`（锚命中 volume_map——`#### KR2:` 与 `2. KR2（…章完成）` 两形态+「卷三→第三卷」归一）
- Consumes: Task 3 `hook_max_age`/`hook_defer_budget`

- [ ] **Step 1: 红测**（spec T2 TDD 全清单：超龄未触达 FAIL/触达 PASS/带锚挂起 PASS/无锚 FAIL/悬空锚 FAIL/超预算 FAIL/龄期 8 内 PASS/多 bullet 取 max/详情块零 bullet 按总览种植章起算）
- [ ] **Step 2: hook_age 门**（RELEVANT 钩×（当前章-last_reinforced>max_age）→当章 plan 钩账行 touch 或挂起行；缺两者 FAIL（修复者 planning）；挂起预算 per_volume 计数超→FAIL；shadow 经调用侧）
- [ ] **Step 3: lint 挂起锚子检查**（`resolve_defer_anchor`；`just volume-nodes <dir> <vol>` 跑绿）
- [ ] **Step 4: 两个 SKILL 契约行**（settling：「物品层在场不等于约定层推进；只有审计判 advance 的在场才发 last_reinforced 增量」升条文；foreshadowing：「正文在场面未被 pending_hooks 登记者 → `- [BLOCKING]` finding；注册并入 settling 钩增量以该 finding 为确证」）；`just lint-contracts && just generate`
- [ ] **Step 5: 绿 + 提交**

---

### Task 7: T4 收尾多样性（review-group-craft 契约 + 轮换门 + ending_diversity + 口癖帽 + 收尾历史注入）

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `skills/shenbi-review-group-craft/SKILL.md`（①复述行检查点 ②≥3 章同型收尾卷级 finding（注入收尾型历史）③反合理化表调和（平静收束预算 10 章窗 ≤3）+ D2 判温+判型 `- [BLOCKING]` + emotion_tone 判温义务）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`hook_type_rotation` FAIL + `ending_diversity` WARN）
- Modify: `src/shenbi/pipeline/audit_context_cache.py`（`SharedAuditContext` 加 `ending_history: list[str]` 字段、`build_shared_audit_context` 自快照派生；**注入机制（R3/M6——`_INJECT_FROM_CACHE` 按文件路径键注入，list 字段骑不上）**：dispatch_helper `_build_skill_prompt` :1137-1153 的 cached-field 注入块**新增 list 字段分支**——`ending_history` 拼为「审查参考数据·近 10 章收尾型历史」小节插入 review-group-craft 的 input_texts，不走文件路径键约定）；
- Modify: `tools/lint_voice_meme.py`（per-catchphrase 卷配额：默认每 3 章 ≤1）
- Test: `tests/unit/gates/g4/test_hook_type_rotation.py`；`tests/unit/tools/test_voice_meme_quota.py`

**Interfaces:**
- Produces: `recent_ending_history(state_json: Path, through: int, window: int = 10) -> list[str]`（自 declared 派生收尾型标签——dispatcher 注入与 ② 同源）；rotation 门读快照 `章尾钩型`（absent 跳过——v4 前兼容）
- Consumes: Task 2 快照；Task 3 shadow

- [ ] **Step 1: 红测**（轮换：连续同型 FAIL/异型 PASS/首章豁免/absent 跳过/shadow；ending_diversity：账目形态（末 3 句 ≥2 数字串）/`呢？`/`他在心里.*一遍`/`这一(笔|夜|章)` 四原型×连续 3 章 WARN；口癖帽：26 处 vs 卷配额 12 FAIL 边界）
- [ ] **Step 2: 轮换门 + 哨兵实现**
- [ ] **Step 3: dispatch 注入 + SKILL 契约改**（`just lint-contracts && just generate`）
- [ ] **Step 4: 口癖帽**（lint_voice_meme chapter 模式增 per-catchphrase 卷配额；regen-accept 判据 4 已有调用面自动获得）
- [ ] **Step 5: 绿 + 提交**

---

### Task 8: T3 卷纲三槽 lint + 卷二回填数据补丁

**复杂度: leaf（tools）+ 数据补丁（协调者）** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `tools/lint_volume_nodes.py`（获得列非空/连续无获得 ≤2/胜利预算行存在）
- Runtime write: `novel-xinghuo-vol1/outline/volume_map.md`（37-86 获得槽/胜利预算行/主角自选目标/轮回触点◆标记 max_gap≤6 排布——卷二节拍重排只动列与标记，不改正文节拍文本）
- Test: `tests/unit/tools/test_volume_nodes_gains.py`

**Interfaces:**
- Produces: lint 新检查 id `gains_empty`/`gains_streak`/`victory_budget_missing`；volume_map 卷二段新列「本章主角获得」与卷头「胜利预算」行
- Consumes: 无（数据侧独立；门侧归 Task 9）

- [ ] **Step 1: 红测**（三检查各自红→绿；连续无获得 3 章 finding、2 章 OK）
- [ ] **Step 2: lint 实现**
- [ ] **Step 3: 卷二回填**（手工+脚本辅助写入 gitignored 文件；`uv run python tools/lint_volume_nodes.py novel-xinghuo-vol1 --volume 2` 跑绿；◆标记按 37-86 排布 max_gap≤6——首标记 ≤ch42、尾标记 ≥ch84；输出贴 progress）
- [ ] **Step 4: 提交**（只 commit tools/tests；volume_map 不进 git）

---

### Task 9: T6 core_motif_touch 门 + _check_touches 分链 + invariants 行更新

**复杂度: infra** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（`core_motif_touch` 滑窗——读快照 `节点标记集`）
- Modify: `tools/lint_volume_nodes.py:84-105`（`_check_touches` 按标记类型分链）
- Modify: `docs/framework/invariants.md`（维度 9 行：数据源/门检「已接线」、声明槽改 volume_map ◆、审计槽保持 `—`；维度 7/8 行门检列补 hook_age/轮换门/ending_diversity/temperature_profile/hot_hook_window/payoff_magnitude、载体 emotion_band→cold_streak_cap 族）
- Test: `tests/unit/gates/g4/test_core_motif_touch.py`；`tests/unit/tools/test_touches_per_marker_chain.py`

**Interfaces:**
- Produces: `core_motif_touch` 门（**对快照 `节点标记集` 先过滤 `轮回触点◆` 标签再单链计间隔**——any-◆ 计数复发并集掩盖（ch22-36 萤回触◆/智力爽◆把间隔压 ≤7，标本不红；plan 审查 I1，与 lint 分链同口径）；距上次轮回触点◆章>max_gap→FAIL，反馈含双路径修复者：planning 补触点拍/volume-outlining 重排◆（仅未生成章）；卷内首标记前不计间隔。红测标本经 `_snapshot_declared` 自真实 volume_map 构造（any-◆ 实现当场红）
- Consumes: Task 2 快照标记集；Task 8 ◆回填（红测标本：卷一 ch21-36 断链 16 章→FAIL）

- [ ] **Step 1: 红测**（间隔 7 FAIL/6 PASS/非标记节点不计/ch21-36 标本回放 FAIL/卷首首标记前不计/shadow；分链：轮回链单独 max gap>8 finding、萤回触链独立、**并集标本仍红**——Task 8 前卷二空档）
- [ ] **Step 2: 门 + 分链实现**（`_check_touches` 改 `markers_to_chains(nodes) -> dict[str, list[int]]` 后逐链跑 gap/span）
- [ ] **Step 3: invariants 行更新**（lint_invariant_coverage 跑绿——`uv run python tools/lint_invariant_coverage.py`；CURRENT_PHASE 保持 P1）
- [ ] **Step 4: 绿 + 提交**

---

### Task 10: T7 retention_anchor 参数化 + shadow 催转 lint + T5 检查点协议文档

**复杂度: infra（门）+ leaf（lint/docs）** ｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py:375-388`（窗口参数化——`retention_anchor {from_ch, to_ch}`；配置缺席沿用硬编码 1-30）
- Create: `tools/lint_shadow_promotion.py`（连续 2 束零误伤未转正→red；读 trace WARN 事件 + 误伤裁定台账段）
- Modify: `docs/regen-vol1-continue-prompt.md`（10 章检查点四行必答：温度谱（快照+勘误）/胜利账/钩龄表/挂起清单；抽读背离→blocking+errata 登记）
- Test: `tests/unit/gates/g4/test_retention_anchor_window.py`；`tests/unit/tools/test_shadow_promotion_lint.py`

**Interfaces:**
- Produces: `lint_shadow_promotion(trace_path: Path, ledger_path: Path | None) -> list[str]`（findings）；文档协议（后续卷 prompt 模板化基础）
- Consumes: Task 3 trace WARN 面；Task 3 retention_anchor 键

- [ ] **Step 1: 红测**（retention：31 章后缺声明 FAIL（窗口开时）/窗口边界 from/to 生效/配置缺席沿用 1-30 硬编码/`to_ch:null`=全卷；催转：2 束 WARN 零误伤未转正→finding、已转正/有误伤→无 finding、trace 无 WARN→「无 shadow 门」降级 OK）
- [ ] **Step 2: 门参数化 + lint 实现**
- [ ] **Step 3: 检查点协议文档**（四行必答+勘误面+抽读 blocking——docs-only，审读 diff）
- [ ] **Step 4: 绿 + 提交**

---

### Task 11: 验收映射执行 + 全量门禁

**复杂度: infra（协调者）** ｜ **test_kind: regression_guard**

**Files:** 无新文件（验收执行 + progress.md 粘贴）

- [ ] **Step 1: 验收映射逐条执行**（spec §10 五条离线面：各测试文件全绿输出、`just volume-nodes novel-xinghuo-vol1 2` 绿、invariants lint 绿、催转 lint 干跑——全部粘贴 progress.md `## 验收证据`；验收 2 实弹/验收 4 G3.4=运行侧边界声明（#81 F947 先例））
- [ ] **Step 2: `just check`**（EXIT=0 全输出粘贴）；`uv lock --check`（未动依赖则注记）
- [ ] **Step 3: audit 计数核验**（`ls .superpowers/sdd/audit-T*.md | wc -l` == 11）
