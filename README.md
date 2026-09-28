# tradeclaude

A small personal toolkit for trading a Wealthsimple TFSA more carefully:

1. **Checklist**: trend, RSI, ATR, support/resistance, 52-week range and earnings date for every holding, with warnings.
2. **Odds**: how likely a price target is to be touched, *and* the same-sized drop, so you can see whether there is any edge.
3. **Plan**: position size from a fixed risk budget, reward:risk, FX fees and line-of-credit interest, *before* you buy.
4. **Paper journal**: log practice trades with fake money and track win rate and P&L.
5. **Agents (optional)**: a multi-agent AI second opinion via [TradingAgents](https://github.com/TauricResearch/TradingAgents) and Claude.

Nothing here places orders. It is for research and practice, not financial advice.

## Setup (once)

Needs Python 3.10+.

```bash
git clone https://github.com/jaimin43/tradeclaude.git
cd tradeclaude
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # should say "8 passed"
```

Price data comes from Yahoo Finance through `yfinance`: free, no key needed. Canadian tickers use `.TO` (e.g. `XEQT.TO`).
Edit `portfolio.json` whenever your holdings change.

## Daily use

```bash
python -m tradeclaude check                 # checklist for every holding
python -m tradeclaude check SOFI URA        # or specific tickers
python -m tradeclaude odds SOFI 17          # chance of touching $17 (and the mirror drop) in 21 trading days
python -m tradeclaude plan SOFI --entry 16.5 --stop 15.2 --target 17.5 --max-cost 360 --borrowed 500
```

`plan` sizes the trade so that hitting your stop loses at most `risk_per_trade_pct` (1%) of the account,
then caps it at `--max-cost`. It adds 1.5% FX each way for US tickers (use `--no-convert` if you pay from USD cash)
and interest at the line-of-credit rate in `portfolio.json`.

### Paper trading: do this for a month before using real money

```bash
python -m tradeclaude paper open SOFI --entry 16.5 --stop 15.2 --target 17.5 --shares 21 --reason "held 16 support, closed above 16.5"
python -m tradeclaude paper status          # open trades vs live price, flags stop/target hits
python -m tradeclaude paper close 1 --exit 17.4
```

Trades are saved in `paper_trades.csv`. After roughly 10 trades, `status` shows whether your average win is bigger than your average loss.
Only move to real money if it is.

## Optional: TradingAgents second opinion

```bash
pip install git+https://github.com/TauricResearch/TradingAgents.git
cp .env.example .env        # then put your ANTHROPIC_API_KEY in .env
python run_agents.py SOFI
```

Analyst agents (fundamentals, news, sentiment, technical) feed a bull-vs-bear debate, a trader, a risk team
and a portfolio manager, which outputs Buy / Overweight / Hold / Underweight / Sell with reasoning.
It uses `claude-haiku-4-5` for the analysts and `claude-sonnet-5` for the final calls to keep costs down.
Expect roughly $1-5 per run. Treat the output as a structured argument to read, not a signal to follow.

## Rules this toolkit enforces (or nags about)

- Don't buy below both the 50- and 200-day averages without a clear reason.
- Know the earnings date: a stop-loss can't protect you from an overnight gap.
- Risk at most 1% of the account per trade, and want at least 2:1 reward:risk.
- Count FX fees and interest: on a $500 trade they can eat most of a small gain.
- TFSA: frequent trading can get gains taxed as business income, and losses permanently use up contribution room.
