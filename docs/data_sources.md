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
| JPM | 2026-01-13 | 4Q25 | jpmorganchase.com/.../quarterly-earnings/2025/4th-quarter/jpm-4q25-earnings-call-transcript.pdf | JPMorganChase IR (first-party PDF) | 2026-09-12 |
| JPM | 2026-07-14 | 2Q26 | jpmorganchase.com/.../quarterly-earnings/2026/2nd-quarter/2Q26-earnings-transcript.pdf | JPMorganChase IR (first-party PDF) | 2026-09-13 |
| MSFT | 2026-07-29 | FY26 Q4 | microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4 | Microsoft IR (first-party HTML transcript) | 2026-09-12 |
| BAC | 2026-07-14 | 2Q26 | d1io3yog0oux5.cloudfront.net/.../bankofamerica/.../2026-07-14+BAC+2Q+Earnings+Call_ADA.pdf | Bank of America IR (first-party PDF, hosted on BofA's IR CDN) | 2026-09-13 |
| BAC | 2026-04-15 | 1Q26 | d1io3yog0oux5.cloudfront.net/.../bankofamerica/.../2026-04-15+BAC+1Q+Earnings+Call_ADA.pdf | Bank of America IR (first-party PDF) | 2026-09-13 |
| CAT | 2026-04-30 | Q1 2026 | s25.q4cdn.com/358376879/.../Q1-2026-Earnings-Transcript.pdf | Caterpillar IR (first-party PDF, hosted on Caterpillar's IR CDN) | 2026-09-13 |
| CAT | 2026-01-29 | Q4 2025 | s25.q4cdn.com/358376879/.../4Q-2025-Caterpillar-Inc-Earnings-Conference-Call_Transcript.pdf | Caterpillar IR (first-party PDF) | 2026-09-13 |
| CAT | 2025-10-29 | Q3 2025 | investors.caterpillar.com/files/doc_financials/2025/q3/3Q-2025-Caterpillar-Inc-Earnings-Call-Transcript_-10-29-2025.pdf | Caterpillar IR (first-party PDF) | 2026-09-13 |
| XOM | 2024-08-02 | Q2 2024 | d1io3yog0oux5.cloudfront.net/.../exxonmobil/.../2Q24+Earnings+Call+Transcript_FINAL.pdf | ExxonMobil IR (first-party PDF, hosted on ExxonMobil's IR CDN) | 2026-09-13 |
| XOM | 2026-01-30 | Q4 2025 | d1io3yog0oux5.cloudfront.net/.../exxonmobil/.../4Q25+Earnings+Transcript.pdf | ExxonMobil IR (first-party PDF) | 2026-09-13 |

All sources are full transcripts (prepared remarks + complete analyst Q&A
with speaker names/firms), all hosted on the issuing company's own domain or
IR content CDN (Cloudfront/Q4cdn buckets under the company's own IR vendor
contract, not a third-party aggregator). Four distinct PDF/HTML shapes were
observed and each got its own normalizer in `src/data/transcript_ingest.py`:
JPM's `Q`/`A`-tagged blocks (`normalize_streetevents_pdf`), MSFT's HTML page
text (`SPEAKER:` lines needing no transformation), BAC's bare speaker-name
lines requiring a parsed roster to disambiguate from body text
(`normalize_bare_name_pdf`), and CAT's `Name^ text` caret-delimited format
with an explicit `CORPORATE SPEAKERS:`/`PARTICIPANTS:` roster
(`normalize_caret_delimited_pdf`). XOM's transcripts needed no normalizer at
all — their `Name:` labels already matched the pipeline's target format
directly.

**Wells Fargo (WFC), Procter & Gamble (PG), and Johnson & Johnson (JNJ) were
evaluated and excluded**: WFC's IR site posts only earnings-release PDFs (no
call dialogue); PG's transcripts are carried only by third-party aggregators
(Seeking Alpha, Motley Fool), which the first-party-only rule above
excludes; JNJ's investor relations site (investor.jnj.com) sits behind
Cloudflare bot-challenge middleware that blocks non-browser HTTP fetches
entirely, so its transcript (confirmed to exist) could not be retrieved
without simulating a real browser session, which was out of scope here.

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
