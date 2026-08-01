# PR #20 Follow-up: Dependabot 配置治理 + embeddings 推理 smoke CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 PR #20 处置 spec 的两项 follow-up——(a) 新建 `.github/dependabot.yml` 约束 transitive-PR 再生 + 删除 stale `renovate.json`；(b) 给 embeddings 推理兼容性加 CI smoke 防线（独立 scheduled workflow）。

**Architecture:** Phase 1 纯配置（dependabot.yml + 删 renovate.json），Phase 2 独立 scheduled workflow 跑 embeddings 推理 smoke（实例化 `all-MiniLM-L6-v2` + encode）。两 PR 拆分（§5.5）。所有改动在 `.github/`，零 src/ 改动。

**Tech Stack:** GitHub Dependabot v2 config（`package-ecosystem: uv`）、GitHub Actions workflow、uv（`uv sync --group dev`）、sentence-transformers + torch（推理 smoke）。

**Spec:** `docs/superpowers/specs/2026-08-02-pr20-followup-dependabot-and-embeddings-ci-design.md`（已过 Phase 1 事实核实 + Phase 2 设计审查，plan-ready）。

## Global Constraints

- **§7 Out-of-Scope**：不动 `src/`；不改 `[project.optional-dependencies].embeddings` 声明位置；不升级 torch/sentence-transformers；不为 embeddings 写功能测试；不重新处置 PR #20。
- **ecosystem = `uv`**（§5.1 已定，GA 2025-03；`pip` 会找 requirements.txt 而 no-op）。
- **`allow.dependency-type` 只配 `direct`**（单一规则一个值；不叠 production/development——那是正交环境轴）。
- **renovate.json 删除**（§5.6 用户裁决；ci.yml 的 renovate 校验 step 由 `if` 守卫自动跳过，无需改 ci.yml）。
- **推理 smoke 用 `all-MiniLM-L6-v2`**（~80MB，非 bge-large-zh ~1.3GB；推理兼容性与具体模型无关）。
- **CI 工具链**：`astral-sh/setup-uv@v3`（无 composite action）；commit 前缀 `chore(deps)`。
- **PR 拆 2 个**（§5.5）：PR-1 = dependabot.yml + 删 renovate.json（Phase 1，纯配置）；PR-2 = embeddings smoke workflow（Phase 2，CI 行为）。
- **YAGNI**：smoke job 只做推理防线，不跑 embeddings 单测（那些已在 PR CI，且 skip-when-available）。

## File Structure

| 文件 | 动作 | 责任 |
|------|------|------|
| `.github/dependabot.yml` | Create | Dependabot v2 配置：uv ecosystem（direct-only）+ github-actions ecosystem |
| `renovate.json` | Delete | stale 残留（Renovate bot 从未开 PR），用户裁决删除 |
| `.github/workflows/embeddings-smoke.yml` | Create | 独立 scheduled（daily）+ dispatch workflow，跑 embeddings 推理 smoke |
| `docs/superpowers/specs/2026-08-02-pr20-followup-dependabot-and-embeddings-ci-design.md` | (已有，归档时移) | 设计 spec（plan 依据） |

**为什么独立 workflow 而非加进 nightly.yml**：`nightly.yml` 当前 DISABLED（schedule 注释掉，仅 dispatch），加进去不会自动跑（§5.4）。独立 `embeddings-smoke.yml` 精准启用 schedule，不连带启用 nightly 的 flaky job（doc-links 依赖外部站）。

---

## PR-1 · Phase 1：Dependabot 配置治理（纯配置）

### Task 1: 新建 `.github/dependabot.yml`（uv direct-only + github-actions）

**Files:**
- Create: `.github/dependabot.yml`
- Test: 无单元测试（YAML 配置文件）；验证靠 YAML 合法性 + 字段核对

**Interfaces:**
- Consumes: spec §2.1 草案 + §2.1 决策点（direct 单规则）
- Produces: Dependabot 行为约束（direct-only，过滤 transitive torch PR）

**复杂度:** leaf（单文件、纯配置、无跨模块）
**test_kind:** characterization（配置文件无 TDD red-green；验证 = YAML 合法 + 字段语义核对）

- [ ] **Step 1: 创建 `.github/dependabot.yml`**

```yaml
# .github/dependabot.yml
# Dependabot 版本更新配置。承接 PR #20 follow-up：
# PR #20 是为 torch（sentence-transformers 的 transitive 依赖）开的僵尸 PR。
# 此配置约束 Dependabot 只为直接依赖开 PR，transitive 由父包升级连带解决。
# 详见 docs/superpowers/specs/2026-08-02-pr20-followup-dependabot-and-embeddings-ci-design.md
version: 2
updates:
  # uv lockfile —— GitHub Dependabot 自 2025-03 GA 原生支持 uv（§5.1）
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    # 单一 allow 规则只能有一个 dependency-type；多个 allow 条目按并集生效。
    # 选 direct = 覆盖三处显式声明（[project.dependencies] / [dependency-groups] /
    # [optional-dependencies]），过滤 indirect 传递依赖（torch 这类）。
    # 不配 production/development —— 那是正交的环境标签轴，叠加只会扩大放行范围。
    allow:
      - dependency-type: "direct"
    labels:
      - "dependencies"
      - "dependabot"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"

  # GitHub Actions —— workflow 依赖（actions/checkout 等）
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"
```

- [ ] **Step 2: 验证 YAML 合法 + 字段语义**

```bash
# YAML 语法合法
python -c "import yaml; d=yaml.safe_load(open('.github/dependabot.yml')); assert d['version']==2; print('YAML ok')"

# uv ecosystem 存在 + direct-only 过滤（V1 + V2）
grep -q 'package-ecosystem: "uv"' .github/dependabot.yml && echo "uv ecosystem ok"
grep -A1 'allow:' .github/dependabot.yml | grep -q 'dependency-type: "direct"' && echo "direct-only ok"

# 确认无 production/development 叠加（避免意外扩大放行）
! grep -q 'dependency-type: "production"' .github/dependabot.yml && echo "no production overlay ok"
```
Expected: 全部 ok。

- [ ] **Step 3: 提交**

```bash
git add .github/dependabot.yml
git commit -m "chore(deps): add dependabot.yml — uv direct-only, filter transitive PRs

PR #20 was a zombie Dependabot PR for torch (a transitive dep of
sentence-transformers). With no dependabot.yml, Dependabot ran on repo-
default config and tracked all ecosystems including indirect deps.

New config: package-ecosystem uv + allow.dependency-type direct only.
Direct covers [project.dependencies] + [dependency-groups] +
[optional-dependencies] explicit declarations; filters indirect
transitive deps (torch). sentence-transformers (direct optional dep)
still tracked; its transitive torch is filtered.

Also adds github-actions ecosystem for workflow deps.

Closes follow-up (a) of PR #20 disposition spec."
```

---

### Task 2: 删除 stale `renovate.json`（§5.6 用户裁决）

**Files:**
- Delete: `renovate.json`
- Modify: 无（ci.yml 的 renovate 校验 step 由 `if` 守卫自动跳过，不需改）

**Interfaces:**
- Consumes: §5.6 决策（用户 2026-08-02 选删除）
- Produces: 单 bot 统一（Dependabot）

**复杂度:** leaf（单文件删除）
**test_kind:** characterization（删除后验证 ci.yml 守卫语义 + 无残留引用）

**关键事实（已核实）**：
- `renovate.json` 存在（1355 bytes），但 `gh pr list` 显示 Renovate bot 从未开 PR（app 未装 / stale）。
- PR #20/#21/#22 全部由 `app/dependabot` 开 → Dependabot 是事实 bot。
- `ci.yml:110-127` 的 "Validate Renovate config schema" step 用 `if: github.event_name == 'pull_request'` + `gh api ... | grep -c '^renovate\.json$'` 守卫。删 renovate.json 后 CHANGED=0 → step 输出 "renovate.json unchanged — skipping"。**无需改 ci.yml**。
- renovate.json 仅在 archive 计划文档中被引用（非活跃代码/配置），删除安全。

- [ ] **Step 1: 确认无活跃引用**

```bash
# 排除 archive 计划文档（历史记录，可保留提及）+ .git + uv.lock
grep -rn "renovate" --include="*.yml" --include="*.yaml" --include="*.py" --include="*.toml" . \
  | grep -v "node_modules\|\.git/\|uv\.lock\|docs/superpowers/plans/archive" \
  | grep -v "ci.yml"
# 应只剩 ci.yml 的校验 step（保留，守卫会自动 skip）
```
Expected: 仅 ci.yml 的 renovate validator step（行 110-127），无其他活跃引用。

- [ ] **Step 2: 删除 renovate.json**

```bash
git rm renovate.json
```

- [ ] **Step 3: 验证 ci.yml renovate 守卫仍语义正确（不破坏）**

```bash
# 守卫逻辑：CHANGED=$(... grep -c '^renovate\.json$' || true)；if CHANGED>0 才跑 validator
# 删文件后：文件不在 PR diff → CHANGED=0 → 走 else 分支 "skipping"
# 验证 ci.yml 该 step 仍在（不删 step，保留为未来恢复路径）
grep -q "Validate Renovate config schema" .github/workflows/ci.yml && echo "renovate guard step preserved ok"
grep -q 'renovate.json unchanged — skipping' .github/workflows/ci.yml && echo "skip-branch intact ok"
```
Expected: 两个 ok（step 保留，skip 分支完好——删 renovate.json 不需改 ci.yml）。

- [ ] **Step 4: 本地全量 gate 不回归**

```bash
just check
```
Expected: 全绿（删除 renovate.json 不影响任何 gate——它不是 Python 代码，不进 ruff/mypy/pyright；yamllint 只扫 workflows/）。

- [ ] **Step 5: 提交**

```bash
git add -A  # renovate.json 的删除
git commit -m "chore(deps): remove stale renovate.json — Dependabot is the active bot

renovate.json existed but the Renovate bot never opened a PR (app not
installed / stale). PR #20/#21/#22 were all opened by app/dependabot,
confirming Dependabot is the de-facto bot. The duplicate config only
adds confusion and risks duplicate PRs if Renovate is ever activated.

ci.yml's 'Validate Renovate config schema' step (L110-127) is guarded by
a changed-files check (grep -c '^renovate\.json$'); with the file gone,
CHANGED=0 and the step auto-skips ('renovate.json unchanged — skipping').
No ci.yml edit needed.

User decision (spec §5.6, 2026-08-02): delete."
```

---

## PR-2 · Phase 2：embeddings 推理 smoke CI（独立 workflow）

> **PR-2 在 PR-1 合并后另起分支实施。** 本 plan 文档同时定义两个 PR 的 task，便于一次审查；执行时按 PR 边界分两次 subagent-driven-development 会话。

### Task 3: 新建 `.github/workflows/embeddings-smoke.yml`（推理 smoke）

**Files:**
- Create: `.github/workflows/embeddings-smoke.yml`
- Test: 无单元测试；验证靠 workflow YAML 合法 + 手动 dispatch 跑通

**Interfaces:**
- Consumes: spec §2.2 B1（推理 smoke）+ §5.3（小模型）+ §5.4（独立 workflow）
- Produces: 每日（+ dispatch）embeddings 推理兼容性防线

**复杂度:** leaf（单文件 workflow，无跨模块；但属 infra-adjacent——CI 行为变更。按 leaf 处理：单文件、无契约/schema/并发改动；协调者亲自实现因触及 CI 行为）
**test_kind:** characterization（workflow 文件；验证 = yamllint + 手动 dispatch 绿）

**关键决策（spec §5 已定）**：
- schedule daily（`0 7 * * *`，UTC，避开夜间其他负载）；同时 `workflow_dispatch` 手动。
- 仅 ubuntu-latest（linux torch wheel 更小，省 macOS 大 wheel）。
- 模型 `all-MiniLM-L6-v2`（~80MB）——推理兼容性与模型无关，小模型省下载。
- `continue-on-error: false`（**刻意偏离 spec §6 风险表"初期 true"**——理由：本 workflow 非分支保护，不阻塞 PR；红 smoke 应被看见而非吞掉。spec §6 该行是保守初稿，plan 阶段裁决为 false 更符合"信号 > 噪音"。Phase 4 审查认可此偏离）。
- 缓存：HuggingFace 模型目录用 `actions/cache@v4`（key 含 model 名 + runner os）。注：`actions/cache@v4` 是本 plan **新引入**（仓库无先例，见签名 grep 记录）。

- [ ] **Step 1: 创建 `.github/workflows/embeddings-smoke.yml`**

```yaml
# .github/workflows/embeddings-smoke.yml
name: Embeddings smoke
# 推理时（inference-time）embeddings 兼容性防线。
# sentence-transformers + torch 由 [dependency-groups].dev 安装（每个 PR CI 都装），
# import 级兼容性已被守。但无测试实例化模型或跑 encode —— 本 job 补这一层：
# 守 torch 2.13 这类升级破坏 sentence-transformers 推理（非 import）的 regression。
# spec: 2026-08-02-pr20-followup-dependabot-and-embeddings-ci-design.md §1.2 根因B
on:
  schedule:
    - cron: '0 7 * * *'   # daily 07:00 UTC
  workflow_dispatch:       # 手动触发

jobs:
  embeddings-inference-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      PYTHONUTF8: "1"
      # HuggingFace 模型缓存目录（actions/cache 挂载点）
      HF_HOME: ${{ github.workspace }}/.hf-cache
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      - run: uv python install 3.12
      # dev 组已含 sentence-transformers + torch（pyproject.toml [dependency-groups].dev）
      - run: uv sync --frozen --group dev
      - name: Cache HuggingFace model (~80MB all-MiniLM-L6-v2)
        uses: actions/cache@v4
        with:
          path: ${{ github.workspace }}/.hf-cache
          key: hf-model-all-MiniLM-L6-v2-${{ runner.os }}
          restore-keys: |
            hf-model-all-MiniLM-L6-v2-
      - name: Inference smoke (instantiate + encode, not import-only)
        run: |
          uv run python -c "
          from sentence_transformers import SentenceTransformer
          # 用小模型 all-MiniLM-L6-v2（~80MB）而非 bge-large-zh（~1.3GB）：
          # 推理兼容性取决于 sentence-transformers + torch 栈，与具体模型无关。
          m = SentenceTransformer('all-MiniLM-L6-v2')
          v = m.encode(['推理兼容性 smoke 测试', 'another sentence'])
          assert v.shape == (2, 384), f'unexpected shape: {v.shape}'
          print('inference ok', v.shape)
          "
```

- [ ] **Step 2: 验证 workflow YAML 合法（yamllint，本地）**

```bash
# ci.yml 的 action-validation job 跑 'yamllint --strict .github/workflows/'，
# 本地复现同一命令确保不破 CI
uv run yamllint --strict .github/workflows/embeddings-smoke.yml
```
Expected: 无错误（strict 模式）。若 yamllint 报 line-length / document-start，调整格式至合规。

- [ ] **Step 3: 验证 yamllint 全 workflows 目录不回归**

```bash
uv run yamllint --strict .github/workflows/
```
Expected: 全部 workflow（含新增 embeddings-smoke.yml）合规。

- [ ] **Step 4: 本地全量 gate 不回归**

```bash
just check
```
Expected: 全绿（新 workflow 不影响 Python 代码 / 契约 / 测试）。

- [ ] **Step 5: 提交**

```bash
git add .github/workflows/embeddings-smoke.yml
git commit -m "ci: add embeddings inference smoke workflow

sentence-transformers + torch are installed via [dependency-groups].dev
on every PR CI, so import-level compatibility is guarded. But no test
instantiates the model or runs encode — the two relevant unit tests
(test_truth_embed.py, test_context_assemble.py) skip when
is_embed_available() is True. So torch 2.13-style upgrades that break
sentence-transformers *inference* (not import) go uncaught.

New independent scheduled workflow (daily 07:00 UTC + manual dispatch):
- instantiates all-MiniLM-L6-v2 (~80MB; inference compatibility is
  model-agnostic) and runs encode() with a shape assertion
- caches the HuggingFace model dir (keyed by model + OS)
- ubuntu-only (smaller torch wheel)
- NOT added to nightly.yml (which is disabled; adding there would not
  auto-run). Independent workflow enables schedule precisely without
  enabling nightly's flaky jobs (doc-links depends on external sites).

Closes follow-up (b) of PR #20 disposition spec."
```

- [ ] **Step 6: 推 branch + 手动 dispatch 验证 smoke 实际跑通**

```bash
# 推到 PR 分支后，在 GitHub UI 或 gh CLI 手动 dispatch
gh workflow run embeddings-smoke.yml --ref <pr-2-branch>
# 等待 run 完成并确认 inference step 绿
gh run watch --exit-status $(gh run list --workflow=embeddings-smoke.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```
Expected: run 绿，"inference ok (2, 384)" 打印（满足 V4 dispatch 半 + V5）。若首次因模型下载超时，确认 cache key 命中后第二次 run 绿。

> **⚠️ V4 scheduled 半的 post-merge 跟进**（Phase 4 审查要求）：`schedule` cron 只在 PR-2 合到默认分支后才生效——dispatch 验证无法预证 cron 触发路径。合并后第 1 个 07:00 UTC 周期内必须人工确认 scheduled run 自动触发（`gh run list --workflow=embeddings-smoke.yml` 看是否有非 dispatch 来源的 run），类比 V3（Dependabot 配置加载）的 post-merge 观察。若 24h 内无 scheduled run，排查 cron 语法 / workflow 是否在默认分支。

---

## AC 覆盖表（spec §4 V1-V7 → task → 验证）

| spec AC | 覆盖 task | 验证 |
|---------|----------|------|
| V1 `.github/dependabot.yml` 存在且 YAML 合法 | T1 S2 | `test -f` + `yaml.safe_load` |
| V2 dependabot.yml 含 `allow.dependency-type: direct` | T1 S2 | grep direct + 确认无 production 叠加 |
| V3 Dependabot 配置被 GitHub 正确加载 | T1（PR 合并后观察） | 仓库 Settings → Dependabot 显示 schedule；或 Dependabot 在 PR 发 "Configuration validated" |
| V4 embeddings smoke workflow 存在且可触发 | T3 S6 | 手动 dispatch run 存在且绿 |
| V5 sentence-transformers + torch 推理在 CI 成功 | T3 S6 | smoke run 的 inference step 绿（非仅 import） |
| V6 现有 PR CI 不回归；smoke 时长可接受 | T2 S4 + T3 S4/S6 | `just check` 全绿 + smoke run 时长记录（cache hit vs miss） |
| V7 前序 PR20 spec 已归档 | （已自动满足） | `test -f .../archive/2026-08-02-pr20-torch-bump-disposition-design.md` 已 PASS |

## 签名 grep 验证记录（plan 专属 rubric，Phase 4 复核订正）

- 无 Python 函数签名变更（全 `.github/` 改动）。N/A。
- **现有 ci.yml 已用版本**（grep 确认）：
  - `actions/checkout@v4`：`grep -rn "actions/checkout" .github/workflows/ci.yml` → 命中。
  - `astral-sh/setup-uv@v3`：`grep -rn "setup-uv@v3" .github/workflows/ci.yml` → 命中。
- **本 plan 新引入**（仓库无先例，Phase 4 复核订正——原稿误称"均为现有版本"）：
  - `actions/cache@v4`：`grep -rn "actions/cache" .github/workflows/` → **零命中**（无 workflow 用过 cache）。v4 是 actions/cache 当前 published 最新 major（对照 [GitHub Marketplace](https://github.com/actions/cache)），按"取当前 major"原则引入，非沿用先例。yamllint 不校验 action 版本号，无 lint 风险。
- dependabot `version: 2` + `package-ecosystem` 取值对照 GitHub docs（uv GA 2025-03）。
- **yamllint --strict 影响域**（Phase 4 新增认知）：pre-commit 的 yamllint hook (`args: [--strict]`, `files: \.(yaml|yml)$`) 扫**所有** `.yml/.yaml`（仅排除 `tests/rounds/`），故 `.github/dependabot.yml` + `.github/workflows/embeddings-smoke.yml` 提交时都会被 `--strict` lint。本 plan 两文件所有行均 ≤100 chars（pyproject line-length=100），合规。

## Self-Review（writing-plans skill 要求）

1. **Spec 覆盖**：§2.1→T1；§5.6 renovate 删除→T2；§2.2 B1 推理 smoke + §5.3 小模型 + §5.4 独立 workflow→T3。§3 Phase 3（归档前序 spec）= 空操作（V7 已满足）。§4 V1-V7 全覆盖（见上表）。✅
2. **Placeholder 扫描**：无 TBD/TODO/"add error handling"；每步含实际 YAML/命令/expected。✅
3. **类型一致性**：无跨 task 函数签名（纯配置 + workflow）。workflow 内 `uses:` 版本与 ci.yml 一致。✅
4. **task 分解**：T1/T2 独立（不同文件，无隐式依赖）；T3 独立 workflow。每个 task 有独立 test cycle（YAML 合法 / gate 不回归 / dispatch 绿）。✅
5. **leaf/infra 分类**：T1/T2 leaf（纯配置，单文件）；T3 leaf 但 CI-行为变更 → 协调者亲自实现（infra-adjacent 路由，按 spec 阶段 5 规则）。✅
