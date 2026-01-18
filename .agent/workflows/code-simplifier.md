---
description: Simplifier et optimiser le code - supprimer la complexité inutile
---

# Code Simplifier Workflow

Quand tu utilises `/code-simplifier`, applique ces principes :

## 1. Principes KISS (Keep It Simple, Stupid)

- **Une fonction = une responsabilité**
- **Pas de nesting > 3 niveaux** (refactor si besoin)
- **Noms explicites** > commentaires
- **DRY** : Si tu copies, abstrais

## 2. Checklist de simplification

Avant chaque modification :

- [ ] Cette variable est-elle utilisée ?
- [ ] Cette fonction peut-elle être plus courte ?
- [ ] Ce commentaire est-il nécessaire ou le code est-il explicite ?
- [ ] Y a-t-il du code mort à supprimer ?
- [ ] Les imports sont-ils tous utilisés ?

## 3. Patterns à appliquer

### Early Returns (éviter l'indentation)

```python
# ❌ Mauvais
def process(data):
    if data:
        if data.is_valid:
            return do_something(data)
    return None

# ✅ Bon
def process(data):
    if not data or not data.is_valid:
        return None
    return do_something(data)
```

### Guard Clauses

```python
# ❌ Mauvais
def calculate(x, y):
    if x > 0:
        if y > 0:
            return x / y
    raise ValueError("Invalid")

# ✅ Bon
def calculate(x, y):
    if x <= 0 or y <= 0:
        raise ValueError("Invalid")
    return x / y
```

### Extraire les conditions complexes

```python
# ❌ Mauvais
if user.age >= 18 and user.verified and not user.banned and user.balance > 0:

# ✅ Bon
is_eligible = user.age >= 18 and user.verified and not user.banned
has_funds = user.balance > 0
if is_eligible and has_funds:
```

## 4. Commandes à exécuter

// turbo

```bash
# Trouver code mort (Python)
vulture . --min-confidence 80

# Trouver imports inutilisés
autoflake --check .

# Complexité cyclomatique
radon cc . -a -s
```

## 5. Output attendu

Après simplification, fournis :

1. **Diff clair** des changements
2. **Raison** de chaque simplification
3. **Métriques** : lignes avant/après, complexité réduite
