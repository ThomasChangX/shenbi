# Spec #88 · 门禁 finding 契约（gate-finding-contract）：id 前缀恒不变 + 严重度分类改精确 id（不靠 prose 子串）

**日期**：2026-11-01（r2 修订 2026-11-02：T3 由「键重写」改判「删冗余键+精确 id 匹配」，T1 契约收窄为唯一必需不变量）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #3 卡；亲验：chapter_drafting.py:651-652 事故注释（spec #83 T9「path-first 形态使 check_id() 提取失效、shadow 静默失灵」）；`G4_CHECK_MAP` 28 键全文（:796-831）；真实 id 清单（§1.3）

**触及的不变量维度**：无（门禁元层——finding 发射格式与严重度路由；不改任何检查的判定语义）

---

## 0. 根因

门禁契约是「返回 JSON 字符串」，但 must_fix **字符串格式本身**是承重接口：5 个消费者用正则/子串抠语义（shadow.check_id、chapter_loop._extract_check_id 逐字复制品、G4_CHECK_MAP 子串分类、G4_FORMAT_EXAMPLES 反馈模板、startswith("G4.") 路由）。发射侧仍多形态并存——**且普遍缺 `G4.` 前缀**（r2 亲验，比原稿更严重）：

| 形态 | 实例 | 位置 | shadow.check_id 结果 |
|---|---|---|---|
| 无 G4 前缀 + 中文详情 | `f"cd.prop_handoff:「{prop}」…"` | chapter_drafting.py:158 | **None（静默失灵）** |
| 无 G4 前缀 + 详情缀 | `f"cd.counter.plan_conflict{_detail_fp}:…"` | :241,:248,:268,:279 | **None** |
| `ss.facts_ops:…` | state_settling.py:773,776 | 无前缀 | **None** |
| `cp.prop_decl:{fp}:…` | chapter_planning.py:661 | 无前缀 | **None** |
| id-first（对） | `f"G4.cd.counter:{fp}:…"` | chapter_drafting.py:648 | `cd.counter` ✓ |

即：**spec #83 T9 只修了一处发射点，其余同类点仍在**——shadow 降级通道对 `cd.prop_handoff`/`cd.counter.*`/`ss.facts_ops`/`cp.prop_decl` 全部失效。这是同一个生产事故的未修完整面。

## 1. 契约定义（r2：只保留消费者真正需要的唯一不变量）

**唯一必需不变量**：must_fix 项以 `G4.<id>` 开头，`id` 匹配 `[a-z_][a-z_0-9]*(\.[a-z_0-9]+)*`。
- file/detail 槽位**不强制**语法（消费者不从字符串取文件；正文可含任意 `:`/中文符）——不在本 spec 发明新语法（原稿的 `id:file:detail` 三元文法属超需发明，废弃）。
- `shadow.check_id()` 与 `_classify_g4_failures` 的输入因此恒为可解析。

### 1.1 真实 id 清单（r2 采集，用于 T3 键重建；plan 期扩为全量）

已采集样本：`cd.prop_handoff` / `cd.counter.plan_conflict` / `cd.counter.base_mismatch` / `cd.counter.prose_mismatch` / `cd.counter` / `cd.title` / `cd.hook_unfulfilled` / `cd.protagonist_absent` / `cd.hook_type_rotation` / `cd.content_overlap` / `cd.no_visual_scene` / `file_not_found` / `ad.not_found` / `ap.not_found` / `bh.not_found` / `bsi.not_found` / `cc.not_found` / `XC.narration_name` / `ss.facts_ops` / `cp.sections` …

### 1.2 G4_CHECK_MAP 键结构（r2 关键发现）

28 键 = **23 HARD + 3 SOFT + 2 WARN**。而 `_classify_g4_failures` 的未匹配分支**已默认 HARD**（:846）——即 23 个 HARD 键全部冗余，与默认等价。真正携带语义的只有 **5 个覆盖键**：`transition`(S)/`fatigue`(S)/`cd.chapter_end_hook`(S)/`cp.golden`(W)/`cp.s5_choice`(W)。而这 5 个的匹配当前走**任意位置子串**（`key in item`）——任意消息含 "meta"/"transition" 即改判。**原稿「把 28 键全改成前缀形态再匹配」属过度施工；正解是删 23 冗余键 + 5 键精确匹配。**

## 2. 任务分解

### T1 · `G4.` 前缀补齐 + 输出契约 lint
- 补齐 §0 表中 4 类无前缀发射点（加 `G4.`；详情文本不动）；
- `gates/shared.py` 增 `finding(check_id, detail="", file="") -> str`（恒产 `G4.<id>` 前缀；detail 自由文本）——新代码用它，旧发射点按触碰迁移（**不一次性重写全部 33 checker**）；
- **输出契约 lint**（新测试，fixtures 语料驱动）：全部 g4 checker 的 must_fix 项逐条断言 `^G4\.[a-z_][a-z_0-9]*(\.[a-z_0-9]+)*`。首跑即红（现有 4 类违规点），修后绿。

### T2 · 解析侧去重
删 `chapter_loop._extract_check_id`（:852）→ import `g4.shadow.check_id`（同正则两 owner 归一；return-None 行为差异以 characterization 钉死）。

### T3 · 分类改精确 id + 键集瘦身
- 匹配改 `id == key or id.startswith(key + ".")`（点边界最长前缀）；
- **删 23 个 HARD 键**（与默认等价）；保留 5 个非 HARD 覆盖键，键名保持现值（`transition`/`fatigue` 等与真实 id 已一致——亲验 `G4.transition:`/`G4.fatigue:` 的 id 恰为 `transition`/`fatigue`）；
- **id 清单化防漏**：plan 期全量采集（全部 checker × fixtures 语料）落 `tests/fixtures/g4-id-inventory.json`；配两条断言——(a) 每个覆盖键必须出现在清单（防陈旧键）；(b) **行为不回归表**：旧子串匹配下被判 SOFT/WARN 的 id 集合 vs 新精确匹配结果 diff 为空（若出现 `cd.transition_budget` 类被旧键意外捕获的 id，显式补键或记为有意变更）；
- 未匹配 → HARD 默认不变。

### T4 · G2/G4 字数双 finding 互引去重
G4.cd 字数族失败消息引用 `G2.6`（`G4.cd.word_count:… (≡G2.6)`），`_classify_g4_failures`/反馈模板对同缺陷两 id 去重——一个字数缺陷产一条重试反馈。**不删任何一层检查**（分层校准属设计内）。

### T5 · shadow 回归参数化
spec #83 T9 铁律测试扩为全 checker 参数化：任一 checker 输出的 must_fix 项 `shadow.check_id()` 必须非空。

## 3. 验收

1. T1 输出契约 lint 绿（0 条违规）；
2. `grep -rn 'mf.append(f"{fp}\|f"cd\.\|f"ss\.\|f"cp\.prop_decl' src/shenbi/gates/` 零输出（无前缀发射清零）；
3. `_extract_check_id` 全仓唯一定义（shadow）；
4. `G4_CHECK_MAP` 恰 5 键且全为非 HARD 覆盖；`g4-id-inventory.json` 两断言绿；
5. 字数缺陷重试反馈恰 1 条（红测）；
6. `just check` exit 0。

## 4. 误报成本

无新 FAIL 门于生成路径（输出契约 lint 是仓库自检面，CI 红，不触运行项目）。T3 若 diff 出行为变化，必为已记录的有意变更（T3-b 断言强制记录）。
