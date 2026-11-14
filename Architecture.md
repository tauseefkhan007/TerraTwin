# TerraTwin Technical Architecture

**Product:** TerraTwin  
**Version:** Hackathon MVP  
**Primary constraint:** Deliver a reliable scientific prototype in approximately two days

## 1. Architecture objectives

TerraTwin must be:

- Scientifically traceable.
- Simple enough for a six-person hackathon team.
- Fast enough for a live demonstration.
- Modular enough to replace prepared data with live ingestion later.
- Explicit about data coverage, uncertainty and limitations.

The recommended architecture is a modular monolith with offline geospatial preprocessing, a lightweight Python API and a React dashboard. Microservices, streaming infrastructure and real-time global raster processing are out of scope for the MVP.

## 2. High-level architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                    External scientific sources               │
│  NASA Earthdata │ USGS │ ESA Copernicus │ NASA PDS │ PGDA    │
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
│                         FastAPI backend                        │
│ candidates │ comparisons │ rankings │ datasets │ methodology   │
└──────────────────────────────┬───────────────────────────────┘
                               │ JSON/GeoJSON
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    React + TypeScript frontend                │
│ map │ rankings │ comparison charts │ reports │ explanations    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                       Researcher / judge
```

## 3. System components

### 3.1 Scientific data sources

The system should use authoritative public sources where possible:

- NASA SRTM or ASTER GDEM for Earth elevation.
- USGS Landsat Collection 2 for Earth surface reflectance and optional surface temperature.
- ESA Copernicus Sentinel-2 for optional Earth optical context.
- NASA LRO LOLA for lunar topography, slope and roughness.
- NASA MOLA products for Martian topography.
- NASA PDS and mission-specific archives for planetary provenance.

Data-source references should be recorded in `data/dataset_catalog.json` and displayed in the application.

### 3.2 Ingestion layer

The ingestion layer is an offline collection of scripts rather than a live service.

Responsibilities:

- Download or import source files.
- Record source URL, product name, version and retrieval date.
- Validate file existence and basic metadata.
- Convert source formats where necessary.
- Preserve raw files separately from derived files.

The ingestion layer must never silently replace failed downloads with invented values. If a source is unavailable, the pipeline should fail clearly or mark that feature unavailable.

### 3.3 Geospatial preprocessing layer

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

### 3.4 Feature store

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

### 3.5 Feature schema

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
- Use local fallback data when external sources fail.
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

