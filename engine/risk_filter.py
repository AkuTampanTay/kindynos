from typing import Optional

from models import ArbitrageOpportunity
from risk import RiskEngine

# Minimum profit above the worst-leg VaR magnitude before a signal is accepted.
# E.g. if the worst leg has VaR95 = -0.8%, the cycle needs profit > 0.8% + 0.1%.
PROFIT_BUFFER = 0.001  # 0.1%


class RiskFilter:
    """
    Guards Bellman-Ford signals against adverse market conditions.

    Strategy: for each leg in the cycle, look up the per-pair historical VaR
    at the configured confidence level. The opportunity is accepted only if its
    net profit ratio minus 1 exceeds the absolute worst-leg VaR plus a fixed
    buffer. Legs with no VaR data (insufficient history) are treated as safe
    so the system is productive during the warm-up window.
    """

    def __init__(self, risk_engine: RiskEngine, var_confidence: float = 0.95):
        self._risk = risk_engine
        self._confidence = var_confidence

    def is_viable(self, opp: ArbitrageOpportunity) -> bool:
        profit = opp.profit_ratio - 1.0
        worst_var = self._worst_leg_var(opp)
        if worst_var is None:
            return True  # no VaR data yet — pass through unfiltered
        # VaR is a negative number (expected loss); abs() gives the magnitude
        return profit > abs(worst_var) + PROFIT_BUFFER

    def _worst_leg_var(self, opp: ArbitrageOpportunity) -> Optional[float]:
        """Return the most negative VaR across all legs, or None if none available."""
        worst: Optional[float] = None
        for edge in opp.legs:
            pair = f"{edge.exchange}:{edge.source}/{edge.target}"
            var = self._risk.var(pair, self._confidence)
            if var is not None:
                worst = var if worst is None else min(worst, var)
        return worst
