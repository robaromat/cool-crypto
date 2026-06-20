# cool-crypto — signal Bitcoin mensuel (stratégie « G75 »)

> **Site en ligne : https://robaromat.github.io/cool-crypto/**
>
> Indique chaque mois s'il faut **acheter, vendre ou conserver** du Bitcoin, et affiche
> tout l'historique mensuel pour pouvoir auditer la méthode facilement.

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

## Architecture

```
engine/
  update.py        # télécharge les prix, calcule le signal, régénère history.csv / data.json / index.html
  build_site.py    # gabarit de la page HTML
docs/              # publié par GitHub Pages
  index.html       # tableau de bord (recommandation + courbe + historique)
  history.csv      # historique mensuel, brut et auditable
  data.json        # mêmes données, format structuré
.github/workflows/
  monthly-update.yml  # exécute update.py le 1er de chaque mois et committe les changements
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
