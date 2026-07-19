# Pipeline 成熟度与行业最佳实践对齐修复 Spec

> **日期:** 2026-07-16
> **状态:** 设计中
> **前置:**
> - `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md`（原始 pipeline 设计）
> - `docs/superpowers/specs/2026-07-06-pipeline-phase1-defect-fix-design.md`（Phase 1 阻塞缺陷修复）
> - `docs/superpowers/specs/2026-07-02-novel-pipeline-root-cause-fixes-design.md`（根因分析）
> **目的:** 基于 2026-07-15 的全量审计（5 个并行分析 agent + 代码逐行核实），系统化修复 Pipeline 的阻断性缺陷、对齐 LLM 工程行业最佳实践、清理一致性债务，使 Pipeline 从"未经验证的精密框架"转变为"可审计、可复现、可生产"的成熟系统。

---

## 1. 背景

### 1.1 审计结论（2026-07-15）

对 Shenbi 仓库进行了 5 个并行 agent 的深度审计 + 主 agent 的逐行代码核实，核心发现：

| 维度 | 评分 | 依据 |
|------|------|------|
| 架构与工程严谨度 | 91/100 | 585 commits / 5 周，1875 单元测试，类型化状态机，8 门控，原子写 |
| 小说创作领域设计 | 93/100 | 6 层分层记忆、Chase Power 伏笔经济、20 审评分权分离 |
| 真实产出完整小说的证据 | ~45/100 | `novel-output/` 空、`tests/rounds/` 被删、`.gitignore` 抑制所有真实输出 |
| 证据可信度 | 40/100 | 伪章节 fixture、删档前科（"幻影数据"）、610 处空字符串 mock |
| 生产就绪度 | 60/100 | dispatch 真实可用但存在死路径 bug、rollback stub、未注册脚本 |

**核心矛盾：** 这是一个 91 分的架构包裹着一个 45 分的未验证内核。585 commits 完善门控/契约/状态机——而仓库内不存在任何一本完整产出的小说。

### 1.2 本 Spec 修复范围

本 Spec 涵盖三类共 20 项修复（P0 阻断 5 + P1 工程实践 9 + P2 一致性 6），来源于审计报告的：

- **§3 Gaps & Consistent Issues**：Critical #1-5、Structure #6-8、Consistency #9-11
- **§5 What It Does Bad**：第 2-8 项（第 1 项"从未产出小说"由 P0.5 根治）
- **§6 What Doesn't Follow Industry Best Practice**：第 1-10 项

---

## 2. 总体策略

### 2.1 实施原则

**每次只改一个缺陷，改完立即验证（`just check`），验证通过才进入下一个。**

延续 Phase 1 的 Toyota Kata 持续改进方法。P0 阶段每项修复后必须全量门控通过；P1/P2 阶段每项修复后必须对应模块测试 + 全量门控通过。

**三条铁律（延续项目"三不原则"）：**
1. 不跳过门控
2. 不手写 mock 替代真实 skill 输出
3. 不将 Dispatcher 评分当作独立评分

### 2.2 依赖链

```
执行后端决策（已定：OpenAI 兼容 API 为主）
    ↓
┌─ P0.1 (phase_runner 死路径)      ─┐
│  P0.2 (shenbi-progress 未注册)    │ 四者全部独立，可并行
│  P0.3 (rollback stub 移除)        │
└─ P0.4 (codex_api 死分支)         ─┘
    ↓ （P0.1-4 全部修复后）
P0.5 (端到端真实运行)              ← 依赖 P0.1-4 + 执行后端就绪
    ↓ 产生第一个可审计产物
P1.3 (结构化输出) → P1.4 (重试) → P1.5 (流式) → P1.6 (温度配置)
    ↓ 这四项共同构成"生产级 API executor"
P1.2 (评分独立性) ← 依赖执行后端决策
P1.8 (golden set) ← 依赖 P0.5 的真实产出
P1.9 (双状态机文档) ← 独立
    ↓
P2.1-P2.6 (一致性清理) ← 大部分独立，可并行
    ↓
最终验收：端到端跑通 + 全量门控 + 可审计产物提交
```

### 2.3 每个 Step 的验证标准

```
改 1 个缺陷 → 跑该模块单元测试 → 跑全量 just check → （P0/P1 关键项）跑金丝雀章节
```

任一阶段失败即停止，不允许带着已知失败进入下一步。

---

## 3. 执行后端决策

### 3.1 现状

Pipeline 的 `dispatch_helper.dispatch_skill`（`src/shenbi/pipeline/dispatch_helper.py:545-604`）有三条路由，按优先级：

1. **API 路径**（`:565-566`）：`SHENBI_LLM_API_KEY` 已设置 → `_dispatch_via_api` 调 `openai.OpenAI`（默认 `https://api.deepseek.com/v1` + `deepseek-v4-pro`）
2. **IDE CLI 路径**（`:569-570`）：`_find_ide_cli()` 返回 `codex`/`zcode` → `_dispatch_via_ide` 子进程
3. **Legacy CLI 路径**（`:582-604`）：`shenbi-dispatch` 子进程

### 3.2 本机环境调研（2026-07-16）

| CLI | 状态 | 备注 |
|-----|------|------|
| `codex` | ✓ `/opt/homebrew/bin/codex`（0.144.1） | `codex exec` 支持 `--skip-git-repo-check`、`-c` 配置覆盖 |
| `claude` | ✓ `/opt/homebrew/bin/claude` | 支持 `-p/--print` headless + `--output-format=stream-json` |
| `zcode` | ✗ 未安装 | — |
| `ollama` | ✗ 未安装 | 无本地模型 |

### 3.3 决策：以 OpenAI 兼容 API 为主执行后端

**结论：** 生产路径走 API，codex/claude CLI 仅作本地开发兜底。

**依据（API 路径 vs CLI 子进程对比）：**

| 维度 | codex/claude CLI 子进程 | OpenAI 兼容 API |
|------|------------------------|-----------------|
| 输出解析 | regex 抓 `### FILE:` 标记（`dispatch_helper.py:272-291`），脆弱 | JSON mode + Pydantic 解析（P1.3） |
| 重试/退避 | 只在门控层重试（昂贵） | 调用层 tenacity 退避（P1.4） |
| 流式 | 不支持 | stream=True，可早停/反馈（P1.5） |
| 温度/模型控制 | 硬编码全局 0.7 | 按 skill 级配置（P1.6） |
| 可观测 | 子进程黑盒，stdout 抓取 | 每次 request 有 latency/token/usage（见 §9：留作未来 spec） |
| 成本追踪 | 无法获取 token usage | response 含 `usage` 字段（见 §9：留作未来 spec） |
| 评分独立性 | 同进程族，agent_id 形式独立 | 真正可分离 session（P1.2） |

**保留 CLI 作为兜底的理由：** 本地无 API key 时的开发/测试仍需可运行。`_find_ide_cli()` 增加 `claude` 探测（codex 优先，claude 次之）。

### 3.4 兼容 OpenAI 接口的可用服务

| 服务 | BASE_URL | 模型示例 |
|------|----------|----------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-v4-pro`（默认） |
| MiniMax | `https://api.minimax.chat/v1` | `M3` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus` |
| Moonshot Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-128k` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |

---

## 4. P0 — 阻断正确性

> **目标：** 修复使 Pipeline 无法跑通的死代码与 stub。P0 全部完成后才能进行 P0.5 端到端运行。

### Step P0.1: phase_runner 死路径

**文件:** `src/shenbi/phase_runner.py:54-66`、`src/shenbi/scoring.py:303,332`

**问题:** `run_gate()` 子进程调用 `tests/validate-gate.py`（`:56` `vg = str(TESTS / "validate-gate.py")`），但该文件在 PR-19 迁移到 `src/shenbi/gates/` 后**已从磁盘删除**。`except (JSONDecodeError, ValueError)`（`:65`）不捕获 `FileNotFoundError` → `shenbi-phase start/pre-skill/post-skill/finalize` 全部会崩溃。

`scoring.py:303`（`--gate-only` 模式）和 `:332`（T1 gate 集成）构造同样的死路径。

```python
# phase_runner.py:54-66（当前）
def run_gate(gate: str, args: list[str]) -> dict[str, Any]:
    vg = str(TESTS / "validate-gate.py")  # ← 文件不存在
    r = subprocess.run(
        [sys.executable, vg, gate] + args,
        capture_output=True, text=True, timeout=60,
    )
    try:
        return cast(dict[str, Any], json.loads(r.stdout))
    except (JSONDecodeError, ValueError):  # ← 不捕获 FileNotFoundError
        return {"status": GateStatus.FAIL, ...}
```

**修复:** 改调 `python -m shenbi.gates.cli`（与 `dispatch_helper.run_gate_g3/g4` 一致）。

```python
def run_gate(gate: str, args: list[str]) -> dict[str, Any]:
    r = subprocess.run(
        [sys.executable, "-m", "shenbi.gates.cli", gate] + args,
        capture_output=True, text=True, timeout=60,
    )
    try:
        return cast(dict[str, Any], json.loads(r.stdout))
    except (json.JSONDecodeError, ValueError, subprocess.SubprocessError):
        return {"status": GateStatus.FAIL, "raw_stdout": r.stdout, "raw_stderr": r.stderr}
```

`scoring.py:303,332` 同理修改：把 `tests/validate-gate.py` 路径替换为 `python -m shenbi.gates.cli`。

**依赖链:** 无前置；P0.5 端到端运行的前置。

**验证:**
- `shenbi-phase start <phase> --round-dir <dir>` 不再 FileNotFoundError
- 单元测试：mock subprocess，验证调用目标是 `shenbi.gates.cli`
- `just check` 全量通过

---

### Step P0.2: shenbi-progress 脚本未注册

**文件:** `src/shenbi/dispatcher/modes/codex.py:85`、`pyproject.toml:55-65`

**问题:** `codex.py:85` 调用 `uv run shenbi-progress mark-done`，但 `pyproject.toml [project.scripts]` 仅注册了 `shenbi-validate/dispatch/score/phase/sync-contracts/generate-plugins`——**`shenbi-progress` 不存在**。codex 模式 dispatch 会在该子进程失败。

```python
# codex.py:82-89（当前）
result = subprocess.run(
    ["uv", "run", "shenbi-progress", "mark-done", skill, ...],  # ← 未注册
    capture_output=True, text=True,
)
```

**修复:** 优先核实 `mark-done` 功能是否已被 `progress.json` 写入逻辑替代。

- **若已替代**（预期）：删除 `codex.py:82-89` 的子进程调用，改由 codex 模式内部直接更新 `progress.json`（复用 `dispatcher/executor.py` 已有的 progress 写入逻辑）
- **若未替代**：在 `pyproject.toml` 注册 `shenbi-progress = "shenbi.dispatcher.progress:main"` 并实现该模块

**依赖链:** 无前置；影响 codex 模式（本地开发兜底），不影响 API 主路径。

**验证:**
- codex 模式 dispatch 不再因该子进程失败
- `uv run shenbi-dispatch <skill> generative <round> "<prompt>"`（codex 模式）端到端跑通
- `just check` 全量通过

---

### Step P0.3: rollback stub 移除

**文件:** `src/shenbi/pipeline/cli.py:12,784-798,839-842`

**问题:** `cmd_rollback`（`:784-798`）返回 `{"status": "not_implemented"}`，但 CLI docstring（`:12`）和 subparser 注册（`:839-842`）广告该命令——用户会被误导以为可用。

```python
# cli.py:784-798（当前）
def cmd_rollback(args: argparse.Namespace) -> int:
    ...
    emit_json({
        "status": "not_implemented",
        "message": "Rollback requires snapshot integration (Wave 3/4)",
    })
    return 0  # ← 返回 0（成功）更具误导性
```

**修复:** P0 阶段移除 CLI 注册，避免误导。真正的 snapshot 回滚实现列入 P1（基于 `snapshots/manifest.json`）。

- 删除 `cli.py:839-842` 的 `p_rollback` subparser 注册
- 删除 `cli.py:12` docstring 中的 `rollback` 行
- `cmd_rollback` 函数保留但标注 `# TODO(P1): implement rollback via snapshots/manifest.json`，改为返回非零退出码 + 明确错误

**依赖链:** 无前置；独立。

**验证:**
- `pipeline --help` 不再显示 rollback
- 直接调用 `pipeline rollback ...` 返回明确错误（非 0、非"成功"）
- `just check` 全量通过

---

### Step P0.4: codex_api 死分支移除

**文件:** `src/shenbi/dispatcher/modes/codex_api.py:13-15`、`src/shenbi/dispatcher/executor.py:237-240,164-174`

**问题:** `codex_api.py` 是 `NoReturn` raise stub，但 `executor.py:237-240` 广告该路由选项。`detect_mode()`（`:164-174`）只返回 `"codex"` 或 `"internal"`——**`codex-api` 分支永远不可达**。

```python
# executor.py:237-240（当前，死代码）
if mode == "codex-api":
    from shenbi.dispatcher.modes.codex_api import dispatch_codex_api
    return dispatch_codex_api(...)  # ← 永不执行
```

**修复:** 移除死分支。

- `executor.py:237-240`：删除 `codex-api` 分支
- `executor.py:164-174`（`detect_mode`）：确认只返回 codex/internal
- `codex_api.py`：保留文件但顶部标注 `# DEPRECATED: superseded by unified API executor (P1.3). Remove in next minor.`

**依赖链:** 无前置；独立。与执行后端决策（§3）一致——API 路径由 `dispatch_helper._dispatch_via_api` 承担，不需独立的 codex_api 模式。

**验证:**
- grep 确认无代码路径可达 `dispatch_codex_api`
- `just check` 全量通过

---

### Step P0.5: 端到端真实运行（根治"未经验证"）

**文件:** `.gitignore`、`novel-output/`（新建）、`run_pipeline.sh`

**问题:** `novel-output/` 空、`tests/rounds/` 被删（commit `b978d3cc`）、`.gitignore` 抑制所有真实 round 输出和 per-skill 报告。此前还有"幻影数据"前科（`goal-prompt.md`："Round 005 已废弃（含幻影 T2/T3 数据）"）。**这是整个项目的核心缺陷——没有可审计的真实产出。**

**修复:** 用 `outline-example.md`（星火燃穹）跑一次完整 Pipeline，覆盖性提交全部中间产物。

1. **`.gitignore` 加例外：**
   ```gitignore
   # 允许 novel-output/ 的真实产出提交（可审计性）
   !novel-output/
   !novel-output/**
   ```
   （`tests/rounds/` 的抑制策略保持不变——pipeline 产物走 `novel-output/`，不走 rounds）

2. **配置执行后端：** 设置 `SHENBI_LLM_API_KEY` + `SHENBI_LLM_BASE_URL` + `SHENBI_LLM_MODEL`（见 §3.4）

3. **执行：**
   ```bash
   just pipeline-init outline-example.md ./novel-output/xinghuo-ranqiong --auto
   just pipeline-resume ./novel-output/xinghuo-ranqiong  # 重复直到 completed
   just pipeline-status ./novel-output/xinghuo-ranqiong
   ```

4. **可审计产物清单（必须提交）：**
   - `pipeline-state.json`（最终状态）
   - `genesis/` 全部产物（story_bible、characters、outline 等）
   - `chapters/chapter-N.md`（至少 N 章，目标完整）
   - `truth/` 全部 truth 文件
   - `audits/chapter-N-*.md`（全部审核报告）
   - `gate-markers/`（G4/G6 markers）

**依赖链:** P0.1-4 全部修复 + 执行后端就绪。**这是整个 spec 的里程碑——产出第一个可审计的真实小说。**

**验证:**
- `novel-output/xinghuo-ranqiong/` 存在且含上述产物
- `pipeline-status` 显示 `phase: completed`
- G6（pipeline 完整性）通过
- README 链接到该运行（作为"已验证"证据）
- 若中途失败：记录失败点，修复后继续（不伪造结果）

**风险与缓解:**
- **API 成本：** 100k 字小说可能消耗显著 token。缓解：先用 `--auto` 跑 5 章金丝雀，确认稳定后再跑全量；手动监控用量（成本预算强制留作未来 spec，见 §9）
- **中途失败：** Pipeline 是 resumable（`pipeline-state.json` 持久化），失败可 resume
- **产出质量不达标：** 这是预期的——P0.5 的目标是"跑通"而非"完美"，质量问题由后续 P1.8（golden set）系统化处理

---

## 5. P1 — 工程实践对齐行业最佳实践

> **目标：** 使 Pipeline 的 LLM 工程层达到生产级。这些是 §6（What Doesn't Follow Industry Best Practice）的系统化修复。

> **P1.1（可观测性）与 P1.7（成本预算）已从本 Spec 移除，留作未来独立 spec。** 见 §9 超出范围。

---

### Step P1.2: 评分独立性强化

**文件:** `src/shenbi/dispatcher/modes/internal.py`、`src/shenbi/gates/g3.py`、`src/shenbi/gates/g3_independence.py`

**现状（已实现，勿重写）:** G3.4 已通过 `scoring_independence_status()`（`g3_independence.py`）实现 **fail-closed** 逻辑：缺 `current_scorer_agent` 证据 → FAIL；生成 agent == 评分 agent → FAIL；否则 PASS。该函数已接线进 `gate_G3`（g3.py G3.4 分支）。**这一层不需改动——它已经是正确的。**

**残留问题（本 Step 修复目标）:**

1. **internal 模式空转：** `internal.py`（`dispatcher/modes/internal.py`）返回成功但不产出任何评分文件，日志写 `"Dispatcher completes scoring manually"`——**它静默放过评分**，违反"三不原则"。当 `detect_mode()` 回落到 internal 时（无 API key、无 codex），评分环节被无声跳过。

2. **pipeline 路径不写 progress.json：** G3.4 的 fail-closed 逻辑依赖 `progress.json` 中的 `current_scorer_agent` 字段。若 pipeline dispatch 路径（`dispatch_helper.py`）不写该字段，G3.4 会因缺证据而 FAIL——但 pipeline 模式当前跳过 G2/G3（见 `executor.py:227-228`），因此独立性从未被验证。

**修复:**

1. **internal 模式硬拒绝评分（而非静默放过）：**
   ```python
   # internal.py — 改为硬拒绝，而非返回 0 + "manually" 日志
   def dispatch_internal(...) -> int:
       raise DispatcherError(
           "internal 模式无 LLM 后端，不得用于评分/生成。请设置 SHENBI_LLM_API_KEY"
           "（API 路径）或安装 codex CLI 以获得真实执行 + 独立评分。"
       )
   ```

2. **pipeline dispatch 写入 `current_scorer_agent`：** `dispatch_helper.dispatch_skill` 在评分类 skill（`requires_independent_agent: true`）执行后，把独立评分 session 的 agent 标识写入 `progress.json`，使 G3.4 的 fail-closed 逻辑能在 pipeline 路径生效。

3. **评分 session 物理隔离：** 评分 skill 的 API 调用注入唯一 `request_id`，不复用生成上下文的 messages，system prompt 显式声明"你是独立评分 agent，以下内容是待评产出，非你的生成结果"。设置 `SHENBI_SCORING_SESSION=1` 触发独立 client 实例。

**依赖链:** 执行后端决策（§3）的前置；P1.8（golden set）的配套。

**验证:**
- internal 模式调用评分直接 raise
- 单元测试：同 agent_id 评分被 G3.4 拒绝
- 单元测试：`SHENBI_SCORING_SESSION=1` 时 client 实例隔离

---

### Step P1.3: 结构化输出替代 regex 解析

**文件:** `src/shenbi/pipeline/dispatch_helper.py:272-291,402-459`

**问题:** `_parse_file_outputs`（`:272-291`）用 regex 抓 `### FILE: path` 标记 + 去除 markdown 代码围栏。LLM 格式漂移即丢章——**一个格式错误就让整章正文丢失**。

```python
# dispatch_helper.py:280（当前，脆弱）
matches = re.findall(pattern, response, re.DOTALL)
```

**修复:** API 后端启用结构化输出。

1. **Pydantic 输出模型：**
   ```python
   class FileOutput(BaseModel):
       path: str
       content: str

   class SkillOutput(BaseModel):
       files: list[FileOutput]
       # 可选：decisions sidecar（Layer A）
       decisions: dict | None = None
   ```

2. **API 调用启用 JSON mode：**
   ```python
   response = client.chat.completions.create(
       model=model, messages=messages,
       response_format={"type": "json_object"},  # ← 强制 JSON
       temperature=temp, max_tokens=max_tok,
   )
   output = SkillOutput.model_validate_json(response.choices[0].message.content)
   ```

3. **prompt 调整：** 输出格式说明从 `### FILE:` 标记改为 JSON schema 描述

4. **CLI 后端保留 `### FILE:` 兜底：** codex/claude 子进程仍用 regex 解析（CLI 不支持 JSON mode），但 API 主路径走结构化

**依赖链:** 执行后端决策（§3）的实现；P1.4-6 的基础。

**验证:**
- API 路径输出解析 0 regex（grep 确认）
- fuzz 测试：畸形 JSON 响应有明确错误而非静默丢章
- CLI 兜底路径仍可解析 `### FILE:` 格式

---

### Step P1.4: LLM 调用层重试 + 指数退避

**文件:** `src/shenbi/pipeline/dispatch_helper.py:402-459`

**问题:** `_dispatch_via_api` 单次 `chat.completions.create`，无重试。429/500/timeout 直接失败，只在昂贵的门控层（重新 dispatch 整个 skill）重试。行业标配是调用层 tenacity 退避。

**修复:** 用 tenacity 包装 API 调用。tenacity **不在当前依赖中**（已核实 `pyproject.toml` 与 `uv.lock` 均无），新增为 required dependency（`uv add tenacity`）。`httpx` 已作为 openai 的传递依赖可用，故重试异常类型可正常引用。

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),  # 对齐 error_handler.MAX_DISPATCH_RETRIES=2（共 3 次）
    wait=wait_exponential_jitter(initial=1, max=30),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    # 仅重试 429/5xx/timeout，不重试 4xx（参数错误）
)
def _call_llm(client, model, messages, **kwargs):
    return client.chat.completions.create(model=model, messages=messages, **kwargs)
```

**重试层次（清晰分工）：**
- **LLM 层（P1.4）：** 重试瞬态网络/API 错误（429/5xx/timeout），指数退避
- **门控层（现有 error_handler）：** 重试结构性失败（G4 不通过），重新 dispatch 整个 skill

LLM 层先耗尽（3 次），门控层再判定（重新 dispatch = 新的 LLM 层重试周期）。

**依赖链:** P1.3 的基础；独立于 P1.5-6。

**验证:**
- 契约测试：mock API 返回 429，验证自动重试 3 次后成功
- 契约测试：mock API 返回 400，验证不重试直接失败
- trace 记录 `attempt` 字段

---

### Step P1.5: 流式输出

**文件:** `src/shenbi/pipeline/dispatch_helper.py:402-459`

**问题:** 阻塞 `create()` 调用，16k token 长等待，无增量反馈、无早停。行业标配 stream=True。

**修复:**

```python
def _call_llm_streaming(client, model, messages, early_stop_patterns=None, **kwargs):
    collected = []
    stop_reason = None
    stream = client.chat.completions.create(
        model=model, messages=messages, stream=True, **kwargs,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        collected.append(delta)
        # 早停：检测漂移关键词（如重复段落、禁用句式）
        if early_stop_patterns:
            text_so_far = "".join(collected)
            for pat in early_stop_patterns:
                if pat in text_so_far:
                    stop_reason = f"early_stop: matched {pat}"
                    break
            if stop_reason:
                break
    return "".join(collected), stop_reason
```

**早停模式来源：** 复用 `genre-config.json` 的 `fatigueWords` 和 `chapter-drafting` SKILL.md 的禁用句式（如 `"不是…而是…"` 连续出现 3 次）。

**交互模式（可选增强）：** `pipeline resume --interactive` 时流式打印到终端，用户可 Ctrl+C 中断并给反馈。

**依赖链:** P1.3-4 的基础；独立于 P1.6。

**验证:**
- 长章节（>5000 字）流式产出，每 chunk < 2s
- 早停测试：注入漂移关键词，验证中断 + stop_reason 记录
- 非流式模式（默认）保持兼容

---

### Step P1.6: 按 skill 级温度/模型配置

**文件:** `src/shenbi/pipeline/dispatch_helper.py:40-49,425-441`、新增 `executor_config.toml`

**问题:** `_API_TEMPERATURE = 0.7`（`:48`）全局硬编码，67 个 skill 共用一个温度。但世界观构建、对话、反 AI 审核的最优温度差异巨大。

**修复:** 引入 per-skill 配置，复用 genre-config.json 的加载模式或新建 `executor_config.toml`。

```toml
# executor_config.toml
[default]
temperature = 0.7
max_tokens = 16384

[overrides."shenbi-chapter-drafting"]
temperature = 0.85   # 创作性高
max_tokens = 16384

[overrides."shenbi-review-continuity"]
temperature = 0.2    # 一致性检查要确定性
model = "deepseek-v4-pro"  # 可指定不同模型

[overrides."shenbi-worldbuilding"]
temperature = 0.75

[overrides."shenbi-review-anti-ai"]
temperature = 0.15   # 模式检测要极低温度

[overrides."shenbi-review-resonance"]
temperature = 0.3
```

```python
# dispatch_helper.py
def _load_executor_config() -> dict:
    config_path = Path(__file__).parent / "executor_config.toml"
    if config_path.exists():
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    return {"default": {"temperature": 0.7, "max_tokens": 16384}}

def _get_skill_params(skill: str) -> tuple[float, str, int]:
    config = _load_executor_config()
    default = config.get("default", {})
    override = config.get("overrides", {}).get(skill, {})
    return (
        override.get("temperature", default.get("temperature", 0.7)),
        override.get("model", os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)),
        override.get("max_tokens", default.get("max_tokens", 16384)),
    )
```

**依赖链:** P1.3-5 的配套；独立。

**清理（避免制造死常量）：** `executor_config.toml` 接入后，`dispatch_helper.py:48-49` 的 `_API_TEMPERATURE`/`_API_MAX_TOKENS` 常量**应删除**（被配置文件的 `default` 段取代）。`_DEFAULT_MODEL` 保留（作为无配置 + 无环境变量时的最终回退）。否则会留下 P2.3 所批评的死常量。

**验证:**
- 不同 skill 实际用不同温度（通过日志或 dispatch 返回值确认 `temperature` 字段）
- 无配置时回退默认 0.7
- `_API_TEMPERATURE`/`_API_MAX_TOKENS` 常量已删除，无残留引用
- 配置文件格式校验（G0 或单独检查）

---

### Step P1.8: Golden set + 人工评分校准

**文件:** `tests/golden/`（新建）、`src/shenbi/scoring.py`、`.github/workflows/`

**问题:** 1875 测试 mock LLM，**无端到端创作质量断言**。评分循环（同模型评同模型输出）。行业实践要求持有出的 golden set + 人工评分校准 + CI smoke test。

**修复:**

1. **建立 `tests/golden/`（10-20 章，人工评分）：**
   - 从 P0.5 的真实产出中选取代表性章节
   - 人工按 rubric 打分（记录到 `golden/<chapter>-scores.json`）
   - 标注已知缺陷（用于 bug-hunt 测试）

2. **`shenbi-score` 增加 `--calibrate-against` 模式：**
   ```bash
   shenbi-score <rubric> <auto-scores.json> \
       --calibrate-against tests/golden/<chapter>-scores.json
   ```
   计算：相关系数（Pearson/Spearman）、inter-rater reliability（Cohen's κ）、系统性偏差

3. **CI smoke test（nightly）：** 真跑 1 章，验证 pipeline 可运行（不强求质量阈值，只验证不崩）
   ```yaml
   # .github/workflows/nightly-smoke.yml
   - name: Pipeline smoke test (1 chapter)
     run: |
       just pipeline-init tests/fixtures/outline-example.md /tmp/smoke --auto
       SHENBI_LLM_API_KEY=${{ secrets.LLM_KEY }} just pipeline-resume /tmp/smoke
   ```

**依赖链:** P0.5（真实产出）的前置；P1.2（评分独立性）的配套。

**验证:**
- `tests/golden/` 存在且含 ≥10 章人工评分
- `--calibrate-against` 输出校准报告
- nightly smoke test 跑通（允许失败告警，不阻断 PR）

---

### Step P1.9: 双状态机文档消歧

**文件:** `src/shenbi/phase_runner.py:1-11`、`src/shenbi/pipeline/cli.py:1-19`、`docs/architecture/overview.md`

**问题:** `phase_runner.py`（T1/T2/T3 测试编排）与 `pipeline/`（小说生成）都叫 phase/checkpoint/gate，易混。§5 WhatBad #9。

**修复:** 不改名（成本高），但显式标注。

1. **两个 CLI 的 docstring + `--help` 顶部加标注：**
   ```python
   # phase_runner.py 模块 docstring
   """State machine for T1/T2/T3 TESTING phase execution.

   ⚠️ 这是测试编排器，NOT 小说生成器。
   小说生成请用 `pipeline` CLI (shenbi.pipeline.cli)。
   """
   ```
   ```python
   # pipeline/cli.py 模块 docstring
   """CLI entry point for the novel pipeline (小说生成).

   ✅ 这是小说生成器。
   T1/T2/T3 测试编排请用 `shenbi-phase` CLI (shenbi.phase_runner)。
   """
   ```

2. **`docs/architecture/overview.md` 增加"两个状态机"小节**，对比表说明用途差异

**依赖链:** 无前置；独立。

**验证:**
- `shenbi-phase --help` 顶部有"测试编排器"标注
- `pipeline --help` 顶部有"小说生成器"标注
- docs 有专节

---

## 6. P2 — 一致性与清理

> **目标：** 清理技术债务，使代码与文档一致。大部分独立，可并行。

### Step P2.1: CJK 编码健壮性

**文件:** `src/shenbi/contracts/fields.py:23-24`、`report-example.txt`

**问题:** `_normalize_ws`（`fields.py:23-24`）仅规范化 ASCII 空白 + U+3000，**无大小写、无零宽折叠**。中文文本中全/半角变体、零宽字符（U+200B/FEFF）常见，导致 field 匹配脆弱。`report-example.txt` 是 GBK 编码，UTF-8 读取乱码。

**修复:**

```python
# fields.py
import unicodedata

def _normalize_ws(text: str) -> str:
    # 折叠 ASCII 空白 + 全角空格
    text = text.replace("\u3000", " ")
    # 剥离零宽字符（U+200B 零宽空格、U+FEFF BOM/ZWNBSP、U+200C/ZWJ、U+200D/ZWNJ）
    text = "".join(c for c in text if c not in "\u200b\ufeff\u200c\u200d")
    # 全/半角折叠（NFKC 把全角字母数字符号转半角）
    text = unicodedata.normalize("NFKC", text)
    # 折叠连续空白
    import re
    text = re.sub(r"\s+", " ", text).strip()
    return text
```

`report-example.txt`：转码为 UTF-8 或移除（它是《钢铁是怎样炼成的》公共领域文本，非项目产物，被误标为"audit report"）。

**依赖链:** 无前置；独立。

**验证:**
- 属性测试：含零宽字符的 field 名能匹配
- 属性测试：全/半角混合的 section heading 能匹配
- `report-example.txt` 不再乱码或已移除

---

### Step P2.2: severity 枚举统一

**文件:** `src/shenbi/contracts/schemas/decisions.py:28,52`、`docs/framework/decisions-schema.md`

**问题:** `Selection.severity`（`:28`）是 `Literal["low","high"]`，但 `Adjustment.severity`（`:52`）是自由 `str`（注释自承认："doc uses 'medium', legacy validator never checked"）。同一文档两处 severity 严格度不同。

**修复:**

```python
# decisions.py
Severity = Literal["low", "medium", "high"]

class Selection(BaseModel):
    severity: Severity = "low"  # 统一用 Severity

class Adjustment(BaseModel):
    severity: Severity  # 从 str 改为 Severity
```

升级 decisions schema 版本（`shenbi-decisions-v1` → `shenbi-decisions-v2`），P2.5 规则按新枚举重新校准。`docs/framework/decisions-schema.md` 同步更新。

**依赖链:** 无前置；影响 decisions.json 产出（向后兼容：v1 的 low/high 在 v2 仍合法，medium 是新增）。

**验证:**
- `"medium"` 通过验证
- `"critical"` 被拒
- 现有 v1 fixture 在 v2 仍合法（low/high 不变）

---

### Step P2.3: 死常量清理 + 阈值单一源

**文件:** `src/shenbi/scoring.py:176-183`、`src/shenbi/contracts/thresholds.py`

**问题:** `thresholds.py` 定义了 `T1_PASS/T2_PASS/T3_PASS/TEST_PASS/CONVERGENCE`。经核实（grep）：**仅 g5.py、g3.py、_scoring_base.py import 了 T1_PASS/T2_PASS/TEST_PASS**；`T3_PASS`、`CONVERGENCE` 未被任何门控/scoring import。`scoring.classify`（`:176-183`）硬编码 90/75/60 而非用 `TEST_PASS`。

**修复:**

1. **`scoring.classify` 改用 `TEST_PASS`：**
   ```python
   from shenbi.contracts.thresholds import TEST_PASS

   def classify(score: float | int) -> ScoreClassification:
       if score >= TEST_PASS:  # 90，而非硬编码
           return ScoreClassification.PASS_EXCELLENT
       if score >= 75:
           return ScoreClassification.PASS_ACCEPTABLE
       if score >= 60:
           return ScoreClassification.CONDITIONAL
       return ScoreClassification.FAIL
   ```

2. **G6 引入 T3_PASS：** G6（`src/shenbi/gates/g6.py`）当前用 `min_chapter_ratio`（基于数量），增加 T3 分数检查时用 `T3_PASS`

3. **核实 `CONVERGENCE`：** 若确实无消费者，删除或标注 `# reserved for future convergence tracking`

**依赖链:** 无前置；独立。

**验证:**
- `classify` 用 TEST_PASS 而非魔法数 90
- grep 确认无未使用的 threshold 导出
- `just check` 全量通过

---

### Step P2.4: contracts/legacy.py 去伪标注

**文件:** `src/shenbi/contracts/legacy.py:1`

**问题:** 文件头标注 DEPRECATED（"This file will be deleted after all importers migrate"），但 `contracts/__init__.py:49-56` 从它 re-export，所有门控/dispatcher 消费它——**"legacy" 实际是规范实现**。误导维护者。

**修复:** 改 docstring 为准确描述。

```python
# legacy.py
"""Canonical contract loader and validator.

历史命名：本模块在 contract 系统重构初期命名为 'legacy'，
但实际上它是当前唯一活跃的 contract 加载器/校验器。
所有门控、dispatcher、pipeline 均通过 contracts.__init__ 消费本模块。

未来如迁移到新实现，应先完成所有 importer 的迁移，再删除本模块。
当前请勿删除——它是 single source of truth。
"""
```

**依赖链:** 无前置；独立。

**验证:**
- docstring 不再误导
- `just check` 全量通过

---

### Step P2.5: deferred PASS stub 透明化

**文件:** `src/shenbi/gates/g7.py:108-112`、`g_dispatch.py:67-69`、`g_reconcile.py:74-76`、`g_transition.py:66-91`、`src/shenbi/gates/shared.py:210-222`

**问题:** 多个门控子检查是无条件 `PASS` + `"deferred"` note：G7.2/3/4/8、GD.2/3、GR.3/4、GT.2/4/5、G0.5。`GateStatus.UNIMPLEMENTED`（`status.py:27`）和 `shared.unimplemented()` helper（`:210-222`）**已存在但从未被任何门控返回**——stub 静默 PASS 掩盖了未实现的检查。

> **注意：G3.1 不在本范围内。** G3.1（`g3.py:85-91`）已显式返回 `"s": "SKIP"` 并注明 "per-skill prerequisites not modeled (G3.2 covers readiness)"——这是有意的设计决策（就绪检查委托给 G3.2），**不是** deferred PASS stub。不要改动它。

**修复（系统化）:** 每个 stub 改返回 `s=UNIMPLEMENTED`，让审计能区分"真通过"与"未实现"。

```python
# g7.py — 改前
c.append({"id": "G7.2", "s": "PASS", "note": "skill-traces check deferred"})

# g7.py — 改后
c.append(shared.unimplemented("G7.2", "skill-traces check not yet implemented"))
```

**G7.AUDIT 汇总增强：** 单独计数 UNIMPLEMENTED，在审计报告中醒目显示（WARN 级别），提示维护者哪些检查是空壳。

**清单（逐个改）：**
| 门控 | 子检查 | 文件:行 |
|------|--------|---------|
| G7 | G7.2/7.3/7.4/7.8 | `g7.py:108-112` |
| G_DISPATCH | GD.2/GD.3 | `g_dispatch.py:67-69` |
| G_RECONCILE | GR.3/GR.4 | `g_reconcile.py:74-76` |
| G_TRANSITION | GT.2/GT.4/GT.5 | `g_transition.py:66-91` |
| G0 | G0.5 | `g0.py:237-238` |

**依赖链:** 无前置；独立。但需注意：改 UNIMPLEMENTED 后，依赖这些门控 PASS 的下游逻辑可能受影响——需逐个评估是否要把 UNIMPLEMENTED 当 PASS 处理（保持现有行为）还是当 WARN（更严格）。**建议：UNIMPLEMENTED 在门控链中按 PASS 处理（不阻断），但在 G7 审计报告中醒目告警。**

**验证:**
- grep 确认无 `"deferred"` + `PASS` 组合
- `shared.unimplemented()` 被调用
- G7.AUDIT 报告列出所有 UNIMPLEMENTED 项
- `just check` 全量通过（UNIMPLEMENTED 不阻断）

---

### Step P2.6: 文档漂移修正

**文件:** `docs/getting-started/first-novel.md:231-233`

**问题:** `first-novel.md:231-233` 自称："Automated orchestration (`next`/`resume`) is currently a placeholder; full generation logic arrives in a later wave."——**已过时**，`pipeline next/resume` 早已实现（`cli.py:582-751`）。

**修复:** 核实后更新或删除该 note。改为准确描述当前状态（orchestration 已实现，端到端验证待 P0.5）。

**依赖链:** 无前置；独立。建议在 P0.5 完成后同步更新（届时可引用真实运行作为示例）。

**验证:**
- 该 note 不再声称"placeholder"
- 文档与代码一致

---

## 7. Structure 6/7/8 合并深挖

### 7.1 孤儿 skill（Structure #6）

**问题:** 两个 skill 产出无人消费的产物：
- `shenbi-plot-thread-weaver` → `outline/thread_map.md`：仅 `sequel-writing` 读（非主流程），per-chapter pipeline 不读
- `shenbi-chapter-pattern` → `outline/chapter_patterns.md`：**无任何 skill 读**（仅 pacing-design 文本提及概念）

**方案（P1 级，二选一）：**

| 方案 | 做法 | 适用 |
|------|------|------|
| A. 接线 | 让 `chapter-planning`/`context-composing` 契约 `reads:` 声明消费这两个文件 | 若产物确实有用 |
| B. 标注 | SKILL.md 显式标注 "advisory skill, 产物非主流程必需，用于人工参考" | 若产物确属辅助 |

**建议：** `thread_map.md` 接线（让 chapter-planning 读取，用于跨章节线索连贯）；`chapter_patterns.md` 标注 advisory（模式检测本是 advisory 性质）。

**验证（方案 A）：** chapter-planning 的 contract.reads 含 thread_map.md；dispatcher 实际传入该文件内容。

### 7.2 死常量 + legacy 伪标注（Structure #7 + #8）

**合并为 P2.3 + P2.4**（见上文）。本质是"单一真相源"原则被破坏。

**系统化预防：引入"单一源审计" CI 检查**

```python
# tools/check_single_source.py（新建）
"""CI 检查：所有 import 必须对应 export，所有 export 必须有 import。
消灭死代码（定义了不用）和悬空引用（用了未定义）。
"""
import ast, pathlib

def check_module(py_file):
    tree = ast.parse(py_file.read_text())
    # 收集所有 __all__ / public def / class
    # 收集所有 import
    # 报告：exported but never imported（外部）= 死代码
    # 报告：imported but not exported = 悬空
```

加入 `just check` 或 pre-commit。

**验证：** CI 报告 0 死常量、0 悬空 import。

---

## 8. 验收标准

### 8.1 P0 验收（阻断修复）

- [ ] `shenbi-phase start` 不再 FileNotFoundError（P0.1）
- [ ] codex 模式 dispatch 不因 `shenbi-progress` 失败（P0.2）
- [ ] `pipeline --help` 不显示 rollback（P0.3）
- [ ] 无代码路径可达 `codex_api`（P0.4）
- [ ] **`novel-output/xinghuo-ranqiong/` 含完整可审计产物**（P0.5）
- [ ] `just check` 全量通过

### 8.2 P1 验收（工程实践）

- [ ] internal 模式评分被硬拒绝（P1.2）
- [ ] API 路径输出解析 0 regex（P1.3）
- [ ] 429 自动重试 3 次（P1.4）
- [ ] 长章节流式产出（P1.5）
- [ ] 不同 skill 用不同温度（P1.6）
- [ ] `tests/golden/` 含 ≥10 章人工评分（P1.8）
- [ ] 两 CLI help 有显式用途标注（P1.9）

### 8.3 P2 验收（一致性）

- [ ] 零宽/全半角 field 匹配通过（P2.1）
- [ ] `severity: "medium"` 合法（P2.2）
- [ ] `classify` 用 TEST_PASS（P2.3）
- [ ] legacy.py docstring 准确（P2.4）
- [ ] 无 `"deferred"` + `PASS` 组合（P2.5）
- [ ] `first-novel.md` 无过时 placeholder 声明（P2.6）

### 8.4 最终验收（里程碑）

- [ ] 端到端跑通 outline-example.md，产出完整小说
- [ ] 全量 `just check` 通过
- [ ] `novel-output/` 产物已提交（可审计）
- [ ] README 链接到真实运行作为验证证据
- [ ] 评分独立性有测试覆盖

---

## 9. 超出范围（Out of Scope）

以下不在本 Spec 范围，留作独立后续任务：

- **可观测性（原 P1.1）——留作未来独立 spec。** 涉及基于现有 `trace/` hash 链签名机制扩展 latency/token/cost 字段（必须纳入 `_SIGNED_FIELDS` + bump `schema_version` + 写 v1→v2 迁移），以及 `pipeline cost` CLI 子命令。因需尊重签名链完整性设计（非简单加字段），单独成 spec 以充分论证迁移策略。本 Spec 的 API 后端决策（§3）已为此铺路——API response 的 `usage` 字段是 token 数据来源。
- **成本预算强制（原 P1.7）——留作未来独立 spec。** 依赖可观测性的 token 追踪落地。涉及 `novel.json.budget_usd` + `PipelineState.spent_usd` 累计 + 超额 ESCALATION。P0.5 端到端运行期间以手动监控用量替代。
- **README Detailed Workflow Chart 增补**（mermaid 图 + 表）——独立文档任务
- **持久化任务队列**（Celery/Temporal）——P1 的 `pipeline-state.json` + filelock 已够用，若未来需分布式再引入
- **prompt 版本化 / A-B 测试**——需独立设计，依赖 P1.8 的 golden set
- **多模型 ensemble**——执行后端决策（§3）已支持按 skill 配置模型，ensemble 是进一步增强

---

## 10. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| P0.5 端到端跑不通（API/模型问题） | 中 | 高 | 先跑 5 章金丝雀；resumable；记录失败点迭代修复 |
| P0.5 成本超预期 | 中 | 中 | 金丝雀先验证用量；手动监控；可选 cheaper 模型跑草稿（成本预算强制留作未来 spec，见 §9） |
| P1.3 结构化输出模型不支持 JSON mode | 低 | 中 | DeepSeek/OpenAI 均支持；不支持则回退 regex + 严格校验 |
| P1.8 golden set 人工评分耗时 | 高 | 低 | 渐进建立（先 5 章，逐步扩到 20）；可邀请外部评审 |
| P2.5 UNIMPLEMENTED 破坏下游 | 低 | 中 | UNIMPLEMENTED 在门控链按 PASS 处理，仅审计告警 |

---

> **本 Spec 是活文档。** 实施过程中若发现新的根因或更优方案，应更新本 Spec 并记录决策。每个 Step 完成后勾选对应验收项。
