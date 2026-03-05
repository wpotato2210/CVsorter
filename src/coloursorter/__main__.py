from __future__ import annotations

import argparse
import sys

from coloursorter.bench.cli import main as bench_main


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ColourSorter module runner")
    parser.add_argument("--mode", choices=("replay", "live"), default="replay")
    parser.add_argument("--source", default="data")
    parser.add_argument("--max-cycles", type=int, default=300)
    parser.add_argument("--artifact-root", default="artifacts/bench")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    old_argv = sys.argv
    sys.argv = [
        "coloursorter",
        "--mode",
        args.mode,
        "--source",
        args.source,
        "--max-cycles",
        str(args.max_cycles),
        "--artifact-root",
        args.artifact_root,
    ]
    try:
        return bench_main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
