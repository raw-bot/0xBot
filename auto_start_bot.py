#!/usr/bin/env python3
"""
Script pour démarrer automatiquement un bot au lancement du serveur
Usage: python3 auto_start_bot.py [bot_id]
"""

import json
import sys
import time
from pathlib import Path

import requests

# Couleurs
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def load_config():
    """Charge la configuration depuis .env.dev"""
    env_file = Path(".env.dev")

    if not env_file.exists():
        return None, None, None

    config = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    return (
        config.get("DEV_EMAIL"),
        config.get("DEV_PASSWORD"),
        config.get("AUTO_START_BOT_ID"),
    )


def wait_for_server(base_url="http://localhost:8020", timeout=30):
    """Attend que le serveur soit prêt"""
    print(f"{BLUE}⏳ Attente du serveur...{NC}")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"{GREEN}✅ Serveur prêt !{NC}")
                return True
        except:
            pass

        print(".", end="", flush=True)
        time.sleep(1)

    print(f"\n{RED}❌ Timeout: Le serveur n'a pas démarré{NC}")
    return False


def get_token(email, password, base_url="http://localhost:8020"):
    """Obtient un token d'authentification"""
    print(f"{BLUE}🔐 Authentification...{NC}")

    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=5,
        )

        if response.status_code == 200:
            token = response.json().get("token")
            print(f"{GREEN}✅ Authentifié{NC}")
            return token
        else:
            print(f"{RED}❌ Erreur d'authentification: {response.status_code}{NC}")
            return None
    except Exception as e:
        print(f"{RED}❌ Erreur: {e}{NC}")
        return None


def start_bot(bot_id, token, base_url="http://localhost:8020"):
    """Démarre un bot"""
    print(f"{BLUE}🤖 Démarrage du bot {bot_id}...{NC}")

    try:
        response = requests.post(
            f"{base_url}/api/bots/{bot_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}✅ Bot démarré avec succès !{NC}")

            # Afficher les détails si disponibles
            if isinstance(data, dict):
                details = data.get("details", {})
                if details:
                    status = details.get("status", "N/A")
                    engine = details.get("engine_running", "N/A")
                    print(f"{BLUE}   Status: {status}{NC}")
                    print(f"{BLUE}   Engine running: {engine}{NC}")
                else:
                    # Format alternatif
                    status = data.get("status", "N/A")
                    if status != "N/A":
                        print(f"{BLUE}   Status: {status}{NC}")

            return True
        else:
            print(f"{RED}❌ Erreur: {response.status_code}{NC}")
            try:
                error = response.json()
                print(f"{RED}   {error.get('detail', 'Unknown error')}{NC}")
            except:
                print(f"{RED}   {response.text}{NC}")
            return False
    except Exception as e:
        print(f"{RED}❌ Erreur: {e}{NC}")
        return False


def get_last_active_bot(token, base_url="http://localhost:8020"):
    """Récupère le dernier bot actif ou inactif (pas stopped)"""
    print(f"{BLUE}🔍 Recherche du dernier bot utilisable...{NC}")

    try:
        response = requests.get(
            f"{base_url}/api/bots",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            bots = data.get("bots", []) if isinstance(data, dict) else data

            if not bots:
                print(f"{YELLOW}⚠️  Aucun bot trouvé{NC}")
                return None

            # Filtrer les bots utilisables (pas STOPPED)
            usable_bots = [bot for bot in bots if bot["status"] != "stopped"]

            if not usable_bots:
                print(
                    f"{YELLOW}⚠️  Aucun bot actif/inactif trouvé (tous sont stopped){NC}"
                )
                print(f"{YELLOW}💡 Créez un nouveau bot ou réactivez-en un{NC}")
                return None

            # Prendre le dernier bot utilisable (le plus récent)
            last_bot = usable_bots[-1]
            status_emoji = "🟢" if last_bot["status"] == "active" else "⚪"
            print(
                f"{GREEN}✅ Trouvé: {status_emoji} {last_bot['name']} ({last_bot['id']}) - Status: {last_bot['status']}{NC}"
            )

            if len(usable_bots) > 1:
                print(
                    f"{BLUE}   💡 {len(usable_bots)} bots disponibles, utilisant le plus récent{NC}"
                )

            return last_bot["id"]
        else:
            print(f"{RED}❌ Erreur: {response.status_code}{NC}")
            return None
    except Exception as e:
        print(f"{RED}❌ Erreur: {e}{NC}")
        return None


def main():
    print(f"{BLUE}{'='*60}{NC}")
    print(f"{BLUE}🚀 Auto-Démarrage de Bot{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

    # Charger la config
    email, password, auto_bot_id = load_config()

    if not email or not password:
        print(f"{RED}❌ Credentials manquants dans .env.dev{NC}")
        print(f"{YELLOW}Créez le fichier avec:{NC}")
        print(f"  DEV_EMAIL=votre@email.com")
        print(f"  DEV_PASSWORD=votre-password")
        print(f"  AUTO_START_BOT_ID=bot-id-optionnel")
        sys.exit(1)

    # Déterminer quel bot démarrer
    bot_id = None

    # 1. Argument en ligne de commande
    if len(sys.argv) > 1:
        bot_id = sys.argv[1]
        print(f"{BLUE}📌 Bot ID depuis argument: {bot_id}{NC}\n")

    # 2. Variable d'environnement
    elif auto_bot_id:
        bot_id = auto_bot_id
        print(f"{BLUE}📌 Bot ID depuis .env.dev: {bot_id}{NC}\n")

    # Attendre que le serveur soit prêt
    if not wait_for_server():
        sys.exit(1)

    print("")

    # Obtenir le token
    token = get_token(email, password)
    if not token:
        sys.exit(1)

    # Si pas de bot_id spécifié, prendre le dernier
    if not bot_id:
        bot_id = get_last_active_bot(token)
        if not bot_id:
            print(f"{YELLOW}💡 Créez d'abord un bot via l'API{NC}")
            sys.exit(1)

    print("")

    # Démarrer le bot
    if start_bot(bot_id, token):
        print(f"\n{GREEN}{'='*60}{NC}")
        print(f"{GREEN}✅ Bot en cours d'exécution !{NC}")
        print(f"{GREEN}{'='*60}{NC}")
        print(f"\n{BLUE}📊 Surveillez les logs du serveur pour voir le bot trader{NC}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
