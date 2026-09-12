"""SEC EDGAR access: CIK lookup, 8-K filing index, filing document fetch.

All requests use a descriptive User-Agent per SEC's fair-access policy
(https://www.sec.gov/os/accessing-edgar-data). Rate-limited to <=10 req/s.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from src.config import SEC_USER_AGENT, TRANSCRIPTS_DIR

HEADERS = {"User-Agent": SEC_USER_AGENT}
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

_RATE_LIMIT_S = 0.15


def _get(url: str) -> requests.Response:
    time.sleep(_RATE_LIMIT_S)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp


def load_ticker_cik_map(cache_path: Path | None = None) -> dict[str, int]:
    """Return {ticker: cik} using SEC's official ticker->CIK mapping, cached locally."""
    cache_path = cache_path or (TRANSCRIPTS_DIR.parent / "ticker_cik_map.json")
    if cache_path.exists():
        raw = json.loads(cache_path.read_text())
    else:
        raw = _get(_TICKER_MAP_URL).json()
        cache_path.write_text(json.dumps(raw))
    return {v["ticker"].upper(): v["cik_str"] for v in raw.values()}


def get_8k_filings(cik: int, forms=("8-K",)) -> list[dict]:
    """Return filing metadata (accession number, filing date, primary document) for a CIK."""
    data = _get(_SUBMISSIONS_URL.format(cik=cik)).json()
    recent = data["filings"]["recent"]
    out = []
    n = len(recent["form"])
    for i in range(n):
        if recent["form"][i] in forms:
            out.append(
                {
                    "accessionNumber": recent["accessionNumber"][i],
                    "filingDate": recent["filingDate"][i],
                    "primaryDocument": recent["primaryDocument"][i],
                    "items": recent.get("items", [""] * n)[i],
                }
            )
    return out


def filing_index_url(cik: int, accession_number: str) -> str:
    acc_nodash = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/"


def fetch_filing_document(cik: int, accession_number: str, document: str) -> str:
    url = filing_index_url(cik, accession_number) + document
    return _get(url).text


if __name__ == "__main__":
    m = load_ticker_cik_map()
    print("AAPL CIK:", m.get("AAPL"))
    filings = get_8k_filings(m["AAPL"])
    print(f"{len(filings)} 8-K filings found for AAPL; most recent:", filings[0] if filings else None)
