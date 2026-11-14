# TerraTwin Product Requirements Document

**Product:** TerraTwin — AI-Powered Planetary Analog Discovery and Characterization Platform  
**Event:** NASA Space Apps Challenge 2026  
**Document status:** Hackathon MVP specification  
**Target build window:** Approximately two days  
**Primary users:** Planetary scientists, analog researchers, mission planners, educators and technically interested members of the public

## 1. Product summary

TerraTwin is an interactive geospatial research platform that identifies Earth locations with measurable similarities to selected regions of the Moon and Mars.

The product combines open Earth-observation and planetary datasets, derives comparable terrain and surface features, calculates transparent similarity scores, ranks candidate locations and explains the evidence behind each result.

TerraTwin evaluates **terrestrial analog usefulness** for research and equipment testing. It does not identify certified lunar or Martian landing sites, guarantee mission safety or claim NASA endorsement.

## 2. Problem statement

Existing terrestrial analog research is valuable but fragmented across scientific papers, datasets, field sites and expert knowledge. Famous locations such as the Atacama Desert, Haughton Crater and Death Valley are well known, while many other potentially useful locations remain less characterized.

Teams need a practical way to:

- Discover candidate Earth locations.
- Compare them with selected lunar and Martian reference regions.
- Understand which properties create the similarity.
- See where evidence is missing or uncertain.
- Distinguish scientific analogy from visual resemblance.

The NASA Space Apps challenge asks participants to use open Earth, Moon and Mars data to identify and characterize new terrestrial analogs. [Official challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

## 3. Product goals

### Primary goals

1. Deliver a functional interactive map of Earth analog candidates.
2. Provide separate Moon and Mars comparison modes.
3. Use real, documented scientific datasets wherever practical.
4. Calculate explainable multi-parameter similarity scores.
5. Display data confidence separately from similarity.
6. Highlight strongest matches, major differences and missing evidence.
7. Produce a credible scientific demonstration within two hackathon days.

### Secondary goals

- Identify less-characterized candidate locations.
- Provide a reusable data and scoring pipeline.
- Make methodology and dataset provenance visible to judges and users.
- Generate concise, evidence-based scientific explanations.

### Non-goals

- Certifying landing-site safety.
- Predicting habitability or life.
- Replacing planetary scientists or field validation.
- Building a global, real-time planetary data-processing system.
- Claiming NASA approval or scientific validation of the scoring model.

## 4. Product principles

- **Evidence before appearance:** visual similarity alone is insufficient.
- **Transparency before complexity:** every score must be explainable.
- **Moon and Mars remain separate:** their environments and datasets are not interchangeable.
- **Missing is not zero:** unavailable measurements must reduce coverage or confidence, not artificially improve or worsen similarity.
- **Prototype honestly:** derived, demonstration or synthetic values must be clearly labelled.
- **Scope discipline:** precompute expensive geospatial analysis and prioritize a reliable MVP.

## 5. Target users and user stories

### Planetary researcher

As a planetary researcher, I want to compare an Earth site with a selected Moon or Mars reference region so that I can assess whether it deserves further analog-study investigation.

### Mission or robotics researcher

As a mission researcher, I want to see terrain and roughness similarities so that I can identify locations for rover, instrument or traverse testing.

### Educator or public user

As an educator, I want to explore a map and understand the scientific reasoning without reading raw datasets or code.

### Hackathon judge

As a judge, I want to see real data sources, a reproducible methodology and a working end-to-end application.

## 6. MVP scope

### Must have

- Interactive Earth map.
- At least four researched Earth candidates.
- Candidate detail page.
- Moon comparison mode.
- Mars comparison mode.
- At least one lunar and one Martian reference region.
- Terrain-derived features: elevation statistics, slope, local relief and roughness.
- Weighted similarity score.
- Data confidence score.
- Score breakdown by parameter.
- Visible data sources and methodology.
- Evidence-based explanation.
- Static or cached fallback data for the final demo.

### Should have

- Earth surface reflectance or aridity indicators.
- Landsat or Sentinel imagery layer.
- Ranking filters by analog type or intended use.
- Downloadable candidate report.
- User-adjustable weights.

### Could have

- Thermal context from Landsat, Diviner or THEMIS.
- Cave or lava-tube evidence.
- Seasonal comparisons.
- User-created candidate locations.
- AI-generated natural-language reports.

### Won’t have in the two-day MVP

- Live global raster processing.
- Full planetary mineralogical classification.
- Reliable cross-body absolute thermal equivalence.
- Landing-site hazard certification.
- Complex machine-learning discovery over every Earth location.

## 7. Core product experience

### 7.1 Mission overview

The home page explains:

- The terrestrial analog problem.
- What TerraTwin measures.
- The distinction between analog usefulness and landing safety.
- The available Moon and Mars modes.

### 7.2 Interactive map

The map must display:

- Earth candidate markers or polygons.
- Candidate names and analog categories.
- Map controls for Moon and Mars modes.
- Optional satellite or terrain basemap.
- A legend explaining colors and score ranges.
- Click-to-open candidate summaries.

### 7.3 Candidate detail view

Each candidate page must contain:

- Name and coordinates.
- Country or region.
- Candidate description.
- Selected planetary reference region.
- Overall similarity score.
- Data confidence score.
- Parameter comparison chart.
- Strongest matching characteristics.
- Major differences.
- Intended analog uses.
- Dataset citations.
- Limitations and unavailable measurements.

### 7.4 Ranking view

Provide separate rankings for:

- Earth-to-Moon analogs.
- Earth-to-Mars analogs.

Each row should show:

- Rank.
- Candidate.
- Similarity score.
- Confidence score.
- Reference region.
- Main matching factor.
- Main limitation.

### 7.5 Dataset and methodology view

This view should document:

- Dataset name and provider.
- Body covered: Earth, Moon or Mars.
- Parameters used.
- Resolution and format where known.
- Access method.
- How the dataset contributes to the score.
- Known limitations.

## 8. Scientific data requirements

### Earth

**SRTM or ASTER GDEM** should provide the primary Earth elevation layer for elevation, slope, local relief and roughness. [NASA SRTM guide](https://www.earthdata.nasa.gov/s3fs-public/2025-05/SRTM_Quick_Guide.pdf) and [ASTER GDEM search](https://search.earthdata.nasa.gov/search?q=aster+gdem)

**Landsat Collection 2 Level-2** may provide surface reflectance and surface temperature. USGS states that Landsat Level-2 products are globally available and that Landsat products have no restrictions on use, subject to appropriate citation. [Landsat surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)

**Copernicus Sentinel-2** may provide higher-resolution optical surface context through the Copernicus Data Space Ecosystem. [ESA data access](https://knowledge-hub-gda.esa.int/training_resource/access-to-open-and-relevant-data/)

### Moon

**LRO LOLA** should provide lunar topography, slope and roughness products. [NASA LOLA](https://science.nasa.gov/mission/lro/lola/) and [NASA south-pole products](https://pgda.gsfc.nasa.gov/products/78)

**LROC** may provide visual context and selected optical imagery.

**Diviner** may provide thermal context as a stretch feature only.

### Mars

**MOLA** should provide Martian topography and derived gradients. [MOLA documentation](https://planetarydata.jpl.nasa.gov/img/data/mgs-m-moc-4-sampler-v1.0/mgs_0001/document/volinfo.htm)

**HRSC/MOLA blended products** may provide higher-resolution Mars terrain where available. [USGS Mars data inventory](https://fdp.astrogeology.usgs.gov/fdp/mars/)

**THEMIS, CTX and HiRISE** may be used for selected visual or thermal evidence, but they are not required for the core MVP.

All planetary products should be traced to NASA’s Planetary Data System or an authoritative mission archive. [NASA PDS](https://pds.nasa.gov/)

## 9. Candidate locations for the MVP

The initial candidate set should be small and geographically diverse:

1. **Bardenas Reales, Spain** — arid badlands and sparse vegetation.
2. **Makhtesh Ramon, Israel** — crater-like erosional terrain; explicitly not an impact-crater claim.
3. **Icelandic highlands** — volcanic, glacial and sparse-vegetation environment.
4. **Ladakh, India** — high-altitude cold desert with strong relief and isolation.

Potential later additions include the Puna de Atacama, Danakil Depression, Réunion volcanic terrain, Antarctic Dry Valleys and lava-cave environments.

USGS identifies terrestrial analogs as useful for geological studies, field training, traverse testing and technology demonstrations, including volcanic, glacial and cave environments. [USGS terrestrial analogs](https://www.usgs.gov/science/science-explorer/planetary-science/terrestrial-analogs)

## 10. Scoring requirements

### Feature extraction

For each Earth candidate and planetary reference window, calculate as many of the following as supported by compatible data:

- Median elevation.
- Elevation range.
- Mean slope.
- Slope variability.
- Local relief.
- Terrain roughness.
- Surface reflectance or material proxy.
- Earth aridity or vegetation indicators.
- Thermal statistics, only when scientifically qualified.

### Normalization

Use robust percentile scaling rather than raw cross-body values:

```text
normalized_value = (value - P5) / (P95 - P5)
```

Clamp the result to 0–1. Document the reference population used for the percentiles.

### Weighted distance

```text
D = sum(weight_i * availability_i * difference_i) /
    sum(weight_i * availability_i)

similarity = 100 * (1 - D)
```

Unavailable features must be excluded from the denominator and displayed to the user.

### Initial weights

Moon mode:

- Terrain morphology: 0.55.
- Surface reflectance/material proxy: 0.25.
- Thermal or illumination context: 0.20, if available.

Mars mode:

- Terrain morphology: 0.40.
- Surface material/reflectance: 0.25.
- Thermal behavior: 0.20, if qualified.
- Aridity, ice or water context: 0.15.

These are proposed product defaults, not NASA-approved weights.

### Confidence

The confidence score should combine:

- Feature coverage.
- Resolution compatibility.
- Source quality and provenance.
- Temporal consistency.

The interface must show confidence independently from similarity.

## 11. AI explanation requirements

The explanation engine may use templates or an LLM, but every explanation must be generated from structured comparison data.

Example output:

> “This candidate matches the selected Martian reference primarily in terrain roughness and aridity-related surface characteristics. The comparison has limited confidence because compatible mineralogical and atmospheric measurements are unavailable. The result supports rover or field-equipment testing, not a claim of equivalent Martian environmental conditions.”

The AI must not:

- Invent measurements.
- Add unsupported geological claims.
- State that NASA endorses the result.
- Convert analog similarity into landing safety.

## 12. Technical architecture

```text
NASA / USGS / ESA datasets
          ↓
Download and preprocessing scripts
          ↓
GeoTIFF / Parquet / JSON feature store
          ↓
Feature extraction engine
          ↓
Moon and Mars scoring modules
          ↓
FastAPI backend
          ↓
React dashboard + MapLibre or Leaflet
          ↓
Charts, rankings and scientific explanations
```

### Recommended stack

- Frontend: React and TypeScript.
- Mapping: MapLibre GL or Leaflet.
- Charts: Plotly or Recharts.
- Backend: Python and FastAPI.
- Geospatial analysis: Rasterio, GeoPandas, NumPy and Shapely.
- Storage: GeoJSON, JSON, Parquet and SQLite.
- Deployment: one container or simple hosted service.

### Suggested repository structure

```text
terr atwin/
  frontend/
  backend/
    app/
      routes/
      models/
      scoring/
      explanations/
  data/
    raw/
    processed/
    candidates/
    references/
  scripts/
  docs/
  README.md
```

### API requirements

```text
GET /api/candidates?mode=moon
GET /api/candidates?mode=mars
GET /api/candidates/{id}
GET /api/candidates/{id}/comparison?mode=moon
GET /api/datasets
GET /api/methodology
```

The comparison endpoint must return the final scores, feature values, weights, contributions, missing fields, sources and limitations.

## 13. Functional requirements

### FR-1: Candidate discovery

The system shall display at least four candidate Earth locations with names, coordinates and descriptions.

### FR-2: Mode separation

The system shall provide independent Moon and Mars comparison modes and rankings.

### FR-3: Map interaction

Users shall be able to select a candidate from the map and open its comparison view.

### FR-4: Transparent scoring

The system shall show how each available feature contributes to the similarity score.

### FR-5: Confidence reporting

The system shall report data confidence separately from similarity.

### FR-6: Missing data

The system shall identify unavailable features and shall not treat them as zero-valued measurements.

### FR-7: Source visibility

The system shall expose dataset names, providers and links for every comparison.

### FR-8: Scientific explanation

The system shall generate an explanation grounded in the selected candidate’s computed results.

### FR-9: Limitations

Every result shall include a clear analog-use limitation and a statement that the result is not a landing-safety assessment.

### FR-10: Demo reliability

The system shall include cached or local fallback data so the primary demo does not depend on live external data services.

## 14. Non-functional requirements

- Candidate pages should load within three seconds using cached data.
- The application should function on a standard laptop browser.
- The interface should be readable at presentation resolution.
- Numerical calculations should be reproducible from stored inputs and configuration.
- Units, coordinate systems and data dates must be displayed or documented.
- The application should remain usable if optional datasets fail to load.
- External APIs should not be required for the basic demonstration.

## 15. Two-day implementation plan

### Hours 0–3

- Freeze scope and candidate list.
- Confirm dataset provenance.
- Define data schema and API contract.

### Hours 3–8

- Prepare Earth and planetary DEM inputs.
- Generate candidate geometries.
- Extract terrain features.

### Hours 8–14

- Implement Moon and Mars scoring modules.
- Generate ranking outputs.
- Add confidence and missing-data handling.

### Hours 12–20

- Build map, candidate selection and ranking screens.
- Add comparison charts and score cards.

### Hours 20–28

- Connect frontend and backend.
- Add source and methodology panels.
- Add structured explanations.

### Hours 28–36

- Validate results and coordinates.
- Test candidate flows and failure states.
- Prepare cached fallback data.

### Hours 36–48

- Freeze features.
- Fix high-impact defects only.
- Rehearse and record a backup demo.

## 16. Team ownership

| Member | Ownership | Required output |
|---|---|---|
| 1 | Product, architecture and integration | Integrated build, scope control and final demo |
| 2 | Backend and scoring | FastAPI service, scoring engine and tests |
| 3 | UI/UX | Wireframes, navigation and responsive interface |
| 4 | Visual design and presentation | Design system, charts, pitch and demo visuals |
| 5 | Science and research | Dataset register, candidate evidence and validation |
| 6 | GIS, testing and documentation | GeoJSON/raster preparation, QA and documentation |

## 17. Success metrics

The MVP is successful if it can demonstrate:

- At least four Earth candidates on a working map.
- Separate Moon and Mars rankings.
- At least one real Earth dataset and one real planetary dataset in the pipeline.
- A reproducible score for every displayed candidate.
- Visible feature contributions and confidence.
- No fabricated measurements or unsupported claims.
- A complete five-minute demo understandable to a non-specialist judge.

## 18. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Planetary files are difficult to process | Use preprocessed DEM products and summary statistics. |
| Cross-body values are not physically equivalent | Compare normalized morphology and label proxies carefully. |
| Missing data distort rankings | Use availability masks and confidence penalties. |
| AI produces unsupported claims | Use structured prompts, templates and source-bound outputs. |
| Live APIs fail during judging | Cache all MVP results locally. |
| Project becomes visually impressive but scientifically weak | Make every score traceable to a dataset and calculation. |
| Candidate locations are too well known | Include at least one less-characterized candidate and explain the selection process. |

## 19. Demo storyline

1. Introduce the fragmented analog-selection problem.
2. Open TerraTwin’s Earth map.
3. Select a candidate and show the Moon comparison.
4. Switch to Mars mode and show a different ranking or explanation.
5. Open the score breakdown and reveal feature contributions.
6. Show confidence and missing-data reporting.
7. Highlight a less-famous candidate and its possible analog use.
8. Close with the limitation: “TerraTwin identifies research analogs, not landing sites.”

## 20. Acceptance checklist

- [ ] Map loads with candidate locations.
- [ ] Candidate selection opens a detail view.
- [ ] Moon and Mars modes are visibly separate.
- [ ] Rankings are calculated from stored feature data.
- [ ] Similarity and confidence are separate values.
- [ ] Missing data are visible and not treated as zero.
- [ ] Every result has dataset citations.
- [ ] Methodology is accessible from the UI.
- [ ] Explanation text matches the actual data.
- [ ] Limitations are visible.
- [ ] Cached demo works without external API calls.
- [ ] Final presentation has a working backup path.

