# TrueFare

Free fare comparison site. A GitHub Action collects prices every 6 hours, saves them to `docs/data/fares.json`, and GitHub Pages shows them. No server, no paid APIs.

## Set up from your phone

1. **Create a public repo** on GitHub (public keeps Actions and Pages free).
2. **Add each file** (GitHub app or github.com in your phone browser: Add file > Create new file, type the full path, paste the content, commit):
   - `routes.json`
   - `collector/collect.py`
   - `.github/workflows/collect.yml`
   - `docs/index.html`
   - `docs/data/fares.json`
   - `docs/data/history.json`
3. **Turn on the site:** Settings > Pages > Deploy from a branch > `main` and folder `/docs` > Save.
4. **Get a free Travelpayouts token** (sign up, connect the Aviasales program, copy the API token and your marker/partner number).
5. **Add secrets:** Settings > Secrets and variables > Actions > New repository secret:
   - `TP_TOKEN` = your API token
   - `TP_MARKER` = your marker number
6. **Add your marker to the page:** edit `docs/index.html`, set `const MARKER = "123456";`.
7. **Run it:** Actions tab > collect-fares > Run workflow. Check the log, then open your Pages link.

## If Google Flights gets blocked

GitHub runs from datacenter addresses, so Google may show a captcha. The log will say `google failed`. Travelpayouts keeps working. To stop trying Google: Settings > Secrets and variables > Actions > Variables > add `USE_GOOGLE` = `0`.

## Change routes

Edit `routes.json`. Each entry: `from`, `to` (airport codes), `cur` (currency), `ahead` (days until departure), `stay` (trip length). `group` is `india` or `holiday`.

## Notes

- Google Flights scraping may break when Google changes its page and goes against Google's terms. It is a benchmark, not a product feature. Check the legal side for your location.
- Travelpayouts prices come from a cache of recent searches, so confirm on the booking site.
- `docs/data/history.json` stores the cheapest price per route per day, ready for price alerts and charts later.
