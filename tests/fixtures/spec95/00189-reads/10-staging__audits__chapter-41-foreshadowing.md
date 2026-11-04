<!-- src: sha256:a93971fd22dc1c1dd43390783477a817df4bb6d897f4c71b9a0e11bca9bc41b9 staging/audits/chapter-41-foreshadowing.md (spec #95 T3 replay fixture; byte copy) -->
# Foreshadowing Lifecycle Report (Chapter 41)

> 章题：勾名｜依据：plans/chapter-41-plan.md 第 7 节 hook 账、chapters/chapter-41.md。生命周期状态列由 shenbi-foreshadowing-track 掌管，本报告只给推荐与证据。

## Phase 1: Recall

本章 DORMANT 池为空：MH01–MH14 全部处于 PLANTED 或 RELEVANT，无 DORMANT→ACTIVE 召回，无 overdue recall。

| Hook ID | Previous State | New State | Reason |
|---------|---------------|-----------|--------|
| MH02 | PLANTED | PLANTED | 按 plan 第 7 节记 defer：本章无雪夜分饼复述、无红纸包改作他用（未裁、未裹伤、未引火、未垫册页；包内饼渣与「正月」墨点未动）；激活方案定在第 46 章「萤回触——她的名字在班期表上过站」（volume_map:154 节点），不 ABANDON |
| MH01 | RELEVANT | RELEVANT | 匣开、四件在场、纸条与路线图首次对格（L106–L154）；trigger 括注的被动形态（外力查抄／焚毁／被动清点）未达，不转化，按 plan 记 defer（至第 2 卷·KR2：匣面开、匣底不动） |

无 overdue 召回项（见 Phase 2 逾期表）。

## Phase 2: Track

### Chapter Operations

| Hook ID | Operation | Previous State | New State | Text Location |
|---------|-----------|---------------|-----------|---------------|
| MH04 | advance（记账对象推进到「名字」本身） | PLANTED | PLANTED（推荐 RELEVANT） | chapters/chapter-41.md L63–L89、L187–L193 |
| MH11 | advance（签字之债反面拍：未签而字勾人） | RELEVANT | RELEVANT | chapters/chapter-41.md L49–L57、L165、L199–L211 |
| MH01 | defer（匣开、两件验而不取；不作状态迁移） | RELEVANT | RELEVANT | chapters/chapter-41.md L106–L154 |
| MH12 | defer（首航人手册未启，仅船期倒计时） | PLANTED | PLANTED | chapters/chapter-41.md L211 |
| B-老驼纸条（plan 级钩子） | advance（叠读对格：小圈落断线点，并轨窗口付息，不解义） | — | — | chapters/chapter-41.md L114–L154 |
| 笔迹链（ch13／14／26，plan 级钩子） | advance（勾名笔迹＝借调令押＋附籍册批注，三张纸一只手） | — | — | chapters/chapter-41.md L199–L211 |

逐条证据见 truth/pending_hooks.md 第 41 章增量行与本章「数据一致性备注」；plan 级两条钩子无 MH／CP 编号，不入 MH 注册表，只在本报告与桥接行留痕（见「边界裁决 4」与 Summary）。

### Overdue Warnings

| Hook ID | Last Reinforced | Current Ch | Interval | Status |
|---------|----------------|------------|----------|--------|
| MH01 | 第 35 章 | 41 | 5/8 | OK |
| MH02 | 第 39 章 | 41 | 1/6 | OK |
| MH04 | 第 39 章 | 41 | 1/10 | OK |
| MH11 | 第 39 章 | 41 | 1/8 | OK |
| MH12 | 第 39 章 | 41 | 1/10 | OK |

无 OVERDUE。

### Max Distance Approaching

| Hook ID | Plant Ch | Current Ch | max_distance | Status |
|---------|---------|------------|-------------|--------|
| MH01 | 2 | 41 | 60 | OK（已用 39，余 21） |
| MH02 | 2 | 41 | 60 | OK（已用 39，余 21） |
| MH11 | 3 | 41 | 60 | OK（已用 38，余 22） |
| MH12 | 22 | 41 | 55 | OK（已用 19，余 36） |
| MH04 | 34 | 41 | 55 | OK（已用 7，余 48） |

无 DISTANCE WARNING。

## Phase 3: Plant

本章 plan 第 7 节无 plant 项（六条全部为 advance／defer），故不新增 `### MHxx` 段、不分配新 ID、不写入 pending_hooks 新条。

### Density Accounting

| Operation Type | This Chapter |
|---------------|-------------|
| plant | 0 |
| reinforce/advance | 4（MH04、MH11、B-老驼纸条、笔迹链） |
| trigger | 0 |
| resolve | 0 |
| defer（不计变更） | 2（MH01、MH12） |
| **Total** | 6 / 8 |

## 跨卷桥接（Cross-Volume Bridge Tracking）

| Bridge ID | 本章文本依据 | 判定 |
|---|---|---|
| BR-01 私账残页 | L63–L89 三笔折三两、四栏纸（末行「未销」）压在册房厚册边；L187–L193 私账「清账」＋「名字：勾销，无价」 | 本体在场并推进记账对象；残页仍夹匣中未取、末行立誓句未出口 → 保持 ACTIVATED／实际激活第 35 章；出行 |
| BR-02 火纹骨哨／老驼信物 | L106–L154 匣开四件在场、纸条与哨腔路线图三次对格小圈落断线点；骨哨与空白格式页验而不取 | 桥关键词（骨哨／老驼遗物）正面出现，但无吹响、无切口、无组织层「递得到」事件 → 保持 ACTIVATED／第 3 章、预期第 45-52 章；出行 |
| BR-04 半部《鉴录》 | L195–L197 末页抄四名（马夫、厨下、更夫、自己，名数四），末行留一格待填日子 | 名栏入册四人、四栏未走全、后半空白仍余 → 保持 ACTIVATED／第 3 章、预期第 56-62 章；出行 |
| BR-05 公司／南方航线 | L211 仅「船还有二十五天」一处船期倒计时；无「公司」二字、无船期表／货单／提单／「件」「活货」栏 | 关键词升级层未达 → 保持 ACTIVATED／第 23 章、预期第 70-72 章；不出行（避免整行重写） |
| BR-03 灰烬定约 | 全章无灰烬、无三倍价、无价目表 | 不触及，不出行 |

## 数据一致性备注

1. **账面算术对齐（正向）**：L75–L77「三笔并作一笔，折三两」（三两＝三千文）加 L69「余月二百四十文不补」＝三千二百四十文，正合 chapters/chapter-39.md L170–L172「三千二百四十文的债，八十三文的现钱」。本章的三两折价不是随口数，而是把第 39 章的债数拆成可核的三笔；建议还账进度表沿用此口径。
2. **工食口径待复核**：L69「工食一项，年额九百六十文，月折八十」（单人年额）与 chapters/chapter-39.md L61「减员四名，工食八文／日，一月按三十日计，合九百六十文／月」（四人月额）同数不同口径。若为刻意（单人年额与四人月额同数，正好互为换算陷阱），需在后文或 state-settling 留一句可核换算；否则属口径漂移，记 MINOR 待复核。
3. **遗物匣内件清单（详见缺陷记录 1）**：本章匣内可见四件（纸条、路线图、骨哨、空白格式页）与第 35 章入匣四件（红纸包、骨哨、《鉴录》、私账残页）不是同一组；正文 L195 又写「他从匣里取出《鉴录》」，说明《鉴录》仍在匣内，则本章「四件」应是匣内当面可见的四件，而非匣内全部。
4. **路线图承接（正向）**：L114–L122 哨腔路线图「图上有一道断线，画到半途就没了」与 chapters/chapter-37.md 场景 2「图上那条线，往南」同图；本章小圈落断线点，正落在「往南」那一截的起点，接驳成立。
5. **老赵与减员名单**：L53 减员四行为「马夫、厨下、更夫、那罕」，L167–L169 站上马夫老赵自称「我名字也在并站的册上。勾没勾，我不知道」。若老赵即四行中的「马夫」，则他应已知被勾；建议明确老赵为另一站并入的马夫，或保留为「并站合册、本站人看不到全册」的信息差（后者更有戏，但需一句交代）。

## 缺陷记录

1. **遗物匣内件清单与第 35 章入匣清单不一**
 - Location: `chapters/chapter-41.md` L110–L111、L148、L195（对 `chapters/chapter-35.md` L43–L59、L206–L212）
 - Original quote: > 「里面四件：老驼的纸条，用细麻线缠了两圈……哨腔那张路线图，折成四折；火纹骨哨；空白格式页一张。」（L110）／「匣里余下两件没动：骨哨躺着，哨口的裂纹朝上；空白格式页压在最底。」（L148）／「他从匣里取出《鉴录》」（L195）
 - Violated rule: 「State transitions require textual evidence」——MH01／BR-02 的判定须以匣内实存物件的唯一文本证据为准，两章清单不同组，本章只能按 plan 记 defer、不迁移状态
 - Severity: MINOR（可解释为「匣内当面可见四件＋匣面夹层两件＋《鉴录》另在匣内」，但正文无一句交代，核对成本转到 state-settling）

## 边界裁决

1. **MH11 不判 TRIGGERED**：trigger 为「主角在任一渡签下名字、落章或明确『不盖』的一刻」。本章他未署名、未画押、未落章；被勾名是受事，属「他没签，字却勾了他」的反面拍，故只记 advance，lifecycle 保持 RELEVANT（Iron Law 6：假兑现垫场）。
2. **MH01 不判 TRIGGERED**：trigger 括注「遗物匣被查抄、焚毁、清点」为被动形态；本章是他自开匣、自对格、两件验而不取，既非外力、亦非清点登记，故记 defer（至第 2 卷·KR2）。
3. **MH12 记 defer**：全章唯一船务信息是 L211「船还有二十五天」，无船期表、无货单「件／活货」栏、无提单、无「公司」二字；按 plan 至第 2 卷·KR1 首航人手册。
4. **plan 级两条钩子不入注册表**：B-老驼纸条、笔迹链（ch13／14／26）无 MH／CP 编号，本章只在本报告与桥接行留痕；建议下一轮在 truth 注册表补立编号，否则「沉默章数」这类阈值无法被机械核对。

## Summary

**Active hooks**: 14（PLANTED 9／RELEVANT 5／TRIGGERED 0／RESOLVED 0）
**This chapter operations**: 6 / 8（advance 4、defer 2、plant 0、trigger 0、resolve 0）
**State distribution**:
- PLANTED: 9（MH02、MH04、MH05、MH07、MH09、MH10、MH12、MH13、MH14）
- RELEVANT: 5（MH01、MH03、MH06、MH08、MH11）
- TRIGGERED: 0

**Risk signals**:
- 无 OVERDUE、无 EXPIRED、无 DISTANCE WARNING（最近一档 MH01：距 max_distance 尚余 21 章）
- [口径待复核] 工食九百六十文的单人年额／四人月额（数据一致性备注 2）
- [清单待复核] 遗物匣内件清单（缺陷记录 1）
- [台账缺编号] B-老驼纸条、笔迹链两条 plan 级钩子无注册表编号

**Next chapter recommended actions**:
- MH04 → 第 43–44 章接「账艺变现／还不起的算式」：三两折价须在正文被第三方承认或拒绝一次，否则折价停在自说自话；注意 notes 的立誓句配额（卷一收束已用掉，卷二不得复用）。
- MH11 → 第 2 卷 KR2（盖章与「不盖」）前保持 RELEVANT；「那只手在暗处」的笔迹链可在第 43–44 章以一次「同一手写的另一张纸」轻触，不必解义。
- MH02 → 按 plan 于第 46 章 advance（班期表过站）；此前的第 43–44 章不再动红纸包，避免把「开春还」提前兑现。
- MH12 → 第 2 卷 KR1 首航人手册（船票／货位／上船工种）；L211 的倒计时须在下一章或第 44 章给出可核的日数递减。
- MH01 → 匣保持「开而复合」，至第 2 卷 KR2 再动；空白格式页（页脚小圈）本章第二次只验不取，建议第 2 卷前不再出场，保持其在匣底的重量。
