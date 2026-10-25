# Spec #75 · 跨章不变量门（cross-chapter-invariants）

> **Date:** 2026-10-25 | **Status:** Active (Revised R1 驳斥复核数据源/fixture/软依赖/机制 + R2 设计审查四空洞钉死：follower 数据通路/WARN-manifest 冲突/回归集可执行清单/写入方与 POV 基线归属 + G6.4 退役/契约连锁整节) | **Severity:** 🔴 P0（防复发核心） | **方法:** G 系新增六项跨章硬校验；旧九章作回归测试集——先证明门能抓，再上岗 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** 无（与 #72/#73 并行，框架侧） | **范围:** src/shenbi/gates/ 新增跨章校验族 / truth registry 数据源 / G 序列接线

> 源自总设计 §3。问题依据：现有 POV/texture/anti-ai 审计全部单章口径，ch1→ch2 人称断裂在单章审计里评 92 分通过；五处跨章硬伤（人称/称谓撞名/时间线/道具链/卡属性）每处单章看都「合格」。

## 1. 六项不变量

| # | 不变量 | 校验逻辑 | 数据源 |
|---|---|---|---|
| 1 | POV 人称一致 | 本章叙述人称（我/他映射的 POV 模式）与前章一致；变更须显式声明 | 前章正文 + **首章推导基线存 truth registry**（R1：povMode 为 F231 幽灵键不作数据源——novel.json/genre-config 均无此键） |
| 2 | 主角称谓字典 | 叙述中主角称谓 ∈ 白名单（登记名 + 代词白名单）；白名单外名字命中即 FAIL | **truth registry 称谓字典表（本 spec 新建）**——登记名值由 #74 项 4 接线；职务称/绰号（「历法房的小子」「黄仓吏」类）不属主角指称不触发（R1 误报面） |
| 3 | 时间锚单调 | 章内叙事日期不早于前章末锚点；回拨须有显式回拨标记 | truth 时间锚 registry + 前章末锚 |
| 4 | 物象道具链归属 | 母题物象实体出现时 owner 链可还原（当前持有者=前章末持有者或经手事件） | pending_hooks MH 表**实体实例化改造**（R1：现按母题不按实体——MH03 一行盖三张纸；registry 记录与正文冲突时**以正文为唯一真值源**——回归集防自证清白） |
| 5 | 角色卡属性一致 | 正文角色性别/所属机构/住所与角色卡一致 | characters/*.md |
| 6 | 资产连续性 | 钱袋/债务等账目跳变须有来源（收入/支出事件对账；**章末钩窗口内的消失/少一枚形态属合法悬念豁免**——ch10 型） | **particle_ledger.md**（R1 修正：G4.cd 账目钩是句式检查非对账机制；结构化金额行 + 阈值 ≥10 文触发，实物互折记折算注记） |

## 2. 施工面

- `src/shenbi/gates/` 新增跨章校验模块 `g4/cross_chapter.py`（纯校验无副作用幂等）；**归属：pipeline-scene-split 步内逐章调用**（拆分后章文件在盘即可跑，独立于 settling 时序）；首章跳过前章依赖项；**双章批语义：章 N 前章恒为 N-1**
- **前章末态数据通路（R2-R1 钉死——settling 是 step 9 晚于拆分 step 5，registry 对 follower 章永缺直接前章）**：主源 = **双备忘时间锚声明行 + 前章正文确定性派生**（planning 同批产出两份 memo，拆分步时俱在；POV/称谓从正文正则推导）；registry 三表 = 滚动聚合**交叉校验层**（非检查时唯一真值）——彻底解耦检查时序与 settling 时序
- truth registry 三表（genesis 播种 + 收束滚动更新；**写入者：state-settling 契约扩展**——R1 决策，非新 skill）：
  - **称谓字典** `truth/name_registry.md`（登记名+代词白名单+合法别称；#74 项 4 接线登记名值）
  - **时间锚** `truth/timeline.md`（**锚规范化层 R1**：current_state.md 时间锚列既有半成品接线——绝对锚（腊月初十）与相对锚（老塾师走后第七日）双列存储，比较用绝对锚；**回拨标记语法 R1 新约定**：memo 场景预算块增「时间锚」声明行，回拨场景行首 `[回拨]` 标记——planning SKILL 同批扩展）
  - **物象 owner 链** `truth/prop_registry.md`（实体实例化：每实体独立条目 + owner 事件流；播种 = 确定性 seeding 脚本从 characters/ 卷纲生成（#75 工具面），MH 详情段拆分由人工/LLM 在 #79 重生成期完成——不要求 genesis skill 扩展）
- **三表写入方分工（R2-R4 钉死）**：章层滚动 = state-settling 契约扩展（updates 增三表，append_dedup 键：timeline=章号 / prop_registry=实体名 / name_registry=卷层 overwrite）；卷层初值播种 = 确定性 seeding 脚本（#75 交付，读 characters/ 生成 name_registry 初值——数据由 #74 项 4 定案）；**POV 基线（R2-R4）：checker 从前章正文直接确定性推导**（首章叙述人称正则推导，无需 registry 预播种；registry timeline 的 POV 列仅交叉校验）
- **回归集 fixture 完整清单（R2-R3 钉死）**：`tests/fixtures/cross-chapter-regression/` 收——ch1-10 十章 + `characters/major/xiao-man.md` + `truth/{pending_hooks,particle_ledger,current_state}.md`（全部真实产物 G0.9 ✓ + G0.11 哈希）；**三新表（name_registry/timeline/prop_registry）不入库**——测试内 tmp_path 构造（G0.9 结构豁免：不冒充 skill 产物入库，#72 先例）；**调用面 = Python 函数直调**（tests import `g4_cross_chapter`——`shenbi-validate G4` 的 skill 键路由闭集不动，独立 CLI 动词 out of scope 记档）；#79 quarantine 副本保留原位
- 失败消息携带违规位置与前章证据（沿用 G4.vo 失败消息模式）+ **修复者提示**（R2-Y4：不变量 1/2/3 → planning+drafting 重派（现熔断回 drafting 机制保留）；4/5 → settling/卡修；6 → settling——消息首段标修复者）
- **G6.4 timeline 正则分支退役（R2-Y1）**：其阿拉伯数字正则永远匹配不了「腊月初十」类锚（旧伤漏网技术根因）——本 checker 上岗同批移除 G6.4 timeline 分支，避免双头检查
- **修订重验扩展（R2-Y4）**：#72 `_revalidate_revised_chapter` 增跨章复跑（修订可推翻 step 5 的跨章 PASS）
- **WARN 语义钉死（R2-R2）**：数据缺口 WARN 仅走 structlog 日志 + settle 滚动进 `truth/audit_drift.md`（观察面），**不落 manifest**——manifest 只记 PASS/FAIL，#72 release_split settled 谓词（latest-per-key 严格 PASS）语义零改动

### 契约与注册同步清单（R2-Y6）

- state-settling SKILL updates 增三表（append_dedup 键如上）→ lint-contracts + generate（deps.json/truth-files.yaml/三表条目 + read extractor：timeline/prop_registry 尾窗读取 `recent_increments` 先例——3125 章尺度防线性读放大）
- G4.ss 增三表结构校验（防畸形行直达 checker）
- memo「时间锚声明行」为硬门消费的新增必备字段——**AGENTS 契约升级纪律**：随批声明「无在途 artifacts 受影响」（#79 前旧管线冻结——旧 memo 不再被门消费，quarantine 即终点）
- planning SKILL 场景预算块增「时间锚」行 + `[回拨]` 标记约定（R1 机制）；drafting SKILL 同步（时间锚落款）
- **#79 反向同步（R2-Y5）**：滚动重置范围增 timeline/prop_registry（章层重置）+ name_registry（卷层保留）；G0.11 MIRROR_MAP 对回归 fixture 的镜像生命周期——随 #79 quarantine 后移除条目（声明式条款入 #79 修订）
- 不变量 5 住所数据源（R2-Y5）：卡内「当前住所」字段口径（#74 项 5 落卡 + 卷纲轨迹行——两源一致由 #74 验收）

## 3. 回归测试集（旧十章）

门禁上岗前对回归集（**旧 ch1-10 实际十章**，fixture 形态）跑一遍，**六项五伤全部命中**才算合格：

1. ch1↔ch2 人称断裂（不变量 1）
2. ch4-5 主角被称「灯」+ ch7 女主撞名（不变量 2）
3. ch1 初十 vs ch2 初七/初八（不变量 3）
4. 红纸包经手链断裂（小满→萤→老妇→井台女不可还原）（不变量 4）
5. 小满性别/星象局机构名（不变量 5）

## 4. 验收

- 六项不变量对回归集复跑：上表五伤全部被抓到（真阳性；**以正文为唯一真值源**——registry 记录不作为回回归对的真值）
- 干净正文（构造正常相邻章）零误报（真阴性）
- 纯校验幂等、无输出文件副作用；`just check` 全绿（**CI 可见——回归集已 fixture 化**）
