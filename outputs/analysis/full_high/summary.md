# Ontology ablation results (full_high, repeats [1, 2])

## Cell scores

```
                                       cell  repeats  macro_auc  weak5_auc  mimic_auc  log_loss  confident_errors
                                    T_plain averaged     0.8990     0.8540     0.9239    0.4382                58
                                    T_plain       r1     0.8963     0.8508     0.9214    0.4414                59
                                    T_plain       r2     0.8991     0.8548     0.9235    0.4372                58
                                     T_onto averaged     0.8955     0.8532     0.9204    0.4406                56
                                     T_onto       r1     0.8930     0.8500     0.9199    0.4425                60
                                     T_onto       r2     0.8953     0.8560     0.9186    0.4413                55
                                    V_plain averaged     0.9356     0.9067     0.9455    0.3338                37
                                    V_plain       r1     0.9324     0.8987     0.9428    0.3381                39
                                    V_plain       r2     0.9362     0.9108     0.9463    0.3341                39
                                     V_onto averaged     0.9405     0.9127     0.9505    0.3298                40
                                     V_onto       r1     0.9385     0.9091     0.9510    0.3299                39
                                     V_onto       r2     0.9406     0.9138     0.9488    0.3331                43
reference: earlier two-reader report labels        -     0.8968     0.8514     0.8995    0.3694                23
```

## Pre-registered effects (paired bootstrap, 10,000 resamples, 95% intervals)

```
                                              effect    metric   delta  ci_low  ci_high  P(improvement)            decision
         H1 ontology, report only (T_onto - T_plain) macro_auc -0.0036 -0.0104   0.0032          0.1493 no proven advantage
         H2 ontology, with images (V_onto - V_plain) macro_auc  0.0049 -0.0013   0.0120          0.9357 no proven advantage
                            H3 interaction (H2 - H1) macro_auc  0.0085  0.0015   0.0162          0.9887               shown
Exploratory: images, no ontology (V_plain - T_plain) macro_auc  0.0365  0.0195   0.0552          1.0000               shown
         H1 ontology, report only (T_onto - T_plain) weak5_auc -0.0007 -0.0131   0.0123          0.4437 no proven advantage
         H2 ontology, with images (V_onto - V_plain) weak5_auc  0.0059 -0.0067   0.0207          0.8021 no proven advantage
                            H3 interaction (H2 - H1) weak5_auc  0.0066 -0.0082   0.0223          0.8187 no proven advantage
Exploratory: images, no ontology (V_plain - T_plain) weak5_auc  0.0528  0.0247   0.0845          1.0000               shown
         H1 ontology, report only (T_onto - T_plain) mimic_auc -0.0034 -0.0114   0.0044          0.1873 no proven advantage
         H2 ontology, with images (V_onto - V_plain) mimic_auc  0.0050 -0.0031   0.0149          0.8769 no proven advantage
                            H3 interaction (H2 - H1) mimic_auc  0.0085 -0.0037   0.0225          0.9193 no proven advantage
Exploratory: images, no ontology (V_plain - T_plain) mimic_auc  0.0216  0.0048   0.0417          0.9964               shown
         H1 ontology, report only (T_onto - T_plain)  log_loss  0.0024 -0.0088   0.0133          0.3366 no proven advantage
         H2 ontology, with images (V_onto - V_plain)  log_loss -0.0041 -0.0149   0.0059          0.7763 no proven advantage
                            H3 interaction (H2 - H1)  log_loss -0.0065 -0.0171   0.0040          0.8842 no proven advantage
Exploratory: images, no ontology (V_plain - T_plain)  log_loss -0.1044 -0.1433  -0.0697          1.0000               shown
```

## Ontology effect per finding (descriptive)

```
         finding  positives  auc_T_plain  auc_T_onto  auc_V_plain  auc_V_onto  onto_effect_report_only  onto_effect_with_images  mimic_subset  weak_five
             ACL         24        0.992       0.989        0.987       0.993                   -0.003                    0.006          True      False
             MCL          9        0.989       0.989        0.982       0.991                    0.000                    0.009         False      False
 Medial Meniscus         26        0.970       0.970        0.975       0.974                    0.000                   -0.001          True      False
Lateral Meniscus         23        0.904       0.897        0.916       0.930                   -0.007                    0.015          True      False
       Medial OA         15        0.908       0.898        0.954       0.956                   -0.009                    0.002         False      False
      Lateral OA         11        0.833       0.833        0.866       0.874                    0.000                    0.009         False       True
           PF OA         21        0.963       0.959        0.965       0.964                   -0.003                   -0.001         False       True
        Effusion         35        0.820       0.831        0.941       0.956                    0.011                    0.015         False       True
       Synovitis         27        0.802       0.798        0.833       0.829                   -0.004                   -0.004         False       True
         Baker's         12        0.855       0.835        0.959       0.964                   -0.020                    0.005         False      False
       Contusion         19        0.852       0.845        0.930       0.941                   -0.007                    0.011          True       True
        Fracture         18        0.901       0.901        0.920       0.915                    0.001                   -0.005          True      False
```

## Run-to-run noise (repeat 1 vs repeat 2)

```
   cell  cells_compared  side_of_0.5_changed  share_changed  mean_abs_prob_diff
T_plain             696                    8         0.0115              0.0096
 T_onto             696                    5         0.0072              0.0106
V_plain             696                   11         0.0158              0.0192
 V_onto             696                    7         0.0101              0.0153
```
