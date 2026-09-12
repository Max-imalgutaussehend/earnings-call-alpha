# Data Provenance

Every transcript used in this project must be logged here with its exact
source, to keep the sample auditable and to avoid any ambiguity about
licensing/ToS. Rule: **only use transcripts either (a) filed by the company
itself with the SEC (8-K Exhibit 99.x), or (b) published by the company on
its own investor-relations site.** No third-party transcript aggregators are
scraped, to avoid ToS issues entirely.

## How to add a call

1. Find the company's 10-Q/10-K/8-K earnings release on SEC EDGAR
   (`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<ticker>&type=8-K`)
   filed on or immediately after the call date.
2. Check the company's IR site (`investor.<company>.com` or similar) for a
   posted transcript or webcast replay with transcript — most large caps post
   these for free.
3. Save the raw transcript text to `data/raw/transcripts/<TICKER>_<YYYY-MM-DD>.txt`.
4. Add a row to the table below with the exact source URL and retrieval date.

## Sample log (fill in as calls are added)

| Ticker | Call Date | Fiscal Period | Source URL | Publisher | Retrieved |
|--------|-----------|----------------|------------|-----------|-----------|
| _(none yet — populate during Phase 1)_ | | | | | |

## Why not use a scraped aggregator dataset?

Third-party transcript sites' terms of service frequently prohibit
redistribution/scraping, and dataset provenance on sites like Kaggle is often
unclear (repackaged aggregator content without a documented chain of
custody). For a project whose entire premise is methodological rigor, using
data whose own provenance is questionable would undercut the point. The
first-party-only rule keeps the (smaller) sample fully defensible.
