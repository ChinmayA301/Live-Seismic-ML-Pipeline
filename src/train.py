"""Train the magnitude-estimation model (point + 90% prediction interval).

Temporal split (train on earlier events, test on later) mirrors deployment: the
model is always scoring events newer than those it learned from. Logs to MLflow.
"""
from __future__ import annotations
import json
import numpy as np
import duckdb
import joblib
import mlflow
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from . import config as C
from .features import modeling_frame


def _prep():
    return ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), C.FEATURES_NUM),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="NA")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=25,
                                               sparse_output=False))]), C.FEATURES_CAT),
    ])


def _model(loss="squared_error", quantile=None):
    kw = dict(learning_rate=0.08, max_iter=400, max_leaf_nodes=31,
              l2_regularization=1.0, early_stopping=True, random_state=C.SEED)
    if quantile is not None:
        return HistGradientBoostingRegressor(loss="quantile", quantile=quantile, **kw)
    return HistGradientBoostingRegressor(loss=loss, **kw)


def train() -> dict:
    con = duckdb.connect(str(C.DB), read_only=True)
    df = con.execute("SELECT * FROM events ORDER BY time").df()
    con.close()
    X, y, t = modeling_frame(df)
    order = np.argsort(t)
    X, y = X.iloc[order], y[order]
    # temporal split: train (earliest 80%) -> test (latest 20%); within train,
    # hold out the most-recent 25% as a conformal CALIBRATION set.
    cut = int(len(X) * 0.8)
    Xtr_all, Xte, ytr_all, yte = X.iloc[:cut], X.iloc[cut:], y[:cut], y[cut:]
    ccut = int(len(Xtr_all) * 0.75)
    Xtr, Xcal, ytr, ycal = (Xtr_all.iloc[:ccut], Xtr_all.iloc[ccut:],
                            ytr_all[:ccut], ytr_all[ccut:])

    point = Pipeline([("prep", _prep()), ("m", _model())]).fit(Xtr, ytr)
    lo = Pipeline([("prep", _prep()), ("m", _model(quantile=C.PI_ALPHAS[0]))]).fit(Xtr, ytr)
    hi = Pipeline([("prep", _prep()), ("m", _model(quantile=C.PI_ALPHAS[1]))]).fit(Xtr, ytr)

    # --- Conformalized Quantile Regression (Romano et al., 2019) ---
    # Distribution-free coverage: widen the quantile band by the conformal
    # quantile of the calibration nonconformity scores.
    target = C.PI_ALPHAS[1] - C.PI_ALPHAS[0]                      # 0.90
    cal_lo, cal_hi = lo.predict(Xcal), hi.predict(Xcal)
    scores = np.maximum(cal_lo - ycal, ycal - cal_hi)            # CQR score
    n = len(scores)
    q_level = min(1.0, np.ceil((n + 1) * target) / n)
    conformal_q = float(np.quantile(scores, q_level, method="higher"))

    pred = point.predict(Xte)
    q_lo, q_hi = lo.predict(Xte), hi.predict(Xte)
    raw_cov = float(((yte >= q_lo) & (yte <= q_hi)).mean())
    conf_cov = float(((yte >= q_lo - conformal_q) & (yte <= q_hi + conformal_q)).mean())
    metrics = {
        "mae": float(mean_absolute_error(yte, pred)),
        "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
        "r2": float(r2_score(yte, pred)),
        "pi90_coverage_raw": raw_cov,
        "pi90_coverage_conformal": conf_cov,
        "pi90_width_raw": float(np.mean(q_hi - q_lo)),
        "pi90_width_conformal": float(np.mean((q_hi + conformal_q) - (q_lo - conformal_q))),
        "conformal_q": conformal_q,
        "n_train": int(len(Xtr)), "n_cal": int(len(Xcal)), "n_test": int(len(Xte)),
    }

    C.MODELS.mkdir(exist_ok=True)
    joblib.dump({"point": point, "lo": lo, "hi": hi, "conformal_q": conformal_q,
                 "resid_std": float(np.std(yte - pred))}, C.MODELS / "magnitude_model.joblib")

    mlflow.set_tracking_uri(f"file:{C.MLRUNS}")
    mlflow.set_experiment("seismic_magnitude")
    with mlflow.start_run(run_name="histgbt_temporal"):
        mlflow.log_params({"model": "HistGBT", "split": "temporal_80_20",
                           "features": len(C.FEATURES_NUM) + len(C.FEATURES_CAT)})
        mlflow.log_metrics(metrics)
    (C.REPORTS / "_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    C.REPORTS.mkdir(exist_ok=True)
    train()
