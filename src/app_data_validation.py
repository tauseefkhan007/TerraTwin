"""Validate the static data artifacts consumed by the NAKSH dashboard.

This is deliberately separate from :mod:`src.source_lock`.  A structurally
valid JSON artifact is not automatically an officially verified science
artifact: ``source_lock.py`` owns that second, stricter decision.  Keeping the
checks separate lets the dashboard say exactly whether a file is malformed,
provisional, or source-verified.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .source_lock import audit_results, load_json


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
DATA = ROOT / "data"


class DataValidationError(ValueError):
    """Raised by callers that request fail-fast validation."""


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _add(errors: list[dict[str, str]], location: str, reason: str) -> None:
    errors.append({"location": location, "reason": reason})


def _read(root: Path, relative: str, errors: list[dict[str, str]]) -> Any | None:
    path = root / relative
    try:
        return load_json(path)
    except FileNotFoundError:
        _add(errors, relative, "Required JSON artifact is missing.")
    except (OSError, json.JSONDecodeError) as error:
        _add(errors, relative, f"JSON could not be read: {error}.")
    return None


def _check_coordinates(
    record: dict[str, Any],
    location: str,
    errors: list[dict[str, str]],
    *,
    longitude_max: float = 180.0,
) -> None:
    lat = record.get("lat")
    lon = record.get("lon")
    if not _finite(lat) or not -90 <= float(lat) <= 90:
        _add(errors, location, "Latitude must be a finite value in [-90, 90].")
    if not _finite(lon) or not -180 <= float(lon) <= longitude_max:
        _add(errors, location, f"Longitude must be a finite value in [-180, {longitude_max}].")


def _check_feature_fields(
    record: dict[str, Any],
    location: str,
    errors: list[dict[str, str]],
    fields: tuple[str, ...] = ("slope", "roughness", "relief"),
) -> None:
    for field in fields:
        value = record.get(field)
        if not _finite(value) or float(value) < 0:
            _add(errors, f"{location}.{field}", "Feature must be a finite non-negative number.")


def _validate_analogx(
    dataset: dict[str, Any] | None,
    errors: list[dict[str, str]],
) -> dict[str, int]:
    if not isinstance(dataset, dict):
        return {}
    earth = dataset.get("earth_features")
    targets = dataset.get("planetary_targets")
    demos = dataset.get("demo_earth_candidates")
    if not isinstance(earth, list) or not isinstance(targets, list) or not isinstance(demos, list):
        _add(errors, "dashboard/analogx_dataset.json", "earth_features, planetary_targets and demo_earth_candidates must be arrays.")
        return {}

    counts = dataset.get("counts", {})
    expected_counts = {
        "earth_feature_records": len(earth),
        "planetary_target_records": len(targets),
        "demo_candidate_records": len(demos),
    }
    for key, actual in expected_counts.items():
        if counts.get(key) != actual:
            _add(errors, f"dashboard/analogx_dataset.json.counts.{key}", f"Expected {actual}, found {counts.get(key)!r}.")

    earth_names: list[str] = []
    for index, row in enumerate(earth):
        location = f"dashboard/analogx_dataset.json.earth_features[{index}]"
        if not isinstance(row, dict):
            _add(errors, location, "Earth feature must be an object.")
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            _add(errors, f"{location}.name", "Earth feature needs a non-empty name.")
        else:
            earth_names.append(name)
        _check_coordinates(row, location, errors)
        _check_feature_fields(row, location, errors)
        for field in ("elevation",):
            if not _finite(row.get(field)):
                _add(errors, f"{location}.{field}", "Context field must be a finite number.")
        for field in ("country", "description", "data_source"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                _add(errors, f"{location}.{field}", "Required descriptive field is missing.")

    if len(earth_names) != len(set(earth_names)):
        _add(errors, "dashboard/analogx_dataset.json.earth_features", "Earth feature names must be unique.")

    target_ids: list[str] = []
    for index, row in enumerate(targets):
        location = f"dashboard/analogx_dataset.json.planetary_targets[{index}]"
        if not isinstance(row, dict):
            _add(errors, location, "Planetary target must be an object.")
            continue
        target_id = row.get("id")
        if not isinstance(target_id, str) or not target_id.strip():
            _add(errors, f"{location}.id", "Planetary target needs a non-empty id.")
        else:
            target_ids.append(target_id)
        if row.get("world") != "Mars":
            _add(errors, f"{location}.world", "The imported planetary target table is expected to contain Mars records only.")
        _check_coordinates(row, location, errors, longitude_max=360.0)
        _check_feature_fields(row, location, errors)
        if not _finite(row.get("elevation")):
            _add(errors, f"{location}.elevation", "Context field must be a finite number.")
        for field in ("name", "data_source"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                _add(errors, f"{location}.{field}", "Required descriptive field is missing.")

    if len(target_ids) != len(set(target_ids)):
        _add(errors, "dashboard/analogx_dataset.json.planetary_targets", "Planetary target ids must be unique.")
    if set(earth_names) & set(target_ids):
        _add(errors, "dashboard/analogx_dataset.json", "Earth names and planetary target ids unexpectedly overlap.")

    source = dataset.get("source")
    if not isinstance(source, dict) or source.get("source_lock_status") != "development_import_pending_official_resources_audit":
        _add(errors, "dashboard/analogx_dataset.json.source.source_lock_status", "Imported repository data must remain explicitly provisional until source audit passes.")
    return {
        "earth_feature_records": len(earth),
        "planetary_target_records": len(targets),
        "demo_candidate_records": len(demos),
    }


def _validate_terrain_rankings(
    rankings: dict[str, Any] | None,
    dataset: dict[str, Any] | None,
    errors: list[dict[str, str]],
) -> dict[str, int]:
    if not isinstance(rankings, dict):
        return {}
    targets = rankings.get("targets")
    ranking_map = rankings.get("rankings")
    if not isinstance(targets, list) or not isinstance(ranking_map, dict):
        _add(errors, "dashboard/terrain_rankings.json", "targets must be an array and rankings must be an object.")
        return {}
    source_target_ids = {
        row.get("id") for row in (dataset or {}).get("planetary_targets", []) if isinstance(row, dict)
    }
    target_ids = [row.get("id") for row in targets if isinstance(row, dict)]
    if set(target_ids) != source_target_ids:
        _add(errors, "dashboard/terrain_rankings.json.targets", "Ranking targets must exactly match imported planetary target ids.")
    expected_earth_count = len((dataset or {}).get("earth_features", []))
    counts = rankings.get("counts", {})
    if counts.get("earth_records") != expected_earth_count:
        _add(errors, "dashboard/terrain_rankings.json.counts.earth_records", f"Expected {expected_earth_count}, found {counts.get('earth_records')!r}.")
    if counts.get("mars_targets") != len(target_ids):
        _add(errors, "dashboard/terrain_rankings.json.counts.mars_targets", f"Expected {len(target_ids)}, found {counts.get('mars_targets')!r}.")

    for target_id in sorted(source_target_ids):
        rows = ranking_map.get(target_id)
        if not isinstance(rows, list) or len(rows) != expected_earth_count:
            _add(errors, f"dashboard/terrain_rankings.json.rankings.{target_id}", f"Expected {expected_earth_count} ranking rows.")
            continue
        ranks = [row.get("rank") for row in rows if isinstance(row, dict)]
        scores = [row.get("score") for row in rows if isinstance(row, dict)]
        if ranks != list(range(1, expected_earth_count + 1)):
            _add(errors, f"dashboard/terrain_rankings.json.rankings.{target_id}.rank", "Ranks must be contiguous from 1.")
        if any(not _finite(score) or not 0 <= float(score) <= 100 for score in scores):
            _add(errors, f"dashboard/terrain_rankings.json.rankings.{target_id}.score", "Terrain scores must be finite values in [0, 100].")
        if scores != sorted(scores, reverse=True):
            _add(errors, f"dashboard/terrain_rankings.json.rankings.{target_id}", "Rows must be sorted by descending score.")
        if any(not isinstance(row, dict) or not isinstance(row.get("site_name"), str) for row in rows):
            _add(errors, f"dashboard/terrain_rankings.json.rankings.{target_id}", "Every row needs a site_name.")
    return {"ranking_targets": len(target_ids), "ranking_rows_per_target": expected_earth_count}


def _validate_target_catalog(payload: dict[str, Any] | None, errors: list[dict[str, str]]) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    sites = payload.get("target_sites")
    matches_by_body = payload.get("analog_matches")
    if not isinstance(sites, list) or not isinstance(matches_by_body, dict):
        _add(errors, "dashboard/target_sites.json", "target_sites and analog_matches are required.")
        return {}
    site_ids: set[str] = set()
    body_counts: Counter[str] = Counter()
    for index, site in enumerate(sites):
        location = f"dashboard/target_sites.json.target_sites[{index}]"
        if not isinstance(site, dict):
            _add(errors, location, "Target site must be an object.")
            continue
        site_id = site.get("id")
        body = site.get("body")
        if not isinstance(site_id, str) or not site_id.strip() or site_id in site_ids:
            _add(errors, f"{location}.id", "Target site ids must be non-empty and unique.")
        else:
            site_ids.add(site_id)
        if body not in {"Moon", "Mars"}:
            _add(errors, f"{location}.body", "Body must be Moon or Mars.")
        else:
            body_counts[body] += 1
        _check_coordinates(site, location, errors, longitude_max=360.0)
        for field in ("name", "short_description", "mission_relevance", "source_note"):
            if not isinstance(site.get(field), str) or not site[field].strip():
                _add(errors, f"{location}.{field}", "Required target-site context is missing.")
        if site.get("coords_approximate") is not True:
            _add(errors, f"{location}.coords_approximate", "Target catalogue coordinates must be labelled approximate.")

    legacy_ids = {"atacama", "mcmurdo", "haughton", "iceland", "hawaii"}
    for body_key in ("moon", "mars"):
        matches = matches_by_body.get(body_key)
        if not isinstance(matches, list) or len(matches) != len(legacy_ids):
            _add(errors, f"dashboard/target_sites.json.analog_matches.{body_key}", "Every Earth analog must have one mapping per body.")
            continue
        seen: set[str] = set()
        for index, match in enumerate(matches):
            location = f"dashboard/target_sites.json.analog_matches.{body_key}[{index}]"
            if not isinstance(match, dict):
                _add(errors, location, "Analog match must be an object.")
                continue
            analog_id = match.get("earth_analog_id")
            target_id = match.get("target_site_id")
            target = next((site for site in sites if isinstance(site, dict) and site.get("id") == target_id), None)
            if analog_id not in legacy_ids or analog_id in seen:
                _add(errors, f"{location}.earth_analog_id", "Analog id must be unique and belong to the five qualitative analog records.")
            if not isinstance(target, dict) or target.get("body", "").lower() != body_key:
                _add(errors, f"{location}.target_site_id", "Mapped target does not belong to the selected body.")
            if not isinstance(match.get("shared_features"), list) or not match["shared_features"]:
                _add(errors, f"{location}.shared_features", "At least one shared feature is required.")
            seen.add(analog_id)
    return {"target_sites": len(sites), "moon_targets": body_counts["Moon"], "mars_targets": body_counts["Mars"]}


def _validate_global_results(payload: dict[str, Any] | None, errors: list[dict[str, str]]) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    sites = payload.get("sites")
    targets = payload.get("targets")
    if not isinstance(sites, list) or not isinstance(targets, list):
        _add(errors, "dashboard/global_results.json", "sites and targets are required arrays.")
        return {}
    site_ids = {site.get("id") for site in sites if isinstance(site, dict)}
    target_ids = {target.get("id") for target in targets if isinstance(target, dict)}
    for index, site in enumerate(sites):
        location = f"dashboard/global_results.json.sites[{index}]"
        if not isinstance(site, dict):
            _add(errors, location, "Site must be an object.")
            continue
        _check_coordinates(site, location, errors)
        if site.get("category") not in {"benchmark", "emerging", "control"}:
            _add(errors, f"{location}.category", "Site category is invalid.")
    for target in targets:
        if not isinstance(target, dict):
            continue
        target_id = target.get("id")
        target_body = target.get("body")
        rows = target.get("rankings")
        if target_body not in {"moon", "mars"}:
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.body", "Target body must be moon or mars.")
        if not isinstance(rows, list) or len(rows) != len(site_ids):
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.rankings", f"Expected {len(site_ids)} rows.")
            continue
        ranks = [row.get("rank") for row in rows if isinstance(row, dict)]
        if ranks != list(range(1, len(site_ids) + 1)):
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.rankings.rank", "Ranks must be contiguous from 1.")
        acis = [row.get("aci") for row in rows if isinstance(row, dict)]
        if any(not _finite(value) or not 0 <= float(value) <= 100 for value in acis):
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.rankings.aci", "ACI values must be finite values in [0, 100].")
        if acis != sorted(acis, reverse=True):
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.rankings", "Rows must be sorted by descending ACI.")
        row_site_ids = {row.get("site_id") for row in rows if isinstance(row, dict)}
        if row_site_ids != site_ids:
            _add(errors, f"dashboard/global_results.json.targets.{target_id}.rankings.site_id", "Ranking site ids must exactly match the site catalog.")
    if len(site_ids) != len(sites) or len(target_ids) != len(targets):
        _add(errors, "dashboard/global_results.json", "Site and target ids must be unique.")
    return {"global_sites": len(sites), "global_targets": len(targets)}


def validate_repository_data(root: Path = ROOT) -> dict[str, Any]:
    """Return a deterministic structural audit for the dashboard's data graph."""

    errors: list[dict[str, str]] = []
    analogx = _read(root, "dashboard/analogx_dataset.json", errors)
    terrain = _read(root, "dashboard/terrain_rankings.json", errors)
    target_catalog = _read(root, "dashboard/target_sites.json", errors)
    global_results = _read(root, "dashboard/global_results.json", errors)
    policy = _read(root, "data/terratwin_source_policy.json", errors)
    official_catalog = _read(root, "data/official_resources_catalog.json", errors)
    source_lock = _read(root, "dashboard/source_lock.json", errors)

    counts: dict[str, int] = {}
    counts.update(_validate_analogx(analogx, errors))
    counts.update(_validate_terrain_rankings(terrain, analogx, errors))
    counts.update(_validate_target_catalog(target_catalog, errors))
    counts.update(_validate_global_results(global_results, errors))

    if isinstance(policy, dict) and isinstance(official_catalog, dict):
        if policy.get("official_resources_url") != official_catalog.get("source_page_url"):
            _add(errors, "data/official_resources_catalog.json.source_page_url", "Official resources URL must match the source policy.")
        resources = official_catalog.get("resources", [])
        urls = [resource.get("resource_url") for resource in resources if isinstance(resource, dict)]
        if len(urls) != len(set(urls)):
            _add(errors, "data/official_resources_catalog.json.resources", "Official resource URLs must be unique.")
        if not resources or not all(resource.get("listed_on_official_resources_tab") is True for resource in resources if isinstance(resource, dict)):
            _add(errors, "data/official_resources_catalog.json.resources", "Every catalog resource must be explicitly marked as listed on the official tab.")

    source_lock_status = source_lock.get("status") if isinstance(source_lock, dict) else "missing"
    if isinstance(source_lock, dict) and not isinstance(source_lock.get("ready"), bool):
        _add(errors, "dashboard/source_lock.json.ready", "Source lock must expose a boolean ready field.")

    source_audit = None
    try:
        source_audit = audit_results()
    except (OSError, KeyError, TypeError, ValueError) as error:
        _add(errors, "src/source_lock.py", f"Source-lock audit could not run: {error}.")

    return {
        "schema_version": 1,
        "generated_on": date.today().isoformat(),
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "counts": counts,
        "source_lock": {
            "status": source_lock_status,
            "ready": bool(source_lock.get("ready")) if isinstance(source_lock, dict) else False,
            "blocked_sources": len(source_audit.get("blocked_sources", [])) if isinstance(source_audit, dict) else None,
            "missing_provenance": len(source_audit.get("missing_provenance", [])) if isinstance(source_audit, dict) else None,
        },
        "meaning": "Structural checks passed; source_lock.ready still controls whether numeric multi-modal results may be presented as official challenge evidence.",
    }


def write_dashboard_audit(root: Path = ROOT) -> dict[str, Any]:
    audit = validate_repository_data(root)
    destination = root / "dashboard" / "data_audit.json"
    destination.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-dashboard", action="store_true", help="write dashboard/data_audit.json")
    args = parser.parse_args()
    audit = write_dashboard_audit() if args.write_dashboard else validate_repository_data()
    if args.write_dashboard:
        print("wrote dashboard/data_audit.json")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
