# -*- coding: utf-8 -*-
"""Genere les pages HTML (BTC et ETH) a partir du payload produit par les moteurs
update.py / update_eth.py. Aucune dependance JS.

render(payload, asset) ou `asset` est une des configs ci-dessous (BTC par defaut)."""
import math, datetime as dt

ACTION_STYLE = {
    "ACHETER":   ("#16a34a", "#f0fdf4", "🟢", "ACHETER / RENFORCER"),
    "VENDRE":    ("#dc2626", "#fef2f2", "🔴", "VENDRE / ALLÉGER"),
    "CONSERVER": ("#2563eb", "#eff6ff", "🔵", "CONSERVER (ne rien faire)"),
    "INIT":      ("#64748b", "#f8fafc", "⚪", "POSITION INITIALE"),
}

# --- Configs par actif -------------------------------------------------------
BTC = dict(
    name="Bitcoin", sym="BTC", slope="5,8",
    title="cool-crypto — signal BTC mensuel (G75)",
    h1="cool-crypto — signal Bitcoin mensuel",
    nav=[("₿ Bitcoin", "./", True), ("Ξ Ethereum", "eth/", False)],
    repo="https://github.com/robaromat/cool-crypto",
    intro=None,
    # bullets "comment lire" specifiques (BTC : machine a etats + bandes)
    rule_html=(
        "<li><b>Valorisation</b> = prix vs « juste valeur » d'une power-law "
        "(pente 5,8, recalibrée chaque 1ᵉʳ janvier). Si prix &gt; <b>2,5×</b> la juste valeur → "
        "« chère ». Si &lt; <b>0,6×</b> → « bon marché ».</li>"
        "<li><b>Tendance</b> = prix au-dessus de sa moyenne mobile 10 mois.</li>"
        "<li><b>Règle G75</b> : valorisation chère → <b>0 %</b> (cash) · sinon tendance haussière → "
        "<b>100 %</b> · sinon (baisse mais pas chère) → <b>75 %</b>.</li>"
        "<li>L'<b>action</b> compare la cible du mois à celle du mois précédent : on n'achète/vend que l'écart.</li>"
    ),
)
ETH = dict(
    name="Ethereum", sym="ETH", slope="2,3",
    title="cool-crypto — signal ETH mensuel (G75)",
    h1="cool-crypto — signal Ethereum mensuel",
    nav=[("₿ Bitcoin", "../", False), ("Ξ Ethereum", "./", True)],
    repo="https://github.com/robaromat/cool-crypto",
    intro=(
        "<div class=\"disc\" style=\"background:#eff6ff;border-color:#bfdbfe;margin:14px 0 0\">"
        "<b>ℹ️ À quoi sert ce signal sur l'ETH ?</b> Contrairement au Bitcoin (où la stratégie bat "
        "« tout conserver » sur le rendement <i>et</i> le risque), sur Ethereum c'est avant tout un "
        "<b>réducteur de risque</b> : rendement quasi identique à HODL sur l'ensemble, mais pire baisse "
        "ramenée de <b>−90 % à −64 %</b>. Depuis 2021 (marché ETH mature) elle bat HODL sur les deux "
        "tableaux. Son intérêt principal : rendre le trajet <b>tenable</b> sans vendre au pire moment."
        "</div>"
    ),
    # bullets "comment lire" specifiques (ETH : valorisation INSTANTANEE)
    rule_html=(
        "<li><b>Valorisation</b> = prix vs « juste valeur » d'une power-law <b>propre à l'ETH</b> "
        "(pente 2,3, recalibrée chaque 1ᵉʳ janvier). « chère » si prix &gt; <b>2,5×</b> la juste valeur.</li>"
        "<li><b>Tendance</b> = prix au-dessus de sa moyenne mobile 10 mois.</li>"
        "<li><b>Règle G75</b> : valorisation chère → <b>0 %</b> (cash) · sinon tendance haussière → "
        "<b>100 %</b> · sinon (baisse mais pas chère) → <b>75 %</b>.</li>"
        "<li><b>Différence clé avec le BTC</b> : la valorisation est <b>instantanée</b> (on sort "
        "<i>tant que</i> c'est cher, on rentre dès que ça se dissipe). La power-law d'ETH étant plus "
        "plate et moins fiable, le mécanisme « collant » du BTC resterait bloqué en cash des années.</li>"
        "<li>L'<b>action</b> compare la cible du mois à celle du mois précédent : on n'achète/vend que l'écart.</li>"
    ),
)


def _nav(asset):
    items = ""
    for label, href, active in asset["nav"]:
        cls = "navlink active" if active else "navlink"
        items += f'<a class="{cls}" href="{href}">{label}</a>'
    return f'<div class="nav">{items}</div>'


def _svg(history):
    W, H, PL, PR, PT, PB = 900, 300, 56, 70, 16, 28
    s = [r["strat"] for r in history]
    h = [r["hodl"] for r in history]
    n = len(history)
    vals = s + h
    lo, hi = math.log10(min(vals)), math.log10(max(vals))
    def X(i): return PL + (W - PL - PR) * i / (n - 1)
    def Y(v): return PT + (H - PT - PB) * (1 - (math.log10(v) - lo) / (hi - lo))
    def path(arr): return "M" + " L".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(arr))
    grid = ""
    for p in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
        yy = Y(10 ** p)
        if yy < PT - 2 or yy > H - PB + 2:
            continue
        lab = "x%s" % (10 ** p if 10 ** p < 1000 else "%dk" % (10 ** p // 1000))
        grid += '<line x1=%d y1=%.1f x2=%d y2=%.1f stroke="#eef2f7"/>' % (PL, yy, W - PR, yy)
        grid += '<text x=%d y=%.1f font-size=10 fill="#94a3b8" text-anchor=end>%s</text>' % (PL - 6, yy + 3, lab)
    xt = ""
    for i, r in enumerate(history):
        if r["date"].endswith("-01-01"):
            xt += '<line x1=%.1f y1=%d x2=%.1f y2=%d stroke="#f4f6fa"/>' % (X(i), PT, X(i), H - PB)
            xt += '<text x=%.1f y=%d font-size=9 fill="#b6c0cd" text-anchor=middle>%s</text>' % (X(i), H - PB + 14, r["date"][:4])
    return f'''<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">
{grid}{xt}
<path d="{path(h)}" fill=none stroke="#cbd5e1" stroke-width=1.5/>
<path d="{path(s)}" fill=none stroke="#16a34a" stroke-width=2.4/>
<text x={W-PR+6} y={Y(s[-1])+3} font-size=11 fill="#16a34a" font-weight=700>Stratégie ×{s[-1]:.0f}</text>
<text x={W-PR+6} y={Y(h[-1])+3} font-size=11 fill="#94a3b8">HODL ×{h[-1]:.0f}</text>
</svg>'''


def _rows_html(history):
    out = []
    for r in reversed(history):
        col, _, _, _ = ACTION_STYLE.get(r["action"], ACTION_STYLE["CONSERVER"])
        tcol = "#16a34a" if r["target"] == 1.0 else ("#f59e0b" if r["target"] == 0.75 else "#dc2626")
        vcol = "#dc2626" if r["valuation"] == "chère" else ("#16a34a" if r["valuation"] == "bon marché" else "#64748b")
        out.append(
            "<tr>"
            f"<td>{r['date']}</td>"
            f"<td class=num>{r['price']:,.0f}</td>"
            f"<td class=num>{r['fair_value']:,.0f}</td>"
            f"<td class=num>{r['ratio']:.2f}</td>"
            f"<td style='color:{'#16a34a' if r['trend']=='HAUSSE' else '#dc2626'}'>{r['trend']}</td>"
            f"<td style='color:{vcol}'>{r['valuation']}</td>"
            f"<td class=num style='color:{tcol};font-weight:700'>{r['target']*100:.0f}%</td>"
            f"<td style='color:{col};font-weight:600'>{r['action']}</td>"
            "</tr>"
        )
    return "\n".join(out).replace(",", " ")


def _explain(c, asset):
    """Explication dynamique de la position cible du mois, selon les 2 signaux."""
    sym = asset["sym"]
    tg = c["target"]
    up = (c["trend"] == "HAUSSE")
    chk = lambda ok: ('<span style="color:#16a34a">✔</span>' if ok
                      else '<span style="color:#dc2626">✗</span>')
    signals = (
        '<div class="sig">'
        f'<div>{chk(not (c["valuation"]=="chère"))} <b>Valorisation</b> : '
        f'{sym + " pas cher" if c["valuation"]!="chère" else sym + " cher (> 2,5× la juste valeur)"} '
        f'<span class="muted">(ratio {c["ratio"]:.2f})</span></div>'
        f'<div>{chk(up)} <b>Tendance</b> : '
        f'{"haussière (prix > moyenne mobile 10 mois)" if up else "baissière (prix < moyenne mobile 10 mois)"}</div>'
        '</div>'
    )
    if tg == 0.0:
        title = "Pourquoi 0 % (tout en cash) ?"
        body = (
            f"<p>La valorisation est <b>chère</b> : le prix dépasse <b>2,5×</b> la juste valeur power-law. "
            f"Dans cette zone, le risque de correction est jugé trop élevé : on <b>sort entièrement</b> du {sym}, "
            "<b>quelle que soit la tendance</b>.</p>"
            "<p class=muted>C'est ce garde-fou qui a permis d'éviter l'essentiel des krachs de 2018 et 2022.</p>"
        )
    elif tg == 1.0:
        title = f"Pourquoi 100 % {sym} ?"
        body = (
            f"<p>Les <b>deux feux sont au vert</b> : le {sym} n'est pas cher <b>et</b> la tendance est haussière. "
            "Aucune raison de se protéger — on est <b>pleinement investi</b>.</p>"
        )
    else:  # 75 %
        title = "Pourquoi 75 % et pas 100 % ?"
        body = (
            "<p>Les deux signaux se <b>contredisent</b>, on prend donc une position <b>intermédiaire</b> :</p>"
            "<ul>"
            "<li><b>Pas 100 %</b> : la <b>tendance est baissière</b> (le prix est repassé sous sa moyenne mobile "
            "10 mois). On réduit l'exposition par prudence, le temps que la tendance se retourne.</li>"
            f"<li><b>Pas 0 % (cash)</b> : le {sym} n'est <b>pas dans la zone chère</b> (loin du plafond de 2,5×). "
            "Tout vendre alors qu'il n'est pas cher ferait rater un éventuel rebond — on <b>garde 75 %</b>.</li>"
            "</ul>"
            "<p class=muted>Le « 75 % » est le <b>curseur de la stratégie</b> : c'est le niveau d'exposition choisi "
            f"quand le {sym} baisse sans être cher. Une version prudente mettrait 50 %, une version agressive 100 %. "
            "75 % est l'entre-deux : on protège une partie du capital tout en restant exposé au rebond.</p>"
        )
    return (
        '<div class="why">'
        f'<div class="whytitle">{title}</div>'
        f'{signals}{body}'
        '</div>'
    )


def render(payload, asset=BTC):
    c = payload["current"]
    st = payload["stats"]
    sym = asset["sym"]
    col, bg, emoji, label = ACTION_STYLE.get(c["action"], ACTION_STYLE["CONSERVER"])
    cur_date = dt.date.fromisoformat(c["date"])
    # prochaine revision = 1er du mois suivant la date courante
    nxt = (cur_date.replace(day=28) + dt.timedelta(days=7)).replace(day=1)
    target_pct = "%.0f%%" % (c["target"] * 100)
    intro = asset.get("intro") or ""
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{asset["title"]}</title>
<style>
 *{{box-sizing:border-box}}
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1e293b;line-height:1.5;
   max-width:960px;margin:0 auto;padding:22px 18px;background:#fafbfc}}
 h1{{font-size:23px;margin:0 0 2px}} .sub{{color:#64748b;font-size:13px;margin-bottom:18px}}
 h2{{font-size:17px;margin:30px 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:6px}}
 .nav{{display:flex;gap:8px;margin:0 0 16px}}
 .navlink{{text-decoration:none;font-weight:600;font-size:14px;color:#475569;background:#fff;
   border:1px solid #e2e8f0;border-radius:9px;padding:7px 14px}}
 .navlink.active{{background:#1e293b;color:#fff;border-color:#1e293b}}
 .reco{{background:{bg};border:1px solid {col}33;border-left:5px solid {col};border-radius:12px;padding:20px 22px;margin:14px 0}}
 .reco .lab{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}}
 .reco .act{{font-size:30px;font-weight:800;color:{col};margin:2px 0 4px}}
 .reco .tgt{{font-size:15px}} .reco .tgt b{{font-size:20px;color:{col}}}
 .facts{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}
 .fact{{flex:1;min-width:120px;background:#fff;border:1px solid #e7ebf0;border-radius:9px;padding:11px 13px}}
 .fact .l{{font-size:11px;color:#64748b}} .fact .v{{font-size:18px;font-weight:700;margin-top:1px}}
 .kpi{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}}
 .kpi .c{{flex:1;min-width:150px;background:#fff;border:1px solid #e7ebf0;border-radius:9px;padding:12px 14px}}
 .kpi .l{{font-size:11px;color:#64748b}} .kpi .v{{font-size:20px;font-weight:700}}
 .g{{color:#16a34a}} .r{{color:#dc2626}} .b{{color:#2563eb}}
 .chartwrap{{background:#fff;border:1px solid #e7ebf0;border-radius:10px;padding:12px;overflow-x:auto}}
 table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#fff}}
 th,td{{border-bottom:1px solid #eef2f7;padding:6px 9px;text-align:left;white-space:nowrap}}
 th{{position:sticky;top:0;background:#f1f5f9;font-weight:600;z-index:1}}
 td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .tablewrap{{max-height:460px;overflow:auto;border:1px solid #e7ebf0;border-radius:10px}}
 .note{{font-size:12px;color:#64748b}}
 .why{{background:#fff;border:1px solid #e7ebf0;border-left:5px solid #f59e0b;border-radius:11px;padding:16px 20px;margin:14px 0}}
 .why .whytitle{{font-size:17px;font-weight:800;margin-bottom:10px}}
 .why .sig{{background:#f8fafc;border-radius:8px;padding:10px 12px;margin-bottom:10px;font-size:13.5px;line-height:1.9}}
 .why p{{margin:8px 0}} .why ul{{margin:8px 0;padding-left:20px}} .why li{{margin:5px 0}}
 .why .muted,.muted{{color:#64748b;font-size:12.5px}}
 .disc{{background:#fffbeb;border:1px solid #fde68a;border-radius:9px;padding:12px 15px;font-size:12.5px;margin-top:18px}}
 code{{background:#f1f5f9;padding:1px 5px;border-radius:4px}}
 a{{color:#2563eb}}
</style></head><body>

{_nav(asset)}
<h1>{asset["h1"]}</h1>
<div class="sub">Stratégie « G75 » · un seul arbitrage par mois (le 1ᵉʳ à 06:00 UTC) · mis à jour le {payload["generated_utc"]}</div>

<div class="reco">
  <div class="lab">Décision du {c['date']} {emoji}</div>
  <div class="act">{label}</div>
  <div class="tgt">Position cible : <b>{target_pct} {sym}</b> &nbsp;·&nbsp; le reste en cash (USDC). Prochaine révision : <b>{nxt.isoformat()}</b>.</div>
</div>
{intro}
<div class="facts">
  <div class="fact"><div class="l">Prix {sym} ({c['date']})</div><div class="v">{c['price']:,.0f} $</div></div>
  <div class="fact"><div class="l">Juste valeur (power-law)</div><div class="v">{c['fair_value']:,.0f} $</div></div>
  <div class="fact"><div class="l">Ratio prix / juste valeur</div><div class="v">{c['ratio']:.2f}</div></div>
  <div class="fact"><div class="l">Tendance (MM 10 mois)</div><div class="v" style="color:{'#16a34a' if c['trend']=='HAUSSE' else '#dc2626'}">{c['trend']}</div></div>
  <div class="fact"><div class="l">Valorisation</div><div class="v">{c['valuation']}</div></div>
</div>

{_explain(c, asset)}

<h2>Performance depuis 2015 (backtest auditable)</h2>
<div class="kpi">
  <div class="c"><div class="l">Rendement / an — Stratégie</div><div class="v g">{st['strat_cagr']*100:.1f} %</div></div>
  <div class="c"><div class="l">Rendement / an — HODL</div><div class="v">{st['hodl_cagr']*100:.1f} %</div></div>
  <div class="c"><div class="l">Pire baisse — Stratégie</div><div class="v g">{st['strat_mdd']*100:.0f} %</div></div>
  <div class="c"><div class="l">Pire baisse — HODL</div><div class="v r">{st['hodl_mdd']*100:.0f} %</div></div>
</div>
<div class="chartwrap">{_svg(payload["history"])}</div>
<div class="note">Capital indexé, échelle logarithmique. Stratégie en vert, conserver-tout (HODL) en gris.</div>

<h2>Historique mensuel complet ({st['months']+1} mois — le plus récent en haut)</h2>
<div class="tablewrap"><table>
<thead><tr><th>Date</th><th class=num>Prix $</th><th class=num>Juste valeur $</th><th class=num>Ratio</th>
<th>Tendance</th><th>Valorisation</th><th class=num>Cible {sym}</th><th>Action</th></tr></thead>
<tbody>
{_rows_html(payload["history"])}
</tbody></table></div>
<div class="note">Données brutes : <a href="history.csv">history.csv</a> · <a href="data.json">data.json</a></div>

<h2>Comment lire le signal</h2>
<ul class="note" style="font-size:13px;line-height:1.7">
{asset["rule_html"]}
</ul>

<div class="disc">
<b>⚠️ Avertissement.</b> Ceci est une <b>étude quantitative personnelle</b>, pas un conseil en investissement. Les performances passées (backtest sur données historiques) ne préjugent pas des performances futures. La « juste valeur » power-law est une extrapolation statistique, pas une loi : elle peut cesser d'être valide. Le {asset["name"]} est un actif très volatil ; n'investissez que ce que vous pouvez vous permettre de perdre. Faites vos propres recherches.
</div>
<div class="note" style="margin-top:14px">Code &amp; méthodologie : <a href="{asset["repo"]}">{asset["repo"].replace("https://","")}</a></div>
</body></html>'''
