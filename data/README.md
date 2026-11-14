# Planetary & Terrestrial DEM Data Directory

This directory stores Digital Elevation Models (DEMs) in `.npy` (NumPy arrays) or `.tif` (GeoTIFF) format.

## Procedural Simulation Datasets
When you run `python main.py`, realistic procedural simulations are generated here automatically:
- `target_moon_artemis_south_pole.npy`: Shackleton / Malapert highland terrain with steep crater walls.
- `target_mars_jezero_crater.npy`: Ancient lakebed, delta fan, and crater rim.
- `earth_iceland_askja.npy`: Young basaltic caldera and subterranean lava tubes.
- `earth_mcmurdo_dry_valleys.npy`: Hyper-arid polar desert and frozen polygon ground.
- `earth_atacama_puna.npy`: High-altitude plateau with extreme UV flux.
- `earth_haughton_crater.npy`: Devon Island Arctic impact crater with breccia sheets.
- `earth_hawaii_mauna_kea.npy`: Basaltic tephra cinder cones (source region of the JSC Mars-1 simulant).

## Adding official-source GeoTIFFs

Final challenge evidence may be ingested only from a resource listed on the official [NASA Space Apps 2026 Resources tab](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources). The exact approved portals are recorded in [`official_resources_catalog.json`](official_resources_catalog.json).

Every downloaded product must carry all fields in `terratwin_source_policy.json`: dataset name, provider, exact resource URL, retrieval date, product/version ID, processing step, coverage/resolution and quality flags. Run `./.venv/bin/python -m src.source_lock --write-dashboard` before displaying or submitting derived scores. Unapproved fallbacks remain development fixtures and are blocked from the dashboard's ranking workspace.
