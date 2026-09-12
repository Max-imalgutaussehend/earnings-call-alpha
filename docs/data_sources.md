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
| JPM | 2026-01-13 | 4Q25 | jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/quarterly-earnings/2025/4th-quarter/jpm-4q25-earnings-call-transcript.pdf | JPMorganChase IR (first-party PDF) | 2026-09-12 |
| MSFT | 2026-07-29 | FY26 Q4 | microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4 | Microsoft IR (first-party HTML transcript) | 2026-09-12 |

Both sources are full transcripts (prepared remarks + complete analyst Q&A
with speaker names/firms). Raw PDF text was normalized to plain
`Speaker: text` format via `src/data/transcript_ingest.py`
(`normalize_streetevents_pdf` for the JPM PDF extraction; the MSFT HTML page
text needed no transformation, its `SPEAKER:` lines already matched the
target format).

**Apple (AAPL) was evaluated and excluded**: its SEC 8-K Exhibit 99.1
filings contain only the financial press release (no call dialogue), and
investor.apple.com does not post a first-party call transcript, only a
webcast replay. Dropped from the universe rather than substituting a
lower-quality source.

## Why not use a scraped aggregator dataset?

Third-party transcript sites' terms of service frequently prohibit
redistribution/scraping, and dataset provenance on sites like Kaggle is often
unclear (repackaged aggregator content without a documented chain of
custody). For a project whose entire premise is methodological rigor, using
data whose own provenance is questionable would undercut the point. The
first-party-only rule keeps the (smaller) sample fully defensible.
