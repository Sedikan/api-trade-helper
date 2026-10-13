import csv
import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .analytics import calculate_position_risk
from .models import MarketSnapshot, PortfolioPosition, Recommendation, UserProfile
from .providers import (
    MarketstackProvider,
    ProviderError,
    TwelveDataProvider,
    create_market_provider,
    create_news_provider,
)
from .services import build_recommendation

app = FastAPI(title="API Trade Helper", version="0.1.0")
provider = create_market_provider()
news_provider = create_news_provider()


class AnalyzeRequest(BaseModel):
    instrument: str
    profile: UserProfile


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Investment Advisor | Panel analityczny</title>
<style>
:root{--canvas:#f5f5f5;--paper:#fff;--surface:#fafafa;--ink:#0a0a0a;--ink-soft:#171717;--muted:#737373;--line:#e5e5e5;--ember:#e7000b}
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--ink);font:14px/1.5 Inter,Segoe UI,Arial,sans-serif}
.shell{max-width:1280px;margin:0 auto;padding:48px 24px 64px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:48px}
.eyebrow{color:var(--muted);font-size:12px;font-weight:500;letter-spacing:.05em;text-transform:uppercase}
h1{color:var(--ink);font-size:42px;letter-spacing:-.05em;line-height:1.1;margin:7px 0 6px}h2{color:var(--ink);font-size:24px;letter-spacing:-.025em;line-height:1.33;margin:0 0 5px}h3{font-size:14px;margin:0 0 8px}
.subtitle,.muted{color:var(--muted)}.subtitle{font-size:16px;margin:0}.badge{background:var(--ink-soft);color:#fafafa;border:0;border-radius:18px;font-size:12px;font-weight:500;padding:6px 10px;white-space:nowrap}
.notice{background:var(--surface);border:1px solid var(--line);border-radius:24px;color:var(--muted);display:flex;gap:12px;padding:16px 20px;margin-bottom:20px}.notice strong{display:block;color:var(--ink)}
.card{background:var(--paper);border:1px solid var(--line);border-radius:24px;box-shadow:0 0 0 1px #1717170d,0 1px 3px #0000001a,0 1px 2px -1px #0000001a;padding:20px}
.controls{display:grid;grid-template-columns:minmax(180px,1fr) minmax(160px,220px) auto;align-items:end;gap:14px}
label{color:var(--muted);display:flex;flex-direction:column;font-size:13px;font-weight:500;gap:6px}input{background:var(--canvas);border:1px solid transparent;border-radius:18px;color:var(--ink);font:inherit;padding:10px 12px}
input:focus{background:transparent;border-color:var(--line);outline:0}button{background:var(--ink);border:0;border-radius:18px;color:#fafafa;cursor:pointer;font:500 14px inherit;min-height:40px;padding:0 16px}
button:hover{background:var(--ink-soft)}button:disabled{cursor:wait;opacity:.6}.helper{font-size:13px;color:var(--muted);margin:12px 0 0}.hidden{display:none!important}
.status{align-items:center;display:flex;gap:8px;margin-top:22px}.dot{background:var(--ink);border-radius:50%;height:7px;width:7px}.grid{display:grid;gap:20px;grid-template-columns:1.15fr .85fr;margin-top:20px}.full{grid-column:1/-1}
.section-title{align-items:center;display:flex;justify-content:space-between;margin-bottom:16px}.action{border-radius:8px;display:inline-block;font-size:12px;font-weight:700;padding:6px 10px}
.action.observe,.action.bullish_scenario,.action.bearish_scenario,.action.no_action,.action.hold{background:var(--canvas);color:var(--ink-soft)}
.thesis{font-size:18px;line-height:1.45;margin:0 0 20px}.facts{display:grid;gap:10px;margin:0;padding:0;list-style:none}.facts li{border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:16px;padding-bottom:9px}
.facts li:last-child{border:0;padding-bottom:0}.facts span:first-child{color:var(--muted)}.facts span:last-child{font-weight:600;text-align:right}.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.metric{background:var(--canvas);border-radius:10px;padding:12px}.metric-label{color:var(--muted);display:block;font-size:12px}.metric-value{color:var(--ink);display:block;font-size:22px;letter-spacing:-.025em;font-weight:600;margin-top:2px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:20px}.callout{background:var(--surface);border-left:2px solid var(--ink-soft);padding:12px 14px}.news-list{display:grid;gap:12px;list-style:none;margin:0;padding:0}.news-list li{border-bottom:1px solid var(--line);padding-bottom:12px}.news-list li:last-child{border:0;padding-bottom:0}.news-list a{color:var(--ink);font-weight:600;text-decoration:none}.news-list a:hover{text-decoration:underline}.news-meta{color:var(--muted);font-size:12px;margin-top:3px}
footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}.error{color:var(--ember);margin-top:14px}
@media(max-width:760px){.shell{padding:22px 14px 40px}header{display:block}.badge{display:inline-block;margin-top:16px}.controls,.grid,.split{grid-template-columns:1fr}.full{grid-column:auto}.metric-grid{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main class="shell">
<header><div><div class="eyebrow">Osobisty asystent analityczny</div><h1>Investment Advisor</h1><p class="subtitle">Spokojna, oparta na danych analiza rynku i ryzyka portfela.</p></div><div id="mode-badge" class="badge">BEZ HANDLU</div></header>
<div class="notice"><div>●</div><div><strong>Ważne: dane demonstracyjne</strong>Ten prototyp nie korzysta jeszcze z notowań live i nie składa zleceń. Wyniki służą wyłącznie do testowania panelu.</div></div>
<section class="card"><div class="section-title"><div><h2>Nowa analiza</h2><div class="muted">Wpisz instrument i podstawowe parametry profilu.</div></div></div>
<form id="analysis-form" class="controls"><label for="instrument">Instrument<input id="instrument" value="NVDA" maxlength="32" required></label><label for="capital">Kapitał (USD)<input id="capital" type="number" min="1" step="100" value="10000" required></label><button id="submit-button" type="submit">Uruchom analizę</button></form>
<p class="helper">Analiza oblicza wskaźniki techniczne i opisuje, czy w danych widać wyraźną przewagę.</p><div id="status" class="status hidden"><span class="dot"></span><span id="status-text"></span></div><div id="error" class="error hidden"></div></section>
<section id="results" class="hidden"><div class="grid"><article class="card"><div class="section-title"><div><h2 id="result-instrument">Analiza instrumentu</h2><div class="muted" id="result-source"></div></div><span id="result-action" class="action"></span></div><p id="thesis" class="thesis"></p><h3>Dane potwierdzające</h3><ul id="facts" class="facts"></ul></article>
<article class="card"><div class="section-title"><div><h2>Wskaźniki</h2><div class="muted" id="metrics-subtitle">Obliczone na podstawie świec</div></div></div><div id="metrics" class="metric-grid"></div></article>
<article class="card full"><div class="section-title"><div><h2>Jak czytać ten wynik?</h2><div class="muted">Analiza nie jest automatycznym sygnałem transakcyjnym.</div></div></div><div class="split"><div><h3>Co unieważnia tezę</h3><div id="invalidation" class="callout"></div></div><div><h3>Scenariusz alternatywny</h3><div id="alternative" class="callout"></div></div></div></article>
<article class="card full"><div class="section-title"><div><h2>Ocena jakości danych</h2><div class="muted">Świeżość i kompletność wejścia analitycznego</div></div><span id="data-quality" class="action"></span></div><div id="disclaimer" class="muted"></div></article></div></section>
<section id="news-section" class="card hidden"><div class="section-title"><div><h2>Najnowsze wiadomości</h2><div class="muted">Ostatnie informacje znalezione dla instrumentu</div></div><span id="news-status" class="action no_action"></span></div><ul id="news-list" class="news-list"></ul></section>
<footer>To analiza pomocnicza, nie gwarancja wyniku. Decyzję podejmujesz Ty.</footer></main>
<script>
const form=document.getElementById('analysis-form'),results=document.getElementById('results'),status=document.getElementById('status'),statusText=document.getElementById('status-text'),error=document.getElementById('error'),button=document.getElementById('submit-button');
const labels={observe:'Obserwuj',bullish_scenario:'Scenariusz wzrostowy',bearish_scenario:'Scenariusz spadkowy',hold:'Utrzymaj',no_action:'Brak działania'},qualityLabels={fresh:'Dane świeże',stale:'Dane nieaktualne',incomplete:'Dane niekompletne'};
const value=(item,digits=2)=>item===null||item===undefined?'Brak danych':Number(item).toFixed(digits);
const addMetric=(container,label,item)=>{const metric=document.createElement('div');metric.className='metric';metric.innerHTML=`<span class="metric-label">${label}</span><span class="metric-value">${value(item)}</span>`;container.appendChild(metric)};
form.addEventListener('submit',async event=>{event.preventDefault();error.classList.add('hidden');results.classList.add('hidden');button.disabled=true;status.classList.remove('hidden');statusText.textContent='Obliczam wskaźniki…';
try{const instrument=document.getElementById('instrument').value.trim().toUpperCase(),capital=Number(document.getElementById('capital').value);if(!instrument||!Number.isFinite(capital)||capital<=0)throw new Error('Podaj poprawny instrument i kapitał.');
const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instrument,profile:{capital,currency:'USD'}})}),body=await response.json();if(!response.ok)throw new Error(body.detail||'Nie udało się wykonać analizy.');
const rec=body.recommendation,tech=body.technical,data=body.data;document.getElementById('result-instrument').textContent=rec.instrument||'Instrument';document.getElementById('result-source').textContent=`Źródło: ${data.source} · dane pobrane: ${new Date(data.fetched_at).toLocaleString('pl-PL')}`;document.getElementById('mode-badge').textContent=data.source==='demo-provider'?'TRYB DEMO · BEZ HANDLU':'DANE LIVE · BEZ HANDLU';document.getElementById('metrics-subtitle').textContent=`Źródło: ${data.source}`;
const action=document.getElementById('result-action');action.textContent=labels[rec.action]||rec.action;action.className=`action ${rec.action}`;document.getElementById('thesis').textContent=rec.thesis||'Brak tezy.';
const facts=document.getElementById('facts');facts.replaceChildren();rec.facts.forEach(fact=>{const li=document.createElement('li');li.textContent=fact;facts.appendChild(li)});const metrics=document.getElementById('metrics');metrics.replaceChildren();
addMetric(metrics,'Cena zamknięcia',tech.close);addMetric(metrics,'SMA (20)',tech.sma_20);addMetric(metrics,'EMA (20)',tech.ema_20);addMetric(metrics,'RSI (14)',tech.rsi_14);addMetric(metrics,'MACD',tech.macd);addMetric(metrics,'ATR (14)',tech.atr_14);
document.getElementById('invalidation').textContent=rec.invalidation||'Brak danych.';document.getElementById('alternative').textContent=rec.alternative_scenario||'Brak danych.';const quality=document.getElementById('data-quality');quality.textContent=qualityLabels[rec.data_quality]||rec.data_quality;quality.className=`action ${rec.data_quality==='fresh'?'bullish_scenario':'no_action'}`;document.getElementById('disclaimer').textContent=rec.disclaimer;statusText.textContent=`Analiza zakończona · pewność: ${rec.confidence}`;results.classList.remove('hidden');
const newsSection=document.getElementById('news-section'),newsList=document.getElementById('news-list'),newsStatus=document.getElementById('news-status');newsList.replaceChildren();newsStatus.textContent=body.news_status==='live'?'Finnhub':'Nie skonfigurowano';if(body.news&&body.news.length){body.news.forEach(item=>{const li=document.createElement('li'),link=document.createElement('a'),meta=document.createElement('div');link.textContent=item.headline;link.href=item.url||'#';link.target='_blank';link.rel='noopener noreferrer';meta.className='news-meta';meta.textContent=`${item.source} · ${new Date(item.published_at).toLocaleString('pl-PL')}`;li.append(link,meta);newsList.appendChild(li)});newsSection.classList.remove('hidden')}else{const li=document.createElement('li');li.className='muted';li.textContent=body.news_status==='live'?'Brak wiadomości dla ostatnich trzech dni.':'Dodaj FINNHUB_API_KEY, aby pobierać wiadomości.';newsList.appendChild(li);newsSection.classList.remove('hidden')}
}catch(requestError){error.textContent=requestError.message;error.classList.remove('hidden');status.classList.add('hidden')}finally{button.disabled=false}});
</script></body></html>"""


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "data_mode": (
            "marketstack"
            if isinstance(provider, MarketstackProvider)
            else "twelve_data"
            if isinstance(provider, TwelveDataProvider)
            else "demo"
        ),
        "news_mode": "live" if news_provider else "not_configured",
    }


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    instrument = request.instrument.strip()
    try:
        snapshot = provider.get_snapshot(instrument)
        news = news_provider.get_news(instrument) if news_provider else []
    except ProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    recommendation, technical = build_recommendation(snapshot, request.profile)
    return {
        "recommendation": recommendation.model_dump(mode="json"),
        "technical": technical.model_dump(mode="json"),
        "data": snapshot.model_dump(mode="json"),
        "news": [item.model_dump(mode="json") for item in news],
        "news_status": (
            "live" if news_provider else "not_configured"
        ),
    }


@app.post("/api/analyze/snapshot")
def analyze_snapshot(snapshot: MarketSnapshot, profile: UserProfile) -> dict:
    recommendation, technical = build_recommendation(snapshot, profile)
    return {"recommendation": recommendation, "technical": technical}


@app.post("/api/portfolio/import", response_model=list[PortfolioPosition])
async def import_portfolio(file: UploadFile = File(...)) -> list[PortfolioPosition]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Oczekiwany jest plik CSV.")
    content = await file.read()
    try:
        rows = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        positions = [PortfolioPosition.model_validate(row) for row in rows]
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowy CSV: {error}") from error
    if not positions:
        raise HTTPException(status_code=400, detail="CSV nie zawiera pozycji.")
    return positions


@app.post("/api/portfolio/risk")
def portfolio_risk(
    position: PortfolioPosition, profile: UserProfile, current_price: float
) -> dict:
    if current_price <= 0:
        raise HTTPException(status_code=422, detail="current_price musi być dodatnie.")
    return calculate_position_risk(position, profile, current_price).model_dump()
