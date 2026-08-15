# Z6 分区独立复核报告 r2（fresh context，第 2 轮）

- 轮次: 2026-08-15 全项目深度审查 · Z6 区独立复核 r2
- 被复核对象: zone-reports/Z6.md（初审 F601-F628）+ zone-reports/Z6-review-r1.md（r1，F629-F642），共 42 条全量复读
- 清单: docs/superpowers/audit-runs/2026-08-15/zones/Z6.files（49 文件全部重读，无缺漏）
- 本轮角度（与 r1 不复用）: (a) 数值边界与数学正确性——除零/空输入/单元素/非有限浮点/百分位语义/阈值 off-by-one（含 F602 哨值 5.0 严格大于的同类系统排查）；(b) 模块间数据形状契约——producer 写的键/格式 vs consumer 读的键/格式逐一对账
- findings 编号段: F643-F699（实际使用 F643-F653，共 11 条：P1×1，P2×6，M×4，P0×0）
- 只读声明: 除本文件外未创建/修改/删除任何仓库文件；未运行 pytest/shenbi-dispatch/pipeline/git 写操作；全部动态验证在 /tmp/z6r2/ 临时目录或纯内存 import 完成（uv run python 调用纯函数）

## 汇总

| 类别 | 数量 | 说明 |
|---|---|---|
| 漏报 | 11 | F643-F653（P1×1: F643；P2×6: F644-F647, F650, F651；M×4: F648, F649, F652, F653） |
| 误报 | 0 | 42 条全部独立复核成立（8 条实跑复验 + 17 条全仓 grep 复验 + 17 条全文件重读）；另附 3 项事实性补充（非误报） |
| 覆盖空洞 | 7 | 最大项：spec 2026-08-14（Status: Design）≥9 项统计修复从未与代码实施状态对账，本轮实证 5 项仍未修 |
| 严重度异议 | 3 | F601 P1→P2（维持 r1 异议并补新证）；F618 叠加注记；F639/F643 定级界线说明 |

核心结论：**本轮两个新角度各命中一个结构性盲区。** 角度 (b) 发现 audit_drift.md 的"三写方一读方"格式契约整体断裂——pipeline 触发器 6.6 的正则对真实生产文件、skill 文档格式、Z6 CLI 格式三种写方全部零匹配（实测 0 命中），且测试用自造格式自证通过（Z4 式 checker↔writer 错配在 Z6 写侧的对应物）。角度 (a) 通过对 docs/superpowers/specs/2026-08-14-stats-determinism-design.md 的实施状态对账，实证 5 项"已设计未实施"的统计缺陷仍在代码中（空 system_terms 恒 ESCALATE、排比截断伪影、TTR 弯引号、短句链无左锚、熵词表盲区），外加 3 项该 spec 未覆盖的新边界缺陷（nan/inf 穿透、反复 off-by-one、短行部分比较）。初审+r1 的"内部正确性"与"接线对账"之后，本轮补上了"数值边界"与"跨模块键/格式契约"两个维度——42 条既有 finding 无一误报。

---

## 一、漏报（F643-F653）

### F643 | audit_drift.md 写读格式契约断裂：触发器 6.6 正则对全部三种真实写方格式零匹配 | 漏报 | P1
- 证据（均实跑）:
  - 读方: src/shenbi/pipeline/triggers.py:325 `_WARNING_RE = re.compile(r"(?:warning|drift|fatigue)\s*[:：]\s*(.+)", re.IGNORECASE)`，check_genre_config_drift（:329-351）统计重复 warning ≥3 次（DRIFT_THRESHOLD=3，:72）；接线在 check_triggers（:406-408，`state.config.genre_config_update_on_drift` 默认 True——state.py:68），flag 经 get_trigger_steps（:453）→ run_triggered_skills（:479）**在线可派发 skill**（本章循环 cli.py:225 消费）。
  - 写方 1（真实生产格式）: `uv run python` 实跑 `_WARNING_RE.findall(open('novel-output/xinghuo-ranqiong/truth/audit_drift.md').read())` → **[]**（该文件由 shenbi-review-resonance 追加 / drift-guidance 合并，格式为 `## Ch55` + `- [维度] 描述`）。
  - 写方 2（skill 文档格式）: drift-guidance SKILL.md「输出格式」规定的 YAML frontmatter（`severity: warning` 为值位、`drift_items:` 含下划线）实跑 → **[]**。
  - 写方 3（Z6 CLI 格式）: compute_drift.py:225-233 `_append_audit` 写 `- [monotonic_decline] dim: detail` 项目符号，实跑 → **[]**。
  - 测试掩盖: tests/unit/pipeline/test_triggers.py:265-274 用自造 `- warning: XYZ` 行使断言通过——**无任何生产写方产出该格式**。
- 根因: 触发器正则面向一个已不存在的历史行格式；三任写方演化后无人做写读对账（正是本轮角度 (b) 的目标形态，Z4 在 checker↔writer 键上命中 6 例，Z6 首扫即中）。
- 影响面: spec 6.6 生成配置自纠偏回路（重复警告→genre-config 更新 skill 派发）在生产永不触发，静默（无错误无日志）。
- 建议方向: 以 YAML frontmatter（写方 2）为契约，读方改 yaml.safe_load 解析 drift_items[].severity/issue；`_append_audit` 同步改写该格式或明确废弃 `--write-audit-drift`。**跨区注记**: 读方 triggers.py 与两个 SKILL.md 写方归属他区，建议聚合方将本条路由至 owning zone 合并处置（Z6 侧为 `_append_audit` 写方）。

### F644 | genre-config.json `drift_detection` 键零写入方——SYSTEM_TERMS "MUST be config-driven" 生产恒走 bootstrap 词表 | 漏报 | P2
- 证据: 读方 src/shenbi/skill_utils/drift_detection/linguistic_drift.py:62-85 load_drift_config（生产在线：compute_linguistic_metrics ← chapter_loop.py:2050）读 `genre-config.json -> drift_detection -> {system_terms, pattern_fingerprints}`；实跑 `uv run python -c "json.load(open('novel-output/xinghuo-ranqiong/genre-config.json'))"` → keys=[version,updated,fatigueWords,pacing,chapterTypes,auditDimensions,customRules,approval]，**无 drift_detection**；tests/fixtures/genre-config-example.json 同样无该键（grep 零命中）；`grep -rn "system_terms|pattern_fingerprints" skills/` → 零命中（无任何 skill 指令写此键；唯一 grep 命中 SKILL.md 处是 CLI 名 `python -m ...drift_detection` 的子串误配）。
- 根因: docstring（linguistic_drift.py:64-68 "MUST be config-driven rather than hardcoded"）的配置生产侧从未落地——F604 的镜像：F604 是 writer 死线，本条是 reader 的数据源死线。
- 影响面: 所有真实项目 M1（system_term_density）/M4（pattern_density）恒用 bootstrap 词表（"参数/系统/格式串/…/MH-/冷在场/冷知道"——单一小说的失效词汇），跨项目检测力系统性折损；且 bootstrap 的 pattern_fingerprints 在无关小说中基线恒 0，与 F618（零基线单次触发）叠加成生产常态。
- 建议方向: 在 genre-config 生成/维护 skill 中补 drift_detection 词表写入指令，或 docstring 降级声称。

### F645 | thresholds.py 阈值单一信源契约被 linguistic_drift.py 硬编码绕过，且 system_term_density_warn/hard 常量全仓零消费者 | 漏报 | P2
- 证据: src/shenbi/skill_utils/drift_detection/linguistic_drift.py:222-226 硬编码 `>100/>50/>30`，:337 硬编码 `>30`，:346 硬编码 em-dash `>20`——全文件无任何 config.thresholds import（读文件确认 import 仅 json/re/…）；src/shenbi/config/thresholds.py:38-39 定义 `system_term_density_warn=30 / system_term_density_hard=50`，docstring:37 声称 "warn → G4 WARN, hard → G4 FAIL"，但 `grep -rn "system_term" src/shenbi/gates/` → **零命中**（G4 不消费）；`grep -rn "DEFAULT_THRESHOLDS" src/` → 消费者仅 g0_config_coherence/state/config 三处，"every consumer…reads the same value"（thresholds.py:9-10）对实际密度消费者不成立。
- 根因: E11 类（阈值多源漂移）复发——thresholds.py 的创建理由（其 docstring:5-10 明记 state 50 vs skill 65 的前科）恰被本模块重演；ESCALATE=100 与 em-dash=20 甚至无对应常量。当前数值一致（30/50），尚无功能错误。
- 验证: 上述 grep（已运行）+ 两文件对照读。
- 影响面: 治理单源机制空转；未来任一侧调阈值即静默分叉（severity 判定 vs G0/G4 口径）。
- 建议方向: linguistic_drift 改 import DEFAULT_THRESHOLDS；补 ESCALATE/em-dash 常量或从 thresholds.py 删除死常量并修正 docstring。

### F646 | `_try_float` 接受 "nan"/"inf"——docstring 声称非有限返回 None；单个 nan 单元静默杀死该维度全部漂移触发 | 漏报 | P2
- 证据（实跑）: compute_drift.py:217-222 只捕 `(TypeError, ValueError)`，docstring:218 却写 "Return float(text), or None if not a finite numeric value"。`_try_float('nan') → nan`、`_try_float('inf') → inf`、`_try_float('NaN') → nan`。毒化实证: `detect_chapter_drift([90,89,88,86,84],'dim')` → `['monotonic_decline']`（对照）；`detect_chapter_drift([90,nan,88,86,84],'dim')` → **[]**——nan 使平滑/比较/均值-2σ 全部判 False，两触发器静默失效。
- 根因: 防御分支只防"不可解析"，不防"可解析但非有限"；docstring 承诺的 finite 检查从未实现。
- 影响面: 趋势表某章 score 单元为 NaN/Inf 字符串（评分 agent 输出坏值是 pending 之外又一种真实坏值形态，parse_trend 的设计目标正是容错坏单元）时，该维度从该点起漂移检测静默失明。
- 建议方向: `math.isfinite` 归一：非有限返回 None。

### F647 | compute_entropy/check_distribution/PATTERNS 词表盲区——词表外模式（含模块自身默认值"未分类"）对所有分析不可见，Σp<1 熵系统性低估 | 漏报 | P2
- 证据（实跑）: compute_pattern.py:170 主入口默认值 `"未分类"` 不在 PATTERNS（:21-35）；compute_entropy（:79-104）只对 PATTERNS 成员计数但分母 n=全部。实测: 30 章全部"未分类" → H=0.0 且 **频率和=0**（30 章整体不可见）；8 已知均匀 + 22 未分类 → H=1.0418、频率和 0.2668（词表内真值 2.0）。pattern_distribution/max_consecutive/transition_matrix 同样只枚举 PATTERNS。
- 根因: 闭集词表假设无入口校验；property 测试 tests/property/stats/test_entropy_properties.py 输入策略显式 `st.sampled_from(PATTERNS)` 并注释"input 必须取自 PATTERNS（compute_entropy 的契约）"——契约仅由测试输入策略单方面声明，代码不强制，而 main() 自己的默认值就违反它。
- 交叉印证: docs/superpowers/specs/2026-08-14-stats-determinism-design.md 子项 4（"熵分母含词表外：词表外 pattern 计分母不计分子 → 全部符号计数"）已设计修复，**Status: Design，代码未实施**。
- 影响面: LLM 判类输出任意新标签（或缺失 pattern 落默认值）时，熵/覆盖率/连续性分析静默失真（熵偏低 → 误报"单调"）。
- 建议方向: 按 spec 子项 4 实施（词表外符号计数），或入口对未知 pattern 归并+告警。

### F648 | detect_rhetoric 反复检测 off-by-one：最后一个短语起始位置不可达，章末反复检出偏低 | 漏报 | M
- 证据（实跑）: compute_stats.py:269 `for i in range(len(text) - phrase_len)` 应为 `len(text) - phrase_len + 1`——末尾 phrase_len 字符永远无法作为短语起点。实测相同重复内容置于章末 vs 章中: 反复=6 vs 9（同文本同内容，位置不同检出差 33%）。
- 根因: 窗口循环边界少 1（与 compute_ngrams:211 的 `+1` 写法同文件内不一致，后者正确）。
- 影响面: 仅假阴性（漏检章末叠句），量级小；style-learning 周期统计轻微低估。
- 建议方向: 补 `+1`；与 compute_ngrams 边界写法对齐。

### F649 | parse_markdown_table 短行部分比较：单元格数少于表头的行，其缺失键的 YAML 值静默不参与 drift 比对 | 漏报 | M
- 证据: records/drift.py:46-50 行 dict 只填 `i < len(cells)` 的键；detect_cross_section_drift（:87-92）`for key, md_val in row.items()` 只遍历行内存在的键——8 列表中截断为 3 列的行只比对 3 键，其余 5 键的 YAML↔md 漂移不可见。
- 根因: 比较方向以 markdown 行为迭代器（F606 的行级单向性的键级细化）；短行无校验告警。
- 影响面: 需要坏格式行（LLM 写表截断）；与 F606 同向叠加。
- 建议方向: 行键数 < 表头键数时报 issue 或以空串补齐参与比较。

### F650 | 空 system_terms → 空正则全位置匹配 → system_term_density≈1000‰ 恒 ESCALATE——spec 已设计修复但未实施 | 漏报 | P2
- 证据（实跑）: linguistic_drift.py:107 `re.compile("|".join(re.escape(t) for t in cfg.system_terms))` 无空表守卫。/tmp/z6r2 构造 `genre-config.json = {"drift_detection":{"system_terms":[],"pattern_fingerprints":[]}}` → 正常 14 字文本 `compute_linguistic_metrics` → **system_term_density=1071.43‰**，`detect_drift` → is_drift=True, **severity=ESCALATE**（生产后果: chapter_loop.py:2063 raise DriftEscalationError，正常章暂停全流水线等人工）。
- 根因: `re.findall("", text)` 在每个位置返回空匹配；docs/superpowers/specs/2026-08-14-stats-determinism-design.md 子项 3 明确记载此 bug 与修复设计（"空列表返回 0 + 类型校验"），Status: Design，**代码未实施**。
- 影响面: 当前生产不可达（F644: 无人写该键），但 F644 的任何修复（开始写 drift_detection 键）会立刻引爆本条——两条必须同批修复。
- 建议方向: 按 spec 子项 3 实施守卫；空表回落 bootstrap。

### F651 | 排比检测 [:20] 截断伪影——任意三个 >20 字连续句子恒判"排比" | 漏报 | P2
- 证据（实跑）: compute_stats.py:256 `a, b, c = sent_texts[i][:20], …` 后 `la=len(a)`——长度取的是**截断后**字符串。实测三个互不平行、各 ~28 字的句子 → 排比=1（应为 0）；一般地，所有 ≥20 字句子截断后长度恒 20，`abs(la-lb)/max(la,lb)=0<0.3` 恒真，每个长句三元组都被计数。正常中文小说长句遍布 → 排比统计接近"长句三元组总数"，完全失真。
- 根因: 截断本意限比较范围，却把长度度量一起截断；docs/superpowers/specs/2026-08-14 子项 6（"[:20] 截断比较 → 长句恒判平行"）已设计修复，Status: Design，**未实施**。
- 影响面: style-learning CLI 周期运行（ch%12 触发，triggers.py:399-401 在线），排比数据喂给 LLM 风格分析——与 F609 同类的"系统性失真统计"（初审对 F609 定 P2，本条对齐）。
- 建议方向: 用原始长度（或截断后仍取 `len(sent)`）比较，删除 `[:20]`。

### F652 | compute_ttr 排除串缺 CJK 弯引号——引号计入"内容字符" | 漏报 | M
- 证据（实跑）: compute_stats.py:171 排除串 `"。，！？；：''「」『』（）——……、\n"` 只有 ASCII 直引号，无 U+201C/U+201D。实测 `compute_ttr('“你好”')` → total_chars=4（两个弯引号计入内容）。
- 根因: 引号体系疏漏（与 F601/F609/F625 同族——本仓引号处理四处四种口径）；docs/superpowers/specs/2026-08-14 子项 5（"TTR 引号未排除：排除串补 “”""''"）已设计修复，**未实施**。
- 影响面: 对话密集文本 TTR 轻微失真（+2 个高频"字符"）；量级小。
- 建议方向: 排除串补 `“”`。

### F653 | `_short_chain_chars` 正则无左锚——长句尾部 ≤15 字被误计入短句链 | 漏报 | M
- 证据（实跑）: linguistic_drift.py:90 `(?:[^。！？\n]{1,15}[。！？\n]){3,}` 的首个重复可匹配**长句的尾部**。实测 `长句(28字)+仅 2 个短句` → _short_chain_chars=22（链需 3 句，实际真短句仅 2——长句尾 14 字+。被当作第 1 句种入链）。
- 根因: 无左边界锚（前句终止符或行首）；docs/superpowers/specs/2026-08-14 子项 8（"短句链无左锚：正则补锚"）已设计修复，**未实施**。
- 影响面: M3 短句链密度偏高；当基线/当前的句长分布漂移时长句尾贡献不成比例（偏移方向随分布变化），ratio 检测可被假阳性/假阴性扰动；量级二阶。
- 建议方向: 按 spec 补左锚 `(?:(?<=。)|(?<=！)|(?<=？)|(?<=\n)|\A)` 类边界。

---

## 二、误报/事实修正（对初审 F601-F628 + r1 F629-F642 全 42 条复读）

**结论: 0 条整条误报。** 复核方式与结果：

| 复核方式 | 编号 | 结果 |
|---|---|---|
| 实跑复验（本轮 /tmp 或纯函数 import） | F601（引号 0/0、破折号 1）、F602（is_drift=False）、F603（float 55.0 落盘）、F608（torn-tail JSONDecodeError）、F614（'2026'/'???'）、F618（零基线 ratio 6.0 触发）、F621（AttributeError）、F637（texture=0 落盘） | 全部成立 |
| 全仓 grep 复验（本轮实际执行） | F604（establish_baseline 零调用）、F622（三 CLI 零 skill 引用）、F629（MARK_DONE 零写入方）、F630（G3 键 + steps_done%5 材料化节奏）、F631-F636（compact/migrate/第4触发器/window-redundancy/escalation 全参/update_genre_config 零生产调用；chapter_loop.py:1029 确为 4 参调用）、F638（benchmarks/index 不存在）、F639（gate_blockers 仅读方）、F640-F642（零读方/零消费） | 全部成立 |
| 全文件重读（49/49，本轮 fresh context） | F605（trail 循环内先于落盘）、F606（仅遍历 md_rows）、F607（字典覆盖）、F609（:27 引号串+:226 逐字计数）、F610（双 except）、F611（RHETORICAL 零引用 grep 复核 + TRANSITION_WORDS 重复项在 :54 可见）、F612（无 CLI 入口）、F613（__main__ 含实质 main()）、F615（jieba.add_word）、F616（print 两处 + sys.stdout.write 7 文件——r1 的数字更正本轮复核正确）、F617（双基线路径/量纲/词表三重不一致）、F619（compact 无锁）、F620（replay 无日志）、F623（isinstance 过滤）、F624（逐事件计数）、F625（:298/:354 ASCII 正则）、F626（_identity 不升版）、F627（:50-51 裸 KeyError）、F628（:284 CWD 相对路径） | 全部成立 |

事实性补充（非误报，扩展既有条目事实面）:
1. **F603 补充**: `resonance_global_floor=True` 实测被拦截（bool 是 int 子类，`True < 60` 为 True → ConfigError），仅错误信息怪异（"floor=True < revision trigger"）——bool 路径安全，F603 的绕过面限于 float。
2. **F627 补充**: 同类裸 KeyError 还有第三处——generate.py:66 `config["format"]`（F627 只列了 :50-51 的 marketplace/type）。
3. **F609 族扩展**: 同文件 compute_ttr 的引号排除串同缺弯引号——已单独立 F652（spec 子项 5 将两者同批）。
4. **F647 与初审批注的关系**: 初审 compute_pattern 条目"正确性核验"称熵/分布推演正确——该结论仅在 input⊆PATTERNS 时成立，词表外盲区当时未测（property 测试同样只测闭集）。

---

## 三、覆盖空洞

1. **「已设计未实施」的 spec 修复从未与代码状态对账（本轮最大空洞）**: docs/superpowers/specs/2026-08-14-stats-determinism-design.md（Status: **Design**，🟡P2）列出 ≥9 项确定性助手统计修复，本轮实证其中 5 项代码未实施: 空 system_terms（→F650）、熵词表分母（→F647）、TTR 弯引号（→F652）、排比截断（→F651）、短句链左锚（→F653）；另 2 项（引号桶恒 0= F601、标点双计=F609）已在前两轮入台账——即初审"重新发现"了 spec 已知项却未发现 spec 本身，r1 亦未做 spec-status 对账。剩余子项（双实现收敛 F659、percentiles n=2 F648 等）建议聚合方一次性全量对账归档。
2. **audit_drift.md 读方与 skill 写方属他区**: F643 的 reader（triggers.py:325-351）与两个 SKILL.md 写方不在 Z6 清单；Z4 式 checker↔writer 扫描从未覆盖 truth/*.md ↔ pipeline reader 缝（本轮仅扫 audit_drift 一条即中 P1，同类缝尚有 resonance_trend 的 confidence 列被 parse_trend 忽略——无害但无人对账过）。
3. **volume_score_trend.md 零代码支持**: drift-guidance SKILL.md:139 声称"读取 truth/volume_score_trend.md…objective_achieved=false 时生成卷级漂移指导"，`grep -rn "volume_score_trend" src/` → **零命中**——skill 指令指向不存在的代码触发器（escalation 的 volume_objective_met 参数数据源同样未见衔接）。
4. **percentile n=2 倒挂的 spec↔测试立场冲突**: spec 2026-08-14 子项 9 列为待修 bug（"P75<P50 数学倒挂"），而 tests/property/stats/test_percentile_properties.py:30-36 注释明确将其文档化为 nearest-rank 方案的已接受不变量（本轮实测 n=2: P25=1,P50=2,P75=1,P95=1）。两文档一边说修一边说不修——本轮不立 finding（测试立场较新且显式），提请 spec owner 裁决。
5. **数值边界测试缺口**: _try_float 非有限（F646）、空 system_terms（F650）、词表外熵（F647——property 测试输入策略显式限定 `st.sampled_from(PATTERNS)`，结构性掩盖）、排比截断（F651）、短句链锚（F653）、parse 短行（F649）——全部无测试触达。
6. **materialize `_as_int` 字符串毒化（死路径注记）**: `_as_int`（materialize.py:18-19）对字符串 INIT payload 执行 `int(value)`——"3.5" 会 ValueError 裸崩（且 int(3.9) 截断）；因 F629（INIT 零写入方）当前不可达，随 F629 修复时一并处置。
7. **M5 对话密度双计口径（记录在案）**: compute_linguistic_metrics:120-122 对 “ 与 ” 各计一次（每轮对话 2×）+ ASCII " 计 1——混合文本权重不均。ratio 检测下中性（基线/当前同口径），当前无绝对阈值消费方；任何未来绝对阈值将继承 2× 系数。

---

## 四、严重度异议表

| 编号 | 现级 | 异议 | 依据 |
|---|---|---|---|
| F601 | P1 | **建议 P2**（维持 r1 异议并补新证） | 本轮复验 count_punctuation 生产零消费（grep 全 src 仅 find_terms 被消费）；"正常路径"不存在。若聚合方按"API 是 spec 支柱 3 规范入口、不确定取更高"保留 P1 亦可辩护 |
| F618 | P2 | 维持，附叠加注记 | F644 使 bootstrap 词表成为生产常态 → pattern_density 等零基线是**常态**而非边界——F618 的"单次出现即触发"实际位于高频路径。不单方升级（复核无权），建议与 F644 同批修复 |
| F639 vs F643 | P2 / P1 | 定级界线说明（非异议） | 两者形态相同（读方期望的数据无写方→检查恒空转），差别在 F643 下游 run_triggered_skills 派发在线（干预回路断）、F639 的 GT.3 无派发。供聚合方核对两条定级一致性 |

其余 39 条（F602-F608、F609-F617、F619-F628、F629-F638、F640-F642）定级经本轮复核未见偏移，无异议。

---

## 五、收敛判定意见

- **硬收敛（连续 2 轮 0 新）: 未达成**——本轮 +11。
- **软收敛（连续 3 轮无新 P0/P1 且每轮 ≤3 条）: 未达成**——本轮新 P1×1（F643），且总量 11 > 3。
- **判定: 不收敛，但性质可分解**: 11 条中 5 条（F647/F650/F651/F652/F653）是 spec 2026-08-14 已设计未实施项的实证（一个此前无人扫描的文档-代码状态维度，可由聚合方一次性对账归档消化）；1 条（F643）是跨区格式契约（建议路由至 owning zone）；真正的本轮新代码内在缺陷为 F644/F645/F646/F648/F649（5 条，P2×3+M×2）。**建议**: 聚合方完成三件事后进入收敛观察——(1) spec 2026-08-14 全子项实施状态入账；(2) F643 路由归区；(3) 下一轮若换新角度扫描（建议: skills/*.md 指令引用的 CLI 参数与实际 argparse 签名对账）仍 0 新 P0/P1，可宣布软收敛。

## 复核统计

- 重读清单文件: 49/49（全部 fresh 重读）
- 独立动态验证: 14 组（E1a-E1c 格式契约三格式实测、E2 nan/inf、E3 熵词表、E4 反复 off-by-one、E6 TTR 边界、E7 bool floor、E8 severity、E9 对话双计、E10 百分位扫描、E11 空 system_terms、E12-E14 spec 未实施项复现；另有 F601/F602/F603/F608/F614/F618/F621/F637 八条既有 finding 实跑复验）——动态实验均在 /tmp/z6r2/ 或纯内存，未触仓库文件
- 全仓 grep 对账: MARK_DONE/establish_baseline/compact/migrate_from_progress/check_linguistic_drift_trigger/window_redundancy/check_escalation/update_genre_config/gate_blockers/test_cycle_phase/subagent_completion_count/serialize_records/is_idempotent/count_words/count_punctuation/tokenize/DEFAULT_THRESHOLDS/system_term/gate 门内 system_term/volume_score_trend/system_terms/pattern_fingerprints/RHETORICAL/sys.stdout.write 计数——共 20+ 组（均已运行）
- 未运行（禁令遵守）: pytest、shenbi-validate/score/dispatch/pipeline、plugins 生成器、git 写操作
- 置信度: F643/F650/F651 high（实测复现 + 三方/两方证据）；F644/F645/F646/F647/F652/F653 high（实测或 grep 零命中即结论）；F648/F649 high（实测/代码机制确定，影响量级小）
