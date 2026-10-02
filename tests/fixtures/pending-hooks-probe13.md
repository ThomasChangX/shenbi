---
type: truth
category: state
status: initialized
produced_at: 2026-10-02T05:51:09Z
---

# 伏笔池

> 本文件由 `shenbi-foreshadowing-lifecycle --mode genesis` 从 `outline/story_frame.md` 与 `outline/volume_map.md` 提取跨卷母钩（master hooks）生成。全部母钩初始化为 PLANTED，兑现章以「章号（卷）」标注。genesis 模式不读写 `truth/bridge_tracker.md`，不处理逐章 hook 账（那属逐章模式职责）。
> 母钩 ID 形态：MH + 两位数字、无连字符，与 `truth/book_spine.md` 既有 MH 编号一致。
> 表头键「当前生命周期」为索引解析入口，本表 8 列形态不得改动。
## 总览
| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
| MH01（共魂规则之谜：被托付则强、背叛自己说出口的话则哑） | PLANTED | 23 | 108（五卷） | RULE | 0.5 | 12 | STAIRCASE |
| MH02（岑昭名字簿的三份抄本：埋井边、缝衣里、准备交出去） | PLANTED | 11 | 98（五卷） | ITEM | 0.6 | 10 | RISING |
| MH03（江砚抄本上不愿填、也还没被填上的空白署名） | PLANTED | 18 | 112（五卷） | ITEM | 0.7 | 12 | FLAT |
| MH04（卫长庚旧星图上少掉的一整类波形） | PLANTED | 4 | 111（五卷） | INFORMATION | 0.6 | 12 | STAIRCASE |
| MH05（维尔的平账执念与那份预备回收名单） | PLANTED | 7 | 88（四卷） | CHARACTER | 0.5 | 12 | RISING |
| MH06（屈铁山儿子的死与血籍之乱那年冬天的井口） | PLANTED | 13 | 107（五卷） | CHARACTER | 0.7 | 12 | STAIRCASE |
| MH07（裴知微十六岁抄过的那份灭门公文与他的笔） | PLANTED | 14 | 106（五卷） | CHARACTER | 0.7 | 12 | RISING |
| MH08（顾阿婆的名字簿与共魂余烬的两种口径） | PLANTED | 3 | 99（五卷） | ITEM | 0.6 | 12 | STAIRCASE |
| MH09（穹幕闭合的真相与星涌谷底的读秒） | PLANTED | 1 | 74（四卷） | INFORMATION | 0.5 | 12 | RISING |
| MH10（跃迁燃料账本：穹洲人被标价，不是被征服） | PLANTED | 19 | 75（四卷） | INFORMATION | 0.6 | 10 | STAIRCASE |
| MH11（被推到面前却始终没被接住的签字笔） | PLANTED | 24 | 105（五卷） | EVENT | 0.5 | 10 | STAIRCASE |
| MH12（从编号到姓名：命名权与名字簿走进战场） | PLANTED | 2 | 118（五卷） | RULE | 0.4 | 10 | STAIRCASE |
| MH13（火与铁的相斥律：火药听话的窗口） | PLANTED | 20 | 82（四卷） | RULE | 0.5 | 10 | FLAT |
| MH14（地脉里积存的不只是余烬，还有人） | PLANTED | 23 | 109（五卷） | INFORMATION | 0.7 | 12 | RISING |
| MH15（帝国抽干地脉的收割时间表） | PLANTED | 43 | 104（五卷） | EVENT | 0.5 | 12 | RISING |
| MH16（陆衍以另一个名字、同一双手再次走进人群） | PLANTED | 113 | 续篇（本书章界外） | CHARACTER | 0.6 | 14 | FLAT |
## 已埋未收

### MH01（共魂规则之谜：被托付则强、背叛自己说出口的话则哑）
- dimension: WORLD ｜ type: RULE ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第23章（共魂第一次灌注，力量来得毫无解释）；规则禁止早于本章被任何角色解释
- trigger_condition: 陆衍当着具体的人说出一句他愿意为之负责的话
- resolve_condition: 共魂最终秘密揭开，规则与承诺结在同一条规则上
- 兑现章（卷）: 第108章（第五卷）｜预期激活章: 第25章（第一次失声）
- subtlety: 0.5 ｜ cultivation_interval: 8 ｜ max_distance: 12 ｜ escalation_curve: STAIRCASE
- depends_on: [MH14]
- notes: core_hook，禁止 ABANDONED；只以后果（失声/增强）呈现规则，不得旁白解释

### MH02（岑昭名字簿的三份抄本：埋井边、缝衣里、准备交出去）
- dimension: SYMBOLIC ｜ type: ITEM ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第11章（做三份）；分置推进: 第18章（抄成星图附录，署名留空）
- trigger_condition: 抄本之一被圣所或官方查抄、或被迫交出的时刻
- resolve_condition: 三份抄本合流为公开名册——不是遗物，是名册
- 兑现章（卷）: 第98章（第五卷）｜预期激活章: 第26-28章
- subtlety: 0.6 ｜ cultivation_interval: 7 ｜ max_distance: 10 ｜ escalation_curve: RISING
- depends_on: [MH03, MH08]
- notes: 与 MH03、MH08 共用地面接口，三钩不得同时停在静默态

### MH03（江砚抄本上不愿填、也还没被填上的空白署名）
- dimension: SYMBOLIC ｜ type: ITEM ｜ lifecycle_state: PLANTED
- 种植章: 第18章（署名处留空）；预置伏笔: 第6章（测绘棚不敢上报空白）
- trigger_condition: 圣所内部发现抄本、要求补署名的时刻（第28章）
- resolve_condition: 留白被填满，下一代录事不必再留空署名
- 兑现章（卷）: 第112章（第五卷）｜预期激活章: 第28章
- subtlety: 0.7 ｜ cultivation_interval: 9 ｜ max_distance: 12 ｜ escalation_curve: FLAT
- depends_on: [MH02]
- notes: 命名权之争的物证；第97章填署后转 RELEVANT 而非 RESOLVED，须待第112章

### MH04（卫长庚旧星图上少掉的一整类波形）
- dimension: INFORMATION ｜ type: INFORMATION ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第4章（陆衍波形在星图上无对应谱线）；推进: 第15章（圈下一次越界读数）
- trigger_condition: 圣所追查旧星图、或他把四十年星图的错误摊开的时刻（第52、73章）
- resolve_condition: 旧星图被烧掉，重画一张把这一类波形画进去、署上自己名字的图
- 兑现章（卷）: 第111章（第五卷）｜预期激活章: 第28章（假读数挡下）、第52章
- subtlety: 0.6 ｜ cultivation_interval: 8 ｜ max_distance: 12 ｜ escalation_curve: STAIRCASE
- depends_on: [MH01]
- notes: 与 MH01 同源（波形类别=共魂人群）；不得提前点明空白页性质

### MH05（维尔的平账执念与那份预备回收名单）
- dimension: CHARACTER ｜ type: CHARACTER ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第7章（看见反向记号，下令活捉而非清除）；推进: 第21章（催缴写成注销）、第30章
- trigger_condition: 维尔的账面上出现一栏预备回收，名单上是他自己（第85章）
- resolve_condition: 他在平账的执念里亲手注销自己；账是平的，人不存在
- 兑现章（卷）: 第88章（第四卷）｜预期激活章: 第30章
- subtlety: 0.5 ｜ cultivation_interval: 7 ｜ max_distance: 12 ｜ escalation_curve: RISING
- depends_on: [MH15]
- notes: 全书对平账秩序最锋利的一次反问；第87章对读后必须走向自注销，不得改为他杀

### MH06（屈铁山儿子的死与血籍之乱那年冬天的井口）
- dimension: CHARACTER ｜ type: CHARACTER ｜ lifecycle_state: PLANTED
- 种植章: 第13章（当众念出每口井的日产量）；推进: 第45章（赌输一次，第一次允许自己怀疑）
- trigger_condition: 他第一次公开承认光靠自发、血籍之乱那年死的人还不够多（第68章）
- resolve_condition: 他替死掉的人念完一整本名字，包括他儿子
- 兑现章（卷）: 第107章（第五卷）｜预期激活章: 第68章
- subtlety: 0.7 ｜ cultivation_interval: 9 ｜ max_distance: 12 ｜ escalation_curve: STAIRCASE
- depends_on: []
- notes: 自发派信念身上最早的一道裂；第93章合流后转 TRIGGERED

### MH07（裴知微十六岁抄过的那份灭门公文与他的笔）
- dimension: CHARACTER ｜ type: CHARACTER ｜ lifecycle_state: PLANTED
- 种植章: 第14章（誓印立约、纪律整队）；推进: 第38章（自请处分）、第59章（扩权）
- trigger_condition: 那支笔在他清点敌我名单的夜里回到他手里（第67-92章区间）
- resolve_condition: 他认输但拒绝认错，带着他那支笔离开，不再要求任何人签字
- 兑现章（卷）: 第106章（第五卷）｜预期激活章: 第67章（不表态）、第92章（认输）
- subtlety: 0.7 ｜ cultivation_interval: 9 ｜ max_distance: 12 ｜ escalation_curve: RISING
- depends_on: []
- notes: 他的正确与干净必须始终有效，否则证伪失去重量

### MH08（顾阿婆的名字簿与共魂余烬的两种口径）
- dimension: SYMBOLIC ｜ type: ITEM ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第3章（郝石头之名第一次写进簿子）；推进: 第39章（加到最厚的一页）
- trigger_condition: 名字簿与共魂余烬在同一场景被并置对读的时刻（第39、99章）
- resolve_condition: 两种口径最后一次对上，地面接口走完它的路
- 兑现章（卷）: 第99章（第五卷）｜预期激活章: 第39章
- subtlety: 0.6 ｜ cultivation_interval: 7 ｜ max_distance: 12 ｜ escalation_curve: STAIRCASE
- depends_on: [MH14]
- notes: 共魂余烬设定在地面上的第一个可触摸接口；画圈与结绳的记法不得现代化改写

### MH09（穹幕闭合的真相与星涌谷底的读秒）
- dimension: WORLD ｜ type: INFORMATION ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第1章（星井、灰籍、帝国舰队三层压迫的远景）；推进: 第20章（星井干涸）、第51-55章
- trigger_condition: 穹幕闭合被证实——不到三百年星火将熄灭（第74章）
- resolve_condition: 真相念给所有人听，念完去点人数
- 兑现章（卷）: 第74章（第四卷）｜预期激活章: 第72章（舰队再临）
- subtlety: 0.5 ｜ cultivation_interval: 8 ｜ max_distance: 12 ｜ escalation_curve: RISING
- depends_on: []
- notes: 与 MH10 分设两钩，信息（穹幕）与账本（标价）揭示章不得并为同章

### MH10（跃迁燃料账本：穹洲人被标价，不是被征服）
- dimension: INFORMATION ｜ type: INFORMATION ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第19章（地脉是电容、星井是插线板的工程类比）
- trigger_condition: 跃迁燃料的账本第一次被完整读到的时刻（第75章）
- resolve_condition: 穹洲人被标价为燃料的事实进公论，与 MH15 的收割表并轨
- 兑现章（卷）: 第75章（第四卷）｜预期激活章: 第75章
- subtlety: 0.6 ｜ cultivation_interval: 8 ｜ max_distance: 10 ｜ escalation_curve: STAIRCASE
- depends_on: [MH09]
- notes: deep_conflict「人是不是燃料」的信息载体；揭示后转 RELEVANT，随 MH15 推进

### MH11（被推到面前却始终没被接住的签字笔）
- dimension: PLOT ｜ type: EVENT ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第24章（签字笔被推到面前，他没有接）；推进: 第47章（拒绝签字，也拒绝别人替他签）
- trigger_condition: 两派同时要求他签字、或胜利后椅子空出来的时刻（第69、105章）
- resolve_condition: 他把权限交回去，写下归还的条件
- 兑现章（卷）: 第105章（第五卷）｜预期激活章: 第69章
- subtlety: 0.5 ｜ cultivation_interval: 7 ｜ max_distance: 10 ｜ escalation_curve: STAIRCASE
- depends_on: [MH07]
- notes: 与 MH12 互为表里；第71章写下归还条件后转 TRIGGERED

### MH12（从编号到姓名：命名权与名字簿走进战场）
- dimension: WORLD ｜ type: RULE ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第2章（把领料簿上的六位数改回三个字）；推进: 第10章（拒绝被叫恩公）、第96-98章
- trigger_condition: 名字簿被作为名册带进战场、命名权被公开交还可追责的许多只手
- resolve_condition: 账本与名字交给下一代，命名权归还无名者
- 兑现章（卷）: 第118章（第五卷）｜预期激活章: 第98章
- subtlety: 0.4 ｜ cultivation_interval: 6 ｜ max_distance: 10 ｜ escalation_curve: STAIRCASE
- depends_on: [MH02, MH03, MH08]
- notes: 全书主题母钩，须贯穿 118 章持续以「记账动作」形式重现，禁止长期静默

### MH13（火与铁的相斥律：火药听话的窗口）
- dimension: WORLD ｜ type: RULE ｜ lifecycle_state: PLANTED
- 种植章: 第20章（星井干涸，灵械迟钝、火药听话；代价是一个人的手）
- trigger_condition: 星涌谷底来临、灵械全面迟钝而火药与冷铁格外听话的窗口（第82章）
- resolve_condition: 窗口被编成可复现的调度表，胜负由算术与后勤决定
- 兑现章（卷）: 第82章（第四卷）｜预期激活章: 第82章
- subtlety: 0.5 ｜ cultivation_interval: 8 ｜ max_distance: 10 ｜ escalation_curve: FLAT
- depends_on: []
- notes: 战斗胜负的物性依据；第44章以其窗口组织破袭，属提前部分触发

### MH14（地脉里积存的不只是余烬，还有人）
- dimension: INFORMATION ｜ type: INFORMATION ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第23章（共魂灌注时听见血籍之乱死者的余烬）
- trigger_condition: 共魂最终秘密被揭开的时刻（第108章）
- resolve_condition: 人格被确认可在下一轮星涌里被重新点着，成为另一个身体里的另一个名字
- 兑现章（卷）: 第109章（第五卷）｜预期激活章: 第108章
- subtlety: 0.7 ｜ cultivation_interval: 9 ｜ max_distance: 12 ｜ escalation_curve: RISING
- depends_on: [MH01, MH08]
- notes: deep_conflict 的终极答案；第110章他承认只是第一次听见了我们，与 MH16 衔接

### MH15（帝国抽干地脉的收割时间表）
- dimension: PLOT ｜ type: EVENT ｜ lifecycle_state: PLANTED ｜ core_hook: true
- 种植章: 第43章（收割时间表浮出水面，穹洲人被标价）
- trigger_condition: 总攻开始、战争只剩一个目的（燃料）的时刻（第95章）
- resolve_condition: 抽脉装置被群众从内部拆掉，殖民秩序的账整体对不上
- 兑现章（卷）: 第104章（第五卷）｜预期激活章: 第95章
- subtlety: 0.5 ｜ cultivation_interval: 8 ｜ max_distance: 12 ｜ escalation_curve: RISING
- depends_on: [MH09, MH10]
- notes: 与 MH05 咬合（维尔体系是其账面执行者）；第102章拆装置为部分兑现，主兑现留第104章

### MH16（陆衍以另一个名字、同一双手再次走进人群）
- dimension: CHARACTER ｜ type: CHARACTER ｜ lifecycle_state: PLANTED
- 种植章: 第113章（功成身退，不以死谢幕）；预置: 第117章（新星图上无人能确认的熟悉波形）
- trigger_condition: 有人在新的星图上看见一个熟悉的波形，无人能确认那是不是他
- resolve_condition: 开放接口，交由新一代与续篇；本书内不兑现
- 兑现章（卷）: 续篇（本书章界外）｜预期激活章: 第117章
- subtlety: 0.6 ｜ cultivation_interval: 10 ｜ max_distance: 14 ｜ escalation_curve: FLAT
- depends_on: [MH12]
- notes: 全书最后一钩；终章落款处那个别人看不懂的记号与共魂余烬规则同源，禁止在本书内收束
## 即将回收

> 第一卷末至第二卷开篇须优先推动的母钩（预期激活章 ≤ 第28章）：
| MH01 | 第25章 | PLANTED | 第一次失声，以后果印证规则，不得解释 |
| MH11 | 第25章 | PLANTED | 悬置的签字笔被重新提起 |
| MH02 | 第26-28章 | PLANTED | 抄本分置后的第一次被查风险 |
| MH03 | 第28章 | PLANTED | 圣所发现抄本，假读数挡下 |
| MH04 | 第28章 | PLANTED | 借假读数事件推进空白页 |
## 已回收

（暂无。genesis 阶段所有母钩均为 PLANTED，回收由 `shenbi-foreshadowing-resolve` 在对应章处理后登记。）
## 废弃伏笔

（暂无。母钩均标记 core_hook，禁止 ABANDONED；如确需废弃须经人工裁决并在此说明原因。）
