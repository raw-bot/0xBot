# Fix: Le capital du bot change maintenant après chaque trade

## 🐛 Problème résolu

Avant ce fix, le capital du bot restait fixe même après des trades. Le bot pouvait acheter et vendre mais son capital affiché ne changeait jamais.

## ✅ Solution implémentée

### 1. Nouveau champ `initial_capital`

Le modèle [`Bot`](../backend/src/models/bot.py:39) a maintenant deux champs:
- **`initial_capital`**: Le capital de départ (ne change jamais sauf si l'utilisateur ajoute/retire des fonds)
- **`capital`**: Le capital disponible actuel qui change après chaque trade

### 2. Mise à jour automatique du capital

**Lors d'un achat** ([`execute_entry`](../backend/src/services/trade_executor_service.py:40)):
```python
cost = actual_price * quantity + fees
bot.capital -= cost  # Débite le capital
```

**Lors d'une vente** ([`execute_exit`](../backend/src/services/trade_executor_service.py:157)):
```python
proceeds = actual_price * quantity - fees
bot.capital += proceeds  # Crédite le capital
```

### 3. Calcul correct de la performance

Le return % est maintenant calculé sur le capital initial:
```python
return_pct = ((bot.capital - bot.initial_capital) / bot.initial_capital) * 100
```

## 🔧 Comment appliquer la migration

### Option 1: Via Docker/psql (RECOMMANDÉ)

```bash
# Se connecter à PostgreSQL
docker exec -it trading_agent_postgres psql -U trading_agent -d trading_agent_db

# Exécuter la migration
\i /path/to/backend/scripts/sql/add_initial_capital.sql

# Vérifier que ça a marché
SELECT id, name, initial_capital, capital FROM bots;
\q
```

### Option 2: Via script Python

Si vous avez accès au virtualenv:

```bash
cd backend
source venv/bin/activate

# Appliquer la migration SQL directement
python -c "
from src.core.database import engine
import asyncio
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text('''
            ALTER TABLE bots ADD COLUMN IF NOT EXISTS initial_capital NUMERIC(20, 2);
            UPDATE bots SET initial_capital = capital WHERE initial_capital IS NULL;
            ALTER TABLE bots ALTER COLUMN initial_capital SET NOT NULL;
        '''))
    print('✅ Migration appliquée!')

asyncio.run(migrate())
"
```

### Option 3: Copier le script SQL et l'exécuter manuellement

Le contenu du script [`add_initial_capital.sql`](../backend/scripts/sql/add_initial_capital.sql:1) est:

```sql
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='bots' AND column_name='initial_capital'
    ) THEN
        ALTER TABLE bots ADD COLUMN initial_capital NUMERIC(20, 2);
        UPDATE bots SET initial_capital = capital;
        ALTER TABLE bots ALTER COLUMN initial_capital SET NOT NULL;
        RAISE NOTICE 'Colonne initial_capital ajoutée avec succès';
    ELSE
        RAISE NOTICE 'Colonne initial_capital existe déjà';
    END IF;
END $$;
```

## 📊 Exemple de comportement

**Avant le fix:**
```
Initial capital: $10,000
After buying BTC: $10,000 (❌ pas de changement)
After selling BTC: $10,000 (❌ pas de changement)
```

**Après le fix:**
```
Initial capital: $10,000
Current capital: $10,000
After buying 0.1 BTC @ $50,000: $5,000 (✅ -$5,000)
After selling 0.1 BTC @ $51,000: $10,100 (✅ +$5,100, profit de $100)
Return: +1.00% (calculé sur initial_capital)
```

## 🔍 Fichiers modifiés

1. **Modèle** - [`backend/src/models/bot.py`](../backend/src/models/bot.py:66)
   - Ajout du champ `initial_capital`
   - Mise à jour de `portfolio_value` et `return_pct`

2. **Trade Executor** - [`backend/src/services/trade_executor_service.py`](../backend/src/services/trade_executor_service.py:21)
   - `execute_entry`: Débite le capital lors d'un achat
   - `execute_exit`: Crédite le capital lors d'une vente

3. **Trading Engine** - [`backend/src/services/trading_engine_service.py`](../backend/src/services/trading_engine_service.py:28)
   - Affichage du capital mis à jour
   - Calcul du return % basé sur `initial_capital`

4. **Bot Service** - [`backend/src/services/bot_service.py`](../backend/src/services/bot_service.py:53)
   - Initialisation de `initial_capital` à la création
   - Mise à jour des deux champs lors de modification manuelle

5. **Migration** - [`backend/alembic/versions/c5d8e9f1a2b3_add_initial_capital_to_bot.py`](../backend/alembic/versions/c5d8e9f1a2b3_add_initial_capital_to_bot.py:1)
   - Migration Alembic pour ajouter la colonne

## 🧪 Comment tester

1. Appliquer la migration
2. Redémarrer le bot avec `./start.sh`
3. Laisser le bot faire un trade
4. Observer que le capital change maintenant dans les logs:

```
💰 Capital: $9,500.00 | Initial: $10,000.00 | Return: -5.00%
✅ BUY 0.1000 BTC @ $50,000.00 ($5,000.00)
💰 Capital: $4,500.00 | Initial: $10,000.00 | Return: -55.00%
```

## ⚠️ Notes importantes

- **Bots existants**: Leur `initial_capital` sera initialisé avec la valeur actuelle de `capital`
- **Ajout de fonds**: Si vous modifiez manuellement le capital d'un bot, `initial_capital` sera aussi mis à jour
- **Paper trading**: Le fix fonctionne aussi en mode paper trading
- **Rollback**: Si besoin, la colonne peut être supprimée avec `ALTER TABLE bots DROP COLUMN initial_capital`

## 📝 Logs améliorés

Les logs montrent maintenant clairement l'évolution du capital:

```
Entry executed: Position 123, Trade 456, Capital: $9,500.00
Exit executed: Position 123, PnL: +$100.00, Capital: $10,100.00