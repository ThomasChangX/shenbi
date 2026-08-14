# PR #20 处置：torch 2.12.1→2.13.0 superseded PR 的归档与依赖治理

> **Date:** 2026-08-02
> **Status:** Design（待批准）
> **Severity:** 🟡 Medium（僵尸 PR 不阻塞开发，但掩盖依赖状态 + 仓库卫生）
> **方法:** `systematic-debugging` skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **关联:** PR #20（Dependabot，OPEN）；`uv.lock`；`pyproject.toml` `[project.optional-dependencies].embeddings`
> **Predecessors:** PR #18（`4e59f97`，a10a15d 的 parent）；commit `13814f6`（feat: pipeline & gate improvements，torch 2.13 随其入 main）

---

## 1. 背景与根因

### 1.1 现象

PR #20 是 Dependabot 开的 `chore(deps): bump torch from 2.12.1 to 2.13.0`，单 commit `a10a15d`（parent = `4e59f97` / PR #18），状态 **OPEN + MERGEABLE**。但 `origin/main` 的 `uv.lock` **已经是 torch 2.13.0**——PR 的 diff（2.12.1→2.13.0）与 main 现状不符。

### 1.2 根因（机制）

Dependabot commit `a10a15d` **已经进入 main**，但**不是通过 PR #20 合并**。`git log --ancestry-path a10a15d..origin/main` 为空，说明 a10a15d 是通过非 merge 路径（fast-forward 或被后续 squash/合并提交吸收）进了 main——最可能是 commit `13814f6`（feat: pipeline & gate improvements）在合入时把 Dependabot 已存在的 `a10a15d` 一并带入。

**结果**：PR #20 的内容（torch 2.13）已 100% 落在 main，但 PR 本身未被 GitHub 识别为"已合并"（因为 a10a15d 不是通过 PR #20 的 merge button 合的）。这是 Dependabot PR 的典型僵尸态——**superseded but not closed**。

### 1.3 torch 在本项目的位置（已核实）

| 维度 | 状态 |
|------|------|
| torch 是否直接依赖 | ❌ 否（`pyproject.toml` core `dependencies` 无 torch，注释明确"避免 core install 拉入 torch/CUDA"）|
| torch 的来源 | `sentence-transformers 5.6.0` 的传递依赖 |
| sentence-transformers 声明位置 | `[project.optional-dependencies].embeddings = ["sentence-transformers>=3.0.0"]`（可选 extra，非 core，非 PEP 735 dep group）|
| src/ 业务代码 import torch | ❌ 0 处 |
| src/ 用 sentence-transformers | ✅ 3 处（`truth_embed.py`、`genesis.py`、`context_assemble.py`）——**全部 `importlib` 动态加载**（软依赖，未装则 no-op） |
| tests/ 用 torch/sentence-transformers | ❌ 0 处 |
| torch 已知漏洞（pip-audit） | ❌ 无（`uv run pip-audit | grep torch` 空） |

**结论**：torch 是 embeddings 可选能力的深传递依赖，core 运行时完全不碰它。

---

## 2. PR #20 处置选项分析

### 2.1 选项 A（推荐）：关闭 PR #20 + Dependabot 配置治理

**动作**：
1. `gh pr close 20` —— 关闭僵尸 PR（内容已在 main，合并无意义且会制造空 merge）。
2. PR 关闭评论注明：torch 2.13.0 已通过 `13814f6` 入 main（commit `a10a15d`），PR #20 superseded。
3. **Dependabot 配置审查**：检查 `.github/dependabot.yml` 是否对 `uv` ecosystem 配了 `open-transitive-dependency-PRs: false`（或等效）——torch 是 transitive，理想情况下 Dependabot 应对纯 transitive bump 谨慎（它们常被父包的新版连带解决）。

**理由**：合并一个内容已 100% 在 main 的 PR 是空操作（或制造 conflict）；关闭 + 记录是诚实的处置。

**代价**：无。torch 2.13 已在 main，业务不受影响。

### 2.2 选项 B：合并 PR #20（不推荐）

**动作**：`gh pr merge 20 --merge`。

**问题**：由于 main 已含 a10a15d，merge 会产生一个**空 diff 的合并提交**（或 GitHub 直接拒绝因 "already merged"）。即便成功，也是噪声 commit + 误导后人（以为 torch 升级走了 PR #20）。**违反"诚实处置"原则**。

### 2.3 选项 C：审查 torch 2.13.0 兼容性 + 跟踪 regression（独立 follow-up）

**动作**：torch 2.13.0 release notes 记录了 **tracked regression**：
- ROCm wheel 在 CPU-only 环境破 `torch.compile`（`RuntimeError: Can't detect vectorized ISA for CPU`）——但本项目用 `SentenceTransformer("bge-large-zh")` 推理，不用 `torch.compile`，且 macOS/CI 无 ROCm wheel，**不影响**。
- 移除 cp313t (free-threaded 3.13) wheels——本项目用 3.11/3.12，**不影响**。

**裁决**：2.13.0 regression 与本项目无关（不用 compile、无 ROCm、非 free-threaded）。但 sentence-transformers 5.6.0 对 torch 2.13 的兼容性**未被 CI 覆盖**（embeddings 是可选 extra，CI 的 `--group dev` 不装它）——这是**真实缺口**，但属 follow-up，非 PR #20 处置的前置。

**推荐**：选项 A 为主；选项 C 的"embeddings 可选组 CI 覆盖"开 follow-up issue（见 §4）。

---

## 3. 验证证据（2026-08-02 实测）

| 断言 | 命令 | 结果 |
|------|------|------|
| main uv.lock 已是 torch 2.13.0 | `grep -A1 '^name = "torch"' uv.lock` | `version = "2.13.0"` ✅ |
| PR #20 diff 是 2.12.1→2.13.0 | `gh pr diff 20 \| grep version` | `-2.12.1 / +2.13.0` ✅ |
| a10a15d 已在 main | `git log --ancestry-path a10a15d..origin/main` | 空（已吸收）✅ |
| a10a15d = PR #20 唯一 commit | `gh pr view 20 --json commits` | 1 commit, oid=a10a15d ✅ |
| a10a15d parent = PR #18 | `git log a10a15d^ -1` | `4e59f97 ci: optimize PR CI (#18)` ✅ |
| src/ 零 import torch | `grep -rl "import torch" src/` | 0 ✅ |
| sentence-transformers 动态加载 | `grep -rn "importlib.import_module.\"sentence_transformers\"" src/` | 3 处 ✅ |
| torch 无 pip-audit 漏洞 | `uv run pip-audit \| grep torch` | 空 ✅ |

---

## 4. 实施计划

### Task 1：关闭 PR #20（选项 A）

**复杂度: leaf**

- `gh pr close 20 --comment "Closing as superseded: torch 2.13.0 already on main via commit a10a15d (absorbed into 13814f6). This PR's diff (2.12.1→2.13.0) reflects a stale base; main already has 2.13.0. Verified: src/ has zero torch imports (it's a transitive dep of optional sentence-transformers). No action needed."`
- **验证**：`gh pr view 20 --json state` → `CLOSED`

### Task 2：审查 Dependabot 配置（transitive deps 治理）

**复杂度: leaf**（若配置已合理则纯审查，无改动）

- 读 `.github/dependabot.yml`，确认 `uv` ecosystem 的配置。
- 若 `open-transitive-dependency-PRs` 未显式设：评估是否应限制 Dependabot 对纯 transitive（如 torch，非 declared dep）开 PR。Dependabot 默认会对 lockfile 里任何可升的包开 PR，包括 transitive——这是 PR #20 出现的根因。
- **裁决标准**：若团队希望 Dependabot 只对 declared deps 开 PR，加 `allow.dependency-type: ["direct"]`；若希望保留 transitive PR 用于安全追踪，维持现状但建立"僵尸 PR 定期清理"流程。
- **本 spec 不强推改动**——这是策略偏好，记 finding 供决策。

### Task 3（follow-up，非本 spec scope）：embeddings 可选组 CI 覆盖

开 issue：
- **现象**：sentence-transformers + torch 是可选 extra，CI 的 `--group dev` 不装它，故 torch/sentence-transformers 升级的兼容性**未被 CI 验证**。
- **风险**：torch 大版本（如未来 3.0）若破 sentence-transformers，动态 `importlib.import_module` 会在运行时（非 CI）才 ImportError。
- **建议**：加一个 nightly/weekly job 用 `--extra embeddings` 装可选组跑 `import sentence_transformers` smoke test。非阻塞，开 issue 跟踪。

---

## 5. 验证标准（Pass criteria）

| 判据 | 阈值 | 验证 |
|------|------|------|
| PR #20 状态 | CLOSED | `gh pr view 20 --json state` |
| main torch 版本 | 2.13.0（保持，不动） | `grep -A1 '^name = "torch"' uv.lock` |
| `just check` | 2787 passed（基线保持） | `just check`（本 spec 不改代码，应无变化）|

---

## 6. 范围纪律

本 spec 只做"PR #20 处置 + Dependabot 配置审查"。**不**做：
- 不改 torch 版本（已在 main 2.13.0，正确状态）
- 不改 `pyproject.toml` 依赖声明（embeddings 可选 extra 的设计是对的）
- 不重构 sentence-transformers 动态加载（软依赖模式是 intentional）
- 不实施 Task 3 follow-up（开 issue 即可，CI 覆盖另案）

---

## 7. 对应 plan

本 spec 即 Design。批准后写 plan（Task 1 极简，可能 spec 即足够无需独立 plan；Task 2 视配置审查结果决定）。
