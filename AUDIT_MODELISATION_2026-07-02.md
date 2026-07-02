# Audit de modélisation — cool-crypto — 2026-07-02

> **Périmètre.** Ce repo est un **générateur de signaux publié en site statique** (GitHub Pages).
> Il n'exécute **aucun ordre** : pas de broker, pas d'exchange, pas de clé API, pas de switch
> PAPER/LIVE (l'exécution est manuelle, hors repo). L'audit porte donc sur la seule chose qui
> compte ici : la **qualité de la modélisation** (signaux, backtests, données) qui pilote des
> décisions réelles. Aucun credential committé (scan du 02/07/2026 : négatif).
>
> **Rappel.** Les performances de backtest ne préjugent pas des performances futures. Tout
> chiffre de ce document provient d'un run réel exécuté le 02/07/2026 (sauf mention d'une date
> de run antérieure), avec sa période de données indiquée.
>
> **Millésimes de données utilisés** : CoinMetrics BTC (2010-07→2026-06) et ETH
> (2015-08→2026-06) ; `engine/ndx_cache.csv` (1985-10→2026-07-01) ; historiques publiés
> `docs/*/history.csv` (jusqu'au 2026-07-01) ; LQQ.PA réel via Yahoo (2008-01→2026-06, run du
> 27/06/2026). Les réimplémentations d'audit ont été **validées contre les courbes publiées**
> (BTC : écart 0,0 % sur 2015-01→2026-04, divergence résiduelle expliquée par le millésime —
> le moteur live complète CoinMetrics par Kraken/Coinbase pour les derniers jours).

---

## 1. Baseline par actif (LQQ / BTC / ETH)

### 1.1 BTC — « G75 » power-law + tendance, à hystérésis

| Élément | Détail | Référence |
|---|---|---|
| Signal valorisation | ratio prix / juste-valeur power-law `exp(A + 5.8·ln(jours depuis genesis))` ; intercept `A` recalibré chaque 1er janvier sur les données **antérieures** uniquement | `engine/update.py:24`, `:96-100`, `:122-123` |
| Machine à états (hystérésis) | ratio > 2,5 → état CASH ; ratio < 0,6 → état BUY ; **entre les deux, l'état précédent persiste** (échauffé depuis 2013) | `engine/update.py:126`, `:132-138` |
| Signal tendance | prix > SMA 10 mois (prix du 1er jour de chaque mois) | `engine/update.py:26`, `:144-149` |
| Allocation | état CASH → 0 % ; sinon tendance haussière → 100 % ; sinon → 75 % | `engine/update.py:151-156` |
| Données | CoinMetrics (2010→) + Kraken/Coinbase pour les jours récents ; prix mensuel = 1er jour disponible du mois | `engine/update.py:39-89`, `:108-115` |
| Backtest | boucle mensuelle walk-forward intégrée à `build()` ; rendement composé `strat *= (1 + w·r)` | `engine/update.py:169-171` |
| Optimisation | **aucune dans le repo** — paramètres (5,8 ; 0,6/2,5 ; SMA10 ; 75 %) issus de sessions de recherche non versionnées (audit ChillBTC, mai-juin 2026) | — |
| Risk mgmt | implicite (cible d'exposition + plafond valorisation) ; pas de stop, pas de circuit breaker | — |
| Perf publiée (01/07/2026, 138 mois) | strat ×1588 (89,8 %/an, MaxDD −44 %) vs HODL ×188 (MaxDD −74 %) | `docs/data.json` |

### 1.2 ETH — G75 **instantané** (sans hystérésis)

| Élément | Détail | Référence |
|---|---|---|
| Signal valorisation | même power-law, pente **2,3**, intercept walk-forward annuel ; état **instantané** : cher si ratio > 2,5 *ce mois-ci* (pas d'état persistant) | `engine/update_eth.py:37`, `:109-114`, `:149-155` |
| Signal tendance / allocation | identiques au BTC (SMA10 ; 0/75/100 %) | `engine/update_eth.py:156-168` |
| Justification de la différence | avec l'hystérésis BTC, l'ETH reste bloqué en cash 2021→2025 (ratio ne repasse quasi jamais < 0,6) et rate la reprise 2023-24 — démontré par timeline (run du 20/06/2026) | docstring `engine/update_eth.py:1-27` |
| Perf publiée (01/07/2026, 114 mois) | strat ×204 (75,1 %/an, MaxDD −64 %) vs HODL ×195 (MaxDD −90 %) | `docs/eth/data.json` |
| Rôle assumé | **réducteur de risque** (rendement ≈ HODL, drawdown −64 % vs −90 %), pas un générateur d'alpha — documenté sur la page | `engine/build_site.py` (bloc intro ETH) |

### 1.3 LQQ — ensemble de momentum absolu multi-fenêtres

| Élément | Détail | Référence |
|---|---|---|
| Signal | pour chaque fenêtre w ∈ {6, 8, 10, 12} mois : Nasdaq-100 en clôture fin de mois > il y a w mois ? Exposition = fraction des fenêtres positives → 0/25/50/75/100 % | `engine/update_lqq.py:36`, `:175-187` |
| Timing | décision à la clôture de fin de mois i−1, appliquée au mois i (pas de look-ahead) | `engine/update_lqq.py:193-196` |
| LQQ simulé | ×2 du rendement **quotidien** du ^NDX (capture la décote de volatilité), hors dividendes et frais | `engine/update_lqq.py:154-163` |
| Validation du simulateur | vs LQQ.PA réel 2008-2026 (run du 27/06/2026) : corrélation mensuelle 0,94 ; MaxDD COVID −51,6 % (sim) vs −52,2 % (réel) ; bear 2022 −62,9 % vs −61,2 % ; CAGR sim 26,6 %/an vs réel 27,8 %/an (les dividendes ×2 dominent le TER → sim **conservatrice**) | — |
| Données | Yahoo ^NDX (q1→q2) → FRED → Stooq, fusionnées avec cache profond committé `engine/ndx_cache.csv` (1985→) ; mode dégradé testé | `engine/update_lqq.py:114-147` |
| Perf publiée (01/07/2026, 330 mois) | strat ×208 (21,4 %/an, MaxDD −59 %) vs HODL LQQ ×34 (MaxDD −98 %) | `docs/lqq/data.json` |

---

## 2. Faiblesses de modélisation

### 2.1 Validité du backtest

**🟠 A1 — Coûts de transaction ignorés (les 3 moteurs).**
`engine/update.py:169-171`, `engine/update_eth.py:181-183`, `engine/update_lqq.py:199-201` : la
composition `strat *= (1 + w·r)` ne modélise ni frais, ni spread, ni slippage.
*Quantification (run 02/07, depuis les historiques publiés)* :

| Actif | Arbitrages | Turnover cumulé | Drag CAGR à 10 / 25 / 50 bps (aller simple) |
|---|---|---|---|
| BTC (139 mois) | 15 | 6,8× | −0,11 / −0,28 / −0,55 pt/an |
| ETH (115 mois) | 24 | 11,0× | −0,20 / −0,50 / −1,00 pt/an |
| LQQ (331 mois) | 85 | 29,5× | −0,13 / −0,32 / −0,65 pt/an |

*Impact* : modeste (le rythme mensuel limite le turnover) mais les CAGR publiés sont bruts.
*Recommandation* : publier les stats **nettes** d'un coût forfaitaire (25 bps par défaut) — correctif trivial.

**🟡 A2 — LQQ simulé hors dividendes (biais conservateur, déjà documenté).**
`engine/update_lqq.py:154-163` : simulation sur ^NDX **prix**. Le vrai LQQ capte ~2× le
rendement des dividendes, net de TER : réel 27,8 %/an vs sim 26,6 %/an (2008-2026, run 27/06).
Le biais joue **contre** la stratégie affichée et les drawdowns sont fidèles → acceptable ; la
page le mentionne. *Recommandation* : optionnel, passer à un proxy total-return.

**🟡 A3 — Skew décision/exécution (train/serve).**
Backtest BTC/ETH : exécution supposée au prix même qui génère le signal (1er jour du mois,
`update.py:108-115`) ; en production, le cron tourne à 06:00 UTC le 1er avec la bougie du jour
**en formation** (`update.py:53-75`) → léger écart aléatoire non biaisé, non modélisé.
LQQ testé explicitement (run 02/07, 1999→2026) : exécution T+0 ×208 (21,4 %/an, DD −58,9 %) ;
**T+1 jour de bourse ×215 (21,6 %/an, DD −58,2 %)** ; T+2 ×185. *Impact* : aucun biais
favorable — le délai réaliste d'un jour ne détruit pas la perf. *Recommandation* : documenter ;
rien à corriger d'urgence.

**🟢 A4 — Pas de look-ahead détecté.**
`calibrate_A` n'utilise que `d < upto` (`update.py:96-100`, `update_eth.py:109-114`) ; le vote
LQQ du mois i n'utilise que la clôture i−1 (`update_lqq.py:193-196`) ; l'échauffement de l'état
BTC (2013→) n'utilise que le passé (`update.py:132-138`). La décote du levier ×2 est
correctement capturée par la composition quotidienne, et le calendrier de bourse (jours cotés
NDX vs 24/7 crypto) est traité par construction (dernier jour coté du mois).

**🟡 A5 — Conventions de prix mensuels incohérentes entre moteurs.**
BTC/ETH : **1er jour** du mois (`update.py:108-115`) ; LQQ : **dernier jour coté**
(`update_lqq.py:165-168`). Chacune est cohérente en interne (pas de biais), mais la comparaison
inter-actifs et une future couche portefeuille exigent une convention unique.

**🟡 A6 — Biais de sélection au niveau des actifs (assumé, à écrire noir sur blanc).**
BTC, ETH et le Nasdaq-100 sont des **survivants désignés ex-post**. Les backtests répondent à
« comment détenir cet actif » et non « fallait-il choisir cet actif ». Le site ne le dit pas.
*Recommandation* : une phrase dans l'avertissement.

### 2.2 Risque de surajustement

**🔴 B1 — BTC : résultat hyper-sensible à la pente power-law.**
`engine/update.py:24` (`SLOPE = 5.8`). Sensibilité (run 02/07, 2015→2026, réplique validée) :

| Variante | Multiple | CAGR | MaxDD |
|---|---|---|---|
| slope **5,4** | **×108** | 51,1 % | −40 % |
| slope 5,8 (prod) | ×1945 | 95,1 % | −40 % |
| slope 6,2 | ×885 | 82,0 % | −63 % |
| band_high 3,0 | ×943 | 83,0 % | −63 % |

Un écart de **−0,4 sur la pente divise le multiple par 18**. La performance phare repose sur
une constante posée à la main, située sur une falaise paramétrique. SMA (8/10/12 → ×1822-1945)
et buffer (50/75/100 % → ×1445-2506) sont, eux, stables.
*Impact* : le chiffre publié (×1588) a une variance de modèle énorme ; si la « vraie » pente
dérive, la stratégie peut passer des années mal calée sans qu'on le voie.
*Recommandation* : **ensemble de paramètres** (vote sur une grille pente × bande), comme déjà
fait pour LQQ — cf. proposition P2.

**🟠 B2 — BTC : l'essentiel de la surperformance vient de l'hystérésis, mécanisme fragile.**
`engine/update.py:126-138`. Version instantanée (mêmes paramètres) : ×644, DD −63 % (vs ×1945,
−40 % sticky). Or l'expérience ETH (timeline, run 20/06) montre le mode de défaillance du
sticky : coincé en cash 2021→2025 quand le ratio ne retraverse plus la bande basse. Sur BTC ça
n'est pas (encore) arrivé parce que la power-law 5,8 est raide — précisément le paramètre le
plus fragile (B1). Les deux findings se composent.

**🟠 B3 — ETH : la pente 2,3 a été choisie avec de l'information in-sample.**
`engine/update_eth.py:37`. Le fit full-sample donnait 2,13 (R² = 0,857, run 20/06) et le
gradient est raide et monotone (run 02/07, 2017→2026) : slope 2,0 → ×110 ; 2,3 → ×266 ;
2,6 → ×562. Plus la pente est haute, plus la « juste valeur » monte vite, plus on reste investi
dans un marché haussier : le paramètre encode partiellement *le résultat souhaité*. Le refit
walk-forward pur a été testé et **rejeté sur preuve** (pente instable 1,1→2,1 → ×16, run
20/06) ; la bonne réponse est l'ensemble (P2), pas le refit.

**🟡 B4 — LQQ : fragilité de fenêtre déjà traitée par l'ensemble (bonne pratique).**
Fenêtre unique (run 27/06, 1999→2026-05) : mom 4 m → ×28 (DD −87 %) ; 8 m → ×209 (−67 %) ;
11 m → ×108 (−74 %). L'ensemble {6,8,10,12} → ×201 (−59 %) et la variante {3,6,9,12} → ×216 :
le choix des 4 fenêtres est peu sensible. C'est le modèle de ce qu'il faut répliquer sur BTC/ETH.

**🟠 B5 — L'optimisation des paramètres n'est pas reproductible depuis le repo.**
Aucun script de recherche, aucune grille, aucun protocole versionné : les constantes de
`update.py:24-28`, `update_eth.py:36-41`, `update_lqq.py:36` sortent de sessions de scratchpad
éphémères. *Recommandation* : committer un dossier `research/` (harnais + protocole + résultats).

### 2.3 Robustesse statistique

**🟠 C1 — Échantillons courts, drawdowns sous-estimés par construction.**
BTC : 136 mois / 15 arbitrages ; ETH : 112 / 24 ; LQQ : 330 / 85. Un seul chemin historique.
Bootstrap par blocs (~6 mois, 2000 tirages, run 02/07) sur les rendements mensuels **des
stratégies publiées** :

| Stratégie | MaxDD observé | MaxDD médian bootstrap | 5 % pire | 1 % pire |
|---|---|---|---|---|
| BTC | −44 % | −43 % | −63 % | −73 % |
| ETH | −64 % | −77 % | −94 % | −97 % |
| LQQ | −59 % | −55 % | −76 % | −83 % |

Le −64 % affiché pour l'ETH est **optimiste vs sa propre distribution** (médiane −77 %).
*Recommandation* : publier une fourchette de drawdown bootstrapée plutôt qu'un point unique.

**🟡 C2 — Métriques publiées incomplètes.**
`equity_stats` (`update.py:181-196`) calcule CAGR et MaxDD correctement (recalcul indépendant
concordant), mais ni Calmar (BTC 2,4 ; ETH 1,3 ; LQQ 0,36 — runs 02/07), ni exposition moyenne,
ni turnover, ni nombre d'arbitrages. Sharpe/Sortino mensuels seraient calculables sans
dépendance.

**🟢 C3 — Tenue out-of-sample réelle (le cœur des trois stratégies est sain).**
Splits par moitiés (runs 02/07 pour BTC/ETH ; 27/06 pour LQQ) :

| | 1ʳᵉ moitié | 2ᵉ moitié |
|---|---|---|
| BTC | 2015-20 : ×285 (156 %/an, DD −36 %) vs HODL ×93 (DD −74 %) | 2021-26 : ×6,8 (43 %/an, DD −40 %) vs HODL ×2,7 (DD −73 %) |
| ETH | 2017-21 : ×314 vs HODL ×460 (sous-perf. en bulle), DD −64 % vs −90 % | 2022-26 : ×0,8 (−3,7 %/an, DD −58 %) vs HODL ×0,6 (−10,8 %/an, DD −69 %) |
| LQQ | 1999-2012 : 12,9 %/an (DD −59 %) | 2013-26 : 31,8 %/an (DD −36 %) |

Aucune stratégie ne dépend d'un seul régime pour battre son HODL en risque. C'est la meilleure
nouvelle de l'audit.

### 2.4 Adéquation au type d'actif

**🟢 D1 — Les modèles sont différenciés par actif, à raison.**
BTC (power-law raide + hystérésis), ETH (power-law plate → instantané, justifié par timeline),
LQQ (pas de power-law pour un indice actions → momentum ; levier ×2 quotidien simulé au jour le
jour et validé sur l'ETF réel). Le reproche classique « même modèle plaqué partout » ne
s'applique pas.

**🔴 D2 — Aucune couche portefeuille : la diversification mesurée est ignorée.**
Corrélations des rendements mensuels **des stratégies** (fenêtre commune 2017-02→2026-07, 114
mois, run 02/07) : BTC-ETH 0,44 ; BTC-LQQ 0,20 ; ETH-LQQ 0,22 (actifs : 0,62 / 0,30 / 0,29).
Portefeuille 1/3-1/3-1/3 rebalancé mensuellement : **×227 (77,0 %/an), MaxDD −32,4 %** — un
drawdown **meilleur que chacune des trois jambes** (BTC −44 %, ETH −64 %, LQQ −36 % sur la même
fenêtre) pour un rendement proche du BTC seul. Le site présente trois silos et laisse ce repas
gratuit sur la table. *Recommandation* : page « Portefeuille » (P3).

**🟡 D3 — Signal LQQ calculé sur indice prix (pas total-return).**
Le momentum sur NDX-TR serait légèrement plus haussier (~+0,8 %/an de dividendes). Effet
probablement faible, non testé faute de série TR profonde committée. À évaluer avec P5.

---

## 3. Approches de modélisation alternatives

### 3.1 Tableau comparatif (classé par valeur attendue / risque d'implémentation)

| # | Proposition | Problème adressé | Bénéfice attendu | Complexité / données | Risque surajustement | Actifs |
|---|---|---|---|---|---|---|
| P1 | **Stats nettes de coûts + métriques enrichies** (Calmar, turnover, expo moyenne, DD bootstrap) | A1, C1, C2 | honnêteté des chiffres publiés ; ~−0,3 à −1 pt/an affiché en moins | triviale, stdlib | nul | les 3 |
| P2 | **Ensemble de paramètres valorisation BTC/ETH** : exposition = moyenne des votes G75 sur une grille pente × bande (ex. slope ∈ {5,4…6,2} × band ∈ {2,0…3,0} pour BTC ; {2,0…2,6} × {2,0…3,0} pour ETH) | B1, B2, B3 (falaise paramétrique) | supprime la dépendance à une constante unique ; réplique la robustesse démontrée de l'ensemble LQQ (B4) | faible, stdlib ; mêmes données | **réduit** le surajustement par construction ; risque = dilution du rendement (à mesurer) | BTC, ETH |
| P3 | **Page « Portefeuille »** : allocation 1/3-1/3-1/3 rebalancée mensuellement (v1), puis pondération inverse-vol 36 m (v2) | D2 | MaxDD −32 % vs −44/−64/−59 % en silos (mesuré) ; un seul chiffre d'allocation actionnable par mois | faible (compose les 3 signaux existants) | faible (v1 sans paramètre ; v2 : 1 paramètre) | portefeuille |
| P4 | **Dossier `research/` versionné** : harnais de backtest commun + protocole de validation + grilles de sensibilité committées | B5 | reproductibilité ; chaque futur changement de paramètre laisse une trace auditable | faible | nul | les 3 |
| P5 | **Proxy total-return pour le signal/backtest LQQ** | A2, D3 | fidélité (+~1 pt/an sur HODL sim ; signal marginalement plus juste) | moyenne : sourcer ^NDX-TR profond et fiable depuis un runner | nul | LQQ |
| P6 | **Overlay volatilité LQQ** (exposition × min(1, σ_cible/σ_réalisée 6 m), plafond 100 %) | drawdown LQQ (−59 %) | testé le 27/06 en variante gate SMA : DD −46 % mais CAGR 17,7 % (vs 21,4 %) — version ensemble×vol à tester | faible ; données quotidiennes déjà en cache | moyen (1 paramètre σ_cible ; gradient à cartographier) | LQQ (adapté au levier : décote ∝ variance) |
| P7 | **Détection de régime (HMM 2 états ou filtre vol)** | régime-dépendance résiduelle | incertain : avec 112-330 points mensuels, un HMM estimé est bruité ; le filtre vol (P6) capture l'essentiel plus simplement | HMM : forte (implémentation EM stdlib) ; ⚠️ 136 points BTC ≪ besoin | **élevé** — déconseillé en l'état | — |
| P8 | **GARCH mensuel** | modélisation de la vol | rejeté : à cadence mensuelle, la vol réalisée sur données quotidiennes (déjà en cache pour LQQ) domine un GARCH estimé sur ~300 points | forte | élevé | — |
| P9 | **Refit walk-forward de la pente power-law** | B3 | **rejeté sur preuve** : testé le 20/06 sur ETH → pente instable (1,1→2,1), ×16 vs ×266 ; l'ensemble P2 est la réponse correcte au même problème | — | — | — |
| P10 | **Kelly fractionné / risk parity complet** | sizing | prématuré tant que P3-v1 n'a pas tourné ; Kelly sur des CAGR backtestés à forte variance (C1) sur-alloue mécaniquement | moyenne | élevé (hérite du bruit des estimateurs) | portefeuille |

### 3.2 Ce que je ne recommande PAS et pourquoi (résumé)

- **ML supervisé (arbres, régressions régularisées)** : 112-330 observations mensuelles par
  actif, cibles bruitées, non-stationnarité — le ratio données/degrés de liberté est
  indéfendable. Le gain espéré est inférieur au risque de sur-apprentissage, même avec purged CV.
- **HMM / GARCH (P7, P8)** : voir tableau — la version simple (vol réalisée) obtient l'essentiel
  du bénéfice pour un dixième du risque.
- **Refit de pente (P9)** : contredit par l'expérience — c'est un cas documenté où « plus
  adaptatif » = pire.

---

## 4. Recommandations priorisées

### 4.1 Corrections indispensables (biais, erreurs)
1. **P1 — publier des stats nettes de coûts** (défaut 25 bps/aller) et compléter les métriques
   (Calmar, turnover, expo moyenne, nb d'arbitrages, fourchette DD bootstrap). Les chiffres
   actuels sont bruts et à point unique — c'est le seul endroit où le site « embellit ».
2. **A6 — une phrase de biais de sélection** dans l'avertissement des 3 pages (« BTC/ETH/NDX
   sont des survivants choisis ex-post »).

### 4.2 Améliorations à fort ROI
3. **P2 — ensembles de paramètres BTC/ETH** (le correctif du 🔴 B1 et des 🟠 B2/B3). Critère de
   succès défini au §5 — si l'ensemble coûte trop de rendement, on publiera au minimum la carte
   de sensibilité sur la page (transparence).
4. **P3 — page Portefeuille** (le correctif du 🔴 D2). v1 sans paramètre (1/3 chacun).
5. **P4 — dossier `research/` versionné** (transforme cet audit en pratique permanente).

### 4.3 Explorations plus avancées (optionnelles, dans l'ordre)
6. **P6 — overlay vol LQQ** (si l'objectif drawdown devient prioritaire sur le rendement).
7. **P5 — total-return LQQ** (si une source TR fiable et profonde est trouvée).
8. P7/P8/P10 : seulement après plusieurs années de vie supplémentaires des stratégies.

---

## 5. Plan d'implémentation et de validation

> Rappels d'exécution : une amélioration à la fois, sur branche dédiée `feat/modeling-<nom>` ;
> validation avant merge ; **rien dans ce plan ne touche à une exécution réelle** (le repo n'en
> a pas — l'exécution reste manuelle et hors périmètre). Le « paper mode » équivalent ici est le
> **shadow run mensuel** : publier le nouveau signal en parallèle de l'ancien sans changer la
> consigne affichée, pendant N mois si souhaité.

### P1 — Stats nettes de coûts + métriques enrichies
- **Fichiers** : `engine/update.py`, `engine/update_eth.py`, `engine/update_lqq.py`
  (fonction `equity_stats` + boucle de composition), `engine/build_site.py` (affichage).
- **Changement** : composer en parallèle une courbe nette `strat_net *= (1+w·r)·(1−c·|Δw|)`
  avec `c = 0.0025` ; ajouter Calmar, turnover, expo moyenne, arbitrages ; bootstrap DD
  (blocs 6 m, 2000 tirages, seed fixe) affiché en fourchette.
- **Validation** : les stats brutes doivent rester identiques au centime (non-régression) ;
  les stats nettes doivent concorder avec le calcul indépendant de cet audit (§2.1 A1, ±0,05 pt).
- **Critère d'acceptation** : concordance chiffrée ci-dessus + rendu des 3 pages inchangé hors
  nouvelles métriques.

### P2 — Ensemble de paramètres BTC/ETH
- **Fichiers** : `engine/update.py`, `engine/update_eth.py` (+ `research/` pour les grilles).
- **Changement** : exposition = moyenne des allocations G75 sur une grille (BTC :
  slope ∈ {5,4;5,6;5,8;6,0;6,2} × band_high ∈ {2,0;2,5;3,0}, hystérésis conservée par membre ;
  ETH : slope ∈ {2,0;2,2;2,4;2,6} × band_high ∈ {2,0;2,5;3,0}, instantané par membre).
  La cible devient continue (arrondie à 5 %) au lieu de {0;75;100}.
- **Validation** : (i) backtest complet vs baseline sur la même période ; (ii) OOS par moitiés
  (mêmes splits que §2.3 C3) ; (iii) carte de sensibilité **de l'ensemble** aux choix de grille
  (retirer/ajouter un membre ne doit pas déplacer le CAGR de plus de ±3 pts) ; (iv) coûts nets
  P1 appliqués (l'ensemble arbitre plus souvent — à chiffrer).
- **Critère d'acceptation chiffré** : Calmar de l'ensemble ≥ Calmar baseline − 10 %, **et**
  perte de CAGR ≤ 15 pts (BTC) / 10 pts (ETH) vs baseline, **et** sensibilité (iii) respectée.
  Sinon : on ne remplace pas la prod ; on publie la carte de sensibilité (transparence) et
  l'ensemble reste en shadow.
- **Shadow run** : 3 mois de double publication (`data.json` : champ `ensemble_target` à côté
  de `target`) avant bascule de la consigne affichée.

### P3 — Page Portefeuille
- **Fichiers** : nouveau `engine/update_portfolio.py`, `engine/build_site.py` (nav + rendu),
  `docs/portfolio/`, workflow (4ᵉ étape après les 3 moteurs).
- **Changement v1** : lit les trois `data.json`, compose 1/3·BTC + 1/3·ETH + 1/3·LQQ
  (rebalance mensuel), publie cible consolidée par poche + backtest combiné sur fenêtre commune.
- **Validation** : réplication du chiffre d'audit (×227, 77,0 %/an, DD −32,4 % sur
  2017-02→2026-07, ±1 % près — même convention de dates) ; vérif de la gestion des débuts de
  série non alignés (LQQ commence en 1999, ETH en 2017).
- **Critère d'acceptation** : concordance avec l'audit + cohérence des cibles affichées
  (somme des poches = 100 %).
- **v2 (après ≥1 mois de v1)** : pondération inverse-vol 36 mois, mêmes protocoles, critère :
  Calmar v2 ≥ Calmar v1 sur OOS par moitiés.

### P4 — Dossier `research/`
- **Fichiers** : `research/harness.py` (le harnais commun de cet audit : chargement, backtest,
  sensibilité, bootstrap, OOS), `research/PROTOCOLE.md` (splits, seeds, critères), résultats CSV.
- **Validation** : le harnais doit répliquer les 3 courbes publiées à l'identique (comme fait
  dans cet audit : écart 0,0 % à millésime de données égal).
- **Critère d'acceptation** : réplication exacte + un `python research/harness.py --all` qui
  régénère toutes les tables du §2 en < 5 min.

### P6 — Overlay vol LQQ (optionnel)
- **Fichiers** : `engine/update_lqq.py`, `research/`.
- **Changement** : `w_final = w_ensemble × min(1, σ_cible / σ_6m)` (σ quotidienne annualisée,
  déjà calculable depuis `ndx_cache.csv`), σ_cible à cartographier sur {20 %, 25 %, 30 %}.
- **Validation** : grille complète + OOS moitiés + coûts nets (turnover supérieur).
- **Critère d'acceptation chiffré** : MaxDD ≤ −50 % (vs −59 %) avec perte de CAGR ≤ 2 pts,
  robuste sur les deux moitiés. Sinon : rester sur l'ensemble nu.

---

*Audit réalisé le 02/07/2026. Runs exécutés sur les millésimes indiqués en tête de document ;
réimplémentations validées contre `docs/*/history.csv`. Ce document ne constitue pas un conseil
en investissement ; les performances passées, backtestées ou bootstrapées, ne préjugent pas des
performances futures.*
