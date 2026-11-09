"""Step 3: build the four cell prompts and the two output schemas, and freeze them with md5 hashes.

Cells (2x2):
    T_plain  report only,     no ontology
    T_onto   report only,     ontology
    V_plain  report + images, no ontology
    V_onto   report + images, ontology

Everything except the ontology section and the structured fields is identical between plain and onto.
Inputs:  prompts/templates/*.md
Outputs: prompts/built/<cell>.md, prompts/built/schema_plain.json, prompts/built/schema_onto.json,
         prompts/built/manifest.json (md5 + word counts; record it in the pre-registration)
"""
import hashlib
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT / "prompts" / "templates"
BUILT = PROJECT / "prompts" / "built"

FINDINGS = ["acl", "mcl", "medial_meniscus", "lateral_meniscus", "medial_oa", "lateral_oa",
            "pf_oa", "effusion", "synovitis", "bakers", "contusion", "fracture"]

# Competition column names, used later to join model output with the gold labels.
COLUMN_OF = {"acl": "ACL", "mcl": "MCL", "medial_meniscus": "Medial Meniscus",
             "lateral_meniscus": "Lateral Meniscus", "medial_oa": "Medial OA", "lateral_oa": "Lateral OA",
             "pf_oa": "PF OA", "effusion": "Effusion", "synovitis": "Synovitis", "bakers": "Baker's",
             "contusion": "Contusion", "fracture": "Fracture"}

ORDER_PLAIN = "For each finding, write a one-sentence evidence note first, then the probability."
ORDER_ONTO = ("First fill in the structured_findings fields using the reference knowledge, then for each "
              "finding write a one-sentence evidence note, then the probability.")

ONTOLOGY_HEADER = """
## Reference knowledge

The reference below summarises published knowledge about these knee MRI findings: imaging signs, grading scales, detection cues, and mimics and pitfalls. Use it when you assess the study. Where it differs from the definitions above, the definitions decide.

"""


def read(name):
    return (TEMPLATES / name).read_text(encoding="utf-8").strip()


def strip_comments(text):
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.S).strip()


def enum(*values):
    return {"type": "string", "enum": list(values)}


def finding_block():
    one = {"type": "object", "additionalProperties": False,
           "properties": {"evidence": {"type": "string"},
                          "probability": {"type": "number"}},
           "required": ["evidence", "probability"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {f: one for f in FINDINGS}, "required": FINDINGS}


def structured_block():
    grade_icrs = enum("0", "1", "2", "3", "4", "unassessable")
    area = enum("no_high_grade_loss", "under_1cm", "about_1cm_or_more", "unassessable")
    men_signal = enum("0", "1", "2", "3", "unassessable")
    men_morph = enum("normal", "truncated_or_blunted", "displaced_fragment_or_bucket_handle",
                     "root_tear_or_extrusion", "macerated", "unassessable")
    props = {
        "acl_status": enum("intact", "signal_change_or_mucoid_without_discontinuity", "low_grade_partial_tear",
                           "high_grade_partial_tear", "complete_tear", "reconstructed", "unassessable"),
        "mcl_status": enum("normal", "grade_1_sprain", "high_grade_partial_tear", "complete_tear",
                           "chronic_changes_only", "unassessable"),
        "medial_meniscus_signal_grade": men_signal,
        "medial_meniscus_morphology": men_morph,
        "lateral_meniscus_signal_grade": men_signal,
        "lateral_meniscus_morphology": men_morph,
        "medial_worst_icrs": grade_icrs, "medial_high_grade_area": area,
        "lateral_worst_icrs": grade_icrs, "lateral_high_grade_area": area,
        "patellofemoral_worst_icrs": grade_icrs, "patellofemoral_high_grade_area": area,
        "effusion_grade": enum("none", "trace", "small", "moderate", "large", "unassessable"),
        "synovial_thickening": enum("absent", "possible", "present", "unassessable"),
        "bakers_cyst_size": enum("none", "small", "moderate", "large", "unassessable"),
        "bakers_cyst_neck_seen": enum("yes", "no", "not_applicable"),
        "contusion_sites": {"type": "array", "items": enum(
            "lateral_femoral_condyle", "medial_femoral_condyle", "lateral_tibial_plateau",
            "medial_tibial_plateau", "patella", "anterior_tibia", "anterior_femur", "other")},
        "fracture_signs": {"type": "array", "items": enum(
            "fracture_line_or_cortical_break", "lipohaemarthrosis", "segond_avulsion", "tibial_spine_avulsion",
            "other_avulsion", "osteochondral_fragment", "subchondral_impaction")},
        "mimic_flags": {"type": "array", "items": enum(
            "acl_mucoid_degeneration", "meniscal_grade_2_signal", "meniscal_pseudotear_ligament_or_flounce",
            "chronic_mcl_changes", "bipartite_patella", "intraosseous_vessel_or_physis",
            "normal_trochlear_thinning")},
    }
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def schema(with_structured):
    props, req = {}, []
    if with_structured:                              # listed first so it is filled before the probabilities
        props["structured_findings"] = structured_block()
        req.append("structured_findings")
    props["findings"] = finding_block()
    req.append("findings")
    return {"type": "object", "additionalProperties": False, "properties": props, "required": req}


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def main():
    BUILT.mkdir(parents=True, exist_ok=True)
    base = read("instructions.md").replace("{DEFINITIONS}", read("definitions.md"))
    knowledge = strip_comments(read("ontology_knowledge.md"))
    material = {"T": read("material_report.md"), "V": read("material_images.md")}

    manifest = {"cells": {}, "schemas": {}, "columns": COLUMN_OF}
    for mod in ["T", "V"]:
        for arm in ["plain", "onto"]:
            text = (base.replace("{MATERIAL}", material[mod])
                        .replace("{ONTOLOGY}", ONTOLOGY_HEADER + knowledge + "\n" if arm == "onto" else "")
                        .replace("{ORDER}", ORDER_ONTO if arm == "onto" else ORDER_PLAIN))
            assert "{" not in text, f"unfilled placeholder in {mod}_{arm}"
            cell = f"{mod}_{arm}"
            (BUILT / f"{cell}.md").write_text(text + "\n", encoding="utf-8")
            manifest["cells"][cell] = {"file": f"{cell}.md", "md5": md5(text + "\n"),
                                       "words": len(text.split()), "schema": f"schema_{arm}.json"}
    for arm in ["plain", "onto"]:
        s = json.dumps(schema(arm == "onto"), indent=2)
        (BUILT / f"schema_{arm}.json").write_text(s + "\n", encoding="utf-8")
        manifest["schemas"][f"schema_{arm}.json"] = md5(s + "\n")

    (BUILT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for cell, info in manifest["cells"].items():
        print(f"{cell:8s} {info['words']:5d} words  md5 {info['md5']}")
    for name, h in manifest["schemas"].items():
        print(f"{name:18s} md5 {h}")
    print("Saved", BUILT)


if __name__ == "__main__":
    main()
