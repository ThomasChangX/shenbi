# Spec #88 · 门禁 finding 契约（gate-finding-contract）：id 前缀恒不变 + 严重度分类改精确 id（不靠 prose 子串）

**日期**：2026-11-01（r2 修订 2026-11-02：T3 由「键重写」改判「删冗余键+精确 id 匹配」，T1 契约收窄为唯一必需不变量；**r2.2 2026-11-02 全量对抗式审计修订**——shadow.check_id 有 fallback 从不返回 None（动机表重写）、发射拓扑分层（helper 无前缀是设计）、纯中文 id 面、5 覆盖键仅 2 真活、T4 前提不成立改判；**r2.3 2026-11-14 价值门驳斥修订**——键数 28→29（`invalid_chapter_role` 系 #95 T1 于 2026-11-04 后加）/T2 补第三正则副本 `tools/lint_shadow_promotion.py:74`/path-first「soft-tracker key 变路径」降级为潜伏危害（cd.prop_handoff 属 HARD 不进 soft_fails）/T1 补 AST lint 假阴性面登记义务/收编第 6 消费者 `_failure_family_id` 截断自证/行号锚按 #87 拆分后树重锚）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.3 Revised 2026-11-14） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #3 卡（会话工作态审计，未入库——承重主张全部有代码亲验锚，r2.3 驳斥复核记录在 .superpowers/sdd/progress.md）；亲验：chapter_drafting.py:716-717 r5.3 path-first 事故注释（r2.3 重锚）；`G4_CHECK_MAP` 29 键全文（chapter_loop.py:812-848，r2.3 重锚）；r2.2 审计对 shadow/发射点/覆盖键逐条实跑；r2.3 驳斥五问复核（fresh-context 68 工具调用 + 协调者 VERIFY）

**触及的不变量维度**：无（门禁元层——finding 发射格式与严重度路由；不改任何检查的判定语义）

---

## 0. 根因（r2.2 重写：问题不是「None」，是「错 id + 错分流」）

门禁契约是「返回 JSON 字符串」，must_fix **字符串格式**是承重接口：5 个消费者用正则/子串抠语义（shadow.check_id、chapter_loop._extract_check_id 逐字复制品、G4_CHECK_MAP 子串分类、G4_FORMAT_EXAMPLES 反馈模板、`startswith("G4.")` 路由）＋**第 6 消费者（r2.3 收编）**：`_failure_family_id`（chapter_loop.py:1200）——docstring 自证 `[a-z_.]+` 首数字截断（"truncates at the first digit"）已用 split-colon 自救，是截断实害的仓库内自证。**r2.2 实测纠正**：`shadow.check_id`（shadow.py:62-65）有 fallback——`re.match(r"G4\.([a-z_.]+)")` 失败时取 `item.split(":",1)[0].replace("G4.","")`，**从不返回 None**；真正的危害是取到**路径或裸家族名**：

| 形态 | 实例 | 位置 | 真实后果（r2.2 实跑） |
|---|---|---|---|
| path-first（helper 返回无前缀，调用点拼路径） | `f"cd.prop_handoff:「{prop}」…"` → 调用点 `f"{fp}:{issue}"` | helper chapter_drafting.py:207-208；调用点 **:683**（r2.3 重锚） | `check_id` → `"chapters/ch025.md"`（路径当 id）；`_enrich_g4_feedback`（chapter_loop:1153-1182，`f.split(":")[0]`）查不到格式示例；**潜伏（r2.3 降级）**：soft-tracker key 变路径——cd.prop_handoff 属 HARD 类不进 soft_fails（:4701-4702），当前不可达；该 id 未来入 GATE_TO_SHADOW_KEY 时 shadow 静默失灵（chapter_drafting.py:716-717 r5.3 注释同口径） |
| 无前缀家族名 | `ss.facts_ops:…` | state_settling.py:889/:904（r2.3 重锚） | → `"ss.facts_ops"`（可解析，但 `startswith("G4.")` 分流走错）；同类还有 **:434/:838/:841/:878/:908/:921/:940/:961(ss.prop_row_match)/:971/:996/:1000/:1013/:1019(ss.identity_row_match)**——入口 `g4_state_settling`（:1084）直接 `mf.extend(_issues)`（:1134）无拼装 |
| 无前缀家族名 | `cp.prop_decl:…` | chapter_planning.py:753 **与 :759**（r2.3 重锚） | → `"cp.prop_decl"`（可解析但无 G4 前缀） |
| **纯中文无 id**（r2.2 新增面） | `XC:chapter-1.md:角色「X」正文用「她」而卡为男性代词…`、`称谓违例（…）: …` | cross_chapter.py:982（`mf.extend(f"XC:{ch_path.name}:{i}")`，r2.3 重锚） | `check_id` → `"XC"`（仅家族名）；**这类项根本没有机器 id**，加前缀之前须先**新发明 id**（消息语义变更） |
| 分层契约（不是违规点） | `cd.counter.plan_conflict*` helper 返回无前缀，调用点 :718-719 `mf.extend(f"G4.{issue}" …)`（r2.3 重锚） | chapter_drafting.py:249-283（helper 族） | 最终 must_fix 是 `G4.cd.counter.*`，**可解析**——r2 把它们列为「无前缀违规」属误判；post_declarations.py:59-67 docstring 明写该分层契约（helper 返回无前缀、调用方 id-first 拼装）；**r2.3：spec #83 T9 已把 counter 族按此契约落地（活样板）** |
| id-first（对） | `f"G4.cd.counter:{fp}:…"` | chapter_drafting.py:648-649 | ✓；同类还有 :757/:791/:814（`f"G4.{_id}:{fp}:{detail}"` 变量 id-first，#83/#95 后新增） |

**结论（r2.2）**：真实缺陷 = ①path-first 一项；②ss./cp. 家族名一批；③纯中文项一批（需新 id）；④`GATE_TO_SHADOW_KEY` 不含 prop_handoff/ss.facts_ops/cp.prop_decl/XC（本就无降级面——不是「降级通道失效」）；⑤六个消费者各自解析（r2.3：收编 `_failure_family_id`）。**修法核心不是给 helper 无脑加前缀（会造 `G4.G4.`），而是把「id 产生」收进单一发射器。**

## 1. 契约定义（r2.2：id 字符集须与消费端正则同批对齐）

**唯一必需不变量**：must_fix 项以 `G4.<id>` 开头，`id` 匹配 **`[a-z0-9_][a-z0-9_.]*`**（r2.2 修正：r2 写 `[a-z_][a-z_0-9]*` 但 `shadow.check_id` 实为 `[a-z_.]+`——**无数字**，`G4.cc.p1p2_empty` 被截成 `cc.p`、`G4.cp.s7_hook_ops` 截成 `cp.s`；本批须同批把 shadow 正则改 `[a-z0-9_.]+`）。
- file/detail 槽位**不强制**语法（消费者不从字符串取文件）。
- **发射拓扑分层（r2.2 新增）**：helper 函数返回 `(id, detail)` 元组或直接调 `finding()` 产完整串；**禁止在 helper 加 `G4.` 再由调用点拼**（双前缀）。T1 先按拓扑分类全部发射点，再改。

### 1.1 真实 id 清单（r2.2 扩：含数字 id 与纯中文家族）

`cd.prop_handoff` / `cd.counter.plan_conflict` / `cd.counter.base_mismatch` / `cd.counter.prose_mismatch` / `cd.counter` / `cd.title` / `cd.hook_unfulfilled` / `cd.protagonist_absent` / `cd.hook_type_rotation` / `cd.content_overlap` / `cd.no_visual_scene` / `cd.no_hook`（`cd.chapter_end_hook` 键对应的**真实失败 id**）/ `cc.p1p2_empty` / `cp.s7_hook_ops` / `file_not_found` / `ad.not_found` / `ap.not_found` / `bh.not_found` / `bsi.not_found` / `cc.not_found` / `XC.narration_name` / `ss.facts_ops` / `ss.prop_row_match` / `ss.identity_row_match` / `cp.sections` / `cp.prop_decl` / `cp.chapter_role` …（plan 期以 AST 枚举全量落 `tests/fixtures/g4-id-inventory.json`；**纯中文项须在本批新发明 id**，如 `XC.pronoun_mismatch`/`XC.title_violation`——语义变更记 deviation）

### 1.2 G4_CHECK_MAP 键结构（r2.2 关键更正）

29 键 = **24 HARD + 3 SOFT + 2 WARN**（r2.3：r2.2 时为 28/23；`invalid_chapter_role` 系 spec #95 T1 于 2026-11-04 后加，commit 3900bb8b）；`_classify_g4_failures` 未匹配分支**默认 HARD**（:868-869）——24 个 HARD 键全部冗余（显式键与默认等价）。真正携带 must_fix 语义的只有 **2 个**：`transition`(S)/`fatigue`(S)。**r2.2 实跑更正**：`cd.chapter_end_hook`/`cp.golden`/`cp.s5_choice` **只出现在 `checks[]`**（chapter_drafting.py:1093、chapter_planning.py:909/:1000/:1007；must_fix 真实 id = `G4.cd.no_hook` chapter_drafting.py:1101-1104 等），其失败 must_fix 的 id 分别是 `cd.no_hook` 等——这 3 键对 must_fix 分类是**死键**（r2 称「5 键携带语义」不成立；r2.3 穷尽 grep 复核=src 域 must_fix 面零出现成立）。且 `cd.post_transition_cross`（post_declarations.py:112 发射 → chapter_drafting.py:814 `G4.` 拼装）含子串 `"transition"` → **今天已被误判为 SOFT**（应为 HARD；全链=shadow:false 转正 → 分类器 `:841` SOFT 键子串命中）——这是 T3 的已知案例，修精确匹配时记录为「有意修正」。

## 2. 任务分解

### T1 · `G4.` 前缀补齐 + 输出契约 lint（**先拓扑分类**）
- **拓扑分类（r2.2 前置）**：AST 枚举全部 `mf.append/extend` 发射点（r2.3 实测约 213 处，gates/g4/*.py 全域），分三类——(a) helper 返回无前缀→调用点拼（chapter_drafting:249-283 helper 族 + :718-719 调用点，**不动**；#83 T9 counter 族活样板）；(b) 直接产 must_fix 的裸家族串（chapter_drafting :683 path-first、state_settling 全部 ss. 点、chapter_planning :753/:759）→ 改 id-first；(c) 纯中文项（cross_chapter :982）→ 先定 id 再发；
- `gates/shared.py` 增 `finding(check_id, detail="", file="") -> str`（恒产 `G4.<id>`），新代码用它；旧发射点按触碰迁移（不一次性重写全部 33 函数）；
- **输出契约 lint**（新测试）：AST 断言所有进入 must_fix 列表的字符串由 `finding()` 或 id-first 常量产生；首跑红（现有违规面），修后绿。**不用 fixtures 语料驱动**（33 个 checker 签名异构、多数缺 project_dir 走降级分支，覆盖率虚高）。**假阴性面登记（r2.3，lint_truth_format 惯例）**：单遍 AST 无数据流——跨函数间接（helper 内 append + 调用点 extend 变量，state_settling 现行形态）与 BinOp/`str.format`/`%` 拼接不可判，登记为已认可残余风险；运行时兜底 = T5 参数化断言（extracted id ∈ inventory）构成纵深。

### T2 · 解析侧去重（r2.2 更正判据）
`chapter_loop._extract_check_id`（:873-876；消费者唯一=soft-tracker key 提取 :4702）与 `shadow.check_id` 是**逐字同构**（含同一 fallback，两者都永不返回 None）——删前者、import 后者，判据=全仓唯一正则 owner（不是「return-None characterization」）。**r2.3 补第三副本**：`tools/lint_shadow_promotion.py:74` 另有一份 `re.match(r"G4\.([a-z_.]+)"`（or 双 pattern，解析 trace WARN payload）——同批改 import `check_id`（`[shadow]` 前缀剥除逻辑保留其侧）或同步改正则，否则「唯一 owner」判据不穷尽、数字截断在 lint 侧复发；chapter_loop.py:1206 `_failure_family_id` docstring 对 `_extract_check_id` 的文字引用随删除改写。**同批**把 shadow 正则从 `[a-z_.]+` 改 `[a-z0-9_.]+`（见 §1）。

### T3 · 分类改精确 id + 键集瘦身（r2.2 改判：2 活键）
- 匹配改 `id == key or id.startswith(key + ".")`（点边界最长前缀）；
- **删 24 个 HARD 键**（r2.3：含 #95 T1 后加的 `invalid_chapter_role`；与默认等价）；保留 **2 个 must_fix 活键** `transition`/`fatigue`；`cd.chapter_end_hook`/`cp.golden`/`cp.s5_choice` 三个 checks-only 键**移出分类映射**（在 checks 分类处直用，注释说明不参与 must_fix）；
- **id 清单化防漏**：plan 期全量采集落 `tests/fixtures/g4-id-inventory.json`；断言——(a) 每个保留键出现在清单；(b) **行为不回归表（item 字符串级）**：子串匹配依赖整条 item（路径/中文详情），id 集合 diff 不足以复现旧行为；语料=fixtures 真实 must_fix+合成对抗串，冻结后做 **property test**：「任何被判 SOFT/WARN 的 item，其 extracted id ∈ 覆盖键集」——把一次性快照升级为持续不变量；`cd.post_transition_cross` 记为**有意修正**（旧=SOFT 误判，新=HARD）；
- 未匹配 → HARD 默认不变；
- **连带测试（r2.2 补；r2.3 行号改准）**：`tests/unit/pipeline/test_g4_classification.py:22-26` 断言 `not_found`/`meta` == HARD——删 24 键即红，同批改写为精确匹配用例。

### T4 · 字数 finding 单一权威（r2.2 撤销原「双 finding 去重」）
**原设计前提不成立**：pipeline 模式**跳过 G2**（executor.py:245-253；outputs 由 G4/G6 验），G2 的 mf 是 **dict** 且失败只 `return 1`，**无 retry-feedback 通道**——两者永不共处一条反馈。改判：**floor 单一权威**——字数下限只在 `chapter_word_floor` 定义；G4.cd 字数失败消息在 detail 里注明 floor 来源（文本引用，不新建 dedup 代码）。**不删任何一层检查**。

### T5 · shadow 回归参数化（r2.2：非空断言恒真）
spec #83 T9 铁律测试扩为全 checker 参数化，但断言改为 **`check_id(item)` 等于期望 id 或 ∈ inventory**（「非空」恒真=空测）；含数字 id 语料（`cc.p1p2_empty`/`cp.s7_hook_ops`）必测。

## 3. 验收

1. T1 输出契约 lint 绿（AST 面，0 条违规）；纯中文项已获新 id 并记 deviation；
2. **r2.2 替换**：`_extract_check_id` 全仓唯一定义（shadow；`tools/lint_shadow_promotion.py` 同批改 import——r2.3）；shadow 正则含数字（`G4.cc.p1p2_empty`→完整 id 红测）；
3. `G4_CHECK_MAP` 恰 **2 个 must_fix 活键**（transition/fatigue）+ 3 个 checks-only 键移出；`g4-id-inventory.json` 两断言绿；`cd.post_transition_cross` 有意修正记录在案；
4. property test 绿（所有 SOFT/WARN item 的 id ∈ 覆盖键集）；**G4 字数失败 detail 含 floor 来源标注（红测）；无 G2/G4 dedup 代码**（r2.2：T4 已撤销双 finding 去重，原「恰 1 条」断言无对象）；
5. `just check` exit 0。

## 4. 误报成本

无新 FAIL 门于生成路径（输出契约 lint 是仓库自检面，CI 红，不触运行项目）。T3 若 diff 出行为变化，必为已记录的有意变更（T3-b 断言强制记录）。T1 的纯中文 id 新发明会改变 must_fix 文本（模型可见面变化）——在卷二开卷窗内属 prompt 行为变更，**须排在束4 验收后**（批次 A 殿后总序已覆盖）。
