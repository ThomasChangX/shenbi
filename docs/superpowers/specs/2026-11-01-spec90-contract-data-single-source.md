# Spec #90 · 契约数据面单源（contract-data-single-source）：一个权威集合 + 三处派生，零构建基础设施

**日期**：2026-11-01（**r2 重写 2026-11-02：原「codegen 方案」经复审否决**——SHORT_MAP 30 条 100% 机械可导、G4_CHECKER_KEYS 本身已是 frozenset 单源，引入生成器属过度施工；**r2.2 2026-11-02 全量对抗式审计修订**——roster 零依赖模块（避免 CLI 冷启动 +120ms）、T4 载体改 lint 侧配置（frontmatter 会进 system prompt，红线失真）、对账面 9 非 6；**r2.3 2026-11-14 价值门驳斥修订**——T1 载体改判：`gates/g4/__init__.py:7-14` eager re-export generic 六符号，`gates/g4/roster.py`「零依赖叶」失真（import 包 init 即拉 generic→shared 全链；shared 别名 import 反向成环且逆转 #89 出鞘）→ 改 **shared 单源 + generic re-export**（零新文件）；编辑面数字 2→3/4 修正；补 `_checker_keys` 改指向缺口；T4a 外置配置对齐 JSON 先例+fail-loud）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.3） ｜ **优先级**：🟡 P2
**动机证据**：architecture-review-20261101 #6/#20/#24 卡；亲验：`SHORT_MAP`（gates/cli.py:23-59）恰 30 条且全部为 `shenbi-` 前缀剥离形态；`G4_CHECKER_KEYS`（g4/generic.py:368-401）为字符串 frozenset（注释「String-only so lint tooling (and g5) can import it without pulling the per-skill checker modules」）；`parse_volume_*` 式的手工同步面共 4 表

**触及的不变量维度**：无（契约/名册数据面）

---

## 0. 根因与方案选择

「哪些技能挂 G4 checker」smeared 在 4 个手工结构：`G4_CHECKER_KEYS`（generic.py，frozenset）/ `G4_CHECKER_SKILLS`（gates/shared.py）/ `SHORT_MAP`（gates/cli.py，dict）/ `build_checkers()`（generic.py，dict）——**#89（2026-11-14）落地后实为 5 处涂布**（+`GENERIC_ONLY_ROSTER` shared.py:814，问题被强化而非缓解）。加一个 checker = 编辑 5-6 处；lint_registry_reconcile 以 **AST 解析框架自身源码**对账（读码不 import 码）——对账存在不等于编辑面缩小。

**方案对比（r2 裁决；r2.3 修 C 的编辑面数字与载体）**：

| 方案 | 编辑面 | 新增机制 | 裁决 |
|---|---|---|---|
| A. frontmatter `contract.g4_checker` + sync_contracts 生成 | 1（SKILL.md） | 生成器 + schema 位 + 33 文件回填 | **否决**：把「哪个函数存在」这件代码级事实搬进散文文件；33 处一次性回填 + 契约 schema 变更（AGENTS.md 契约升级纪律的破坏面） |
| B. 生成 Python/JSON 模块 | 1 | 构建步 + import 时读档 | **否决**：本仓 codegen 先例（deps.json/index.json）都是**数据面**；checker 名册是**代码面**，多一层生成反而引入自举/幂等问题 |
| **C. 一个权威集合 + 派生（采用）** | **3（新 checker 文件 + 权威集合一行 + build_checkers wiring 行；若该技能现居 GENERIC_ONLY_ROSTER 则 4——再删其 fallback 行）** | **零** | ✓ 纯 Python 派生，无构建、无新文件格式。（r2.3 修正：原「2」漏计 build_checkers wiring——函数对象不可派生，不写 wiring 行则 `set(checkers)==G4_CHECKER_KEYS` assert 当场红；「其余手工编辑=0」限定为**名册面**——SHORT_MAP/G4_CHECKER_SKILLS 派生化后自动通过） |

**先例约束**：spec #9（spec 日期 2026-08-14；plan 2026-08-24）裁决「lint 对账优于 g4 消费 pydantic 契约模型」——本 spec 不动该裁决（不新增契约模型消费）；C 方案正是在既判框架内把「可机械推导的手工副本」删掉。

## 1. 任务分解

### T1 · 权威集合收敛（G4_CHECKER_KEYS 为单源）

**派生等价性已实跑验证（2026-11-02；r2.3 于 #89 落地后复验仍真）**：`SHORT_MAP`（30）与 `{k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}`（30）**完全相等**；`set(G4_CHECKER_KEYS) == set(G4_CHECKER_SKILLS)` 亦为真（#89 未动三名册任一定义，只新增 GENERIC_ONLY_ROSTER）。即 T1 无 override 例外，纯机械替换。

- **r2.3 载体改判（原 r2.2「gates/g4/roster.py 零依赖叶」被证伪）**：`gates/g4/__init__.py:7-14` **eager re-export generic 六符号**（gate_G4 族）——`import shenbi.gates.g4.roster` 必先执行包 init → generic → shared+structlog 全链，「零依赖叶」失真：①cli 顶层 import roster → 冷启动回退全链成本（正是本 task 要避免的）；②shared:776 处别名 import roster → shared（半初始化）→ g4 包 init → generic → `from shenbi.gates.shared import chapter_no/fail/passed/...`——六助手（:190/:199/:211/:224/:604/:651）今日恰都定义在 :776 **之前**才能活，顺序脆弱，且逆转 #89「shared 出鞘/no g4 import」性质；
- **采用方案（r2.3 定判，不再是「plan 定」）**：**`gates/shared.py` 为权威集合宿主**——`G4_CHECKER_SKILLS` 的 frozenset 字面量原地升格为单源（与 `GENERIC_ONLY_ROSTER` 同文件成干净二分），`generic.py` 改 `from shenbi.gates.shared import G4_CHECKER_KEYS`（generic 本就 import shared，零新边零新文件），`g0.py:112` 的 module-level `from shenbi.gates.shared import G4_CHECKER_SKILLS` 零改动，G4_CHECKER_KEYS 注释「String-only so lint tooling (and g5) can import it without pulling the per-skill checker modules」继续成立（shared 比 generic 更轻）。generic.py 旧 frozenset **删除**（防遮蔽副本）；
- **SHORT_MAP 派生移入 cli 的 G4 懒加载分支内**（唯一消费点 cli.py:169 本就在该分支，分支内已付 generic 链 import 成本，边际为零）——cli 顶层零新 import，冷启动不回退；
- `build_checkers()` 保留 dict（函数对象不可派生），末尾 assert 保留 `set(build_checkers()) == G4_CHECKER_KEYS`（generic.py:496-497 现存形态）；
- `G4_CHECKER_KEYS` 注释里的手写计数「27 static + 3」改 `len()` 自述；
- 备选（plan 期若发现 shared 宿主有未知破裂面才启用）：`gates/roster.py` 顶层叶——`gates/__init__.py` 仅 docstring（6 行），#85 `src/shenbi/truth_format.py`「only acyclic landing point」同模式。

### T2 · lint 面对账收缩
lint_registry_reconcile **实为 10 个面**（9 个 R1 面——`_r1_skill_closure:305-321` 调 9 次 `_face_*`——加 R5 `_r5_glob_validity:510-533`），非 r2 列的 6 面——遗漏 `_face_master:186`/`_face_index_md:246`/`_face_deps_dead:297`/R5。因 T1 变恒真的面（SHORT_MAP ⊇ checkers / G4_CHECKER_SKILLS == keys）删除或降为「派生无漂移」断言；**保留**：using-shenbi 触发表、t2 种子文本、master/index/deps 面、R5（`G5_CHECKER_GLOBS` 严格包含——携带每技能真实 glob 知识，注释为何手工）。**r2.2 更正**：`_face_agents_counts:274-283` 的 regex 在 AGENTS.md **零命中**（无 `<n> skills` 数字断言）——当前恒真，不是「真散文面」守卫；要么给 AGENTS.md 真加计数，要么删面。**r2.3 必改**：`_checker_keys`（:136-141，AST 解析 generic.py 的 G4_CHECKER_KEYS）被 :310（_r1_skill_closure）与 :515（R5）**共用**——T1 把字面量迁走后若不改指向，`_literal_str_set` 返回空集 → R5/`_face_g5_globs` **静默恒真**（空集∩任何=空）——必须同批改解析 shared.py（别名/re-export 形态 AST 不可读，改读权威字面量所在文件）。另：`_face_short_map` 的 `_short_map_keys:108` 只认 `ast.Dict`——派生式（DictComp）返回 None 仅追加 WARN 不红——T1 落地与 T2 删/改面**必须同批**，否则该面静默失去保护。

### T3 · decisions 三源之第三源（lint 自身减负）
- `lint_decisions_sources` 弃「crude YAML scan」（:23-50 行扫描器——新 write-semantics 键静默破扫）改走 `load_contract`（lint_contracts.py:17 先例：tools 可 import src）；
- `STEM_TO_SKILL`（:54-63，**8 条**手条目）改从 contracts 派生（writes 含 `-decisions.json` → 技能）；**r2.2 必须参数化归一**：naive `N→*` fnmatch 会把 `chapters/chapter-N-decisions.json` 同时匹配到 `chapter-N-revision-decisions.json`（二义），严格 `{N}/{N+1}→N` 归一后 8 条映射唯一且与手表一致；二义即 fail 的断言入测试；
- **value-set 对账**复制 status-vocab 模板（lint_status_strings 面 3 先例）：decisions-schema.md 的枚举清单（handling/severity 等）↔ `contracts/schemas/decisions.py` 的 Literal 值集相等——防「加 Handling 值文档静默过期」。
- **r2 裁剪**：原稿的「Per-Skill 表生成器」**删除**——名字列已有对账，值集对账补上后表生成的信息增量为零。

### T4 · 散文↔YAML 缝小刀（不做散文 codegen；r2.2 换载体）
- **载体改判（r2.2 关键；r2.3 格式对齐）**：9 条中央 allowlist（:64-106）**迁 `tools/contract_prose_allowlist.json`**（lint 侧配置，按 skill 键控；**JSON 非 yaml**——tools/ 外置配置先例 `artifact-lint-exemptions.json`/`module-coverage-floors.json` 均 JSON、零 yaml 先例），**不放 SKILL.md frontmatter**——实测 `dispatch_helper` 的 system_prompt = SKILL.md 全文，`_strip_autogen_blocks`（dispatch_helper.py:237-247）只删 `<!-- AUTO-GENERATED -->`/AUTO-CHECK 块、**不删 frontmatter**，注解会原样进模型上下文（且计入 token 预算）——「prompt 行为零变化」红线被证伪；且 `load_contract` 返回固定 7 键 dict、`_validate` 静默丢弃未知键，lint 读不到 frontmatter 注解，还需扩 loader/schema（「零新机制」也不成立）。**r2.3 设计要求：配置文件缺失/不可解析必须 fail-loud（exit 1）**——外部文件会 missing（in-code tuple 不会），静默回落空 allowlist = 42 条类 R1 全量浮出的反向事故；
- lint_contract_prose 掩码 level⑤（自认 "broadest mask"）收窄为 per-skill 声明族匹配；**r2.2 实测**：收窄后浮出 **42 条 R1、横跨 16 个 skill**（refs 含 pending_hooks/world-rules/characters）——不是「小刀」；拆 **T4a（allowlist 迁配置，零行为）** 与 **T4b（收窄+未声明读迁移清单）**，T4b 排束4 验收后；
- `skills/shenbi-writing-skills/SKILL.md` 补「机器契约」节（现 140 行零提 contract:/decisions/write-semantics/plan_format）+ 5 行 lint 面（元技能必须提及 `contract:` 与 `decisions`；「过不了 G0」的断言改为列具体 G0 子门编号，plan 期补证）。

## 2. 验收

1. **编辑面演练（r2.2 限定场景；r2.3 数字修正）**：**给已有技能加 checker**（新 checker 文件 + 权威集合一行 + build_checkers wiring 行 = **3 处**；若该技能现居 GENERIC_ONLY_ROSTER 则再删其 fallback 行 = 4 处）→ SHORT_MAP/G4_CHECKER_SKILLS **名册面自动通过（其余名册手工编辑 = 0，对比现状 5-6 处）**；演练后回滚。**新增 checker 技能**不在本演练面——仍需技能目录/SKILL.md/deps.json/G5 globs/using-shenbi/`docs/skills/index.md`/`plugins/master.json` 六处（r2.2 明确，不夸大收益）；
2. `grep -rn "G4_CHECKER_SKILLS = \|SHORT_MAP = \|G4_CHECKER_KEYS = " src/shenbi/` 各恰 1 定义点（r2.3 补 G4_CHECKER_KEYS 面——防迁移后 generic 留遮蔽副本）；`grep -rn "G4_CHECKER_KEYS" src/shenbi/gates/g4/generic.py` 仅 re-import + 注释，零本地 frozenset 字面量；
3. lint_decisions_sources 无自有 frontmatter **解析逻辑**（AST 断言，非 `grep "crude"`——删注释即满足不算数）且 STEM_TO_SKILL 零手条目、二义即 fail；
4. 值集对账红测：临时给 pydantic 模型加一个 Handling 值 → lint 红（回滚）；
5. writing-skills lint 面对缺节红、现状绿（r2.3 归宿建议：挂 `lint_repo_consistency.py` 既有技能文件面族，不新建 lint 文件）；
6. `just check` exit 0。

## 3. 风险

- T1 若 SHORT_MAP 现值与派生式不等（存在非机械短名）→ 该条目不硬导，保留显式 override 并在 spec-deviations 记录（**先证伪再合并**；r2.3 runtime 复验 30/30 全等，预期不触发）；
- T1 载体（r2.3）：shared 宿主方案下 generic re-export 不得引入 `gates/g4/` 包级新 import 环——plan 期以 `python -c "import shenbi.gates.cli"` 冷启动不回退 + `import shenbi.gates.g0` 零 g4 拉入为验收锚；备选 gates/roster.py 顶层叶仅在发现未知破裂面时启用；
- T2 与 T1 **必须同批**（`_short_map_keys` 只认 ast.Dict——派生式落地面为 DictComp 时旧 lint 面静默降级 WARN）；`_checker_keys` 改指向 shared.py 同批，否则 R5/_face_g5_globs 静默恒真；
- T4 的 allowlist 迁移**不触碰任何 SKILL.md**（r2.2：载体改外置配置——frontmatter 会原样进 system prompt，原文「只加注解不改散文=prompt 零变化」被证伪；r2.3 定 JSON+fail-loud）；T4b 收窄 level⑤ 浮出 42 条 R1，须先做未声明读迁移清单，**排束4 验收后窗口**。
