# Spec #92 · 测试与门禁管线卫生（test-ci-hygiene）：deps.json 哈希块**删除**、标记退役、阈值单源、hook 构造性子集

**日期**：2026-11-01（r2 修订 2026-11-02：`_tool_hashes` 由「坍缩为单摘要」改判**整删**——亲验确认 G7 不使用它、唯一消费者是 R3 自洽检查；连带测试处置列全；**r2.2 2026-11-02 全量对抗式审计修订**——T3 标记退役按现文不可执行（`--strict-markers`+1,153 标注=收集 ERROR，已复现），改三选一；T1 连带清单补两处与 G0.14 文案；数字按实测刷新）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #7/#12/#22/#27 卡；亲验：`_tool_hashes` 恰 216 条（deps.json:205-422，占 442 行文件 49%）；`grep -rn "_tool_hashes" src/` 仅 g0.py:152/:200 **注释**；G7 全文无工具哈希使用（唯一 tamper 面是 :338 trace audit）；`pytest.mark.slow` 全仓 0 使用；deps.json 156 commits 中 88% 同批触 src/

**触及的不变量维度**：无（测试/CI 基建）

---

## 0. 根因

**数据冒充检查**：`_tool_hashes` 的 216 条哈希零运行时决策消费者——唯一验证者是 R3 lint（`lint_registry_reconcile.py:481-500`），它从**同一工作树**重算哈希与自身比较：src 任意编辑 → 必须重跑 `lock-tool-hashes.sh` → 200 行 diff 才能过 check。信息量为零，审查 locality 毁灭（真正手工的 prerequisite 行淹没在哈希海）。
**备选案已评估并否决**：单组合摘要 + G0 消费（「验轮次内工具未漂」）——该需求未被提出，为记录找消费者属反向工程；未来若需轮次可复现性，G0.14 校准哈希模式可再扩（届时另立 spec）。

其余三处同根（**r2.2 按实测刷新**）：`unit` 标记 1,153 处/161 文件（r2 记 1,118）；收集总数 5,974，`-m unit` 1,898（31.8%）；`-m "not last" --no-cov` **21.95s** vs `-m unit --no-cov` **19.30s**——快路只省 **2.7s（12%）却漏 68% 用例**（r2 的「25.0s/省 11s」不可复现；带 coverage 的 pytest 腿 40.36s，`just check` 整体 ~90s 是含 21 个 lint 的整条链，两个口径不得混用）；`--cov-fail-under=85` 四拷 + hook 缺 `--hypothesis-profile=ci`（dev 100 例 vs CI 1000 例——property 测试可过 hook 败 CI）+ hook 跳 18/23 lint 却独有 pip-audit；沉积目录/幻影配置/孪生目录/300 行 per-file-ignores。

## 1. 任务分解

### T1 · `_tool_hashes` 整删
- 删 deps.json `_tool_hashes` 块（216 条）、`tests/lock-tool-hashes.sh`、R3 face（lint_registry_reconcile:481-500 + docstring :23-25）；
- **连带测试（r2.2 补全）**：`tests/unit/test_lint_registry_reconcile.py` **两个** R3 用例（**:168-179、:181-197**）、`tests/unit/gates/test_g0_calibration_hash.py:37`（fixture 空键）与 **:86/:109（断言 must_fix 含 `lock-tool-hashes.sh` 串）**、`tests/unit/contracts/schemas/test_deps.py:68`（`d.tool_hashes` 断言）、**:106**（roundtrip 里 `"_tool_hashes": {...}`，extra:forbid 下删字段即 ValidationError）与 **:149**（`test_deps_doc_defaults` 断言 `d.tool_hashes == {}`——r2.2 复核补）；
- **G0.14 文案与活文档（r2.2 补）**：`g0.py:183/:197/:216` 三条 must_fix 提示串含 `tests/lock-tool-hashes.sh`——删脚本不改提示则判据红+测试红；同批改文案（指向 `just generate`/人工说明）与两处断言；`goal-prompt.md:28/:88`、`command-to-give.md:24` 是**活操作文档**须同步（:88 还谎称 G0.13/G7.17 校验工具哈希——G0.13 是 independence markers、G7 无哈希面）；
- `contracts/schemas/deps.py:62` 删除 `tool_hashes` 字段（`extra:forbid` 下应与数据同步——先删数据再删字段或反之，plan 定序）；
- justfile `check` 中若引用该脚本则同步删。
**判据**：`grep -rn "_tool_hashes\|lock-tool-hashes" . --include="*.py" --include="*.json" --include="*.sh" --include="*.md" --include="justfile" --exclude-dir=tests/fixtures --exclude-dir=docs/superpowers/plans --exclude-dir=docs/superpowers/specs` 零（**r2.2 补排除面**：历史 fixture `tests/fixtures/calibration/README.md:64`、plan 正文与 archive 多处为历史记录；活文档 goal-prompt/command-to-give 不排除，须同批改）。
**文件目标**：<230 行；**演练验收**：改任一 src 文件 → deps.json diff 恰 0 行。

### T2 · 类型化单装载 + REPO_ROOT
- `contracts/schemas/deps.py` 增 `load_deps(repo_root) -> DepsDoc` 单装载；**r2.2 更正：src 内是 6 个读者**（phase_runner.py:**40** / scoring.py:**289** / g5.py:84 / g6.py:40 / g0.py:**178**（:773 是传 path 的调用点）/ sync_contracts.py:**180**（:29 是常量））——另 3 个 tools 读者（lint_routing_faces:45 / lint_repo_consistency:233 / lint_registry_reconcile:166）显式列入或排除；**phase_runner.py:37 已有同名 `load_deps()`（返回 Any）——须改薄包装/删除**，否则两个 loader 静默分叉；
- `shenbi/paths.py` 出 `REPO_ROOT` 常量替换三种深度 parents[2]/[3]/[4]（**r2.2 实测 7 个代码点**：phase_runner:33 / gates/shared:26 / dispatch_helper:94 / g0_purity:105 / plugins/generate:22 / modes/codex:282 / **scoring.py:286**；codex.py:281 是注释另计）。
**判据**：`grep -rn "parents\[[234]\]" src/shenbi/ | grep -v paths.py` 零。

### T3 · 标记退役 + 快路重定义（test 与 test-all 合并）——**r2.2 重写：现文不可执行**
**实测阻断**：`--strict-markers`（pyproject.toml:529）+ **1,153 处** `pytest.mark.unit`（161 文件）→ 删 marker 定义即**全仓收集 ERROR**（`pytest --collect-only -o 'markers=slow: x'` 已复现），「随触碰消退」物理不可能（消退期间每天 `just check` 红）。**三选一，plan 期定**：
- **(a) 最小风险**：保留 `unit` 注册，只合并配方（`test` = `-m "not last" --no-cov`，`test-all` 删），marker 与 1,153 处标注留作历史；
- **(b) 推荐**：同批脚本清扫 1,153 处标注（`tests/` 下按文件批量去 `@pytest.mark.unit`/`pytestmark` 项），marker 定义与标注一起删——机械、可验证；
- **(c) 路径选择**：`-m "unit"` 改为路径参数（`tests/unit` 等），marker 与标注同批删——需先确认 `-m unit` 的 1,898 例与路径集完全重合（不重合则漏选）。
`slow` 零使用可直接删。`test-all` 删需同步 `tests/test_justfile_injection.py:93` 的 pinned 配方表；**CI 无 `just test` 引用（已 grep），「CI workflows 同步」降级为「无引用，仅更新文档」**。
**判据（r2.2 重定）**：`just test` 收集数 == 5,974（not last）；耗时 <60s；`--strict-markers` 下收集零 ERROR。

### T4 · 阈值单源 + hook 构造性子集
- `--cov-fail-under` 只活 pyproject `fail_under`；justfile:54 / pre-push-check.sh:73 / nightly.yml:43 三拷删；
- justfile 拆子配方 `just lint`（**现行 20 条 + #95 T1 新增 1 条 = 21**，ruff/format 同层）/ `just type`（mypy+basedpyright+shellcheck）/ `just test-ci`（两段 pytest + module-coverage）；`check` 依赖三者；CI 可分层跑（lint 单独 retry 不拖类型检查）；
- pre-push-check.sh 改调 just 子配方（**构造性子集**，非手抄旗标）+ 补 `--hypothesis-profile=ci`；pip-audit 差异显式二选一（plan 裁决：hook 删或以 just 面新增）。

### T5 · 沉积清除
- `git rm -r tests/skill-behavior tests/skill-triggering`（六月迁移后「留参考」，零消费者；ARCHIVE-MIGRATED.md 保留——其映射目标在 tiers/t1-skill/ 仍有效）；
- norecursedirs 三处清理（亲验：`tests/dispatcher` **幻影** + 上述**同批删除**的两目录——r2.2 措辞更正：不是「已删」）；
- `tests/unit/contract/`（2 文件）并入 `tests/unit/contracts/`；
- per-file-ignores ~300 行整并为目录级规则（整并判据=规则集完全同体，个别独有规则保留独立行）。

### T6 · dispatch 输出构造器（渐进，不凑数）
`tests/helpers/dispatch_payload.py`（**tests/helpers/ 目录需新建**）：`file_block(path, body)` + 常用技能输出构造器（conftest `seed_genesis_outputs` 先例）；**首批换装 5 个最高频文件**——r2.2 补度量口径：按「文件内 `===...===` 构造块数 + 手写 dispatch 字典数」排序取前 5，plan 期列文件名；其余随触碰渐进（历史教训是缺构造器，不是欠一次性大迁移）。

## 2. 验收

1. T1 判据零 + 演练 diff=0；
2. T2 两判据零；
3. `just test` 单命令 == 全量 not last（**5,974**）且 <60s；`--strict-markers` 下收集零 ERROR；`grep -rn "cov-fail-under"` 零；
4. hook ⊆ check 构造性（测试或 lint 面断言两者旗标集差为空，pip-audit 例外显式注记）；
5. `just check` exit 0；`just lint` 单跑 <3min。

## 3. 风险

- 删 per-file-ignores 若误合独有规则 → ruff 红（红测即守门）；
- T1 字段删除与 deps schema `extra:forbid` 的先后序由 plan 钉（建议同 commit）；
- CI workflow 引用面同步（ci.yml/nightly.yml 中 just 调用）。
