"""Build terrain-only rankings from the imported Earth and Mars feature tables.

The cross-body score deliberately uses slope, roughness and relief. Absolute
elevation is retained as context but excluded from similarity because Earth and
Mars elevations use different planetary datums.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .analogx_dataset import SOURCE_COMMIT, SOURCE_REPOSITORY, load_earth_features, load_planetary_targets, validate_dataset


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "dashboard" / "terrain_rankings.json"
FEATURES = ("slope", "roughness", "relief")


def _log_delta(left: float, right: float) -> float:
    return abs(math.log1p(max(0.0, left)) - math.log1p(max(0.0, right)))


def terrain_similarity(earth: dict[str, Any], target: dict[str, Any]) -> tuple[float, dict[str, float]]:
    components = {
        "slope": abs(float(earth["slope"]) - float(target["slope"])) / max(1.0, abs(float(target["slope"]))),
        "roughness": _log_delta(float(earth["roughness"]), float(target["roughness"])),
        "relief": _log_delta(float(earth["relief"]), float(target["relief"])),
    }
    distance = sum(components.values()) / len(FEATURES)
    score = 100.0 * math.exp(-distance)
    return round(score, 2), {key: round(value, 4) for key, value in components.items()}


def build_payload() -> dict[str, Any]:
    earth = load_earth_features()
    targets = load_planetary_targets()
    validate_dataset(earth, targets)
    rankings: dict[str, list[dict[str, Any]]] = {}
    for target in targets:
        rows = []
        for site in earth:
            score, components = terrain_similarity(site, target)
            rows.append({
                "site_name": site["name"],
                "country": site["country"],
                "lat": site["lat"],
                "lon": site["lon"],
                "score": score,
                "distance_components": components,
                "features": {key: site[key] for key in ("elevation", *FEATURES)},
            })
        rows.sort(key=lambda row: row["score"], reverse=True)
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        rankings[target["id"]] = rows
    return {
        "schema_version": 1,
        "dataset_id": "terrain-feature-similarity-v1",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "earth_product": "NASADEM_HGT.001",
            "mars_product": "MGS MOLA MEGDR",
            "status": "repository_import_terrain_only",
        },
        "method": {
            "scored_features": list(FEATURES),
            "excluded_context_features": {"elevation": "Earth and Mars elevations use different planetary datums."},
            "formula": "100 * exp(-mean(slope_relative_delta, log1p_roughness_delta, log1p_relief_delta))",
            "coverage_score": 100,
            "guardrail": "Terrain similarity is not a landing-site safety assessment or a claim of environmental equivalence.",
        },
        "counts": {"earth_records": len(earth), "mars_targets": len(targets)},
        "targets": targets,
        "rankings": rankings,
    }


def main() -> int:
    OUTPUT_PATH.write_text(json.dumps(build_payload(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
