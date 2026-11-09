"""Step 6: the pre-registered analysis of the 2x2 (PREREGISTRATION.md, sections 8 and 9).

Usage
  python pipeline/06_analyze.py                      # reads outputs/runs/full_high
  python pipeline/06_analyze.py --run full_high --repeats 1 2

Outputs (outputs/analysis/<run>/)
  cells.csv          every cell scored: repeats averaged (primary) and each repeat alone
  effects.csv        H1, H2, H3 and the exploratory image effect, with 95% intervals and decisions
  per_finding.csv    ontology effect per finding, with and without images
  repeat_noise.csv   run-to-run agreement between repeat 1 and repeat 2
  summary.md         the same results as readable text, for the thesis
"""
import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("score", PROJECT / "pipeline" / "04_score.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)                      # reuse the validated scorer (load_gold, load_source, summary)

CELLS = ["T_plain", "T_onto", "V_plain", "V_onto"]
METRICS = ["macro_auc", "weak5_auc", "mimic_auc", "log_loss"]
REFERENCE = (S.LLM_DIR / "llm_claude_full.csv", S.LLM_DIR / "llm_openai_full.csv")


def as_table(df):
    """Markdown table if the optional 'tabulate' package is installed, plain text otherwise."""
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```\n" + df.to_string(index=False) + "\n```"


def effect_values(m):
    """The four pre-registered contrasts from one set of cell scores m[cell][metric]."""
    out = {}
    for k in METRICS:
        h1 = m["T_onto"][k] - m["T_plain"][k]
        h2 = m["V_onto"][k] - m["V_plain"][k]
        out[("H1 ontology, report only (T_onto - T_plain)", k)] = h1
        out[("H2 ontology, with images (V_onto - V_plain)", k)] = h2
        out[("H3 interaction (H2 - H1)", k)] = h2 - h1
        out[("Exploratory: images, no ontology (V_plain - T_plain)", k)] = m["V_plain"][k] - m["T_plain"][k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="full_high")
    ap.add_argument("--repeats", nargs="+", type=int, default=[1, 2])
    args = ap.parse_args()

    run_dir = PROJECT / "outputs" / "runs" / args.run
    out_dir = PROJECT / "outputs" / "analysis" / args.run
    out_dir.mkdir(parents=True, exist_ok=True)
    gold = S.load_gold()

    # Cell scores: repeats averaged (primary), and each repeat alone.
    spec = {c: "+".join(str(run_dir / f"{c}_r{r}.csv") for r in args.repeats) for c in CELLS}
    preds = {c: S.load_source(spec[c], gold) for c in CELLS}
    rows = []
    for c in CELLS:
        rows.append({"cell": c, "repeats": "averaged", **S.summary(preds[c], gold)})
        for r in args.repeats:
            rows.append({"cell": c, "repeats": f"r{r}",
                         **S.summary(S.load_source(str(run_dir / f"{c}_r{r}.csv"), gold), gold)})
    ref = S.load_source(f"{REFERENCE[0]}+{REFERENCE[1]}", gold)
    rows.append({"cell": "reference: earlier two-reader report labels", "repeats": "-", **S.summary(ref, gold)})
    cells = pd.DataFrame(rows)
    cells.to_csv(out_dir / "cells.csv", index=False)

    # Paired bootstrap: every resample scores all four cells on the same studies.
    base = {c: S.summary(preds[c], gold) for c in CELLS}
    point = effect_values(base)
    rng = np.random.default_rng(S.SEED)
    draws = {key: [] for key in point}
    for _ in range(S.N_BOOT):
        idx = rng.integers(0, len(gold), len(gold))
        m = {c: S.summary(preds[c], gold, idx) for c in CELLS}
        for key, v in effect_values(m).items():
            draws[key].append(v)
    eff = []
    for (name, metric), v in point.items():
        d = np.array(draws[(name, metric)])
        lo, hi = np.percentile(d, [2.5, 97.5])
        if metric == "log_loss":                     # lower is better: an improvement is a negative change
            shown, p_better = hi < 0, (d < 0).mean()
        else:
            shown, p_better = lo > 0, (d > 0).mean()
        eff.append({"effect": name, "metric": metric, "delta": v, "ci_low": lo, "ci_high": hi,
                    "P(improvement)": p_better,
                    "decision": "shown" if shown else "no proven advantage"})
    effects = pd.DataFrame(eff)
    effects.to_csv(out_dir / "effects.csv", index=False)

    # Ontology effect per finding (descriptive; per-finding AUCs rest on 9-35 positives).
    pf = []
    for lab in S.LABELS:
        a = {c: base[c].get(f"auc_{lab}", np.nan) for c in CELLS}
        pf.append({"finding": lab, "positives": int(gold[lab].sum()), **{f"auc_{c}": a[c] for c in CELLS},
                   "onto_effect_report_only": a["T_onto"] - a["T_plain"],
                   "onto_effect_with_images": a["V_onto"] - a["V_plain"],
                   "mimic_subset": lab in S.MIMIC_SUBSET, "weak_five": lab in S.WEAK_FIVE})
    per_finding = pd.DataFrame(pf)
    per_finding.to_csv(out_dir / "per_finding.csv", index=False)

    # Run-to-run noise between the first two repeats.
    noise = []
    if len(args.repeats) >= 2:
        r1, r2 = args.repeats[:2]
        for c in CELLS:
            a = S.load_source(str(run_dir / f"{c}_r{r1}.csv"), gold)
            b = S.load_source(str(run_dir / f"{c}_r{r2}.csv"), gold)
            flips = ((a.values >= 0.5) != (b.values >= 0.5))
            noise.append({"cell": c, "cells_compared": flips.size, "side_of_0.5_changed": int(flips.sum()),
                          "share_changed": flips.mean(), "mean_abs_prob_diff": np.abs(a.values - b.values).mean()})
    noise = pd.DataFrame(noise)
    noise.to_csv(out_dir / "repeat_noise.csv", index=False)

    # Readable summary.
    show = ["cell", "repeats", "macro_auc", "weak5_auc", "mimic_auc", "log_loss", "confident_errors"]
    lines = [f"# Ontology ablation results ({args.run}, repeats {args.repeats})", "",
             "## Cell scores", "", cells[show].round(4).pipe(as_table), "",
             "## Pre-registered effects (paired bootstrap, 10,000 resamples, 95% intervals)", "",
             effects.round(4).pipe(as_table), "",
             "## Ontology effect per finding (descriptive)", "",
             per_finding.round(3).pipe(as_table), ""]
    if len(noise):
        lines += ["## Run-to-run noise (repeat 1 vs repeat 2)", "", noise.round(4).pipe(as_table), ""]
    (out_dir / "summary.md").write_text("\n".join(lines))

    print(cells[show].round(4).to_string(index=False))
    print()
    print(effects[effects.metric == "macro_auc"].round(4).to_string(index=False))
    print("\nSaved", out_dir)


if __name__ == "__main__":
    main()
