"""One live 'tick' of the pipeline: ingest -> validate -> score -> monitor.

    python pipeline.py             # ingest latest day, validate, score, monitor
    python pipeline.py --train     # also retrain the model first
    python pipeline.py --feed week # ingest a wider window

Designed to run on a schedule (see .github/workflows/pipeline.yml). Idempotent.
"""
from __future__ import annotations
import argparse
import sys
from src import ingest, validate, score, monitor, train as train_mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default="day", choices=["hour", "day", "week", "month"])
    ap.add_argument("--train", action="store_true", help="retrain before scoring")
    args = ap.parse_args()

    print("① ingest"); ingest.main(args.feed)
    print("\n② validate")
    if not validate.validate(validate.load_events()):
        sys.exit("critical data-quality failure — halting before scoring")
    if args.train:
        print("\n③ train"); train_mod.train()
    print("\n④ score"); score.score()
    print("\n⑤ monitor"); monitor.monitor()
    print("\n✓ pipeline tick complete")


if __name__ == "__main__":
    main()
