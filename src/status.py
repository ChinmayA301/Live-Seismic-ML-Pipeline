"""Write reports/STATUS.md — a live snapshot committed by the scheduled job."""
from __future__ import annotations
import json
import datetime as dt
import duckdb
from . import config as C


def main() -> None:
    con = duckdb.connect(str(C.DB), read_only=True)
    total = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    span = con.execute("SELECT MIN(time), MAX(time) FROM events").fetchone()
    flagged = con.execute("SELECT COUNT(*) FROM scored WHERE review_flag").fetchone()[0]
    scored = con.execute("SELECT COUNT(*) FROM scored").fetchone()[0]
    con.close()
    m = json.loads((C.REPORTS / "_metrics.json").read_text())

    md = f"""# Pipeline Status

_Auto-generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC by the scheduled job._

| | |
|---|---|
| Events in catalog | **{total:,}** |
| Catalog span | {span[0]:%Y-%m-%d} → {span[1]:%Y-%m-%d} |
| Scored | {scored:,} |
| Flagged for review | **{flagged:,}** ({flagged/max(scored,1):.1%}) |

## Model (magnitude estimation, temporal test)
| MAE | RMSE | R² | 90% PI coverage (raw → conformal) |
|---|---|---|---|
| {m['mae']:.3f} | {m['rmse']:.3f} | {m['r2']:.3f} | {m['pi90_coverage_raw']:.0%} → {m['pi90_coverage_conformal']:.0%} |

See `reports/drift_report.html` for the latest feature-drift check.
"""
    (C.REPORTS / "STATUS.md").write_text(md)
    print("wrote reports/STATUS.md")


if __name__ == "__main__":
    main()
