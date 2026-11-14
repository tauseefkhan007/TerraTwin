"""Load and validate the complete AnalogX tabular dataset import.

The upstream repository contains a large raw NASADEM cache. NAKSH keeps the
reproducible feature tables in-repo and records the raw-cache inventory in
``data/analogx/cache_manifest.json`` instead of duplicating several gigabytes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "analogx"
DASHBOARD_PATH = ROOT / "dashboard" / "analogx_dataset.json"
SOURCE_REPOSITORY = "https://github.com/hazraanirban2006-boop/analogx-hackathon-ready"
SOURCE_COMMIT = "76f3dbf1f418eb36cf244033468c8d2fcc249bfa"

EARTH_NUMERIC_FIELDS = ("lat", "lon", "elevation", "slope", "roughness", "relief")
TARGET_NUMERIC_FIELDS = EARTH_NUMERIC_FIELDS
DEMO_NUMERIC_FIELDS = ("lat", "lon", "elevation", "slope", "roughness", "temperature", "geology")


def _read_csv(path: Path, numeric_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for field in numeric_fields:
                row[field] = float(row[field])
            rows.append(row)
    return rows


def load_earth_features() -> list[dict[str, Any]]:
    return _read_csv(DATA_DIR / "earth_features.csv", EARTH_NUMERIC_FIELDS)


def load_planetary_targets() -> list[dict[str, Any]]:
    return _read_csv(DATA_DIR / "planetary_targets.csv", TARGET_NUMERIC_FIELDS)


def load_demo_candidates() -> list[dict[str, Any]]:
    return _read_csv(DATA_DIR / "demo_earth_candidates.csv", DEMO_NUMERIC_FIELDS)


def load_sensitivity_audit() -> str:
    path = DATA_DIR / "sensitivity_results.txt"
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path.name}")


def validate_dataset(
    earth: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    demo: list[dict[str, Any]] | None = None,
) -> None:
    if len(earth) != 49:
        raise ValueError(f"Expected 49 Earth feature records, found {len(earth)}")
    if len(targets) != 2:
        raise ValueError(f"Expected 2 planetary target records, found {len(targets)}")
    if demo is not None and len(demo) != 10:
        raise ValueError(f"Expected 10 demo Earth candidate records, found {len(demo)}")
    names = [str(row["name"]) for row in earth]
    if len(names) != len(set(names)):
        raise ValueError("Earth feature records contain duplicate names")
    for group_name, records, fields in (
        ("Earth", earth, EARTH_NUMERIC_FIELDS),
        ("target", targets, TARGET_NUMERIC_FIELDS),
        ("demo", demo or [], DEMO_NUMERIC_FIELDS),
    ):
        for row in records:
            for field in fields:
                if not math.isfinite(float(row[field])):
                    raise ValueError(f"{group_name} record {row.get('name', row.get('id'))} has non-finite {field}")


def dashboard_payload() -> dict[str, Any]:
    earth = load_earth_features()
    targets = load_planetary_targets()
    demo = load_demo_candidates()
    sensitivity_audit = load_sensitivity_audit()
    validate_dataset(earth, targets, demo)
    return {
        "schema_version": 1,
        "dataset_id": "analogx-nasa-terrain-v1",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "earth_table": "backend/data/nasa/earth_features.csv",
            "target_table": "backend/data/nasa/planetary_targets.csv",
            "earth_product": "NASADEM_HGT.001",
            "planetary_product": "NASA/JPL MGS MOLA MEGDR",
            "source_lock_status": "development_import_pending_official_resources_audit",
        },
        "counts": {
            "earth_feature_records": len(earth),
            "planetary_target_records": len(targets),
            "demo_candidate_records": len(demo),
            "sensitivity_audit_characters": len(sensitivity_audit),
            "raw_hgt_tiles": 150,
            "raw_zip_caches": 150,
        },
        "earth_features": earth,
        "planetary_targets": targets,
        "demo_earth_candidates": demo,
        "sensitivity_audit": sensitivity_audit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-dashboard", action="store_true")
    args = parser.parse_args()
    payload = dashboard_payload()
    if args.write_dashboard:
        DASHBOARD_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {DASHBOARD_PATH.relative_to(ROOT)}")
    else:
        print(json.dumps({"counts": payload["counts"], "source": payload["source"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
