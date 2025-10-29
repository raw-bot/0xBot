# 🔍 Audit Global du Projet - Plan d'Action

## Phase 1: Cartographie des Flux Critiques (30min)
**Objectif:** Identifier les chemins critiques

**Flux à mapper:**
1. **Bot Start** → Trading Engine → Market Data → LLM → Decision → Execution
2. **Entry Flow** → Risk Validation → Order Execution → Position Creation → Capital Update
3. **Exit Flow** → Price Check → SL/TP Trigger → Order Execution → Position Close → Capital Update
4. **Portfolio State** → Positions → Capital → Equity Calculation

## Phase 2: Analyse Statique (1h)

**A. Types & Cohérence**
```bash
# Script d'audit automatique
python -c "
import ast, os
for root, dirs, files in os.walk('backend/src'):
    for f in [f for f in files if f.endswith('.py')]:
        # Chercher: mixed Decimal/float, async mal géré, None checks manquants
"
```

**Zones critiques à vérifier:**
- `models/*.py` - Propriétés calculées (Decimal vs float)
- `services/trade_*.py` - Arithmétique financière
- `services/trading_engine_service.py` - Async/await patterns
- `services/*_service.py` - Database queries (lazy loading)

**B. Dépendances de données**
```bash
# Vérifier cohérence DB schema vs models
alembic current
alembic history
```

## Phase 3: Tests de Régression Minimaux (2h)

**Créer:** `backend/scripts/tests/audit_critical_paths.py`

```python
"""
Test 1: Full Trading Cycle
- Start bot → Wait 1 cycle → Check positions created
- Force price change → Check SL triggered
- Verify capital: initial - entry_cost + exit_proceeds = final

Test 2: Multi-Symbol Handling
- 5 symbols → Each gets correct price
- Positions don't mix prices

Test 3: Capital Integrity
- Sum(capital + invested) = equity
- After 10 cycles: no drift

Test 4: Database Consistency
- Positions.status matches reality
- Trades.realized_pnl calculated correctly
- Bot.capital updated atomically
"""
```

## Phase 4: Monitoring En Production (24h)

**Ajouter métriques critiques:**
```python
# Dans trading_engine_service.py
logger.info(f"METRICS | Positions: {len(positions)} | "
           f"Capital: ${capital} | Equity: ${equity} | "
           f"Drift: {abs(equity - (capital + invested))}")
```

**Alertes à monitorer:**
- Positions > 2h sans exit
- Capital drift > $0.01
- Erreurs async/await
- Prix = 0 ou None

## Phase 5: Audit Code Critique (1h30)

**Services par priorité:**

**🔴 CRITIQUE (vérifier d'abord):**
1. `trading_engine_service.py` - Orchestration
2. `trade_executor_service.py` - Argent réel
3. `position_service.py` - État positions
4. `risk_manager_service.py` - Protections

**🟡 IMPORTANT:**
5. `market_data_service.py` - Prix corrects
6. `llm_prompt_service.py` - Données au LLM
7. `enriched_llm_prompt_service.py` - Parsing réponses

**🟢 SECONDAIRE:**
8. Autres services (logging, indicators, etc.)

### Checklist par Service

**Pour chaque service critique:**
- [ ] Types cohérents (Decimal pour $)
- [ ] Async/await correctement utilisé
- [ ] None checks avant utilisation
- [ ] DB queries: pas de lazy loading en async
- [ ] Logs: erreurs catchées et loggées
- [ ] Rollback: en cas d'erreur DB

### Outils d'Audit Automatisés

```bash
# 1. Type checking
mypy backend/src/services/*.py

# 2. Unused imports
pylint backend/src/services/*.py --disable=all --enable=unused-import

# 3. Complexity
radon cc backend/src/services/ -a -nb

# 4. Security
bandit -r backend/src/
```

## Phase 6: Métriques de Succès Globales

**Après audit complet:**
- ✅ 0 crash en 24h
- ✅ SL/TP triggers > 0
- ✅ Capital drift < $0.01
- ✅ Toutes positions closes en < 4h
- ✅ Tests critiques passent

## Phase 7: Livrable Final

`docs/AUDIT_REPORT.md` avec:
1. Liste bugs trouvés + criticité
2. Fixes appliqués
3. Tests de non-régression
4. Métriques avant/après

**Durée totale:** 5-6h audit + 24h monitoring
**Résultat:** Code audit, bugs critiques fixés, monitoring actif