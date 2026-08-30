> **Date:** 2026-08-14 | **Status:** Done (PR #82 + follow-ups #83/#84/#85) (Revised 2026-08-30 · SDD #20 修订：R1 宿主/门禁具体化；R2 移交 C22＝spec #60（同主体跨轮 F1106/F1152/F1151 显式认领）；R3 架构改道 G1→settle 纯函数 + 验收 fixtures 化) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 3/7） | **依赖:** 无硬依赖；F302/F640/F324 修复本体分别归活跃 spec #36（C10）/#27 C1-T6/#37 C11-T4（F324 写入侧已由 PR #42 落地 `_shared.py::update_total_chapters`），本 spec 引用不重复实施 | **范围:** novel-output 产物契约（章节格式/truth 注册表/审计产物/滞留文件）| **核心洞察:** 真实项目产物与显式契约大面积背离（章节头/META/注册表），registry 三源分裂

# 产物契约（Z11 补齐 C）

## R1 · 章节格式契约对齐（F1301/F1302, P1）
- 证据：56/56 无 `# Chapter N:` 头（0 命中契约正则）；6 章无 META 块 + ch40 用 `## META` YAML 自创格式
- 修复（修订）：
  - **写入侧宿主 = dispatch_helper `_write_parsed_outputs` 的 post-write `is_chapter` integrity 块**（dispatch_helper.py:1209 起写路径、:1314-1318 已有 prose-leakage/fence-balance 检查——规范化器挂同一块：确保 `# Chapter N:` 头存在，缺失则机器插入首行，不动正文）；chapter_loop 只持契约串不落盘，非宿主
  - **门禁侧新增 FAIL 级章节契约检查**（今日 G2 无此检查：`_META_RE` 仅用于 WARN 级 meta-ratio，g2.py:344-380，头行零检查）——G2 新检查 ID 如 `G2.chapter_contract`：头行命中 `# Chapter N:` 正则 + META 命中 `_META_RE`（单一契约源，禁止第二份正则）或在豁免清单；豁免清单文件仿 `tests/tiers/g4-exemptions.json`（g0.py:528 先例）：落位 `docs/framework/z11-chapter-exemptions.json`，schema={project, chapter, reason}；G2 检查以被检文件路径推导键——chapter 取文件名 `_CHAPTER_NUM_RE`、project 取路径中 `novel-output/<project>/` 段（G2 CLI 无 project 参数，推导规则入检查实现）
  - **存量批量修复**：`tools/` 一次性脚本机器插入头行（可确定性执行，无 dispatch；跑完后删除或归 tools/oneoff 不留常驻 mutating 工具）；6 章缺失 META **不手写伪造**（G0.9 精神）——登记豁免清单
- **验收（可执行化）：56/56 章含契约头；META 要么命中 `_META_RE` 要么在豁免清单（脚本 + pytest 表达，fixture 取 `novel-output/xinghuo-ranqiong/chapters/` 真实产物副本）**

## R2 · truth registry 闭合（F1307, P1；F1322, M）—— **已移交 C22（spec #60），本 spec 不执行（2026-08-30 阶段 1 重裁）**
- 移交依据：F1307/F1322 与 2026-08-15 审计轮 F1152/F1106 为同主体跨轮重编号——活跃 spec #60（C22 registry-reconcile）T2-6 显式认领 bridge_tracker/state_snapshot-pre-rev 补登记，T2-7（F1151）裁决根 truth/ 模板目录改名 `_templates/`（该目录被 2 个模板结构测试消费，非纯测试残留，删除裁决不成立）；本 spec 原拟的删除/登记与 C22 冲突，按单 spec 原子性移交
- 历史证据（留档）：根 truth/（bridge_tracker + character_matrix）不在 truth-files.yaml；state_snapshot-pre-rev.md（tracked）也未登记

## R3 · 状态/账本产物契约（F1309/F1310/F1313, P1——F640/F324/F302 的产物侧实证）
- 证据：progress.json 空壳仅 scorer 字段（F1309）；closure=pending + closure_step=0 + total_chapters 缺位（F1310）；cost/token-ledger.jsonl 不存在（F1313）
- 修复（修订，架构改道）：**产物契约检查不进 G1**（gate_G1 是 pre-dispatch 输入校验，g1.py:147；产物是管线输出，进 G1 会对现行项目 fail-closed 阻塞全部派发）→ 新增**纯函数** `check_product_contracts(project_dir) -> list[str]`（只读、幂等、无副作用，返回违规清单；可独立 pytest）——调用点=章节 **settle 路径**（chapter_loop 章节 settle 处，非 `_maybe_materialize_progress` 本体：该函数 :707-726 是 best-effort、`except Exception: pass` 不阻塞管线，FAIL 语义放它的吞错壳内会被吞掉），违规非空 → raise（中断 settle，FAIL-CLOSED）；**不在每 5 步 hook 处调用**（中途 progress 合法不完整，避免误报）。爆炸半径注记：与 G1 拒绝理由同源（现行项目 fail-closed），但 settle 路径只阻塞该次章节收尾而非全部派发，且现行产物确属真实违约——暴露为正确行为，与 #27/#36 修复合流后自然转绿。修复本体（F302 落账/F640 materialize/total_chapters 写入）由 #36/#27/#37 及 PR #42 承接，本 spec 仅接线检查 + fixtures 验证
- **验收（fixtures 化——核心原则 8 禁现场 dispatch）：真实产物副本作 known-bad fixture（现 progress.json 空壳）被新检查判 FAIL；构造的完整形态 fixture（源自真实产物字段 + #42 写入侧代码路径生成的合规形态）判 PASS；token-ledger 检查用 cost/ledger.py 单元测试面表达**

## 可测试性（修订新增）
- T1 为主：R1/R3 各一组 pytest（R2 已移交）；fixture 引用 `tests/fixtures/`（真实产物副本，G0.9/G0.11 哈希一致）
- 验证命令：`uv run pytest tests/unit/... -k z11` + `just check`；无 LLM 产物验收需现场 dispatch
- 不涉及评分场景，无 G3.4 面

## P2 清单（审计产物/滞留/漂移）
- **F1308（P2）** staging truth 与正式 truth 内容不一致（pending_hooks 9886 vs 4171）
- **F1311（P2）** audit_reports 状态记录与磁盘 117 个审计文件脱节（resonance+review-summary 全缺）
- **F1312（P2）** 双 resonance gate-marker：`G4-review-resonance-generative.json` 为验证运行写入的污染 marker
- **F1314（P2）** audits 722 无内容重复，但 texture 维度配置=true 而磁盘 0 文件 + sensitivity 双发（F329 实证）
- **F1315（P2）** ch56 审计不完整：6/13 维缺失 + ch56 无 audit_reports 记录
- **F1316（P2）** config-change-log.jsonl 单条无操作条目（old=true/new=true）且时间戳晚于运行结束
- **F1317（P2）** write-audit/trace.jsonl 记录与 GATE_FAIL 语义一致但 root truth 残留仍落盘
- **F1321（P2）** plan-decisions 全部滞留 staging（55 个），plans/ 零 decisions；ch54 缺 plan-decisions

## M 清单（并入 M 批量 spec）
- **F1322（M）** 与 F1307 一并移交 C22（spec #60）T2-6/T2-7 处置
