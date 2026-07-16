"""Feature engineering for magnitude estimation from network geometry."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config as C


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["abs_lat"] = df["lat"].abs()
    df["log_nst"] = np.log1p(df["nst"].clip(lower=0))
    df["log_dmin"] = np.log1p(df["dmin"].clip(lower=0))
    df["hour"] = pd.to_datetime(df["time"], utc=True).dt.hour
    return df


def modeling_frame(df: pd.DataFrame):
    """Return (X, y, time) for rows usable for supervised magnitude estimation."""
    df = make_features(df)
    need = ["mag", "nst", "gap", "rms", "depth", "lat", "lon"]
    df = df[df["type"] == "earthquake"].dropna(subset=need)
    X = df[C.FEATURES_NUM + C.FEATURES_CAT].copy()
    y = df[C.TARGET].to_numpy()
    return X, y, df["time"].to_numpy()
