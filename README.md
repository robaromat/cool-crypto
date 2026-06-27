# cool-crypto — signaux crypto mensuels (stratégie « G75 »)

> **Site en ligne : https://robaromat.github.io/cool-crypto/** (Bitcoin)
> **· Ethereum : `/eth/` · LQQ (Nasdaq-100 ×2) : `/lqq/`**
>
> Indique chaque mois s'il faut **acheter, vendre ou conserver** du Bitcoin, de l'Ethereum et du
> LQQ, et affiche tout l'historique mensuel pour pouvoir auditer la méthode facilement.

⚠️ **Étude quantitative personnelle, pas un conseil en investissement.** Voir l'avertissement plus bas.

---

## La stratégie en une phrase

Un seul arbitrage par mois (le 1ᵉʳ à 06:00 UTC) entre **Bitcoin** et **cash**, piloté par deux signaux :

| Signal | Question | Source |
|---|---|---|
| **Tendance** | Le prix est-il au-dessus de sa **moyenne mobile 10 mois** ? | prix mensuels |
| **Valorisation** | Le prix est-il cher/bon marché vs sa **« juste valeur » power-law** ? | régression log-log, pente 5,8 |

### Règle d'allocation « G75 »

| Valorisation | Tendance | Position cible |
|---|---|---|
| chère (> 2,5× juste valeur) | — | **0 %** (cash) |
| pas chère | haussière | **100 % BTC** |
| pas chère | baissière | **75 % BTC** |

Le « 75 % » est le curseur qui distingue G75 : quand le BTC baisse **sans être cher**, on reste
exposé à 75 % (au lieu de 50 % pour une version prudente, ou 100 % pour une version agressive).

### Résultats du backtest (2015 → aujourd'hui, walk-forward, sans information du futur)

| | Stratégie G75 | HODL (tout garder) |
|---|---|---|
| Rendement / an | ~93 % | ~61 % |
| Pire baisse | ~−40 % | ~−74 % |

> Les performances passées ne préjugent pas des performances futures. Le chiffre de rendement
> n'est **pas** reconductible : il repose en partie sur deux krachs (2018, 2022) évités, et sur
> la persistance de la power-law — qui n'est pas garantie.

---

## Ethereum — même logique, une différence clé

Le signal ETH (https://robaromat.github.io/cool-crypto/eth/) applique **la même règle G75**, avec
une power-law **propre à l'ETH** (pente **2,3**, lancement réseau 30/07/2015) et une adaptation
démontrée par backtest :

- **Valorisation instantanée** (et non « collante » comme sur BTC). La power-law d'ETH est plus
  plate (pente 2,3, R²≈0,86) et moins fiable que celle du BTC (pente 5,8). Avec le mécanisme à
  hystérésis du BTC, le portefeuille resterait bloqué en cash des années (ex : 2021→2025, en ratant
  la reprise 2023-24). On sort donc **tant que** c'est cher (> 2,5× juste valeur) et on re-rentre
  dès que la surévaluation se dissipe.

### Résultats du backtest ETH (2017 → aujourd'hui, walk-forward)

| | G75 ETH | HODL |
|---|---|---|
| Multiple | ~×266 | ~×280 |
| Rendement / an | ~82 % | ~83 % |
| Pire baisse | **~−64 %** | ~−90 % |

> Sur l'ETH, G75 est avant tout un **réducteur de risque** : rendement quasi identique à HODL sur
> l'ensemble (tout le petit écart vient de la mania de 2017), mais pire baisse fortement réduite.
> **Depuis 2021** (marché ETH mature), elle bat HODL sur les deux tableaux. Comparaison des moteurs
> testés : la power-law bat MVRV on-chain, force relative ETH/BTC et Metcalfe. À considérer comme un
> outil pour rendre la détention **tenable**, pas comme un faiseur de surperformance.

---

## LQQ — Nasdaq-100 ×2 (produit à effet de levier)

Le signal LQQ (https://robaromat.github.io/cool-crypto/lqq/) applique le **même esprit**
(une décision par mois) à l'**ETF Amundi LQQ**, un ×2 à réinitialisation quotidienne sur le
Nasdaq-100. Sur un produit à levier, **ne pas timer = ruine** : le buy & hold a perdu **−98 %**
au krach 2000-2002.

**Méthode retenue : ensemble de momentum absolu multi-fenêtres** (la méthode momentum de
« Floran », robustifiée). Pour chaque fenêtre w ∈ {6, 8, 10, 12} mois, le Nasdaq-100 a-t-il
progressé sur les w derniers mois ? L'exposition cible au LQQ = **fraction des fenêtres
positives** (0 / 25 / 50 / 75 / 100 %), le reste en cash.

> Pourquoi un ensemble et pas une seule fenêtre ? Le backtest montre que le choix d'une fenêtre
> unique est **fragile** (8 mois → ×209 mais ses voisins 4 et 11 mois → ×28 et ×108, drawdowns
> −87 %/−74 %). Voter sur 4 horizons donne ~le même rendement sans dépendre d'un « nombre magique ».

### Résultats du backtest LQQ (1999 → aujourd'hui, signal mensuel)

| | Ensemble momentum | Buy & Hold LQQ ×2 |
|---|---|---|
| Multiple | ~×201 | ~×32 |
| Rendement / an | ~21 % | ~14 % |
| Pire baisse | **~−59 %** | ~−98 % |

> LQQ **simulé** à partir du Nasdaq-100 (^NDX, ×2 quotidien, hors dividendes → conservateur) ;
> simulation **validée** sur le vrai LQQ.PA depuis 2008 (drawdowns COVID/2022 reproduits à ~1 pt
> près, corrélation mensuelle 0,94). Le vrai ETF capte en plus ~+1,2 %/an de dividendes ×2.
> Approches comparées : momentum absolu (fenêtre unique et ensemble), SMA Faber, vol-targeting,
> paliers de levier — l'ensemble de momentum offre le meilleur rendement à exposition ≤ 100 %.

---

## Architecture

```
engine/
  update.py        # BTC : télécharge les prix, calcule le signal, régénère docs/
  update_eth.py    # ETH : idem (power-law pente 2,3, valorisation instantanée) -> docs/eth/
  update_lqq.py    # LQQ : ensemble momentum {6,8,10,12} sur Nasdaq-100 (Yahoo ^NDX) -> docs/lqq/
  build_site.py    # gabarit HTML commun (render BTC/ETH + render_lqq + navigation)
docs/              # publié par GitHub Pages
  index.html       # tableau de bord BTC (recommandation + courbe + historique)
  history.csv / data.json
  eth/             # tableau de bord ETH (index.html, history.csv, data.json)
  lqq/             # tableau de bord LQQ (index.html, history.csv, data.json)
.github/workflows/
  monthly-update.yml  # exécute update.py + update_eth.py + update_lqq.py le 1er du mois et committe
```

**Aucune dépendance** : uniquement la bibliothèque standard de Python (≥ 3.10).

### Sources de données
- **CoinMetrics** (communautaire, hébergé sur GitHub) : historique profond depuis 2010.
- **Kraken** puis **Coinbase** : prix récents / du 1ᵉʳ du mois (joignables depuis un runner cloud).

### Lancer en local
```bash
python engine/update.py
# -> régénère docs/ et affiche le signal courant dans le terminal
```

---

## Méthodologie détaillée
Voir [`docs/methodologie.md`](docs/methodologie.md) (formules exactes, calibration, limites).

## Avertissement
Ce dépôt est une **étude quantitative personnelle**. Ce n'est **pas** un conseil en
investissement, ni une sollicitation. Le Bitcoin est très volatil ; n'investissez que ce que
vous pouvez vous permettre de perdre, et faites vos propres recherches.

Crédit méthodologique : inspiré de l'approche [ChillBTC](https://investchill.github.io/chillbtc/)
(time-series momentum + power-law), avec un filtre de tendance par moyenne mobile et un curseur
d'exposition « 75 % » distinct.
