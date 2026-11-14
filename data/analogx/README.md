# AnalogX dataset import

This directory contains the complete tabular dataset exported by the public
`hazraanirban2006-boop/analogx-hackathon-ready` repository at commit
`76f3dbf1f418eb36cf244033468c8d2fcc249bfa`.

Imported records:

- `earth_features.csv`: 49 Earth candidate terrain records with elevation,
  slope, roughness and relief.
- `planetary_targets.csv`: 2 Mars target terrain records: Jezero Crater and
  Olympus Mons flank.
- `demo_earth_candidates.csv`: the repository's demo table, retained for
  reproducibility.
- `sensitivity_results.txt`: the repository's published sensitivity audit.

The source repository also tracks 150 NASADEM HGT tiles and 150 compressed
tile caches. They are not duplicated into NAKSH because they total more than
5 GB and the ZIP/HGT pairs duplicate the same source coverage. Their complete
inventory and on-demand source references are recorded in
`cache_manifest.json`.

The tables are imported for NAKSH development and comparison. They do not
automatically pass NAKSH's official NASA Space Apps Resources-tab source lock:
the exact product URL, retrieval date, processing step, resolution and quality
flags must still be audited before any number is presented as final challenge
evidence.
