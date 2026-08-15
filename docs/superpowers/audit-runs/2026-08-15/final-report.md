# 全项目深度审计 Final Report — 2026-08-15/16 轮

> **状态：G7 已裁决（2026-08-16）**。项目所有者整批批准协调者推荐方案：终态确认、软收敛接受、三条边界维持 P1、修复顺序按总纲+quick wins、降级门全追认。审计正式闭合，进入修复阶段。
> 执行规范：docs/superpowers/full-project-audit-prompt.md（v3）；$AUDIT_DATE=2026-08-15；$UNATTENDED=true。

## 1. 机械统计（命令输出原文，非手抄）

```
$ python3 -c '...ledger 三分+G 计数...'
F=641 T=129 D=4 G=4 total=778
$ python3 -c '...severity 分布...'
P0=12 P1=145 P2=460 M=161 (sum=778)
$ grep -c '| verified |' findings-ledger.md
verified=86
$ wc -l coverage-ledger.md && grep -c 'deep-read' coverage-ledger.md
coverage-ledger 行数=2975 deep-read 处置=2937
$ ls zone-reports/ | wc -l && ls thread-reports/ | wc -l && ls d1/*.md d1/*.log 2>/dev/null | wc -l
zone-reports=46 thread-reports=16 d1 工件=19
$ git -C . log --oneline --since='2026-08-15' -- docs/superpowers/audit-runs/2026-08-15 | wc -l
审计目录提交数（本审计期间）见 git log
$ grep '^| F\|^| T' findings-ledger.md | grep ' P0 '  # 代表清单
  F301 | TokenLedger 系统性少计：并行审计波/并行 post-draft/genesis/closure/trigge
  F501 | [write_audit.py] parametric 技能审计双向失效（误拦/空转）
  F502 | [snapshot.py] truth 文件整体删除逃过 OWNERSHIP 审计
  F504 | [report.py(消费端)+dispatch_helper(根因)] 8 调用点未传 state → TokenLe
  F751 | t1 bug-hunt/clean 模板场景的植入缺陷在所引 fixture 内容中不存在（内容级断链，测试空转）
  F868 | volume-consolidation 整文件覆写 volume_summaries 但 reads 不含该文件，追加
  F1101 | 5 章正文被修订技能摘要覆写丢失（不可恢复）
  F1102 | decisions.json 契约被静默违反：145 个中 88 个（61%）不合规
  F630 | materialize_progress 周期性整体重建 progress.json，静默覆盖 dispatcher 与
  F360 | append_dedup 契约更新模式全链路零实现：truth 累积文件每章被整文件覆写（或被无法看到现状的 LLM 幻
  F529 | `_matches_declared` 从不 fnmatch 裸 glob 契约模式：10 技能 11 条 `*` 契约
  T101 | file_type=decisions 使 chapter-drafting/short-drafting 的 .md

```

## 2. 覆盖声明

- **表 A**：2937/2937 tracked 文件全 deep-read，零未处置（coverage-ledger.md，G6 复核 100% 完整、0 幽灵路径）
- **表 B**：25 条磁盘产物处置（audited/generated-excluded/cache-ignored），含 F1176 修正（1083 文件权威处置）
- **四层覆盖**：D1 机械层 12 项全套（d1/ 19 工件归档，D1⑨ 勘误见 T1301）；D2 结构化模式（预登记抽样 1048 引用）；D3 语义深读（46 份区报告：11 区 22 段初审 + 24 复核轮）；D4 运行时产物（Z11 两段 + 专项；T11 运行时核验 11 项）
- **线程**：T1-T16 全部 16 份报告齐全
- **G6 meta-audit**：Z7 35.2%（31/31 成立）、Z11 26.1%（12/12 成立）、20/20 类别复演、23 项裁决落账抽检（19 落账 + 4 缺口已补 G601）

## 3. P0 清单（12 条，全部协调者亲核）

| ID | 一句话 | 簇 |
|---|---|---|
| T101 | 章节主产物绕过 G2 全部质量检查（file_type=decisions + .md continue） | C4 |
| F360 | append_dedup 零实现——truth 累积文件每章整覆写（生产实证 56→1 行） | C3 |
| F868 | volume-consolidation 覆写 volume_summaries（reads 不含） | C3 |
| F1101 | 5 章正文被修订摘要覆写丢失（不可恢复） | C3 |
| F630 | materialize_progress 每 5 步整体重建 progress.json 摧毁 G3.4 证据链 | C10 |
| F301/F504 | TokenLedger 生产死码（11 调用点零传 state） | C10 |
| F501 | 写审计 parametric 双向失效 | C32 |
| F529 | 裸 glob 契约从不 fnmatch——合法写入误拦 rc=2（生产 3 次 GATE_FAIL 实证） | C32 |
| F502 | truth 整体删除逃过 OWNERSHIP 审计 | C32 |
| F751 | bug-hunt 植入缺陷与 fixture 内容断链（测试空转） | C16 |
| F1102 | decisions 契约静默违反 88/145（协调者全树复跑 145 中仅 5 过 schema——F237） | C4 |

## 4. 根因结论（37 簇，详见 phase4-clustering.md）

最大元根因 **C1（67 条）："读方↔写方的键空间/命名族/格式从未对账"**——checker 期望的键/值/格式与写方实际产出系统性断裂（DONE/done、agent_id/agent、t1_scores 零写方、marker 命名族、SKILL 格式 vs 解析正则……）。其余高频根因：truth 写路径"有键的没接线、接线的没键"（C3/C7）、确定性 helper 纯 prompt 接线（C7）、状态词表无单源（C8/C9）、计量 dead-wire（C10）、并发保护缺失（C11）、测试构造形态≠生产形态（C14-C17）。

## 5. Spec 产出（阶段 5）

38 份：37 簇 spec + 总纲 `2026-08-16-audit-remediation-master.md`（优先级矩阵：P0×7 簇 191 条先行，主线 C32→C3→C34→C1）。INDEX 登记 #27-#64（活跃 23→61）。

## 6. 收敛状态与残余风险（G4 双轨披露）

| 区 | 终态 | 残余风险 |
|---|---|---|
| Z11 | **软收敛达成**（三件套齐，G7 追认待） | F1101/F1102/F1162/F1171 在架 |
| Z4 | 缝隙扫净+核心面稳定判定（未达形式标准） | P1×4 在架 |
| Z7/Z9/Z10 | 软收敛候选/定向处置后可判/收敛在望 | 见各区报告 |
| Z1/Z2/Z3/Z5/Z6/Z8 | 未达形式标准（每轮仍产新 P1，发现面归约为元根因族） | 见 progress 终态登记表 |

未继续加轮的裁量依据：G4 双轨设计（v2 教训：唯一终止条件不可达）+ 17 轮复核零完全误报 + G6 独立深核通过 + 额度现实。**此裁量本身列为 G7 待裁决事项。**

## 7. 质量声明与限制

- 全部 P0/P1 经协调者亲核（86 条 verified）；17 轮复核零整条误报；G6 独立抽样 63/63 成立——点估计误报率 0%，95% CI 上界 ≈4.8%
- 已修正的审计自身缺陷：19 行双登记、12+4 项裁决落账缺口（G601）、F977 SDK 重试表述、T1301（D1⑨ false assurance）、计数勘误（off-by-23）
- 限制：G6 深核集中于 Z7/Z11，Z2/Z3/Z5 的 P0/P1 未逐条独立深核（靠复核轮+亲核覆盖）；G6 实际种子 20260816 与预登记 20260815 不一致（协议注记）；沙箱回写事故 1 起（已恢复，read-path 副作用立案线索）
- 不可审计项（T11 声明）：pipeline 无离线可执行模式（T1108）——运行时主路径无法免计费审计验证；token 台账/指纹不可审计（T1611，因 F301 本身）

## 8. G7 待裁决事项

1. 审计终态确认（774 findings + 4 G6 立案 = 778；37 簇；38 spec）
2. 未达形式收敛区的处置：接受软收敛披露 vs 继续加轮（裁量已按默认方向执行）
3. F371 P0 边界 / F794 P0 讨论 / F828 P0 边界——三条 P1 维持裁决是否上探
4. 修复优先级矩阵的执行顺序确认（总纲 §2）
5. 触发式简报（≥300）与 $UNATTENDED 各降级门的追认
