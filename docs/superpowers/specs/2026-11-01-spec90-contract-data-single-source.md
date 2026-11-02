# Spec #90 · 契约数据面单源（contract-data-single-source）：一个权威集合 + 三处派生，零构建基础设施

**日期**：2026-11-01（**r2 重写 2026-11-02：原「codegen 方案」经复审否决**——SHORT_MAP 30 条 100% 机械可导、G4_CHECKER_KEYS 本身已是 frozenset 单源，引入生成器属过度施工；**r2.2 2026-11-02 全量对抗式审计修订**——roster 零依赖模块（避免 CLI 冷启动 +120ms）、T4 载体改 lint 侧配置（frontmatter 会进 system prompt，红线失真）、对账面 9 非 6）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟡 P2
**动机证据**：architecture-review-20261101 #6/#20/#24 卡；亲验：`SHORT_MAP`（gates/cli.py:23-59）恰 30 条且全部为 `shenbi-` 前缀剥离形态；`G4_CHECKER_KEYS`（g4/generic.py:368-401）为字符串 frozenset（注释「String-only so lint tooling (and g5) can import it without pulling the per-skill checker modules」）；`parse_volume_*` 式的手工同步面共 4 表

**触及的不变量维度**：无（契约/名册数据面）

---

## 0. 根因与方案选择

「哪些技能挂 G4 checker」smeared 在 4 个手工结构：`G4_CHECKER_KEYS`（generic.py，frozenset）/ `G4_CHECKER_SKILLS`（gates/shared.py）/ `SHORT_MAP`（gates/cli.py，dict）/ `build_checkers()`（generic.py，dict）。加一个 checker = 编辑 5-6 处；lint_registry_reconcile 以 **AST 解析框架自身源码**对账（读码不 import 码）——对账存在不等于编辑面缩小。

**方案对比（r2 裁决）**：

| 方案 | 编辑面 | 新增机制 | 裁决 |
|---|---|---|---|
| A. frontmatter `contract.g4_checker` + sync_contracts 生成 | 1（SKILL.md） | 生成器 + schema 位 + 33 文件回填 | **否决**：把「哪个函数存在」这件代码级事实搬进散文文件；33 处一次性回填 + 契约 schema 变更（AGENTS.md 契约升级纪律的破坏面） |
| B. 生成 Python/JSON 模块 | 1 | 构建步 + import 时读档 | **否决**：本仓 codegen 先例（deps.json/index.json）都是**数据面**；checker 名册是**代码面**，多一层生成反而引入自举/幂等问题 |
| **C. 一个权威集合 + 派生（采用）** | **2（checker 文件 + 权威集合一行）** | **零** | ✓ 纯 Python 派生，无构建、无新文件格式 |

**先例约束**：spec #9（spec 日期 2026-08-14；plan 2026-08-24）裁决「lint 对账优于 g4 消费 pydantic 契约模型」——本 spec 不动该裁决（不新增契约模型消费）；C 方案正是在既判框架内把「可机械推导的手工副本」删掉。

## 1. 任务分解

### T1 · 权威集合收敛（G4_CHECKER_KEYS 为单源）

**派生等价性已实跑验证（2026-11-02）**：`SHORT_MAP`（30）与 `{k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}`（30）**完全相等**；`set(G4_CHECKER_KEYS) == set(G4_CHECKER_SKILLS)` 亦为真。即 T1 无 override 例外，纯机械替换。

- **新增 `gates/g4/roster.py`（零依赖叶，r2.2 关键修正）**：`G4_CHECKER_KEYS` frozenset **迁到此文件**，generic/shared/cli 全从 roster import——实测本机 `import shenbi.gates.cli`≈1.8ms、冷 import `g4.generic`≈80-120ms（环境相关）；若按 r2 让 `gates/cli` 顶层 import generic，每次 `shenbi-validate` 子进程加约 0.1s（每章 5-6 次），直接回退 T1604 的懒加载优化；
- `gates/shared.G4_CHECKER_SKILLS` 改为 roster 的别名（或反向，plan 定；判据=形成单一定义点）；
- `gates/cli.SHORT_MAP` 改派生式 `{k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}`；**r2.2 删除「保留等值断言作为回归守卫」**——SHORT_MAP 就是派生结果，自断言恒真、不是守卫；真守卫=`build_checkers` 断言 + G0.15；
- `build_checkers()` 保留 dict（函数对象不可派生），末尾 assert 改为 `set(build_checkers()) == G4_CHECKER_KEYS`（当前已存在于 generic.py:492——r2.2 注：该条是 no-op，不计入编辑面收益）；
- `G4_CHECKER_KEYS` 注释里的手写计数「27 static + 3」改 `len()` 自述。

### T2 · lint 面对账收缩
lint_registry_reconcile **实为 10 个面**（9 个 R1 面——`_r1_skill_closure:305-321` 调 9 次 `_face_*`——加 R5 `_r5_glob_validity:510-533`），非 r2 列的 6 面——遗漏 `_face_master:186`/`_face_index_md:246`/`_face_deps_dead:297`/R5。因 T1 变恒真的面（SHORT_MAP ⊇ checkers / G4_CHECKER_SKILLS == keys）删除或降为「派生无漂移」断言；**保留**：using-shenbi 触发表、t2 种子文本、master/index/deps 面、R5（`G5_CHECKER_GLOBS` 严格包含——携带每技能真实 glob 知识，注释为何手工）。**r2.2 更正**：`_face_agents_counts:274-283` 的 regex 在 AGENTS.md **零命中**（无 `<n> skills` 数字断言）——当前恒真，不是「真散文面」守卫；要么给 AGENTS.md 真加计数，要么删面。

### T3 · decisions 三源之第三源（lint 自身减负）
- `lint_decisions_sources` 弃「crude YAML scan」（:23-50 行扫描器——新 write-semantics 键静默破扫）改走 `load_contract`（lint_contracts.py:17 先例：tools 可 import src）；
- `STEM_TO_SKILL`（:54-63，**8 条**手条目）改从 contracts 派生（writes 含 `-decisions.json` → 技能）；**r2.2 必须参数化归一**：naive `N→*` fnmatch 会把 `chapters/chapter-N-decisions.json` 同时匹配到 `chapter-N-revision-decisions.json`（二义），严格 `{N}/{N+1}→N` 归一后 8 条映射唯一且与手表一致；二义即 fail 的断言入测试；
- **value-set 对账**复制 status-vocab 模板（lint_status_strings 面 3 先例）：decisions-schema.md 的枚举清单（handling/severity 等）↔ `contracts/schemas/decisions.py` 的 Literal 值集相等——防「加 Handling 值文档静默过期」。
- **r2 裁剪**：原稿的「Per-Skill 表生成器」**删除**——名字列已有对账，值集对账补上后表生成的信息增量为零。

### T4 · 散文↔YAML 缝小刀（不做散文 codegen；r2.2 换载体）
- **载体改判（r2.2 关键）**：9 条中央 allowlist（:64-106）**迁 `tools/contract_prose_allowlist.yaml`**（lint 侧配置，按 skill 键控），**不放 SKILL.md frontmatter**——实测 `dispatch_helper` 的 system_prompt = SKILL.md 全文，`_strip_autogen_blocks` 只删 `<!-- AUTO-GENERATED -->`/AUTO-CHECK 块、**不删 frontmatter**，注解会原样进模型上下文（且计入 token 预算）——「prompt 行为零变化」红线被证伪；且 `load_contract` 返回固定 7 键 dict、`_validate` 静默丢弃未知键，lint 读不到 frontmatter 注解，还需扩 loader/schema（「零新机制」也不成立）。
- lint_contract_prose 掩码 level⑤（自认 "broadest mask"）收窄为 per-skill 声明族匹配；**r2.2 实测**：收窄后浮出 **42 条 R1、横跨 16 个 skill**（refs 含 pending_hooks/world-rules/characters）——不是「小刀」；拆 **T4a（allowlist 迁配置，零行为）** 与 **T4b（收窄+未声明读迁移清单）**，T4b 排束4 验收后；
- `skills/shenbi-writing-skills/SKILL.md` 补「机器契约」节（现 140 行零提 contract:/decisions/write-semantics/plan_format）+ 5 行 lint 面（元技能必须提及 `contract:` 与 `decisions`；「过不了 G0」的断言改为列具体 G0 子门编号，plan 期补证）。

## 2. 验收

1. **编辑面演练（r2.2 限定场景）**：**给已有技能加 checker**（新 checker 文件 + 权威集合一行）→ SHORT_MAP/G4_CHECKER_SKILLS/build_checkers 断言全自动通过，**其余手工编辑 = 0**（对比现状 5-6 处）；演练后回滚。**新增 checker 技能**不在本演练面——仍需技能目录/SKILL.md/deps.json/G5 globs/using-shenbi/`docs/skills/index.md`/`plugins/master.json` 六处（r2.2 明确，不夸大收益）；
2. `grep -rn "G4_CHECKER_SKILLS = \|SHORT_MAP = " src/shenbi/gates/` 各恰 1 定义点（派生式）；
3. lint_decisions_sources 无自有 frontmatter **解析逻辑**（AST 断言，非 `grep "crude"`——删注释即满足不算数）且 STEM_TO_SKILL 零手条目、二义即 fail；
4. 值集对账红测：临时给 pydantic 模型加一个 Handling 值 → lint 红（回滚）；
5. writing-skills lint 面对缺节红、现状绿；
6. `just check` exit 0。

## 3. 风险

- T1 若 SHORT_MAP 现值与派生式不等（存在非机械短名）→ 该条目不硬导，保留显式 override 并在 spec-deviations 记录（**先证伪再合并**）；
- T4 的 allowlist 迁移**不触碰任何 SKILL.md**（r2.2：载体改 `tools/contract_prose_allowlist.yaml`——frontmatter 会原样进 system prompt，原文「只加注解不改散文=prompt 零变化」被证伪）；T4b 收窄 level⑤ 浮出 42 条 R1，须先做未声明读迁移清单，**排束4 验收后窗口**。
