# Scripts Utilitaires

Ce dossier contient tous les scripts utilitaires pour le projet.

## Structure

```
scripts/
├── tests/              # Scripts de test et diagnostic
├── sql/                # Scripts SQL pour gestion de la DB
└── bot_management/     # Scripts de gestion des bots
```

## Usage

Tous les scripts doivent être exécutés depuis le dossier `backend/`:

```bash
cd backend
source venv/bin/activate
python scripts/tests/test_okx_connection.py
```

## Contenu

### 📊 tests/
Scripts de test et diagnostic de l'API OKX

### 💾 sql/
Scripts SQL pour maintenance de la base de données

### 🤖 bot_management/
Scripts Python pour activer/gérer les bots de trading