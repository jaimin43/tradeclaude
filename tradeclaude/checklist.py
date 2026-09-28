"""The pre-trade checklist: trend, momentum, volatility, levels, calendar."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from . import indicators as ind


@dataclass
class Report:
    symbol: str
    price: float
    sma50: float | None
    sma200: float | None
    rsi14: float | None
    atr14: float | None
    annual_vol: float | None
    support: float
    resistance: float
    high_52w: float
    low_52w: float
    earnings: dt.date | None

    @property
    def trend(self) -> str:
        return ind.trend_label(self.price, self.sma50, self.sma200)

    def warnings(self, horizon_days: int = 30) -> list[str]:
        out = []
        if self.trend == "DOWNTREND":
            out.append("below 50- and 200-day averages: buying here is fighting the trend")
        if self.rsi14 is not None and self.rsi14 > 70:
            out.append(f"RSI {self.rsi14:.0f} is overbought: chasing risk")
        if self.rsi14 is not None and self.rsi14 < 30:
            out.append(f"RSI {self.rsi14:.0f} is oversold: bounce possible, but wait for confirmation")
        if self.earnings and (self.earnings - dt.date.today()).days <= horizon_days:
            out.append(f"earnings on {self.earnings}: overnight gap risk inside your holding window")
        if self.annual_vol is not None and self.annual_vol > 0.45:
            out.append(f"high volatility ({self.annual_vol:.0%}/yr): size small, stops get hit often")
        return out


def build_report(symbol: str, df: pd.DataFrame, earnings: dt.date | None = None) -> Report:
    close = df["Close"]
    support, resistance = ind.support_resistance(df, 20)
    year = df.iloc[-252:]
    return Report(
        symbol=symbol,
        price=float(close.iloc[-1]),
        sma50=ind.sma(close, 50),
        sma200=ind.sma(close, 200),
        rsi14=ind.rsi(close, 14),
        atr14=ind.atr(df, 14),
        annual_vol=ind.annual_volatility(close),
        support=support,
        resistance=resistance,
        high_52w=float(year["High"].max()),
        low_52w=float(year["Low"].min()),
        earnings=earnings,
    )


def _fmt(x: float | None, spec: str = ".2f") -> str:
    return "n/a" if x is None else format(x, spec)


def render(r: Report) -> str:
    lines = [
        f"== {r.symbol}  ${r.price:.2f}  [{r.trend}]",
        f"   50d avg {_fmt(r.sma50)} | 200d avg {_fmt(r.sma200)} | RSI {_fmt(r.rsi14, '.0f')}"
        f" | ATR ${_fmt(r.atr14)}/day | vol {_fmt(r.annual_vol, '.0%') if r.annual_vol else 'n/a'}",
        f"   20d support {r.support:.2f} | 20d resistance {r.resistance:.2f}"
        f" | 52w {r.low_52w:.2f} - {r.high_52w:.2f} ({r.price / r.high_52w - 1:+.0%} from high)",
        f"   next earnings: {r.earnings or 'none / unknown'}",
    ]
    lines += [f"   ! {w}" for w in r.warnings()]
    return "\n".join(lines)


@dataclass
class Plan:
    shares: int
    cost: float
    risk: float
    reward: float
    reward_risk: float
    fx_fees: float
    interest: float
    net_if_target: float
    net_if_stop: float


def plan_trade(
    entry: float,
    stop: float,
    target: float,
    account_value: float,
    risk_pct: float = 1.0,
    max_cost: float | None = None,
    fx_fee_pct: float = 0.0,
    borrowed: float = 0.0,
    apr_pct: float = 0.0,
    days: int = 30,
) -> Plan:
    """Size a trade so that hitting the stop loses at most `risk_pct` of the account.

    All money is in the trade's currency. `fx_fee_pct` is charged on the way in
    and out (e.g. 1.5 for Wealthsimple CAD<->USD).
    """
    if not stop < entry < target:
        raise ValueError("need stop < entry < target for a long trade")
    per_share_risk = entry - stop
    shares = int(account_value * risk_pct / 100 // per_share_risk)
    if max_cost is not None:
        shares = min(shares, int(max_cost // entry))
    cost = shares * entry
    fx = cost * fx_fee_pct / 100 * 2
    interest = borrowed * apr_pct / 100 * days / 365
    risk = shares * per_share_risk
    reward = shares * (target - entry)
    return Plan(
        shares=shares,
        cost=cost,
        risk=risk,
        reward=reward,
        reward_risk=(target - entry) / per_share_risk,
        fx_fees=fx,
        interest=interest,
        net_if_target=reward - fx - interest,
        net_if_stop=-risk - fx - interest,
    )
