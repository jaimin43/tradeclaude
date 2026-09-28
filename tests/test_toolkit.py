import datetime as dt
from pathlib import Path

import pytest

from tradeclaude import checklist, data, paper
from tradeclaude import indicators as ind

FIXTURE = Path(__file__).parent / "fixtures" / "sofi_daily.csv"  # SOFI, May 5 - Sep 25 2026


@pytest.fixture
def sofi():
    return data.load_csv(str(FIXTURE))


def test_indicators_on_real_prices(sofi):
    assert len(sofi) == 100
    r = ind.rsi(sofi["Close"])
    assert 0 < r < 100
    a = ind.atr(sofi)
    assert 0.5 < a < 1.0  # SOFI moved roughly $0.70 a day
    assert 0.4 < ind.annual_volatility(sofi["Close"]) < 0.7
    assert ind.sma(sofi["Close"], 200) is None  # only 100 days


def test_rsi_extremes():
    import pandas as pd
    assert ind.rsi(pd.Series(range(1, 40), dtype=float)) == 100.0
    assert ind.rsi(pd.Series(range(40, 1, -1), dtype=float)) < 1


def test_hit_rate_matches_manual_count(sofi):
    hr = ind.historical_hit_rate(sofi, 0.0625, 21)
    assert hr["windows"] == 79
    assert round(hr["up"], 2) == 0.81 and round(hr["down"], 2) == 0.62
    assert hr["up_first"] + hr["down_first"] <= 1


def test_touch_probability_is_symmetric_in_log_space():
    up = ind.touch_probability(16, 17, 0.53, 21)
    down = ind.touch_probability(16, 16 * 16 / 17, 0.53, 21)
    assert up == pytest.approx(down)
    assert 0.6 < up < 0.8


def test_trend_label():
    assert ind.trend_label(16.0, 17.56, 19.16) == "DOWNTREND"
    assert ind.trend_label(20.0, 19.0, 18.0) == "UPTREND"
    assert ind.trend_label(18.0, 17.0, 19.0) == "MIXED"


def test_report_warns_about_earnings(sofi):
    soon = dt.date.today() + dt.timedelta(days=10)
    rep = checklist.build_report("SOFI", sofi, earnings=soon)
    assert any("earnings" in w for w in rep.warnings())
    assert "SOFI" in checklist.render(rep)


def test_plan_trade_sizes_by_risk_and_counts_costs():
    p = checklist.plan_trade(entry=16.0, stop=15.2, target=17.0, account_value=7000,
                             risk_pct=1.0, max_cost=360, fx_fee_pct=1.5,
                             borrowed=500, apr_pct=4.95, days=30)
    assert p.shares == 22  # capped by $360, not by the $70 risk budget (87 shares)
    assert p.reward_risk == pytest.approx(1.25)
    assert p.fx_fees == pytest.approx(22 * 16 * 0.03)
    assert p.interest == pytest.approx(2.03, abs=0.01)
    assert p.net_if_target == pytest.approx(22 - p.fx_fees - p.interest)
    with pytest.raises(ValueError):
        checklist.plan_trade(16, 17, 18, 1000)


def test_paper_journal_roundtrip(tmp_path):
    j = tmp_path / "trades.csv"
    t = paper.open_trade(j, "sofi", 16.0, 15.2, 17.0, 10, "bounce off support")
    assert paper.open_trades(j)[0]["symbol"] == "SOFI"
    paper.close_trade(j, t["id"], 17.0)
    s = paper.summary(j)
    assert s == {"trades": 1, "total_pnl": 10.0, "win_rate": 1.0, "avg_win": 10.0, "avg_loss": 0.0}
    with pytest.raises(KeyError):
        paper.close_trade(j, t["id"], 18.0)
