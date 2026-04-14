#!/usr/bin/env python3
"""Unified utility to manage IU feature scaffolding across IU types.

This script provides a single entry point for database, generator, and predictor
IU feature management by delegating to the existing type-specific managers.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

MANAGER_SCRIPT_BY_TYPE: Dict[str, Path] = {
    "database": SCRIPT_DIR / "manage_database_iu_features.py",
    "generator": SCRIPT_DIR / "manage_generator_iu_features.py",
    "predictor": SCRIPT_DIR / "manage_predictor_iu_features.py",
}


def _run_manager(iu_type: str, forwarded_args: List[str]) -> int:
    script_path = MANAGER_SCRIPT_BY_TYPE[iu_type]
    cmd = [sys.executable, str(script_path), *forwarded_args]
    result = subprocess.run(cmd, check=False)
    return result.returncode


def _prompt_iu_type() -> str:
    types = list(MANAGER_SCRIPT_BY_TYPE.keys())

    print("\n" + "=" * 60)
    print("Unified IU Feature Manager")
    print("=" * 60)
    print("Select IU type:")
    for idx, iu_type in enumerate(types, start=1):
        print(f"  {idx}. {iu_type}")

    while True:
        raw = input("Choose IU type number (or press Enter to cancel): ").strip()
        if raw == "":
            raise SystemExit("No IU type selected. Exiting.")
        if raw.isdigit():
            pick = int(raw)
            if 1 <= pick <= len(types):
                return types[pick - 1]
        print("Invalid selection. Try again.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage IU feature scaffolding across IU types")
    parser.add_argument("--type", choices=sorted(MANAGER_SCRIPT_BY_TYPE.keys()), help="IU type to manage")
    parser.add_argument("--list", action="store_true", help="Only print current IU feature status")
    parser.add_argument("--add", metavar="IU_ID", help="Add IU feature for a specific IU id")
    parser.add_argument("--remove", metavar="IU_ID", help="Remove IU feature for a specific IU id")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    if args.add and args.remove:
        raise SystemExit("Use either --add or --remove, not both.")

    # Support global status view across all IU types.
    if args.list and not args.type and not args.add and not args.remove:
        exit_code = 0
        for iu_type in ("database", "generator", "predictor"):
            print(f"\n# {iu_type.title()}\n")
            code = _run_manager(iu_type, ["--list"])
            if code != 0:
                exit_code = code
        raise SystemExit(exit_code)

    if (args.add or args.remove) and not args.type:
        raise SystemExit("--type is required when using --add or --remove.")

    iu_type = args.type or _prompt_iu_type()

    forwarded_args: List[str] = []
    if args.list:
        forwarded_args.append("--list")
    if args.add:
        forwarded_args.extend(["--add", args.add])
    if args.remove:
        forwarded_args.extend(["--remove", args.remove])
    if args.yes:
        forwarded_args.append("--yes")

    exit_code = _run_manager(iu_type, forwarded_args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
