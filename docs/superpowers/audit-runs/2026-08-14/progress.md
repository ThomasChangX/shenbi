# 审计进度 — 2026-08-14
## 阶段状态机
| 阶段 | 状态 | 轮次历史 |
|---|---|---|
| 0 清点与基线 | done | D1 ①-⑫ 全部运行并归档；3 findings (D1-01~03) |
| 1 整体层审查 | done | 8 维度全部有结论；8 findings F0-01~08 |
| 2 分区深度审查 | in_progress | Z1-Z6 多轮复核进行中（Z6 4轮/Z3 3轮/Z2 3轮/Z4 3轮/Z5 3轮）；F325 误报撤销；P0×1(F324)；Z7-Z11 待派发 |
| 3 线程 | pending | — |
| 4 聚类校准 | pending | — |
| 5 spec 产出 | pending | — |
| 6 覆盖证明+裁决 | pending | — |
## 抽样种子登记（阶段 0 生成，禁止事后修改）
- D2 漂移抽样清单 (seed=20260814，活跃文档引用全验；归档 spec 引用归 T10/T15；高风险文档 AGENTS/架构/契约/gates 由 Z9 全查):
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:36 → error_handler.py:36-37
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:37 → error_handler.py:40-57
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:38 → error_handler.py:60-81
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:51 → chapter_loop.py:203-244
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:52 → audit_layer.py:44-53
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:66 → skills/shenbi-chapter-revision/SKILL.md:9-10
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:67 → revision_router.py:199
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:68 → parallel_dispatch.py:189-249
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:116 → revision_router.py:199
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:18 → 2026-06-22-positive-quality-gates.md:7
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:44 → 2026-07-19-01-truth-file-and-state-accumulation-design.md:42
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:102 → dispatch_helper.py:1030-1037
      - docs/superpowers/specs/INDEX.md:32 → error_handler.py:36-37
      - docs/superpowers/specs/INDEX.md:32 → parallel_dispatch.py:189-249
      - docs/superpowers/specs/INDEX.md:32 → revision_router.py:199
      - docs/framework/chapter-file-format.md:48 → src/shenbi/gates/shared.py:120-121
- 阶段 4 抽查: seed=20260814，从已 verified findings 中按 (id_hash % 100) < 10 抽取 ≥10%（规则固定：按 ledger 行序 hash，禁止事后挑选）
- G6 meta-audit: seed=20260814，≥20% per-file 报告条目，按区成层（每区≥1条；Z3/Z4/Z5/Z11 与低置信度文件必抽；区内按 path 确定性 hash 排序取前 k 条；k = max(1, round(n*0.20))；Z7 共 182 条、Z8 20、Z9 43、Z11 256 等按上表）
## 会话日志（追加式）
### 2026-08-14 会话 1
- 完成: 阶段 1 整体层审查——8 维度全部有结论；8 findings (F0-01~08) 录入（skills 计数漂移 / deps.json 契约缺 5 skill / gate 文档漂移 / INDEX 计数 / dispatch-subagent 引用 / py 版本三元不一致 / SECURITY weekly 声明 / coverage 注释漂移）
- 下一步: 阶段 2——Z5/Z6 复核收敛 → Z1-Z4 收报告核实 → Z7-Z11 派发
- 待核实 findings: F500-F512 (Z5), F601-F611 (Z6) 已核实 verified；Z5-01 (novel-output decisions.json 83/145 无效) 待 Z11 深查
