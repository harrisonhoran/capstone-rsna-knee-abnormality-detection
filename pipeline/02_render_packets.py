"""Step 2: render each gold study into a packet of PNG pages for the image-reading cells.

Per study:
  - overview pages: every series, 4x4 tiles per page, each tile captioned with its series tag
    and frame number (long series are sampled evenly so the packet stays within the page budget)
  - detail pages: one fluid-sensitive series per plane, 3x3 larger tiles from the central slices

Output: outputs/packets/<StudyInstanceUID>/pNN_*.png + manifest.json, and outputs/packets/packets.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pydicom
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
INVENTORY = PROJECT / "data" / "inventory.csv"
OUT = PROJECT / "outputs" / "packets"

LABELS = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA",
          "PF OA", "Effusion", "Synovitis", "Baker's", "Contusion", "Fracture"]

MAX_PAGES = 42                     # page budget per study
OVERVIEW_CAPS = [48, 32, 16]       # max frames per series on overview pages; lowered if over budget
OV_GRID, OV_TILE = 4, 256          # overview: 4x4 tiles of 256 px
DT_GRID, DT_TILE = 3, 384          # detail: 3x3 tiles of 384 px
DETAIL_FRAMES = 18                 # frames per plane on detail pages (2 pages)
CAPTION_H, HEADER_H, GAP = 18, 30, 4
PLANE_ORDER = {"Sagittal": 0, "Coronal": 1, "Axial": 2}
PLANE_SHORT = {"Sagittal": "SAG", "Coronal": "COR", "Axial": "AX"}


def font(size):
    try:
        return ImageFont.load_default(size=size)       # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def load_series(paths):
    """Read one series: slices sorted along the scan direction, windowed to 8 bit."""
    slices = []
    for p in paths:
        ds = pydicom.dcmread(p)
        img = ds.pixel_array.astype(np.float32)
        img = img * float(getattr(ds, "RescaleSlope", 1) or 1) + float(getattr(ds, "RescaleIntercept", 0) or 0)
        ipp = getattr(ds, "ImagePositionPatient", None)
        iop = getattr(ds, "ImageOrientationPatient", None)
        if ipp is not None and iop is not None:
            normal = np.cross(np.array(iop[:3], float), np.array(iop[3:], float))
            pos = float(np.dot(normal, np.array(ipp, float)))
        else:
            pos = float(getattr(ds, "InstanceNumber", 0) or 0)
        spacing = [float(x) for x in getattr(ds, "PixelSpacing", [1.0, 1.0])]
        slices.append((pos, img, spacing))
    slices.sort(key=lambda s: s[0])
    values = np.concatenate([s[1].ravel() for s in slices])
    lo, hi = np.percentile(values, [0.5, 99.5])
    scale = 255.0 / max(hi - lo, 1e-6)
    frames = [np.clip((img - lo) * scale, 0, 255).astype(np.uint8) for _, img, _ in slices]
    return frames, slices[0][2]


def tile_image(frame, spacing, size):
    """Fit a slice into a square tile, keeping true proportions (pixel spacing)."""
    h_mm, w_mm = frame.shape[0] * spacing[0], frame.shape[1] * spacing[1]
    k = size / max(h_mm, w_mm)
    w, h = max(1, round(w_mm * k)), max(1, round(h_mm * k))
    im = Image.fromarray(frame).resize((w, h), Image.LANCZOS)
    tile = Image.new("L", (size, size), 0)
    tile.paste(im, ((size - w) // 2, (size - h) // 2))
    return tile


def make_page(title, tiles, grid, tile_px):
    """tiles = list of (tile image, caption). Returns one page image."""
    rows = -(-len(tiles) // grid)                      # rows actually used
    cell_w, cell_h = tile_px + GAP, tile_px + CAPTION_H + GAP
    page = Image.new("L", (grid * cell_w + GAP, HEADER_H + rows * cell_h + GAP), 0)
    draw = ImageDraw.Draw(page)
    draw.text((GAP + 2, 6), title, fill=255, font=font(16))
    for i, (tile, caption) in enumerate(tiles):
        x = GAP + (i % grid) * cell_w
        y = HEADER_H + (i // grid) * cell_h
        page.paste(tile, (x, y))
        draw.text((x + 2, y + tile_px + 2), caption, fill=220, font=font(13))
    return page


def pick(n, k, lo=0.0, hi=1.0):
    """k evenly spaced slice indices between fractions lo and hi of a series of n slices."""
    a, b = int(round(lo * (n - 1))), int(round(hi * (n - 1)))
    if b - a + 1 <= k:
        return list(range(a, b + 1))
    return sorted(set(int(round(x)) for x in np.linspace(a, b, k)))


def describe(row):
    parts = [row["Anatomical_Plane"],
             "fluid-sensitive" if row["Fluid_Sensitive"] == 1 else "not fluid-sensitive",
             "fat-suppressed" if row["Fat_Suppression"] == 1 else "no fat suppression"]
    return ", ".join(parts)


def render_study(study_uid, series_rows, inv):
    # Order series: sagittal, coronal, axial; fluid-sensitive first within a plane.
    series_rows = series_rows.assign(_p=series_rows["Anatomical_Plane"].map(PLANE_ORDER).fillna(9))
    series_rows = series_rows.sort_values(["_p", "Fluid_Sensitive", "Fat_Suppression", "SeriesInstanceUID"],
                                          ascending=[True, False, False, True]).reset_index(drop=True)
    loaded = []
    for i, row in series_rows.iterrows():
        paths = inv.loc[inv["SeriesInstanceUID"] == row["SeriesInstanceUID"], "path"].tolist()
        if not paths:
            continue
        frames, spacing = load_series(paths)
        tag = f"S{len(loaded) + 1}"
        short = f"{tag} {PLANE_SHORT.get(row['Anatomical_Plane'], '?')}" + (" FS" if row["Fat_Suppression"] == 1 else "")
        loaded.append({"tag": tag, "short": short, "row": row, "frames": frames, "spacing": spacing})

    # Detail series: per plane, the first fluid-sensitive series (fat-suppressed preferred by the sort).
    detail = []
    for plane in PLANE_ORDER:
        cands = [s for s in loaded if s["row"]["Anatomical_Plane"] == plane and s["row"]["Fluid_Sensitive"] == 1]
        if cands:
            detail.append(cands[0])
    detail_pages = sum(-(-len(pick(len(s["frames"]), DETAIL_FRAMES, 0.1, 0.9)) // DT_GRID ** 2) for s in detail)

    # Choose the largest overview cap that keeps the packet within the page budget.
    for cap in OVERVIEW_CAPS:
        ov_pages = sum(-(-len(pick(len(s["frames"]), cap)) // OV_GRID ** 2) for s in loaded)
        if ov_pages + detail_pages <= MAX_PAGES:
            break

    out_dir = OUT / study_uid
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("p*.png"):
        old.unlink()
    pages = []

    def save(page, kind, s, idx):
        name = f"p{len(pages) + 1:02d}_{kind}_{s['tag']}.png"
        page.save(out_dir / name)
        pages.append({"file": name, "kind": kind, "series": s["tag"], "frames": [i + 1 for i in idx]})

    for s in loaded:                                                    # overview pages
        idx, n = pick(len(s["frames"]), cap), len(s["frames"])
        for start in range(0, len(idx), OV_GRID ** 2):
            chunk = idx[start:start + OV_GRID ** 2]
            tiles = [(tile_image(s["frames"][i], s["spacing"], OV_TILE), f"{s['short']} {i + 1}/{n}") for i in chunk]
            sampled = "" if len(idx) == n else f" (every ~{n / len(idx):.1f}th frame shown)"
            title = f"OVERVIEW  {s['tag']}: {describe(s['row'])}  frames {chunk[0] + 1}-{chunk[-1] + 1} of {n}{sampled}"
            save(make_page(title, tiles, OV_GRID, OV_TILE), "overview", s, chunk)

    for s in detail:                                                    # detail pages
        idx, n = pick(len(s["frames"]), DETAIL_FRAMES, 0.1, 0.9), len(s["frames"])
        for start in range(0, len(idx), DT_GRID ** 2):
            chunk = idx[start:start + DT_GRID ** 2]
            tiles = [(tile_image(s["frames"][i], s["spacing"], DT_TILE), f"{s['short']} {i + 1}/{n}") for i in chunk]
            title = f"DETAIL  {s['tag']}: {describe(s['row'])}  frames {chunk[0] + 1}-{chunk[-1] + 1} of {n}"
            save(make_page(title, tiles, DT_GRID, DT_TILE), "detail", s, chunk)

    manifest = {
        "StudyInstanceUID": study_uid,
        "overview_cap": cap,
        "series": [{"tag": s["tag"], "SeriesInstanceUID": s["row"]["SeriesInstanceUID"],
                    "description": describe(s["row"]), "slices": len(s["frames"])} for s in loaded],
        "pages": pages,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return {"StudyInstanceUID": study_uid, "series": len(loaded), "pages": len(pages),
            "overview_cap": cap, "slices": sum(len(s["frames"]) for s in loaded)}


def main():
    inv = pd.read_csv(INVENTORY)
    train = pd.read_csv(RAW / "train.csv")
    series = pd.read_csv(RAW / "train_series.csv")
    gold_ids = train.loc[train[LABELS].notna().all(axis=1), "StudyInstanceUID"].tolist()
    summary = []
    for n, uid in enumerate(gold_ids, 1):
        info = render_study(uid, series[series["StudyInstanceUID"] == uid], inv)
        summary.append(info)
        print(f"[{n}/{len(gold_ids)}] {uid[-12:]}  series {info['series']}  pages {info['pages']}  cap {info['overview_cap']}")
    df = pd.DataFrame(summary)
    df.to_csv(OUT / "packets.csv", index=False)
    print(f"\nStudies: {len(df)} | pages per study min/median/max: "
          f"{df['pages'].min()} / {df['pages'].median():.0f} / {df['pages'].max()} | total pages: {df['pages'].sum()}")
    print("Saved", OUT / "packets.csv")


if __name__ == "__main__":
    main()
