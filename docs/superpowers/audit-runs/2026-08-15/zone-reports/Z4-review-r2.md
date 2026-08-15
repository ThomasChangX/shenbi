# Z4 复核报告（r2，fresh-context）— src/shenbi/gates/

- 复核轮：2026-08-15 全项目深度审查，Z4 区独立复核第 2 轮
- 编号段：F449–F462（初审 F401–F431，r1 F432–F448）
- 本轮角度（连续两轮不复用；r1 已用 词表+声明面对账）：**(a) 引用断链重扫**——checker 代码内全部路径/键/函数引用 vs 实际存在性（chdir/CWD 锚点假设、相对路径锚点、常量引用、progress.json/summary.json 键空间 vs 写入方词表、文件命名族 vs 写入方命名）；**(b) 采样截断检查**——checker 的输出截断/上限逻辑（`[:8]`/`[:15]`/`[:5000]` 等）截断后判定是否仍正确
- 只读约束：仓库零写入；验证脚本在 /tmp/z4r2/，输出实际运行并粘贴；pytest 未执行（禁令）
- 附加对账源（超出 Z4.files 的只读引用，用于写入方面核对）：src/shenbi/trace/materialize.py、src/shenbi/dispatcher/modes/codex.py、src/shenbi/dispatcher/executor.py、src/shenbi/pipeline/dispatch_helper.py、src/shenbi/audit/_shared.py、src/shenbi/scoring.py、tests/round-exec.sh、command-to-give.md、tests/unit/gates/test_g_reconcile.py

## 总体结论

初审与 r1 的全部事实性结论本轮逐条复读**均成立，无误报**。但本轮角度 (a) 命中一个两轮都未扫到的结构性缝隙：**checker 读的 JSON 键空间/文件命名族 vs 框架写入方实际写的键空间/命名族从未对账**。r1 的"调用面对账"只对账了**文件路径**（哪个 checker 收到哪些文件），没有对账**键名与取值词表**（status: "DONE" vs "done"、agent_id vs agent、remaining_bug_hunt vs remaining_{bug-hunt}、*-scores.json vs *-scores-subagent.json、output_files 无写方）。由此产出 2 条新 P1（GR.2 假 FAIL + GR.1 死检查；G3.5 反作弊检查结构性失效）与一批 P2。角度 (b) 的结论：所有 must_fix 列表的**截断均为展示性截断**（判定由未截断集合驱动，判定正确）；真正的风险在**数据采样截断**（`[:8]` 文件、`[:15]` 章、`[:5000]` 字符、`[:10]` 约束）+ g6.py 的**字典序章节排序**使采样系统性偏斜，检测面收窄而 PASS 记录不披露（F459）。

收敛判定：**部分收敛**。核心 checker 面（G0/G2/G4/G5/G6/G7 主路径）经三轮已稳定（本轮重读未推翻任何既有 finding 的事实）；但 checker↔writer 词表缝隙本轮仍产出 P1×2 + P2×8，建议下一轮（如有）仅针对该缝隙做定向收尾，而非再全量重读。

---

## 一、漏报（初审与 r1 均未发现）

### F449 | g_reconcile 状态词表与写入方不匹配：GR.1 恒死检查 + GR.2 对每个可解析报告假 FAIL | 漏报 | P1
- 证据: src/shenbi/gates/g_reconcile.py:40 `td.get("status") == "DONE"`（GR.1）、:61 `td.get("status") != "DONE"`（GR.2）；框架仅有的两个 progress.json 写入方全部写**小写**——src/shenbi/trace/materialize.py:59 `"status": str(payload.get("status", "done"))`、src/shenbi/dispatcher/modes/codex.py:44 `skill_entry[test_type] = {"score": score, "status": "done"}`。叠加 r1 未验证的"-scores 后缀"问题（g_reconcile.py:52-57 的 rsplit 使 candidate_tt="generative-scores"，而写方键为裸 "generative"），GR.2 存在两个独立的假 FAIL 源。测试掩盖：tests/unit/gates/test_g_reconcile.py:57/58/92 手工构造 `"status": "DONE"`（大写）夹具，使词表漂移不可见
- 根因: checker 期望的键值词表与写入方词表从未对账（本轮角度 (a) 的核心命中）；初审把 GR.2 键格式列为"未验证观察"（Z4.md L494），r1 未解决
- 验证: /tmp/z4r2/repro_reconcile.py（以 materialize/codex 写方形态构造 progress.json + 真实命名报告）输出：
  ```
  A writer-shape (done) -> status: FAIL   must_fix: ['GR.2:shenbi-worldbuilding-generative-scores:status=?']
  B uppercase DONE, -scores.json report -> FAIL  must_fix: ['GR.2:...-scores:status=?']      # 后缀问题独立存在
  C uppercase DONE, plain report -> PASS                                               # 两错相消的窄通道
  D done + missing report (GR.1 应 FAIL) -> PASS   must_fix: None                        # GR.1 死检查
  E done(lowercase) + plain report -> FAIL  must_fix: ['GR.2:shenbi-worldbuilding-generative:status=done']  # 纯大小写问题
  ```
  调用面：G_RECONCILE 经 `shenbi-validate G_RECONCILE <round_dir>`（cli.py:135，usage 列表 cli.py:61 含它）对任何框架产出的轮目录运行即复现；src 内无其他调用方（grep 证实）
- 建议方向: 状态比较改大小写不敏感（或对齐 materialize 的 "done"/"skip" 词表）；GR.2 解析时剥 `-scores`/`-scores-subagent` 后缀；夹具改用写方真实形态

### F450 | G3.5 历史 scorer 去重读 `agent_id` 键，唯一写方写 `agent` 键——反作弊检查在框架数据上结构性失效 | 漏报 | P1
- 证据: src/shenbi/gates/g3.py:215 `aid = entry.get("agent_id", "")`；唯一写 scoring_history 的代码 src/shenbi/pipeline/dispatch_helper.py:1985 `"scoring_history": [{"agent": "pipeline-skill-generator", "g2_passed": True}]`（键名 `agent`）。键不匹配 → aid 恒 "" → `if aid:` 恒跳过 → prior_agents 恒空 → G3.5 恒 PASS
- 根因: 同 F449——读方键空间 vs 写方键空间无对账、无门禁
- 验证: /tmp/z4r2/repro_misc.py V3（progress.json 按写方形态写 current_scorer_agent="scorer-A" 且 scoring_history 含 {"agent":"scorer-A"}，G3.5 应 FAIL）输出：
  ```
  V3 G3.5 check (scorer-A already scored; should FAIL): [{'id': 'G3.5', 's': 'PASS', 'note': '0 prior scorers'}] | gate: PASS
  ```
  调用面真实存在：dispatch_helper.py:1990 以子进程跑 `shenbi.gates.cli G3`（管线主路径）
- 建议方向: 读方兼容 `agent`/`agent_id` 两键，或写方补 `agent_id`；加一个"写方形态"回归测试

### F451 | G3.4 的 scorer==生成者比对读取 `agent_trace` 键——全仓库无任何写入方，比对结构性死线 | 漏报 | P2
- 证据: src/shenbi/gates/g3_independence.py:23-27 `agent_trace = progress.get("agent_trace")`（dict 时才比对）；grep 全 src/+tests/（排除读取方与测试）`agent_trace` 写入方为零。fail-closed 半边（无 current_scorer_agent 即 FAIL）仍有效，但"生成 agent == 评分 agent → FAIL"永远不可能触发；且管线写方把 current_scorer_agent 恒写成新鲜 uuid（dispatch_helper.py:1984），检查在管线内是构造性恒 PASS 的"仪式"
- 根因: 与 F450 同根（键空间无写方）
- 验证: `grep -rn "agent_trace" src/ tests/ --include="*.py" --include="*.sh" | grep -v "gates/g3\|test"` → 空输出
- 建议方向: dispatcher 记录 agent_trace[skill]=生成 agent id，或删除该比对并注明仅 fail-closed 生效

### F452 | G3.3 读 `skills[skill].output_files`——无任何写入方，G3.3 生产恒 SKIP（死检查） | 漏报 | P2
- 证据: src/shenbi/gates/g3.py:151-153 `skills.get(skill_name, {}).get("output_files", [])`；全仓库 progress.json 写入方（materialize.py:59、codex.py:44）只写 `{status, score}` 两键，`grep -rn '"output_files"' src/` 仅命中读取方 g3.py:153
- 根因: 同 F449/F450 键空间缝隙；G3.3 "Output files passed G2" 从未真正校验过任何产物
- 验证: `grep -rn "output_files" src/ --include="*.py" | grep -v "gates/\|audit/_shared\|derive_output"` → 仅 phase_runner/executor 的局部变量（不落盘 progress.json）
- 建议方向: 写方补 output_files，或 G3.3 改为直接 derive_output_files 重算（与 G5.5 同源）

### F453 | G0.7 校验 `tests/scoring.py`——该路径不存在（ scorer 已迁至 src/shenbi/scoring.py ），G0.7 恒 WARN 死检查 | 漏报 | P2
- 证据: src/shenbi/gates/g0.py:365-369 `scoring_py = TESTS / "scoring.py"`；`ls tests/scoring.py` → No such file；实际位置 src/shenbi/scoring.py（g3.py:39 `from shenbi.scoring import load_rubric` 证明迁移）。G0.7 的语义是"scoring.py 存在性自检"，现永远 WARN "scoring.py not found"
- 根因: src-layout 迁移后 G0.7 的路径引用未更新（本轮角度 (a)：路径引用 vs 实际存在性）
- 验证: 仓库根实跑 `gate_G0('outline-example.md')` 输出：`G0.7: [{'id': 'G0.7', 's': 'WARN', 'r': 'scoring.py not found'}] | G0 gate status: PASS`
- 建议方向: 改查 src/shenbi/scoring.py（或 import 探测），消除永久 WARN 噪声

### F454 | G0.5b 注释宣称 "block if >20" 但无任何 FAIL 分支——升级条件是永不执行的死意图 | 漏报 | P2
- 证据: src/shenbi/gates/g0.py:309-319：`if rubric_mismatches:` 仅 append WARN（note 字符串含 "block if >20"）；全函数无 `len(rubric_mismatches) > 20` 的 fail 路径。G0.5b 在任何失配数量下都只 WARN
- 根因: 文档化的阻断语义未实现（截断/判定角度的邻近命中：数量阈值只出现在展示文本里）
- 验证: 读码（309-319 无第二个条件分支）
- 建议方向: 实现 >20 FAIL，或删除该 note 措辞

### F455 | GT.1 读 `remaining_{from_phase}`：写方键为 `remaining_bug_hunt`（下划线），标准拼写 "bug-hunt"（连字符）或任何 T2 相位名都取不到键——非空队列也恒 PASS | 漏报 | P2
- 证据: src/shenbi/gates/g_transition.py:47-48 `phase_key = f"remaining_{from_phase}"`；唯一写方 src/shenbi/trace/materialize.py:87-89 写 `remaining_generative` / `remaining_bug_hunt` / `remaining_clean` 三键。from_phase="bug-hunt" → 键 `remaining_bug-hunt` 不存在 → 默认 [] → GT.1 空转 PASS；from_phase 为 T2 相位名（genesis/drafting/management）时键空间同样不存在（写方只写测试类型队列）
- 根因: GT 语义（相位转换）与写方键空间（测试类型队列）从未对齐
- 验证: /tmp/z4r2/repro_misc.py V4 输出：
  ```
  V4 GT with from_phase='bug-hunt' (queue NON-empty): PASS
  V4b GT with from_phase='bug_hunt' (underscore): FAIL
  ```
- 建议方向: 归一化 phase 名（hyphen↔underscore）或键空间单源化

### F456 | gate_G2 接受 rd 参数但从不用于相对路径解析（G2.1 假 FAIL；G2.11 的 .bak 锚定 CWD） | 漏报 | P2
- 证据: src/shenbi/gates/g2.py:50-51 `for fp in fps: p = Path(fp)`（无 resolve_input_path）；rd 仅在 G2.11 用作进入条件（g2.py:290），且 `bak = Path(bak_path(fp))`（g2.py:291）= fp+".bak" 相对路径锚定 CWD。对照：G4 侧有 resolve_input_path(fp, rd)（shared.py:58-75，Task 15b 明确移除 CWD 回退），G2 未跟进。文档化调用形态存在：cli.py:65 用法示例即相对路径；command-to-give.md:46 `shenbi-validate G2 <files> <FILE_TYPE> <round_dir>`
- 根因: Task 15b 的 CWD 回退移除只在 G4 侧落地；G2 的 rd 参数成为"接受的死参数"
- 验证: /tmp/z4r2/repro_misc.py V2 输出（文件实际存在于 rd/chapters/ 下）：
  ```
  V2 G2 rel+rd status: FAIL | must_fix: ['G2.1:chapters/chapter-1.md']   # 假 FAIL：从未读到文件
  V2b G2 abs must_fix: ['G2.6:/tmp/.../chapter-1.md']                    # 绝对路径时真检查运行（差分证明）
  ```
  缓解：T1 手工协议从仓库根执行（CWD 恰为锚点）时不触发；T2/pipeline 调用面（executor/phase_runner）传绝对路径不触发——触发面为 CWD≠锚点的 CLI 手动调用，与 r1 F437 的 G4 形态同类
- 建议方向: G2 循环头部统一 `p = resolve_input_path(fp, round_dir)`（G2.11 的 bak 随之锚定 rd）

### F457 | cli.py G4 的 bughunt/clean 分支丢弃 rd → 相对路径直接 ValueError 崩溃（F437 的同族、不同分支） | 范围补充（F437/F414） | P2
- 证据: src/shenbi/gates/cli.py:107-110 `gate_G4_bughunt(file_list)` / `gate_G4_clean(file_list)`——rd（arg(2)）已解析但不传；generic.py:94 `resolve_input_path(fp_path, rd)` 在 rd=None + 相对路径时 raise ValueError（shared.py:70-74），CLI 顶层无捕获 → traceback
- 根因: r1 F437 只覆盖 generative 分支（worldbuilding raise）；bughunt/clean 包装函数签名（generic.py:354-361）甚至不接受 rd
- 验证: /tmp/z4r2/repro_misc.py V6 输出：
  ```
  V6 bughunt rel path CRASH: round_dir required to resolve relative path 'chapters/chapter-1.md'; silent CWD
  ```
- 建议方向: gate_G4_bughunt/clean 增加 rd 形参并由 cli 透传；CLI 顶层捕 ValueError 转 FAIL JSON（F437 建议）

### F458 | find_report/G0.10/G7.15 的报告命名族与唯一自动写方不匹配：codex 模式只产出 `*-scores-subagent.json`，三个读取方全部漏读 | 漏报（写方跨区） | P2
- 证据: 读取方命名族——shared.py:149-167 find_report 只试 `<skill>-<tt>-scores.json`/`<skill>-<tt>.json`/`<skill>.json`；g0.py:447 G0.10 glob `*-generative-scores.json`；g7.py:204 G7.15 glob `*-generative-scores.json`。写方——dispatcher/modes/codex.py:56+85 写 `{skill}-{test_type}-scores-subagent.json`（safe_write）；src 内无其他 t1-reports 写入方（grep 证实；scoring.py 不落盘报告，round-exec.sh 只建空目录）。后果：(a) G5.1 回退路径（g5.py:65-70）find_report 返回 None → `G5.1:{pr}:no_report` 假 FAIL；(b) G0.10 计数不含 codex 报告 → 恒 WARN "N/74 remaining"；(c) G7.15 模式分析跳过它们。detect_mode 在本机实测返回 codex（`which codex` → /opt/homebrew/bin/codex）
- 根因: 命名族引用 vs 写方命名从未对账；与 F449 的 "-scores/-scores-subagent" 解析问题同族
- 验证: `grep -rn "t1-reports" src/shenbi --include="*.py" | grep -v gates/` → 仅 codex.py:56；`grep -n "scores" tests/round-exec.sh` → 仅 summary.json 脚手架
- 建议方向: find_report/G0.10/G7.15 的 glob 增补 `-scores-subagent.json` 变体（或 codex 模式改写规范名）

### F459 | 采样截断 + 字典序章节排序：G6.8/G6.10/G6.9/G5.3 的检测面被系统性截窄且 PASS 记录不披露；空 skill-output 脚手架上 G7.5 记空转 PASS | 漏报 | P2
- 证据（数据采样截断——影响判定数据，非展示）: g5.py:149 outline 文件 `[:3]`、:154 输出文件 `[:8]`、:156/:191 内容 `[:5000]`/`[:3000]`（G5.3 数值/术语冲突检测）；g6.py:197/:207 章 `[:15]`、:198/:208/:259 内容 `[:5000]`/`[:3000]`、:262 约束 `[:10]`（PASS 记录 `constraints_extracted` 记未截断总数而只强制前 10 条，g6.py:281）；g6_checks.py:30/:52 内容 `[:5000]`/`[:3000]`（G6.4 时间线/未来知识）、:229 章 `[:min(10,…)]`。字典序偏斜：g6.py:66 `sorted(ch_dir.glob("chapter-*.md"))` 是字符串序——实测 `[chapter-1, chapter-10, chapter-100, chapter-2, chapter-20, chapter-3, …]`，故 `chapters[:15]`（G6.8 ghost/口头禅）与 `chapters[:10]`（G6.10 风格）采到的是字典序前缀而非小说前 N 章：30 章小说中第 3-9 章整段不被采样。展示性截断（判定仍正确，复核确认）: g5.py:201 `conflicts[:10]`、g6_checks.py:66/:264、g0.py:315、g0_purity.py:43/:83、g2.py:309——判定均由未截断集合驱动。另: g7.py:67-80 对 round-exec.sh:87 脚手架创建的**空** skill-output 目录记 `G7.5 PASS`（rglob 无文件 → placeholders 空 → PASS 而非 SKIP）
- 根因: "for speed" 采样上限 + 默认排序语义未对账"按章号"；PASS 记录未携带采样元数据（唯一例外 G6.10 记 chapters_sampled）
- 验证: `sorted([f'chapter-{i}.md' for i in [1..10,20,100]])[:10]` 实跑输出见上；其余为读码（行号已列）
- 建议方向: 章序列统一 `sorted(..., key=章号)`；采样截断在 check 记录中披露（sampled/total）；G7.5 空目录改 SKIP

### F460 | check_chapter_title 错误消息引用 "SKILL.md:125"——实际标题规则位于第 140 行 | 漏报 | M
- 证据: src/shenbi/gates/g4/chapter_drafting.py:73 `(SKILL.md:125)`；skills/shenbi-chapter-drafting/SKILL.md:140 才是"章节标题不要包含章节号"规则（:127 是模板标题占位）
- 验证: `grep -n "标题" skills/shenbi-chapter-drafting/SKILL.md` → 127/140
- 建议方向: 引用改 140 或去掉行号

### F461 | command-to-give.md:46 引用 `tests/dispatch-subagent.sh`——该脚本已被删除（dispatcher Python 化），协议文档断链 | 跨区备注 | M
- 证据: command-to-give.md 步骤 6 `bash tests/dispatch-subagent.sh <skill> generative <round_dir> "<prompt>"`；全仓库 find 无该文件（ADR 0009-dispatcher-python-rewrite.md 记录迁移）；现入口为 shenbi-dispatch
- 验证: `find . -name "dispatch-subagent*"` → 空
- 建议方向: 更新协议文档为 `uv run shenbi-dispatch ...`

---

## 二、误报 / 事实修正

本轮**未发现初审或 r1 的整条误报**。逐条复读 F401–F448 的代码事实全部成立（F403 的 8 处 jload ValueError 点、F405 clean 首位定位、F408/F409/F410/F411/F420/F432–F435 等抽查读码一致）。两点范围补充已单列：F457（F437 的 bughunt/clean 分支扩展）、F458（F449 的命名族扩展）。r1 的严重度异议（F401 P1→P2）维持。

## 三、覆盖空洞（两轮审查方法的共同缺口）

### F462 | 初审与 r1 均未对账 "checker 键空间/命名族 ↔ 写入方键空间/命名族"：progress.json 与 t1-reports 的读方期望没有任何写方满足，也无门禁 | 覆盖空洞 | P2
- 证据: F449（status DONE/done）、F450（agent_id/agent）、F451（agent_trace 无写方）、F452（output_files 无写方）、F455（remaining_bug_hunt/bug-hunt/相位名）、F458（-scores.json/-scores-subagent.json）六个 drift 的共同根因。r1 的角度 (b) 对账了"调用面文件集"（哪些文件传给 checker），但没有对账"读方期望的 JSON 键与取值词表 vs 写方实际产出"；测试夹具手工构造大写 DONE（test_g_reconcile.py:57）使漂移在 CI 不可见
- 验证: 各 finding 的 grep/复现输出（见上）
- 建议方向: 为 progress.json/summary.json/t1-reports 建立单一 schema（contracts/schemas/state.py 已有雏形）+ 写方/读方共用的命名常量；G0 增加一条"读写词表一致"检查

## 四、严重度异议汇总

| 编号 | 轮次判级 | 本轮意见 | 依据 |
|---|---|---|---|
| F401（初审 P1→r1 P2） | P2 | 维持 r1 降级 | F446 复核逻辑本轮复读成立 |
| F449（本轮新） | — | P1：CLI 文档化 gate 对真实轮目录必现假 FAIL + 死检查（repro A/D/E） | 严重度表 "checker 假 FAIL" |
| F450（本轮新） | — | P1：管线主路径（dispatch_helper 跑 G3）上反作弊检查结构性恒 PASS（repro V3） | 严重度表 "checker 假 PASS" |
| F451/F452/F453/F454/F455/F456/F457/F458/F459 | — | P2：死检查/死线/文档化语义未实现/触发面受限的假 FAIL/检测面收窄 | 各条证据 |
| F460/F461 | — | M | 文档引用漂移 |

## 五、验证命令与产物索引（均在 /tmp/z4r2/，仓库零写入）

- repro_reconcile.py —— F449（A/B/C/D/E 五形态：写方形态假 FAIL、后缀独立复现、大小写独立复现、GR.1 死检查）
- repro_misc.py —— V1 字典序排序（F459）/ V2 G2 相对路径假 FAIL 差分（F456）/ V3 G3.5 键错配（F450）/ V4 GT.1 键错配（F455）/ V6 bughunt 分支崩溃（F457）
- 实跑 G0 —— F453（G0.7 恒 WARN）
- grep 组 —— F451（agent_trace 无写方）、F452（output_files 无写方）、F458（t1-reports 唯一写方 codex）、F460（SKILL.md:140）、F461（dispatch-subagent.sh 不存在）、F449 写方行号（materialize.py:59 / codex.py:44）
- 未验证项（逐条声明）：F458 的 G5.1 no_report 端到端触发（需 codex 真跑一轮；静态链完整：find_report 命名族 vs codex.py:56 命名，find/glob 均不匹配）；F459 的 G7.5 空目录 PASS（round-exec.sh:87 脚手架读码推断 + g7.py:67-80 读码，未实际建目录运行）；F449 的"src 内无 G_RECONCILE 调用方"（grep 证实，仅 CLI 暴露）

## 六、收敛判定意见

- 支持 r1 的全部修正与降级；核心 checker 面（G0/G2/G4/G5/G6/G7 主路径 + decisions 单源 + G3.4 fail-closed）三轮结论一致，**该子域可判收敛**。
- 本轮新增集中在单一缝隙（checker↔writer 键空间/命名族，F462），产出 P1×2。若协调者要求完全收敛，建议下一轮仅做该缝隙的定向复核（列写方清单：materialize/codex/dispatch_helper/round-exec.sh × 读方清单：g3/g5/g0.10/g_reconcile/g_transition/g7.15/shared.find_report，双向枚举键与命名）；无需再全量重读 52 文件。
