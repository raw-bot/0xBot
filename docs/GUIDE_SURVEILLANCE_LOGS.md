# 📊 Guide Complet - Surveillance des Logs 0xBot

**Comment surveiller votre bot même quand il fonctionne en arrière-plan**

---

## 🚀 Méthodes de Surveillance des Logs

### 1. **Logs en Temps Réel (Recommandé)**

#### Commande universelle pour suivre tous les logs :
```bash
# Suivre tous les logs en temps réel
tail -f backend.log | grep -E "(BOT|ERROR|INFO|WARNING|Trading|🤖|💰|📊)"

# Ou plus simple :
tail -f backend.log
```

#### Logs spécifiques par composant :
```bash
# Logs du bot principal
tail -f backend.log | grep "🤖"

# Logs LLM/décisions
tail -f backend.log | grep -E "(LLM|Décision|Confidence)"

# Logs trades
tail -f backend.log | grep -E "(💰|Trade|Position)"

# Logs erreurs seulement
tail -f backend.log | grep -i error

# Logs performance
tail -f backend.log | grep -i "perf\|cache\|llm"
```

### 2. **Surveillance Multi-Fichiers**

```bash
# Suivre plusieurs fichiers de log simultanément
tail -f backend.log logs/bot.log

# Avec couleurs pour mieux différencier
tail -f backend.log | grep --color=always "ERROR\|WARNING\|🤖\|💰"
```

### 3. **Monitoring Avancé avec Filtrage**

```bash
# Logs des dernières 10 minutes seulement
tail -f backend.log | grep "$(date '+%H:%M')"

# Filtrer par niveau d'importance
tail -f backend.log | grep -E "ERROR|CRITICAL|🤖.*ERROR"

# Surveiller les décisions LLM
tail -f backend.log | grep -A2 -B2 "Decision\|Confidence"
```

---

## 📁 Localisation des Fichiers de Log

### Fichiers de Log Principaux
```bash
# 1. Log principal (le plus important)
backend.log

# 2. Logs spécifiques du bot
logs/bot.log

# 3. Logs des services (si séparés)
logs/services.log

# 4. Logs Docker (si conteneurisé)
docker logs trading_agent_backend

# 5. Logs système
sudo journalctl -u trading-agent -f
```

### Vérifier quels fichiers de log existent :
```bash
# Lister tous les fichiers de log
find . -name "*.log" -type f

# Voir la taille et modification des logs
ls -lah *.log logs/*.log 2>/dev/null

# Vérifier si les logs sont actifs (tail + Ctrl+C pour arrêter)
tail -f backend.log
```

---

## 🔍 Surveillance par Processus

### Trouver le processus du bot :
```bash
# Trouver tous les processus Python liés au bot
ps aux | grep -E "(python|main.py|uvicorn)"

# Trouver le PID spécifique
pgrep -f "backend.*main.py"

# Voir les détails du processus
ps -ef | grep trading
```

### Surveiller par PID :
```bash
# Voir les logs d'un processus spécifique
strace -p <PID> 2>&1 | head -20

# Surveiller les fichiers ouverts par le processus
lsof -p <PID> | grep log
```

---

## 📊 Monitoring Automatique avec Alertes

### Script de surveillance automatique :
```bash
cat > surveiller_bot.sh << 'EOF'
#!/bin/bash

echo "🔍 Surveillance automatique de 0xBot..."
echo "========================================"

# Fonction pour vérifier si le bot fonctionne
check_bot_running() {
    if pgrep -f "backend.*main.py" > /dev/null; then
        echo "✅ Bot en fonctionnement"
        return 0
    else
        echo "❌ Bot ARRETÉ!"
        return 1
    fi
}

# Fonction pour surveiller les logs
watch_logs() {
    echo "📊 Surveillance des logs en temps réel..."
    echo "Appuyez sur Ctrl+C pour arrêter"
    echo ""

    # Logs colorés en temps réel
    tail -f backend.log | grep --color=always -E \
        "🤖.*BOT|💰.*TRADE|📊.*LLM|ERROR|WARNING"
}

# Fonction pour alertes erreurs
watch_errors() {
    echo "🚨 Surveillance des erreurs uniquement..."
    echo "Appuyez sur Ctrl+C pour arrêter"
    echo ""

    tail -f backend.log | grep --color=always -i "error\|critical\|failed"
}

# Menu interactif
while true; do
    clear
    echo "🤖 0xBot - Surveillance Logs"
    echo "=========================="
    echo "1. Vérifier statut du bot"
    echo "2. Logs en temps réel (colorés)"
    echo "3. Surveillance erreurs uniquement"
    echo "4. Voir les 50 dernières lignes"
    echo "5. Rechercher dans les logs"
    echo "6. Quitter"
    echo ""
    read -p "Votre choix (1-6): " choice

    case $choice in
        1) check_bot_running ;;
        2) watch_logs ;;
        3) watch_errors ;;
        4) tail -50 backend.log ;;
        5)
            echo "Rechercher dans les logs:"
            read -p "Mot-clé à chercher: " keyword
            grep -i "$keyword" backend.log | tail -20
            ;;
        6) echo "👋 Au revoir!"; exit 0 ;;
        *) echo "❌ Choix invalide"; sleep 2 ;;
    esac

    echo ""
    read -p "Appuyez sur Entrée pour continuer..."
done
EOF

chmod +x surveiller_bot.sh
```

---

## 🔔 Système d'Alertes Automatiques

### Script d'alertes par email :
```bash
cat > alertes_bot.sh << 'EOF'
#!/bin/bash

# Configuration
LOG_FILE="backend.log"
ALERT_EMAIL="votre@email.com"
ERROR_COUNT=0

# Fonction d'envoi d'alerte
send_alert() {
    local subject="$1"
    local message="$2"
    echo "[$(date)] ALERT: $subject - $message"
    # Ici vous pouvez ajouter l'envoi d'email, Slack, etc.
}

# Surveillance continue
tail -f "$LOG_FILE" | while read line; do
    # Détecter les erreurs critiques
    if echo "$line" | grep -i "error\|critical\|failed" > /dev/null; then
        ERROR_COUNT=$((ERROR_COUNT + 1))
        send_alert "ERREUR DÉTECTÉE" "$line"

        if [ $ERROR_COUNT -ge 5 ]; then
            send_alert "TROP D'ERREURS" "5+ erreurs détectées, vérifiez le bot!"
            ERROR_COUNT=0
        fi
    fi

    # Détecter les arrêts inattendus
    if echo "$line" | grep -i "stopped\|terminated\|exiting" > /dev/null; then
        send_alert "BOT ARRÊTÉ" "Le bot semble s'être arrêté"
    fi

    # Détecter les bonnes nouvelles
    if echo "$line" | grep -i "trade executed\|profit\|success" > /dev/null; then
        send_alert "SUCCÈS" "$line"
    fi
done
EOF

chmod +x alertes_bot.sh
```

---

## 🖥️ Dashboard de Monitoring Web

### Utiliser le dashboard que nous avons créé :
```bash
# Démarrer le dashboard de performance
python3 performance_monitor.py --dashboard --port 8080

# Accéder via navigateur :
# http://localhost:8080
```

**Fonctionnalités du dashboard :**
- 📊 Métriques temps réel
- 📈 Graphiques de performance
- 🚨 Alertes automatiques
- 🔄 Mise à jour automatique (30s)

---

## 📱 Commandes de Diagnostic Rapide

### Checklist complète :
```bash
# 1. Vérifier si le bot fonctionne
check_bot_running() {
    if pgrep -f "backend.*main.py" > /dev/null; then
        echo "✅ Bot actif"
        ps aux | grep "backend.*main.py"
    else
        echo "❌ Bot arrêté"
    fi
}

# 2. Voir les logs récents
recent_logs() {
    echo "📋 20 dernières lignes du log principal:"
    tail -20 backend.log
}

# 3. Rechercher les erreurs
find_errors() {
    echo "🚨 Erreurs dans les dernières 100 lignes:"
    tail -100 backend.log | grep -i error
}

# 4. Vérifier l'espace disque
check_disk_space() {
    echo "💾 Espace disque:"
    df -h | grep -E "/$|/Users"
}

# Utilisation mémoire du processus
check_memory() {
    echo "🧠 Mémoire utilisée par le bot:"
    pgrep -f "backend.*main.py" | xargs ps -o pid,ppid,cmd,%mem,%cpu
}

# Exécuter tous les diagnostics
full_diagnostic() {
    echo "🔍 DIAGNOSTIC COMPLET 0xBot"
    echo "==========================="
    check_bot_running
    echo ""
    recent_logs
    echo ""
    find_errors
    echo ""
    check_disk_space
    echo ""
    check_memory
}

# Lancer le diagnostic complet
full_diagnostic
```

---

## 🚀 Scripts Pratiques Pré-Faits

### 1. **Surveillance Continue Simple**
```bash
# Version ultra-simple - juste suivre les logs
tail -f backend.log
```

### 2. **Surveillance avec Filtrage**
```bash
# Logs importants seulement
tail -f backend.log | grep -E "BOT|LLM|Trade|Error"
```

### 3. **Mode Dashboard**
```bash
# Lancer le dashboard web
python3 performance_monitor.py --dashboard --port 8080
```

### 4. **Alertes Automatiques**
```bash
# Lancer la surveillance d'erreurs
./alertes_bot.sh
```

---

## ⚡ Commandes Rapides de Référence

### **Quotidennes :**
```bash
# Vérifier que tout va bien
tail -f backend.log | grep "🤖.*BOT"

# Voir les dernières décisions
tail -20 backend.log | grep -A5 -B5 "Decision"
```

### **Dépannage :**
```bash
# Voir les erreurs récentes
tail -50 backend.log | grep -i error

# Rechercher un problème spécifique
grep -i "mot-clé" backend.log

# Voir ce qui se passe maintenant
tail -f backend.log
```

### **Monitoring Avancé :**
```bash
# Dashboard complet
python3 performance_monitor.py --dashboard --port 8080

# Surveillance automatique
./surveiller_bot.sh

# Alertes par erreur
./alertes_bot.sh
```

---

## 🎯 **Recommandation Finale**

**Pour une surveillance efficace, utilisez :**

1. **Logs temps réel** : `tail -f backend.log | grep --color=always -E "🤖|💰|📊|ERROR"`
2. **Dashboard web** : `python3 performance_monitor.py --dashboard --port 8080`
3. **Script automatique** : `./surveiller_bot.sh`

**Votre bot sera sous surveillance 24/7 avec alertes automatiques !** 🚀
