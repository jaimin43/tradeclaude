"""Command line: python -m tradeclaude <command> ...

  check [SYMBOL ...]       checklist for symbols (default: every holding in portfolio.json)
  odds SYMBOL TARGET [--days N]
                           chance of touching TARGET (and the mirror-image downside) in N days
  plan SYMBOL --entry E --stop S --target T [--max-cost C] [--borrowed B]
                           position size, reward:risk, fees and interest for a trade
  paper open SYMBOL --entry E --stop S --target T --shares N --reason "..."
  paper close ID --exit X
  paper status             open trades vs live price, plus closed-trade stats
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import checklist, data, paper
from . import indicators as ind

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO = ROOT / "portfolio.json"
JOURNAL = ROOT / "paper_trades.csv"


def load_portfolio() -> dict:
    return json.loads(PORTFOLIO.read_text())


def cmd_check(args) -> None:
    symbols = args.symbols or [h["symbol"] for h in load_portfolio()["holdings"]]
    for s in symbols:
        try:
            df = data.history(s, "2y")
            print(checklist.render(checklist.build_report(s, df, data.next_earnings(s))))
        except Exception as e:  # keep going for the other tickers
            print(f"== {s}: {e}")
        print()


def cmd_odds(args) -> None:
    df = data.history(args.symbol, "1y")
    price = float(df["Close"].iloc[-1])
    vol = ind.annual_volatility(df["Close"])
    move = args.target / price - 1
    down = price * (1 - abs(move))
    print(f"{args.symbol} ${price:.2f}, volatility {vol:.0%}/yr, horizon {args.days} trading days")
    print(f"  touch {args.target:.2f} ({move:+.1%}): {ind.touch_probability(price, args.target, vol, args.days):.0%}")
    print(f"  touch {down:.2f} ({-abs(move):+.1%}): {ind.touch_probability(price, down, vol, args.days):.0%}")
    hr = ind.historical_hit_rate(df.iloc[-120:], abs(move), args.days)
    if hr:
        print(f"  last {hr['windows']} windows: up hit {hr['up']:.0%}, down hit {hr['down']:.0%}, "
              f"up first {hr['up_first']:.0%}, down first {hr['down_first']:.0%}")
    print("  Similar up/down odds mean no edge: the setup (trend, levels, timing) has to supply it.")


def cmd_plan(args) -> None:
    pf = load_portfolio()
    is_us = not args.symbol.upper().endswith(".TO")
    account = args.account
    if account is None:
        account = 0.0
        for h in pf["holdings"]:
            px = float(data.history(h["symbol"], "5d")["Close"].iloc[-1])
            account += px * h["shares"] * (data.usd_cad() if h["currency"] == "USD" else 1.0)
        if is_us:
            account /= data.usd_cad()
    p = checklist.plan_trade(
        args.entry, args.stop, args.target, account,
        risk_pct=pf["risk_per_trade_pct"], max_cost=args.max_cost,
        fx_fee_pct=pf["fx_fee_pct"] if is_us and args.convert else 0.0,
        borrowed=args.borrowed, apr_pct=pf["line_of_credit_apr_pct"], days=args.days,
    )
    cur = "USD" if is_us else "CAD"
    print(f"{args.symbol}: buy {p.shares} shares @ {args.entry} = {p.cost:.2f} {cur}")
    print(f"  risk to stop {p.risk:.2f} | reward to target {p.reward:.2f} | reward:risk {p.reward_risk:.1f}:1")
    print(f"  fx fees {p.fx_fees:.2f} | interest {p.interest:.2f}")
    print(f"  net if target hit {p.net_if_target:+.2f} | net if stopped out {p.net_if_stop:+.2f}")
    if p.reward_risk < 2:
        print("  ! reward:risk under 2:1 - most traders skip setups like this")


def cmd_paper(args) -> None:
    if args.action == "open":
        row = paper.open_trade(JOURNAL, args.symbol, args.entry, args.stop, args.target, args.shares, args.reason)
        print(f"opened #{row['id']}: {row['shares']} {row['symbol']} @ {row['entry']}")
    elif args.action == "close":
        row = paper.close_trade(JOURNAL, args.id, args.exit)
        print(f"closed #{row['id']} {row['symbol']}: P&L {row['pnl']}")
    else:
        for r in paper.open_trades(JOURNAL):
            px = float(data.history(r["symbol"], "5d")["Close"].iloc[-1])
            flag = "STOP HIT" if px <= float(r["stop"]) else "TARGET HIT" if px >= float(r["target"]) else ""
            pnl = (px - float(r["entry"])) * float(r["shares"])
            print(f"#{r['id']} {r['symbol']} entry {r['entry']} now {px:.2f} P&L {pnl:+.2f} {flag}")
        s = paper.summary(JOURNAL)
        print(f"closed: {s['trades']} trades, P&L {s['total_pnl']:+.2f}, win rate {s['win_rate']:.0%}, "
              f"avg win {s['avg_win']:.2f}, avg loss {s['avg_loss']:.2f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="tradeclaude", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("symbols", nargs="*")
    c.set_defaults(func=cmd_check)

    o = sub.add_parser("odds")
    o.add_argument("symbol")
    o.add_argument("target", type=float)
    o.add_argument("--days", type=int, default=21)
    o.set_defaults(func=cmd_odds)

    p = sub.add_parser("plan")
    p.add_argument("symbol")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--target", type=float, required=True)
    p.add_argument("--account", type=float, help="account value in the trade's currency (default: priced from portfolio.json)")
    p.add_argument("--max-cost", type=float, help="cap on money put into this trade")
    p.add_argument("--borrowed", type=float, default=0.0, help="amount borrowed from the line of credit")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--no-convert", dest="convert", action="store_false",
                   help="US trade paid from USD cash (no FX fee)")
    p.set_defaults(func=cmd_plan)

    pp = sub.add_parser("paper")
    pp.add_argument("action", choices=["open", "close", "status"])
    pp.add_argument("symbol_or_id", nargs="?")
    pp.add_argument("--entry", type=float)
    pp.add_argument("--stop", type=float)
    pp.add_argument("--target", type=float)
    pp.add_argument("--shares", type=int)
    pp.add_argument("--reason", default="")
    pp.add_argument("--exit", type=float)
    pp.set_defaults(func=cmd_paper)

    args = ap.parse_args(argv)
    if args.cmd == "paper":
        args.symbol = args.id = args.symbol_or_id
    args.func(args)


if __name__ == "__main__":
    main()
