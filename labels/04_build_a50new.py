"""a50-new training labels = 0.5 * report part + 0.5 * outsider image OOF (same recipe as a50 / a50r).
Report part:
  extracted rows : average of the two LLM readers (Claude + OpenAI), Effusion and Synovitis recalibrated by grade
                   (rates measured on the 58 gold studies); v3.1 where an LLM row is missing
  silver rows    : Harry's hand labels (silver-1 60, silver-2 159)
  gold rows      : gold (not blended)
Unlabeled rows (no report) stay NaN, exactly as in a50.
Usage (from the repo root): python labels/04_build_a50new.py [pilot|full]
Inputs in data/labels/: train_processed_v3_1.csv, outsider_oof.csv, silver1_final_labels.csv, silver2_hand_labels.csv,
  rsna_llm_labels/llm_{claude,openai}_<stage>.csv (from labels/03_dual_llm_readers.ipynb).
Output: data/labels/train_labels_a50new.csv (full) or train_labels_a50new_pilot.csv"""
import sys
from pathlib import Path
import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score

STAGE = sys.argv[1] if len(sys.argv) > 1 else "full"
D = Path("data/labels")
LLM_DIR = D / "rsna_llm_labels"
T = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA", "PF OA", "Effusion",
     "Synovitis", "Baker's", "Contusion", "Fracture"]
K = ["acl", "mcl", "medial_meniscus", "lateral_meniscus", "medial_oa", "lateral_oa", "pf_oa", "effusion",
     "synovitis", "bakers", "contusion", "fracture"]
SMOOTH = 6          # pseudo-count pulling a group's measured rate toward the readers' own mean

v = pd.read_csv(D / "train_processed_v3_1.csv").set_index("StudyInstanceUID")
lt = v.label_type
outsider = pd.read_csv(D / "outsider_oof.csv").set_index("StudyInstanceUID")[T]
s1 = pd.read_csv(D / "silver1_final_labels.csv").set_index("StudyInstanceUID")[T]
s2 = pd.read_csv(D / "silver2_hand_labels.csv").set_index("StudyInstanceUID")[T]
readers = {m: pd.read_csv(LLM_DIR / f"llm_{m}_{STAGE}.csv").set_index("StudyInstanceUID") for m in ("claude", "openai")}

# ---- truth for calibration: GOLD ONLY. The silver hand labels are read from reports and disagree with the image
# readers exactly here (small effusion: gold 58% positive, silver ~20%), so they cannot calibrate toward the image labels.
truth = v.loc[lt == "gold", T]

def eff_bucket(g):
    return {"none": "none/trace", "trace_physiologic": "none/trace", "small_mild": "small",
            "moderate": "mod/large", "large": "mod/large"}.get(g, "unsized")

def groups(d, label):
    if label == "Effusion":
        return d["g_effusion_size"].fillna("not_mentioned")
    syn = d["g_synovitis_state"].fillna("not_mentioned").replace({"mentioned_mild": "mentioned",
                                                                   "mentioned_moderate_severe": "mentioned"})
    return np.where(syn == "mentioned", "mentioned", "silent | eff " + d["g_effusion_size"].map(eff_bucket))

def recalibrate(d, label, key, report):
    """Shift each grade group so its mean matches the gold+silver positive rate; keeps the order inside a group."""
    p = d[f"p_{key}"].astype(float)
    grp = pd.Series(groups(d, label), index=d.index)
    fit = d.index.intersection(truth.index)
    rows, new = [], p.copy()
    for g in sorted(grp.unique()):
        members = grp.index[grp == g]
        f = members.intersection(fit)
        mean_p = p.loc[members].mean()
        pos = (truth.loc[f, label] > 0.5).sum()
        rate = (pos + SMOOTH * mean_p) / (len(f) + SMOOTH)
        new.loc[members] = (p.loc[members] + rate - p.loc[f].mean() if len(f) else p.loc[members])
        rows.append({"group": g, "n all": len(members), "n truth": len(f), "truth pos": int(pos),
                     "reader mean p (truth rows)": round(p.loc[f].mean(), 3) if len(f) else np.nan,
                     "target rate": round(rate, 3)})
    report.append((label, pd.DataFrame(rows)))
    return new.clip(0.01, 0.99)

report, llm = [], {}
for m, d in readers.items():
    P = d[[f"p_{k}" for k in K]].set_axis(T, axis=1).astype(float)
    for label, key in (("Effusion", "effusion"), ("Synovitis", "synovitis")):
        rep = []
        P[label] = recalibrate(d, label, key, rep)
        report += [(f"{m}: {lab}", tab) for lab, tab in rep]
    single = d["single_knee"].astype(str).str.lower().isin(["true", "1"])
    llm[m] = P[single]                       # not-a-single-knee reports: fall back to v3.1
ids = llm["claude"].index.union(llm["openai"].index)
avg = pd.concat([llm["claude"].reindex(ids), llm["openai"].reindex(ids)]).groupby(level=0).mean()

# ---- assemble ----
ext = lt[lt == "extracted"].index
lab = lt[lt.isin(["extracted", "silver"])].index
rep = v[T].copy()
have = ext.intersection(avg.index)
rep.loc[have] = avg.loc[have, T].values
rep.loc[s1.index] = s1.values
rep.loc[s2.index] = s2.values
new = v[T].copy()
new.loc[lab] = 0.5 * rep.loc[lab].values + 0.5 * outsider.loc[lab].values
new.loc[lt == "unlabeled"] = np.nan

known = new.loc[lt != "unlabeled"]
assert new.loc[lt == "gold"].equals(v.loc[lt == "gold", T])
assert known.notna().all().all() and ((known >= 0) & (known <= 1)).all().all()

for name, tab in report:
    print(f"\n--- recalibration {name}\n{tab.to_string(index=False)}")
print(f"\nextracted rows: {len(ext):,} | with LLM labels: {len(have):,} | v3.1 fallback: {len(ext) - len(have):,}")
a50 = v[T].copy(); a50.loc[lab] = 0.5 * v.loc[lab, T].values + 0.5 * outsider.loc[lab].values
d = (new - a50).loc[lab]
print(pd.DataFrame({"mean |Δ| vs a50": d.abs().mean().round(3),
                    "pos share a50": (a50.loc[lab] >= .5).mean().round(3),
                    "pos share a50new": (new.loc[lab] >= .5).mean().round(3),
                    "gold pos share": (v.loc[lt == "gold", T] >= .5).mean().round(3)}).to_string())
# blind check: LLM average vs gold (gold rows are never fit-free for the recalibration, so this is optimistic)
g = v.index[lt == "gold"].intersection(avg.index)
if len(g):
    print("\nLLM part vs gold (recalibration was fitted on these rows too; optimistic):",
          round(np.nanmean([roc_auc_score(v.loc[g, t] > .5, avg.loc[g, t]) for t in T]), 3))
out = D / ("train_labels_a50new.csv" if STAGE == "full" else f"train_labels_a50new_{STAGE}.csv")
new.reset_index().to_csv(out, index=False)
print("written", out, "| rows", len(new), "| NaN rows", int(new.isna().all(axis=1).sum()))
