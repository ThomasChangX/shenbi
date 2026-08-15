> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C34）| **依赖:** 无硬前置（但 C1 键空间对账 lint 的验收依赖本簇的路径协议先定稿——gate 读方假 FAIL 多为路径解析错位的症状）| **范围:** gates/cli.py 参数协议、g4 各 checker 路径解析、G0 布局探测、phase_runner、snapshot 根、capability_fs | **核心洞察:** skill-output/novel-output/project-output 三套布局并存，rd/project_dir 双参数语义从未统一——checker 按 CWD 或错误根解析，相对路径调用恒假 FAIL（F101：T2 永久阻塞的实测复现）

# C34 · 路径/布局契约统一（path-layout-contract）

## 元信息
- 簇：C34（路径/布局契约分裂：rd/project_dir/三套输出布局），14 条，最高严重度 P1（F101/F401/F433/F519，其中 F101/F401 verified），证据等级=实验佐证
- 成员：F101（代表）、F115、F119、F401、F407-F408、F412-F413、F433、F446、F456-F457、F519、F628
- 来源：Z1/Z4/Z5/Z6 + 各复核轮
- 关系：supersede `2026-08-14-gate-effectiveness-design.md`（#8）的 R8/F163 面（=F101）

## 背景与根因
没有任何一处定义"rd 与 project_dir 各指什么、输出布局有哪几种、相对路径按哪个根解析"。各缺陷：
1. **假 FAIL 族**（F101 P1 verified：phase_runner G4 第 3 参传 round_dir，project-output 下输出恒 not_found，T2 永久阻塞；F401 P1 verified：g4/chapter_revision 忽略 rd/project_dir，标准相对路径调用即假 FAIL；F433 P1：CLI G4 分支 project_dir 恒等 rd，违背文档化 T2 协议 rd≠project_dir；F456：gate_G2 收 rd 但从不用于相对路径解析；F408：word_count_md 用未解析路径相对+rd 崩溃；F457：G4 bughunt/clean 分支丢 rd→ValueError）
2. **布局分裂**（F413：三套布局并存，G0.3 扫描不存在的 skill-output；F407：project_dir 只当布尔开关、目录上溯只认 skill-output）
3. **根错位**（F519 P1：快照根=框架仓库根，G2 与审计观测面不同根；F115：rglob 回退把项目内任意预存 .md 送 G2；F628：--write-audit-drift 写死相对路径依赖 CWD；F119：CapabilityFS 相对路径按进程 CWD 而非 allow_root 解析）
4. **契约张力**（F412：G1.4 在 checker 内写 .bak——纯验证契约偏离；F446：F401 触发链异议——假 FAIL 限"相对 json + rd + CWD≠rd"的手动 CLI 形态）

## 目标
1. 一页路径协议（docs/framework/）：rd（round 目录）与 project_dir（小说项目根）的唯一定义、三布局的探测规则与新旧映射、相对解析统一入口
2. 全部 checker 走同一 `resolve_input_path`/`resolve_output_path`；无 checker 自行拼路径或依赖 CWD
3. 快照/审计/G2 观测面同根

## 任务分解
### R1 · 路径协议成文 + 单源 helper（F413 + F407 + 全簇地基）
- `gates/paths.py`（或扩展既有 resolve_input_path）：`Layout = detect(project_dir)`（novel-output/project-output/skill-output 兼容探测）+ `resolve(fp, rd, project_dir)` 单入口；协议写入 docs/framework/paths.md（含 rd≠project_dir 的 T2 调用矩阵）
- **验收**：`git grep -n "skill-output" -- src/shenbi/gates/` 仅剩探测表一处；三布局 fixture 各跑一遍 G4 定位到同一文件

### R2 · checker 接线（F101 + F401 + F433 + F456 + F408 + F457）
- phase_runner G4 参数改传 project_dir；g4/chapter_revision、g4_chapter_drafting、length_normalizing、gate_G2、cli G4 全分支改走 R1 helper；F446 的触发链描述并入回归用例注释
- **验收**：F101 实测复现场景（project-output + T2）G4 定位成功；相对路径 + CWD≠rd 手动 CLI 形态全绿

### R3 · 观测面同根（F519 + F115 + F628 + F119）
- 快照根、写审计根、G2 .bak 锚定统一为 project_dir（rd 只作 round 记录）；cmd_post_skill rglob 回退限定声明输出目录；--write-audit-drift 与 CapabilityFS 相对路径改按 allow_root/显式根解析
- **验收**：同一次 dispatch 的 G2 观测文件集 = write-audit 快照集（一致性断言用例）

### R4 · .bak 契约裁决（F412）
- G1.4 的 .bak 写入移出 checker（由 dispatcher 预阶段统一备份，checker 只读）或在 AGENTS.md 成文豁免——二选一裁决并同步文档
- **验收**：裁决落地后 `just gate G1` 无写副作用（或豁免成文）

## 验收（簇级）
- `just check` 全绿；`tests/unit/gates/test_path_resolution.py` 参数化覆盖（3 布局 × rd 传/不传 × 相对/绝对 × CWD 两态）
- C34 全部 14 条 merged-into F101 回写关闭

## 风险
- R1 协议若选择"废除 skill-output 兼容"，旧 round 数据不可读——保留只读兼容探测，新产物单一布局
- 本簇是 C1（读方对账 lint）的地基：C1 验收中"gate 能读到真实写方产物"的用例须在本簇合入后才能全绿，两 spec 验收顺序见总纲依赖表

## 验证命令
- 布局探测单源：`git grep -n "skill-output" -- src/shenbi/gates/`（仅剩探测表一处）
- 路径矩阵：`pytest tests/unit/gates/test_path_resolution.py -q`（3 布局 × rd 传/不传 × 相对/绝对 × CWD 两态参数化）
- T2 复现（F101）：project-output 布局 round 上 `shenbi-validate G4 <files> generative` 定位成功
- 观测面同根：同一次 dispatch 的 G2 观测集 = write-audit 快照集（一致性断言用例）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F101 <- F115, F119, F401, F407-F408, F412-F413, F433, F446, F456-F457, F519, F628`
- 上轮承接：#8 的 R8/F163 面（=F101）随本簇关闭；F446（触发链异议）的裁注并入回归用例注释
