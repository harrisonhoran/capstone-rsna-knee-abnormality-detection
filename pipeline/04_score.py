"""Step 4: score label sources against the 58 expert-labelled (gold) studies.

Usage
  python pipeline/04_score.py selfcheck
      Scores the two existing report readers and their average. Expected macro AUC about
      .891 (Claude), .885 (GPT-6.1 Sol), .897 (average). Run this before trusting any new number.
  python pipeline/04_score.py score A.csv [B.csv ...]
      One row of metrics per source.
  python pipeline/04_score.py compare A.csv B.csv
      Paired bootstrap of B minus A (macro AUC, weak-five AUC, mimic-subset AUC, log loss).
  A source can be several repeat files joined with '+', e.g. "outputs/runs/V_onto_r1.csv+outputs/runs/V_onto_r2.csv".
  Repeats are averaged per study and finding before scoring.

Prediction files: one row per StudyInstanceUID, probabilities in either the competition column names
("ACL", ..., "Fracture") or p_<key> columns ("p_acl", ..., "p_fracture").
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
LLM_DIR = PROJECT / "outputs" / "reference"   # earlier two-reader report labels, gold studies, probabilities only
OUT = PROJECT / "outputs" / "scores"

LABELS = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA",
          "PF OA", "Effusion", "Synovitis", "Baker's", "Contusion", "Fracture"]
KEYS = ["acl", "mcl", "medial_meniscus", "lateral_meniscus", "medial_oa", "lateral_oa",
        "pf_oa", "effusion", "synovitis", "bakers", "contusion", "fracture"]
WEAK_FIVE = ["PF OA", "Effusion", "Synovitis", "Contusion", "Lateral OA"]       # reports under-call these
MIMIC_SUBSET = ["ACL", "Medial Meniscus", "Lateral Meniscus", "Contusion", "Fracture"]  # fixed in advance
N_BOOT, SEED, EPS = 10_000, 0, 1e-4


def load_gold():
    t = pd.read_csv(RAW / "train.csv")
    g = t.loc[t[LABELS].notna().all(axis=1)].set_index("StudyInstanceUID")[LABELS].astype(int)
    assert len(g) == 58, f"expected 58 gold studies, found {len(g)}"
    return g


def load_source(spec, gold):
    """Read one source (repeat files joined with '+'), average repeats, align to the gold studies."""
    frames = []
    for path in spec.split("+"):
        df = pd.read_csv(path).set_index("StudyInstanceUID")
        if all(f"p_{k}" in df.columns for k in KEYS):
            df = df[[f"p_{k}" for k in KEYS]].set_axis(LABELS, axis=1)
        frames.append(df[LABELS].astype(float))
    p = sum(frames) / len(frames)
    p = p.reindex(gold.index)
    missing = int(p.isna().any(axis=1).sum())
    if missing:
        print(f"  warning: {spec}: {missing} gold studies missing; filled with 0.5")
        p = p.fillna(0.5)
    return p.clip(0, 1)


def auc(y, s):
    """ROC AUC via the rank-sum (Mann-Whitney) formula; ties get average ranks. Same value as
    sklearn's roc_auc_score, but fast enough for 10,000 bootstrap resamples."""
    r = rankdata(s)
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def aucs(p, gold, idx=None):
    """AUC per finding on the given study positions (None = all). Findings with one class are skipped."""
    out = {}
    for c in LABELS:
        y = gold[c].values if idx is None else gold[c].values[idx]
        s = p[c].values if idx is None else p[c].values[idx]
        if 0 < y.sum() < len(y):
            out[c] = auc(y, s)
    return out


def short(spec):
    """Readable name for a source: file names without folders or extensions, repeats joined by '+'."""
    return "+".join(Path(p).stem for p in spec.split("+"))


def summary(p, gold, idx=None):
    a = aucs(p, gold, idx)
    y = gold.values if idx is None else gold.values[idx]
    s = (p.values if idx is None else p.values[idx]).clip(EPS, 1 - EPS)
    return {
        "macro_auc": np.mean(list(a.values())),
        "weak5_auc": np.mean([a[c] for c in WEAK_FIVE if c in a]),
        "mimic_auc": np.mean([a[c] for c in MIMIC_SUBSET if c in a]),
        "log_loss": float(-np.mean(y * np.log(s) + (1 - y) * np.log(1 - s))),
        "confident_errors": int(((s >= 0.9) & (y == 0)).sum() + ((s <= 0.1) & (y == 1)).sum()),
        **{f"auc_{c}": v for c, v in a.items()},
    }


def score(specs):
    gold = load_gold()
    rows = []
    for spec in specs:
        m = summary(load_source(spec, gold), gold)
        rows.append({"source": short(spec), **m})
    df = pd.DataFrame(rows)
    show = ["source", "macro_auc", "weak5_auc", "mimic_auc", "log_loss", "confident_errors"]
    print(df[show].round(4).to_string(index=False))
    print("\nAUC per finding:")
    print(df.set_index("source")[[f"auc_{c}" for c in LABELS]].T.round(3).to_string())
    return df


def compare(spec_a, spec_b):
    """Paired bootstrap over studies: the same resampled studies score both sources."""
    gold = load_gold()
    pa, pb = load_source(spec_a, gold), load_source(spec_b, gold)
    base_a, base_b = summary(pa, gold), summary(pb, gold)
    rng = np.random.default_rng(SEED)
    keys = ["macro_auc", "weak5_auc", "mimic_auc", "log_loss"]
    deltas = {k: [] for k in keys}
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(gold), len(gold))
        sa, sb = summary(pa, gold, idx), summary(pb, gold, idx)
        for k in keys:
            deltas[k].append(sb[k] - sa[k])
    rows = []
    for k in keys:
        d = np.array(deltas[k])
        better = (d < 0).mean() if k == "log_loss" else (d > 0).mean()     # lower log loss is better
        rows.append({"metric": k, "A": base_a[k], "B": base_b[k], "delta_B_minus_A": base_b[k] - base_a[k],
                     "ci_low": np.percentile(d, 2.5), "ci_high": np.percentile(d, 97.5), "P(B better)": better})
    df = pd.DataFrame(rows)
    print(f"A = {short(spec_a)}\nB = {short(spec_b)}\n")
    print(df.round(4).to_string(index=False))
    print(f"\nConfident errors: A {base_a['confident_errors']}, B {base_b['confident_errors']}")
    return df


def selfcheck():
    claude, openai = LLM_DIR / "llm_claude_full.csv", LLM_DIR / "llm_openai_full.csv"
    df = score([str(claude), str(openai), f"{claude}+{openai}"])
    expected = [0.891, 0.885, 0.897]
    print("\nExpected macro AUC:", expected)
    ok = all(abs(a - b) < 0.0015 for a, b in zip(df["macro_auc"], expected))
    print("SELF-CHECK", "PASSED" if ok else "FAILED: the scorer does not reproduce the known numbers")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "selfcheck":
        selfcheck()
    elif cmd == "score" and args:
        score(args).to_csv(OUT / "score_latest.csv", index=False)
        print("Saved", OUT / "score_latest.csv")
    elif cmd == "compare" and len(args) == 2:
        compare(*args).to_csv(OUT / "compare_latest.csv", index=False)
        print("Saved", OUT / "compare_latest.csv")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
