# Journal des modifications - Projet NOF1

## 2025-10-26 - Initialisation du dépôt Git

### Fichiers créés
- `.gitignore` : Configuration pour exclure les fichiers temporaires, dépendances, et logs
  - Exclusion de venv/, node_modules/, __pycache__, *.db, *.log, etc.

### Actions Git
- Initialisation du dépôt git local
- Commit initial : **6374424** - "Sauvegarde initiale du projet NOF1 - Trading Bot avec AI"
- 117 fichiers ajoutés, 23 962 lignes de code

### Contenu sauvegardé
- Backend Python (FastAPI, services de trading, modèles)
- Frontend React (TypeScript, Vite)
- Documentation (corrections/, docs/, specs/)
- Scripts de déploiement et configuration
- Migrations Alembic

### Statut
✅ Dépôt git initialisé et sauvegarde complète effectuée
✅ Working tree propre, aucune modification en attente

---

## 2025-10-26 - Correction Bug Equity (Priorité Critique)

### Problème identifié
- **Bug** : Les prix des positions (`current_price`) n'étaient JAMAIS mis à jour pendant le cycle de trading
- **Impact** : L'equity restait figée et ne reflétait pas la valeur réelle du portefeuille en temps réel
- **Symptôme** : Equity changeait de seulement $0.17 sur plusieurs heures malgré des positions avec PnL

### Correction appliquée

**Fichier modifié** : `backend/src/services/trading_engine_service.py`

**Ligne 172-173** : Ajout de l'appel à `_update_position_prices()` au début du cycle de trading

```python
# 0. Update position prices FIRST to get accurate equity
await self._update_position_prices()
```

**Avant** : La fonction `_update_position_prices()` existait (ligne 533) mais n'était jamais appelée
**Après** : Elle est maintenant appelée AVANT de récupérer le portfolio state, garantissant des prix à jour

### Résultat attendu
- ✅ Equity sera mise à jour en temps réel à chaque cycle
- ✅ Les PnL non réalisés seront visibles immédiatement
- ✅ Vision précise de la performance du portefeuille

### Prochaine étape
🧪 Phase de test pour valider que l'equity bouge correctement

---

## 2025-10-26 - Correction Bug Capital (Problème de synchronisation)

### Problème identifié
- **Bug** : Utilisation de `db.merge(bot)` qui ne garantissait pas d'avoir le capital le plus récent depuis la DB
- **Impact** : Risque de race condition et de calculs incorrects sur le capital lors de trades multiples
- **Localisation** : `trade_executor_service.py` dans les fonctions `execute_entry()` et `execute_exit()`

### Corrections appliquées

**Fichier modifié** : `backend/src/services/trade_executor_service.py`

**1. Fonction `execute_entry()` (lignes 143-147)** :
```python
# CRITICAL: Reload bot from DB to get latest capital BEFORE modifying
from sqlalchemy import select
query = select(Bot).where(Bot.id == bot.id)
result = await self.db.execute(query)
bot = result.scalar_one()
```

**2. Fonction `execute_exit()` (lignes 238-242)** :
```python
# CRITICAL: Reload bot from DB to get latest capital BEFORE modifying
from sqlalchemy import select
query = select(Bot).where(Bot.id == position.bot_id)
result = await self.db.execute(query)
bot = result.scalar_one()
```

**Avant** : Utilisait `bot = await self.db.merge(bot)` (ne garantit pas la fraîcheur des données)
**Après** : Recharge explicitement le bot depuis la DB avec un SELECT (garantit d'avoir le capital le plus récent)

### Avantages
- ✅ Garantit que le capital utilisé est toujours à jour
- ✅ Évite les race conditions lors de trades multiples
- ✅ Évite la confusion en gardant le nom de variable `bot` (pas de `fresh_bot`)

### Note
Les warnings du linter concernant les imports sqlalchemy sont normaux et n'affectent pas le fonctionnement.

---

## 2025-10-26 - Amélioration des Logs (Lisibilité et Clarté)

### Problème identifié
- **Logs trop verbeux** : Noms de modules longs (trading_engine_service, httpx, etc.)
- **Pollution** : Messages répétitifs (Fetching, Created, HTTP Request, etc.)
- **Manque de clarté** : Difficile de suivre l'activité du bot

### Améliorations appliquées

**Fichier modifié** : `backend/src/core/logger.py`

**1. Format simplifié (lignes 130-169)** :
- ✅ Timestamp simplifié (HH:MM:SS sans millisecondes)
- ✅ Noms de modules supprimés pour les logs INFO/DEBUG
- ✅ Noms de modules abrégés avec emojis pour WARNING/ERROR :
  - `trading_engine_service` → 🤖 BOT
  - `trade_executor_service` → 💰 TRADE
  - `market_data_service` → 📊 DATA
  - `market_analysis_service` → 📈 ANALYSIS
  - `llm_prompt_service` → 🧠 LLM
  - `position_service` → 📍 POSITION
  - `risk_manager_service` → ⚠️  RISK

**2. Filtre anti-bruit (lignes 207-244)** :
Classe `NoiseFilter` qui supprime les messages contenant :
- "Fetching"
- "Created order"
- "HTTP Request:"
- "HTTP Response:"
- Messages de connexion DB

**3. Loggers bruyants réduits au silence (lignes 339-347)** :
- httpx, httpcore, urllib3 → WARNING only
- asyncio → WARNING only
- sqlalchemy.engine, sqlalchemy.pool → WARNING only

### Résultat attendu

**Avant** :
```
12:34:56.789 | trading_engine_service | 📊 Analyzing BTC/USDT
12:34:56.892 | httpx                  | HTTP Request: GET https://...
12:34:57.123 | market_data_service   | Fetching candles for BTC/USDT
```

**Après** :
```
12:34:56 | 📊 Analyzing BTC/USDT
12:34:57 | 💰 Entry executed: Position 123, Trade 456, Capital: $1,200.00
12:35:12 | 🤖 BOT | ⚠️  Trading cycle error: ...
```

Logs plus compacts, lisibles et avec seulement les informations essentielles ! ✨

---

## 2025-10-26 - Phase 2 : Corrections Bot Trop Conservateur

### Problèmes identifiés
- **Bot refuse de trader** : 0 positions sur 160 cycles, confiance 30-50%
- **Contradictions Market Regime** : RISK_ON déclaré avec breadth négatif
- **Paramètres trop stricts** : SL 2%, seuils confiance 60%+, R/R 1.5:1 min
- **Capital sous-utilisé** : 27% au lieu de 80% disponible

### Corrections appliquées

#### 🔴 Correction 1 : Market Regime (`market_analysis_service.py`, lignes 183-215)

**Problème** : Critères trop laxistes créant des contradictions

**Modifications** :
- Corrélation RISK_ON : `< 0.5` → `< 0.6` (plus strict)
- Performance alts : `> btc` → `> btc + 0.01` (doivent VRAIMENT surperformer)
- Volatilité RISK_ON : `< threshold` → `< threshold * 0.8` (vraiment basse)
- Volatilité RISK_OFF : `> threshold` → `> threshold * 1.2` (vraiment haute)
- Détermination régime : Exige 3/3 critères pour confiance 100%, 2/3 pour 67%

**Résultat attendu** : Fini les contradictions "RISK_ON avec breadth négatif"

#### 🔴 Correction 2 : Prompt LLM (`llm_prompt_service.py`)

**2.1 - Paramètres par défaut (lignes 125-135)** :
- Stop Loss : `2%` → `3.5%` (donne respiration pour volatilité normale)
- Take Profit : `4%` → `7%` (vise gains significatifs, maintient R/R 2:1)
- Position : Reste à 10% par défaut, ajustable 6-15% selon conviction

**2.2 - Seuils de confiance (lignes 167-171)** :
```
AVANT : 0-0.4 (no trade), 0.4-0.6 (small), 0.6-0.8 (standard)
APRÈS : 0-0.35 (no trade), 0.35-0.50 (small), 0.50-0.70 (standard), 0.70-1.0 (high)
```
✅ Accepte maintenant les trades à 50-60% de confiance (au lieu de 60%+)

**2.3 - Section HOLD (lignes 178-185)** :
- Ajout : "If you see a setup with 0.5+ confidence and 3+ confluence factors, you SHOULD take it!"
- Message : "50-60% confidence trade with proper risk management is VALID"
- ❌ Supprimé : "Do NOT enter just to do something" (trop défaitiste)

**2.4 - Section EXIT (lignes 194-202)** :
- RSI overbought : `>75` → `>78` (moins sensible)
- RSI oversold : `<25` → `<22`
- Position stale : `>2h` → `>4h` (plus de patience)
- Condition : "AND original thesis clearly invalidated" (pas juste temps)

**2.5 - Multi-Timeframe (lignes 97-111)** :
- 🎯 Emphase sur 1H comme filtre PRINCIPAL de direction
- 📍 5min UNIQUEMENT pour timing d'entrée (pas décision de direction)
- Clarification : "DO NOT fight the 1H trend!"

#### 🔴 Correction 3 : Contraintes Risque (`risk_manager_service.py`)

**3.1 - Max position** (ligne 42) : `10%` → `15%`

**3.2 - Max exposure** (ligne 52) : `80%` → `85%` du capital

**3.3 - Risk/Reward minimum** (ligne 73) : `1.5:1` → `1.3:1`

**3.4 - Position minimum** (ligne 77) : `$10` → `$50` (trades plus significatifs)

#### ✅ Correction 4 : Cycle de trading

**Statut** : Déjà aligné sur 5 minutes (300s) - Aucune modification nécessaire

### Résultats attendus

| Métrique | Avant | Après (Cible) |
|----------|-------|---------------|
| Trades/jour | 0-2 | 3-8 |
| Capital utilisé | 27% | 50-70% |
| Confidences LLM | 30-50% | 50-70% |
| PnL moyen/trade | $0.05 | $5-15 |
| Taux d'action | <1% cycles | 5-10% cycles |

### Fichiers modifiés
1. ✅ `backend/src/services/market_analysis_service.py` (1 fonction)
2. ✅ `backend/src/services/llm_prompt_service.py` (5 sections)
3. ✅ `backend/src/services/risk_manager_service.py` (4 contraintes)

### Prochaine étape
🧪 **Tests en paper trading** pendant 24-48h pour valider les améliorations

---

## 2025-10-26 - Phase 3 : Optimisations et Métriques de Performance

### Amélioration appliquée

#### 🔵 Métriques de Performance Horaires (`trading_engine_service.py`)

**Problème** : Manque de visibilité sur la performance du bot au cours de la journée

**Modifications** :

**1. Tracking de performance (lignes 75-77)** :
```python
self.cycle_count = 0  # Compteur de cycles
self.session_start = datetime.utcnow()  # Début de session
```

**2. Incrément du compteur (ligne 304-305)** :
- Chaque cycle incrémente le compteur

**3. Résumé horaire automatique (lignes 311-313)** :
- Toutes les 12 cycles (= 1 heure avec cycles de 5 min)
- Appel à `_log_hourly_summary()`

**4. Fonction de résumé (lignes 559-598)** :
Affiche un tableau récapitulatif contenant :
- ⏱️  Session Time & nombre de cycles
- 💰 Equity actuelle vs initiale
- 📈 Return % (coloré vert/rouge)
- 💵 Unrealized PnL (coloré vert/rouge)
- 📍 Nombre de positions ouvertes
- 🎯 Nombre de trades aujourd'hui
- 📊 Utilisation du capital (%)

**Exemple de sortie** :
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         📊 HOURLY SUMMARY                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ⏱️  Session Time: 2.0h | Cycles: 24                                         ║
╠──────────────────────────────────────────────────────────────────────────────╣
║  💰 Equity: $1,250.50 | Initial: $1,000.00                                   ║
║  📈 Return: +25.05%                                                          ║
║  💵 Unrealized PnL: +$15.30                                                  ║
╠──────────────────────────────────────────────────────────────────────────────╣
║  📍 Open Positions: 2                                                        ║
║  🎯 Trades Today: 5                                                          ║
║  📊 Capital Utilization: 65.2%                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Résultat attendu
- ✅ Visibilité claire sur la performance chaque heure
- ✅ Suivi du taux d'activité (trades/heure)
- ✅ Monitoring de l'utilisation du capital
- ✅ Tableau formaté avec couleurs pour lecture rapide

### Phase 3 complète
1. ✅ Multi-timeframe renforcé (fait en Phase 2)
2. ✅ Métriques de performance horaires (fait)
3. 🧪 Tests longs 24-48h (en cours)

---

## 2025-10-26 - Script de Réinitialisation pour Tests

### Nouveau script créé

**Fichier** : `backend/scripts/sql/reset_bot_for_testing.sql`

**Fonctionnalités** :
1. ✅ Réinitialise le capital à $10,000.00
2. ✅ Réinitialise le capital initial à $10,000.00
3. ✅ Reset le total_pnl à $0.00
4. ✅ Supprime tous les trades d'aujourd'hui (reset compteur)
5. ✅ Ferme toutes les positions ouvertes
6. ✅ Affiche l'état avant/après avec formatage clair

### Comment l'utiliser

**Commande unique** :
```bash
cd /Users/cube/Documents/00-code/nof1
sqlite3 backend/database.db < backend/scripts/sql/reset_bot_for_testing.sql
```

**Ce que fait le script** :
- Affiche l'état actuel du bot (capital, trades, positions)
- Réinitialise le capital à $10,000
- Supprime les trades d'aujourd'hui
- Ferme les positions ouvertes
- Affiche l'état final

**Sortie attendue** :
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ÉTAT AVANT MODIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: 0xBot | Actif | $1,200.00 → $10,000.00
📈 Trades: 5 entrées, 3 sorties

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ÉTAT APRÈS MODIFICATION  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: 0xBot | Actif | $10,000.00
📈 Trades: 0 | Positions: 0
🎉 Réinitialisation terminée !
```

### ⚠️ Important
- **Arrêtez le bot** avant d'exécuter le script
- Ce script est **sans danger** (utilise une transaction)
- Toutes les données historiques sont **préservées** (sauf trades d'aujourd'hui)
- Parfait pour recommencer des tests proprement

---

## 2025-10-26 - Script de Création de Bot

### Problème résolu : Base de données vide

La base de données était vide (0 bytes), donc le script SQL ne pouvait pas fonctionner.

### Nouveau script Python créé

**Fichier** : `backend/scripts/create_test_bot.py`

**Fonctionnalités** :
1. ✅ Crée un nouveau bot avec capital $10,000
2. ✅ Configure automatiquement les paramètres optimisés (Phase 2)
3. ✅ Détecte si un bot existe déjà et propose de le réinitialiser
4. ✅ Mode paper trading activé par défaut
5. ✅ Symboles par défaut : BTC/USDT, ETH/USDT, SOL/USDT

### Comment l'utiliser

**Commande unique** :
```bash
cd /Users/cube/Documents/00-code/nof1/backend
source venv/bin/activate
python scripts/create_test_bot.py
```

**Configuration du bot créé** :
- 💰 Capital Initial : $10,000.00
- 💰 Capital Actuel : $10,000.00  
- 📊 Paper Trading : Activé
- 🎯 Modèle LLM : qwen-max
- 📈 Symboles : BTC/USDT, ETH/USDT, SOL/USDT
- ⚙️  Paramètres de risque optimisés :
  - Max position : 15%
  - Max exposure : 85%
  - Stop Loss : 3.5%
  - Take Profit : 7%

### Si un bot existe déjà

Le script détectera automatiquement le bot existant et vous proposera de le réinitialiser à $10,000.

---

## 2025-10-26 - Standardisation du nom du bot

### Changement appliqué

**Nom standardisé** : **"0xBot"**

### Fichiers modifiés

1. ✅ `backend/scripts/create_test_bot.py` (ligne 63)
   - "AI Trading Bot - Test" → "0xBot"

2. ✅ `backend/scripts/tests/test_api.py` (ligne 107)
   - "Test Bot Qwen" → "0xBot"

3. ✅ `corrections/reset_bot.md` (ligne 282)
   - "AI Trading Bot - Test" → "0xBot"

### Résultat

Le bot sera maintenant créé avec le nom **"0xBot"** de manière cohérente dans tout le projet. 🚀

---

## 2025-10-26 - Guide de Gestion du Bot et Script Reset

### Documentation créée

**Fichier** : `corrections/guide-gestion-bot.md`

Guide complet expliquant les deux solutions complémentaires pour gérer le bot :
1. ✅ **reset.sh** - Reset rapide pour tests quotidiens
2. ✅ **create_test_bot.py** - Nouveau bot propre pour fresh start (avec auto-config)

### Nouveau script créé

**Fichier** : `backend/scripts/reset.sh`

**Fonctionnalités** :
1. ✅ Réinitialise un bot existant rapidement
2. ✅ Supprime toutes les positions du bot
3. ✅ Supprime tous les trades du bot
4. ✅ Reset le capital à une valeur donnée (défaut $10,000)
5. ✅ Reset le total_pnl à $0.00
6. ✅ Adapté pour **PostgreSQL** (pas SQLite)
7. ✅ Confirmation avant exécution (sécurité)
8. ✅ Output formaté avec couleurs et émojis

### Adaptation PostgreSQL

Le script a été adapté pour fonctionner avec **PostgreSQL** au lieu de SQLite :
- Utilise `psql` au lieu de `sqlite3`
- Variables d'environnement pour connexion DB
- Support des credentials PostgreSQL
- Commandes SQL adaptées (`NOW()` au lieu de `datetime('now')`)

### Comment l'utiliser

**Reset avec capital par défaut ($10,000)** :
```bash
cd backend/scripts
./reset.sh <bot-id>
```

**Reset avec capital personnalisé** :
```bash
cd backend/scripts
./reset.sh <bot-id> 5000
```

### Exemple de sortie

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 RESET BOT DE TRADING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Bot ID: bot-abc123
   Capital: $10000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confirmer la réinitialisation? (o/N): o
🗑️  Suppression des positions...
🗑️  Suppression des trades...
💰 Réinitialisation du capital...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Bot réinitialisé avec succès!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Capital: $10000
   Positions: 0
   Trades: 0
   PnL: $0.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Vous pouvez relancer le bot avec: ./start.sh
```

### Quand utiliser quoi ?

| Situation | Script à utiliser |
|-----------|------------------|
| Test quotidien rapide | `reset.sh` |
| DB vide (0 bytes) | `create_test_bot.py` |
| Cache mémoire persistant | `create_test_bot.py` |
| Après corrections majeures | `create_test_bot.py` |
| Garder historique | `reset.sh` |

### ⚠️ Important

- **Arrêtez le bot** avant d'exécuter ces scripts
- Les deux scripts sont **complémentaires**, pas concurrents
- `reset.sh` garde l'historique, `create_test_bot.py` crée un nouveau bot from scratch

---

## 2025-10-26 - Auto-Configuration du Bot ID

### Amélioration appliquée

**Problème** : Après avoir créé un bot, l'utilisateur devait manuellement copier-coller le bot ID dans `.env.dev`

**Solution** : Configuration automatique du bot ID

### Fichier modifié

**Fichier** : `backend/scripts/create_test_bot.py`

**Fonctionnalités ajoutées** :

1. ✅ **Fonction `save_bot_id_to_env()`** (lignes 19-79)
   - Sauvegarde automatiquement le bot ID dans `.env.dev`
   - Crée le fichier `.env.dev` s'il n'existe pas
   - Met à jour `AUTO_START_BOT_ID` si déjà présent
   - Gestion d'erreurs robuste

2. ✅ **Appel automatique après création/reset** 
   - Après création d'un nouveau bot (ligne 167)
   - Après réinitialisation d'un bot existant (ligne 119)

### Comportement

**Si `.env.dev` existe** :
- Cherche la ligne `AUTO_START_BOT_ID=`
- Met à jour la valeur avec le nouveau bot ID
- Préserve tout le reste du fichier

**Si `.env.dev` n'existe pas** :
- Crée le fichier avec une structure de base
- Ajoute les placeholders pour `DEV_EMAIL` et `DEV_PASSWORD`
- Ajoute automatiquement `AUTO_START_BOT_ID=<bot-id>`

### Exemple de sortie

```
✅ Bot créé avec succès!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ID: d8f9e1a2-3b4c-5d6e-7f8g-9h0i1j2k3l4m
   Nom: 0xBot
   ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Bot ID sauvegardé dans .env.dev

🚀 Vous pouvez maintenant démarrer le bot avec: ./start.sh
```

### Résultat

✅ **Plus besoin de copier-coller le bot ID manuellement**
✅ **Workflow complètement automatisé**
✅ **Simple et facile à debugger**

### Workflow simplifié

**Avant** :
```bash
python scripts/create_test_bot.py
# Copier le bot ID affiché
# Ouvrir .env.dev
# Coller AUTO_START_BOT_ID=<bot-id>
./dev.sh
```

**Après** :
```bash
python scripts/create_test_bot.py
./dev.sh  # Le bot ID est déjà configuré !
```

