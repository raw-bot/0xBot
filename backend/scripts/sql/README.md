# Scripts SQL

Scripts SQL pour la maintenance et la gestion de la base de données PostgreSQL.

## Scripts Disponibles

### ⚙️ activate_bot.sql
Active un bot dans la base de données.
- Met le statut à 'active'
- Configure les paramètres de trading

**Usage:**
```bash
psql -U postgres -d trading_agent -f scripts/sql/activate_bot.sql
```

### 🔧 fix_quota.sql
Corrige les quotas LLM des bots.
- Réinitialise les compteurs de requêtes
- Met à jour les limites

**Usage:**
```bash
psql -U postgres -d trading_agent -f scripts/sql/fix_quota.sql
```

### 📊 update_bot_quota.sql
Met à jour les quotas d'un bot spécifique.
- Modifie les limites de requêtes LLM
- Ajuste les paramètres de trading

**Usage:**
```bash
psql -U postgres -d trading_agent -f scripts/sql/update_bot_quota.sql
```

### 🔄 reset_trades_today.sql
Réinitialise le compteur de trades du jour.
- Affiche les trades d'aujourd'hui (ENTRY vs EXIT)
- Permet de nettoyer les EXIT trades mal comptés
- Utile après le fix du bug de comptage

**Usage:**
```bash
psql -U postgres -d trading_agent -f scripts/sql/reset_trades_today.sql
```

## Notes

- Tous les scripts nécessitent une connexion à la base de données
- Modifier les valeurs dans les scripts avant exécution
- Faire une sauvegarde avant de modifier la base
- Vérifier les résultats après exécution

## Connexion à la DB

```bash
# Via psql
psql -U postgres -d trading_agent

# Via Python
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_agent