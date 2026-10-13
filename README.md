# API Trade Helper

Bezpieczny, lokalny MVP osobistego asystenta analitycznego dla portfela
użytkownika XTB. Aplikacja nie składa zleceń i nie udaje dostępu do
aktualnych kwotowań, dopóki nie zostanie skonfigurowany dostawca danych.

## Zakres MVP

- deterministyczne wskaźniki: SMA, EMA, RSI, MACD, ATR i Bollinger Bands;
- obliczenia ryzyka pozycji na podstawie kapitału, limitu ryzyka i stop-loss;
- import pozycji z CSV;
- API FastAPI do analizy symbolu i portfela;
- walidacja bezpiecznej odpowiedzi rekomendacyjnej;
- prosty interfejs HTML bez automatycznego handlu;
- adapter danych demo oraz integracja Twelve Data/Finnhub po konfiguracji kluczy.

## Uruchomienie

```powershell
cd .\investment-advisor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Otwórz `http://127.0.0.1:8000`.

## CSV portfela

Nagłówki: `instrument,side,quantity,entry_price,stop_loss,take_profit,currency`.
`side` przyjmuje `long` albo `short`. Import nie wykonuje żadnej transakcji.

## Dane live i newsy

Aplikacja obsługuje:

- **Marketstack** — dzienne świece EOD dla analizy technicznej (ma pierwszeństwo);
- **Twelve Data** — alternatywne dzienne świece dla analizy technicznej;
- **Finnhub** — wiadomości spółek z ostatnich trzech dni.

Załóż konto u dostawców i ustaw klucze tylko w zmiennych środowiskowych:

```powershell
$env:MARKETSTACK_API_KEY = "twój-klucz-marketstack"
$env:TWELVE_DATA_API_KEY = "twój-klucz-twelve-data"
$env:FINNHUB_API_KEY = "twój-klucz-finnhub"
uvicorn app.main:app --reload
```

Nie wpisuj kluczy do kodu, README ani plików commitowanych do repozytorium.
Jeżeli ustawisz `MARKETSTACK_API_KEY`, aplikacja użyje Marketstack. W
przeciwnym razie spróbuje Twelve Data, a bez obu kluczy działa w trybie demo.
Bez
`FINNHUB_API_KEY` analiza rynku działa, ale sekcja newsów będzie oznaczona jako
nie skonfigurowana. Błędy zewnętrznego API są pokazywane jawnie — aplikacja
nie zastępuje niedostępnych danych zgadywaniem.

### Bezpieczne uruchomienie z kluczem Marketstack

Możesz też użyć skryptu, który pyta o klucz lokalnie i nie zapisuje go w
projekcie:

```powershell
cd .\investment-advisor
.\run-live.ps1
```

Jeśli PowerShell zablokuje skrypt, uruchom jednorazowo:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run-live.ps1
```

Wklej nowy klucz dopiero w monit skryptu. Obecny klucz podany w rozmowie
traktuj jako ujawniony i unieważnij go w panelu Marketstack.

## Zasady danych

Warstwa analityczna nie zgaduje brakujących wartości. Przed użyciem
produkcyjnym trzeba dodać limity i cache, monitoring świeżości, mapowanie
symboli na instrumenty XTB oraz porównać kwotowania dostawcy z kwotowaniami
brokera. Darmowe plany mogą mieć limity, opóźnienia lub ograniczony zakres
instrumentów.

To narzędzie analityczne i edukacyjne, nie licencjonowane doradztwo
inwestycyjne ani gwarancja wyniku. CFD i dźwignia mogą powodować straty
przekraczające wpłatę.
