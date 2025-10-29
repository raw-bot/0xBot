# 🔍 AUDIT DES CONFLITS ET REDONDANCES

## 🚨 CONFLITS CRITIQUES IDENTIFIÉS

### CONFLIT 1: Seuils de Confiance Multiples (Non-Coordonnés)

```python
# Problem: Le LLM ne sait pas quel seuil utiliser !
- ENTRY: confidence < 0.75 (ligne 414)
- EXIT précoce (< 1h): confidence < 0.85 (ligne 449)
- EXIT normal (> 1h): confidence < 0.75 (ligne 459)
```

### CONFLIT 2: Max Position Size - 4 Valeurs Différentes

```python
# Problem: Instructions contradictoires au LLM !
1. bot_service.py:         "max_position_pct": 0.15      # 15%
2. risk_manager_service.py:  max_position_pct = 0.15     # 15%
3. prompt LLM:             "0.03 to 0.08"               # 3-8%
4. llm_prompt_service.py:  max_position = 0.10           # 10%
```

### CONFLIT 3: Triple Validation Redondante

```python
# Problem: Validation répétitive et coûteuse !
1. Filter confiance dans trading_engine_service.py
2. RiskManagerService.validate_complete_decision()
3. Validation supplémentaire dans trade_executor
```

### CONFLIT 4: Messages de Logging Contradictoires

```python
# Problem: Messages différents pour le même échec !
"Low confidence 72% < 80% threshold" (OLD)
"Low confidence 72% < 75% threshold" (NEW)
```

## 🔧 SOLUTIONS RECOMMANDÉES

### 1. Harmoniser les Seuils de Confiance

- Utiliser un seul seuil cohérent (75% pour ENTRY)
- Passer le contexte dans le prompt LLM

### 2. Standardiser max_position_pct

- Choisir 0.08 (8%) comme valeur universelle
- Synchroniser tous les fichiers

### 3. Simplifier les Validations

- Garder seulement le filtre de confiance dans trading_engine
- Supprimer la double validation dans risk_manager
- Garder risk_manager pour les validations techniques (SL/TP)

### 4. Uniformiser les Messages

- Un seul format de message d'erreur
- Cohérence entre tous les services
