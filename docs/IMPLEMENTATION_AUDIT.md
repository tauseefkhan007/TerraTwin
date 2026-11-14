# NAKSH / TerraTwin implementation audit

**Audit date:** 2026-11-15  
**Scope:** `PRD.md`, `Architecture.md`, the static dashboard, the imported terrain artifacts, the source-policy gate and the optional FastAPI service.

## Executive result

The application now has one explicit data-integrity audit and three visibly separate evidence states:

1. **Imported terrain records:** 49 Earth feature records and 2 Mars terrain targets from the pinned repository import. These are source-verified for terrain-only screening in Global Search and Earth browse mode through the separate `terrain_source_lock.json` path.
2. **Synthetic demo:** the original five-site Explore Sites flow remains usable for the live demonstration: Moon/Mars JSON result tables, radar chart, what-if controls and procedural 3D meshes. Its labels and provenance state that it is synthetic demo data.
3. **Multi-modal inherited baseline:** the 33-site, 8-target ranking workspace remains source-locked. It cannot be presented as official challenge evidence until every input has an exact approved Resources-tab URL and complete provenance.

This is the scientifically safe interpretation of the PRD: the demo is functional, the imported dataset is visible, and no unverified score is silently promoted to a final result.

## Findings and fixes

| Area | Finding | Resolution |
| --- | --- | --- |
| Body separation | Earth browse records, Moon target catalogue records and Mars target catalogue records were available through different paths and could look interchangeable. | `getVisibleSites()` now uses only imported Earth records in Earth mode; Moon/Mars map markers use their own body-specific target catalogue. Backend candidate endpoints apply the same body filter. |
| Data graph | There were competing legacy, imported-terrain and global-result JSON paths without one structural check. | Added `src/app_data_validation.py`, generated `dashboard/data_audit.json`, and added regression tests for counts, ids, coordinates, ranks, bodies and score bounds. |
| Explore Sites regression | The imported loader replaced the legacy site array, so the old five-site demo result validator no longer matched and the demo stopped loading. | Legacy result validation now targets the five qualitative demo records only; the imported 49-record list is kept as a separate Earth browse source. The demo ACI/radar/what-if flow is initialized even while official source lock is pending. |
| Source status | The UI could show a stale score table without making the distinction clear. | Synthetic scores are labelled “synthetic demo”; imported terrain scores say “source-verified terrain-only”; the multi-modal ranking workspace stays gated. |
| Coverage | Imported terrain views used a hard-coded `100%` statement. | Coverage is calculated from the loaded Earth rows for slope, roughness and relief and rendered in the validation view and Global Search summary. |
| Backend | FastAPI only exposed OAuth/authentication endpoints, while the architecture described scientific API extraction points. | Added read-only `/api/datasets`, `/api/methodology`, `/api/candidates`, `/api/candidates/{id}` and `/api/candidates/{id}/comparison`. Provisional scores are returned separately from verified scores. |
| Grounded guardrails | The Global Search guardrail referred generically to “lunar/Martian” conditions. | The report now names the selected target body and keeps the gravity/pressure/radiation/subsurface limitation visible. |

## Source-policy result

The structural data audit passes. The terrain-only source lock is ready, while the broader official source lock remains intentionally blocked:

- structural audit: `pass`
- source lock: `blocked_inherited_baseline`
- blocked source checks: 6
- files missing required provenance: 3
- terrain source lock: `ready` (49 Earth records, 2 Mars targets, slope/roughness/relief only)

The broader lock is not a frontend failure. It correctly prevents the inherited multi-modal result snapshot from being called official challenge evidence. The terrain lock is a narrower claim: its pinned NASADEM DOI and MOLA image provenance supports only the imported slope/roughness/relief comparison. Climate, geology, radiation, landing safety and environmental equivalence remain unverified. The exact official Resources-tab URL and selected NASA product endpoints are recorded in `data/official_product_urls.json`.

## Verification performed

```text
72 Python unit tests: OK
2 browser tests: skipped because Playwright/browser is not installed in this environment
dashboard/global-search.js: Node syntax check: OK
dashboard/index.html: inline JavaScript VM syntax check: OK
git diff --check: OK
```

Run locally:

```bash
./.venv/bin/python -m src.app_data_validation --write-dashboard
./.venv/bin/python -m src.source_lock --write-dashboard
./.venv/bin/python -m unittest discover -s tests -v
```

## Live-demo contract

- Use **Explore Sites** for the clearly labelled synthetic interaction demo.
- Use **Global Search** for the 49-record imported terrain inventory and source-verified terrain-only comparisons.
- Use the source-lock panel and the approved Resources-tab links when presenting provenance.
- Do not claim the inherited multi-modal scores are final until the source lock changes to `ready`.
