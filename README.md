# OPC Radar — 一人公司商机雷达
Static site in `site/` (GitHub Pages). Data: `site/data/items.json`.
Refresh: `python3 scripts/refresh.py` (GitHub search + HN Algolia; merges hand-curated `scripts/curated.json`). To automate: move `ops/workflows/*.yml` into `.github/workflows/` (needs a token with workflow scope). Until then publish with `git subtree push --prefix site origin gh-pages`.
