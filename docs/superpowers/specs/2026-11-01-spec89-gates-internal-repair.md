# Spec #89 · 门禁内部性修复（gates-internal-repair）：CheckContext 一次装载、四窄助手、shared.py 出鞘、调用缝说真话

**日期**：2026-11-01（r2 修订 2026-11-02：删除对 #85 的伪依赖——CHAPTER_NUM_RE 已存在；RoundPaths 落点修正 paths.py；text 合流目标核清；**r2.2 2026-11-02 全量对抗式审计修订**——T2 grep 空判据改 AST、T3 删 ss 伪条目、T4 strip_narrative_body 归 #85、T5 正名事实更正、T6 恒真断言改集合对账；**r2.3 2026-11-14 价值门驳斥修订**——T5 主项划掉（#87 已清偿）、T4 换源清单补 4 破裂面、T6 判据强化双条件+GENERIC_ONLY_ROSTER 必需件、T3 degrade 计数 5+前缀变体、T2 口径标注 gates 全域、全部行号锚 re-anchor 至 2026-11-14 树[main 02e90e5c，其间 #85/#86/#87/#88/#95/#98-#100 已落地]；**r2.4 2026-11-14 设计审查轮 1 吸收**——T4 换源补 3 面（lint_key_reconciliation strict 锚+test_shared+test_scoring）+QUOTE_PAIR 预决方案(a)+T5 挂 AC8+lru_cache 测试协议+缺目录降级语义+T1/T2/T3 施工序+T2 lint 落 tools/ 形态+残余登记补 pipeline 域 7 处；**r2.5 2026-11-14 设计审查轮 2 吸收**——re-export 延伸至 segment_sentences（cd:28/:1129+test_shared_prose_primitives 两消费方零改）/T5 同文件表述更正/src 6 文件计数/后缀断言 f-string 包含式；**r2.6 2026-11-14 设计审查轮 3 吸收**——AC4 双 re-export 措辞对齐/T6 公式按施工终态 set(ALL_SKILLS())/degrade+load_facts_oracle 等价性 characterization 判据）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.6） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #4/#17/#18 卡（该文档为立项批次会话产物，未入库——证据以本 spec 代码锚为权威）；协调者亲验（2026-11-14 树）：`g4_chapter_drafting` 主函数 **796 行**（:584-1379，#88 finding() 改写后 +24）；`CHAPTER_NUM_RE` 在 gates/shared.py:**183** 已存在（gates/g4 与 g6 域零使用——g2.py:340 与 dispatch_helper:1736-1944 在用，非 g4/g6）；`class RoundPaths` 在 **src/shenbi/paths.py:55**（非 gates/shared）；`_ending_archetype_of`→`ending_archetype_of` **已被 #87 正名清偿**（f5aac4f6，chapter_drafting:514 公共名、pipeline/audit_context_cache.py:124 已用新名且压制已摘）；`check_chapter_title`/`check_hook_fulfillment` 被 chapter_loop.py:**3557/3565** 惰性 import（#87 拆分后漂移）

**触及的不变量维度**：无（门禁内部结构；判定语义不变——characterization 先行）

---

## 0. 根因

ADR 0008 strangler 分件完成但未剪枝：g4_chapter_drafting 单函数 **796 行**横跨 6 spec 的检查（主函数独特检查 id 实测 **23** 个，另有 mf 直发与子函数发射），逐检查重推导同一上下文（**当前章 plan 同文件每章重读 5 次**：主函数 :659/:924/:1060/:1194 四处 read_text + `_spec82_hook_rotation` 子函数 :556（经主函数 :1045 调用）再读一次；另正文自身双读 :650 `content = pf.read_text` + `word_count_md`（shared.py:331）内部再 read、`read_genre_config` 主函数内 4 次调用——T1 施工时可顺带收敛，非验收义务）。章号内联正则 gates 域 20 处。`gates/shared.py` **942 行**是单子算术楼：含写文件函数（唯二写面 = `write_gate_marker`:720-745 内 mkdir+safe_write）、import 时 FS 扫描（唯二 = `ALL_SKILLS`:778-782 / `T1_SCAFFOLD_SKILLS`:787-795 两处 iterdir）、文本原语错置（skill_utils 因此倒依赖 gates：compute_stats.py:15-21 import 5 个 gates 符号）。33 checker 间 ~10-30% 脚手架拷贝。pipeline 直连门禁内部（`g4_cross_chapter` 根本不在 build_checkers 注册表（generic.py:404-495 逐条核对）——注册表对「哪些门存在」说谎；唯一生产消费 pipeline/chapter_loop.py:1587-1590 直连）。

## 1. 任务分解（**抗过度工程裁决先行：不做 table-DSL**）

### T1 · CheckContext 一次装载（chapter_drafting）
循环顶构造 `CheckContext`（content / memo_text / chapter_no / project_root / props/counters/identity facts oracle），plan 读 1 次入 context；检查从 context 取；主函数目标 <300 行，检查体拆为该文件已会写的具名函数（`_spec82_hook_rotation` 样板）。**同域直接模板**：cross_chapter.py:37-50 `@dataclass CrossChapterContext`（构造后穿全检查）——照抄该模式，非新建范式。**拆分边界（驳斥 G1 实测）**：跨章读三族（content_uniqueness :934-963 glob 他章、_spec82_hook_rotation :565-570 前窗、micro_hook_run/payoff_density :1213-1259 前章 plan）保留在拆出的具名函数内部，context 只载当前章面；golden_slot 三点同步（:1316-1379 状态链）与 voice_density（:1270-1315）需经 context 传中间态或整块拆出。拆后主函数估 150-250 行。**characterization**：既有 cd 测试族全绿不动。
**read 计数判据先例**：tests/gates/g4/test_content_uniqueness_cache.py:19-37（monkeypatch `Path.read_text` 计数 + 断言恰 N 读）——照抄该模式钉 plan 读取。

### T2 · 章号单源采用（**无 #85 依赖**）
`CHAPTER_NUM_RE`（gates/shared.py:183）已存在，直接采用：**gates 全域**（= g4 域 15 + g6 域 5）内联 `chapter-(\d+)` 实测 **20 处**（chapter_drafting ×6 :547/:655/:918/:1053/:1190/:1207、cross_chapter ×5 :118/:730/:760/:873/:996、generic ×2 :250/:314、chapter_planning :653、decisions_validator :65、g6 :87/:421/:431、g6_checks :42/:127）→ 换常量；chapter_planning 的 `-(\d+)-plan` 分歧形态（:**889**）统一。已知残余（登记不修）：域外另有 g2.py:340 `.match`（前缀语义）、dispatch_helper :1919/:1932/:1944（别名 `_CHAPTER_NUM_RE` 已单源）、chapter_loop :384 `re.fullmatch`——三种语义变体不在本批收敛面。
**判据（r2.2 定；r2.4 落点改 tools/ 形态对齐 #85/#88 惯例）**：落 `tools/lint_chapter_num_single_source.py`（AST 遍历 `re.compile/search/match` 字符串常量，断言 `gates/` 下除 `shared.py:183` 无 `chapter-(\d+)` 字面量）+ `tests/unit/tools/test_lint_chapter_num_single_source.py`（lint 单测）+ justfile check 面接线；`chapter_no()` 内部用 `CHAPTER_NUM_RE.search`；**后缀锚点改写口径（r2.4 明确、r2.5 补边角）**：decisions_validator 的 `chapter-(\d+)-decisions\.json` 与 chapter_planning 的 `-(\d+)-plan` 改写为 `chapter_no()` + 显式后缀检查——**优先用重构字面量包含**（`f"chapter-{n}-decisions.json" in filepath` 钉精确等值；`endswith` 对 `chapter-3-plan-decisions.json` 类名字会误匹配，原连续正则不匹配——语义逐字对齐），复合字面量从源里消失，lint 断言按精确模式等值（裸 `chapter-(\d+)` 会把任意 `chapter-N-*.ext` 都匹配——这正是保留后缀断言的原因）。AST lint 防回归与 #85/#88 同级（动态构造绕过为已接受缺口——现存 20 处全为字符串字面量）。
**施工注意（驳斥 G8）**：chapter_planning.py:654 已有局部变量 `chapter_no`——同文件引入同名助手会 shadow，须改局部变量名或 import 别名。
**残余登记补全（r2.4，登记不收）**：pipeline 域 7 处在 lint 域外——parallel_dispatch.py:88（search）、helper_injection.py:52（search）、chapter_loop.py:384（fullmatch）/‌:3510（match）、dispatch_helper.py:608（aggregate 复合正则）、context_assemble.py:254（search）、text/style_fingerprint.py:38（`chapter-(\d+)\.md` 复合）——语义变体（match/fullmatch/复合）与 gates 域 search 主流不同，不属本批收敛面。

### T3 · 四窄助手（跨文件拷贝收敛，非框架）
- `chapter_no(path)`（封 T2 常量，search 语义——gates 域 20 处全是 search）；
- `load_facts_oracle(project_dir, dim)`（`load_facts + is not None and not is_empty` 三连收敛——真实面 6 处/3 文件：chapter_drafting :613(PROPS)/:617(COUNTERS)/:623(IDENTITY)、chapter_planning :725、cross_chapter :947(别名 `_lf` 形态)/:975）；
- `degrade(check_id, reason)`（「degradation visible」WARN 惯用串收敛——**r2.3 计数更正：5 个发射点**（cd :668/:695/:740、cp :735、xc :964；spec 旧值 ×6 系把 cd:166 docstring 误计）；**签名须容纳前缀变体**：`no_facts`（4 处）/`no_ledger`（cd:740）/`no_decl`（cd:706，不带该串）——助手按 (kind, check_id, what_skipped) 参数化，非硬编码单一前缀；**模板形态（r2.4）**：per-kind 前缀模板 + 允许 free-form 尾注（cd:706 尾 `(legacy-memo compat, ch17-class false-red guard)` 与 cd:740 中段 `particle_ledger.md absent` 逐字保持——现有测试只钉子串（test_f16_cp_declarations.py:103 钉 "no_facts"），字符串等价以发射点逐字对齐为准）；**等价性判据（r2.6）**：五发射点改写前后输出逐字快照断言（characterization）+ load_facts_oracle 三连行为等价 characterization——两助手不设独立 AC，依赖 AC7+本 characterization 钉死；
- `RoundPaths.require_roots()`（**落 src/shenbi/paths.py:55 的 RoundPaths**）——11 个 checker 的 7 行同体前导（含同串 ValueError）收进构造/类方法（paths.py RoundPaths 现无任何 classmethod/`__post_init__`——dataclass 标准做法，行为测试基座 tests/unit/gates/g4/test_round_paths_explicit_root.py 在场）。**调用序（r2.4）**：pacing_design 的 `if not project_dir` 启发式（:33-34）**先解析 project_dir、再调** require_roots/构造——(rd=None, project_dir=None, fps 非空) 场景行为不得改变。

### T4 · shared.py 出鞘（不重排整体，只搬错置件）
- `write_gate_marker`（:720-745）/`marker_filename`（:711）迁 `gate_manifest.py`（record_gate_result 已在彼 :108）；消费者 `scoring.py:16,281,299,307`、`gates/cli.py:116,194,202,206` 同步换源（行号 2026-11-14 精确命中）；
- 文本原语迁 `shenbi/text/`：**搬 `segment_sentences`（shared:376）+ `QUOTE_PAIR`（shared:371）两符号（r2.4 预决方案(a)——QUOTE_PAIR 本是文本原语，迁 text/cjk.py 归位；**r2.5 re-export 延伸至 segment_sentences**——shared 同时留 `from shenbi.text.cjk import QUOTE_PAIR, segment_sentences` 两 re-export 别名，保 cd:28/:1129 与 test_shared_prose_primitives.py:7/:24-29（身份断言经单对象仍成立）等既有 import 方零改；参数注入方案(b) 弃——改签名扩散 8 调用方面更大）**——`strip_narrative_body`（:338）留原处（尾部依赖 `META_BLOCK_RE`（:37）与 `strip_scene_markers`（:51），只搬它会反向 import gates.shared；其 frontmatter 面与 #85 `truth_format` 重叠、归后续批次）；**目标已核**：`text/cjk.py` 已有 `find_quote_spans`:63/`count_quote_pairs`:73/`dialogue_char_ratio`:83，本批不新建包、不动既有 cjk 函数；解开 `skill_utils/style_learning/compute_stats.py:15-21` 倒依赖块的 segment_sentences 一项（换源 `from shenbi.text.cjk import segment_sentences`；其余符号 META_BLOCK_RE/count_similes/strip_narrative_body 留待后续；QUOTE_PAIR 经 shared re-export 面不动）；
- `ALL_SKILLS`（:778-782）/`T1_SCAFFOLD_SKILLS`（:787-795）import 时扫目录改惰性函数 + `functools.lru_cache`（G0/G7 重复扫盘提速）；**降级语义（r2.4）**：惰性函数保持既有 `if SKILLS.exists() else []` 守卫——SKILLS/TESTS 目录缺失返回 `[]` 不 raise（原实现语义逐字保持）；**r2.3+r2.4 换源清单（穷尽——驳斥 G6 四面 + 设计审查轮 1 三面）**：
  - src 6 文件 11 使用点：g0.py:413/:606/:715/:720-721（+:111 import）、g7.py:45（ALL_SKILLS）/:65（**T1_SCAFFOLD_SKILLS**，同批惰性化换源面）、g_reconcile.py:76、sync_contracts.py:38、g_dispatch.py:48、dispatch_helper.py:**3082-3085**；
  - **tools/lint_contracts.py:19/:27**；
  - **tools/lint_key_reconciliation.py:54-66（r2.4 补——strict lint 面）**：两条 ReadKey 锚 grep 字面 `src/shenbi/gates/shared.py: def marker_filename` 与 `src/shenbi/gates/cli.py: write_gate_marker(`（justfile:33 `--strict` 必跑）——write_gate_marker/marker_filename 迁 gate_manifest.py 后锚须改指新址；**注意 shared 留 re-export shim 不解此面**（锚匹配字面 `def`）；
  - **tests/unit/gates/test_shared.py:30/:156/:169/:177（r2.4 补）**——`from shenbi.gates.shared import write_gate_marker` 迁后 ImportError，换源 gate_manifest；
  - **tests/unit/test_scoring.py:1261/:1268（r2.4 补）**——`from shenbi.gates.shared import marker_filename` 同上；
  - **tests/round-exec.sh:34-36**——内嵌 `parse_report_stem(f.stem, ALL_SKILLS)` 把 ALL_SKILLS 作 callable 传参，函数化后传参形态必破（TypeError），须同步改调用（`ALL_SKILLS()`）；
  - **tests/unit/gates/test_g0_dynamic_count.py:13**——`assert isinstance(ALL_SKILLS, list | set)` 须改为断言惰性函数行为；**测试协议（r2.4）**：断言调用返回 list、两次调用同值（lru_cache 生效）、「新目录可感知」断言须先 `ALL_SKILLS.cache_clear()` 再调（缓存函数上直接建目录观察不到变化——两条断言不加 cache_clear 步骤互相矛盾）；
  - **tests/unit/gates/test_g0_config_coherence.py:192**——`monkeypatch.setattr(g0mod, "ALL_SKILLS", [])` 补丁缝失效，须改为 patch 惰性函数（或 patch 其 cache）；
  - 其余 import ALL_SKILLS 的测试（test_g0.py:257/:295 + **:102 stale docstring「module-level constants」随改（r2.4）**、test_g7_reverse_coverage.py:7、test_g7.py:203、test_g_dispatch.py:68）逐点核对调用形态随改。
  - 循环 import 无虞（驳斥 G5）：惰性函数仍定义在 shared 内，消费方 import 路径不变。

### T5 · 调用缝说真话（r2.3 缩小——主项已被 #87 清偿；r2.4 挂验收）
- ~~`_ending_archetype_of`→`ending_archetype_of` 正名~~ **已完成**：#87（f5aac4f6）已正名+摘 pyright 压制（chapter_drafting:514 公共名、pipeline/audit_context_cache.py:124 已用新名）——本项划掉，git show f5aac4f6 实锤；
- 剩余：gates→gates 的 `_declared_history`（chapter_drafting:**545/:1209** 两处 `reportPrivateUsage` 压制，定义在 chapter_planning.py:75 私有）——**正名公共**（`declared_history`，domain 内两消费点+chapter_planning 自用 :117/:551 同步换）；既有 lint_private_imports 只盖 tests→pipeline 域（:31-41），gates→gates 压制无既有执法——本批正名后 chapter_drafting **零 reportPrivateUsage**（AC8）；
- `g4_cross_chapter` **文档化为非注册表门**（docs/framework/gates.md 增行：pipeline 直调 chapter_loop.py:1587-1590、需跨章上下文装配，注册表形态装不下）——AC8 第二判据；
- `verdict_fence.match_verdict_scoped` 已被两个 review checker 内部 import（review_arc_payoff:16 / review_resonance:33）——**不动**（同包内部协作，非跨包私用）；
- **登记为接受态（r2.4）**：check_chapter_title/check_hook_fulfillment 在 chapter_loop.py:3557/3565 的惰性 import——#87 拆分后既定形态、门签名稳定，不改（动机证据段引用仅作漂移记录）。

### T6 · G0.12 真实现（现为假检查——亲验 :708-725 仅计数后无条件 PASS：:714-715 纯算术，:716-723 无条件 append PASS，零验证分支）
**r2.3 判据强化（驳斥 G7：原第一判据对注入恒绿）**。`build_checkers()` 在 `g4/generic.py:404`，调用它必须 import g4——与「G0 不 import g4」互斥；且推演证明 `set(G4_CHECKER_SKILLS)==set(G4_CHECKER_KEYS)`（30=30，均 roster 声明）**捕获不了注入**：skills/ 注入带 SKILL.md 的假目录 → ALL_SKILLS 74→75（FS 扫描）而双 roster 均不变 → set==set 依旧绿。**真判据双条件**：
1. **tests 侧**：`set(build_checkers()) == set(G4_CHECKER_KEYS)` 断言已存在于 `tests/unit/gates/g4/test_build_checkers.py:8-11`（30=30，导入完整性归它）——不动；
2. **G0 侧（本批新建）**：shared.py 新增 `GENERIC_ONLY_ROSTER`（**44 项显式 frozenset** = 当前 `ALL_SKILLS − G4_CHECKER_SKILLS`，74−30；落 shared.py 使 G0 可 import——G0 不 import g4 模块[避免冷启动+把「环境检查」变成「门实现检查」]），G0.12 改真断言 `set(ALL_SKILLS()) == set(G4_CHECKER_SKILLS) | GENERIC_ONLY_ROSTER`（T4 惰性化后 ALL_SKILLS 为函数——公式按施工终态形态书写）；**红测**：monkeypatch 注入 `'fake-skill'` 进 ALL_SKILLS 面 → G0.12 FAIL；**维护语义**：新 generic 技能须显式登记 GENERIC_ONLY_ROSTER（新 dedicated 技能登记 G4_CHECKER_SKILLS）——把「隐性依赖 FS 扫描」变「显式声明」，正是假检查变真检查的意义。**第三名单面登记（r2.4，不属本批）**：skills 域自此有三对账面（skills/ 目录 ↔ master.json[lint_registry_reconcile R1] ↔ ∪G4_CHECKER_SKILLS[G0.12]）——不变量不同非重复建设；lint_registry_reconcile R1 扩展（新技能 PR 期即红、给出精确修法提示）登记为后续候选。

## 2. 验收

1. `g4_chapter_drafting` 主函数 <300 行；plan 每章恰读 1 次（**monkeypatch `Path.read_text` 计数断言 + plan 路径过滤**，先例 test_content_uniqueness_cache.py:19-37；测试输入用 tests/fixtures/ 真实项目或 tmp_path 构造结构输入——G0.9 结构性输入豁免）；
2. 章号内联正则归零（T2 判据——`tools/lint_chapter_num_single_source.py` 绿：gates 域除 shared.py:183 外零 `chapter-(\d+)` 字面量，justfile 接线）；
3. RoundPaths 前导 ValueError 同串归一（11→1；`pacing_design.py:33-34` 的 `if not project_dir` 启发式先解析后调（r2.4），行为不变；`tests/unit/gates/test_g4_signatures.py:42` 以 `match="round_dir or project_dir required"` 钉串，收敛不得改串）；
4. `gates/shared.py` 无写函数、无 import 时 FS 扫描（**新写专项 import 副作用测试**——monkeypatch `Path.iterdir` 计数后 importlib.reload(shared) 断言零调用；既有 lint_no_fs_mutation 检测不到现状，不可挂靠）；**`text/` 新增恰 2 个符号**（segment_sentences + QUOTE_PAIR，r2.4 预决方案(a)；**shared 留 QUOTE_PAIR + segment_sentences 两 re-export 别名（r2.5 延伸——保 cd:28 与 test_shared_prose_primitives 零改）**；strip_narrative_body 留原处）；**T4 换源七破裂面全绿**（round-exec.sh / test_g0_dynamic_count.py / test_g0_config_coherence.py / lint_contracts.py / **lint_key_reconciliation.py（--strict）/ test_shared.py / test_scoring.py**）；
5. **skill_utils 对 `segment_sentences` 的 import 归零**（compute_stats.py:15-21 的 QUOTE_PAIR 经 shared re-export 面不动；META_BLOCK_RE/count_similes/strip_narrative_body 留待后续——原「文本原语 import 归零」不可达）；
6. G0.12 对注入的无 checker 假技能红（红测形态：T6 双条件判据第 2 条 + monkeypatch 注入）；
7. `just check` exit 0；
8. **（r2.4）** chapter_drafting 零 `reportPrivateUsage` 压制（`_declared_history`→`declared_history` 正名）；docs/framework/gates.md 含 g4_cross_chapter 非注册表门段。

## 3. 顺序（r2.4）

**跨 spec**：#85（PR #281）与 #87（PR #331）均已归档——旧顺序约束（「#85 先落」「建议先于 #87」）已自然满足，无前置依赖。T4 与 #90（contract-data-single-source）同触 shared.py 的 roster 面：本批 T4 只惰性化 ALL_SKILLS/T1_SCAFFOLD_SKILLS + 新增 GENERIC_ONLY_ROSTER，不动 G4_CHECKER_SKILLS/G4_CHECKER_KEYS 归属（#90 的单源迁移面）——共享文件面表权威序 #89→#90 与本执行序一致。T1 与 #88（已归档）无冲突面。
**批内施工序（r2.4 补——T1/T2/T3 同文件 chapter_drafting.py）**：**T3 助手落地 + T2 换常量先行**（在完整 796 行主函数上小步替换、每步可验），**T1 大拆分后行**（拆分搬运的是已换好的形态，避免二次改写）；T6（GENERIC_ONLY_ROSTER，shared.py 纯新增）与 T4 惰性化同文件不同段，先后皆可；**T5 触 chapter_planning 正名 + chapter_drafting:545/:1209 两消费点改名（与 T1 同文件、序后无冲突）+ gates.md（r2.5 更正——非「无文件冲突面」）**；T4 触 shared.py 搬迁段≠roster 段。总序：**T3→T2→T1→T4→T5→T6**（或 T6 任意插前）。
