# 📊 Surveillance Rapide des Logs 0xBot

## 🚀 Commandes Essentielles (À retenir !)

### 1. **Logs en Temps Réel Simple**
```bash
# Voir les logs en direct (plus simple)
tail -f backend.log

# Avec filtrage intelligent et couleurs
./logs_temps_reel.sh
```

### 2. **Surveillance Avancée**
```bash
# Menu interactif complet
./surveiller_logs_bot.sh

# Alertes automatiques (erreurs, arrêts, etc.)
./alertes_logs_bot.sh
```

### 3. **Diagnostic Rapide**
```bash
# Status complet en 30 secondes
./diagnostic_rapide.sh
```

### 4. **Dashboard Web**
```bash
# Interface graphique dans le navigateur
python3 performance_monitor.py --dashboard --port 8080
# Puis ouvrir: http://localhost:8080
```

---

## ⚡ **Utilisation Quotidienne**

### **Matin** (Vérifier que tout va bien)
```bash
./diagnostic_rapide.sh
```

### **Surveillance Continue** (Toute la journée)
```bash
# Dans un terminal séparé
./logs_temps_reel.sh
```

### **Alertes** (En cas de problème)
```bash
# Lancer les alertes automatiques
./alertes_logs_bot.sh
```

### **Investigation** (Quand il y a un problème)
```bash
# Menu complet avec recherche
./surveiller_logs_bot.sh
```

---

## 🔍 **Filtrage des Logs**

### **Voir seulement :**
```bash
# Erreurs seulement
tail -f backend.log | grep -i error

# Décisions du bot seulement
tail -f backend.log | grep "🤖"

# Trades exécutés seulement
tail -f backend.log | grep "💰"

# Performance LLM seulement
tail -f backend.log | grep -E "LLM|Decision"
```

---

## 📁 **Fichiers de Log**

- **Principal** : `backend.log`
- **Bot spécifique** : `logs/bot.log` (si existe)
- **Docker** : `docker logs trading_agent_backend`

---

## 🎯 **Scénarios Courants**

### **"Mon bot ne répond plus"**
```bash
1. ./diagnostic_rapide.sh
2. ./logs_temps_reel.sh
3. grep -i "error" backend.log | tail -10
```

### **"Je veux surveiller en continu"**
```bash
# Terminal 1
./logs_temps_reel.sh

# Terminal 2 (alertes)
./alertes_logs_bot.sh

# Terminal 3 (dashboard)
python3 performance_monitor.py --dashboard --port 8080
```

### **"Il y a une erreur"**
```bash
# Voir les dernières erreurs
tail -50 backend.log | grep -i error

# Recherche spécifique
grep -i "votre-mot-cle" backend.log
```

---

**💡 Conseil : Gardez `tail -f backend.log` ouvert dans un terminal pendant que vous travaillez !**
