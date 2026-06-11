# Expected Output: shenbi-location-builder Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Capital-to-port travel time is "three days by horse" in capital.md but "a half-day ride" in port-city.md — spatial contradiction | error | `world/locations/capital.md`: travel section; `world/locations/port-city.md`: travel section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the frontier fort description (it is spatially consistent)
- Issues with atmosphere quality (all locations have proper sensory signatures)
- Issues with prose format (all locations use narrative prose)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of both contradicting travel time statements
- Severity classification for each issue
