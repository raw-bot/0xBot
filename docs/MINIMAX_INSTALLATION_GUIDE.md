# Guide d'installation MiniMax-M2 pour VSCode

## 🚀 Installation et Configuration pour votre projet de Trading

### Étape 1 : Installation de l'extension MiniMax

1. **Ouvrir VSCode**
2. Aller dans l'onglet Extensions (`Cmd+Shift+X`)
3. Rechercher "MiniMax"
4. Installer l'extension officielle **"MiniMax AI"** (par MiniMax)
5. **Redémarrer VSCode**

### Étape 2 : Configuration de votre compte

1. **Créer un compte MiniMax** :
   - Aller sur https://platform.minimaxi.com/
   - Créer un compte gratuit
   - Récupérer votre API key

2. **Configurer dans VSCode** :
   - `Cmd+Shift+P` (Palette de commandes)
   - Taper "MiniMax: Set API Key"
   - Coller votre API key

### Étape 3 : Configuration optimale pour votre projet

#### Settings recommandés (`.vscode/settings.json`) :

```json
{
    "minimax.maxTokens": 4000,
    "minimax.temperature": 0.3,
    "minimax.contextWindow": "large",
    "minimax.autoSuggest": true,
    "minimax.inlineSuggest": true
}
```

#### Extensions complémentaires recommandées :

1. **GitLens** - Visualisation commits avec IA
2. **Error Lens** - Affichage erreurs inline
3. **Auto Rename Tag** - Gestion tags HTML/JSX
4. **Git Graph** - Visualisation branches
5. **Thunder Client** - Tests API (essentiel pour votre projet)

### Étape 4 : Configuration spécifique Trading

#### Extensions financières :

1. **Python**
   - Vérifier que l'interpréteur Python 3.11 est sélectionné
   - Installer `Python` de Microsoft (officielle)

2. **Prettier** - Formatage code automatique
3. **ESLint** - Linting pour TypeScript/JavaScript

### Étape 5 : Configuration workspace pour votre projet

#### `.vscode/launch.json` (Debugging Python) :

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI Backend",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/src/main.py",
            "args": [],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}/backend",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend/src"
            }
        }
    ]
}
```

#### `.vscode/tasks.json` (Tasks projet) :

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Install Backend Dependencies",
            "type": "shell",
            "command": "cd",
            "args": ["${workspaceFolder}/backend", "&&", "pip", "install", "-r", "requirements.txt"],
            "group": "build"
        },
        {
            "label": "Start Backend",
            "type": "shell",
            "command": "cd",
            "args": ["${workspaceFolder}/backend", "&&", "uvicorn", "src.main:app", "--reload"],
            "group": "build",
            "dependsOn": "Install Backend Dependencies"
        },
        {
            "label": "Start Frontend",
            "type": "shell",
            "command": "cd",
            "args": ["${workspaceFolder}/frontend", "&&", "npm", "run", "dev"],
            "group": "build"
        }
    ]
}
```

### Étape 6 : Intégration IA pour votre projet

#### Configuration MiniMax pour développement :

1. **Context Project** :
   - Créer un `.vscode/minimax-config.json` :
   ```json
   {
       "projectType": "trading-bot",
       "language": ["python", "typescript", "react"],
       "frameworks": ["fastapi", "sqlalchemy", "react", "tailwind"],
       "apis": ["ccxt", "okx", "binance"],
       "contextFiles": [
           "backend/src/**/*.py",
           "frontend/src/**/*.tsx",
           "docs/**/*.md"
       ]
   }
   ```

#### Prompts recommandés pour MiniMax :

**Pour développement backend** :
```
Tu assistes un développeur sur un projet de trading algorithmique.
Stack: FastAPI + SQLAlchemy + PostgreSQL + Redis + CCXT.
Architecture microservice, code asynchrone, tests unitaires rigoureux.
Règles: 1) Priorité sécurité financière, 2) Code testable, 3) Logging exhaustif, 4) Documentation claire.
```

**Pour développement frontend** :
```
Tu assistes un développeur sur l'interface d'un bot de trading.
Stack: React + TypeScript + TailwindCSS + Zustand.
État global, composants réutilisables, UX intuitive pour traders.
Règles: 1) Données temps réel, 2) Performance, 3) Responsive, 4) UX fluide.
```

### Étape 7 : Raccourcis clavier essentiels

- `Cmd+L` - Chat IA contextuel
- `Cmd+K Cmd+L` - Assistant inline
- `Cmd+Shift+L` - Code actions IA
- `F5` - Debugger Python
- `Cmd+Shift+B` - Run tasks

### Étape 8 : Bonnes pratiques avec MiniMax

#### ✅ À faire :
- Donner le contexte du projet au début
- Spécifier le langage/framework
- Mentionner les contraintes (tests, sécurité)
- Demander du code avec documentation

#### ❌ À éviter :
- Informations sensibles (clés API)
- Modifications code critique sans tests
- Déploiements directement en prod

### Étape 9 : Workflow recommandé

1. **Analyse** : Demander à MiniMax d'analyser le code existant
2. **Planification** : Stratégie de modification/refactoring
3. **Implémentation** : Code en petites itérations
4. **Tests** : Vérification systématique
5. **Documentation** : Mise à jour des commentaires

### Étape 10 : Monitoring et métriques

#### Dashboard MiniMax dans VSCode :
- Suivi des conversations
- Statistiques d'utilisation
- Historique des prompts

#### Intégration Git :
- Messages de commit avec assistance IA
- Reviews automatisés
- Documentation mise à jour

---

## 🎯 Configuration spécifique Trading

Pour votre projet de trading, attention particulière à :

### Sécurité
- **Jamais** de clés API dans les prompts
- Utiliser variables d'environnement
- Tests sur données de démo uniquement

### Performance
- Optimisations avec IA assistance
- Profilage code sensible
- Monitoring performance

### Debug
- Logging détaillé requis
- Tests unitaires exhaustifs
- Simulation stratégies

---

**🎉 Installation terminée !**

Votre environnement VSCode + MiniMax-M2 est maintenant configuré pour optimiser le développement de votre projet de trading automatisé.