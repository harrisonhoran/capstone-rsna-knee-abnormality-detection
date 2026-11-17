<!--
Ontology knowledge for the ontology arm.
Included: imaging signs, grading scales, detection cues, mimics and pitfalls.
Excluded on purpose: competition_label_prior bands, calibration_notes, co-occurrence and etiology percentages,
epidemiology, management and treatment. Each section names its source fields.
HTML comments are removed by 03_build_prompts.py and never reach the model.
-->
### ACL tear
<!-- source: https://msk-radiology.com/knee/knee-anterior-cruciate.html
labels.acl_tear.primary_mri_signs_essential_criteria, secondary_mri_signs, detection_cues, mimics_and_pitfalls, common_pitfalls, differential_diagnosis.abnormal_signal_without_tear -->
- Primary signs: non-visualisation of ACL fibres; complete fibre discontinuity; abnormal orientation (not parallel to the Blumensaat line); mass-like appearance with oedema or haemorrhage.
- Secondary signs: lateral femoral notch (sulcus) deeper than about 1.5-2 mm; contusions of the lateral femoral condyle and posterior lateral tibial plateau; Segond fracture; tibial spine avulsion; anterior tibial translation over 7 mm; PCL buckling (angle under 105 degrees).
- Look at all three planes: empty notch on axial images, ACL fibres on sagittal, Segond fracture on coronal.
- Mimics: mucoid degeneration (thickened "celery stalk" ACL with intact fibres); ACL ganglion cyst; synovitis or synovial hypertrophy that looks like an intact ACL; ligamentum mucosum that looks like an intact ACL on sagittal images; magic angle artefact; volume averaging; normal high signal in children.

### MCL tear
<!-- source: labels.mcl_posteromedial_corner_injury.grading, key_imaging_findings_table, reporting.common_pitfalls, reporting.imaging_pearls -->
- Grade I sprain: oedema around the ligament with intact fibres and normal thickness.
- Higher-grade injury: fibre disruption with thickening and increased signal of the superficial MCL; check the femoral attachment, the mid-substance and the tibial attachment.
- Chronic changes: an "onion skin" appearance, or a Pellegrini-Stieda lesion (calcification near the femoral attachment), without acute oedema.
- Check the posterior coronal slices for the posterior oblique ligament.

### Meniscal tears (medial and lateral)
<!-- source: labels.meniscal_tear_simple.diagnostic_rule, grading_table, detection_cues, mimics_and_pitfalls, common_pitfalls, radial_tears.mri_signs; labels.meniscal_tear_complex.detection_cues, bucket_handle_tears.classic_pattern_mri_findings, fragment_search_rules, mimics_and_pitfalls -->
- Signal grades: 0 normal low signal; 1 punctate intrameniscal signal; 2 linear signal that does not reach the surface (degeneration, not a tear); 3 signal that reaches an articular surface (tear).
- Two-slice touch rule: diagnose a tear only when surface-reaching signal is seen on at least two consecutive images.
- Planes: vertical tears are best seen on coronal images, horizontal tears on sagittal images, radial tears on coronal and axial images.
- Morphologic signs: truncated triangle or "ghost" meniscus; blunted free edge; fewer than two "bow ties" on consecutive sagittal images; double PCL sign or a fragment in the notch (displaced bucket-handle tear); a size difference of 50% or more between the anterior and posterior horn (flipped fragment); root tear with an empty footprint or meniscal extrusion over 3 mm.
- Search for displaced fragments in the notch, the gutters, the recesses and beneath the tibial plateaus.
- Mimics: meniscal flounce (wavy but intact); transverse meniscal ligament (anterior horn pseudotear); meniscofemoral ligaments (posterior horn pseudotear); popliteus tendon and popliteomeniscal fascicles at the lateral meniscus; magic angle artefact; chondrocalcinosis; prior partial meniscectomy.

### Cartilage loss (medial, lateral and patellofemoral osteoarthritis)
<!-- source: meta.shared_classification_tables.icrs_cartilage_grading_summary (mri column); labels.cartilage_loss_patterns.detection_cues, mimics_and_pitfalls; labels.icrs_cartilage_classification.classification_checkpoints, location_specific_considerations.patellofemoral, mimics_and_pitfalls -->
- ICRS grades on MRI: 0 uniform thickness and signal; 1 signal heterogeneity with an intact surface; 2 defect under 50% of cartilage thickness; 3 defect over 50% of thickness, subchondral plate intact; 4 full-thickness loss down to bone.
- Grade each compartment separately: medial tibiofemoral, lateral tibiofemoral, patellofemoral (patella and trochlea). Estimate both the depth and the area of the worst defect.
- Supporting signs: subchondral marrow changes, subchondral cysts, osteophytes, meniscal extrusion. These support but do not replace a cartilage defect.
- Fluid-sensitive sequences show defects best; look for fissuring and for fluid undermining the cartilage (delamination). The patellofemoral joint is best assessed on axial images.
- Mimics: normal thinning of the central trochlea and the patellar apex (trochlear pseudodefect); magic angle artefact at the patella; partial volume on thick slices overestimates depth; chemical shift and motion artefact.

### Joint effusion
<!-- source: competition_labels.joint_effusion.supplementary_general_knowledge.grading_convention_commonly_used; labels.synovitis.effusion_vs_synovitis_distinction.key_facts, conventional_unenhanced_mri_semiquantitative_scoring_systems -->
- Grading convention: trace is physiological and seen in most normal knees; small is mild distension, usually within normal range; moderate is clearly abnormal distension; large is marked distension and may be tense.
- Fluid is assessed by distension of the joint and its recesses, especially the suprapatellar recess. Validated MRI scores (WORMS, MOAKS) grade effusion-synovitis on a 4-point scale by the maximal distension of the synovial cavity.
- A fat-fluid level in a joint recess (lipohaemarthrosis) indicates an intra-articular fracture.

### Synovitis
<!-- source: labels.synovitis.pathophysiology.definition, effusion_vs_synovitis_distinction.core_problem, effusion_vs_synovitis_distinction.key_facts, common_pitfalls -->
- Synovitis is inflammation of the synovial membrane: lining hyperplasia, subintimal fibrosis and increased vascularity.
- On non-contrast MRI, fluid and inflamed synovium have similar signal (both bright on fluid-sensitive sequences), so signal alone does not separate them. Look for morphology: synovial thickening, proliferation or frond-like projections, as opposed to uniform simple fluid distension.
- Effusion and synovitis are related but not equivalent: either can be present without the other.
- Hoffa fat-pad hyperintensity ("Hoffa synovitis") is a proposed but nonspecific surrogate.

### Baker's cyst
<!-- source: labels.baker_popliteal_cyst.definition, imaging.mri, imaging.ultrasound.diagnostic_criterion, differential_diagnosis -->
- A fluid-filled, synovial-lined collection in the popliteal fossa that communicates with the joint between the medial head of the gastrocnemius and the semimembranosus tendon. Usually at or below the joint line. Low signal on T1, high signal on T2.
- The "neck" between these two tendons, extending toward the joint, is the discriminating feature; a posterior fluid collection without it is only suggestive.
- May contain septations or debris; may rupture or dissect, usually inferomedially.
- Mimics, none of which has that neck: large parameniscal cyst, ganglion cyst, liquefied haematoma, MCL or pes anserinus bursitis, popliteal artery aneurysm, synovial sarcoma.

### Bone contusion
<!-- source: labels.contusion.definition, mri_diagnostic_criterion, mri_signal_characteristics_consolidated.note, common_pitfalls, osteochondral_lesion_overlap.relevance_to_competition_labeling, injury_mechanism_patterns.patterns[].contusion_location -->
- Post-traumatic marrow change (haemorrhage, oedema, microtrabecular injury) without a discrete cortical fracture line.
- MRI appearance: geographic, non-linear, ill-defined marrow signal that is low on T1 and high on T2 or fat-suppressed fluid-sensitive images.
- Pitfalls: a linear bright line, especially in the epiphysis, is usually a normal intraosseous vessel; normal physeal signal in skeletally immature knees; subtle lesions at the posterior medial femoral condyle are easy to miss.
- The marrow signal of a contusion and of an osteochondral fracture can look identical; what separates them is whether a discrete fracture line or cortical or cartilage defect is also present.
- Typical contusion locations by mechanism: pivot shift, mid lateral femoral condyle and posterolateral tibial plateau (sometimes the posterior lip of the medial tibial plateau); dashboard, anterior tibia; hyperextension, "kissing" anterior tibia and anterior femoral condyle; clip (valgus), lateral femoral condyle with a smaller medial femoral condyle focus; lateral patellar dislocation, anterolateral lateral femoral condyle and inferomedial patella.

### Acute fracture
<!-- source: labels.acute_fracture.core_diagnostic_signs.cortical_break_direct_signs, core_diagnostic_signs.lipohemarthrosis.significance, tibial_plateau_fracture.why_subtle, segond_fracture.description, avulsion_fractures_ligament_markers.key_sites, patellar_fractures.types, patellar_fractures.mimic_bipartite_patella -->
- Direct signs: loss of the sharp cortical margin; a fracture line; a step-off at an articular surface; impaction of subchondral bone, which can occur without an obvious line.
- A fat-fluid level in a joint recess (lipohaemarthrosis) indicates an intra-articular fracture even when the line itself is not seen.
- Tibial plateau fractures can be subtle: the fracture plane is often oblique to the imaging plane and depression may be minimal.
- Avulsion fractures are fractures: Segond fracture (small cortical fragment from the lateral tibial plateau, 3-5 mm below the joint line); tibial spine (ACL insertion); posterior tibia (PCL insertion); fibular head (LCL and biceps femoris); Gerdy's tubercle (iliotibial band); medial and lateral femoral condyles (MCL and LCL origins).
- Patellar fractures: transverse fractures are obvious; vertical and osteochondral fractures are subtle and need axial images.
- Mimic: bipartite patella, usually superolateral, with smooth corticated margins, unlike the sharp non-corticated margins of an acute fracture.
