# Contributing to 0xBot

Merci de votre intérêt pour contribuer à 0xBot ! 🎉

## 🚀 Comment Contribuer

### 1. Reporter un Bug

Si vous trouvez un bug, veuillez ouvrir une [Issue](../../issues) avec :
- Une description claire du problème
- Les étapes pour reproduire le bug
- Votre environnement (OS, Python version, etc.)
- Les logs pertinents

### 2. Proposer une Fonctionnalité

Pour proposer une nouvelle fonctionnalité :
1. Ouvrez une [Issue](../../issues) avec le tag "enhancement"
2. Décrivez clairement la fonctionnalité souhaitée
3. Expliquez pourquoi elle serait utile
4. Si possible, proposez une implémentation

### 3. Soumettre une Pull Request

#### Processus

1. **Fork** le projet
2. **Clone** votre fork
```bash
git clone https://github.com/VOTRE_USERNAME/0xBot.git
cd 0xBot
```

3. **Créez une branche** pour votre fonctionnalité
```bash
git checkout -b feature/ma-super-feature
```

4. **Faites vos changements** en suivant les bonnes pratiques
5. **Testez** vos changements
6. **Commitez** avec un message clair
```bash
git commit -m "feat: ajoute ma super feature"
```

7. **Push** vers votre fork
```bash
git push origin feature/ma-super-feature
```

8. **Ouvrez une Pull Request** vers la branche `master`

#### Conventions de Code

- **Python** : Suivez PEP 8
- **Type hints** : Utilisez les type hints Python
- **Docstrings** : Documentez les fonctions complexes
- **Noms de variables** : Descriptifs et en anglais
- **Comments** : En français ou anglais selon le contexte

#### Format des Commits

Utilisez le format [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` - Nouvelle fonctionnalité
- `fix:` - Correction de bug
- `docs:` - Documentation uniquement
- `style:` - Formatage, points-virgules manquants, etc.
- `refactor:` - Refactoring du code
- `test:` - Ajout de tests
- `chore:` - Maintenance, dépendances, etc.

Exemples :
```
feat: ajoute support pour Binance
fix: corrige le calcul du stop-loss
docs: met à jour le guide d'installation
refactor: simplifie le service de trading
```

### 4. Tests

Avant de soumettre une PR :

```bash
# Installer les dépendances de dev
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Lancer les tests (quand disponibles)
pytest

# Vérifier le linting
flake8 src/
```

### 5. Documentation

Si vous ajoutez une fonctionnalité :
- Mettez à jour le `README.md` si nécessaire
- Ajoutez de la documentation dans `docs/`
- Commentez votre code pour les parties complexes

## 🎯 Domaines de Contribution

Voici quelques domaines où nous accueillons les contributions :

### Trading & IA
- Amélioration des prompts LLM
- Nouveaux indicateurs techniques
- Stratégies de trading alternatives
- Support de nouveaux exchanges (Binance, Bybit, etc.)

### Infrastructure
- Tests unitaires et d'intégration
- Monitoring et métriques
- Performance et optimisation
- Documentation

### Frontend
- Interface web React/Vue
- Dashboard temps réel
- Graphiques et visualisations
- Mobile app

### Sécurité
- Audit de sécurité
- Gestion des clés API
- Rate limiting
- Logging sécurisé

## 📝 Checklist Pull Request

Avant de soumettre votre PR, vérifiez que :

- [ ] Le code suit les conventions du projet
- [ ] Les tests passent (si applicables)
- [ ] La documentation est à jour
- [ ] Les commits sont bien formatés
- [ ] Pas de fichiers sensibles (.env, clés API, etc.)
- [ ] Le code fonctionne en paper trading
- [ ] Vous avez testé localement

## 🐛 Processus de Review

1. Un mainteneur reviewera votre PR
2. Des changements peuvent être demandés
3. Une fois approuvée, votre PR sera mergée
4. Vous serez ajouté aux contributeurs ! 🎉

## 💬 Questions ?

N'hésitez pas à :
- Ouvrir une [Discussion](../../discussions)
- Poser des questions dans les Issues
- Contacter les mainteneurs

## 🙏 Reconnaissance

Tous les contributeurs seront reconnus dans le README.

Merci de contribuer à 0xBot ! 🚀

---

**Note importante** : Ce projet est à but éducatif. Le trading de cryptomonnaies comporte des risques financiers importants. Les contributeurs ne sont pas responsables des pertes financières.

