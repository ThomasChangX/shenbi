# Spec #75 跨章不变量门 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development / executing-plans, task-by-task.

**Goal:** 六项跨章不变量硬校验（POV/称谓/时间锚/物象链/卡属性/资产）+ truth registry 三表 + scene-split 步接线 + 旧十章回归集（五伤真阳性）。

**Architecture:** 双源数据通路（memo 声明行 + 前章正文确定性派生为主源；registry 交叉校验）；checker `g4/cross_chapter.py` 挂 scene-split 步内逐章调用；manifest 独立键 G4.xc；WARN 只走日志+audit_drift。回归集 fixture 化（真实产物），三新表 tmp_path 构造。

**Tech Stack:** 既有 G4 checker 形态 / record_gate_result / planning 场景预算块机器可解析格式（#72）/ recent_increments extractor 先例。

## Global Constraints（spec rev3）

- 六不变量：POV 人称（正文推导）/称谓（白名单+三信号绑定：主语位/内汲动词/邻句共指任二）/时间锚（memo 声明行+中文锚规范化，[回拨] 标记）/物象（正文唯一真值+经手事件还原）/卡属性（性别/机构/住所）/资产（memo 余额声明行主源，≥10 文阈值，章末钩窗口悬念豁免）
- 双章批：章 N 前章恒为 N-1；首章跳过前章依赖项
- manifest 键 `(pipeline-scene-split, G4.xc)`；WARN 不落 manifest（structlog + audit_drift）
- 修复者路由消息（1/2/3→planning+drafting；4/5→settling/卡；6→settling）；修订重验双向扇出
- registry 三表：name_registry（卷层 overwrite+透传）/timeline+prop_registry（章层 append_dedup：键=章号/实体名）；尾窗读取
- G6.4 timeline 正则分支退役；POV/中文锚正则确定性（无 LLM）
- fixture：ch1-10 + xiao-man.md + truth/{pending_hooks,particle_ledger,current_state}.md 真实拷入 + G0.11 哈希；三新表 tmp_path 构造；测试函数直调
- 纯校验幂等零副作用；conventional commits；G0.9 纪律

---

### Task 1: 回归集 fixture + checker 骨架（前章定位/首章跳过/双源读取）

**复杂度: infra · test_kind: tdd_red_green**

**Files:**
- Create: `tests/fixtures/cross-chapter-regression/`（十章+卡+truth 三件拷贝）+ `tests/fixtures/cross-chapter-regression/MANIFEST.sha256`（G0.11——按 justfile check_fixture_mirror 形态；若 MIRROR_MAP 需登记则 tools/lint_fixture_mirror 同步）
- Create: `src/shenbi/gates/g4/cross_chapter.py`（入口 `g4_cross_chapter(fps, rd, project_dir, repo_root) -> str`——签名循既有 checker；内部：章号解析/前章=N-1/首章跳过/`_load_memo_declarations`（场景预算块解析复用 #72）+`_load_prev_chapter`）
- Test: `tests/unit/gates/g4/test_cross_chapter_skeleton.py`

**Interfaces:**
- Produces: `check_cross_chapter(chapter_path, prev_path, memo_path, ctx) -> list[str]`（六项分发骨架，本 task 空实现）+ `CrossChapterContext`（project_dir/卡目录/registry 可选/白名单可选）
- fixture 拷贝：`novel-xinghuo-vol1/chapters/chapter-{1..10}.md` + `characters/major/xiao-man.md` + `truth/{pending_hooks,particle_ledger,current_state}.md`（只拷不动源）

- [ ] 失败测试（骨架：首章跳过返回 []；前章定位 N-1；双源读取 memo 声明行）→ 红
- [ ] 实现 + fixture 拷贝 + 哈希 → 绿
- [ ] `uv run pytest tests/unit/gates/g4/test_cross_chapter_skeleton.py -q` + `just check`（mirror lint 过）→ 提交 `feat(gates): spec75 T1——checker 骨架 + 回归集 fixture`

### Task 2: 不变量 1 POV + 2 称谓（正文推导 + 三信号绑定）

**复杂度: infra · test_kind: tdd_red_green**

**Files:** Modify `cross_chapter.py`；Test `tests/unit/gates/g4/test_xc_pov_name.py`

- POV：叙述人称推导（段首句「我」密度 vs 「他」密度——正则闭集我/你/他/她 + 段落级投票）；本章 vs 前章模式不一致且 memo 无 POV 变更声明 → FAIL（修复者提示 planning+drafting）
- 称谓：白名单（ctx.name_whitelist：登记名+代词；缺省 [「临」,「他」]）+ 三信号绑定（主语位/内汲动词绑定「在心里/暗自/寻思」类/邻句代词共指）——白名单外名命中主角绑定 → FAIL；首章推导基线=首章正文
- 用例：fixture ch1→ch2 人称断裂真阳性；ch4-5「灯」绑定真阳性（三信号形态）；真阴性构造（白名单内+职务称不触发）
- 提交 `feat(gates): spec75 T2——POV 人称一致 + 称谓字典三信号绑定`

### Task 3: 不变量 3 时间锚（声明行 + 中文锚规范化 + [回拨]）+ planning SKILL 扩展

**复杂度: infra · test_kind: tdd_red_green**

**Files:** Modify `cross_chapter.py` + `skills/shenbi-chapter-planning/SKILL.md`（场景预算块增三声明行：时间锚/余额/POV——机器可解析格式 `- 时间锚: 腊月初十｜- 余额: 一百九十二文｜- POV: 他`，回拨 `- 时间锚: [回拨]腊月初五`）；Test `test_xc_timeline.py`

- 中文锚规范化：`腊月初十`→(12,10)；`初十`（无月）→继承前锚月；相对锚（`老塾师走后第七日`）→解析失败 WARN 跳过（白名单语法外）；绝对锚单调比较，[回拨] 标记豁免
- 用例：ch1 初十 vs ch2 初七真阳性；回拨标记真阴性；无月继承
- 提交 `feat(gates): spec75 T3——时间锚单调门 + planning 三声明行扩展（无在途 artifacts 受影响：旧 memo 随 #79 quarantine 终点）`

### Task 4: 不变量 4 物象链 + 5 卡属性

**复杂度: infra · test_kind: tdd_red_green**

**Files:** Modify `cross_chapter.py`；Test `test_xc_prop_card.py`

- 物象：memo 经手声明行（`- 物象: 红纸包|萤→我`）+ 正文唯一真值——本章出现 registry 已知实体而 owner 无经手事件 → FAIL（修复者 settling）；实体初见登记
- 卡属性：性别代词（她/他）vs 卡、机构名 vs 卡（含 #74 前旧卡真阳性即「伤」）、住所 vs 卡当前住所字段（卡无字段跳过 WARN）
- 用例：红纸包链真阳性（fixture 章+构造经手流）；小满性别真阳性（真实卡 fixture）；真阴性
- 提交 `feat(gates): spec75 T4——物象 owner 链还原 + 卡属性一致`

### Task 5: 不变量 6 资产 + G6.4 timeline 退役

**复杂度: infra · test_kind: tdd_red_green + characterization（G6.4 退役面）**

**Files:** Modify `cross_chapter.py` + `src/shenbi/gates/g6_checks.py`（timeline 分支移除）+ 既有 G6.4 测试更新；Test `test_xc_assets.py`

- 资产：memo 余额声明行主源（本章声明 vs 前章声明±事件行——`- 事件: 收入|十二文|抄书`）；跳变 ≥10 文无事件 → FAIL；章末钩窗口（末场景）内「少一枚/消失」形态豁免
- G6.4 timeline 退役 + 其测试用例迁移/删除
- 提交 `feat(gates): spec75 T5——资产连续性双源门 + G6.4 timeline 退役`

### Task 6: 接线（scene-split 步 + manifest G4.xc + 修订双向扇出 + WARN 通路）

**复杂度: infra（协调者亲自）· test_kind: tdd_red_green**

**Files:** Modify `src/shenbi/pipeline/chapter_loop.py`（`_run_scene_split_step` 内逐章调 `g4_cross_chapter` + `record_gate_result(project_dir, "chapter_loop", n, "pipeline-scene-split", "G4.xc", result)` + WARN log）+ `_revalidate_revised_chapter`（双向扇出 N/N+1）；Test `tests/pipeline/test_xc_wiring.py`

- scene-split 步 G4.cd 终验后追加跨章检查；首章跳过；FAIL 进 issues 熔断链（消息携修复者）
- 修订重验：修订章 N 复跑 cross_chapter(N) 与 cross_chapter(N+1)（后继对照）
- 提交 `feat(pipeline): spec75 T6——scene-split 步跨章接线 + G4.xc manifest + 修订双向扇出`

### Task 7: registry 三表 + state-settling 契约 + seeding 脚本 + 契约连锁

**复杂度: infra（契约面）· test_kind: tdd_red_green + regression_guard**

**Files:**
- Create: `src/shenbi/pipeline/registry_seeding.py`（确定性脚本：characters/ → name_registry.md 初值；CLI `python -m shenbi.pipeline.registry_seeding <dir>`）
- Modify: `skills/shenbi-state-settling/SKILL.md`（updates 增三表——timeline/prop append_dedup、name_registry overwrite+透传）+ `docs/framework/truth-files.yaml`（三表条目 + extractor 尾窗）+ `src/shenbi/gates/g4/state_settling.py`（三表结构校验）
- Test: seeding 单测 + G4.ss 三表用例 + cross_chapter registry 交叉校验层（数据在场时核对/缺席 WARN）

- `just lint-contracts && just generate` 绿
- 提交 `feat(pipeline): spec75 T7——registry 三表 + settling 契约扩展 + seeding 脚本（无在途 artifacts 受影响）`

### Task 8: 五伤回归全量 + 真阴性 + WARN 态 + 验收收尾

**复杂度: infra · test_kind: regression_guard**

- `tests/unit/gates/g4/test_xc_regression.py`：五伤对 fixture 真阳性逐伤断言（POV/灯/初十/红纸包/小满）+ 干净相邻章真阴性（tmp_path 构造）+ registry 缺席 WARN 态 + 纯幂等（同输入双跑同输出）
- `just check` 完整跑；验收证据贴 progress.md
- 提交 `chore(spec75): T8 五伤回归 + 验收收尾`

---

## 验收覆盖表

| spec §4 | task | 命令 |
|---|---|---|
| 五伤真阳性 | T8 | pytest test_xc_regression（逐伤断言） |
| 真阴性零误报 | T8 | 同上（干净相邻章） |
| 幂等无副作用 + just check | T8 | 双跑同输出 + just check EXIT=0 |

## Self-Review

- 覆盖：六不变量 T2-T5/接线 T6/registry T7/回归 T8/fixture T1 ✓；G6.4 退役 T5；契约连锁 T7+T3
- 中文锚正则细节（初十→10、月份继承）T3 内钉；三信号正则 T2 内钉（ch4:88 形态用例护栏）
