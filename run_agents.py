"""Get a multi-agent second opinion on one ticker with TradingAgents + Claude.

    python run_agents.py SOFI                # analyse as of today
    python run_agents.py SOFI 2026-09-01     # analyse a past date (to compare with what happened)

Needs ANTHROPIC_API_KEY in .env (see README). Each run makes dozens of model
calls, so it costs money: start with the cheaper model settings below.
The output is a research opinion, not a trade signal.
"""
from __future__ import annotations

import datetime as dt
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else dt.date.today().isoformat()

    config = DEFAULT_CONFIG.copy()
    config.update(
        llm_provider="anthropic",
        deep_think_llm="claude-sonnet-5",      # judge / portfolio manager
        quick_think_llm="claude-haiku-4-5",    # analysts: cheap and fast
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
        output_language="English",
    )

    graph = TradingAgentsGraph(debug=True, config=config)
    _, decision = graph.propagate(ticker, date)
    print(f"\n{ticker} as of {date}: {decision}")


if __name__ == "__main__":
    main()
