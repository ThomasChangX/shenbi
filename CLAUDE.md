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
