# Mise à Jour du Format du Prompt LLM - Reproduction Bot +93%

## Date: 2025-10-27

## Objectif
Reproduire exactement le format du prompt du bot de référence +93% pour améliorer la performance du trading.

## Modifications Apportées

### 1. enriched_llm_prompt_service.py

#### _format_market_data() - Format EXACT du bot +93%
- **Header**: Format `ALL {symbol} DATA` avec ligne récapitulative
- **Open Interest**: Ajout de Latest et Average values
- **Funding Rate**: Intégration du taux de financement
- **Séries temporelles**: 10 points pour tous les indicateurs:
  - Mid prices
  - EMA indicators (20‑period)
  - MACD indicators
  - RSI indicators (7‑Period et 14‑Period)
- **Contexte 4h**: ATR3 vs ATR14, Volume vs Average Volume
- **Séries 4h**: MACD indicators et RSI indicators

#### build_enriched_prompt() - Structure identique
- **Introduction**: "It has been X minutes since you started trading..."
- **Section complète**: `CURRENT MARKET STATE FOR ALL COINS` avec TOUS les coins en détail
- **Section performance**: `HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE`
- **Section analyse**: `▶ CHAIN_OF_THOUGHT` pour l'analyse
- **Section décisions**: `▶ TRADING_DECISIONS` pour la sortie
- **Format de sortie**: `BTC HOLD 72% QUANTITY: 0.12`

### 2. market_data_service.py

#### Nouvelle méthode get_open_interest()
- Récupère l'Open Interest depuis l'exchange
- Retourne `{latest, average}`

#### get_market_snapshot() enrichi
- Ajout `open_interest` et `funding_rate`
- Calcul et stockage de TOUTES les séries:
  - `price_series`, `ema20_series`, `ema50_series`
  - `macd_series`, `rsi7_series`, `rsi14_series`
- Calcul ATR3 et ATR14
- Structure `technical_indicators` avec valeurs 5m et 1h

#### get_market_data_multi_timeframe() amélioré
- Ajout séries 4h: `macd_series_4h`, `rsi14_series_4h`
- Calcul complet des indicateurs 4h (EMA20/50, MACD, RSI14, ATR3/14, Volume)
- Remplissage de `technical_indicators['1h']` avec vraies valeurs 4h

### 3. indicator_service.py
- **Déjà prêt**: Toutes les méthodes nécessaires existaient
- `calculate_atr()` pour ATR3 et ATR14
- `calculate_rsi()` support RSI7 et RSI14

## Format Final Reproduit

```
It has been 7512 minutes since you started trading. The current time is 2025-10-27 18:21:15...

CURRENT MARKET STATE FOR ALL COINS
==================================================

ALL BTC DATA
current_price = 115599.5, current_ema20 = 115641.785, current_macd = 49.905, current_rsi (7 period) = 41.836
In addition, here is the latest BTC open interest and funding rate for perps:
Open Interest: Latest: 31170.17 Average: 31237.52
Funding Rate: 1.25e-05

Intraday series (3‑minute intervals, oldest → latest):
Mid prices: [115637.5, 115679.5, 115684.5, ...]
EMA indicators (20‑period): [115561.966, 115572.446, ...]
MACD indicators: [52.171, 53.662, 50.39, ...]
RSI indicators (7‑Period): [55.115, 57.713, 52.086, ...]
RSI indicators (14‑Period): [55.066, 56.362, 53.693, ...]

Longer‑term context (4‑hour timeframe):
20‑Period EMA: 112938.535 vs. 50‑Period EMA: 111539.738
3‑Period ATR: 421.773 vs. 14‑Period ATR: 606.485
Current Volume: 3.771 vs. Average Volume: 4710.214
MACD indicators: [620.872, 633.819, 769.48, ...]
RSI indicators (14‑Period): [56.894, 60.384, 68.763, ...]

[ETH, SOL, BNB, XRP, DOGE data in same format]

HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): 128.53%
Available Cash: 13654.1
Current Account Value: 22852.7

[Positions data]

Sharpe Ratio: 0.499

▶ CHAIN_OF_THOUGHT
[Analysis for each coin]

▶ TRADING_DECISIONS
ETH HOLD 65% QUANTITY: 5.74
BTC HOLD 75% QUANTITY: 0.12
SOL HOLD 65% QUANTITY: 33.88
...
```

## Impact Attendu
- **Performance améliorée**: Format identique au bot +93% devrait donner des résultats similaires
- **Données complètes**: Toutes les informations nécessaires pour l'analyse technique
- **Compatibilité**: Structure de sortie compatible avec le système existant

## Fichiers Modifiés
- `backend/src/services/enriched_llm_prompt_service.py`
- `backend/src/services/market_data_service.py`

## Tests Requis
- Vérifier que le prompt généré correspond exactement au format de référence
- Tester que toutes les données sont correctement récupérées
- Valider que les décisions LLM sont parsées correctement