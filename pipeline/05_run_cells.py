"""Step 5: run the 2x2 cells through the OpenAI API and save every raw response.

Usage
  python pipeline/05_run_cells.py --effort high --limit 5        # pilot: 5 studies, all 4 cells, repeat 1
  python pipeline/05_run_cells.py --effort high --repeat 1       # full run, repeat 1 (58 studies x 4 cells)
  python pipeline/05_run_cells.py --effort high --repeat 2       # full run, repeat 2
  python pipeline/05_run_cells.py --effort high --cells T_plain,T_onto --repeat 1   # only some cells

Each run type and reasoning effort gets its own folder, so pilots and full runs never mix:
  outputs/runs/pilot_<effort>/   any run with --limit
  outputs/runs/full_<effort>/    full runs

Resumable: a study/cell/repeat whose response file already exists is skipped, so a crashed or
interrupted run continues where it stopped. Delete a response file to redo that call.

Needs OPENAI_API_KEY in a .env file at the project root (never commit .env).
Outputs, inside the run folder
  raw/<cell>_r<k>/<StudyInstanceUID>.json   full response + usage + prompt md5 (the audit trail)
  <cell>_r<k>.csv                            12 probabilities per study (input to 04_score.py)
  <cell>_r<k>_structured.csv                 ontology cells only: the structured fields
  usage_summary.csv                          tokens and cost per cell and repeat
"""
import argparse
import base64
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
BUILT = PROJECT / "prompts" / "built"
PACKETS = PROJECT / "outputs" / "packets"
RUNS = PROJECT / "outputs" / "runs"     # replaced in main() by outputs/runs/<pilot|full>_<effort>

MODEL = "gpt-6.1-sol"
REASONING_EFFORT = "high"                # set by --effort; the same for every cell in a run
PRICE_PER_M = {"input": 1.00, "cached_input": 0.05, "output": 5.00}   # GPT-6.1 Sol, standard tier, USD
LABELS = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA",
          "PF OA", "Effusion", "Synovitis", "Baker's", "Contusion", "Fracture"]
KEYS = ["acl", "mcl", "medial_meniscus", "lateral_meniscus", "medial_oa", "lateral_oa",
        "pf_oa", "effusion", "synovitis", "bakers", "contusion", "fracture"]


def gold_studies():
    t = pd.read_csv(RAW / "train.csv")
    g = t.loc[t[LABELS].notna().all(axis=1), ["StudyInstanceUID", "Report"]]
    return g.sort_values("StudyInstanceUID").reset_index(drop=True)


def page_as_jpeg_data_url(path):
    """PNG page -> JPEG data URL. Token cost depends on pixel size, not file size; JPEG keeps uploads small."""
    buf = io.BytesIO()
    Image.open(path).convert("L").save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def user_content(study_uid, report, with_images):
    content = [{"type": "input_text", "text": "Radiology report:\n\n" + str(report).strip()}]
    if with_images:
        manifest = json.loads((PACKETS / study_uid / "manifest.json").read_text())
        series = "\n".join(f"{s['tag']}: {s['description']}, {s['slices']} slices" for s in manifest["series"])
        content.append({"type": "input_text",
                        "text": f"Series in this study:\n{series}\n\nThe {len(manifest['pages'])} image pages follow, in order."})
        for i, page in enumerate(manifest["pages"], 1):
            content.append({"type": "input_text", "text": f"Page {i}: {page['file']}"})
            content.append({"type": "input_image", "detail": "high",
                            "image_url": page_as_jpeg_data_url(PACKETS / study_uid / page["file"])})
    return content


def validate(parsed, with_structured):
    f = parsed["findings"]
    for k in KEYS:
        p = f[k]["probability"]
        if not (isinstance(p, (int, float)) and 0 <= p <= 1):
            raise ValueError(f"{k}: probability {p!r} is not between 0 and 1")
    if with_structured and "structured_findings" not in parsed:
        raise ValueError("structured_findings missing")


def call_once(client, cell, repeat, study_uid, report, manifest):
    out_path = RUNS / "raw" / f"{cell}_r{repeat}" / f"{study_uid}.json"
    if out_path.exists():
        return "skipped"
    info = manifest["cells"][cell]
    instructions = (BUILT / info["file"]).read_text(encoding="utf-8")
    schema = json.loads((BUILT / info["schema"]).read_text())
    with_images, with_structured = cell.startswith("V"), cell.endswith("onto")

    last_error = None
    for attempt in range(4):
        try:
            t0 = time.time()
            resp = client.responses.create(
                model=MODEL,
                instructions=instructions,
                input=[{"role": "user", "content": user_content(study_uid, report, with_images)}],
                reasoning={"effort": REASONING_EFFORT},
                text={"format": {"type": "json_schema", "name": "knee_labels", "schema": schema, "strict": True}},
            )
            parsed = json.loads(resp.output_text)
            validate(parsed, with_structured)
            u = resp.usage
            record = {
                "StudyInstanceUID": study_uid, "cell": cell, "repeat": repeat, "model": MODEL,
                "reasoning_effort": REASONING_EFFORT, "prompt_md5": info["md5"],
                "schema_md5": manifest["schemas"][info["schema"]],
                "time_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1),
                "attempt": attempt + 1, "response_id": resp.id,
                "usage": {"input_tokens": u.input_tokens,
                          "cached_tokens": getattr(u.input_tokens_details, "cached_tokens", 0) or 0,
                          "output_tokens": u.output_tokens,
                          "reasoning_tokens": getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0},
                "output": parsed,
            }
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(record, indent=2))
            return "ok"
        except Exception as e:                      # rate limits, timeouts, invalid output: back off and retry
            last_error = e
            time.sleep(5 * 2 ** attempt)
    return f"FAILED after 4 attempts: {last_error}"


def cost(usage):
    uncached = usage["input_tokens"] - usage["cached_tokens"]
    return (uncached * PRICE_PER_M["input"] + usage["cached_tokens"] * PRICE_PER_M["cached_input"]
            + usage["output_tokens"] * PRICE_PER_M["output"]) / 1e6


def compile_run(cell, repeat):
    """Gather the raw responses of one cell/repeat into the CSVs the scorer reads."""
    folder = RUNS / "raw" / f"{cell}_r{repeat}"
    rows, structured, usage = [], [], []
    for f in sorted(folder.glob("*.json")):
        r = json.loads(f.read_text())
        out = r["output"]
        rows.append({"StudyInstanceUID": r["StudyInstanceUID"],
                     **{lab: out["findings"][k]["probability"] for lab, k in zip(LABELS, KEYS)}})
        if "structured_findings" in out:
            structured.append({"StudyInstanceUID": r["StudyInstanceUID"],
                               **{k: (";".join(v) if isinstance(v, list) else v)
                                  for k, v in out["structured_findings"].items()}})
        usage.append({**r["usage"], "cost_usd": cost(r["usage"]), "seconds": r["seconds"]})
    if not rows:
        return None
    pd.DataFrame(rows).to_csv(RUNS / f"{cell}_r{repeat}.csv", index=False)
    if structured:
        pd.DataFrame(structured).to_csv(RUNS / f"{cell}_r{repeat}_structured.csv", index=False)
    u = pd.DataFrame(usage)
    return {"cell": cell, "repeat": repeat, "studies": len(u),
            "mean_input_tokens": round(u.input_tokens.mean()), "mean_output_tokens": round(u.output_tokens.mean()),
            "mean_reasoning_tokens": round(u.reasoning_tokens.mean()), "mean_cost_usd": round(u.cost_usd.mean(), 4),
            "total_cost_usd": round(u.cost_usd.sum(), 2), "mean_seconds": round(u.seconds.mean(), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="T_plain,T_onto,V_plain,V_onto")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None, help="only the first N studies (pilot)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--effort", default="high", choices=["none", "low", "medium", "high", "xhigh", "max"])
    args = ap.parse_args()

    global RUNS, REASONING_EFFORT
    REASONING_EFFORT = args.effort
    RUNS = PROJECT / "outputs" / "runs" / f"{'pilot' if args.limit else 'full'}_{args.effort}"
    RUNS.mkdir(parents=True, exist_ok=True)
    print("Run folder:", RUNS)

    load_dotenv(PROJECT / ".env")
    client = OpenAI()
    manifest = json.loads((BUILT / "manifest.json").read_text())
    cells = args.cells.split(",")
    studies = gold_studies()
    if args.limit:
        studies = studies.head(args.limit)

    jobs = [(c, s.StudyInstanceUID, s.Report) for c in cells for s in studies.itertuples()]
    print(f"{len(jobs)} calls: {len(studies)} studies x {len(cells)} cells, repeat {args.repeat}, "
          f"{MODEL} effort={REASONING_EFFORT}")
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(call_once, client, c, args.repeat, uid, rep, manifest): (c, uid)
                   for c, uid, rep in jobs}
        for n, fut in enumerate(as_completed(futures), 1):
            c, uid = futures[fut]
            status = fut.result()
            print(f"[{n}/{len(jobs)}] {c:8s} {uid[-12:]}  {status}")
            if status.startswith("FAILED"):
                failures.append((c, uid, status))

    summary = [s for c in cells if (s := compile_run(c, args.repeat))]
    df = pd.DataFrame(summary)
    print("\n" + df.to_string(index=False))
    summary_path = RUNS / "usage_summary.csv"
    if summary_path.exists():
        old = pd.read_csv(summary_path)
        old = old[~(old.cell.isin(df.cell) & (old.repeat == args.repeat))]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(summary_path, index=False)
    if failures:
        print(f"\n{len(failures)} calls failed; rerun the same command to retry them.")


if __name__ == "__main__":
    main()
