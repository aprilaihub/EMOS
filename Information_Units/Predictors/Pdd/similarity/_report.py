"""Lightweight progress/warning collector shared by the pipeline stages."""

from __future__ import annotations

import logging

_log = logging.getLogger("emos.pdd.similarity")
_log.addHandler(logging.NullHandler())  # no implicit stderr output; users opt in via logging config


class Reporter:
    """Collect warnings (for ``run_info.json``) and optionally print progress."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.warnings: list[str] = []

    def info(self, message: str) -> None:
        _log.info(message)
        if self.verbose:
            print(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        _log.warning(message)
        if self.verbose:
            print(f"WARNING: {message}")
