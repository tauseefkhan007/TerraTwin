"""Enforce TerraTwin's official NASA Space Apps Resources-tab source policy.

The challenge page is a catalog of approved portals, not a single downloadable
dataset. This module therefore does two things:

* records the exact resources listed on that page;
* blocks a result snapshot until every input has an exact approved-resource URL
  and the required provenance fields.

The inherited ranking snapshot intentionally fails this audit. That is safer
than presenting AWS Terrain Tiles, NASA POWER, or an untraceable geology prior
as official challenge evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "terratwin_source_policy.json"
CATALOG_PATH = ROOT / "data" / "official_resources_catalog.json"
RESULTS_PATH = ROOT / "dashboard" / "global_results.json"
DASHBOARD_AUDIT_PATH = ROOT / "dashboard" / "source_lock.json"
REAL_DATA_GLOB = "data_real/*.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_url(value: str) -> str:
    """Normalize only URL punctuation; never broaden a source match by domain."""

    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/") or ("/" if parsed.netloc else "")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def official_resource_urls(catalog: dict[str, Any]) -> set[str]:
    return {
        normalize_url(resource["resource_url"])
        for resource in catalog["resources"]
        if resource.get("listed_on_official_resources_tab") is True
    }


def missing_fields(record: dict[str, Any], required: Iterable[str]) -> list[str]:
    return sorted(field for field in required if not record.get(field))


def audit_results(
    *,
    policy: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
    results: dict[str, Any] | None = None,
    real_data_paths: Iterable[Path] | None = None,
) -> dict[str, Any]:
    policy = policy or load_json(POLICY_PATH)
    catalog = catalog or load_json(CATALOG_PATH)
    results = results or load_json(RESULTS_PATH)
    required = policy["required_provenance_fields"]
    approved_urls = official_resource_urls(catalog)
    approved_resources = [
        {
            "id": resource["id"],
            "name": resource["name"],
            "provider": resource["provider"],
            "scope": resource["scope"],
            "resource_url": resource["resource_url"],
        }
        for resource in catalog["resources"]
        if resource.get("listed_on_official_resources_tab") is True
    ]

    blocked_sources: list[dict[str, Any]] = []
    method = results.get("method", {})
    source_records = method.get("source_records")
    if not isinstance(source_records, dict):
        blocked_sources.append({
            "location": "dashboard/global_results.json:method.source_records",
            "reason": "The result snapshot has no per-layer provenance record with an exact official resource URL.",
        })
        for layer, value in method.get("data", {}).items():
            blocked_sources.append({
                "location": f"dashboard/global_results.json:method.data.{layer}",
                "value": value,
                "reason": "Inherited source description cannot be verified against an exact URL listed on the official Resources tab.",
            })
    else:
        data_layers = set(method.get("data", {}))
        record_layers = set(source_records)
        for missing_layer in sorted(data_layers - record_layers):
            blocked_sources.append({
                "location": f"method.source_records.{missing_layer}",
                "reason": "Every displayed method layer must have its own exact official resource URL and provenance record.",
            })
        for layer, record in source_records.items():
            if not isinstance(record, dict):
                blocked_sources.append({"location": f"method.source_records.{layer}", "reason": "Record must be an object."})
                continue
            resource_url = record.get("resource_url", "")
            if normalize_url(resource_url) not in approved_urls:
                blocked_sources.append({
                    "location": f"method.source_records.{layer}.resource_url",
                    "value": resource_url,
                    "reason": "URL is not listed on the official Resources tab.",
                })
            absent = missing_fields(record, required)
            if absent:
                blocked_sources.append({
                    "location": f"method.source_records.{layer}",
                    "missing_fields": absent,
                    "reason": "Required provenance is incomplete.",
                })

    missing_provenance: list[dict[str, Any]] = []
    paths = list(real_data_paths) if real_data_paths is not None else sorted(ROOT.glob(REAL_DATA_GLOB))
    for path in paths:
        record = load_json(path)
        absent = missing_fields(record, required)
        if absent:
            missing_provenance.append({"file": str(path.relative_to(ROOT)), "missing_fields": absent})
        resource_url = record.get("resource_url")
        if resource_url and normalize_url(resource_url) not in approved_urls:
            blocked_sources.append({
                "location": str(path.relative_to(ROOT)),
                "value": resource_url,
                "reason": "URL is not listed on the official Resources tab.",
            })

    ready = not blocked_sources and not missing_provenance
    if ready:
        status = "ready"
        message = "Every displayed input has an exact official Resources-tab URL and complete provenance."
    else:
        status = "blocked_inherited_baseline"
        message = "Numeric ranking results are development fixtures and are hidden from final evidence until every input is re-ingested from an approved Resources-tab resource."

    return {
        "status": status,
        "ready": ready,
        "audited_on": date.today().isoformat(),
        "official_resources_url": policy["official_resources_url"],
        "message": message,
        "approved_resources": approved_resources,
        "blocked_sources": blocked_sources,
        "missing_provenance": missing_provenance,
        "required_provenance_fields": required,
        "next_step": "Select exact products from the listed portals, download them, record the required provenance fields, regenerate global_results.json, and rerun this audit.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-dashboard", action="store_true", help="write dashboard/source_lock.json")
    args = parser.parse_args()
    audit = audit_results()
    if args.write_dashboard:
        DASHBOARD_AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {DASHBOARD_AUDIT_PATH.relative_to(ROOT)}")
    print(json.dumps(audit, indent=2))
    return 0 if audit["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
