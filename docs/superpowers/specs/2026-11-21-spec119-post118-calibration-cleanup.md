# Spec #119 · post-118 标定收尾（post118-calibration-cleanup）：uniqueness 纯形池过滤＋review 预算单源接线

**日期**：2026-11-21｜ **系列**：spec #118 两项 FINDING 回裁落地（用户 2026-11-21 裁定，专家团四席推荐）｜ **状态**：Design（r1，2026-11-21）｜ **优先级**：🟡 P2（常规排，#110 之后不插队）

**裁定记录（2026-11-21 · 用户「按照专家团意见立项」）**：
- **FINDING①（protagonist 4 章纯代词）＝零动作**：臂即修复——hard 臂原样保留，四章（ch17/18/35/44）作为生成器行为 finding 归档留红（firing 0.08 诚实新常态）；不修文、不放宽；C 阈值重标定推迟至跨书数据（B5）。本件**不含**该裁定任何 task（baseline 行注记随本件 docs PR 落）。
- **FINDING②（uniqueness 32 FAIL＝100% pre-rev 自稿污染）＝批准纯章形池过滤**：测量效度修复非放宽（40% 阈不动）——T1 落地。
- **deviation #8（review 预算公式漂移）＝follow-up 本件**：T2 落地（终审同建议）。

**动机证据**：post118 权威重放（`reports/2026-11-20-gate-power-vol1-post118.md`）——content_uniqueness 首份真实点火 18 PASS/32 FAIL（firing 0.64）；audit-T8 独立重算：**32/32 FAIL 的 max-overlap 伙伴均为自身 `chapter-N-pre-rev.md`**（ch1 vs 自身 pre-rev 重叠 1.0；glob 池 82 个 .md vs 50 纯章分母）；**纯池重跑 FAIL=0/50**——自稿污染 100%、vol1 零真实跨章重复，聋门（64% 伪报淹没真信号，与 simile 56% WARN 失聪同构）。review 面：`src/shenbi/pipeline/review_checklist.py:386` 仍为退役公式 `max(5, wc//1000)`，`skills/shenbi-review-group-craft/SKILL.md:237`「＝G4 口径…单一阈值来源」自 #118 T4 起失实；矛盾窗=密度∈(1.0, 5/wc×1000]（当前语料 max 0.809＝窗空、零现行浪费——文档完整性＋未来防护项）。

**触及的不变量维度**：门检面（#93 单源纪律——纯形谓词与 review 预算均单源派生）＋测量面=执法面口径（#116 C3 原则）。

## 立项预答栏（v7.1 义务）

**④ 博弈路径清单**（假设本件全部实施，根因「比对池含历史层变体致测量失真」能否复发）：
- 新变体后缀再污染（-rev2/未来新形态）→ 纯形**白名单**（`chapter-NN.md` 数字精确形）非黑名单——新后缀自动落在池外；复发路径闭；
- 变体名文件藏重复逃逸检测（红队注记）→ 理论面：章文件命名由管道控制（drafting 恒写 `chapter-N.md`；-pre-rev 为管道修订备份产物非模型可选输出位）；仓内三先例（g6.py:83-86/triggers.py:110/dispatch_helper.py:1701）已视 pre-rev 为历史层；残余面记 baseline 期望点火带观察；
- review 预算再漂移 → T2 预算**从常量派生**（非第二份字面），`TRANSITION_CAP_PER_1000` 改动自动传导；re-pin 测试锁派生关系。
- **结论：无仍通路径**（白名单形＋派生形双闭）。

**⑤ 候选机制清单**（buy-before-build）：
- 纯形判定 → **复用 replay `_pure_chapter` 既有谓词**——但现居 tools/（src 不可 import tools）→ 最小搬移：谓词单源化到 `src/shenbi/gates/shared.py`，replay 与门同引（覆盖 ~100%，不新建）；
- pre-rev 排除 → 仓内三先例模式（本件取纯形白名单，先例仅作语义佐证）；
- review 预算派生 → `math.ceil(TRANSITION_CAP_PER_1000 * wc / 1000)` 单式，无既有更优机制（lint_threshold_reconciliation 为 CONSTELLATION 单带工具，#118 已证不覆盖此面）。
- **结论：两件复用一件最小搬移，无 ≥60% 重叠既有物可整件升格。**

---

## 0. 根因

#118 T7 修复死门后取到的首份真实点火暴露：比对池 glob（`chapter-*.md`）把管道修订备份层（pre-rev）当活章比对——历史层与活层同池，测量面≠执法面（replay 分母 `_pure_chatter` 纯形 50 vs 门池 82）。review 预算面为 #118 触面纪律（不扩大裁定范围）正确拒绝就地修的遗留——本件是裁定后的机械执行面。

## 1. 任务分解（每 task：实现＋红测＋重跑 gate-power 刷点火带＋baseline 行同步）

### T1 · uniqueness 纯章形池过滤＋谓词单源
- `src/shenbi/gates/shared.py` 新增 `is_pure_chapter(stem: str) -> bool`（`chapter-NN.md` 数字精确形——语义=replay `_pure_chapter`，搬移单源化）；`tools/gate_power_replay.py` 的 `_pure_chapter` 改引 shared（测量面=执法面同谓词）；
- `_check_content_uniqueness` 比对池：`chapters_dir.glob("chapter-*.md")` → 纯形过滤（`[p for p in ... if is_pure_chapter(p.stem)]`）；**40% 阈与指纹口径不动**；SKIP 两分支（目录缺席/基数≤1）基数口径随池口径同变；
- 判据：红测（同目录放 `chapter-1.md`＋`chapter-1-pre-rev.md` 近全同稿——断言 pre-rev **不入池**不触发 FAIL；纯形双侧仍在时 content_overlap 仍红——负例复用既有 duplicated fixture）；50 章重跑 **FAIL 32→0**（纯池 0/50 已被 audit-T8 独立预证）；baseline uniqueness 行期望点火带回填「FAIL=真实跨章重复（现语料 0）」＋FINDING② 已执行注记。

### T2 · review 预算单源派生＋SKILL 措辞清偿
- `review_checklist.py:386` `transition_budget = max(5, wc // 1000)` → `math.ceil(TRANSITION_CAP_PER_1000 * wc / 1000)`（import 自 chapter_drafting 单源）；`skills/shenbi-review-group-craft/SKILL.md:237` 措辞改指常量（「预算=G4 `TRANSITION_CAP_PER_1000` 派生」）；
- 判据：`tests/unit/pipeline/test_review_checklist_precompute.py:82` re-pin（派生关系锁：wc=3200→预算 ceil(3.2)=4；wc=2008→ceil(2.008)=3——与门口径一致断言）；SKILL 文本改动过 `just lint-contracts`（纯散文面无 reads/writes 变更）；post118 矛盾窗（密度∈(1.0,5/wc×1000]）自本 task 起闭合。

## 2. 验收
1. T1-T2 判据全绿（红测双向＋50 章重跑＋baseline 同步）；
2. diff 面止于：`gates/shared.py`（新谓词）＋`chapter_drafting.py`（`_check_content_uniqueness` 一函数）＋`gate_power_replay.py`（谓词改引）＋`review_checklist.py`＋SKILL.md 一行＋三测试文件＋baseline——无未裁定面；
3. `just check` 全绿。

## 3. 风险
- 谓词搬移的调用方兼容：replay/tests 现引 `_pure_chapter` 处改引点一次清（grep 全调用方）；
- SKILL.md 触碰触发契约 lint 面（散文改动零契约变更——预期 diff 空，若 lint 报 reads/writes 则回查）；
- 单书语料（B5）：纯形池口径随跨书布局复核（若新书用不同章文件命名约定需重定标——记 baseline 注释）。
