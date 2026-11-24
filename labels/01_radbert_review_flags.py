"""
RadBERT label cleaning + text embeddings for RSNA knee.
Run on a GPU box (Kaggle notebook with internet ON, or local).
  pip install transformers torch scikit-learn pandas
Inputs : train_processed_v2.csv (run from data/labels/)
Outputs: radbert_soft_labels.csv   (OOF probs for every study, incl. the 59 unlabeled)
         radbert_label_flags.csv   (studies where RadBERT strongly disagrees with the extracted label)
         radbert_emb.npy + radbert_emb_ids.csv  (768-d report embeddings from the fine-tuned model)
"""
import numpy as np, pandas as pd, torch, torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup

MODEL = "zzxslp/RadBERT-RoBERTa-4m"
LABELS = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA",
          "PF OA", "Effusion", "Synovitis", "Baker's", "Contusion", "Fracture"]
MAX_LEN, HEAD = 512, 128          # head+tail truncation keeps the Impression at the end
EPOCHS, BS, LR, FOLDS = 4, 16, 2e-5, 5
dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)

df = pd.read_csv("train_processed_v2.csv")  # run from data/labels/
df["text"] = df["report_english"].fillna(df["Report"]).fillna("").astype(str)
lab = df[df.label_type != "unlabeled"].reset_index(drop=True)
unl = df[df.label_type == "unlabeled"].reset_index(drop=True)
tok = AutoTokenizer.from_pretrained(MODEL)


def encode(text):
    ids = tok(text, add_special_tokens=False, verbose=False)["input_ids"]
    body = MAX_LEN - 2
    if len(ids) > body:                       # head + tail
        ids = ids[:HEAD] + ids[-(body - HEAD):]
    ids = [tok.cls_token_id] + ids + [tok.sep_token_id]
    return ids


class DS(Dataset):
    def __init__(self, d, with_y=True):
        self.ids = [encode(t) for t in d.text]
        self.y = d[LABELS].values.astype("float32") if with_y else None
    def __len__(self): return len(self.ids)
    def __getitem__(self, i):
        return self.ids[i], (self.y[i] if self.y is not None else np.zeros(len(LABELS), "float32"))


def collate(b):
    L = max(len(x) for x, _ in b)
    ids = torch.full((len(b), L), tok.pad_token_id)
    att = torch.zeros((len(b), L), dtype=torch.long)
    for i, (x, _) in enumerate(b):
        ids[i, :len(x)] = torch.tensor(x); att[i, :len(x)] = 1
    return ids, att, torch.tensor(np.stack([y for _, y in b]))


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = AutoModel.from_pretrained(MODEL)
        self.head = nn.Linear(self.enc.config.hidden_size, len(LABELS))
    def embed(self, ids, att):                # mean pooling
        h = self.enc(input_ids=ids, attention_mask=att).last_hidden_state
        m = att.unsqueeze(-1).float()
        return (h * m).sum(1) / m.sum(1)
    def forward(self, ids, att):
        e = self.embed(ids, att)
        return self.head(e), e


@torch.no_grad()
def predict(model, d, with_y=False):
    model.eval(); P, E = [], []
    for ids, att, _ in DataLoader(DS(d, with_y), BS * 2, collate_fn=collate):
        with torch.autocast(dev, enabled=dev == "cuda"):
            lo, e = model(ids.to(dev), att.to(dev))
        P.append(torch.sigmoid(lo.float()).cpu().numpy()); E.append(e.float().cpu().numpy())
    return np.concatenate(P), np.concatenate(E)


def train(d):
    model = Net().to(dev)
    dl = DataLoader(DS(d), BS, shuffle=True, collate_fn=collate)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * len(dl) * EPOCHS), len(dl) * EPOCHS)
    pos = d[LABELS].mean().values
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.clip((1 - pos) / pos, 1, 10) ** 0.5,
                                                         dtype=torch.float32, device=dev))
    scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")
    for ep in range(EPOCHS):
        model.train()
        for ids, att, y in dl:
            with torch.autocast(dev, enabled=dev == "cuda"):
                lo, _ = model(ids.to(dev), att.to(dev))
                loss = lossf(lo.float(), y.to(dev))
            opt.zero_grad(); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); sch.step()
        print(f"  epoch {ep+1} loss {loss.item():.4f}")
    return model


def aucs(y, p):
    y = (np.asarray(y) >= 0.5).astype(int)
    return {c: round(roc_auc_score(y[:, j], p[:, j]), 4) for j, c in enumerate(LABELS)
            if 0 < y[:, j].sum() < len(y)}


# ---- 1) Sanity check: train on extracted, score against human (gold+silver) labels ----
hum = lab[lab.label_type.isin(["gold", "silver"])]
m = train(lab[lab.label_type == "extracted"])
p_h, _ = predict(m, hum, True)
print("AUC vs gold/silver:", aucs(hum[LABELS].values, p_h))
del m; torch.cuda.empty_cache()

# ---- 2) 5-fold OOF over all labeled rows -> soft labels + noise flags; average folds for unlabeled ----
# labels are soft (0-1 confidences), so binarize before building the strat key
strat = (lab[LABELS].values >= 0.5).astype(int) @ (2 ** np.arange(len(LABELS)))
strat = pd.Series(strat).map(lambda k: k if (strat == k).sum() >= FOLDS else -1).values
oof = np.zeros((len(lab), len(LABELS))); emb = np.zeros((len(lab), 768), "float32")
p_unl = np.zeros((len(unl), len(LABELS))); e_unl = np.zeros((len(unl), 768), "float32")
for f, (tr, va) in enumerate(StratifiedKFold(FOLDS, shuffle=True, random_state=42).split(lab, strat)):
    print(f"fold {f}")
    m = train(lab.iloc[tr])
    oof[va], emb[va] = predict(m, lab.iloc[va], True)
    pu, eu = predict(m, unl); p_unl += pu / FOLDS; e_unl += eu / FOLDS
    del m; torch.cuda.empty_cache()
print("OOF AUC vs own labels:", aucs(lab[LABELS].values, oof))

soft = pd.concat([pd.DataFrame(oof, columns=LABELS).assign(StudyInstanceUID=lab.StudyInstanceUID.values),
                  pd.DataFrame(p_unl, columns=LABELS).assign(StudyInstanceUID=unl.StudyInstanceUID.values)])
soft[["StudyInstanceUID"] + LABELS].to_csv("radbert_soft_labels.csv", index=False)

# Flags: confident disagreement with the extracted label (review these by hand / with an LLM)
rows = []
for j, c in enumerate(LABELS):
    y, p = lab[c].values, oof[:, j]
    for i in np.where(((y >= 0.5) & (p < 0.1)) | ((y < 0.5) & (p > 0.9)))[0]:
        rows.append((lab.StudyInstanceUID[i], c, y[i], round(p[i], 3), lab.label_type[i],
                     lab[f"{c}_evidence"][i], lab.text[i][:400]))
pd.DataFrame(rows, columns=["StudyInstanceUID", "label", "given", "radbert_p", "label_type",
                            "evidence", "report_snippet"]).to_csv("radbert_label_flags.csv", index=False)
print(f"{len(rows)} flagged label cells")

np.save("radbert_emb.npy", np.concatenate([emb, e_unl]))
soft[["StudyInstanceUID"]].to_csv("radbert_emb_ids.csv", index=False)
