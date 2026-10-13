from datetime import datetime, timedelta, timezone

from app.analytics import indicators
from app.models import Candle


def candles(count: int = 40) -> list[Candle]:
    return [
        Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
        )
        for index in range(count)
    ]


def test_indicators_are_deterministic_and_available_with_sufficient_history():
    result = indicators(candles())
    assert result.sma_20 == 129.5
    assert result.ema_20 is not None
    assert result.rsi_14 == 100
    assert result.atr_14 == 2


def test_candle_rejects_invalid_range():
    try:
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=10,
            high=9,
            low=8,
            close=10,
        )
    except ValueError:
        return
    raise AssertionError("Invalid candle should be rejected")
