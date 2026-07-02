# Shenbi (神笔)

> AI 驱动的长篇小说创作框架，通过门控技能编排保证质量。
>
> AI-driven long-form novel writing framework with quality-gated skill orchestration.

[![CI](https://github.com/ThomasChangX/shenbi/actions/workflows/ci.yml/badge.svg)](https://github.com/ThomasChangX/shenbi/actions/workflows/ci.yml)
[![Docs](https://github.com/ThomasChangX/shenbi/actions/workflows/docs.yml/badge.svg)](https://github.com/ThomasChangX/shenbi/actions/workflows/docs.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 什么是 Shenbi / What is Shenbi

Shenbi 是一套小说写作 AI 技能框架。用 AI 写一部完整的小说，意味着要协调几十个专业环节——世界观构建、角色设计、伏笔管理、文风打磨、反 AI 检测——同时在数十万字的内容中保持一致性。Shenbi 通过 67 个写作技能、8 道质量门控（G0-G7）、三层测试评分系统（T1/T2/T3）和真相文件状态管理来解决这个问题。

Shenbi is a novel-writing AI skill framework. Writing a complete novel with AI means orchestrating dozens of specialized tasks — worldbuilding, character design, foreshadowing management, style polishing, anti-AI detection — while maintaining consistency across hundreds of thousands of words. Shenbi solves this through 67 writing skills, 8 quality gates (G0-G7), a three-tier testing and scoring system (T1/T2/T3), and truth-file state management.

## 为什么选择 Shenbi / Why Shenbi

- **技能编排 / Skill orchestration** — 67 个写作技能覆盖从世界观构建到反 AI 检测的全流程，按 9 个流水线阶段组织 / 67 writing skills cover the full process from worldbuilding to anti-AI detection, organized by 9 pipeline phases
- **质量门控 / Quality gates** — 8 道验证门控（G0-G7）在每个关键边界强制执行质量检查，没有任何门控可以跳过 / 8 validation gates (G0-G7) enforce quality at every critical boundary — no gate can be skipped
- **可测量的质量 / Measurable quality** — T1/T2/T3 评分系统使用 0-100 的评分标准，94 分为推进门槛，100 分为收敛目标 / T1/T2/T3 scoring uses 0-100 rubrics, with 94 as the advancement threshold and 100 as the convergence target

## 快速开始 / Quick Start

```bash
git clone https://github.com/ThomasChangX/shenbi.git
cd shenbi
uv sync --group dev
just check
```

详见 [安装指南 / Installation Guide](docs/getting-started/installation.md)。

See the [Installation Guide](docs/getting-started/installation.md) for details.

## 文档 / Documentation

完整文档发布在 https://thomaschangx.github.io/shenbi/

Full documentation is published at https://thomaschangx.github.io/shenbi/

| 文档 / Docs | 说明 / Description |
|-------------|-------------------|
| [核心概念 / Concepts](docs/getting-started/concepts.md) | 技能、真相文件、门控、评分 / Skills, truth files, gates, scoring |
| [第一本小说 / First Novel](docs/getting-started/first-novel.md) | 完整长篇小说创作流程 / Complete long-form pipeline walkthrough |
| [技能目录 / Skills](docs/skills/index.md) | 全部 69 个技能的完整目录 / Full catalog of all 69 skills |
| [架构概览 / Architecture](docs/architecture/overview.md) | 流水线、门控链、评分系统 / Pipeline, gate chain, scoring system |

## 技能一览 / Skills at a Glance

| 阶段 / Phase | 技能数 / Skills | 说明 / Description |
|-------------|----------------|-------------------|
| 创世 / Genesis | 11 | 世界观、力量体系、阵营、角色、故事架构 / World, power, factions, characters, story |
| 架构 / Architecture | 5 | 故事架构细化、节奏、伏笔线 / Story refinement, pacing, thread weaving |
| 规划 / Planning | 3 | 章节规划、伏笔种植、上下文组装 / Chapter planning, foreshadowing, context |
| 起草 / Drafting | 9 | 起草、结算、文风、反检测、字数 / Drafting, settling, style, anti-detect, length |
| 审计 / Audit | 18 | 专项审核（角色、连贯性、节奏等）/ Specialized reviews (character, continuity, pacing...) |
| 基设 / Foundation | 4 | 基础审查、修订、真相同步 / Foundation review, revision, truth sync |
| 管理 / Management | 9 | 快照、漂移、卷总结、评分 / Snapshot, drift, consolidation, scoring |
| 导入 / Import | 4 | 已有作品导入分析 / Existing work import & analysis |
| 短篇 / Short Story | 3 | 短篇小说精简流程 / Short novel streamlined pipeline |
| 管道外 / Out-of-Pipeline | 7 | 辅助工具、元技能、起草辅助 / Auxiliary tools, meta-skills, drafting helper |

> 部分技能出现在多个阶段。完整目录见 [技能目录 / Skills](docs/skills/index.md)。
>
> Some skills appear in multiple phases. See the [full catalog](docs/skills/index.md) for details.

## 贡献 / Contributing

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md).

路线图见 [docs/roadmap.md](docs/roadmap.md)。

Roadmap in [docs/roadmap.md](docs/roadmap.md).

## License

[MIT](LICENSE)
