# 📋 DÉCOUPAGE EN PHASES - EXPERT ROADMAP

## Vue d'ensemble
Transformation du bot pour exploiter Qwen3 Max à 100% avec un découpage en **7 phases indépendantes**.

---

## PHASE 1 : Service de Mémoire Trading (15 min)
**Objectif** : Créer le service de contexte de trading  
**Fichier** : `/backend/services/trading_memory_service.py`

### Actions
- ✅ Créer le fichier `trading_memory_service.py`
- ✅ Implémenter `TradingMemoryService` avec :
  - Contexte de session (durée, invocations)
  - Contexte portfolio (capital, equity, PnL)
  - Contexte positions (positions ouvertes, PnL par position)
  - Contexte trades du jour (nombre, win rate, meilleurs/pires)
  - Calcul du Sharpe Ratio
- ✅ Tester l'import : `python3 -c "from backend.services.trading_memory_service import TradingMemoryService; print('✅ OK')"`

### Validation
```bash
cd /Users/cube/Documents/00-code/0xBot
python3 -c "from backend.services.trading_memory_service import TradingMemoryService; print('✅ Memory Service OK')"
```

**Fichiers modifiés** : 1 nouveau fichier  
**Risque** : Faible (nouveau service isolé)

---

## PHASE 2 : Service de Prompts Enrichis (15 min)
**Objectif** : Créer le service de génération de prompts avancés  
**Fichier** : `/backend/services/enriched_llm_prompt_service.py`

### Actions
- ✅ Créer le fichier `enriched_llm_prompt_service.py`
- ✅ Implémenter `EnrichedLLMPromptService` avec :
  - `build_enriched_prompt()` : Construction du prompt avec tout le contexte
  - `parse_llm_response()` : Parsing des réponses JSON du LLM
  - `get_simple_decision()` : Méthode wrapper
- ✅ Tester l'import

### Validation
```bash
python3 -c "from backend.services.enriched_llm_prompt_service import EnrichedLLMPromptService; print('✅ Prompt Service OK')"
```

**Fichiers modifiés** : 1 nouveau fichier  
**Risque** : Faible (nouveau service isolé)

---

## PHASE 3A : Imports Trading Engine (5 min)
**Objectif** : Ajouter les imports nécessaires  
**Fichier** : `/backend/services/trading_engine_service.py`

### Actions
- ✅ Backup du fichier : `cp trading_engine_service.py trading_engine_service.py.backup`
- ✅ Ajouter à la ligne ~15 :
```python
from backend.services.enriched_llm_prompt_service import EnrichedLLMPromptService
from backend.services.trading_memory_service import get_trading_memory
```
- ✅ Vérifier compilation : `python3 -m py_compile backend/services/trading_engine_service.py`

### Validation
```bash
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Imports OK"
```

**Fichiers modifiés** : 1 (modification mineure)  
**Risque** : Très faible

---

## PHASE 3B : Initialisation Services (5 min)
**Objectif** : Initialiser les nouveaux services dans le trading engine  
**Fichier** : `/backend/services/trading_engine_service.py`

### Actions
- ✅ Dans `__init__`, après `self.llm_service = ...`, ajouter :
```python
self.enriched_prompt_service = EnrichedLLMPromptService(db)
self.trading_memory = get_trading_memory(db, bot.id)
```
- ✅ Vérifier compilation

### Validation
```bash
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Init OK"
```

**Fichiers modifiés** : 1 (modification mineure)  
**Risque** : Très faible

---

## PHASE 3C : Méthodes Helper (10 min)
**Objectif** : Ajouter les méthodes de calcul d'indicateurs  
**Fichier** : `/backend/services/trading_engine_service.py`

### Actions
- ✅ Ajouter à la fin de la classe `TradingEngine` :
  - `_get_all_coins_quick_snapshot()` : Snapshot rapide de tous les coins
  - `_calculate_rsi()` : Calcul RSI
  - `_calculate_ema()` : Calcul EMA
- ✅ Vérifier compilation

### Validation
```bash
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Helpers OK"
```

**Fichiers modifiés** : 1 (ajout de méthodes)  
**Risque** : Faible (méthodes utilitaires isolées)

---

## PHASE 3D : Remplacement Appel LLM (15 min)
**Objectif** : Remplacer l'ancien système LLM par le nouveau  
**Fichier** : `/backend/services/trading_engine_service.py`

### Actions
- ✅ Localiser le bloc :
```python
# Get LLM decision
llm_decision = await self.llm_service.get_decision(
    symbol=symbol,
    market_data=market_snapshot,
    position=current_position
)
```
- ✅ Remplacer par le nouveau système avec prompt enrichi
- ✅ Ajouter parsing de la réponse JSON
- ✅ Ajouter fallback en cas d'erreur de parsing
- ✅ Vérifier compilation

### Validation
```bash
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ LLM Integration OK"
```

**Fichiers modifiés** : 1 (modification critique)  
**Risque** : Moyen (changement logique principale)

---

## PHASE 3E : Enrichissement Market Data (10 min)
**Objectif** : Ajouter les séries temporelles au market snapshot  
**Fichier** : `/backend/services/trading_engine_service.py`

### Actions
- ✅ Localiser où `market_snapshot` est créé
- ✅ Ajouter les séries :
  - `price_series` : 10 derniers prix
  - `ema_series` : 10 dernières valeurs EMA
  - `rsi_series` : 10 dernières valeurs RSI
- ✅ Vérifier compilation

### Validation
```bash
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Market Enrichment OK"
```

**Fichiers modifiés** : 1 (enrichissement données)  
**Risque** : Faible (ajout d'informations)

---

## PHASE 4 : Tests Unitaires (10 min)
**Objectif** : Vérifier que tout compile et fonctionne  

### Actions
```bash
# Test imports
cd /Users/cube/Documents/00-code/0xBot
python3 -c "from backend.services.trading_memory_service import TradingMemoryService; print('✅ Memory OK')"
python3 -c "from backend.services.enriched_llm_prompt_service import EnrichedLLMPromptService; print('✅ Prompt OK')"
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Engine OK"

# Test compilation globale
python3 -c "from backend.services.trading_engine_service import TradingEngine; print('✅ All imports OK')"
```

### Validation
- ✅ Tous les imports passent
- ✅ Pas d'erreur de syntaxe
- ✅ Pas d'erreur de dépendances circulaires

**Risque** : Nul (tests uniquement)

---

## PHASE 5 : Déploiement et Monitoring (10 min)
**Objectif** : Lancer le bot et observer les premiers résultats  

### Actions
```bash
# Backup de la DB
cp backend/database.db backend/database.db.backup

# Reset et lancement
./scripts/reset.sh
./start.sh

# Observer les logs
tail -f backend.log | grep -E "(Session Duration|Decision|Confidence)"
```

### Validation (premiers 10 minutes)
- ✅ Bot démarre sans erreur
- ✅ Logs montrent "Session Duration: X minutes"
- ✅ Confidences apparaissent (vérifier 50%+)
- ✅ Raisonnements apparaissent (vérifier longueur)
- ✅ Décisions HOLD majoritaires

**Risque** : Moyen (première exécution réelle)

---

## PHASE 6 : Validation 30 Minutes (30 min)
**Objectif** : Valider le comportement sur une période courte  

### Checklist
- [ ] Bot continue de tourner sans crash
- [ ] Contexte enrichi apparaît dans les logs
- [ ] Décisions LLM sont HOLD majoritairement (>60%)
- [ ] Confidences entre 50% et 85%
- [ ] Maximum 2-3 trades en 30 minutes
- [ ] Raisonnements mentionnent le portfolio
- [ ] Pas d'erreur de parsing JSON

### Métriques à surveiller
```bash
# Compter les décisions
grep "Decision" backend.log | tail -20

# Vérifier les trades
sqlite3 backend/database.db "SELECT COUNT(*) FROM trades WHERE timestamp > datetime('now', '-30 minutes');"

# Vérifier les confidences
grep "Confidence" backend.log | tail -10
```

**Risque** : Faible (observation uniquement)

---

## PHASE 7 : Validation 24h et Documentation (suivi)
**Objectif** : Valider sur la durée et documenter  

### Après 24h
- [ ] Analyser les métriques de performance
- [ ] Comparer avec les objectifs :
  - 1-3 trades/h (vs 10 trades/10min avant)
  - Conf 75-85% (vs 65% avant)
  - Reasoning 200+ chars (vs 50 chars avant)
  - HOLD 70%+ (vs 20% avant)
- [ ] Documenter les résultats dans `edits.md`
- [ ] Créer rapport de performance

### Rollback si nécessaire
```bash
cd /Users/cube/Documents/00-code/0xBot/backend/services
cp trading_engine_service.py.backup trading_engine_service.py
rm trading_memory_service.py enriched_llm_prompt_service.py
./start.sh
```

**Risque** : Nul (validation long terme)

---

## 📊 Résumé des Phases

| Phase | Durée | Fichiers | Risque | Dépendances |
|-------|-------|----------|--------|-------------|
| 1 | 15 min | 1 nouveau | Faible | Aucune |
| 2 | 15 min | 1 nouveau | Faible | Phase 1 |
| 3A | 5 min | 1 modif | Très faible | Phase 1, 2 |
| 3B | 5 min | 1 modif | Très faible | Phase 3A |
| 3C | 10 min | 1 modif | Faible | Phase 3B |
| 3D | 15 min | 1 modif | Moyen | Phase 3C |
| 3E | 10 min | 1 modif | Faible | Phase 3D |
| 4 | 10 min | Tests | Nul | Phase 1-3E |
| 5 | 10 min | Déploiement | Moyen | Phase 4 |
| 6 | 30 min | Validation | Faible | Phase 5 |
| 7 | 24h+ | Documentation | Nul | Phase 6 |

**Total** : ~2h30 de travail actif + 24h de validation

---

## 🎯 Ordre d'Exécution Recommandé

**Session 1 (45 min)** : Phases 1, 2, 3A, 3B, 3C  
➡️ Créer les services et helpers

**Session 2 (30 min)** : Phases 3D, 3E, 4  
➡️ Intégrer et tester

**Session 3 (1h)** : Phases 5, 6  
➡️ Déployer et valider court terme

**Session 4 (suivi)** : Phase 7  
➡️ Valider long terme et documenter

---

## ⚠️ Points d'Attention

1. **Toujours backup** avant modification de `trading_engine_service.py`
2. **Tester imports** après chaque phase
3. **Vérifier logs** en temps réel pendant Phase 5
4. **Ne pas paniquer** si beaucoup de HOLD (c'est l'objectif !)
5. **Garder backup DB** avant reset

---

*Découpage créé à partir de EXPERT_ROADMAP.md - Version 1.0*

