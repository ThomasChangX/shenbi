> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-02 · 阶段 2 实核收窄 + 设计审查 R1 修订:F442 已修剔除、F204 重钉、T1 按边界类型拆分、C29 软依赖、F337/F614/F1018 归属定名) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C12，28 条）| **代表 finding:** F102 | **严重度上限:** P1（F102/F203/F517/F976）| **涉及文件面:** phase_runner.py、scoring.py（子进程/gate 调用）、dispatcher/（executor、modes/codex、cli）、dispatch_helper（_write_parsed_outputs/extract）、gates/（jload 面）、trace/（writer、versioning）、skill_utils/（compute_pattern）、plugins/generate.py、tools/generate_autocheck_docs.py、run_pipeline 脚本面（注入项归 C26）

# 裸崩边界守卫（audit-crash-boundary-guards）

## 背景

子进程输出 json.loads 无守卫、超时/None/畸形输入以 traceback 穿透；LLM stdout 提取用首匹配正则/字面回退把垃圾写进产物。错误本应降级为结构化失败（BLOCKED/FAIL + stderr 上下文），实际以裸崩或垃圾数据形式穿透。四类证据：

1. **P1 级**：F102（cmd_start/cmd_finalize 把 str(None)="None" 当 project_dir 传 G5——按 AGENTS.md 文档用法 G5 恒 FAIL，verified）；F203（codex 输出 JSON 提取正则取最内层扁平对象，嵌套 scores 解析错误，verified）；F517（坏 YAML truth 使审计崩溃，finally 掩盖 + 审计行丢失）；F976（上轮 F140 断链复现：shenbi-score 成功路径恒 exit 1——console script 对非 int 返回值 + stderr 混入 dict repr，协调者实跑复现）。
2. **子进程边界无守卫**：F106（run_gate 未捕获 TimeoutExpired，gate 超时整机 traceback 而非 BLOCKED）、F125（两处 gate 子进程无 timeout，挂起无限等待）、F107（--gate-only 裸 json.loads stdout + --type 缺值 IndexError）、F124（cmd_post_score 对 malformed scores 裸抛 JSONDecodeError——该检查正是为这场景而写）、F204（run_g1/run_g2 无守卫 json.loads，崩溃丢 stderr）、F403（8 个 gate 的 jload ValueError 未捕获 → traceback）。
3. **LLM stdout 提取/落盘边界**：F329（_write_parsed_outputs literal 路径回退：整段 stdout 写入目标文件——模型路径漂移时垃圾写入）、T509（截断 `### FILE:` 输出实测被解析器静默接受并落盘——与 C29 截断标记联动）、F234（extract_chapter 首匹配正则，多章号路由错章）、F223（from_markdown 首次匹配 + 子串场景识别，散文数字污染 G4 输入）。
4. **散点裸崩**：F123（main() 位置参数与 flag 共用无解析器，缺位时 flag token 绑定为 phase/skill 并写垃圾状态文件）、F135（--chapter 非整数裸崩）、F409（hooks YAML 列表含字符串 → AttributeError）、F437（文档化三段式相对路径调用未捕获 ValueError）、F509（snapshot 无 id 记 "None" 键碰撞）、F526（snapshot_tree 非UTF-8/目录/TOCTOU 使审计链崩溃）、F608（torn-tail 时 TraceWriter 构造裸 JSONDecodeError）、F621（章节列表非 dict 元素裸崩）、F626（versioning 死循环理论路径）、F627（gen_codex 裸 KeyError）、F442（复合 checker 角色倒置致 gate 名错标）、F337/F1018（CLI 零测试/工具脚本缺陷）。

## 修复目标

1. 全部子进程边界（gate/scoring/skill 调用）：超时捕获 → BLOCKED；stdout 非法 JSON → 结构化 FAIL + stderr 摘要；零 traceback 穿透到顶层。
2. LLM stdout 提取：无有效结构时拒绝落盘（结构化失败），字面回退路径删除或显式标记 quarantined。
3. CLI 入口参数全量校验（argparse/类型检查），文档化用法 100% 可执行。
4. shenbi-score 成功路径 exit 0（F976 断链修复）。

## 任务分解

- **T1a · 子进程守卫统一（F106/F107/F125/F204/F124）**：抽公共 `run_subprocess_json()` helper（timeout + 捕获 TimeoutExpired/JSONDecodeError → 结构化 GateResult/exit code + stderr 尾部上下文）；**仅用于真实子进程边界**：phase_runner.py `run_gate`(:113-134，补 TimeoutExpired)、scoring.py `--gate-only` 路径(:381-391)与 G3 前置子进程(:420-432，无 timeout + `except Exception: pass` 吞错一并修)、phase_runner cmd_post_score(:346)。
- **T1b · gate jload 守卫扫尾（F403 残余）**：gate jload（shared.py:51）是**进程内文件读**，不是子进程边界——不用 T1a helper，按既有守卫惯例（g5.py:38-48 形态）对残余裸调点逐个 try/except → 结构化 `fail(...)`：g5.py:59、g_reconcile.py:34（g3.py:137/151/203/265 已被 F444 守卫覆盖，剔除）。守卫不得引入副作用（AGENTS.md gate 检查器纯函数幂等）。
- **T2 · LLM 输出提取硬化（F203/F329/T509/F234/F223）**：JSON 提取改"全部候选 + schema 判别"（或 json 五指纹定位）替代最内层/首匹配正则（codex.py:131）；_write_parsed_outputs 删除 literal 整段落盘回退（dispatch_helper.py:1455-1457 `__stdout__` 回退；解析失败 → quarantined 文件 + FAIL，不写目标路径；注意 `__stdout__` 作为**契约声明路径**的合法路由(:1468)保留，仅删除回退用途）；extract_chapter 多章号歧义 → 显式错误；截断输出拒绝——**基础截断检测独立可做**（末个 `### FILE:` 块未闭合/无内容即拒），C29 截断标记协议（spec #44）为后续增强，**非硬依赖**。
- **T3 · CLI 参数协议（F102/F123/F135/F437/F107 argv 面/F337 残余/F1018）**：phase_runner main() 换 argparse（位置参数/flag 分离）；None/空 project_dir、非整数 chapter、相对路径语义在入口校验并输出用法错误（exit 2 而非 traceback/垃圾状态）；F102 的 "None" 字符串判定加哨兵测试；F107 的 `--type` 缺值 IndexError（scoring.py:380，argv 解析面）归本 task；F337 残余（gates/cli.py:141 `a1.split(",")` 逗号歧义）随 CLI 面一并处置；F1018（工具脚本 `tools/generate_autocheck_docs.py:122` repl 未转义）归属本 task 批量处置；全部入口 `--help` smoke 测试。
- **T4 · 散点裸崩修复（F409/F509/F526/F608/F621/F626/F627/F517/F614）**：逐点类型守卫/结构化异常（YAML 形状校验、"None" 键哨兵、UTF-8 errors 处理、torn-tail 容错构造（writer.py:63）、非 dict 元素跳过+WARN、versioning 无注册迁移 raise、plugins/generate.py .get 缺省、executor.py:302-306 finally 守卫 + records/parser.py:40 yaml.safe_load 守卫（坏 YAML → 结构化审计失败不丢行）、trace/materialize.py:81 round 字段 "???" 归一化）。F442 已修（PR 前序合入）剔除。
- **T5 · exit code 契约（F976）**：console script 返回 int；成功路径 exit 0——以 `tests/fixtures/` 固定 scores.json 驱动的 pytest 回归用例钉死（95 分 PASS → exit 0），不依赖协调者手跑。
- **T6 · 防复发 lint**：`git grep -nE "json\.loads\(.*(stdout|output)" src/shenbi` 清点零裸调用（全经 T1a helper）；**豁免类**：gate 内部 jload（T1b 形态，非子进程边界）逐点带豁免注记；CI 加 ruff 规则或 grep 断言。

## 批量清理（纯 M 成员）

- F135/F337/F614/F621/F626/F627/F1018 随 T3/T4 批量处置（归属已在任务分解定名）；F442 已修剔除。

## 验收标准

1. 回归用例集：文档化命令逐条实跑（含 F102 AGENTS.md 用法、F437 三段式、F976 评分成功路径）全部 exit 0 或结构化 FAIL，零 traceback；CLI 入口 `--help` smoke 全过。
2. 单测：超时 gate → BLOCKED；非法 JSON stdout → FAIL 含 stderr 摘要；截断 ### FILE: → quarantined 不落目标（T1a/T2 断言）；**T2 回归验收**：fixtures 驱动的 dispatch 解析失败场景 → quarantine 文件写入 + 目标路径未被写 + 结构化 FAIL（非 crash）。
3. `git grep -nE "json\.loads\(" src/shenbi | grep -v run_subprocess_json` 为空或每项带豁免注记（gate 内部 jload 属豁免类，T6 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险：提取硬化（T2）会把此前"侥幸解析成功"的边缘输出改为失败——quarantined 机制保留原始输出供人工/重试恢复，不丢数据；删除 literal 回退后某些低质量模型轮次显性 FAIL，属预期收紧。
- 回滚：T1 helper 逐调用点迁移可分批；T2 每提取器独立提交；quarantine 目录可整体清理。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C12（28 条，代表 F102）：

F102 F106 F107 F123 F124 F125 F135 F203 F204 F223 F234 F329 F337 F403
F409 F437 F442 F509 F517 F526 F608 F614 F621 F626 F627 F976 F1018 T509
