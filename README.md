# RSNA Knee Abnormality Detection 2026: labels, inputs and blending

Code for my capstone thesis, *What Moved the Score: Labels, Inputs and Blending in a Silver-Medal Pipeline for
the RSNA 2026 Knee Abnormality Challenge*. The pipeline finished **191st of 6,425 teams** on the
[RSNA Knee Abnormality Detection 2026](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection)
private leaderboard (macro AUC .945, silver medal, top 3.0%).

The competition scores 12 knee MRI findings against radiologists reading the images, but the training labels
have to come from free-text reports. The pipeline has three stages:

1. **Labels.** Two LLMs read every report; their average is blended 50/50 with out-of-fold predictions of my
   own image models (two rounds of distillation). Final labels: **a50v2**, macro AUC .939 against the 58
   expert-labeled studies.
2. **Model.** A 2.5D ConvNeXt-T with multiple-instance pooling: five MRI series, 55 overlapping three-slice
   windows per study, left knees mirrored, one attention pool per finding.
3. **Ensemble.** A 12-model leg (8 general models + 4 single-finding specialists) at 20% in a per-finding rank
   average with the public .958 base notebook.

The full list of experiments, with results and decisions, is in [`docs/experiments.md`](docs/experiments.md).

## Repository layout

```
labels/
  01_radbert_review_flags.py      RadBERT text model; flags cells where it disagrees with the LLM labels for hand review
  02_apply_label_fixes_v3_1.py    v2 -> v3.1: Baker's cyst size rule, look-alike cap, 55 hand-reviewed cells
  03_dual_llm_readers.ipynb       two LLM readers (Claude Sonnet 5.5, GPT-6.1 Sol) on all 4,407 reports
  04_build_a50new.py              a50new = 0.5 LLM report part + 0.5 public-model out-of-fold predictions
  05_build_a50v2.py               a50v2 = 0.5 report part + 0.5 my own models' out-of-fold predictions (final labels)
training/
  train_cnn_mil.ipynb             Colab training notebook (ConvNeXt-T, 5 folds); RUN cell set to the final settings
submission/
  final_958_base_plus_ours_12models.ipynb   the final submission: public .958 base 80% + my 12-model leg 20%
  ours_plus_r6_majority_ours.ipynb          second pick: my leg + the public R6 model, my share 53% (public .956)
evaluation/
  score_oof.py                    scores out-of-fold predictions on the v3.1 / gold / conv yardsticks, paired bootstrap
docs/
  experiments.md                  every experiment, by pipeline stage
  experiments_quadrant_data.csv   benefit and estimated cost per experiment (and the chart)
  label_criteria.md               the 12 competition label definitions
```

## Reproducing

Competition data is not redistributed. Accept the competition rules on Kaggle and download the competition files.
Label files and caches go in `data/` (gitignored).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # API keys for the LLM readers; Kaggle credentials
```

### 1. Labels (CPU and API calls; roughly $100 for the two readers)

Run from the repo root, with the inputs in `data/labels/`:

```bash
cd data/labels && python ../../labels/01_radbert_review_flags.py && cd -   # then review radbert_label_flags.csv by hand
cd data/labels && python ../../labels/02_apply_label_fixes_v3_1.py && cd -
# run labels/03_dual_llm_readers.ipynb  ->  data/labels/rsna_llm_labels/llm_{claude,openai}_full.csv
python labels/04_build_a50new.py full
python labels/05_build_a50v2.py data/labels/teacher_oof/*.csv
```

Inputs not produced here: `train_processed_v2.csv` (the first LLM extraction), the hand labels
(`silver1_final_labels.csv`, `silver2_hand_labels.csv`, `radbert_flag_review.csv`), the public model's
out-of-fold predictions (`outsider_oof.csv`) and, for step 5, the out-of-fold files of the six model runs
trained on a50new (lat, dense5, ov2, ov2 seed 1, d5oai, ov2oai), which come from step 2 below.

### 2. Training (Colab, A100; about 2.5 GPU-hours per 5-fold run)

`training/train_cnn_mil.ipynb` reads the series cache (`0266fa68`: tissue-centred 130 mm crop, 24 slices per
series, 384 px), the label CSVs and the scanner-grouped fold file from Google Drive and Kaggle. Its **RUN** cell
is set to the final general model:

| Setting | Value |
| --- | --- |
| Backbone | ConvNeXt-T (`convnext_tiny.fb_in22k_ft_in1k`), 256 px, Optuna-tuned learning rates |
| Labels | a50v2 (validation on a50new) |
| Layout | dense5, overlapping windows at stride 2 (55 windows) |
| Laterality | left knees mirrored |
| Folds | 5 scanner-grouped folds, early stopping after 3 epochs without gain |
| Seeds | 42, 1, 2, 3 (`CFG["seed"]` in the Config cell) |

Three kinds of final models were made with small, one-off edits to this notebook that were not kept as options:

- **Full-data models**: the same settings trained on all labeled studies for a fixed number of epochs, without
  folds (same leaderboard score as 20 fold models at a fifth of the inference time).
- **Augmentation variants**: four extra training-time augmentation recipes (named erasemulti, elastic,
  seriesdrop and ridge in the experiment logs), one per model, kept as ensemble members.
- **Single-finding specialists**: Lateral Meniscus and PF OA, loss weight 0 on the other 11 findings and the
  checkpoint chosen on that finding's AUC; two seeds each.

### 3. Submission (Kaggle, 2×T4, internet off)

`submission/final_958_base_plus_ours_12models.ipynb` runs the public .958 base (Raptor-384, Raptor-224 and R6)
and my 12-model leg, then writes `submission.csv` as `0.8 × base + 0.2 × leg` in rank space, per finding.
It needs the base notebook's public datasets and my model weights attached as Kaggle datasets; the first cell
checks every input before any stage starts.

### 4. Evaluation

```bash
python evaluation/score_oof.py --run quad=oof/s42.csv,oof/s1.csv,oof/s2.csv,oof/s3.csv \
                               --run lat=oof/lat.csv --blend "quad+lat=quad:3,lat:1" \
                               --base quad --compare quad+lat
```

## Credits

The final blend uses public Kaggle work under its stated licences: dreaddevelopment's Raptor CoAtNet recipe and
weights, nartaa's 224-pixel CoAtNet and the R6 ConvNeXt bundle, as credited inside the submission notebook.
The study-level network design (window tokens, per-finding attention pooling, EMA weights) was adapted from a
public ConvNeXt reader notebook.

## Licence

Code under the MIT licence ([`LICENSE`](LICENSE)). Competition data is used under the
[competition rules](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/rules). OAI data, used in
experiments only, is not redistributed (OAI data use agreement).
