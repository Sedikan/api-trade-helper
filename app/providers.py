import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Candle, MarketSnapshot, NewsItem


class ProviderError(RuntimeError):
    """Raised when an external data provider cannot return valid data."""


def _get_json(url: str) -> dict | list:
    try:
        request = Request(url, headers={"User-Agent": "investment-advisor/0.1"})
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ProviderError("Nie udało się połączyć z dostawcą danych.") from error
    if isinstance(payload, dict) and (
        payload.get("status") == "error" or payload.get("error")
    ):
        provider_error = payload.get("error")
        message = (
            provider_error.get("message")
            if isinstance(provider_error, dict)
            else payload.get("message")
        ) or "Dostawca zwrócił błąd."
        raise ProviderError(str(message))
    return payload


class DemoMarketDataProvider:
    """Deterministic demo data; never represents live market prices."""

    def get_snapshot(self, instrument: str) -> MarketSnapshot:
        start = datetime.now(timezone.utc) - timedelta(days=40)
        candles: list[Candle] = []
        price = 100.0
        for index in range(40):
            close = price + ((index % 7) - 3) * 0.35 + 0.18
            high = max(price, close) + 0.5
            low = min(price, close) - 0.5
            candles.append(
                Candle(
                    timestamp=start + timedelta(days=index),
                    open=price,
                    high=high,
                    low=low,
                    close=close,
                    volume=1000,
                )
            )
            price = close
        return MarketSnapshot(
            instrument=instrument.upper(),
            candles=candles,
            source="demo-provider",
            fetched_at=datetime.now(timezone.utc),
            delay_minutes=None,
        )


class TwelveDataProvider:
    """Live daily candles from Twelve Data."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_snapshot(self, instrument: str) -> MarketSnapshot:
        query = urlencode(
            {
                "symbol": instrument.upper(),
                "interval": "1day",
                "outputsize": 100,
                "apikey": self.api_key,
            }
        )
        payload = _get_json(f"https://api.twelvedata.com/time_series?{query}")
        if not isinstance(payload, dict) or not isinstance(payload.get("values"), list):
            raise ProviderError("Twelve Data nie zwrócił świec dla tego instrumentu.")
        candles: list[Candle] = []
        try:
            for row in reversed(payload["values"]):
                candles.append(
                    Candle(
                        timestamp=datetime.fromisoformat(
                            str(row["datetime"]).replace("Z", "+00:00")
                        ).replace(tzinfo=timezone.utc),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]) if row.get("volume") else None,
                    )
                )
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderError("Twelve Data zwrócił nieprawidłowy format świec.") from error
        if len(candles) < 2:
            raise ProviderError("Twelve Data zwrócił zbyt mało danych.")
        return MarketSnapshot(
            instrument=instrument.upper(),
            candles=candles,
            source="Twelve Data",
            fetched_at=datetime.now(timezone.utc),
            delay_minutes=None,
        )


class MarketstackProvider:
    """Live end-of-day candles from Marketstack."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_snapshot(self, instrument: str) -> MarketSnapshot:
        query = urlencode(
            {
                "access_key": self.api_key,
                "symbols": instrument.upper(),
                "limit": 100,
            }
        )
        payload = _get_json(f"https://api.marketstack.com/v1/eod?{query}")
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ProviderError("Marketstack nie zwrócił danych EOD dla tego instrumentu.")
        candles: list[Candle] = []
        for row in reversed(payload["data"]):
            try:
                raw_timestamp = str(row.get("date") or row.get("datetime"))
                if raw_timestamp.endswith("+0000"):
                    raw_timestamp = f"{raw_timestamp[:-5]}+00:00"
                timestamp = datetime.fromisoformat(
                    raw_timestamp.replace("Z", "+00:00")
                )
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                candles.append(
                    Candle(
                        timestamp=timestamp.astimezone(timezone.utc),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]) if row.get("volume") else None,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        if len(candles) < 2:
            raise ProviderError(
                "Marketstack nie zwrócił co najmniej dwóch kompletnych świec. "
                "Sprawdź symbol oraz plan API."
            )
        return MarketSnapshot(
            instrument=instrument.upper(),
            candles=candles,
            source="Marketstack",
            fetched_at=datetime.now(timezone.utc),
            delay_minutes=None,
        )


class FinnhubNewsProvider:
    """Recent company news from Finnhub."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_news(self, instrument: str, days: int = 3) -> list[NewsItem]:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=days)
        query = urlencode(
            {
                "symbol": instrument.upper(),
                "from": start.isoformat(),
                "to": end.isoformat(),
                "token": self.api_key,
            }
        )
        payload = _get_json(f"https://finnhub.io/api/v1/company-news?{query}")
        if not isinstance(payload, list):
            raise ProviderError("Finnhub nie zwrócił listy wiadomości.")
        news: list[NewsItem] = []
        for row in payload[:10]:
            try:
                news.append(
                    NewsItem(
                        headline=str(row["headline"]),
                        source=str(row.get("source") or "Finnhub"),
                        url=str(row["url"]) if row.get("url") else None,
                        published_at=datetime.fromtimestamp(
                            int(row["datetime"]), tz=timezone.utc
                        ),
                        summary=str(row["summary"]) if row.get("summary") else None,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return news


def create_market_provider() -> (
    DemoMarketDataProvider | TwelveDataProvider | MarketstackProvider
):
    marketstack_key = os.getenv("MARKETSTACK_API_KEY", "").strip()
    if marketstack_key:
        return MarketstackProvider(marketstack_key)
    twelve_data_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    return TwelveDataProvider(twelve_data_key) if twelve_data_key else DemoMarketDataProvider()


def create_news_provider() -> FinnhubNewsProvider | None:
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    return FinnhubNewsProvider(api_key) if api_key else None
