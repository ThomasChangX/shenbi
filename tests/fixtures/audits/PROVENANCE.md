# 审计语料 fixtures 来源（provenance sidecar）

spec #105 T1b 差分基线语料——**逐字节复制**（未加头/未改写，G0.9：真实 skill 输出；
差分基线纯净性优先，provenance 走本 sidecar 而非文件内头——plan r3-MC 偏离②）。

复制日期：2026-11-15｜来源项目：`novel-xinghuo-vol1/audits/`（gitignored 运行工件）

| 文件 | 选章理由（覆盖面） |
|------|------|
| chapter-1-anti-ai.md | bracket CRITICAL/MINOR |
| chapter-2-memo-compliance.md | cell BLOCKING |
| chapter-10-anti-ai.md | bracket BLOCKING（派发完整性实弹族） |
| chapter-11-anti-ai.md | cell ERROR |
| chapter-11-foreshadowing.md | cell MINOR |
| chapter-11-memo-compliance.md | cell CRITICAL |
| chapter-11-review-summary.md | heading 形 `## CRITICAL Issues`（`## BLOCKING` heading 形 vol1 实有于 chapter-23-review-summary.md 未选入——已知缺口归 (c) 层构造行覆盖 test_chapter_loop.py:1127/1135，audit-T1b I-2） |
| chapter-13-memo-compliance.md | bold MINOR |
| chapter-14-pacing.md | bracket WARNING |
| chapter-15-foreshadowing.md | cell WARNING |
| chapter-18-world-rules.md | bold WARNING |
| chapter-23-anti-ai.md | bold ERROR |
| chapter-32-sensitivity.md | bold BLOCKING+table-bold 形 |
| chapter-40-reader-pull.md | 派发完整性实弹（T5 红测引文源 :44） |
| chapter-1-character.md | **main 既有 fixture**（非本批复制；来源见 git log d7f22fb2）——被新差分基线消费，属早期真实 skill 输出 |
| chapter-1-consistency.md | **main 既有 fixture**（非本批复制；来源见 git log 1939200e）——同上 |

语料空洞（构造行内红绿补，G0.9 禁手造 fixture）：bracket ERROR、bold CRITICAL。
