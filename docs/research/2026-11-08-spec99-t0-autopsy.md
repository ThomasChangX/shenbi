# Spec #99 T0 · 束7 settle 三连败 blob 验尸 + 判别法 + 标题语法表面盘点

**日期**：2026-11-08 ｜ **spec**：`docs/superpowers/specs/2026-11-08-spec99-settle-base-row-fidelity.md`（r4.2）§T0 ｜ **验收**：spec §2 验收 1
**取证方式**：全程离线（零 LLM 派发）——盘内 blob/dispatch/trace/ledger/quarantine 交叉分析 + 框架真实代码重放（`uv run python`，只读消费 `shenbi.pipeline.dispatch_helper._increment_units` / `shenbi.pipeline.truth_io.upsert_markdown_row` / `shenbi.gates.g4.state_settling`；重放工件写 `/tmp`，repo 零改动）。

---

## 0. 工件清单与自校验

四次派发（`novel-xinghuo-vol1/observability/dispatches/`，模型均 deepseek-flash，finish_reason=stop，attempt 字段均=1——重派队列每派新起，派内重试进度以 prompt 反馈块计数为准）：

| 派 | dispatch | trace seq | ts (UTC) | user_prompt_blob（盘上字节/解码字符） | response_blob（盘上字节） |
|---|---|---|---|---|---|
| 首派 | `00255-shenbi-state-settling-ch047-a1.json` | 1214 | 2026-11-08T01:45:52 | `c4fe26a1…` 139112B/59467ch | `c7e9d718…` 20276B |
| a1 重派 | `00264-shenbi-state-settling-ch047-a1.json` | 1231 | 02:01:50 | `29053cec…` 140578B/60247ch | `e0cf9604…` 14267B |
| a2 重派 | `00265-shenbi-state-settling-ch047-a1.json` | 1233 | 02:11:05 | `aa91eee2…` 146035B/62701ch | `8600f0fa…` **20665B** |
| a3 重派 | `00266-shenbi-state-settling-ch047-a1.json` | 1235 | 02:19:19 | `ee3d214a…` 146468B/63035ch | `fa7b451f…` 18000B |

九个 blob 全在 `novel-xinghuo-vol1/observability/blobs/`，逐一 `shasum -a 256` 自校验通过（与 dispatch JSON 内哈希一致）。system prompt 四派同 blob `82c14e27…`（30614B）。时序链：00255（settle 过检落账）→ 评审组 00256-00260 → 修订 00261-00263（audit-routed revision）→ **re-settle 三连败 00264/265/266** → 评分链 00267-269（trace seq 1237-1242）→ 台账裁决 #19 手术收束（vol1-ledger.md 束7 节）。

**r4.2 勘误复核**：「三派 response 逐字节相同」精确化为——**三派 response 的 47 块改写形逐字一致**（差异仅 a1 少 48 块、多 1 个空行与 1 行交互表行），**a2/a3 的 character_matrix 输出整体逐字节相同**（869 chars）；三派 response blob 整体大小不同（14267/20665/18000B，其余 8 个 truth 文件各派有差异）。逐字性主张成立，逐字节主张按此口径收窄。

---

## §1 三派证据链（a1=00264 / a2=00265 / a3=00266）

### 1.1 a1（00264）：读 live，重写自陈行，无反馈在场

**prompt 基底**（`29053cec…`，60247 chars）：reads 含 `truth/character_matrix.md`（live，非 staging）。matrix 投影段（`<untrusted-source path="truth/character_matrix.md">`，10218 chars，起于 blob 字符偏移 ~12230）尾部行集：

```
（blob 偏移 21501）## 第 47 章状态增量
（偏移 21504 = 「第」字位；spec r3 记 @21504 即此口径）
### 那罕（林烽）
- 当前位置: 石沟驿公事房（站房西头那间小屋住）
- 当前状态: 在役；过站归他记，本章兼补旗号一栏
- 时间锚: 二月初八
- 本章所接: 过站文书十七页（十四页填、三页空）；赵瘸子的四格旗号抄样
- 本章所记: 私账「债」页三行（合济号／四格留添名／经手人「崔」字），抄样折四折夹在页间露一角
- 情感主调: 按兵不动；认出而「不嚷，只记」
- 心口一句: 「喊是嗓子的事，记才是账的事。」／「此账必有还之日。」
- 未解: 「崔」是谁；三页空白是哪个队；左下一格留给谁
### 赵瘸子（石沟驿老驿卒）
- 当前状态: 在役；授旗号抄样、点卯念号
- 本章所教: 旗号是商队打的旗、旗下有字号、字号底下有印；「旗号一栏不许空着交上去」「认出来也别嚷。嚷了不落墨，等于没认」
（偏移 21870，行内含 spec r3 记的 @21872——同一行，计数口径差 2 字符）
- 自陈: 「我描的。描了十一年，就记下这么一家。」
- 本章一收: 「添了名的，就不是货的事了。」
（偏移 21921）## 第 48 章状态增量   ← 47 块区间 [21501, 21921)，共 20 行
```

要点：**live 47/48 块标题均为空格形** `## 第 47 章状态增量`／`## 第 48 章状态增量`。

**response**（`e0cf9604…`，`staging/truth/character_matrix.md` 552 chars）= 1 行交互总表行（那罕×崔，与 live 同键同文）+ 47 块（430 chars，**无 48 块**——「a1 未重发 48 块」实证）。改写形（改写前后原文）：

```
前（live/prompt）：- 自陈: 「我描的。描了十一年，就记下这么一家。」
后（response）  ：- 自陈: 「我描的。描了十一年，就记下这么一家的旗。旁的我懒得记。」
正文原句（chapters/chapter-47.md L66）：
「我描的。」赵瘸子说，「描了十一年，就记下这么一家的旗。旁的我懒得记。」
```

即模型按键 `自陈` 做 keyed-upsert，值替换为**更全的章内原句**（probe31 已裁定语义下的合法操作）。47 块内其余 18 个内容行逐字复现、同序。

**反馈在场性**：prompt 中「上次重派」计数 **0**。

### 1.2 a2（00265）：读 staging（自陈已是新形），重发双块，反馈 ×1

**prompt**（`aa91eee2…`）：reads 的 matrix 面变为 **`staging/truth/character_matrix.md`**（F-3 staging-first——a1 落 staging 后重派基座切换）。其投影段（10227 chars）内 47 块自陈行已是新形：

```
- 自陈: 「我描的。描了十一年，就记下这么一家的旗。旁的我懒得记。」
```

即 **a2 眼中的「基底」里旧句已不存在**（live 不再注入）——反馈令「旧句原样保留」与模型可见现实直接矛盾（矛盾指令死锁的读侧一半）。

**反馈在场性**：prompt 头部（偏移 787）「上次重派」×1，逐字：

```
上次重派输出未过 G4 结构门：['G4.ss.matrix_structure:novel-xinghuo-vol1/staging/truth/character_matrix.md:content_dropped:1行（去重后 1）——被丢行 verbatim 清单（原样保留于输出，作为基底行）：\n  - 自陈: 「我描的。描了十一年，就记下这么一家。」\n指令：以上行原样保留于输出（作为基底行），仅在其后追加本章新键行——不要重发整档，不要改写基底行。\n正例：live 已有 `| a | 1 |` 与 `| b | 2 |` 两行、本章新增键 c 时，输出=那两行原样+新行 `| c | 3 |`（不是重发 a/b 的改写）。 (合并基底=staged 副本，被丢行不会自 live 自动恢复——…)'
```

同一反馈串还含第二项：`G4.ss.hooks_structure:…pending_hooks.md:content_dropped:1行`，被丢行为 `- 证据（第 47 章）: chapters/chapter-47.md L60–L62 赵瘸子交下「旗号抄样，一页四格」…`（hooks 面同型，见 §5-dev7）。

**response**（`8600f0fa…`，20665B；matrix 输出 869 chars）= 47 块 + 48 块双块重发：47 块与 a1 逐字一致（仅块尾多 1 空行），**48 块与 live 48 块逐字节相同**（「a2 重发 follower 块且与 live 逐字同稿」实证）。

### 1.3 a3（00266）：读 staging（与 a2 所见逐字节相同），反馈 ×2，输出与 a2 逐字节相同

**prompt**（`ee3d214a…`）：matrix 面仍 `staging/truth/character_matrix.md`，其投影段 10227 chars **与 a2 prompt 内的逐字节相同**（sha256 前缀 `7f8882c8…` 同）——staging 已幂等稳定。反馈在场性：**「上次重派」×2**（偏移 787 与 2868，两条逐字相同——retry_failure_history 累积，束5 PR #291 机制）。

**response**（`fa7b451f…`）：character_matrix 输出与 a2 **整体逐字节相同**（869 chars）。

### 1.4 own-block 豁免失效的逐派影响——框架真实代码重放（本节核心验证）

重放方法（离线，零派发）：

```python
# /tmp 物化：live=现盘 truth/character_matrix.md（71343 chars）；逐派：
units = _increment_units(response["files"][character_matrix].content)  # dispatch_helper.py:2219
merged = reduce(
    lambda b, u: upsert_markdown_row(b, u, "角色A,角色B"), units, base
)  # truth_io 契约键（SKILL:56）
issues = state_settling._check_matrix_structure(staged_pf)  # sidecar {"chapter": 47}
# a2/a3 的 base=上一派 merged（staging-first 链，dispatch_helper.py:2714-2722）
```

结果（三派全部复现，**与 00265/00266 prompt 内嵌反馈逐字一致**）：

```
a1: content_dropped:1行（去重后 1）——被丢行 verbatim 清单：
      - 自陈: 「我描的。描了十一年，就记下这么一家。」
a2: 同上（一字不差）
a3: 同上（一字不差）
```

机制分解（对应 `state_settling.py` 现行代码）：

1. `_current_settle_chapter`（:295-313）从 sidecar 得 chapter=47；
2. `_strip_increment_section`（:316-333）正则 **:322** `re.compile(rf"^##\s*第{chapter}章状态增量\s*$")` 要求 `第47章` **数字两侧无空格**——live 标题系 `第 47 章` 空格形 → `heading_re.match` 恒 False → `inside` 恒 False → **47 块 20 行全部留在比对基底**（own-block 豁免静默失效；重放实测：strip 仅剥掉标题行本身 562 chars 中 0 行块体——`stripped` 仍含旧自陈行）；
3. `_dropped_content_lines`（:93-124）→ `_seq_drops`（:127-139）序保持扫描：47 块内 18 个同序 verbatim 行在 staged（被替换后的新 47 块）中按序命中（probe18 #005 指针语义），**仅差异行**（旧自陈行）在 staged 全文无命中 → 入清单恰 1 行；
4. `_format_drops`（:182-213）渲染三段式反馈——即 a2/a3 prompt 所见。

**反事实验证（④ 疗效预演）**：把 strip 换成容错形（`^##\s*第\s*(\d+)\s*章\s*状态增量\s*$`）后重跑 `_dropped_content_lines`：leader-only `{47}` 与 bundle `{47,48}` 两口径 **drops 均为 NONE（门过）**——同一 staged 文件、同一 live，唯一变量是标题语法容错。绿由④单独产生（T2(b) 归因的预证）。

**结论（§1）**：三派证据链闭合——模型行为三派一致且合法（own-block keyed-upsert 换更准引文），门反馈三派一致且恒红（旧句永远「被丢」），staging 视图与反馈指令互相矛盾且永无收敛路径。**H4 假阳性死锁成立，逐字级复现。**

---

## §2 首派 00255：空格形双块的起源

**prompt**（`c4fe26a1…`）matrix 投影段（8999 chars）内容 = 交互总表尾部 64 行（最新至 `| … | 第 46 章 |`）+ extractor 注记，**不含任何 `##` 增量块**（首次结算时 47/48 块尚不存在；matrix_scoped 只保 N/N+1 块）。模型可见的全部「第 N 章」字样均为**带空格形**（表行 `| 第 46 章 |`、`第 3-4 章` 等）。

**response**（`c7e9d718…`）`staging/truth/character_matrix.md`（1318 chars）创建双块（content 内偏移：47 标题 match 起点 **458**（`第` 字位 461），48 标题 **879**（`第` 字位 882）——spec r4「47@461/48@882」即 `第` 字位口径，复核一致）：

```
## 第 47 章状态增量        ← 空格形
### 那罕（林烽）…（自陈行= 旧形「…就记下这么一家。」，content 偏移 827）
## 第 48 章状态增量        ← 空格形
```

首派过检（trace seq 1214 DISPATCH→1215 AUDIT_PASS），落账后 live 47/48 块 = 00255 输出（现盘 live:1049-1092 与其逐字相同，仅 47/48 块间少 1 空行——合并层空行节奏归一）。要点：

1. **空格形是首派 00255 的模型自撰**，且当时 prompt 里没有任何无空格增量块范例可抄——唯一无空格教学面（#23 注入 `## 第N章状态增量`、SKILL 正文）竞争不过满屏带空格的表行；重试指引示例（chapter_loop.py:955，空格形）首派不在场；
2. 空格形经**过检落账**进入 live（门不校验标题语法——标题行在 `_content_stream` 里只是一行须逐字存活的普通内容行，自匹配自身）；
3. 此后写径精确匹配（§4-③）在同形替换下持续成功，空格形被 staging/live 双侧锁定；三重派全部从 staging 抄形，形态永不漂移——**锁死而非漂移**。

**空格形系长期生产现象（复核确认）**：现盘 live 标题形态清单（`grep -n "^## " truth/character_matrix.md`）：空格形=ch3(:106)/ch4(:122)/ch9(:179)/ch11(:204)/ch29(:624)/ch30(:649)/ch47(:1049)/ch48(:1068)；无空格形=ch1/5/7/13/14/17-28/31-46；带后缀形=`## 第 12 章状态增量（手工合并）`(:230)、ch15(:292)、ch16(:311)。fixture `tests/fixtures/spec95/00189-reads/02-staging__truth__character_matrix.md`（ch41 期 staging 字节复制件）:73/:92/:108 同样混形。即空格形自卷一最初几章（2026-10-26/27）起间歇在场，「ch47/48 模型自撰」表述不成立——首派 00255 发空格双块只是延续既有混形分布（spec r4 判断复核通过）。

---

## §3 判别法：被丢行定位逐窗裁定（本报告核心）

判别标准：**被丢行位于（空格形）own-block 标题下 → H4 误归因（①③=首派预防面）；位于基底区（own-block 外）→ 真 H1（①③=根治面）**。每窗分别裁，允许异质结论。

### 3.1 probe29（POC ch4，sessions 23-24）——**倾向真 H1（基底区），blob 缺证，置信低**

旧 POC blob **不在盘**：observability 归档自 2026-10-29（dispatch 00001=ch023）方启动；2026-10-26/27 regen 前段无 prompt/响应快照（`docs/regen-vol1-observability-mining.md`「口径缺口：无 dispatch 时刻 prompt/响应快照」），POC probe 会话工件无存档目录（repo 内 `_quarantine`/fixtures/v2-archived 均无 probe29-31 窗口件；v2-archived 无 observability/）。按 spec T0 预授权路径取二级证据：

- `skills/shenbi-state-settling/SKILL.md:98`：「**任何对已有『## 第N章状态增量』section 或『交互总表』已有行的文本重写**（如扩展 `- 当前位置: ...` 内容、合并活跃关系等），都触发 G4.ss.matrix_structure content_dropped（attempts=3 耗尽后 approve 仍失败，详见 probe29 ch4）」；:103：「本铁律自 probe29 ch4 验证后固化（sessions 23-24）」。

裁定：SKILL 措辞把 probe29 的被丢行归于「已有 section/已有行」的**改写**——即当时语义下的**基底区**（probe31 的 own-block 豁免尚不存在，但「已有」的典型所指是前章块与总表行）。**倾向真 H1**。保留不确定：无 blob 无法排除部分被丢行实为同窗重派对自己首派块的替换（若如此该子集属 H4 前身）。deviation 记 §5-dev1。

### 3.2 probe30（POC ch4）——**真 H1（基底区行改写），blob 缺证，代码注释即裁决文**

`src/shenbi/pipeline/dispatch_helper.py:1455-1459`（#23 注入的来历注释）：「probe30 ch4 matrix_structure content_dropped: SKILL.md 铁律 0 alone did not survive high write-pressure chapters — **the model rewrote existing rows** when many increments landed at once」。「rewrote existing rows」= 交互总表已有行（表行在 `_content_stream` 中虽豁免，但块内/基底散文行不豁免；且该窗实锤驱动的是注入面而非豁免面）。裁定：**基底区，真 H1 族**（高压写入下的整档污染形态）。

### 3.3 probe31（POC ch2）——**own-block（H4 族的祖先窗），构造性裁定**

`src/shenbi/gates/g4/state_settling.py:295-303`（`_current_settle_chapter` docstring）：「probe31 ch2 escalation: the audit-routed re-settle's keyed-upsert **ATOMICALLY REPLACES the current chapter's own increment block**; without chapter-awareness the matrix guard flagged the replaced bullets as content_dropped and every re-settle that touched its own block died — a deterministic deadlock, not model noise (**2 byte-identical attempts**)」。复现用例 `tests/unit/gates/g4/test_state_settling.py:811-849`（`test_re_settle_replacing_own_chapter_block_passes_matrix_structure`，用例 live 全用**无空格**标题）。裁定：**被丢行=本章 own-block 内 bullet，H4 族（豁免缺位窗——当时豁免尚未存在，本窗即豁免的立法依据）**。标题形：用例与修复正则均按无空格设计（若当时块系空格形，probe31 修复本身不会生效），推定无空格形——H4 的**语法面**（空格不容）在本窗未触发，触发的是**豁免缺位面**。

### 3.4 束4 裁决 #12（v3，2026-11-05，ch43/44 草写二次 escalation 手术）——**判别法不适用（非 settle 增量族）**

- 台账（vol1-ledger.md 束4 节，裁决 #12）：手术五项全部**草写面**（物象短称撞→#86 matcher、黏连子句、转折词计数、钩行同步、声口卡形）；
- 束4 的 settle 面**一次过**：dispatch `00218-shenbi-state-settling-ch043-a1.json` 单派（trace seq 1095→1096 AUDIT_PASS），prompt 无重派反馈，台账明记「settle 一次过（11195 字/13 件增量/零重试）」；
- 束4 草写重派链 blob 在盘（`00214/00215/00216-shenbi-chapter-drafting-ch043-a1.json`），00215/00216 prompt 实查：反馈= `pipeline-scene-split: word_band:ch44:total_chars 2684 不在带 [2800,4000]` 等，**全窗零 content_dropped**。

裁定：**#12 与 matrix content_dropped 族无族属关系**（失败族=草写字数振荡+matcher 限度）。spec 动机证据②的「归因待同判别法复核」结论=**排除族属**；其对 spec 的价值仅剩「每窗 1 接骨+手术风险」的生产税计量，不参与 H1/H4 判别。

### 3.5 可盘复发窗补充裁定（blob 时代，spec83 r3 勘误清单的复核——判别法的旁证族谱）

**ch37 窗（2026-11-01，束1 修订后 re-settle 三派 00154/00161/162）——孪生块豁免缺口（C1 面），非空格语法面**。a3 prompt（00162）内嵌反馈逐字：`content_dropped:1行 e.g. ['- 财务：一百三十三文付五十、余八十三（袋口敞开…']`。定位：该行现盘 live:861，位于 `## 第38章状态增量`（live:843，**无空格形**）块的 `### 主角当前状态` 下——即**孪生章（N+1=38）块内**。a1/a2 response（5127/5005 chars）均含 `##第37章状态增量`+`##第38章状态增量` 双块（无空格形）；a2 把 38 块财务行的本息值 `三两九钱六分` 更正为 `三两二钱四分`（束1 评审算术修正：240 文=36+123+36+45）。sidecar chapter=37 → strip 只豁免 37 块 → 38 块合法 keyed-upsert 被判 drop。裁定：**own-bundle（孪生）块改写被误判——H4 族的 C1 豁免范围面**（标题无空格、正则本可命中，但目标章集不含 38）。台账束1 收尾「ch37-only 增量 vs live 已含 ch38 行→content_dropped 恒红→清空队列项」与此互证。

**ch41 窗（2026-11-01，束3，三派 00189/191/193 + 裁决 #08 回植 21 行×8 文件）——基底区质量丢失（门真阳性），机制=修订/回植链而非引语改写**。铁证：`pipeline-state.json` 残留 stale `retry_feedback["ch41-shenbi-state-settling"]`（束3 #09 冻结时清队列未清反馈——另一处卫生债）：`content_dropped:4行 e.g. ['- 那罕（林烽）：榆林驿站附籍站户「那罕」（定册…', '- 那罕已知：县里章程「签了才发数」，而签了字的…', '- 持有：私账（「站务」页三笔＋行首日子正月廿六…']` + hooks 面 5 行（`- 证据（第 39 章）: …`）。被丢行现盘落在 ch39/ch42 块邻域（live:879/:976/:887 一带），**均在 own(41) 块之外**。三派 response 仅含 41/42 双块（6129/5483/2624 chars），非整档重发（台账「模型重发整档」表述与 blob 不符——实际丢失链涉及修订步重派覆写手工修复+staging 清场，见裁决 #08/#09）。裁定：**基底区（前章/孪生混合）真丢失，门真阳性；非 H1 引语语义引力、亦非 H4**——独立子族（修订-回植覆写链）。附带发现两处手术瘢痕（见 §5-dev4）。

**ch25/ch31 复发窗（2026-10-29，各三派/两派）——不可裁（live-当时不可复原）**。staged 真件在盘（repo 根 `_quarantine/ch25-resettle-attempt1/`、`ch31-resettle-attempt1/`，含 character_matrix.md + sidecar chapter=25）；但重放需 live-当时，而现盘 live 的早期块已被束1/束3 手工回植污染（实证：live:422 一行 **ch39 内容的「情绪」行错插在 ch20 块内**、live:887-888 ch39 块内「持有」行整行重复两次）——以现盘截断重建 live 会制造假 drop（实测即命中错插行）。裁定：**证据不足，挂 deviation**（§5-dev3）。ch23 窗（dispatch 00001 单派+`_quarantine/ch23-settle-attempt1-staging/`）同因不裁。

### 3.6 判别法总裁定

| 窗 | 被丢行定位 | 标题形 | 裁定 | 证据级 |
|---|---|---|---|---|
| probe29 ch4 | 基底区（已有行/已有 section 改写） | 不可考 | **倾向真 H1** | 二级（SKILL:98/:103），置信低 |
| probe30 ch4 | 基底区（已有表行改写） | 不可考 | **真 H1** | 二级（dispatch_helper:1455-1459 注释=裁决文） |
| probe31 ch2 | own-block（本章块 bullet 替换） | 推定无空格 | **H4（豁免缺位祖先窗）** | 二级（state_settling:295-303 + 测试:811-849） |
| 束4 #12 | ——无 content_dropped—— | —— | **不适用（草写面，排除族属）** | 一级（blob 00214-216/00218 在盘实查） |
| （旁证）ch37 | 孪生 38 块内（keyed 财务行更正） | 无空格 | **H4-C1（豁免范围面）** | 一级（00162 反馈逐字+response blob） |
| （旁证）ch41 | 基底区（39/42 块邻域真丢失） | 混形 | **门真阳性（修订-回植链子族）** | 一级（pipeline-state 残留反馈+response blob） |
| 束7 ch47 | **own-block 47 块内自陈行** | **空格形** | **H4（语法面）** | 一级（§1 全链+重放复现） |

**对「①③定位」的净效应**：spec 动机证据①（probe29-31）拆开后是**异质**的——probe29/30 提供真 H1（基底区改写）的历史证据（低置信），probe31 属 H4 族的立法窗；②不适用；③（束7）为 H4 语法面实锤。**H1 并未被证伪，但也无一级证据在盘**；H4 有两窗一级实锤（束7 语法面 + ch37 范围面）。→ ①③按 spec §3 风险条款落 **「首派预防面」**（保留且有价值：基底区引语/表行改写在 probe29/30 时代真实发生过，预防教学对此有效面），④⑤为 H4 根治面。两果均不缩批。

---

## §4 标题语法表面盘点（四表面+第五邻接面）

| # | 表面 | 位置 | 现行形 | 实文 |
|---|---|---|---|---|
| ① | gate 豁免 | `src/shenbi/gates/g4/state_settling.py:322` | **严格形** | `heading_re = re.compile(rf"^##\s*第{chapter}章状态增量\s*$")`——`第{chapter}章` 数字两侧不容空白；有 `\s*$` 尾锚 |
| ② | 提取器 | `src/shenbi/pipeline/read_extractors.py:917-919`（spec 记 :916-918） | **容错形·无尾锚** | `chapter_block_res = [_re.compile(rf"^##\s*第\s*{n}\s*章\s*状态增量") for n in (chapter, chapter + 1)]`——matrix_scoped 保 N/N+1 块（束7 三派 prompt 里 47/48 块全靠它注入——**容错形在束7 全程工作正常**，即「模型看得到块、门却剥不掉块」的不对称） |
| ③ | 写径 | `src/shenbi/pipeline/truth_io.py:1585`（`_replace_section` :1572-1612） | **精确匹配** | `if line.strip() != heading: continue`——标题整行字符串相等才替换；失配返回 None |
| ③′ | EOF 追加链 | `truth_io.py:1642-1662` | 兜底序 | `_hook_section_bullet_merge`(:1643) → `_replace_outline_section`(:1649) → `_replace_section`(:1651) → thread 专用(:1660) → **`merged = existing.rstrip() + "\n" + new_row`(:1662, EOF 追加)** |
| ④ | 教学 | `src/shenbi/pipeline/chapter_loop.py:955`（`G4.ss.matrix_structure` 重试指引） | **空格形** | `"## 第 2 章状态增量\n"`——重试反馈的「期望格式」示例即空格形（实弹在场证据：pipeline-state 残留 ch41 反馈内嵌同款示例，模型真见过） |
| ⑤ | 邻接面（不改） | `read_extractors.py:52` | 已容错 | `_SECTION_UNIT_RE = re.compile(r"^#{2,4}\s*第\s*(\d+)\s*章", re.MULTILINE)`——`### 第 47 章`/`## 第N章状态增量` 通吃，附记兼容不改，复核无异议 |

**EOF 追加重复块触发条件推演+实证**：④① 教学统一无空格规范形后，若 live 仍带空格块（ch47/48 即是），未来重派发 `##第47章状态增量` 增量 → 表面③ `line.strip() != heading` 恒真 → `_replace_section` 返 None → 沿 ③′ 链落到 :1662 EOF 追加 → **重复块**；且④修复后的容错豁免会把两个同名 span（旧空格块+新无空格块）都剥出比对 → **G4 不可见**。离线实证（真实 `_replace_section`）：

```
live="…## 第 47 章状态增量\n- 自陈: 旧句…"，增量标题 "##第47章状态增量" → _replace_section → None（→ EOF 追加重复块）
同形（空格 vs 空格，束7 实况）→ 替换成功（束7 未触发重复块的原因）
```

——①与写径归一互为前置（spec r4/I4 判断复核通过）。

**尾锚 `\s*$` 的在盘论据**：live 已存在带后缀标题 `## 第 12 章状态增量（手工合并）`/ch15/ch16——无尾锚的豁免正则会把「（手工合并）」变体也当增量块标题；④保留尾锚（spec I2）与此实证一致，plan 锚点取舍理由补此条。

---

## §5 族同源判定 + deviations + T1 影响裁定

### 5.1 族谱对比（probe29-31 vs 束7，及可盘旁证窗）

| 维度 | probe29（ch4） | probe30（ch4） | probe31（ch2） | ch37（束1） | ch41（束3） | **束7（ch47）** |
|---|---|---|---|---|---|---|
| 改写方向 | 已有行扩展/合并 | 已有表行改写 | own-block 整块替换 | 孪生块 keyed 财务行**算术更正** | 基底行真丢失（覆写链） | own-block 引语行 keyed-upsert **换更准章句** |
| 块归属 | 基底区 | 基底区 | own（本章） | own-bundle（孪生 38） | 基底区（39/42 邻域） | **own（47）** |
| 反馈在场性 | 无结构化反馈（盲重派时代） | 同左；#23 注入即本窗产物 | 盲（2 逐字节同 attempts） | a3 起旧式 e.g. 截断反馈 | 盲（stale 反馈残留在 pipeline-state） | **三段式 verbatim 反馈×1/×2 累积在场**——与 staging 视图+keyed-upsert 语义三向矛盾 → 死锁不收敛 |
| 门判定 | 真阳性（按当时语义） | 真阳性 | 假阳性（豁免缺位） | 假阳性（豁免范围） | 真阳性 | **假阳性（豁免语法）** |

同源性结论：probe31/ch37/束7 三窗同族（**合法 keyed-upsert 被门误杀的确定性死锁**），分别对应豁免机制的**缺位/范围/语法**三个缺陷层——④（语法单源化+孪生扩展）一次修复后两层；probe29/30 为另一族（基底区改写，门真阳性），是①③教学面的历史根据；ch41 又一族（修订-回植覆写），本批不触及。

### 5.2 deviations

1. **probe29-31 旧 POC blob 不在盘**（observability 2026-10-29 起才有；probe 会话工件无存档）——按 SKILL:98/:103、dispatch_helper:1455-1459、state_settling:295-303、test_state_settling.py:811-849 四源二级证据裁定（spec T0 预授权路径）；probe29 置信低（无 blob 无法排除同窗 own-block 子集）。
2. **束4 #12 判别法不适用**（§3.4）——spec 动机②从「归因待复核」落为「排除族属」；建议 T3 台账 supersede 时一并修正动机证据②的表述。
3. **ch23/25/31 复发窗不可裁**：staged 真件在盘（`_quarantine/`）但 live-当时被后续手工回植污染，无法复原（§3.5）。
4. **手术瘢痕两处（束1/束3 回植遗产，现盘 live 实测）**：live:422（ch39 内容「情绪」行错插 ch20 块内）；live:887-888（ch39 块「持有」行整行重复）。另 `pipeline-state.json` 残留 stale `retry_feedback["ch41-shenbi-state-settling"]`（清队列未清反馈）。三者均为数据卫生债，不属本批修复面，建议登记 #86 类死面清扫候选。
5. **台账 #19 手术描述与现盘不一致**：台账记「基底 verbatim 复原+全句作新增行（两全形）」，现盘 live（mtime 2026-11-08 09:51）47 块仅旧形单行、无新增行——手术中间态已被 09:51 的后续处理覆写，无法从盘面复原；不影响 H4 裁定（三派 blob 链完整），T3 supersede #19 时以此为准。
6. **「三派 response 逐字节相同」口径收窄**（§0）：逐字改写形一致成立；整 blob 逐字节不一致（14267/20665/18000B）。
7. **邻接发现（④范围外）**：a2/a3 同窗还败于 `pending_hooks` `content_dropped:1行`（`- 证据（第 47 章）: …L60–L62…`）——`_HOOKS_VOLATILE_RE`（state_settling.py:65，源 truth_io.py:696 `HOOKS_VOLATILE_FIELDS` 含「证据」）要求 `证据` 后**紧跟**冒号，不认 `证据（第 47 章）` 装饰键形 → 同族「精确字面量 vs 装饰变体」病灶在 hooks 面的映出。④仅管矩阵增量标题族，此面记后续候选（#86 死面或新 spec），不入本批。
8. **a1 prompt 自陈行偏移口径**：行起点 21870（spec r3 记 @21872，同行内 +2 字符口径差，无实质出入）；47 块区间 [21501,21921)（spec 记 @21504-21924 = `第` 字位口径）。

### 5.3 对 T1 各候选的影响裁定（①③定位措辞建议）

- **④（标题语法单源化+bundle 孪生豁免+三消费方）**：束7 一级实锤+反事实验证（§1.4 容错形即全绿）+ch37 一级旁证（孪生面）——**根治面地位无可争议**；EOF 追加链推演（§4）支持「①与写径归一互为前置」的 r4 强制。
- **⑤（#23 注入双矛盾修正）**：a1 行为受 `NEVER modify or extend any earlier ## 第N章状态增量 section` 与 probe31 语义的直接矛盾支配（束7 a1 即「合规地」只发新块却仍被杀）；bundle 双章口径缺失与 a1 未发 48 块/a2a3 补发的行为摆动吻合——**与④配对强制成立**。
- **①③（铁律 0 own-block 排除条款+引语双行正例+G4 报文正例）**：按 §3.6 净效应落 **「首派预防面」** 措辞——理由：(a) H1（基底区改写）无一级在盘证据但 probe29/30 二级证据同向且未证伪；(b) ①的 own-block 排除条款与引语双行正例在 H4 修复后仍有独立价值（own-block 内引语行改写在 probe31 语义下永远合法，教学须把「更准引文→新起一行」的出口教给模型，避免模型在合法域内继续选「替换」形——束7 模型若有此出口，a1 起即可两全形收敛）；(c) 建议措辞：「①③=首派预防面（基底区改写预防+own-block 引语两全形出口）」，不写「根治」。T3 线 2 观测口径相应为：首派引语保真（仅 own-block 外改写可观测）——与 spec r4 原文一致，无需改动。
- **红线复核**：本报告未发现需要改动 content_dropped 判定语义或 append-only 铁律的证据——束7 的门「错」在豁免域的语法，不在判据本身（`_seq_drops` 行为经重放确认逐行精确）。

---

## 结论

束7 三连败的 H4 假阳性死锁在 blob 层逐字闭合并经框架真实代码离线复现：**空格形 own-block（首派 00255 自撰、满屏带空格表行诱导、过检落账锁定）→ gate :322 严格正则剥不掉 → 合法 keyed-upsert（换更准章句，ch47:66 原句）被判 content_dropped:1 行 → 反馈与 staging 视图矛盾 → 3/3 熔断+手术**。判别法裁定：动机证据①异质（probe29/30=真 H1 低置信/probe31=H4 祖先窗）、②不适用（束4 #12 排除族属）、旁证 ch37=H4-C1 面、ch41=门真阳性独立子族——**①③定首派预防面、④⑤根治面、两果均不缩批**（spec §3 风险条款两分支同时成立）。四表面+第五邻接面盘点与 spec r4 一致（含 :916-918→:917-919 行号漂移、尾锚的在盘后缀标题论据、EOF 追加链实证）。
