> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 2/7） | **依赖:** contract-single-source | **范围:** decisions.json 全链（producer 模板 → 写路径 → G4.dec 门 → 下游读取）| **核心洞察:** decisions-schema v1 契约在生产主路径三态并存——写入无校验（T1-03）、读取悬空（T1-04/T1-05）、产物滞留（T1-05），G4.dec 恒 SKIP（T1-01 = Z11-01 根因答案）

# Decisions 链（补齐 B）

## 症状
- 真实产物 96% 无效：145 文件中 83 invalid JSON + 57 schema 违反 + 仅 5 通过（T1-02）
- G4.dec 恒 SKIP "no files"——_resolve_g4_files 只返回 step.output_path 单一 .md（T1-01，生产 gate marker 实证）
- 写路径 _validate_json_output 仅语法校验、IDE/codex 直写完全绕过（T1-03）；磁盘 67 个 "Extra data" 文件证明未经过 raw_decode 截断
- Z11 产物侧：83/145 无效根因 = 门侧 SKIP + 写侧绕过双因素（F1304）；62 个可解析中 57 schema-ok（F1305）；DEBUG_USE_MANUAL_CREATE 暴露手动路径（F1303）

## R1 · G4.dec 文件列表接入 decisions.json（T1-01, P1）
- 证据：_resolve_g4_files（chapter_loop.py:565-584）只返回 step.output_path；真实 marker `G4-shenbi-chapter-drafting-generative.json` 含 `{"id":"G4.dec","s":"SKIP","r":"no files"}`
- 修复：_resolve_g4_files 纳入契约全部输出（含 .json）；**验收：真实产物 decisions.json 进入 G4.dec 检查列表，无效文件 FAIL**

## R2 · producer 模板与 prompt 编码 schema/P2.5（T1-02, P1）
- 证据：5 个 skill 的 SKILL.md 输出模板无 decisions 段；dispatch_helper.py:725 仅一句 "must conform" 且文档不可达
- 修复：SKILL.md 模板内嵌 decisions 示例段 + prompt 注入 schema/P2.5 摘要；**验收：真实产物 schema 违反率显著下降（目标 <20%）**

## R3 · 写路径 schema 前置校验（T1-03, P1；F1303/F1304/F1305, P1）
- 证据：_validate_json_output 对 clean JSON 原样放行；IDE/codex 直写绕过（modes/codex.py:61-66）；DEBUG_USE_MANUAL_CREATE 暴露手动路径
- 修复：所有写路径（含 IDE/codex）经 DecisionsDoc.model_validate 校验，失败 FAIL + 不落盘；DEBUG 路径移除或加门禁
- **验收：磁盘 decisions.json 100% schema 有效或带明确校验失败标记**

## P2 清单
- **T1-04（P2）** context/chapter-N-context-decisions.json 悬空读：producer（context-composing）被确定性策展替换，consumer（chapter-drafting）仍声明该读，API 路径无 G1 → 静默丢失
- **T1-05（P2）** plan-decisions.json / state-settling-decisions.json：registry 声明但零契约 producer，且 staging commit 只提交契约路径/仅 *.md → 55+1 文件滞留 staging，从未 commit/校验/读取
- **T1-06（P2）** SkillOutput.decisions 死字段：定义+prompt 要求输出，但写路径从不消费
- **T1-07（P2）** decisions-schema.md ↔ DecisionsDoc 双向往弱漂移：selections 标 REQUIRED 但 model 默认 []；produced_at 标 ISO 8601 但 model 仅 str；selections severity 含 medium 且 docs 未列
- **T1001（P2）** D1 行号订正在归档 spec 中再次漂移（4 处关键引用偏离实际代码 7-22 行）
- **T1101（P2）** mutmut 按仓库配置结构性不可运行；基线文档归因错误
- **T1102（P2）** mutation-score.txt 非基线；`just mutate-check`/compare_mutation_score.py 恒 exit 2 死工具
- **T1103（P2）** 突变分数下界 59.6%（exceptions 41.1% / logging 58.6% / shared 63.3%），未达宣称 P-3 80%
- **T1105（P2）** G0.8/G0.9/G0.9c 只扫 `scenario.md`，`scenario-pressure.md` 免疫——6 个压力场景 5 个含同款非 fixture 路径引用
- **T1107（P2）** `tests/benchmark/` 空洞（仅 `__init__.py`）；唯一 benchmark 测试是 `1+1` 冒烟；`norecursedirs "tests/benchmarks"`（复数）指向不存在目录
- **T1108（P2）** gate-outputs 差分基线陈旧（2026-06-15）且无 enforcement；G6/G7 基线因 round-001 目录消失而不可再生
- **T1109（P2）** `tests/golden/` 空洞确认（README 声称 10-20 章，目录仅 README；P1.8 验收"≥10 章人工评分"未实现；0 消费方）
- **T12-03（P2）** run_pipeline.sh 与 tests/round-exec.sh 将目录参数插值进 `python3 -c "…"` 双引号 shell 串 → `'`/`"`/`$()`/反引号 均可注入任意命令（命令注入；Z10 区确认 + 新实例）
- **T12-04（P2）** codex/zcode 子进程全量继承父环境：SHENBI_LLM_API_KEY（T1 路径）/CI token 等凭证可达 workspace-write 通用编码 agent；与 T12-02 注入链叠加构成凭证外泄路径
- **T12-05（P2）** 写路径穿越防御脆弱隐式：`relative_to` 词法不归一化 `..`（拦截仅靠 wildcard 正则形态）；symlink 目录逃逸（声明目录为 symlink 时契约校验通过的写落盘到 link 目标）；safe_write 零规范化
- **T12-06（P2）** 按名拼接的防御缺失：`skills/{skill}/SKILL.md` 与 `load_contract(skill)` 无 skill 名词法校验（当前调用方全为硬编码配置，未来不可信 skill 名 → 任意仓库文件读入 system prompt + 契约混淆）；plugins/generate.py `REPO_ROOT / config["output"]` 允许 `..`
- **T1301（P2）** pytest-asyncio 声明于 dev group 但全仓零异步测试（休眠插件）
- **T1302（P2）** pytest-ordering 声明但零使用，且 0.6（2019）无人维护
- **T1303（P2）** numpy 为核心依赖但其全部引用点仅在 Route B 可选路径执行
- **T1304（P2）** dev group 的 setuptools 无任何运行时消费者（冗余直接声明）
- **T14-02（P2）** hook_planting 死线补全（F307 新面）：TRIGGER_STEPS 卷边界仍 dispatch LLM 版 shenbi-foreshadowing-plant（活跃路径），与 foreshadowing-resolve 同块双写 pending_hooks.md
- **T14-05（P2）** memory-distill 密度触发（60/15/20 阈值计数）声明未实现：确定性计数规则停留 SKILL.md，triggers.py 无密度检查
- **T14-06（P2）** 双路由重复：review-resonance 的三路径分流（skill_utils.review_resonance.routing + calibration，SKILL 指令级）与 pipeline 侧 route_chapter_revision 是两套独立路由
- **T14-07（P2）** 系统性模式：16 个确定性助手仅 ~5 个代码层接线——"确定性替换已 9 次实现"的说法是"实现 16 次、接线 ~5 次"；供 phase 4 聚类的母模式
- **T1501（P2）** 96MB 孤儿 blob（commit 对象 dump）无路径、unreachable；`.git` 膨胀 75MB
- **T1502（P2）** gh-pages 分支 mkdocs 构建产物入库（search_index.json 6.9MB + bundle js.map 1MB）+ 5 个 6.5-6.9MB 孤儿 search_index 变体 + 4.1MB 文件清单 dump + 673KB uv.lock 孤儿
- **T1503（P2）** 孤儿分支 `docs/token-efficiency-p2-spec`：P2 效率 spec + field-level 3.7 spec 从未合并 main 也未归档；Layer B 功能已实现（ea9575e）但文档悬空
- **T1504（P2）** 远程分支残留：sdd/inference-control-audit（13 commits 已 squash 合入 #40 未删）、docs/archive-inference-control（已合入 #41 未删）、pre-commit-autoupdate 升级未合入（ruff/mypy/hooks 版本滞后）、10 个 dependabot 分支 NOT-IN-MAIN
- **T1505（P2）** G5 numeric revert 闭环未完成：b74e9ae 修复 → dc6fc67 revert（pin inert）→ 承诺的 source PR 从未落地；`m.group(2)` 非捕获组 IndexError 被吞、numeric 检测死路被测试固化（F498 历史根因）

## M 清单（并入 M 批量 spec）
- **T1-08（M）** G2.dec.4 多对象检测按 `"$schema"` 原始计数：对 67 个真实 "Extra data" 拼接 0 命中（均不重复 $schema），反而对 rationale 字符串内出现 `"$schema"` 文本的合法文件有误报面
- **T1002（M）** INDEX:91 "PR #20 torch-bump 处置（待 #3 follow-up）" 注记过期
- **T1104（M）** `[tool.mutmut] paths_to_mutate` 弃用（mutmut 3.6 应 `source_paths`）
- **T1106（M）** 压力场景计数错误（简报 7 个 vs 实际 6 个）+ 场景非自包含（需手工构造虚构项目）、无 runner、无自动化执行证据
- **T1305（M）** plugins/master.json version=0.2.0 与 pyproject version=0.1.0 漂移，无同步机制
- **T1306（M）** pyproject.toml:11 pydantic 注释"P-1 不用；为 P0 schemas 准备"已过期
- **T1506（M）** dispatch_helper zcode 半迁移残留：auto-detect 已 revert 但 IDE CLI 路径仍列 zcode + "requires separate testing"/"future zcode usage-report" 注释
- **T1507（M）** `contracts/legacy.py` 命名残留：文件名 legacy 实为当前单源契约加载器（docstring 自述）
- **T1508（M）** 归档文档 broken links：2026-06-15-p-1.e-06-enterprise.md → 0001/0002/0009-ADR 链接失效；ci-optimization-design.md → `file.md`；eliminate-existing-warnings-plan.md → `../nonexistent-test-link.md`
