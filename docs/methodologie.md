# Méthodologie — stratégie G75

## 1. Univers et fréquence
- Actif : **Bitcoin (BTC/USD)**, alterné avec du **cash** (USDC).
- Décision : **une fois par mois**, le 1ᵉʳ à 06:00 UTC, sur le prix de début de mois.
- Aucune intervention entre deux 1ᵉʳ du mois.

## 2. Signal de tendance — moyenne mobile 10 mois
À chaque début de mois, on compare le prix `P(t)` à la moyenne des **10 derniers prix mensuels** :

```
MM10(t) = moyenne( P(t-9) … P(t) )
Tendance = HAUSSE  si  P(t) > MM10(t)
           BAISSE  sinon
```

C'est le filtre de tendance « à la Faber ». Il re-rentre plus tôt après un creux et sort plus
proprement qu'une comparaison point-à-point. Le résultat est stable pour une fenêtre de 8 à 11 mois.

## 3. Signal de valorisation — power-law
La « juste valeur » suit une droite en échelle log-log en fonction de l'**âge** du Bitcoin
(jours depuis le bloc genesis du 3 janvier 2009) :

```
ln(juste_valeur) = A + 5,8 × ln(jours_depuis_genesis)
```

- **Pente = 5,8** (fixe).
- **Intercept A** : recalibré **une fois par an, le 1ᵉʳ janvier**, comme la moyenne de
  `ln(prix) − 5,8 × ln(jours)` sur **tout l'historique antérieur** (puis gelé pour l'année).
  → garantit l'absence d'information du futur (walk-forward).

Bandes de tolérance :

```
ratio = prix / juste_valeur
ratio > 2,5  → « chère »        (valorisation = CASH)
ratio < 0,6  → « bon marché »   (valorisation = BUY)
entre les deux → on conserve l'état précédent
```

## 4. Règle d'allocation « G75 »

```
si valorisation == chère        → 0 %   (cash)
sinon si tendance == HAUSSE      → 100 % BTC
sinon                            → 75 %  BTC
```

Le « 75 % » est le curseur d'exposition lorsque le BTC **baisse sans être cher**. Une version
prudente mettrait 50 %, une version agressive 100 % ; 75 % est l'entre-deux retenu ici.

## 5. Action affichée
Chaque mois, on compare la cible à celle du mois précédent :
- cible en hausse → **ACHETER / RENFORCER**
- cible en baisse → **VENDRE / ALLÉGER**
- cible inchangée → **CONSERVER**

On n'achète/vend que l'écart entre l'ancienne et la nouvelle cible.

## 6. Limites et honnêteté
- Le backtest porte sur le seul Bitcoin, l'actif qui a le plus récompensé ce type de stratégie ;
  l'essentiel de la surperformance vient d'avoir évité **deux krachs** (2018, 2022).
- La power-law **n'est pas une loi** : c'est une extrapolation statistique du passé, qui prédit
  elle-même des rendements futurs déclinants. Si le régime de croissance du BTC change, la
  « juste valeur » devient trompeuse.
- Le cash est supposé rémunéré à 0 % (hypothèse prudente) ; les frais de transaction sont négligés
  (≈ 1 à 2 arbitrages par an).
- **Ce document décrit une méthode quantitative, pas un conseil en investissement.**
