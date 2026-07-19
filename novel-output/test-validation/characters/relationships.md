# 角色关系矩阵

> 本文件为关系权威。角色性格底色存于各自角色卡（`characters/major/*.md`、`characters/minor/*.md`），此处不重复（去重铁律）。
> slug 引用规范：所有关系以 slug 互引，避免姓名歧义。本步锁定主要角色 slug，对应角色卡由后续 Phase 2/3 生成。

## 一、关系总览矩阵

| 角色 | lu-heng（主角） | mo-qingluo | pei-ji | shen-yan | a-zhi |
|------|----------------|------------|--------|----------|-------|
| **lu-heng** | — | 盟友/债主→生死相托（4） | 追缉/理念宿敌（5） | 师友/隐患（4） | 庇护/被庇护（3） |
| **mo-qingluo** | 欠命债→甘愿血契（4） | — | 旧识/互相提防（3） | 客户/不信任（2） | 雇主/姐姐式（3） |
| **pei-ji** | 必缉之异端（5） | 边境走私眼中钉（3） | — | 幕后大敌（4） | 不入眼的蝼蚁（1） |
| **shen-yan** | "还原先民之学"的钥匙（4） | 可用之棋（2） | 被通缉对象（4） | — | 不关心（1） |
| **a-zhi** | 唯一会听她说话的人（3） | 雇主姐姐（3） | 恐惧对象（2） | 陌生（1） | — |

> 强度 1–5：1＝淡漠/功能性，3＝稳定互动，5＝生死攸关/执念级。

## 二、角色 slug 锁定（待角色卡生成）

| slug | 姓名 | 角色 | 卡片去向 |
|------|------|------|----------|
| lu-heng | 陆衡 | 主角 | `characters/protagonist.md`（已生成） |
| mo-qingluo | 莫青萝 | 灰港走私商 / 第一盟友 | `characters/major/mo-qingluo.md`（待生成） |
| pei-ji | 裴寂 | 圣座异端裁判官 / 主要对手 | `characters/major/pei-ji.md`（待生成） |
| shen-yan | 沈砚 | 地下密会魁首 / 异端学者 | `characters/major/shen-yan.md`（待生成） |
| a-zhi | 阿织 | 源息稀薄的素民少女 | `characters/major/a-zhi.md`（待生成） |
| tie-wuchang | 铁无常 | 灰港码头工头 | `characters/minor/tie-wuchang.md`（待生成） |
| bai-shou | 白首 | 知情的老源贵 | `characters/minor/bai-shou.md`（待生成） |

## 三、关系条目（slug 化）

### 关系 1：lu-heng ↔ mo-qingluo
- **relationship_type**: 恩债盟友 / 走私商与异乡人
- **intensity**: 4
- **key_exchange_summary**: 陆衡在灰港码头被工头铁无常刁难时，莫青萝以"这人能替我算清三年来铁无常吃掉的货账"为由将他赎下，实则看出他记账的功夫远超寻常账房。两人从雇佣起步：青萝给他食宿与灰港的生存常识，陆衡替她核账、辨别货源真伪。当裴寂持烬刑令追至，青萝为给陆衡争取逃亡时间，违心立下一道"护送异端出境"的血契（律五），关系自此由债主雇工升级为以命相托。陆衡始终因青萝为他立血契而愧疚，这也成为他日后必须解开血契、或推翻律五桎梏的动机之一。
- **first_active_chapter**: 1
- **last_active_chapter**: ongoing

### 关系 2：lu-heng ↔ pei-ji
- **relationship_type**: 追缉者与被缉者 / 理念宿敌
- **intensity**: 5
- **key_exchange_summary**: 裴寂是圣座异端裁判所派驻南境的息卫，律十（沉默之律）与律四（异端裁定）的执行者。最初他只把陆衡当作又一个小丑般的散布谬说者，直到亲眼读到陆衡那张"借息—还息能量账本"——他第一次看到比圣座典籍更精准地描述源息流向的东西。追缉自此由公务变成执念：他既害怕陆衡是对的（那他半生烬刑过的人皆是冤魂），又必须证明陆衡是错的（否则圣座合法性崩塌）。两人在灰港、赤霞边境、余烬荒原边缘三度正面交锋，每次都是陆衡以证据逃、裴寂以铁律追。
- **first_active_chapter**: 3
- **last_active_chapter**: ongoing

### 关系 3：lu-heng ↔ shen-yan
- **relationship_type**: 师友 / 危险的合作者
- **intensity**: 4
- **key_exchange_summary**: 沈砚是地下密会"还原先民之学"运动的幕后魁首，表面是灰港一名制墨的老匠人。他最先识破陆衡"不懂咒文却懂原理"的价值，主动提供密会珍藏的先民晶书残片，换取陆衡用现代方法论帮其解读。两人亦师亦友：沈砚给他这个世界的史料与禁典，陆衡给沈砚一套能把碎片串成体系的方法。但隐患在于——沈砚的终极目标并不止于"还原"，密会中已有人开始尝试复刻镜像三禁（律七）以求速成。陆衡越接近真相，越像在给一颗他无法控制的火种添柴。
- **first_active_chapter**: 2
- **last_active_chapter**: ongoing

### 关系 4：lu-heng ↔ a-zhi
- **relationship_type**: 庇护者与被庇护者 / 跨阶层友谊
- **intensity**: 3
- **key_exchange_summary**: 阿织是灰港一名源息极稀的素民少女，在青萝货栈做杂工。她听不懂陆衡讲的"能量守恒"，却是第一个不把他当疯子、而把他的话当真的人——因为她一生都被圣座"源贵/素民"之分踩在脚下，陆衡那句"源息浓度不决定一个人的价值"是她听过最暖的话。陆衡则从阿织身上第一次具象地看到：圣座的知识垄断不仅是认知问题，更是吃人的阶层压迫。阿织是陆衡"知识普惠"理想的第一个受益者，也是他最柔软的牵挂。
- **first_active_chapter**: 1
- **last_active_chapter**: ongoing

### 关系 5：mo-qingluo ↔ pei-ji
- **relationship_type**: 边境走私商与裁判官 / 旧识互相提防
- **intensity**: 3
- **key_exchange_summary**: 莫青萝的走私线长期游走在律八（边境自治旧约）与律四之间，裴寂多次想借异端之名入灰港抄她的货，都被她以旧约为盾挡回。两人是老对手，彼此摸得清底牌：青萝知道裴寂不是贪官、是真信那套秩序，裴寂也知道青萝不是异端、只是个趁乱吃饭的商人。正因如此，当青萝为陆衡立血契时，裴寂反而迟疑了——他读得出这道血契背后的分量。
- **first_active_chapter**: 3
- **last_active_chapter**: ongoing

### 关系 6：shen-yan ↔ pei-ji
- **relationship_type**: 密会魁首与裁判官 / 幕后大敌
- **intensity**: 4
- **key_exchange_summary**: 沈砚是裴寂真正想抓却始终抓不到的"幕后供给者"。裴寂肃清了南境十几处密会据点，每次都晚一步——沈砚像知道裁判所的每一步棋。两人从未照面，却已博弈多年。裴寂死追陆衡，一半原因正是怀疑陆衡是沈砚放出来的诱饵。
- **first_active_chapter**: 4
- **last_active_chapter**: ongoing

## 四、网络说明

- 本步共锁定 **4 位主要角色**（mo-qingluo、pei-ji、shen-yan、a-zhi）与 **2 位次要角色**（tie-wuchang、bai-shou）的 slug。
- 关系条目共 6 对，满足"≥3 对且含主角与每位主要角色"的要求。
- 角色性格底色、voice_profile、archetype_sources 将在后续 Phase 2/3 的角色卡中定义，本文件不重复（去重铁律）。
