# Backend - NOF1 Trading Bot

Backend FastAPI pour le bot de trading automatisé avec IA.

## 🏗️ Structure du Projet

```
backend/
├── src/                    # Code source principal
│   ├── core/              # Composants core (DB, Exchange, LLM)
│   ├── models/            # Modèles SQLAlchemy
│   ├── routes/            # Endpoints API REST
│   ├── services/          # Logique métier
│   └── middleware/        # Middlewares FastAPI
├── scripts/               # Scripts utilitaires
│   ├── tests/            # Scripts de test et diagnostic
│   ├── sql/              # Scripts SQL de maintenance
│   └── bot_management/   # Scripts de gestion des bots
├── alembic/              # Migrations de base de données
├── tests/                # Tests unitaires et d'intégration
├── .env                  # Configuration (ne pas commiter)
└── requirements.txt      # Dépendances Python
```

## 🚀 Démarrage Rapide

### Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Configuration

1. Copiez `.env.example` vers `.env`
2. Configurez les variables d'environnement:
   - Base de données PostgreSQL
   - Redis
   - Clés API (OKX, LLM providers)

### Lancement

```bash
# Développement (avec reload automatique)
uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8020
```

### Accès

- API: http://localhost:8020
- Documentation: http://localhost:8020/docs
- ReDoc: http://localhost:8020/redoc

## 📊 Base de Données

### Migrations

```bash
# Créer une nouvelle migration
alembic revision --autogenerate -m "Description"

# Appliquer les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1
```

### Scripts SQL

Voir [`scripts/sql/README.md`](scripts/sql/README.md) pour les scripts de maintenance.

## 🧪 Tests

### Scripts de Test

```bash
# Test connexion OKX
python scripts/tests/test_okx_connection.py

# Diagnostic clés API
python scripts/tests/diagnose_okx_keys.py

# Test API backend
python scripts/tests/test_api.py
```

Voir [`scripts/tests/README.md`](scripts/tests/README.md) pour plus de détails.

### Tests Unitaires

```bash
pytest tests/
```

## 🤖 Gestion des Bots

```bash
# Activer un bot
python scripts/bot_management/activate_bot_pg.py

# Vérifier le statut
python scripts/bot_management/check_bot_status.py
```

Voir [`scripts/bot_management/README.md`](scripts/bot_management/README.md).

## 🔧 Configuration Exchange

### OKX (Actuel)

Mode Paper Trading (par défaut):
- Utilise l'API publique OKX (gratuit)
- Données réelles du marché
- Trades simulés en base de données
- Aucun risque financier

Mode Live Trading:
- Nécessite des clés API OKX valides
- Passe des ordres réels
- Gère un capital réel

### Symboles

Format automatique:
- `BTC/USDT` → converti en `BTC/USDT:USDT` (perpetual swaps)
- `ETH/USDT` → converti en `ETH/USDT:USDT`

## 📚 Documentation

- [Migration Binance → OKX](../docs/MIGRATION_BINANCE_TO_OKX.md)
- [Résumé de Session](../SESSION_2025-10-24_RESUME.md)
- [Guide de Test](../docs/GUIDE_TEST_SIMPLE.md)

## 🔐 Sécurité

- Ne jamais commiter le fichier `.env`
- Utiliser des clés API en lecture seule quand possible
- Ne jamais activer la permission "Withdraw" sur les clés API
- Tester en paper trading avant le live trading

## 📦 Dépendances Principales

- **FastAPI**: Framework web
- **SQLAlchemy**: ORM
- **PostgreSQL**: Base de données
- **Redis**: Cache et rate limiting
- **CCXT**: API exchange crypto
- **OpenAI/Anthropic/DeepSeek**: LLM providers
- **Alembic**: Migrations DB

## 🐛 Debugging

Logs en temps réel:
```bash
tail -f logs/app.log
```

Variables d'environnement:
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 📞 Support

Pour les problèmes:
1. Vérifier les logs
2. Tester la connexion OKX: `python scripts/tests/test_okx_connection.py`
3. Vérifier la configuration: `.env`
4. Consulter la documentation dans `docs/`

## 🎯 Prochaines Étapes

- [ ] Interface utilisateur améliorée
- [ ] Backtesting automatisé
- [ ] Support multi-exchanges
- [ ] Notifications en temps réel
- [ ] Dashboard analytics avancé
