> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C31）| **依赖:** 无硬前置；上轮 T12-01/T12-04/T12-05 未修复核在本簇重立（T1206/T1207/T1204）| **范围:** 审计报告判定解析、_write_parsed_outputs 路径校验、dispatch env、phase 参数净化、capability_fs、会话日志 | **核心洞察:** 被审内容可以伪造审查者的判定（T1201 PoC：章节文本经证据引用伪造 G4 PASS 与共振分数）——信任边界在"产物内容"与"框架判定"之间从未建立

# C31 · 注入/越权安全面修复（injection-authorization）

## 元信息
- 簇：C31（注入/越权安全面：prompt injection/路径穿越/env 继承），10 条，最高严重度 P1（T1201/F105/F308，均 verified），证据等级=实验佐证
- 成员：T1201（代表）、F105、F308、F1161、T306、T307、T1202、T1204、T1206、T1207
- 来源：thread-reports/T12.md、T3.md + Z1/Z3/Z11-b
- 关系：supersede `2026-08-14-security-injection-design.md`（#22）的 T12-01（→T1206）/T12-04（→T1207）/T12-05（→T1204）与命令注入/env/路径穿越 P2 面

## 背景与根因
四类信任边界缺失：
1. **判定伪造**（T1201 P1 verified）：审计报告决策解析器无作用域 first-match——被审章节文本通过"证据引用"格式即可写入伪造的 G4 判定行与共振分数，gate 记 v=通过。协调者独立 PoC 复现（真实判定被阻断→伪造行通过）。
2. **防御死代码**（F308 P1 verified）：`replace("<", "\u003c")` 恒等替换（`\u003c` 就是 `<`），防 `</document>` 注入的声称防御从未生效。
3. **路径/参数越权**（F105 P1 verified：phase 参数未净化拼进 phase-state 路径，`../` 可穿越写出 round_dir；T1204 P2：symlink 重定向契约写逃出 project_dir，_write_parsed_outputs 实证；T1202 P2：carrier 行优先级倒置，反馈内容可覆盖机器上下文占位符）。
4. **env 与日志泄露**（T1207 P2：env 全量继承使 SHENBI_LLM_API_KEY 可达 workspace-write codex 子进程；F1161 M：本地会话日志残留完整 Google OAuth URL 含一次性 state/nonce/code_challenge；T306 M/T307 P2：注入无过滤标注、T1 dispatch 面结构性无 reads 注入过滤）。

## 目标
1. 框架判定只来自框架通道：判定解析限定作用域（只认机器写的信封段），产物内容无法注入判定
2. 输入边界净化：phase 参数白名单、输出路径必须 resolve 后前缀校验 project_dir/round_dir、symlink 解析后同校验
3. 子进程 env 白名单传递；会话日志密钥/OAuth 参数脱敏

## 任务分解
### R1 · 判定解析作用域（T1201，P0 级修复面）
- 审计报告的 G4 判定/共振分数改为只在框架写入的结构化信封（write-audit/state 字段或独立 JSON）中读取；正则/first-match 解析器限定在信封区（机器行分隔符 + 转义），正文命中不采纳并 WARN"疑似注入"
- **验收**：T1201 PoC 用例入回归——含伪造判定行的章节文本不能改变 gate 结果；真实判定阻断场景仍阻断

### R2 · 转义修复（F308）
- `<` 转义改为 `&lt;`（或删除该声称防御，改用 CDATA 包裹注入内容）；全仓 grep 同型恒等转义（`replace(x, esc(x))` 形态）零残留
- **验收**：含 `</document>` 的技能输出/输入不再截断后续解析；单测覆盖

### R3 · 路径与参数边界（F105 + T1204 + T1202）
- phase 参数白名单校验（`../` 拒绝 + 报错信封）；`_write_parsed_outputs` 每个输出路径 `resolve(strict=False)` 后校验 `is_relative_to(project_dir)`，symlink 先 resolve 再校验；carrier/机器行优先级反转（机器行最后写、解析取机器行）
- **验收**：穿越用例（`../escape.md`、symlink 指外）FAIL 且不落盘；正常相对路径全绿

### R4 · env 白名单与日志脱敏（T1207 + F1161）
- codex/子进程 env 改白名单（PATH/HOME/项目显式变量 + SHENBI_ 前缀），密钥类默认不透传
- 会话/审计日志写入前脱敏：OAuth URL 参数（state/nonce/code_challenge/code）、`sk-`/Bearer 令牌模式
- **验收**：派发生成的子进程 env dump 无 SHENBI_LLM_API_KEY；构造含密钥的日志行落盘为 `***`

### R5 · 注入标注补全（T306 + T307）
- dispatch 注入的 reads 内容统一带来源标注（文件路径 + 哨兵边界），T1 dispatch 面与 pipeline 面同构；标注格式与 R1 信封一致
- **验收**：两个派发面的注入文本含相同边界标记；R1 解析器对两面输入行为一致

## 验收（簇级）
- `just check` 全绿；安全用例集中 `tests/unit/security/`（PoC 用例必须真实文件驱动，G0.9）
- C31 全部 10 条 merged-into T1201 回写关闭；上轮 #22 spec 归档前核对 T12-01/04/05 三条已在本簇关闭

## 风险
- R1 改判定通道与 C1（审计级联格式对账）、C32（write-audit 信封）交叠——信封格式以 C32 的 write-audit.jsonl 为单源，本 spec 只做消费侧
- env 白名单可能漏传个别工具必需变量——先在 CI 全链路跑一遍（just pipeline smoke）核对，白名单成文于 docs/framework/

## 验证命令
- 判定伪造回归：`pytest tests/unit/security/ -k "forged_verdict or t1201" -q`（PoC 用例必须真实文件驱动，G0.9）
- 恒等转义清剿：`git grep -nE 'replace\("<", "\\\\u003c"\)' -- src/`（零命中）
- 路径穿越：`pytest tests/unit/security/ -k "traversal or symlink" -q`
- env 白名单：派发子进程 env dump 断言无 SHENBI_LLM_API_KEY（用例内临时密钥）
- 日志脱敏：`grep -rE "code_challenge|sk-" docs/superpowers/audit-runs/ --include="*.log"`（修复后新日志零命中）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T1201 <- F105, F308, F1161, T306-T307, T1202, T1204, T1206-T1207`
- 上轮承接：#22（security-injection）的 T12-01/T12-04/T12-05 对应 T1206/T1207/T1204，随本簇关闭后 #22 归档

## 边界注记（2026-08-30，SDD #22 REWRITE 对账）
- T12-01 属性侧（`<document name="{fname}">` 属性转义 + wildcard 写文件名白名单）由修订版 #22 R1 承接，本簇 R2 仅覆盖内容侧 `<` 转义——两 spec 分工，禁双修
- T12-03 残留半面（tests/round-exec.sh `python3 -c` 插值）由修订版 #22 R2 承接，本簇不涉及
- T12-06（skill 名词法校验 + plugins/generate.py output 穿越）由修订版 #22 R3 承接
- T12-02 残留「状态文件只读保护」（pipeline-state/gate-markers/scores 对 codex 写面的预防性约束）与 T12-05 残留「safe_write 路径规范化」自 #22 让渡收口至本簇：前者并入 R3 路径边界范围，后者并入 R3（_write_parsed_outputs 之外 safe_write 层的同型 resolve+前缀校验）
