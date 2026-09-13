"""Project-wide configuration: universe, paths, dates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
TRANSCRIPTS_DIR = DATA_RAW / "transcripts"
PRICES_DIR = DATA_RAW / "prices"

for d in (DATA_RAW, DATA_PROCESSED, TRANSCRIPTS_DIR, PRICES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Curated universe: 8-10 large caps across distinct sectors, chosen so that
# each has a clearly identifiable "core segment" in its revenue reporting
# (needed for the core-segment sentiment feature).
#
# AAPL deliberately excluded: verified it has no first-party full Q&A
# transcript (SEC 8-K Ex-99.1 is press-release only, no IR transcript
# posted) -- see docs/data_sources.md. Not used rather than substituted
# with a lower-quality (third-party-scraped) source.
#
# JNJ excluded: investor.jnj.com is behind Cloudflare bot-challenge
# middleware that blocks non-browser fetches; PG excluded: pginvestor.com
# does not post first-party transcripts, only third-party aggregators
# (Seeking Alpha, Motley Fool) carry them, which the sourcing rule in
# docs/data_sources.md excludes. GOOGL and GS are still candidates for a
# future addition but have not yet been verified to have a first-party
# transcript -- do not add them to the manifest without checking first.
UNIVERSE = {
    "MSFT": {"sector": "Technology", "core_segment_keywords": ["azure", "cloud", "intelligent cloud"]},
    "GOOGL": {"sector": "Technology", "core_segment_keywords": ["search", "advertising"]},
    "JPM": {"sector": "Financials", "core_segment_keywords": ["consumer", "community banking"]},
    "BAC": {"sector": "Financials", "core_segment_keywords": ["consumer banking", "deposits", "global banking"]},
    "GS": {"sector": "Financials", "core_segment_keywords": ["global banking", "markets"]},
    "CAT": {"sector": "Industrials", "core_segment_keywords": ["construction industries", "resource industries"]},
    "XOM": {"sector": "Energy", "core_segment_keywords": ["upstream", "exploration", "permian", "guyana"]},
}

TICKERS = list(UNIVERSE.keys())

# SEC EDGAR requires a descriptive User-Agent identifying the requester.
SEC_USER_AGENT = "Portfolio Research Project - max.rml@web.de"

EVENT_WINDOWS = [1, 3]  # trading days after call date
PRICE_LOOKBACK_DAYS = 15  # calendar days before call date, for benchmark alignment
PRICE_LOOKAHEAD_DAYS = 10

FF_FACTORS_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)

TRANSACTION_COST_BPS = 10  # per side, stated assumption for the illustrative backtest
