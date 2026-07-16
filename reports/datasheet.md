# Datasheet — USGS Real-Time Earthquake Feeds

Following *Datasheets for Datasets* (Gebru et al., 2021).

## Motivation
- **Purpose here:** a live scientific data stream for an MLOps pipeline + catalog-QA modeling.
- **Original creation:** the USGS/ANSS Comprehensive Catalog (ComCat), published as rolling GeoJSON summary feeds for public/operational use.

## Composition
- **Instances:** individual seismic events (earthquakes and a few other types) reported in the last hour / day / week / month.
- **Fields:** time, location (lon, lat, depth), magnitude + `magType`, network parameters (`nst`, `gap`, `dmin`, `rms`), significance (`sig`), felt reports, `status` (automatic/reviewed), source network.
- **Grain:** one row per event, keyed by USGS `id`.
- **Labels:** `mag` (catalog magnitude) is the modeling target; it is itself a produced estimate, revised as events move from `automatic` → `reviewed`.

## Collection
- Automatically computed from seismic station networks, then human-reviewed for larger/notable events. Real, continuously updated. No sampling by us beyond the feed windows.

## Preprocessing (this project)
- Epoch-ms times → UTC timestamps; upsert into DuckDB keyed by `id` (idempotent). Modeling restricted to `type = earthquake` with complete geometry. Great Expectations gate enforces physical ranges. See [`../src`](../src).

## Uses & limitations
- **Appropriate:** catalog QA, MLOps demonstration, uncertainty-quantification methodology.
- **Not appropriate:** forecasting, hazard/risk assessment, life-safety decisions.
- **Caveats:** feeds are rolling windows (not a fixed historical archive); magnitudes and even event presence can be **revised** after ingestion; `automatic` vs `reviewed` events differ systematically; coverage/detection varies by region and network density.

## Distribution & license
- Public USGS feeds; U.S. Government work, generally public domain. Attribute USGS/ANSS ComCat. Feeds are rolling — reproduce by re-ingesting (results will differ as the live catalog moves).
