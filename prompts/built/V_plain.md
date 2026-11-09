You are labelling one knee MRI study for a research project. For each of 12 findings, estimate the probability that expert musculoskeletal radiologists, reading this study's MRI images against the definitions below, graded the finding as PRESENT.

## How the expert labels were made

- The experts read the images. They did not use the report.
- Each finding has a written definition with a severity threshold. A finding that is present but below its threshold was graded negative.
- Cases on the fence were graded negative.

## The 12 findings

1. **acl** - ACL tear: A high-grade partial or full-thickness tear of the anterior cruciate ligament, meaning complete discontinuity of the ligament, or more than 50 percent of fibers disrupted, with or without secondary signs such as characteristic pivot-shift bone contusions. Mild signal change, degeneration, or thickening without discontinuity is graded negative.
2. **mcl** - MCL tear: A high-grade partial or complete acute tear of the medial collateral ligament, with disrupted fibers and edema within and adjacent to the ligament. Low-grade sprains and chronic or remote stress changes are graded negative.
3. **medial_meniscus** - Medial meniscus tear: Abnormal signal that definitely contacts the meniscal surface on at least two images, or a morphologic abnormality such as a truncated, diminutive, or displaced fragment, involving the medial meniscus. Intrasubstance degeneration that does not reach the surface is negative.
4. **lateral_meniscus** - Lateral meniscus tear: Same criteria as medial meniscus tear, applied to the lateral meniscus.
5. **medial_oa** - Medial compartment osteoarthritis: A moderate or large area (roughly 1 cm or greater) of high-grade cartilage loss, defined as greater than 50 percent of cartilage thickness, in the medial compartment, with or without underlying subchondral marrow changes.
6. **lateral_oa** - Lateral compartment osteoarthritis: Same criteria as medial compartment osteoarthritis, applied to the lateral compartment.
7. **pf_oa** - Patellofemoral compartment osteoarthritis: Same criteria as medial compartment osteoarthritis, applied to the patellofemoral compartment.
8. **effusion** - Joint effusion: A moderate or large amount of fluid distending the joint.
9. **synovitis** - Synovitis: Inflammation and thickening of the synovial lining of the joint.
10. **bakers** - Baker's cyst: A moderate or large fluid collection in the characteristic location behind the knee.
11. **contusion** - Bone contusion: A bone contusion, seen as bone marrow edema-like signal from impact, without a discrete fracture line.
12. **fracture** - Acute fracture: An acute cortical break or fracture line.

## Material for this study

You have the study's radiology report and a set of pages rendered from the study's MRI images. The report may be in any language.

- Overview pages show every series, 16 slices per page. A series with more than 48 slices is sampled evenly, and the page title says so. Detail pages show the central slices of one fluid-sensitive series per plane at a larger size.
- Each page title gives the series tag (S1, S2, ...), the plane, and whether the series is fluid-sensitive and fat-suppressed. Each tile caption gives the series, plane and slice number, for example "S3 COR FS 12/30".
- Treat the report as a colleague's read that may be incomplete. A finding it reports is a reason to look closely. A finding it does not mention may still be visible. Where the images are clear, decide from the images.
- Look at every page before you decide.
- In each evidence note, cite the series and slices you relied on, for example "S1 SAG FS 14-16".

## How to answer

- Give a probability between 0 and 1 for each finding, not a yes or no. Use values near 0 or 1 only when the evidence is clear.
- Judge each finding against its own definition.
- For each finding, write a one-sentence evidence note first, then the probability.
- Return only the JSON object the response schema asks for.
