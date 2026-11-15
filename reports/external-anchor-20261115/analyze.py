"""External-anchor panel analysis (spec #115 T3 prereg; r2 stratification).

Reads ratings-rater{1,2,3}.csv from this directory, joins key.csv, pulls the
resonance overall score from the vol1 trend, and reports:
  - ICC(2,k) on the 12 x 3 rater-standardized panel matrix
  - Spearman rho(panel mean, resonance overall) + 5000-draw chapter bootstrap CI
  - per-band descriptives (low n=2 / mid n=5 / high n=5, unweighted)
  - invalidation checks (rating range, missing cells, rater count)
"""

# ruff: noqa: PLR2004, T201 — standalone analysis script (1-7 Likert bounds, stdout report)

from __future__ import annotations

import csv
import random
import re
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
TREND = Path("novel-xinghuo-vol1/truth/resonance_trend.md")
ITEMS = ["q1_continue", "q2_emotion", "q3_memory", "q4_immersion", "q5_recommend"]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into a list of row dicts."""
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def resonance_scores() -> dict[int, int]:
    """Parse overall scores from the vol1 resonance trend table."""
    out: dict[int, int] = {}
    for line in TREND.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|", line)
        if m:
            out[int(m.group(1))] = int(m.group(2))
    return out


def icc_2k(mat: np.ndarray) -> float:
    """ICC(2,k): two-way random effects, absolute agreement, average raters."""
    n, k = mat.shape
    grand = mat.mean()
    row_means = mat.mean(axis=1)
    col_means = mat.mean(axis=0)
    ss_total = float(((mat - grand) ** 2).sum())
    ss_rows = float(k * ((row_means - grand) ** 2).sum())
    ss_cols = float(n * ((col_means - grand) ** 2).sum())
    ss_err = ss_total - ss_rows - ss_cols
    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_err = ss_err / ((n - 1) * (k - 1))
    denom = ms_rows + (ms_cols - ms_err) / n
    return (ms_rows - ms_err) / denom if denom else float("nan")


def bootstrap_rho(x: np.ndarray, y: np.ndarray, draws: int = 5000) -> tuple[float, float]:
    """Percentile bootstrap CI for Spearman rho (chapter resampling)."""
    rng = random.Random(20261115)
    n = len(x)
    vals: list[float] = []
    for _ in range(draws):
        idx = [rng.randrange(n) for _ in range(n)]
        xs, ys = x[idx], y[idx]
        if np.std(xs) == 0 or np.std(ys) == 0:
            continue
        r = stats.spearmanr(xs, ys).statistic
        if not np.isnan(r):
            vals.append(float(r))
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals)) - 1]
    return lo, hi


def main() -> int:  # noqa: PLR0912
    """Run the panel analysis and write analysis.md."""
    key = {r["item_id"]: int(r["chapter"]) for r in read_csv(HERE / "key.csv")}
    raters: dict[str, dict[str, dict[str, float]]] = {}
    for n in (1, 2, 3):
        p = HERE / f"ratings-rater{n}.csv"
        if not p.exists():
            raise SystemExit(f"missing {p}")
        rows = read_csv(p)
        table: dict[str, dict[str, float]] = {}
        for r in rows:
            item = r["item_id"]
            if not item:
                continue
            try:
                vals = {q: float(r[q]) for q in ITEMS}
            except (KeyError, ValueError) as exc:
                raise SystemExit(f"bad rating row in {p}: {r} ({exc})") from exc
            for _q, v in vals.items():
                if not 1 <= v <= 7:
                    raise SystemExit(f"rating out of 1-7 in {p}: {r}")
            table[item] = vals
        raters[f"r{n}"] = table
    items = sorted(key)
    missing = [i for i in items if any(i not in r for r in raters.values())]
    if missing:
        raise SystemExit(f"missing ratings for: {missing}")

    # prereg panel score: z-score EACH item within each rater across chapters,
    # average the 5 item z-scores per chapter, then average across raters.
    zmat = np.zeros((len(items), len(raters)))
    for j, r in enumerate(raters.values()):
        item_mat = np.array([[r[i][q] for q in ITEMS] for i in items], dtype=float)
        sd = item_mat.std(axis=0, ddof=0)
        sd[sd == 0] = 1.0
        z = (item_mat - item_mat.mean(axis=0)) / sd
        zmat[:, j] = z.mean(axis=1)
    panel_mean = zmat.mean(axis=1)
    res = resonance_scores()
    y = np.array([res[key[i]] for i in items], dtype=float)
    x = panel_mean
    rho = float(stats.spearmanr(x, y).statistic)
    lo, hi = bootstrap_rho(x, y)
    icc = icc_2k(zmat)

    bands: dict[str, list[str]] = {"low": [], "mid": [], "high": []}
    for i in items:
        v = res[key[i]]
        bands["low" if v <= 76 else "mid" if v <= 80 else "high"].append(i)

    out = [
        "# External anchor report",
        "",
        f"- chapters: {len(items)}; raters: {len(raters)}",
        f"- ICC(2,k): **{icc:.3f}** (panel invalid if < 0.5)",
        f"- Spearman rho(panel, resonance overall): **{rho:.3f}** "
        f"(bootstrap 95% CI {lo:.3f} .. {hi:.3f})",
        "",
        "| band | n | chapters | mean resonance | mean panel z |",
        "|---|---:|---|---:|---:|",
    ]
    for band, ids in bands.items():
        if not ids:
            continue
        rv = np.mean([res[key[i]] for i in ids])
        pv = np.mean([panel_mean[items.index(i)] for i in ids])
        out.append(
            f"| {band} | {len(ids)} | {', '.join(str(key[i]) for i in ids)} | {rv:.1f} | {pv:.2f} |"
        )
    out += [
        "",
        "## per-chapter",
        "",
        "| item | chapter | resonance | panel z |",
        "|---|---:|---:|---:|",
    ]
    for i in items:
        out.append(f"| {i} | {key[i]} | {res[key[i]]} | {panel_mean[items.index(i)]:+.2f} |")
    (HERE / "analysis.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
