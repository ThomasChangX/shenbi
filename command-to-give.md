在 /Users/xiaotiac/Documents/GitHub/shenbi 根目录，按 docs/superpowers/plans/2026-06-11-test-framework.md 执行测试轮次。

> **Quick reference**: All commands have `just` shortcuts. Run `just --list` for the full list. Key commands: `just check`, `just test`, `just gate G0 <seed>`, `just dispatch <skill> <type> <round> <prompt>`.

## 可靠性边界

**在这个边界内，框架输出可信。边界外不承诺。**

1. **Fixtures = 项目源文件的精确副本。** `outline-example.md` 修改后必须同步到 `tests/fixtures/`。G0.11 检查哈希一致性。
2. **Gate 链不可跳过。** G0 阻断 = 必须解决并重新 G0 通过后才能 dispatch。G2 失败 = 输出不合格。G4 失败 = 结构不合格。Gate 失败不评分。
3. **Skill 输入只能是 fixture。** 所有路径以 `tests/fixtures/` 开头。G0.9 检查。违反 → G0 阻断。
4. **同一 fixtures + 同一 skills = 确定性输出。** 每次重跑可对比。

## 执行协议（不可跳过任何步骤）

### 第一步：创建 Round

```bash
bash tests/round-exec.sh claude T1
```

输出包含 G0 结果。G0 通过 → 继续第二步。G0 失败 → 按 G0 输出的 `must_fix` 逐条修复，重新运行 G0。**G0 不通过不 dispatch 任何 skill。**

**注意**：修改 validate-gate.py / scoring.py / phase-runner.py / summarize-round.py 后，必须运行 `bash tests/lock-tool-hashes.sh` 更新 `deps.json` 中的 SHA256 锁定值，否则 G0.13 阻断。

### 第二步：确认进度

运行 `uv run shenbi-progress validate <round_dir>` 验证 progress.json 内部一致性。对于本轮计划测试的 skill，检查 scores 目录是否有已有分数。≥94 的 skill 不重跑。**跳过 skill 的唯一依据是已有分数 ≥94。不存在其他跳过理由。**

### 第三步：按 skill 列表执行

对每个待测试 skill，按 generative → bug-hunt → clean 顺序。三个测试类型每个必须独立执行和评分。

**中断规则：同一类 gate 失败模式出现 ≥3 次，立即暂停，先修根因再继续。禁止对同一类问题逐个打补丁超过 2 次。**

- G2.5（frontmatter 缺失）出现在 ≥3 个不同 skill → 暂停，修改 G2.5 规则或修改 SKILL.md 模板
- G4 同一 checker 在同一字段上失败 ≥3 次 → 暂停，对齐 SKILL.md 与 G4 checker
- 评分 subagent JSON 格式问题 ≥3 次 → 暂停，修复 scoring.py 或评分 dispatch 指令
- 场景引用不存在的 fixture ≥3 次 → 暂停，生成缺失 fixture 或修改场景

暂停后修复的是**源头**（SKILL.md / G4 checker / scoring.py / fixture），不是逐个改输出文件。

**Generative 协议**:
1. 读 `tests/tiers/t1-skill/<skill>/generative/input/scenario.md`
2. 读 `skills/<skill>/SKILL.md`
3. 执行 skill。输出到 `skill-output/<skill>/`
4. 跑 `uv run shenbi-validate G2 <files> <FILE_TYPE> <round_dir>`（FILE_TYPE 从 skill 推导：chapter-drafting/style-polishing → `chapter`，state-settling/foreshadowing → `truth`，其余默认 `chapter`）
5. 跑 `uv run shenbi-validate G4 <skill> <files> <round_dir>`
6. **只在 G2 和 G4 都通过后**，新开独立 subagent 评分（使用 `bash tests/dispatch-subagent.sh <skill> generative <round_dir> "<prompt>"`）。**Dispatcher 不得评分。** 评分 subagent 只接收 rubric 路径和输出文件路径，不接收生成过程上下文。评分 subagent 的输出格式必须是：`{"1": 90, "2": 85, ...}`（仅整数键映射到 0-100 分数，无其他字段）。
7. 跑 `uv run shenbi-score <rubric> <scores.json> --test-type generative`
   - **scoring.py 退出的四种状态**：
     - 0 = 评分计算成功，结果写入 stdout。Dispatcher 将 stdout 保存到 `t1-reports/<skill>-generative-scores.json`
     - 2 = 评分验证失败（dimensions 为空、缺失维度、分数越界）。**必须重新 dispatch 评分 subagent**（最多 2 次，每次使用新 subagent 实例）。3 次都失败 → 记录为 0 分并标记 `scoring_reject: true`
     - 3 = Gate marker 缺失（`MARKER_MISSING`）。**必须先运行 G4/G6 gate 并生成 marker 文件，再评分。**
     - 1 = 其他错误，排查后重试
   - **分片规则**：输出文件总大小 > 20000 字时，将输出文件拆分为 N 组（每组 ≤ 15000 字），每组独立 dispatch 评分 subagent。最终每个维度的分数取各组最低分（conservative merge）。
8. 分数记录到 `t1-reports/<skill>-generative-scores.json`

**Bug-Hunt 协议**:
1. 读 `tests/tiers/t1-skill/<skill>/bug-hunt/input/scenario.md`
2. 复制 generative 产出到 `skill-output/<skill>-bughunt/`
3. 按 scenario 描述向副本注入缺陷
4. 运行 skill 的 review 模式检测缺陷
5. 报告写到 `skill-output/<skill>-bughunt/bug-hunt-report.md`。**报告必须包含**：缺陷是否检出、检出位置(文件+行号)、违反的 SKILL.md 规则名、引用证据
6. 新开 subagent 评分。评分 subagent 输出格式：`{"1": 90, "2": 85, ...}`（仅整数键）。kill switch：未检出 planted defect → 0。证据缺行号 → 0。规则名错误 → 0。跑 `uv run shenbi-score <rubric> <scores.json> --test-type bug-hunt`，验证规则同 generative。

**Clean 协议**:
1. 读 `tests/tiers/t1-skill/<skill>/clean/input/scenario.md`
2. 复制 generative 产出到 `skill-output/<skill>-clean/`
3. 运行 review 模式（输入无缺陷）
4. 报告写到 `skill-output/<skill>-clean/clean-report.md`。**报告必须包含**：逐文件确认、零问题声明
5. 新开 subagent 评分。评分 subagent 输出格式：`{"1": 90, "2": 85, ...}`（仅整数键）。kill switch：任何幻觉缺陷 → 0。"改进建议" = 幻觉缺陷。跳过文件 → 输出完整性 0。跑 `uv run shenbi-score <rubric> <scores.json> --test-type clean`，验证规则同 generative。

### 第四步：增强

分数 < 94 的 skill：
1. 读评分报告，定位扣分维度
2. 区分根因类型：
   - SKILL.md 缺少精确输出模板 → 修改 SKILL.md，加模板
   - Rubric 与 SKILL.md 矛盾 → 修改 rubric 对齐 SKILL.md
   - 输出内容缺陷（数学错误/缺失章节/假数据）→ 重新执行 skill
3. 修复后重新评分。循环直到 ≥ 94。

### 第五步：推进

**全部 59 个 skill 的 generative、bug-hunt、clean 均 ≥ 94 → 开始 T2。**
在此之前不进入 T2。T2 的推进门槛同样是 94。

### 第六步：T2 Phase 执行

全部 T1 skill ≥ 94 后，对每个 T2 phase 按 deps.json 顺序执行：

```bash
# 1. 启动 phase（运行 G5）
uv run shenbi-phase start <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output

# 2. 对每个 prerequisite skill：
uv run shenbi-phase pre-skill <phase> <skill> --round-dir <round-dir>
#    读 skills/<skill>/SKILL.md，执行 skill，输出到 <round-dir>/project-output/
uv run shenbi-phase post-skill <phase> <skill> --round-dir <round-dir> --project-dir <round-dir>/project-output

# 3. 确认所有 skill 完成并评分
uv run shenbi-phase pre-score <phase> --round-dir <round-dir>
# 4. 独立 subagent 评分（Dispatcher 不得评分）
uv run shenbi-score tests/tiers/t2-phase/<phase>/rubric.md <score-file> --test-type generative --round-dir <round-dir>
# 5. 记录分数
uv run shenbi-phase post-score <phase> <score-file> --round-dir <round-dir>
# 6. 封存
uv run shenbi-phase finalize <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output
```

**phase-runner.py 每个步骤都有前置条件检查。跳过步骤会失败。** 分数 < 94 的 phase 按第四步增强规则处理。

### 第七步：T3 Pipeline 执行

全部 T2 phase ≥ 94 且 finalized 后，对每个 T3 pipeline 执行：

```bash
# 1. 确认 T2 全部 finalized + ≥ 94（从 summary.json 读取）
# 2. 运行 G6
uv run shenbi-validate G6 <pipeline> <round-dir> <round-dir>/project-output
# 3. 独立 subagent 评分
uv run shenbi-score tests/tiers/t3-pipeline/<pipeline>/rubric.md <score-file> --test-type generative --round-dir <round-dir>
# 4. 记录到 t3-reports/<pipeline>-generative-scores.json
```

T3 不使用 phase-runner.py。G6 gate marker 是评分的前置条件。

### 每轮结束

```bash
uv run shenbi-summarize <round_dir>
uv run shenbi-validate G7 <round_dir>
bash tests/round-exec.sh --validate <round_dir>
```

## 阈值

- 90 = 单次测试通过
- 94 = tier 推进门槛（一个 skill 的三种测试全部 ≥ 94 该 skill 才算在 tier 内通过）
- 100 = 收敛目标
