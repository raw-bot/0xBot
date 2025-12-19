# Fix: Stop Loss et Take Profit Configurables

## Problème Identifié

L'erreur `unsupported operand type(s) for *: 'decimal.Decimal' and 'float'` se produisait dans [`trading_engine_service.py`](../backend/src/services/trading_engine_service.py:327) lors du calcul des valeurs par défaut de stop loss et take profit.

De plus, les valeurs de stop loss (3.5%) et take profit (7%) étaient codées en dur dans le code au lieu d'être configurables via les paramètres du bot.

## Solution Implémentée (avec Fallback Values)

### 1. Fix du bug Decimal × float

**Fichier**: [`backend/src/services/trading_engine_service.py`](../backend/src/services/trading_engine_service.py:323)

Le code utilise maintenant `Decimal` pour toutes les opérations arithmétiques:

```python
# Get SL/TP from bot's risk_params with fallback values
stop_loss_pct = current_bot.risk_params.get("stop_loss_pct", 0.035)  # 3.5% default
take_profit_pct = current_bot.risk_params.get("take_profit_pct", 0.07)  # 7% default

# Calculate default stop loss and take profit prices
default_sl = current_price * (Decimal("1") - Decimal(str(stop_loss_pct))) if current_price > 0 else None
default_tp = current_price * (Decimal("1") + Decimal(str(take_profit_pct))) if current_price > 0 else None
```

### 2. Paramètres configurables avec fallbacks

**Fichier**: [`backend/src/models/bot.py`](../backend/src/models/bot.py:76)

Les nouveaux bots ont ces valeurs par défaut dans `risk_params`:

```python
risk_params: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=lambda: {
        "max_position_pct": 0.10,
        "max_drawdown_pct": 0.20,
        "max_trades_per_day": 10,
        "stop_loss_pct": 0.035,      # 3.5% stop loss
        "take_profit_pct": 0.07       # 7% take profit
    }
)
```

### 3. Migration OPTIONNELLE

**Pas besoin de migration urgente !** Le code utilise des fallback values.

Si vous voulez explicitement définir les valeurs dans la base de données:

**Option 1: Via Alembic**
```bash
cd backend
alembic upgrade head
```

**Option 2: Via Script SQL**
```bash
psql -d your_database -f backend/scripts/sql/update_risk_params_defaults.sql
```

## Avantages de cette Approche

1. ✅ **Fix immédiat**: Bug Decimal/float résolu
2. ✅ **Pas de migration urgente**: Fallback values = compatible avec bots existants
3. ✅ **Configurabilité**: Les valeurs SL/TP peuvent être personnalisées par bot
4. ✅ **Robustesse**: Fonctionne même si `risk_params` manque les nouvelles clés
5. ✅ **Flexibilité**: Migration peut être appliquée plus tard sans urgence

## Utilisation

### Pour un nouveau bot avec valeurs personnalisées

```python
bot = Bot(
    name="My Trading Bot",
    risk_params={
        "max_position_pct": 0.10,
        "max_drawdown_pct": 0.20,
        "max_trades_per_day": 10,
        "stop_loss_pct": 0.05,    # 5% stop loss personnalisé
        "take_profit_pct": 0.10   # 10% take profit personnalisé
    }
)
```

### Pour modifier un bot existant

```python
bot.risk_params["stop_loss_pct"] = 0.04  # 4%
bot.risk_params["take_profit_pct"] = 0.08  # 8%
await db.commit()
```

### Pour un bot existant sans ces paramètres

Le code utilise automatiquement les fallbacks (3.5% et 7%), donc **aucune action requise**.

## Tests

Après application de la migration, vérifier que:
1. Le bot démarre sans erreur de type `Decimal` * `float`
2. Les positions créées utilisent les valeurs SL/TP configurées
3. Les bots existants ont bien les nouvelles valeurs par défaut dans leurs `risk_params`

## Date

2025-10-26