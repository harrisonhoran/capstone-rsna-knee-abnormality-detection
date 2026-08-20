# =============================================================================
# rsna-knee-2026.py
# Kaggle RSNA Knee Abnormalities Competition
# =============================================================================

# stdlib
import os
import warnings
from pathlib import Path

# third-party
import numpy as np
import pandas as pd
import kagglehub
import xgboost as xgb
from scipy.stats import pointbiserialr, trim_mean
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 999)


# =============================================================================
# Paths
# =============================================================================

NOTEBOOK_DIR = Path(__file__).resolve().parent
DATA_DIR = NOTEBOOK_DIR / "data/competition"
DATA_DIR_EXT = NOTEBOOK_DIR / "data/external"
OUTPUT_DIR = NOTEBOOK_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# =============================================================================
# Data Collection
# =============================================================================

dataset_path = kagglehub.dataset_download("rsna-knee-abnormality-detection")

dfs = {}
for file in os.listdir(dataset_path):
    if file.endswith(".csv"):
        key = file.replace(".csv", "")
        dfs[key] = pd.read_csv(os.path.join(dataset_path, file))




# =============================================================================
# Data Cleaning
# =============================================================================