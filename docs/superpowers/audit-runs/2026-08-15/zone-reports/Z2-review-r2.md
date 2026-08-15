# Z2 分区独立复核报告 r2（2026-08-15 轮）

- 复核 agent: Z2 fresh-context 独立复核轮 2（与初审、r1 均无关）
- 复核方式: 38 文件全量重读 + 本轮专项角度（**计数三方对账 + 采样截断检查**）+ `uv run python -c` 行为验证 + git 考古
- 编号段: F231–F236（初审 F201–F223、r1 F224–F230 已用）
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件；未运行 pytest；未执行 shenbi-dispatch/pipeline 任何子命令；未 git add/commit

## 总结论

初审 23 条 + r1 7 条逐条对照代码与实跑复核：**无全假条目，无需推翻**。本轮角度命中两个此前漏报的实质问题：**genre-config 契约模型 9 条规则只实现了 7 条**（缺 approval 必填与顶层字段数=8，G4 洞，P1）与 **deps.json 技能账目三方漂移**（磁盘 74 vs 账目 69，5 个生产 chapter_loop 技能漏账，且无任何对账防线，P2）。截断角度另检出 fields 解析器重复标题静默覆盖、extract_chapter 首匹配误路由两个潜伏缺陷。

---

## 一、漏报（新 finding）

### F231 | deps.json 技能账目三方漂移：磁盘 74 vs 账目 69 vs AGENTS.md 69，5 个生产技能漏账且无对账防线 | coverage-gap | P2
- 证据:
  - 磁盘: `skills/` 目录 74 个含 SKILL.md（`ls -d skills/*/ | wc -l` = 74）；`known_skill_names()`（src/shenbi/contracts/registry.py:66-75）实测返回 74；
  - deps.json 账目: `t2-phases[].prerequisites` 去重 62 + `_out_of_pipeline` 三组 7 = **69**（重合 0）；
  - AGENTS.md "67 functional + 2 meta = 69 total"、contracts/ownership.py:7 "完整 69 技能 OWNERSHIP 迁移"——两处计数声明同为本轮磁盘现状的上界漂移；
  - **5 个漏账技能**: `shenbi-foreshadowing-lifecycle`、`shenbi-review-group-{factual,character,craft,plan}`——既不在任何 t2/t3 prerequisites 也不在 `_out_of_pipeline`。git 考古: 5 个目录均由 dd1fc62（2026-07-20，PR #19，即 r1 F224 的同一提交）以 MERGE-1/MERGE-2 方式引入，deps.json 与 AGENTS.md 计数未同步；
  - **漏账技能是生产路径**：src/shenbi/pipeline/chapter_loop.py:187（foreshadowing-lifecycle 为 CHAPTER_STEPS 步骤）与 :205-226（4 个 review-group 为步骤 9-12 审计波），并非孤儿；
  - **无对账防线**: G0.15（gates/g0.py:609-626）只做单向 `G4_CHECKER_SKILLS ⊆ known_skill_names`；tests/unit/contracts/schemas/test_deps.py 只测 shape（69/79-86 行），全仓无任何断言"磁盘技能 ⊆ deps.json 账目"的测试或门；`phase_of`（contracts/schemas/deps.py:67-78）对漏账技能与不存在技能同样返回 None，无法区分；
  - deps.json 是生产消费的权威名册: phase_runner.py:246-249/320 以 prerequisites 为逐技能 G4 marker 完成性清单——漏账技能若未来并入某 T2 阶段而名单未更新，其完成性检查会被静默跳过。
- 验证（实际运行）:
  ```
  $ uv run python -c "…known_skill_names() len; deps.json t2 去重 ∪ _out_of_pipeline"
  known_skill_names (disk scan): 74
  t2 members: 62 oop: 7 union: 69 (overlap: 0)
  unaccounted disk skills: ['shenbi-foreshadowing-lifecycle', 'shenbi-review-group-character',
                            'shenbi-review-group-craft', 'shenbi-review-group-factual', 'shenbi-review-group-plan']
  $ git log --oneline --follow -- skills/shenbi-review-group-plan/SKILL.md
  dd1fc62 fix: P0 blocking defects — dead paths, stubs, misleading CLI (4 fixes + 1 cleanup) (#19)
  ```
- 根因: `_out_of_pipeline._note` 自称穷尽账目（"These skills pass T1 but are not required by any T2 phase"），但无机制强制其与磁盘对账；引入技能的提交不触达 deps.json。
- 建议方向: 在 G0.15 扩展或新增一条双向对账（`known_skill_names() == t2 成员 ∪ t3 引用 ∪ out_of_pipeline 全组`），并把 AGENTS.md/ownership.py 的 69 更新为派生值或删除硬计数；5 个漏账技能补入 `_out_of_pipeline` 或对应 phase。
- 定级依据: 数据/文档漂移 + 防御缺失 = P2（无现行运行时破坏：漏账技能属 pipeline 路径，phase_runner 不派发它们）。

### F232 | genre-config 契约模型"9 条可自动检查规则"只实现 7 条：approval 必填与顶层字段数=8 完全未编码，G4 放行无审批配置 | error | P1
- 证据:
  - 权威表: skills/shenbi-genre-config/SKILL.md:288-301 "可自动检查的计数规则" 共 **9 行**——①顶层字段数=8 ②approval 字段存在（必填）③approval.decision ∈ {approved, rejected} ④禁用词数≤50 ⑤禁用词替换全覆盖 ⑥慎用词替换全覆盖 ⑦章节类型数 6-10 ⑧审计维度数 5-10 ⑨禁用维度理由；字段表另注明 approval "**REQUIRED**…缺失即不合格"；
  - 代码: contracts/skills/genre_config.py 仅 7 个 validator（:39-103），对应规则 ③④⑤⑥⑦⑧⑨；**规则 ①② 无任何实现**——docstring 第 3 行却声称 "Encodes the 9 checkable rules"；
  - 生产接线: gates/g4/genre_config.py:36 只调 `GenreConfig.model_validate(data)`，无模型外补充检查；`_approval_decision_valid`（genre_config.py:41-42）对空 decision `if decision and …` 直接放行；`extra="ignore"` + 全字段 default_factory 使任意键子集可构造。
- 验证（实际运行）:
  ```
  $ uv run python -c "…GenreConfig.model_validate(…)"
  missing approval + only 2 top-level keys -> PASSES (rules 1,2 not enforced)
  extra 9th top-level key (incl unknown tropeInventory) -> PASSES (rule 1 not enforced)
  approval={} (no decision) -> PASSES (rule 2 not enforced)
  ```
- 根因: 模型按"字段存在才检查"的宽松风格编写，两条"必须存在"型规则被跳过；docstring 计数声明（9）与实现（7）漂移正是本轮计数对账角度的命中点。与 F202（规则⑨空 customRules 绕过）同族但独立成洞——F202 修 `if disabled and self.custom_rules:` 不影响本条。
- 影响: 未审批（无 approval）或结构漂移（顶层键数≠8、未知键混入）的 genre-config.json 通过 G4 结构校验——审批门禁（"缺失即不合格"）在唯一自动检查点上不存在。
- 建议方向: 补两个 validator（顶层字段数恒等校验需先把 `extra` 改 forbid 或显式数键；approval 必填 + decision 空值 FAIL）；同步把 docstring "9 rules" 与实现数目对齐；补测试覆盖"缺 approval/键数≠8"负路径。
- 定级依据: 与 F202 同判例（G4 校验洞、正常路径功能错误）= P1。

### F233 | fields 解析器对重复 H2 标题静默覆盖：过滤产物只保留最后一个同名节，无 WARN | error | P2（潜伏，被 F224 掩盖）
- 证据: src/shenbi/contracts/fields.py:44-51——`sections[current_heading] = …` 字典赋值，同标题后节覆盖前节；:58-60 匹配成功即 `matched=True`，被覆盖内容无声丢失。
- 验证（实际运行）:
  ```
  $ uv run python -c "…extract_h2_sections(md_with_duplicate_ headings); filter_to_fields(md, ['主角状态'], 'truth/x.md')"
  sections keys: ['主角状态', '其他']
  kept body for duplicate: 'second copy OVERWRITES first'
  matched: True | first copy present: False
  ```
- 现实触达: 全仓扫描 truth/*.md 重复 H2 = 0；novel-output/xinghuo-ranqiong/snapshots/ 有 12 个含重复 H2 的真实产出文件（如 chapter-033 快照 "第33章更新"×3）——说明该格式在真实输出中自然出现，truth 文件一旦经同类汇总生成即触发；当前 Layer B 死线（F224）使生产影响为零。
- 建议方向: 重名标题改为列表拼接（`sections.setdefault(h, []).append(body)`）或检测到重复时 log.warning；与 F201（部分匹配丢字段）同文件一并修。

### F234 | extract_chapter 首匹配正则：prompt 提及多个章号时取最先出现者，路由错章 | error | P2（潜伏）
- 证据: src/shenbi/contracts/paths.py:155-157——`re.search(r"\bchapter\s+(\d+)\b", text, IGNORECASE)` 取全文第一个匹配；executor.py:174-175 与 :261-262 在无载体行时以它决定 G1 读入/G2 校验的章节文件路由。
- 验证（实际运行）:
  ```
  $ uv run python -c "…extract_chapter('Review the audit of chapter 24 first, then draft chapter 25 per plan')"
  extract_chapter -> 24      （目标是 25）
  ```
- 现实触达: kwarg > 载体行 > 正则的三级优先里它是最末兜底，pipeline API 路由带 [path-context] 不触达；CLI 人工 prompt（tests/round-exec.sh 不直传 prompt）中"先看 24 章审计再写 25 章"类表述即错读。与 F223（首匹配正则污染）同族。
- 建议方向: 取最后一个匹配（目标章通常在指令动词侧）或要求匹配 "draft|write|第 N 章" 类目标动词邻近；至少在多匹配时 log.warning。

### F235 | g4_genre_config 诊断截断：ValidationError 只报告前 5 条（errors[:5]），其余静默丢弃 | error | M（跨区证据）
- 证据: gates/g4/genre_config.py:40 `for err in errors[:5]`——超出 5 条的违规不进 mf，FAIL 判定不受影响但诊断信息丢失（10 个审计维度全坏时只见 5 条）。
- 验证: 读代码；该文件属 gates/ 区（Z2 外），因本轮截断角度顺带检出，仅记录并归并入 F232 修复工单（补 approval/键数校验后错误数会显著增多，截断影响放大）。
- 建议方向: 全量报告或 `f"…(+{len(errors)-5} more)"` 汇总行。

### F236 | registry.py docstring 指向已删除的 src/shenbi/contract.py（"未迁移返回 None（contract.py 仍负责）"） | doc-drift | M
- 证据: src/shenbi/contracts/registry.py:62；`ls src/shenbi/contract.py` → No such file or directory；现行加载器是 contracts/legacy.py（contracts/__init__.py:47-56 的 re-export 注释正确，唯 registry.py 此句未同步）。
- 验证: `grep -n "contract.py" src/shenbi/contracts/registry.py` → 62 行命中。
- 建议方向: 改为 "未迁移返回 None（legacy.load_contract 负责）"。

---

## 二、误报（初审 + r1 复核）

**无新增误报。** 本轮独立实跑/重读复核的条目全部成立：
- F203（codex 嵌套 JSON 误取内层）——本轮实跑复现 `extracted: {"d1": 5, "d2": 4}`；
- F205（derive_file_type）——本轮实跑 `shenbi-chapter-drafting → decisions`、`shenbi-context-composing → decisions`；
- F215（load_registry 无缓存）——本轮实测 20×load_contract = 174.5 ms（≈8.7 ms/次），与初审量级一致；
- F224（Layer B 死线）——本轮重读 dispatch_helper.py:581-605，`reads` 经 legacy._validate 归一化为 list[str] 后 `isinstance(read_path_entry, dict)` 恒假，`if fields:` 不可达，确认；
- F225/F226（write_semantics.key / no_op_behavior 零消费）——本轮 grep 复验：`["key"]|get("key")` 全仓零命中；`no_op_behavior` 仅 docstring 命中；`skip_paths` 形参无调用方传值；
- F202/F207/F208/F212/F213/F214/F223/F230——代码重读与 r1 实跑结论一致（F213 本轮再核对 pacing_design.py:55 `[15,35]` vs 文件 docstring:7 `[20,30]` vs SKILL.md:176/187，成立）。

**对初审 F210 汇总的一处补充勘误（r1 已指出"fields 已接线"不实）之外，本轮再确认一点**：初审 registry.py 节称 "REGISTRY 的唯一生产消费是 tools/generate_autocheck_docs.py"（F210 证据之一）成立，且 REGISTRY 现为 10 个模型条目（本轮实测），与磁盘 74 技能的覆盖比进一步佐证 F210 umbrella 的"假象覆盖"论断。

---

## 三、覆盖空洞

1. **deps.json 账目无对账防线（F231 直接成因）**: G0.15 只单向查 G4 checker 漂移；无任何门/测试断言磁盘技能集 == deps.json 账目集。修复 F231 时应补 G0.15b 或 property 测试（`known_skill_names() == accounted`）。
2. **genre_config 规则覆盖矩阵未锁（F232/F202 共同成因）**: 测试只触 7 条已实现规则的正路径，"9 条规则 × 实现/测试"矩阵从未对账——建议加一条参数化测试逐规则断言存在负路径用例。
3. **fields 解析器两个未测形状**: 重复 H2 标题（F233）与 JSON 部分匹配（F201 的 json 侧同胞：fields.py:76-79 同样只在零匹配时回退）均无测试——与 r1 空洞 2 同层加深。
4. **extract_chapter 多章号 prompt 无测试**（F234）: test_path_context.py 13 tests 全部单章号。
5. **dispatcher 路径无 prompt 体积上限**: Z2 两文件（executor/codex）对 prompt 长度无任何 cap/截断策略；F224 使全量 truth 文件注入后该缺失成为不可见的 token 风险面（Budget 模型仅是 decisions.json 的输出侧自报，`estimate ≤ limit` 无交叉校验，schema 文档亦未要求——记录为设计空洞而非 bug）。
6. r1 标注的 must-test 清单全部维持（dispatcher/cli.py 整模块、SHENBI_G1_SKIP_READS/dispatch_exception 路径、legacy 归一化守卫、decisions rationale 长度、registry version!=1）。

---

## 四、严重度异议（无权改定级，仅提异议）

- **支持 r1 的 F201 P1→P2 强异议**: 本轮再次确认 filter_to_fields 生产调用不可达（F224），escape-hatch 部分匹配语义当前触发面=0。
- **F202 P1 维持，且 F232 应与之同级 P1**: 两条是同一权威规则表的两个不同未实现面，同判例同级别；若 F202 定 P1 而 F232 降级会造成同表规则执行不一致的错觉。
- **F230 P2 无异议，补充**: 本轮重读确认 `_no_three_consecutive_same` 与 g4 no_beat_data 分支不可达链条与 r1 描述一致。
- 其余条目（F203-F209/F211-F223/F224-F229）定级与决策表逐条对照无异议。

---

## 五、本轮专项角度发现摘要

### (a) 计数三方对账
- **技能名册三方**: 磁盘 74 / deps.json 账目 69 / AGENTS.md+ownership.py 声明 69 → F231（5 技能漏账，全部 dd1fc62 引入且被 chapter_loop 生产消费）。
- **规则计数对账**: genre_config docstring 9 vs validator 7 vs SKILL.md 表 9 → F232；g0.py:546 注释 "20 skills" vs G4_CHECKER_SKILLS 实际 22（gates/ 区，顺带记录不立案）。
- **registry 计数**: truth-files.yaml concepts 70 == load_registry 70 == bootstrap_registry 70（三源一致，property 测试在跑）；但该测试 docstring "实测 54==54==54" 是陈旧快照值（tests/property/contracts/test_registry_consistency.py:24，归入 F231 证据链）。RegistryKind 16 值全部在用（实测 distinct kinds=16），无漂移。
- **G4 checker 双向**: deps.json g4_checker(4) ⊆ G4_CHECKER_SKILLS(22)，无漂移。
- **缓存计数**: executor 的 `_truth_files_cache`/`_decisions_files_cache`（executor.py:34-61）为进程级一次性缓存、无失效需求（CLI 单发语义）、无命中计数缺口；load_registry 无缓存即 F215（本轮复测 8.7 ms/次），无新发现。

### (b) 解析器截断/上限逻辑完整性
- 有上限且已执行: rationale ≤100 字符、禁用词 ≤50、chapterTypes 6-10、auditDimensions 5-10、scene types 6-12、KR 3-5、codex timeout 600s。
- 截断类缺陷: 嵌套 JSON 首个扁平对象误取（F203，初审）、首匹配正则污染（F223，初审）+ 章号首匹配（F234，新）、重复 H2 覆盖（F233，新）、g4 诊断 errors[:5]（F235，新）、NNN 无界替换（F209，初审 M）。
- 验证为不可达/可接受: `split("---", 2)` frontmatter 截断——本轮全量扫描 74 个 SKILL.md，唯一"丢 contract 块"的 2 个（using-shenbi、shenbi-writing-skills）本就无 contract 块（meta 技能），维持初审"不立案"结论；`raw_text[:500]` 仅日志预览；`parse_path_context` 取首行是文档化的防注入设计。
- JSON 侧 escape-hatch 与 md 侧同病（零匹配才回退，fields.py:76-79）——F201 的 json 胞枝，随 F201 一并修。

## 汇总

| 类别 | 数量 | 条目 |
|---|---|---|
| 漏报 | 6 | F231(P2)、F232(P1)、F233(P2)、F234(P2)、F235(M)、F236(M) |
| 误报 | 0 | （F210 汇总的"fields 已接线"子句由 r1 勘误，本轮维持该勘误） |
| 覆盖空洞 | 6 项 | 见第三节 |
| 严重度异议 | 2 | 支持 r1 F201→P2；F232 与 F202 同级 P1（判例一致性） |

### 收敛判定

- 三轮累计: 初审 23（P1×3）→ r1 +7（P1×1）→ r2 +6（P1×1）。**未完全收敛但收敛中**: 本轮 P1（F232）不在 r1 的系统性断裂（Layer B）延长线上，而是初始审查已覆盖文件（genre_config.py）上的规则计数不完备——说明"逐文件语义深读"对"声明 vs 实现计数对账"这一形状仍有盲区，且与 F202 同表不同洞，属同类未穷尽。
- 缺陷呈明显聚类: ①"声明→归一化之后断线"家族（F210/F224/F225/F226/F229）；②"权威规则表未全量编码"家族（F202/F232/F212/F213）；③"首匹配/覆盖式解析"家族（F203/F223/F233/F234）。三个家族各有系统性修法（接线审计、规则矩阵测试、解析器锚定改造），建议按家族立整改工单而非逐条打补丁。
- 建议闭合条件: 若下一轮（新角度）在 contracts/skills/* 内不再产出 P1 且 P2 增量 ≤2，可判定收敛；重点先修 F224（恢复 Layer B）与 F232/F202（genre-config 规则矩阵），两者都是一次修复消一族的高杠杆点。
