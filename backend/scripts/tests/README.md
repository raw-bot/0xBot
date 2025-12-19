# Scripts de Test et Diagnostic

Scripts pour tester et diagnostiquer la connexion à l'exchange OKX.

## Scripts Disponibles

### 🔍 test_okx_connection.py
Test basique de connexion à l'API OKX.
- Teste l'API publique (sans authentification)
- Teste le mode démo (avec clés API)
- Affiche le prix BTC actuel

**Usage:**
```bash
cd backend
python scripts/tests/test_okx_connection.py
```

### 🔧 diagnose_okx_keys.py
Diagnostic complet des clés API OKX.
- Vérifie les variables d'environnement
- Teste les clés en mode LIVE
- Teste les clés en mode DEMO
- Fournit des recommandations

**Usage:**
```bash
cd backend
python scripts/tests/diagnose_okx_keys.py
```

### 🧪 test_okx_demo_keys.py
Test spécifique pour les clés API demo.
- Teste différentes configurations
- Analyse les erreurs
- Recommandations pour le mode demo

**Usage:**
```bash
cd backend
python scripts/tests/test_okx_demo_keys.py
```

### 🌐 test_api.py
Test de l'API REST du backend.
- Vérifie les endpoints principaux
- Teste l'authentification
- Valide les réponses

**Usage:**
```bash
cd backend
python scripts/tests/test_api.py
```

## Notes

- Tous les scripts nécessitent que le `venv` soit activé
- Les clés API sont lues depuis le fichier `.env`
- Ces scripts sont **en lecture seule** et ne modifient rien