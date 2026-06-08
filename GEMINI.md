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

## SessionStart Behavior

The `hooks/hooks.json` (Claude Code) and `hooks/hooks-cursor.json` (Cursor) entry points are platform-specific. For Gemini CLI, the equivalent is:

1. On session start, the agent reads this `GEMINI.md`.
2. The agent then loads `skills/using-shenbi/SKILL.md` and follows its skill-check order before any other action.

## Skill Loading

All 59 skills are listed in `.claude-plugin/plugin.json`. For Gemini CLI, treat the `skills` array as the canonical list of available skills. Load them on demand by file path: `skills/<skill-name>/SKILL.md`.

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
