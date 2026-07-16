"""Score events: predicted magnitude + conformal interval + review flag.

QA use case: flag events whose cataloged magnitude falls OUTSIDE the model's
conformal prediction interval given the detection-network geometry — i.e. events
that are inconsistent with the network and worth a human look. Not prediction of
future earthquakes.
"""
from __future__ import annotations
import duckdb
import joblib
import numpy as np
import pandas as pd
from . import config as C
from .features import modeling_frame

SCORED_DDL = """
CREATE TABLE IF NOT EXISTS scored (
    id VARCHAR PRIMARY KEY, time TIMESTAMP, mag DOUBLE, pred DOUBLE,
    pi_lo DOUBLE, pi_hi DOUBLE, residual DOUBLE, review_flag BOOLEAN,
    scored_at TIMESTAMP DEFAULT now());
"""


def score() -> dict:
    m = joblib.load(C.MODELS / "magnitude_model.joblib")
    con = duckdb.connect(str(C.DB))
    df = con.execute("SELECT * FROM events ORDER BY time").df()
    X, y, t = modeling_frame(df)
    ids = df[df["type"] == "earthquake"].dropna(
        subset=["mag", "nst", "gap", "rms", "depth", "lat", "lon"])["id"].to_numpy()

    pred = m["point"].predict(X)
    lo = m["lo"].predict(X) - m["conformal_q"]
    hi = m["hi"].predict(X) + m["conformal_q"]
    out = pd.DataFrame({
        "id": ids, "time": pd.to_datetime(t, utc=True), "mag": y, "pred": pred,
        "pi_lo": lo, "pi_hi": hi, "residual": y - pred,
        "review_flag": (y < lo) | (y > hi),
    })

    con.execute(SCORED_DDL)
    con.register("s", out)
    con.execute("""INSERT INTO scored (id,time,mag,pred,pi_lo,pi_hi,residual,review_flag)
                   SELECT id,time,mag,pred,pi_lo,pi_hi,residual,review_flag FROM s
                   ON CONFLICT (id) DO UPDATE SET pred=excluded.pred, pi_lo=excluded.pi_lo,
                   pi_hi=excluded.pi_hi, residual=excluded.residual,
                   review_flag=excluded.review_flag, scored_at=now();""")
    con.close()

    flagged = out[out.review_flag]
    top = (flagged.reindex(flagged.residual.abs().sort_values(ascending=False).index)
           .head(10)[["id", "mag", "pred", "pi_lo", "pi_hi", "residual"]])
    stats = {"scored": len(out), "review_flagged": int(out.review_flag.sum()),
             "flag_rate": round(float(out.review_flag.mean()), 4)}
    print(f"scored={stats['scored']} flagged_for_review={stats['review_flagged']} "
          f"({stats['flag_rate']:.1%})")
    print("\nTop review candidates (|actual − predicted| largest):")
    print(top.round(2).to_string(index=False))
    return stats


if __name__ == "__main__":
    score()
