# Shenbi (神笔) 贡献者指南

## 项目定位

Shenbi 是一套小说写作 AI 技能框架。每个技能是一个 SKILL.md 文件，指导 AI agent 完成小说创作的特定环节。

## 技能规范

- 每个技能位于 `skills/<skill-name>/SKILL.md`
- Frontmatter: `name`（仅字母数字连字符）+ `description`（只描述触发条件，≤500字符）
- 描述陷阱：description 绝不描述技能做什么，只描述何时使用
- 关键技能使用 DOT 流程图定义权威流程（DOT 是规范文档，不需要自动化渲染；如需渲染，添加 `charset="utf-8"` 和 CJK 字体声明）
- 每个纪律性技能包含反理性化表格

## 术语约定

- "your human partner" — 与 agent 协作的人类创作者，不用 "the user"
- "truth files" — 小说项目中的真相文件（世界状态、伏笔池等）
- "chapter memo" — 8段式章节备忘

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：
- `feat: add shenbi-worldbuilding skill`
- `fix: correct anti-rationalization table in review-anti-ai`

## P-1.E Foundation (2026-06-15)

Framework runtime code migrated from `tests/` to `src/shenbi/`. Contributors should:

- **Use entry points**: `shenbi-score`, `shenbi-progress`, `shenbi-phase`, `shenbi-summarize`, `shenbi-validate`, `shenbi-dispatch` (not `python3 tests/X.py`)
- **Use `pipeline` CLI**: `pipeline init <seed>`, `pipeline status <dir>`, `pipeline review <dir> <decision>` (novel orchestration; `just pipeline-init`, `just pipeline-status`, `just pipeline-review`, `just pipeline-resume`)
- **Use `just`**: `just check` runs all CI checks; `just test` runs unit tests
- **Find framework code** under `src/shenbi/` (not `tests/`)
- **Install dev deps** via `uv sync --group dev` (PEP 735, not `--extra dev`)
- **Coverage thresholds**: 80% branch, 90% line, 0.10 test density
- **No `print()`** in framework code; use structlog
- **No `ignore_errors`** in mypy overrides; no overrides at all post-P-1.E
- **No deferral comments**: every PR is complete or links a tracking issue

Full P-1.E details: `docs/superpowers/specs/2026-06-15-p-1.e-foundation-completion/README.md`
