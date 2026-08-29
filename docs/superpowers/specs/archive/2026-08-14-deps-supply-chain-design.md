> **Date:** 2026-08-14 | **Status:** Rejected (2026-08-30 · 全部可执行面被活跃 spec 认领：D1-01 → #41 C27 supersede，Z11-01 → #19/#20；执行本 spec 即重复实施) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** pyproject.toml/uv.lock | **核心洞察:** dev group 含 sentence-transformers 使降级路径测试永远 skip（masking）

# 依赖与供应链

## R1 · dev group 含 sentence-transformers（D1-01, P1）
- 证据：pyproject.toml:17 注释声明"移至 optional 避免 torch"，:47 dev group 显式含 sentence-transformers → dev 安装拉 torch/CUDA；2 个降级路径测试（test_truth_embed.py:122、test_context_assemble.py:167）永远 skip（"sentence_transformers installed; degradation path not testable"）
- 背景：embeddings-smoke.yml 说明 dev 组含 st 是有意（CI 守 import 兼容）——但降级路径测试失去意义
- 修复选项：(a) 降级路径测试用 monkeypatch 模拟未安装；(b) 单独 group 装 st 仅 embeddings-smoke 用；**验收：降级路径测试真实执行**

## R2 · Z11-01 decisions.json 无效产物（P1，转 Z11 区）
- novel-output 44/89 最终 decisions.json 无效（Extra data/空文件）；`_validate_json_output` 修复引入（dd1fc62）后仍有产物 → 恢复逻辑有洞或旁路写路径；Z11 深查根因后定 spec
