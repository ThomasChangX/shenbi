# Z7 分区初审报告（agent d）— tests/property/ + tests/skill-behavior/ + tests/skill-triggering/

- 日期：2026-08-14
- 范围：`docs/superpowers/audit-runs/2026-08-14/zones/Z7-d.files` 全部 52 文件（deep-read 52/52）
- 只读约束：仅执行 grep / git / read / diff / python -c 只读分析；未创建/修改/删除任何仓库文件（本段文件除外）；未 git add/commit。
- 编号段：F850–F861（12 条 finding）

## 0. 总体结论

Z7-d 覆盖三类测试资产：**property 测试**（19 文件，47 个测试函数，Hypothesis）、**skill-behavior 测试**（21 个 .md 行为场景）、**skill-triggering 测试**（12 个 .md 路由场景）。

- **property 测试整体质量较高**：cjk/stats/drift/gates/trace 五组不变量与实现逐一核验一致（compute_drift 排除语义、compute_entropy 归一化、compute_percentiles P50==median、G3.4 fail-closed、CapabilityFS 只读、trace hash 链），无 mock 滥用（全部直测真实函数），无 skip/xfail（d1-11 清点 0 命中本区）。`d1-01-just-check.log` 真实运行 2814 passed 中本区全过；`pytest --collect-only` 全量收集 47 函数。
- **`.hypothesis/examples` 失败样本核对**：实际工件为 12 个 patch 文件（2026-06-30，共 **17 个** `@example(...).via('discovered failure')`）+ 11 个 **0 字节** example 文件（全部未跟踪）。任务描述的"44 个失败样本"与实际不符。17 个已发现失败**全部在当前提交的测试代码中得到修复**（`\r`/`\ud800` → `blacklist_characters="\r\n"` + `blacklist_categories=("Cs",)`；`''`/`'主'` → 空串守卫；`[1,2]` → P50 改 `values[n//2]`；`['引入','升级','转折']` → 熵上界 +1e-4 容差），逐例验证通过。
- **结构性大问题（F850）**：`tests/skill-behavior/` + `tests/skill-triggering/` 全部 33 个 .md 文件是 `tests/tiers/t1-skill/<skill>/bug-hunt/input/` 场景的**精确重复副本**（38 对 diff 全部 IDENTICAL；`tests/ARCHIVE-MIGRATED.md` 记录迁移，原文"保留供参考"）。运行时只消费 tiers 树（G0.8 扫描 `TESTS/tiers/t1-skill`，dispatcher 按 `test_type=bug-hunt` 派发），pyproject `norecursedirs` 把两个目录排除出 pytest——即本区 33 个 .md 是**非执行参考副本**，无同步机制 → 双源漂移隐患。
- **skill-behavior/skill-triggering 与 SKILL.md 契约一致性**：36 个技能名全部真实存在；主要语义（OOC=error、过期伏笔=error、备忘一致、蓄压释放=warning、spot-fix/rewrite 路由、±15%、eraResearch 激活、canon 严格度）与 SKILL.md 一致；但存在 ① 铁律编号系统性漂移（测试引"铁律1/2/3"与现 SKILL.md 的 铁律2/4 错位，且"培育超期=warning"在 SKILL.md 无对应铁律，F853）② phase3-plant-track-resolve 内部算术自相矛盾（CP 债务 18 vs 12，F851）③ revision-mode-routing 期望混合策略与 SKILL.md"混合→rewrite"冲突（F852）④ 触发路由歧义（F855）⑤ 快照"11 个 truth 文件"硬编码（F854）。
- **property 套件真实性问题**：2 个空转属性测试（F856 word_count_md 无 CJK 字符策略、F857 drift 升序序列永不触发递减）+ 1 个伪属性测试（F858 `@given(st.data())` 未使用）+ 1 处陈旧注释（F859 54→70）。
- **flake 风险**：trace 链测试未设 `deadline=None`（全套件唯一例外），dev profile（默认 deadline=200ms）下 20 次 fsync/example 可能超时（F860）；CI profile（`conftest.py` `deadline=None`）下无风险。

### 覆盖缺口（d1-06）处置总说明

`d1-06-coverage-gaps.txt`（真实 85.16% 版本，见 d1-baseline.md 更正记录 2）**不含 tests/property / tests/skill-behavior / tests/skill-triggering 任何条目**（grep 0 命中）——该清单按 src/ 未覆盖行组织，测试文件本身不产生覆盖条目。本区处置方式为：property 测试作为 src 模块的**增量覆盖层**（cjk.py / compute_drift.py / compute_pattern.py / compute_stats.py / capability_fs.py / g3_independence.py / gates/shared.py / trace/writer.py / trace/replay.py / contracts/legacy.py / gates/g0.py），其覆盖缺口即"空转属性"（F856/F857）与"伪属性"（F858）——属性测试声称检查的路径未被真正生成。skill-behavior/skill-triggering 为 .md 场景，无 pytest 覆盖概念；其"执行缺口"是 F850 的重复副本问题（权威版本在 tiers，本区副本不执行）。

---

# 一、tests/property/（19 文件）

### tests/property/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 目录占位（0 字节文件存在，`ls -la` 确认）✓
- findings: 无
- 验证命令: `ls -la tests/property/.gitkeep`（`-rw-r--r-- 0`）
- 置信度: high

### tests/property/__init__.py
- 处置: deep-read
- 声称检查的不变量: 包 docstring `"""Shenbi property test package."""` ✓；无代码
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/cjk/__init__.py
- 处置: deep-read
- 声称检查的不变量: 包 docstring ✓；无代码
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/contracts/__init__.py
- 处置: deep-read
- 声称检查的不变量: docstring 声明"三表（REGISTRY 派生）一致（spec 支柱五；判据 5）"——见 F858 的"三表"实际仅两独立源
- findings: [F858]
- 验证命令: read；`src/shenbi/contracts/registry.py:17-26`（bootstrap_registry 内部调 load_registry）
- 置信度: high

### tests/property/drift/__init__.py
- 处置: deep-read
- 声称检查的不变量: docstring "drift 排除/触发不变量（spec 支柱五）" ✓ 与 test_drift_properties.py 内容一致
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/gates/__init__.py
- 处置: deep-read
- 声称检查的不变量: 空文件（0 字节）✓
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/stats/__init__.py
- 处置: deep-read
- 声称检查的不变量: docstring "算术统计不变量（spec 支柱五）" ✓
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/trace/__init__.py
- 处置: deep-read
- 声称检查的不变量: docstring "trace hash-链不变量" ✓
- findings: 无
- 验证命令: read
- 置信度: high

### tests/property/cjk/test_cjk_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_find_terms_substring_found`：text 前 2 字符必被 find_terms 命中（find_terms 精确子串语义，cjk.py:23-41；term=text[:2] 在位置 0 必命中）✓
  - `test_punctuation_matches_all_tokens`：破折号/省略号整 token 计数 == 实现（cjk.py:58-70 逐桶 `sum(text.count(token))`）✓ ——与 test_punct_properties.test_each_punct_count_matches_text_count 断言重复（冗余但无害）
  - `test_mixed_ge_cjk_only` / `test_count_words_non_negative`：count_words mixed = cjk+latin（cjk.py:77-82）→ 平凡成立（构造性真，非独立不变量）
  - 无 @settings：继承 profile（CI max_examples=1000/deadline=None；dev 100/200ms）——函数极快，无 flake
  - 覆盖缺口：无（cjk.py 由本文件 + unit 覆盖）
- findings: 无（冗余断言记入文件内说明，不单列）
- 验证命令: `read src/shenbi/text/cjk.py:23-82` 逐函数比对
- 置信度: high

### tests/property/cjk/test_g612_embedded_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - G6.12 内嵌必检出：pre+term+post 拼接后 find_terms 命中且 hits[0].term==term ✓——依赖 cjk_pad 字母表（"在这个时代悄然兴起运动发展和平"）与 term 字母表（革命/暴动/起义/敏感词）**不相交**（逐字符核验无重叠），保证 hits[0] 是内嵌项而非 pre 内误命中；若未来字母表改动引入交集，测试将 flake——当前成立
  - `test_old_word_boundary_regex_fails_on_embedded`：旧 `[^\w]` 正则对纯 CJK 内嵌不命中（CJK 全为 \w）→ `assert old is None` 钉死 bug 行为 ✓ 与 cjk.py docstring（:24-27 "Replaces broken \w-anchored regex"）一致
  - `test_find_terms_hit_position_correct`：start==len(pre)、end==len(pre)+len(term)——同字母表不相交前提 ✓
  - max_examples 200/20/100 + deadline=None，无 flake
  - 覆盖缺口：无
- findings: 无
- 验证命令: `read src/shenbi/text/cjk.py:23-41`；字母表逐字符交集检查（python -c）
- 置信度: high

### tests/property/cjk/test_punct_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - 整 token 计数：counts[name] == Σtext.count(token)（cjk.py:67-70 实现同构）✓；docstring 对照 compute_stats.compute_punctuation 的 per-char 重复计数 bug（F604 已入 ledger）——本测试钉死正确实现 ✓
  - `test_dash_counted_once_not_per_char`：'——' 整体计数 ✓（cjk.py:49）
  - 策略字母表 = PUNCTUATION_TOKENS 全部 token 字符 + CJK + "level123 空格"，min_size=0/max_size=80 ✓
  - max_examples 200/200/100 + deadline=None ✓
  - 覆盖缺口：无
- findings: 无
- 验证命令: `read src/shenbi/text/cjk.py:44-70`（PUNCTUATION_TOKENS 与 count_punctuation 逐字一致）
- 置信度: high

### tests/property/cjk/test_tokenize_frozen.py
- 处置: deep-read
- 声称检查的不变量:
  - 冻结基线（jieba==0.42.1，pyproject.toml:10 精确 pin ✓）：4 条文本的 words/POS 硬编码，用**隔离 Tokenizer**（`jieba.Tokenizer()` + `pseg.POSTokenizer(_t)`，:12-14）规避 cjk.tokenize 的全局 jieba.add_word 污染（cjk.py:100-103 已知全局变异）✓ 设计正确
  - `test_tokenize_preserves_chars_concat`：全局 tokenize 拼接==原文（_FROZEN 文本无空白，`if w.strip()` 过滤不丢字）✓
  - `test_tokenize_is_deterministic` / `test_tokenize_concat_equals_input`：策略字母表无空白字符（"主角缓缓走向古老大门光明黑暗耐心修炼需要"）→ `w.strip()` 过滤不破坏拼接；空串由 `if not text.strip(): return` 守卫（:87-88）✓；`''`/`'主'` 两个历史失败样本（patch b3ff1435/0db60c3d）当前均通过
  - 覆盖缺口：无（determinism/concat/冻结三层）
- findings: 无
- 验证命令: `grep -n "jieba" pyproject.toml`（`jieba==0.42.1`）；逐例重算 `''`、`'主'` 走查；read cjk.py:93-104
- 置信度: high

### tests/property/contracts/test_registry_consistency.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_three_registry_sources_agree`：yaml 直读 concepts == load_registry().concepts == bootstrap_registry() keys。**实测 70==70==70**（非 docstring 声称的 54==54==54，F859）。`br` 由 `bootstrap_registry()` 内部调用 `load_registry()` 派生（registry.py:24-31）→ **br==lr 是构造性成立**，"三表独立一致"实为两独立源（yaml 直读 vs pydantic 解析）+ 一个派生映射（F858）；仍能捕获 pydantic 校验丢条目/重名键收缩等缺陷 ✓
  - `test_every_truth_file_has_kind`：参数化（70 条），kind 非空 ✓
  - `test_bootstrap_subset_of_yaml`：`@given(st.data())` 但 `_data` 未使用——**伪属性测试**（确定性断言套 hypothesis 外壳）（F858）
  - 覆盖缺口：无（三断言覆盖三种读路径）
- findings: [F858, F859]
- 验证命令: `python3 -c` 实跑三源计数（70==70==70）；`read src/shenbi/contracts/registry.py:17-31`（bootstrap 派生）；`read src/shenbi/contracts/legacy.py:93-115`（REGISTRY_PATH==truth-files.yaml，legacy.py:32）
- 置信度: high

### tests/property/drift/test_drift_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_monotonic_decline_span_excludes_overridden`：excl 索引处 run/start/prev 重置（compute_drift.py:92-93）→ 递减跨度 [start,i] 必与 excl 不交；detail 格式 `chapters {start+1}-{i+1}` 与正则 `chapters (\d+)-(\d+)` 匹配 ✓；**不变量与实现逐行核验成立**（excl 重置 start=i+1 保证跨度不含被排除章）
  - `test_excluding_all_decline_indices_suppresses_finding`：**空转**（F857）——`.map(sorted)` 升序序列永不产生递减（`v < prev` 恒假，compute_drift.py:95），排除是否起作用根本无从验证
  - `test_volume_decline_iff_last_below_second_to_last`：与实现（compute_drift.py:139 `scores[-1] < scores[-2]`）逐字等价 ✓（floats 禁 NaN/Inf，无边界坑；`-0.0<0.0` 双侧同算）
  - `test_volume_decline_at_most_one_finding`：实现至多 1 finding ✓；kind/dim 断言 ✓
  - 策略 excl ∈ [0,19] 集合 max_size=8，与 len(raw)∈[0,20] 兼容；无 filter 健康检查问题
  - 覆盖缺口：排除语义的真实反向路径（被排除章夹在递减序列中间）**未被生成**（F857 同根）
- findings: [F857]
- 验证命令: `read src/shenbi/skill_utils/drift_detection/compute_drift.py:68-147` 逐行比对；`python3 -c` 走查 excl 重置语义
- 置信度: high

### tests/property/gates/test_capability_fs_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - roundtrip：`\r`/`\n` 与 surrogate（Cs）已被 blacklist（:16）——3 个历史失败样本（patch 3eb9828e/504577a4 等 8 个 patch）的根因（Path.write_text 通用换行翻译 + UTF-8 无法编码 surrogate）全部修复 ✓
  - 写侧全拒：write_text/write_bytes/unlink/mkdir 均 PermissionError（capability_fs.py:44-54）✓
  - 沙箱越界拒绝：`inside` 为 root 时读 `outside` → PermissionError/FileNotFoundError ✓（capability_fs.py:22-29 resolve+relative_to）
  - `function_scoped_fixture` HealthCheck 抑制 ✓（tmp_path+@given 组合的必要处理）
  - 覆盖缺口：无（capability_fs.py 100%，Z1 报告已核）
- findings: 无
- 验证命令: `read src/shenbi/capability_fs.py` 全 54 行；对比 8 个 patch 的失败样本逐例确认 blacklist 生效
- 置信度: high

### tests/property/gates/test_g34_independence_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - fail-closed 双路径：无 current_scorer_agent → FAIL（g3_independence.py:20-22）；空 progress → FAIL ✓
  - 同源自评 → FAIL（:26 `str(gen) == str(scorer)`）✓
  - 异 agent → PASS 且 reason==""（:27-28）✓；`assume(scorer != gen)` + `filter_too_much` 抑制 ✓（ascii+digits ≤20 字符，碰撞概率可忽略）
  - 有 scorer 无 gen trace → PASS（:24-25 非 dict/缺 skill 键走不到同源判定）✓
  - **接线核验**：g3.py:197-198 确实调用 scoring_independence_status（docstring "已接线" 属实）✓
  - 覆盖缺口：无
- findings: 无
- 验证命令: `grep -n "scoring_independence_status" src/shenbi/gates/g3.py`（:15 import, :198 调用）；read g3_independence.py 全 28 行
- 置信度: high

### tests/property/gates/test_gate_invariants.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_word_count_md_always_non_negative`：docstring 声称 "Chinese chars counted"，但策略字母表 = ascii_letters + " \n。！？，、"（:33）**不含任何 [一-鿿] CJK 字符** → word_count_md 恒 0（shared.py:122 `len(re.findall(r"[一-鿿]", c))`）→ **空转**（F856）
  - `test_normalize_file_paths_returns_list` / `test_count_transition_words_returns_non_negative`：与实现（shared.py:170-179, 314-331）一致，前者含 None/str/list/tuple 分支但策略只生成 list——分支覆盖靠 unit 测试补 ✓
  - `test_jload_round_trips_dict`：dict→写→jload 读回 ✓（shared.py:44-55 要求 dict；str→int 值可 JSON 化）✓
  - `test_gate_g0_returns_valid_json_for_empty_seed`：gate_G0(seed_file=None) → g0.py:177-179 早退 `passed("G0", checks)`（G0.1 SKIP）→ JSON 含 gate/status ✓；**钉死了 F407（Z4 已录：G0 无 seed 早退空转 PASS）的行为**——属性测试把该缺陷固化为期望
  - 覆盖缺口：word_count_md 的 CJK 计数路径（F856）
- findings: [F856]
- 验证命令: `read src/shenbi/gates/shared.py:100-122,170-179,314-331`；`read src/shenbi/gates/g0.py:153-179`（无 seed 早退）；`python3 -c` 验证策略字母表无 CJK
- 置信度: high

### tests/property/stats/test_entropy_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_present_counts_sum_to_n`：输入 ⊆ PATTERNS（compute_pattern.py:21-35），Σcount==n 精确成立 ✓
  - `test_entropy_matches_recompute`：源（compute_pattern.py:79-104）累计原始熵后一次性 round(.,4)；测试同样 Σ 后 round——完全同构 ✓
  - `test_entropy_bounded_non_negative`：0 ≤ H ≤ log2(k)+1e-4；round 上行 ≤5e-5 < 1e-4 容差 ✓；历史失败样本 `['引入','升级','转折']`（patch d80c2f23）验证：H=1.585 ≤ log2(3)+1e-4=1.58506 ✓
  - `test_single_pattern_zero_entropy`：单模式 H==0.0 ✓（p=1, log2(1)=0）
  - 覆盖缺口：无
- findings: 无
- 验证命令: `read src/shenbi/skill_utils/chapter_pattern/compute_pattern.py:79-104`；`python3 -c` 复算 1.585 vs 1.58506
- 置信度: high

### tests/property/stats/test_percentile_properties.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_p50_equals_median_index`：P50==vs[len//2]（compute_stats.py:102 `values[n // 2]`）✓——docstring 记录旧 bug（`int(n*0.50)-1`，n≥2 偏移）；历史失败样本 `[1,2]`（patch 5f8569c5/d74d3bc6）：旧实现 P50=values[0]=1 vs median=values[1]=2；新实现 P50=values[1]=2==median ✓ 修复确认
  - `test_p50_equals_sentence_stats_median`：compute_sentence_stats 内部 sort + median=lengths[n//2]（:112-115）与 compute_percentiles 同索引 ✓
  - `test_percentiles_within_range`：nearest-rank 索引 `max(0, int(n*x)-1)` ∈ [0,n-1] → 值 ∈ [min,max] ✓；docstring 正确解释了 P25<=P50 但 P50>P95 的可能（n=2 时 P50=values[1]、P25/P95=values[0]）——不变量选型正确（未错误断言单调性）
  - `test_percentiles_empty_returns_zeros`：实现（:95-96）一致 ✓
  - 覆盖缺口：无
- findings: 无
- 验证命令: `read src/shenbi/skill_utils/style_learning/compute_stats.py:93-142`；`python3 -c` 复算 n=2 各百分位
- 置信度: high

### tests/property/trace/test_chain_invariants.py
- 处置: deep-read
- 声称检查的不变量:
  - `test_chain_always_verifies`：写任意 A/B/C 序列 → replay 全签名通过、seq==1..n（event.py:47-50 sha256 链；writer.py:80-99 每事件 sign_and_new 链 prev；replay.py:38-46 校验）✓
  - `test_tamper_any_field_breaks_chain`：改 target → canonical_payload 变（event.py:33-38 排序键）→ _verify 失败 → replay 截断返回 [] ✓；注意 replay 会触发 safe_write 截断副作用（replay.py:47-48）——测试只断言返回值，可接受
  - **flake 风险（F860）**：两测试均未设 `deadline=None`（全 property 套件唯一例外）；TraceWriter.append 每次 fsync（writer.py:92-97），单 example 最多 20 次 + TemporaryDirectory 创建；dev profile（conftest.py:12 `deadline=200`）下可能超 200ms 抖动；CI profile（conftest.py:11 `deadline=None`）无风险
  - 覆盖缺口：无（正链 + 篡改双路径）
- findings: [F860]
- 验证命令: `read src/shenbi/trace/event.py:19-50`（_SIGNED_FIELDS 不含 signature）；`read src/shenbi/trace/writer.py:76-99`；`read tests/conftest.py:9-14`（ci/dev profile）
- 置信度: high

---

# 二、tests/skill-behavior/（21 文件）

**共同背景（F850）**：21 个文件全部是 `tests/tiers/t1-skill/<skill>/bug-hunt/input/` 场景的逐字重复（diff 全部 IDENTICAL，迁移记录见 `tests/ARCHIVE-MIGRATED.md`）。运行时（G0.8、dispatcher bug-hunt 派发）只读 tiers 树；pyproject.toml:416-417 将本目录排除出 pytest。以下各文件按"场景真实性 / 与 SKILL.md 契约一致性 / 内部一致性"三查。

### tests/skill-behavior/review-catches-bug/phase2-character-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：OOC 植入（档案"谨慎谋定后动" vs 无动机转变的孤身冒进）自洽；输入节选与植入表/期望输出/通过条件互指一致 ✓
  - 契约一致性：`shenbi-review-character` 存在；OOC=blocking error（SKILL.md 铁律2:64）与测试"标记 ERROR 不是 WARNING"一致 ✓；输出格式（BDI/OOC/配角/声音/弧线/评分/修复）与 SKILL.md 输出格式节一致 ✓
  - 通过条件含"评分 ≤ 5/10"，期望输出 2/10 ✓ 内部一致
- findings: 无（F850 共同）
- 验证命令: `read skills/shenbi-review-character/SKILL.md:61-110`；`diff` 与 tiers 副本
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase2-continuity-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：正午→太阳西沉同章无时间过渡，矛盾植入清晰；推断时间表（正午 vs 17:00-18:00）自洽 ✓
  - 契约一致性：`shenbi-review-continuity` 存在；ERROR 级别与连续性硬错误语义一致 ✓
  - 评分 3/10 ≤ 5/10 通过线 ✓
- findings: 无（F850 共同）
- 验证命令: read + diff
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase2-foreshadowing-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：双 bug 植入（hook-001 resolve 备忘未兑现 + hook-002 培育超期）计算核验：hook-001 种植 50/max_distance 30/本章 100 → 50>30 EXPIRED ✓；hook-002 last_reinforced 85/cultivation_interval 10/本章 100 → 15>10 OVERDUE ✓；期望表与数字一致 ✓
  - 契约一致性：`shenbi-review-foreshadowing` 存在；"备忘必须与正文一致"= SKILL.md 铁律4 ✓；"过期伏笔=error"= 铁律2 ✓；但测试引用的"铁律1：过期伏笔=error / 铁律2：培育超期需警告 / 铁律3：备忘一致"**编号与现 SKILL.md 全部错位**，且"培育超期=warning"在 SKILL.md 铁律**无对应条款**（仅 检查执行 1 列培育间隔检查，无严重度规定）→ F853
- findings: [F853]
- 验证命令: `read skills/shenbi-review-foreshadowing/SKILL.md:64-78`（铁律 5 条逐条比对）；`read hook-lifecycle.md:19-22`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase2-pacing-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：连续 4 QUEST > maxConsecutiveQuest:3，蓄压表自洽 ✓；测试注明"spec 默认 5，本测试定制 3"与 SKILL.md 示例"3/5 OK"（默认 5）一致 ✓
  - 契约一致性：`shenbi-review-pacing` 铁律2"蓄压必须有释放 → warning"（SKILL.md:71）与测试 WARNING 级别一致 ✓；但测试引用"铁律1"→ 实际为 SKILL.md 铁律2（编号错位，F853 同根）
  - 评分 5/10 ≤ 6/10 通过线 ✓ 内部一致
- findings: [F853]
- 验证命令: `read skills/shenbi-review-pacing/SKILL.md:68-79`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase3-foreshadowing-lifecycle.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：hook-003 过期计算核验：25-8=17>5 OVERDUE ✓；25-5=20>15 EXPIRED ✓；"过期 5 章未超 10 → WARNING"（核心伏笔升级临界）在测试内部自洽，但**该"升级 critical"规则在 SKILL.md/lifecycle-states.md 无出处**（K 级：测试钉死契约未定义的升级阈值，M 级并入 F853 家族）
  - 注意：hook 字段用 `planted_chapter`（本文件）vs phase3-plant-track-resolve 用 `plant_chapter`——两测试对同一伏笔 schema 字段名不一致（M 级，记入 F853 家族：schema 词表未统一）
  - 契约一致性：`shenbi-foreshadowing-track` 存在；"过期=error"一致 ✓
- findings: [F853]
- 验证命令: read + 字段名 grep（`grep -rn "planted_chapter\|plant_chapter" tests/skill-behavior/ skills/shenbi-foreshadowing-*/`）
- 置信度: medium（升级阈值规则无契约出处，需人工裁决）

### tests/skill-behavior/review-catches-bug/phase3-plant-track-resolve.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：5 章生命周期（PLANTED→RELEVANT→RELEVANT静默→TRIGGERED→RESOLVED）状态机与 `lifecycle-states.md` 一致（状态表 PLANTED/RELEVANT/TRIGGERED/RESOLVED + 操作 REINFORCE/TRIGGER/RESOLVE/ARCHIVE）✓；静默章不更新 last_reinforced、间隔 1<2 不 OVERDUE 等细粒度期望正确 ✓
  - track 铁律引用（1 每活跃伏笔必须评估 / 2 状态转换需文本证据 / 3 core_hook 禁 ABANDON）与 SKILL.md 铁律 1/2/3 **逐条吻合**（track 无"独立评分"铁律，编号未偏移）✓
  - **内部算术矛盾（F851）**：:309 头部 "**Chase Power 债务**: 18 (GREEN)" vs :318-321 计算 "2.0 × 4 × 1.5 = 12 / 累计 CP 债务：12 / 剩余：0"——公式（chase-power.md:10-15 hook_power 2.0 × time_since_plant 4 × escalation 1.5 = 12）支持 12；18 无来源。另 :299 `cp_released: 100`（百分比）与 :315 表"100%"一致 ✓；但 :349 通过条件要求 `cp_released=100` 而 :299 同值——数字语义（12 vs 100）在 CP 债务/释放两个维度混用，期望输出不可判一
  - `plant_chapter`（本文件）vs `planted_chapter`（lifecycle 文件）字段名不一致（F853 家族）
- findings: [F851, F853]
- 验证命令: `read skills/shenbi-foreshadowing-resolve/chase-power.md:10-15`；`python3 -c` 复算 2.0*4*1.5=12；`read skills/shenbi-foreshadowing-track/SKILL.md:58-66`（铁律逐条）
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase3-volume-consolidation.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：卷总结输入/期望行为（读 volume_map → 总结 → 伏笔盘点 → 生成 volume_summaries.md → 跨卷衔接点）与 `shenbi-volume-consolidation` SKILL.md 流程一致 ✓
  - "铁律: 归档不是删除"与 SKILL.md 铁律3"保留可回查性"（:64）语义一致（措辞不同，无编号引用）✓
  - 通过/失败条件自洽 ✓
- findings: 无（F850 共同）
- 验证命令: `read skills/shenbi-volume-consolidation/SKILL.md:37,60-64,112`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4-dialogue-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：4 处叠词台词植入与 voice_profile 对照表自洽；"叠词密度 100%（4/4）"计算 ✓
  - 契约一致性：`shenbi-review-dialogue` 存在；声音错位=error 与铁律语义一致 ✓；输出格式（Voice Profile 匹配度/问题台词定位/评分/修复）与 SKILL.md 输出格式一致 ✓
  - 内部一致：评分 3/10 ≤ 5/10 ✓
- findings: 无（F850 共同）
- 验证命令: read + `grep -n "铁律" skills/shenbi-review-dialogue/SKILL.md`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4-memo-compliance-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：8 段式备忘（plans/chapter-007-plan.md）第 6 段"章尾改变：守夜未眠" vs 正文"回房入睡"——未兑现植入清晰；备忘 8 段核对表逐段标注 ✓
  - 契约一致性：`shenbi-review-memo-compliance` 存在（description 明示 "8-section chapter memo compliance"）✓；备忘未兑现=ERROR 语义一致 ✓
  - 内部一致：评分 4/10 ≤ 5/10 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4-reader-pull-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：日历式流水账章节（起床→看书→睡觉）vs 备忘第 2 段"为师门问责铺垫期待"——期待管理缺失植入清晰；四维度（章首钩子/期待管理/章尾悬念/主动词密度）打分表 0/10 自洽 ✓
  - 契约一致性：`shenbi-review-reader-pull` 铁律 2/3/4（章头 200 字生死线/章尾悬念/期待必须回应）与测试的 ERROR 判定一致 ✓；"反钩子写法"分析正确
  - 评分 0/10 ≤ 3/10 通过线 ✓
- findings: 无（F850 共同）
- 验证命令: `read skills/shenbi-review-reader-pull/SKILL.md:61-72`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-era-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：明朝背景植入 6 处时代错误（台灯/皮椅/咖啡/怀表/盖章/合同），替代词合理 ✓；通过条件"检测 ≥4 个"、失败条件"<3 个 FAIL"自洽（4 与 3 间留有判定带宽）✓
  - 契约一致性：`shenbi-review-era` 激活条件（SKILL.md:37 "eraResearch 为 truthy 或 eraConstraints 非空"）与测试准备（eraResearch=true）一致 ✓；"时代错位=error"（铁律2）与测试"每个错误标记 error"一致 ✓
  - 失败条件引用"铁律: eraResearch = true 时必须审计"——SKILL.md 铁律无此编号条款（激活条件在 :37 非铁律节）→ F853 家族（M）
- findings: [F853]
- 验证命令: `read skills/shenbi-review-era/SKILL.md:37,60-66`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-fanfic-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：火影同人 canon 模式植入鸣人性格倒转，4 处偏离点与"原作人物=公共契约"铁律3 一致 ✓
  - 契约一致性：`shenbi-review-fanfic` 存在；"canon 模式严格还原"（铁律2：同人模式决定严格度）✓；"标记 error 非 warning"（canon 严格度）✓；"用 AU 可以这样写"→FAIL（测试显式区分 canon/AU，与 fanfic-modes.md 语义一致）✓
- findings: 无（F850 共同）
- 验证命令: read + `grep -n "canon" skills/shenbi-review-fanfic/SKILL.md`
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-highpoint-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：蓄压 7 段 ~250 字 vs 爆发 2 段 ~40 字（6:1），爽点虚化植入清晰；文本节选自洽 ✓
  - 契约一致性：`shenbi-review-highpoint` 存在；爽点虚化=error 语义一致 ✓
  - 失败条件"认为'一剑解决很爽'→FAIL"——叙事主观判断 vs 读者体验的区分合理 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-long-span-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：3 章结尾同构重复（"看着X，心中涌起一股难以言喻的Y"/"风从X吹来，吹动他的Y"/"他知道，[展望]"）植入清晰；n-gram 检测维度表自洽 ✓
  - 契约一致性：`shenbi-review-long-span` 存在（description 明示 "cross-chapter pattern repetition"）；"跨 3 章重复=error"与测试一致 ✓；失败条件"只检测单章内部→FAIL"正确区分跨章 vs 单章 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-memo-compliance-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：3 项偏离（hook-002 未兑现/禁止事项违反/核心任务偏离）植入清晰；失败条件"只检测出 1 项→PARTIAL"设定了部分通过语义（非 FAIL）——三态判定自洽 ✓
  - 契约一致性：`shenbi-review-memo-compliance` 存在；备忘偏离=error 一致 ✓；"偏离需要主动重写备忘并获批准"与备忘签字画押语义一致 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-motivation-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：利己反派无条件救政敌弟子（无利益链）植入清晰；行为链分析表自洽 ✓
  - 契约一致性：`shenbi-review-motivation` 存在（description "motivation and behavior-chain"）✓；动机断裂=error 一致 ✓；"转变需要行为链支撑"与铁律语义一致 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-pov-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：限定 POV 中写苏婉内心独白（"他不知道的是"句式）植入清晰；测试正确论证"'他不知道的是'≠ 可写出来给读者看" ✓
  - 契约一致性：`shenbi-review-pov` 存在（description "POV consistency and information boundary"）✓；越界=error 一致 ✓
  - 评分 4/10 ≤ 5/10 ✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-reader-pull-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：流水账章首（"上一章的战斗结束了"）与章尾（"也许明天会好一点"）双缺失植入清晰 ✓
  - 契约一致性：`shenbi-review-reader-pull` 铁律2/3（章头 200 字生死线/章尾悬念）与测试双 ERROR 一致 ✓；"铁律: 每章都应有章首钩子和章尾悬念"= 铁律2+3 合并表述（无编号错位，措辞综合）✓
- findings: 无（F850 共同）
- 验证命令: read
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-texture-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：12 段均匀流水账植入；五维度问题表（流水账/段落等长/缺乏对话/缺乏感官/呼吸感差）自洽 ✓
  - 契约一致性：`shenbi-review-texture` 存在（description "流水账 detection"）✓；"段落均匀=error"与测试一致 ✓；失败条件"铁律: 日常也必须有功能"——该铁律实际位于 `shenbi-review-pacing` 铁律4（"日常段落必须有功能"），**跨技能引用**（texture 测试引 pacing 铁律）→ F853 家族（M）
- findings: [F853]
- 验证命令: `grep -n "日常" skills/shenbi-review-texture/SKILL.md skills/shenbi-review-pacing/SKILL.md`（pacing:75 命中；texture 无）
- 置信度: high

### tests/skill-behavior/review-catches-bug/phase4b-world-rules-bug.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：筑基中期用 7 级技能 + 破防筑基后期（低等级不破防）双 bug 植入；战力表/设定冲突表自洽 ✓
  - 契约一致性：`shenbi-review-world-rules` 铁律2（战力体系=天花板）/3（世界规则=物理定律）与测试双 ERROR 逐条对应 ✓；"铁律: 战力崩坏 = error"一致 ✓
  - 评分 2/10 ≤ 4/10 ✓
- findings: 无（F850 共同）
- 验证命令: `read skills/shenbi-review-world-rules/SKILL.md:68-80`
- 置信度: high

### tests/skill-behavior/revision-fixes-issue/phase2-polishing-fix.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：3 段正文植入句长均匀（CV<0.25）/疲劳词"他"每段 6-7 次；期望润色输出（CV>0.30、"他"≤3、5 情节锚点保留、字数差 ≤±15%、修改统计 4 行）全部可判 ✓
  - 契约一致性：`shenbi-style-polishing` 铁律1（只改表达不动情节）/铁律2（字数 ≤±15%）/铁律3（[polisher-note] 标记结构问题）与测试逐条对应；测试引用"铁律 #1/#2"——style-polishing 无"独立评分"铁律，编号**恰好吻合** ✓
  - 通过条件"未对结构性问题插入 [polisher-note]"与铁律3 语义一致 ✓；修改统计示例（-12 字 -4.0%）自洽 ✓
- findings: 无（F850 共同）
- 验证命令: `read skills/shenbi-style-polishing/SKILL.md:59-70`
- 置信度: high

### tests/skill-behavior/revision-fixes-issue/phase4b-revision-mode-routing.md
- 处置: deep-read
- 声称检查的不变量:
  - 场景真实性：3 类问题（了字密度/禁忌词/段落方差 = 局部；OOC = 结构）路由期望表自洽 ✓
  - **契约冲突（F852）**：通过条件要求"最终修订使用混合策略（PATCHES + REVISED_CONTENT）"，而 `shenbi-chapter-revision` SKILL.md:74-76 明示"局部问题 → spot-fix（PATCHES）；结构问题 → rewrite（REVISED_CONTENT）；**混合 → rewrite（保守策略）**"——测试要求混合输出两种模式，契约规定混合只走 rewrite。且 SKILL.md:76"混合 → rewrite"本身与 :74-75 的逐问题路由并存，测试按"逐问题路由"理解，契约按"整体保守"理解——测试与契约对 auto 模式路由语义不一致（P2）
  - "±15%"引用与 chapter-revision 铁律3 一致 ✓
- findings: [F852]
- 验证命令: `read skills/shenbi-chapter-revision/SKILL.md:47-52,65-76`
- 置信度: high

---

# 三、tests/skill-triggering/prompts/（12 文件）

**共同背景（F850）**：12 个文件全部是 `tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase{2,3,4,4b}-*.md` 的逐字重复；运行时只读 tiers 树。与 `using-shenbi/SKILL.md` 触发映射逐用例比对（F855 家族）。

### tests/skill-triggering/prompts/phase2-character-trigger.md
- 处置: deep-read
- 声称检查的不变量: 用户输入"角色说话做事/人设" → 期望路由 `shenbi-review-character`（明确排除 character-design 与 style-polishing）；using-shenbi 触发映射 :46 "角色一致性/人设崩了/OOC" → review-character ✓ 一致；通过/失败条件与 skill-check 流程语义一致 ✓
- findings: 无（F850 共同）
- 验证命令: `grep -n "review-character" skills/using-shenbi/SKILL.md`（:46）
- 置信度: high

### tests/skill-triggering/prompts/phase2-continuity-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入"时间线/事件顺序" → `shenbi-review-continuity`；触发映射 :45 "连贯性/前后矛盾/对不上" → review-continuity ✓ 语义一致（输入词"时间线"未在映射出现——映射用"连贯性/矛盾"；测试期望按意图路由而非字面词，映射覆盖缺口属 using-shenbi 侧，M 级记 F855 家族）；失败条件"跳过 using-shenbi 直接调用审计技能→FAIL"与 meta 技能契约一致 ✓
- findings: [F855]
- 验证命令: `grep -n "review-continuity" skills/using-shenbi/SKILL.md`（:45）
- 置信度: medium

### tests/skill-triggering/prompts/phase2-foreshadowing-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入含"伏笔"×3 + "检查"（无连续"伏笔检查"短语）→ 期望 `shenbi-review-foreshadowing`；触发映射 :48 "伏笔检查/埋线检查"→review-foreshadowing，但 :73 "伏笔/埋线/hook"→**shenbi-foreshadowing-plant**——输入命中泛化"伏笔"而非"伏笔检查"，**关键字路由可能误判到 plant**；测试失败条件明确"路由到 track/resolve→FAIL"（未把 plant 列为失败项，但 plant 同样是错误路由）；测试钉死的行为与触发映射的确定性路由**冲突**（P2）→ F855
- findings: [F855]
- 验证命令: `grep -n "伏笔" skills/using-shenbi/SKILL.md`（:48 与 :73 双映射）
- 置信度: high

### tests/skill-triggering/prompts/phase2-polishing-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入"润色/读起来更顺/剧情别动" → `shenbi-style-polishing`（排除 anti-detect/chapter-revision）；触发映射 :65 "润色/打磨/文字" → style-polishing ✓；"不改对话情节"与 style-polishing 铁律1 一致 ✓
- findings: 无（F850 共同）
- 验证命令: `grep -n "润色" skills/using-shenbi/SKILL.md`（:65）
- 置信度: high

### tests/skill-triggering/prompts/phase3-foreshadowing-trigger.md
- 处置: deep-read
- 声称检查的不变量: 三用例区分 plant/track/resolve：
  - 用例 A"埋一条伏笔…种下 hook" → plant；触发映射 :73 "伏笔/埋线/hook" → plant ✓
  - 用例 B"检查伏笔池的状态…哪些 hook 需要推进" → track；映射 :74 "伏笔追踪/hook状态" → track（输入含"伏笔池"+"hook"——命中 :73 泛化"hook"→plant 的歧义同样存在）✓ 意图对但映射歧义（F855）
  - 用例 C"TRIGGERED…兑现" → resolve；映射 :75 "伏笔兑现/收线" → resolve ✓
- findings: [F855]
- 验证命令: `grep -n "伏笔\|hook" skills/using-shenbi/SKILL.md`（:73-75）
- 置信度: high

### tests/skill-triggering/prompts/phase3-intent-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入"长期目标/更新" → `shenbi-intent-management`（排除 chapter-planning）；映射 :92 "作者意图/长期目标" → intent-management ✓；期望双写 author_intent.md + current_focus.md 与 SKILL.md 契约一致（抽查）✓
- findings: 无（F850 共同）
- 验证命令: `grep -n "intent" skills/using-shenbi/SKILL.md`（:92）
- 置信度: high

### tests/skill-triggering/prompts/phase3-snapshot-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入"快照/创建" → `shenbi-snapshot-manage`（排除 state-settling）；映射 :88 "回滚/快照" → snapshot-manage ✓；通过条件"复制全部 **11 个** truth 文件 + manifest"——SKILL.md:67/116 用 glob `truth/*.md`（**无 11 硬编码**），真实项目 novel-output/xinghuo-ranqiong/truth 实测 **13 个文件** → 硬编码 11 已过期（F854）
- findings: [F854]
- 验证命令: `ls novel-output/xinghuo-ranqiong/truth/ | wc -l`（13）；`grep -n "truth/\*" skills/shenbi-snapshot-manage/SKILL.md`（:67,116,124）
- 置信度: high

### tests/skill-triggering/prompts/phase3-truth-sync-trigger.md
- 处置: deep-read
- 声称检查的不变量: 输入"重新提取/同步/truth 文件" → `shenbi-truth-sync`（与 state-settling 区分：起草后自动 vs 手动编辑后）；映射 :87 "同步状态/重新提取" → truth-sync ✓；"不读取修改后正文就更新→FAIL"合理 ✓
- findings: 无（F850 共同）
- 验证命令: `grep -n "同步\|truth" skills/using-shenbi/SKILL.md`（:87）
- 置信度: high

### tests/skill-triggering/prompts/phase4-management-triggers.md
- 处置: deep-read
- 声称检查的不变量: 14 用例矩阵，逐一与触发映射比对：length-normalizing（:43 ✓）/anti-detect（:66 ✓）/chapter-pattern（:93 ✓）/drift-guidance（:91 ✓）/genre-config（无专属行，靠 description 路由——映射缺 genre-config 触发行，M 记 F855 家族）/short-outline（:81 ✓）/short-drafting（:82 ✓）/short-packaging（:83 ✓）/import-analysis（:76 ✓）/style-learning（:77 ✓）/canon-import（:80 ✓）/volume-outlining（:95 ✓）/market-radar（:85 ✓）/sequel-writing（:84 ✓）；失败条件"用例 2 路由到 shenbi-review-anti-ai→FAIL"——`shenbi-review-anti-ai` 存在（技能清单核验 OK）✓
- findings: [F855]（genre-config 无触发映射行）
- 验证命令: `grep -n "genre-config" skills/using-shenbi/SKILL.md`（0 命中——映射缺行）；逐一 grep 其余 13 技能
- 置信度: high

### tests/skill-triggering/prompts/phase4b-audit-triggers.md
- 处置: deep-read
- 声称检查的不变量: 12 用例矩阵，与触发映射比对：world-rules（:49 ✓）/dialogue（:50 ✓）/motivation（:51 ✓）/pov（:52 ✓）/texture（:53 ✓）/highpoint（:55 ✓）/long-span（:57 ✓）/era（:59 ✓）/fanfic（:60 ✓）/spinoff（:61 ✓）/reader-pull（:54 ✓）/memo-compliance（:63 ✓）全部命中；失败条件区分 world-rules vs continuity、highpoint vs pacing ✓；12/12 技能存在 ✓
- findings: 无（F850 共同）
- 验证命令: 逐用例 `grep -n` 触发映射（:45-63）
- 置信度: high

---

# 四、findings 清单摘要（F850–F861）

| ID | 类别 | 严重度 | 一句话 | 证据 | 状态 |
|---|---|---|---|---|---|
| F850 | error | P2 | tests/skill-behavior + tests/skill-triggering 全部 33 个 .md 是 tests/tiers/t1-skill 场景的精确重复副本（38 对 diff IDENTICAL），运行时仅消费 tiers 树，两目录被 norecursedirs 排除且无同步机制 | tests/ARCHIVE-MIGRATED.md:1-77; pyproject.toml:416-417; src/shenbi/gates/g0.py:368; diff 38/38 IDENTICAL | specced |
| F851 | error | M | phase3-plant-track-resolve.md 内部算术矛盾：Chase Power 债务 18（:309）vs 计算 2.0×4×1.5=12（:318-321，chase-power.md 公式支持 12）；cp_released=100 与 CP 债务 12 混用两种量纲 | 测试 :299,309,318-321,349; skills/shenbi-foreshadowing-resolve/chase-power.md:10-15 | specced |
| F852 | error | P2 | phase4b-revision-mode-routing.md 要求混合策略（PATCHES+REVISED_CONTENT），与 shenbi-chapter-revision SKILL.md:76"混合 → rewrite（保守策略）"直接冲突 | 测试通过条件 :33-36; SKILL.md:74-76 | specced |
| F853 | error | M | 铁律编号系统性漂移 + 无契约条款：测试引"铁律1/2/3"与现 SKILL.md 错位（review 技能均以"独立评分"为铁律1 后移）；"培育超期=warning"（phase2-foreshadowing-bug）、"过期>10章升级critical"（phase3-foreshadowing-lifecycle）、"eraResearch=true 必须审计"（phase4b-era）、"日常也必须有功能"（phase4b-texture 引用 pacing 铁律4）、planted_chapter/plant_chapter 字段名分裂 | 5 个测试文件 vs 5 个 SKILL.md 铁律节逐条比对 | specced |
| F854 | error | M | phase3-snapshot-trigger.md 硬编码"11 个 truth 文件"，SKILL.md 用 glob truth/*.md，真实项目 13 个 → 计数过期 | 测试 :29; SKILL.md:67,116,124; ls novel-output/xinghuo-ranqiong/truth = 13 | verified |
| F855 | error | P2 | 触发路由歧义：using-shenbi 映射 :73"伏笔/埋线/hook"→plant 与 :48"伏笔检查"→review 双映射；phase2-foreshadowing-trigger/phase3-foreshadowing-trigger 用例B 输入不含精确短语，关键字路由可能误判 plant；phase2-continuity 输入词"时间线"不在映射；phase4-management 用例5 genre-config 无映射行 | 测试输入逐词 vs 映射 :43-95 | verified |
| F856 | error | M | test_word_count_md_always_non_negative 空转：策略字母表无 [一-鿿] CJK 字符 → word_count_md 恒 0，声称的"Chinese chars counted"路径从未被生成 | test_gate_invariants.py:33; shared.py:122 | verified |
| F857 | error | M | test_excluding_all_decline_indices_suppresses_finding 空转：`.map(sorted)` 升序序列永不产生 monotonic_decline，排除语义无从验证（测试名声称"排除真起作用"不成立） | test_drift_properties.py:46-53; compute_drift.py:95 | verified |
| F858 | optimization | M | test_bootstrap_subset_of_yaml 伪属性测试（@given(st.data()) 未使用）；test_three_registry_sources_agree"三表一致"实为两独立源（bootstrap_registry 内部派生自 load_registry） | test_registry_consistency.py:42-45,20-31; registry.py:17-31 | verified |
| F859 | docs | M | registry 测试 docstring "实测 54==54==54" 过期（实际 70==70==70） | test_registry_consistency.py:24; python 实测 70 | verified |
| F860 | error | M | trace 链测试未设 deadline=None（套件唯一例外），dev profile（默认 200ms）下 20×fsync/example 可抖动；CI profile 无风险 | test_chain_invariants.py:14-15,26-27; writer.py:92-97; tests/conftest.py:9-14 | verified |
| F861 | error | M | .hypothesis/examples 实际 11 个 0 字节未跟踪文件（任务称 44 样本，不符）；12 个 patch 共 17 个已发现失败全部未跟踪；.hypothesis/.gitignore 声称"Examples ARE committed"但 git 仅跟踪 .gitkeep——声明的提交式回归网不成立（17 个失败已在测试代码中修复，回归保护靠提交的守卫/黑名单/容差） | .hypothesis/.gitignore; git ls-files .hypothesis（2 文件）; 12 patch 逐例复算 | verified |

---

# 五、覆盖统计

| 维度 | 数字 |
|---|---|
| 清单文件数 | 52 |
| deep-read 文件数 | 52（100%） |
| property 测试文件 | 19（含 7 个 .py 测试文件 + 7 个 `__init__.py` + .gitkeep + 4 个空 __init__） |
| property 测试函数 | 47（`def test_` 计数；pytest collect-only 全量收集，d1-01 运行 2814 passed 中通过） |
| skill-behavior 文件 | 21（全部为 tiers 副本） |
| skill-triggering 文件 | 12（全部为 tiers 副本） |
| findings 总数 | 12（F850–F861）：P2×3、M×9 |
| skip/xfail | 0（d1-11-skipxfail.txt 本区 0 命中） |
| d1-06 覆盖缺口条目 | 0（清单按 src/ 行组织，本区测试文件无条目；处置见总说明） |
| mock 滥用 | 0（property 全直测真实函数；行为/触发场景为自包含输入+期望输出） |

## 未覆盖文件列表

（空——52/52 全部完成 per-file deep-read，无未覆盖文件）
