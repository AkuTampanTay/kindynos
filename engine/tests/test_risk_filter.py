import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models import Edge, ArbitrageOpportunity, SignalStatus
from risk import RiskEngine
from risk_filter import RiskFilter, PROFIT_BUFFER


def make_opportunity(profit_ratio: float, legs=None) -> ArbitrageOpportunity:
    if legs is None:
        legs = [Edge(source="A", target="B", exchange="TestEx", rate=profit_ratio)]
    return ArbitrageOpportunity(
        cycle=["A", "B", "A"],
        profit_ratio=profit_ratio,
        legs=legs,
        status=SignalStatus.CONFIRMED,
    )


class TestRiskFilterNoData:
    def test_passes_through_when_no_var_data(self):
        """With empty RiskEngine, all signals should pass (warm-up window)."""
        rf = RiskFilter(RiskEngine())
        opp = make_opportunity(1.005)
        assert rf.is_viable(opp) is True

    def test_large_profit_passes_when_no_data(self):
        rf = RiskFilter(RiskEngine())
        assert rf.is_viable(make_opportunity(1.10)) is True

    def test_tiny_profit_passes_when_no_data(self):
        rf = RiskFilter(RiskEngine())
        assert rf.is_viable(make_opportunity(1.0001)) is True


class TestRiskFilterWithData:
    def _engine_with_var(self, pair: str, prices: list) -> RiskEngine:
        r = RiskEngine()
        for p in prices:
            r.update(pair, p)
        return r

    def _stable_prices(self, n: int = 50, base: float = 100.0, noise: float = 0.001):
        import random
        random.seed(42)
        prices = [base]
        for _ in range(n - 1):
            prices.append(prices[-1] * (1 + random.uniform(-noise, noise)))
        return prices

    def _volatile_prices(self, n: int = 50, base: float = 100.0, noise: float = 0.05):
        import random
        random.seed(99)
        prices = [base]
        for _ in range(n - 1):
            prices.append(prices[-1] * (1 + random.uniform(-noise, noise)))
        return prices

    def test_high_profit_exceeds_stable_var(self):
        pair = "TestEx:A/B"
        risk = self._engine_with_var(pair, self._stable_prices())
        rf = RiskFilter(risk)
        leg = Edge(source="A", target="B", exchange="TestEx", rate=1.5)
        # 10% profit easily beats low-volatility VaR
        opp = make_opportunity(1.10, legs=[leg])
        assert rf.is_viable(opp) is True

    def test_tiny_profit_rejected_when_var_exceeds_it(self):
        pair = "TestEx:A/B"
        risk = self._engine_with_var(pair, self._volatile_prices())
        rf = RiskFilter(risk)
        leg = Edge(source="A", target="B", exchange="TestEx", rate=1.0001)
        # 0.01% profit against high-volatility VaR should be rejected
        opp = make_opportunity(1.0001, legs=[leg])
        assert rf.is_viable(opp) is False

    def test_profit_exactly_at_threshold_is_rejected(self):
        pair = "TestEx:A/B"
        risk = self._engine_with_var(pair, self._stable_prices(noise=0.005))
        rf = RiskFilter(risk)
        var = risk.var(pair)
        assert var is not None
        # profit = |VaR| exactly, which is below |VaR| + PROFIT_BUFFER
        marginal_profit = abs(var)
        leg = Edge(source="A", target="B", exchange="TestEx", rate=1.0)
        opp = make_opportunity(1.0 + marginal_profit, legs=[leg])
        assert rf.is_viable(opp) is False

    def test_worst_leg_var_drives_decision(self):
        """Filter uses the worst (most negative) VaR across all legs."""
        r = RiskEngine()
        stable = self._stable_prices(noise=0.001)
        volatile = self._volatile_prices(noise=0.05)
        for p in stable:
            r.update("Ex:A/B", p)
        for p in volatile:
            r.update("Ex:B/C", p)

        rf = RiskFilter(r)
        leg_ab = Edge(source="A", target="B", exchange="Ex", rate=1.5)
        leg_bc = Edge(source="B", target="C", exchange="Ex", rate=1.5)
        # Even though A/B is stable, the B/C leg is very volatile → filter applies
        opp = make_opportunity(1.0001, legs=[leg_ab, leg_bc])
        assert rf.is_viable(opp) is False
