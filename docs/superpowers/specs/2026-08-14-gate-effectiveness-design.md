> **Date:** 2026-08-14 | **Status:** Design (Revised 2026-08-24 · SDD #8 执行前事实修正：F404 路径迁至 contracts/schemas/decisions.py、R9 引用 materialize 实为 trace/materialize.py、R8/F163 划归 #48/C34 不在本份范围) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** src/shenbi/gates/ + dispatcher/ + pipeline/ | **核心洞察:** G3.4 独立性门被伪造证据击穿 + 门序回归使 G1/G2 空转

# 门禁有效性（G3/G2/门序）

## R1 · run_gate_g3 伪造 scorer 证据（F408, P1；从属 F214/F3AF）
- 证据：dispatch_helper.py:1921-1945 在 progress.json 缺失时写入伪造 `current_scorer_agent: pipeline-g3-scorer-<uuid>` + `scoring_history` → G3.4 fail-closed 恒 PASS
- 影响：G3 全路径零真实校验（与 F345 并行波无 G3 叠加 → G3.4 显式契约静默满足）
- 修复：删除伪造写入，缺证据时如实 FAIL；**验收：空 progress 目录 G3 FAIL**

## R2 · 并行审计波绕过 G3（F345, P1）
- 证据：6 个 audit skill requires_independent=True，串行路径 chapter_loop.py:2907-2917 跑 G3，并行波（parallel_dispatch）零 G3 调用
- 修复：并行波接入 G3 或显式声明审计 skill 独立性由其他机制保证；**验收：并行波审计后 gate-manifest 含 G3 记录**

## R3 · executor 门序回归（F227, P1；从属 F246）
- 证据：executor.py:190-199 在 dispatch_codex 之前跑 G1/G2（校验尚不存在的输出）；原 shell 版注释 "the skill execution happened earlier"（git show 99f91f0）
- 影响：文档化 first-novel 流程第一步即失败；fresh round G1/G2 恒 FAIL
- 修复：G2 移至执行后（或仅校验预存在输出）；**验收：fresh round worldbuilding 派发 PASS**

## R4 · GR.2 -scores 后缀误报（F401, P1）
- 证据：g_reconcile.py:52-62 不剥离 `-scores` 后缀 → 生产命名 `<skill>-generative-scores.json` 恒误报 FAIL；测试 docstring 自认规避（masking）
- 修复：`stem.removesuffix("-scores")` + 删除测试规避注释；**验收：生产命名 + progress DONE → PASS**

## R5 · P2.5 rationale 空串绕过（F404, P1；从属 F458/F232）
- 证据：src/shenbi/contracts/schemas/decisions.py:33 `has = rationale is not None`（2026-08-24 修正：原引 gates/decisions.py 已迁移）——空串 `""` 视为已提供 → manual_override + "" 通过 REQUIRED
- 修复：`has = bool(rationale and rationale.strip())`；**验收：空串 rationale → REJECT**

## R6 · genre_config disabled 维度空 customRules 跳过（F216, P1）
- 证据：genre_config.py:94 `if disabled and self.custom_rules:`——customRules 空时整段跳过
- 修复：`if disabled:` 逐维度要求 rule 命中；**验收：disabled dim + 空 rules → REJECT**

## R7 · G7.1b ALL_SKILLS 反向覆盖（F432, P1）
- 证据：ALL_SKILLS=74 vs t1-skill 69，5 个无脚手架技能（group-*/lifecycle）永不 FAIL 反转
- 修复：反向覆盖以脚手架全集为准或补脚手架；**验收：满分 round G7.1b PASS**

## R8 · phase_runner G4 目录参错位（F163, P1）——已划归 spec #48/C34（2026-08-24 范围裁定）
- 证据：phase_runner.py:216 G4 第 3 参传 round_dir，T2 输出在 `<round-dir>/project-output/` → 11 个 rp.read checker 恒 not_found → T2 永久阻塞
- **范围裁定**：#48（C34 路径/布局契约统一）显式 supersede 本项——一页路径协议 + resolve 单入口是更根本修复，本份只修传参会与之冲突。本份 SDD #8 不实施 R8，由 #48 承接

## R9 · G3.3 output_files 层级错位恒 SKIP（F444, P1；同族 R1/R2）
- 证据：g3.py:151-153 `skills.get(skill,{}).get("output_files",[])` 在 skill 层读，而全部生产 progress 写入方均**不含 output_files 键**（codex.py:44 只写 score/status、trace/materialize.py 只写 status/score（2026-08-24 修正路径）、round-exec.sh 写空 skills、run_gate_g3 伪造无 skills 键；g_reconcile.py:36-40 按 `[skill][test_type]` 解析同一结构；Z4.review4 修正 review3 的 "test_type 层" 说法）→ "G3.3 Output files passed G2" 复查在所有已知生产形状下恒 SKIP；tests/unit/gates/test_g3.py:118/220 用非生产形状（skill 层 output_files）钉死代码路径，掩盖死路
- 修复：改读 `skills.get(skill,{}).get(test_type or "generative",{}).get("output_files",[])`；测试改用生产形状；**附带**：修复后 gate_G2 对非 dict JSON 抛的 ValueError（F419/F431 家族）将穿透 g3.py:188 except（仅 JSONDecodeError/OSError）→ 一并加 ValueError；**验收：生产形状 progress + output_files → G3.3 实际执行（非 SKIP）**

## 补充（同批次）
- **F402（P1）**：g4_length_normalizing 用未解析路径计字数（:29 解析 pf vs :35 用原始 fp）→ rd+相对路径崩溃；改 `word_count_md(pf)` + 补回归测试
- **F158（P1）**：phase_runner phase 参数未净化拼接进状态文件路径（load_state/save_state `f"{phase}.json"`）→ `../` 穿越写出 round_dir；净化 phase 参数（白名单或路径安全校验）
- **F417（记录条目）**：Z4 覆盖率缺口处置汇总（tests/unit/gates 无 test_gate_manifest.py / test_memory_distill.py，gate_manifest 0% 覆盖——随 F431/F471 家族修复补测试）
