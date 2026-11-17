# Does a knee MRI ontology help an LLM label knee MRIs?

A pre-registered 2 x 2 ablation on the 58 expert-labelled studies of the
[RSNA Knee Abnormality Detection 2026](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection) training set.
An LLM (GPT-6.1 Sol, reasoning effort high) gives a probability for each of the 12 competition findings, reading
either the radiology report alone (**T**) or the report plus rendered MRI pages (**V**), with or without a curated
ontology section in the prompt (**plain** / **onto**). Each cell ran twice; the two repeats are averaged.

The design, hypotheses, frozen prompt hashes and decision rules were committed in
[`PREREGISTRATION.md`](PREREGISTRATION.md) (commit `f684fcd`) before any output was scored.

## Results

Macro AUC over the 12 findings, 58 studies (full tables: [`outputs/analysis/full_high/summary.md`](outputs/analysis/full_high/summary.md)).

| Cell | Material | Ontology | Macro AUC | Log loss |
| --- | --- | --- | --- | --- |
| T_plain | report | no | 0.8990 | 0.4382 |
| T_onto | report | yes | 0.8955 | 0.4406 |
| V_plain | report + images | no | 0.9356 | 0.3338 |
| V_onto | report + images | yes | 0.9405 | 0.3298 |

Pre-registered effects (paired bootstrap over studies, 10,000 resamples, 95% intervals):

| Effect | Δ macro AUC | 95% CI | Decision |
| --- | --- | --- | --- |
| H1 ontology, report only | −0.0036 | [−0.0104, 0.0032] | no proven advantage |
| H2 ontology, with images | +0.0049 | [−0.0013, 0.0120] | no proven advantage |
| H3 interaction (H2 − H1) | +0.0085 | [0.0015, 0.0162] | shown |
| Exploratory: images, no ontology | +0.0365 | [0.0195, 0.0552] | shown |

In short: seeing the images helps clearly; the ontology does not help on its own, but it helps more with images than without.

## Repository layout

```
PREREGISTRATION.md          design, hypotheses, frozen hashes, decision rules
pipeline/
  01_inventory.py           download the gold-58 DICOMs, check they are complete and readable
  02_render_packets.py      render each study into PNG page packets for the image cells
  03_build_prompts.py       build the 4 prompts + 2 JSON schemas from prompts/templates, record md5s
  04_score.py               scorer (AUC, weak-five, mimic subset, log loss, paired bootstrap)
  05_run_cells.py           run the 2x2 through the OpenAI Responses API (resumable)
  06_analyze.py             the pre-registered analysis
prompts/templates/          prompt sections (definitions, instructions, ontology knowledge, ...)
prompts/built/              the frozen prompts and schemas used in the runs (manifest.json has the md5s)
outputs/runs/full_high/     per-study probabilities for every cell and repeat (the model outputs)
outputs/runs/pilot_*/       pilot outputs (5 studies; not used in the analysis, see PREREGISTRATION.md §7)
outputs/reference/          earlier two-reader report labels, gold studies only (reference row + scorer self-check)
outputs/analysis/full_high/ the analysis tables
```

## Reproducing

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Competition data.** Accept the competition rules on Kaggle, download the competition files and put
`train.csv` and `train_series.csv` in `data/raw/`. Competition data is not redistributed here.
The 58 gold studies are the rows of `train.csv` with all 12 labels filled.

### A. Re-run the analysis from the committed model outputs (minutes, no API cost)

```bash
python pipeline/03_build_prompts.py      # rebuilds prompts/built; md5s must match manifest.json
python pipeline/04_score.py selfcheck    # expects macro AUC ≈ .891 / .885 / .897, prints SELF-CHECK PASSED
python pipeline/06_analyze.py            # writes outputs/analysis/full_high/
```

`cells.csv`, `effects.csv`, `per_finding.csv` and `repeat_noise.csv` reproduce exactly.
`summary.md` prints its tables as markdown if the optional `tabulate` package is installed and as plain text otherwise.

### B. Re-run the whole experiment (≈ $11 of API calls, a few hours)

Also needs Kaggle API credentials (for `kagglehub`) and an OpenAI API key: copy `.env.example` to `.env` and fill it in.

```bash
python pipeline/01_inventory.py                              # downloads harrisonhoran/ds-rsna-gold-images-only
python pipeline/02_render_packets.py                         # outputs/packets/ (≈ 550 MB, 1,095 pages)
python pipeline/03_build_prompts.py
python pipeline/05_run_cells.py --effort high --repeat 1     # 58 studies x 4 cells
python pipeline/05_run_cells.py --effort high --repeat 2
python pipeline/06_analyze.py
```

LLM outputs are not deterministic, so a fresh run will differ slightly from the committed one; the
run-to-run noise between our two repeats is in `outputs/analysis/full_high/repeat_noise.csv`
(1–2% of study × finding cells change side of 0.5).
Raw API responses (`outputs/runs/*/raw/`) are kept locally but not committed, because the
evidence notes can quote or paraphrase the competition reports.

## Licence and data

Code under the MIT licence ([`LICENSE`](LICENSE)). Competition data is used under the
[RSNA Knee competition rules](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/rules).
