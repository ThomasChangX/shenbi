# Z1 复核报告 r1（fresh-context 独立复核）

- 轮次: 2026-08-15 全项目深度审查
- 分区: Z1（src/shenbi/ 顶层 14 清单文件）
- 复核 agent 编号段: F121–F199（初审 F101–F120）
- 本轮角度: (a) 引用断链重扫（docstring/注释/usage 中的路径与符号引用 vs 磁盘/代码实况）；(b) 初审"全部/仅/唯一"断言的完整性复查（全仓 grep 二次验证）
- 方法: 14/14 清单文件 fresh 全量重读 + 跨区依赖（gates/cli.py、gates/g5.py、gates/shared.py、command-to-give.md、pyproject.toml、justfile、82 份 rubric）独立核实 + /tmp 只读场景实测（未触碰仓库文件、未运行 pytest/dispatch/pipeline）
- 结论速览: 初审 20 条 findings **零误报**（关键断言逐条独立重验成立）；**漏报 8 条**（F121–F128，其中 P2×6、M×2）；覆盖空洞 6 项；严重度异议 3 项（含 ledger 层 F104/F757 同缺陷异级）

---

## 一、漏报（新 findings）

### F121 | T1 marker 读写协议错配：bug-hunt/clean 的 G4 marker 永不存在，marker 强制对 2/3 测试类型不可满足 | error | P2
- 证据: src/shenbi/scoring.py:196-202（t1 分支按 `G4-{skill_name}-{test_type}.json` 查找）; src/shenbi/gates/cli.py:101-121（**全仓唯一** G4 marker 写入方 cli.py:121 恒写 `write_gate_marker("G4", full_name, "generative", ...)`；:107-110 的 bughunt/clean 分支不写任何 marker）; tests/unit/test_scoring.py:481-501（仅钉 generative 命名）
- 根因: marker 写侧硬编码 "generative"，读侧用变量 test_type，两侧协议从未对齐；bughunt/clean G4 分支漏调 write_gate_marker
- 验证（已运行，/tmp 场景）: 磁盘放置 `G4-worldbuilding-generative.json`（写侧唯一能产出的名字）后调 check_gate_markers：
  ```
  test_type='generative' -> missing=[]
  test_type='bug-hunt'   -> missing=['G4-worldbuilding-bug-hunt']
  test_type='clean'      -> missing=['G4-worldbuilding-clean']
  ```
  全仓 `grep -rn "write_gate_marker" src` 仅 cli.py:121(G4)/128(G6) 两处；磁盘现存 marker 全部为 `G4-*-generative.json`（find 实测 20+ 个，零 bug-hunt/clean 命名）
- 建议方向: 写侧按实际 test_type 写 marker（并给 bughunt/clean 分支补 marker 写入），或读侧统一认 generative marker；补 bug-hunt/clean 命名的回归测试
- 定级说明: 文档化 T1 流程不传 --round-dir 故未踩中，判 P2；若按"marker 强制功能对 2/3 测试类型永久死路"从严可 argue P1（见严重度异议）

### F122 | filter_dimensions_by_test_type 的 scope 号码抽取对区间只取端点："Shared audit (3-7)" → {3,7}，漏 4/5/6 | error | P2（latent）
- 证据: src/shenbi/scoring.py:129-132（`re.findall(r"dim\s+(\d+)", ...)` + `re.findall(r"#?(\d+)", scope)`，无区间展开）; 44 个可解析 rubric 中 20+ 个使用区间 scope（如 tests/tiers/t1-skill/shenbi-review-memo-compliance/rubric.md:41 `Shared audit (3-7)`、using-shenbi/rubric.md `All bespoke (3-7)`）
- 根因: 号码抽取只做逐 token 匹配，未处理 "a-b" 区间语义
- 验证（已运行）: `re.findall(r"#?(\d+)", "Shared audit (3-7)")` → `['3','7']`；excluded 集合 = {3,7}，4/5/6 不在内。当前所有区间 scope 均标 "Yes"（全 44 文件 No 单元格扫描仅 chapter-drafting 与 _template 两处、且用的是列表格式 dims 6,7,9），故未触发——属埋雷：任一区间 scope 改标 No 即静默漏豁免中间维度
- 建议方向: 区间正则 `(\d+)\s*[-–]\s*(\d+)` 展开；对 scope 含数字但抽取为空/单点的情况打 warning

### F123 | phase_runner main() 位置参数与 flag 共用 args 无解析器：缺位时 flag token 被绑定为 phase/skill 并写出垃圾状态文件 | error | P2
- 证据: src/shenbi/phase_runner.py:345-372（`args = sys.argv[2:]` 后 `phase = args[0]`、`skill = args[1]` 盲取，find_flag 在同一数组里扫 flag）
- 根因: 手写 argv 解析，位置参数与 `--flag value` 不互斥
- 验证（已运行，/tmp 场景）: `python -m shenbi.phase_runner start --round-dir /tmp/z1rev/round`（漏写 phase）→ 不报 usage 错，而是 `phase = "--round-dir"`，G5 返回 `must_fix: ["unknown phase: --round-dir"]`，并**实际写出** `phase-state/--round-dir.json`（内容 `"phase": "--round-dir"`，文件已核实存在）
- 建议方向: 先剥离 flag/value 对再取位置参数；位置参数缺失或以 `--` 开头 → usage error + exit(1)。与 F105（argv→文件名）同一信任面，修复时应一并处理
- 备注: `pre-skill genesis --round-dir X`（漏 skill）同类——skill 绑定为 "--round-dir"

### F124 | cmd_post_score 对 malformed scores 文件裸抛 JSONDecodeError traceback——该检查正是为这个场景而写，却不结构化报错 | error | P2
- 证据: src/shenbi/phase_runner.py:290-292（注释 "a malformed file must abort here rather than silently advancing state"，实现为无守卫 `json.loads(...)`）
- 根因: 校验意图与错误处理形态脱节（对比同函数 scores_file 不存在时有结构化 emit error）
- 验证（已运行，/tmp 场景）: state=skills_done + `not-json{` scores 文件 → `json.decoder.JSONDecodeError: Expecting value: line 1 column 1` 整机 traceback，无 JSON 输出
- 建议方向: try/except JSONDecodeError → emit {"status": ERROR, message} + exit(1)。同类：load_state（phase_runner.py:39）对损坏 state 文件也未守卫，建议一并处理
- 备注: 状态确实未推进（崩溃退出），功能方向正确、错误处理形态错误，故 P2 而非 P1

### F125 | scoring.py 两处 gate 子进程调用无 timeout——挂起的 gate 会让 scoring CLI 无限挂起 | error | P2
- 证据: src/shenbi/scoring.py:304-308（--gate-only 分支）、:343-355（T1 G3 分支），两处 `subprocess.run(...)` 均无 timeout 参数；对照 src/shenbi/phase_runner.py:87-92（60s）与 src/shenbi/pipeline/dispatch_helper.py:1937-1946（60s + TimeoutExpired 捕获）——仓内已有两处正确模式，本文件漏配
- 根因: 子进程调散点复制时超时策略未同步
- 验证: 未运行（需真实挂起子进程；静态直读确认无 timeout kwarg）
- 建议方向: 两处补 timeout=60 并捕获 TimeoutExpired → 结构化 FAIL；长期收敛到共享 run_gate helper

### F126 | scoring CLI 三重文档↔实现漂移：usage 承诺 T1|T2|T3 门检（仅实现 T1）、--gate-only 承诺通用 GATE（仅 G2 argv 协议）、协议文档声明处理 exit 3 MARKER_MISSING（文档化调用永远产生不了 exit 3） | docs/error | P2
- 证据: src/shenbi/scoring.py:289（usage: `--tier T1|T2|T3 --phase <name>: enable gate checks before scoring`）vs :337（实现仅 `if tier == "T1" and test_type:`，T2/T3 no-op；--phase 即 F118 死参数）; :290/:300-305（usage `--gate-only <GATE>` 通用承诺，实际 argv `[gate, files, ftype]` 只匹配 G2 协议，传 G4 即错位）; command-to-give.md:49/64/71（T1 三个评分命令均不传 --round-dir/--tier → marker 检查与 G3 集成在文档化 T1 流程零执行）+ :57-60（同一协议详细描述 exit 3 = MARKER_MISSING 的处置——其自带的命令行永远触发不了该状态）; command-to-give.md:104/122（T2/T3 传 --round-dir 但不传 --tier → G3 集成同样零执行）
- 根因: 防御性 flag 逐个添加后 usage/协议文档未回写；T2/T3 门检承诺未实现
- 验证: 已运行（usage/实现行号直读 + command-to-give.md 全文核对；--round-dir 缺省时 check_gate_markers :189-190 直接返回 []）
- 建议方向: usage 收窄为实际行为（T1 only + gate-only 仅 G2），或实现 T2/T3 门检；协议文档补 --round-dir/--tier 或删除 exit 3 处置段；与 F121（marker 名错配）合并修复才能让 T1 marker 强制真正可达

### F127 | __init__.py docstring 子模块清单过期程度远超 F117 所述：仅列 6 项，实际顶层 .py 13 + 子包 13 | error | M
- 证据: src/shenbi/__init__.py:3-10（仅列 exceptions/logging/scoring/phase_runner/gates/dispatcher）vs `ls src/shenbi/`（顶层 .py 13 个：另有 capability_fs/cli_utils/error_guidance/paths/recovery/safe_write/status/sync_contracts；子包 13 个：audit/config/contracts/cost/dispatcher/gates/orchestration/pipeline/plugins/records/skill_utils/text/trace）
- 根因: 与 F117 同源（包演进后 docstring 未随迁），F117 只点到 forwarder 注记
- 验证: 已运行（ls 输出比对）
- 建议方向: 删除枚举式清单改为指向前导模块/文档，避免每次加模块都漂移

### F128 | load_rubric 无节作用域：全文件任何 `| <int> | <name> | <int>% |` 形状表格行都会成为评分维度（latent） | error | M
- 证据: src/shenbi/scoring.py:30-70（in_table 状态只由 `| #` / `|---` 行触发、由非表格行复位，与所在 ## 节无关——Dimension Applicability 表头 `| # | Dimension |` 同样会置 in_table=True）
- 根因: 解析器按行形状而非节语义识别维度表
- 验证: 已运行（82 份 rubric 全扫描：当前零污染——18 个新格式 rubric 的适用性表第 3 列均为散文文本，int() 失败被 continue 吞掉；唯一 >9 维的 chapter-drafting 是合法的双段主表）。属埋雷：任何辅助表格第 3 列出现纯数字即静默混入维度并扭曲权重和（触发 weight_mismatch 警告或直接改分）
- 建议方向: 解析限定在 `## Dimensions`（或首个主表）节内；或对 kill_switch/applicability 节内的表格行显式跳过

---

## 二、误报（初审条目反驳）

**无。** 初审 20 条（F101–F120）逐条独立重验，全部成立。关键重验记录：

| 初审 | 复核方式 | 结果 |
|---|---|---|
| F101 | gates/cli.py:113-121 直读（`rd=arg(2)`、`project_dir=rd`）；g4 内 RoundPaths 消费者 grep = 11 个 checker | 成立（"11 个 checker" 计数吻合） |
| F102 | phase_runner.py:117/307 `str(project_dir)` + gates/g5.py:115 `if project_dir:`（"None" 真值）直读 | 成立 |
| F103 | scoring.py:356-362 直读（吞点 :361-362） | 成立 |
| F104 | 自跑扫描：62 份含 Applicability 节、44 份可解析（"Dimension scope" 表头）、18 份不可解析 | 成立（18 计数复核一致） |
| F105 | phase_runner.py:36-47 直读 | 成立 |
| F106 | 异常元组直读 + `subprocess.TimeoutExpired` ∉ OSError 静态确认（对照 dispatch_helper:1941-1944 已有正确模式，反证该缺陷非必然） | 成立 |
| F107 | scoring.py:300-313 直读 | 成立 |
| F108 | `ls docs/{registry,gates,schemas,dispatcher,integrity}.md` 全部 No such file；`ls tests/build_registry.py` No such file；`grep -rn SHENBI_SUBAGENT_TIMEOUT src tests tools docs justfile` 仅 error_guidance.py:44（余为 coverage HTML 与审计文档自引） | 成立（"全部 doc_url"断言精确：6 条目 5 个唯一文件均断链） |
| F109 | 全仓 grep `get_guidance\|ErrorGuidance\|error_guidance\|RECOVERY_STRATEGIES\|RecoveryStrategy`（src+tests+tools）→ 仅 3 个测试文件 | 成立（"零运行时消费者"复核为真） |
| F110 | 7 类逐一 grep（src+tests+tools）→ **零命中**（比初审表述更彻底：连测试都不引用这 7 类）；`.to_dict()` 仅 tests/unit/test_exceptions.py:46,54（pipeline/state.py 的 to_dict 是另一类） | 成立 |
| F111 | tests/unit/test_safe_write.py:62-100 直读：两个 chmod 测试手工 os.open+chmod 后断言 chmod 生效，从未调用 `_acquire_lock`/`safe_write`（注释自称 "Use _acquire_lock directly" 与实现不符） | 成立 |
| F112 | grep tests 仅纯函数测试 | 成立（见下方轻微异议 1） |
| F113 | scoring.py:440-441 直读 | 成立 |
| F114 | 全仓 grep → scoring_bridge 仅自身 + tests/unit/orchestration/test_bridges.py | 成立（见轻微异议 2） |
| F115/F116 | phase_runner.py:208-216 + gates/cli.py:91-104 直读 | 成立 |
| F117 | __init__.py:8-9 直读 | 成立（F127 为其扩展） |
| F118 | 四个散点逐一验证：error_guidance.py:9 / recovery.py:8 未用 log；sync_contracts.py:124-134 函数体无 skill 引用（:149 传入）；`grep -n "_phase" scoring.py` 仅 :321/:331；phase_runner.py:188 裸 assert | 成立 |
| F119 | capability_fs.py:22-29 直读 | 成立 |
| F120 | scoring.py:262-274 直读（`len(set(values))==1` 无样本数下限） | 成立 |

轻微异议（不推翻 finding，仅修正表述/登记）：

1. **F112 影响面表述偏窄**: 验证段写 "grep sync_contracts tests tools justfile → 仅纯函数测试"，但 justfile:22（`just check` 内 `uv run shenbi-sync-contracts >/dev/null && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`）与 justfile:59（`generate`）实际端到端执行 main() 并做幂等 diff（CI codegen-idempotency 同源）。即 main() 并非完全无护栏——有仓级端到端幂等门，缺的是 pytest 级隔离测试。P2 可保留（改写 69 个 SKILL.md 的变更器无隔离回归仍属测试缺口），但"零测试"应读作"零 pytest 覆盖"。
2. **F114 属重复登记**: 与本轮 F506（Z5，同文本"两 bridge 生产零调用"）及 2026-08-14 轮 F500 为同一缺陷（grep 证实 2026-08-14 findings-ledger 已有 F500 完整登记）。初审对 F101 标注了 R8/F163、对 F105 标注了 F158，唯独 F114 漏标 prior ID——ledger 合并时注意。

---

## 三、覆盖空洞

1. **marker 读写协议一致性**: 初审核对了 G4 marker 命名与 phase_runner 消费方的一致性（generative 流），但未核对 scoring.check_gate_markers 读侧与写侧 test_type 的协议一致性 → 本轮 F121。
2. **"能解析但解析错"面**: F104 只发现"不解析"（18 份），未验证可解析 44 份的解析语义正确性 → F122（区间端点）、F128（无节作用域）。
3. **argv 解析健壮性**: 初审覆盖 find_flag 缺值、裸 assert、路径穿越，未覆盖位置参数与 flag 错位绑定 → F123。
4. **文档化调用 vs 防御 flag 激活**: 初审未对照 command-to-give.md 的实际命令行与 scoring 防御性 flag（--tier/--round-dir）的激活条件 → F126。
5. **subprocess 超时面只扫了 phase_runner**: F106 限于 run_gate；scoring.py 两处同类调用未扫 → F125。
6. **ledger 层空洞（跨区）**: F104（Z1，P1）与 F757（Z7-c，P2）为同一缺陷双档登记且严重度不一致，需合并裁决（见异议 3）；F114/F506/F500 三重登记。

---

## 四、严重度异议（无权改级，仅提请复议）

1. **F121（本轮新报，自判 P2）**: 若采信"usage 明示 --test-type bug-hunt/clean + marker 检查是 AGENTS.md 'no gate can be skipped' 的执行面，而该执行面对 2/3 测试类型永久不可满足"的解读，符合 P1"正常路径可复现功能错误"。当前判 P2 的依据是文档化 T1 流程不传 --round-dir（未进入该分支）。建议 owner 结合 F126 一并裁决：修复 F126（协议补 --round-dir）会立刻把 F121 暴露为 P1。
2. **F123（本轮新报，自判 P2）**: 与 F105（P1）同一信任边界（未净化 argv → 任意 token 成为写出文件名）。若 maintainer 按"同一攻击面合并"处理，F123 应随 F105 升级；单看其自身（垃圾文件 + 误导性报错，无越界写出）为 P2。
3. **F104 vs F757（跨区 ledger 不一致）**: 同一"18 份 rubric Applicability 失效"缺陷，Z1 登记 P1、Z7-c 登记 P2。按决策表"正常路径可复现功能错误"（bug-hunt/clean T1 评分失真或 REJECT 误拒）支持 P1，建议 F757 并入 F104 并统一为 P1。
4. **F112 定级维持 P2 但建议附注**: 见轻微异议 1——`just check`/CI codegen 幂等门是实际存在的护栏，裁决时可考虑降 M 或保留 P2 附 mitigation 说明。

---

## 五、本轮角度发现摘要

**(a) 引用断链重扫**：初审已覆盖 error_guidance doc_url/action（F108）、__init__ forwarder 注记（F117）、recovery "P-3 implements"（F109）。本轮新增断链/漂移 4 处：scoring usage "T1|T2|T3" vs 仅 T1（F126）；--gate-only 通用 GATE 承诺 vs 仅 G2 argv 协议（F126）；command-to-give.md 声明处置 exit 3 MARKER_MISSING 而其文档化命令行永不可达该状态（F126）；__init__ 子模块清单 6/26（F127）。safe_write.py:5-6 "src/shenbi/*.py whose ruff ignore list omits RUF002" 的声称经 pyproject:155-168 核对**准确**（且 ruff check 实跑通过），非断链。

**(b) "全部/仅/唯一"完整性复查**：初审 5 组全仓断言全部经独立 grep 证实——F109（error_guidance/recovery 仅测试消费）、F110（7 异常类零引用，实际连测试引用都没有）、F108（SHENBI_SUBAGENT_TIMEOUT 仅 :44）、F114（scoring_bridge 仅测试）、F110 附注（to_dict 仅测试）。一处方法学警示供后续区复用：grep `CapabilityFS | grep -v capability_fs.py` 会把 tests/unit/test_capability_fs.py 一并滤掉（路径含同名子串）——初审结论侥幸正确（两个测试文件都是消费者），但该 grep 模式有假阴性风险，本次已用 `grep -rln ... tests/unit` 修正复核。

**覆盖完整性**: 14/14 清单文件重读（含 py.typed，空文件确认存在）；初审"deep-read 14/14、未覆盖无"的覆盖声明属实。

## 附：验证命令记录（本轮实际运行）

- `ls docs/{registry,gates,schemas,dispatcher,integrity}.md tests/build_registry.py` → 全部 No such file（F108 复核）
- `grep -rn "SHENBI_SUBAGENT_TIMEOUT" src tests tools docs justfile pyproject.toml` → 仅 error_guidance.py:44
- `for exc in ScoringError ...; do grep -rn "$exc" src tests tools; done`（7 类）→ 全部零命中（F110 复核）
- `grep -rn "get_guidance|ErrorGuidance|error_guidance|RECOVERY_STRATEGIES|RecoveryStrategy" src tests tools`（滤自身）→ 仅 tests 3 文件（F109 复核）
- `grep -rn "scoring_bridge|check_scorer_agreement|flag_score_collapse" src tests tools`（滤自身/直测）→ 仅 scoring_bridge 自身 + test_bridges.py（F114 复核）
- rubric 全量扫描脚本 ×3（82 份：Applicability 节计数 62 / 可解析 44 / 不可解析 18；No 单元格定位；区间 scope 定位；load_rubric 污染扫描）
- marker 错配实测: check_gate_markers 三 test_type 对比（见 F121 输出）
- cmd_post_score 崩溃实测: `.venv/bin/python -m shenbi.phase_runner post-score genesis /tmp/z1rev/bad_scores.json --round-dir /tmp/z1rev/round` → JSONDecodeError traceback（F124）
- flag 错位实测: `.venv/bin/python -m shenbi.phase_runner start --round-dir /tmp/z1rev/round` → `phase-state/--round-dir.json` 落盘（F123）
- `uv run ruff check src/shenbi/capability_fs.py src/shenbi/safe_write.py` → All checks passed（safe_write docstring 声称核对）
- `grep -rn "RetryExhaustedError|DispatchWriteFailureError" src` → 链路逐行核对（chapter_loop.py:626,2919 raise / cli.py:313 catch；dispatch_helper.py:1119 raise / :367,1678,1789 catch）（F110 反证侧复核）
- /tmp/z1rev 场景已清理验证用途，未触碰仓库任何文件
