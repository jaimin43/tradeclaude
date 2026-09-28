"""Market data via yfinance (free, no API key; Canadian tickers use the .TO suffix)."""
from __future__ import annotations

import datetime as dt

import pandas as pd


def history(symbol: str, period: str = "1y") -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No price data for {symbol} (check the ticker, e.g. XEQT.TO for TSX)")
    return df[["Open", "High", "Low", "Close", "Volume"]]


def next_earnings(symbol: str) -> dt.date | None:
    """Next earnings date, or None (ETFs have none; Yahoo sometimes omits it)."""
    import yfinance as yf

    try:
        cal = yf.Ticker(symbol).calendar
    except Exception:
        return None
    dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
    today = dt.date.today()
    upcoming = [d for d in (dates or []) if isinstance(d, dt.date) and d >= today]
    return min(upcoming) if upcoming else None


def usd_cad() -> float:
    return float(history("USDCAD=X", period="5d")["Close"].iloc[-1])


def load_csv(path: str) -> pd.DataFrame:
    """Load an OHLC CSV with a date column (used by tests and offline runs)."""
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    return df.rename(columns=str.title)
