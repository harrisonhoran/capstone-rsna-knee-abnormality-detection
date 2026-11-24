# Official Label Criteria — RSNA 2026 Knee Abnormality Detection

Authoritative reference distilled from the host's competition overview (courtesy Dr. Jacob Kazam; host Q&A on LLM usage from Po-Hao "Howard" Chen — see `COMPETITION_RULES_NOTES.md` for that rules thread). This document **supersedes** `knee-mri-reading-process/README.md` and `SEARCH_PATTERN.md` wherever they conflict on a specific severity threshold: those two files are paraphrased from a general MSK teaching video (Dr. Atinga) and say so explicitly. This file quotes the actual ground-truth criteria the annotating radiologists used to produce *this competition's* labels.

Use this file as the source of truth for:
- `pipeline/label_engineering.py`'s LLM report-extraction prompt — labels for the unlabeled majority must match these criteria, not looser teaching-level criteria
- calibration/threshold decisions in `PROJECT_PLAN.md` stages 4 and 9
- validating any segmentation-derived features in `PROJECT_PLAN.md` stage 5b

## Ground rules that apply to all 12 labels

- **Binary presence/absence, one label per whole examination, for a single knee** — not per-slice, per-lesion, or per-compartment-instance (the 3 OA labels are the one case scored per-compartment, see below).
- **Ambiguous / borderline ("on the fence") findings are graded NEGATIVE.** The host explicitly favors specificity over sensitivity at the boundary. Any label-engineering prompt or modeling threshold should carry the same bias — when in doubt, negative.
- **Two independent subspecialty MSK radiologists label each study; a third adjudicates disagreements** to produce one consensus label. Expect real but bounded inter-reader noise even in the "officially labeled" subset.
- **"Fluid sensitive" (host's own definition):** a sequence in which edema, hemorrhage, and other fluid appear bright and fat is suppressed in some way (PD fat-sat, T2 fat-sat, STIR — matches the `Fluid_Sensitive`/`Fat_Suppression` flags already planned for `train_series.csv` in stage 2 EDA).
- **Three knee compartments**, used for the three OA labels: **medial** (medial femoral condyle / medial tibial plateau), **lateral** (lateral femoral condyle / lateral tibial plateau), **patellofemoral** (patella / femoral trochlea).
- Reports are in **many languages**; the criteria below are what extraction should map onto in any language, not specific English keywords.

## Per-label criteria

### ACL
**Positive:** high-grade partial or full-thickness tear — complete discontinuity of the ligament, OR more than 50% of fibers disrupted — with or without secondary pivot-shift bone contusions.
**Negative:** mild signal change, degeneration, or thickening without discontinuity.
*(Confirms the teaching-video caveat that ACL intrasubstance signal without disruption may be mucoid degeneration — the host gives it a hard >50%-of-fibers / complete-discontinuity bar.)*

### MCL
**Positive:** high-grade partial or complete **acute** tear — disrupted fibers and edema within/adjacent to the ligament.
**Negative:** low-grade sprains, AND chronic or remote stress changes.
*(Correction to this project's earlier notes: the video's 3-tier grading — low/moderate/high — maps to only the "high" tier being positive here. "Low grade" (perifascial edema, otherwise-normal ligament) and "moderate grade" (thickened, abnormal signal, fibers still continuous) both grade NEGATIVE. `knee-mri-reading-process/SEARCH_PATTERN.md`'s earlier suggestion to treat "edema only" language as a soft positive is superseded by this.)*

### Medial Meniscus / Lateral Meniscus (same criteria, scored separately)
**Positive:** abnormal signal that definitely contacts the meniscal surface on **at least two images**, OR a morphologic abnormality (truncated, diminutive, or displaced fragment).
**Negative:** intrasubstance degeneration that does not reach the surface.
*(Matches the video's "≥2 slices/sequences" rule; adds the morphologic path explicitly, which covers bucket-handle/displaced-fragment tears that may not present as a classic bright line.)*

### Medial OA / Lateral OA / PF OA (same criteria, scored separately per compartment)
**Positive:** a moderate or large area (roughly **≥1 cm**) of high-grade cartilage loss — **greater than 50% of cartilage thickness** — in that compartment, with or without underlying subchondral marrow changes.
**Negative:** smaller-area or lower-grade cartilage thinning.
*(New and specific — useful for stage 5b: if reproducing cartilage thickness as a segmentation-derived feature, validate/binarize against this exact threshold — >50% thickness loss over a ≥1cm area — rather than an arbitrary cutoff.)*

### Effusion
**Positive:** a **moderate or large** amount of fluid distending the joint.
**Negative:** small/physiologic effusion (explicitly normal per both this source and the teaching video, e.g. post-activity).

### Synovitis
**Positive:** inflammation and thickening of the synovial lining of the joint.
*(A distinct finding from Effusion — synovial lining morphology, not fluid volume; matches the video's explicit "these are different findings" point.)*

### Baker's (popliteal) cyst
**Positive:** a **moderate or large** fluid collection in the characteristic location behind the knee (semimembranosus–medial gastrocnemius interval).
**Negative:** small collections there, and the other normal-variant popliteal fluid pockets (popliteus tendon sheath, gastrocnemius-origin cysts) — per the video, those are incidental unless focally tender.

### Contusion
**Positive:** bone marrow edema-like signal from impact, **without** a discrete fracture line.

### Fracture
**Positive:** an acute cortical break or fracture line.
*(Implies the same marrow signal change as Contusion, plus the cortical break — Contusion and Fracture remain a near-hierarchical pair, per `SEARCH_PATTERN.md` step 6.)*

## Source

2026 RSNA Knee Abnormality Detection AI Challenge, competition overview page ("Label Description" section), courtesy Dr. Jacob Kazam. Pasted into this project 2026-09-08.

## Worked examples from the host's image annotation guidelines

Exact captions from the host's annotated positive/negative example figures (yellow arrows/arrowheads mark the finding in each figure). These are real radiology-report-register phrasing for each label at the decision boundary — useful as few-shot calibration for `pipeline/label_engineering.py`'s extraction prompt, and as a sanity check on borderline cases during error analysis.

### Osteoarthritis (Medial / Lateral / PF OA)

**Positive:**
- "Diffuse full thickness cartilage loss in medial femoral condyle with subchondral reactive changes (arrowheads)" — medial compartment.
- "Focal area of high-grade area of cartilage loss with subchondral reactive changes in the trochlea (arrowheads)." — patellofemoral compartment; note a *focal* (not diffuse) area still qualifies once it's high-grade with reactive marrow change.

**Negative:**
- "Normal homogeneous cartilage signal in the medial femoral condyle without underlying subchondral marrow changes"
- "Mild heterogenous signal (arrowheads) in the lateral tibial plateau due to normal orientation of cartilage fibers" — a normal cartilage-fiber-orientation artifact, not thinning; don't let heterogeneous signal alone trigger a positive read.

### Medial / Lateral Meniscus Tear

**Positive:**
- "Increased signal definitely contacting surface on 2 slices (arrows) and parameniscal cyst (arrowhead) compatible with a meniscal tear" — the ≥2-image surface-contact rule shown directly; the parameniscal cyst is a supportive secondary sign, not itself the criterion.

**Negative:**
- "Increased signal definitely contacting surface on a single slice (arrow) with mild irregularity on adjacent slices compatible with fraying without a definite tear (arrowheads)" — surface contact on only **1** slice = negative ("fraying"), directly illustrating why the ≥2-image bar exists.
- "Increased signal (arrowheads) not definitely reaching surface compatible with degenerative changes. No tear." — signal present but doesn't reach the surface at all = negative.

### MCL Tear

**Positive:**
- "Intact fibers with ligament thickening and edema signal (arrows) and edema signal adjacent to the ligament (arrowheads) compatible with a high-grade partial tear"
- "Torn fibers anteriorly with ligament thickening and edema signal within and adjacent to the ligament (arrowheads) with intact fibers posteriorly (arrows) compatible with an acute high-grade partial tear."

**Negative:**
- "Intact fibers with increased signal at the femoral attachment without edema signal adjacent to the ligament (arrows) compatible with remote tear" — note the caption itself uses the word "tear," but it's a *remote* tear, i.e. chronic, so it grades negative per the host's rule.
- "Intact fibers with ligament thickening (arrows) without edema signal adjacent to the ligament compatible with chronic stress changes or remote injury"

**Important refinement to the "Per-label criteria" MCL entry above:** that entry (from the host's prose description) says positive requires "disrupted fibers and edema." The first positive example here has **intact** fibers, yet is still called a high-grade partial tear, based on ligament thickening plus edema *within and adjacent to* the ligament. So fiber disruption is sufficient but not strictly necessary — thickening + edema-within-and-adjacent-to-the-ligament is enough on its own. What separates these positives from the negatives above is the **presence of edema adjacent to the ligament**: both negative examples have thickening/signal change but explicitly **no adjacent edema**, and are chronic/remote. So the real discriminator for label-extraction purposes is acute peri-ligamentous edema, not fiber continuity per se — update the extraction prompt's mental model accordingly if it's ever revised.

### ACL Tear

**Positive:**
- "Complete ligament discontinuity in the intercondylar notch (arrows) with secondary signs including pivot shift bone contusions and deep notch sign (arrowheads)" — note "deep notch sign" as another secondary sign alongside pivot-shift contusions, not previously listed.

**Negative:**
- "Thickened ligament with increased signal and no discontinuity (arrows) and no secondary signs compatible with mucoid degeneration of the ACL" — the canonical mucoid-degeneration mimic, now with an exact caption/phrasing to pattern-match against.

*Source: host-provided image annotation guideline figures ("Positive OA" / "Negative OA", "Positive for Meniscal Tear" / "Negative for Meniscal Tear", "Positive for MCL Tear" / "Negative for MCL Tear", "Positive ACL Tear" / "Negative ACL Tear"), pasted into this project 2026-09-08.*
