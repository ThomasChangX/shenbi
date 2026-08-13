# D1⑪ skip/xfail 清点结果

## 运行时 skip（`pytest -n auto -m "not last" --no-cov -rs`，2814 passed / 216 skipped）
| 数量 | 位置 | 原因 | 初步处置 |
|---|---|---|---|
| 214 | tests/integration/test_doc_links.py:36 (参数化) | markdown-link-check npm 未安装 | 环境依赖 skip — Z7 判定 keep/其他 |
| 1 | tests/unit/pipeline/test_truth_embed.py:122 | sentence_transformers 已安装；降级路径不可测 | **masking 候选** — dev group 含 st 导致降级路径永远测不到（与 F-D1-01 同根因） |
| 1 | tests/unit/pipeline/test_context_assemble.py:167 | 同上 | 同上 |

## 源码标记（15 处）
- 13× `pytest.skip(` + 2× `@pytest.mark.skipif`（详见 d1-11-skipxfail.txt，Z7 逐条处置）
