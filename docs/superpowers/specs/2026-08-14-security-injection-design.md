> **Date:** 2026-08-14 | **Status:** Design (Revised 2026-08-30) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 5/7）| **依赖:** 无 | **范围:** wrapper 属性注入（T12-01 属性半面）/ round-exec.sh 命令注入（T12-03 半面）/ 按名拼接防御（T12-06）
> **修订记录（2026-08-30，SDD #22 价值门 REWRITE）:** 收窄为未被承接的独占面；已承接面让渡——T12-01 内容侧 no-op 转义（F300/F308）→ spec #45 R2；T12-02 持久化注入链与 codex 写面 → F512 已由 C32 R3（PR 合并 26db756）修复写审计接线，判定伪造缓解与 env/路径/symlink 面归 spec #45（T1201/T1206/T1207/T1204）；T12-03 的 run_pipeline.sh 半面 → spec #64（F003/F1013/T1205）；T12-04 → spec #45 R4（T1207）；T12-05 → spec #45 R3（T1204）。**禁止双修**：上述让渡面本 spec 不实施。

# 安全与提示注入（补齐 E · 修订收窄版）

## R1 · wrapper 属性侧注入与文件名词法白名单（T12-01 属性半面，P1）
- 证据：`dispatch_helper.py:781` `<document name="{fname}">` 属性值零转义，`fname` = `full_path.relative_to(project_dir)`；`_wildcard_to_regex` 的 `[^/]*` 放行 `"` 文件名（实证 `import/canon/x" auto="1.md` 匹配 `^import/canon/[^/]*\.md$`）→ 逃逸 wrapper 属性注入 prompt
- 修复：(a) 属性值转义（`&quot;`/`&lt;`/`&amp;` entity）；(b) wildcard 写路径文件名词法白名单（拒绝 `"`、`<`、`>`、控制字符），校验须先于 `_resolve_wildcard_path` 的 `parent.mkdir`（dispatch_helper.py:500）执行以满足「FAIL 不落盘」
- 边界：内容侧 `<`→`\u003c` no-op 转义（F300/F308）归 #45 R2，本 spec 不动 `safe_content` 转义逻辑
- 取材口径（G0.9）：对抗性文件名对象由测试自身在 tmp_path 构造（真实文件系统对象，非提交的手写 fixture）；提交面 fixtures 仅用于良性读回路径
- 拒绝机制：wildcard 写文件名违规 → `DispatchWriteFailureError` 报错信封（与 `_write_parsed_outputs` 现有失败路径同型）
- **验收：含 `"` 文件名的 wildcard 写被拒绝（FAIL 不落盘、无 mkdir 残留）；读回时属性值经 entity 转义不逃逸 wrapper（tmp_path 构造对抗文件名 + fixtures 驱动良性路径）**

## R2 · tests/round-exec.sh 命令注入（T12-03 半面，P2）
- 证据：`tests/round-exec.sh:19,29,92-102` 将 `${ROUND_DIR}`/`${TIER}`/`${EXPECTED_CHAPTERS}` 插值进 `python3 -c "…"` 双引号 shell 串（92-102 多行块三变量插值；108-113 另有 `'${ROUND_DIR}/.token-hashes.json'` 同类插值）——与 run_pipeline.sh 同类双语言（shell+Python）逃逸；:78/:84 为 stdin 传入，安全，不动
- 边界：`run_pipeline.sh:31-38,70-79` 同缺陷归 spec #64 T2（F003/F1013/T1205，argv 传参改造），本 spec 只修 round-exec.sh，不触碰 run_pipeline.sh（禁双修）
- 修复：`python3 -c` 调用改 argv 传参（`python3 -c '…' "$ROUND_DIR"` + python 侧 `sys.argv[1]`）或等价参数化（本文件 JSON 解析已全用 python json，无 grep -o 面——该条款为自 run_pipeline.sh 漂移，不适用；argv 化后值须经 `json.dump` 序列化写入，顺带修复 EXPECTED_CHAPTERS=N/A 未加引号破坏 progress.json 的隐性 bug，不得用字符串模板回写保留旧形态）
- 测试接线：pytest 包装 `tests/test_round_exec_injection.py` 以 subprocess 跑 `bash tests/round-exec.sh --validate <恶意目录名>` 样本矩阵（`'`、`"`、`$()`、反引号、括号平衡串）——round-exec.sh 本身无 CI 调用方，pytest 包装是进 `just check` 的唯一面；create 模式需活模型，不在验收面。**防空洞前提**：恶意名目录须预置 summary.json+meta.json，否则 `--validate` 在 round-exec.sh:13-16 因 summary 缺失先行 FAIL、永远到不了被修的 :19/:29 参数化调用——矩阵用例必须断言「注入 payload 未执行」（如目录内不出现 payload 侧写文件）且退出非零来自参数化路径本身的响亮报错
- **验收：注入样本经 pytest 包装跑 `--validate` 模式行为=响亮报错非零退出（不执行任意命令、不静默死）**

## R3 · 按名拼接的词法防御（T12-06，P2）
- 证据：`dispatch_helper.py:599` `_PROJECT_ROOT / "skills" / skill / "SKILL.md"`、`contracts/legacy.py:200` `load_contract(skill)`（经 `_skill_path`，也被 `requires_independent_agent` 复用）、`phase_runner.py:150` `PROJECT / "skills" / skill / "SKILL.md"` 三处按名拼接均无 skill 名词法校验（当前调用方全为硬编码配置，未来不可信 skill 名 → 任意仓库文件读入 system prompt + 契约混淆）；`src/shenbi/plugins/generate.py:65` `REPO_ROOT / config["output"]` 允许 `..`（:68 为后续 mkdir）
- 拒绝机制：`_skill_path`（contracts/legacy.py）违规 → raise `ContractError`（同文件现有惯例）；phase_runner 拼接点 → `emit_json` + `CommandStatus.ERROR` 信封退出（同 `_sanitize_phase` 惯例）；generate.py 逃逸 → `ValueError` 带路径信息
- 修复：(a) skill 名词法校验单一入口（`^[a-z0-9][a-z0-9-]*$` 白名单，拒绝 `/`、`..`、空），dispatch_helper/legacy/_skill_path/phase_runner 三拼接点与 `load_contract` 复用同一校验函数（校验函数定义于 `src/shenbi/contracts/legacy.py` 紧邻 `_skill_path`，无循环依赖、三调用方 import 可达；74 个现有 skill 名已全量核对零误拒）；(b) generate.py output 路径 `resolve()` 后 `is_relative_to(REPO_ROOT)` 校验，逃逸即报错
- **验收：`../`、绝对路径、空段、大写/特殊字符 skill 名被拒（报错信封）；合法 kebab 名全绿；`config["output"]` 含 `..` 被拒（单测）**

## 残留登记（本 spec 不实施，防孤儿）
- T12-02 的「状态文件只读保护」（pipeline-state/gate-markers/scores 对 codex 写面的预防性约束，区别于 C32 已落地的写审计检出）与 T12-05 的「safe_write 零规范化」——两条均已以边界注记形式补记到 spec #45（c31-injection-authorization），由其 R3/R4 范围收口
