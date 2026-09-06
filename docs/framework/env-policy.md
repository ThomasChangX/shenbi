# 子进程环境白名单（env policy）

> spec #45 R4（T1207/F1161）。实现：`src/shenbi/env_policy.py`（`build_child_env` / `redact`）。

dispatch 派生的子进程不再继承全量 `os.environ`（原行为使 `SHENBI_LLM_API_KEY` 等密钥可达 workspace-write codex 子进程）。两个派发面各有一个白名单：

## codex 面（`codex exec` CLI）

精确名单：`PATH` `HOME` `LANG` `LC_ALL` `LC_CTYPE` `TERM` `TMPDIR` `CODEX_HOME` `OPENAI_BASE_URL` `OPENAI_API_BASE` `HTTPS_PROXY` `HTTP_PROXY` `NO_PROXY`（及小写代理变体）

前缀：`SHENBI_*`

## uv 面（`uv run shenbi-dispatch` / `shenbi-score` 等）

在 codex 面之上追加：精确 `VIRTUAL_ENV` `PYTHONDONTWRITEBYTECODE`；前缀 `UV_*` `PYTHON*`

## 密钥排除与逃生阀

- 变量名含 `KEY` / `TOKEN` / `SECRET` / `PASSWORD`（不区分大小写）一律不透传——含 `SHENBI_LLM_API_KEY`、`OPENAI_API_KEY`
- 运维显式追加通道：`SHENBI_ENV_PASSTHROUGH="VAR1:VAR2"`（冒号分隔）——被点名变量即使密钥命名也透传（点名即意图），并记 INFO 日志 `env_passthrough_explicit` 供审计
- 框架内部 gate subprocess（G3/G4 CLI 直调）不属本策略范围（框架内部面，密钥可达性低）

## 日志脱敏（F1161）

`shenbi.logging.structlog_redact` processor 在渲染前对全部 string 事件值过 `env_policy.redact`：

- OAuth URL 一次性参数：`state=…` `nonce=…` `code_challenge=…` `code=…` → `参数=***`
- API key：`sk-…` → `sk-***`
- Bearer：`Bearer …` → `Bearer ***`
