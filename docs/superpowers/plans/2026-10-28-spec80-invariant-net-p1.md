# Spec #80 P1 invariant-net Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **本项目补充**：全部 task 涉及 infra 模块（facts 新域/`gates/g4/`/`contracts/`/`pipeline/`）→ **协调者亲自实现**（v6 leaf/infra 分流铁律），逐 task TDD + task 后 fresh-context 重审产出 `.superpowers/sdd/audit-T<N>.md`。无 audit-T<N>.md 不得开始 T<N+1>。

**Goal:** 落地 spec #80 P1——规范事实库（props/counters/identity 三维）+ 唯一查询面 + F15/F16/F17 三门检 + 13 维四槽普查 + lint_invariant_coverage + 真实伤口 mutant CI（含 ch8 基线补全）+ regen-vol1 确定性 backfill。

**Architecture:** facts 是 `src/shenbi/facts/` 新域（StrEnum 词表 + pydantic schema + 纯函数 op 状态机 + flock 原子 JSON IO + 查询投影）；门检挂既有 G4 检查器族（G4.xc=cross_chapter.py、G4.cd=chapter_drafting.py、G4.cp=chapter_planning.py、G4.ss=state_settling.py），facts 缺席一律 skip+WARN（XC.registry 先例）；settle 双写（方案 b：op 走 decisions sidecar 加性键 `facts_ops`，Markdown 面零改动，G4.ss 一致性断言拦分叉）；mutant CI per-mutant check-id 断言。

**Tech Stack:** Python 3.11+ / pydantic（既有依赖）/ StrEnum / structlog / pytest。零新第三方依赖。

## Global Constraints

- **spec**：`docs/superpowers/specs/2026-10-28-spec80-invariant-net.md` rev5（commit 8ac16b26）——施工唯一真源
- **P1 边界**：验收 4（ch25-26 实弹）/5（G3.4 复评）=P2 运行侧，本 plan 不实现；投影层 projection.py=P3，不建
- **gate 纯度**（AGENTS.md）：门检纯函数幂等零副作用；op 应用=写侧住 facts 模块；F16s=纯读者 simulate
- **状态字面量单一信源**：新枚举唯一定义于 `src/shenbi/facts/enums.py`（StrEnum）；status-vocab.md 注册行值集全等；invariants.md 只引用不定义
- **无 print**：`src/shenbi/` 用 structlog；CLI stdout 走 `shenbi.cli_utils.emit_json`/`echo`
- **验证同构**：一切验证走 `uv run`/`just`（CI `uv run --frozen` 同构）；系统 python 不算证据
- **F947**：全部验收离线确定性（fixtures 断言 + lint），零真实 dispatch
- **G3.4 声明**：本 spec 无 LLM 产物评分场景（全离线结构性验证）——无需独立评分子 agent
- **契约三源同步**：改 SKILL.md reads/writes → `just lint-contracts` 绿 + `just generate` 生成物 diff 为空；禁止手改生成物
- **fixtures**：`tests/fixtures/invariant-mutants/` 只能是真实伤口导出（已入库两份）；mutant 的 facts 态种子=测试内构造（G0.9 构造性结构输入豁免，spec §3 钉死）
- **pathspec commit**：所有 commit 显式列文件，禁 `git add -A`

---

### Task 1: facts 域模块——词表 + schema + op 状态机（纯内存）

**Files:**
- Create: `src/shenbi/facts/__init__.py`
- Create: `src/shenbi/facts/enums.py`
- Create: `src/shenbi/facts/schemas.py`
- Create: `src/shenbi/facts/store.py`
- Create: `src/shenbi/exceptions.py`（追加 `FactsOpRejectedError`）
- Test: `tests/unit/facts/test_store_state_machine.py`

**Interfaces:**
- Produces（后续 task 消费的精确签名）:
  - `shenbi.facts.enums.PropOp`（StrEnum：`hold|transfer|acquire|lose`）
  - `shenbi.facts.enums.CounterOp`（StrEnum：`increment|set`）
  - `shenbi.facts.enums.IdentityOp`（StrEnum：`rename|set_alias`）
  - `shenbi.facts.enums.FactsDim`（StrEnum：`props|counters|identity`）
  - `shenbi.facts.schemas.PropFact`（pydantic：`entity: str; owner: str; events: list[str]`）
  - `shenbi.facts.schemas.CounterFact`（`name: str; value: int; history: list[str]`）
  - `shenbi.facts.schemas.IdentityFact`（`narration_name: str; from_ch: int; aliases: list[str]`）
  - `shenbi.facts.schemas.FactsFile`（`schema_: str = Field(alias="$schema"); dim: FactsDim; facts: dict[str, PropFact|CounterFact|IdentityFact]` 按 dim 多态；`ops_log: list[dict]`）
  - `shenbi.facts.schemas.PropTransferEvent`（`op: str; prop: str; from_: str = Field(alias="from"); to: str; evidence: str; chapter: int`）
  - `shenbi.facts.store.apply_prop_op(file: FactsFile, ev: PropTransferEvent) -> FactsFile`（拒收 raise）
  - `shenbi.facts.store.apply_counter_op(file: FactsFile, name: str, op: str, delta: int, chapter: int) -> FactsFile`
  - `shenbi.facts.store.apply_identity_op(file: FactsFile, op: str, *, new_name: str|None, alias: str|None, from_ch: int) -> FactsFile`
  - `shenbi.exceptions.FactsOpRejectedError(FrameworkError)`（属性 `reason: str`）
- 状态机规则（spec §1.1「无来源的二次获得=拒收」+ 实体副本语义 rev1）：
  - `transfer`：from_ 必须 == 当前 owner（或实体不存在时 from_ 为「初见」语义=首登）；to 成为新 owner
  - `acquire`：实体已存在且 owner ≠ to 且无声明来源 ⇒ **拒收**；实体不存在 ⇒ 合法初见获得
  - `lose`：owner 必须 == 声明者
  - **副本语义**：`entity` 键携带消歧后缀（如 `火纹骨哨·帖木哥支`）——同母题新实体=新键初见，老键不动（spec F16 硬约束「ch20 双实体并存全绿」由此达成：backfill 种子把帖木哥之哨立为独立键）
  - counter `increment`：value += delta 且 delta ≥ 1（`delta<=0` 拒收——单调律）；`set` 仅种子期合法（chapter=0）

- [ ] **Step 1: 失败测试**（红——模块不存在）

```python
# tests/unit/facts/test_store_state_machine.py
"""T1: facts op 状态机——纯内存合法性校验（spec §1.1）。

G0.9 注：facts 态种子为测试内构造的结构性输入（spec §3 钉死的豁免面）。
"""
import pytest

from shenbi.exceptions import FactsOpRejectedError
from shenbi.facts.schemas import FactsFile, PropTransferEvent
from shenbi.facts.store import apply_prop_op


def _props_file() -> FactsFile:
    return FactsFile.model_validate({
        "$schema": "shenbi-facts-v1",
        "dim": "props",
        "facts": {
            "火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": ["ch3 老驼所授"]},
        },
        "ops_log": [],
    })


def test_transfer_from_current_owner_passes():
    ev = PropTransferEvent.model_validate({
        "op": "transfer", "prop": "火纹骨哨", "from": "那罕", "to": "帖木哥",
        "evidence": "chapter-20.md L218", "chapter": 20,
    })
    out = apply_prop_op(_props_file(), ev)
    assert out.facts["火纹骨哨"].owner == "帖木哥"
    assert len(out.ops_log) == 1


def test_acquire_without_source_rejected():
    # ch20 伤口形态：帖木哥「我揣了二十年」——无来源的二次获得
    ev = PropTransferEvent.model_validate({
        "op": "acquire", "prop": "火纹骨哨", "from": "", "to": "帖木哥",
        "evidence": "chapter-20.md L218", "chapter": 20,
    })
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(_props_file(), ev)


def test_copy_entity_is_a_new_key_not_reacquisition():
    # 实体副本语义（rev1）：同母题新实体=独立键初见——修复后 ch20 双哨并存全绿
    ev = PropTransferEvent.model_validate({
        "op": "acquire", "prop": "火纹骨哨·帖木哥支", "from": "", "to": "那罕",
        "evidence": "chapter-20.md L218", "chapter": 20,
    })
    out = apply_prop_op(_props_file(), ev)
    assert out.facts["火纹骨哨"].owner == "那罕"       # 老键不动
    assert out.facts["火纹骨哨·帖木哥支"].owner == "那罕"
```

（counter 单调/identity rename 同型用例：`test_counter_increment_monotonic`、`test_counter_nonpositive_delta_rejected`、`test_identity_rename_updates_narration_name`——三用例与上述同构，实现时一并写。）

- [ ] **Step 2:** `uv run pytest tests/unit/facts/test_store_state_machine.py -q` → 预期 FAIL（ModuleNotFoundError）
- [ ] **Step 3:** 实现 `enums.py`（StrEnum 四枚）、`schemas.py`（pydantic v2 `model_config = {"extra": "forbid"}`，FactsFile 按 dim 判 facts 值类型）、`store.py`（三个 apply_* 纯函数，拒收 `raise FactsOpRejectedError(reason=...)`）、exceptions.py 追加一行类
- [ ] **Step 4:** 重跑 → PASS
- [ ] **Step 5:** `git add src/shenbi/facts/ src/shenbi/exceptions.py tests/unit/facts/ && git commit -m "feat(facts): op state machine for props/counters/identity (spec #80 T1)"`

---

### Task 2: facts IO——flock 原子读写 + pipeline-init 空种子

**Files:**
- Modify: `src/shenbi/facts/store.py`（追加 IO 函数）
- Modify: `src/shenbi/pipeline/cli.py` 或 init 路径（pipeline-init 空种子——先定位 init 落 truth/ 的函数再钉文件）
- Create: `tests/unit/facts/__init__.py`
- Test: `tests/unit/facts/test_store_io.py`

**Interfaces:**
- Consumes: `truth_io.truth_file_flock(path)`（`src/shenbi/pipeline/truth_io.py:123` 既有 flock）
- Produces:
  - `shenbi.facts.store.load_facts(project_dir: Path, dim: FactsDim) -> FactsFile | None`（缺席返回 None——门检 WARN 降级依据；文件损坏 raise `TruthFileParseError`）
  - `shenbi.facts.store.save_facts(project_dir: Path, file: FactsFile) -> None`（flock + tmp 文件原子 rename；`facts/$schema` 常量 `shenbi-facts-v1`）
  - `shenbi.facts.store.seed_empty(project_dir: Path) -> None`（pipeline-init bootstrap：三维空种子文件；幂等——已存在不覆写）

- [ ] **Step 1: 失败测试**

```python
# tests/unit/facts/test_store_io.py
"""T2: facts JSON 侧车 IO——flock 原子写 + 空种子 bootstrap（spec §1.1/§4 F15 空种子语义）。"""
from pathlib import Path

from shenbi.facts.enums import FactsDim
from shenbi.facts.store import load_facts, save_facts, seed_empty


def test_load_absent_returns_none(tmp_path: Path):
    assert load_facts(tmp_path, FactsDim.PROPS) is None  # 门检 WARN 降级依据


def test_save_then_load_roundtrip(tmp_path: Path):
    from tests.unit.facts.test_store_state_machine import _props_file
    save_facts(tmp_path, _props_file())
    back = load_facts(tmp_path, FactsDim.PROPS)
    assert back is not None and back.facts["火纹骨哨"].owner == "那罕"
    assert (tmp_path / "truth" / "facts" / "props.json").is_file()


def test_seed_empty_idempotent_creates_three_dims(tmp_path: Path):
    seed_empty(tmp_path)
    for dim in ("props", "counters", "identity"):
        assert (tmp_path / "truth" / "facts" / f"{dim}.json").is_file()
    seed_empty(tmp_path)  # 幂等：不覆写
```

- [ ] **Step 2:** 跑 → FAIL
- [ ] **Step 3:** 实现（`save_facts` 用 `truth_file_flock` + **`shenbi.safe_write.safe_write` 原子写**——purity lint `tools/lint_no_fs_mutation.py` 禁 src/shenbi/ 裸 `os.replace`/`write_text`，safe_write 是唯一 allowlist 原子写入口（plan 审查 R1-C2）；`seed_empty` 三维空 `FactsFile`）；pipeline-init 挂钩：在 init 流程写 truth/ 的函数里追加 `seed_empty(project_dir)` 一行（执行时 grep 定位 `pipeline init` 的 truth 播种点，实测文件名以现场为准——预期 `src/shenbi/pipeline/cli.py` init 命令或 `registry_seeding.py`）
- [ ] **Step 4:** 重跑 PASS + 既有 init 测试不破（`uv run pytest tests/unit/pipeline/ -q -k init`）
- [ ] **Step 5:** commit（pathspec 列全）

---

### Task 3: 查询面——`shenbi-facts` CLI + 现态紧凑投影

**Files:**
- Create: `src/shenbi/facts/query.py`
- Create: `src/shenbi/facts/cli.py`
- Modify: `pyproject.toml`（entry point `shenbi-facts = "shenbi.facts.cli:main"`）
- Test: `tests/unit/facts/test_query.py`

**Interfaces:**
- Produces:
  - `shenbi.facts.query.current_state(file: FactsFile, dim: FactsDim, *, chapter: int | None = None) -> dict[str, dict]`——现态紧凑视图：props=`{entity: {owner}}`、counters=`{name: {value}}`、identity=`{narration_name, from_ch, aliases}`（from_ch 必含——F15 检查消费，plan 审查 R1-I8）；`chapter` 参数=P1 相关性语义（spec rev5 R4-M5：全量返回，预留过滤位，P1 不实现历史点）
  - `shenbi.facts.query.planning_view(project_dir: Path, dim: FactsDim) -> str`——紧凑文本投影（token 有界，spec rev2 I4）；facts 缺席返回空串。**P1 消费方=R2 备注后为 P2**（R2-M8：P1 planning 读 `truth/facts/<dim>.json` 文件本体（T9 接线），context_assemble 接线 planning_view=P2 实弹期——函数保留为查询面 API 面，验收用 CLI/测试消费，非死线）
  - CLI：`shenbi-facts query --project <dir> --dim props|counters|identity [--chapter N]` → stdout JSON（`emit_json`）；缺席 dim → exit 1 + stderr WARN（`echo(err=True)`）

- [ ] **Step 1: 失败测试**（current_state 三维投影形态 + CLI 缺席降级 exit code——用 subprocess 或直接调 main(argv)）
- [ ] **Step 2:** FAIL → **Step 3:** 实现（query.py 纯函数；cli.py 参照 `shenbi.cost.report` 的 main 模式）→ **Step 4:** PASS + `uv run shenbi-facts query --project novel-xinghuo-vol1 --dim props`（种子未建 → 预期 exit 1 WARN，贴输出进 progress.md）
- [ ] **Step 5:** commit

---

### Task 4: 共享转移动词表 + F16 G4.cp 声明解析与合法性

**Files:**
- Modify: `src/shenbi/gates/shared.py`（追加 `TRANSFER_VERBS` 与 `TRANSFER_CONTEXT_RE`）
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（`g4_chapter_planning` 内追加 F16 声明检查）
- Test: `tests/unit/gates/g4/test_f16_cp_declarations.py`

**Interfaces:**
- Consumes: `load_facts(project_dir, FactsDim.PROPS)`；plan_format token 检查（chapter_planning.py:155-163 既有）
- Produces:
  - `shenbi.gates.shared.TRANSFER_VERBS: frozenset[str]`——闭集扩容：`{"递给","塞给","交给","送给","还给","还了","给了","留给","转手","递了","送了","交到","递到","递还","抽出","揣着","揣进","取出"}`（#75 闭集 ∪ 伤口形态「抽出/揣着/揣进/取出」四动词，spec F16——R2-M5 对齐字面集）
  - `shenbi.gates.g4.chapter_planning.parse_prop_declarations(memo_text: str) -> list[tuple[str, str, str, str]]`——解析结构化声明行 `物件@op: A→B`；返回 `(prop, op, from_, to)` **四元组**列表；`@hold` 单值形态 from_=to=owner 占位（plan 审查 R1-M10）
  - G4.cp 新 FAIL 消息前缀：`cp.prop_decl:`（G4_CHECK_MAP 注册 HARD——T8 接线）
  - 检查逻辑：声明 op 对 facts 现态合法性（transfer 的 from_==facts owner；副本后缀键=初见合法）；facts 缺席 ⇒ `WARN cp.prop_decl:no_facts`（skip 不 FAIL）；**旧备忘豁免必须 WARN 可见**：memo 无 `物件@` 声明行 ⇒ `WARN cp.prop_decl:legacy_memo`（13/24 静默死法禁令）。**plan_format 决策（钉死，plan 审查 R1-I4）**：声明行 P1 为 **v3 内可选**（不 bump v4——v4 硬门化=P2 全量声明行 backfill 完成后的升级动作）；P1 硬门=G4.cd 交接共现（undeclared handoff FAIL），G4.cp 声明合法性只对在场声明行生效

- [ ] **Step 1: 失败测试**

```python
# tests/unit/gates/g4/test_f16_cp_declarations.py
"""T4: F16 G4.cp——memo 物象声明解析 + 对 facts 现态合法性（spec §4 F16）。"""
from shenbi.gates.g4.chapter_planning import parse_prop_declarations


def test_parse_declaration_line():
    memo = "- 火纹骨哨@transfer: 帖木哥→那罕\n- 红纸包@hold: 那罕"
    decls = parse_prop_declarations(memo)
    assert decls[0] == ("火纹骨哨", "transfer", "帖木哥", "那罕")
    assert decls[1][1] == "hold"


def test_declared_transfer_from_wrong_owner_fails(tmp_path, monkeypatch):
    # facts owner=那罕，声明 from_=老驼 ⇒ 非法
    ...  # 组装 facts 文件 + 调 g4_chapter_planning，断言 FAIL 消息含 "cp.prop_decl:"
```

（豁免用例 `test_legacy_memo_warns_not_silent`：v3 无声明行备忘 ⇒ WARN 非静默 skip——**本 task 核心红测**。）

- [ ] **Step 2-5:** 同 TDD 循环；commit `feat(gates): F16 G4.cp prop declarations vs facts (spec #80 T4)`

---

### Task 5: F16 G4.cd 正文交接共现检查 + 实体副本

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（`g4_chapter_drafting` 内追加）
- Modify: `src/shenbi/gates/g4/cross_chapter.py`（不变量 4 的 facts 在场吸收开关）
- Test: `tests/unit/gates/g4/test_f16_cd_handoffs.py`

**Interfaces:**
- Consumes: `TRANSFER_VERBS`（T4）；`load_facts`；`parse_prop_declarations`（T4——G4.cd 读同一 memo 声明）
- Produces:
  - `shenbi.gates.g4.chapter_drafting.check_prop_handoffs(text: str, memo_text: str, props: dict[str, dict]) -> list[str]`——「非 owner 人名 + facts 实体名 + 交接动词」共现而 memo 无对应声明 ⇒ FAIL；返回消息前缀 `cd.prop_handoff:`
  - XC 吸收（spec rev2 I1 + plan 审查 R1-I7）：`cross_chapter.py` 不变量 4 prose 扫描段加 facts 在场开关——**facts 非空**（`load_facts(PROPS)` 非 None 且 facts dict 非空——空种子≡缺席，rev5 R4-M2 空洞堵死）时跳过该段——**含 memo 声明 hop 检查子段**（cross_chapter.py:664-678 registry-oracle 路径，R2-M10：facts 在场时不留双 oracle 并行，remediation 文本单一化）；缺席/空时照旧全 severity 运行（rev5 R4 措辞）
  - **动词表双路径单表**（plan 审查 R1-I5）：不变量 4 的 `_markers` alternation 改从 `shenbi.gates.shared.TRANSFER_VERBS` 构建（spec rev3 R2-M2——fallback 层同享扩容动词族，防两表漂移）
  - 实体键匹配：正文用短名（「骨哨」「火纹骨哨」），facts 键可带消歧后缀——匹配器 `entity_in_text(entity: str, text: str) -> bool`（后缀 `·` 分割前段 + 全名双形态）
  - 副本并存绿：ch20 修复语料（两把哨并存）+ 声明完备 ⇒ 零 FAIL（mutant T11 复用本用例）

- [ ] **Step 1: 失败测试**——核心用例直接吃伤口 fixture：

```python
# tests/unit/gates/g4/test_f16_cd_handoffs.py
"""T5: F16 G4.cd——正文无源交付拍拦截（spec §4 F16；ch20 L218 伤口）。"""
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import check_prop_handoffs

FIXTURE = Path("tests/fixtures/invariant-mutants/ch20-name-swap-prop-break.md")


def test_wound_undeclared_handoff_fails():
    text = FIXTURE.read_text(encoding="utf-8")
    # fixture L218 区域：「帖木哥把布解开…」「这个你揣着」——交接动词「揣着」+非 owner 帖木哥
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs(text, memo_text="", props=props)
    assert any("cd.prop_handoff:" in i for i in issues)
```

- [ ] **Step 2-5:** TDD 循环；commit

---

### Task 6: F15 叙事名——G4.xc narration_name

**Files:**
- Modify: `src/shenbi/gates/g4/cross_chapter.py`（`check_cross_chapter` 追加不变量段 + `g4_cross_chapter` 组装）
- Test: `tests/unit/gates/g4/test_f15_narration_name.py`

**Interfaces:**
- Consumes: `load_facts(project_dir, FactsDim.IDENTITY)`；`_sentence_spans`/对白剥离（cross_chapter 既有工具可复用；若无对白剥离则新写 `strip_dialogue(text) -> str`——剥「」『』段落）
- Produces:
  - `shenbi.gates.g4.cross_chapter.check_narration_name(text: str, identity: dict, memo_text: str, *, chapter: int | None = None) -> list[str]`（None ⇒ from_ch 边界检查关 ⇒ 别名判红——R2-I2：默认不得等价「改名前」）——剥对白后叙述段出现 `identity["aliases"]` 任一 ⇒ FAIL `XC.narration_name:`；备忘 `[旧名回溯]` 标记段落豁免（闪回）；`from_ch` 边界：`chapter < identity["from_ch"]` ⇒ 用旧名不 FAIL（M5 合法改名路径——chapter 参数 plan 审查 R1-I8）
  - facts 缺席/空种子（键缺失≡维缺失）⇒ WARN（skip 不 FAIL）——`XC.narration_name:no_facts`
  - 快照豁免（rev2 M1）：`g4_cross_chapter` 层过滤 `*pre-rev*`/`*snapshot*` 文件名（G2 先例）
  - `shenbi.gates.g4.cross_chapter.strip_dialogue(text: str) -> str`

- [ ] **Step 1: 失败测试**——伤口直接判红：

```python
# tests/unit/gates/g4/test_f15_narration_name.py
"""T6: F15——叙事名回退拦截（spec §4 F15；ch19/20 林烽×12 伤口）。"""
from pathlib import Path

from shenbi.gates.g4.cross_chapter import check_narration_name, strip_dialogue

FIXTURE = Path("tests/fixtures/invariant-mutants/ch20-name-swap-prop-break.md")


def test_stripped_dialogue_still_has_narration_hits():
    text = FIXTURE.read_text(encoding="utf-8")
    assert "林烽" in strip_dialogue(text)  # ≈7 处叙述段命中，剥对白后仍在


def test_alias_in_narration_fails():
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    issues = check_narration_name(FIXTURE.read_text(encoding="utf-8"), identity, memo_text="")
    assert any("XC.narration_name:" in i for i in issues)


def test_flashback_marker_exempts():
    memo = "- [旧名回溯] 本章闪回段用旧名"
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    # chapter=20 显式传参——隔离 memo 标记豁免（不被 from_ch 边界混淆，R2-M12）
    issues = check_narration_name("林烽翻过驿务条。", identity, memo, chapter=20)
    assert issues == []  # 豁免由 memo 标记声明（简化形态：memo 有标记即整章豁免闪回段）
```

（`from_ch` 边界用例 `test_before_from_ch_old_name_legal`；修复后 ch20 零林烽绿用例 `test_fixed_chapter_clean`——读 `novel-xinghuo-vol1/chapters/chapter-20.md`。）

- [ ] **Step 2-5:** TDD；commit `feat(gates): F15 narration-name invariant on G4.xc (spec #80 T6)`

---

### Task 7: F17 计数器三方对账——G4.cd

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（追加）
- Test: `tests/unit/gates/g4/test_f17_counters.py`

**Interfaces:**
- Consumes: `load_facts(project_dir, FactsDim.COUNTERS)`；`parse_counter_declarations(memo_text) -> list[tuple[str, int]]`（解析 `计数: <名> N+1` 形态行，本 task 产出）
- Produces:
  - `shenbi.gates.g4.chapter_drafting.parse_counter_declarations(memo_text: str) -> list[tuple[str, int]]`
  - `shenbi.gates.g4.chapter_drafting.check_counter_reconciliation(text: str, memo_text: str, counters: dict[str, dict]) -> list[str]`——三方对账（spec rev4 R3-M11）：①prose 总数族「N个名字/N名字」≡ facts 现值 ②memo `N+1` ≡ facts+1 ③prose 序数「第N个名字」≡ memo 声明值；任一不符 ⇒ FAIL `cd.counter:`；页范围总数锚（「第一页三个名字」）scope 锚定=忽略页限定词、取全局计数器比对（rev5 R5-M3 plan 钉死：P1 忽略页键，页内计数不立独立计数器）；**计数器语义钉死**（R2-I4a）：`鉴录名数`=那罕添入《鉴录》的名数（非全书总名数——canon ch17「四十三个名字」为全书口径，不与本计数器比对）；**激活规则**（R2-I4b）：F17 三检查仅当 memo 声明该计数器（`计数: <名>` 行在场）才激活，无声明 ⇒ WARN skip（旧备忘兼容期，防 ch17 类假红）；facts 缺席 ⇒ WARN
  - 计数名映射：facts counters 键 ↔ prose 计数词族（P1 仅《鉴录》名数：键 `鉴录名数`，prose 词族 `名字`）

- [ ] **Step 1: 失败测试**——counter-dup mutant 击杀面：

```python
# tests/unit/gates/g4/test_f17_counters.py
"""T7: F17——计数器三方对账（spec §4 F17；ch8↔ch9 计数互斥伤口）。"""
from pathlib import Path

from shenbi.gates.g4.chapter_drafting import check_counter_reconciliation

FIXTURE = Path("tests/fixtures/invariant-mutants/ch09-counter-dup.md")


def test_wound_total_vs_facts_baseline_fails():
    # facts 基线 count=3（ch8 已添第三个名字）；ch9 pre-rev 语料「第一页两个名字」⇒ 2≠3 FAIL
    text = FIXTURE.read_text(encoding="utf-8")
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo_text="", counters=counters)
    assert any("cd.counter:" in i for i in issues)


def test_ordinal_vs_memo_declared_fails():
    # memo 声明 N+1=3（「添第三个名字」），prose 序数也是第三——但 facts=3 时序数应为第四
    text = "他添了第三个名字——赵三。"
    memo = "- 计数: 鉴录名数 3+1"
    counters = {"鉴录名数": {"value": 3}}
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter:" in i for i in issues)  # 4≠3
```

（绿用例：修复后 ch9「第一页三个名字」+ facts=3 ⇒ 零 FAIL。）

- [ ] **Step 2-5:** TDD；commit

---

### Task 8: settle 双写——decisions `facts_ops` 加性键 + 写侧应用 + G4.ss 读侧校验

**Files:**
- Modify: `src/shenbi/contracts/schemas/decisions.py`（DecisionsDoc 追加 `facts_ops` 可选字段——extra:forbid 下必须同批，R4-I1）
- Modify: `docs/framework/decisions-schema.md`（Fields 表加行）
- Modify: `skills/shenbi-state-settling/SKILL.md`（:417 顶层键白名单行扩 `facts_ops` + op 发射契约段）
- Create: `src/shenbi/facts/settle_ops.py`（写侧：从 sidecar 读 ops → `apply_*` → `save_facts`，fail-fast 在 Markdown upsert 之前）
- Modify: `src/shenbi/gates/g4/state_settling.py`（G4.ss：op↔row 一致性断言 + identity 对账 + F16s 纯读者 simulate）
- Modify: settle commit 调用点（**plan 审查 R1-C1/R2-C1——写路径接线，三站点全枚举**）：①`src/shenbi/pipeline/chapter_loop.py:1884` ②`:2128`（两处 auto-commit `staging_auto_committed_state_settle`）③`src/shenbi/pipeline/cli.py:655-712 _commit_staging_for_checkpoint`（**review-path commit**，`state_settle_review_required=True` 时走——R2-C1 勘误：dispatcher/cli.py 无 staging 路径，「I3 镜像」实为此处 :681 注记）；三站点均在 staging commit 之后、Markdown upsert 之前调 `apply_sidecar_ops`，拒收 ⇒ staging commit 一并失败回滚（fail-fast 语义）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（G4_CHECK_MAP 追加：`"XC.narration_name": HARD, "cd.prop_handoff": HARD, "cp.prop_decl": HARD, "cd.counter": HARD, "ss.facts_ops": HARD, "ss.prop_row_match": HARD`——T4-T7 消息前缀的 severity 注册，spec rev5 R4-M1）
- Test: `tests/unit/facts/test_settle_ops.py`、`tests/unit/gates/g4/test_g4_ss_facts.py`

**Interfaces:**
- Consumes: T1 全部 apply_*；`DecisionsDoc`（decisions.py:71-86 既有）
- Produces:
  - `shenbi.contracts.schemas.decisions.FactsOps`（pydantic：`props: list[PropTransferEvent] = []; counters: list[CounterEvent] = []; identity: list[IdentityEvent] = []`）；`DecisionsDoc.facts_ops: FactsOps | None = None`
  - `shenbi.facts.settle_ops.apply_sidecar_ops(project_dir: Path, sidecar_path: Path) -> None`——读 `facts_ops` → 逐维 apply → save_facts；任一 op 拒收 ⇒ `FactsOpRejectedError` 上抛（settle 门 FAIL，attempts/escalation 既有协议），**不写任何文件**（fail-fast）。**RMW 锁范围**（R2-M9）：load→apply→save 全程持 `truth_file_flock(facts_path)`（save_facts 内部锁重入由外层锁覆盖——锁粒度按 path-keyed 既有语义）
  - G4.ss 检查（state_settling.py 内追加，纯读者）：①sidecar `facts_ops` 缺席且章内 truth/prop_registry 有本座行变更 ⇒ WARN（旧 settle 兼容期）②`ss.prop_row_match:`——sidecar 声明的 op 与 Markdown 行 owner 不一致 ⇒ FAIL（props 对账，facts canonical）③**`ss.identity_row_match:`**——facts 别名集 ↔ name_registry 别名/旌名行对账（登记名 prose 备注显式出范围——rev5 R4-I2，永不永久红；plan 审查 R1-I6）④F16s simulate：逐 op 对现 facts 干跑 apply，拒收 ⇒ FAIL `ss.facts_ops:illegal_op`（无 mutation）
  - `shenbi.facts.schemas.CounterEvent`（pydantic：`name: str; op: str; delta: int; chapter: int`）与 `IdentityEvent`（`op: str; new_name: str | None = None; alias: str | None = None; from_ch: int = 0`）——plan 审查 R1-M11 补定义
  - P2.5 规则扩展（decisions 校验器）：op 条目属 routine 免 rationale；**触发钉死**（R2-M6）：`FactsOps.rationale: str | None`，任一 op 的 op 值 ∉ 该实体当前态合法集（即 F16s simulate 会拒收的形态）⇒ rationale 必填非空（`lint_decisions_sources` 三源同批登记）

- [ ] **Step 1: 失败测试**——三点 enforcement（pydantic 接受 facts_ops 键 / fail-fast 拒收不留半写 / G4.ss 对账 FAIL）
- [ ] **Step 2-5:** TDD；SKILL.md 契约改完跑 `just lint-contracts` + `just generate`（生成物 diff 空）；commit

---

### Task 9: SKILL 契约扩展——planning 声明模板 + reads 接线

**Files:**
- Modify: `skills/shenbi-chapter-planning/SKILL.md`（writes 模板加 `物件@op`/`计数:` 结构化声明行示例；reads 加 facts 查询面产物）
- Modify: `skills/shenbi-state-settling/SKILL.md`（T8 已动白名单——本 task 补 op 发射示例段）
- Modify: `docs/framework/truth-files.yaml`（truth 段追加三行：`- {name: truth/facts/props.json, kind: truth, producer: pipeline}` ×3 维——spec §1.4 glob 口径的字面展开形态，R2-M12 注）
- Modify: `docs/framework/status-vocab.md`（域清单追加**四行**——plan 审查 R1-M12：PropOp/CounterOp/IdentityOp/FactsDim 四枚举全注册，值集与 StrEnum 成员全等）
- Test: `tests/unit/contracts/test_truth_files_facts.py`（注册对账：truth-files.yaml 含三维 + lint_status_strings 绿）

**Interfaces:**
- Consumes: T8 的 SKILL 白名单变更
- Produces: 契约三源同步后的 deps.json/docs/skills 生成物（`just generate` 产出，禁止手改）
- 注意：reads 声明的查询面产物形——`truth/facts/<dim>.json`（planning 读文件本体而非 CLI 产物；dispatcher 读切片走既有机制）

- [ ] **Step 1:** 红测（truth-files.yaml 三维注册 + status-vocab 三域可被 lint_status_strings 解析全等）
- [ ] **Step 2-5:** TDD + `just lint-contracts` + `just generate` 双绿；commit

---

### Task 10: 普查文档 + INDEX 必填节

**Files:**
- Create: `docs/framework/invariants.md`——13 维×四槽表（列：维度/载体（逐行命实，R3-M9）/声明/门检 check id/审计 reads/期相 P1|P2|P3/mutant 义务（F15+族或 facts 承载才 Yes，R3-I1））；P1 三行满槽，其余行按现状填（XC 门控维度注记既有红测文件名）；表头注明 CURRENT_PHASE=P1 语义与字面量「只引用不定义」
- Modify: `docs/superpowers/specs/INDEX.md`（登记与编号约定段追加「触及的不变量维度」必填节说明）
- Modify: `docs/superpowers/specs/2026-10-28-spec80-invariant-net.md`（自补该节——R2-I3 同批消自绊）
- Modify: `docs/superpowers/specs/2026-10-28-spec81-observability-net.md`（同上）
- Test: `tests/unit/tools/test_invariants_doc_shape.py`（表格列数/13 行数/P1 行四槽非空——文档形状守卫）

- [ ] **Step 1-5:** TDD（文档形状红测先行）；commit `docs(framework): invariant census 13-dim four-slot table (spec #80 T10)`

---

### Task 11: mutant CI——ch8 基线导入 + per-mutant check-id 断言

**Files:**
- Create: `tests/fixtures/invariant-mutants/ch08-counter-baseline.md`（从 `novel-xinghuo-vol1/chapters/chapter-8.md` 导出计数相关段落+备忘行——真实产物副本，G0.9/G0.11：带源文件 provenance 头）
- Create: `tests/gates/test_invariant_mutants.py`
- Test: 即本文件（自验）

**Interfaces:**
- Consumes: T4-T7 全部门检函数；fixtures 两份既有 + 本 task ch8 基线（**接线断言**——plan 审查 R1-M9：`test_ch08_baseline_derives_count_three` 从 ch08 fixture 解析「添第三个名字」断言基线 count=3，fixture 非死件）
- Produces: spec §7 验收 1 的载体；mutant 名归一规则（plan 审查 R1-M13）：普查表 mutant 名 hyphen 形 ↔ 测试名 underscore 形（`name-swap` ↔ `test_mutant_name_swap_killed_by_`），lint/T12 grep 前统一 `-.→_` 归一

- [ ] **Step 1: 写 mutant 测试**（per-mutant check-id 断言——spec rev2 I5）:

```python
# tests/gates/test_invariant_mutants.py
"""Spec #80 §3: 变异体全被拦=网眼无洞的机器证明。

per-mutant check-id 断言：合并语料不得掩盖死门。
G0.9: 语料=真实伤口导出 fixtures；facts 态种子=测试内构造（spec §3 豁免面）。
"""
from pathlib import Path

import pytest

from shenbi.gates.g4.chapter_drafting import check_counter_reconciliation, check_prop_handoffs
from shenbi.gates.g4.cross_chapter import check_narration_name

FIX = Path("tests/fixtures/invariant-mutants")


def test_mutant_name_swap_killed_by_f15():
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    issues = check_narration_name((FIX / "ch20-name-swap-prop-break.md").read_text("utf-8"), identity, "")
    assert any(i.startswith("XC.narration_name:") for i in issues)


def test_mutant_prop_chain_break_killed_by_f16():
    props = {"火纹骨哨": {"owner": "那罕"}}
    issues = check_prop_handoffs((FIX / "ch20-name-swap-prop-break.md").read_text("utf-8"), "", props)
    assert any("cd.prop_handoff:" in i for i in issues)


def test_mutant_counter_dup_killed_by_f17():
    counters = {"鉴录名数": {"value": 3}}  # ch8 基线：第三个名字=抱门框老人，count=3
    text = (FIX / "ch09-counter-dup.md").read_text("utf-8")
    memo = "- 计数: 鉴录名数 2+1"  # pre-rev 备忘：把赵三当第三个——与 ch8 冲突
    issues = check_counter_reconciliation(text, memo, counters)
    assert any("cd.counter:" in i for i in issues)
```

- [ ] **Step 2:** `uv run pytest tests/gates/test_invariant_mutants.py -q` → 三 mutant 全 FAIL 断言过 = PASS（若 F15/F16/F17 任一未拦 ⇒ 红——即死门探测器）
- [ ] **Step 3:** 绿语料对极（防误报面）：修复后 ch9/ch20 + 声明完备种子 ⇒ 三检查零 FAIL（spec §7 验收 3）
- [ ] **Step 4:** 全量 `uv run pytest tests/gates/ tests/unit/facts/ tests/unit/gates/g4/ -q`
- [ ] **Step 5:** commit

---

### Task 12: lint_invariant_coverage + just check 接线

**Files:**
- Create: `tools/lint_invariant_coverage.py`
- Modify: `justfile`（check target 追加一行 `uv run python tools/lint_invariant_coverage.py`，与 lint_status_strings 并列）
- Test: `tests/unit/tools/test_lint_invariant_coverage.py`

**Interfaces:**
- Consumes: `docs/framework/invariants.md`（T10 表）、`tests/gates/test_invariant_mutants.py`（T11 mutant 名单）、`tests/fixtures/invariant-mutants/` 目录
- Produces: exit 0/1 CLI（模式照 `tools/lint_status_strings.py`：structlog + 逐违规输出 + sys.exit）
- lint 谓词（spec §2 + R3 修正）：
  - 表形状：13 行×七列，期相列 ∈ {P1,P2,P3}
  - `CURRENT_PHASE = "P1"`（模块常量，随批次 bump——R3-M10）
  - 期相 ≤ CURRENT_PHASE 的行：四槽非空，否则红
  - mutant 义务行（义务列=Yes 且期相≤CURRENT_PHASE）：`tests/gates/test_invariant_mutants.py` 须有对应 `test_mutant_<name>_killed_by_` 用例（源码 grep），否则红
  - INDEX 活跃项（`Status: Active`）含「触及的不变量维度」节，否则红（P1 只校 P1 期相维度存在性）
  - **P1 缩窄声明**（plan 审查 R1-M16）：spec §2「扫全部 check id 对照普查表」的 code→table 全量对账=P2+ 期责任；P1 lint 只校 P1 期相行的四槽/mutant/INDEX 节，非缩窄违 spec——spec §2 期相列机制（rev3 R2-M3）即为此设计
  - 字面量「只引用不定义」：invariants.md 不得含 `= "` 形态的值定义（防 doc 私定义）

- [ ] **Step 1-5:** TDD（用 tmp invariants.md 喂正反例）；接线 justfile 后跑 `just check` 全绿；commit

---

### Task 13: regen-vol1 backfill 工具 + 验收 3 绿语料 + 收尾

**Files:**
- Create: `tools/facts_backfill.py`（确定性种子派生——`tools/plan_craft_backfill.py` 先例模式；禁手写 JSON）
- Test: `tests/unit/tools/test_facts_backfill.py`
- 验收汇总进 progress.md（无独立 commit 若纯验证；有 fixture/工具修复则列 pathspec）

**Interfaces:**
- Produces: `tools/facts_backfill.py --project novel-xinghuo-vol1 [--apply]`（**dry-run 为默认**——R2-M7 对齐 plan_craft_backfill 先例与 F947 立场：默认零写入，`--apply` 才落盘）——①从修复后章节正典派生三维种子（props：24 章经手链现状 owner——含 `火纹骨哨`（那罕）与 `火纹骨哨·帖木哥支`（那罕，ch20 副本键）；counters：`鉴录名数=4`（ch9 后：陆秉文/阿六/老人/赵三）；identity：narration_name=那罕、from_ch=3、aliases=[林烽]）②memo 声明行 backfill（11 份既有声明行键形态归一 + 13 份旧备忘补 `物件@op` 行——从章节正文+registry 交叉派生）③registry 陈旧行重写（赵三行/《鉴录》行/「临」备注——**绝不整文件重生成**，rev5 R4-I2）；**行↔键匹配**（R2-M11）：`ss.prop_row_match` 用 T5 `entity_in_text` 同型匹配器对齐 registry 行键（「火纹骨哨（老驼所授·主线）」↔facts「火纹骨哨」）；facts 键无 registry 行（帖木哥支）=初见不补写 P1；骨哨主行 ch20 经手由 op 追补（transfer 老驼线→记录帖木哥交付拍）④默认 dry-run 打印 diff 零写入（`--apply` 才写）
- 验收 3 断言（`tests/unit/tools/test_facts_backfill.py` 内，**plan 审查 R1-C3 修正**）：绿断言用 **per-chapter 前置态种子**（G0.9 测试内构造豁免）——ch9 检查喂 count=3 前置态（ch8 后、ch9 前）、ch20 检查喂 `火纹骨哨·帖木哥支` owner=帖木哥 前置态；直接喂终态种子（count=4/双哨皆那罕）会撞 F17 总数对账与 F16 cp 合法性而假红——as-of 态 P1 由测试构造，`--as-of` CLI=P2。终态种子仍为工具交付（运行侧 ch25+ settle 消费）

- [ ] **Step 1-5:** TDD；跑 `uv run python tools/facts_backfill.py --project novel-xinghuo-vol1`（默认 dry-run）贴输出进 progress.md（真实项目文件 P1 不落写——运行侧 backfill 由用户/P2 执行，本 task 交付工具+离线断言）；commit

---

## 验收覆盖表（spec §7 → task → 验证命令）

| spec 验收 | task | 可执行验证 |
|---|---|---|
| 1. mutant 测试全绿（P1 三 mutant 被拦） | T11 | `uv run pytest tests/gates/test_invariant_mutants.py -v` |
| 2. lint_invariant_coverage 进 just check 且绿 | T12 | `just check`（含新 lint）+ `uv run python tools/lint_invariant_coverage.py` |
| 3. 修复后语料过 F15/F16/F17（ch20 双哨全绿/骨哨合法/计数单调） | T11+T13 | `uv run pytest tests/unit/tools/test_facts_backfill.py tests/gates/test_invariant_mutants.py -q`（绿语料对极用例） |
| （§6 P1 双契约合规：backfill 同批） | T8+T9+T13 | `just lint-contracts` + `just generate` diff 空 + backfill 工具交付 |
| 4/5（P2 运行侧） | — | 本 plan 边界外（F947 切层，spec §6 rev1） |

## F947 离线化声明

全部验收以 fixtures 断言 + lint + tmp_path 构造表达；零 `shenbi-dispatch`/`pipeline resume` 调用；backfill 对真实项目仅 `--dry-run` 取证。

## G3.4 声明

本 plan 无 LLM 产物评分场景（全离线结构性验证）——无需独立评分子 agent。

## Self-Review 记录

- plan 审查 R2（1C/3I/8M）修正已并入：C1 seam 三站点勘误（pipeline/cli.py:_commit_staging_for_checkpoint 为 review-path 第三站点，dispatcher/cli.py 无 staging）/I2 chapter 默认 None/I3 ss.identity_row_match 入 map（七键）/I4 计数器语义+激活规则（ch17 假红消解）；M5-M12 逐项
- plan 审查 R1（3C/5I/8M）修正已并入：C1 settle commit 接线（T8）/C2 safe_write 原子写（T2）/C3 per-chapter 前置态绿种子（T13）；I4 v3 内可选钉死/I5 动词表双路径单表（T5）/I6 identity 对账（T8）/I7 空种子吸收洞（T5）/I8 chapter 参数（T6/T3）；M9-M16 逐项（ch08 fixture 接线/四元组/event 类型定义/四枚举注册/名归一/注释精度/__init__.py/T12 缩窄声明）
- 覆盖：spec §1.1（T1/T2/T3/T8）§1.2（T1）§1.3（T13）§1.4（T2/T3/T8/T9/T12 全清单逐项）§2（T10/T12）§3（T11）§4 F15（T6）/F16（T4/T5/T8）/F17（T7）§5=P2 §6 P1 各句（验收表）§7 条 1-3（表）——无缺口
- 占位符：无 TBD/「适当处理」；memo 豁免闪回简化形态（整章豁免）在 T6 明示为 P1 形态——段级精化留 P2 非占位
- 类型一致：`check_prop_handoffs(text, memo_text, props)` T5/T11 一致；`FactsFile.facts` dict 值多态 T1/T2 一致；消息前缀 T4-T8 与 G4_CHECK_MAP T8 注册逐一对应（`XC.narration_name:`/`cp.prop_decl:`/`cd.prop_handoff:`/`cd.counter:`/`ss.facts_ops:`/`ss.prop_row_match:`）
