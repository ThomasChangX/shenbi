# 契约一致性基础设施 (Contract Consistency Infrastructure)

- **状态**: Draft (pending user review)
- **日期**: 2026-07-08
- **范围**: 根因机制层 —— 路径解析统一 / 契约图闭环 / Schema 单一源 / 字段匹配单一化
- **优先级原则**: 质量 > 可维护性 > 开发成本
- **前提**: 项目处于验证阶段,无历史包袱 → 采用 schema-first 立即切换,不留过渡态

---

## 1. 背景与动机

系统运行中频繁出现 pipeline 与 skill 之间的文件路径错配、读写不一致,导致整个流程出错。对 `src/shenbi/` 全量审计(4 个探索 agent,gates / dispatcher+pipeline / contracts+scoring+cli / 跨模块上下文依赖)发现问题的广度远超最初的 7 缺口诊断。

### 1.1 审计发现的一致性问题(8 大类)

| 类 | 根因 | 严重度 |
|---|---|---|
| 1. 章节占位符解析 | 3 套分叉实现,其中 `executor.py:75` 用无界 `str.replace("N")`,腐蚀任何含字母 N 的路径(`resonance`→`reso5a5ce`) | 高 |
| 2. 根目录解析 | `round_dir`/`project_dir`/`PROJECT`/CWD 四套根;G4 的 `resolve_g4_base` 静默 fallback 到 CWD;`.bak` 用裸字符串 fp | 高 |
| 3. 契约图闭包 | 无"每个 read 必须有 producer"的闭包检查;pipeline 直接写的文件不在 skill 契约图内 | 高 |
| 4. Schema 校验 | decisions.json 三处手写副本;truth-files.yaml 两处读不同子集;deps.json 四处裸 `.get()` | 高 |
| 5. 字段过滤 | 三套匹配语义(filter/G1 精确、lint normalize);逃生舱静默退化;fields_map 查键逻辑不同 | 中 |
| 6. gate↔gate 隐式契约 | `.bak` 三处裸 fp;BACKUP_SKILLS 硬编码漏列 5 个 truth-updating skill;PhaseState 枚举 vs 裸字面量 | 高 |
| 7. gate 入口分叉 | 三套入口(`validate-gate.py`/`python -m`/`uv run`),validate-gate.py 未 hash 锁定 | 中 |
| 8. 已确认活 bug | D16(G6.10 死路径)、D19(G3.1 死键)、D20(pipeline 产物路径分叉)、D21-D22-D24 | 高 |

### 1.2 本 spec 的边界(分解策略)

本 spec 聚焦**根因机制层**(类 1-5 的基础设施)。gate 内部契约治理、入口统一、活 bug 修复作为**后续独立 spec**,各自有明确边界:

- **本 spec(契约一致性基础设施)**:单一解析器 + RoundPaths(三根)+ 契约图闭环(含 Producer Registry)+ Schema 单一源(全结构化文件 pydantic)+ 字段匹配单一化
- **spec 2(gate↔gate 契约治理)**:`.bak` 统一、BACKUP_SKILLS 派生、PhaseState 单向引用、marker coverage
- **spec 3(gate 入口统一)**:单一入口 + hash 锁定
- **spec 4(活 bug 修复)**:D16/D19/D20/D21/D22/D24 修复 + 回归测试

**分解理由**:类 6-8 是 gate 内部治理,与类 1-5 的路径/契约/schema 机制正交。混入一份 spec 会模糊焦点、增大回滚粒度。

---

## 2. 目标与非目标

### 2.1 目标 —— 五大根因机制

1. **单一占位符解析**:消灭 3 套分叉的章节占位符替换与章节提取;含 N 路径不被腐蚀。
2. **RoundPaths 三根封装**:`round_dir` + `project_dir` + `repo_root`;所有路径解析的唯一出口;消除 CWD fallback 和裸字符串 join。
3. **契约图闭环 + Producer Registry**:每个 read 必须有 producer(skill / pipeline / external);pipeline 产物登记;ORPHAN_READ 静态 FAIL。
4. **Schema 单一源**:所有多处消费的结构化文件(decisions / deps / novel / progress / summary / scores / registry)都有 pydantic 模型;一处定义,所有消费方 import;`extra: forbid`。
5. **字段匹配单一化**:`match_field` 单函数;filter / G1 / lint 统一调用;逃生舱语义集中。
6. **现存活 bug 切除**:审计确认的 D16/D19/D20/D21/D22/D24 —— 它们是上述五类机制主题的现存实例(路径错配/契约不一致/schema 缺失/字段问题),本 spec 一并根治,不遗留。

### 2.2 非目标(明确排除)

- gate↔gate 隐式契约治理(`.bak` BACKUP_SKILLS 派生、PhaseState 单向引用、marker coverage)→ spec 2
  - **例外**:`.bak` 的**路径构造**走 RoundPaths(属本 spec 路径统一范围);BACKUP_SKILLS **列表派生**留 spec 2
- gate 入口三套分叉统一 → spec 2
- `chapter_loop.py` 硬编码步骤顺序(执行序是独立关注点)
- `legacy.py:_validate` contract 块校验重写(它工作良好,非任何缺口根源)
- DAG 生成器本身(`sync_contracts.build_dag` 已正确)

### 2.3 成功标准

- 故意写错 read 路径 → CI 在 PR 阶段 FAIL 并精确报 `ORPHAN_READ: skill=X reads=foo-bar.md no producer`。
- 任何含 N 的路径(如 `NPC-list.md`、`rules-N-bound.md`)解析不被腐蚀。
- `round_dir ≠ project_dir ≠ repo_root` 三根分离 fixture 下,G4 / gate / dispatcher 行为正确。
- pipeline 写的文件(如 `context/chapter-N-context.md`)被闭包校验正确识别为有 producer,不误报孤儿。
- 所有 pydantic 模型 `extra: forbid`;任一结构化文件带拼写错误字段 → 加载失败。
- 字段标题漂移 → CI FAIL,且 filter / G1 / lint 对同一输入产生一致结果。

---

## 3. 架构:三层校验栈

```
┌─────────────────────────────────────────────┐
│  Layer C: CI/Authoring (静态, FAIL)         │
│  ├─ lint_contract_graph.py   (闭包 + Producer Registry) │
│  ├─ lint_contract_fields.py  (字段, 用 match_field)     │
│  └─ schema_compat_check      (版本兼容)                │
├─────────────────────────────────────────────┤
│  Layer B: Schema 单一源 (pydantic)          │
│  ├─ decisions / registry / deps / novel ... │
│  └─ 所有消费方 import 模型,g2/g4/lint 共用    │
├─────────────────────────────────────────────┤
│  Layer A: 运行期统一                         │
│  ├─ contracts/paths.py 单一解析器 + extract   │
│  ├─ paths.py RoundPaths (三根)               │
│  ├─ contracts/fields.py match_field 单函数    │
│  └─ G5.2 glob-aware WARN                     │
└─────────────────────────────────────────────┘
```

每层可独立测试、独立演进。schema 是底座,运行期统一在中间,CI 校验在顶层。修一类问题只动一层。

---

## 4. Layer A:运行期统一

### 4.1 单一占位符解析 + 章节提取

**现状(3 套分叉)**:
- `dispatcher/executor.py:66` `_resolve_chapter_path`:无界 `path.replace("NNN",...).replace("N", str(chapter))`,缺章返哨兵 `""`。
- `pipeline/dispatch_helper.py:104` `_resolve_path`:有界正则 `(?<=[-/])N(?=[-./]|$)`,缺章直传。
- `pipeline/chapter_loop.py:332` `_substitute_chapter`:有界正则,chapter 必填。
- 另:`executor.py:63` `_extract_chapter` 用 `\bchapter\s+(\d+)\b`(词边界);`dispatch_helper.py:100` 用 `chapter\s+(\d+)`(无词边界)——`subchapter 5` 一个返 None 一个返 5。

**设计**:新建 `src/shenbi/contracts/paths.py`,提供两个唯一函数:

```python
# src/shenbi/contracts/paths.py

class UnresolvedPathError(ValueError):
    """路径含章节占位符但无章节上下文。"""

def resolve_chapter_path(path: str, chapter: int | None) -> str:
    """单一次占位符替换。合并两份旧实现的最严语义。

    规则:
    - chapter is None 且路径含 NNN/N → 抛 UnresolvedPathError
    - 替换顺序:先 NNN(3位补零),再 N(有界正则,防误伤)
    - 有界正则:(?<=[-/])N(?=[-./]|$) —— 防止腐蚀 VolumeN、resonance 等
    """
    if chapter is None:
        if "NNN" in path or re.search(r"(?<=[-/])N(?=[-./]|$)", path):
            raise UnresolvedPathError(path)
        return path
    result = path.replace("NNN", f"{chapter:03d}")
    return re.sub(r"(?<=[-/])N(?=[-./]|$)", str(chapter), result)

def extract_chapter(text: str) -> int | None:
    """单一次章节提取。统一用词边界正则。"""
    m = re.search(r"\bchapter\s+(\d+)\b", text, re.IGNORECASE)
    return int(m.group(1)) if m else None
```

`executor.py`、`dispatch_helper.py`、`chapter_loop.py` 删除各自的 `_resolve_*` / `_substitute_chapter` / `_extract_chapter`,改为 `from shenbi.contracts.paths import resolve_chapter_path, extract_chapter`。

**为什么"抛异常"而非旧 executor 的哨兵**:空哨兵把错误吞成"文件不存在",下游 G1.1 报"input not found"而非"路径未解析"——这正是当前路径错配难以诊断的原因。抛异常让根因直接暴露。调用方(dispatcher)捕获后决定:genesis 阶段无章节属正常,跳过该路径;chapter 阶段抛异常 = 真正的 bug。

### 4.2 RoundPaths 三根封装

**现状根因**:`round_dir` / `project_dir` / `PROJECT`(repo 根) 三套根散落使用;G4 的 `resolve_g4_base` 用 `rd if rd else Path.cwd()`(静默 CWD fallback);10 个 G4 checker 硬编码 `pd/"world/..."` 忽略传入的 fps;codex.py:58 的 rubric_path 是唯一 CWD 相对路径;`.bak` 三处用裸 `Path(str(fp)+".bak")`。

**设计**:新建 `src/shenbi/paths.py` 的 `RoundPaths` 值对象,封装三根关系:

```python
# src/shenbi/paths.py
from dataclasses import dataclass
from pathlib import Path
from shenbi.contracts.paths import resolve_chapter_path

@dataclass(frozen=True)
class RoundPaths:
    """一次 dispatch/run 中所有路径解析的唯一出口。frozen 防误改。"""
    round_dir: Path    # 本轮工作区(产物、markers、state)
    project_dir: Path  # 小说项目根(novel.json, world/, chapters/, truth/)
    repo_root: Path    # 仓库根(SKILL.md, fixtures, rubric, validate-gate.py)

    def read(self, rel: str, chapter: int | None = None) -> Path:
        """reads 可来自 round_dir(本轮中间产物)或 project_dir(持久库)。
        优先 round_dir, fallback project_dir —— 明确这个优先级,消灭隐式分歧。"""
        resolved = resolve_chapter_path(rel, chapter)
        rd = self.round_dir / resolved
        if rd.exists():
            return rd.resolve()
        return (self.project_dir / resolved).resolve()

    def write(self, rel: str, chapter: int | None = None) -> Path:
        """writes 总在 round_dir(本轮产物区)。"""
        resolved = resolve_chapter_path(rel, chapter)
        return (self.round_dir / resolved).resolve()

    def repo(self, rel: str) -> Path:
        """repo 资源(只读):SKILL.md, fixtures, rubric。"""
        return (self.repo_root / rel).resolve()

    def backup(self, rel: str, chapter: int | None = None) -> Path:
        """G2.11 的 .bak 必须与被 diff 的文件同根。"""
        return self.write(rel, chapter).with_name(self.write(rel, chapter).name + ".bak")
```

**范围扩展(关键)**:以下位点全部改走 RoundPaths:
- `dispatcher/executor.py`:`derive_input_files`/`derive_output_files` 用 `rp.read()`/`rp.write()`。
- `pipeline/dispatch_helper.py`:读循环用 `rp.read()`;`_PROJECT_ROOT` 换成 `rp.repo()`。
- `gates/g1.py`、`g2.py`、`g4/`(全部 10 个硬编码 checker)、`g5.py`:路径构造改用 RoundPaths。
- **消除 `resolve_g4_base` 的 CWD fallback**:无 round_dir 时报错(`ValueError`),不再静默用 CWD。
- **G4 硬编码 checker 改造**:`worldbuilding.py`/`story_architecture.py`/`relationship_map.py`/`plot_thread_weaver.py`/`power_system.py`/`volume_outlining.py`/`foreshadowing_track.py`/`faction_builder.py`/`location_builder.py`/`pacing_design.py` 的 `pd = resolve_g4_base(rd); pd/"world/..."` 改为 `rp.read("world/...")`。
- **codex.py:58 rubric_path**:从 `Path(os.environ.get("RUBRIC", f"tests/tiers/..."))`(CWD 相对)改为 `Path(os.environ.get("RUBRIC", str(rp.repo(f"tests/tiers/t1-skill/{skill}/rubric.md"))))`。保留 `RUBRIC` 环境变量覆盖能力(测试/调试用),但默认值走 `rp.repo()` 而非 CWD 相对字符串。
- **`.bak` 三处**(g1.py:179, g2.py:242, style_polishing.py:35):改用 `rp.backup()`,消除裸 `Path(str(fp)+".bak")` 与 style_polishing 内部不一致(.bak 在 CWD、内容在 base)。

**为什么 read 优先 round_dir**:round_dir 是本轮工作区,可能含上游 skill 刚产出的中间文件;project_dir 是持久库(truth/style/outline)。本轮产物应优先,否则读到上一轮陈旧中间文件。这个优先级当前是隐式且不一致的,本设计显式化。

### 4.3 G5.2 glob-aware WARN

**现状**:`g5.py:78` 裸 `set` 差集,字面匹配,只查相邻前置。

**设计**:
- 匹配逻辑改用 `dag_key`(从 `sync_contracts.py` 提取到 `contracts/graph.py`),让 `chapters/chapter-N.md` 与 `chapters/chapter-5.md` 正确关联。
- 保持 WARN(不 FAIL),与既定失败语义策略一致。
- **不改"只查相邻"为"全图"**——全图闭包校验放在 Layer C 静态做;运行期 G5.2 保持轻量,只对当前 phase 的相邻链做即时 WARN。

**为什么运行期不全图**:全图校验是 O(skills²),每次 dispatch 跑一遍成本高且重复(契约是静态的)。静态期跑一次足矣;运行期只补"相邻链即时反馈"的增量价值。

### 4.4 共享模块清单(Layer A 产出)

| 文件 | 内容 |
|---|---|
| `src/shenbi/contracts/paths.py` | `resolve_chapter_path` + `extract_chapter` + `UnresolvedPathError` |
| `src/shenbi/paths.py` | `RoundPaths`(三根) |
| `src/shenbi/contracts/fields.py` | `match_field` + `filter_to_fields`(从 dispatch_helper 抽出) |
| `src/shenbi/contracts/graph.py` | `dag_key`(从 sync_contracts 抽出,供 G5.2/lint 共用) |

---

## 5. Layer B:Schema 单一源

### 5.1 设计原则:Schema-First 立即切换

为**所有多处消费的结构化文件**建 pydantic v2 模型,集中在 `src/shenbi/contracts/schemas/`。每个模型定义后,所有消费方立即 `import` 并 `model_validate`,删除手写 `.get()` 校验。不留两套逻辑并存的过渡态(项目无历史包袱,验证期容错)。

所有模型 `model_config = {"extra": "forbid"}`——拒绝未知键,让拼写错误当场暴露。

### 5.2 模型清单

| 模型 | 文件 | 当前校验位点(重复) | 消除 |
|---|---|---|---|
| `DecisionsDoc` | decisions.json | g2.py:92(硬编码字面量)、g4/decisions_validator.py:53、g4/_decisions_schema.py | 3→1 |
| `TruthFilesRegistry` | truth-files.yaml | legacy.py:77(读 concepts+globs+patterns)、registry.py:30(只读 concepts) | 2→1,加结构校验 |
| `DepsDoc` | deps.json | sync_contracts.py:236、scoring.py:206、phase_runner.py:33、g0.py:91 | 4→1 |
| `NovelConfig` | novel.json | pipeline/cli.py:141,165 | 2→1 |
| `ProgressDoc` | progress.json | G3/G_DISPATCH/G_TRANSITION 多处 `.get()` | 0→1(从无到有) |
| `SummaryDoc` | summary.json | G5.1/G7.1/G7.16 | 0→1 |
| `ScoreReport` | scores.json | scoring.py:405、G7.14/G7.15 | 2→1 |

### 5.3 关键模型示例

```python
# src/shenbi/contracts/schemas/decisions.py
from pydantic import BaseModel, Field, field_validator, model_validator

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"

class Selection(BaseModel):
    model_config = {"extra": "forbid"}
    basis: str
    severity: str = "low"
    rationale: str | None = None
    # ... 其他字段

    @model_validator(mode="after")
    def validate_p25_rationale(self):
        # P2.5: routine+low → rationale FORBIDDEN
        #       manual_override 或 high → rationale REQUIRED
        #       rationale ≤ 100 chars
        ...
        return self

class DecisionsDoc(BaseModel):
    model_config = {"extra": "forbid"}
    schema_: str = Field(alias="$schema")
    skill: str
    chapter: int | str
    selections: list[Selection] = []
    adjustments: list[Adjustment] = []
    budget: dict | None = None
    produced_at: str

    @field_validator("schema_")
    @classmethod
    def check_version(cls, v):
        if v != DECISIONS_SCHEMA_VERSION: raise ValueError(...)
        return v
```

```python
# src/shenbi/contracts/schemas/registry.py
class RegistryConcept(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    kind: Literal["truth", "decisions", "artifact", "report", "config", "short"]
    producer: Literal["skill", "pipeline", "external"] = "skill"  # ← Producer Registry
    glob: str | None = None

class TruthFilesRegistry(BaseModel):
    model_config = {"extra": "forbid"}
    version: int = 1  # ← 版本字段,默认 1,新版拒绝
    concepts: list[RegistryConcept]

    @field_validator("version")
    def check_supported(cls, v):
        if v != 1: raise ValueError(f"unsupported registry version {v}, expected 1")
        return v
```

### 5.4 错误信息映射

pydantic 的 `ValidationError` 需映射到 gate 的 micro-failure 格式(`{id, file, s, r}`)。一个适配函数 `pydantic_err_to_gate_failures(err, file_path, gate_id_prefix)` 统一转换,g2/g4 共用。

### 5.5 版本化策略

- `truth-files.yaml` 的 `version: 1` 当前形态;向前兼容(加字段)不 bump;破坏性(删字段/改语义)bump 到 2,`check_supported` 拒绝旧版,CI 报住所有未迁移的 consumer。
- decisions.json 的 `$schema: shenbi-decisions-v1` 同理。

### 5.6 死代码清理

审计发现 `contracts/registry.py` 的 `REGISTRY` 和 `load_skill_contract()` 零生产调用,`contracts/skills/*.py` 约 50 个最小 stub(dead code,仅 genre_config/pacing_design 实际使用)。本次 schema 化时清理这些死代码,避免新增模型时混淆"哪个是活的"。

---

## 6. Layer C:CI 静态校验

### 6.1 契约图闭包校验 + Producer Registry

**现状**:`dependency-dag.json` 已生成(glob-aware),但无消费者做闭包检查;pipeline 直接写的文件不在 skill 契约图。

**设计**:

(a) **Producer Registry**:`truth-files.yaml` 每个概念加 `producer` 字段:
- `producer: skill` —— 由 skill 的 writes/updates 生产(默认)
- `producer: pipeline` —— 由 pipeline 代码生产(如 `context_assemble.write_context_file` 写 `context/chapter-N-context.md`、`_snapshot_chapter_files` 写 snapshots、`_save_manifest` 写 `snapshots/manifest.json`)
- `producer: external` —— seed 文件(novel.json、era-reference.md、import/source/*、source_canon/*、benchmarks/anchors/)

pipeline 产物必须在 registry 显式登记 `producer: pipeline`,否则闭包校验会把它们的消费者误报为孤儿 read。

(b) **闭包检查**:新建 `tools/lint_contract_graph.py`:

```python
def find_closure_violations(contracts, registry):
    """闭包检查:每个 read 必须有 producer 或为 external。"""
    producers = {}  # dag_key(file) -> set(skill)
    for skill, c in contracts.items():
        for f in [*c["writes"], *c["updates"]]:
            producers.setdefault(dag_key(f, registry), set()).add(skill)

    external = {c.name for c in registry.concepts if c.producer == "external"}
    # pipeline 产物也算合法 producer
    pipeline_produced = {c.name for c in registry.concepts if c.producer == "pipeline"}

    orphan_reads = []      # FAIL
    dangling_writes = []   # WARN

    for skill, c in contracts.items():
        for f in c["reads"]:
            key = dag_key(f, registry)
            if key in external or key in pipeline_produced:
                continue
            if key not in producers:
                orphan_reads.append((skill, f))

    for producer_skill, keys in producers.items():
        for key in keys:
            if no_consumer(key, contracts, registry) and key not in external:
                dangling_writes.append(...)

    return orphan_reads, dangling_writes
```

**失败语义**:
- `ORPHAN_READ` → **FAIL**(exit 1,挡 PR)。抓 `foo.md` vs `foo-bar.md` 错配。
- `DANGLING_WRITE` → **WARN**(stderr,不挡 PR)。无人读的产物可能是新功能或废弃,不硬拦。

**为什么复用 `dag_key`**:保证"静态闭包检查"与"DAG 生成"用同一套匹配语义,不会出现"DAG 有边但闭包报孤儿"的矛盾。`dag_key` 从 `sync_contracts.py` 提取到共享的 `contracts/graph.py`。

**DAG 不直接读**:`dependency-dag.json` 是生成产物可能滞后;闭包检查实时从 contracts + registry 构建 producer 映射。

### 6.2 字段过滤单一化

**现状**:`_extract_h2_sections`(精确)、`check_fields_exist`(精确但非阻塞 WARN)、`lint_contract_fields.py`(normalize,宽松)——三套语义。

**设计**:
- 新建 `src/shenbi/contracts/fields.py:match_field(declared, heading)`,单一匹配函数(精确 `.strip()`,不做 normalize——与运行期 filter 一致)。
- `_filter_to_fields` 从 `dispatch_helper.py` 抽到 `contracts/fields.py`,filter / G1 / lint 全部调用 `match_field` + `filter_to_fields`。
- lint 升级为 fixture-driven FAIL:拿 producer 的真实最新 fixture 输出跑 `filter_to_fields`,断言每个声明字段命中(非逃生舱 fallback)。
- 逃生舱(命中 0)语义集中定义:运行期(`filter_to_fields` 在 dispatch 时调用)WARN + 返回全文,不中断 dispatch;CI(`lint_contract_fields.py` 对 fixture 调用)FAIL。两者调用同一个 `filter_to_fields`/`match_field`,只是调用方对"命中 0"的反应不同——filter 函数本身返回 `(filtered_text, matched: bool)`,由调用方决定 WARN 还是 FAIL。

### 6.3 版本兼容性校验

在 `just lint-contracts` 里:
- `truth-files.yaml` 的 `version` 经 `TruthFilesRegistry` 模型校验。
- decisions schema 版本:producer 写出的 `$schema` 版本 ≤ 所有 consumer 期望。

### 6.4 聚合入口

```makefile
# justfile
lint-contracts:
    uv run python tools/lint_contract_graph.py
    uv run python scripts/lint_contract_fields.py  # 升级版,用 match_field
    uv run python tools/lint_contracts.py           # 现有,保留

check: ruff mypy basedpyright pytest lint-contracts  # lint-contracts 接入 just check
```

CI(`.github/workflows/ci.yml`)里 `just check` 自动包含新目标。PR 触碰 `skills/`、`docs/framework/truth-files.yaml`、任何 `*-decisions.json` 时这些 lint 必跑。

---

## 7. 实施顺序(4 阶段)

```
阶段 0:基线快照(摸清违规规模)
  └→ 阶段 1:底座建立(Layer A + B 共享模块:schemas 模型 + paths/fields/RoundPaths)
      schema-first 立即切换,所有消费方 import 模型,删除手写校验
      └→ 阶段 2:运行期统一(所有 gate/dispatcher/pipeline 改用 RoundPaths + 单一解析器)
          └→ 阶段 3:静态校验(lint_contract_graph + match_field + Producer Registry 登记)
              └→ 阶段 4:历史债清零(全量违规修复 + 金丝雀测试)
```

### 7.1 阶段 0 — 基线快照(前置调查)

在写实施 plan 前先跑探查,产出违规清单作为后续阶段输入:
- 扫所有 SKILL.md 的 reads/writes,统计孤儿 read。
- 扫 truth-files.yaml,找 external seed、过宽 glob、需登记的 pipeline 产物。
- 扫所有结构化文件(decisions/deps/novel 等),找 extra:forbid 会暴露的多余字段。
- 比对 3 套解析器在所有真实路径上的输出差异,确认含 N 路径腐蚀的真实 case。
- **逐项复现并固化** D16/D19/D20/D21/D22/D24 六个活 bug(见 §7.5 处理协议),每个写一个能稳定复现"修复前错误行为"的测试,作为修复验证基准。

### 7.2 阶段 1 — 底座建立

**产出**:
- `src/shenbi/contracts/schemas/{decisions,registry,deps,novel,progress,summary,scores}.py`
- `src/shenbi/contracts/paths.py`(`resolve_chapter_path` + `extract_chapter`)
- `src/shenbi/paths.py`(`RoundPaths`)
- `src/shenbi/contracts/fields.py`(`match_field` + `filter_to_fields`)
- `src/shenbi/contracts/graph.py`(`dag_key`)

**改动(schema-first 立即切换)**:
- `legacy.load_registry()` 返回 `TruthFilesRegistry` 模型实例;`resolves()` 访问模型属性。
- g2/g4 的 decisions 校验:删除手写,改 `DecisionsDoc.model_validate`。
- deps.json 4 处、novel.json 2 处、progress/summary/scores 各处:改 import 对应模型。
- 清理 `contracts/registry.py` 的 dead `REGISTRY`/`load_skill_contract`、`contracts/skills/*.py` 的 dead stub(仅保留 genre_config/pacing_design)。

**验证**:模型单测;`load_registry()` 返回类型变但行为等价;现有 gate 测试全绿。

### 7.3 阶段 2 — 运行期统一

**产出**:dispatcher / pipeline / 所有 gate 改用 RoundPaths + 单一解析器。

**改动(本 spec 最大改动面)**:
- `dispatcher/executor.py`:删 `_resolve_chapter_path`/`_extract_chapter`;`derive_*` 用 RoundPaths。
- `pipeline/dispatch_helper.py`:删 `_resolve_path`/`_filter_to_fields`;读循环用 RoundPaths;`_PROJECT_ROOT` 换 `rp.repo()`。
- `pipeline/chapter_loop.py`:删 `_substitute_chapter`;改用共享函数。
- `gates/g1.py`/`g2.py`/`g5.py`:路径构造用 RoundPaths;`.bak` 用 `rp.backup()`;修 g1.py:65 docstring 漂移。
- `gates/g4/` 全部 checker(含 10 个硬编码):改用 RoundPaths;删 `resolve_g4_base` 的 CWD fallback。
- `gates/g4/style_polishing.py`:`.bak` 用 `rp.backup()`,消除内部不一致。
- `dispatcher/modes/codex.py`:rubric_path 走 `rp.repo()`。
- `g5.py:78`:G5.2 改用 `dag_key`。

**验证**:
- RoundPaths / paths / fields / graph 单测。
- **关键回归测试**:固定一组真实 skill 路径,断言新旧解析器输出一致(除已知分叉 case)。
- T1/T2/T3 全套跑通。
- 三根分离 fixture(round_dir≠project_dir≠repo_root)下 G4/gate/dispatcher 行为正确;G2.11 `.bak` diff 不再跨根 no-op。

**风险缓解**:一个 gate/模块一个 commit,每 commit 跑 `just check`,红灯立即定位。

### 7.4 阶段 3 — 静态校验

**产出**:
- `tools/lint_contract_graph.py`(闭包 FAIL + dangling WARN)
- 升级 `scripts/lint_contract_fields.py`(fixture-driven,用 match_field,FAIL)
- `truth-files.yaml` 登记 `producer` 字段(skill/pipeline/external);pipeline 产物显式登记。
- justfile `lint-contracts` 接入 `just check`。

**验证**:
- 故意写错 read 路径的测试 skill → lint 报 `ORPHAN_READ` 并 exit 1。
- 标题漂移 fixture → 字段校验 FAIL。
- pipeline 产物(`producer: pipeline`)不误报孤儿。

### 7.5 阶段 4 — 历史债清零

**输入**:阶段 0 违规清单 + 阶段 3 工具实跑结果(交叉验证)。

**处理协议(每类违规)**:
- **ORPHAN_READ**:
  - 拼写错误 → 修正 read 对齐 producer write。
  - producer 漏写 → 给 producer 补 write 声明。
  - 合理 seed → truth-files.yaml 标 `producer: external`。
  - pipeline 产物 → truth-files.yaml 标 `producer: pipeline`。
  - **禁止**:为消警告删 read 或加假 producer。每项修复说明类别。
- **字段漂移**:truth 标题改了 → 更新 consumer fields;consumer fields 拼错 → 修正。
- **结构化文件多余字段**(extra:forbid):合法未登记 → 加模型字段;非法/历史遗留 → 删除。
- **过宽 glob**:收窄为具体 pattern 或登记 known_files。

**处理协议(每类违规)**:
- **ORPHAN_READ**:
  - 拼写错误 → 修正 read 对齐 producer write。
  - producer 漏写 → 给 producer 补 write 声明。
  - 合理 seed → truth-files.yaml 标 `producer: external`。
  - pipeline 产物 → truth-files.yaml 标 `producer: pipeline`。
  - **禁止**:为消警告删 read 或加假 producer。每项修复说明类别。
- **字段漂移**:truth 标题改了 → 更新 consumer fields;consumer fields 拼错 → 修正。
- **结构化文件多余字段**(extra:forbid):合法未登记 → 加模型字段;非法/历史遗留 → 删除。
- **过宽 glob**:收窄为具体 pattern 或登记 known_files。
- **已确认活 bug**(审计确认的 6 个,逐项切除 + 金丝雀测试):
  - **D16**(G6.10 死路径):`g6.py:275` 读 `pd/"config"/"style_profile.md"`,producer 写 `style/style_profile.md` → 修正为 `rp.read("style/style_profile.md")`(走 RoundPaths,§4.2 改造后自动正确路径)。**金丝雀**:断言 G6.10 在有 style_profile 时不再 SKIP。
  - **D19**(G3.1 死键):`g3.py:85` `deps.get(skill_name)` 但 deps.json 无顶层 skill 键 → 修正为先查 `deps["t2-phases"]` 找含该 skill 的 phase,取该 phase 的 prerequisites;或若 T1 prerequisite 确实需要 per-skill,在 `DepsDoc` 模型(§5.2)里定义正确结构后让 G3.1 查对位置。**金丝雀**:断言 G3.1 对有前置依赖的 skill 不再返回空 prereqs。
  - **D20**(pipeline 产物路径分叉):`snapshots/chapter-NNN/` 契约概念 vs pipeline 写 `snapshots/chapter-{N:03d}-{ts}.md` 平文件 → 在 truth-files.yaml 登记真实 pipeline 产物(`producer: pipeline`),让契约图反映现实而非虚构。**金丝雀**:断言 pipeline 产物的 consumer 不被报孤儿。
  - **D21**(truth 模板缺 H2):`_init_truth_templates` 只种 H1,skill 期望 H2 字段 → 从 consumer 声明的 fields 派生 H2 骨架写入模板。**金丝雀**:断言 genesis 首跑时 G1 `check_fields_exist` 对模板文件不 WARN。
  - **D22**(hook state 大小写):G6.7 不敏感,`_count_triggered_hooks` 仅大写 → 用 `match_field` 同款的集中匹配,或定义 `HookState` 枚举(enum 值 `TRIGGERED`),所有读写引用枚举值。**金丝雀**:断言小写 `triggered` 也被正确识别。
  - **D24**(registry 无非空断言):`bootstrap_registry` 结构漂移会清空 → `TruthFilesRegistry` 模型(§5.2)加载后断言 `len(concepts) > 0`,加 lint 检查非空。**金丝雀**:断言空 registry 加载失败。

**验证**:阶段 3 所有 lint 跑出零 FAIL;D16/D19/D20/D21/D22/D24 六个活 bug 的复现测试在修复后转 PASS(从 FAIL/错误行为翻转为正确行为)。DANGLING_WRITE 的 WARN 记录到文档但不阻塞。

---

## 8. 测试策略

### 8.1 测试分层映射

| 层级 | 测什么 | 新增测试 |
|---|---|---|
| 单元(B/A 共享模块) | pydantic 模型、paths、RoundPaths、match_field、dag_key | 模型序列化/校验、解析器边界、三根优先级、字段命中/逃生舱 |
| 单元(C1 闭包) | 闭包逻辑 | ORPHAN_READ FAIL、DANGLING_WRITE WARN、external/pipeline 放行、glob-aware |
| 集成(Layer A) | gate 改造后行为不变 | g1/g2/g4/g5 用 RoundPaths + 新解析器,T1 fixture 全绿 |
| 集成(Layer B) | g2/g4 切换后校验等价 | 同一 decisions.json 新旧校验结果一致(除 forbid 新增暴露) |
| T2 阶段链 | 相邻 skill 真实读写交接 | G5.2 glob-aware WARN 在真实链触发正确 |
| T3 端到端 | 全管线无路径错配 | 完整 chapter loop 跑通,无 "input not found" 类失败 |

### 8.2 金丝雀回归测试(防错配回潮)

1. **错配注入**:测试 fixtures 放一个故意写错 read 路径的 skill,断言 `lint-contracts` FAIL 并报 `ORPHAN_READ: skill=X reads=foo-bar.md no producer`。整个 spec 的防回归哨兵。
2. **含 N 路径不腐蚀**:`NPC-list.md`、`rules-N-bound.md`、`anti-N` 等路径,断言 `resolve_chapter_path` 不腐蚀。防有人重新引入无界 replace。
3. **三根分离**:round_dir≠project_dir≠repo_root 的 fixture,断言 G4/gate/dispatcher 行为正确,G2.11 `.bak` diff 不跨根 no-op。
4. **字段匹配一致性**:对每个有 dict-form reads 的 consumer,拿 producer 真实 fixture 跑 `filter_to_fields`,断言 filter/G1/lint 三处结果一致(用同一 match_field)。
5. **D16 G6.10 不再死路径**:有 style_profile 时 G6.10 执行实际检查而非 SKIP。防止有人改回 `config/` 路径。
6. **D19 G3.1 不再死键**:对有前置依赖的 skill,G3.1 返回非空 prereqs 并实际校验。防止 deps 键结构再次错配。

### 8.3 测试数据原则

延续 G0.9:所有 fixture 是真实 skill 输出。新增"错配注入"测试用独立测试 skill(如 `tests/fixtures/synthetic-skill/`),不污染真实 skill 集。

---

## 9. 行业最佳实践对照

| 机制 | 行业对照 | 本设计 |
|---|---|---|
| 单一占位符解析 | Pact matching provider / Helm tpl / Jinja 单一环境 | ✅ 单一 `resolve_chapter_path` + `extract_chapter` |
| RoundPaths 值对象 | Rust PathBuf+工作目录封装 / Go fs.FS / Next.js 项目根探测 | ✅ 三根封装,禁裸 join,消除 CWD fallback |
| 契约图闭包 + Producer Registry | Consumer-Driven Contract Testing (Pact broker) / Conflux Schema Registry ownership / Terraform dependency graph | ✅ 闭包 FAIL + pipeline 产物统一登记 |
| Schema-First | protobuf/gRPC / OpenAPI / Avro | ✅ 全结构化文件 pydantic 化,一处定义 |
| 字段匹配单一化 | @typescript-eslint exhaustive 检查 / Pact consumer expectation | ✅ `match_field` 单函数,filter/G1/lint 共用 |

---

## 10. 后续 spec(明确边界)

本 spec 建立的 RoundPaths / schemas / match_field / dag_key 共享模块是后续 spec 的基础。按"严格逐个 spec"节奏(本 spec 走完 plan→实施→验证后,基于真实反馈再设计下一个):

- **spec 2(gate↔gate 契约治理 + 入口统一)**:基于 RoundPaths 统一 `.bak`;BACKUP_SKILLS 从契约派生(消灭硬编码漏列);PhaseState 单向引用;marker coverage;gate 三套入口(`validate-gate.py`/`python -m`/`uv run`)收敛为单一入口 + hash 锁定。合并为一个 spec 是因为入口统一与 gate↔gate 治理都属"gate 内部一致性"主题。
  - 本 spec 已切除的 D16/D19/D20/D21/D22/D24 不在此 spec 范围。
