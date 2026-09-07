# Bug-Hunt Test: shenbi-review-memo-compliance

## Skill Under Test
`skills/shenbi-review-memo-compliance/SKILL.md`

## Test Setup
A novel project exists with chapter memo at `tests/fixtures/chapter-plan-example.md` and drafted chapter 7 at `tests/fixtures/chapter-draft-example.md`. The memo has 8 sections. Section 3 lists 5 required payoffs in its 该兑现的 table:
1. 林烽的现代人设（≤300字，用行为而非旁白展示）
2. 锈泥巷的物理环境（五感逐步展开）
3. 灵能修炼贷款机制（规则用对话展示）
4. 种姓制度的基本框架（通过不以为然的日常对话反衬）
5. 灵能僭越罪（章中段冲击性信息）

The drafted chapter delivers items 1-3 and 5, but item 4's required delivery vehicle — a neighbour or collector explaining the caste framework through offhand daily dialogue — never occurs; 庶民 status is conveyed only through the protagonist's own inference.

## Scenario
The agent runs a memo-compliance audit on chapter 7. The audit report at `tests/fixtures/audit-report-example.md` checks BDI, OOC, 配角, 声音, and PRE_WRITE_CHECK — but performs no section-by-section verification against the memo at all. Its stated 审计依据 is only "章节内部一致性 + PRE_WRITE_CHECK 自定规则", so the memo's per-item delivery requirements are never checked and under-delivered items pass undetected.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/audit-report-example.md`: audit scope | Memo compliance coverage gap — audit cites "章节内部一致性 + PRE_WRITE_CHECK 自定规则" as its only basis; no verification of the memo's 5 payoff items, so the undelivered caste-dialogue requirement (item 4) is missed | error |

## Agent Task
Run shenbi-review-memo-compliance audit on chapter 7. Find the planted defect where the audit never performs the section-by-section memo compliance check, letting an under-delivered memo item pass.
