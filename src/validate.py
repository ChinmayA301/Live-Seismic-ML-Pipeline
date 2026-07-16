"""Great Expectations validation gate — physical guardrails on ingested events.

Runs before modeling/scoring so bad or malformed records never reach the model.
Exits non-zero on any critical failure (usable as a CI/pipeline gate).
"""
from __future__ import annotations
import sys
import duckdb
import pandas as pd
import great_expectations as gx
from . import config as C


def load_events() -> pd.DataFrame:
    con = duckdb.connect(str(C.DB), read_only=True)
    df = con.execute("SELECT * FROM events").df()
    con.close()
    return df


def validate(df: pd.DataFrame, write_report: bool = True) -> bool:
    batch = (gx.get_context().data_sources.add_pandas("seismic")
             .add_dataframe_asset("events")
             .add_batch_definition_whole_dataframe("b")
             .get_batch(batch_parameters={"dataframe": df}))
    E = gx.expectations
    specs = [  # (expectation, critical)
        (E.ExpectColumnValuesToNotBeNull(column="id"), True),
        (E.ExpectColumnValuesToBeUnique(column="id"), True),
        (E.ExpectColumnValuesToBeBetween(column="mag", min_value=-2, max_value=10,
                                         mostly=0.999), True),
        (E.ExpectColumnValuesToBeBetween(column="depth", min_value=-11, max_value=800,
                                         mostly=0.999), True),
        (E.ExpectColumnValuesToBeBetween(column="lat", min_value=-90, max_value=90), True),
        (E.ExpectColumnValuesToBeBetween(column="lon", min_value=-180, max_value=180), True),
        (E.ExpectColumnValuesToBeBetween(column="rms", min_value=0, mostly=0.99), False),
        (E.ExpectColumnValuesToBeBetween(column="gap", min_value=0, max_value=360,
                                         mostly=0.99), False),
        (E.ExpectColumnValuesToBeInSet(column="type",
                                       value_set=["earthquake", "quarry blast",
                                                  "explosion", "ice quake", "other event",
                                                  "mining explosion", "sonic boom",
                                                  "nuclear explosion", "rock burst",
                                                  "landslide", "volcanic eruption"],
                                       mostly=0.99), False),
    ]
    rows, n_fail, n_crit = [], 0, 0
    for exp, crit in specs:
        r = batch.validate(exp)
        ok = bool(r.success)
        n_fail += (not ok); n_crit += (not ok and crit)
        rows.append({"expectation": type(exp).__name__,
                     "column": getattr(exp, "column", ""),
                     "critical": "yes" if crit else "no",
                     "result": "PASS" if ok else "FAIL",
                     "unexpected_pct": round((r.result or {}).get("unexpected_percent", 0), 3)})
    rep = pd.DataFrame(rows)
    print(rep.to_string(index=False))
    print(f"{len(specs)-n_fail}/{len(specs)} passed; {n_crit} critical failures.")
    if write_report:
        C.REPORTS.mkdir(parents=True, exist_ok=True)
        (C.REPORTS / "data_quality_report.md").write_text(
            f"# Data Quality — events ({len(df):,} rows)\n\n" + rep.to_markdown(index=False))
    return n_crit == 0


def main() -> None:
    ok = validate(load_events())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
