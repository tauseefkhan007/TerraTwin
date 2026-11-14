# TerraTwin Technical Architecture

**Product:** TerraTwin  
**Version:** Hackathon MVP  
**Primary constraint:** Deliver a reliable scientific prototype in approximately two days

## Implemented stack for this branch

TerraTwin is currently a fast static-data MVP with an optional local FastAPI service, not a deployed React application:

- **Scientific pipeline:** Python 3.10+, NumPy, SciPy, rasterio, pyproj and Pillow.
- **Application UI:** static HTML, CSS and vanilla JavaScript.
- **Mapping and charts:** Leaflet and Chart.js loaded from public CDNs.
- **Feature store:** cached JSON/GeoJSON and local files; SQLite is the planned compact application database once the source-compliant catalog is locked.
- **Authentication:** small FastAPI service with GitHub/Google OAuth, signed HTTP-only session cookies and environment-only provider credentials.
- **Collaboration:** GitHub branches and pull requests.
- **Source policy:** final evidence may use only the official NASA Space Apps 2026 Resources tab; the imported terrain path has its own NASADEM/MOLA lock, while inherited multi-modal inputs remain blocked.

The current demo still runs as static HTML/CSS/JavaScript. FastAPI now exposes read-only dataset, methodology, candidate and comparison endpoints in addition to the optional Google/GitHub sign-in flow; a React client remains a future extraction path.

## 1. Architecture objectives

TerraTwin must be:

- Scientifically traceable.
- Simple enough for a six-person hackathon team.
- Fast enough for a live demonstration.
- Modular enough to replace prepared data with live ingestion later.
- Explicit about data coverage, uncertainty and limitations.

The MVP is a modular monolith with offline geospatial preprocessing and a static dashboard reading precomputed result JSON. Microservices, streaming infrastructure, a live API and real-time global raster processing are out of scope for the MVP.

## 2. High-level architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                    External scientific sources               │
│  NASA Earthdata │ NASA Worldview │ NASA PDS/LRO │ ESA/CSA/JAXA │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Offline ingestion and preprocessing              │
│  Download │ crop │ reproject │ resample │ quality checks      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Feature and evidence store                 │
│  GeoJSON │ GeoTIFF │ Parquet │ JSON │ SQLite                  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  Deterministic scoring engine                 │
│  normalization │ weighted distance │ coverage │ confidence    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────┴───────────────────────────────┐
│               Optional FastAPI extraction                      │
│ candidates │ comparisons │ rankings │ datasets │ methodology  │
└──────────────────────────────┬───────────────────────────────┘
                               │ JSON/GeoJSON
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Static HTML/CSS/JavaScript dashboard              │
│ map │ rankings │ comparison charts │ reports │ explanations   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                       Researcher / judge
```

## 3. System components

### 3.0 Application/API boundary

The static dashboard is the primary presentation layer and reads the validated JSON artifacts directly for an offline demo. The optional FastAPI service exposes the same evidence state through:

- `/api/datasets` for source-lock and structural-audit status;
- `/api/methodology` for the formula and required guardrails;
- `/api/candidates` and `/api/candidates/{id}` for body-separated records;
- `/api/candidates/{id}/comparison` for terrain-only evidence with explicit global-versus-terrain status.

`dashboard/terrain_source_lock.json` independently certifies the 49 Earth and 2 Mars imported records for slope, roughness and relief. When it is ready but the global source lock is blocked, comparison responses keep the multi-modal `similarity_score` null and place the source-verified terrain value in `terrain_similarity_score` with status `source_verified_terrain_only`. If the terrain audit is also unavailable, the value is kept in `provisional_similarity_score`.

### 3.1 Authentication boundary

The dashboard has a local demo path and an optional OAuth path. When the FastAPI auth service is running, GitHub and Google buttons redirect to the provider, validate a one-time state value, fetch the normalized profile, and issue a short-lived signed HTTP-only session cookie. Provider credentials and callback URLs are read from `.env`; provider passwords and access tokens are never stored. The current session holds identity only, separate from the scientific feature store. Team collaboration remains handled through GitHub repository access and pull requests.

### 3.2 Scientific data sources

For the challenge submission, the source of truth is the official [NASA Space Apps 2026 Resources tab](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources). The exact resources captured from that page are recorded in [`data/official_resources_catalog.json`](data/official_resources_catalog.json): NASA Earthdata Search, NASA Worldview, NASA PDS, NASA LRO, NASA LRO Diviner, CSA RADARSAT resources, ESA Copernicus Data Space, ESA Open Science Catalog and JAXA G-Portal.

No URL outside that catalog may be used in final challenge evidence. `src/source_lock.py` validates the global multi-modal result snapshot; `src/app_data_validation.py` validates the narrower `dashboard/terrain_source_lock.json` against the exact NASADEM DOI and MOLA product URL. The inherited adapters and result JSON remain available for regression testing only and are hidden from the ranking workspace until the global audit passes.

### 3.3 Ingestion layer

The ingestion layer is an offline collection of scripts rather than a live service.

Responsibilities:

- Download or import source files from an exact URL in `data/official_resources_catalog.json`.
- Record the complete provenance contract in `data/terratwin_source_policy.json`.
- Validate file existence and basic metadata.
- Convert source formats where necessary.
- Preserve raw files separately from derived files.

The ingestion layer must never silently replace failed downloads with invented values or an unapproved fallback. If a source is unavailable, the pipeline should fail clearly, mark that feature unavailable and keep the source lock blocked.

### 3.4 Geospatial preprocessing layer

Responsibilities:

- Crop rasters to candidate and reference windows.
- Reproject or transform data into the analysis coordinate system.
- Resample to a documented analysis resolution.
- Derive slope, local relief and roughness from elevation.
- Calculate raster statistics.
- Produce candidate-level feature records.

Recommended Python libraries:

- `rasterio` for raster I/O and raster operations.
- `numpy` for numerical calculations.
- `geopandas` for vector data.
- `shapely` for geometries.
- `pyproj` for coordinate transformations.
- `scipy` only if needed for additional terrain statistics.

All derived products should include the source dataset identifiers used to create them.

### 3.5 Feature store

The MVP should store both geospatial artifacts and compact feature summaries.

```text
data/
  raw/
    earth/
    moon/
    mars/
  processed/
    earth/
    moon/
    mars/
  candidates/
    candidates.geojson
  features/
    earth_features.parquet
    moon_features.parquet
    mars_features.parquet
  metadata/
    dataset_catalog.json
    processing_runs.json
```

Use GeoJSON for map geometries and Parquet or JSON for feature summaries. SQLite can provide simple filtering and joins without introducing a database service.

### 3.6 Feature schema

Example candidate feature record:

```json
{
  "candidate_id": "bardenas_reales",
  "body": "earth",
  "name": "Bardenas Reales",
  "latitude": 42.2,
  "longitude": -1.5,
  "analysis_window_km": 5,
  "features": {
    "elevation_median_m": 340.0,
    "elevation_range_m": 215.0,
    "slope_mean_deg": 8.4,
    "slope_std_deg": 6.1,
    "local_relief_m": 182.0,
    "roughness_index": 0.42,
    "surface_reflectance_proxy": 0.31,
    "aridity_proxy": 0.87
  },
  "availability": {
    "terrain": true,
    "surface_reflectance": true,
    "thermal": false,
    "water_ice": false
  },
  "sources": [
    "srtm_30m_v3",
    "landsat_c2_l2"
  ],
  "processing": {
    "crs": "EPSG:32630",
    "generated_at": "2026-11-14T00:00:00Z",
    "pipeline_version": "0.1.0"
  }
}
```

Planetary reference records should use the same feature names where the quantities are compatible, while preserving body-specific metadata such as datum, projection and product resolution.

## 4. Scoring architecture

The scoring engine must be deterministic and independent of the frontend.

### 4.1 Inputs

- Candidate feature record.
- Planetary reference feature record.
- Mode: `moon` or `mars`.
- Feature weights.
- Normalization parameters.
- Availability masks.

### 4.2 Processing stages

```text
raw feature values
      ↓
unit and quality validation
      ↓
robust normalization
      ↓
feature-level difference
      ↓
availability masking
      ↓
weighted aggregation
      ↓
similarity score + confidence score
```

### 4.3 Scoring interface

```python
score_comparison(
    candidate: FeatureRecord,
    reference: FeatureRecord,
    mode: Literal["moon", "mars"],
    weights: dict[str, float],
    normalization: NormalizationConfig,
) -> ComparisonResult
```

### 4.4 Comparison result

```json
{
  "candidate_id": "bardenas_reales",
  "reference_id": "mars_arid_terrain_01",
  "mode": "mars",
  "similarity_score": 74.6,
  "confidence_score": 68.2,
  "features": [
    {
      "name": "roughness_index",
      "candidate_value": 0.42,
      "reference_value": 0.46,
      "normalized_difference": 0.08,
      "weight": 0.20,
      "contribution": 0.016,
      "available": true,
      "source_ids": ["srtm_30m_v3", "mola_global_dem"]
    }
  ],
  "missing_features": ["thermal_behavior", "mineralogy"],
  "strongest_matches": ["terrain roughness", "surface aridity proxy"],
  "major_differences": ["Earth atmosphere", "surface material uncertainty"],
  "limitations": [
    "This is a terrestrial analog assessment, not a Mars landing-safety evaluation."
  ]
}
```

### 4.5 Moon and Mars configuration

Keep configuration explicit and separate:

```yaml
moon:
  weights:
    terrain_morphology: 0.55
    surface_material: 0.25
    thermal_illumination: 0.20

mars:
  weights:
    terrain_morphology: 0.40
    surface_material: 0.25
    thermal_behavior: 0.20
    aridity_ice_water: 0.15
```

An unavailable feature is removed from the active denominator and reduces confidence. It must not receive a fabricated default value.

## 5. Backend architecture

### 5.1 Backend modules

```text
backend/app/
  main.py
  config.py
  routes/
    candidates.py
    comparisons.py
    datasets.py
    methodology.py
  models/
    candidate.py
    feature.py
    comparison.py
  services/
    candidate_service.py
    scoring_service.py
    source_service.py
    explanation_service.py
  scoring/
    normalize.py
    distance.py
    confidence.py
    profiles.py
  repositories/
    feature_repository.py
    dataset_repository.py
```

### 5.2 API endpoints

#### List candidates

```http
GET /api/candidates?mode=moon&limit=20
```

Response:

```json
{
  "mode": "moon",
  "items": [
    {
      "id": "bardenas_reales",
      "name": "Bardenas Reales",
      "latitude": 42.2,
      "longitude": -1.5,
      "similarity_score": 71.4,
      "confidence_score": 74.0
    }
  ]
}
```

#### Candidate detail

```http
GET /api/candidates/{candidate_id}
```

Returns candidate metadata, geometry, available features and source references.

#### Comparison

```http
GET /api/candidates/{candidate_id}/comparison?mode=mars&reference_id=mars_arid_terrain_01
```

Returns the complete `ComparisonResult`, including feature contributions and missing data.

#### Dataset catalog

```http
GET /api/datasets
```

Returns dataset names, providers, coverage, parameters, resolution, access links and usage notes.

#### Methodology

```http
GET /api/methodology
```

Returns the active scoring profile, normalization explanation, confidence formula and limitations.

### 5.3 Backend behavior on errors

- Return structured error JSON.
- Do not return a score if required candidate or reference features are missing.
- Distinguish unavailable optional data from invalid data.
- Log source and processing errors for reproducibility.
- Allow the frontend to show a graceful fallback state.

## 6. Frontend architecture

### 6.1 Frontend modules

```text
frontend/src/
  app/
    router.tsx
    queryClient.ts
  pages/
    MissionOverview.tsx
    Explorer.tsx
    CandidateReport.tsx
    Rankings.tsx
    Datasets.tsx
    Methodology.tsx
  components/
    AppShell.tsx
    ModeToggle.tsx
    CandidateMap.tsx
    CandidateCard.tsx
    RankingTable.tsx
    SimilarityBreakdown.tsx
    ConfidenceBadge.tsx
    SourceList.tsx
    LimitationCallout.tsx
  charts/
    FeatureComparisonChart.tsx
    ContributionChart.tsx
  api/
    client.ts
    candidates.ts
    comparisons.ts
```

### 6.2 Main application state

```text
selectedMode: moon | mars
selectedCandidateId: string | null
selectedReferenceId: string
activeMapLayers: string[]
candidateFilters: FilterState
comparison: ComparisonResult | null
```

Use URL query parameters for mode and candidate selection so demo links are shareable:

```text
/explorer?mode=mars&candidate=bardenas_reales
```

### 6.3 Required frontend states

- Loading.
- Empty candidate list.
- Candidate selected.
- Comparison unavailable.
- Optional data unavailable.
- API error with cached fallback.
- Confidence warning.

### 6.4 Map requirements

- Use a stable basemap.
- Display candidate markers or polygons.
- Color markers by similarity score.
- Use a separate visual treatment for confidence.
- Never imply that a high score equals a safe landing site.
- Include a legend and attribution.

## 7. Data flow in detail

### Offline path

```text
Dataset catalog
      ↓
Download script
      ↓
Raw archive
      ↓
Preprocessing script
      ↓
Candidate/reference windows
      ↓
Feature extraction
      ↓
Validation report
      ↓
Feature store
```

### Runtime path

```text
User selects Moon or Mars mode
      ↓
Frontend requests candidate rankings
      ↓
FastAPI loads precomputed feature records
      ↓
Scoring service calculates or retrieves comparison
      ↓
API returns score, confidence and evidence
      ↓
Frontend renders map, charts and explanation
```

### Explanation path

```text
ComparisonResult
      ↓
validated explanation payload
      ↓
template or constrained LLM prompt
      ↓
scientific explanation
      ↓
source and limitation checks
      ↓
UI display
```

The explanation layer should not have direct authority to add new measurements or sources.

## 8. Storage and provenance

Every derived feature should be traceable to:

- Dataset identifier.
- Product version.
- Source URL.
- Retrieval date.
- Processing script version.
- Coordinate reference system.
- Analysis resolution.
- Candidate/reference geometry.
- Quality flags.

Example dataset catalog record:

```json
{
  "id": "mola_global_dem",
  "name": "Mars Orbiter Laser Altimeter global DEM",
  "provider": "NASA/JPL",
  "body": "mars",
  "parameters": ["elevation", "terrain_gradient"],
  "format": "planetary raster",
  "access_url": "https://pds.nasa.gov/",
  "status": "verified-source",
  "used_in_mvp": true,
  "notes": "Resolution and projection must be recorded for the exact product used."
}
```

## 9. Security and reliability

The MVP does not require user accounts or sensitive data.

Minimum protections:

- Keep API keys in environment variables.
- Never commit credentials or tokens.
- Sanitize any user-provided candidate names or report text.
- Limit LLM input to structured, non-sensitive scientific data.
- Use local fallback data only for development diagnostics; never present it as final challenge evidence.
- Pin dependency versions before the final demo.

## 10. Deployment architecture

### Recommended MVP deployment

```text
Single host or container
  ├── frontend static build
  ├── FastAPI backend
  ├── SQLite database or JSON feature store
  └── cached GeoJSON and comparison results
```

The frontend can be served as static assets and the backend can serve `/api` routes. A reverse proxy is optional.

### Local fallback

The final demonstration must work using:

- Precomputed candidate GeoJSON.
- Precomputed comparison JSON.
- Bundled source metadata.
- Local basemap or a stable external basemap with a graceful fallback.

Do not require a live download of NASA or ESA data during the presentation.

## 11. Testing strategy

### Unit tests

- Normalization boundaries.
- Weighted-distance calculation.
- Missing-feature masking.
- Confidence calculation.
- Moon and Mars profile separation.
- Score range between 0 and 100.

### Data tests

- Coordinates fall within expected regions.
- Rasters have valid dimensions and CRS metadata.
- Units are recorded.
- No NaN values are silently converted to zero.
- Source IDs exist in the dataset catalog.

### API tests

- Candidate list returns valid GeoJSON-compatible coordinates.
- Comparison endpoint returns feature contributions.
- Unknown candidate returns 404.
- Unsupported mode returns 400.
- Optional data failure returns a clear availability state.

### UI tests

- Mode toggle changes ranking and comparison data.
- Map click opens the correct candidate.
- Score and confidence are visually distinct.
- Missing-data warning is visible.
- Source links work.
- Cached fallback operates without the external processing pipeline.

## 12. Performance strategy

- Precompute all MVP feature statistics.
- Avoid sending full rasters to the browser.
- Send GeoJSON boundaries and summary values only.
- Cache rankings by mode and reference region.
- Lazy-load report charts where possible.
- Keep optional imagery layers disabled until requested.

Target behavior:

- Initial dashboard load: under five seconds on the demo network.
- Candidate selection: under two seconds using cached data.
- Ranking update: under two seconds.
- No runtime raster resampling in the browser.

## 13. Architecture decisions and tradeoffs

### Precomputation instead of live processing

Precomputation sacrifices arbitrary global exploration but significantly improves reliability and makes the scoring reproducible within the hackathon timeline.

### SQLite/JSON instead of a spatial database

SQLite or JSON is sufficient for four to ten candidates. PostGIS can be introduced later if TerraTwin expands to thousands of locations or user-generated queries.

### Deterministic scoring instead of black-box ML

The deterministic model is easier to validate, explain and defend to judges. Machine learning can be added later for candidate discovery, but not as a substitute for scientific evidence.

### Optional AI explanations

The product remains functional without an LLM. This reduces operational risk and ensures that the score is not dependent on generative output.

## 14. Future architecture

After the MVP, the system could evolve toward:

- Cloud-optimized GeoTIFF and STAC ingestion.
- PostGIS or DuckDB spatial analytics.
- Tile servers for raster visualization.
- Candidate-generation over global Earth grids.
- Versioned scoring experiments.
- User-defined weights and reference regions.
- Field observations and validation feedback.
- Reproducible research notebooks and downloadable reports.

These extensions should be implemented only after the core scientific workflow is stable.

