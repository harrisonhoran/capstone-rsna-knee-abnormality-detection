"""Step 1: download the gold-58 DICOMs and check that everything is there and readable."""
from collections import Counter
from pathlib import Path

import kagglehub
import pandas as pd
import pydicom
from pydicom.errors import InvalidDicomError

PROJECT = Path(__file__).resolve().parent.parent   # the comp-rsna-knees folder
RAW = PROJECT / "data" / "raw"                     # competition files, read-only
OUT = PROJECT / "data"                             # files this pipeline creates

LABELS = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA",
          "PF OA", "Effusion", "Synovitis", "Baker's", "Contusion", "Fracture"]

# The DICOMs live in the Kaggle download cache, NOT in the project folder.
dicom_root = Path(kagglehub.dataset_download("harrisonhoran/ds-rsna-gold-images-only"))
print("DICOM folder:", dicom_root)

files = [p for p in dicom_root.rglob("*") if p.is_file()]
print("Files:", len(files), "| extensions:", Counter(p.suffix.lower() for p in files).most_common(5))

# Read every header (no pixels) so the script works whatever the folder layout is.
rows, not_dicom = [], 0
for p in files:
    try:
        ds = pydicom.dcmread(p, stop_before_pixels=True)
    except InvalidDicomError:
        not_dicom += 1
        continue
    rows.append({
        "path": str(p),
        "StudyInstanceUID": str(ds.get("StudyInstanceUID", "")),
        "SeriesInstanceUID": str(ds.get("SeriesInstanceUID", "")),
        "InstanceNumber": int(ds.get("InstanceNumber", 0) or 0),
        "Rows": int(ds.get("Rows", 0) or 0),
        "Columns": int(ds.get("Columns", 0) or 0),
        "TransferSyntaxUID": str(ds.file_meta.get("TransferSyntaxUID", "")),
    })

inv = pd.DataFrame(rows)
print("DICOM files:", len(inv), "| not DICOM:", not_dicom)
inv.to_csv(OUT / "inventory.csv", index=False)
print("Saved", OUT / "inventory.csv")

# Compare with the competition tables.
train = pd.read_csv(RAW / "train.csv")
series = pd.read_csv(RAW / "train_series.csv")
gold_ids = set(train.loc[train[LABELS].notna().all(axis=1), "StudyInstanceUID"])
gold_series = set(series.loc[series["StudyInstanceUID"].isin(gold_ids), "SeriesInstanceUID"])
print(f"Gold studies found: {len(gold_ids & set(inv['StudyInstanceUID']))} of {len(gold_ids)}")
print(f"Gold series found:  {len(gold_series & set(inv['SeriesInstanceUID']))} of {len(gold_series)}")
print("Slices per series (min / median / max):",
      inv.groupby("SeriesInstanceUID").size().describe()[["min", "50%", "max"]].tolist())

# Try to decode one image for each compression type.
for ts, group in inv.groupby("TransferSyntaxUID"):
    try:
        shape = pydicom.dcmread(group["path"].iloc[0]).pixel_array.shape
        print(f"Decode OK   {ts}  ({len(group)} files, shape {shape})")
    except Exception as e:
        print(f"Decode FAIL {ts}  ({len(group)} files): {e}")