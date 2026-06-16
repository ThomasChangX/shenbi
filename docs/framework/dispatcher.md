# Dispatcher

The dispatcher runs skills in pipeline order, passing truth-file state between them.

```bash
uv run shenbi-dispatch <skill> <test_type> <round_dir> [prompt]
```

See `src/shenbi/dispatcher/` for implementation.
