# Spec #117 · 审计证据可验证性（audit-evidence-verifiability）：发现级四要素校验、引述逐字/行号指称/规则名对账、消费三态

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit · B 异模型元审）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：契约面 `skills/shenbi-review-group-craft/SKILL.md:267-276`（四要素：位置 `文件路径 L行号-行号`／原文引述 `>` ≥20 字／违反规则逐字／严重度；「缺失任一要素的缺陷报告视为不合格」）；门禁实现 `src/shenbi/gates/g4/generic.py:125-126`（仅 `re.search(r"(?:L\d+|line\s+\d+|:\d+|`[^`]+\.[a-z]+`)")`——**报告级、四选一、不验指称**）、`:129-137`（`has_rule` 只匹配「铁律/SKILL.md…」词形，不验规则名逐字存在）、`src/shenbi/pipeline/llm_output_integrity.py:173-192`（`check_audit_line_refs` 只验 `end <= max_line`，不验该行内容是否支持结论）、`src/shenbi/pipeline/audit_layer.py:253/:256`（`"BLOCKING" in content` / `"CRITICAL" in content` 消费严重度）；覆盖 `src/shenbi/gates/g4/review_resonance.py:36` 与 `src/shenbi/gates/g4/review_arc_payoff.py:50` 是仅有的两个专用 review 结构校验器——**12 个 active review 技能中 10 个**走 `g4_generic_generative`（存在/非空/≥50 字），bug-hunt 四要素形态检查仅在 `test_type=bug-hunt` 时生效；实测（vol1 **588 份章审计**全量只读回放，脚本附录 A）：四要素**形态**完备 64/588=**10.9%**（非饥饿子集 9.3%）、`>` 引述块 31.8%、规则名要素 23.6%、行号 94.0%；提取 ≥10 字引述 **2883** 条，在「全项目 md + 全部 SKILL.md」中逐字命中 2070 条（71.8%），**813 条（28.2%）在任何项目/技能文本中找不到逐字来源**；28 份报告的全部引述均不可解析；按 kind：group-craft 三产物四要素 5.3-11.4%、引述不可解析 21.8-33.7%；对照组 `audits/chapter-13-resonance.md`（有专用校验器）行号+引述+锚点+相对位置齐备而四要素启发式 0%——**四要素指标是契约形态率，不是证据缺失率**，这正说明契约与生产形态脱节、且门禁两端都不校验；历史前科 #109（96 份本轮 STARVED 词族口径的饥饿产物，另 49 份编造通过）证明「无正文也能出具判定」，本件处理**有正文但证据不可验证**的另一半；可用原语 `src/shenbi/gates/g4/quote_verbatim.py:21-25`（quote in prose + 空白归一）、`g4/verdict_fence.py`（围栏作用域，#113 同侧）。

**触及的不变量维度**：无（审计产物有效性基建——新 check id 族 `G4.av.evidence_*`，不挂叙事维度）

---

## 0. 根因

**审计层是体系的质量传感器，但传感器的输出只被形态校验。** 四要素契约（位置/原文引述/规则名/严重度）在门禁侧退化为「报告里任意出现一个像位置的字符串」；引述是否逐字、行号指向的句子是否支持结论、规则名是否逐字存在于被引 SKILL，全部无消费面。生产 review 路径（10/12 active 技能）更只有「文件存在、非空、≥50 字」。于是**编造证据、陈旧证据、真实证据在门禁前同价**：报告里的「证据」是自由文本，不是可验证事实；而下游 `audit_layer` 又只用 `"BLOCKING" in content` 做路由，等于把质量判决建立在未验证的字符串上。与 #109 的分工： #109 修「输入饿死」型 invalid；本件修「输入齐全但证据不成立」型。

**用户裁定（2026-11-15）**：不考虑在飞项目——588 份存量审计只回放报告（分布/交叉表），**不改写不补评不迁移**；新跑批才 enforce（显式声明路径）；零付费派发（纯确定性校验）。

**备选案已评估并否决**：「并入 #105 T2 llm_output_integrity 扩展」——#105 管 severity 词表单源/派发完整性/聚合条目级，证据四要素是不同契约（发现级 parser+指称对账+消费三态），并入会超载并拖慢 #105 的静默丢包修复；「报告级校验（任一 finding 合格即整篇合格）」——实测契约形态 10.9% 证明报告级正是漏洞；「让 LLM 判官审证据」——循环依赖（判官审判官），而逐字比对是确定性、零成本、可重放的。

## 1. 任务分解

### T1 · 发现级 parser（确定性）
- 把异构报告解析为 `findings[{location(path, Lrange), quotes[], rule, severity}]`，支持三类生产形态：group 族四要素块、表格行（texture/reader-pull 形态）、legacy `- [BLOCKING] …` 行；位置归一化支持 `L23-27` / `L约 236-262` / `第 3 场`；
- 解析失败 → `evidence_unparsed`（**可见**，不静默丢弃）；报告输出解析覆盖率与未解析行清单；
- 不写项目文件；报告落 `reports/`。

**判据**：对 vol1 588 份回放，解析覆盖率与附录 A 基线的 kind 分布一致（误差 <2pp）；未解析清单可枚举；同输入同输出。

### T2 · 校验器（新 `G4.av.evidence_*`，复用 quote_verbatim）
- `location`：path 存在；L 范围在文件内；引述（≥20 CJK、空白归一、允许多段拼接）在 L 范围内逐字出现；行号缺失但有引述 → 全章搜索并标 `line_unspecified`（容忍 `L约`/场次定位）；
- `quote`：≥20 字；`>` 块或表格引述均可（**格式容忍、语义从严**）；
- `rule`：报告所属 SKILL.md 中存在逐字规则名；失败 → WARN（命名漂移）；armed 下 FAIL；
- `severity`：走 #105 单源（`contracts/severity.py`）；
- `stale`：引述不在当前产物但在 snapshots/.bak 中命中 → `evidence_stale`（区分陈旧与编造）；无快照 → `evidence_unresolved_or_stale`（单态，文档声明）。

**判据**：红测五条（编造引述→`evidence_unresolved`；旧版引述→`evidence_stale`；合法表格引述→PASS；规则名漂移→WARN；≥20 字下限边界）；对真实 audit 文件的 fixture 回放（G0.9：真实产物）。

### T3 · 消费三态（validated / unvalidated / invalid）
- findings 标 `validated` / `unvalidated` / `invalid`（#109 T4 饥饿形态归 invalid）；只有 `validated` 的 BLOCKING/CRITICAL 驱动 revision 路由；
- `unvalidated` 可见但不路由；`review-summary` 报三类计数，**禁止净结论**（`Failed>0` 或 `unvalidated>0` 时不得输出「No BLOCKING…」，沿用 #109 T4 语义）；
- `audit_layer.py` 的 `"BLOCKING" in content` 消费面换成 validated 集（保留 raw 扫描为报告字段）。

**判据**：红测三条（unvalidated BLOCKING 不触发路由；validated 触发；review-summary 缺口披露行）；`git grep` 证明 audit_layer 不再以裸子串做路由。

### T4 · vol1 全量回放报告（只读）
- 588 份 → 四要素形态完备率 / 引述逐字率 / stale / unresolved-or-stale / unparsed 分布；与 #109 invalid 口径做交叉表（invalid×unparsed、valid×unresolved）；
- 输出「若 T2 上线，本批将有多少报告降为 unvalidated」的只报不写估算；
- 明确不生成迁移工具、不改写任何 audit 文件。

**判据**：报告落盘且数字与附录 A 一致；零项目写入（`git status` 不含 novel-xinghuo-vol1）。

## 2. 验收
1. T1-T4 判据全绿；
2. parser 覆盖三类形态；未解析可见；
3. 校验器红测五条；真实 fixture 回放零崩溃；
4. 消费三态接线：unvalidated 不路由、validated 路由、summary 披露；
5. 回放报告与 #109 invalid 口径交叉表；`git status` 证明未写项目。

## 3. 风险
- 解析异构（契约形态率 10.9% 说明形态漂移大）→ T1 先出覆盖率基线，parser 范围按基线钉死；未解析不得静默；
- 误伤（合法转述/省略号/跨行引述）→ 三态而非二态；`line_unspecified` 容忍；armed 前 shadow 报告一轮；
- 行号近似（`L约 236-262`、场次定位）→ 归一化 + 全章回退搜索；
- `stale` 依赖快照可得性（`snapshots/`/`.bak`）——无快照时单态 `unresolved_or_stale`，不得声称「编造」；
- **共享文件面**：`src/shenbi/pipeline/llm_output_integrity.py` 与 #105 T2 同文件——顺序 **#105 → #117**；`gates/g4/generic.py` 无在飞冲突（#88/#89 已完结）；`justfile 配方面` 与 #92/#116 共享——**#92 → #116 → #117**；`skills/shenbi-review-*/SKILL.md` 本件**不改文本**（契约已要求四要素，缺的是执行），避免与 #109 T1/#96 同文件冲突；
- 单书语料（B5 边界）：回放基线只对 vol1 成立，跨书迁移另议。

## 附录 A · 588 份章审计回放基线（2026-11-15）
| 指标 | 全量 588 | 非饥饿 492 |
|---|---:|---:|
| 四要素形态完备（启发式） | 10.9% | 9.3% |
| `>` 引述块（≥20 CJK） | 31.8% | 26.0% |
| 规则名要素（铁律/SKILL.md 词形） | 23.6% | 21.3% |
| 行号（`L\d+`/`line \d+`/`:N`） | 94.0% | 95.3% |
| ≥10 字引述总数 | 2883 | 2656 |
| 引述在全项目文本中逐字命中 | 71.8% | 72.3% |
| 引述不可解析 | 28.2% | 27.7% |
| 全部引述均不可解析的报告 | 28 份 | 17 份 |

按 kind（非饥饿，四要素形态率/引述不可解析率）：texture 8.6%/33.7%、reader-pull 11.4%/27.3%、anti-ai 5.3%/21.8%、resonance 0.0%/24.5%（有专用校验器；表格形态，形态率不适用）、sensitivity 22.7%/22.7%、memo-compliance 28.1%/29.1%、pov 0.0%/26.9%、dialogue 0.0%/33.9%。

**命令**：`uv run python /tmp/shenbi_b_audit/audit_evidence_census2.py`（只读 `novel-xinghuo-vol1/audits/*.md`、章/plan/全项目 md、`skills/**/SKILL.md`；引述正则 `「([^」]{10,})」`；饥饿词族 `待补|无法核对|无法完整审计|正文未提供|…`）。
