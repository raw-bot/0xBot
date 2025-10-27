# 🎯 Stratégie pour Sortir de l'Ornière

## Le Problème
Après 10+ fixes, Qwen répond toujours "Insufficient data" avec confidence 50%. On tourne en rond sans voir le vrai problème.

## 🔬 Nouvelle Approche: MÉTHODOLOGIE SCIENTIFIQUE

Au lieu de deviner, on va **VOIR EXACTEMENT** ce qui se passe.

---

## PHASE 1: Diagnostic Complet (5 min)

### Étape 1: Lancer le script de diagnostic

```bash
cd backend
python scripts/tests/debug_prompt_content.py
```

### Étape 2: Analyser la sortie

Le script va afficher:
1. ✅ Les valeurs calculées (RSI, EMA, MACD)
2. ✅ Le prompt COMPLET envoyé à Qwen
3. ✅ Une vérification automatique des valeurs dans le prompt

### Étape 3: Identifier le problème

**Scénario A**: Les valeurs dans le prompt sont **correctes** (RSI 43.5, EMA 1141.2, etc.)
→ **Le problème est le PROMPT lui-même** (trop complexe ou mal formulé)

**Scénario B**: Les valeurs dans le prompt sont **par défaut** (RSI 50, EMA 0)
→ **Le problème est le CALCUL** (notre dernier fix n'a pas fonctionné)

---

## PHASE 2: Action selon Diagnostic

### Si Scénario A (Prompt trop complexe)

**SOLUTION**: Simplifier drastiquement le prompt

1. Créer un prompt minimaliste qui FORCE une décision:

```python
# Prompt ultra-simple
prompt = f"""
You are a crypto trader. Analyze {symbol}:

CURRENT DATA:
- Price: ${price}
- RSI(14): {rsi}
- Trend: {'Bullish' if ema20 > ema50 else 'Bearish'}

RULES:
- RSI < 35 AND Bullish → ENTRY
- RSI > 65 AND Bearish → EXIT
- Otherwise → HOLD

OUTPUT JSON:
{{
  "{symbol}": {{
    "signal": "entry|hold|exit",
    "confidence": 0.75,
    "justification": "One line reason",
    "entry_price": {price},
    "stop_loss": {price * 0.965},
    "profit_target": {price * 1.07},
    "side": "long",
    "size_pct": 0.05
  }}
}}
"""
```

2. Tester ce prompt minimal
3. Si ça marche → Enrichir progressivement

### Si Scénario B (Calcul défaillant)

**SOLUTION**: Forcer des valeurs de test

1. Modifier temporairement [`market_data_service.py`](backend/src/services/market_data_service.py) pour logger:

```python
# Dans get_market_snapshot, après calcul des indicateurs
logger.info(f"🔍 DEBUG RSI series: {rsi14_series[-10:]}")  # 10 dernières valeurs
logger.info(f"🔍 DEBUG RSI final: {get_last_valid(rsi14_series)}")
```

2. Relancer et vérifier les logs
3. Si toujours des None → Problème plus profond dans IndicatorService

---

## PHASE 3: Test avec Valeurs Forcées

Si tout échoue, créons un **mode test** qui force des valeurs:

```python
# Test mode: force des valeurs connues
TEST_MODE = True

if TEST_MODE:
    snapshot['technical_indicators']['5m'] = {
        'ema20': 1140.5,
        'ema50': 1135.2,
        'macd': 2.5,
        'rsi7': 45.3,
        'rsi14': 43.5,
    }
```

Si Qwen prend des décisions avec ces valeurs forcées → Le problème est CONFIRMÉ dans le calcul.

---

## PHASE 4: Solution Radicale

Si rien ne marche, deux options:

### Option A: Changer de stratégie LLM
- Utiliser un prompt beaucoup plus simple
- Réduire le contexte à l'essentiel
- Accepter des décisions moins sophistiquées mais qui FONCTIONNENT

### Option B: Mode debug permanent
- Ajouter un flag `--debug` qui log TOUT
- Sauvegarder chaque prompt dans un fichier
- Analyser manuellement pourquoi Qwen ne répond pas comme attendu

---

## 🚀 Commandes à Exécuter MAINTENANT

```bash
# 1. Lancer le diagnostic
cd backend
python scripts/tests/debug_prompt_content.py > /tmp/diagnostic.txt

# 2. Voir le résultat
cat /tmp/diagnostic.txt

# 3. Copier-coller la section "PROMPT COMPLET" ici pour analyse
```

---

## 📊 Métriques de Succès

On saura qu'on a réussi quand:
1. ✅ Le script de diagnostic montre des vraies valeurs dans le prompt
2. ✅ Qwen répond avec confidence > 55%
3. ✅ Le bot prend au moins 1 décision ENTRY ou EXIT par heure
4. ✅ Les décisions sont cohérentes avec les conditions de marché

---

## 💡 Pourquoi Cette Approche Fonctionne

1. **Visibilité totale**: On voit EXACTEMENT ce qui se passe
2. **Pas de supposition**: Les données parlent d'elles-mêmes
3. **Test incrémental**: On part du simple pour aller au complexe
4. **Fallback clair**: Si ça ne marche pas, on a un plan B et C

---

## 🎯 Prochaine Étape

**LANCEZ LE DIAGNOSTIC MAINTENANT** et envoyez-moi:
1. Les valeurs calculées affichées
2. Un extrait du prompt (les 50 premières lignes)
3. Les valeurs vérifiées à la fin

Avec ça, on saura EXACTEMENT où est le problème et comment le résoudre.

Plus de devinettes. Plus de fixes aveugles. Que des FAITS.