# Spec #90 · 契约数据面单源（contract-data-single-source）：一个权威集合 + 三处派生，零构建基础设施

**日期**：2026-11-01（**r2 重写 2026-11-02：原「codegen 方案」经复审否决**——SHORT_MAP 30 条 100% 机械可导、G4_CHECKER_KEYS 本身已是 frozenset 单源，引入生成器属过度施工）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟡 P2
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

**先例约束**：spec #9（2026-08-24）裁决「lint 对账优于 g4 消费 pydantic 契约模型」——本 spec 不动该裁决（不新增契约模型消费）；C 方案正是在既判框架内把「可机械推导的手工副本」删掉。

## 1. 任务分解

### T1 · 权威集合收敛（G4_CHECKER_KEYS 为单源）

**派生等价性已实跑验证（2026-11-02）**：`SHORT_MAP`（30）与 `{k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}`（30）**完全相等**；`set(G4_CHECKER_KEYS) == set(G4_CHECKER_SKILLS)` 亦为真。即 T1 无 override 例外，纯机械替换。

- `gates/shared.G4_CHECKER_SKILLS` 改为 `from shenbi.gates.g4.generic import G4_CHECKER_KEYS` 的别名（或反向，plan 定；判据=形成单一定义点）；
- `gates/cli.SHORT_MAP` 改派生式 `{k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}`，并保留**等值断言作为回归守卫**（防未来非机械短名混入而不自知）；
- `build_checkers()` 保留 dict（函数对象不可派生），末尾 assert 改为 `set(build_checkers()) == G4_CHECKER_KEYS`；
- `G4_CHECKER_KEYS` 注释里的手写计数「27 static + 3」改 `len()` 自述。

### T2 · lint 面对账收缩
lint_registry_reconcile 中因 T1 变恒真的面（SHORT_MAP ⊇ checkers / G4_CHECKER_SKILLS == keys）删除或降为「派生无漂移」断言；**保留**：using-shenbi 触发表、t2 种子文本、AGENTS.md 计数（真散文面，codegen/派生不可能）；`G5_CHECKER_GLOBS` **保留手工**（携带每技能真实 glob 知识）并注释为何手工。

### T3 · decisions 三源之第三源（lint 自身减负）
- `lint_decisions_sources` 弃「crude YAML scan」（:23-50 行扫描器——新 write-semantics 键静默破扫）改走 `load_contract`（lint_contracts.py:17 先例：tools 可 import src）；
- `STEM_TO_SKILL`（:54-63 第四份手工名册）改从 contracts 派生（writes 含 `-decisions.json` → 技能）；
- **value-set 对账**复制 status-vocab 模板（lint_status_strings 面 3 先例）：decisions-schema.md 的枚举清单（handling/severity 等）↔ `contracts/schemas/decisions.py` 的 Literal 值集相等——防「加 Handling 值文档静默过期」。
- **r2 裁剪**：原稿的「Per-Skill 表生成器」**删除**——名字列已有对账，值集对账补上后表生成的信息增量为零。

### T4 · 散文↔YAML 缝小刀（不做散文 codegen）
- lint_contract_prose 掩码 level⑤（自认 "broadest mask"）收窄为 per-skill 声明族匹配；9 条中央 allowlist（:64-106）迁移进各 SKILL.md frontmatter 注解（豁免随技能走）；
- `skills/shenbi-writing-skills/SKILL.md` 补「机器契约」节（现 140 行零提 contract:/decisions/write-semantics/plan_format——按其教学写出的 SKILL.md 过不了 G0）+ 5 行 lint 面（元技能必须提及 `contract:` 与 `decisions`）。

## 2. 验收

1. **编辑面演练**：临时加假 checker（新文件 + 权威集合一行）→ SHORT_MAP/G4_CHECKER_SKILLS/build_checkers 断言全自动通过，**其余手工编辑 = 0**（对比现状 5-6 处）；演练后回滚；
2. `grep -rn "G4_CHECKER_SKILLS = \|SHORT_MAP = " src/shenbi/gates/` 各恰 1 定义点（派生式）；
3. lint_decisions_sources 无自有 frontmatter 解析（grep "crude" 零）且 STEM_TO_SKILL 零手条目；
4. 值集对账红测：临时给 pydantic 模型加一个 Handling 值 → lint 红（回滚）；
5. writing-skills lint 面对缺节红、现状绿；
6. `just check` exit 0。

## 3. 风险

- T1 若 SHORT_MAP 现值与派生式不等（存在非机械短名）→ 该条目不硬导，保留显式 override 并在 spec-deviations 记录（**先证伪再合并**）；
- T4 的 allowlist 迁移触碰 9 个 SKILL.md frontmatter：**只加注解不改散文指令**（prompt 行为零变化——卷二开卷前红线）。
