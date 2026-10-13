---
type: truth
category: state
status: initialized
created_at: 2026-10-02T21:31:11Z
---

# 伏笔池

> 跨卷主钩（MH）由 shenbi-foreshadowing-lifecycle 创世模式从 `outline/story_frame.md` 与 `outline/volume_map.md` 提取；生命周期状态（PLANTED→RELEVANT→TRIGGERED→RESOLVED）由该技能统一驱动，`last_reinforced`／`subtlety` 由 state-settling 维护。
## 总览
| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
| MH01（净场裂口与穹外之路） | PLANTED | 17 | 96（五卷） | INFORMATION | 0.5 | 20 | STAIRCASE |
| MH02（老陶的未编号名录与「记账人」） | PLANTED | 6 | 93（五卷） | ITEM | 0.6 | 18 | RISING |
| MH03（程墨抄错的那个字） | PLANTED | 4 | 52（三卷） | INFORMATION | 0.5 | 21 | STAIRCASE |
| MH04（裴知远的违禁记录与「查无此人」） | PLANTED | 11 | 70（四卷） | ITEM | 0.5 | 20 | RISING |
| MH05（墨衡的星图与穹顶有隙） | PLANTED | 12 | 92（五卷） | ITEM | 0.6 | 25 | STAIRCASE |
| MH06（借来的灵能之账） | PLANTED | 8 | 85（五卷） | INFORMATION | 0.5 | 25 | RISING |
| MH07（星烬配额与矿脉余命） | PLANTED | 12 | 85（五卷） | INFORMATION | 0.6 | 20 | RISING |
| MH08（铁翼的净化名册） | PLANTED | 15 | 82（五卷） | ITEM | 0.5 | 18 | STAIRCASE |
| MH09（不在任何册上的变量僵局） | PLANTED | 20 | 22（二卷） | EVENT | 0.4 | 12 | FLAT |
| MH10（星火网络的跨地域成形） | PLANTED | 39 | 60（三卷） | EVENT | 0.4 | 20 | RISING |
| MH11（格雷的档案系统与删改报告） | PLANTED | 23 | 86（五卷） | ITEM | 0.5 | 22 | STAIRCASE |
| MH12（「谁在供养，谁在享用」之问） | PLANTED | 10 | 100（五卷） | INFORMATION | 0.4 | 30 | STAIRCASE |
| MH13（多世轮回与穹外启程） | PLANTED | 97 | 100（五卷） | EVENT | 0.7 | 10 | FLAT |
## 详情
### MH01（净场裂口与穹外之路）

- type: INFORMATION
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 17
- resolve_chapter: 96
- subtlety: 0.5
- cultivation_interval: 8
- max_distance: 20
- escalation_curve: STAIRCASE
- trigger_condition: 主角一行靠近净场旧址外围，或禁言之令的禁地氛围被具体化
- resolve_condition: 净场裂口被确认为唯一向上之路，第一批人启程走向穹外
- depends_on: []
- notes: 金手指／世界秘密／终局出口三重交汇点；前期只以禁地传闻侧写，禁止提前解释裂口原理。
### MH02（老陶的未编号名录与「记账人」）

- type: ITEM
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 6
- resolve_chapter: 93
- subtlety: 0.6
- cultivation_interval: 10
- max_distance: 18
- escalation_curve: RISING
- trigger_condition: 野民第一次被当成人来召集，或「记账人」制度被提出
- resolve_condition: 林阿箬主持第一份公开账本，「记账人」成为可运行制度
- depends_on: []
- notes: 野民被当人看待的第一份证据；名字与编号的对立是全书主题的物质锚。
### MH03（程墨抄错的那个字）

- type: INFORMATION
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 4
- resolve_chapter: 52
- subtlety: 0.5
- cultivation_interval: 10
- max_distance: 21
- escalation_curve: STAIRCASE
- trigger_condition: 登记制的豁免方式被使用，或一字之差的人情债被具体化
- resolve_condition: 程墨以一次失败的抄写替人担下档案，主角被迫偿还人情债
- depends_on: []
- notes: 一字偏差等于一条命，也等于一桩死罪；豁免即债务的记账原型。
### MH04（裴知远的违禁记录与「查无此人」）

- type: ITEM
- dimension: CHARACTER
- lifecycle_state: PLANTED
- plant_chapter: 11
- resolve_chapter: 70
- subtlety: 0.5
- cultivation_interval: 8
- max_distance: 20
- escalation_curve: RISING
- trigger_condition: 裴知远在违禁记录前犹豫要不要落笔，或执行禁言之令
- resolve_condition: 裴知远以祠卫少使身份公开否认「天授灵脉」，被本姓除名
- depends_on: []
- notes: 体制内良心觉醒的物证；「查无此人」是体制裂缝的第一处标记。
### MH05（墨衡的星图与穹顶有隙）

- type: ITEM
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 12
- resolve_chapter: 92
- subtlety: 0.6
- cultivation_interval: 10
- max_distance: 25
- escalation_curve: STAIRCASE
- trigger_condition: 墨衡再次登场，或「星象只记发生过的事」与穹顶有隙被提及
- resolve_condition: 星图兑现，裂口通行资格与海量星烬代价被付清
- depends_on: []
- notes: 提醒读者星辰大海是终局门票而非中期捷径；被禁止存在的穹顶裂缝图。
### MH06（借来的灵能之账）

- type: INFORMATION
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 8
- resolve_chapter: 85
- subtlety: 0.5
- cultivation_interval: 12
- max_distance: 25
- escalation_curve: RISING
- trigger_condition: 沈越借他人灵脉引灵，或同伴灵脉上的永久损耗被提及
- resolve_condition: 星烬耗尽前的最后配给与代价分配，这笔记不清的账被清算
- depends_on: []
- notes: 主角无灵脉根基的道德锚；每次救人都在别人身上留下永久损耗。
### MH07（星烬配额与矿脉余命）

- type: INFORMATION
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 12
- resolve_chapter: 85
- subtlety: 0.6
- cultivation_interval: 10
- max_distance: 20
- escalation_curve: RISING
- trigger_condition: 铁翼缺矿所致的虚弱被看出，或三方收紧配额的动因浮现
- resolve_condition: 共同倒计时归零，最后配给与代价分配落地
- depends_on: []
- notes: 暗线中的时钟，决定谁先动手，也决定结局的紧迫；三方战争的共同底牌。
### MH08（铁翼的净化名册）

- type: ITEM
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 15
- resolve_chapter: 82
- subtlety: 0.5
- cultivation_interval: 8
- max_distance: 18
- escalation_curve: STAIRCASE
- trigger_condition: 净化名单被念出，或名册被搜出并被引用
- resolve_condition: 名册反噬，尉迟凛自己的名字出现在上面
- depends_on: []
- notes: 可抄写也可反噬的名字清单；登记逻辑与净化逻辑同源的物证。
### MH09（不在任何册上的变量僵局）

- type: EVENT
- dimension: CHARACTER
- lifecycle_state: PLANTED
- plant_chapter: 20
- resolve_chapter: 22
- subtlety: 0.4
- cultivation_interval: 6
- max_distance: 12
- escalation_curve: FLAT
- trigger_condition: 三方卷宗同时标注沈越却无册可查，逼他必须找一个「留在岚洲的理由」
- resolve_condition: 沈越第一次在登记局与格雷正面对账，把「谁在供养」摊上桌面
- depends_on: []
- notes: 卷二开篇承一卷末三方共同命名；「未登记」既是自由也是死罪的具象化。
### MH10（星火网络的跨地域成形）

- type: EVENT
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 39
- resolve_chapter: 60
- subtlety: 0.4
- cultivation_interval: 10
- max_distance: 20
- escalation_curve: RISING
- trigger_condition: 星火网络跨地域扩展，矿谷—田垄—港口三点连线
- resolve_condition: 星火燎原、铁翼全面南下，网络转为可复制的战时组织
- depends_on: []
- notes: 方法脱离主角个人而流通的判据；「可持续、可被普通人掌握」的实证。
### MH11（格雷的档案系统与删改报告）

- type: ITEM
- dimension: CHARACTER
- lifecycle_state: PLANTED
- plant_chapter: 23
- resolve_chapter: 86
- subtlety: 0.5
- cultivation_interval: 10
- max_distance: 22
- escalation_curve: STAIRCASE
- trigger_condition: 格雷的档案被铁翼引用为净化名册，或她第一次沉默
- resolve_condition: 删改过的报告被公开，登记制与净化逻辑同源被揭穿
- depends_on: []
- notes: 「文明」成为屠杀上游的反讽；豁免与共谋的界限被反复拷问。
### MH12（「谁在供养，谁在享用」之问）

- type: INFORMATION
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 10
- resolve_chapter: 100
- subtlety: 0.4
- cultivation_interval: 12
- max_distance: 30
- escalation_curve: STAIRCASE
- trigger_condition: 提问方式被说出口，或被人听进去并当成疯话
- resolve_condition: 卷末把问题交给下一世继续追问，主题收束但不闭合
- depends_on: []
- notes: deep_conflict 的语言载体；从私下疑问升级为公开命题，是全书主题钩。
### MH13（多世轮回与穹外启程）

- type: EVENT
- dimension: WORLD
- lifecycle_state: PLANTED
- plant_chapter: 97
- resolve_chapter: 100
- subtlety: 0.7
- cultivation_interval: 5
- max_distance: 10
- escalation_curve: FLAT
- trigger_condition: 多世轮回装置启动（仅全书后 10% 章节点亮）
- resolve_condition: 新一代人类自信地走向星辰大海，全书收官
- depends_on: [MH01]
- notes: 每次转世必须保留一条前世因果线索，禁止概述式转世；仅作具象场景呈现。
