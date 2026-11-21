# Spec #119 · post-118 标定收尾（post118-calibration-cleanup）：uniqueness 纯形池过滤＋review 预算单源接线

**日期**：2026-11-21｜ **系列**：spec #118 两项 FINDING 回裁落地（用户 2026-11-21 裁定，专家团四席推荐）｜ **状态**：Done (PR #376)（r1.1，2026-11-22——阶段 3 设计审查三 I 修订；r1 立项 2026-11-21）｜ **优先级**：🟡 P2（常规排，#110 之后不插队）

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
- review 预算派生 → `math.ceil(TRANSITION_CAP_PER_1000 * max(wc, 1) / 1000)` 单式，无既有更优机制（lint_threshold_reconciliation 为 CONSTELLATION 单带工具，#118 已证不覆盖此面）。
- **结论：两件复用一件最小搬移，无 ≥60% 重叠既有物可整件升格。**

---

## 0. 根因

#118 T7 修复死门后取到的首份真实点火暴露：比对池 glob（`chapter-*.md`）把管道修订备份层（pre-rev）当活章比对——历史层与活层同池，测量面≠执法面（replay 分母 `_pure_chapter` 纯形 50 vs 门池 82）。review 预算面为 #118 触面纪律（不扩大裁定范围）正确拒绝就地修的遗留——本件是裁定后的机械执行面。

## 1. 任务分解（每 task：实现＋红测；**gate-power 重跑为批级一次**——T1 后执行（T2 零门触面），报告落 `reports/<日期>-gate-power-vol1-post119.md`，baseline 最近回放指针整表重指（post118 先例）；baseline 两 FINDING 行注记已随立项 PR #372 预落——T1 后核期望列即可）

### T1 · uniqueness 纯章形池过滤＋谓词单源
- `src/shenbi/gates/shared.py` 新增 `is_pure_chapter(stem: str) -> bool`（`chapter-NN.md` 数字精确形——语义=replay `_pure_chapter`，搬移单源化）；`tools/gate_power_replay.py` 的 `_pure_chapter` 改引 shared（测量面=执法面同谓词）；
- `_check_content_uniqueness`（`src/shenbi/gates/g4/chapter_drafting.py:1126`）比对池：`chapters_dir.glob("chapter-*.md")` → 纯形过滤（`[p for p in ... if is_pure_chapter(p.stem)]`）；**40% 阈与指纹口径不动**；SKIP 两分支（目录缺席/基数≤1）基数口径随池口径同变；
- 判据（r1.1 改写）：红测三面——① pre-rev 不入池：tmp_path 放 `chapter-1.md`＋`chapter-1-pre-rev.md` 近全同稿，断言不触发 FAIL 且行走 SKIP 分支（r 含「基数」）**或**加第二纯形章使比对真跑断言 PASS（过滤与 SKIP 两机制不混一个断言）；② 纯形双侧仍红：tmp_path 构造两个纯形近全同章（G0.9 结构性输入允许面——负例语义复用既有 duplicated fixture 的「13 段 append」构造法，不复用其文件名形态）；③ **既有测适配**：`tests/unit/gates/g4/test_gate_power_negatives.py::test_content_duplicated_fails_content_overlap_gate`（fixture 池 `tests/fixtures/gate-power/chapters/` 过滤后塌缩至纯形 1 → SKIP）须适配——fixture 增补纯形比对章或测试重构，保持 content_overlap 红测有效；50 章重跑 **FAIL 32→0**（纯池 0/50 已被 audit-T8 独立预证）；baseline uniqueness 行期望列核对（「FAIL=真实跨章重复（现语料 0）」）。

### T2 · review 预算单源派生＋SKILL 措辞清偿
- `review_checklist.py:386` `transition_budget = max(5, wc // 1000)` → `math.ceil(TRANSITION_CAP_PER_1000 * max(wc, 1) / 1000)`（import 自 `src/shenbi/gates/g4/chapter_drafting.py` 单源；`max(wc,1)` 镜像门侧 :998 护栏——wc=0 退化态不产「零转折也 ERROR」假阳）；比较语义钉死：**转折计数 ≥ 预算即 ERROR（预算=首个失败计数）**——非整千 wc 与门 FAIL 精确对齐、整千 wc 严一词（保守向：门 FAIL 章必不漏过 review）；`skills/shenbi-review-group-craft/SKILL.md:237` 措辞改指常量派生（「预算=G4 `TRANSITION_CAP_PER_1000` 派生：`ceil(CAP×max(wc,1)/1000)`，计数 ≥ 预算即 ERROR」）；`skills/shenbi-chapter-drafting/anti-ai-reference.md:22` 第三处退役公式副本（「G4 单一口径 max(5,·)」失实声明，被 drafting SKILL.md:109 活引用）同步清偿改指常量派生（r1.1 扩面——价值门裁定 (a)）；
- 判据（r1.1 补全）：`tests/unit/pipeline/test_review_checklist_precompute.py` re-pin 面=**:25-29 公式级钉**（`expected = max(5, wc // 1000)`）＋**:71-83 整测**（含 :83 `>= 5` 断言——新公式下 wc=999/1000 预算 1 必红；逐例新期望 999→1/1000→1/4999→5/6000→6/9000→9）＋边界测测名/docstring 同步（旧「G4's max(5, wc//1000)」措辞改派生口径；wc=6000 整数边界保守一格注记）；SKILL/anti-ai-reference 文本改动过 `just lint-contracts`（纯散文面无 reads/writes 变更）；post118 矛盾窗（密度∈(1.0,5/wc×1000]）自本 task 起闭合（保守向闭合——review 永不宽于门）。

## 2. 验收
1. T1-T2 判据全绿（红测双向＋50 章重跑＋baseline 同步）；
2. diff 面止于：`gates/shared.py`（新谓词）＋`src/shenbi/gates/g4/chapter_drafting.py`（`_check_content_uniqueness` 一函数）＋`gate_power_replay.py`（谓词改引）＋`review_checklist.py`＋review-group-craft SKILL.md 一行＋**anti-ai-reference.md 一行（r1.1 扩面）**＋测试文件（`test_review_checklist_precompute.py` re-pin＋gate_power_negatives 红测/适配＋谓词新测，G0.9 结构性输入走 tmp_path）＋（如需）`tests/fixtures/gate-power/chapters/` 纯形比对章增补＋baseline＋新 replay 报告——无未裁定面；
3. `just check` 全绿。

## 3. 风险
- 谓词搬移的调用方兼容：replay/tests 现引 `_pure_chapter` 处改引点一次清（grep 全调用方）；
- SKILL.md 触碰触发契约 lint 面（散文改动零契约变更——预期 diff 空，若 lint 报 reads/writes 则回查）；
- 单书语料（B5）：纯形池口径随跨书布局复核（若新书用不同章文件命名约定需重定标——记 baseline 注释）。
