"""Utilities for loading modular property mappings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

_MAPPINGS_ROOT = Path(__file__).resolve().parent
_COMMON_FILE = _MAPPINGS_ROOT / "common_properties.json"
_SOURCES_ROOT = _MAPPINGS_ROOT / "sources"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _discover_source_types() -> list[str]:
    if not _SOURCES_ROOT.exists():
        return []
    return sorted(
        item.name
        for item in _SOURCES_ROOT.iterdir()
        if item.is_dir()
    )


def _discover_sources_by_type(source_type: str) -> list[str]:
    folder = _SOURCES_ROOT / source_type
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Unknown source_type '{source_type}'")
    return sorted(path.stem for path in folder.glob("*.json"))


def _build_source_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for source_type in _discover_source_types():
        for source in _discover_sources_by_type(source_type):
            if source in index:
                raise ValueError(
                    "Duplicate source mapping name discovered in multiple source types: "
                    f"'{source}'"
                )
            index[source] = source_type
    return index


def load_common_properties() -> dict:
    """Load canonical property definitions."""
    return _read_json(_COMMON_FILE)


def _source_file_path(source_type: str, source: str) -> Path:
    return _SOURCES_ROOT / source_type / f"{source}.json"


def load_source_mapping_file(source: str, source_type: str | None = None) -> dict:
    """Load one source mapping file."""
    resolved_type = source_type
    if resolved_type is None:
        source_index = _build_source_index()
        resolved_type = source_index.get(source)

    if not resolved_type:
        raise ValueError(f"Unknown source '{source}'")

    path = _source_file_path(resolved_type, source)
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found for source '{source}': {path}")
    return _read_json(path)


def load_source_property_mapping(source: str, source_type: str | None = None) -> dict:
    """Return source mapping as {common_name: source_config} for one source."""
    payload = load_source_mapping_file(source=source, source_type=source_type)
    return payload.get("properties", {})


def iter_source_files(source_type: str | None = None) -> Iterable[Path]:
    """Yield source mapping files by group or across all groups."""
    source_types = [source_type] if source_type else _discover_source_types()

    for group in source_types:
        for source in _discover_sources_by_type(group):
            yield _source_file_path(group, source)


def load_merged_property_mappings(
    source_type: str | None = None,
    sources: Iterable[str] | None = None,
) -> dict:
    """Merge modular files into the legacy schema used across EMOS."""
    common = load_common_properties()
    merged = {
        "description": "Merged view of modular property mappings.",
        "version": common.get("version", "2.0"),
        "properties": {
            name: dict(details)
            for name, details in common.get("properties", {}).items()
        },
    }

    if sources is not None:
        source_payloads = [load_source_mapping_file(source=s) for s in sources]
    else:
        source_payloads = [_read_json(path) for path in iter_source_files(source_type=source_type)]

    for payload in source_payloads:
        source = payload.get("source")
        if not source:
            continue

        for common_name, source_cfg in payload.get("properties", {}).items():
            if common_name not in merged["properties"]:
                merged["properties"][common_name] = {}
            merged["properties"][common_name][source] = source_cfg

    return merged
