# Case Study — Live Seismic ML Pipeline
*Portfolio / blog-ready writeup. Pairs with the [README](../README.md) and [model card](model_card.md).*

## Problem
Most portfolio ML lives in a static notebook on a frozen CSV. Real ML systems run on **live data on a schedule**, validate their inputs, quantify uncertainty, and watch themselves for drift. This project is that system, built on a genuinely live scientific stream — the USGS earthquake feed — with an honest, well-posed task: **estimate an event's magnitude from its detection-network geometry, and flag events inconsistent with the network for review.**

## Why it matters
It demonstrates the two things a static project can't: **production ML operations** (scheduled ingestion → validation → scoring → monitoring, idempotent and one-command) and **deep statistical rigor** (distribution-free uncertainty via conformalized quantile regression, temporal validation, drift detection). And it does so without overclaiming — it explicitly is *not* earthquake prediction.

## Data
[USGS real-time GeoJSON feeds](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) — public, no-auth, updated ~every minute. ~10.8k real events over a month at bootstrap; the scheduled job keeps it current.

## Methods
1. **Ingest** — parse GeoJSON, upsert into DuckDB keyed by event id (idempotent; re-runs never duplicate).
2. **Validate** — Great Expectations physical guardrails (magnitude/depth/coord/gap ranges); gates scoring on critical failure.
3. **Model** — HistGradientBoosting magnitude regressor with a **temporal** train/test split; feature set is network geometry (station count, azimuthal gap, distance, RMS, depth, location).
4. **Uncertainty** — quantile regressors for a 90% interval, then **Conformalized Quantile Regression** (Romano et al., 2019) for distribution-free coverage.
5. **Score** — predict + conformal interval; flag events outside the interval as QA review candidates.
6. **Monitor** — Evidently feature-drift (train window vs recent) as the retrain signal.
7. **Track & schedule** — MLflow for runs; a GitHub Actions cron job runs the whole loop every 6 hours and commits refreshed reports.

## Key results (temporal test)
- **R² 0.90, MAE 0.27** magnitude units — network geometry explains magnitude well.
- **Conformal calibration** lifts 90%-interval coverage from **77% → 87%** (width 0.93 → 1.16); the residual gap is temporal-shift-induced.
- **5.6%** of events flagged for review; top candidates have observed magnitudes ~2 units above the network-implied estimate.
- **6/10 features drift** between the training window and recent events.

## Limitations
Not forecasting; catalog magnitude is itself an estimate; ~1 month of data; exchangeability violated by drift; single-seed temporal split. See README.

## What I'd improve next
Region-conditional (Mondrian) conformal intervals; online/rolling retraining triggered by the drift signal; a small serving API; add felt-report classification as a second head; longer historical backfill from ComCat.

---

## Résumé bullets
> **Live Seismic ML Pipeline** — *Python, scikit-learn, DuckDB, Great Expectations, MLflow, Evidently, GitHub Actions*
> - Built an end-to-end **MLOps pipeline on a live scientific feed** (USGS earthquakes): idempotent ingestion → Great Expectations validation gate → model scoring → Evidently drift monitoring, orchestrated in one command and run on a **scheduled GitHub Action** that commits refreshed reports.
> - Trained a magnitude-estimation model (**R² 0.90, MAE 0.27**) on detection-network geometry with a **temporal** train/test split, tracked in MLflow.
> - Delivered **distribution-free uncertainty** via **Conformalized Quantile Regression**, improving 90%-interval coverage from 77% to 87% out-of-time, and used the intervals to flag network-inconsistent events for catalog QA.
> - Scoped the task honestly (catalog quality control, **not** earthquake prediction) with a model card, datasheet, and drift-driven retrain signal.

## Interview talking points
- **"Why is this MLOps and not a notebook?"** It runs on a schedule against live data, is idempotent (upsert-keyed ingestion), gates itself on data-quality failures before scoring, tracks every run, and monitors its own drift. A GitHub Action executes the whole loop every 6 hours and commits the results. That's a system, not an analysis.
- **"Explain the conformal prediction."** My quantile intervals under-covered out-of-time — 77% for a nominal 90%. CQR takes a held-out calibration set, computes nonconformity scores, and widens the band by their conformal quantile to get a distribution-free coverage guarantee. It brought coverage to 87%. The remaining 3 points are because conformal assumes exchangeability and seismicity drifts over time — which is exactly why the drift monitor exists.
- **"Isn't predicting magnitude circular / trivial?"** It's not prediction of the future — it's a consistency check. The magnitude and the network geometry are related but not identical; where they disagree (5.6% of events), the event is inconsistent with the network that recorded it, which is a real QA signal seismologists care about, especially for automatically-detected events awaiting review.
- **"How do you avoid overclaiming?"** The whole framing is guarded: it's catalog QA, not forecasting; the target is an estimate, so flags are consistency outliers not confirmed errors; and the model card states intended/not-intended use plainly. Knowing what the data *can't* support is the point.
- **"When would it retrain?"** The Evidently drift report and the conformal coverage on recent data are the triggers — sustained feature drift plus coverage decay means the calibration is stale. Currently 6/10 features drift over the month, so in production I'd retrain on a rolling window.
