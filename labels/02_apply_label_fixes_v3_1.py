"""
v3.1 label fixes: train_processed_v2.csv -> train_processed_v3_1.csv  (v2 is only read, never written)
  1) Restore Excel-corrupted report_english ('#NAME?' etc.) from Report.
  2) Baker's, extracted rows only:
       raise to a size-based floor when the report affirms a Baker's/popliteal cyst
       (clause-level negation, so "no effusion or popliteal cysts" stays negative);
       cap at 0.15 when the report names only a mimic (meniscal/parameniscal/ganglion cyst) and no Baker's wording.
     Rule alone scores 0.956 AUC on the 118 gold/silver studies (RadBERT: 0.834).
  3) Hand-reviewed cells from radbert_flag_review.csv (verdict == extractor_fixed) override everything.
Gold/silver/unlabeled rows are never touched.
"""
import pandas as pd
import re

CYST = re.compile(r"(baker'?s?|popliteal)\s*(\((baker'?s?|popliteal|synovial)\)\s*)?(synovial\s+)?cysts?"
                  r"|cysts?\s+(in|of)\s+the\s+popliteal\s+fossa"
                  r"|baker'?s?\s+bursa"
                  r"|synovial\s+cysts?[^.]{0,60}gastrocnemi"
                  r"|(fluid|loculation|collection|distension)[^.,]{0,40}gastrocnemi\w*[- ]semimembranos\w*\s+bursa"
                  r"|gastrocnemi\w*[- ]semimembranos\w*\s+bursa[^.,]{0,30}(fluid|distension|distended)", re.I)
MIMIC = re.compile(r"para ?menisc|ganglion|meniscal cyst|subchondral|intraosseous|tibiofibular", re.I)
NEG = re.compile(r"\b(no|not|without|absence|absent|negative|nor|free of|exclude[sd]?|none|ruled out)\b", re.I)
NEG_AFTER = re.compile(r"cysts?\s*[:\-]?\s*(none|not (seen|identified|present|visualized)|absent|no)\b"
                       r"|without (a |any )?(formed |definite |discrete |true )?cyst", re.I)
SIZE = re.compile(r"\b(mildly|trace|tiny|minimal|minute|millimetric|small|little|thin|low[- ]volume|mild|moderate|moderately|medium|large|larger|big|massive|giant|huge|sizeable|sizable|voluminous)\b", re.I)
FLOOR = {"mildly": 0.8, "millimetric": 0.5, "moderately": 0.9, "larger": 0.9, "trace": 0.5, "tiny": 0.5, "minimal": 0.55, "minute": 0.5, "thin": 0.6, "little": 0.8, "small": 0.85,
         "low-volume": 0.8, "low volume": 0.8, "mild": 0.8, "moderate": 0.9, "medium": 0.9, "large": 0.9,
         "big": 0.9, "massive": 0.9, "giant": 0.9, "huge": 0.9, "sizeable": 0.9, "sizable": 0.9, "voluminous": 0.9, None: 0.8}


def sentences(text):
    # rejoin hard-wrapped lines ("No\nsignificant effusion or popliteal cysts") before splitting
    t = re.sub(r"(?<![.;:!?])[ \t]*\n[ \t]*(?=[a-z(])", " ", str(text))
    return [s for s in re.split(r"(?<=[.;])\s+|\n", t) if s.strip()]


def affirmed_mentions(text):
    """Yield (clause, size_word) for each non-negated, non-mimic Baker's/popliteal cyst mention."""
    for s in sentences(text):
        for clause in re.split(r",|\bbut\b|\bhowever\b|\bwhile\b", s, flags=re.I):
            m = CYST.search(clause)
            if not m or MIMIC.search(clause):
                continue
            before = clause[:m.start()]
            if NEG.search(before) or NEG_AFTER.search(clause[m.start():]):
                continue
            sz = None
            # size word may sit earlier in the same sentence ("tiny, elongated ... Baker's cyst")
            head = s[:s.lower().find(clause.lower().strip()[:20]) + len(before)] if clause.strip() else before
            found = SIZE.findall(head[-80:])
            if not found:  # size stated after the mention ("... bursa is millimetric in thickness")
                found = SIZE.findall(clause[m.end():][:60])
            if found:
                sz = found[-1].lower().replace("low volume", "low-volume")
            yield clause.strip(), sz


def baker_floor(text):
    vals = [FLOOR.get(sz, 0.8) for _, sz in affirmed_mentions(text)]
    return max(vals) if vals else None


MIMIC_ONLY = re.compile(r"meniscal cyst|parameniscal|ganglion", re.I)
BAKER_WORD = re.compile(r"baker|gastrocnemi\w*[- ]semimembranos|popliteal cyst|synovial cyst", re.I)


def is_mimic_only(text):
    """No affirmed Baker's mention, no Baker's vocabulary at all, but a named mimic present."""
    t = str(text)
    return baker_floor(t) is None and not BAKER_WORD.search(t) and bool(MIMIC_ONLY.search(t))


B = "Baker's"
df = pd.read_csv("train_processed_v2.csv")
rev = pd.read_csv("radbert_flag_review.csv")
ext = df.label_type.eq("extracted")
df["label_fix"] = ""

bad = df.report_english.astype(str).str.strip().str.match(r"^(#NAME\?|#VALUE!|#REF!|=)")
df.loc[bad, "report_english"] = df.loc[bad, "Report"]
df.loc[bad, "label_fix"] += "text_restored;"

text = df.report_english.fillna(df.Report).astype(str)
floor = text.map(baker_floor)
up = ext & floor.notna() & (floor > df[B])
df.loc[up, B] = floor[up]
df.loc[up, "label_fix"] += "baker_affirmed;"
mim = ext & text.map(is_mimic_only) & (df[B] > 0.15)
df.loc[mim, B] = 0.15
df.loc[mim, "label_fix"] += "baker_mimic_only;"

pos = {u: i for i, u in df.StudyInstanceUID.items()}
n = 0
for _, r in rev[rev.verdict.eq("extractor_fixed")].iterrows():
    i = pos[r.StudyInstanceUID]
    if df.at[i, "label_type"] == "extracted":
        df.at[i, r.label] = r.new_label
        df.at[i, "label_fix"] += f"review:{r.label};"
        n += 1

print(f"text restored {bad.sum()} | Baker's raised {up.sum()} | Baker's mimic-capped {mim.sum()} | reviewed cells {n}")
df.to_csv("train_processed_v3_1.csv", index=False)
print("wrote train_processed_v3_1.csv")
