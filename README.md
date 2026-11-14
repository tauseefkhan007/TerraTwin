# TerraTwin
### Evidence-first Earth analog discovery for Moon and Mars missions
**NASA International Space Apps Challenge 2026** - *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

[![Event](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

TerraTwin is an interactive screening tool for comparing Earth field environments with selected lunar and Martian mission targets. It keeps similarity, evidence coverage, source provenance and irreducible Earth-versus-planet gaps visible in the same report.

> **Source-policy lock:** final challenge claims must use only datasets and links listed on the official [NASA Space Apps 2026 Resources tab](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources). The current dashboard contains an imported PTAE baseline for reuse-first development. Its inherited adapters and generated results are explicitly provisional until revalidated against that tab.

The current branch is the first TerraTwin build: an MIT-licensed scientific scoring base, Earth–Moon–Mars intro animation, four mission-profile presets, a separate coverage score, per-site guardrails, famous-analog benchmark checks and a deterministic grounded Science Copilot scaffold.

The official source lock is enforced by [`src/source_lock.py`](src/source_lock.py), [`data/official_resources_catalog.json`](data/official_resources_catalog.json) and [`dashboard/source_lock.json`](dashboard/source_lock.json). The dashboard hides numeric ranking results while the audit is blocked. This is intentional: the imported baseline must not be mistaken for official challenge evidence.

Exact product endpoints selected for the re-ingestion are recorded in
[`data/official_product_urls.json`](data/official_product_urls.json). Recording
an endpoint does not certify the inherited result snapshot; the data must still
be downloaded, processed and audited against that endpoint.

## AnalogX dataset import

NAKSH also loads the complete tabular terrain import from the public
[`analogx-hackathon-ready`](https://github.com/hazraanirban2006-boop/analogx-hackathon-ready)
repository: 49 Earth feature records, 2 Mars target records and its sensitivity
audit. The dashboard reports this inventory in Global Analog Search. The
repository's duplicate 150-tile HGT/150-tile ZIP cache is represented by
[`data/analogx/cache_manifest.json`](data/analogx/cache_manifest.json) and is
downloaded only when reproducing the upstream ETL. This import remains
development-only until the exact NASA product provenance passes the official
Resources-tab audit.

## Inherited scientific baseline

The sections below document the imported PTAE v2 baseline for the team while the TerraTwin source-compliant adapters are being prepared. Treat its numeric results as development fixtures, not final challenge evidence.

## What is new in the inherited v2 baseline

| Weakness of v1 | Fix in v2 |
| :--- | :--- |
| Procedural (synthetic) terrain | Real elevation: LRO LOLA (Moon), MGS MOLA (Mars), SRTM/NASADEM-based AWS Terrain Tiles (Earth) |
| Five famous sites only | 33 regions: 14 benchmarks, 14 less-studied candidates, 5 negative controls |
| Terrain only, plus a boolean bonus | Three dimensions: terrain, NASA POWER climate, curated geology |
| Pixel-scale slope compared across 20 m, 30 m and 463 m DEMs | Slope over identical ground baselines (240 m to 3.84 km), so resolution cancels |
| One window per site | Sliding 40 km windows find the best sub-region; the map shows exactly where |
| Gaussian on means, single score | Rank uncertainty from 1000 random weightings, plus negative-control AUC |
| Earth treated as a perfect analog | Explicit "where it breaks down" panel and the conditions no Earth site can reproduce |

## Inherited baseline results (development fixture only)

The numbers below are retained so the team can regression-test the imported scoring engine. They are not the final TerraTwin challenge results until the official Resources-tab-only pipeline is complete.

Mean ACI across targets (0 to 100, a relative index; Earth never reaches 100):

| Body | Top 5 |
| :--- | :--- |
| **Mars** (Jezero, Gale, Gusev, Meridiani, Oxia, Hellas) | Gilf Kebir, Egypt (51); Dasht-e Lut, Iran (50); Qaidam Basin, China (48); Pinacate, Mexico (45); Atacama Yungay, Chile (38) |
| **Moon** (Shackleton, Malapert) | Death Valley, USA (44); McMurdo Dry Valleys, Antarctica (42); Tibesti, Chad (37); Bernese Alps (control, 35); Dasht-e Lut, Iran (33) |

Takeaways:
- For Mars, four of the five best regions are **less-studied deserts**, and the benchmark Atacama still ranks in the top five, which is the expected sanity check.
- Negative controls (rainforest, plains, glaciated and monsoon mountains) are separated from candidates with AUC 0.84 on Mars targets.
- **The Moon result is weaker (AUC 0.66).** Lunar polar terrain is rugged, so steep mountain controls match its slope statistics; only climate and geology reject them. Treat Moon rankings as hypotheses.
- Terrain alone separates controls from candidates with AUC 0.64, climate 0.86 and geology 0.95. The dimensions are complementary, so scores are combined multiplicatively (a site must be adequate on every dimension).

Full per-target tables: [results/global_ranking.csv](results/global_ranking.csv) and the dashboard.

## Method in brief
1. **Data.** Earth: AWS Terrain Tiles (zoom 11). Moon: LOLA 20 m south-polar DEM. Mars: MOLA 463 m. All resampled to a common 120 m grid and 40 km windows.
2. **Terrain signature.** Median and 90th-percentile slope over baselines of 240, 480, 960, 1920 and 3840 m, plus Hurst exponent and relief (differential-slope method; Kreslavsky and Head 2000; Rosenburg et al. 2011). Mars uses only baselines of 960 m and longer because gridded MOLA does not resolve finer terrain.
3. **Environment.** NASA POWER climatology (mean temperature, daily range, rain, humidity, pressure) compared with a target clipped to the most extreme values reachable on Earth.
4. **Geology.** Curated tags (impact, basaltic, lava tubes, ground ice, evaporites, and so on) in [catalog/](catalog/). These are expert priors, not measurements, and are labelled as such.
5. **Score.** Weighted geometric mean of the three similarities (default 0.5 / 0.25 / 0.25). The additive mean is available in the dashboard.
6. **Uncertainty and validation.** 1000 random weightings per target; negative-control AUC; best-window coverage.

### Limitations
- The aggregation was changed from additive to geometric after we saw that the additive form let a wet alpine valley rank first for the Moon. Both are reported; the geometric form does not remove the Moon weakness.
- NASA POWER is a 0.5 degree reanalysis and is coarse for single sites (it over-estimates rain in Iceland, for example).
- Gridded MOLA limits Mars comparisons to kilometre-scale terrain; rover-scale roughness needs HiRISE or CTX DEMs.
- Geology tags and the "emerging" label are judgement, not data. Rankings guide where to look next; they do not confirm analogs.
- Earth cannot reproduce gravity, vacuum or Mars pressure, or the radiation environment (see the dashboard table).

## Quickstart
```bash
git clone https://github.com/tauseefkhan007/TerraTwin.git
cd TerraTwin
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.global_search                         # downloads real data (cached in cache/), writes dashboard/global_results.json
python -m http.server --directory dashboard 8000    # open http://localhost:8000/
```
Open the **Global Search** tab after the source audit passes. Until then, it shows the approved Resources-tab catalog and the exact missing provenance/source checks instead of displaying the inherited rankings.

Run the audit after every data ingestion:

```bash
./.venv/bin/python -m src.source_lock --write-dashboard
```

Exit code `0` means the official source lock passed. Exit code `2` means the dashboard remains blocked because at least one input is not traceable to an exact approved URL or lacks provenance.

### Open the frontend on another laptop

Run the frontend on the host laptop's network interface, then open the host laptop's LAN address from the second laptop. Find the address with `ipconfig getifaddr en0` on macOS (or your operating system's network settings).

```bash
python -m http.server --bind 0.0.0.0 --directory dashboard 8000
```

On the second laptop, open `http://<host-lan-ip>:8000/`. For demo access, the frontend is sufficient. If the second laptop must use the auth API too, run the API on the network interface and set `TERRATWIN_FRONTEND_URL` in `.env` to `http://<host-lan-ip>:8000`:

```bash
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8001
```

The host and second laptop must be on the same network, and the host firewall must allow ports 8000 and 8001. Do not expose this development server to the public internet.

### Optional Google/GitHub sign-in

The dashboard works in local demo mode without an auth service. To enable the two sign-in buttons, copy `.env.example` to `.env`, create OAuth apps with the callback URLs shown there, fill in the provider credentials, and run the API in a second terminal:

```bash
cp .env.example .env
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

The API issues a short-lived signed session cookie and never stores provider passwords or access tokens. Keep `.env` local; it is ignored by Git.

Tests (offline): `python -m unittest discover -s tests -v`. Browser tests also need `pip install -r requirements-dev.txt && python -m playwright install chromium`.

## Repository layout
```text
catalog/                 Earth sites and Moon/Mars targets (curated tags, heritage, limits)
src/geodata.py           Data adapters retained for the provisional development baseline
src/source_lock.py       Official Resources-tab catalog and provenance gate
src/multiscale.py        Baseline slope signatures, sliding windows, water masking
src/analog_score.py      Terrain/environment/geology similarity, aggregation, robustness, AUC
src/global_search.py     End-to-end pipeline and CLI
dashboard/               Static TerraTwin web app (Global Search plus legacy demo tabs)
tests/                   Unit tests for the inherited baseline and the v1 pipeline
main.py, src/terrain_metrics.py, similarity_matcher.py, synthetic_generator.py
                         v1 synthetic-terrain demo, kept for the original tabs and tests
```

## Inherited v1 synthetic demo (legacy)
`python main.py --target moon --json-out` and `--target mars` still regenerate the calibrated synthetic-terrain demo used by the dashboard's "Explore Sites" and "Compare" tabs. Those scores are **not** measurements; use Global Search for real-data results.

## Inherited open-data references
The approved resource list is recorded in [data/official_resources_catalog.json](data/official_resources_catalog.json). The inherited baseline references LRO LOLA, MGS MOLA, AWS Terrain Tiles and NASA POWER, but those inherited numeric results remain blocked until each exact product is re-ingested from a resource listed on the official page and receives complete provenance.

## Use of Super Intelligence (SI) tools
Per the Space Apps rules: the v1 prototype was drafted with an AI assistant, and the v2 redesign (data pipeline, scoring, dashboard tab, tests, documentation) was developed with GitHub Copilot. Design decisions, data choices and validity checks remain the team's responsibility.

## License
MIT. See [LICENSE](LICENSE).
