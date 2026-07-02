# Gemini CLI — Shenbi Entry Point

This file is the Gemini CLI entry point for the **shenbi** (神笔) novel-writing skill framework.

When the Gemini CLI loads a project that contains this `GEMINI.md`, the agent MUST first load the `using-shenbi` skill from `skills/using-shenbi/SKILL.md` before responding to any user request. The `using-shenbi` skill enforces the **1% Rule**: if there is any chance a shenbi skill applies, check it before responding.

## Tool Mapping

Gemini CLI tools map to shenbi expectations as follows:

| shenbi expects | Gemini CLI tool |
|----------------|-----------------|
| Read files | `read_file` / `Read` |
| Write files | `write_file` / `Write` |
| Edit files | `edit_file` / `Edit` |
| Run shell commands | `run_shell_command` / `Shell` |
| Search the web | `google_web_search` / `WebSearch` |
| Glob file matching | `glob` / `Glob` |
| Grep content search | `search_file_content` / `Grep` |

## P-1.E Layout (2026-06-15)

Framework runtime code lives under `src/shenbi/`. Invoke via entry points:

| Old (pre-P-1.E) | New (post-P-1.E) |
|---|---|
| `python3 tests/scoring.py ...` | `shenbi-score ...` |
| `python3 tests/summarize-round.py ...` | `shenbi-summarize ...` |
| `python3 tests/update-progress.py ...` | `shenbi-progress ...` |
| `python3 tests/phase-runner.py ...` | `shenbi-phase ...` |
| `python3 tests/validate-gate.py ...` | `shenbi-validate ...` |
| `bash tests/dispatch-subagent.sh ...` | `shenbi-dispatch ...` |

Or use `just`:
- `just check` — all CI checks
- `just test` — unit tests
- `just gate G0 <seed>` — gate invocation
- `just dispatch <skill> <type> <round> <prompt>`
- `just pipeline-init <seed>` — initialize novel pipeline
- `just pipeline-status <dir>` — check pipeline status
- `just pipeline-review <dir> <decision>` — submit checkpoint review
- `just pipeline-resume <dir>` — resume pipeline execution

Install: `uv sync --group dev` (PEP 735 dependency groups).

## SessionStart Behavior

The `hooks/hooks.json` (Claude Code) and `hooks/hooks-cursor.json` (Cursor) entry points are platform-specific. For Gemini CLI, the equivalent is:

1. On session start, the agent reads this `GEMINI.md`.
2. The agent then loads `skills/using-shenbi/SKILL.md` and follows its skill-check order before any other action.

## Skill Loading

58 functional skills (shenbi-*) + 1 meta (using-shenbi) = 59 total, listed in `plugins/master.json` (single source; manifests generated via `shenbi-generate-plugins`). For Gemini CLI, treat the `skills` array as the canonical list of available skills. Load them on demand by file path: `skills/<skill-name>/SKILL.md`.

## Environment Variable

To activate the shenbi hook detector on Gemini CLI, set `GEMINI_CLI=1` in the session environment. The `hooks/session-start` script uses this to identify the platform and emit:

```json
{"platform": "gemini-cli", "action": "inject-skill", "skill": "using-shenbi"}
```

## Conventions

- "your human partner" — refers to the author collaborating with the agent
- "truth files" — the novel project's authoritative state files under `truth/`
- "chapter memo" — the 8-section planning document under `plans/chapter-N-plan.md`

For the full skill framework, see `skills/using-shenbi/SKILL.md`.
