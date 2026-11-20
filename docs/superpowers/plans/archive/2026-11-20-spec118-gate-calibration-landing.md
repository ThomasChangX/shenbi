# Spec #118 门标定落地批 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 机械执行 2026-11-20 用户七门裁定＋content_uniqueness P1 修＋三残行分类收口（spec r2.2 权威），每 task 红测双向＋50 章重跑＋baseline 同步三件套。

**Architecture:** 全部行为改动集中在 `src/shenbi/gates/g4/chapter_drafting.py` 九函数＋`src/shenbi/text/voice_lexicon.py` 常量单源＋`src/shenbi/contracts/skills/genre_config.py` validator；负例证据走 #116 变异引擎（`tools/gen_gate_power_fixtures.py` MUTATIONS 扩展）维护者侧重生成 fixture；取数走 `just gate-power`（零 LLM 离线回放）。执行序 spec T8 先行（时限风险前置），plan task 编号=执行序，spec task 号在标题括注。

**Tech Stack:** Python 3.11+ / pytest（unit T1 层）/ just task runner / structlog（`shenbi.logging.get_logger`）。

## Global Constraints（编译自 spec 项目级约束＋§Profile——M-2 修正：spec 无逐字块，此为编译面；F947/G0.9/G0.11 出自 single-model-sdd-prompt.md §Profile「plan 加项」；`lint_threshold_reconciliation --strict` 判据经 just check:53 接线在阶段 7 全量门统一跑——本 plan 各 task 不单独跑该 lint）

- **触面止于**（spec 验收 2，核验＝hunk 落点全在枚举内）：`chapter_drafting.py` 九函数（`_check_voice_density`/`_check_chapter_end_hook`/`_load_protagonist_names`/`_check_protagonist_presence`/`_check_protagonist`/`_check_transitions`/`_check_simile_band`/`ending_archetype_of`/`_check_content_uniqueness`）＋`voice_lexicon.py`＋`contracts/skills/genre_config.py`＋`tools/gate_power_replay.py`＋`tools/gen_gate_power_fixtures.py`＋`tools/lint_voice_meme.py`＋测试文件＋fixture 重摆＋baseline/提案 docs＋`reports/`——无未裁定检查被顺手改。
- **红测改钉保留原 FAIL 方向样本**（C1 双向义务——防全绿漂移）。
- **fixture 真实性 G0.9/G0.11**：scenario 输入只引用 `tests/fixtures/` 真实产物；变异 fixture 一律经 `tools/gen_gate_power_fixtures.py` 维护者侧重生成（provenance 头＋同源确定性），禁手造/手改/内联硬编码真实章文本。
- **阈值单源**：新常量只落 `voice_lexicon.py`/`chapter_drafting.py` 模块级单一声明点＋定标注释（vol1 定标，跨书重跑复核——B5）；单源断言测试执法（禁裸副本）。
- **门检查器纯函数幂等、无副作用**；`src/shenbi/` 禁 `print()`（structlog：`from shenbi.logging import get_logger`）；文件 I/O 走 `pathlib`。
- **commit pathspec 显式列文件**，禁 `git add -A`/`git add .`；conventional commits（`feat:`/`test:`/`fix:`/`docs:`）。
- **每 task 三件套**：红测双向＋50 章重跑（命令 `just gate-power novel-xinghuo-vol1 --out <workspace>/replay-T<N>.md`，数字进 task report；最终权威报告在 Task 8 落 `reports/`）＋baseline 行同步（归因/期望点火带列当轮更新；「最近回放数」统一在 Task 8 终值刷新）。
- **全离线**：SDD 全程禁真实 LLM dispatch（F947：验收不依赖 dispatch，全部 fixtures 回放/结构断言）。
- **测试层级**：全部 T1 层（per-skill unit，`tests/unit/gates/g4/`＋`tests/unit/tools/`）。

**实施前公共步骤（Task 1 首步内执行一次）：** `git rev-parse HEAD` 记录 BASE；跑 `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-baseline.md` 留改动前基线（已存在 reports/2026-11-20-gate-power-vol1.md 作对照源）。

---

### Task 1: spec T8 · payoff_density 变异负例＋三残行分类收口（执行序最先——时限约束项）

**Files:**
- Modify: `tools/gen_gate_power_fixtures.py`（MUTATIONS 注册表＋`payoff_axis_stripped` 变异函数，~:296 后插入函数、:346 后注册）
- Create: `tests/fixtures/gate-power/plans/chapter-9-plan.md`（维护者侧引擎重生成）
- Create: `tests/fixtures/gate-power/chapter-9-payoff-stripped.md`（维护者侧引擎重生成，verbatim_copy --full）
- Modify: `tests/unit/gates/g4/test_gate_power_negatives.py`（新增 `test_payoff_stripped_warns_payoff_density`）
- Modify: `docs/framework/gate-power-baseline.md`（三残行分类回填）

**Interfaces:**
- Consumes: `MUTATIONS: dict[str, Callable[..., str]]`（:325-347 既有注册表）；`PROVENANCE_TMPL`（:29-34）；引擎 CLI（`main()` :350-384：`--mutation` choices 自动从 MUTATIONS 派生）。
- Produces: `payoff_axis_stripped(text: str) -> str`（变异函数）；`MUTATIONS["payoff_axis_stripped"]`；红测 `test_payoff_stripped_warns_payoff_density`。

- [ ] **Step 1: 写失败红测**（`tests/unit/gates/g4/test_gate_power_negatives.py` 末尾追加；测试走真实 g4 管线，fixture 为引擎产物）

```python
def test_payoff_stripped_warns_payoff_density() -> None:
    """spec #118 T8：chapter-9 plan 的 **payoff 拍** 轴登记被删 → payoff_density WARN 行.

    负例=WARN-only（该门无 mf 臂）；变异产物=plans/chapter-9-plan.md
    （引擎 payoff_axis_stripped）＋配对章 chapter-9-payoff-stripped.md（verbatim
    --full）。窗口 k∈{7,8,9}：7/8 plan fixture 缺席＋9 轴被删 → 无轴 WARN 必发。
    """
    res = _g4("chapter-9-payoff-stripped.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.payoff_density"]
    assert rows and rows[0]["s"] == "WARN" and "无轴登记" in rows[0]["r"], rows
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_payoff_stripped_warns_payoff_density -v`
Expected: FAIL with `KeyError`/fixture-missing 或 rows 为空（fixture 与变异均未生成，`_g4` 读不到章或 WARN 行不存在）。

- [ ] **Step 3: 实现变异函数并注册**（`tools/gen_gate_power_fixtures.py`，`content_duplicated` 后插入）

```python
def payoff_axis_stripped(text: str) -> str:
    """删 **payoff 拍** 行的轴登记段（轴(债|名声|名字数|进度)→无轴）→ payoff_density WARN.

    变异源=plan 文件（先例 hookdecl_mismatched）；门侧正则锚
    chapter_drafting.py:1374-1375（\*\*payoff 拍\*\*[：:].*轴[（(]?(债|名声|名字数|进度)）。
    """
    return re.sub(
        r"(\*\*payoff 拍\*\*[：:][^｜\n]*?)｜轴[（(](?:债|名声|名字数|进度)[)）]",
        r"\1",
        text,
    )
```

并在 `MUTATIONS` 字典 `"content_duplicated": content_duplicated,` 行后追加：

```python
    "payoff_axis_stripped": payoff_axis_stripped,
```

- [ ] **Step 4: 维护者侧重生成两个 fixture**（源=gitignored 真实产物，G0.9；同源确定性）

```bash
uv run python tools/gen_gate_power_fixtures.py \
  novel-xinghuo-vol1/plans/chapter-9-plan.md \
  tests/fixtures/gate-power/plans/chapter-9-plan.md \
  --mutation payoff_axis_stripped --full
uv run python tools/gen_gate_power_fixtures.py \
  novel-xinghuo-vol1/chapters/chapter-9.md \
  tests/fixtures/gate-power/chapter-9-payoff-stripped.md \
  --mutation verbatim_copy --full
```

Expected: 各打印一行 `<out> <- <source> [...]`；`grep -c "轴(进度)" tests/fixtures/gate-power/plans/chapter-9-plan.md` 输出 `0`（原行 `扮猪吃虎｜轴(进度)｜小兑现` 已去轴段）。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v`
Expected: 全 PASS（含新测与既有 25 测——plan fixture 新增不触既有 chapter-1 面）。

- [ ] **Step 6: baseline 三残行分类回填**（`docs/framework/gate-power-baseline.md`）

`G4.cd.payoff_density` 行（:61）：分类 `unclassified`→`floor-untested`，证据列填 `tests/unit/gates/g4/test_gate_power_negatives.py::test_payoff_stripped_warns_payoff_density`，归因改「回放 0 行发射（v3 近窗无轴登记章为 0——WARN-only 臂；**spec #118 T8 红测已建**）；裁定 2026-11-20 floor-untested」。
`G4.cd.quote_type` 行（:62）：分类→`floor-untested`，证据列填 `tests/unit/gates/g4/test_spec76_voice_quote.py::test_g4cd_quote_type_three_point_sync`（既有行为红测——真实 g4 管线三场景 must_fix 点火，r2/I-7 裁定依据：分类证据义务已满足，不为 M-1 形态同源重复建测），归因注记同。
`cd.provenance_anchor` 行（:75）：分类→`floor-untested`，证据列填 `tests/unit/gates/g4/test_spec83_provenance_anchor.py::test_provenance_mismatch_warns_and_match_green`，归因注记同。

- [ ] **Step 7: 验收 lint＋commit**

Run: `uv run python tools/lint_gate_power_baseline.py` → Expected: 三残行 WARN 消失（零 `unclassified` 残行）、exit 0（未到升格锚仅 WARN 面，此处应全清）。

```bash
git add tools/gen_gate_power_fixtures.py tests/unit/gates/g4/test_gate_power_negatives.py tests/fixtures/gate-power/plans/chapter-9-plan.md tests/fixtures/gate-power/chapter-9-payoff-stripped.md docs/framework/gate-power-baseline.md
git commit -m "test: spec #118 T8 payoff_density 变异负例＋三残行分类收口（quote_type/provenance_anchor 引既有行为红测为证据链）"
```

### Task 2: spec T1 · voice_density 两级拆分（在场 hard＋密度 WARN）

**Files:**
- Modify: `src/shenbi/text/voice_lexicon.py`（:33 后新增 `DEFAULT_VOICE_PRESENCE_MIN = 1` 常量＋注释）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:1391-1438`（`_check_voice_density` 两级化＋模块头 `from shenbi.logging import get_logger`/`log = get_logger(__name__)`——若文件尚无则加）
- Modify: `src/shenbi/contracts/skills/genre_config.py:142-148`（validator 扩 `presence_min∈[1,5]`）
- Modify: `tools/lint_voice_meme.py:123-127`（旧键消费跟随密度臂口径）
- Modify: `tools/gen_gate_power_fixtures.py`（`voice_stripped` 变异扩展——Step 2；`ACCOUNTING_VERBS` 须显式 import：`from shenbi.text.voice_lexicon import ACCOUNTING_VERBS`，该文件现未导入）
- Modify: `tests/fixtures/gate-power/chapter-1-voice-stripped.md`（Step 2 重生成）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（改钉＋三态样本）；Create `tests/unit/text/test_voice_threshold_single_source.py`（单源断言）；`tests/unit/contracts/`（validator 红测两例）
- Modify: `docs/framework/gate-power-baseline.md`（`G4.cd.voice_density` 行期望点火带＋归因）

**Interfaces:**
- Consumes: `distinct_voice_signals(body: str, catchphrases: list[str] | None) -> int`（voice_lexicon.py:90，三类信号同计——hard 臂操作数，r2/I-4 钉死）；`DEFAULT_VOICE_DENSITY_MIN = 2`（:33，密度臂缺省）；`read_genre_config`；`_g4` 测试助手。
- Produces: `DEFAULT_VOICE_PRESENCE_MIN = 1`（在场臂缺省，单源）；`_check_voice_density` 两级行为：`memo_v2 ∧ signals < presence_min` → mf `G4.cd.voice_density:{fp}:{signals}<{presence_min}`（absent=三类全零才 FAIL）；`signals ≥ presence_min ∧ signals < density_min` → WARN 行（劝谏面）；过线 → PASS 行。config 键：新 `voice_density_min.presence_min∈[1,5]`（validator :146-148 扩展）；旧 `min_per_chapter∈[0,5]` 读入仅填密度臂＋`log.warning` deprecate。

- [ ] **Step 1: 实现首日离线重算**（M-2 判据钉——预期数进 task report）

```bash
uv run python -c "
from pathlib import Path
from shenbi.text.voice_lexicon import catchphrases_from_card, distinct_voice_signals
from shenbi.gates.shared import strip_narrative_body
cps = catchphrases_from_card(Path('novel-xinghuo-vol1/characters/protagonist.md').read_text(encoding='utf-8'))
chs = [p for p in sorted(Path('novel-xinghuo-vol1/chapters').glob('chapter-*.md')) if len(p.stem.split('-'))==2 and p.stem.split('-')[1].isdigit()]
sig = [distinct_voice_signals(strip_narrative_body(p.read_text(encoding='utf-8')), cps) for p in chs]
print(f'n={len(sig)} absent(0)={sig.count(0)} ==1: {sig.count(1)} >=2: {sum(1 for s in sig if s>=2)}')"
```

Expected（阶段 3 审查同款重算参照）: `absent(0)` 为小数目（审查实测 82 章面 =1；以本命令 50 纯章形输出为准）——**该数写进 task-2-report.md 作为重跑对照钉**。

- [ ] **Step 2: 变异引擎扩 `voice_stripped`＋重生成 fixture（实测钉：现 fixture signals=1——口癖灭但账房动词残存 1 类；新语义 1≥1 不 FAIL，须灭三类至 0 保旧测 FAIL 方向）**

`tools/gen_gate_power_fixtures.py` `voice_stripped`（:66-71 `_VOICE_NEUTRAL` 消费处）追加二段中和：

```python
def voice_stripped(text: str) -> str:
    """口癖短语→中性语＋账房动词/自嘲反问收尾中和 → signals=0（spec #118 T1 改钉）.

    r2 实测：仅灭口癖留 signals=1（账房动词残存）——两级化后 1≥presence 不
    FAIL；须三类全灭保 `test_voice_stripped_fails_voice_density_gate` 的
    must_fix 断言（0<1，C1 原 FAIL 方向保留）。
    """
    out = text
    for old, new in _VOICE_NEUTRAL:
        out = out.replace(old, new)
    for verb in ACCOUNTING_VERBS:  # from shenbi.text.voice_lexicon import ACCOUNTING_VERBS
        out = out.replace(verb, "记下")
    out = re.sub(r"(吧|呢)？(\s|$)", r"。\2", out)  # 自嘲反问收尾中和
    return out
```

维护者侧重生成：`uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-voice-stripped.md --mutation voice_stripped`
验证：`uv run python -c "...distinct_voice_signals(strip_narrative_body(Path('tests/fixtures/gate-power/chapter-1-voice-stripped.md').read_text()), cps)..."` → Expected: `0`。

- [ ] **Step 3: 写失败红测**（`test_voice_stripped_fails_voice_density_gate` 断言**不变**——0<1 仍 must_fix；新增三态测试追加其后）

```python
def test_voice_density_two_level_three_states(tmp_path: Path) -> None:
    """spec #118 T1 裁定 B 三态：0 FAIL / 1 类在场过＋密度 WARN / ≥2 纯 PASS.

    构造性输入（G0.9 允许面——结构级样本基于真实 fixture）：复用重生成后的
    voice-stripped fixture（signals=0）＋真实卡/plan 前置物，逐态注入。
    """
    import shutil

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    for label, inject, want_fail, want_warn in (
        ("absent", "", True, False),  # signals=0 → FAIL（=旧测同 fixture 面）
        (
            "presence-only",
            "他心想：这笔我先记下。",
            False,
            True,
        ),  # 真实卡口癖原串「这笔我先记下。」逐字在场 → 1 类（C-1 修正：原注入缺「我」非口癖原串）
        (
            "dense",
            "他心想：这笔我先记下。入账的时辰到了。",
            False,
            False,
        ),  # 口癖＋账房动词「入账」→ 2 类 → 纯 PASS
    ):
        d = tmp_path / label
        d.mkdir()
        for sub in ("characters", "plans"):
            shutil.copytree(FIX_DIR / sub, d / sub, dirs_exist_ok=True)
        base = (FIX_DIR / "chapter-1-voice-stripped.md").read_text(encoding="utf-8")
        (d / "chapter-1.md").write_text(base.rstrip("\n") + f"\n\n{inject}\n", encoding="utf-8")
        res = json.loads(
            g4_chapter_drafting([str(d / "chapter-1.md")], str(d), str(d), repo_root=None)
        )
        mf = res.get("must_fix", [])
        warn_rows = [
            c for c in res["checks"] if c["id"] == "G4.cd.voice_density" and c["s"] == "WARN"
        ]
        assert any(m.startswith("G4.cd.voice_density:") for m in mf) == want_fail, (label, mf[:3])
        assert bool(warn_rows) == want_warn, (label, warn_rows)
```

- [ ] **Step 4: 跑红测确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_voice_density_two_level_three_states -v`
Expected: FAIL——`absent` 或 `presence-only` 态断言失败（变异已扩但门未两级化：absent 0<2 FAIL ✓ 而 presence-only 1<2 仍 must_fix ✗）。

- [ ] **Step 5: 实现**（`voice_lexicon.py` :33 `DEFAULT_VOICE_DENSITY_MIN = 2` 后）

```python
#: 声口在场性 hard 臂缺省（spec #118 T1 裁定 B 两级拆分：在场 ≥1 hard——三类
#: 信号任一在场即过，absent＝三类全零才 FAIL）。genre-config 覆盖键
#: voice_density_min.presence_min（validator 域 [1,5]——0 非法，堵逐书清零
#: hard 臂面）；旧键 min_per_chapter 只填密度/WARN 臂（deprecate）。
#: v1 (2026-11-20, spec #118): 1（vol1 定标，跨书重跑复核——B5）
DEFAULT_VOICE_PRESENCE_MIN = 1
```

`chapter_drafting.py` `_check_voice_density` 全函数替换为：

```python
def _check_voice_density(ctx: CheckContext, c: list[dict[str, Any]], mf: list[str]) -> None:
    """Spec #76 v2 声口密度（spec #118 T1 裁定 B 两级拆分）.

    hard 臂＝在场性（distinct_voice_signals ≥ presence_min，absent＝口癖/
    账房动词/自嘲反问三类全零才 FAIL——r2/I-4 钉死操作数）；密度臂＝原 ≥2
    语义降 WARN 报告行（劝谏面不拦章）。旧 config 键 min_per_chapter 只填
    密度臂（T1(a)：映射进 hard 臂会使裁定在携带旧覆盖的项目上静默不生效）。
    """
    _body = ctx.narrative
    _cps: list[str] = []
    if ctx.project_dir:
        _pcard = Path(ctx.project_dir) / "characters" / "protagonist.md"
        if _pcard.is_file():
            _cps = catchphrases_from_card(_pcard.read_text(encoding="utf-8"))
    _signals = distinct_voice_signals(_body, _cps)
    _vdm = (
        (read_genre_config(ctx.project_dir or str(ctx.pf.parent)) or {})
        .get("market_params", {})
        .get("voice_density_min", {})
    )
    _presence_min = (
        int(_vdm.get("presence_min", DEFAULT_VOICE_PRESENCE_MIN))
        if _vdm
        else DEFAULT_VOICE_PRESENCE_MIN
    )
    if _vdm and "min_per_chapter" in _vdm:
        _density_min = int(_vdm["min_per_chapter"])
        log.warning(
            "genre_config voice_density_min.min_per_chapter deprecated: fills density(WARN) arm only; use presence_min for the hard arm (spec #118 T1)",
            file=str(ctx.fp),
            value=_density_min,
        )
    else:
        _density_min = DEFAULT_VOICE_DENSITY_MIN
    if ctx.memo_v2 and _signals < _presence_min:
        # 束6 逐字化报文保留（缺席修复指引不变）
        _miss = [p for p in _cps if p not in _body]
        _cp_part = (
            f"未在场卡口癖（须逐字照抄、一字不可改）："
            f"{'；'.join(f'『{p}』' for p in _miss[:4])}；另可计分："
            if _miss
            else "卡口癖已全在场——补其余信号；可计分："
        )
        mf.append(
            f"G4.cd.voice_density:{ctx.fp}:{_signals}<{_presence_min} "
            f"(v2 章——声口信号完全缺席；{_cp_part}"
            f"账房动词任一（如『{'』『'.join(ACCOUNTING_VERBS[:3])}』）"
            f"或自嘲反问收尾（『…吧？』『…呢？』句式）；修复者: drafting)"
        )
        return
    if ctx.memo_v2 and _signals < _density_min:
        c.append(
            {
                "id": "G4.cd.voice_density",
                "file": ctx.fp,
                "s": GateStatus.WARN,
                "r": f"声口密度 {_signals}<{_density_min}（劝谏面不拦章——spec #118 T1 两级拆分）",
            }
        )
        return
    c.append(
        {
            "id": "G4.cd.voice_density",
            "file": ctx.fp,
            "s": GateStatus.PASS if ctx.memo_v2 else GateStatus.WARN,
            "r": f"signals={_signals}/presence≥{_presence_min}"
            + ("" if ctx.memo_v2 else " (v1 章——dispatch 域外，WARN 口径)"),
        }
    )
```

（模块头若尚无 logger：`from shenbi.logging import get_logger` ＋ `log = get_logger(__name__)`；`from shenbi.text.voice_lexicon import DEFAULT_VOICE_PRESENCE_MIN` 并入 :11-13 既有 import。）

`genre_config.py` :146-148 validator 扩展（旧键块后加新键块）：

```python
        # （重审轮 2 新问题修正）旧键检查改在场守卫形——先改既有 :146-148 块：
        #   旧形： if vdm is not None and not 0 <= vdm.get("min_per_chapter", -1) <= 5:
        #   新形： if vdm is not None and "min_per_chapter" in vdm and not 0 <= vdm["min_per_chapter"] <= 5:
        # 缺省 -1 会把 presence_min-only 新式 config 误拒（域违报文还使测试
        # match="presence_min" 经 dict repr 错误通过）——守卫后缺席键不检查。
        # spec #118 T1: 两级拆分——在场臂新键（0 非法：堵逐书清零 hard 臂）；
        # 旧键 min_per_chapter 域不变（密度/WARN 臂，消费端 deprecate WARN）。
        # 嵌套层级（plan 审查 C-2 修正）：v=market_params，vdm=voice_density_min
        # 子 dict——presence_min 是 vdm 的子键，非 v 的。
        vpm = vdm.get("presence_min") if isinstance(vdm, dict) else None
        if vpm is not None and not 1 <= int(vpm) <= 5:
            raise ValueError(f"market_params.voice_density_min.presence_min∈[1,5], got {vpm}")
```

（注：vdm 缺席而 presence_min 存在＝新键裸奔——同块 `if vdm is None and "presence_min" in v.get("voice_density_min", {}) ... ` 形不成立（vdm 即该 dict）；实际裸奔形=vdm 为非 dict/缺 presence_min——validator 只治域不治缺席，缺席走消费端缺省 1，键族完整性由 genre-config 契约文档同步声明。）

**validator 红测**（追加到 `tests/unit/contracts/test_market_params.py`——复用其 `_base()`/`_FULL` 构造与 `GenreConfig.model_validate` 面；重审新缺陷 1 修正：真实校验面是 pydantic validator 经 model_validate 触发，且 hook_grading 须携带合法 `max_consecutive_micro∈[1,3]` 否则先被旧检查绊住）：

```python
def test_voice_presence_min_domain_rejects_zero() -> None:
    """spec #118 T1(b): presence_min∈[1,5]——0 非法（堵逐书清零 hard 臂）."""
    mp = _FULL | {"voice_density_min": {"presence_min": 0}}
    with pytest.raises(ValueError, match="presence_min"):
        GenreConfig.model_validate(_base() | {"market_params": mp})


def test_voice_presence_min_only_config_accepted() -> None:
    """旧键在场守卫：presence_min-only 新式 config 合法（不被旧键缺省 -1 误拒）."""
    mp = _FULL | {"voice_density_min": {"presence_min": 2}}
    cfg = GenreConfig.model_validate(_base() | {"market_params": mp})
    assert cfg.market_params["voice_density_min"] == {"presence_min": 2}
```

**旧键→臂映射钉（pipeline 级，入 negatives 文件）**——signals=1（口癖在场）＋genre-config 旧键 min_per_chapter=2 → 断言无 `G4.cd.voice_density` must_fix 且密度 WARN 行在（风险 M-6「测试断言」义务；目录构造复用三态测试 presence-only 场景＋`genre-config.json` 写入 `{"market_params": {"voice_density_min": {"min_per_chapter": 2}}}`）。

`tools/lint_voice_meme.py:123-127` 跟随：读键逻辑改为「density 臂取 `min_per_chapter`（缺省 `DEFAULT_VOICE_DENSITY_MIN`）」口径不变、注释补一句「spec #118 T1 起 min_per_chapter 语义=密度/WARN 臂」。

- [ ] **Step 6: 单源断言测试**（Create `tests/unit/text/test_voice_threshold_single_source.py`）

```python
"""spec #118 T1/I-2: 声口阈值单源断言（可执行替代空转 lint 判据）."""

from __future__ import annotations

import subprocess
from pathlib import Path

from shenbi.text.voice_lexicon import (
    DEFAULT_VOICE_DENSITY_MIN,
    DEFAULT_VOICE_PRESENCE_MIN,
)

REPO = Path(__file__).resolve().parents[3]


def test_threshold_constants_pinned() -> None:
    assert DEFAULT_VOICE_PRESENCE_MIN == 1
    assert DEFAULT_VOICE_DENSITY_MIN == 2


def test_no_bare_copies_outside_single_source() -> None:
    """仓内（src/＋tools/）除单源 voice_lexicon 外无 presence/density 阈裸副本."""
    out = (
        subprocess.run(
            [
                "grep",
                "-rn",
                "-E",
                "DEFAULT_VOICE_(PRESENCE|DENSITY)_MIN\\s*=\\s*[0-9]",
                "src/",
                "tools/",
            ],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        .stdout.strip()
        .splitlines()
    )
    assert all("voice_lexicon.py" in ln for ln in out), out
```

- [ ] **Step 7: 跑全量门测＋重跑对照**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/text/test_voice_threshold_single_source.py tests/unit/contracts/ -v`（contracts 面覆盖 genre_config validator 改动）
Expected: 全 PASS（改钉 voice_stripped 仍 FAIL 方向＋三态＋单源断言）。

Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T2.md`
Expected: `G4.cd.voice_density` 行——新 FAIL 数＝Step 1 离线重算 `absent(0)` 数（14→该数），其余转 WARN/PASS；数字写 task-2-report.md 对照。

- [ ] **Step 8: baseline 行同步＋commit**

`gate-power-baseline.md` `G4.cd.voice_density` 行：归因追加「**裁定 B 已执行（spec #118 T1）**：hard 臂=在场 ≥1（absent X 章 FAIL——见 replay-T2），密度臂 WARN N 章」；期望点火带填「FAIL=absent 章数；WARN=密度带外章数」。

```bash
git add src/shenbi/text/voice_lexicon.py src/shenbi/gates/g4/chapter_drafting.py src/shenbi/contracts/skills/genre_config.py tools/lint_voice_meme.py tools/gen_gate_power_fixtures.py tests/fixtures/gate-power/chapter-1-voice-stripped.md tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/text/test_voice_threshold_single_source.py tests/unit/contracts/ docs/framework/gate-power-baseline.md
git commit -m "feat: spec #118 T1 voice_density 两级拆分——在场 hard＋密度 WARN＋genre-config 键迁移钉死＋单源断言"
```

### Task 3: spec T2 · hook 多字/结构臂＋单字降 WARN＋镜像等价钉

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`_check_chapter_end_hook` :1208-1237 三态化）
- Modify: `tools/gate_power_replay.py`（`hook_window_attribution` :128-147 同步＋锚注释更新）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（新增单字-only WARN 测）；`tests/unit/tools/test_gate_power_replay.py`（两例镜像↔门等价钉）

**Interfaces:**
- Consumes: 门内联张力正则（:1211-1212）；镜像 `HOOK_TENSION_RE`/`SINGLE_CHAR_TENSION`（:110/:113）；`hook_window_attribution(content) -> dict`（含 `multi`/`singles`/`single_char_only` 键）。
- Produces: 门三态——`has_multi（多字张力词）∨ has_q ∨ has_ledger` → PASS 行；仅单字命中 → `s=WARN` 行（id 不变 `G4.cd.chapter_end_hook`，r=「仅单字张力词命中（…）——多字/？/账目行臂未中，劝谏面」）；全灭 → mf `G4.cd.no_hook`（不变）。镜像 `hook_window_attribution` 增 `gate_class: "hard"|"single_only"|"none"` 键（与门三态同名映射）。

- [ ] **Step 1: 写失败红测**（negatives 新增；mirror 等价钉两例）

```python
def test_hook_single_char_only_warns_not_fails() -> None:
    """spec #118 T2 裁定 A：单字-only 命中→WARN 行非 FAIL（三态中间档）.

    构造：真实章尾窗仅留单字张力词（多字/？/数字串全灭）——voice-stripped
    同款手法在 hook_killed 基础上保留单字。fixture 由引擎新增变异
    hook_single_only 生成（Step 3）。
    """
    res = _g4("chapter-1-hook-single-only.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
    mf = res.get("must_fix", [])
    assert rows and rows[0]["s"] == "WARN" and "单字" in rows[0]["r"], rows
    assert not any(m.startswith("G4.cd.no_hook:") for m in mf), mf[:3]
```

`tests/unit/tools/test_gate_power_replay.py` **`TestNarrativeWindow` 类内追加**（M-1 修正：仓内无 TestWindowAttribution 类——既有窗口一致性测试 :96 在 TestNarrativeWindow）：

```python
def test_mirror_gate_equivalence_single_only(self) -> None:
    """spec #118 T2/I-6 等价钉①：镜像 single_char_only ⟺ 门 WARN."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    fp = Path("tests/fixtures/gate-power/chapter-1-hook-single-only.md").resolve()
    attr = hook_window_attribution(fp.read_text(encoding="utf-8"))
    res = json.loads(g4_chapter_drafting([str(fp)], str(fp.parent), str(fp.parent), repo_root=None))
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
    assert attr["gate_class"] == "single_only" and attr["single_char_only"]
    assert rows and rows[0]["s"] == "WARN" and not res.get("must_fix")


def test_mirror_gate_equivalence_hard_arms(self) -> None:
    """等价钉②：多字/？/账目行臂真 ⟺ 门 PASS 行（真实 fixture 章既有形态）."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    fp = Path("tests/fixtures/gate-power/chapter-1-fatigue-flooded.md").resolve()
    attr = hook_window_attribution(fp.read_text(encoding="utf-8"))
    res = json.loads(g4_chapter_drafting([str(fp)], str(fp.parent), str(fp.parent), repo_root=None))
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.chapter_end_hook"]
    assert attr["gate_class"] == "hard"
    assert attr["has_q"] or attr["multi"] or attr["has_ledger"]
    assert rows and rows[0]["s"] == "PASS"
```

- [ ] **Step 2: 跑红测确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_hook_single_char_only_warns_not_fails "tests/unit/tools/test_gate_power_replay.py::TestNarrativeWindow::test_mirror_gate_equivalence_single_only" -v`
Expected: FAIL——fixture 未生成（前）/现行门把单字-only 判 PASS（`gate_class` 键不存在，断言 KeyError）。

- [ ] **Step 3: 新变异＋门三态化＋镜像同步**

变异函数（`tools/gen_gate_power_fixtures.py`，hook_killed 后）：

```python
def hook_single_only(text: str) -> str:
    """尾窗张力词单字化（多字→『还』、？→。、数字串→汉字）→ 单字-only 命中.

    spec #118 T2 三态中间档负例：多字/？/账目行臂全灭、单字臂保留。
    """
    paras = narrative_window(text)
    head, tail = paras[:-8], paras[-8:]
    out = []
    for p in tail:
        q = re.sub(r"然而|不过|依然|尚未|未解|不知|等待|没说|没答|未完|代价", "还", p)
        q = re.sub(r"[？?]", "。", q)
        q = re.sub(r"\d+", "数", q)
        out.append(q)
    return "\n\n".join(head + out)
```

注册 `MUTATIONS` ＋ 维护者侧生成：
```bash
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-hook-single-only.md --mutation hook_single_only
```

门改动（`_check_chapter_end_hook` :1208-1237 的判定块替换；词表拆分进模块级常量＝单源，两文件同形注释互指）：

```python
# chapter_drafting.py 模块级（_check_chapter_end_hook 上方）：
#: 章尾钩多字张力词（spec #118 T2 裁定 A：多字∨？∨账目行=hard 臂；单字集
#: 但却还仍瞒藏账欠谜 与账房腔母题同词表——单字-only 命中降 WARN）。
#: vol1 定标，跨书重跑复核（B5）。镜像=tools/gate_power_replay.py:110（同形同步义务）。
HOOK_MULTI_TENSION_RE = re.compile(r"(然而|不过|依然|尚未|未解|不知|等待|没说|没答|未完|代价)")
HOOK_SINGLE_TENSION = frozenset("但却还仍瞒藏账欠谜")
```

`if window_cjk >= 30:` 块内：

```python
            has_q = bool(re.search(r"[？?]", window_text))
            has_multi = bool(HOOK_MULTI_TENSION_RE.search(window_text))
            # 账目钩 (P1-3, 2026-10-23)——≥2 独立数字串（runs 非 bare chars）
            has_ledger = len(re.findall(r"\d+", window_text)) >= 2
            has_single = any(ch in HOOK_SINGLE_TENSION for ch in window_text)
            if has_multi or has_q or has_ledger:
                c.append(
                    {
                        "id": "G4.cd.chapter_end_hook",
                        "file": ctx.fp,
                        "s": GateStatus.PASS,
                        "window_cjk": window_cjk,
                    }
                )
            elif has_single:
                c.append(
                    {
                        "id": "G4.cd.chapter_end_hook",
                        "file": ctx.fp,
                        "s": GateStatus.WARN,
                        "r": (
                            "仅单字张力词命中（多字/？/账目行臂未中）——"
                            "单字集与账房腔母题同词表，降劝谏面（spec #118 T2）"
                        ),
                        "window_cjk": window_cjk,
                    }
                )
            else:
                excerpt = window_text[:30]
                mf.append(
                    f"G4.cd.no_hook:{ctx.fp}:{window_cjk}字合并窗口未检出疑问句/张力词/账目行；"
                    ...  # 原 FAIL 文案原样保留
                )
```

（原 :1211-1212 混编正则删除——多字项迁入 `HOOK_MULTI_TENSION_RE`，单字项迁入 `HOOK_SINGLE_TENSION`；但|却 在单字集内保留。）

镜像同步（`gate_power_replay.py:110-147`）：镜像文件内与门同形定义 `HOOK_MULTI_TENSION_RE`/`HOOK_SINGLE_TENSION`（两文件同形注释互指锚；镜像的 `hits` 来自全词表 `HOOK_TENSION_RE`，multi 判定用 `hits - SINGLE_CHAR_TENSION` 与门 `HOOK_MULTI_TENSION_RE` 语义等价——plan 审查 M-5 已核），`hook_window_attribution` 返回 dict 增键：

```python
        "gate_class": (
            "hard" if (has_q or has_ledger or (hits - SINGLE_CHAR_TENSION))
            else ("single_only" if hits & SINGLE_CHAR_TENSION else "none")
        ),
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/tools/test_gate_power_replay.py -v`
Expected: 全 PASS——原 `test_hook_killed_real_chapter_fails_hook_gate` 仍红方向（全灭 FAIL，C1 保留）＋新三态＋两等价钉。

- [ ] **Step 5: 重跑对照＋baseline＋commit**

Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T3.md`
Expected: `G4.cd.chapter_end_hook` 行 50 章＝P(多字/？/账目)＋W(15 单字-only)＋F0——**15 单字章转 WARN**（对照 replay-baseline.md 的 single_char_only=15 归因数）；数字入 task-3-report.md。baseline 行归因追加「裁定 A 已执行（spec #118 T2）：单字-only 15 章转 WARN，镜像等价钉×2 入测」。

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tools/gate_power_replay.py tools/gen_gate_power_fixtures.py tests/fixtures/gate-power/chapter-1-hook-single-only.md tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/tools/test_gate_power_replay.py docs/framework/gate-power-baseline.md
git commit -m "feat: spec #118 T2 hook 多字/结构臂＋单字-only 降 WARN＋镜像 gate_class 等价钉×2"
```

### Task 4: spec T3 · protagonist roster 去重＋名字单独下限

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`_load_protagonist_names` :483-516 去重；`_check_protagonist_presence` :460-480 名字下限臂）
- Modify: `tools/gate_power_replay.py`（I-4：`ARM_TO_CANONICAL` 增 `"G4.cd.protagonist_name_absent": "G4.cd.protagonist_presence"`＋`STATE_FREE_IDS` 增 `G4.cd.protagonist_presence` 族回射面——新 mf 臂须回射父行，否则 post118 报告出现无 baseline 行的未注册 canonical）；`tools/lint_gate_power_baseline.py`（`EXPLICIT_SUPPLEMENT` 同步增补——helper-append 形扫描不可见）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（roster 单测＋名字 0/代词≥3 红）

**Interfaces:**
- Consumes: `split_frontmatter`（:497 既有）；`_check_protagonist_presence(text, names, threshold=3) -> list[str]`；`_check_protagonist(ctx, c, mf)`（:1240 调用处——SKIP 行 :1244-1252 保持）。
- Produces: roster 无重复（frontmatter＋YAML 双源同名只入一次）；`_check_protagonist_presence` 新增名字臂 issue 前缀 `G4.cd.protagonist_name_absent`（名字计数 0 且代词撑阈时发射——名字集=names 排除裸代词「他」）。

- [ ] **Step 1: 写失败红测**

```python
def test_protagonist_roster_no_duplicate_append(tmp_path: Path) -> None:
    """spec #118 T3 裁定 A：frontmatter＋YAML 双源同名只入表一次（:495/:508 双 append 修复）."""
    from shenbi.gates.g4.chapter_drafting import _load_protagonist_names

    d = tmp_path / "proj"
    (d / "characters").mkdir(parents=True)
    (d / "characters" / "protagonist.md").write_text(
        "---\nname: 那罕\n---\n\n声口：账房腔。\n", encoding="utf-8"
    )
    names = _load_protagonist_names(str(d))
    assert names.count("那罕") == 1, names  # 双 append 实弹形 ['那罕','那罕','他']


def test_protagonist_name_absent_fails_presence_gate(tmp_path: Path) -> None:
    """spec #118 T3 裁定 B：名字 0/代词 ≥3 → G4.cd.protagonist_name_absent FAIL."""
    from shenbi.gates.g4.chapter_drafting import _check_protagonist_presence

    issues = _check_protagonist_presence("他数着账。他合上册。他睡了。", ["那罕", "他"])
    assert any(i.startswith("G4.cd.protagonist_name_absent") for i in issues), issues
```

- [ ] **Step 2: 跑红测确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_protagonist_roster_no_duplicate_append tests/unit/gates/g4/test_gate_power_negatives.py::test_protagonist_name_absent_fails_presence_gate -v`
Expected: FAIL——`names.count==2`（双 append）＋新 issue 前缀不存在。

- [ ] **Step 3: 实现**

`_load_protagonist_names` 的双 append 修复（:493-508 重写为单源优先＋去重兜底）：

```python
# spec #118 T3: frontmatter regex 与 YAML 双解析同名双 append 修复——
# YAML 单源优先（split_frontmatter 边界单源 #85 T6），regex 仅作
# YAML 失败时的回退；两路产出最终去重（保序）。
name: str | None = None
fm_text, _body = split_frontmatter(text)
if fm_text:
    try:
        import yaml as _yaml

        fm_core_lines = fm_text.split("\n")
        fm_core = "\n".join(fm_core_lines[1:-2] if fm_core_lines[-1] == "" else fm_core_lines[1:-1])
        fm = _yaml.safe_load(fm_core)
        if isinstance(fm, dict) and "name" in fm:
            name = str(fm["name"]).strip()
    except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
        pass  # malformed YAML frontmatter → fall back to regex name match below
if name is None:
    match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    if match:
        name = match.group(1).strip()
if name:
    names.append(name)
```

`_check_protagonist_presence` 名字臂（:475-480 重写）：

```python
    total = sum(text.count(name) for name in protagonist_names)
    # spec #118 T3 裁定 B：名字（非裸代词）单独 ≥1——堵「代词撑满门」面；
    # POV 声明替代走实现取 ≥1 简单面（spec 声明）。
    pronouns = {"他", "她", "它"}
    name_roster = [n for n in protagonist_names if n not in pronouns]
    issues: list[str] = []
    if total < threshold:
        issues.append(
            f"G4.cd.protagonist_absent: protagonist appears {total} times (threshold: {threshold})"
        )
    if name_roster and not any(text.count(n) for n in name_roster):
        issues.append(
            "G4.cd.protagonist_name_absent: 名字（非代词）0 次出现——代词不可撑门（spec #118 T3）"
        )
    return issues
```

- [ ] **Step 4: 跑全量＋重跑对照**

Run: `uv run pytest tests/unit/gates/g4/ -v`
Expected: 全 PASS——`test_protagonist_vanished_real_chapter_fails_presence_gate` 仍红方向（全替换→total<3 FAIL，C1 保留）。

Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T4.md`
Expected: 名字缺席章数＝**实测 X（预期 0；非 0 记 finding 回裁不放宽——I-5 判据）**；**重放 protagonist 中位/最小不变（I-4 修正：镜像 `_protagonist_names` 本就单名去重——门侧去重修的是门内计数非镜像）**；数字入 task-4-report.md。baseline 行归因追加「裁定 A+B 已执行（spec #118 T3）：roster 去重＋名字下限臂；C 阈值重标定推迟至本重跑取数后」。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tools/gate_power_replay.py tools/lint_gate_power_baseline.py tests/unit/gates/g4/test_gate_power_negatives.py docs/framework/gate-power-baseline.md
git commit -m "fix: spec #118 T3 protagonist roster 去重＋名字（非代词）单独 ≥1 下限臂＋回射注册"
```

### Task 5: spec T4 · transition per-1000 密度封顶（1.0/千字）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`_check_transitions` :954-956 封顶化＋模块级常量）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（改钉 flooded——断言形态更新）；`tests/unit/gates/g4/test_transition_cap_single_source.py`（Create——单源断言）

**Interfaces:**
- Consumes: `count_transition_words(strip_narrative_body(ctx.content))`（:937 口径不变）；`ctx.wc`（`word_count_md`＝叙事体 CJK 计数——**密度分母同口径**）。
- Produces: 模块级 `TRANSITION_CAP_PER_1000 = 1.0`（单源常量＋定标注释）；判定 `tc / max(ctx.wc, 1) * 1000 > TRANSITION_CAP_PER_1000` → mf（报文带密度值与封顶）；mf id `G4.transition` 不变（报文形 `{tc}>{max_t}` → `{density:.2f}>{cap}/千字`）。

- [ ] **Step 1: 写失败测试**（常量**尚未落码**——I-5/重审新缺陷 3 修正：常量块已移除，只留测试；Step 2 的 ImportError 红钉成立；常量＋定标注释在 Step 3 与实现同落）

Create `tests/unit/gates/g4/test_transition_cap_single_source.py`:

```python
"""spec #118 T4/I-2: 转折封顶常量单源断言（可执行替代空转 lint 判据）."""

from __future__ import annotations

import subprocess
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import TRANSITION_CAP_PER_1000

# 本文件在 tests/unit/gates/g4/ 下——parents[3]=tests/，repo 根须取 parents[4]
# （plan 审查 I-2 修正：parents[3] 会 cwd 到 tests/ 使 grep 空输出断言虚设）。
REPO = Path(__file__).resolve().parents[4]


def test_cap_constant_pinned() -> None:
    assert TRANSITION_CAP_PER_1000 == 1.0


def test_density_caliber_recaptured(tmp_path: Path) -> None:
    """重标定行为区分红测（I-5）：旧阈带内/新封顶外章——tc=4, wc≈2000 →
    旧 max(5,2)=5 PASS vs 新密度 2.0>1.0 FAIL（构造性输入，G0.9 允许面）."""
    import json as _json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    ch = d / "chapter-1.md"
    # wc（word_count_md 叙事体 CJK）≈2000：每段 50 CJK ×40 段；tc=4：4 段首带
    # 计数面连接词（不过，/此时，/突然，/终于，——count_transition_words 面）。
    paras = [f"第{i}段" + "字" * 48 + "。" for i in range(40)]
    paras[3] = "不过，" + paras[3]
    paras[11] = "此时，" + paras[11]
    paras[19] = "突然，" + paras[19]
    paras[27] = "终于，" + paras[27]
    ch.write_text("---\n---\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
    res = _json.loads(g4_chapter_drafting([str(ch)], str(d), str(d), repo_root=None))
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.transition:") for m in mf), mf[:3]  # 新封顶下 4/2.0>1.0 FAIL


def test_no_bare_copies_outside_single_source() -> None:
    out = (
        subprocess.run(
            ["grep", "-rn", "-E", "TRANSITION_CAP_PER_1000\\s*=\\s*[0-9.]+", "src/", "tools/"],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        .stdout.strip()
        .splitlines()
    )
    assert all("chapter_drafting.py" in ln for ln in out), out
```

- [ ] **Step 2: 跑测确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_transition_cap_single_source.py -v`
Expected: FAIL with `ImportError: cannot import name 'TRANSITION_CAP_PER_1000'`。

- [ ] **Step 3: 实现**（模块级常量落码＋:954-956 替换——常量定标注释：vol1 定标（B5——跨书重跑复核）：50 纯章形 gate-caliber 实测（word_count_md 叙事体 CJK 分母＋strip_narrative_body 计数面，2026-11-20 replay-baseline 同源）median=0.000/P95≈0.36/max=0.809 → 取 1.0＝max·1.24 裕度；flooded 负例密度 ≫1 仍 FAIL）

```python
    # spec #118 T4 裁定 B: per-1000 密度封顶（绝对阈 max(5, wc//1000) 退役）。
    _density = tc / max(ctx.wc, 1) * 1000
    if _density > TRANSITION_CAP_PER_1000:
        mf.append(f"G4.transition:{ctx.fp}:{tc}次/千字{_density:.2f}>{TRANSITION_CAP_PER_1000}")
    else:
        c.append(
```

（else 分支 PASS 行原样保留。）

- [ ] **Step 4: 改钉 flooded 红测**（断言 `G4.transition:` 前缀不变——报文形变不影响前缀匹配；`test_transition_flooded_real_chapter_fails_transition_gate` 保持原断言即应仍绿——跑之验证）

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_transition_flooded_real_chapter_fails_transition_gate tests/unit/gates/g4/test_transition_cap_single_source.py -v`
Expected: 双 PASS（flooded 密度 ≫1 仍红——原 FAIL 方向保留 C1；单源断言绿）。

- [ ] **Step 5: 重跑对照＋baseline＋commit**

Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T5.md`
Expected: `G4.transition` 50 章 **零新 FAIL**（观测带内——max 0.809<1.0）；transition 归因段中位 0 不变；数字入 task-5-report.md。baseline 行归因追加「裁定 B 已执行（spec #118 T4）：per-1000 封顶 1.0（vol1 定标注释在常量处），零新 FAIL」。

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/gates/g4/test_transition_cap_single_source.py docs/framework/gate-power-baseline.md
git commit -m "feat: spec #118 T4 transition per-1000 密度封顶 1.0（vol1 定标）＋单源断言"
```

### Task 6: spec T5 · simile narrative-only 换装＋WARN 路由报告行

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`_check_simile_band` :1289-1313）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（改钉 `test_simile_flooded_warns_pileup_side`）
- Modify: `docs/framework/gate-power-baseline.md`（行 56 分类依据迁移注记）

**Interfaces:**
- Consumes: `count_similes(content) -> dict`（返回键 `per_1000`）；`strip_narrative_body`。
- Produces: 计量面 `count_similes(strip_narrative_body(ctx.content))`（M7 对照列转正）；带外→报告行（`s=PASS`＋`r` 注记＋`per_1000` 载荷——同 scene_concreteness 报告先例；**不进 WARN 通道**）；带内→PASS 行（原样）。带常数 [2.0,4.0] 不变（B 重设带推迟——注释声明）。

- [ ] **Step 1: 改钉红测（先改测试——现行实现下新断言必红）**

`test_simile_flooded_warns_pileup_side` 重写为：

```python
def test_simile_flooded_warns_pileup_side() -> None:
    """spec #118 T5 裁定 C+A 改钉：narrative 口径 flooded → 报告行（s=PASS＋per_1000 载荷），WARN 通道无行."""
    res = _g4("chapter-1-simile-flooded.md")
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.simile_band"]
    assert rows, res["checks"][:3]
    assert rows[0]["s"] == "PASS", rows  # 报告行非 WARN 通道
    assert rows[0].get("per_1000", 0.0) > 4.0 and rows[0].get("r"), rows  # 计量载荷＋注记在
```

- [ ] **Step 2: 跑红测确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_simile_flooded_warns_pileup_side -v`
Expected: FAIL——现行 `s=="WARN"`（旧断言期望新形态，实现未动）。

- [ ] **Step 3: 实现**（:1289-1313 重写）

```python
def _check_simile_band(ctx: CheckContext, c: list[dict[str, Any]], mf: list[str]) -> None:
    """Spec #71 simile density band（spec #118 T5 裁定 C+A 换装）.

    计量面=narrative-only（strip_narrative_body——M7 对照列转正，消除
    PRE/POST 污染）；带外降报告行（s=PASS＋per_1000 载荷，不进 WARN 通道
    ——56% WARN 使劝谏通道失聪，裁定 A）。带 [2,4] 重设（裁定 B）推迟至
    C 换装后用干净数字评估——本 task 不动带常数。
    """
    simile_stats = count_similes(strip_narrative_body(ctx.content))
    per_1000 = simile_stats["per_1000"]
    if 2.0 <= per_1000 <= 4.0:
        c.append(
            {"id": "G4.cd.simile_band", "file": ctx.fp, "s": GateStatus.PASS, "per_1000": per_1000}
        )
    else:
        c.append(
            {
                "id": "G4.cd.simile_band",
                "file": ctx.fp,
                "s": GateStatus.PASS,
                "r": (
                    f"simile density {per_1000}/千字 outside [2,4] (low = dry, high = pile-up; "
                    "报告行非 WARN——spec #118 T5 裁定 A；俗套喻体抽检归审计)"
                ),
                "per_1000": per_1000,
            }
        )
```

- [ ] **Step 4: 跑测＋重跑对照**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -v` → 全 PASS。
Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T6.md`
Expected: `G4.cd.simile_band` WARN 列 **28→0**（全转报告行 PASS）；数字入 task-6-report.md。baseline 行 56：期望点火带填「WARN 通道 0 行」＋分类依据迁移注记「discriminating 依据自『WARN 开火』迁移为『红测可捕获（T5 改钉）』（r2/M-3）」。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/unit/gates/g4/test_gate_power_negatives.py docs/framework/gate-power-baseline.md
git commit -m "feat: spec #118 T5 simile narrative-only 计量换装＋带外路由报告行（WARN 通道 28→0）"
```

### Task 7: spec T6 · ending 扩分类器（限 ≤4 新形态）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`ending_archetype_of` :519-536 扩表）
- Create: `tests/fixtures/gate-power/chapter-N-ending-<form>.md`（≤4 件真实章尾窗拷贝——引擎 `ending_ledgered` 同款手法或尾窗追记形态句，维护者侧重生成）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（每新 archetype ≥1 真实样本归类断言）

**Interfaces:**
- Consumes: `ending_archetype_of(text) -> str | None`（四分支：账目形态/呢？自嘲/心里复述/复述起手）；`strip_narrative_body`＋尾窗 `[-220:]` 口径。
- Produces: ≤4 新 archetype 分支（形态名从采样归纳——**停手条件：扩后 None 率仍 >50% → 出 retire 提案回裁，不自行退役**）；每形态 ≥1 真实章样本红测。

- [ ] **Step 1: 采样 47 None 收尾**（维护者侧离线，清单入 task-7-report.md）

```bash
uv run python -c "
from pathlib import Path
from shenbi.gates.g4.chapter_drafting import ending_archetype_of
chs = [p for p in sorted(Path('novel-xinghuo-vol1/chapters').glob('chapter-*.md')) if len(p.stem.split('-'))==2 and p.stem.split('-')[1].isdigit()]
nones = [(p.name, ending_archetype_of(p.read_text(encoding='utf-8'))) for p in chs]
nones = [(n, t) for n, t in nones if t is None]
print(f'None total={len(nones)}')
for n, _ in nones: print(n)"
```

→ 逐个打开 None 章尾窗（`tail -c 1200`）人工归纳形态频次，取 ≤4 高频形（候选方向：对白悬停/动作收束/景物余韵/悬念问句——**以实际采样为准**，超出 4 形即止）。

- [ ] **Step 2: 写失败红测**（每形态一测；样本=真实章尾窗 fixture。示例模板——形态名/正则以 Step 1 归纳为准替换 `<form>`/`<RE>`）

```python
def test_ending_new_form_classified() -> None:
    """spec #118 T6：新 archetype <form> 至少 1 真实章样本归类非 None."""
    from shenbi.gates.g4.chapter_drafting import ending_archetype_of

    res = ending_archetype_of(
        (FIX_DIR / "chapter-<N>-ending-<form>.md").read_text(encoding="utf-8")
    )
    assert res == "<form>", res
```

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -k ending -v` → Expected: FAIL（新形态分支未实现，返回 None）。

- [ ] **Step 3: 实现**（`ending_archetype_of` 分支扩表——每分支带形态注释＋采样来源章号；fixture 由引擎 `ending_ledgered` 同款手法维护者侧生成：尾窗追加该形态收束句，或对采样命中章整拷贝 `--full`＋provenance 头）

```python
    # spec #118 T6 扩表（≤4 形态，vol1 采样归纳——来源章号见各分支注释；
    # 扩后 None 率仍 >50% 的停手条款见 spec）：
    if re.search(r"<RE>", tail):
        return "<form>"
    ...  # 其余新形态同式
```

- [ ] **Step 4: 跑测＋重跑对照**

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py -k ending -v` → 全 PASS（含既有 `test_ending_repeated_helper_three_ledger_closers`——账目形态分支不变，C1 保留）。
Run: `just gate-power novel-xinghuo-vol1 --out .superpowers/sdd/2026-11-20-spec118-gate-calibration-landing/replay-T7.md`
Expected: ending 归因段 None 章数 47→**新数（扩表覆盖率数字入 task-7-report.md；仍 >50% → 停手出 retire 提案回裁——此为回裁义务非本 task 失败）**。baseline 行 67 归因追加「裁定 A 已执行（spec #118 T6）：+K 形态，None 率 47/50→X/50」。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/fixtures/gate-power/chapter-*-ending-*.md tests/unit/gates/g4/test_gate_power_negatives.py docs/framework/gate-power-baseline.md
git commit -m "feat: spec #118 T6 ending 扩分类器（+K 形态，vol1 采样归纳）"
```

### Task 8: spec T7 · content_uniqueness P1 修＋fixture 重摆＋权威重跑报告

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`_check_content_uniqueness` :1082-1113 目录对齐＋SKIP 行）
- Move/Create: `tests/fixtures/gate-power/chapters/chapter-1-duplicated.md`＋`tests/fixtures/gate-power/chapters/chapter-3.md`（重摆＋维护者侧重生成）；Delete: `tests/fixtures/gate-power/project-output/`（旧路径残件）
- Modify: `tests/unit/gates/g4/test_chapter_drafting.py:34-53`（C-3：既有 `test_fails_when_content_overlap_above_40_percent` 建 `rd/project-output/chapters` 布局——目录切换后必红；其 `chapters = rd / "project-output" / "chapters"` 改 `rd / "chapters"`，docstring 同步）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（SKIP 显式红测＋既有 `test_content_duplicated...` 改路径）
- Create: `reports/2026-11-20-gate-power-vol1-post118.md`（权威终版重跑报告）
- Modify: `docs/framework/gate-power-baseline.md`（全行「最近回放数」终值刷新至 post118 报告）；`docs/framework/gate-calibration-proposals.md`（裁定表逐项标「已执行」）

**Interfaces:**
- Consumes: `_text_fingerprint`/`_fingerprint_of`（指纹口径不变）；`GateStatus.SKIP`（先例 `_check_protagonist` :1244-1252 同构发射）；`ctx.pf`（本章路径比对排除）。
- Produces: 比对目录 `Path(ctx.rd) / "chapters"`（对齐真实布局）；目录缺席/基数 ≤1 → SKIP 行（`id=G4.cd.content_uniqueness, s=SKIP, r=原因`——不再静默）；既有比对/40% 阈逻辑不变。**git 考古结论**（坏了/从未活过）写 task-8-report.md。

- [ ] **Step 1: git 考古**（结论入 task-8-report.md）

```bash
git log --oneline -S "project-output" -- src/shenbi/gates/g4/chapter_drafting.py | tail -5
git log --all --oneline --diff-filter=A -- "**/project-output/chapters*" | head -5
```

判定：门的 `rd/project-output/chapters` 布局是否曾对应任何真实生产布局（rd=round dir 语义下 chapters 落 `rd/chapters/`——预期结论「从未活过」；以考古输出为准）。另记（M-3）：`ctx.rd is None` 时仍零行发射（生产 dispatch 恒传 rd——dispatch_helper 布局面；SKIP 义务覆盖目录缺席/基数不足两态，rd-None 态记 task report 注记不扩验收）。

- [ ] **Step 2: 写失败红测**（SKIP 显式——空 rd 场景）

```python
def test_content_uniqueness_skip_row_when_dir_absent(tmp_path: Path) -> None:
    """spec #118 T7：目录缺席/基数≤1 → 显式 SKIP 行（含原因）非静默（r2/M-1 复用 SKIP 先例；I-3 双分支）."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    # 分支①（I-3 修正：章不落 chapters/ 下——目录缺席臂）：
    d = tmp_path / "proj"
    d.mkdir()
    ch = d / "chapter-1.md"
    ch.write_text("---\n---\n\n正文数段。\n", encoding="utf-8")
    res = json.loads(g4_chapter_drafting([str(ch)], str(d), str(d), repo_root=None))
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.content_uniqueness"]
    assert rows and rows[0]["s"] == "SKIP" and "比对目录缺席" in rows[0]["r"], rows
    # 分支②：目录在但基数 ≤1——r 含「基数」
    d2 = tmp_path / "proj2"
    (d2 / "chapters").mkdir(parents=True)
    ch2 = d2 / "chapters" / "chapter-1.md"
    ch2.write_text("---\n---\n\n正文数段。\n", encoding="utf-8")
    res2 = json.loads(g4_chapter_drafting([str(ch2)], str(d2), str(d2), repo_root=None))
    rows2 = [c for c in res2["checks"] if c["id"] == "G4.cd.content_uniqueness"]
    assert rows2 and rows2[0]["s"] == "SKIP" and "基数" in rows2[0]["r"], rows2
```

Run: `uv run pytest tests/unit/gates/g4/test_gate_power_negatives.py::test_content_uniqueness_skip_row_when_dir_absent -v`
Expected: FAIL——rows 为空（现行静默返回）。

- [ ] **Step 3: 实现**（:1082-1113 重写头部）

```python
def _check_content_uniqueness(ctx: CheckContext, c: list[dict[str, Any]], mf: list[str]) -> None:
    """F415-0815 memoized overlap vs other chapters.

    spec #118 T7（裁定二 P1 修）：比对目录对齐真实布局 rd/chapters（原
    rd/project-output/chapters 在生产布局缺席——门静默不跑，50 章回放
    0 行发射，#116 挖出的死门）；目录缺席/基数 ≤1 显式 SKIP 行（先例
    _check_protagonist :1244-1252 同构），不再静默。
    """
    if ctx.rd:
        chapters_dir = Path(ctx.rd) / "chapters"
        if not chapters_dir.exists():
            c.append(
                {
                    "id": "G4.cd.content_uniqueness",
                    "file": ctx.fp,
                    "s": GateStatus.SKIP,
                    "r": f"比对目录缺席: {chapters_dir}（spec #118 T7 显式 SKIP）",
                }
            )
            return
        other_chapters = list(chapters_dir.glob("chapter-*.md"))
        if len(other_chapters) <= 1:
            c.append(
                {
                    "id": "G4.cd.content_uniqueness",
                    "file": ctx.fp,
                    "s": GateStatus.SKIP,
                    "r": f"比对基数 ≤1（{len(other_chapters)}）——无跨章比对面（spec #118 T7）",
                }
            )
            return
        ...  # 既有指纹比对逻辑原样保留（:1090-1113 不动）
```

- [ ] **Step 4: fixture 重摆＋维护者侧重生成**（G0.9/G0.11——禁手移改内容）

```bash
uv run python tools/gen_gate_power_fixtures.py \
  novel-xinghuo-vol1/chapters/chapter-1.md \
  tests/fixtures/gate-power/chapters/chapter-1-duplicated.md \
  --mutation content_duplicated --full \
  --donor novel-xinghuo-vol1/chapters/chapter-3.md
cp tests/fixtures/gate-power/project-output/chapters/chapter-3.md \
   tests/fixtures/gate-power/chapters/chapter-3.md   # donor 比对章——verbatim_copy 产物原样重摆（provenance 头已在）
rm -r tests/fixtures/gate-power/project-output
```

既有 `test_content_duplicated_fails_content_overlap_gate` 的 `_g4("project-output/chapters/chapter-1-duplicated.md")` 改 `_g4("chapters/chapter-1-duplicated.md")`。跑之确认仍红（FAIL 方向保留——`G4.cd.content_overlap` mf）。

注意：`_g4` 传 `rd=FIX_DIR`——fixture `FIX_DIR/chapters/` 下章基数=2（duplicated+chapter-3），比对面成立。

- [ ] **Step 5: 跑全量＋权威重跑**

Run: `uv run pytest tests/unit/gates/g4/ tests/unit/tools/ -v` → 全 PASS。
Run: `just gate-power novel-xinghuo-vol1 --out reports/2026-11-20-gate-power-vol1-post118.md`
Expected: **史上首份 content_uniqueness 真实点火数据**（50 章 vs 82 章池比对——PASS/SKIP/FAIL 实况）；全检查前后对照数字（voice FAIL=absent 数/simile WARN 0/ending None 新数/hook 15→WARN）；高误报 → 记 finding 回裁不放宽。全行 baseline「最近回放数」刷新至 post118 报告；提案文档裁定表逐项标「已执行」。

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/fixtures/gate-power/chapters/ tests/fixtures/gate-power/project-output tests/unit/gates/g4/test_gate_power_negatives.py tests/unit/gates/g4/test_chapter_drafting.py reports/2026-11-20-gate-power-vol1-post118.md docs/framework/gate-power-baseline.md docs/framework/gate-calibration-proposals.md
git commit -m "fix: spec #118 T7 content_uniqueness 比对目录对齐＋显式 SKIP＋首份真实点火数据（fixture 重摆+权威重跑报告）"
```

（M-4 修正：`tests/fixtures/gate-power/project-output` 已列入上方 pathspec——已删目录的暂存由显式列路径承载，pathspec 含已删路径合法。）

---

## AC 覆盖表（spec 验收 §2 → task → test）

| AC | task | 验证 |
|---|---|---|
| 1. T1-T8 判据全绿（三件套） | Task 1-8 | 各 task Step「重跑对照」＋task-N-report.md |
| 2. diff 面止于九函数枚举（**M-6：模块级 hunk 预期在列**——Task 2 logger/presence_min import、Task 3 HOOK_* 常量、Task 5 TRANSITION_CAP 常量产生的 chapter_drafting.py 模块级 hunk 属九函数改动的附属面，核验时按「函数体＋其模块级常量/import 附属」口径） | 全部 | 阶段 7 `git diff origin/main..HEAD --stat` hunk 核验 |
| 3. just check 全绿（含哨兵零 WARN 残行） | 全部 | 阶段 7 `just check` |
| 4. 50 章重跑报告落 reports/（前后对照） | Task 8 | reports/2026-11-20-gate-power-vol1-post118.md |
| 5. 提案裁定表逐项「已执行」＋点火带首填 | Task 8 Step 5 | gate-calibration-proposals.md＋baseline 期望点火带列 |

**TDD 说明**：全部 task `test_kind: tdd_red_green`（行为改动＋红测先行）；Task 1/3/8 含 fixture 重生成步骤（维护者侧引擎，G0.9）。**复杂度：全部 infra**（`chapter_drafting.py`∈§Profile infra 模块清单——协调者亲实现，TDD 红→绿→重构纪律；每 task commit 后 fresh-context 首审出 `audit-T<N>.md`）。
