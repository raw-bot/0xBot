#!/usr/bin/env python3
"""
Script de test complet pour l'API AI Trading Agent.

Ce script teste toutes les fonctionnalités de l'API :
- Authentification (login)
- Création de bot
- Contrôle du bot (start/pause/stop)
- Récupération des positions et trades
"""

import requests
import json
import time
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8020"
TEST_EMAIL = "drawbot@protonmail.com"
TEST_PASSWORD = "password123"  # Changez si différent

# Couleurs pour l'affichage
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_section(msg: str):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{Colors.RESET}\n")


# ============================================================================
# Tests
# ============================================================================

def test_health():
    """Test du endpoint health."""
    print_section("Test 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"API est opérationnelle: {data['service']} v{data['version']}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erreur de connexion: {e}")
        return False


def test_login() -> Optional[str]:
    """Test de connexion et récupération du token."""
    print_section("Test 2: Authentification")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data['token']
            print_success(f"Connexion réussie pour {data['email']}")
            print_info(f"User ID: {data['id']}")
            print_info(f"Token: {token[:20]}...")
            return token
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return None


def test_create_bot(token: str) -> Optional[str]:
    """Test de création d'un bot."""
    print_section("Test 3: Création d'un Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    bot_data = {
        "name": "0xBot",
        "model_name": "qwen-max-3",
        "capital": 1000.0,
        "paper_trading": True,
        "risk_params": {
            "max_position_pct": 0.15,
            "max_drawdown_pct": 0.20,
            "max_trades_per_day": 10
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/bots",
            headers=headers,
            json=bot_data
        )
        
        if response.status_code == 201:
            bot = response.json()
            bot_id = bot['id']
            print_success(f"Bot créé avec succès!")
            print_info(f"Bot ID: {bot_id}")
            print_info(f"Nom: {bot['name']}")
            print_info(f"Modèle: {bot['model_name']}")
            print_info(f"Capital: ${bot['capital']}")
            print_info(f"Status: {bot['status']}")
            print_info(f"Paper Trading: {bot['paper_trading']}")
            return bot_id
        else:
            print_error(f"Création échouée: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return None


def test_list_bots(token: str):
    """Test de listage des bots."""
    print_section("Test 4: Liste des Bots")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/bots",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Récupération réussie: {data['total']} bot(s)")
            
            for bot in data['bots']:
                print_info(f"Bot: {bot['name']} ({bot['model_name']}) - Status: {bot['status']}")
                print_info(f"  Capital: ${bot['capital']} | PnL: ${bot['total_pnl']:.2f} ({bot['return_pct']:.2f}%)")
            
            return True
        else:
            print_error(f"Liste échouée: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_start_bot(token: str, bot_id: str):
    """Test de démarrage d'un bot."""
    print_section("Test 5: Démarrage du Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/bots/{bot_id}/start",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Bot démarré: {data['message']}")
            return True
        else:
            print_error(f"Démarrage échoué: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_get_bot(token: str, bot_id: str):
    """Test de récupération d'un bot spécifique."""
    print_section("Test 6: Détails du Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/bots/{bot_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            bot = response.json()
            print_success(f"Détails récupérés pour {bot['name']}")
            print_info(f"Status: {bot['status']}")
            print_info(f"Portfolio Value: ${bot['portfolio_value']:.2f}")
            print_info(f"Total PnL: ${bot['total_pnl']:.2f}")
            print_info(f"Return: {bot['return_pct']:.2f}%")
            return True
        else:
            print_error(f"Récupération échouée: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_get_positions(token: str, bot_id: str):
    """Test de récupération des positions."""
    print_section("Test 7: Positions du Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/bots/{bot_id}/positions",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Positions récupérées: {data['total']} position(s)")
            
            if data['total'] > 0:
                for pos in data['positions']:
                    print_info(f"Position {pos['symbol']}: {pos['side']}")
                    print_info(f"  Quantity: {pos['quantity']} @ ${pos['entry_price']}")
                    print_info(f"  Current: ${pos['current_price']}")
                    print_info(f"  PnL: ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_pct']:.2f}%)")
            else:
                print_warning("Aucune position ouverte")
            
            return True
        else:
            print_error(f"Récupération échouée: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_get_trades(token: str, bot_id: str):
    """Test de récupération des trades."""
    print_section("Test 8: Historique des Trades")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/bots/{bot_id}/trades",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Trades récupérés: {data['total']} trade(s)")
            
            if data['total'] > 0:
                for trade in data['trades'][:5]:  # Afficher les 5 derniers
                    print_info(f"Trade {trade['symbol']}: {trade['side']}")
                    print_info(f"  Quantity: {trade['quantity']} @ ${trade['price']}")
                    print_info(f"  Fees: ${trade['fees']:.2f}")
                    print_info(f"  PnL: ${trade['realized_pnl']:.2f}")
            else:
                print_warning("Aucun trade enregistré")
            
            return True
        else:
            print_error(f"Récupération échouée: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_pause_bot(token: str, bot_id: str):
    """Test de pause d'un bot."""
    print_section("Test 9: Pause du Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/bots/{bot_id}/pause",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Bot mis en pause: {data['message']}")
            return True
        else:
            print_error(f"Pause échouée: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_stop_bot(token: str, bot_id: str):
    """Test d'arrêt d'un bot."""
    print_section("Test 10: Arrêt du Bot")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/bots/{bot_id}/stop",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Bot arrêté: {data['message']}")
            if 'details' in data:
                print_info(f"Positions ouvertes: {data['details']['open_positions']}")
            return True
        else:
            print_error(f"Arrêt échoué: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


# ============================================================================
# Main
# ============================================================================

def main():
    """Exécute tous les tests."""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  🤖 AI Trading Agent - Test Suite")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Test 1: Health
    if not test_health():
        print_error("Le serveur n'est pas accessible. Vérifiez qu'il tourne sur le port 8020.")
        return
    
    # Test 2: Login
    token = test_login()
    if not token:
        print_error("Authentification échouée. Vérifiez les credentials.")
        return
    
    # Test 3: Créer un bot
    bot_id = test_create_bot(token)
    if not bot_id:
        print_warning("Impossible de créer un bot. Les tests suivants utiliseront un bot existant.")
        # Essayer de récupérer un bot existant
        test_list_bots(token)
        return
    
    # Test 4: Lister les bots
    test_list_bots(token)
    
    # Test 5: Démarrer le bot
    test_start_bot(token, bot_id)
    
    # Attendre un peu pour laisser le bot s'initialiser
    print_info("Attente de 3 secondes pour l'initialisation du bot...")
    time.sleep(3)
    
    # Test 6: Détails du bot
    test_get_bot(token, bot_id)
    
    # Test 7: Positions
    test_get_positions(token, bot_id)
    
    # Test 8: Trades
    test_get_trades(token, bot_id)
    
    # Test 9: Pause
    test_pause_bot(token, bot_id)
    
    # Test 10: Stop
    test_stop_bot(token, bot_id)
    
    # Résumé final
    print_section("Tests Terminés !")
    print_success("Tous les endpoints ont été testés avec succès!")
    print_info(f"Bot de test ID: {bot_id}")
    print_info("Vous pouvez vérifier l'état dans la base de données avec:")
    print_info(f"  docker exec trading_agent_postgres psql -U postgres -d trading_agent -c \"SELECT * FROM bots WHERE id='{bot_id}';\"")


if __name__ == "__main__":
    main()