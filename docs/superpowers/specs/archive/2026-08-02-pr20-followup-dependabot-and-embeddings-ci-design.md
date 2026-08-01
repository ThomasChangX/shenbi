# PR #20 Follow-up：Dependabot 配置治理 + embeddings 可选组 CI 覆盖

> **Date:** 2026-08-02
> **Series:** 依赖治理（承接 `2026-08-02-pr20-torch-bump-disposition-design.md` §2.1/§2.3 follow-up）
> **Depends on:** PR #20（已 CLOSED）；前序 spec `2026-08-02-pr20-torch-bump-disposition-design.md`（主任务已完成，本 spec 接管其遗留的两项 follow-up）
> **Status:** 设计中（Design）
> **Severity:** 🟡 Medium（根因未修 → 僵尸 PR 会再生；embeddings 推理时零 CI 覆盖 → 兼容性回归无防线）
> **目的:** 落地 PR #20 处置 spec 的两项 follow-up：(a) 新建 `.github/dependabot.yml` 约束 transitive-PR；(b) 给 embeddings 可选组加 CI 覆盖。闭合后前序 spec 方可干净归档。

---

## 1. 背景

### 1.1 来由

PR #20（`chore(deps): bump torch from 2.12.1 to 2.13.0`）是 Dependabot 开的 **transitive 依赖 PR**——torch 不是本项目直接依赖，而是 `sentence-transformers`（`[project.optional-dependencies].embeddings`）的传递依赖。该 PR 形成僵尸态（commit 通过非 merge 路径入 main，PR 未自关），已于 2026-08-01 手动关闭。

前序 spec（`2026-08-02-pr20-torch-bump-disposition-design.md`）处置 PR #20 时明确留了两项 follow-up（§2.1 动作 3 + §2.3 推荐），**但二者均无独立 spec/issue 追踪**（已核实：archive 零命中，`gh issue list` 零命中）。本 spec 承接这两项，使其有独立追踪，闭合后前序 spec 方可归档。

### 1.2 根因（已实测核实，2026-08-02）

**根因 A（僵尸 PR 再生机制）**：`.github/dependabot.yml` **不存在**（`find . -name "dependabot*"` 零命中，`.github/` 下无该文件）。Dependabot 因此以**仓库级默认配置**运行——GitHub 自动为所有 ecosystem（含 `uv`/pip）开 PR，**不区分 direct 还是 transitive 依赖**。torch 作为 sentence-transformers 的传递依赖，照样触发 PR。无配置约束 = 僵尸 PR 会再生（每次 torch/sentence-transformers 升级都可能复现 PR #20 模式）。

**根因 B（embeddings 推理时零 CI 覆盖）**：⚠️ **本节经阶段 2 设计审查复核后重述**（原表述"零 CI 覆盖"不实）。

事实更正：`sentence-transformers>=3.0.0` **同时在** `[dependency-groups].dev`（`pyproject.toml:47`）与 `[project.optional-dependencies].embeddings`（`pyproject.toml:23`）两处声明。`uv.lock` 第 3610 行解析了 `torch`，第 3345/3368 行把 sentence-transformers 列为 dev 组成员。因此 `uv sync --frozen --group dev`（所有 CI job 用的命令）**已经安装** sentence-transformers + torch，import 级兼容性在每个 PR CI 上已被守。

**真正的缺口（narrower gap）是推理时（inference-time）兼容性**：
- `tests/unit/pipeline/test_truth_embed.py:119-127` 与 `tests/unit/pipeline/test_context_assemble.py:164-167` 触及 `embed_and_store`/降级路径，但二者都在 `is_embed_available()` 为 True 时 `pytest.skip`（"sentence_transformers installed; degradation path not testable"）。
- **没有任何测试实例化 `SentenceTransformer('bge-large-zh')` 或调用 `model.encode()`**。import 通 ≠ 推理通。
- 后果：torch 2.13.0 这类升级若破坏 sentence-transformers 的**模型加载/推理**（非 import），CI 全绿却实际 embeddings 功能已坏——无人守这一层。

结论：Follow-up (b) 的 CI 覆盖目标是**推理 smoke**（实例化模型 + 一次 encode），而非 import（已被覆盖）。

---

## 2. 修复方案

### 2.1 Follow-up (a)：新建 `.github/dependabot.yml`

Dependabot 配置文件当前**不存在**。新建，约束 `uv` ecosystem 行为。

#### 配置内容（草案，plan 阶段细化）

```yaml
# .github/dependabot.yml
version: 2
updates:
  # uv lockfile —— GA 支持的 ecosystem（见 §5.1 决策，已定为 "uv"）
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    # 关键：只为直接依赖开 PR，transitive 由父包升级连带解决
    # （torch 这类传递依赖不应单独开 PR，避免 PR #20 式僵尸态再生）
    # NOTE: 单一 allow 规则只能有一个 dependency-type；多个 allow 条目按并集生效。
    # 选 direct = 覆盖三处显式声明（[project.dependencies]/[dependency-groups]/
    # [optional-dependencies]），过滤 indirect 传递依赖。
    # 不配 production/development —— 那是正交的环境标签轴，叠加只会扩大放行范围。
    allow:
      - dependency-type: "direct"
    labels:
      - "dependencies"
      - "dependabot"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"

  # GitHub Actions —— workflow 依赖
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

#### 关键决策点（§5 决策）

1. **`allow.dependency-type: "direct"`** 是过滤 transitive 的关键。GitHub Dependabot 文档（已核实）：单一 `allow` 规则**只能有一个** `dependency-type`；多个 `allow` 条目按**并集**生效（匹配任一即放行）。选 `direct`（覆盖 `[project.dependencies]` + `[dependency-groups]` + `[optional-dependencies]` 三处显式声明）即过滤掉 indirect 传递依赖。无需第二规则——`production`/`development` 是正交的**环境标签**轴，与"是否过滤 transitive"无关，叠加只会**扩大**而非精确化过滤。
   - `[project.optional-dependencies].embeddings` 的 `sentence-transformers` 是 direct（显式可选依赖）→ 仍被跟踪（期望：想升级它）。其传递依赖 `torch` 是 indirect → 被过滤（PR #20 根因修复）。
2. **ecosystem 名**：**已定 `uv`**（§5.1 在 spec 内解决，GA 2025-03 支持；不再延后到 plan）。
3. **`schedule.interval`**：weekly（与基线 CI 节奏匹配）。
4. **`open-pull-requests-limit: 5`**：避免 PR 积压。

#### 验证标准

- 文件存在：`test -f .github/dependabot.yml`。
- YAML 合法：`python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`（或 actionlint / yamllint）。
- **行为验证**：下次 Dependabot 运行后，不再为 torch 这类 transitive 依赖单独开 PR（观察 1-2 个周期）。
- **回归保护**：仍能为 `pyproject.toml` 直接声明的依赖（openai、tenacity、sentence-transformers、pytest 等）开 PR。

### 2.2 Follow-up (b)：embeddings 推理 smoke CI 覆盖

#### 缺口（经阶段 2 复核修正）

`--group dev` **已装** sentence-transformers + torch（见 §1.2 根因 B 修正）。缺口是**推理时**：无 CI 步骤实例化模型或跑 encode；现有 2 个相关单测在 `is_embed_available()` 为 True 时 skip。本 Follow-up 的 smoke 须做**推理**（实例化 + encode 一段 dummy 文本），而非仅 import。

> ⚠️ **nightly.yml 当前 DISABLED**（schedule 注释掉，仅 `workflow_dispatch` 手动触发，见 `nightly.yml:18-21`）。B1 落到 nightly.yml 意味着覆盖**不会自动执行**，除非 §5.4 决定重启 schedule 或另建独立 scheduled workflow。

#### 方案（三种选项，§5 决策）

**选项 B1（推荐，推理 smoke）**：在 `nightly.yml`（或新 scheduled workflow，§5.4）加 embeddings 推理 smoke job。
```yaml
embeddings-smoke:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v3        # 与现有 ci.yml/nightly.yml 一致（无 composite action）
      with:
        enable-cache: true
    # dev 组已含 sentence-transformers；--extra embeddings 冗余但无害（PEP 621 extra 与 group 正交）
    - run: uv sync --frozen --group dev
    - name: 推理 smoke（实例化 + encode，非仅 import）
      run: uv run python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2'); v = m.encode(['测试句子']); print('inference ok', v.shape)"
```
- **优点**：nightly 节奏（不拖慢 PR CI）；**真实推理**验证（实例化 + encode，守 torch 2.13 式 runtime regression，非仅 import）。
- **模型**：用 `all-MiniLM-L6-v2`（~80MB）而非 `bge-large-zh`（~1.3GB）——推理兼容性与模型无关，小模型足够且 CI 时长友好（§5.3 决策）。
- **代价**：nightly 多一 job（装 torch ~2-3min + 模型 ~80MB 下载）。
- **风险**：torch wheel 体积（~200MB linux）；模型下载需缓存（§5.3）。

**选项 B2（PR CI 加矩阵项）**：在 `ci.yml` quality job 的 matrix 加一个推理 smoke 维度。
- **不推荐**：拖慢每个 PR 的 CI（torch 安装 + 模型下载）；与 PR #18 "矩阵收缩"决策冲突。

**选项 B3（security.yml 漏洞覆盖）**：⚠️ **经阶段 2 复核：冗余**。`--group dev` 已装 sentence-transformers + torch，`security.yml` 的 `pip-audit` **已经审计**它们（pip-audit 扫整个已装环境）。加 `--extra embeddings` 不增加覆盖。**除非**意图是"独立审计 embeddings extra 而非随 dev 组抖动"——若是，需显式说明且收益有限。**建议删除 B3**，Follow-up (b) 收敛为仅 B1。

#### 关键决策点（§5 决策）

1. **选 B1 / B2 / B3**：倾向 **仅 B1**（B3 经复核冗余，B2 违 PR #18）。
2. **模型下载策略**：见 §5.3（倾向小模型 `all-MiniLM-L6-v2` + 缓存）。
3. **nightly 重启决策**：见 §5.4（nightly.yml 当前 disabled，B1 不会自动跑）。

---

## 3. 实施阶段

### Phase 1：新建 `.github/dependabot.yml`（Follow-up a）

1. 创建 `.github/dependabot.yml`（§2.1 草案）。
2. plan 阶段核实 ecosystem 名（`uv` vs `pip`）+ GitHub Actions ecosystem 配置。
3. 验证 YAML 合法 + 推 branch 观察 Dependabot 是否正确加载配置（PR 上 Dependabot 会发 "Configuration validated" 评论，或 Dashboard 显示 schedule）。

### Phase 2：embeddings 推理 smoke CI 覆盖（Follow-up b，按 §5 决策）

1. plan 阶段前置调研（部分已在阶段 1/2 完成）：
   - `--group dev` 已装 sentence-transformers + torch（§1.2 修正），smoke 须做**推理**（实例化 + encode），非 import。
   - CI 无 composite action，用 `astral-sh/setup-uv@v3`；smoke job `uv sync --frozen --group dev` 即可（embeddings extra 冗余）。
   - 模型用 `all-MiniLM-L6-v2`（§5.3 选项 C）；torch wheel 体积对时长的影响实测记录（V6）。
2. 按 §5.4 决策（倾向独立 scheduled workflow）建 workflow + smoke job。
3. 推 branch，手动 dispatch 验证 smoke job 实际跑通（推理 step 绿）。

### Phase 3：归档前序 spec（⚠️ 已完成，本 Phase 为空操作）

前序 spec `2026-08-02-pr20-torch-bump-disposition-design.md` **已在 `archive/`**（截至本 spec 修订时核实）。本 Phase 不再做归档动作；INDEX 的 "承接 #1 已归档" 已正确反映此状态。本 spec 自身归档在阶段 11 进行。

---

## 4. 验证标准

| # | 标准 | 命令 / 证据 |
|---|---|---|
| V1 | `.github/dependabot.yml` 存在且 YAML 合法 | `test -f .github/dependabot.yml && python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"` |
| V2 | dependabot.yml 含 `allow.dependency-type: direct`（过滤 transitive） | `grep -A3 "allow:" .github/dependabot.yml` |
| V3 | Dependabot 配置被 GitHub 正确加载（无 config error） | 仓库 Settings → Dependabot 或 PR 评论确认 |
| V4 | embeddings smoke workflow 存在且可触发（scheduled 或 dispatch） | 新 workflow 文件存在 + 至少一次 run（手动 dispatch 触发）绿 |
| V5 | sentence-transformers + torch **推理**（实例化 + encode）在 CI 成功 | smoke job 的 `SentenceTransformer(...).encode(...)` step 绿（非仅 import） |
| V6 | 现有 PR CI 不回归；新 smoke job 时长可接受 | `just check` 全绿；smoke job 时长在 Phase 2 实测后记录（缓存命中 vs miss 分别报数），无硬阈值（原 < +5min 不可客观核验，已删） |
| V7 | 前序 PR20 spec 已归档（**已自动满足**，归档动作早于本 spec 完成） | `test -f docs/superpowers/specs/archive/2026-08-02-pr20-torch-bump-disposition-design.md`（当前已 PASS） |

---

## 5. 待决策项（plan 阶段定，spec 只记选项）

### 5.1 Dependabot ecosystem 名与 directory（✅ 阶段 2 在 spec 内解决）

经查 GitHub 官方文档（[Dependabot uv GA 公告 2025-03-13](https://github.blog/changelog/2025-03-13-dependabot-version-updates-now-support-uv-in-general-availability/) + [Astral uv Dependabot 指南](https://docs.astral.sh/uv/guides/integration/dependabot/)）：
- **决策：`package-ecosystem: "uv"`，`directory: "/"`。** uv 自 2025-03 GA 起被原生支持。`pip` 会找 `requirements.txt`（本项目无），会 no-op 或 error。
- 本项不再延后到 plan——选错会**静默禁用** Dependabot，是设计级正确性问题。

### 5.2 embeddings CI 覆盖方案

- **选项 B1（推荐，推理 smoke）**：nightly smoke job（实例化模型 + encode，非仅 import）。
- **选项 B2**：PR CI matrix 加维度（拖慢 PR，违 PR #18，不推荐）。
- **选项 B3（冗余，建议删）**：security.yml 加 `--extra embeddings`——但 `--group dev` 已装 sentence-transformers+torch，pip-audit 已覆盖；无增量。
- **倾向**：仅 B1（B3 经阶段 2 复核冗余，B2 违 PR #18）。

### 5.3 模型下载策略

- **选项 A**：`actions/cache` 缓存 HuggingFace 模型目录（key 含模型名 + OS）。
- **选项 B（否决）**：smoke job 仅做 `import sentence_transformers`，不实例化模型——但 import 已被 `--group dev` 覆盖，此举无增量覆盖（阶段 2 复核）。
- **选项 C（推荐）**：用更小的 dummy model `all-MiniLM-L6-v2`（~80MB）替代 `bge-large-zh`（~1.3GB）。推理兼容性与具体模型无关（同一 sentence-transformers + torch 栈），小模型足够且 CI 时长友好。
- **倾向**：C + A（小模型 + 缓存）。

### 5.4 nightly workflow 重启决策（阶段 2 新增）

`nightly.yml` 当前 **DISABLED**（L18-21 schedule 注释，仅 `workflow_dispatch`）。B1 smoke 落 nightly.yml 不会自动跑。
- **选项 A**：B1 smoke 加进 nightly.yml + 重启 schedule（取消 L20 注释）。代价：windows-smoke / 313-migration / doc-links 也会自动跑（可能 flaky，doc-links 依赖外部站）。
- **选项 B（推荐）**：新建独立 minimal scheduled workflow（如 `embeddings-smoke.yml`，独立 cron），只跑 embeddings smoke，不连带启用 nightly 全部 job。
- **选项 C**：smoke 仅 `workflow_dispatch` 手动跑（覆盖承诺降级为"手动 smoke"，非"nightly 防线"）。
- **倾向**：B（独立 workflow，精准覆盖，不污染 nightly）。

### 5.5 PR 拆分

- **选项 A**：单 PR（两项 follow-up 同属"依赖治理"，合并审阅）。
- **选项 B**：拆 2 PR（dependabot.yml + embeddings CI 各一），降低单 PR 体量。
- **倾向**：拆 2 PR（Phase 1 极简配置，Phase 2 涉及 CI 行为，风险等级不同）。

### 5.6 Renovate 配置共存处置（阶段 1 新增决策项，✅ 用户已选删除）

仓库根有 `renovate.json`（完整配置），但 Renovate bot 从未开过 PR（stale 残留 / app 未装）；事实活跃 bot = Dependabot。
- **选项 A（✅ 已定）**：本 spec 顺手 `git rm renovate.json`，统一用 Dependabot，消除双 bot 混淆与未来重复 PR 风险。**用户 2026-08-02 裁决选 A。**
- **选项 B（未选）**：保留 `renovate.json`，在 dependabot.yml 注释说明共存策略。
- ⚠️ **实施订正（audit-T2 发现）**：原 spec 称 "ci.yml 的 renovate 校验 step 删文件后自动 skip，无需改 ci.yml"——**此判断错误**。GitHub PR-files API 把**删除**的文件也列为 changed（`status: "removed"`，`filename` 仍为 `renovate.json`），故删除 PR 本身 CHANGED=1 → validator 对缺失文件 exit 1 → CI 红（已用 PR #23 删除实证）。故 plan Task 2 同时移除 ci.yml 的 renovate 校验 step（死代码 + 对本 PR 会 CI 红），与删文件同 PR 落地。

---

## 6. 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Dependabot 配置加载报错（YAML 语法 / 字段值） | 低 | Dependabot 不运行 | V3 观察；§5.1 已定 ecosystem=uv（GA 支持）；配错回退删文件回默认 |
| `allow.dependency-type: direct` 意外过滤想保留的 PR | 低 | 显式依赖升级被漏 | V2 核实；`direct` 覆盖三处显式声明；单一规则只配 direct（§2.1） |
| embeddings smoke job 因模型下载失败/超时 | 中 | smoke workflow 红 | §5.3 用小模型 `all-MiniLM-L6-v2` + 缓存；初期 `continue-on-error: true` |
| torch wheel 体积拖慢 smoke job | 中 | smoke 时长 +2-4min | 仅独立 scheduled workflow（非 PR CI）；linux-only |
| smoke 落 nightly.yml 但 schedule 仍 disabled → 覆盖不自动跑 | 中 | 名义 nightly 实为手动 | §5.4 倾向独立 workflow（选项 B），规避此风险 |
| 删除 `renovate.json` 后若用户本意是双 bot | 低 | 失去 Renovate 能力 | git 历史可恢复；**已与用户确认选删除**（§5.6） |

**回滚**：
- Phase 1：`rm .github/dependabot.yml`（Dependabot 回到默认配置）。
- Phase 2：移除新 job（workflow 改动可 revert）。

---

## 7. 不做的事（Out of Scope）

1. **不重新处置 PR #20**（已 CLOSED，前序 spec 已完成主动作）。
2. **不升级 torch / sentence-transformers**（本 spec 是配置/CI 覆盖，非版本升级）。
3. **不改 `[project.optional-dependencies].embeddings` 的声明位置**（PEP 621 extra 是正确的；不迁到 `[dependency-groups]`，因为语义上 embeddings 是"可选功能"非"开发工具"）。
4. **不为 embeddings 写功能测试**（本 spec 只做"安装 + import + 兼容性"防线；功能正确性另开 spec）。
5. **不动 src/ 的 2 处动态 importlib 加载**（软依赖设计是有意的，避免 core install 拉入 torch）。

---

## 8. 相关

- **前序 spec**：`docs/superpowers/specs/archive/2026-08-02-pr20-torch-bump-disposition-design.md`（主任务已完成并已归档，本 spec 接管其 follow-up）。
- **PR #20**（已 CLOSED）：僵尸 PR 的案例，本 spec 防其再生。
- **PR #21/#22**（已 merged）：均由 Dependabot 开。#21（pillow）是 mkdocs-material 的 **transitive**（indirect），会被 `dependency-type: direct` 过滤（期望）。#22（pymdown-extensions）在 `[dependency-groups].docs`（L54）**显式声明**，属 direct，**不会被过滤**——仍正常开 PR（期望，docs 组依赖要升级）。本 spec 防的是 #21 式 / torch 式 **transitive** 单独开 PR，不防 #22 式显式依赖。
- **`renovate.json`（共存 bot）**：仓库根有完整 Renovate 配置，但 `gh pr list` 显示 Renovate bot 从未开过 PR（未装 app / stale 残留）。当前事实 bot = Dependabot。§5.6 决策（**用户已选删除**）顺手 `git rm renovate.json` 消除双 bot 混淆。
- **PR #18**（CI 矩阵收缩）：本 spec embeddings CI 方案需与之协调（不在 PR CI 加矩阵项，避免回退 PR #18 的优化）。
- **`pyproject.toml`**：L17-18 注释（"避免 core install 拉入 torch/CUDA"）+ L22-23 `[project.optional-dependencies].embeddings` 声明。
