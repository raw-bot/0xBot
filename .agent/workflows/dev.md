---
description: Development workflow for 0xBot - CRITICAL PORT INFO
---

# 🚨 CRITICAL - PORTS 0xBot 🚨

## ⚠️ NE JAMAIS OUBLIER ⚠️

| Service                | Port     |
| ---------------------- | -------- |
| **Dashboard Frontend** | **3030** |
| Backend API            | 8020     |
| PostgreSQL             | 5432     |
| Redis                  | 6379     |

## Dashboard URL

```
http://localhost:3030
```

## Lancer le bot + dashboard

// turbo-all

1. Exécuter le script de lancement:

```bash
cd /Users/cube/Documents/00-code/0xBot && ./dashboard.sh
```

## Vérifier le statut Docker

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Arrêter le bot

```bash
# Ctrl+C dans le terminal du dashboard.sh
# ou
pkill -f "uvicorn.*8020"
pkill -f "vite.*3030"
```
