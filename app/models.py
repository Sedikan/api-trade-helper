from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Side = Literal["long", "short"]
Action = Literal[
    "observe",
    "bullish_scenario",
    "bearish_scenario",
    "hold",
    "no_action",
]


class Candle(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "Candle":
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise ValueError("Candle high/low does not contain open/close")
        return self


class MarketSnapshot(BaseModel):
    instrument: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=2)
    source: str = Field(min_length=1)
    fetched_at: datetime
    delay_minutes: float | None = Field(default=None, ge=0)


class NewsItem(BaseModel):
    headline: str
    source: str
    url: str | None = None
    published_at: datetime
    summary: str | None = None


class PortfolioPosition(BaseModel):
    instrument: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class UserProfile(BaseModel):
    capital: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    risk_per_trade_percent: float = Field(default=1, gt=0, le=5)
    max_data_age_minutes: int = Field(default=60, gt=0)
    leverage_enabled: bool = False


class TechnicalIndicators(BaseModel):
    close: float
    sma_20: float | None
    ema_20: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    atr_14: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None


class PositionRisk(BaseModel):
    instrument: str
    risk_amount: float | None
    risk_percent: float | None
    position_value: float
    warning: str | None = None


class Recommendation(BaseModel):
    instrument: str | None
    action: Action
    thesis: str | None
    facts: list[str]
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = None
    invalidation: str | None
    alternative_scenario: str | None
    confidence: Literal["low", "medium", "high"]
    data_quality: Literal["fresh", "stale", "incomplete"]
    disclaimer: str = (
        "To analiza pomocnicza, nie gwarancja wyniku. Decyzję podejmujesz Ty."
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
