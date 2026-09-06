> **Date:** 2026-08-16 | **Status:** Done (PR #161)（Revised 2026-09-07 · SDD #45 事实核实：F105 已修 PR #63 剔除、T1206 已修 PR #91 维持让渡、T1204 降级防御性收口、F308 行号 747→872） | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C31）| **依赖:** 无硬前置；上轮 T12-01/T12-04/T12-05 未修复核在本簇重立（T1206/T1207/T1204）| **范围:** 审计报告判定解析、_write_parsed_outputs 路径校验、dispatch env、phase 参数净化、capability_fs、会话日志 | **核心洞察:** 被审内容可以伪造审查者的判定（T1201 PoC：章节文本经证据引用伪造 G4 PASS 与共振分数）——信任边界在"产物内容"与"框架判定"之间从未建立

# C31 · 注入/越权安全面修复（injection-authorization）

## 元信息
- 簇：C31（注入/越权安全面：prompt injection/路径穿越/env 继承），10 条，最高严重度 P1（T1201/F308，均 verified；F105 原列 P1 已修 PR #63），证据等级=实验佐证
- 成员：T1201（代表）、F308、F1161、T306、T307、T1202、T1204、T1206、T1207；~~F105~~（closed-by PR #63）；T1206 closed-by PR #91（让渡 #22，见边界注记）
- 来源：thread-reports/T12.md、T3.md + Z1/Z3/Z11-b
- 关系：supersede `archive/2026-08-14-security-injection-design.md`（#22）的 T12-01（→T1206）/T12-04（→T1207）/T12-05（→T1204）与命令注入/env/路径穿越 P2 面

## 背景与根因
四类信任边界缺失：
1. **判定伪造**（T1201 P1 verified）：审计报告决策解析器无作用域 first-match——被审章节文本通过"证据引用"格式即可写入伪造的 G4 判定行与共振分数，gate 记 v=通过。协调者独立 PoC 复现（真实判定被阻断→伪造行通过）。
2. **防御死代码**（F308 P1 verified，现 dispatch_helper.py:872）：`replace("<", "\u003c")` 恒等替换（`\u003c` 就是 `<`），防 `</document>` 注入的声称防御从未生效。
3. **路径/参数越权**（F105 P1 verified：phase 参数未净化拼进 phase-state 路径，`../` 可穿越写出 round_dir；T1204 P2：symlink 重定向契约写逃出 project_dir，_write_parsed_outputs 实证；T1202 P2：carrier 行优先级倒置，反馈内容可覆盖机器上下文占位符）。
4. **env 与日志泄露**（T1207 P2：env 全量继承使 SHENBI_LLM_API_KEY 可达 workspace-write codex 子进程；F1161 M：本地会话日志残留完整 Google OAuth URL 含一次性 state/nonce/code_challenge；T306 M/T307 P2：注入无过滤标注、T1 dispatch 面结构性无 reads 注入过滤）。

## 目标
1. 框架判定只来自框架通道：判定解析限定作用域（只认机器写的信封段），产物内容无法注入判定
2. 输入边界净化：phase 参数白名单、输出路径必须 resolve 后前缀校验 project_dir/round_dir、symlink 解析后同校验
3. 子进程 env 白名单传递；会话日志密钥/OAuth 参数脱敏

## 任务分解
### R1 · 判定解析作用域（T1201，P0 级修复面）
- **信封格式（本 spec 自含定义，2026-09-07 设计审查钉死）**：判定信封 = 报告中的机器围栏块——行锚定 `^```verdict$` 起至下一个 `^```$` 止（非贪婪、多行、取全文**最后一个**匹配块）；块内两行 `判定: <token>` 与 `共振: <N>/100`。**位置次序（与既有尾部机器块的兼容裁决）**：围栏块置于校准门判定小节之后、报告末尾固定两行校准块（`calibration:`/`anchors:`，SKILL.md:143-150）之前——校准块保持「末尾固定两行」契约不变，两套机器契约共存不挤位。**证据引述格式约束**：证据列引述沿用 `> ` 前缀格式且禁止行首裸三反引号（防 tokenize 错配吞围栏闭标记），随 SKILL 输出契约成文。现有 write-audit.jsonl 只记 FS 写所有权、无判定字段，C32 spec 亦未定义判定产出——本节围栏信封即消费接口提案，C32 落地如引入 JSON 信封可平移
- 判定/共振分数解析限定在围栏块内，解析点**三处**同改：`review_resonance.py` `_match_verdict`、`review_arc_payoff.py`、`chapter_loop.py:1597-1640` `_parse_resonance_score`（现对全文 first-match 四模式：`Resonance Score`/`Score: N`/`resonance_score:`/`(N/100)`，是 PoC 分数伪造的第三消费端；改造后围栏内新增 `共振: <N>/100` 行读取，围栏外命中 → WARN"疑似注入"不采纳）。`_VERDICTS` token 前缀校验在围栏内原样保留；G3.4 独立评分不受影响（判定解析属 G4）；`llm_output_integrity.py:51` `VERDICT_MARKERS` 只做存在性启发不采纳值，不属伪造通道、不改（划界免重查）
- **产出方改造（与消费方同 PR）**：`skills/shenbi-review-resonance/SKILL.md` 输出契约（:137 现为裸 `判定:` 行）与 `chapter_loop.py:686-690` `G4_FORMAT_EXAMPLES["G4.rr.verdict"]` 重试反馈模板（现教模型输出裸行——不改则重试路径围栏永不激活）同步要求 reviewer 以 ```verdict 围栏块输出判定。改 SKILL.md 后须重跑 `shenbi-sync-contracts`/`just generate` 并提交生成物 diff（幂等门禁会强制）
- 存量无围栏报告（兼容裁决）：降级路径 = **全文最后一个非 `> ` 引用行的匹配** + WARN `legacy_report_no_envelope`（引述行是被审文本回显、跳过；报告判定行必然出现在正文引用之后）——裸 first-match 会被早期伪造行劫持（T1201 本体），last-match+跳引述把注入面压缩到 reviewer 自书行；产出方改造落地后新报告全部走围栏，降级窗口收敛
- 派发面（R5）注入的 reads 内容统一包裹 `<untrusted-source path="...">` 边界标记（属性经 `_escape_attr`、正文实体转义）；该标记格式以本节为唯一定义、R5 为消费方（R1 格式定义是 R5 硬前置）
- **验收**：T1201 PoC 用例入回归——含伪造判定行的章节文本不能改变 gate 结果；真实判定阻断场景仍阻断；无围栏旧报告走降级路径且 WARN

### R2 · 转义修复（F308）
- `<` 转义改为 `&lt;`（复用 dispatch_helper.py:624 既有 `_escape_attr` 同型实现；:869 注释中的 `\u003c` 字面残留同步改写，否则 grep 验收假红）；全仓 grep 同型恒等转义（`replace(x, esc(x))` 形态）零残留
- **验收**：`git grep -n 'u003c' -- src/` 零命中；含 `</document>` 的技能输出/输入不再截断后续解析；单测覆盖；对若干 fixtures 派发输出做替换前后对比回归（实体化不破坏可读性）

### R3 · 路径与参数边界（T1204 + T1202；F105 已修 PR #63 `phase_runner._sanitize_phase`，剔除）
- ~~phase 参数白名单校验~~（closed-by PR #63，不重复实现）；`_write_parsed_outputs`（dispatch_helper.py:1426 起）每个输出路径 `resolve(strict=False)` 后校验 `is_relative_to(project_dir)`，symlink 先 resolve 再校验
- carrier 优先级反转落点（T1202）：机制 = `[path-context]` 行——`contracts/paths.py:format_path_context`（写侧，triggers.py:582 机器行已最后追加）与 `parse_path_context`（读侧 :62 取**首个**命中）；修复 = 解析改取**最后一个** `[path-context]` 行（机器行最后写、解析取机器行；T1204 可达面收窄依据：`contracts/paths.py:59 _UNSAFE_VALUE_RE` 拒 `/ \ ..` 值 + 唯一写点机器拼装，按防御性收口承接）
- 边界扩容（2026-08-30 自 #22 让渡）：`safe_write` 层同型 resolve+前缀校验（T12-05 残留）——`safe_write(path, ..., allowed_roots)` 新增可选参数：传根列表时 `path.parent.resolve()` 后校验 `is_relative_to` 某根，不传则保持现行为（调用方实测 66 处，爆炸半径受控）；安全关键调用方 `_write_parsed_outputs` 必传 `project_dir`。**权威关系**：`_write_parsed_outputs` 自身校验为权威拒绝面（报错信封 + WARN 日志事件），safe_write allowed_roots 为纵深二线（静默结构校验）——避免两套不一致的拒绝语义
- T12-02 残留「状态文件只读保护」实现口径（轮 2 I-3 补入）：`_write_parsed_outputs` 路径校验中加 deny-list——codex 写面拒绝 `phase-state/`、gate-markers、`scores.json` 族状态路径（框架写面不受限）；这些文件本就由框架 safe_write 独占产出
- **验收**：穿越用例（`../escape.md`、symlink 指外）FAIL 且不落盘；正常相对路径全绿；deny-list 用例——codex 产物声明写 `phase-state/x.json` 拒绝；T1202 用例——prompt 中被审文本携带的伪造 `[path-context]` 行先于机器行出现时，解析结果取机器行

### R4 · env 白名单与日志脱敏（T1207 + F1161）
- codex/子进程 env 改白名单，分层成文：codex exec 面（PATH/HOME/CODEX_HOME/OPENAI_ 非密钥配置子集如 OPENAI_BASE_URL/代理类——`OPENAI_API_KEY` 等密钥名显式排除）与 uv run 面（追加 UV_*/PYTHON*）各自白名单，SHENBI_ 前缀透传（密钥值本身按密钥类规则排除），密钥类默认不透传；留 `SHENBI_ENV_PASSTHROUGH`（冒号分隔）运维追加通道；白名单成文 `docs/framework/env-policy.md`
- 会话/审计日志写入前脱敏：OAuth URL 参数（state/nonce/code_challenge/code）、`sk-`/Bearer 令牌模式；脱敏落点 = `src/shenbi/logging.py` structlog Processor + 独立 redact 函数（单测直接覆盖）
- **验收**：派发生成的子进程 env dump 无 SHENBI_LLM_API_KEY；构造含密钥的日志行经 structlog 管道落盘为 `***`（单测断言，非 grep 审计产物）

### R5 · 注入标注补全（T306 + T307；R1 格式定义为硬前置）
- dispatch 注入的 reads 内容统一带来源标注（文件路径 + 围栏哨兵边界，格式取 R1 定义），T1 dispatch 面（dispatcher/modes/codex.py:118 现为裸 prompt）与 pipeline 面同构
- **验收**：两个派发面的注入文本含相同边界标记；R1 解析器对两面输入行为一致

## 验收（簇级）
- `just check` 全绿；安全用例新建并集中 `tests/unit/security/`（目录现不存在，须新建并纳入 pytest 收集；PoC 用例必须真实文件驱动，G0.9）
- C31 全部 10 条回写关闭（F105→closed-by PR #63、T1206→closed-by PR #91 直接回写 ledger，其余 merged-into T1201）；ledger F105 行"未修复"状态同步回写；#22 已归档（2026-08-30 Done PR #91，其 T12-01/T12-06 由自身 R1/R3 承接关闭），本簇只需关 T12-04/T12-05 对应的 T1207/T1204

## 风险
- R1 改判定通道与 C1（审计级联格式对账）、C32（write-audit 信封）交叠——write-audit.jsonl 现无判定字段、C32 未定义判定产出，信封格式由本 spec R1 自含定义（围栏块）作为消费接口提案，C32 落地时可平移
- env 白名单可能漏传个别工具必需变量——分层白名单 + SHENBI_ENV_PASSTHROUGH 逃生阀，CI 全链路核对，成文 docs/framework/env-policy.md

## 验证命令
- 判定伪造回归：`pytest tests/unit/security/ -k "forged_verdict or t1201" -q`（PoC 用例必须真实文件驱动，G0.9）
- 恒等转义清剿：`git grep -n 'u003c' -- src/`（零命中）
- 路径穿越：`pytest tests/unit/security/ -k "traversal or symlink" -q`
- env 白名单：派发子进程 env dump 断言无 SHENBI_LLM_API_KEY（用例内临时密钥）
- 日志脱敏：`pytest tests/unit/security/ -k redact -q`（redact 函数 + structlog processor 单测；修复后新日志零 `code_challenge|sk-` 残留）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T1201 <- F308, F1161, T306-T307, T1202, T1204, T1207`；F105 closed-by PR #63、T1206 closed-by PR #91（直接回写，不并入本簇 merged）
- 上轮承接：#22（security-injection，已归档 Done PR #91）的 T12-04/T12-05 对应 T1207/T1204 在本簇关闭（T12-01/T12-06 已随 #22 自身修复关闭）

## 边界注记（2026-08-30，SDD #22 REWRITE 对账）
- T12-01 属性侧（`<document name="{fname}">` 属性转义 + wildcard 写文件名白名单）由修订版 #22 R1 承接，本簇 R2 仅覆盖内容侧 `<` 转义——两 spec 分工，禁双修
- T12-03 残留半面（tests/round-exec.sh `python3 -c` 插值）由修订版 #22 R2 承接，本簇不涉及
- T12-06（skill 名词法校验 + plugins/generate.py output 穿越）由修订版 #22 R3 承接
- T12-02 残留「状态文件只读保护」（pipeline-state/gate-markers/scores 对 codex 写面的预防性约束）与 T12-05 残留「safe_write 路径规范化」自 #22 让渡收口至本簇：前者并入 R3 路径边界范围，后者并入 R3（`_write_parsed_outputs` 之外 safe_write 层的同型 resolve+前缀校验）
