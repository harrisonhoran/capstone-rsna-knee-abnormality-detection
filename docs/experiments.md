# All experiments, by pipeline stage

Every experiment and trial run from 29 September to 22 October 2026, plus two runs after the competition
(Appendix A of the final report). Results are changes in macro AUC unless stated. Yardsticks:
**gold** = the 58 expert-labeled studies, pooled out of fold; **v3.1** = report-derived labels, pooled out of fold
(4,348 studies) or one fold (about 870); **conv** = 277 expert and hand-labeled studies; **LB** = public leaderboard.
Ideas that were proposed but never run are not listed.

`experiments_quadrant_data.csv` and `experiments_quadrant.png` place 49 of these by benefit and estimated cost
(cost = GPU-hours + 0.1 × CPU-hours, estimated from run times in the logs).

## Labels

| Experiment | Result | Decision |
| --- | --- | --- |
| v2: first LLM extraction of the reports | Baseline DINOv2 model, LB .889 | Superseded |
| v3.1: small and trace Baker's cysts raised, 42 look-alike cysts capped, 55 cells fixed by hand | LB .889 → .891; Baker's gold +.029; gold macro −.010 (rare findings, noise) | Kept as report base |
| a50: 0.5 v3.1 + 0.5 public image model's out-of-fold predictions | LB .891 → .896 | Superseded |
| a50r: text-rule floors and hand labels in the report half | Fold 0 v3.1 −.004; gold and conv not different | Dropped |
| a50new: two LLM report readers (Claude Sonnet 5.5, GPT-6.1 Sol) replace the report half | Label set +.025 on gold; models trained on it −.009 (DINOv2) and +.0035 (ConvNeXt), both within noise | Kept as report half |
| Third LLM (Claude Opus 5.5) adjudicates 255 disputed cells | Label set +.002 on gold | Pilot only |
| Synovitis rule: silent synovitis with effusion ≥ .5 raised to .45 | Fold 2: no change | Dropped |
| Imputation rules (Hoffa's fat-pad edema → synovitis, tendinopathy → PF OA) | Not supported by the images or by gold | Dropped |
| **a50v2: second distillation round, my six-run leg as image teacher** | **Model gold +.0115 (+.002 to +.020), conv +.013, v3.1 +.010** | **Kept (final labels)** |
| a50v2 mix of report and teacher, report share .3 to .6 | Flat on gold (within .002) | Kept .5 |
| Hand review of 80 disputed cells | Report label right in 70 of 80 | Folded into a50v3 |
| a50v3: third distillation round | Teacher gain about a fifth of round two's | Dropped |
| LLM review of the report half (Claude Opus, 577 studies) | Label set gold +.0016 (n.s.); PF OA +.026, Baker's −.013 | PF OA only, as a50v4 |
| a50v4: reviewed PF OA report text | Gold −.0028 (mean of 2 seeds) | Dropped |
| Report-rule relabeling (29-phrase search; all-negative and "small means positive" rules) | Both rules failed on gold | Dropped |
| Zero-shot multilingual NLI labels (mDeBERTa-v3) | Gold macro .714, against .897 for the LLM readers | Dropped |

## Input and preprocessing

| Experiment | Result | Decision |
| --- | --- | --- |
| Baseline cache: 130 mm centre crop, 24 slices per series, 384 px, 5 series slots, 22 windows | DINOv2 model, LB .889 | Superseded |
| Knee-centred (tissue) crop | Ties the centre crop on v3.1 and gold; conv −.006; the two averaged were best | Kept (cache 0266fa68) |
| Sagittal re-crop to include the anterior knee | Gold −.005 (n.s.) | Dropped |
| Sixth series slot (axial without fat suppression) | −.003 on folds 0 and 3 | Dropped |
| Denser layout, 22 → 40 windows | Fold 3 v3.1 +.0079 (+.0033 to +.0121) | Kept |
| Overlapping windows at stride 2, 40 → 55 | Pooled v3.1 +.0021, conv +.0069 | Kept |
| 36-slice cache, 85 windows | Fold 3 tie at about 8× the compute | Dropped |
| 384 px input instead of 256 | Fold 3 +.0014 | Parked |
| Mirroring left knees | Alone gold +.011; as third member gold +.0038, conv +.0037 | Kept |
| Centre crop at 256 px | Flat | Dropped |
| OAI knees, 3 labels, weight 1.0 | Fold 3 v3.1 +.0022 | Moved to the denser layout |
| OAI knees, all 9 MOAKS labels | Lateral Meniscus clearly worse | Dropped |
| OAI knees on the denser layout, weight 0.5 | Helped on a50new labels; on a50v2 −.002 to −.003 at 1.6× cost | Dropped for final labels |

## Model and training

| Experiment | Result | Decision |
| --- | --- | --- |
| DINOv2 ViT-S at 336 px | LB .889 | Superseded |
| DINOv2 Optuna tune (backbone learning rate ×3) | LB .896 → .916 | Superseded |
| EfficientNet-B4 (Noisy Student), tuned, batch-norm frozen | Gold .891 alone; three-model ensemble conv +.0048 | Superseded |
| RadImageNet ResNet-50 | Fold 0 plateau .750 | Dropped |
| ConvNeXt-T with attention pooling, untuned | LB .907 | Became the base model |
| **ConvNeXt-T Optuna tune (20 trials)** | **Gold +.037 (+.014 to +.062)** | **Kept** |
| ConvNeXt-T re-tune on the final layout (16 trials) | +.0019 (noise) | Settings unchanged |
| CoAtNet-2, untuned and tuned | Adding it to ConvNeXt gold −.002 | Dropped |
| ConvNeXt-S at 384 px | Fold 3 −.0018; blend +.0003; 10 h for 5 folds | Dropped |
| EfficientNetV2-S, tuned, 2 seeds | −.0035 alone | Dropped |
| MaxViT-T, untuned and 3 Optuna rounds | Blend −.0004 v3.1, −.0029 conv | Dropped |
| OrthoFoundation-L (knee foundation model), frozen features | Gold .835 against .932; blend −.0055 | Dropped |
| Second, third and fourth seeds | +.0028, +.0009, +.0002 | Kept four |
| Synovitis loss ×4 with checkpoint on synovitis | Synovitis +.007; macro −.001 | Dropped |
| Series dropout during training | Fold 0 .9463 against .9481 | Dropped |
| Epoch averaging (epochs 6–11) | No gain | Dropped |
| Early stopping, patience 3 | Same results, 4–7 fewer epochs | Kept |
| 36 auxiliary report outputs (keyword targets) | −.0034 (−.0067 to −.0003) | Dropped |
| 23 augmentation recipes, one per run | None beat plain training on a second seed | None kept alone |
| Four recipe models added to the four seeds | Fold 3 v3.1 +.0014, conv +.0037 | Kept as members |
| OA specialists by loss masking | Best +.0026, under the +.003 bar | Dropped |
| Single-finding specialists: Lateral Meniscus, PF OA | Fold 3 +.0138 and +.0048 on their finding; LB .948 → .949 | Kept |
| Medial OA specialists | Fold 3 +.0032; LB −.001 | Dropped |
| Full-data models (all studies, fixed epoch) | Same LB as 20 fold models at 1/5 of the inference time | Kept |

## Inference and post-processing

| Experiment | Result | Decision |
| --- | --- | --- |
| Slice-shift test-time augmentation | No LB change at 3× inference time | Dropped |
| Series-dropout test-time augmentation | v3.1 −.0001, conv −.0003 | Dropped |
| Per-finding stacker on my own outputs and metadata | Lower on every yardstick | Dropped |
| Per-finding stacker with image intensity features | v3.1 −.0027 | Dropped |
| Cross-finding post-processing | Hurt gold | Dropped |
| Background preprocessing and time guards | Stack plus leg runtime about 9.5 h → 6.6 h | Kept |
| Decoder check and missing-model guard | Caught two silent failures | Kept |

## Ensembles and submissions (public leaderboard)

| Experiment | Result | Decision |
| --- | --- | --- |
| My model + Raptor at weight .5 / .7 / .8 | .921 / .926 / .928 | Superseded |
| Public .943 stack + my leg | .943 to .944 | Superseded |
| .950 public base + my leg at .10 / .20 / .50 | .950 / .951 / .950 | Superseded |
| .957 base + my leg at .10 / .20 / .30 | .956 / .957 / .956 | Kept .20 |
| **.958 base + 12-model leg at .20** | **.958 public, .945 private (191st of 6,425)** | **Final submission** |
| .958 base + 14 models (Medial OA specialists) | .957 | Dropped |
| My leg + R6, my share .53 | .956 | Second pick |

## After the competition

| Experiment | Result |
| --- | --- |
| Late submission of the 1st-place notebook, unchanged | .969 public / .960 private |
| 1st-place pipeline retrained, one fold at 256 px | .962 public / .954 private |
