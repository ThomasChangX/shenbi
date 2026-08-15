# G6 Meta-Audit — 对审计本身的分层深核（fresh context）

- 轮次: 2026-08-15 全项目深度审查 · 阶段 6
- Agent: G6 meta-audit（独立于全部初审/复核/线程 agent）
- 对象: findings-ledger.md（774 条：F=641 / T=129 / D=4）、progress.md、coverage-ledger.md、zone-reports/、以及被审代码/产物现场
- 铁则遵守: 只读审计（除本报告外零仓库写入；脚本只写 /tmp/g6x/；novel-output 只读；未运行 pytest/dispatch/pipeline；无 git 写操作；全部命令非交互）
- 随机种子: **20260816**（协调者任务书指定）。注: progress.md:21 预登记的 G6 种子为 20260815，与实际执行的 20260816 不一致——两者均为固定种子、可复现，不影响有效性，作为协议注记记录（不立案）

---

## 1. 抽样方法与可复现命令

### 1.1 分层抽样（机械随机，种子 20260816）

```bash
# Z7 区 findings（F7xx 三位编号，grep '^| F7' 会混入非 Z7 项，实际为 88 条而非任务书估计的 ~81）
grep '^| F7' findings-ledger.md | awk -F'|' '{print $2}' | tr -d ' ' > /tmp/g6x/f7_ids.txt   # 88 条
# Z11 区 findings（必须过滤四位编号 F11xx，否则混入 Z1 的 F110-F119；实际 46 条而非任务书估计的 ~40）
grep '^| F11' findings-ledger.md | awk -F'|' '{print $2}' | tr -d ' ' | grep -E '^F11[0-9]{3}$' > /tmp/g6x/f11_ids.txt  # 46 条

python3 - <<'EOF'
import random
f7  = open('/tmp/g6x/f7_ids.txt').read().split()
f11 = [x for x in open('/tmp/g6x/f11_ids.txt').read().split()]
rng = random.Random(20260816)
print(sorted(rng.sample(f7, 31)))    # Z7: 31/88 = 35.2%  (≥35% ✓)
print(sorted(rng.sample(f11, 12)))   # Z11: 12/46 = 26.1% (≥25% ✓)
EOF
```

- **Z7 实抽 31/88 = 35.2%**（下限 35% 满足）：F702 F703 F708 F715 F717 F718 F719 F726 F729 F732 F735 F741 F743 F744 F748 F751 F752 F754 F755 F756 F758 F759 F765 F767 F769 F770 F776 F778 F779 F792 F797
- **Z11 实抽 12/46 = 26.1%**（下限 25% 满足）：F1103 F1105 F1111 F1114 F1152 F1157 F1168 F1171 F1173 F1174 F1176 F1177

### 1.2 全量类别复演（每个 distinct 类别 1 条，同种子）

```bash
python3 - <<'EOF'
import random, re
rows = {}
for line in open('findings-ledger.md'):
    m = re.match(r'^\| (D\d+|F\d+) \|', line)
    if m:
        parts = [p.strip() for p in line.split('|')]
        rows.setdefault(parts[3], []).append(parts[1])
rng = random.Random(20260816)
for cat in sorted(rows): print(cat, '->', rng.choice(rows[cat]))
EOF
```

类别列共 **20 个 distinct 值**（error 469、漏报 109、optimization 22、deps 18、security 8、docs 4、severity-dispute 2、及 13 个单条类别含复合 error/* 变体）——20 类每类抽 1 条，全覆盖。

### 1.3 每条判定流程

打开该 finding 的 zone-report 原文段 → 提取其证据声称（file:line / 计数 / 实跑输出）→ 打开代码或产物现场独立核验（sed/grep/python 只读；对"实跑声称"条目用只读 python 独立复现）→ 三值判定：**成立 / 不成立 / 证据不足**。

---

## 2. Z7 深核判定表（31/88 = 35.2%）

判定口径：成立 = 核心声称全部或实质全部在现场证实；括注 = 证据细节缺陷（不推翻核心）。

| ID | 判定 | 依据（一句话） |
|---|---|---|
| F702 | 成立 | test_scoring.py:434-441 `or True` 逐字在案，恒真断言坐实 |
| F703 | 成立 | test_review_checklist.py:209 `assert len(result) >= 0` 原样在案 |
| F708 | 成立 | g5.py:153 正则单捕获组 + :159 `m.group(2)` 必然 IndexError + 宽 except 吞掉，G5.3 死代码链完整 |
| F715 | 成立 | test_plugins_generate.py:63-68 手工保存/恢复无 try-finally，测试名与 FileNotFoundError 分支名不副实 |
| F717 | 成立 | d1-06 日志五项覆盖率（memory_distill 12%/sync_contracts 56%/audit_context_cache 54%/baseline 19%/safe_write 66%/score_* 69-80%）逐项核对一致 |
| F718 | 成立 | test_phase_runner_property.py:48-52 `seed` 形参在函数体零使用 |
| F719 | 成立 | test_field_filtering.py docstring 声称 dispatch_helper 集成，但 `dispatch_helper` 仅出现在 docstring、import 全来自 contracts.fields |
| F726 | 成立（实跑复现） | 独立只读复现：`_should_skip_audit('dialogue', 扁平形状)=False` vs `(嵌套形状)=True`——生产喂扁平、测试喂嵌套，级联永不触发的声称精确复现 |
| F729 | 成立 | test_dispatch_helper_keys.py:40-42 同一 helper 同参双调后断言相等（x==x），注入块不在测试路径 |
| F732 | 成立 | `_require_mlc` skip 守卫 + nightly.yml:19 `# schedule:` 注释禁用 + 每文件 spawn 子进程三要素在案 |
| F735 | 成立 | test_crash_recovery.py:145-149 零断言；:151-158 mock `state.save` 而生产（crash_recovery.py:124-127）调用模块级 `save_state` |
| F741 | 成立 | tests/golden/ 仅含 README.md；README 描述的 chapter-N-original/scores/calibration-report 全不存在 |
| F743 | 成立 | state.py 校验只查空值/越界；测试夹具 current_step='shenbi-chapter-drafting'+step_index=4，而 CHAPTER_STEPS[0基4]='pipeline-post-draft-extract'，错位对静默通过 |
| F744 | 成立 | 近恒真断言（`"chapter" in str(dict)` 恒真支）+ `_INPUT_MAX_CHARS_PER_FILE` 在测试文件 grep 零命中 |
| F748 | 成立 | test_audit_cascading.py:115 "Wait, 1 from ch1 + 2 from ch2" 草稿注释逐字在案；unknown-skill 分支测试零覆盖（grep 'unknown' 零命中） |
| F751 | 成立 | 五组独立抽验全中：Hard Rule/硬规则 grep=0、chapter-plan 8 节齐全（2/4/6 节在 :28/:70/:97）、novel-example.json 无 time_period、林墨/苏晴/老陈/玉佩 全 0、skills/custom-scene-transition 不存在 |
| F752 | 成立 | location-builder scenario :8-11 四角色全指同一文件、:14 同文件自我矛盾（自引用比较）逐字在案 |
| F754 | 成立 | worldbuilding expected-output.md:7 要求 `world/rules.md` 证据；dispatcher 无 fixture→round 物化机制（grep 零命中） |
| F755 | 成立 | deps.json drafting 前置 9 项 vs seed 6 步，缺的三项（review-resonance/foreshadowing-recall/score-arc）逐一核对一致 |
| F756 | 成立（独立重算） | 独立全量重哈希（剥 sha256: 前缀）：99 条中 ok=33 / 过期=63 / 已删=3，删除文件与 claimed 三文件逐一吻合 |
| F758 | 成立 | 8 个 skill 各仅 1 文件 rubric.md；anchor-curate/escalation-review 的标题仅 Universal/Bespoke 两节（无 kill switch/分档线/applicability） |
| F759 | 成立 | 5 个具名 skills 目录（lifecycle/review-group-*×4）: skills 有目录、t1 无、deps.json 零命中；skills=74 / t1=70(含 _template) |
| F765 | 成立 | `grep -rn book_spine_init tests/ --include=*.py` 零命中；d1-06 显示 77% 且缺行即函数体 |
| F767 | 成立 | 双收 grep 复跑得 8 处（含 F716 已列 2 处），新增 6 处与 finding 清单逐一吻合 |
| F769 | 成立 | docs .md 计数单调增长复证：d1 时 371 → r1 时 390 → 本轮实测 465（+root 9）；增长本身即证明该声称 |
| F770 | 成立 | pyproject.toml:420-423 addopts 全局挂 `--cov=shenbi`；现存 coverage.xml line-rate=21.92% 即部分运行污染实证 |
| F776 | 成立 | 黑石饼/老周/灵能催化剂 novel-output 全树 grep 零命中、命中仅在 calibration+tiers 闭环互引；27 锚点数吻合；README schema "Never invented" 原文在案 |
| F778 | 成立（细节缺陷→G602） | 三文件 sha256 全同 df81acba75e3… ✓；但 "2494 字节" 实为 **2494 字符**（字节 6980）——单位标注错误，不影响同一性结论 |
| F779 | 成立 | manifest.md:7-8 `sha256:abc123`/`sha256:xyz789` 占位符逐字在案 |
| F792 | 成立 | snapshots/ 平铺 51 章+manifest、`find -type d` 仅根；`use_legacy_snapshot=True` 在 tests/ 零命中（唯一 grep 命中为 coverage HTML 生成物） |
| F797 | 成立（独立复算） | 独立统计 pipeline-state: review-anti-ai 旧步名 55 章 / review-group-* 0 章 / intent-management 与 foreshadowing-recall 各 56/56——三个数字精确复现 |

**Z7 结果: 31/31 成立（100%）；0 整条误报；1 条证据细节单位错误（F778，见 G602）。**

## 3. Z11 深核判定表（12/46 = 26.1%）

| ID | 判定 | 依据（一句话） |
|---|---|---|
| F1103 | 成立（1 细节不可复现→G604） | 核心精确复现：revision_count 56/56=0、resonance_score 56/56=null、34 份 revision-decisions 在盘；但 route 分布（21/23/5/6）经 3 种文本抽取策略均无法机械复现（10/34 文件 JSON 不可解析） |
| F1105 | 成立 | resonance_trend.md=316B 仅 ch55 一行；audit_drift.md=850B 仅 1 条目——精确复现 |
| F1111 | 成立（独立复算） | drafting marker files_checked=['chapters/chapter-56.md']（末次覆写）+ revision marker `checks:[]`+PASS + validation-report ch1 G4 FAIL(word_count 2813<3000) 矛盾 + pipeline-manifest 全仓 0——四要素全中 |
| F1114 | 成立（独立复算） | closure=pending/step=0、ch56 9 步 pending、last_snapshot=None vs 磁盘 51 快照、checkpoint_history 2 条 vs 22 marker、ch56 缺 dialogue/motivation/resonance/sensitivity/world-rules 5 审计——全部精确复现 |
| F1152 | 成立 | bridge_tracker 在 truth-files.yaml grep 零命中、在 index.json:631 有条目（reads 空）——登记缺口坐实 |
| F1157 | 成立 | 归档 progress.md :10-21 全 [x]（含 Phase 11 归档）vs :54-62 尾部 8 个未勾选 Phase——自相矛盾残留在案 |
| F1168 | 成立（独立复算） | truth-index.json characters=[relationships, 林烽] 2 条/hooks 7/rules 10；current_state 前排参数 冷/光/安静 全缺席；`_maybe_rebuild_truth_index` 确系 dd1fc62(07-20) 加入晚于运行窗口 |
| F1171 | 成立（抽点+量级复证） | ch35.md:338 META-END 后元叙述尾段逐字在案（38650B）；chapter-23-memo-compliance:97 "请将上述内容写入" 在案；snapshot ch5:2161 在案；独立宽模式集量级复证 62/722 审计+39/51 快照（与 55+37 同量级） |
| F1173 | 成立 | ch49:5/ch51:31 "确定性 helper 无法在只读沙箱中执行…手动计算" vs ch50:26-29 逐字引用 helper CLI JSON 输出；xinghuo 无 trace.jsonl（ls 证实）——三态矛盾+不可裁决成立 |
| F1174 | 成立（夸大细节→G603） | retry_feedback 54 条、resonance 35 条、audit_retry_count 全 0——核心精确复现；但 "must_fix 全部为 no_valid_verdict" 实测 **30/35**（另 5 条为 detail_table 缺置信度/裁判理由、evidence 无 file:line） |
| F1176 | 成立（独立重算） | constants 1067 + patches 13 + unicode 2 + playwright 1 = 1083 独立复算吻合；coverage-ledger 表 B 已按处置落账（见 §5.2） |
| F1177 | 成立（独立复算） | 台账中 F1301/F1302/F1320 唯一命中即 F1177 自身行（此前零承接）；盘上复现：抽查 5 章首 15 行均无 `# Chapter` 头、DEBUG 自称 1226 vs 实测 1229 文件 |

**Z11 结果: 12/12 成立（100%）；0 整条误报；2 条证据细节缺陷（F1174 夸大、F1103 子分布不可机械复现）。**

## 4. 全量类别复演（20/20 类别全覆盖）

| 类别（条数） | 抽中 | 判定 | 依据（一句话） |
|---|---|---|---|
| clean 结构性 (1) | F463 | 成立（实跑复现） | 独立复现 `check_gate_markers(test_type='bug-hunt') → missing=['G4-shenbi-worldbuilding-bug-hunt']`；marker 写方仅 cli.py:121/128 且硬编码 generative |
| dead-wire (1) | F622 | 成立 | 两 CLI 的 main 仅被各自 `__main__.py` 样板与归档 plan 引用，零 skill/生产/测试调用 |
| deps (18) | F844 | 成立 | `skills/_shared/REVIEW_EVIDENCE.md` 不存在而 SKILL.md:94 引用；pacingRules/maxConsecutiveQuest/maxGapQuest 在真实与 fixture genre-config 均零命中（实际键 `pacing`） |
| docs (4) | F336 | 成立 | closure 传字面量 0（cli.py:298-302）而 genesis 传 None 且签名/docstring 明示 None 为"无章上下文"语义 |
| error (469) | F004 | 成立 | justfile 5 个 lint 脚本 vs ci.yml 5 个不同集合；ci.yml 缺 lint_contract_graph/lint_contract_fields 双向确认 |
| error/dead-code (1) | F611 | 成立 | RHETORICAL 定义外零引用（grep exit 1）；TRANSITION_WORDS "与此同时" 重复 2 次 |
| error/docs (1) | F612 | 成立 | preserve_check.py 无 main/__main__ 块，实际 CLI 入口是 `python -m ...revision_routing`（--diagnosis），docstring 的 --original/--regenerated 用法不存在 |
| error/可观测性 (1) | F620 | 成立 | replay.py 全文件零 `log.` 调用，截断 safe_write 静默 |
| error/并发 (1) | F619 | 成立 | compaction.py:50-56 直写 tempfile+os.replace，不经 safe_write flock 锁协议（注释自认 "mirrors" 实为平行实现） |
| error/纯函数性 (1) | F615 | 成立 | cjk.py:100-104 `jieba.add_word(term)` 改全局单例词典 |
| optimization (22) | F784 | 成立 | 4 个抽测词干（arc-example/book-spine-example/world-rules-example/canary-3-chapter-seed）全库引用全 0 |
| security (8) | F1161 | 成立 | .playwright-mcp/console-*.log 含 accounts.google.com OAuth state 参数实测在案 |
| severity-dispute (2) | F772 | 成立（立场条目） | 其讨论对象 F777 实质独立证实（见下） |
| test (1) | F613 | 成立 | d1-06 日志 revision_routing/__main__.py 0% lines 3-17 |
| 修正 (1) | F445 | 成立（独立重算） | checkers 注册表 31 项 - SHORT_MAP 20 项 = 11，缺项清单含 review-arc-payoff/review-resonance——独立重算精确吻合 |
| 文案 (1) | F616 | 成立 | escalation/check.py:149 `print(` 在案 |
| 漏报 (109) | F1033 | 成立 | AGENTS.md "67+2=69" vs 磁盘 skills/ 74 目录实测 |
| 范围补充 (1) | F457 | 成立（实跑复现） | 独立复现 `resolve_input_path('chapters/chapter-1.md', None)` → ValueError；cli.py bughunt/clean 分支确不传 rd |
| 覆盖空洞 (1) | F462 | 成立（聚合条目） | 其聚合的 F445/F457/F458 等子证据链经本抽样独立证实（见本表多行） |
| 跨区备注 (1) | F461 | 成立（行号漂移） | `bash tests/dispatch-subagent.sh` 引用实在（现 :48，审计时 :46——行号漂移 2 行），脚本确实不存在 |

附加（类别复演顺带核实 F777 本体）: chapter-2/5/9-draft.md 三文件均 12825B/150 行同构、全库引用零命中——F777 实质成立，但其 "4503-4504 字节" 同样实为**字符数**（并入 G602）。

**类别复演结果: 20/20 成立（100%）。**

---

## 5. 审计过程完整性核

### 5.1 progress.md 裁决记录 vs ledger 落账（抽检 23 项裁决）

落账成功（19 项）: F306→P2 ✓、F514→P2 ✓、F757→P1 ✓、F710→P1 ✓（续10 补改后）、F318→P1 ✓、F307→P2 ✓、F1104→P1 ✓、F121→P1 ✓、F129→P1 ✓、F007→P2 ✓、阶段4 校准 12 项全部落账（F131/F376/F536/F351/F005/F438/F796→P1 ✓；F355→P2 ✓；F105 维持 P1 ✓）。

**落账失败（4 项，立案 G601）**:

| ID | progress 裁决 | ledger 实际 | 出处 |
|---|---|---|---|
| F340 | 续7 "P0→P2（裁决修正登记）" | **仍 P0** | 续2 曾升 P0（落账✓），续7 降级未落账 |
| F201 | 续6 "降P2 接受"（Z2 复核r1） | **仍 P1** | — |
| F601 | 续6 "降P2 接受"（Z6 复核r1） | **仍 P1** | — |
| F401 | 续7 "降P2 接受"（Z4 复核r1） | **仍 P1** | — |

后果: 以 ledger 机械计数生成的终态数字会**高估 P0×1、P1×3**（progress 续13 自记 P0×12 与 ledger 实际 P0×13 的矛盾即由此来）。根因: 续10 的教训（"裁决必须当场机械验证落账"）只向前生效，未回扫续6/续7 的历史裁决。

### 5.2 coverage-ledger 表 A/表 B 处置完整性

- **表 A**: 2937 数据行，处置列 100% 填充（全部 deep-read），0 畸形行。
- **表 A ↔ git 对账**（独立重算，core.quotepath=off）: tracked 3086 = 表内 2937 + 缺 149；149 条全部为本审计自身产物（111 条 audit-runs/2026-08-15/ 工件 + 38 条阶段5 specs/2026-08-16-*）——均为阶段0 清点之后生成，缺席合理；**表 A 0 条幽灵路径**（A-not-tracked=0）。
- **表 B**: 25 行，处置分布 audited 9 / generated-excluded 2 / cache-ignored 14，与 progress 续5 声称一致。
- **F1176 修正落账验证**: .hypothesis/constants(1067)→cache-ignored（附 28 文件环境完整性备注）、patches(13)→audited(F1169)、unicode_data→cache-ignored——已按 Z11-r2 处置表正确落账 ✓。
- 上轮（2026-08-14）164 个 tracked 审计产物按 DV1 拆分处置在案（coverage-ledger 含 165 处 audit-runs/2026-08-14 引用）。

### 5.3 其他过程观察

- **只读违规事故闭环**（续3）: 续3 记录的 review-checklist-56.json 回写事故有处置（git checkout 恢复）与预防措施（任务书模板加"纯函数验证"约束），且 Z7-r2（续11）证明新约束生效（replay.py safe_write 规避）——闭环真实。
- **F770/F1040 关联**: 我实测现存 tests/coverage/coverage.xml line-rate=21.92%，与续10 记录的"部分运行口径 21.92%"吻合——该污染产物作为证据使用而非隐瞒，诚实。
- **简报触发（774≥300）**已按 $UNATTENDED 语义执行并留档 ✓。

---

## 6. 量化结论

| 指标 | 值 |
|---|---|
| Z7 抽样通过率 | **31/31 = 100%**（35.2% 抽样比） |
| Z11 抽样通过率 | **12/12 = 100%**（26.1% 抽样比） |
| 类别复演通过率 | **20/20 = 100%**（20 类全覆盖） |
| 合计 | **63/63 成立，0 整条误报** |
| 证据细节缺陷率 | 4/63 ≈ 6.3%（G602×1 组 2 处、G603、G604；另有 F461 行号漂移 1 处、F1103 子分布不可复现计入 G604） |
| **全库整条误报率估计** | 点估计 **0%**；95% CI 上界 ≈ 3/63 = **4.8%**（rule of three）→ 按 774 条折算全库完全误报期望 **0–37 条**，且上界偏保守（抽样集中在证据密度最高的 Z7/Z11 复核条目） |
| 实跑声称复现 | F726/F457/F463/F756/F776/F797/F1111/F1114/F1168/F1176/F445 共 11 条含实跑/计数声称的条目全部独立复现成功 |

**审计过程完整性**: 裁决落账抽检 23 项中 4 项未落账（17%）——全部集中于续10 教训生效（续10）之前的续6/续7；其后全部裁决（含阶段4 校准 12 项）100% 落账。覆盖台账表 A/B 完整、无幽灵、修正闭环。

## 7. 元评估结论与限制声明

### 7.1 对"复核轮 17 轮次零完全误报"的评估

**结论: 该声称在我方独立样本中成立且可信。** 依据:
1. 63 条分层独立深核（含全部 17 条 P0/P1 中被抽中的 22 条高严重度样本中的实跑声称 11 项）零整条误报；
2. 审计自身已展示自纠能力并被我方验证有效（F751 转折词计数由 r1 自行修正为 2；F710 落账缺口由续10 自查补改；F1171 由 r2 主动修正 r1 的计数且我方量级复证一致）；
3. 高风险方向（审计者用宽 grep 造数、用 mock 冒充实跑、以推断冒充现场）在我方复现中均未见实例——所有抽中的计数声称（哈希 99/63/3、checkers 31-20=11、retry 54/35、109 污染量级、1083 缺口）独立重算吻合。

**精度注记（不构成推翻）**: "17 轮次"计数口径未在 progress 中定义——zone-reports/ 实有 27 份复核报告（Z1×2/Z2×3/Z3×3/Z4×3/Z5×4/Z6×2/Z7×2/Z8×2/Z9×2/Z10×2/Z11×2）；若按"报告过零误报结论的轮次"或简报撰写时点计数则为 17，属可解释但未注明。

### 7.2 限制声明

1. **抽样偏向**: Z7/Z11 深核集中于测试区与运行时产物区；其余区（Z2/Z3/Z5/Z9 等）仅经类别复演各触 1 条。Z2/Z3/Z5 的 P0/P1（如 F224/F360/F529/F531）未逐条深核——若这些区存在系统性误报，本审计检出力有限。
2. **不可机械复现项**: F1103 route 分布、F1171 的 109 精确计数（依赖 agent 的 33 变体模式库）只能做到量级/抽点复证，无法字节级复现。
3. **时点漂移**: 行号级证据存在少量漂移（F461 :46→:48）；被审文件在审计窗口内被本审计自身修改过（docs/ 新增 .md 致 F769 类计数实时变化）——判定均以"核心声称是否在现场成立"为准。
4. **G6 自身**: 单人复核，判定依据已逐条给出但未二次交叉；种子 20260816 与预登记 20260815 不一致（协调者指令优先，见 §0 注记）。

---

## 8. 新立案（G6xx）

### G601 | 4 项裁决降级未落账: F340(P0→P2)/F201(P1→P2)/F601(P1→P2)/F401(P1→P2) — ledger 严重度与 progress 裁决不一致 | process | P1（对审计产物数字的影响面）
- 证据: progress.md 续6（F201/F601 降P2 接受）、续7（F401 降P2 接受；F340 P0→P2 裁决修正登记）vs findings-ledger.md 当前行: F340=P0、F201=P1、F601=P1、F401=P1（本报告 §5.1 表）
- 根因: 续10 教训（裁决必须当场机械验证落账）仅向前生效，续6/续7 历史裁决无回扫
- 影响: final-report 若按 ledger 机械计数将高估 P0×1/P1×3；G7 裁决与阶段5 spec 优先级矩阵（按严重度排序）同受影响——阶段5 的 12 项校准裁决未含这 4 条，非二次改判
- 建议: 终审前按 progress 裁决补改 4 行严重度并机械 recount；或由 G7 显式推翻续6/续7 裁决恢复原级（二选一，须留裁决记录）

### G602 | Z7-d 证据单位系统性标注错误: 字符数被标注为"字节"（F777: 4503-4504 实为字符，字节 12825；F778: 2494 实为字符，字节 6980） | 证据细节 | M
- 证据: `wc -c` 与 `len(text)` 独立复测（F778: bytes=6980/chars=2494；F777 ch2-draft: bytes=12825/chars=4503）；同一 agent（Z7-d）两处同型错误，属系统性而非笔误
- 加重因素: Z7-review-r1 对 F778 的字节数标注为"未验证"而非核查（§3 精度注记 2）——复核轮存在可轻易消除的验证空转
- 影响: 结论不受影响（文件同一性/复制体由哈希独立证实）；但下游若引用"2494 字节"做体量分析会错 ~2.8 倍
- 建议: 终审更正两处单位；复核规则补"量化声称中 length/size 类必须带单位复测"

### G603 | F1174 证据夸大: "must_fix 全部为 no_valid_verdict" 实测 30/35 | 证据细节 | M
- 证据: 独立遍历 retry_feedback 35 条 resonance 条目: 30 条含 no_valid_verdict，5 条为 G4.rr.detail_table（缺 置信度/裁判理由）与 G4.rr.evidence（no_file_line_ref）
- 影响: 核心（35 章首评不合格经重试、audit_retry_count 56/56=0 死字段）不受影响；"全部"措辞会误导读者以为失败模式单一
- 建议: 措辞改"35 条 resonance 重试反馈中 30 条 no_valid_verdict、5 条 detail_table/evidence 格式不合格"

### G604 | F1103 route 分布子声称（no-revision:21/spot-fix:23/constrained-regenerate:5/regenerate:6）不可机械复现 | 证据充分性注记 | M
- 证据: 3 种抽取策略（route 词干/selected 键/mode 正则）均得不出该分布（且 34 文件中 10 个 JSON 不可解析）；核心声称（34 份产物 vs 计数全 0）精确复现
- 影响: 若终审/spec 引用该分布做修订模式分析，需先落一个可复现的抽取脚本
- 建议: 将分布标记为"agent 语义读数，未机械复现"，或补脚本再引用

---

## 9. 总结论

1. **抽样证据支持审计质量结论**: Z7 35.2%、Z11 26.1%、类别 20/20 全覆盖共 63 条深核，整条误报 0，实跑声称 11/11 独立复现——"零完全误报"声称可信，全库整条误报率估计 0%（95% CI 上界 4.8%）。
2. **审计过程存在一处需终审处理的实质缺口**: G601（4 项裁决未落账，影响终态 P0/P1 计数）；其余过程要件（覆盖台账完整性、事故闭环、只读合规、自纠机制）核验通过。
3. **证据质量系统性偏弱项**: 量化声称的单位/全称量词标注（G602/G603/G604，3 条 M 级细节缺陷，均不动摇结论）。
4. G6 通过判定: **有条件通过**——G601 修复（或 G7 显式改判）前，final-report 的 P0/P1 机械计数应以补改后 ledger 为准。
