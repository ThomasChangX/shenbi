# F1154 — snapshot-manage manifest fixture 缺失报告（spec #57 T4）

仓库不存在 shenbi-snapshot-manage 的真实 manifest 产物可作 fixture（G0.9 禁手造、
SDD 核心原则 8 禁现场 dispatch 取证）。`tests/fixtures/snapshots/chapter-025/manifest.md`
为 spec #54 (C16 F779) 已裁决的 grandfathered 样本：frontmatter provenance 显式声明
"hand-authored snapshot manifest; checksums are real sha256"（synthetic-sample），
checksums 为 tests/fixtures/chapters/ 真实文件 sha256。
t1-skill 场景（shenbi-snapshot-manage / shenbi-sequel-writing）引用该 fixture。
布局冻结后（本 spec item 9）如未来产出真实 snapshot-manage manifest，应替换本样本
并删除本报告。

附注（spec #57 T4 磁盘清退）：chapter-030/ 与 pre-chapter-25/ 下时间戳快照样本的
`source:` frontmatter 指向 novel-output 上游（已随本 spec 清退删除）——样本保留为
真实历史产物，该引用属历史 provenance 非活路径依赖。
