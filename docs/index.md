# Shenbi (神笔)

> AI 驱动的长篇小说创作框架，通过门控技能编排保证质量。
>
> AI-driven long-form novel writing framework with quality-gated skill orchestration.

---

## 解决什么问题 / The Problem

用 AI 写一部完整的小说，意味着要协调几十个专业环节——世界观构建、角色设计、伏笔管理、文风打磨、反 AI 检测——同时在数十万字的内容中保持一致性。现有的 AI 工具缺乏系统性的流程编排和质量验证机制。

Writing a complete novel with AI means orchestrating dozens of specialized tasks — worldbuilding, character design, foreshadowing management, style polishing, anti-AI detection — while maintaining consistency across hundreds of thousands of words. Existing AI tools lack systematic process orchestration and quality verification.

---

## 核心能力 / Core Capabilities

### 技能编排 / Skill Orchestration

67 个写作技能 + 2 个元技能，按 9 个流水线阶段组织。从世界观构建到反 AI 检测，覆盖长篇小说创作的全流程。

67 writing skills + 2 meta-skills, organized by 9 pipeline phases. From worldbuilding to anti-AI detection, covering the full long-form novel creation process.

→ [技能目录 / Skill Catalog](skills/index.md)

### 质量门控 / Quality Gates

8 个验证门控（G0-G7）在流水线的每个关键边界强制执行质量检查。没有任何门控可以跳过。

Eight validation gates (G0-G7) enforce quality checks at every critical pipeline boundary. No gate can be skipped.

→ [架构概览 / Architecture](architecture/overview.md)

### 可测量的质量 / Measurable Quality

三层评分系统（T1/T2/T3）使用 0-100 的评分标准，94 分为推进门槛，100 分为收敛目标。

A three-tier scoring system (T1/T2/T3) uses 0-100 rubrics, with 94 as the advancement threshold and 100 as the convergence target.

→ [架构概览 / Architecture](architecture/overview.md)

---

## 从这里开始 / Get Started

### 我想写小说 / I Want to Write a Novel

从安装开始，了解核心概念，然后跟着第一本小说的完整流程走一遍。

Start with installation, learn the core concepts, then follow the complete first-novel walkthrough.

→ [快速开始 / Getting Started](getting-started/installation.md)

### 我想理解框架 / I Want to Understand the Framework

了解流水线设计、门控链、评分系统和真相文件如何协同工作。

Understand how the pipeline design, gate chain, scoring system, and truth files work together.

→ [架构概览 / Architecture Overview](architecture/overview.md)
