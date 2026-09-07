# C34 路径/布局契约统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec #48（docs/superpowers/specs/2026-08-16-c34-path-layout-contract-design.md）：布局探测单源 + gate 路径解析收口 + 观测面同根 + G1.4 .bak 契约裁决。

**Architecture:** `Layout.detect()` 落在 `src/shenbi/paths.py`（与 RoundPaths 同家，禁立第三权威）；checker 相对解析统一走 `resolve_input_path`（gates/shared.py）；drift/audit 写观测锚定 project_dir；G1.4 .bak 走**成文豁免**裁决（Option B，见 T6 裁决记录）。

**Tech Stack:** Python 3.11+ / pathlib / pytest（uv run 与 CI 同构）。

## Global Constraints

- 全部 task 为 **infra**：协调者亲自实现（SDD leaf/infra 分流规则），TDD。
- gate checker 纯函数幂等（AGENTS.md）；框架代码无 `print()`（structlog）；conventional commits；pathspec commit（禁 `git add -A`）。
- 验证命令一律 `uv run pytest ...` / `just check`（环境同构）。
- fixture 只能从 `tests/fixtures/` 真实产物 tmp_path 组装（G0.9）。
- 每个 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`。

---

### Task 1: `Layout.detect()` 单源 + paths.md 协议成文（spec R1 地基）

**Files:**
- Modify: `src/shenbi/paths.py`（新增 detect，紧邻 RoundPaths）
- Create: `docs/framework/paths.md`
- Test: `tests/unit/test_layout_detect.py`（新建）

**Interfaces:**
- G0.9 注记：detect_layout 为纯路径拓扑函数，测试用最小 JSON 占位文件测探测逻辑（非 LLM 产物语义校验，不属 fixture 真实性管辖）；布局**内容** fixture（genre-config/novel.json/md）一律复制 `tests/fixtures/genre-config-example.json`、`tests/fixtures/novel-example.json`、`tests/fixtures/chapter-*-draft.md` 真实产物。
- Produces: `class Layout(str, Enum): SKILL_OUTPUT="skill-output"; NOVEL_OUTPUT="novel-output"; PROJECT_OUTPUT="project-output"; NONE="none"` 与 `def detect_layout(project_dir: Path) -> Layout`（纯函数，**项目目录级**键控：dir 含 novel.json→PROJECT_OUTPUT；dir 含 genre-config.json 且 dir.parent.name=="novel-output"→NOVEL_OUTPUT；dir 含 genre-config.json 且 dir.parent.name=="skill-output"→SKILL_OUTPUT；dir 名即布局根（"novel-output"/"skill-output"/"project-output"）→对应布局（根级命中，供根推导用）；否则从 dir 逐级上溯父目录重复上述判定，到文件系统根仍无命中→NONE）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_layout_detect.py
from pathlib import Path
from shenbi.paths import Layout, detect_layout

def _mk(root: Path, layout: str) -> Path:
    proj = root / layout / "proj-x"
    (proj).mkdir(parents=True)
    return proj

def test_detect_project_output(tmp_path):
    p = _mk(tmp_path, "rounds/r1")
    (p / "novel.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.PROJECT_OUTPUT

def test_detect_novel_output(tmp_path):
    p = _mk(tmp_path, "novel-output")  # p = <tmp>/novel-output/proj-x，parent.name=="novel-output"
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.NOVEL_OUTPUT

def test_detect_skill_output(tmp_path):
    p = _mk(tmp_path, "skill-output")
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    assert detect_layout(p) is Layout.SKILL_OUTPUT

def test_detect_upward_walk(tmp_path):
    p = _mk(tmp_path, "skill-output")
    (p / "genre-config.json").write_text("{}", encoding="utf-8")
    deep = p / "chapters" / "ch3"
    deep.mkdir(parents=True)
    assert detect_layout(deep) is Layout.SKILL_OUTPUT  # 上溯命中

def test_detect_none(tmp_path):
    p = _mk(tmp_path, "misc")
    assert detect_layout(p) is Layout.NONE
```

- [ ] **Step 2:** `uv run pytest tests/unit/test_layout_detect.py -q --no-cov` → FAIL（ImportError: cannot import name 'Layout'）
- [ ] **Step 3:** paths.py 实现（Enum + detect_layout 纯函数，无 I/O 副作用；注释声明"single layout-probe authority, spec #48 C34/F413"）
- [ ] **Step 4:** 同命令 → 5 passed
- [ ] **Step 5:** 写 `docs/framework/paths.md`：rd/project_dir 唯一定义、三布局探测规则与新旧映射、rd≠project_dir 的 T1(rd==project_dir)/T2(rd≠project_dir) 调用矩阵、RoundPaths↔resolve_input_path 分工、grep 豁免清单（g0.py:329/330/340/346/356、g7.py:72/88）
- [ ] **Step 6:** Commit `feat: C34 R1 layout detect single-source + paths protocol doc (spec #48 T1)`（列文件路径）

### Task 2: RoundPaths.read() 显式回退 + 11 checker 调用方迁移（spec R1）

**Files:**
- Modify: `src/shenbi/paths.py:16-25`（read()）
- Modify: `src/shenbi/gates/g4/{pacing_design,foreshadowing_track,faction_builder,location_builder,relationship_map,story_architecture,worldbuilding,character_design,plot_thread_weaver,power_system,volume_outlining}.py`（RoundPaths 构造点）
- Test: `tests/unit/gates/g4/test_round_paths_explicit_root.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 paths.py。
- Produces: `RoundPaths.read(rel, chapter=None, *, strict: bool = False)`——rd 命中返回；miss 且 strict=True 抛 `FileNotFoundError`；miss 且 strict=False 返回 project_dir 路径**并**经模块级 logger `log = get_logger(__name__)` 的 `log.debug`（仓库惯例，gates/shared.py:7-11 同款）("round_paths_read_fallback", rel=rel)` 记事件（满足 spec"记 debug 日志"；测试用 `structlog.testing.capture_logs()` 断言——本仓 configure_logging 用 PrintLoggerFactory(stderr)，caplog 捕不到 structlog 事件（capture_logs 工作先例：tests/unit/test_scoring.py:1240、tests/unit/test_dispatcher_executor.py:350））。checker 侧构造改为 `RoundPaths(round_dir=Path(rd) if rd else Path(project_dir), project_dir=Path(project_dir) if project_dir else Path(rd), repo_root=...)` 的显式双根形式不变，但 read miss 回退事件可观测。

- [ ] **Step 1: 失败测试**（rd miss → project_dir 命中返回 + hook 记录；rd miss 且 strict → FileNotFoundError；rd 命中不触发 hook；三个真实 checker（pacing_design/worldbuilding/character_design）在 rd 只有 genre-config、目标 md 在 project_dir 时 read 走通且 hook 有记录——用 tmp_path 从 `tests/fixtures/` 复制真实 fixture 文件组装）
- [ ] **Step 2:** 跑 → FAIL
- [ ] **Step 3:** 实现：read() 加 strict/hook；11 个 checker 的 RoundPaths 构造统一为显式双根（`rd or pd` / `pd or rd` 已是现状则仅补注释 `# spec #48 C34: explicit roots, no silent fallthrough`——以 grep 实际形态为准，凡 `rd or project_dir` 单根构造改为显式双根）
- [ ] **Step 4:** `uv run pytest tests/unit/gates/g4/test_round_paths_explicit_root.py tests/unit/test_round_paths.py -q --no-cov` → 全 PASS；`git grep -n "\.read(" -- src/shenbi/gates/g4/` 仍 11 文件（清单闭包不变）
- [ ] **Step 5:** Commit `fix: C34 R1 RoundPaths.read explicit fallback + 11-checker explicit roots (spec #48 T2)`

### Task 3: G0.3/G0.cc/chapter_drafting 上溯改走 detect()（spec R1 收口）

**Files:**
- Modify: `src/shenbi/gates/g0.py:210`（G0.3 skill-output 扫描）、`src/shenbi/gates/g0.py:664`（G0.cc novel-output 扫描）、`src/shenbi/gates/g4/chapter_drafting.py:265-267`（skill-output 上溯）
- Test: `tests/unit/gates/g0/test_g0_layout_scan.py`、`tests/unit/gates/g4/test_chapter_drafting_detect.py`（新建）

**Interfaces:**
- Consumes: Task 1 `detect_layout`。
- Produces: 布局根枚举改为 detect 驱动：`_layout_project_roots(base: Path, layouts: frozenset[Layout]) -> list[Path]`（新纯 helper 于 g0.py）——候选 = base 直接子目录 ∪ base/{"novel-output","skill-output"} 的子目录（排除自身名为布局根的容器目录），逐个跑项目目录级 `detect_layout`，且 (root / "genre-config.json").exists() 的**项目根**（键文件存在性保留 G0.cc 既有过滤语义——detect 的布局根名命中仅在上溯判定中作锚，不单独构成项目根返回）；结果 sorted() 保序。G0.3 传 {NOVEL_OUTPUT, SKILL_OUTPUT}（项目根集合**扩大**为全部检出布局——F413 行为修复本体，Step-1 测试断言 novel-output 项目可被 G0.3 找到），G0.cc 传 {NOVEL_OUTPUT}（语义不变）。chapter_drafting 的 `while proj_dir.name != "skill-output"` 上溯改为：从 `pf.parent` 逐级上溯父目录至首个含 genre-config.json 的祖先，取其为 project_root（单项目假设显式化：布局根下多项目时取路径上最近的那个）；无命中回落 `read_genre_config(str(pf.parent))` 现状并注释对齐 paths.md。

- [ ] **Step 1: 失败测试**（PROJECT 注入：monkeypatch.setattr(g0, "PROJECT", tmp_path)（g0.py 用模块级 PROJECT 常量，无 base 参数）；G0.3 在 novel-output 布局项目上能找到 genre-config（现状找不到→silent no-op）；chapter_drafting 的 project_root 在 project-output 布局 md 上指向含 genre-config 的真实项目根——tmp_path 从 fixtures 组装三布局）
- [ ] **Step 2:** FAIL → **Step 3:** 实现接线 → **Step 4:** PASS + `git grep -n "skill-output" -- src/shenbi/gates/` 命中仅剩 g0.py 注释/文案豁免点与 g7.py:72/88（g0.py:210 与 chapter_drafting.py:265/267 的探测语义命中消失）
- [ ] **Step 5:** Commit `fix: C34 R1 G0.3/G0.cc/chapter_drafting layout scans via detect() (spec #48 T3)`

### Task 4: cli G4/G2/bughunt-clean 路径收口（spec R2：F433+F101 残留+F456+F457+F446）

**Files:**
- Modify: `src/shenbi/gates/cli.py:100-165`（G4 分支 + G2 分支）、`src/shenbi/gates/g2.py:59-61`（G2.1）、`src/shenbi/gates/g4/generic.py:381-388`（bughunt/clean 包装）、`src/shenbi/gates/g7.py:175-180`（G7.13）、`src/shenbi/phase_runner.py:261-263`（G4 调用补 project_dir 第 4 实参——T2 阶段 project-output 布局下 rd≠project_dir，缺此接线则 F433 症状在 T2 运行中残留；project_dir 取 `proj` 推导的项目根，与 derive_output_files 同源）
- Test: `tests/unit/gates/test_cli_g4_project_dir.py`、`tests/unit/gates/test_g2_resolve.py`（新建）

**Interfaces:**
- Produces: cli G4 分支新增可选第 4 位置参数 `project_dir`（缺省回落 rd，T1 形态 rd==project_dir 成文于 paths.md 矩阵）；`gate_G4_bughunt(file_paths, round_dir=None, project_dir=None, repo_root=None)` 与 `gate_G4_clean(...)` 同签名（透传 g4_generic_*，向后兼容默认 None）；g2.py G2.1 改 `p = resolve_input_path(fp, round_dir)`（ValueError 捕获转结构化 FAIL：`{"id":"G2.1","s":FAIL,"r":"not found (relative path requires round_dir)"}`）；G7.13 的 `project_dir=str(rd / "project-output")` 改与 cli 同源：`project_dir=str(detect 布局根)`：g7 侧用 `detect_layout(rd)` 推导（rd 为 project-output 布局根时即 rd 本身；否则回落 `rd / "project-output"` 现状并注释对齐 paths.md 矩阵）。

- [ ] **Step 1: 失败测试**：
  - F433 复现：project-output 布局，rd 与真实 project_dir 分置。`.integrity-findings-3.jsonl` **G0.9 合规来源 = 测试内经真实写方代码路径生成**：直调模块级函数 `from shenbi.pipeline.dispatch_helper import _write_parsed_outputs`（dispatch_helper.py:1418，模块级可独立调用；`skill=None` + `parsed={"audits/chapter-3-x.md": "<无 verdict 短文本>"}` 即触发 check_audit_completeness→_append_integrity_findings 写 `<pd>/audits/.integrity-findings-3.jsonl`）——不手写 jsonl 内容。写方文件名须含**非补零**章号（`audits/chapter-3-x.md`）：写方以 `m.group(1)` 字符串拼名（chapter-03 → "03"），读方 `int()` 去 padding 寻址（→"3"）——补零名会让读方永远缺席，此处 pin 非补零形态。cli G4 传第 4 参 project_dir 后 `gate_G4(...)` 结果含 G4.ac/av PWI checks（现状 project_dir=rd 时缺席）
  - F457 复现：bughunt/clean + 相对路径 + rd → 结构化结果非未捕获 ValueError；另 no-rd 形态（shenbi-validate G4 bughunt <rel>）→ cli ValueError 守卫扩展至 bughunt/clean 分支，同样结构化 FAIL
  - F456 复现：gate_G2(["ch3.md"], "chapter", rd=tmp) 且 CWD≠rd → G2.1 定位 rd/ch3.md 成功（现状 not found）
  - F446 回归：相对 json + rd + CWD≠rd → 结构化 FAIL JSON 或 PASS，永不裸崩
- [ ] **Step 2:** FAIL → **Step 3:** 实现（cli argparse 位置参数扩展注意向后兼容：第 4 参可缺省）→ **Step 4:** `uv run pytest tests/unit/gates/test_cli_g4_project_dir.py tests/unit/gates/test_g2_resolve.py tests/unit/gates/ -q --no-cov` 全 PASS
- [ ] **Step 5:** Commit `fix: C34 R2 gate path wiring — G4 project_dir, G2.1 resolve, bughunt/clean rd, G7.13 align (spec #48 T4)`

### Task 5: 观测面同根残留（spec R3：F115 残留+F628+F119）

**Files:**
- Modify: `src/shenbi/phase_runner.py:248-255`（rglob 回退）、`src/shenbi/skill_utils/drift_detection/compute_drift.py:246-300`（main args + 写入路径）、`src/shenbi/capability_fs.py:22-28`（_sandbox）
- Test: `tests/unit/test_phase_runner_fallback.py`、`tests/unit/skill_utils/test_compute_drift_anchor.py`、`tests/unit/test_capability_fs.py`（扩展）

**Interfaces:**
- Produces: phase_runner rglob 回退限定 `derive_output_files` 声明目录内（回退扫描根 = `proj` 下契约声明路径的父目录；无声明可依则记 SKIP 不送 G2）；compute_drift 新增 `--project-dir` 参数（缺省从输入 truth 路径上溯 `truth/` 父目录推导），`_append_audit(findings, Path(project_dir) / "truth" / "audit_drift.md")`，trend 默认路径同锚；CapabilityFS `_sandbox` 相对路径先拼 `self._root` 再 resolve（`p if p.is_absolute() else self._root / p`）。

- [ ] **Step 1: 失败测试**：
  - rglob 回退不再捡 proj 内声明目录之外的预存 .md（tmp 组装：契约无输出声明 + 目录有无关 .md → G2 SKIP 非 chapter 校验）
  - compute_drift：CWD≠project_dir 下 `--write-audit-drift` 写入 `<project_dir>/truth/audit_drift.md`；无 --project-dir 时从输入路径推导同位置；与 `pipeline/triggers.py:77` AUDIT_DRIFT_PATH 及 chapter_loop.py:1567 读方路径形态一致
  - CapabilityFS：`fs.read_text(Path("truth/x.md"))` 锚定 allow_root/truth/x.md（现状 PermissionError 或 CWD 误读）
- [ ] **Step 2:** FAIL → **Step 3:** 实现 → **Step 4:** `uv run pytest tests/unit/test_phase_runner_fallback.py tests/unit/skill_utils/test_compute_drift_anchor.py tests/unit/test_capability_fs.py tests/property/gates/test_capability_fs_properties.py -q --no-cov` 全 PASS
- [ ] **Step 5:** Commit `fix: C34 R3 observation-plane roots — rglob scope, drift anchor, CapabilityFS allow_root join (spec #48 T5)`

### Task 6: G1.4 .bak 契约裁决（spec R4：F412）——裁决 = Option B 成文豁免

**裁决记录（写进 paths.md + gates.md）**：选 **Option B（成文豁免）**。理由：G2.11 的 .bak 读方契约（shared.py:40-48 bak_path）与 dispatcher 失败恢复路径已依赖"G1 运行时 .bak 已存在"这一时序；将备份移到 dispatcher 预阶段（Option A）需迁移 executor.py run_g1 subprocess 接线 + G1.4 SKIP 分支 + G2.11 读方三处，破坏面大于收益且引入"G1 未跑但 G2.11 期望 .bak"的新时序洞。豁免范围严格限定 G1.4 的 .bak 备份写（幂等：存在即跳过），非任意写。

**Files:**
- Modify: `src/shenbi/gates/g1.py:224-249`（docstring 注明豁免与裁决出处）、`docs/framework/gates.md`（豁免条目）、`docs/framework/paths.md`（.bak 锚定=源文件同目录，路径协议一部分）、`AGENTS.md`（Python Conventions 节 gate 纯函数条目加一句豁免引用："唯一豁免：G1.4 的 .bak 幂等备份写（docs/framework/gates.md 裁决）"）
- Test: `tests/unit/gates/test_g1_bak_exemption.py`（新建，幂等断言）

- [ ] **Step 1: 失败测试**：G1.4 两次运行（同 round_dir 同文件）第二次 r == ".bak exists" 不重写（幂等豁免行为被 pin）；docstring/文档含豁免关键词断言（防回退）
- [ ] **Step 2:** FAIL → **Step 3:** docstring + gates.md + paths.md 落文 → **Step 4:** PASS + `uv run just gate G1 <真实 fixture skill+files>`（只读验证入口）无异常
- [ ] **Step 5:** Commit `docs: C34 R4 G1.4 .bak adjudicated exemption (Option B) + protocol docs (spec #48 T6)`

### Task 7: 簇级路径矩阵 + 回写（spec 簇级验收）

**Files:**
- Create: `tests/unit/gates/test_path_resolution.py`
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（C34 成员回写：11 条 merged-into F433 关闭；F401/F408/F519 注记已由先前 PR 修复）、`docs/superpowers/specs/INDEX.md`（#48 状态注记——归档在阶段 12，此处仅回写注记）

**Interfaces:**
- Consumes: T1-T6 全部。

- [ ] **Step 1:** 参数化矩阵测试：`@pytest.mark.parametrize("layout", [SKILL_OUTPUT, NOVEL_OUTPUT, PROJECT_OUTPUT]) × rd 传/不传 × 相对/绝对 × CWD∈{rd, other} × project_dir∈{rd, ≠rd}`——三布局 tmp 组装（fixture 源文件取 `tests/fixtures/` 真实产物复制），断言 G4 定位到同一目标文件
- [ ] **Step 2:** FAIL（矩阵缺口）→ **Step 3:** 补齐收口（若有矩阵格失败，回对应 task 修复而非在本 task 打补丁）→ **Step 4:** `uv run pytest tests/unit/gates/test_path_resolution.py -q --no-cov` 全 PASS；ledger 回写 + INDEX 注记
- [ ] **Step 5:** Commit `test: C34 cluster path-resolution matrix + ledger writeback (spec #48 T7)`

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 grep 收口 | T3 | `git grep -n "skill-output" -- src/shenbi/gates/` 豁免清单外零探测命中 |
| R1 三布局同文件 | T7 | `uv run pytest tests/unit/gates/test_path_resolution.py -q --no-cov` |
| R2 PWI 定位 / 相对全绿 | T4 | `uv run pytest tests/unit/gates/test_cli_g4_project_dir.py tests/unit/gates/test_g2_resolve.py -q --no-cov` |
| R3 drift 锚定 / CapFS / rglob | T5 | `uv run pytest tests/unit/skill_utils/test_compute_drift_anchor.py tests/unit/test_capability_fs.py tests/unit/test_phase_runner_fallback.py -q --no-cov` |
| R4 豁免成文 | T6 | `uv run pytest tests/unit/gates/test_g1_bak_exemption.py -q --no-cov` + gates.md 条目 |
| 簇级 just check | 全 | `uv run just check` |
| 回写 14 条 | T7 | ledger F433 行 + INDEX |

## 复杂度/test_kind 声明

- 全部 task：`复杂度: infra`（paths/gates/pipeline/capability_fs），协调者亲自实现。
- T1-T5：`test_kind: tdd_red_green`（新行为）；T6：`test_kind: regression_guard`（行为保持 + 文档 pin）；T7：`test_kind: characterization`（矩阵收口）。
- 测试层级：全部 T1（unit）；T7 矩阵以 tmp 组装覆盖 T2 形态但仍在 unit 层（不触发真实 dispatch，核心原则 8）。fixtures 全部引用 `tests/fixtures/` 真实产物路径（G0.9）。
- 无评分场景 → 无 G3.4 调度需求。

- paths.md 注记：detect 键控项目根直置的 genre-config.json，而 dispatch_helper._load_genre_config_cached 读 config/genre-config.json（dispatch_helper.py:228）为既有分置——映射表显式记录，不在本簇收敛。
