# Pre-registration: ontology ablation for LLM knee MRI labels

- **Author:** Harrison Horan
- **Date registered:** 2026-11-09, before any full run and before any model output was scored against the expert labels
- **Git commit of this file:** f684fcdd95eef7ec406e708e61ffb229bf7ecf81

## 1. Question

Does a structured knee MRI ontology, added to an LLM labeller's prompt, improve agreement with expert image-based labels, when the LLM reads only the radiology report and when it also sees the MRI images?

## 2. Hypotheses

- **H1 (report only):** the ontology does not improve report-only labels. Expected: T_onto - T_plain macro AUC near 0, 95% CI including 0.
- **H2 (with images):** the ontology improves report + image labels. Expected: V_onto - V_plain macro AUC above 0.
- **H3 (interaction):** the ontology helps more with images than without. Expected: (V_onto - V_plain) - (T_onto - T_plain) above 0.

If an effect's 95% interval includes 0, it is reported as "no proven advantage", together with the upper limit of the interval as the largest effect the data cannot rule out.

## 3. Design

A 2 x 2 factorial on the same studies, with 2 repeats per cell.

| Cell | Material | Ontology |
| --- | --- | --- |
| T_plain | report only | no |
| T_onto | report only | yes |
| V_plain | report + rendered image pages | no |
| V_onto | report + rendered image pages | yes |

Held fixed in all cells: model, reasoning effort, the 12 official competition definitions verbatim, the instruction that on-the-fence cases are graded negative, the answer rules, the output format for the 12 probabilities, and in the image cells the same page packet per study.

The ontology cells add (a) a curated knowledge section (imaging signs, grading scales, detection cues, mimics and pitfalls for the 12 findings, about 1,180 words) and (b) 19 structured fields filled before the 12 probabilities. Calibration notes, label-prior bands and co-occurrence percentages from the ontology file are excluded.

## 4. Data

- **Studies:** the 58 training studies of the RSNA Knee Abnormality Detection 2026 competition that carry expert labels (rows of `data/raw/train.csv` with all 12 labels filled). md5 of the sorted StudyInstanceUID list, one per line: `5a41a353f07bc978e7dc3ec0c9d51875`.
- **Positives per finding:** ACL 24, MCL 9, Medial meniscus 26, Lateral meniscus 23, Medial OA 15, Lateral OA 11, PF OA 21, Effusion 35, Synovitis 27, Baker's 12, Contusion 19, Fracture 18.
- **Images:** DICOMs from the Kaggle dataset `harrisonhoran/ds-rsna-gold-images-only` (58 studies, 336 series, 10,528 slices), rendered by `pipeline/02_render_packets.py`: overview pages of every series (4 x 4 tiles, 256 px, series over 48 slices sampled evenly), detail pages of one fluid-sensitive series per plane (3 x 3 tiles, 384 px, 18 central slices), at most 42 pages per study. Resulting packets: 11 to 29 pages per study, 1,095 pages in total.

## 5. Frozen materials

Prompts built by `pipeline/03_build_prompts.py` (`prompts/built/manifest.json`):

| File | md5 |
| --- | --- |
| T_plain.md (548 words) | fe58fbc39606c924f61319ec24f54dc5 |
| T_onto.md (1,732 words) | cf1887f6d47b7651c4bec8fc6e772968 |
| V_plain.md (638 words) | fb740b937647bb8bf42ea1632140a748 |
| V_onto.md (1,822 words) | 4eee0b28d5ce88f7c2d4d06ac99c443f |
| schema_plain.json | 56de9289f7bef16a9451002108dbe668 |
| schema_onto.json | 0cb3870f1001895c5b2f46f859749682 |

Model call (`pipeline/05_run_cells.py`): `gpt-6.1-sol` through the OpenAI Responses API, reasoning effort **high**, strict JSON-schema structured output, images sent as JPEG (quality 90) with `detail: high`, one call per study and cell.

## 6. Runs

- Full run: `--effort high --repeat 1`, then `--effort high --repeat 2`, all 58 studies x 4 cells each (464 calls).
- Failed calls are retried by rerunning the same command. A valid response is never replaced by a rerun.
- Every raw response is kept with its token usage, prompt md5 and timestamp.

## 7. Pilot disclosure

Before registration, three pilots ran on the first 5 studies in sorted StudyInstanceUID order (ending ...520594649149, ...248839028269, ...080836752052, ...439102017580, ...983002209238), all 4 cells, once each, at reasoning effort medium, high and xhigh (60 calls). They were used only to check response validity, cost, time, reasoning tokens, series coverage in the evidence notes and the share of unassessable structured fields. They were not scored against the expert labels. Effort **high** was chosen on those process measures. Pilot outputs are kept separately (`outputs/runs/pilot_*`) and are not used in the analysis; the full run re-labels these 5 studies.

## 8. Outcomes and analysis

- **Primary outcome:** macro AUC over the 12 findings on the 58 studies.
- **Secondary outcomes:** AUC on the weak five (PF OA, Effusion, Synovitis, Contusion, Lateral OA); AUC on the mimic subset (ACL, Medial meniscus, Lateral meniscus, Contusion, Fracture); log loss; confident errors (p >= 0.9 on a gold negative or p <= 0.1 on a gold positive); AUC per finding.
- **Cell score:** the two repeats are averaged per study and finding, then scored (`pipeline/04_score.py`).
- **Primary comparisons:** T_onto vs T_plain (H1), V_onto vs V_plain (H2), the interaction (H3).
- **Statistics:** paired bootstrap over studies, 10,000 resamples, seed 0, 95% percentile intervals. The same resampled studies score every cell, so the interaction interval comes from the same resamples.
- **Run-to-run noise:** agreement between repeat 1 and repeat 2 is reported per cell (share of the 696 cells per cell whose probability changes side of 0.5, and macro AUC of each repeat).
- **Exploratory, labelled as such:** V_plain vs T_plain (effect of seeing the images); an after-the-fact ontology rule arm applied to existing label sets; analysis of the structured fields; the earlier two-reader report labels as a reference row.

## 9. Decision rules

- An effect counts as shown if its 95% interval lies entirely above 0.
- Otherwise the result is "no proven advantage", reported with the interval's upper limit.
- **Gate to a full-training-set relabel** (future work if not run): V_onto - V_plain interval above 0, or a point estimate of at least +0.01 macro AUC with both repeats pointing the same way.

## 10. Known limitations, stated in advance

- **Power:** with 58 studies (9 to 35 positives per finding), macro AUC moves by about +/-0.02 by chance.
- **Prompt length:** the ontology prompts are about 1,180 words longer than the plain prompts; length is not matched.
- **One model and one prompt design;** the result may not carry to other models.
- **Image resolution:** the model sees rendered, down-sampled 2D pages, not 3D volumes at full resolution.
- **The 58 studies were used during the earlier competition work** (calibration of earlier report labels). The prompts registered here contain no gold-derived anchors: only the official definitions and the curated ontology knowledge.

## 11. Deviations

Any change after this file is committed is recorded here with its date and reason.

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-17 | Reference report labels (`llm_claude_full.csv`, `llm_openai_full.csv`) moved to `outputs/reference/`, cut to the 58 gold studies and the probability columns; `LLM_DIR` in `04_score.py` updated. | Repository clean-up, so the reference row and self-check can be published without report text. Scores unchanged (all analysis CSVs reproduce byte-for-byte). |
| 2026-11-17 | Source comments in `prompts/templates/ontology_knowledge.md` edited (a source URL added). | Attribution only. HTML comments are stripped by `03_build_prompts.py`; the built prompt md5s are unchanged. |
