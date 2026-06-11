# Generative Test: shenbi-chapter-planning

## Skill Under Test
`skills/shenbi-chapter-planning/SKILL.md`

## Test Setup
A novel project exists with completed volume outline and truth files. The project is ready to plan chapter 7 of Volume 2. Truth files include `truth/pending_hooks.md` with active hooks, `truth/chapter_summaries.md` with recent summaries, and `outline/volume_map.md` with volume structure.

## Agent Task
Run shenbi-chapter-planning to produce a complete chapter memo for chapter 7. The memo must contain all 8 required sections: (1) 当前任务, (2) 读者此刻在等什么, (3) 该兑现的/暂不掀的, (4) 日常/过渡承担什么任务, (5) 关键抉择过三连问, (6) 章尾必须发生的改变, (7) 本章 hook 账, (8) 不要做. Goal derivation must follow the priority chain (instruction > override > volume KR > focus > intent). Hook accounting must track all active hooks. End-of-chapter change must specify 1–3 concrete changes. The "不要做" section must name specific avoid-patterns, not generic advice.

## Seed Input
Volume outline from `tests/fixtures/outline-example.md` and hook state from `tests/fixtures/pending-hooks-example.md`
