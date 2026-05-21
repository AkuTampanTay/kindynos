import math
import statistics
from collections import deque
from typing import Deque, Dict, Optional


class PriceWindow:
    """Sliding window of mid-prices for a single asset pair."""

    def __init__(self, window_size: int = 100):
        self._prices: Deque[float] = deque(maxlen=window_size)

    def push(self, price: float) -> None:
        self._prices.append(price)

    @property
    def size(self) -> int:
        return len(self._prices)

    def log_returns(self) -> list:
        prices = list(self._prices)
        if len(prices) < 2:
            return []
        return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]

    def volatility(self) -> Optional[float]:
        """Annualised daily volatility (std-dev of log returns, scaled by sqrt(365))."""
        returns = self.log_returns()
        if len(returns) < 2:
            return None
        return statistics.stdev(returns) * math.sqrt(365)

    def historical_var(self, confidence: float = 0.95) -> Optional[float]:
        """
        Historical Value at Risk at the given confidence level.
        Returns the worst-case daily log return at (1-confidence) quantile.
        A negative number means expected loss, e.g. -0.05 = -5% in 1 day.
        """
        returns = self.log_returns()
        if len(returns) < 10:
            return None
        sorted_r = sorted(returns)
        idx = int((1.0 - confidence) * len(sorted_r))
        return sorted_r[max(idx, 0)]


class RiskEngine:
    """
    Aggregates PriceWindows for all tracked asset pairs and exposes
    per-pair risk metrics consumed by the dashboard layer.
    """

    def __init__(self, window_size: int = 100):
        self._windows: Dict[str, PriceWindow] = {}
        self._window_size = window_size

    def update(self, pair: str, price: float) -> None:
        if pair not in self._windows:
            self._windows[pair] = PriceWindow(self._window_size)
        self._windows[pair].push(price)

    def volatility(self, pair: str) -> Optional[float]:
        w = self._windows.get(pair)
        return w.volatility() if w else None

    def var(self, pair: str, confidence: float = 0.95) -> Optional[float]:
        w = self._windows.get(pair)
        return w.historical_var(confidence) if w else None

    def snapshot(self) -> Dict[str, Dict]:
        """Return a dict of all tracked pairs with current risk metrics."""
        result = {}
        for pair, window in self._windows.items():
            result[pair] = {
                "samples": window.size,
                "volatility": window.volatility(),
                "var_95": window.historical_var(0.95),
            }
        return result
