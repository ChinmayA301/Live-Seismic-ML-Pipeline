"""Data-drift monitoring with Evidently.

Compares the model's training window (older events) against the most recent
window. Seismicity is bursty and regionally shifting, so real drift is expected —
this is what erodes conformal coverage over time and signals when to retrain.
"""
from __future__ import annotations
import duckdb
import pandas as pd
from evidently import Report, Dataset, DataDefinition
from evidently.presets import DataDriftPreset
from . import config as C
from .features import make_features

OUT = C.REPORTS / "drift_report.html"


def monitor(recent_frac: float = 0.2) -> dict:
    con = duckdb.connect(str(C.DB), read_only=True)
    df = con.execute("SELECT * FROM events WHERE type='earthquake' "
                     "AND mag IS NOT NULL ORDER BY time").df()
    con.close()
    df = make_features(df)
    cut = int(len(df) * (1 - recent_frac))
    ref, cur = df.iloc[:cut], df.iloc[cut:]

    feats = [c for c in C.FEATURES_NUM if c in df.columns]
    dd = DataDefinition(numerical_columns=feats)
    report = Report([DataDriftPreset()])
    result = report.run(
        reference_data=Dataset.from_pandas(ref[feats].reset_index(drop=True), data_definition=dd),
        current_data=Dataset.from_pandas(cur[feats].reset_index(drop=True), data_definition=dd))
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    result.save_html(str(OUT))

    summary = {"drifted": None, "n_features": len(feats)}
    for mrow in result.dict().get("metrics", []):
        v = mrow.get("value")
        if isinstance(v, dict) and "share" in v:
            summary["drifted"] = f"{int(v['count'])}/{len(feats)} ({v['share']:.0%})"
            break
    print(f"drift (train vs recent {recent_frac:.0%}): {summary['drifted']} features -> {OUT.name}")
    return summary


if __name__ == "__main__":
    monitor()
