# Spec #92 · 测试与门禁管线卫生（test-ci-hygiene）：deps.json 工具哈希块**删除**（calibration 半段保留）、标记退役、阈值单源、hook 构造性子集

**日期**：2026-11-01（r2 修订 2026-11-02：`_tool_hashes` 由「坍缩为单摘要」改判**整删**——亲验确认 G7 不使用它、唯一消费者是 R3 自洽检查；连带测试处置列全；**r2.2 2026-11-02 全量对抗式审计修订**——T3 标记退役按现文不可执行（`--strict-markers`+1,153 标注=收集 ERROR，已复现），改三选一；T1 连带清单补两处与 G0.14 文案；数字按实测刷新；**r3 2026-11-15 价值门 REWRITE 修订**——T1 拆双职：lock-tool-hashes.sh 后半段（:34-59）锁 `_calibration_hashes.combined` 是 G0.14 运行时消费物（g0.py:221）且为唯一 re-lock writer，「整删脚本+文案指向 just generate」是悬空指针（sync_contracts 对 calibration 零处理）→ 改为脚本瘦身保 calibration 半段、G0.14 提示串换名；判据 1 补排除面 `docs/superpowers/audit-runs/`（40 个历史文件命中，as-written 恒红）；定序勘误（extra:forbid 下唯一安全序=数据与字段同 commit 删）；T6 目录改道 `tests/support/`（已存在=共享测试工具之家，新建 tests/helpers/ 被 buy-before-build 驳）；T2 注记升格既有 5 处同值常量性质；全量数字重基线（217 条/1,296 标注/197 文件/lint 28/per-file-ignores 382/175 commits））｜ **系列**：架构复审批次 A ｜ **状态**：Design（r3，Revised 2026-11-15） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #7/#12/#22/#27 卡（母报告未入库，spec 自带亲验锚点为主证据）；亲验（r3 重基线）：`_tool_hashes` 恰 **217** 条（tests/tiers/deps.json:205-422，占 443 行文件 ~49%）；`grep -rn "_tool_hashes" src/` 仅 g0.py 注释（:187/:235）；G7 全文无工具哈希使用（347 行 0 命中，唯一 tamper 面是 :338 trace audit）；`pytest.mark.slow` 全仓 0 使用；deps.json **175** commits 中近 10 条 **10/10 全部**同批触 src/

**触及的不变量维度**：无（测试/CI 基建）

---

## 0. 根因

**数据冒充检查**：`_tool_hashes` 的 217 条哈希零运行时决策消费者——唯一验证者是 R3 lint（`lint_registry_reconcile.py:420-437` face + docstring :23-25 + main 接线 :492），它从**同一工作树**重算哈希与自身比较：src 任意编辑 → 必须重跑 `lock-tool-hashes.sh` → 200 行 diff 才能过 check。信息量为零，审查 locality 毁灭（真正手工的 prerequisite 行淹没在哈希海）。
**备选案已评估并否决**：单组合摘要 + G0 消费（「验轮次内工具未漂」）——该需求未被提出，为记录找消费者属反向工程；未来若需轮次可复现性，G0.14 校准哈希模式可再扩（届时另立 spec）。
**r3 关键更正（脚本双职）**：`tests/lock-tool-hashes.sh` 是双职脚本——前半（:10-30）锁 `_tool_hashes`（删除对象），后半（:34-59）锁 `_calibration_hashes.combined`（**G0.14 运行时消费物**，g0.py:221 读取、:218/:232/:251 三条 must_fix 指回本脚本 re-lock，且全仓无其他 writer）。T1 因此**不能整删脚本**：瘦身为 calibration-only（改名），G0.14 的 re-lock 途径原样保留（must_fix 串仅换脚本名，语义不变）。

其余三处同根（**r3 重基线**）：`unit` 标记 **1,296 处/197 文件**（r2.2 记 1,153/161，两周 +143/+36 持续增长）；收集总数与分腿耗时 plan 期重测（r2.2 的 5,974/1,898/21.95s/19.30s 为当时快照）；`--cov-fail-under=85` 四拷（justfile:61 / pre-push-check.sh:73 / nightly.yml:43 / pyproject:601）+ hook 缺 `--hypothesis-profile=ci`（dev 100 例 vs CI 1000 例——property 测试可过 hook 败 CI）+ hook 只跑 5/28 lint 却独有 pip-audit（lint 总数 r3 实测 28 条：27 条 `uv run python tools/` + `just lint-contracts`；r2.2 记 21）；沉积目录/幻影配置/孪生目录/**382 行** per-file-ignores（r2.2 记 ~300）。

## 1. 任务分解

### T1 · `_tool_hashes` 整删（**r3：脚本拆双职，calibration 半段保留**）
- **删**：deps.json `_tool_hashes` 块（217 条，:205-422）、R3 face（lint_registry_reconcile:420-437 + docstring :23-25 + main 接线 :492）、`lock-tool-hashes.sh` **前半段**（:10-30 工具哈希锁）；
- **留（r3 改道核心）**：脚本瘦身为 calibration-only 并**改名 `tests/lock-calibration-hash.sh`**（保留 :34-59 calibration 段）；`_calibration_hashes` 键、deps.py `calibration_hashes` 字段（:64）、G0.14 检查逻辑**原样保留**——g0.py 三条 must_fix 串（**现 :218/:232/:251**）仅换脚本名（语义不变：G0.14 的 re-lock 途径保留）；g0.py 注释两处措辞改（:187 「Mirrors the existing `_tool_hashes` integrity pattern」、:235 「envelope used by `_tool_hashes`」——envelope 接受逻辑保留，仅去 `_tool_hashes` 措辞）；justfile:56 shellcheck 列表换名；
- **连带测试（r2.2 补全，r3 行号校准）**：`tests/unit/test_lint_registry_reconcile.py` **两个** R3 用例（**~:168-179、:181-197**）、`tests/unit/gates/test_g0_calibration_hash.py` **:37**（`_write_deps` fixture 基底 `{"_tool_hashes": {}}` 行——改基底）与 **:86/:109**（断言 must_fix 含 `lock-tool-hashes.sh` 串——**换新脚本名**，测试本身保留：它是 G0.14 calibration 域断言非工具哈希域）、`tests/unit/contracts/schemas/test_deps.py:68`（`d.tool_hashes` 断言）、**:106**（roundtrip 里 `"_tool_hashes": {...}`）与 **:149**（`test_deps_doc_defaults` 断言 `d.tool_hashes == {}`）；
- **活文档（r2.2 补，r3 更正处置）**：`goal-prompt.md:28/:88`、`command-to-give.md:24` 同批改——:88 还谎称 G0.13/G7.17 校验工具哈希（G0.13 实为 independence markers [g0.py:161]，G7.17 全仓不存在）；:24 的正确文案指向**新脚本名**（calibration re-lock 真实存在）而非 just generate；
- `contracts/schemas/deps.py:62` 删除 `tool_hashes` 字段——**定序勘误（r3）：`extra:forbid` 下唯一安全序=数据键与 schema 字段同 commit 删**（字段先删而数据键在 → DepsDoc 解析 ValidationError；「或反之」不成立）。
**判据**：`grep -rn "_tool_hashes" . --include="*.py" --include="*.json" --include="*.sh" --include="*.md" --include="justfile" --exclude-dir=tests/fixtures --exclude-dir=docs/superpowers/plans --exclude-dir=docs/superpowers/specs --exclude-dir=docs/superpowers/audit-runs` 零（**r3 补排除面 audit-runs：40 个历史审计文件含字面量，as-written 恒红**）；`grep -rn "lock-tool-hashes" .`（同排除面）零（**改名后旧名消亡**；新名 `lock-calibration-hash` 的命中为合法保留面）。活文档 goal-prompt/command-to-give 不排除，须同批改。
**文件目标**：deps.json <230 行；**演练验收**：改任一 src 文件 → deps.json diff 恰 0 行。

### T2 · 类型化单装载 + REPO_ROOT
- `contracts/schemas/deps.py` 增 `load_deps(repo_root) -> DepsDoc` 单装载；src 内 6 个读者（phase_runner.py:**38-51**（同名 `load_deps()` 返回 Any——**须改薄包装/删除**，否则两个 loader 静默分叉）/ scoring.py:**286** / g5.py:84 / g6.py:41 / g0.py:**178**（:797 是传 path 的调用点）/ sync_contracts.py:29+**180**）——另 3 个 tools 读者（lint_routing_faces:45 / lint_repo_consistency:**244** / lint_registry_reconcile `_deps` def **:137**、调用点 :187/:206/:234/:422/:452——r3 勘误：r2.2 引的 :166 是 R1 master.json 非deps 读者）显式列入或排除；
- `shenbi/paths.py` 出 `REPO_ROOT` 常量替换三种深度 parents[2]/[3]/[4]（7 个代码点：phase_runner:34 / gates/shared:31 / dispatch_helper:87 / g0_purity:105 / plugins/generate:22 / modes/codex:283 / scoring.py:286；codex.py:282 是注释另计）。**r3 注记（buy-before-build 裁定）**：仓内已有 5 处同值常量（shared.PROJECT:31 / dispatch_helper._PROJECT_ROOT:87 / generate.REPO_ROOT:22 / sync_contracts.PROJECT:29 / codex 局部 :283）——本 task 性质是**升格既有常量至单源**（收敛 5 处重复到 paths.py 一处），非新建平行常量；plan 期列 5 处换装点。
**判据**：`grep -rn "parents\[[234]\]" src/shenbi/ | grep -v paths.py` 零。

### T3 · 标记退役 + 快路重定义（test 与 test-all 合并）——**r2.2 重写：现文不可执行；r3 数字重基线**
**实测阻断**：`--strict-markers`（pyproject.toml:**577**，markers 注册 :583）+ **1,296 处** `pytest.mark.unit`（**197 文件**，r3 实测）→ 删 marker 定义即**全仓收集 ERROR**（`pytest --collect-only -o 'markers=slow: x'` 已复现），「随触碰消退」物理不可能（消退期间每天 `just check` 红）。**三选一，plan 期定**：
- **(a) 最小风险**：保留 `unit` 注册，只合并配方（`test` = `-m "not last" --no-cov`，`test-all` 删），marker 与 1,296 处标注留作历史；
- **(b) 推荐**：同批脚本清扫 1,296 处标注（`tests/` 下按文件批量去 `@pytest.mark.unit`/`pytestmark` 项），marker 定义与标注一起删——机械、可验证（r3 驳斥复核确认：tests 内无 marker 计数/注册断言，唯一钉子是 justfile 注入测试）；
- **(c) 路径选择**：`-m "unit"` 改为路径参数（`tests/unit` 等），marker 与标注同批删——需先确认 `-m unit` 用例集与路径集完全重合（不重合则漏选；plan 期实测收集数）。
`slow` 零使用可直接删。`test-all` 删需同步 `tests/test_justfile_injection.py` EXPECTED_CALLS 表（**现 :92/:93** 钉 `"test"`/`"test-all"` 两键）；**CI 无 `just test` 引用（r3 复跑 grep 仍零），「CI workflows 同步」降级为「无引用，仅更新文档」**。
**判据（r3 重定）**：`just test` 收集数 == plan 期实测基线（not last 全量）；耗时 <60s；`--strict-markers` 下收集零 ERROR。

### T4 · 阈值单源 + hook 构造性子集
- `--cov-fail-under` 只活 pyproject `fail_under`（:601）；justfile:61 / pre-push-check.sh:73 / nightly.yml:43 三拷删；
- justfile 拆子配方 `just lint`（**r3 实测 28 条**：27 条 `uv run python tools/` + `just lint-contracts`——含 #90/#91 期间新增的 lint_gate_status_comparisons 等；ruff/format 同层）/ `just type`（mypy+basedpyright+shellcheck）/ `just test-ci`（两段 pytest + module-coverage）；`check` 依赖三者；CI 可分层跑（lint 单独 retry 不拖类型检查）；
- pre-push-check.sh 改调 just 子配方（**构造性子集**，非手抄旗标）+ 补 `--hypothesis-profile=ci`；pip-audit 差异显式二选一（plan 裁决：hook 删或以 just 面新增）。

### T5 · 沉积清除
- `git rm -r tests/skill-behavior tests/skill-triggering`（六月迁移后「留参考」，零消费者；ARCHIVE-MIGRATED.md 保留——其映射目标在 tiers/t1-skill/ 仍有效）；
- norecursedirs 三处清理（亲验：`tests/dispatcher` **幻影** + 上述**同批删除**的两目录——r2.2 措辞更正：不是「已删」）；
- `tests/unit/contract/`（2 文件）并入 `tests/unit/contracts/`；
- per-file-ignores **382 行**（r3 实测，:123-504）整并为目录级规则（整并判据=规则集完全同体，个别独有规则保留独立行）。

### T6 · dispatch 输出构造器（渐进，不凑数）
`tests/support/dispatch_payload.py`（**r3 改道：落既有 `tests/support/`**——共享测试工具既定之家（capability_fs.py 先例），新建 tests/helpers/ 被 buy-before-build 驳）：`file_block(path, body)` + 常用技能输出构造器（conftest `seed_genesis_outputs` 先例）；**首批换装 5 个最高频文件**——按「文件内 `===...===` 构造块数 + 手写 dispatch 字典数」排序取前 5，plan 期列文件名（r3 探针：`===` 构造面最高 tests/unit/pipeline/test_scene_splitter.py ~10 处）；其余随触碰渐进（历史教训是缺构造器，不是欠一次性大迁移）。

## 2. 验收

1. T1 两判据零（`_tool_hashes` 全排除面零 + 旧脚本名零；新名 `lock-calibration-hash.sh` 为合法保留面）+ 演练 diff=0 + **G0.14 calibration 链路存活**（`pytest tests/unit/gates/test_g0_calibration_hash.py` 绿——换名后断言仍过）；
2. T2 两判据零；
3. `just test` 单命令 == plan 期实测基线（not last 全量）且 <60s；`--strict-markers` 下收集零 ERROR；`grep -rn "cov-fail-under"` 零；
4. hook ⊆ check 构造性（测试或 lint 面断言两者旗标集差为空，pip-audit 例外显式注记）；
5. `just check` exit 0；`just lint` 单跑 <3min。

## 3. 风险

- 删 per-file-ignores 若误合独有规则 → ruff 红（红测即守门）；
- **T1 字段删除定序（r3 钉死）：数据键与 schema 字段同 commit 删**（extra:forbid 下字段先行=ValidationError；数据先行单 commit=lint_registry_reconcile R3 face 尚存时会红）；
- **T1 脚本改名换装面**：g0.py 三串+测试两断言+justfile:56+活文档三处同 commit 换名，漏一处即 grep 判据红（判据即守门）；
- CI workflow 引用面同步（ci.yml/nightly.yml 中 just 调用）。
