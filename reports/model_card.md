# Model Card — Seismic Magnitude Estimator (network-geometry QA)

> **Research / operations-QA prototype.** Estimates cataloged magnitude for quality control. **Not** an earthquake forecaster.

## Model details
- **Task:** regression — estimate an event's cataloged magnitude from detection-network geometry, with a 90% prediction interval.
- **Model:** `HistGradientBoostingRegressor` (point) + two quantile regressors (0.05, 0.95), **conformalized (CQR)** for distribution-free interval coverage.
- **Prediction time:** at/after event detection — uses only network parameters reported with the event.
- **Version:** v1.0, seed 42, reproducible via `python -m src.train`.

## Intended use
- **Intended:** catalog **quality control** — flag events whose magnitude is inconsistent with the recording network for human review; demonstrate a live MLOps + uncertainty-quantification workflow.
- **Not intended:** forecasting future earthquakes (impossible from this data), hazard assessment, or any life-safety decision. Outputs are consistency scores, not warnings.

## Data
- **Source:** USGS real-time GeoJSON feeds (public, no-auth). ~10.8k events over ~1 month at bootstrap.
- **Features:** depth, `nst` (station count), `gap` (azimuthal gap), `dmin`, `rms`, |lat|, lon, log-transforms, hour, network, `magType`.
- **Target:** `mag`. Rows: `type = earthquake` with complete geometry.

## Validation
- **Temporal split** (train earliest 80% → test latest 20%); within train, most-recent 25% held out as the **conformal calibration set**. Mirrors deployment (always scoring newer events).

## Metrics (temporal test)
| MAE | RMSE | R² | 90% coverage raw → conformal | mean width raw → conformal |
|---|---|---|---|---|
| 0.27 | 0.38 | 0.90 | 0.77 → 0.87 | 0.93 → 1.16 |

Review flag rate: **5.6%** of scored events fall outside their conformal interval.

## Ethical / scientific risks
- **Misinterpretation as prediction** — explicitly guarded against in all docs.
- **Ground-truth is itself an estimate** — flags indicate *network inconsistency*, not confirmed catalog errors; a seismologist adjudicates.
- **Automatic vs reviewed events** differ systematically; the model mixes both, so flags on `automatic` events (pre-human-review) are expected and appropriate targets.

## Monitoring & maintenance
- **Evidently** drift (train vs recent window) runs every tick; **6/10 features currently drift**. Sustained drift + falling conformal coverage is the retrain trigger.
- MLflow tracks each training run.

## Recommendation
Suitable as a catalog-QA assistant and as an MLOps/uncertainty-quantification demonstration. **Not** for any forecasting or safety use.
