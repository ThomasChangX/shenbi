> **Date:** 2026-08-14 | **Status:** Design (Revised 2026-08-24 · SDD #8 执行前事实修正：F404 路径迁至 contracts/schemas/decisions.py、R9 引用 materialize 实为 trace/materialize.py、R8/F163 划归 #48/C34 不在本份范围) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** src/shenbi/gates/ + dispatcher/ + pipeline/ | **核心洞察:** G3.4 独立性门被伪造证据击穿 + 门序回归使 G1/G2 空转

# 门禁有效性（G3/G2/门序）

## R1 · run_gate_g3 伪造 scorer 证据（F408, P1；从属 F214/F3AF）
- 证据：dispatch_helper.py:2262-2287（原引 1921-1945，行号已漂移）在 progress.json 缺失时写入伪造 `current_scorer_agent: pipeline-g3-scorer-<uuid>` + `scoring_history` → G3.4 fail-closed 恒 PASS
- 影响：G3 全路径零真实校验（与 F345 并行波无 G3 叠加 → G3.4 显式契约静默满足）
- 修复：删除伪造写入，缺证据时如实 FAIL（行为变更：依赖伪造 PASS 的既有 round 将开始 FAIL——预期 fail-closed，无回滚路径需要）；**验收：空 progress 目录 G3 FAIL**

## R2 · 并行审计波绕过 G3（F345, P1）
- 证据：6 个 audit skill requires_independent=True，串行路径 chapter_loop.py:3023 跑 G3，并行波（parallel_dispatch）零 G3 调用
- 修复（2026-08-24 择一定案）：**并行波接入 G3**——parallel_dispatch 在波完成后对 requires_independent=True 的 skill 调 run_gate_g3（真实证据、缺则 FAIL），结果写入 gate-manifest；**验收：并行波审计后 gate-manifest 含 G3 记录**

## R3 · executor 门序回归（F227, P1；从属 F246）
- 证据：executor.py:203-227（原引 190-199，行号已漂移）在 dispatch_codex 之前跑 G1/G2（校验尚不存在的输出）；原 shell 版注释 "the skill execution happened earlier"（git show 99f91f0）
- 影响：文档化 first-novel 流程第一步即失败；fresh round G1/G2 恒 FAIL
- 修复：G2 移至执行后（或仅校验预存在输出）；**验收：fresh round worldbuilding 派发 PASS**

## R4 · GR.2 -scores 后缀误报（F401, P1）
- 证据：g_reconcile.py:50-68 不剥离 `-scores` 后缀 → 生产命名 `<skill>-generative-scores.json` 恒误报 FAIL；测试 docstring 自认规避（masking）
- 修复：stem 依次剥离 `-subagent`、`-scores` 后缀（覆盖 F464 记载的 `*-scores-subagent.json` 生产命名）+ 删除测试规避注释
- **边界（2026-08-24 审查定案）**：状态字面量大小写归一（生产写 `done`、GR.2 判 `DONE`，F449）**不在本项**——F449/F710 由 spec #24 承接，避免双修
- **验收：生产命名（含 -scores-subagent）+ progress 状态 "DONE"（大写构造）→ GR.2 不再因后缀 FAIL**

## R5 · P2.5 rationale 空串绕过（F404, P1；从属 F458/F232）
- 证据：src/shenbi/contracts/schemas/decisions.py:33 `has = rationale is not None`（2026-08-24 修正：原引 gates/decisions.py 已迁移）——空串 `""` 视为已提供 → manual_override + "" 通过 REQUIRED
- 修复：Selection `_p25` 与 Adjustment `_rationale` 两处 validator 同步收紧——`has = bool(rationale and rationale.strip())`；Adjustment.rationale 增加 strip 非空校验（F458：`rationale: str` 必填但空串通过）；**验收：空串/纯空白 rationale → REJECT（Selection 与 Adjustment 各一例）**

## R6 · genre_config disabled 维度空 customRules 跳过（F216, P1）
- 证据：genre_config.py:94 `if disabled and self.custom_rules:`——customRules 空时整段跳过
- 修复：`if disabled:` 逐维度要求 rule 命中；**验收：disabled dim + 空 rules → REJECT**

## R7 · G7.1b ALL_SKILLS 反向覆盖（F432, P1）
- 证据：ALL_SKILLS=74 vs t1-skill 69，5 个无脚手架技能（group-*/lifecycle）永不 FAIL 反转
- 修复（2026-08-24 择一定案）：**反向覆盖以 t1-skill 脚手架全集为准**（69，不补脚手架）；**验收：反推断言——5 个无脚手架技能不再出现在 missing_coverage；全技能覆盖 round 的 G7.1b PASS 用脚手架全集反推表达**

## R8 · phase_runner G4 目录参错位（F163, P1）——已划归 spec #48/C34（2026-08-24 范围裁定）
- 证据：phase_runner.py:216 G4 第 3 参传 round_dir，T2 输出在 `<round-dir>/project-output/` → 11 个 rp.read checker 恒 not_found → T2 永久阻塞
- **范围裁定**：#48（C34 路径/布局契约统一）显式 supersede 本项——一页路径协议 + resolve 单入口是更根本修复，本份只修传参会与之冲突。本份 SDD #8 不实施 R8，由 #48 承接

## R9 · G3.3 output_files 层级错位恒 SKIP（F444, P1；同族 R1/R2）
- 证据：g3.py:151-153 `skills.get(skill,{}).get("output_files",[])` 在 skill 层读，而全部生产 progress 写入方均**不含 output_files 键**（codex.py:44 只写 score/status、trace/materialize.py 只写 status/score（2026-08-24 修正路径）、round-exec.sh 写空 skills、run_gate_g3 伪造无 skills 键；g_reconcile.py:36-40 按 `[skill][test_type]` 解析同一结构；Z4.review4 修正 review3 的 "test_type 层" 说法）→ "G3.3 Output files passed G2" 复查在所有已知生产形状下恒 SKIP；tests/unit/gates/test_g3.py:118/220 用非生产形状（skill 层 output_files）钉死代码路径，掩盖死路
- 修复（2026-08-24 审查定案，读侧+写侧双改）：① g3.py 改读 `skills.get(skill,{}).get(test_type or "generative",{}).get("output_files",[])`（test_type 层）；② producer 接线——codex `_record_completion` 增可选 `output_files` 参数写入 `skills[skill][test_type]["output_files"]`（调用方从契约 writes 传入），否则修完读侧门仍恒 SKIP；③ 测试改用生产形状（经真实 `_record_completion` 代码路径构造，满足 G0.9）；**附带**：修复后 gate_G2 对非 dict JSON 抛的 ValueError（F419/F431 家族）将穿透 g3.py:188 except（仅 JSONDecodeError/OSError）→ 一并加 ValueError；**验收：经真实 producer 写入 output_files 的 progress + gate_G3 → G3.3 实际执行（非 SKIP）**
- 边界：trace/materialize.py 的 MARK_DONE 事件不携 output_files——pipeline 路径的 G3.3 维持 SKIP-by-design（记 spec-deviations），扩展 trace 事件 schema 归 #31/C5 域

## 补充（同批次）
- **F402（P1）**：g4_length_normalizing 用未解析路径计字数（:29 解析 pf vs :35 用原始 fp）→ rd+相对路径崩溃；改 `word_count_md(pf)` + 补回归测试
- **F158（P1）**：phase_runner phase 参数未净化拼接进状态文件路径（load_state/save_state `f"{phase}.json"`）→ `../` 穿越写出 round_dir；净化 phase 参数（白名单或路径安全校验）
- **F417（记录条目）**：Z4 覆盖率缺口（tests/unit/gates 无 test_gate_manifest.py，gate_manifest 0% 覆盖）——**随本份 R1/R2 收编**（两者均写 gate-manifest，task 补 test_gate_manifest.py 行为级测试）
