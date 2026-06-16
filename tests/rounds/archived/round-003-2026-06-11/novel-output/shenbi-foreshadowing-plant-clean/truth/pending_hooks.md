---
project: 星火燃穹：位面解放战争史
last_updated: 2026-06-12
version: 0.4.0
---

# 伏笔池

**活跃伏笔数**: 9
**已解决伏笔数**: 0

## 活跃伏笔总览

| Hook ID | 内容概要 | 类型 | 维度 | 微妙度 | 升级曲线 | 种植章 | 状态 | 核心伏笔 |
|---------|---------|------|------|--------|---------|--------|------|---------|
| hook-ch1-001 | 灵能修炼贷款：债务体系揭示 | GENUINE | THEMATIC | 0.45 | RISING | 1 | PLANTED | 是 |
| hook-ch1-002 | 金手指灵能感知——他人不察的低频嗡鸣 | GENUINE | CHARACTER | 0.75 | RISING | 1 | PLANTED | 否 |
| hook-ch1-003 | 外部势力碎片化暗示（列塔尼亚/涅普敦） | GENUINE | STRUCTURAL | 0.80 | FLAT | 1 | PLANTED | 否 |
| hook-ch2-001 | 废料场铭文金属片——同心圆六角星符号 | GENUINE | SYMBOLIC | 0.50 | RISING | 2 | PLANTED | 是 |
| hook-ch3-001 | 阿莲手腕褪色灵能印记——非庶民非贵族的第三类 | GENUINE | CHARACTER | 0.65 | RISING | 3 | PLANTED | 否 |
| hook-ch4-001 | 金手指首次有意识分解——炉芯回路自动拆解成基础铭文单元 | GENUINE | CHARACTER | 0.60 | RISING | 4 | PLANTED | 否 |
| hook-ch5-001 | 阿莲口中的"小禾"——她唯一一次主动提起的名字 | GENUINE | CHARACTER | 0.55 | FLAT | 5 | PLANTED | 是 |
| hook-ch5-002 | 催收组长齐管事的"我不是来为难你的，我是来帮你理清账目的" | SMOKESCREEN | STRUCTURAL | 0.40 | RISING | 5 | PLANTED | 否 |
| hook-ch5-003 | 被雨水浸烂的地下传单残片——"……不靠救世主，全靠……" | SIDE_SHADOW | SYMBOLIC | 0.80 | RISING | 5 | PLANTED | 否 |

## hooks

- id: hook-ch1-001
  content: "催收员告知林烽灵能修炼贷款已逾期，墙上告示列出逾期处罚条款——强制劳役或灵能剥离。林烽第一次意识到这个世界'欠债'的含义远比现代严重。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: THEMATIC
  subtlety: 0.45
  plant_chapter: 1
  cultivation_interval: 3
  last_reinforced: 1
  max_distance: 150
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false
  notes: "种植位置：对话段落（催收员互动）+ 环境细节（墙上告示）。全书'个人债务→系统债务→文明债务'主题的起点。催收员处理为'按规矩做事的另一个庶民'，暗示压迫来自系统而非个人——这一处理本身是伏笔的一部分。"

- id: hook-ch1-002
  content: "林烽穿越后感知到空气中存在他人似乎不察的灵能嗡鸣——低频震颤像电流穿过骨骼。章末在破屋独处时，安静环境中这种感知变得更清晰。他将其归因为'穿越后遗症'。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.75
  plant_chapter: 1
  cultivation_interval: 5
  last_reinforced: 1
  max_distance: 80
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：环境探索段落（穿越后感知锈泥巷的五感描写中嵌入）+ 章末独处段落。通过日常五感描写自然嵌入，不设单独'金手指展示'段落。不展示分解/塑形/融合的具体操作。第4章首次科学揭示能力原理。"

- id: hook-ch1-003
  content: "锈泥巷灵能炉底部磨损铭文残存非庶民文字（列塔尼亚制造标记）；催收员提及'上面定的规矩，我只管执行'；邻居随口说'矿场那边又要人了，涅普的订单赶不完'——三处碎片分散嵌入不同场景，不给读者整合信息的机会。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: STRUCTURAL
  subtlety: 0.80
  plant_chapter: 1
  cultivation_interval: 4
  last_reinforced: 1
  max_distance: 60
  escalation_curve: FLAT
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：三处碎片分别嵌入——(1)环境探索段落（灵能炉铭文）、(2)对话段落（催收员台词）、(3)邻里对话段落（邻居随口提及）。分散在不同场景中阻止读者首次阅读时整合。FLAT曲线保持碎片化暗示节奏，第3章起逐步具象化后转为RISING。"

- id: hook-ch2-001
  content: "林烽在废料场帮工清理矿渣时，一块巴掌大的金属片从渣堆中滑出——表面灰绿色纹路不是锈，而是排列规律的几何图案：三层同心圆中心是六角星符号。金属片非天然合金，比钢密、比铜轻。林烽贴肉揣了两里路走回锈泥巷，它始终冰凉。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: SYMBOLIC
  subtlety: 0.50
  plant_chapter: 2
  cultivation_interval: 6
  last_reinforced: 2
  max_distance: 25
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false
  notes: "种植位置：日常过渡段落（废料场劳动力换取口粮场景）。金属片在清理矿渣时自然滑出——不设专门'发现宝物'场景，嵌入日常劳动的单调节奏中降低突兀感。巴掌大的物理触感、恒温冰凉的体温差异作为识别特征。三层同心圆+六角星的几何规律性暗示人工制品而非自然物，但不揭示来源。关联A3暗流一（梅德兰底层沉默觉醒）和种子一（废料场铭文）。RISING曲线：捡到不解(Ch2)→被林烽灵能无意激活并微微发热(约Ch8)→首次破译部分信息(约Ch14)→揭示前穿越者梵光政权关联(约Ch19)→成为关键线索/工具(约Ch25前)。"

- id: hook-ch3-001
  content: "阿莲递给林烽一块黑面包时，手腕上露出半截已褪色的灵能印记——不是庶民的方形庶民印，也不是贵族的菱形贵族印，而是某种只剩残边的圆形图案。她发现林烽在看时迅速拉下袖子，用'小时候烫的'敷衍过去——但她说这句话时声音比平时低了半度。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.65
  plant_chapter: 3
  cultivation_interval: 7
  last_reinforced: 3
  max_distance: 50
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：对话段落（阿莲日常互动中的短暂视觉细节）。在黑面包传递的自然动作中一闪而过——不设特写镜头，依靠读者自己注意到这个异常。圆形灵能印记暗示阿莲可能来自梅德兰灵能体系之外的第三类出身。连接B4情感/人性线和阿莲角色弧（Ch3-10）。RISING曲线：首次被看到但被敷衍(Ch3)→林烽开始注意阿莲的其他异常细节(约Ch6)→阿莲在空袭中更主动的行为暴露出训练痕迹(约Ch9)→阿莲牺牲后圆形印记的真相由第三方揭示(约Ch11)→成为林烽理解'底层不只是受害者'的认知锚点(约Ch15前)。"

- id: hook-ch4-001
  content: "林烽首次有意识驱动分解能力时，锈泥巷公共灵能炉的一根故障铭文管在他指尖下'自动'拆解成六个基础铭文单元——排列方式整齐得不像是随机碎裂，更像是某种他从未学过的语法。炉芯重新启动后一切如常，但林烽盯着自己的手指发了整整十秒的呆——他在现代写代码时也有过这种感觉，叫'debug时无意发现了底层API'。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.60
  plant_chapter: 4
  cultivation_interval: 4
  last_reinforced: 4
  max_distance: 30
  escalation_curve: RISING
  depends_on:
    - hook-ch1-002
  core_hook: false
  promoted: false
  notes: "种植位置：日常过渡段落（公共灵能炉维修帮工场景）。通过维修故障设备的日常行为展示金手指的首次应用——不是训练场、不是危机时刻，而是在'帮邻居修炉子换一顿午饭'的琐事中。'debug时无意发现底层API'的现代类比将灵能铭文与计算机编程建立认知桥梁——暗示林烽的金手指本质上是'看到灵能的底层结构'而非'更强的灵能'。连接B1灵能科技/种田线。RISING曲线：日常场景中首次有意识使用(Ch4)→开始在独处时有意识地重复实验(约Ch7)→在救助阿莲时第一次在压力下使用(约Ch9-10)→能力边界和代价开始显现(约Ch13)→首次结合现代思维进行系统性灵能实验(约Ch28)。"

- id: hook-ch5-001
  content: "阿莲在帮林烽补第三件工服时，忽然停下针线，看着锈泥巷尽头被灵能炉烟尘染成灰黄色的天空。'我以前认识一个人，'她说，'叫小禾。她跟你一样，刚来的时候也以为算清楚账就能找到出路。'这是阿莲第一次主动提起自己的过去。林烽等她继续说，但她把线头咬断，站起来说：'补好了。明天你自己去西巷交工服，我不去了。'"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.55
  plant_chapter: 5
  cultivation_interval: 15
  last_reinforced: 5
  max_distance: 91
  escalation_curve: FLAT
  depends_on: []
  core_hook: true
  promoted: false
  notes: "种植位置：日常对话段落（缝补工服的安静时刻）。在重复劳动的低张力场景中自然引出——阿莲在机械性动作（缝补）中放下戒备，这是日常生活中最容易说出真心话的时刻。'小禾'这个称呼通过阿莲之口一次性植入，本章不再赘述。FLAT曲线设计意图：全书最安静的伏笔之一，不做章节级强化，依靠角色本身的命运（阿莲在Ch10牺牲）使其在林烽和读者心中持续发酵，直到Ch96以完全不同的形式回收。连接种子二（阿莲口中的'小禾'）、B4情感/人性线（独立情感线）。全书情感锚点的起点——这不是一个'等待解释的谜题'，而是一个'等待兑现的承诺'。"

- id: hook-ch5-002
  content: "锈泥巷庶民贷款管理处换了新的催收组长。齐管事——一个四十出头、戴单片灵能眼镜、说话永远不提高音量的人——接手了林烽的贷款账户。他的前任三个月前突然调离，锈泥巷没人知道原因。林烽第一次见他时做好了被为难的准备，但齐管事翻开账本后只说了句：'你的复利条款有三处计算错误——我不是来为难你的，我是来帮你理清账目的。'他的手指点在其中一行数字上，单片眼镜的反光遮住了他的眼神。"
  state: PLANTED
  operation: plant
  type: SMOKESCREEN
  dimension: STRUCTURAL
  subtlety: 0.40
  plant_chapter: 5
  cultivation_interval: 5
  last_reinforced: 5
  max_distance: 12
  escalation_curve: RISING
  depends_on:
    - hook-ch1-001
  core_hook: false
  promoted: false
  notes: "种植位置：对话段落（催收管理处场景）。在读者已经建立'催收系统=压迫'的条件反射后，引入一个表面友善的催收组长——他的友善本身是最大的可疑。烟雾弹的误导效果：读者被引导认为齐管事是隐藏更深、更危险的压迫者（可能替代催收员成为新的对抗焦点）。退出策略：齐管事实为梅德兰买办阶级内部被排挤的边缘人物——他的'帮你理清账目'是真话而非伪装。他正在秘密收集买办与列塔尼亚勾结操纵庶民债务的证据，意图在阶级内部权力斗争中自保。第12章林烽进入地下网络后，齐管事通过第三方向他传递了一份锈泥巷庶民贷款的真实账目——揭示买办从中抽成的比例。第17章齐管事被发现并处决，他的死亡成为林烽理解'买办阶级内部也有裂缝，但裂缝里的人同样会被吞噬'的第一课。烟雾弹在第17章由读者和主角同时获知真相时完成释放。RISING曲线：初见建立怀疑(Ch5)→陆续释放'齐管事在隐瞒什么'的线索强化读者猜疑(约Ch7-10)→林烽收到匿名账目但不知来源(Ch12)→真相揭示+角色死亡(Ch17)。"

- id: hook-ch5-003
  content: "林烽去公告栏查看灵能炉维修排班表时，墙角雨水洼里泡着半张传单——纸张已经浸烂大半，残存文字只能辨认出'……不靠救世主，全靠……'六个字，以及下方一个被水渍模糊的齿轮图案。林烽弯腰看了两秒，起身时脚后跟无意中把残纸踢进了墙缝。他说不清自己为什么没有捡起来读——也许是锈泥巷教会了他'不该看的东西别看'。"
  state: PLANTED
  operation: plant
  type: SIDE_SHADOW
  dimension: SYMBOLIC
  subtlety: 0.80
  plant_chapter: 5
  cultivation_interval: 8
  last_reinforced: 5
  max_distance: 40
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：日常过渡段落（查看公告栏的例行公事场景）。在主角做一件最日常的事情（查排班表）时，让地下传单作为环境噪音出现——不是情节驱动，而是氛围驱动。'不该看的东西别看'是林烽穿越以来学会的第一条锈泥巷生存法则——此时的林烽还在'独善其身'的犬儒惯性中，这个细节暗示他内心的自我保护机制已经开始松动（他说不清为什么没有捡）。齿轮图案是梅德兰地下抵抗网络的符号雏形——此时读者和林烽都不知道这个符号的含义。连接A3暗流一（梅德兰底层沉默觉醒）。RISING曲线：作为环境噪音首次出现(Ch5)→类似的齿轮符号在更多场景中作为背景元素出现(约Ch9-12)→林烽首次认出这个符号与地下组织的关联(约Ch15)→地下网络公开化后齿轮成为公开标识(约Ch20-30)→成为梅德兰解放运动的象征符号(约Ch40后)。"


## 第5章伏笔种植汇总

**章节**: 第5章
**写入文件**: `truth/pending_hooks.md`
**种植条目数**: 3 / 8（密度预算）

### 已种植项

| Hook ID | 类型 | 维度 | 微妙度 | 升级曲线 | max_distance | 依赖 |
|---------|------|------|--------|---------|--------------|------|
| hook-ch5-001 | GENUINE | CHARACTER | 0.55 | FLAT | 91 | — |
| hook-ch5-002 | SMOKESCREEN | STRUCTURAL | 0.40 | RISING | 12 | hook-ch1-001 |
| hook-ch5-003 | SIDE_SHADOW | SYMBOLIC | 0.80 | RISING | 40 | — |

### 种植位置分析

| Hook ID | 种植位置 | 场景类型 | 种植策略依据 |
|---------|---------|---------|-------------|
| hook-ch5-001 | 缝补工服对话段落 | 日常对话 | 日常段落是埋伏笔的最佳位置——读者在低张力场景中放松警惕，'小禾'作为随口一提的名字自然嵌入，不会引起过度解读 |
| hook-ch5-002 | 催收管理处对话段落 | 冲突-对话 | 对话段落适合种植信息型伏笔——齐管事的台词既是规则揭示也是人物建立，双重功能降低伏笔的突兀感 |
| hook-ch5-003 | 查看公告栏过渡段落 | 日常过渡 | 过渡段落适合种植氛围型伏笔——地下传单作为环境噪音出现，在不占用叙事焦点的前提下完成信息注入 |

### 本章未种植项（延迟至后续章节）

| 原因 | 条目 | 计划种植章 |
|------|------|-----------|
| 密度预算已达3/8，剩余5个操作位预留给reinforce/trigger/resolve操作 | 种子三（列塔尼亚炸弹商标）的进一步具象化 | 第11章 |
| 本章以情感和主题铺垫为主，金手指技术线保持Ch4的展示强度即可 | 金手指分解能力的第二次实验性使用 | 第7章 |
| 外部势力信息需在阿莲牺牲(Ch10)后以更强烈的方式揭示 | 列塔尼亚/涅普敦的系统性揭示 | 第9-11章 |

### 密度核算

| 操作类型 | 本章数量 |
|---------|---------|
| plant | 3 |
| reinforce | 0 |
| trigger | 0 |
| resolve | 0 |
| **合计** | **3 / 8** |

### 跨线程依赖检查

| Hook ID | depends_on | 被依赖条目状态 | 检查结果 |
|---------|-----------|--------------|---------|
| hook-ch5-001 | [] | — | 通过：独立新启线程，无依赖冲突 |
| hook-ch5-002 | [hook-ch1-001] | PLANTED (Ch1) | 通过：依赖项已种植，可正常建立关联 |
| hook-ch5-003 | [] | — | 通过：独立新启线程，无依赖冲突 |

### 烟雾弹退出策略确认

**hook-ch5-002 (SMOKESCREEN)**
- 退出时机：第17章
- 退出方式：齐管事被买办处决 + 林烽通过第三方获知真相（包括齐管事生前传递的真实账目）
- 读者体验设计：第5-16章读者怀疑齐管事是隐藏反派 → 第17章揭示他是系统内部的边缘反抗者 → 反转带来"敌人不只在明处，盟友也不一定活着"的认知升级
- 叙事功能：为第12章林烽进入地下网络提供信息入口（匿名账目），为买办阶级内部矛盾提供第一个具象案例
