# 核心概念 / Core Concepts

在使用 Shenbi 之前，需要了解五个核心概念。

Before using Shenbi, you need to understand five core concepts.

---

## 技能 / Skill

技能是一个 `SKILL.md` 文件，位于 `skills/<name>/` 目录下，指导 AI agent 完成小说创作的特定环节。每个技能的 YAML frontmatter 包含 `name` 和 `description`（只描述何时触发，不描述做什么）。

A skill is a `SKILL.md` file under `skills/<name>/` that instructs an AI agent on a specific novel-writing task. Each skill's YAML frontmatter contains `name` and `description` (describing only when to trigger, not what it does).

技能按 9 个流水线阶段组织。Agent 通过 `using-shenbi` 元技能的触发规则表发现和加载技能。

Skills are organized by 9 pipeline phases. Agents discover and load skills through the trigger map in the `using-shenbi` meta-skill.

→ [技能目录 / Skill Catalog](../skills/index.md)

---

## 真相文件 / Truth Files

真相文件是小说项目的持久化状态文件。它们在技能之间传递状态：每个技能读取相关真相文件获取当前状态，执行后通过 `shenbi-state-settling` 更新真相文件。

Truth files are persistent project state files. They carry state between skills: each skill reads relevant truth files for current state, and after execution, `shenbi-state-settling` updates them.

`docs/framework/truth-files.yaml` 定义了 15 种文件类别。5 个核心类别是 config、world、character、outline、truth。

`docs/framework/truth-files.yaml` defines 15 file `kind` values. The 5 core categories are config, world, character, outline, truth.

这是 Shenbi 保持 20 万字小说不自相矛盾的核心机制。

This is the core mechanism that keeps a 200,000-word novel from contradicting itself.

---

## 门控 / Gates

8 个验证门控（G0-G7）在流水线的关键边界强制执行质量检查。核心原则：**没有任何门控可以跳过。**

Eight validation gates (G0-G7) enforce quality checks at critical pipeline boundaries. Core principle: **no gate can be skipped.**

- **G0** 在轮次创建时检查环境完整性（工具哈希、fixture 纯度） / Environment check at round creation (tool hashes, fixture purity)
- **G2/G4** 检查输出文件的结构和质量 / Output file structure and quality
- **G7** 在轮次关闭时做全面审计 / Full audit at round closure

门控失败意味着输出被拒绝——不评分、不推进。

A gate failure means the output is rejected — not scored, not advanced.

-→ [门控详情 / Gate Details](../architecture/overview.md)

---

## 轮次 / Rounds

轮次是一次完整的测试执行周期。每个轮次有自己的目录（如 `round-006/`），包含输入 fixtures、技能输出、评分报告、gate markers 和 progress.json。

A round is a complete test execution cycle. Each round has its own directory (e.g., `round-006/`) containing input fixtures, skill outputs, scoring reports, gate markers, and progress.json.

轮次的关键属性是**可复现性**：同一 fixtures + 同一 skills = 确定性输出。每次重跑都可以对比。

The key property of a round is **reproducibility**: same fixtures + same skills = deterministic output. Every re-run can be compared.

创建轮次：`bash tests/round-exec.sh <agent> <tier>`

---

## 评分层级 / Scoring Tiers

三层评分系统衡量质量的不同范围：

The three-tier scoring system measures quality at different scopes:

| 层级 / Tier | 范围 / Scope | 说明 / Description |
|-------------|-------------|-------------------|
| T1 | 单技能 / Per-skill | 每个技能输出按 rubric 打 0-100 分 |
| T2 | 单阶段 / Per-phase | 阶段内所有技能需达到推进门槛 |
| T3 | 端到端 / End-to-end | 流水线连续性和完整性 |

**94 分是推进门槛**——一个技能的三种测试（generative、bug-hunt、clean）全部 >= 94 才算在 tier 内通过。**100 分是收敛目标。**

**94 is the advancement threshold** — all three test types (generative, bug-hunt, clean) must score >= 94 for a skill to pass. **100 is the convergence target.**

-→ [评分详情 / Scoring Details](../architecture/overview.md)
