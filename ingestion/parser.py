import json
import time
from typing import Any, Dict, Optional


class MarketDataParser:
    """
    Normalises raw WebSocket payloads from multiple exchanges into a
    canonical dict schema:

        {
            "exchange":           str,
            "base":               str,
            "quote":              str,
            "bid":                float,
            "ask":                float,
            "exchange_timestamp": int,   # ms since epoch, from exchange
            "ingest_timestamp":   int,   # ms since epoch, local arrival
        }
    """

    @staticmethod
    def normalize_binance_ticker(raw_msg: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(raw_msg)
            if data.get("e") != "24hrTicker":
                return None
            symbol: str = data.get("s", "")
            base, quote = _split_symbol_binance(symbol)
            return {
                "exchange": "Binance",
                "base": base,
                "quote": quote,
                "bid": float(data["b"]),
                "ask": float(data["a"]),
                "exchange_timestamp": int(data["E"]),
                "ingest_timestamp": int(time.time() * 1000),
            }
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None

    @staticmethod
    def normalize_bybit_ticker(raw_msg: str) -> Optional[Dict[str, Any]]:
        """
        Parses Bybit V5 orderbook.1 stream (best bid/ask).

        The spot ticker stream does NOT carry bid/ask — we subscribe to
        orderbook.1 instead, which always has the best bid and best ask.

        Snapshot format:
          {"topic": "orderbook.1.BTCUSDT", "type": "snapshot",
           "data": {"b": [["price", "size"]], "a": [["price", "size"]]}}

        Delta format is identical but either side can be empty when unchanged.
        """
        try:
            data = json.loads(raw_msg)
            if data.get("type") not in ("snapshot", "delta"):
                return None
            topic: str = data.get("topic", "")
            if not topic.startswith("orderbook.1."):
                return None
            symbol = topic.split(".", 2)[2]          # "BTCUSDT"
            payload = data.get("data", {})
            bids = payload.get("b", [])
            asks = payload.get("a", [])
            if not bids or not asks:
                return None                          # delta with only one side — skip
            base, quote = _split_symbol_bybit(symbol)
            return {
                "exchange": "Bybit",
                "base": base,
                "quote": quote,
                "bid": float(bids[0][0]),
                "ask": float(asks[0][0]),
                "exchange_timestamp": int(data.get("ts", time.time() * 1000)),
                "ingest_timestamp": int(time.time() * 1000),
            }
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def normalize_okx_ticker(raw_msg: str) -> Optional[Dict[str, Any]]:
        """
        Parses OKX V5 tickers channel.

        OKX does NOT use an "action" field.  Every message looks like:
          {"arg": {"channel": "tickers", "instId": "BTC-USDT"},
           "data": [{"bidPx": "...", "askPx": "...", "ts": "...", ...}]}

        The subscribe-ack uses "event" instead of "arg", so the "arg" check
        naturally skips it.
        """
        try:
            data = json.loads(raw_msg)
            if "arg" not in data or "data" not in data:
                return None
            for item in data["data"]:
                inst_id: str = item.get("instId", "")
                parts = inst_id.split("-")
                if len(parts) < 2:
                    continue
                base, quote = parts[0], parts[1]
                bid_px = item.get("bidPx")
                ask_px = item.get("askPx")
                if not bid_px or not ask_px:
                    continue
                return {
                    "exchange": "OKX",
                    "base": base,
                    "quote": quote,
                    "bid": float(bid_px),
                    "ask": float(ask_px),
                    "exchange_timestamp": int(item.get("ts", time.time() * 1000)),
                    "ingest_timestamp": int(time.time() * 1000),
                }
            return None
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUOTE_SUFFIXES = ["USDT", "USDC", "BUSD", "BTC", "ETH", "BNB", "USD"]


def _split_symbol_binance(symbol: str):
    """Heuristically split a Binance symbol like 'BTCUSDT' into ('BTC', 'USDT')."""
    for q in _QUOTE_SUFFIXES:
        if symbol.endswith(q):
            return symbol[: -len(q)], q
    return symbol, "UNKNOWN"


def _split_symbol_bybit(symbol: str):
    return _split_symbol_binance(symbol)
