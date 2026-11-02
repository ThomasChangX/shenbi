# Spec #92 · 测试与门禁管线卫生（test-ci-hygiene）：deps.json 哈希块**删除**、标记退役、阈值单源、hook 构造性子集

**日期**：2026-11-01（r2 修订 2026-11-02：`_tool_hashes` 由「坍缩为单摘要」改判**整删**——亲验确认 G7 不使用它、唯一消费者是 R3 自洽检查；连带测试处置列全）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #7/#12/#22/#27 卡；亲验：`_tool_hashes` 恰 216 条（deps.json:205-422，占 442 行文件 49%）；`grep -rn "_tool_hashes" src/` 仅 g0.py:152/:200 **注释**；G7 全文无工具哈希使用（唯一 tamper 面是 :338 trace audit）；`pytest.mark.slow` 全仓 0 使用；deps.json 156 commits 中 88% 同批触 src/

**触及的不变量维度**：无（测试/CI 基建）

---

## 0. 根因

**数据冒充检查**：`_tool_hashes` 的 216 条哈希零运行时决策消费者——唯一验证者是 R3 lint（`lint_registry_reconcile.py:481-500`），它从**同一工作树**重算哈希与自身比较：src 任意编辑 → 必须重跑 `lock-tool-hashes.sh` → 200 行 diff 才能过 check。信息量为零，审查 locality 毁灭（真正手工的 prerequisite 行淹没在哈希海）。
**备选案已评估并否决**：单组合摘要 + G0 消费（「验轮次内工具未漂」）——该需求未被提出，为记录找消费者属反向工程；未来若需轮次可复现性，G0.14 校准哈希模式可再扩（届时另立 spec）。

其余三处同根：`unit` 标记把 5,962 测试切 32%/68% 而全量实测 25.0s（买 11 秒付持续惊讶因子）；`--cov-fail-under=85` 四拷 + hook 缺 `--hypothesis-profile=ci`（dev 100 例 vs CI 1000 例——property 测试可过 hook 败 CI）+ hook 跳 18/23 lint 却独有 pip-audit；沉积目录/幻影配置/孪生目录/300 行 per-file-ignores。

## 1. 任务分解

### T1 · `_tool_hashes` 整删
- 删 deps.json `_tool_hashes` 块（216 条）、`tests/lock-tool-hashes.sh`、R3 face（lint_registry_reconcile:481-500 + docstring :23-25）；
- **连带测试三处（已亲验）**：`tests/unit/test_lint_registry_reconcile.py:173-191`（stale 检测用例删）、`tests/unit/gates/test_g0_calibration_hash.py:37`（fixture 构造中的空 `_tool_hashes` 键删）、`tests/unit/contracts/schemas/test_deps.py:68`（`d.tool_hashes` 断言删）；
- `contracts/schemas/deps.py:62` 删除 `tool_hashes` 字段（`extra:forbid` 下应与数据同步——先删数据再删字段或反之，plan 定序）；
- justfile `check` 中若引用该脚本则同步删。
**判据**：`grep -rn "_tool_hashes\|lock-tool-hashes" . --include="*.py" --include="*.json" --include="*.sh" --include="justfile"` 零（排除 git 历史）。
**文件目标**：<230 行；**演练验收**：改任一 src 文件 → deps.json diff 恰 0 行。

### T2 · 类型化单装载 + REPO_ROOT
- `contracts/schemas/deps.py` 增 `load_deps(repo_root) -> DepsDoc` 单装载；七裸读者（phase_runner.py:33-53 / scoring.py:286 / g5.py:84 / g6.py:40 / g0.py:773 / sync_contracts.py:29）换装（DepsDoc 由「仅测试消费」转正）；
- `shenbi/paths.py` 出 `REPO_ROOT` 常量替换三种深度 parents[2]/[3]/[4]（phase_runner:33 / gates/shared:26 / dispatch_helper:94 / g0_purity:105 / plugins/generate:22 / modes/codex:282）。
**判据**：`grep -rn "parents\[[234]\]" src/shenbi/ | grep -v paths.py` 零。

### T3 · 标记退役 + 快路重定义（test 与 test-all 合并）
亲验：`just test` = `-m "unit"`；`just test-all` = `-m "not last"`——合并为 `test`（`-m "not last" --no-cov`），`test-all` 删（同义）；`unit`/`slow` markers 定义删（slow 零使用；unit 的 1118 处标注随触碰消退，**不做一次性清扫**）；CI workflows 对 `just test` 的引用同步。
**判据**：`just test` 收集数 == 全量 not last；耗时 <60s。

### T4 · 阈值单源 + hook 构造性子集
- `--cov-fail-under` 只活 pyproject `fail_under`；justfile:54 / pre-push-check.sh:73 / nightly.yml:43 三拷删；
- justfile 拆子配方 `just lint`（20 lint + ruff/format）/ `just type`（mypy+basedpyright+shellcheck）/ `just test-ci`（两段 pytest + module-coverage）；`check` 依赖三者；CI 可分层跑（lint 单独 retry 不拖类型检查）；
- pre-push-check.sh 改调 just 子配方（**构造性子集**，非手抄旗标）+ 补 `--hypothesis-profile=ci`；pip-audit 差异显式二选一（plan 裁决：hook 删或以 just 面新增）。

### T5 · 沉积清除
- `git rm -r tests/skill-behavior tests/skill-triggering`（六月迁移后「留参考」，零消费者；ARCHIVE-MIGRATED.md 指 git 历史）；
- norecursedirs 三处清理（亲验：`tests/dispatcher` **幻影**、两个已删目录）；
- `tests/unit/contract/`（2 文件）并入 `tests/unit/contracts/`；
- per-file-ignores ~300 行整并为目录级规则（整并判据=规则集完全同体，个别独有规则保留独立行）。

### T6 · dispatch 输出构造器（渐进，不凑数）
`tests/helpers/dispatch_payload.py`：`file_block(path, body)` + 常用技能输出构造器（conftest `seed_genesis_outputs` 先例）；**首批换装 5 个最高频文件**，其余随触碰渐进（历史教训是缺构造器，不是欠一次性大迁移）。

## 2. 验收

1. T1 判据零 + 演练 diff=0；
2. T2 两判据零；
3. `just test` 单命令 == 全量 not last 且 <60s；`grep -rn "cov-fail-under"` 零；
4. hook ⊆ check 构造性（测试或 lint 面断言两者旗标集差为空，pip-audit 例外显式注记）；
5. `just check` exit 0；`just lint` 单跑 <3min。

## 3. 风险

- 删 per-file-ignores 若误合独有规则 → ruff 红（红测即守门）；
- T1 字段删除与 deps schema `extra:forbid` 的先后序由 plan 钉（建议同 commit）；
- CI workflow 引用面同步（ci.yml/nightly.yml 中 just 调用）。
