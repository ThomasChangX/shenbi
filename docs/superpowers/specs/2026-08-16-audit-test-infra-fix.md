> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08 · 阶段 1 复核：11 存活 / 2 降级 / 1 子句驳斥，证据刷新至 main HEAD b21997f4) | **Severity:** 🟠 P1（F1159 回归重放机制双重死亡）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C17）| **代表 finding:** F001 | **簇规模:** 18 条 | **严重度上限:** P1
> **范围:** .github/workflows/（nightly/ci）、pyproject.toml（pytest/mutmut/hypothesis 配置）、tests/baselines/、tests/golden/、tests/benchmark/ | **证据等级:** 实验佐证（T11 线程实测复现 mutmut 空转根因 + Z11-b）
> **与既有 spec 关系:** #16/#25 批量 spec 不含本簇；doc-links 部分与 C23（文档机械漂移）共享防线目标，执行顺序建议 C17 先立 CI 承载面

# C17 · 测试基础设施配置失效修复（test-infra）

## 背景（根因 + 证据）

**根因**：承诺的质量防线（nightly、doc-links、benchmark、mutation、hypothesis 回归重放、golden 集）全部处于"配置齐全但不执行/执行即空转"状态——基础设施只有声明没有运行，失效无人发现（phase4 §1 候选元根因 F 的第四拆分）。

代表证据：
- **F001**（P2）：nightly.yml:8-16 schedule 被注释整体 DISABLED → doc-links 371 项测试零自动执行环境（本地工具未装即 skip + nightly 禁用，双层门禁挡死）
- **F1159**（P1）：hypothesis「Examples ARE committed」回归重放双重死亡——.gitignore 压制使 43+ 失败样本从未入库（CI/新克隆零重放），叠加上轮 F1318（M）未修；T1107 协调者抽核：examples/ 44 文件仅 .gitkeep 被跟踪
- **T1104**（P2，实测复现；**2026-09-08 降级**：pyproject 已改 `paths_to_mutate` 多文件数组写法，配置键问题已修）：mutmut 基线两个月未建立；残存根因 = venv editable .pth 令沙盒测试静默测回原仓库
- **F741**（P2）：tests/golden/README.md 承诺的 golden 评测集（chapter-N-original.md 等）不存在，无任何测试消费（T1106：README 承诺 10-20 章实际 0 文件）
- **F742/T1102**（P2；**2026-09-08 部分驳斥 + 降级为 M 级残件**：tests/benchmark/test_c28_baselines.py 已有 3 真实用例——PR #153，且因拼写失配未被排除、现已被正常收集；存活面仅一行死配置删除）：norecursedirs 写 `tests/benchmarks`（复数）但实际目录 `tests/benchmark`（单数）——指向不存在目录的死排除项，纯配置谎言
- **F782/T1103**（P2；**2026-09-08 降级**：G4-genre_config.json 已被 tests/unit/test_scoring.py:1267 消费，剩 6/7）：gate-outputs 基线 6/7 无自动化消费者且多数已实质漂移，G6/G7 不可再生成（tests/rounds 不存在）
- **F783**（P2）：mutation-score.txt 为 "BASELINE NOT YET ESTABLISHED" 占位，`just mutate-check` 恒失败；F1010：compare_mutation_score.py docstring 称 CI 使用实际未接线
- **F1158**（P2）：43 个失败样本全 stale——10 个测试 key 与当前 58 个 @given 函数 digest 0/10 匹配，本地重放价值为零
- **F1160**（P2）：.benchmarks 基准历史为单次冒烟 autosave，无真实基准套件、无跨运行可比性
- **T1101**（P2）：压力测试纯 prompt 无 harness——6 个 prompt md 零 CI/harness 引用
- **T1105**（P2）：两模块突变得分 35.1%/32.4% <50%，escalation 54% 突变体无测试触达
- **T1109**（P2）：G0.5 权重和校验永久 UNIMPLEMENTED，2026-06 基线曾以硬编码假 PASS 掩盖
- **F732**（P2）：doc-links 在任何场所都不执行且逐文件 spawn 子进程（性能面）

## 目标

每条防线二选一并落笔成文：**激活**（真实运行 + 结果被消费）或**诚实下线**（删除承诺与配置，文档不再声称）。消灭"配置存在但永不运行"的中间态。

## 任务分解

### T1 · hypothesis 回归重放复活（P1 优先）
1. .gitignore 手术：`.hypothesis/` 整目录忽略改为 `.hypothesis/*` + 定向反排除（`!examples/`、`!.gitignore`）——目录级忽略下 git 无法 re-include 子文件（F1318 失败模式根源），必须先拆目录通配；提交现存 44 样本（**执行结果 2026-09-08**：43 stale 样本删除——hypothesis 6.155 对通过样本自动剪除，43 个沉积即陈旧证据；库以 go-forward 形态激活，见 spec-deviations）
2. 清 stale（F1158）：对 10 个 digest 0/10 匹配的 key 重放定级——仍失败的修测试或删样本，全 stale 的整批重建
3. CI replay 接线：样本入库后 Hypothesis 在常规 pytest 运行中隐式重放 examples 库；CI 步骤须使日志可见证重放发生（如 `--hypothesis-show-statistics` 输出），使"样本入库"真正等于"CI 重放"（F1159 验收锚点）

### T2 · doc-links 防线落地（与 C23 共享）
4. F001/F732：nightly 恢复 schedule 或拆分 internal-links 子集进 per-PR CI（推荐后者：内部链接检查无 npm 依赖可纯 Python 实现）；改造为批量解析而非逐文件 spawn
5. 该防线上线即成为 C23 机械漂移修复的持续防线（C23 验收依赖此项）

### T3 · mutation 基线建立或下线
6. T1104 残存修复路径（配置键已修，2026-09-08 复核）：排除 editable .pth 干扰（沙盒复制树方案为首选；mutmut 3.x CLI/配置可用面先实测核实再选）后建立基线；下线时钟自本任务开工起算两周（**执行结果 2026-09-08**：SDD 单 session 压缩为限时尝试，复现三重结构性障碍后裁决下线，见 spec-deviations）
7. F783/F1010：基线建立后 mutation-score.txt 写入真实值、compare_mutation_score.py 接入 CI（weekly）或删除；T1105 低分模块（escalation 等）→ C15 已 Done（PR #189），若其补测面未覆盖则在 findings-ledger 为 T1105 开新登记行、归属本 spec 处理，不指向已关闭 spec
8. 若两周内无法修复 mutmut 空转：下线路径——删 mutmut 配置与 just mutate-check，justfile/README 同步（自包含步骤，不等 C24）
9. F782/T1103：gate-outputs 剩余 6/7 基线接线（G6/G7 回归测试读取）或删除（G4-genre_config.json 已有消费者，保留）

### T4 · golden/benchmark 诚实化
10. F741/T1106：golden 集二选一——从 novel-output 真实树建 5 章最小集并接入差分断言，或删 README 承诺
11. F742/T1102：删除 norecursedirs 中指向不存在目录的死条目 `tests/benchmarks`（tests/benchmark 真实用例——#153 建立——现已被正常收集，保持收集状态，勿删勿重建勿排除）；F1160 的 .benchmarks 冒烟数据清掉
12. T1101：6 个压力 prompt md 要么接 harness（作为 T1 压力场景数据源）要么移入 docs/ 降级为设计材料（注：norecursedirs 现行排除 tests/pressure-tests，接 harness 时需同步移除该排除）

### T5 · G0.5 假 PASS 清理
13. T1109：G0.5 权重和校验实现真逻辑（读权重表求和断言；原注释称全量校验昂贵——以全量跑一次实测裁决，若确贵则采样并记录理由），删除 UNIMPLEMENTED/硬编码分支；基线记录更正

### 批量清理（M 级成员）
本簇无 M 级成员（18 条全 P1/P2）。

## 验收标准（真实数据可复验）

1. `git ls-files .hypothesis/examples | wc -l` > 0；本地：对注入的 1 个已知失败样本 replay 会红（红灯验证，先于 CI 落地）；CI：workflow 日志可见 replay/statistics 执行记录——且 CI 重放证据须锚定提交样本确实被加载（如空库新克隆下注入失败样本使 CI 红，或日志含 example 载入痕迹），statistics 输出本身不构成重放证明
2. internal-links 检查在 per-PR CI 真实运行：临时把 README 一条链接改坏 → CI FAIL（记录后还原）
3. mutation 路径定稿后：`just mutate-check` 要么以真实基线通过，要么该命令与配置从仓库消失（`git grep mutmut` 与声称一致）
4. golden/benchmark：README/配置声称与磁盘一致（承诺集存在且有消费者，或承诺删除）——`grep -rn "golden" tests/ README*` 与实际对账 + 若选激活分支须有 pytest 消费者实际运行绿的证据
5. G0.5：权重表注入一个和≠100 的负样本 → G0 FAIL（红灯验证）
6. `just check` / `just test` 全绿；无新增 skip

## 风险与回滚

- **风险**：激活防线后存量失败一次性涌出（doc-links 断链 ~371 项、mutation 低分）——先跑基线报告分级：阻断级立即修（多数与 C23 文档漂移同体），非阻断登记跟进
- **风险**：nightly/per-PR CI 时长增长——internal-links 拆子集 + 批量解析控制；mutation 限 weekly/按模块轮转
- **回滚**：每个 T 独立 PR；CI 工作流改动可整文件 revert；hypothesis 样本入库为纯新增无回滚风险

## 簇成员清单（18 条，自查用）

F001, F732, F741-F742, F782-F783, F1010, F1158-F1160, T1101-T1107, T1109（代表 F001）
