"""a50v2 training labels: the second distillation round (the labels behind the final models).

    a50v2 = 0.5 * report part + 0.5 * image teacher        on extracted + silver rows
    gold rows (58)       = the expert labels, unchanged
    unlabeled rows (59)  = NaN, so the study set and folds stay identical to a50new

Report part: recovered exactly from a50new, which is 0.5 * report + 0.5 * outsider OOF,
    so report = 2 * a50new - outsider (checked: rebuilding a50new from it is exact).
Image teacher: the mean raw out-of-fold probability of my own model runs trained on a50new
    (the six-run leg: lat, dense5, ov2, ov2 seed 1, d5oai, ov2oai), quantile-mapped per finding
    onto the outsider OOF's distribution. That keeps the stronger teacher's ranking and a50new's
    scale and positive rates.

Note: this script was rebuilt for the repository from the recorded recipe; the original builder lived
in a scratch environment that no longer exists. Check the output against the md5 of the production
file (66c04df2b575955621d28e7ec3a3843e) if you have the same teacher OOF files.

Usage (from the repo root):
    python labels/05_build_a50v2.py data/labels/teacher_oof/*.csv
Each teacher file: one pooled 5-fold OOF csv per run, columns StudyInstanceUID + the 12 findings.
Inputs in data/labels/: train_processed_v3_1.csv (label_type), train_labels_a50new.csv, outsider_oof.csv.
Output: data/labels/train_labels_a50v2.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

T = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA", "PF OA", "Effusion",
     "Synovitis", "Baker's", "Contusion", "Fracture"]
D = Path("data/labels")
REPORT_SHARE = 0.5          # a sweep of .3 to .6 was flat on the expert labels; .5 kept

teacher_files = sys.argv[1:]
if not teacher_files:
    raise SystemExit("give the teacher OOF csv files as arguments")

v31 = pd.read_csv(D / "train_processed_v3_1.csv").set_index("StudyInstanceUID")
lt = v31["label_type"]
a50new = pd.read_csv(D / "train_labels_a50new.csv").set_index("StudyInstanceUID")[T]
outsider = pd.read_csv(D / "outsider_oof.csv").set_index("StudyInstanceUID")[T]

lab = lt.index[lt.isin(["extracted", "silver"])]
gold = lt.index[lt == "gold"]

# 1. report part, recovered from a50new
report = 2 * a50new.loc[lab] - outsider.loc[lab]
assert np.allclose(0.5 * report + 0.5 * outsider.loc[lab], a50new.loc[lab]), "report part does not rebuild a50new"

# 2. teacher = mean raw OOF probability over the runs
runs = [pd.read_csv(f).drop_duplicates("StudyInstanceUID").set_index("StudyInstanceUID")[T] for f in teacher_files]
teacher = sum(r.loc[lab] for r in runs) / len(runs)
assert teacher.notna().all().all(), "a teacher run is missing studies"

# 3. quantile-map each finding onto the outsider OOF's distribution over the same rows
mapped = teacher.copy()
for t in T:
    pct = teacher[t].rank(method="average", pct=True)
    mapped[t] = np.quantile(outsider.loc[lab, t].values, pct.clip(0, 1).values)

# 4. blend, keep gold, leave unlabeled empty
new = a50new.copy()
new.loc[lab] = (REPORT_SHARE * report + (1 - REPORT_SHARE) * mapped).clip(0, 1).values
new.loc[gold] = v31.loc[gold, T].values
new.loc[lt.index[lt == "unlabeled"]] = np.nan

known = new.loc[lt != "unlabeled"]
assert known.notna().all().all() and ((known >= 0) & (known <= 1)).all().all()
print(pd.DataFrame({"pos share a50new": (a50new.loc[lab] >= .5).mean().round(3),
                    "pos share a50v2": (new.loc[lab] >= .5).mean().round(3),
                    "mean |change|": (new.loc[lab] - a50new.loc[lab]).abs().mean().round(3)}).to_string())
out = D / "train_labels_a50v2.csv"
new.reset_index().to_csv(out, index=False)
print("written", out, "| rows", len(new), "| teacher runs", len(runs))
