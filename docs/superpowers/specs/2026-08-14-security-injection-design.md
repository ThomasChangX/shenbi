> **Date:** 2026-08-14 | **Status:** Design (Revised 2026-08-30) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 5/7）| **依赖:** 无 | **范围:** wrapper 属性注入（T12-01 属性半面）/ round-exec.sh 命令注入（T12-03 半面）/ 按名拼接防御（T12-06）
> **修订记录（2026-08-30，SDD #22 价值门 REWRITE）:** 收窄为未被承接的独占面；已承接面让渡——T12-01 内容侧 no-op 转义（F300/F308）→ spec #45 R2；T12-02 持久化注入链与 codex 写面 → F512 已由 C32 R3（PR 合并 26db756）修复写审计接线，判定伪造缓解与 env/路径/symlink 面归 spec #45（T1201/T1206/T1207/T1204）；T12-03 的 run_pipeline.sh 半面 → spec #64（F003/F1013/T1205）；T12-04 → spec #45 R4（T1207）；T12-05 → spec #45 R3（T1204）。**禁止双修**：上述让渡面本 spec 不实施。

# 安全与提示注入（补齐 E · 修订收窄版）

## R1 · wrapper 属性侧注入与文件名词法白名单（T12-01 属性半面，P1）
- 证据：`dispatch_helper.py:781` `<document name="{fname}">` 属性值零转义，`fname` = `full_path.relative_to(project_dir)`；`_wildcard_to_regex` 的 `[^/]*` 放行 `"` 文件名（实证 `import/canon/x" auto="1.md` 匹配 `^import/canon/[^/]*\.md$`）→ 逃逸 wrapper 属性注入 prompt
- 修复：(a) 属性值转义（`&quot;`/`&lt;`/`&amp;` entity）；(b) wildcard 写路径落盘前文件名词法白名单（拒绝 `"`、`<`、`>`、控制字符）
- 边界：内容侧 `<`→`\u003c` no-op 转义（F300/F308）归 #45 R2，本 spec 不动 `safe_content` 转义逻辑
- **验收：含 `"` 文件名的 wildcard 写被拒绝（FAIL 不落盘）；已含 `"` 属性的既有文件名读回时属性值经转义不逃逸 wrapper（fixtures 驱动测试）**

## R2 · tests/round-exec.sh 命令注入（T12-03 半面，P2）
- 证据：`tests/round-exec.sh:19,29,92-99` 将 `${ROUND_DIR}`/`${TIER}`/`${EXPECTED_CHAPTERS}` 插值进 `python3 -c "…"` 双引号 shell 串——与 run_pipeline.sh 同类双语言（shell+Python）逃逸
- 边界：`run_pipeline.sh:31-38,70-79` 同缺陷归 spec #64 T2（F003/F1013/T1205，argv 传参改造），本 spec 只修 round-exec.sh，不触碰 run_pipeline.sh（禁双修）
- 修复：`python3 -c` 调用改 argv 传参（`python3 -c '…' "$ROUND_DIR"` + python 侧 `sys.argv[1]`）或等价参数化；JSON 解析用 python json 模块替代 grep -o 形态
- **验收：注入样本矩阵（目录名含 `'`/`"`/`$()`/反引号/括号平衡恶意串）行为=响亮报错退出，不执行任意命令（测试固化进 round-exec.sh 自检或 tests/）**

## R3 · 按名拼接的词法防御（T12-06，P2）
- 证据：`dispatch_helper.py:599` `_PROJECT_ROOT / "skills" / skill / "SKILL.md"` 与 `contracts/legacy.py:200` `load_contract(skill)` 均无 skill 名词法校验（当前调用方全为硬编码配置，未来不可信 skill 名 → 任意仓库文件读入 system prompt + 契约混淆）；`plugins/generate.py:67` `REPO_ROOT / config["output"]` 允许 `..`
- 修复：(a) skill 名词法校验单一入口（`^[a-z0-9][a-z0-9-]*$` 白名单，拒绝 `/`、`..`、空），拼接点与 `load_contract` 复用同一校验函数；(b) generate.py output 路径 `resolve()` 后 `is_relative_to(REPO_ROOT)` 校验，逃逸即报错
- **验收：`../`、绝对路径、空段、大写/特殊字符 skill 名被拒（报错信封）；合法 kebab 名全绿；`config["output"]` 含 `..` 被拒（单测）**

## 残留登记（本 spec 不实施，防孤儿）
- T12-02 的「状态文件只读保护」（pipeline-state/gate-markers/scores 对 codex 写面的预防性约束，区别于 C32 已落地的写审计检出）与 T12-05 的「safe_write 零规范化」——两条均已以边界注记形式补记到 spec #45（c31-injection-authorization），由其 R3/R4 范围收口
