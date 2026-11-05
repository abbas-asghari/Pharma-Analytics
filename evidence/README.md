# Visual verification

`figures/` contains **14 complete SVG figures covering all ten questions**, exported from `default_results.json` with Apache ECharts. The Persian font is embedded. These are the complete standalone visual deliverables; the JPEG files below are selected browser screenshots and can show only part of a long page.

Screenshots show the real browser dashboard with the default 1401 → 1402 filters:

- `q01-market.jpg`: annual sales volume and value (Q1).
- `q02-q03-growth.jpg`: value and volume growth (Q2, Q3).
- `q04-q05-suppliers.jpg`: suppliers ranked by target-year value, same order in both charts.
- `q06-q07-distributors.jpg`: distributors ranked by target-year volume, same order in both charts.
- `q08-atc.jpg`: value and volume by ATC L1 (Q8).
- `q09-atc-shares.jpg`: signed percentage stacks including Unknown (Q9).
- `q10-otc.jpg`: OTC vs Rx (Q10).

`validation.json` compares the browser database queries with the original full-grain SQLite database. PostgreSQL server restore has not been run in this environment.

The screenshots are visual checks, not an alternative data source. Open the dashboard for interactive tooltips and exact numeric CSV exports. Browser download completion was not verifiable through the embedded browser automation; export button handlers and file endpoints are included.
