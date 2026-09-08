# novel-output 目录说明（C18 F1119 漂移裁决 · 2026-09-08）

三棵子树用途不同，**不互为镜像**：

- `xinghuo-ranqiong/` — 生产树（56 章小说及其 audits/snapshots/plans/truth/staging 产物）
- `test-validation/` — 测试验证树（dispatch 写安全验证运行，含 trace.jsonl/write-audit.jsonl 计量链）
- `validation-results/` — 历史手动验证记录（2026-07 的 manual-run 输出，已被 C18 cleanup 标注 superseded，见各文件头注）

结构漂移（三树目录形态不一致）为历史形成，非缺陷；生产语义以 `xinghuo-ranqiong/` 为准。
产物污染基线与清洗记录：`docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`。
