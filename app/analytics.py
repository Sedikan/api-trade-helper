from math import sqrt
from statistics import mean, pstdev

from .models import Candle, PositionRisk, PortfolioPosition, TechnicalIndicators, UserProfile


def _closes(candles: list[Candle]) -> list[float]:
    return [c.close for c in candles]


def sma(values: list[float], period: int) -> float | None:
    return mean(values[-period:]) if len(values) >= period else None


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    result = mean(values[:period])
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(change, 0) for change in changes[:period]]
    losses = [max(-change, 0) for change in changes[:period]]
    average_gain = mean(gains)
    average_loss = mean(losses)
    for change in changes[period:]:
        average_gain = (average_gain * (period - 1) + max(change, 0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0)) / period
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + average_gain / average_loss))


def atr(candles: list[Candle], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    true_ranges: list[float] = []
    for previous, current in zip(candles, candles[1:]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return mean(true_ranges[-period:])


def indicators(candles: list[Candle]) -> TechnicalIndicators:
    closes = _closes(candles)
    fast = ema(closes, 12)
    slow = ema(closes, 26)
    macd_value = fast - slow if fast is not None and slow is not None else None
    macd_series: list[float] = []
    for index in range(26, len(closes) + 1):
        fast_value = ema(closes[:index], 12)
        slow_value = ema(closes[:index], 26)
        if fast_value is not None and slow_value is not None:
            macd_series.append(fast_value - slow_value)
    signal = ema(macd_series, 9) if macd_series else None
    window = closes[-20:] if len(closes) >= 20 else []
    deviation = pstdev(window) if window else None
    middle = mean(window) if window else None
    return TechnicalIndicators(
        close=closes[-1],
        sma_20=sma(closes, 20),
        ema_20=ema(closes, 20),
        rsi_14=rsi(closes),
        macd=macd_value,
        macd_signal=signal,
        atr_14=atr(candles),
        bollinger_upper=middle + 2 * deviation if middle is not None and deviation is not None else None,
        bollinger_lower=middle - 2 * deviation if middle is not None and deviation is not None else None,
    )


def calculate_position_risk(
    position: PortfolioPosition, profile: UserProfile, current_price: float
) -> PositionRisk:
    position_value = current_price * position.quantity
    if position.stop_loss is None:
        return PositionRisk(
            instrument=position.instrument,
            risk_amount=None,
            risk_percent=None,
            position_value=position_value,
            warning="Brak stop-loss — ryzyko pozycji nie może być policzone.",
        )
    distance = abs(position.entry_price - position.stop_loss)
    risk_amount = distance * position.quantity
    risk_percent = risk_amount / profile.capital * 100
    warning = (
        "Ryzyko przekracza limit profilu."
        if risk_percent > profile.risk_per_trade_percent
        else None
    )
    return PositionRisk(
        instrument=position.instrument,
        risk_amount=risk_amount,
        risk_percent=risk_percent,
        position_value=position_value,
        warning=warning,
    )
