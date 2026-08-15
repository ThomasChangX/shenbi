# Z5 独立复核报告 r4（fresh-context，2026-08-15 轮）

- 复核 agent: Z5-review-r4（与初审者、复核 r1/r2/r3 均无关的独立上下文）| 编号段: F531–F599（实用 F531–F536；初审 F501–F514、r1 F515–F524、r2 F525–F528、r3 F529–F530）
- 复核对象: docs/superpowers/audit-runs/2026-08-15/zones/Z5.files 全部 13 文件（audit/ 5 + cost/ 5 + orchestration/ 3）+ 本轮角度要求的审计基础设施消费链（dispatcher/executor.py、pipeline/parallel_dispatch.py、pipeline/write_safety.py、pipeline/dispatch_helper.py 路由层、trace/writer.py、gates/g7_trace.py、pipeline/crash_recovery.py、pipeline/filelock_utils.py、safe_write.py——后五者跨区，仅作证据链引用）
- 本轮强制新角度（与前三轮均不复用）:
  - **(a) 并发与竞态面**——审计记录 seam 在并行审计波下的进程间竞争、write_safety 分类 vs 契约面、safe_write 锁边界（flock 目录锁 vs 三处绕行 append）、审计可重入性（audit_writes/registry 纯读复核）、pre→post 快照一致性窗口
  - **(b) 失败恢复路径**——rc=2 在重试决策中的语义（重入/放大）、write-audit.jsonl 半写与 durability、审计中断后账本/trace 一致性、G7 对损坏证据的处理
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件（`git status --porcelain` 无输出）；未执行 pytest；未运行 shenbi-dispatch/pipeline；未 git 写操作。所有实验脚本仅写 /tmp/z5r4/，一切命令非交互（</dev/null）。对 novel-output/test-validation 只读计数。
- 核心复核结论一句话: **前三轮 30 条 finding 无一整体误报（本轮全部复读+关键条实跑复现）；但两个强制新角度各命中一条前三轮完全没碰的维度——(a) 并行审计波在 legacy 路由上并发触发 record_audit_outcome，而 TraceWriter 自我声明"NOT thread/proc-safe"（TOCTOU），实跑复现 seq 重复+签名链分叉、G7 误报 tamper（F531，P1）；(b) rc=2（写审计 GATE_FAIL）在所有重试决策中与瞬时失败不可区分，test-validation 真实数据里 worldbuilding 的 3 条同判词 GATE_FAIL（trace 时间戳 13:43:06/07/08 相邻一秒）就是该机制的生产实证（F533）。另发现 write_safety 前缀分类与契约面冲突（resonance 写共享 truth 文件却在并行波，且有测试把这个误分类锁死）、write-audit.jsonl durability/时间戳缺口、G7 损坏行静默截断（跨区）。**

---

## 一、漏报（初审/r1/r2/r3 均未发现；均附实跑证据或文件行号）

### F531 | 并行审计波在 legacy 路由并发调用 record_audit_outcome → TraceWriter TOCTOU 使 trace.jsonl 签名链分叉/seq 重复 → G7 把合法运行误报 tamper | 漏报 | P1
- 生产路径（全部行号实看）: chapter_loop.py:2541-2618（step_idx==_FIRST_AUDIT_IDX 时 core wave 7 技能 + genre wave 并行，Semaphore(4)）→ parallel_dispatch.py:86-91（线程内 dispatch_skill，**无 round_dir**）→ dispatch_helper.py:1902（`rd = str(round_dir) if round_dir else str(project_dir)` → rd=project_dir）→ :1909-1910（`uv run shenbi-dispatch` **subprocess**，最多 4 个并发）→ dispatcher/cli.py:11,25（dispatch_with_write_audit）→ executor.py:283-286（finally 内 post snapshot + audit + record）→ **record.py:44（每个子进程各自 `TraceWriter(round_dir).append(...)`，同一 `<project_dir>/trace.jsonl`）**
- 根因: trace/writer.py:4-6 docstring 自我声明——"Concurrency: NOT thread/proc-safe — __init__ reads then append writes (TOCTOU). Current dispatch is sequential (spec: 顺序执行 topology), so this is safe. Concurrent dispatch needs flock or staging isolation (future work)"。该"顺序执行"假设被后来加入的 parallel_dispatch（ThreadPoolExecutor + 子进程）打破；TraceWriter.__init__ 对整个文件**读两遍**（_count_existing + _last_sig_existing，writer.py:46-57），随后才 sign+append，窗口随 trace 变长而增大
- 验证（已运行，/tmp/z5r4/trace_race.py——两个子进程各执行 `TraceWriter(d)` 构造后 delay 0.5s 再 append，窗口为演示目的放大；生产窗口 = 双全文件读 + sign + write + fsync）:
  ```
  seeded events: 2, last seq: 2
  A wrote seq=3
  B wrote seq=3
  seq column after race: [1, 2, 3, 3]
  G7 audit_trace manifest: ['G7T.tamper: seq=3 signature mismatch (内容被改/链断裂)']
  ```
- 影响面: 无 API key 且无 IDE CLI 的部署形态（= legacy 回退路由，dispatch_helper.py:11-12 自述 "T1 testing / legacy"）下，**每一章的并行审计波都会让最多 4 个子进程并发 append 同一 trace.jsonl** → seq 重复 + prev_signature 分叉 → G7（gates/g7_trace.py:40-48 逐行重算链）对合法运行报 `G7T.tamper`——防篡改审计的证据链被框架自身的并发写坏掉。F533 的重试再入会进一步增加 append 次数、放大碰撞面。测试盲区: 全仓无 TraceWriter 并发测试（grep tests/ 无 concurrent/thread/race + TraceWriter 组合命中）
- 建议方向: TraceWriter init+append 外套 flock（对 trace.jsonl 或其目录）；或 record_audit_outcome 的 trace 事件改由父进程单写者聚合（子进程只写 write-audit.jsonl，父进程按完成顺序补 trace）
- 定级依据: 判定表 P1「并发竞态」字面命中。根文件跨区（trace/writer.py），触发点与修复面含 Z5 属地的 record.py seam，故在本区立案并标注跨区
- 置信度: high（实跑复现 + 生产路径行号链完整）

### F532 | write_safety 按名称前缀而非契约分类：shenbi-review-resonance 契约声明写共享 truth 文件（truth/audit_drift.md、truth/resonance_trend.md）却被判 READ_ONLY_AUDIT 进入并行波，模块"explicit and enforced"承诺被现有技能违反，且测试把误分类锁死 | 漏报 | P2
- 证据（已运行）:
  ```
  $ uv run python -c "...load_contract(s); classify_skill_write_safety(s)"
  shenbi-review-resonance | writes+updates: ['audits/chapter-N-resonance.md', 'truth/audit_drift.md', 'truth/resonance_trend.md'] | classified: read_only_audit
  shenbi-review-arc-payoff | writes+updates: ['audits/volume-N-payoff.md', 'truth/audit_drift.md', 'truth/arc_payoff_trend.md'] | classified: read_only_audit
  ```
  + write_safety.py:45-46（`if skill.startswith("shenbi-review-"): return WriteSafety.READ_ONLY_AUDIT`——只看名字）+ write_safety.py:1-7 模块 docstring 声称"makes that boundary **explicit and enforced**… cannot silently place a write-capable skill on the concurrent path and race on truth files" + chapter_loop.py:231-237（step 13 shenbi-review-resonance，is_audit=True）+ :2577（core_skills 过滤 `s.is_audit and "review" in s.skill` → resonance 在并行波内）+ parallel_dispatch.py:166（assert_parallelizable 依前缀放行）
- 测试锁死: tests/unit/pipeline/test_parallel_dispatch_safety.py:17-26 **显式断言** shenbi-review-resonance / shenbi-review-arc-payoff == READ_ONLY_AUDIT——测试只验证分类器的名字规则，从不与契约面对账，误分类被固化为回归基线
- 现状评估（如实）: (a) 波内今天没有 audit_drift.md 的第二个写者（arc-payoff 触发器恒 False，audit_layer.py:78；由 triggers.py:238/closure.py:88 串行路径调度），波内也没有该文件的读者（全仓 reads 含 truth/audit_drift.md 的只有 shenbi-intent-management，条件步不在波内）→ 当前无活跃数据竞争；(b) safe_write 单文件原子（API 路径 _write_parsed_outputs→safe_write，dispatch_helper.py:1139）使读者只见旧/新不见半写；(c) 但 resonance_trend.md 另有框架侧写者（chapter_loop.py:3043-3053 经 _build_resonance_trend_row 追加行）——同一文件"技能契约声明写 + 框架代码也写"的双写者并存，且 audit_drift.md 的两个技能写者（resonance/arc-payoff）一旦未来被同时调度即是整文件 last-writer-wins 丢失更新
- 根因: 分类器的前缀捷径（write_safety.py:44-50）与契约面（SKILL.md frontmatter）零联动；docstring 声称的"enforced"仅对未加 `shenbi-review-` 前缀的新技能成立
- 验证: 上述实跑输出；契约提取经 load_contract（权威路径）
- 影响面: 并发安全边界的核心承诺失效——任何 `shenbi-review-*` 技能写共享 truth 文件都会静默落到并行路径；本条与 F524（resonance_trend.md 第三消费者格式互斥）同文件不同机制，互补不重叠
- 建议方向: classify 改为"前缀 AND 契约 writes+updates 不含 truth/ 共享文件"，或至少在 assert_parallelizable 里对波内技能做契约写面检查；同步修正 test_parallel_dispatch_safety.py 的断言来源
- 定级依据: P2（latent 并发缺陷 + 模块契约声明与现实冲突；当前无活跃碰撞——若发现波内真实读写碰撞再升 P1）
- 置信度: high

### F533 | rc=2（写审计 GATE_FAIL）与瞬时失败在所有重试决策中不可区分：确定性假阳性被完整重试（波内 ×3 / 串行 ×3，可嵌套）→ LLM 成本放大 + 同技能同章重复 GATE_FAIL 行/事件；test-validation 已有生产实证 | 漏报 | P2
- 证据（代码行号）:
  - executor.py:287-288（`if not audit_ok and rc == 0: rc = 2`——GATE_FAIL 与 G1/G2 失败共用 rc=1 之外唯一的"失败"语义）
  - dispatch_helper.py:1925（`DispatchResult(r.returncode == 0, r.returncode, ...)`——rc=2 → success=False，rc 数值虽保留但下游不读）
  - 并行波: parallel_dispatch.py:92（`if result.success: return result`）+ :117-125（失败→backoff→重试，MAX_RETRIES=2 → **同一技能完整重派 3 次**）
  - 串行路径: chapter_loop.py:2864-2871（`if not result.success: return _handle_failure(..., "dispatch", ...)`）→ :587-671（retry_counts+1、retry_budget_consumed+1，attempt < max_revision_retries 时返回 False 重试）→ error_handler.py:52-57；耗尽后 dispatch_escalation + ESCALATION checkpoint（:644-671）
  - 唯一区分退出码的地方是评分路径 error_handler.py:84-100（exit_code 2/3 语义表）——写审计路径没有任何对应物
- 生产实证（已运行，只读计数 novel-output/test-validation）:
  ```
  write-audit.jsonl: 4 rows | blocked: 3 | total viol: 6 | checked sum: 21
    shenbi-worldbuilding blocked viol:2 checked:7   × 3 行（判词完全相同）
  trace.jsonl:
    1 2026-07-19T13:43:06 write-audit GATE_FAIL shenbi-worldbuilding
    2 2026-07-19T13:43:07 write-audit GATE_FAIL shenbi-worldbuilding
    3 2026-07-19T13:43:08 write-audit GATE_FAIL shenbi-worldbuilding
    4 2026-07-19T13:43:08 write-audit AUDIT_PASS shenbi-escalation-review
  ```
  3 条同判词 GATE_FAIL、trace 时间戳相邻一秒——即 F529 假阳性触发后重试机制**完整重跑了 3 次 dispatch**（internal 模式快所以代价不明显；API/codex 模式下是 3 倍真实 LLM 调用），并写入 3 行账本 + 3 个 trace 事件
- 根因: 重试决策只看 success 布尔值；确定性策略违规（越权/drift/假阳性）与瞬时故障（超时/网络）共享同一重试通道——前者重试在语义上不可能成功
- 影响面: (a) F529/F501/F516 的每次触发被放大为 3 次完整 dispatch（API 模式 = 3× token 成本，叠加 F504 还不落账）；(b) write-audit.jsonl/trace 出现同判词重复行，forensic 计数（r3 式对账）与重试不可区分（账本行**无时间戳字段**，见 F534）；(c) 重试 attempt N 的 pre 快照已含 attempt N-1 写入的文件——同一次逻辑 dispatch 的各 attempt 审计结论可互相矛盾；(d) 每次重试再入 record_audit_outcome，扩大 F531 的碰撞面
- 建议方向: DispatchResult 增带 rc 语义（gate_violation vs transient），_dispatch_with_retry/_handle_failure 对 gate_violation 不重试、直接升级
- 定级依据: P2（失败恢复语义缺陷；放大的是既有 P0/P1 的后果，自身不独立造成数据错误）
- 置信度: high（生产数据直接实证）

### F534 | write-audit.jsonl 无 fsync、无锁、无时间戳：自称"真理之源/绝不静默丢弃"的账本与同函数内 TraceWriter（fsync）及 safe_write 标准形成 durability 不对称，崩溃窗口丢行 + 并发大行可撕裂 + 重试与多次调用不可区分 | 漏报 | P2（低影响）
- 证据: record.py:36-39（`ledger.open("a")` + 单次 `fh.write`，close 时才 flush，**无 os.fsync**、无任何锁）vs writer.py:92-95（trace 事件逐条 flush+fsync）vs safe_write.py:107-112（temp+fsync+replace 框架标准）；record.py:29-35 账本行字段 = skill/blocked/violations/drift/checked_files——**无 timestamp**（对照 cost/ledger.py:69 TokenUsageRecord 有 timestamp）
- 根因: Tier B 账本按"append-only 够用"实现，未对齐框架自身的持久化纪律；追 加 时 multi-writer（F531 同场景）下超过 8KB 缓冲的行（长 checked_files/violations，worldbuilding 实测行已 7 文件）会拆多次 write syscall，进程交错时可产生半行
- 验证（已运行）: `grep -rn "write-audit" src/ tools/ scripts/` → 唯一引用者为 record.py 自身与 skill_utils/drift_detection 的无关开关（`--write-audit-drift` 写 truth/audit_drift.md，r2 已排除）——**账本零程序化读者**，半行当前不崩任何东西（latent）
- 影响面: (a) 掉电/崩溃窗口内审计行丢失而 fsync 过的 trace 事件（若已到）幸存——"真理之源"反而比镜像更易失；(b) 并发半行（F531 场景）留 latent 损坏；(c) 无时间戳使账本自身无法区分重试与独立调用（F533 的 3 行需借 trace.jsonl 的 ts 才能判定）
- 建议方向: 账本写后 flush+fsync（对齐 TraceWriter）；行内加 ts 字段；与 F531 一并考虑文件锁
- 定级依据: P2（durability 边界缺陷；当前 forensic-only 影响面，如实标注低影响）
- 置信度: high

### F535 | G7 `_read_only_events` 遇中段坏行 break 静默截断事件列表：在中间位置插入/损毁一行非法 JSON 即可让其后所有事件（含被篡改内容）对 G7 不可见而 PASS | 漏报 | P1（跨区：gates/g7_trace.py，属"相关审计基础设施"）
- 证据: gates/g7_trace.py:24-27（`except Exception: break  # torn line: stop here (read-only, no repair)`）+ :38-49（链校验/monotonic/COMPACTION 检查全部作用于**截断后**的列表；manifest 为空时记 `G7T.chain PASS` 且带 `events: len(events)` 计数）
- 根因: "torn tail line 停止"的防御意图被泛化为"任何坏行都停止且不报告"——尾部撕裂（崩溃半写）是良性场景，但中段坏行（插入篡改、编码损坏、F531/F534 族的并发交错写）会让 G7 静默只验前缀
- 验证: 代码路径推演 + 与 F531 实验互补——F531 的竞争产生的是**合法 JSON 但链断裂**的行（被 G7 抓到）；本条针对**非法 JSON 行**的另一种竞争/篡改产物。未另行构造中段坏行实验（机制为单行 break，确定性成立）
- 影响面: G7 的核心契约（docstring: "recomputes the hash chain to detect tampering"）存在静默绕过路径：篡改者无需破解哈希链，只要把目标行连同自身改成非法 JSON。正常路径可复现度低（需外部损坏），但防篡改门的威胁模型恰恰包含主动篡改
- 建议方向: 坏行不应静默 break——至少记一条 `G7T.corrupt_line` manifest 项（fail-visible）；仅当坏行是最后一行时才按 torn-tail 宽容
- 定级依据: P1（对照 F518 先例：门被静默绕过 = P1；"静默错误结果"若按 P0 解释亦有可辩空间，保守取 P1，供 triage 仲裁）。属地: gates 区——建议移交该区 owner 复核编号归属
- 置信度: high（行号+控制流确定）

### F536 | 审计链无跨调用互斥：dispatch_with_write_audit 全程无锁，WriteLock 只保护 pipeline CLI 状态操作、不覆盖 shenbi-dispatch；pre→post 分钟级窗口内他方对 watch 面文件的写入被错误归属为本技能 | 漏报 | P2
- 证据: executor.py:263-291（pre snapshot → dispatch → post snapshot → audit，全程零锁）；filelock_utils.py:1-9 + pipeline/cli.py:479/578/667/757（WriteLock/ReadLock 只在 pipeline CLI 命令层持有，锁对象是 pipeline-state.json.lockfile）；safe_write 的目录 flock（safe_write.py:54-61）只覆盖 safe_write 调用者，不覆盖快照读与 append-only 账本；T1 入口（`just dispatch` → shenbi-dispatch，dispatcher/cli.py）无任何互斥
- 根因: 审计拓扑按"顺序执行"设计（snapshot.py:3 docstring 自述），从未定义并发调用契约；F519 使快照根 = 框架仓库根（executor.py:30-31），r3 生产数据证明该根下的 truth/*.md 是真实进入 watch 面的活跃目录——任何并发操作者（开发者编辑、第二个 dispatch、CI 并行 round 共享 checkout）在窗口内的写入都会进入本 dispatch 的 post 快照
- 验证: 机制由代码结构确定（无锁路径 + F515 已证 added 语义无 OWNERSHIP 约束）；未构造双进程实验（需要真实 dispatch，禁跑）。归因错误的方向已由 F516（post 内容判 drift 不看本次改动）与 F529（存在即判"未声明写入"）的既有实跑覆盖其判据侧
- 影响面: 并发调用场景（运维手动并行、CI 共享 checkout）下：A 的窗口捕获 B 的写入 → A 被误判 GATE_FAIL（F529/F516 类判词）或 B 的越权被算到 A 头上——审计归属事实错误。单进程内当前无共调度（WriteLock 串行化 pipeline 命令；波内 watch 面互斥不重叠），故现实触达需操作者并发
- 建议方向: dispatch_with_write_audit 外套 round_dir/repo 级互斥（复用 filelock_utils 或 safe_write 目录锁）；或在审计行记录"窗口内非本技能进程"的归因警示
- 定级依据: P2（需操作者并发的边界缺陷；F531 已把同一场景下"记录路径损坏"的活跃面单列为 P1）
- 置信度: medium-high（结构确定，未实跑双进程）

---

## 二、误报/事实修正（对初审/r1/r2/r3 的复核）

**无整体误报。** 本轮重点复读 r3 的两条 + 抽验前三轮有实跑声称的条目，全部独立复现:

| 复核对象 | 方法 | 结果 |
|---|---|---|
| F529（r3, P0）裸 glob 不被 `_matches_declared` 认 | 实跑 `_declared_patterns('shenbi-worldbuilding')` + `_matches_declared` ×3 + 直接 fnmatch | declared 含 `truth/*.md`；`globs.get('truth/*.md')→None`；matcher False×3 / 直接 fnmatch True×3——**成立** |
| F529 契约面"10 技能 11 条" | 用**权威 load_contract** 全量扫描（初次用自写正则仅数出 6 条——正则吃不掉 dict 形多行条目；改用 loader 后**精确 10 技能 11 条**，与 r3 完全一致） | 成立；方法论注记：契约面计数必须走 load_contract，frontmatter 正则不可靠 |
| F529 生产数据（4 行/3 blocked/6 viol/21 checked；trace 3×GATE_FAIL+1×AUDIT_PASS） | 只读重计 novel-output/test-validation | **逐项一致**（并额外产出 F533 的重试实证） |
| F530（r3, P2）token_usage round-trip 丢失 | `PipelineState.from_json(s.to_json())` | `<absent>` / hasattr False——成立 |
| F516（r1, P1）pre==post 零改动仍 drift 阻断 | 构造合法 drift fixture（## hooks + ## 活跃伏笔表不一致） | BLOCKED，drift 3 条，viol 0——成立 |
| F517（r1, P1）坏 YAML 崩溃 | post 含 `{ state: <<<< broken` | CRASH: ParserError——成立 |
| F525（r2, P2）读路径 mkdir + 文件碰撞崩溃 | 临时目录构造 | `[] -> ['cost']`；`FileExistsError`——成立 |
| F526（r2, P2）非 UTF-8 快照崩溃 | 写 `\xff\xfe\x00` 字节 | CRASH: UnicodeDecodeError——成立 |
| F528（r2, P2）parametric literal vs 已解析 watch | 双形态 snapshot_tree | raw literal 见 2 章 / executor watch 仅 chapter-1——成立 |
| F522（r1, P2）logger extra= 载荷 | stdlib vs structlog 双跑 | stdlib 丢载荷 / structlog 嵌套 "extra" 键——成立 |

无新的子论断级修正。

---

## 三、覆盖空洞（本轮角度的扫描结论）

1. **审计记录路径的并发维度四轮全部缺席**（→ F531/F534/F536）: 前三轮核对了调用形状、声明面、词表、计数，从未问"record_audit_outcome 会被并发调用吗"。答案（并行波 legacy 路由 ×4 子进程）直接产出新 P1。配套测试盲区: 全仓无 TraceWriter 并发/进程竞争测试。
2. **write_safety 分类面 vs 契约面对账缺失**（→ F532）: 四轮都读过 parallel_dispatch/write_safety 的调用形状，但没人把 `_WRITE_SHARED_SKILLS`/前缀规则的判定集与 load_contract 的真实写面做双向 diff；test_parallel_dispatch_safety.py:17-26 的断言反向锁死了误分类。
3. **rc 语义/重试路径维度缺失**（→ F533）: r1-r3 追踪了 rc=2 的产生（executor.py:287-288），从未追踪 rc=2 的**消费**（重试/升级两层的放大语义）。
4. **账本 durability/字段完备性维度缺失**（→ F534）: r2 查了"谁读 write-audit.jsonl"（零读者），未查"怎么写"（fsync/锁/时间戳）。
5. 跨区观察（移交对应 zone owner，不占 Z5 编号）:
   - crash_recovery.py:66 的 `atexit.register(_emergency_cleanup)` 在**正常退出**时也会执行: 无条件把 current_step 改写为 `EMERGENCY_SHUTDOWN_AT_<...>`（:114-117，正常完成时该值为 "chapter_complete"，chapter_loop.py:1096）并 save_state——每次干净运行的状态文件都带"紧急关停"标记，污染 resume 语义与 forensic 读数。属地: crash_recovery/状态机区
   - safe_write.py:83-91 M5 回退锁的 stale-takeover：两个等待者 1s 后都 unlink+O_EXCL 重建可双双获锁（注释自认 "likely stale"）。POSIX flock 主路径下不可达；属地: safe_write 区
   - G7 坏行截断（已立 F535，属地 gates 区，建议移交）
6. 非问题确认（负结果如实记录）: (a) audit_writes/parametric_globs/load_contract 为纯读无共享可变状态——审计计算本体线程安全（竞态全部在记录路径与窗口归属，不在计算路径）; (b) `executor._truth_files_cache` 懒初始化竞态为幂等赋值，benign; (c) 并行波内 review 技能 watch 面互不重叠（各自 audits/chapter-N-<suffix>.md），无波内快照面交叉; (d) checkpoint.py 的 staging 提交逐文件走 safe_write（原子），多文件整体非事务（崩溃留部分提交）——与 F536 同族的窗口问题，影响已被 retry/escalation 路径兜住，不另立编号。

---

## 四、严重度异议表（无权改定级，仅提异议）

| 编号 | 现级 | 异议 | 理由 |
|---|---|---|---|
| F535（本轮新立） | P1（自评） | 供仲裁: P0 可辩 | 判定表 P0 含"静默错误结果"——G7 对损坏证据返回 PASS 属于门的静默错误结果；取 P1 是因正常路径需外部损坏前置（对照 F518 先例 P1）。倾向维持 P1 |
| F531（本轮新立） | P1（自评） | 无异议预期 | 判定表"并发竞态"在 P1 行；若仲裁认定 legacy 路由非生产路径可辩 P2，但该路由是 dispatch_helper 文档自述的合法回退且 test-validation 即其产物 |
| 前三轮 | — | 无新异议 | r1 对 F514 的 M→P2、r1/r2 对 F513 的弱异议维持原立场，本轮无新证据；其余定级经本轮复现印证 |
| F504/F529/F502 | P0 | 维持 | 生产/实跑证据本轮再次印证（F529 生产 3×GATE_FAIL 重算一致） |

---

## 五、验证记录汇总（本轮实跑清单）

| 验证 | 命令要点 | 结果 |
|---|---|---|
| F531 复现 | 两子进程并发 `TraceWriter(d)`+append（窗口放大 0.5s，已披露） | seq [1,2,3,3]；G7 `G7T.tamper: seq=3 signature mismatch` |
| F531 生产路径 | 行号链 chapter_loop:2541→parallel_dispatch:86→dispatch_helper:1902/1909→cli:11→executor:285→record:44 | 全部实看成立 |
| F532 | load_contract + classify 双跑 | resonance/arc-payoff 写 truth 文件却 read_only_audit |
| F532 测试锁死 | test_parallel_dispatch_safety.py:17-26 | 显式断言两技能 READ_ONLY |
| F533 生产实证 | test-validation write-audit.jsonl + trace.jsonl 只读计数 | 4 行/3 blocked/6 viol/21 checked；trace ts 相邻 1s 的 3×GATE_FAIL |
| F533 代码链 | parallel_dispatch:92-128 / chapter_loop:2864-2871,587-671 / error_handler:52-57,84-100 | rc=2 无处特判（仅评分路径分码） |
| F534 | record.py:36-39 vs writer.py:92-95 对照 + grep 读者 | 无 fsync/锁/时间戳；零程序化读者 |
| F535 | g7_trace.py:24-27 控制流 | break-on-corrupt + PASS 记录 |
| F529 复读 | matcher ×3 + fnmatch ×3 + load_contract 契约面全扫 | False×3/True×3；10 技能 11 条精确一致 |
| F530 复读 | PipelineState round-trip | token_usage `<absent>` |
| F516/F517 复读 | 合法 drift fixture / 坏 YAML | BLOCKED(3 drift) / ParserError |
| F525/F526/F528 复读 | 临时目录 | mkdir、FileExistsError、UnicodeDecodeError、双形态快照均复现 |
| F522 复读 | stdlib vs structlog | 丢载荷 / 嵌套 extra |
| 只读声明 | `git status --porcelain` | 无输出 |

## 六、汇总表

| 编号 | 标题 | 类别 | 严重度 | 与前轮关系 |
|---|---|---|---|---|
| F531 | 并行波 legacy 路由并发 record_audit_outcome → TraceWriter TOCTOU → 链分叉 + G7 误报 tamper（实跑复现） | error | P1 | 漏报（并发维度缺失；根跨区 trace/writer.py） |
| F532 | write_safety 前缀分类 vs 契约冲突：resonance/arc-payoff 写共享 truth 文件却 READ_ONLY 进并行波（测试锁死） | error | P2 | 漏报（分类面↔契约面从未对账） |
| F533 | rc=2 与瞬时失败在重试决策不可区分 → 确定性假阳性完整重试 ×3（生产 3×GATE_FAIL 实证） | error | P2 | 漏报（rc 消费端/重入语义缺失） |
| F534 | write-audit.jsonl 无 fsync/锁/时间戳，durability 与归因不对称 | error | P2 | 漏报（账本写侧纪律未查） |
| F535 | G7 坏行静默截断事件列表 → 非法行插入可绕过防篡改（跨区 gates） | error | P1 | 漏报（审计基础设施消费端） |
| F536 | 审计链无跨调用互斥，分钟级窗口写入错误归属 | error | P2 | 漏报（互斥维度缺失） |
| —（误报） | 无整体误报；前三轮关键实跑声称 10 项全部独立复现 | — | — | 无新修正 |
| —（异议） | F535 P1↔P0 供仲裁；无对前轮的新异议 | — | — | 见异议表 |

## 收敛判定

- 本轮新 finding: **6 条（P1×2, P2×4）**；发现误报: **0**。
- **未收敛——硬收敛（连续 2 轮 0 新）不成立（本轮 6 新）；软收敛（连续 3 轮无新 P0/P1 且每轮 ≤3 条）不成立（本轮出现 2 条新 P1，且超过 3 条上限）。**
- 判定依据: 第 4 轮仍以两个此前完全未开的角度产出有实跑/生产实证的 P1（F531 并发竞态、F535 审计门静默绕过），说明 Z5 周边审计基础设施（记录路径、并发调度、G7 消费端）尚未被任何前轮角度覆盖过。且 F529/F501 等 P0 未修复状态下，F533 的重试放大正在生产形态中持续发生（test-validation 已留痕）。
- 建议下一步: (1) triage F531（TraceWriter flock 或单写者化）——这是当前唯一会在合法运行中主动损坏 G7 证据链的缺陷; (2) F533 与 F529/F501 一并修（rc 语义区分后，假阳性不再被重试放大）; (3) F535 移交 gates 区 owner 复核; (4) F532 的分类器修复合并契约面对账测试; (5) 若有下一轮，建议角度: 修复后回归（F529 一行修复对 11 条裸 glob 契约的全量影响）+ trace/compaction 与 migrate 路径的崩溃恢复（本轮未展开）。
