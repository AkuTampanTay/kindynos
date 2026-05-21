import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from risk import PriceWindow, RiskEngine


class TestPriceWindow:
    def test_empty_window_returns_no_log_returns(self):
        w = PriceWindow()
        assert w.log_returns() == []

    def test_single_price_returns_no_log_returns(self):
        w = PriceWindow()
        w.push(100.0)
        assert w.log_returns() == []

    def test_two_prices_returns_one_log_return(self):
        w = PriceWindow()
        w.push(100.0)
        w.push(110.0)
        returns = w.log_returns()
        assert len(returns) == 1
        assert abs(returns[0] - math.log(110.0 / 100.0)) < 1e-12

    def test_log_returns_length_is_prices_minus_one(self):
        w = PriceWindow()
        for p in [100, 101, 102, 103, 104]:
            w.push(float(p))
        assert len(w.log_returns()) == 4

    def test_window_size_caps_stored_prices(self):
        w = PriceWindow(window_size=5)
        for i in range(10):
            w.push(float(i + 1))
        assert w.size == 5

    def test_volatility_none_with_fewer_than_two_returns(self):
        w = PriceWindow()
        w.push(100.0)
        assert w.volatility() is None

    def test_volatility_none_with_exactly_one_return(self):
        w = PriceWindow()
        w.push(100.0)
        w.push(101.0)
        # one log-return → stdev needs ≥ 2 observations
        assert w.volatility() is None

    def test_volatility_returns_float_with_enough_samples(self):
        w = PriceWindow()
        for p in [100, 101, 99, 102, 98, 103]:
            w.push(float(p))
        vol = w.volatility()
        assert vol is not None
        assert vol > 0

    def test_var_none_with_fewer_than_ten_returns(self):
        w = PriceWindow()
        for p in range(1, 10):   # 9 prices → 8 returns
            w.push(float(p))
        assert w.historical_var() is None

    def test_var_returns_negative_number(self):
        w = PriceWindow()
        import random
        random.seed(42)
        base = 100.0
        for _ in range(50):
            base *= 1 + random.uniform(-0.02, 0.02)
            w.push(base)
        var = w.historical_var(confidence=0.95)
        assert var is not None
        assert var < 0  # VaR is always a loss (negative)

    def test_higher_confidence_gives_more_negative_var(self):
        w = PriceWindow()
        import random
        random.seed(7)
        base = 100.0
        for _ in range(100):
            base *= 1 + random.uniform(-0.03, 0.03)
            w.push(base)
        var_90 = w.historical_var(confidence=0.90)
        var_99 = w.historical_var(confidence=0.99)
        assert var_99 <= var_90  # 99% VaR is worse (more negative)


class TestRiskEngine:
    def test_empty_engine_snapshot_is_empty(self):
        r = RiskEngine()
        assert r.snapshot() == {}

    def test_unknown_pair_volatility_is_none(self):
        r = RiskEngine()
        assert r.volatility("X/Y") is None

    def test_unknown_pair_var_is_none(self):
        r = RiskEngine()
        assert r.var("X/Y") is None

    def test_update_creates_window_entry(self):
        r = RiskEngine()
        r.update("BTC/USDT", 40000.0)
        snap = r.snapshot()
        assert "BTC/USDT" in snap

    def test_snapshot_samples_count_correct(self):
        r = RiskEngine()
        for price in [100.0, 101.0, 102.0]:
            r.update("ETH/USDT", price)
        assert r.snapshot()["ETH/USDT"]["samples"] == 3

    def test_volatility_available_after_sufficient_samples(self):
        import random
        random.seed(1)
        r = RiskEngine()
        price = 100.0
        for _ in range(30):
            price *= 1 + random.uniform(-0.01, 0.01)
            r.update("BTC/USDT", price)
        assert r.volatility("BTC/USDT") is not None

    def test_var_available_after_sufficient_samples(self):
        import random
        random.seed(2)
        r = RiskEngine()
        price = 100.0
        for _ in range(30):
            price *= 1 + random.uniform(-0.01, 0.01)
            r.update("ETH/USDT", price)
        assert r.var("ETH/USDT") is not None
