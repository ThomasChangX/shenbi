> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 P0（F751 内容级断链）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C16，候选元根因 F 核心）| **代表 finding:** T801 | **簇规模:** 31 条 | **严重度上限:** P0
> **范围:** tests/fixtures/ 全量 + tests/tiers/ 场景 + src/shenbi/gates/g0.py（g0_purity 执法）+ calibration/ | **证据等级:** 实验佐证（T8 线程 + Z7-c/Z7-d，协调者核验 g0_purity 零执法）
> **与既有 spec 关系:** 吸收 #18（archive/2026-08-14-fixture-authenticity-design.md）未执行的 R1–R4 全部内容并扩展 G0.9 执法面——#18 建议随本 spec 启动而归档（归档动作由协调者执行）

# C16 · fixture 真实性失真与 G0.9 零执法修复（fixture-authenticity-fix）

## 背景（根因 + 证据）

**根因**：G0.9 声称 "fixtures exclusively real outputs / upstream copies"，但门只验 scenario 路径前缀、不验存在性/内容/来源——真实性零执法。fixture 大量为虚构/复制体/占位符，形成四链传导：**fixture 失真 → 场景空转 → 测试假阳性 → 契约虚设**（T809），测试绿灯不构成生产行为验证（phase4 §1 候选元根因 F 主拆分）。

代表证据：
- **T801**（P1，verified）：g0_purity 路径白名单 + grep provenance 为空——执法零检查
- **F751**（P0，verified）：t1 bug-hunt/clean 模板场景的植入缺陷在所引 fixture 内容中不存在（内容级断链，bug-hunt 测试空转）
- **F752**（P1）：location-builder bug-hunt 缺陷表第一行 "`chapter-plan-example.md` vs `chapter-plan-example.md`" 自引用比较
- **F753**（P1）：874KB 公版小说《钢铁是怎样炼成的》（report-example.txt）被 9 个场景声称为各自评审产物
- **F754**（P1）：expected-output.md 证据定位指向从未物化的轮次产物路径（world/rules.md、story/okr.md 等）
- **F776**（P1）：27 个校准锚点引文为虚构语料（"半块黑石饼/老周"全库 grep 不存在于 novel-output/），违反自身 schema 且被 G0.14 锁哈希
- **F777**（P1）：9 个 chapter draft 是同一文本仅改 H1 章号的复制体且零引用；**F778**：chapter-7/8/9-example 三文件逐字节相同
- **F779**（P1）：snapshots/chapter-025/manifest.md 的 checksums 为占位符（`sha256:abc123`）
- **T802**（P1）：4 个 fixture 内嵌 G0.9 note 自我豁免 + frontmatter 虚构 generated_by（YAML 非法）
- **T804**（P1）：26 个被场景消费 fixture 完全无来源
- 其余：F761（15 真孤儿）、F762（变体文件绕过纯度扫描）、F763（"11 truth files" 虚构常数）、F780（4 对镜像未登记 MIRROR_MAP）、F781（32 副本无同步守卫）、F784（19 死 fixture）、F785/F786（停用词/敏感词表空转）、F787（genre-config-example 结构漂移）、F789（空目录被当存在引用）、F947（活跃 spec 验收依赖真实 LLM dispatch 或手写 mock）、F1154（snapshot-manage manifest.json 为测试构造非真实产物）、T803（G0.11 覆盖 4/91 且缺侧静默跳过）、T805（锚点 schema 无 source 字段+循环定义）、T806（引文行号虚构）、T807（20 chapters 数字断链）、T808（rhythm_principles 身份错配）

## 目标

1. **G0.9 从"声称"变"执法"**：scenario 引用的 fixture 路径必须存在；被消费 fixture 必须有 provenance（真实输出/上游副本/显式合成样本三态标注）；虚构内容冒充真实输出直接 FAIL
2. fixture 库清理：删除/重建/降标注，使 100% 可溯源
3. bug-hunt 场景内容级闭合：植入缺陷必须真实存在于所引 fixture（消灭 F751 空转）
4. calibration 锚点重建为真实 prose excerpt 或显式合成标注（连带 G0.14 锁值重算）

## 任务分解

### T1 · G0.9 执法补齐（先立防线再清库）
1. g0.py g0_purity 扩展三检查：(a) scenario 全部引用路径存在性闭包扫描（F789/T806 类即 FAIL）；(b) 消费中 fixture 的 provenance frontmatter 存在且三态合法（T802 的非法 YAML 与自我豁免 note 判 FAIL）；(c) 变体/旁路文件纳入同一扫描（F762）
2. bug-hunt 场景加内容级校验：expected 证据定位（文件+行号/锚文本）必须能在所引 fixture 中解析命中（F751/F754/T806）——最小实现：expected-output.md 的证据行格式化后 grep 验证
3. G0.11 缺侧静默跳过改为显式报告缺失清单（T803）

### T2 · fixture 库治理（T1 红线内逐类处置）
4. 复制体族（F777/F778）：9 个 chapter-draft 复制体零引用 → 删除；chapter-7/8/9 三胞胎 → 保留 1 份并重建为互异真实样本或删
5. 角色滥用（F752/F753）：report-example.txt 恢复其唯一合法角色（import 源小说），9 个误用场景改指各技能真实产物 fixture（从 novel-output 真实树复制入库并标 provenance）
6. 伪造快照族（F779/F780）：chapter-025 manifest 占位 checksum → 用真实 novel-output 快照重建；4 对镜像登记 MIRROR_MAP 或去重（F781 的 32 副本同步守卫一并为 check_fixture_mirror 加 CI 接线——与 C25 F1012 协同）
7. 孤儿/死件（F761/F784）：删除（word-stem 级 grep 0 命中复核后）
8. 词表/配置类（F785/F786/F787）：stop_words_zh.txt 按自身 spec 重排并接线消费者或删；sensitive_words.txt 扩容并与 scenario 声称对齐；genre-config-example.json 从真实输出重导
9. 虚构常数（F763）："11 truth files" 改为从 truth-files.yaml 计算

### T3 · calibration 锚点重建
10. 27 锚点（F776/T805）：锚文语料改用 novel-output 真实章节 excerpt；无法溯源的按"显式合成样本"降级标注；schema 加 source 字段（file+line 指针）
11. G0.14 锁值随重建重算（注意 T815 双实现哈希漂移问题，重算走 gate 同一规范化路径）

### T4 · spec 验收契约
12. F947：活跃 spec 中"依赖真实 LLM dispatch"的验收改写为可离线复验形式（fixture 回放/结构断言），plan 阶段不改写即 BLOCKED 的规则写入 writing-plans 约定
13. F1154：snapshot-manage 用真实 skill 产出的 manifest.json 替换测试构造件（与 C19 快照布局定稿协同）

### 批量清理（M 级成员）
- **F790**（M）：qidian 榜单 fixture 数据不可核验 → 降级"合成样本"标注或删除

## 验收标准（真实数据可复验）

1. `shenbi-validate G0 <seed>`（或对应 g0_purity 入口）在治理后的 fixture 库上 PASS，且对注入的 3 个负样本（不存在路径 / 无 provenance / 虚构 generated_by）各 FAIL 一次（红灯验证记录）
2. bug-hunt expected 证据闭包扫描 0 失败（扫描脚本输出计数 = 0）
3. `find tests/fixtures -type f | xargs grep -L "provenance"`（按最终约定字段）仅返回白名单文件；复制体检测（`fdupes` 或 hash 去重）在 fixtures 内 0 组重复（显式镜像登记除外）
4. calibration 27 锚点全部带可解析 source 指针，`shenbi-validate G0` 的 G0.14 分支用新哈希 PASS
5. 依赖 fixtures 的测试套件全绿且 skip 数不增；被删孤儿 fixture 全库引用扫描 0 残留
6. 与 #18 的验收项逐条对照：#18 R1–R4 全部被本 spec T1–T3 覆盖（对照表写入 PR 描述）

## 风险与回滚

- **风险**：清理动 tests/tiers 场景引用面广，可能连锁改 20+ scenario 文本——分批 PR（先执法后清理），每批独立可回滚
- **风险**：真实产物入库体积（novel-output 复制）——单文件截断策略须与 C29 的截断披露协议一致（截断要标注）
- **风险**：G0.9 收紧后存量违规一次性涌出——先跑全量报告定基线，分 P0（内容断链）/P1（无 provenance）/P2（孤儿）三波清
- **回滚**：g0_purity 新检查加 feature flag（env 或配置）可单独关闭；fixture 删除走独立 commit 便于 revert

## 簇成员清单（31 条，自查用）

F750-F754, F761-F763, F776-F781, F784-F787, F789-F790, F947, F1154, T801-T809（代表 T801；F750 为 G0.9 边界争议条）
