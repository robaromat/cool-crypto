#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cool-crypto — moteur de la strategie G75 adaptee a Ethereum.

Une seule decision par mois (le 1er a 06:00 UTC), MEME LOGIQUE que le BTC, mais
avec une difference cle : la valorisation est INSTANTANEE (pas de machine a etats
collante). Raison demontree par backtest : la power-law d'ETH est plus plate
(pente ~2.3, R2~0.86) et moins fiable que celle du BTC (pente 5.8) ; le ratio
d'ETH ne retraverse quasi jamais la bande "tres bon marche" (<0.6x), si bien que
le mecanisme d'hysteresis du moteur BTC resterait bloque en cash pendant des
annees (ex : 2021->2025) et raterait les reprises. On sort donc du marche
UNIQUEMENT TANT QUE c'est cher, et on re-entre des que la surevaluation se dissipe.

  - Tendance     : prix ETH au-dessus de sa moyenne mobile 10 mois ?
  - Valorisation : prix vs "juste valeur" power-law (pente 2.3, intercept recalibre
                   chaque 1er janvier). "chere" si > 2.5x, "bon marche" si < 0.6x.
  - Allocation G75 (instantanee) :
        prix CHER (> 2.5x juste valeur, ce mois-ci)      -> 0 %  (cash)
        sinon, tendance HAUSSIERE                         -> 100 % ETH
        sinon (baisse mais pas chere)                     -> 75 % ETH

Backtest 2017->2026 (signal mensuel) : x266, ~82 %/an, pire baisse -64 %
vs HODL x280, ~83 %/an, pire baisse -90 %. Robuste hors-echantillon (2021+ :
-58 % de pire baisse vs -77 % pour HODL).

Reconstruit tout l'historique mensuel walk-forward (sans information du futur),
puis genere : docs/eth/history.csv, docs/eth/data.json, docs/eth/index.html
"""
import json, math, csv, io, os, sys, datetime as dt
from collections import OrderedDict
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs", "eth")
GENESIS = dt.date(2015, 7, 30)  # lancement du reseau Ethereum (Frontier)
SLOPE = 2.3                     # pente de la power-law ETH (constante structurelle)
BAND_LOW, BAND_HIGH = 0.6, 2.5  # bandes "bon marche" / "cher"
SMA_WIN = 10                    # moyenne mobile 10 mois
BUFFER = 0.75                   # G75 : exposition quand baisse mais pas cher
START = dt.date(2017, 1, 1)     # debut de l'historique publie (apres rodage SMA + power-law)

UA = {"User-Agent": "cool-crypto/1.0 (+https://github.com/robaromat/cool-crypto)"}


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_coinmetrics():
    """Historique profond (depuis 2015), heberge sur GitHub — fiable depuis un runner."""
    raw = _get("https://raw.githubusercontent.com/coinmetrics/data/master/csv/eth.csv", 120)
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    out = {}
    for x in rd:
        p = x.get("PriceUSD", "")
        if p:
            v = float(p)
            if v > 0:
                out[x["time"][:10]] = v
    return out


def fetch_recent():
    """Jours recents / prix live. Kraken puis Coinbase en secours (US/cloud friendly)."""
    out = {}
    # Kraken : ~720 jours
    try:
        j = json.loads(_get("https://api.kraken.com/0/public/OHLC?pair=ETHUSD&interval=1440", 30))
        key = list(j["result"].keys())[0]
        for row in j["result"][key]:
            d = dt.datetime.fromtimestamp(int(row[0]), dt.timezone.utc).strftime("%Y-%m-%d")
            out[d] = float(row[4])  # close
    except Exception as e:
        print("WARN Kraken:", e, file=sys.stderr)
    # Coinbase : ~300 jours (secours / complement)
    try:
        j = json.loads(_get("https://api.exchange.coinbase.com/products/ETH-USD/candles?granularity=86400", 30))
        for c in j:  # [time, low, high, open, close, vol]
            d = dt.datetime.fromtimestamp(int(c[0]), dt.timezone.utc).strftime("%Y-%m-%d")
            out.setdefault(d, float(c[4]))
    except Exception as e:
        print("WARN Coinbase:", e, file=sys.stderr)
    if not out:
        raise RuntimeError("Aucune source de prix recente joignable (Kraken + Coinbase KO).")
    return out


def load_daily():
    cm = fetch_coinmetrics()
    rec = fetch_recent()
    cm_last = max(cm)            # derniere date CoinMetrics
    daily = dict(cm)
    for d, p in rec.items():     # les sources recentes priment apres la fin de CoinMetrics
        if d > cm_last:
            daily[d] = p
    items = sorted(daily.items())
    dates = [dt.date.fromisoformat(d) for d, _ in items]
    prices = [p for _, p in items]
    return dates, prices


def days_since(d):
    return max((d - GENESIS).days, 1)


def calibrate_A(dates, prices, upto):
    """Intercept de la power-law : moyenne(lnP - SLOPE*ln(jours)) sur tout l'historique anterieur."""
    res = [math.log(p) - SLOPE * math.log(days_since(d))
           for d, p in zip(dates, prices) if d < upto and p > 0]
    return sum(res) / len(res) if res else None


def build():
    dates, prices = load_daily()
    print("Donnees:", dates[0], "->", dates[-1], "(%d jours)" % len(dates))

    # prix de debut de mois (1er jour disponible du mois)
    monthly = OrderedDict()
    for d, p in zip(dates, prices):
        k = (d.year, d.month)
        if k not in monthly:
            monthly[k] = (d, p)
    mkeys = list(monthly.keys())
    mdate = [monthly[k][0] for k in mkeys]
    mprice = [monthly[k][1] for k in mkeys]

    Acache = {}
    def A_for(d):
        if d.year not in Acache:
            Acache[d.year] = calibrate_A(dates, prices, dt.date(d.year, 1, 1))
        return Acache[d.year]
    def fair_value(d):
        a = A_for(d)
        return math.exp(a + SLOPE * math.log(days_since(d))) if a is not None else None

    rows = []
    strat, hodl = 1.0, 1.0
    prev_w = None
    for i, k in enumerate(mkeys):
        d, p = mdate[i], mprice[i]
        if d < START:
            continue
        fv = fair_value(d)
        ratio = p / fv if fv else None
        # valorisation INSTANTANEE (pas de machine a etats)
        if ratio is not None and ratio > BAND_HIGH:
            valuation = "chère"
        elif ratio is not None and ratio < BAND_LOW:
            valuation = "bon marché"
        else:
            valuation = "normale"
        # tendance : moyenne mobile 10 mois
        if i - SMA_WIN >= 0:
            sma = sum(mprice[i - SMA_WIN + 1:i + 1]) / SMA_WIN
            trend_up = p > sma
        else:
            sma = None
            trend_up = False
        # allocation G75 (instantanee)
        if valuation == "chère":
            w = 0.0
        elif trend_up:
            w = 1.0
        else:
            w = BUFFER
        # action vs mois precedent
        if prev_w is None:
            action = "INIT"
        elif w > prev_w + 1e-9:
            action = "ACHETER"
        elif w < prev_w - 1e-9:
            action = "VENDRE"
        else:
            action = "CONSERVER"
        prev_w = w
        # rendement du mois (pour la courbe d'equite)
        if i + 1 < len(mkeys):
            r = mprice[i + 1] / p - 1
            strat *= (1 + w * r)
            hodl *= (1 + r)
        rows.append(dict(
            date=str(d), price=round(p, 2), fair_value=round(fv, 2) if fv else None,
            ratio=round(ratio, 3) if ratio else None,
            sma10=round(sma, 2) if sma else None, trend="HAUSSE" if trend_up else "BAISSE",
            valuation=valuation,
            target=w, action=action, strat=round(strat, 4), hodl=round(hodl, 4),
        ))
    return rows


def equity_stats(rows):
    sc = [r["strat"] for r in rows]
    hc = [r["hodl"] for r in rows]
    n = len(rows) - 1
    def cagr(m): return m ** (12 / n) - 1 if n > 0 else 0
    def mdd(c):
        pk = -1; m = 0
        for v in c:
            pk = max(pk, v); m = min(m, v / pk - 1)
        return m
    return dict(
        months=n,
        strat_mult=sc[-1], hodl_mult=hc[-1],
        strat_cagr=cagr(sc[-1]), hodl_cagr=cagr(hc[-1]),
        strat_mdd=mdd(sc), hodl_mdd=mdd(hc),
    )


if __name__ == "__main__":
    rows = build()
    stats = equity_stats(rows)
    os.makedirs(DOCS, exist_ok=True)

    # CSV auditable
    with open(os.path.join(DOCS, "history.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "prix_usd", "juste_valeur_usd", "ratio", "moyenne_mobile_10m",
                    "tendance", "valorisation", "cible_eth", "action", "mult_strategie", "mult_hodl"])
        for r in rows:
            w.writerow([r["date"], r["price"], r["fair_value"], r["ratio"], r["sma10"],
                        r["trend"], r["valuation"], r["target"], r["action"], r["strat"], r["hodl"]])

    payload = dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        params=dict(slope=SLOPE, band_low=BAND_LOW, band_high=BAND_HIGH, sma_window=SMA_WIN, buffer=BUFFER),
        stats=stats, current=rows[-1], history=rows,
    )
    with open(os.path.join(DOCS, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # page HTML (generee par build_site.py, config ETH)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_site import render, ETH
        html = render(payload, ETH)
        with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("eth/index.html ecrit.")
    except Exception as e:
        print("WARN rendu HTML:", e, file=sys.stderr)

    c = rows[-1]
    print("\n=== SIGNAL COURANT ETH (%s) ===" % c["date"])
    print("Prix %.0f | juste valeur %.0f | ratio %.2f" % (c["price"], c["fair_value"], c["ratio"]))
    print("Tendance %s | valorisation %s" % (c["trend"], c["valuation"]))
    print("CIBLE: %.0f%% ETH -> %s" % (c["target"] * 100, c["action"]))
    print("Strat x%.0f (%.1f%%/an, DD %.1f%%) | HODL x%.0f (%.1f%%/an, DD %.1f%%)" % (
        stats["strat_mult"], stats["strat_cagr"] * 100, stats["strat_mdd"] * 100,
        stats["hodl_mult"], stats["hodl_cagr"] * 100, stats["hodl_mdd"] * 100))
