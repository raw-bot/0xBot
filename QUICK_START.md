# ⚡ QUICK START - Installation en 5 minutes

## 🎯 Ce que ça fait

Avant :
```
⚡ ENRICHED | Valid decision for BTC/USDT: HOLD @ 65%
```

Après :
```
📝 Decision logged to: logs/llm_decisions/
[2 fichiers créés avec TOUT le contexte + raisonnement du LLM]
```

---

## 🚀 Installation Express

```bash
# 1. Aller à la racine du projet
cd /Users/cube/Documents/00-code/0xBot

# 2. Lancer le script d'installation
chmod +x install.sh
./install.sh

# 3. Modifier 2 fichiers (ouvrir MODIFICATIONS.patch pour copier-coller)
#    - backend/src/services/enriched_llm_prompt_service.py (5 modifs)
#    - backend/src/services/trading_engine_service.py (1 modif)

# 4. Redémarrer le bot
./dev.sh

# 5. Attendre 1-2 cycles (6-10 minutes)

# 6. Vérifier
ls logs/llm_decisions/prompts/ | wc -l    # > 0 ?
ls logs/llm_decisions/responses/ | wc -l  # > 0 ?

# 7. Analyser
python3 analyze_llm_logs.py
```

---

## 📊 Utilisation

### Lire un log complet
```bash
# Prompt envoyé
cat logs/llm_decisions/prompts/[nom_fichier].prompt.txt

# Réponse + raisonnement
cat logs/llm_decisions/responses/[nom_fichier].response.txt
```

### Analyser tous les logs
```bash
python3 analyze_llm_logs.py
```

### Chercher un pattern
```bash
# Trouver toutes les décisions ENTRY
ls logs/llm_decisions/responses/*ENTRY*

# Compter les HOLD
ls logs/llm_decisions/responses/*HOLD* | wc -l

# Voir la confidence moyenne
grep "confidence" logs/llm_decisions/responses/*.response.txt
```

---

## 🐛 Troubleshooting Express

### Erreur : "LLM Decision Logger not found"
```bash
# Recopier le fichier
cp llm_decision_logger.py backend/src/services/
```

### Pas de logs créés
```bash
# Recréer les dossiers
mkdir -p logs/llm_decisions/{prompts,responses}

# Vérifier les modifications code
grep "LLM_LOGGER_ENABLED" backend/src/services/enriched_llm_prompt_service.py
```

### Bot ne démarre pas
```bash
# Vérifier la syntaxe Python
python3 -m py_compile backend/src/services/enriched_llm_prompt_service.py
```

---

## 📚 Docs Complètes

- **README.md** : Vue d'ensemble
- **INSTALLATION_GUIDE_LOGGING.md** : Guide détaillé
- **MODIFICATIONS.patch** : Code exact
- **RÉCAPITULATIF_SOLUTION_C.md** : Tout ce qui a été fait

---

**C'est tout ! En 5 minutes tu as un système de logging complet. 🎉**
