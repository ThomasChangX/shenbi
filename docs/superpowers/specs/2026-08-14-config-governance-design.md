> **Date:** 2026-08-14 | **Status:** Revised 2026-08-29 (SDD #13 阶段 3 审查吸收) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** config/ + gates/g0_config_coherence.py + gates/g0.py(cc 调用点) + pipeline/audit_layer.py + pipeline/triggers.py(genre_config_update 消费点) + skills/shenbi-genre-config(契约) | **核心洞察:** 关键审计维度禁用治理存在多条独立绕过向量 + 治理层零接线

# 配置治理绕过

## 向量清单（同一修复批次）
- **F606（P2）**：floor 只认 int，float/str 绕过（59.5 通过）；读侧 G0 `check_config_coherence` 的 `resonance_global_floor` 同样无类型守卫
- **F611（P2）**：规则 1 只拦 `auditDimensions.<dim>:false`，整键对象覆盖绕过
- **F631（P2）**：`is False` 被 falsy 值 0/null/"" 绕过（写侧与读侧同时失明）
- **F643（P2）**：键缺失语义矛盾（G0 视缺失为启用、audit_layer 视缺失为禁用）
- **F666（P2）**：整键标量（`{"auditDimensions": false}`）→ g0 AttributeError 崩溃 + 审计静默停用
- **F638（P2）**：snake_case 配置（`audit_dimensions` 回退）绕过 camelCase 检查
- **F635（P2）**：update_genre_config 治理层零生产调用（genre-config 由 skill/CLI 直写）
- **F614（P2）**：中途 ConfigError 留 audit-trail 幻影条目

## 修复设计

### R1 · Rule 1 统一重写 + 类型守卫（F606/F611/F631/F666，写侧+读侧）
- 写侧 `config_coherence.py` Rule 1 改为：对任意触及 `auditDimensions`（整键或任意前缀，camelCase 与 snake_case 两形，见 R3）的 change，解析**新旧合并后**的关键维度终值；终值 `value is not True`（即 `False/0/None/""` 一律视为禁用；`1`/truthy 不视为显式启用）为禁用时，critical 维度须 ≥50 字 rationale。dotted-key `changes` dict **无法表达键删除**（无 absence 哨兵；`None` 即 falsy 禁用，照常被拦）——删除仅经由整文件覆盖路径发生、由 R4 的 diff 治理管辖；dict 路径中未提及的键为 no-op
- Rule 2 类型守卫：`resonance_global_floor` 接受 int 与 float（`isinstance(v, (int, float)) and not isinstance(v, bool)`），低于 trigger 即拒；str 拒绝并报 ConfigError。读侧接线：`g0.py:672` 调用点现未传 `resonance_global_floor`（恒 None、floor 检查死线）——本 spec 补线：当 PipelineState 存在时传入其 config 的 floor 值，读侧同口径守卫。已知非对称（接受，不在本 spec 处理）：写侧允许 floor ∈ [60,65) 而 G0 `threshold_mismatch` 标记任何偏离 65 默认值的配置
- F666：`check_config_coherence` 对 `auditDimensions` 非法形态（非 dict 的标量/列表）**不崩溃、响亮失败**——产出 `G0.cc.malformed_audit_dimensions` FAIL 条目；`g0.py` 调用点 except 子句**不扩大**（类型守卫在 checker 内闭环，禁止裸 except 吞错）
- **验收**：4 向量（F611 整键对象、F631 falsy、F666 标量、F606 float/str floor）全部在写侧被拦截或读侧被 G0 标记；`{"auditDimensions": false}` 使 G0 返回 FAIL 而非 AttributeError

### R2 · 键缺失语义统一（F643）——按 criticality 分裂
- 统一语义：**critical 维度（AUDIT_SAFETY_MATRIX 中 `critical: true`：texture/antiAi/continuity）缺失 = 启用**（两侧一致）；**非 critical genre 维度缺失 = 不激活**（显式 opt-in，维持现状）。判活口径三处统一为 `value is True`（truthy 值如 `1` 不算显式启用——G0 的 critical 禁用检查从 `is False` 改为键存在时 `is not True`、运行时不激活，fail-safe 且消除三处语义分叉；`texture: 1` 纳入派生验收变体）
- 读侧 G0 维持 `get(dim, True)`（仅对 critical 维度）；`audit_layer.get_active_genre_audits` 对 critical 维度改 `get(dim_key, True)` + `is True` 判活。爆炸半径核查：critical 三维中仅 `texture` 在 GENRE_ACTIVATION_MATRIX（antiAi/continuity 为 core-circle 固定步、被 `_CORE_CIRCLE_KEYS` 过滤），且两份真实配置（novel-output/xinghuo-ranqiong、test-validation）均显式 `texture: true` → 对现有配置零行为变化、零新增 dispatch
- **验收**（针对整文件 diff 路径 `govern_genre_config_change`）：新配置删除 `texture` 键 → 治理视为对 critical 维度的禁用企图，无 ≥50 字 rationale 即 ConfigError；读侧 audit_layer 仍激活 texture 审计（缺失=启用），G0 不误报。fixture 注记：`tests/fixtures/genre-config-example.json` 本身含 `texture: false`（真实 rationale 案例），「删除 texture」变体从其派生时是「禁用→回退启用」方向的断言，非 fixture 矛盾

### R3 · 键形统一（F638）
- 抽取共享 helper `resolve_audit_dimensions(config) -> tuple[dict[str, Any], bool]`（返回 (合并后维度 dict, malformed 标志)；camelCase `auditDimensions` 优先、snake_case `audit_dimensions` 仅补充 camelCase 未出现的键；**任一键形存在但非 dict 即整体 malformed**（含合法 camelCase dict + 杂散标量 snake_case 键的组态——fail-safe 取 FAIL 而非部分解析，显式选择）→ malformed=True、返回空 dict）。Rule 1 写侧、G0 读侧、audit_layer 运行时**三处共用同一实现**，防两套合并逻辑漂移；audit_layer 现有回退行为语义不变（malformed 时运行时结果与今日 isinstance 守卫一致=[]）。写侧遇 malformed change 值直接 ConfigError
- **验收**：`{"audit_dimensions": {"texture": false}}` 在写侧触发 rationale 要求、读侧被 G0 标记

### R4 · 治理层接线（F635）——创建/更新分流
- **创建路径不动**：pipeline-init（cli.py 直写 seed 派生配置）保持 `safe_write`，初始创建无 rationale 语义
- **rationale 源头补齐（前置工作项）**：`skills/shenbi-genre-config` 契约扩写 decisions sidecar（`kind: artifact` + writes 增 `genre-config-decisions.json`，schema `shenbi-decisions-v1`）；rationale 载体用 `selections[]`（`basis: manual_override`，P2.5 已强制其带 rationale）而非 `adjustments[]`（后者语义是 drift 处置，不复用）；schema 演进：`chapter` 字段对非章节型 skill 可空——触点三处（decisions-schema.md 文档、`contracts/schemas/decisions.py:76`、G2 decisions 分支 g2.py 与 G4 decisions_validator.py 的必填校验放宽；G4 `_check_adjacent_budget` 按文件名锚定 chapters/ 不受影响），存量 sidecar 均含 chapter，放宽为向后兼容。
- **更新路径接线**：消费点 = `run_triggered_skills`（triggers.py:479-601；流程 = dispatch ~532 → G4 565-581 →（可选 G3；genre_config_update 现无 requires_g3，如未来增补须一并纳入回滚阶段））。对 `category=genre_config_update` 的 TriggerStep：(a) dispatch 前**快照** `genre-config.json`；(a′) sidecar 校验机制：`gate_G4` 为该 skill 组合 `make_composite_checker(g4_genre_config, g4_decisions)`，组合路由**按文件名分区**（`*-decisions.json` → decisions checker，其余含非-decisions `.json` → existing/structural checker）——现有按扩展名分区（`.json` 全进 decisions checker）在收窄后会把 genre-config.json 静默漏检致 `fps=[]` 假 FAIL，须一并改为按文件名分区。**共享 helper 爆炸半径（整改清单）**：① `generic.py:333` `make_composite_checker(g4_decisions, g4_chapter_revision)` 为反向注册（今日 `.md` 喂 g4_decisions 被静默跳过、`.json` 喂结构 checker，本就错乱）——规范化参数序为 `(g4_chapter_revision, g4_decisions)` 并补/迁测试锚定 `.md` 走结构校验、`*-decisions.json` 走 DecisionsDoc；② 逐一审计其余 4 个存量 composite 注册（chapter-drafting / chapter-planning / context-composing / state-settling）在该 skill G4 实际文件集下无非-decisions `.json` 落入 md 结构 checker（结构 checker 无 `.json` 守卫），有则显式路由；call site 传 `[genre-config.json, genre-config-decisions.json]`（sidecar 路径经 `resolve_contract_path` 同款解析，同 step.output_path 待遇）；skill 契约改动后跑 `just generate` 同步生成物（deps.json/docs/数据契约块），禁手改；(b) G4 通过后对 **快照 vs 新配置 diff** 跑 `govern_genre_config_change(project_dir, old_config, new_config, rationale) -> None`（diff 中被禁用/删除/降低的 critical 项按 Rule 1 处置——floor 不在 genre-config.json 内（居 PipelineState.config），diff 路径无 Rule 2 适用；通过则追加 audit trail，violation 抛 ConfigError）；(c) **任一失败阶段（dispatch / G4 / 治理 ConfigError）一律回滚**（本 step 原子性；后续其他 step 的失败不回滚已成功的 genre-config 更新——per-step 原子、显式声明）：`safe_write` 恢复快照旧配置 + 删除本次产出的 stale `genre-config-decisions.json`（及 skill 铁律 4 的 `genre-config.json.bak.*`）+ 按既有 `last_trigger_failure` 机制记失败——被拒/失败更新不得留存在盘上；(d) rationale = sidecar `selections[]` 中 `basis=manual_override` 条目 rationale 的合并摘要，合并后 <50 字即 ConfigError、>500 字亦 ConfigError（逼 skill 产单条 50-100 字合并 rationale；上限防 trail 行不可 grep）
- `update_genre_config`（dotted-key API）保留为库 API 并维持测试覆盖，但生产路径以 `govern_genre_config_change` 为准（docstring 注明）
- 更新 `config_coherence.py` 模块 docstring 使其与实际路由一致
- **验收**（可执行）：单测 `govern_genre_config_change`——有效更新（含 rationale 的 texture 禁用）通过且 `config-change-log.jsonl` 增加对应条目；无 rationale 的 critical 禁用抛 ConfigError 且函数无副作用；集成路径：fixture 旧配置 + 派生新配置经 `run_triggered_skills` 断言 ConfigError 后盘上配置 == 快照、trail 无新增行

### R5 · 两阶段提交（F614）
- `update_genre_config`（及 R4 的 `govern_genre_config_change`）先对**全部** changes 完成校验，再统一落盘 config + 逐条追加 trail——中途 ConfigError 不留任何 trail 幻影条目
- **验收**：混合有效+无效 change 批次抛 ConfigError 后 `config-change-log.jsonl` 无新增行

## 执行顺序
R1（含 F666 G0 响亮失败）→ R2 → R3 → R4 → R5（R5 依赖 R4 产生生产语义，最后落地）

## 测试与 fixture 计划
- 基线：`tests/fixtures/genre-config-example.json`（真实产物副本，已在库）；bypass 变体（整键覆盖/falsy/标量/snake_case/float floor/`texture: 1`）在测试内**程序化派生**自该副本（G0.9：不手写 fixture）；audit trail 的合并 rationale 上限 500 字已在 R4(d) 强制（超限 ConfigError）
- 测试层级：全 T1（unit），治理接线 R4 加 chapter_loop/triggers 消费点单测
