"""Ingest USGS GeoJSON feeds into a DuckDB store (idempotent upsert by event id).

Re-running never duplicates: events are keyed by USGS id and updated in place, so
the pipeline can run on a schedule and only ever grows / refreshes the catalog.
"""
from __future__ import annotations
import json
import pathlib
import urllib.request
import duckdb
import pandas as pd
from . import config as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR PRIMARY KEY, time TIMESTAMP, updated TIMESTAMP,
    mag DOUBLE, magType VARCHAR, depth DOUBLE, lat DOUBLE, lon DOUBLE,
    nst INTEGER, gap DOUBLE, dmin DOUBLE, rms DOUBLE, sig INTEGER, felt INTEGER,
    place VARCHAR, net VARCHAR, status VARCHAR, type VARCHAR,
    ingested_at TIMESTAMP DEFAULT now()
);
"""


def _feed_to_df(obj: dict) -> pd.DataFrame:
    rows = []
    for f in obj["features"]:
        p, g = f["properties"], f["geometry"]
        coords = (g or {}).get("coordinates") or [None, None, None]
        rows.append({
            "id": f["id"], "time": p.get("time"), "updated": p.get("updated"),
            "mag": p.get("mag"), "magType": p.get("magType"),
            "lon": coords[0], "lat": coords[1], "depth": coords[2],
            "nst": p.get("nst"), "gap": p.get("gap"), "dmin": p.get("dmin"),
            "rms": p.get("rms"), "sig": p.get("sig"), "felt": p.get("felt"),
            "place": p.get("place"), "net": p.get("net"),
            "status": p.get("status"), "type": p.get("type"),
        })
    df = pd.DataFrame(rows)
    # USGS times are epoch ms
    for c in ("time", "updated"):
        df[c] = pd.to_datetime(df[c], unit="ms", utc=True)
    return df


def load_feed(feed: str = "hour", local_path: str | None = None) -> pd.DataFrame:
    if local_path:
        obj = json.loads(pathlib.Path(local_path).read_text())
    else:
        with urllib.request.urlopen(C.FEEDS[feed], timeout=60) as r:
            obj = json.loads(r.read())
    return _feed_to_df(obj)


def upsert(df: pd.DataFrame) -> dict:
    C.DATA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(C.DB))
    con.execute(SCHEMA)
    before = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    con.register("incoming", df)
    cols = ("id,time,updated,mag,magType,depth,lat,lon,nst,gap,dmin,rms,"
            "sig,felt,place,net,status,type")
    con.execute(f"""
        INSERT INTO events ({cols})
        SELECT {cols} FROM incoming
        ON CONFLICT (id) DO UPDATE SET
            updated=excluded.updated, mag=excluded.mag, status=excluded.status,
            sig=excluded.sig, felt=excluded.felt, nst=excluded.nst, gap=excluded.gap,
            dmin=excluded.dmin, rms=excluded.rms;
    """)
    after = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    con.close()
    return {"received": len(df), "new": after - before, "total": after}


def main(feed: str = "day", local_path: str | None = None) -> None:
    df = load_feed(feed, local_path)
    stats = upsert(df)
    print(f"ingest[{feed}]: received={stats['received']} new={stats['new']} "
          f"total={stats['total']}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "day",
         sys.argv[2] if len(sys.argv) > 2 else None)
