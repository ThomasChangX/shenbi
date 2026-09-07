# Logging

Shenbi uses `structlog` for structured logging. All framework modules import `from shenbi.logging import get_logger`.

See [API → Logging](../api/logging.md) for the API reference.

## 输出通道裁决（spec #50 / C36）

框架代码的三类输出通道，各有唯一合法形态：

| 通道 | 合法形态 | 执法 |
|---|---|---|
| 日志 | `structlog`（`shenbi.logging.get_logger`，写 stderr） | 惯例 |
| 人面文本（CLI 状态/错误消息） | `shenbi.cli_utils.echo(msg, *, err=False)`（`err=True` 写 stderr；write+flush，BrokenPipe 干净退出） | ruff `T20` |
| 机器可读 stdout（JSON 契约，供 shell/下游 CLIs/skills 层 `python -m shenbi.skill_utils.*` 消费） | `shenbi.cli_utils.emit_json(obj)` 或直接 `sys.stdout.write` | ruff `T20` |

- `print()` 在 `src/shenbi/` **零豁免**（ruff `T20`，2026-09-07 起）。
- 框架外豁免：`tools/**`、`scripts/**`（CLI 脚本）与 `tests/**`（审计记录型输出）经 `[tool.ruff.lint.per-file-ignores]` 豁免 `T201`。
- `echo` 继承流编码（与 `emit_json` 同性质）：非 UTF-8 locale 下中文同样抛 `UnicodeEncodeError`，接受该一致性。
