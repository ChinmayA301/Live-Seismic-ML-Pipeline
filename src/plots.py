"""Figures for the README / model card. Reads the scored table + saved model."""
from __future__ import annotations
import duckdb
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.inspection import permutation_importance
from . import config as C
from .features import modeling_frame

INK, ACC, BAD = "#1f2933", "#2b6cb0", "#c0392b"
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130, "font.size": 10.5,
                     "axes.titleweight": "bold", "axes.grid": True,
                     "grid.color": "#e6e9ee", "axes.axisbelow": True})


def _save(fig, name):
    C.FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(C.FIG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("  fig:", name)


def main():
    con = duckdb.connect(str(C.DB), read_only=True)
    s = con.execute("SELECT * FROM scored").df()
    df = con.execute("SELECT * FROM events ORDER BY time").df()
    con.close()
    m = joblib.load(C.MODELS / "magnitude_model.joblib")

    # 1. predicted vs actual
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.hexbin(s.mag, s.pred, gridsize=45, cmap="Blues", mincnt=1)
    lim = [min(s.mag.min(), s.pred.min()), max(s.mag.max(), s.pred.max())]
    ax.plot(lim, lim, "--", color=INK, lw=1)
    r2 = 1 - np.sum((s.mag - s.pred) ** 2) / np.sum((s.mag - s.mag.mean()) ** 2)
    ax.set_title(f"Predicted vs actual magnitude (R²={r2:.2f})")
    ax.set_xlabel("Cataloged magnitude"); ax.set_ylabel("Predicted magnitude")
    _save(fig, "01_pred_vs_actual.png")

    # 2. residual distribution
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.hist(s.residual, bins=60, color=ACC, alpha=0.85)
    ax.axvline(0, color=INK, lw=1)
    ax.set_title("Residuals (actual − predicted)")
    ax.set_xlabel("Magnitude residual"); ax.set_ylabel("Count")
    _save(fig, "02_residuals.png")

    # 3. flagged review candidates on the residual tail
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ok, fl = s[~s.review_flag], s[s.review_flag]
    ax.scatter(ok.mag, ok.residual, s=6, color="#9fb3c8", label="within interval")
    ax.scatter(fl.mag, fl.residual, s=14, color=BAD, label="flagged for review")
    ax.axhline(0, color=INK, lw=1)
    ax.set_title("QA flags: events inconsistent with the network")
    ax.set_xlabel("Cataloged magnitude"); ax.set_ylabel("Residual"); ax.legend(fontsize=8)
    _save(fig, "03_review_flags.png")

    # 4. permutation feature importance
    X, y, t = modeling_frame(df)
    n = min(3000, len(X))
    pi = permutation_importance(m["point"], X.iloc[-n:], y[-n:], n_repeats=5,
                                random_state=C.SEED, scoring="r2")
    idx = np.argsort(pi.importances_mean)[-12:]
    names = np.array(C.FEATURES_NUM + C.FEATURES_CAT)[idx]
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.barh(names, pi.importances_mean[idx], color=ACC)
    ax.set_title("Permutation importance (drop in R²)")
    ax.set_xlabel("Importance")
    _save(fig, "04_feature_importance.png")


if __name__ == "__main__":
    main()
