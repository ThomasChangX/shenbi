# novel-output 目录说明（C18 F1119 漂移裁决 · 2026-09-08）

三棵子树用途不同，**不互为镜像**：

- `xinghuo-ranqiong/` — 生产树（56 章小说及其 audits/snapshots/plans/truth/staging 产物）
- `test-validation/` — 测试验证树（dispatch 写安全验证运行，含 trace.jsonl/write-audit.jsonl 计量链）
- `validation-results/` — 历史手动验证记录（2026-07 的 manual-run 输出，已被 C18 cleanup 标注 superseded，见各文件头注）

结构漂移（三树目录形态不一致）为历史形成，非缺陷；生产语义以 `xinghuo-ranqiong/` 为准。
产物污染基线与清洗记录：`docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`。

## 已知失配（F1167 · C18 裁决 2026-09-08）

`genre-config.json` `auditDimensions.texture: true` 但生产树 audits/ 从未生成 texture 审计文件（manual-era 遗留失配）。**不翻转 config**：G0.cc 一致性门禁将 texture 禁用列为 CRITICAL（E34 根因，需人工批准+替代检测机制）；本失配作为已文档化已知态留档，待 texture 审计真实落地或人工裁决后消除。
