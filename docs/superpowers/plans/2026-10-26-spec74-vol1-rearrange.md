# Spec #74 实施计划 — 卷一口径重锚 + KR 重排 + 角色卡修复

> Spec: `docs/superpowers/specs/2026-10-25-spec74-vol1-rearrange.md`（rev6 GO）
> 数据根: `novel-xinghuo-vol1/`（gitignored——数据编辑就地落地+取证；PR 载体=spec/plan/lint 工具）
> 全部 task 数据承载/设计承载 → **协调者亲自实现**（infra 分流；无 leaf 分派）

## Task 1: 角色卡修复批（characters/）

- **改动**（全部就地编辑 `novel-xinghuo-vol1/characters/`）:
  - `major/xiao-man.md`: role 行 星象局→历法房；全卡递墨 token 清扫（L27「递过墨」+场景锚段——送墨拍删除）
  - `protagonist.md`: 增行首 `登记名：临` 字段（seeding 读取路径——L73 列表项形态不被正则识别，行首字段落地使读路径符合 #74 项 4 layout）；L226/240 定约表述统一「雪夜立约」；L240 城破后→围城期旌名波（老塾师拒用旌名而死，他接过半部《鉴录》）城破后固化；新增行首 `住所：` 字段（历法房→打铜巷→社学动线）
  - `major/lao-tuo.md`: 全卡 token 清扫（已故城破之夜战死→卷一后段误点战死；arc_summary L7 行规锚改雪夜立约）
  - `major/deng.md`: 增规则行「每世化身独立建立场景（禁零介绍登场）」
  - `major/hui-jin.md`: 墨字钥匙两化名 canonize（卷一两次不同化名同字）
- **test_kind**: characterization（数据不变量断言，非 TDD——数据编辑无红绿循环）
- **验证**: load_card_attributes 两次调用（`characters/major/` → xiao-man 性别代词=他、机构=历法房；`characters/` → protagonist 住所字段在）——**同时给 xiao-man.md 落显式 `性别：男`/`机构：历法房` 行首字段**（免 heuristic 回退漂移）；grep 旧 token 零残留（递墨/城破之夜/城破，战死/城破后他被夺名/星象局——含 lao-tuo L80「城破，战死」与 L7/L66 裸「城破之夜」变体）
- **复杂度**: infra（跨卡 canon 裁定承载）

## Task 2: volume_map 卷一全层重写

- **改动**（`novel-xinghuo-vol1/outline/volume_map.md` 卷一段）:
  - Objective 行重写（引擎留存轴口径）
  - 几何表落地（KR 1-48/49-95/96-143 + 阶梯 20/30/30/20 + 张力 20/35/25/20——卷一 143 精确，表内即终值）
  - KR 节点表按拍位全序重写：ch1 双钩/ch2 温情/ch3 双死（萤死怀里→他死→轮回显形+金句）/ch4 夺名链起+智识小胜◆读懂/ch5 智力爽◆复利反杀/ch6 定约/ch7 变现◆驿站少赔+三倍价余响/…/城破~95 帖木哥收官/老驼初遇95→切口104→立约114→战死124/卷末四轴快照结算
  - 前 12 章无连续 2 章空白；萤回触链 ~11+ 触点行（间隔≤8）
  - 金句/母题物象行按拍位重排；黄金三章约束块重写（围城期三拍）；跨卷桥接卷一侧随新章号
  - 住所动线成节（与 protagonist 住所字段两源一致）
- **验证**: Task 4 的 lint 工具跑过（密度/◆/回触/全序单调）
- **复杂度**: infra

## Task 3: 口径重锚 apply

- **改动**:
  - **手工重跨全部 12 卷标题 + `**章节范围**` 行**（`--apply` 只从 heading spans 派生 novel.json/frontmatter，不造 span）：各卷字数预算不变，逐卷 span = ceil(卷字数/3200)，尾卷收口使 max span end **恰为 3125**（逐卷 ceil 之和 ≥ 3125，余量在尾卷收敛）；卷一 span = 1-143（ceil(456000/3200)=143 精确，T2 章号即终值无回改环）。卷二+ **span** 重锚不违反过渡态政策（政策冻结的是节点表细排，非预算骨架）
  - 预算对账段重declare（字数不变/新章数口径）→ `just volume-budget novel-xinghuo-vol1 --apply` 写回 novel.json/frontmatter
  - `rhythm_principles.md` 卷一行重锚（工具不读此文件——手工编辑 + grep 验证）
  - `thread_map.md`：**编辑落在 `### <ID>` 线索详情的跨度/状态字段**（overview 行是派生镜像，`--repair` 会从详情重derive——只改 overview 会被静默回滚）；**前置子项：C1-C13 线索节紧凑管道格式规范化**（`- **状态**: RESOLVED｜**跨度**: …` 单行多字段 → 每行一字段——lint/sync 双解析器都把整块管道串当状态值，13 项 row_state_mismatch 的根因（25 为 findings 总数，含 12 项 planted_with_resolve 异因类）；C1(2-7)/C2(44-52) 正是卷一重锚对象，规范化为必做）；然后 `just pool-lint novel-xinghuo-vol1 --repair` derive overview → **post-lint grep 断言新章号存活**（A2 起始/B2 跨度等卷一锚行）
  - **MH1-12 planted_with_resolve（既有债，非 #74 造成）**：PLANTED 生命周期 + 兑现章=十二卷跨度——记录入 spec-deviations 为已知债（裁定归 foreshadowing 生命周期域/#79 前的卷层收束，非本 spec 施工面）；pool-lint 验收口径 = **row_state_mismatch 清零 + findings ⊆ 已知债清单**（MH 12 项允许保留，exit code 可为 1——证据形态：lint 输出逐项比对清单）
- **验证**: `just volume-budget novel-xinghuo-vol1` verdict=OK（无 re_budget_pending）；pool-lint findings ⊆ {MH1-12}（row_state_mismatch=0；预期 exit 1；证据=lint 输出逐项比对清单）
- **复杂度**: infra（工具写回 + 级联面）

## Task 4: 节点表 lint 工具（PR 载体）+ 验收全量

- **新增** `tools/lint_volume_nodes.py`（通用卷级节点表 lint，参数化 project_dir+卷号）:
  - 密度：前 N 章窗无连续 2 章空白（N=12）
  - 总量：节点表最大章号 == 卷 span end（防 apply 错配）
  - ◆ 三槽（**首发章号截止**语义，非计数）：`智力爽◆` 标记首次出现行章号 ≤5；`变现◆` 首现 ≤8；`智识小胜◆` 为分类标签不参与截止检查（缺标记行时 lint 对该槽报 FAIL 而非跳过——零 ◆ 行非合规态）
  - 萤回触：触点行间隔 ≤8 章
  - 全序单调：节点章号严格递增
  - 测试 `tests/unit/tools/test_lint_volume_nodes.py`（构造 tmp 卷表：违规各形态 FAIL/干净 PASS——G0.9 结构性用例豁免）
- **验收全量**（spec §4 逐条 → 命令，输出贴 progress）:
  - lint_volume_nodes 卷一 PASS；volume-budget OK；pool-lint findings ⊆ {MH1-12}（row_state_mismatch=0，预期 exit 1）
  - registry_seeding 播种 + name_registry 三行核对
  - load_card_attributes 预检（性别他/历法房/住所）+ 卡措辞随改两处 grep 零残留
  - `just check` EXIT=0（CI 面=unit test only——项目数据 gitignored，真实数据调用不进 justfile）
- **复杂度**: infra；**test_kind**: tdd_red_green（工具逻辑红绿）

## Task 5: 收尾

- spec-deviations 记录：三项半落地条目/数据 gitignored 交付形态/**MH1-12 既有债清单（pool-lint waiver）**/**thread_map 详情正文内旧口径锚在冻结下保留**（A1 推进形态/B2 第48章等——归各卷 outlining）/C 节规范化为 #74 前置修补说明；progress 验收证据；INDEX 状态、归档

## 验收覆盖表

| spec §4 | task | 验证命令 |
|---|---|---|
| 节点表无连续 2 章空白 + ◆ 三槽 | T2+T4 | `uv run python tools/lint_volume_nodes.py novel-xinghuo-vol1 --volume 1` |
| 萤回触可见 + 灰烬钥匙定稿 | T2+T4 | 同上（回触间隔项）+ grep hui-jin 墨化名 + volume_map 节点行两化名 token + 节点表行内「灯」零指称（人工口径——KR3 标题「灯在人在」豁免） |
| 五项卡修复 + 预检 + 卡措辞两处 | T1+T4 | load_card_attributes 断言 + grep 零残留 |
| volume-budget 收敛 + rhythm/thread 重锚 | T3 | `just volume-budget …` verdict=OK + pool-lint findings ⊆ {MH1-12}（row_state_mismatch=0，预期 exit 1）+ post-repair grep 新章号存活 |
| 阶梯 canon 一致 + 四轴快照 | T2+T4 | grep 阶梯四级名目与 story_frame 一致 + grep 卷末结算节点四轴 |
| 住所两源一致 | T1+T2 | grep protagonist 住所字段与卷纲动线行互证（同三地名） |
| rhythm_principles 卷一行重锚 | T3 | grep rhythm_principles 卷一行新章号 |
| G0.3 收敛 | T3 | volume-budget verdict=OK（隐含） |
| Objective 行无冲突 | T2 | grep 旧表述零残留 |

## Self-Review

- F947 合规：全部验收离线可复验（lint/预算工具/断言），零 LLM dispatch
- 契约面：无 SKILL/src 契约变更（纯数据+新独立工具）→ 无在途 artifacts 影响
- 顺序依赖：T1→T4（seeding 后预检）；T2→T3（预算声明随新表）；T3→T4（lint 需 apply 后章数）。**确定性注记**：卷一 143=ceil(456000/3200) 精确（genre-config 已 3200）——T2 写入即终值；lint 增「节点表最大章号 == 卷 span end」检查防总量错配
- registry_seeding 三行核对口径：登记名=临（读 T1 落地的 protagonist.md 行首 `登记名：临` 字段——原 L73 列表项形态不被正则识别，行首字段为 #74 项 4 layout）/代词白名单=他/禁用名=灯
