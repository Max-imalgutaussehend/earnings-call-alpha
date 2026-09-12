"""Price and benchmark-factor data via yfinance and Kenneth French Data Library."""
from __future__ import annotations

import io
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf

from src.config import FF_FACTORS_URL, PRICES_DIR, SEC_USER_AGENT


def fetch_prices(ticker: str, start: date, end: date, cache: bool = True) -> pd.DataFrame:
    cache_path = PRICES_DIR / f"{ticker}.parquet"
    if cache and cache_path.exists():
        df = pd.read_parquet(cache_path)
        if df.index.min().date() <= start and df.index.max().date() >= end:
            return df.loc[str(start) : str(end)]

    df = yf.download(ticker, start=start - timedelta(days=5), end=end + timedelta(days=5), progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.to_parquet(cache_path)
    return df.loc[str(start) : str(end)]


def fetch_fama_french_daily(cache: bool = True) -> pd.DataFrame:
    """Fama-French 3-factor daily returns (Mkt-RF, SMB, HML, RF), in decimal form."""
    cache_path = PRICES_DIR / "ff3_daily.parquet"
    if cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    resp = requests.get(FF_FACTORS_URL, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = zf.namelist()[0]
        raw = zf.read(name).decode("latin-1")

    lines = raw.splitlines()
    start_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("19") or l.strip().startswith("20"))
    end_idx = next(i for i, l in enumerate(lines[start_idx:], start_idx) if l.strip() == "")
    data_lines = lines[start_idx:end_idx]

    rows = []
    for line in data_lines:
        parts = line.split(",")
        if len(parts) != 5:
            continue
        d, mkt_rf, smb, hml, rf = parts
        rows.append((d.strip(), float(mkt_rf), float(smb), float(hml), float(rf)))

    df = pd.DataFrame(rows, columns=["date", "Mkt-RF", "SMB", "HML", "RF"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date") / 100.0  # FF reports in percent
    df.to_parquet(cache_path)
    return df


if __name__ == "__main__":
    px = fetch_prices("AAPL", date(2024, 1, 1), date(2024, 3, 1))
    print(px.tail())
    ff = fetch_fama_french_daily()
    print(ff.tail())
