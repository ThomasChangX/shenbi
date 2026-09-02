# Plan — spec #40 总纲记账 pass（2026-09-03）

> Spec: docs/superpowers/specs/2026-08-16-audit-remediation-master.md §8 · 全部 docs/ledger 记账，零生产代码
> 分支: docs/spec40-master-bookkeeping · spec 号映射 #27=C1…#39=C13
> Ledger 基线：当前 778 ID 行（774 D/F/T + 4 G6xx），691 open / 86 verified / 1 closed（T1002，C24 的 `closed（顺带修复）`——非批次 A，脚本不得触碰）。19 行畸形重复行已在 f86ceaa6 清除，今日不存在。

## Task 1 · 矩阵状态标注（T1）
- §7 附录矩阵 13 个 Done 簇行加 `✅ Done (PR #N)`；文件名列改 archive/ 实名（两种形态见 §8）
- §2.1 P0 表 C3/C4/C10/C11 行加同标注；§2.2/§2.3 分组行内 C13/C8 等加简注
- 核对：不改变任何计数列；13 行全覆盖

## Task 2 · findings-ledger 回写（T2）
- 从 phase4-clustering.md §2 簇总表解析 C1-C13 压缩成员清单（区间展开）
- 匹配策略：**首格精确匹配**（`^\| <ID> \|`），禁止子串——F1-F1177 并存，`F10` 子串会命中 F100/F1000+
- 从 13 份归档簇 spec 提取剔除/残余权威记录（grep 修订记录节）：
  - 「已修 elsewhere」剔除条目 → `closed (fixed by PR #X)` 注明实际 PR
  - 残余/遗留观察缺口条目 → **保持原状态（open/verified）** + `residual (spec #NN)` 注记
  - 其余成员 → `closed (C-N spec #NN, PR #N)`
- 行内定位：状态列为**尾格**锚定，不按固定列号——已知错位行 F002(NF=14)/F004,F007(NF=15)/F006(NF=16) 非批次 A 成员、T702（C3 成员，行内未转义管道致 16 格、状态在第 15 格）需特殊处理后再关闭
- 验收：改动只落在 findings-ledger.md；行数不变（778）；**逐簇断言** closed 数 = 该簇成员数 − 剔除/残余数（逐簇预期表随脚本输出）；全表 closed 总数与逐簇和一致；抽验 10 行格式

## Task 3 · #25 解散归档（T3）
- 残余核对面 = #25 的 Z1-整体层（3 条）+ 统一修复模式家族主条目（约 8 条，共 ~11 条，非全 287）——**语义核对**（根因/描述对照），禁止 ID 字符串 grep：08-14 与 08-15 轮 F 号命名空间碰撞（#25 F112/F202 与 08-15 同号不同义，C35 已标记）
- 每条给 08-15 簇归宿或记入总纲 §8 deviation（不静默丢弃）
- 文件头加解散注记（08-14/08-15 ledger 家族区分 + 九次 DEFER 显式 supersede + 剩余承接=§7 矩阵 24 活跃簇）→ git mv 到 archive/（该文件无 markdown 相对链接，安全）
- INDEX 删 #25 行

## Task 4 · INDEX 刷新（T4）
- 计数头 28→27；「最后更新」→ 2026-09-03

## Task 5 · 门禁与交付（T5）
- `just check` 全绿（docs workflow mkdocs --strict 由 PR CI 复核）
- pathspec 显式列文件 commit；PR → CI 全绿 → squash merge
- 归档收尾（本 plan 负责，防计数漂移重演 f1d48255；**作为 post-merge 的独立 docs(archive) PR（同 #146/#143 先例），不在主 PR 内**）：本 plan git mv 到 plans/archive/、plans/INDEX.md 活跃 1→0/已归档 90→91；spec #40 文件本体按 §5「长期保留为 37 簇索引」**不移 archive/**，Status 改 `Bookkeeping pass Done (PR #N)`，且 specs/INDEX.md #40 行的 `状态: Design` 字段同步改
