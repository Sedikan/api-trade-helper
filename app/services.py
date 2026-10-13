from datetime import datetime, timezone

from .analytics import indicators
from .models import MarketSnapshot, Recommendation, UserProfile


def build_recommendation(
    snapshot: MarketSnapshot, profile: UserProfile
) -> tuple[Recommendation, object]:
    technical = indicators(snapshot.candles)
    age_minutes = (
        datetime.now(timezone.utc) - snapshot.fetched_at.astimezone(timezone.utc)
    ).total_seconds() / 60
    stale = age_minutes > profile.max_data_age_minutes
    incomplete = technical.rsi_14 is None or technical.atr_14 is None
    quality = "incomplete" if incomplete else "stale" if stale else "fresh"
    facts = [f"Źródło: {snapshot.source}", f"Cena zamknięcia: {technical.close:.4f}"]
    if technical.rsi_14 is not None:
        facts.append(f"RSI(14): {technical.rsi_14:.2f}")
    if technical.atr_14 is not None:
        facts.append(f"ATR(14): {technical.atr_14:.4f}")
    if quality != "fresh":
        return (
            Recommendation(
                instrument=snapshot.instrument,
                action="no_action",
                thesis="Brak wystarczająco świeżych i kompletnych danych do analizy.",
                facts=facts,
                invalidation=None,
                alternative_scenario="Poczekaj na aktualne i kompletne dane.",
                confidence="low",
                data_quality=quality,
            ),
            technical,
        )
    action = "observe"
    thesis = "Dane nie pokazują wystarczająco wyraźnej przewagi."
    if technical.rsi_14 is not None and technical.rsi_14 < 30:
        action = "bullish_scenario"
        thesis = "RSI wskazuje wyprzedanie, ale nie potwierdza samodzielnie odwrócenia trendu."
    elif technical.rsi_14 is not None and technical.rsi_14 > 70:
        action = "bearish_scenario"
        thesis = "RSI wskazuje wykupienie, ale nie potwierdza samodzielnie spadków."
    return (
        Recommendation(
            instrument=snapshot.instrument,
            action=action,
            thesis=thesis,
            facts=facts,
            invalidation="Zmiana warunków technicznych lub nieaktualność danych.",
            alternative_scenario="Jeżeli warunek nie zostanie potwierdzony, rozważ brak działania.",
            confidence="medium" if action != "observe" else "low",
            data_quality=quality,
        ),
        technical,
    )
