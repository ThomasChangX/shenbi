> **Date:** 2026-08-14 | **Status:** Revised 2026-08-29 (SDD #13 阶段 3 审查吸收) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** config/ + gates/g0_config_coherence.py + gates/g0.py(cc 调用点) + pipeline/audit_layer.py | **核心洞察:** 关键审计维度禁用治理存在多条独立绕过向量 + 治理层零接线

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
- 写侧 `config_coherence.py` Rule 1 改为：对任意触及 `auditDimensions`（整键或任意前缀，camelCase 与 snake_case 两形，见 R3）的 change，解析**新旧合并后**的关键维度终值；终值经 falsy 判定（`not value` 且非显式布尔 `True`——即 `False/0/None/""` 均视为禁用）为禁用时，critical 维度须 ≥50 字 rationale
- Rule 2 类型守卫：`resonance_global_floor` 接受 int 与 float（`isinstance(v, (int, float)) and not isinstance(v, bool)`），低于 trigger 即拒；str 拒绝并报 ConfigError。读侧 G0 floor 检查同口径
- F666：`check_config_coherence` 对 `auditDimensions` 非法形态（非 dict 的标量/列表）**不崩溃、响亮失败**——产出 `G0.cc.malformed_audit_dimensions` FAIL 条目；`g0.py` 调用点 except 子句**不扩大**（类型守卫在 checker 内闭环，禁止裸 except 吞错）
- **验收**：4 向量（F611 整键对象、F631 falsy、F666 标量、F606 float/str floor）全部在写侧被拦截或读侧被 G0 标记；`{"auditDimensions": false}` 使 G0 返回 FAIL 而非 AttributeError

### R2 · 键缺失语义统一（F643）——按 criticality 分裂
- 统一语义：**critical 维度（AUDIT_SAFETY_MATRIX 中 `critical: true`：texture/antiAi/continuity）缺失 = 启用**（两侧一致）；**非 critical genre 维度缺失 = 不激活**（显式 opt-in，维持现状）
- 读侧 G0 维持 `get(dim, True)`（仅对 critical 维度）；`audit_layer.get_active_genre_audits` 对 critical 维度改 `get(dim_key, True)`。爆炸半径核查：critical 三维中仅 `texture` 在 GENRE_ACTIVATION_MATRIX（antiAi/continuity 为 core-circle 固定步、被 `_CORE_CIRCLE_KEYS` 过滤），且两份真实配置（novel-output/xinghuo-ranqiong、test-validation）均显式 `texture: true` → 对现有配置零行为变化、零新增 dispatch
- **验收**：从 auditDimensions 删除 `texture` 后——写侧被 Rule 1（解析新旧合并终值，键消失即终值缺失=启用但被显式移除，视为需 rationale 的禁用企图）拦截；读侧 audit_layer 仍激活 texture 审计（缺失=启用），G0 不误报。测试断言删除 critical 键不会静默停用审计

### R3 · 键形统一（F638）
- 治理检查（Rule 1 与 G0）同时认 camelCase `auditDimensions` 与 snake_case `audit_dimensions`（两形并存时 camelCase 优先、snake_case 仅补充出现的新键）；audit_layer 运行时回退保持不变
- **验收**：`{"audit_dimensions": {"texture": false}}` 在写侧触发 rationale 要求、读侧被 G0 标记

### R4 · 治理层接线（F635）——创建/更新分流
- **创建路径不动**：pipeline-init（cli.py 直写 seed 派生配置）保持 `safe_write`，初始创建无 rationale 语义
- **更新路径接线**：`shenbi-genre-config` TriggerStep（triggers.py，`output_path="genre-config.json"`，category=genre_config_update）产出经 G5 校验后，消费点对 **新旧配置 diff** 跑治理校验（复用 Rule 1/2 逻辑的 `govern_genre_config_change(project_dir, old, new, rationale)`：diff 中被禁用/降低的 critical 项按 Rule 1 处置，rationale 取该 skill decisions.json 的 adjustment 摘要，缺失即 ConfigError）+ 追加 audit trail
- 更新 `config_coherence.py` 模块 docstring 使其与实际路由一致
- **验收**：写 genre-config 更新走治理路径产生 audit trail 条目；禁用 critical 维度无 rationale 时更新被拒

### R5 · 两阶段提交（F614）
- `update_genre_config`（及 R4 的 `govern_genre_config_change`）先对**全部** changes 完成校验，再统一落盘 config + 逐条追加 trail——中途 ConfigError 不留任何 trail 幻影条目
- **验收**：混合有效+无效 change 批次抛 ConfigError 后 `config-change-log.jsonl` 无新增行

## 执行顺序
R1（含 F666 G0 响亮失败）→ R2 → R3 → R4 → R5（R5 依赖 R4 产生生产语义，最后落地）

## 测试与 fixture 计划
- 基线：`tests/fixtures/genre-config-example.json`（真实产物副本，已在库）；bypass 变体（整键覆盖/falsy/标量/snake_case/float floor）在测试内**程序化派生**自该副本（G0.9：不手写 fixture）
- 测试层级：全 T1（unit），治理接线 R4 加 chapter_loop/triggers 消费点单测
