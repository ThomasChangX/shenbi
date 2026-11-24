# Spec #108 · 审核灵敏度探针（audit-recall-canary）：确定性变异器目录 + 派发探针 harness + 召回矩阵报告（审计召回=体系缺失的第一元指标）

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（r1.1，2026-11-24 Revised）｜ **优先级**：🟡 P2
**动机证据**：`src/shenbi/gates/g7.py`（G7 全文不读 `audits/*.md`——grep 零命中；G7.13 复核的是门不是 LLM 审计）——**审者假阴性无任何测量面**；`tests/tiers/t1-skill/_template/rubric.md:19-30`（kill switch 三分：bug-hunt「漏检植入缺陷→0」/clean「幻觉缺陷→0」/**generative 仅 HARD-GATE violation→0**——审者漏检在生成侧评分零成本）；`src/shenbi/pipeline/chapter_loop.py:686-709`（cascade skip：3 连净章跳审计 + CASCADE_REVERIFY_GAP=5——被跳过的审计技能无抽样验证机制）；覆盖面盘点（2026-11-15 审核体系审计）：**>5 章跨章语义一致性无审核面**（LLM 审窗普遍 3-5 章；long-span 每 24 章且只查统计形态；arc-payoff 卷尾摘要粒度）——伤害无数据；`docs/framework/invariants.md` mutant 义务列（spec #80 rev4 R3-I1——**mutant 先例**：义务谓词挂门检维度；本件把 mutant 思想从「门」推广到「审计技能」）；`tests/fixtures/`（G0.9 真产物基座现成）；`novel-xinghuo-vol1/cost/report.md`（一束 canary ≈ 6 技能×10 变异 ≈ 60 派发 ≈ $0.35——束8 探针同量级）。

**触及的不变量维度**：恒等 identity、时间、持有与经手 props、枚举计数 counters、叙事纪律（POV/声口）、情绪节奏（均只读消费——测既有门检/审计的召回率，不改载体/声明/门检任何槽）

**r1.1 修订（2026-11-24 · 实现审计回写；spec 组合席透镜复核＋评测科学席实测，协调者核）**：
- **重复次数（L4 可判别性）**：原文「逐 mutator 生成变异副本 → 派发」即每格 1 份、无重复数。评审派发有随机性，单次读数的召回估计噪声不可控。改为：每个 mutator × 每个基座章重复 k≥3（或 ≥3 个基座章），报告按 mutator 给 Wilson 区间，并预注册「最小可检效应」。
- **缺未变异对照臂**：#107 T2 以本件为测量器并要求「audits 误报率不升」——本件原设计没有对照臂，测不出误报率。T2 增补：每个基座章同时跑一次**未变异**派发作对照臂（成本约 +1/9），「对照臂上的 finding 数」即基线误报率。
- **验收由「召回>0」改为可判**：结构面 mutator 1–8 的判据改为「召回点估计 ≥ 预注册下限且区间下界 >0」；mutator 9 仍预期 0 检出（缺口数据）。
- **T3 的 before 底座不可复现**：#105 已于 2026-11-16 归档，本件实弹尚未跑过——「为 #105 改动提供 before/after 底座」的 before 补不回。T3 改为「为其后的审计面改动（#107／#117／#123）提供 before/after 底座」，#105 的对照登记为不可得。
- **期望检出面须逐项可 FAIL（评测科学席实测，协调者复核一例）**：`G4.cd.simile_band` 两臂都只出 PASS（`src/shenbi/gates/g4/chapter_drafting.py:1397/:1406` 一带，注释「报告行非 WARN——spec #118 T5 裁定 A」）却登记为有判别力；首批 mutator 的「期望检出面」须核对目标门在真数据上确能 FAIL，按构造不可 FAIL 的门不作期望面。
- **顺序**：独立 dry-run 可随时；实弹随令。

---

## 0. 根因

**体系测量了判官的一切除了「抓得住真缺陷吗」**：一致性（G7.15 同分向量/双评探针）、塌缩（flag_score_collapse）、置信度（锚点命中率）都有哨兵，唯独召回率缺席。后果：审计面的一切改动（含 #105 契约硬化/#106 下限接线/#107 分档）都无法量化验证「审得更好了」；cascade skip 跳过的章、>5 章语义漂移的伤害，全部停留为无数据的争论。

**用户裁定（2026-11-15）**：不考虑在飞项目——探针基座用 tests/fixtures 真产物（G0.9 合规）或随令指定的项目章；变异副本进 /tmp round dir，**永不触碰任何项目 truth/chapters 面**。

**备选案已评估并否决**：「G7 增元审计、重审已 approve 章节」——重审无真值（不知缺陷在哪），只有植入已知缺陷才有 ground truth，且 G7 读 audits 面是大破面；「生产内嵌 canary 章」——污染正文/truth 面，独立 harness 干净且随令跑。

## 1. 任务分解

### T1 · 变异器目录（确定性纯函数）
- `src/shenbi/pipeline/canary/mutators.py`：每 mutator =（fixture 章文本+项目上下文 → 变异文本 + 期望检出面标注），首批 9 个从实弹 P1 清单（escalation 报告真缺陷形态）取材：
  1. POV 人称换装（叙述段主语代词系统性换装）→ 期望 `XC pov_break` / group-character D4；
  2. 保留名劫持（禁用名用作在场角色）→ 期望 `XC reserved_name_hijack`；
  3. 时间锚回拨（改写时间锚与既有锚矛盾）→ 期望 `XC timeline_rollback` / group-factual D1；
  4. 计数漂移（「第三次」→「第二次」）→ 期望 `cd.counter` 三方对账；
  5. current_state 字段事实矛盾（改写主角位置/持有物）→ 期望 group-factual D1/D2；
  6. 字数带击穿（截断至带下限-20%）→ 期望 G4.cd word_count 地板；
  7. 章末钩缺席（改写章尾为平收）→ 期望 `cd.chapter_end_hook`；
  8. AI tell 注入（插入三连排比+疲劳词）→ 期望 group-craft D3（预计算 ai_marker_hits 面）；
  9. **长程承诺措辞漂移**（改写 20 章前 pending_hooks 钩的兑现措辞——语义等价但细节漂移）→ **期望检出面=无（缺口登记）**——为「>5 章语义一致性」未来立项提供伤害数据。

**判据**：每 mutator 单测（同输入同输出确定性 + 变异 diff 锚点存在）；期望面标注与 invariants.md 门检列 check id 对齐（表内 id 逐字）。

### T2 · 探针 harness
- `just audit-canary <dir|fixture> [--chapters N] [--dry-run]`：取最近已过章（或 fixture）逐 mutator 生成变异副本 → 派发 review 固定六步（factual/character/craft/plan/resonance/sensitivity）+ G4.XC → 解析 findings 对期望面 → 召回矩阵 `reports/canary-report-<ts>.md`（mutator × 检出面 × 命中/漏检）；
- `--dry-run` 只产矩阵骨架不派发（CI 可零成本跑构造正确性）；**实弹=付费派发，随用户令**（授权口径）；cascade-skip 中的技能也纳入派发面（验证跳过不漏检）。

**判据**：dry-run 全绿（矩阵构造+零派发证明）；实弹一束（用户令）产出报告落盘。

### T3 · 消费与挂账
- 召回 0 的期望面 → 报告 WARN 行（mutator 名+期望面+「无人检出」）；报告为 #105/#107 改动提供 before/after 底座（验收引用同一束 fixture）；挂账面=报告自身+INDEX 挂账注记（不进 drift-guidance 生产读面——canary 是元指标非章级信号）。

**判据**：报告含 WARN 节；#105/#107 验收节可引用 canary 报告路径作对照底座。

## 2. 验收
1. T1-T3 判据全绿；
2. 首批实弹报告落盘：召回矩阵基线（结构面 mutator 1-8 预期召回>0——若结构面 mutator 也有 0 检出即真 finding，挂账修复）；mutator 9 预期 0 检出（缺口数据落地）；
3. 成本记录入报告（派发数/tokens/$，与 $0.35 量级预估对照）。

## 3. 风险
- **变异器造出的缺陷不真实**（人工痕迹重→检出率虚高或虚低）→ 首批保守取材实弹真缺陷形态 + 每 mutator 语义说明；报告注明「canary 召回≠生产召回」的口径边界；
- 成本失控 → 默认 dry-run、实弹随令、单束预算上限预注册；
- 与生产隔离 → 变异副本只进 /tmp round dir（harness 路径纪律红测：canary 运行后项目 truth/chapters mtime 不变）；
- fixtures 章与真实项目章分布差异 → harness 支持双基座（fixture 束=CI 对照、项目章束=随令实弹），报告标注基座。
