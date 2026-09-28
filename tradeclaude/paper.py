"""Paper-trading journal stored in a CSV. Practise with fake money first."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

FIELDS = ["id", "symbol", "opened", "entry", "stop", "target", "shares", "reason",
          "closed", "exit", "pnl"]


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def open_trade(path: Path, symbol: str, entry: float, stop: float, target: float,
               shares: int, reason: str, today: dt.date | None = None) -> dict:
    rows = _read(path)
    row = {
        "id": str(max((int(r["id"]) for r in rows), default=0) + 1),
        "symbol": symbol.upper(), "opened": str(today or dt.date.today()),
        "entry": entry, "stop": stop, "target": target, "shares": shares, "reason": reason,
        "closed": "", "exit": "", "pnl": "",
    }
    rows.append(row)
    _write(path, rows)
    return row


def close_trade(path: Path, trade_id: str, exit_price: float, today: dt.date | None = None) -> dict:
    rows = _read(path)
    for r in rows:
        if r["id"] == str(trade_id) and not r["closed"]:
            r["closed"] = str(today or dt.date.today())
            r["exit"] = exit_price
            r["pnl"] = round((exit_price - float(r["entry"])) * float(r["shares"]), 2)
            _write(path, rows)
            return r
    raise KeyError(f"no open trade with id {trade_id}")


def summary(path: Path) -> dict:
    closed = [r for r in _read(path) if r["closed"]]
    pnls = [float(r["pnl"]) for r in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    return {
        "trades": len(pnls),
        "total_pnl": round(sum(pnls), 2),
        "win_rate": len(wins) / len(pnls) if pnls else 0.0,
        "avg_win": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(losses) / len(losses) if losses else 0.0,
    }


def open_trades(path: Path) -> list[dict]:
    return [r for r in _read(path) if not r["closed"]]
