"""Pure indicator math on pandas Series/DataFrames (columns: High, Low, Close).

No network access here, so everything is unit-testable with fixture data.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import pandas as pd

TRADING_DAYS = 252


def sma(close: pd.Series, period: int) -> float | None:
    if len(close) < period:
        return None
    return float(close.iloc[-period:].mean())


def rsi(close: pd.Series, period: int = 14) -> float | None:
    """Wilder's RSI (the version most charting apps show)."""
    if len(close) <= period:
        return None
    delta = close.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Wilder's Average True Range: the typical daily move in dollars."""
    if len(df) <= period:
        return None
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1).iloc[1:]
    return float(tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().iloc[-1])


def annual_volatility(close: pd.Series, lookback: int = 100) -> float | None:
    rets = (close / close.shift(1)).apply(math.log).dropna().iloc[-lookback:]
    if len(rets) < 20:
        return None
    return float(rets.std() * math.sqrt(TRADING_DAYS))


def support_resistance(df: pd.DataFrame, lookback: int = 20) -> tuple[float, float]:
    """Recent swing low / high over `lookback` days (a simple, honest proxy)."""
    window = df.iloc[-lookback:]
    return float(window["Low"].min()), float(window["High"].max())


def touch_probability(price: float, level: float, annual_vol: float, days: int) -> float:
    """Chance the price *touches* `level` within `days` trading days.

    Driftless random-walk (reflection principle). It says nothing about
    direction; compare the up and down numbers to see the symmetry.
    """
    if annual_vol <= 0 or days <= 0:
        return 0.0
    sigma = annual_vol * math.sqrt(days / TRADING_DAYS)
    z = abs(math.log(level / price)) / sigma
    return min(1.0, 2 * (1 - NormalDist().cdf(z)))


def historical_hit_rate(df: pd.DataFrame, pct: float, days: int) -> dict[str, float] | None:
    """Over past windows, how often +pct / -pct was touched, and which came first."""
    h, l, c = df["High"].tolist(), df["Low"].tolist(), df["Close"].tolist()
    n = len(c) - days
    if n < 10:
        return None
    up = down = up_first = down_first = 0
    for i in range(n):
        tu, td = c[i] * (1 + pct), c[i] * (1 - pct)
        hit_u = next((j for j in range(i + 1, i + days + 1) if h[j] >= tu), None)
        hit_d = next((j for j in range(i + 1, i + days + 1) if l[j] <= td), None)
        up += hit_u is not None
        down += hit_d is not None
        if hit_u is not None and (hit_d is None or hit_u < hit_d):
            up_first += 1
        elif hit_d is not None:
            down_first += 1
    return {"windows": n, "up": up / n, "down": down / n, "up_first": up_first / n, "down_first": down_first / n}


def trend_label(price: float, sma50: float | None, sma200: float | None) -> str:
    if sma50 is None or sma200 is None:
        return "not enough data"
    if price > sma50 > sma200:
        return "UPTREND"
    if price < sma50 < sma200:
        return "DOWNTREND"
    return "MIXED"
