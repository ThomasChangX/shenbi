# Spec #107 · 审评分档（reviewer-model-tier）：executor_config per-skill model 键 + dispatch 单源接线 + 评计量表 A/B 预注册（thinking 解禁/第二模型）

**日期**：2026-11-15｜ **系列**：评审工艺批（review-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟡 P2（机制先行，采用门槛=用户配置第二模型端点）
**动机证据**：`src/shenbi/pipeline/dispatch_helper.py:3713`（model 单全局：`os.environ.get(SHENBI_LLM_MODEL, "deepseek-v4-flash")`，:93-97 定义）——executor_config.toml 全文无 model 键，**审与写同模型同端点**；`executor_config.toml:120-186`（评审计族全员 `thinking="disabled"`）+ `:188-195`（根因注释：思考与内容共享 completion 预算，曾 152 empties 烧 ~18% 成本——**权宜非设计**，自注 "revisit with post-rollout data"）+ `:132-135`（"Evaluative queue… deferred to P1 pilot" 欠账自认）；`dispatch_helper.py:251-296`（三键消费面 `_get_skill_temperature/_get_skill_max_tokens/_get_skill_thinking`——第四键 model 的结构平行位现成）+ `:3720`（api_dispatch_start 已 log model——**观测面免费**）；`src/shenbi/gates/g3_independence.py:18-28`（G3.4 fail-closed 校验的是路由号≠生成者——**会话隔离 ≠ 认知隔离**：同模型审写=训练分布盲点共享，写作者的概率惯性审者同样看不见）；`novel-xinghuo-vol1/cost/report.md`（评审族 160/593≈27% 调用、$0.92≈16.7% 成本——分档的成本面基线）。

**触及的不变量维度**：无（执行器配置面）

---

## 0. 根因

**模型选择只有全局一档，「独立审」的独立性止于会话隔离**；评计量表（thinking=disabled+低温）是预算事故的权宜组合，其认识论代价（判官推理深度低于作者）从未被 A/B 数据裁定过——仓库自己在 `:132-135` 标注 "deferred to P1 pilot" 而该 pilot 至今未做。机制缺口很小（一个 config 键+一个 getter），但缺了它一切「换模型审」的实验都无处落配。

**用户裁定（2026-11-15）**：不考虑在飞项目——本件只落机制与预注册协议，不改任何技能的默认档位（默认行为零变化）；A/B 实弹与第二模型端点配置随用户令。

**备选案已评估并否决**：「全链换更强审模型」——评审族已占 27% 调用，全量升档无判据先例（spec #98 分档实验方法论=先机制先预注册）；「评审专用微调/自建裁判模型」——超出当前阶段，机制先行、能力后议。

## 1. 任务分解

### T1 · per-skill model 键 + 单源接线
- executor_config.toml `[overrides."<skill>"]` 支持 `model = "<model-id>"`；`_get_skill_model(skill) -> str | None`（结构平行 `_get_skill_thinking`；None → env 单源缺省；**空串/非 str → 派发前 ValueError fail-loud**，错误文案点名键与技能名）；
- 接线 `dispatch_helper.py:3713`：`model = _get_skill_model(skill) or os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)`（API 双调用点 :3450/:3687 经同一变量，单点改）；
- 观测确认：api_dispatch_start 已记 model（:3720）；cost/report 按 skill 的分账已有——**确认模型维度可从 log/trace 聚合**（若 cost 面无 model 分组键，补分组——plan 期定，最小面）。

**判据**：单测（override 命中/缺省回退 env/空串 fail-loud 三分支）；`git grep -n "_get_skill_model" src/shenbi/pipeline/dispatch_helper.py` 接线命中；executor_config.toml 注释示例（含「默认不设=现状」说明）。

### T2 · 评计量表 A/B 预注册（协议件——跑不跑用户令）
- `docs/research/2026-11-15-spec107-reviewer-tier-ab.md`（spec #98 T0 预注册先例）三臂，对象=review-resonance + review-group-character（判温/动机最需推理链的两技能）：
  - **A 臂（对照）**：现状（thinking=disabled + 0.1/0.15）；
  - **B 臂**：`thinking="low"` + `max_tokens=49152` 头寸（预算根因由头寸解——T1 的 config 键零改动即可配）；
  - **C 臂**：第二模型（T1 model 键；须用户配置端点）；
  - 判据：固定 fixture 章束上 finding 捕获率差分（**#108 canary 为测量器**——本件与 #108 构成依赖对：canary 先行或降级为人工 bug-hunt 束）+ audits 误报率不升 + 完成预算/成本记录；
  - 停机条件与预注册口径全文先落盘，实弹随令。

**判据**：预注册文档落盘（臂/判据/停机条件/成本预算四节齐）；文档引用 #108 测量器并注明降级路径。

### 明确不建
- codex CLI 模式的 per-skill 模型选择（CLI 自身配置域，本件文档化「codex 模式不受此键影响」即可）；
- 任何默认档位变更（含 B 臂 thinking 解禁——一律经 A/B 数据+用户裁定）。

## 2. 验收
1. T1/T2 判据全绿；
2. 默认行为零变化：无 model 键的技能派发 model 取值与现状逐字节一致（差分单测）；
3. 配置容错：toml 解析失败/键类型错 → fail-lloud 报错点名技能与键（不静默回退）。

## 3. 风险
- 第二模型端点不在位 → 本件纯机制不阻塞（C 臂空转至用户配置）；
- B 臂重燃预算截断（thinking 独食 completion 的旧根因）→ 臂内强制 49152 头寸先行，预注册含完成预算监控条款；
- **共享文件面**：dispatch_helper.py 与 #92 在飞 T2a（typed loader 六读者换装）同文件——**#92 → #107** 顺序；executor_config.toml 与 #98 已完结（无在飞冲突）；
- model 键拼错 → 派发时 API 404 类失败重试浪费 → 失败分类（classify_dispatch_failure）对 model-not-found 归确定性失败零重试直 escalation（既有 C33 通道复用，plan 期核对类别归位）。
