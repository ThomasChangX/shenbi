# Phase 4 抽查复核报告（§4 阶段 4：种子抽查 40/40 verified findings）

- 抽查 agent：阶段 4 抽查复核（fresh-context）
- 样本：`phase4-spotcheck-sample.txt` 全部 40 条（F117–F651），每条均打开真实文件核对证据行
- 复核方法：对每条 finding 的 zone-report 详情 → 定位证据 file:line → read/grep 源码实证（含运行时探针、生产产物 `novel-output/xinghuo-ranqiong/` 对照）
- 判定维度：证据充分性 | 结论准确性 | 严重度恰当性（按决策表复核，异议仅记录供协调者参考，不作为升级依据）
- 只读合规：未创建/修改/删除任何仓库文件（除本报告）

## 一、判定表

| ID | 证据充分 | 结论准确 | 严重度异议 | 备注（实证要点） |
|---|---|---|---|---|
| F117 | ✅ | ✅ | 无 | sync_contracts.py:40-41 `except ContractError: continue` 无日志；:89 `contracts.get(skill,{})` 被跳技能空产出；:112-121 verify_bijection 与 derive_expected_outputs 同源同一 contracts dict（docstring :104-110 亦自述"非意义检查"）→ 两处同缺断言恒过。结论成立，P2 恰当。 |
| F146 | ✅ | ✅ | 观察：M↔P2 低置信 | scoring.py:205-207 `if deps_path.exists(): json.loads(...)` 仅防缺失；调用点 :368 确认。M 可辩护（触发需 deps.json 外部损坏、fail-loud 无部分写入，与 F145 同族同 M）；按决策表字面"边界/错误处理缺陷"亦可 P2。不升级，记录。 |
| F225 | ✅ | ✅ | 无 | executor.py:99-103 仅 `load_contract(skill)["reads"]` 纯路径；`grep read_fields/filter_to_fields src/shenbi/dispatcher/` 0 命中；dispatch_helper.py:592/:1229-1230 唯二消费点均在 pipeline；AGENTS.md:87-89 契约字面确认。P2 恰当。 |
| F228 | ✅ | ✅ | 观察：P2↔P1 低置信 | audit/_shared.py:38-56 无 glob 展开（仅 resolve_or_skip N/NNN）；g2.py:44-55 `p.exists()` 对 glob 字面恒 False；9 技能 glob writes 逐一实测（worldbuilding/character-design/canon-import/import-analysis/sequel-writing/short-packaging/snapshot-manage/truth-sync/character-extraction 均在 `skills/*/SKILL.md` 命中）。重试轮（输出已存在）仍失败→按决策表可争 P1；受 F227（P1，同路径）掩盖，Z2 多轮已注低置信 P1 异议，P2 可辩护。 |
| F231 | ✅ | ✅ | 无 | review_checklist.py:183（povMode）/:187（sensitivityFlags，finding 写 :186 差 1 行，无关）；genre_config.py 模型 8 字段、fixture 9 键、ownership.py `_GENRE_KEYS` 9 键均无此二键；review-group-character SKILL.md:59 与 review-pov SKILL.md:49/74 悬空引用确认。P2 恰当。 |
| F245 | ✅ | ✅ | 观察：P2↔P1（finding 自注） | paths.py:28-42/:50-55 确认 N/NNN 一律按章节语义；resolve_volume_path 生产消费者仅 closure.py:20,158；dispatch_helper.py:656-658 对 writes 直接 `resolve_chapter_path(write_path, chapter=None)` → 抛 UnresolvedPathError（closure 卷/弧技能确定性失败，实测路径成立）。finding 自注"F227/F235 修复后可升 P1"——同意该观察。 |
| F261 | ✅ | ✅ | 无 | decisions.py:11-12 VALID_BASIS/VALID_SEVERITY 生产代码仅定义处出现（grep 实测）；`_p25` :34-35 长度检查先于 :41-42 routine_low FORBIDDEN → routine+low 超长报长度错误。不改变 FAIL 结果，M 恰当。 |
| F265 | ✅ | ✅ | 观察：M↔P2 跨区不一致 | snapshot.py:87-91 `_diff_records` `pre_by[rid].get(k) != rec.get(k)` None 哨兵确认（null 新增键不可见）；ownership.py:125-135 record_field 只查 modified_record_keys。与 Z5 F537（P2）同根家族，此处定 M——跨区严重度口径不一致，供协调者参考。 |
| F269 | ✅ | ✅ | 观察：**与 F534 完全重复且 M↔P2 不一致** | snapshot.py:64-67 `except (JSONDecodeError,TypeError): return ()` 确认；ownership.py:114-119 空集恒过；write_audit.py:61-64 owned 文件跳过 file-level 兜底。**Z2 F269（M）≡ Z5 F534（P2）：同代码行、同机制、同结论，严重度不一致**——强烈建议协调者合并并统一。 |
| F326 | ✅* | ✅ | 无 | 核心实证成立：chapter_loop.py:2405-2415 `ThreadPoolExecutor(max_workers=2)` 并发 dispatch lifecycle+state-settling；两契约均 `updates: truth/pending_hooks.md`（逐一 load 确认）；write_safety.py WRITE_SHARED 注释"must serialize"。**证据行瑕疵**："两 skill 均在 _WRITE_SHARED_SKILLS" 不精确——lifecycle 不在字面集合内，但 classify_skill_write_safety 保守默认同样归 WRITE_SHARED（:45-50），结论不受影响。P1（并发竞态 lost-update）恰当。 |
| F327 | ✅ | ✅ | 无 | `grep decide_revision src/` 仅 revision_router.py:119 定义 + 测试调用；route_chapter_revision（:86-105）blocking 形参函数体 0 使用；chapter_loop.py:1895-1904 resonance below-floor 仅 log.warning。P2 恰当。 |
| F331 | ✅ | ✅ | 无 | chapter_loop.py:2666-2677 G4 失败仅 `log.warning("parallel_post_draft_g4_failed")` 后 add_step_done+推进；对照串行 `_handle_failure`（:587-671）重试/升级。P2 恰当。 |
| F342 | ✅ | ✅ | 无 | volume_snapshot_pending 仅定义（triggers.py:647）+ docstring 引用（:536/:629）；state.py:200-222 add_audit_result/increment_retry/reset_retry 零生产调用（grep 实测仅定义）。P2 死代码恰当。 |
| F350 | ✅ | ✅ | 无 | chapter_loop.py:1875 `_create_pre_revision_backup` 在 `_route_revision_after_resonance` 顶部、路由判定之前无条件调用；:2621-2622 并行波恒调。M 恰当（每章一份冗余副本）。 |
| F351 | ✅ | ✅ | 无 | dispatch_helper.py:675-680 json_mode 仅提示词文本；`grep response_format` 全文件仅 :544 注释提及，`_call_llm_streaming_with_retry` 无实际传参。M 恰当（1 次重试浪费、无数据损坏）。 |
| F357 | ✅ | ✅ | 无 | dispatch_helper.py:611-614 注入键 `truth/style_profile.md` vs audit_context_cache.py:63-65 读取 `style/style_profile.md`——目录错位实证；注入循环 :616-618 `fname not in raw_inputs` 恒真（无契约读 truth/style_profile.md）。P2 恰当。 |
| F360 | ✅ | ✅ | 无 | chapter_loop.py:836-844 `build_index(project_dir)` 返回值丢弃、无落盘，仅 `log.info("truth_index_rebuilt")`。P2 恰当（truth-index.json 无 pipeline 内读者，非 P1）。 |
| F369 | ✅ | ✅ | 无 | cli.py:421 `parse_seed(args.seed_file)` 无 try/except；seed_parser.py:101-103 缺失路径 raise FileNotFoundError。M 恰当。 |
| F380 | ✅ | ✅ | 无 | genesis.py:77-79 step16 shenbi-anchor-curate optional=True；:218-225 optional 首败即 `optional_step_skipped`+advance；anchor-curate 契约 writes `benchmarks/anchors/AC-NNN.md`（实测）；genesis 无章节上下文 → resolve_chapter_path 抛 UnresolvedPathError → DispatchResult(False) → 跳过。P2 恰当。 |
| F392 | ✅ | ✅ | 无 | dispatch_helper.py:1113-1119 `_validate_json_output` ValueError re-raise；:1657-1663/:1760-1766 仅捕 DispatchWriteFailureError；:826-848 raise ValueError；传播链至 CLI 无兜底（cmd_next/cmd_resume 仅捕 FileNotFoundError）。P2 恰当。 |
| F394 | ✅ | ✅ | 无 | crash_recovery.py:39-42 注释"remove any atexit hooks"后仅 signal.signal×2，无 atexit.unregister（grep 0 命中）；:66 `atexit.register(_emergency_cleanup)` 无去重。M 恰当（注释漂移）。 |
| F397 | ✅ | ✅ | **同意 P0**（协调者升级恰当） | 全链实证：state-settling 契约 reads 仅 `chapters/chapter-N.md` + 6 文件 `mode: append_dedup`；`_write_parsed_outputs` :1127 `safe_write(full_path, content)` 整文件覆写、mode 仅入 log；`write_truth_file` 生产调用仅 chapter_loop.py:3014（串行 resonance 路径，F301 下不可达）；生产佐证 `truth/chapter_summaries.md` 仅 2/56 章条目。区报告定 P1（贴 P0 边界）、ledger 定 P0——按决策表"数据损坏/丢失"触发 P0，同意 P0。 |
| F399 | ✅ | ✅ | 无 | cmd_next（cli.py:588-618）无 checkpoint_history/转换逻辑；cmd_resume（:731-768）approve 分支才有 GENESIS_COMPLETE 转换与 VOLUME_BOUNDARY 延迟快照/`_update_total_chapters`；genesis.py:280-281 `step_idx >= len(GENESIS_STEPS)` 恒 True 无 checkpoint。P2 恰当（resume 可恢复，M 亦可辩护）。 |
| F3AD | ✅ | ✅ | 无 | filelock_utils.py:85（WriteLock）/:129（ReadLock）`__init__` 无条件 `mkdir(parents=True)`；cli.py:478/:798 只读命令用 ReadLock。M 恰当（纯目录副作用，无数据损坏）。 |
| F431 | ✅ | ✅ | 无 | shared.py:50-55 jload 非 dict 自抛 ValueError；g1.py:260-274 等 except 元组仅 `(json.JSONDecodeError, OSError)`（ValueError 不属 JSONDecodeError 分支）→ 8 处消费点崩溃（g1/g3/g5/g7/read_genre_config/gate_manifest 实例抽查确认）。P2 恰当。 |
| F449 | ✅ | ✅ | 无 | g_reconcile.py:40（GR.1 `== "DONE"`）/:61-62（GR.2 `!= "DONE"`）；trace/materialize.py:54 默认 `"done"` 小写、codex.py:44 `"done"`。GR.1 恒死 / GR.2 恒 FAIL 成立。P2 恰当。 |
| F463 | ✅ | ✅ | 无 | g3.py:100 `reports_dir.glob("*.json")` 无 skill_name 过滤；:107 `_compute_rubric_weighted_score(data, skill_name)` 用 gate 技能 rubric 评估全部报告。P2 恰当（跨技能互扰，需多报告共存触发）。 |
| F472 | ✅ | ✅ | 无 | gates/cli.py:104-110 `rd = arg(2, None)` 解析后未传给 `gate_G4_bughunt(file_list)`/`gate_G4_clean(file_list)`；generic.py:32 `resolve_input_path(fp, rd)` rd=None → shared.py:68-73 抛 ValueError（相对路径）。P2 恰当。 |
| F482 | ✅ | ✅ | 无 | chapter_drafting.py:58-66 docstring 声明"Thematic naming encouraged (1-4 Chinese characters)"；:67-93 实现仅 第\d+章/重复/星期标签三检查，无长度/主题化逻辑。M 恰当（docs 漂移）。 |
| F487 | ✅ | ✅ | 无 | chapter_drafting.py:146-148 正则 `^name:` + :150-158 YAML frontmatter 双源 append 同名（标准 protagonist.md 100% 触发）；:128 `sum(text.count(name)...)` 翻倍。P2 恰当（fail-open 方向、检查质量退化）。 |
| F498 | ✅ | ✅ | 观察：P2↔P1 低置信 | g5.py:153 `(\d+)\s*(?:...)` 单捕获组、:159 `m.group(2)` IndexError、:171-172 `except Exception: continue` 吞掉 → G5.3 numeric 永不填充；test_g5.py:139-163 显式钉死惰性行为并注释 "source bug"（读码确认）。"测试钉死缺陷"字面贴近 P1"测试失效掩盖真实缺陷"，但测试有显式文档注释（非静默合成形状掩盖），P2 可辩护。 |
| F4A0 | ✅ | ✅ | 无 | g6.py:240-253 约束提取、:262 `constraints[:10]`、:265 `"人" in ctx or "个" in ctx` 过滤、:267-269 `ctx.split(str(val))[0]` 首个数字子串错配机制（"5"∈"500" 场景）全部读码确认。P2 恰当（检查器↔真实格式漂移、静默漏检方向）。 |
| F513 | ✅ | ✅ | 无 | executor.py:25-26 `PROJECT_DIR = REPO_ROOT`（框架仓库根）；:244/:264 `snapshot_tree(PROJECT_DIR, watch)` 而非 round_dir；技能实际写 round_dir（codex `-C round_dir`）→ 审计比对错树、violations 恒空。P1 恰当（唯一执行路径审计静默全过）。 |
| F527 | ✅ | ✅ | 观察：**与 Z2 F233 跨区重复** | ownership.py:52-71 `_HOOK_KEYS_NEW_RECORD` 16 键零消费（grep 实测）；:120-124 record_create 分支只查 deleted_record_ids/modified_record_keys，从不校验新记录键集；snapshot.py:82-94 无键集通道。**与 Z2 F233 为同一 finding 的跨区独立发现**——供协调者合并。P2 恰当。 |
| F530 | ✅ | ✅ | 无 | escalation_bridge.py:19-21 `val = float(cells[6]); if val > 0: scores.append(val)` 0 分被过滤确认。M 恰当（dead-wire 桥上下文，无现行生产影响）。 |
| F534 | ✅ | ✅ | 观察：**与 F269 完全重复且 P2↔M 不一致** | snapshot.py:64-67 JSONDecodeError→() 确认；OWNERSHIP field 文件被覆写为非法 JSON → field 级零违规。**与 Z2 F269 同代码行、同机制，严重度 P2（Z5）vs M（Z2）不一致**——合并时须统一。 |
| F537 | ✅ | ✅ | 观察：**与 Z2 F260 跨区重复且 P2↔M 不一致** | snapshot.py:73-75 `a.get(k) != b.get(k)` 缺键↔null 值归并确认；新增/删除 null 值键零检测。**与 Z2 F260（M）同 finding，Z5 定 P2**——供协调者合并统一。 |
| F612 | ✅ | ✅ | 无 | linguistic_drift.py:218-229 `is_drift = max_deviation_ratio > 5.0` 与 severity 绝对阈值（>30/>50/>100）正交；chapter_loop.py:2023-2043 全部干预（含 ESCALATE raise）在 `if result.is_drift:` 门内。baseline 被污染（base 60‰/current 110‰ → ratio 1.83）时 ESCALATE 被吞成立。P1 恰当（安全网静默失效，契约 07-19-07 明示）。 |
| F625 | ✅ | ✅ | 无 | versioning.py:33-38 `while e.schema_version < CURRENT_VERSION: up = MIGRATIONS.get(..., _identity); e = up(e)` — _identity 不改变版本 → 无限循环。P2 恰当（当前潜伏：CURRENT_VERSION=1、无生产调用，扩展点启用即 hang）。 |
| F651 | ✅ | ✅ | 无 | records/parser.py:37-45 `yaml.safe_load(body)` 无重复键检测；PyYAML SafeLoader last-wins 为既定行为（`state: A`+`state: B`→B）。P2 恰当（权威记录源静默视图损失；当前真实数据无 `## hooks` 故潜伏，F637）。 |

> ✅* = 证据行有一处轻微不精确（见备注），不影响结论成立。

## 二、抽查统计

| 维度 | 通过 | 存疑 | 失败 |
|---|---|---|---|
| **证据充分性** | 40 | 0（F326 轻微证据行瑕疵，仍成立） | 0 |
| **结论准确性** | 40 | 0 | 0 |
| **严重度恰当性**（含跨区重复/一致性观察） | 30 | 10 | 0 |
| **综合判定** | **30** | **10** | **0** |

- **证据充分性：40/40 通过**。全部证据 file:line 真实存在且支持结论；F326 的唯一瑕疵（lifecycle 不在 `_WRITE_SHARED_SKILLS` 字面集合内，但保守默认归类等价）不影响结论成立。
- **结论准确性：40/40 通过**。未发现结论与证据脱节、过度推断或结论性错误；行号漂移仅 2 处（F231 :186→:187、F245 无）且均无关紧要。
- **失败：0**。未发现任何证据缺失、证据矛盾或结论不成立的 finding。

### 存疑清单（10 条，均为记录性观察，供协调者参考，非升级依据）

1. **跨区重复且严重度不一致（需合并统一，3 对）**：
   - **F269（M，Z2）≡ F534（P2，Z5）**：`_changed_top_keys` JSONDecodeError 静默返回 ()——同代码行、同机制、同结论，严重度 M vs P2；
   - **F260（M，Z2）≡ F537（P2，Z5）**：`_changed_top_keys` null 值键归并——同 finding，M vs P2；
   - **F233（P2，Z2）≡ F527（P2，Z5）**：record_create 不校验新记录键集、`_HOOK_KEYS_NEW_RECORD` 死配置——同 finding，严重度一致但应去重。
2. **可争 P1 的低置信观察（4 条，均被更早缺陷掩盖或测试有显式文档）**：F228（9 glob 技能任何轮次 G2 不可过，受 F227 掩盖）、F245（closure 4 技能确定性失败，finding 自注 F227/F235 修复后可升 P1）、F498（"测试钉死 source bug" 贴近 P1 触发条件，但测试有显式注释）、F146（M 按决策表字面可 P2，触发需 deps.json 外部损坏且 fail-loud，M 可辩护）。
3. **跨区严重度口径不一致（1 条）**：F265（M）与同根家族 Z5 F537（P2）口径不一致。
4. **F326 证据行瑕疵（1 条）**：见上，结论不受影响。

## 三、最终消息（抽查统计摘要）

**阶段 4 抽查复核完成：40/40 样本全部核对真实源码，证据充分 40、结论准确 40、失败 0；综合判定 通过 30 / 存疑 10 / 失败 0。** 重点确认：F397（P0，数据丢失）全链实证成立且协调者升级恰当；F513（P1，审计快照根错位）、F612（P1，安全网门控失效）、F326（P1，并发竞态）均证据充分。需要协调者处理的主要事项：3 对跨区重复 finding（F269≡F534、F260≡F537、F233≡F527）应合并并统一严重度（前两对 M↔P2 不一致）；其余存疑均为低置信 P1 边界观察（F228/F245/F498）与轻微证据行瑕疵（F326），不影响 findings 成立性。
