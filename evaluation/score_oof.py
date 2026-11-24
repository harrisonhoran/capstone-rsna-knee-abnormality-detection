"""Score pooled 5-fold out-of-fold (OOF) predictions on the three local yardsticks used in the report,
and compare runs or blends with a paired bootstrap.

Yardsticks
    v3.1   report-derived labels for every labeled study (expert labels where they exist), 4,348 studies
    gold   the 58 expert-labeled studies (decides final picks)
    conv   gold + my hand labels written from reports (277 studies)

Blends are per-finding rank averages, the same way the submission combines models.

Usage (from the repo root):
    python evaluation/score_oof.py \
        --run quad=oof/s42.csv,oof/s1.csv,oof/s2.csv,oof/s3.csv \
        --run lat=oof/lat.csv \
        --blend "quad+lat=quad:3,lat:1" \
        --base quad --compare quad+lat
A run given as several files (one per fold) is concatenated. Every OOF csv needs StudyInstanceUID,
the 12 findings and an is_gold column (as written by training/train_cnn_mil.ipynb).
"""
import argparse
import warnings

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
T = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA", "PF OA", "Effusion",
     "Synovitis", "Baker's", "Contusion", "Fracture"]


def load_run(paths):
    df = pd.concat([pd.read_csv(p) for p in paths]).drop_duplicates("StudyInstanceUID")
    return df.set_index("StudyInstanceUID")


def rank(df, ids):
    return df.loc[ids, T].apply(lambda c: rankdata(c) / len(c))


def macro(P, Y):
    y = Y.values > .5
    p = P.loc[Y.index, T].values
    d = {t: roc_auc_score(y[:, j], p[:, j]) for j, t in enumerate(T) if 0 < y[:, j].sum() < len(y)}
    return np.mean(list(d.values())), d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v31", default="data/labels/train_processed_v3_1.csv")
    ap.add_argument("--silver", nargs="*", default=["data/labels/silver1_final_labels.csv",
                                                    "data/labels/silver2_hand_labels.csv"])
    ap.add_argument("--run", action="append", required=True, help="name=file1,file2,...")
    ap.add_argument("--blend", action="append", default=[], help="name=run1:weight,run2:weight")
    ap.add_argument("--base", help="run or blend the comparisons are made against")
    ap.add_argument("--compare", nargs="*", default=[])
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    runs = {}
    for r in a.run:
        name, files = r.split("=", 1)
        runs[name] = load_run(files.split(","))
    ref = pd.read_csv(a.v31).set_index("StudyInstanceUID")
    ids = None
    for r in runs.values():
        ids = r.index if ids is None else ids.intersection(r.index)
    first = next(iter(runs.values()))
    gold = ids[first.loc[ids, "is_gold"].astype(bool).values]
    hand = pd.concat([pd.read_csv(f).set_index("StudyInstanceUID")[T] for f in a.silver])
    conv = pd.concat([ref.loc[gold, T], hand])
    conv = conv[~conv.index.duplicated()]
    conv = conv.loc[conv.index.intersection(ids)]

    R = {k: rank(v, ids) for k, v in runs.items()}
    for b in a.blend:
        name, parts = b.split("=", 1)
        parts = [(p.split(":")[0], float(p.split(":")[1])) for p in parts.split(",")]
        w = np.array([p[1] for p in parts])
        w /= w.sum()
        R[name] = sum(wi * R[k] for wi, (k, _) in zip(w, parts))

    print(f"studies {len(ids)} | gold {len(gold)} | conv {len(conv)}")
    rows = {k: [macro(P, ref.loc[ids, T])[0], macro(P, ref.loc[gold, T])[0], macro(P, conv)[0]] for k, P in R.items()}
    print(pd.DataFrame(rows, index=["v3.1", "gold", "conv"]).T.round(4))
    print("\nper finding, gold:")
    print(pd.DataFrame({k: macro(R[k], ref.loc[gold, T])[1] for k in R}).round(3))
    keys = list(runs)
    if len(keys) > 1:
        print("\nSpearman rank correlation (mean over findings):")
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                c = np.mean([spearmanr(R[keys[i]][t], R[keys[j]][t])[0] for t in T])
                print(f"  {keys[i]} ~ {keys[j]}: {c:.3f}")

    if a.base and a.compare:
        rng = np.random.default_rng(a.seed)
        for yard, Y in [("v3.1", ref.loc[ids, T]), ("gold", ref.loc[gold, T]), ("conv", conv)]:
            idx = Y.index.values
            for c in a.compare:
                d = []
                for _ in range(a.n_boot):
                    s = pd.Index(rng.choice(idx, len(idx)))
                    y = Y.loc[s].values > .5

                    def m(P):
                        p = P.loc[s, T].values
                        return np.nanmean([roc_auc_score(y[:, j], p[:, j]) if 0 < y[:, j].sum() < len(y) else np.nan
                                           for j in range(len(T))])
                    d.append(m(R[c]) - m(R[a.base]))
                d = np.array(d)
                print(f"bootstrap {yard}: {c} - {a.base}: {d.mean():+.4f} "
                      f"[95% {np.percentile(d, 2.5):+.4f}, {np.percentile(d, 97.5):+.4f}] P>0 {np.mean(d > 0):.2f}")


if __name__ == "__main__":
    main()
