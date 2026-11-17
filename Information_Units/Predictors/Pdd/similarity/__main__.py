"""Command-line entry point.

    python -m Information_Units.Predictors.Pdd.similarity --config config.json
    python -m Information_Units.Predictors.Pdd.similarity --input-dir cifs/mp --input-dir cifs/cod --tau 0.05

A JSON config file holds any :class:`SimilarityConfig` field; command-line options override it.
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import ConfigError, SimilarityConfig
from .pipeline import run_similarity_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m Information_Units.Predictors.Pdd.similarity",
        description="Duplicate screening: AMD on the full set, PDD EMD on candidate pairs only.",
    )
    parser.add_argument("--config", help="JSON file with SimilarityConfig fields")
    parser.add_argument("--input-dir", action="append", dest="input_dirs", help="folder of CIFs (repeatable)")
    parser.add_argument("--output-dir")
    parser.add_argument("--k-amd", type=int)
    parser.add_argument("--k-pdd", type=int)
    parser.add_argument("--k-max", type=int)
    parser.add_argument("--k-tsne", type=int)
    parser.add_argument("--tau", type=float, help="duplicate threshold [A]")
    parser.add_argument("--metric", help="euclidean | cityblock | chebyshev")
    parser.add_argument("--linkage", help="complete | single | average | ward (ward needs euclidean)")
    parser.add_argument("--composition", action="append", dest="composition_filter",
                        help="keep only this reduced formula (repeatable)")
    parser.add_argument("--highlight", action="append", help="structure label to highlight in the heatmap (repeatable)")
    parser.add_argument("--n-jobs", type=int)
    parser.add_argument("--crosscheck-cifreader", action="store_true", default=None)
    parser.add_argument("--plot-pdd-subset", action="store_true", default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data: dict = {}
    if args.config:
        with open(args.config, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    for name in (
        "input_dirs", "output_dir", "k_amd", "k_pdd", "k_max", "k_tsne", "tau", "metric", "linkage",
        "composition_filter", "highlight", "n_jobs", "crosscheck_cifreader", "plot_pdd_subset",
    ):
        value = getattr(args, name)
        if value is not None:
            data[name] = value
    try:
        config = SimilarityConfig.from_dict(data)
        result = run_similarity_pipeline(config, verbose=not args.quiet)
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.quiet:
        print(json.dumps(result.summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
