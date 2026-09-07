> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-07 · 价值门首轮驳斥复核：F401/F408/F519 已由先前 PR 修复出簇，F101/F115 降级为部分残留，见各条注记) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C34）| **依赖:** 无硬前置（但 C1 键空间对账 lint 的验收依赖本簇的路径协议先定稿——gate 读方假 FAIL 多为路径解析错位的症状）| **范围:** gates/cli.py 参数协议、g4 各 checker 路径解析、G0 布局探测、phase_runner、write-audit/drift 观测根、capability_fs | **核心洞察:** skill-output/novel-output/project-output 三套布局并存，rd/project_dir 双参数语义从未统一——checker 按 CWD 或错误根解析，相对路径调用恒假 FAIL

# C34 · 路径/布局契约统一（path-layout-contract）

## 元信息
- 簇：C34（路径/布局契约分裂：rd/project_dir/三套输出布局），修订后 11 条存活（原 14 条；F401/F408/F519 已修复出簇，F101/F115 降级并入），最高严重度 P1（F101 残留面/F433），证据等级=实验佐证 + 2026-09-07 main HEAD 驳斥复核
- 存活成员：F433（代表）、F101(残留)、F115(残留)、F407、F412、F413、F446(裁注)、F456、F457、F628、F119(语义修正)
- 出簇（2026-09-07 复核，已被先前 PR 修复）：F401（resolve_input_path 接线 + ValueError 防 CWD 回退，gates/shared.py:65-82）、F408（chapter_drafting.py:227 先 resolve 再 word_count + cli.py:153-163 ValueError 守卫，PR #142 F437）、F519（snapshot_tree(project_dir) 两平面同根，dispatch_helper.py:2651/2673）
- 来源：Z1/Z4/Z5/Z6 + 各复核轮（F 编号以 **2026-08-15** findings-ledger 为准）
- 关系：supersede #8（已归档 Done，PR #63/#64）的 R8/F163 面（=F101 原始指控；其崩溃链已被 ecef16e2 修复，残留面见下）

## 背景与根因
没有任何一处定义"rd 与 project_dir 各指什么、输出布局有哪几种、相对路径按哪个根解析"。G4 读方已有 `resolve_input_path`（gates/shared.py:65，~25 个 checker 接线），但统一止步于此——G2 与 bughunt/clean 分支未接，布局探测无单源，观测根仍分裂。修订后各缺陷：
1. **假 FAIL/假 PASS 残留族**（F433 P1：cli.py:150 `project_dir=rd` 恒等，违背文档化 T2 协议 rd≠project_dir——后果：g4_post_write_integrity 在 `project_dir/audits`（=rd/audits）找 `.integrity-findings-<n>.jsonl`，而写方 `_write_parsed_outputs` 写真实 project_dir（dispatch_helper.py:1197），project_dir≠rd 时 PWI findings 静默缺席；F101 残留面同此根因：phase_runner.py:261-263 现传 rd 正确，崩溃链不复现；F456 P1：gate_G2 收 rd 但 G2.1 存在性检查仍用裸 `Path(fp)`（g2.py:59）按 CWD 解析，rd 仅用于 G2.11 truth-diff 分支；F457：g4/generic.py:381-388 bughunt/clean 包装不收不传 rd，cli.py:131-139 直传 file_list 且 ValueError 守卫只包 generative 分支——相对路径 + bughunt/clean = 未捕获崩溃）
2. **布局分裂**（F413：三布局并存（g0.py:210 skill-output / g0.py:664 novel-output / phase_runner.py:309 project-output），G0.3 扫描可能不存在的 skill-output；F407：project_dir 在 g4_generic_* 只当布尔开关（generic.py:371），目录上溯只认 skill-output（chapter_drafting.py:265-267）；已有 RoundPaths（src/shenbi/paths.py，PR #19）与 resolve_input_path 但均非全 gate 面单入口，无 docs/framework/paths.md 协议）
3. **观测根错位残留**（F115 残留：cmd_post_skill rglob 回退仅存 `chapter is None` 角落（phase_runner.py:240-255），仍会把项目内任意预存 .md 送 G2；F628：compute_drift.py `--write-audit-drift` 写死 `Path("truth/audit_drift.md")` CWD 相对 + 趋势文件默认 CWD 相对；F119 语义修正：CapabilityFS（capability_fs.py:22-28）现为 fail-closed（越 allow_root 抛 PermissionError）而非读错文件，残留 = 相对路径按进程 CWD resolve 而非拼接 allow_root）
4. **契约张力**（F412：G1.4（g1.py:224-237）在纯验证 checker 内 safe_write .bak——G2.11 依赖 .bak 的现状与"checker 无副作用"契约冲突，需裁决；F446 裁注：F401 触发链原限定"相对 json + rd + CWD≠rd 手动 CLI 形态"——该形态现已由 resolve_input_path 消除，裁注改为回归用例断言该形态恒绿）

## 目标
1. 一页路径协议（docs/framework/paths.md）：rd（round 目录）与 project_dir（小说项目根）的唯一定义、三布局的探测规则与新旧映射、相对解析统一入口（收敛 resolve_input_path 与 RoundPaths 的关系声明）
2. G2 与 G4 全分支（含 bughunt/clean）走同一 `resolve_input_path`；cli.py 不再把 project_dir 恒等 rd（T2 协议下传真实 project_dir 或成文豁免）
3. drift/audit 写观测面同根（project_dir/allow_root），无 CWD 依赖

## 任务分解
### R1 · 路径协议成文 + 布局探测单源（F413 + F407 + 全簇地基）
- `gates/paths.py`（或扩展既有 resolve_input_path/paths.py）：`Layout = detect(project_dir)`（novel-output/project-output/skill-output 兼容探测）+ 协议写入 docs/framework/paths.md（含 rd≠project_dir 的 T2 调用矩阵、RoundPaths 与 resolve_input_path 的分工声明）；G0.3/G0.cc 布局扫描改走探测单源
- **验收**：`git grep -n "skill-output" -- src/shenbi/gates/` 仅剩探测表一处；三布局 fixture 各跑一遍 G4 定位到同一文件

### R2 · gate 接线收口（F433 + F101 残留 + F456 + F457 + F446 裁注）
- cli.py G4 分支区分 rd 与 project_dir（新增显式 project_dir 参数或成文 rd==project_dir 的 T1 豁免矩阵）；g4_post_write_integrity 按 R1 协议锚定真实 project_dir；gate_G2 的 G2.1 存在性检查改走 resolve_input_path(fp, rd)；bughunt/clean 包装签名收 rd 并接线；F446 裁注改回归用例（相对 json + rd + CWD≠rd 恒绿）
- **验收**：project-output 布局 + project_dir≠rd 场景 PWI findings 可被 G4 定位（修复 F433 静默缺席）；相对路径 + CWD≠rd 下 G2/bughunt/clean 全绿不崩溃

### R3 · 观测面同根残留（F115 残留 + F628 + F119）
- cmd_post_skill rglob 回退限定声明输出目录（或 chapter is None 时显式 FAIL 而非扫描）；compute_drift 的 audit/trend 写入路径按显式根（--project-dir 或 allow_root）解析；CapabilityFS 相对路径改按 allow_root 拼接后校验
- **验收**：rglob 回退不再捡项目内预存 .md；CWD≠project_dir 下 compute_drift 写入位置不变；相对路径 CapabilityFS 操作锚定 allow_root（单测断言）

### R4 · .bak 契约裁决（F412）
- G1.4 的 .bak 写入移出 checker（由 dispatcher 预阶段统一备份，checker 只读）或在 AGENTS.md/docs/framework/gates.md 成文豁免——二选一裁决并同步文档
- **验收**：裁决落地后 G1 checker 无写副作用（或豁免成文 + docstring 引用）

## 验收（簇级）
- `just check` 全绿；`tests/unit/gates/test_path_resolution.py` 参数化覆盖（3 布局 × rd 传/不传 × 相对/绝对 × CWD 两态 × project_dir=rd/≠rd）
- C34 修订后 11 条存活成员 merged-into F433 回写关闭；F401/F408/F519 三条在 ledger 标注已由先前 PR 修复出簇

## 风险
- R1 协议若选择"废除 skill-output 兼容"，旧 round 数据不可读——保留只读兼容探测，新产物单一布局
- 本簇是 C1（读方对账 lint）的地基：C1 验收中"gate 能读到真实写方产物"的用例须在本簇合入后才能全绿，两 spec 验收顺序见总纲依赖表
- R2 改 cli.py G4 签名/语义涉及全部 G4 调用方（phase_runner、tests、pipeline）——须 grep 全调用方兼容迁移

## 验证命令
- 布局探测单源：`git grep -n "skill-output" -- src/shenbi/gates/`（仅剩探测表一处）
- 路径矩阵：`pytest tests/unit/gates/test_path_resolution.py -q`（3 布局 × rd 传/不传 × 相对/绝对 × CWD 两态 × project_dir 两态参数化）
- F433 复现：project-output 布局 + project_dir≠rd round 上 `shenbi-validate G4` PWI findings 定位成功
- 观测面同根：CWD≠project_dir 下 drift 写入位置不变（单测断言）+ CapabilityFS 相对路径锚定 allow_root（单测断言）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3，修订后）：`F433 <- F101, F115, F407, F412-F413, F446, F456-F457, F628, F119`
- 出簇：F401、F408、F519（2026-09-07 驳斥复核确认已由先前 PR 修复，ledger 注记修复出处）
- 上轮承接：#8 的 R8/F163 面（=F101 原始指控）崩溃链已修，残留面（F433 根因）随本簇关闭；F446 裁注改回归用例
