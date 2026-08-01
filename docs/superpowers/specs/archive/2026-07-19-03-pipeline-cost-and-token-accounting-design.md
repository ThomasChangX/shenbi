# Spec 16: Pipeline Cost and Token Accounting Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Medium
> **Source:** SHOUT-OUT — discovered during cross-spec review of Specs 1-11
> **Relationship:** Interacts with Spec 6 (token waste reduction), Spec 7 (observability), Spec 8 (context engineering)

---

## 1. Executive Summary

Specs 6, 7, and 8 all reference token waste and cost optimization, but NONE of the 11 existing specs establish a comprehensive cost and token accounting system. During the cross-spec review, the following gaps were identified:

1. **No `response.usage` capture:** Spec 7's verification confirmed that `_dispatch_via_api` (`dispatch_helper.py:432-441`) does NOT read `response.usage` — the API returns token counts (prompt_tokens, completion_tokens, total_tokens) but they are silently discarded.

2. **No cost estimation:** With no token counts captured, there is no way to estimate API costs per chapter, per skill, or per pipeline run. The 56-chapter production run cost is unknown.

3. **No token budget enforcement:** Spec 8 proposes priority-driven budget allocation, but there is no mechanism to measure whether the budget is actually respected. If a skill's prompt exceeds its allocated budget, the overflow is silently sent to the API (and billed).

4. **No cost-per-quality metric:** The framework scores chapters 0-100 (G3), but without cost data, there is no way to compute "cost per quality point" — a critical metric for optimizing the cost/quality tradeoff.

5. **No historical cost trend:** Without per-chapter token tracking, there is no way to detect cost drift (e.g., later chapters costing more due to context bloat).

---

## 2. Root Cause Analysis

### 2.1 Missing Usage Capture

The API dispatch path (`_dispatch_via_api`) calls `client.chat.completions.create(...)` and reads `response.choices[0].message.content` but does NOT read `response.usage`. The `response.usage` object contains:
- `prompt_tokens`: input tokens (what we sent)
- `completion_tokens`: output tokens (what the LLM generated)
- `total_tokens`: sum

This data is FREE — the API returns it with every call — but it's discarded.

### 2.2 No Cost Aggregation

Even if individual call usage were captured, there is no aggregation layer:
- No per-skill token totals
- No per-chapter token totals
- No per-pipeline-run token totals
- No cost estimation (tokens × price-per-token)

### 2.3 Budget Blindness

Spec 8's priority-driven budget allocates token budgets per file category. But without measuring actual token usage, there's no feedback loop:
- If a file exceeds its budget, the truncation kicks in (Spec 8 Fix 7), but the overflow is not logged
- If the total prompt exceeds the model's context window, the API returns an error (expensive failure)
- No pre-flight check estimates whether the assembled prompt will fit

---

## 3. Fix Strategy

### 3.1 Capture response.usage in API Dispatch

```python
# In dispatch_helper.py _dispatch_via_api, after response = client.chat.completions.create(...)
response = client.chat.completions.create(...)
content = response.choices[0].message.content

# NEW: Capture usage
if hasattr(response, 'usage') and response.usage:
    usage = {
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens,
    }
    log.info("llm_token_usage",
             skill=skill, chapter=chapter,
             **usage)
    _record_token_usage(project_dir, skill, chapter, usage)
```

### 3.2 Token Usage Ledger

Create a persistent token usage ledger:

```python
# src/shenbi/cost/ledger.py (new)

@dataclass
class TokenUsageRecord:
    timestamp: str
    skill: str
    chapter: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

class TokenLedger:
    """Persistent token usage ledger."""

    def __init__(self, project_dir: Path):
        self.ledger_path = project_dir / "cost" / "token-ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, skill: str, chapter: int, usage: dict):
        record = TokenUsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            skill=skill,
            chapter=chapter,
            prompt_tokens=usage['prompt_tokens'],
            completion_tokens=usage['completion_tokens'],
            total_tokens=usage['total_tokens'],
            estimated_cost_usd=_estimate_cost(usage),
        )
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(asdict(record)) + '\n')

    def summarize(self) -> dict:
        """Aggregate token usage by skill, chapter, and total."""
        ...
```

### 3.3 Cost Estimation

```python
# src/shenbi/cost/pricing.py (new)

# Pricing as of 2026-07 (configurable for model changes)
PRICING = {
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    # Add other models as needed
}

def estimate_cost(usage: dict, model: str = "gpt-4o") -> float:
    rates = PRICING.get(model, PRICING["gpt-4o"])
    input_cost = usage['prompt_tokens'] * rates['input']
    output_cost = usage['completion_tokens'] * rates['output']
    return input_cost + output_cost
```

### 3.4 Pre-Flight Context Budget Check

Before dispatching any skill, estimate the prompt token count and warn if it exceeds budget:

```python
def _estimate_prompt_tokens(prompt: str) -> int:
    """Rough estimate: 1 token ≈ 4 chars for English, ≈ 1.5 chars for CJK."""
    cjk_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    other_chars = len(prompt) - cjk_chars
    return int(cjk_chars / 1.5 + other_chars / 4)

# Before dispatch:
estimated = _estimate_prompt_tokens(full_prompt)
if estimated > model_context_limit * 0.8:
    log.warning("prompt_approaching_context_limit",
                estimated=estimated, limit=model_context_limit)
```

### 3.5 Cost Dashboard CLI

```bash
uv run shenbi-cost report <project_dir>
# Output:
# Total cost: $X.XX
# Per-skill breakdown:
#   shenbi-chapter-drafting: $X.XX (Y% of total)
#   shenbi-review-resonance: $X.XX (Y% of total)
#   ...
# Per-chapter average: $X.XX
# Cost per quality point: $X.XX (total_cost / average_g3_score)
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/dispatch_helper.py` (`_dispatch_via_api`) | Capture `response.usage` | Record token usage from API |
| `src/shenbi/cost/ledger.py` (new) | Token usage ledger | Persistent per-call records |
| `src/shenbi/cost/pricing.py` (new) | Cost estimation | Convert tokens to USD |
| `src/shenbi/cost/report.py` (new) | Cost dashboard CLI | Summarize costs per skill/chapter |
| `src/shenbi/pipeline/dispatch_helper.py` | Add pre-flight prompt token estimate | Warn before context overflow |

---

## 5. Verification Criteria

1. **Every API dispatch** records `prompt_tokens`, `completion_tokens`, `total_tokens` to the ledger
2. **Cost report** aggregates per-skill, per-chapter, and total cost
3. **Pre-flight check** warns when estimated prompt > 80% of context limit
4. **Cost-per-quality** metric computed (total_cost / average_g3_score)
5. **Historical trend** visible (cost per chapter over the full run)
6. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 16 (this spec, Pipeline Cost and Token Accounting)
    |
    +---> Enhances: Spec 6 (token waste is now measurable)
    +---> Enhances: Spec 7 (observability includes cost)
    +---> Enhances: Spec 8 (budget enforcement is now verifiable)

Prerequisites: None (standalone infrastructure build)
```
