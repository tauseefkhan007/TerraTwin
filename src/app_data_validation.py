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

from .source_lock import audit_results, load_json, normalize_url, official_resource_urls


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


def _validate_terrain_source_lock(
    lock: dict[str, Any] | None,
    dataset: dict[str, Any] | None,
    policy: dict[str, Any] | None,
    official_catalog: dict[str, Any] | None,
    exact_products: dict[str, Any] | None,
    cache_manifest: dict[str, Any] | None,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    """Validate the narrower source lock for the imported terrain-only path.

    This lock is intentionally separate from the global multi-modal lock.  It
    certifies only that the displayed slope/roughness/relief import traces to
    the pinned NASADEM and MOLA products; it cannot unlock climate, geology,
    landing-safety, or environmental-equivalence claims.
    """

    if not isinstance(lock, dict):
        _add(errors, "dashboard/terrain_source_lock.json", "Terrain source lock must be a JSON object.")
        return {"status": "missing", "ready": False, "records": 0}

    status = lock.get("status")
    ready = lock.get("ready")
    if status != "ready":
        _add(errors, "dashboard/terrain_source_lock.json.status", "Terrain-only source lock must be ready.")
    if ready is not True:
        _add(errors, "dashboard/terrain_source_lock.json.ready", "Terrain-only source lock must expose ready=true.")
    if lock.get("scope") != "terrain_only_import":
        _add(errors, "dashboard/terrain_source_lock.json.scope", "Terrain source lock scope must be terrain_only_import.")

    earth_rows = (dataset or {}).get("earth_features", []) if isinstance(dataset, dict) else []
    mars_rows = (dataset or {}).get("planetary_targets", []) if isinstance(dataset, dict) else []
    dataset_source = (dataset or {}).get("source", {}) if isinstance(dataset, dict) else {}
    lock_dataset = lock.get("dataset") if isinstance(lock.get("dataset"), dict) else {}
    expected_record_counts = {"earth_records": len(earth_rows), "mars_records": len(mars_rows)}
    for key, expected in expected_record_counts.items():
        if lock_dataset.get(key) != expected:
            _add(errors, f"dashboard/terrain_source_lock.json.dataset.{key}", f"Expected {expected}, found {lock_dataset.get(key)!r}.")
    if expected_record_counts != {"earth_records": 49, "mars_records": 2}:
        _add(errors, "dashboard/analogx_dataset.json", "The pinned terrain import must contain exactly 49 Earth and 2 Mars records.")

    for field in ("repository", "commit"):
        if lock_dataset.get(field) != dataset_source.get(field):
            _add(errors, f"dashboard/terrain_source_lock.json.dataset.{field}", "Terrain lock must match the imported dataset source snapshot.")
    if not isinstance(lock_dataset.get("commit_date"), str) or not lock_dataset["commit_date"].strip():
        _add(errors, "dashboard/terrain_source_lock.json.dataset.commit_date", "Pinned source commit date is required.")

    raw_inventory = lock_dataset.get("raw_inventory") if isinstance(lock_dataset.get("raw_inventory"), dict) else {}
    manifest_raw = (cache_manifest or {}).get("raw_cache", {}) if isinstance(cache_manifest, dict) else {}
    expected_inventory = {
        "nasadem_hgt_tiles": manifest_raw.get("nasa_dem_hgt_tiles", {}).get("file_count"),
        "nasadem_zip_caches": manifest_raw.get("nasa_dem_zip_caches", {}).get("file_count"),
        "mola_img_files": 1,
        "mola_label_files": 1,
    }
    for key, expected in expected_inventory.items():
        if expected is None or raw_inventory.get(key) != expected:
            _add(errors, f"dashboard/terrain_source_lock.json.dataset.raw_inventory.{key}", f"Expected {expected!r}, found {raw_inventory.get(key)!r}.")
    if isinstance(cache_manifest, dict) and cache_manifest.get("source_commit") != lock_dataset.get("commit"):
        _add(errors, "data/analogx/cache_manifest.json.source_commit", "Raw cache manifest and terrain lock must point to the same pinned commit.")

    source_records = lock.get("source_records")
    if not isinstance(source_records, dict):
        _add(errors, "dashboard/terrain_source_lock.json.source_records", "Terrain lock needs Earth and Mars provenance records.")
        source_records = {}
    required_fields = tuple((policy or {}).get("required_provenance_fields", ()))
    approved_urls = set()
    if isinstance(official_catalog, dict) and isinstance(official_catalog.get("resources"), list):
        approved_urls = official_resource_urls(official_catalog)
    expected_layers = {
        "earth_elevation": {
            "resource_url": "https://search.earthdata.nasa.gov",
            "exact_product_url": "https://doi.org/10.5067/MEASURES/NASADEM/NASADEM_HGT.001",
            "version_or_product_id": "NASADEM_HGT.001",
            "product_key": "earth_elevation_nasadem_hgt_v1",
        },
        "mars_elevation": {
            "resource_url": "https://pds.nasa.gov",
            "exact_product_url": "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg004/megt90n000cb.img",
            "version_or_product_id": "MGS-M-MOLA-5-MEGDR-L3-V1",
            "product_key": "mars_elevation_mola_megdr",
        },
    }
    for layer, expected in expected_layers.items():
        record = source_records.get(layer)
        if not isinstance(record, dict):
            _add(errors, f"dashboard/terrain_source_lock.json.source_records.{layer}", "Required terrain provenance record is missing.")
            continue
        absent = [field for field in required_fields if not record.get(field)]
        if absent:
            _add(errors, f"dashboard/terrain_source_lock.json.source_records.{layer}", f"Required provenance is incomplete: {', '.join(absent)}.")
        if normalize_url(record.get("resource_url", "")) not in approved_urls:
            _add(errors, f"dashboard/terrain_source_lock.json.source_records.{layer}.resource_url", "URL is not listed on the official Resources tab.")
        for field in ("resource_url", "exact_product_url", "version_or_product_id"):
            if record.get(field) != expected[field]:
                _add(errors, f"dashboard/terrain_source_lock.json.source_records.{layer}.{field}", f"Expected the pinned official {field}.")
        product = ((exact_products or {}).get("products", {}) if isinstance(exact_products, dict) else {}).get(expected["product_key"])
        if not isinstance(product, dict):
            _add(errors, f"data/official_product_urls.json.products.{expected['product_key']}", "Pinned exact product record is missing.")
        else:
            for field in ("exact_product_url", "version_or_product_id", "approved_portal_url"):
                expected_value = expected["exact_product_url"] if field == "exact_product_url" else expected["version_or_product_id"] if field == "version_or_product_id" else expected["resource_url"]
                if product.get(field) != expected_value:
                    _add(errors, f"data/official_product_urls.json.products.{expected['product_key']}.{field}", "Exact product catalog does not match the terrain source lock.")
        snapshot_url = record.get("source_snapshot_url", "")
        if not isinstance(snapshot_url, str) or lock_dataset.get("commit", "") not in snapshot_url:
            _add(errors, f"dashboard/terrain_source_lock.json.source_records.{layer}.source_snapshot_url", "Provenance must link to the pinned repository snapshot.")

    method = lock.get("method") if isinstance(lock.get("method"), dict) else {}
    if method.get("scored_features") != ["slope", "roughness", "relief"]:
        _add(errors, "dashboard/terrain_source_lock.json.method.scored_features", "Terrain-only scoring must be limited to slope, roughness and relief.")
    if method.get("coverage_score") != 100:
        _add(errors, "dashboard/terrain_source_lock.json.method.coverage_score", "Terrain-only source coverage must be 100 for the three scored features.")
    guardrail = method.get("guardrail", "")
    if not isinstance(guardrail, str) or not all(term in guardrail.lower() for term in ("landing", "climate", "geology", "environmental")):
        _add(errors, "dashboard/terrain_source_lock.json.method.guardrail", "Terrain lock must state the non-inference guardrails.")

    return {
        "status": status,
        "ready": ready is True and status == "ready",
        "records": len(source_records),
        "earth_records": len(earth_rows),
        "mars_records": len(mars_rows),
    }


def validate_repository_data(root: Path = ROOT) -> dict[str, Any]:
    """Return a deterministic structural audit for the dashboard's data graph."""

    errors: list[dict[str, str]] = []
    analogx = _read(root, "dashboard/analogx_dataset.json", errors)
    terrain = _read(root, "dashboard/terrain_rankings.json", errors)
    target_catalog = _read(root, "dashboard/target_sites.json", errors)
    global_results = _read(root, "dashboard/global_results.json", errors)
    policy = _read(root, "data/terratwin_source_policy.json", errors)
    official_catalog = _read(root, "data/official_resources_catalog.json", errors)
    exact_products = _read(root, "data/official_product_urls.json", errors)
    cache_manifest = _read(root, "data/analogx/cache_manifest.json", errors)
    source_lock = _read(root, "dashboard/source_lock.json", errors)
    terrain_source_lock = _read(root, "dashboard/terrain_source_lock.json", errors)

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

    terrain_lock_status = _validate_terrain_source_lock(
        terrain_source_lock,
        analogx,
        policy,
        official_catalog,
        exact_products,
        cache_manifest,
        errors,
    )

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
        "terrain_source_lock": terrain_lock_status,
        "meaning": "Structural checks passed; terrain_source_lock.ready controls the imported terrain-only evidence path, while source_lock.ready separately controls multi-modal challenge evidence.",
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
