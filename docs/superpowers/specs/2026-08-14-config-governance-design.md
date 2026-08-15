> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** config/ + gates/g0_config_coherence.py + audit_layer.py | **核心洞察:** 关键审计维度禁用治理存在 4 个独立绕过向量 + 治理层零接线

# 配置治理绕过

## 向量清单（同一修复批次）
- **F606（P2）**：floor 只认 int，float/str 绕过（59.5 通过）
- **F611（P2）**：规则 1 只拦 `auditDimensions.<dim>:false`，整键对象覆盖绕过
- **F631（P2）**：`is False` 被 falsy 值 0/null/"" 绕过（写侧与读侧同时失明）
- **F643（P2）**：键缺失语义矛盾（G0 视缺失为启用、audit_layer 视缺失为禁用）
- **F666（P2）**：整键标量（`{"auditDimensions": false}`）→ g0 AttributeError 崩溃 + 审计静默停用
- **F638（P2）**：snake_case 配置绕过 camelCase 检查
- **F635（P2）**：update_genre_config 治理层零生产调用（genre-config 由 skill 直写）
- **F614（P2）**：中途 ConfigError 留 audit-trail 幻影条目
- **F606/F611/F631/F643/F666 统一修复**：规则 1 覆盖整键与任意前缀 + falsy 判定 + 键缺失语义统一 + 类型守卫；**验收：4 向量全部拦截**
- **F635 修复**：skill 直写路径接入治理层；**验收：写 genre-config 产生 audit trail**
