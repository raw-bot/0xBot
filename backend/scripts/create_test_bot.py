#!/usr/bin/env python3
"""
Script pour créer un nouveau bot de test avec capital de $10,000
Configure automatiquement le bot ID dans .env.dev
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire backend au path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot, BotStatus
from src.models.user import User


def save_bot_id_to_env(bot_id: str) -> bool:
    """
    Sauvegarde automatiquement le bot ID dans .env.dev
    
    Args:
        bot_id: L'ID du bot à sauvegarder
        
    Returns:
        True si succès, False sinon
    """
    # Chemin vers .env.dev (à la racine du projet)
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env.dev"
    
    try:
        # Lire le contenu existant ou créer un nouveau fichier
        if env_file.exists():
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Chercher et mettre à jour AUTO_START_BOT_ID
            bot_id_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith('AUTO_START_BOT_ID='):
                    lines[i] = f'AUTO_START_BOT_ID={bot_id}\n'
                    bot_id_found = True
                    break
            
            # Si pas trouvé, ajouter à la fin
            if not bot_id_found:
                # Ajouter une ligne vide si le fichier ne se termine pas par une
                if lines and not lines[-1].endswith('\n'):
                    lines.append('\n')
                lines.append(f'\n# Auto-generated bot ID\n')
                lines.append(f'AUTO_START_BOT_ID={bot_id}\n')
            
            # Écrire le fichier mis à jour
            with open(env_file, 'w') as f:
                f.writelines(lines)
                
            print(f"✅ Bot ID sauvegardé dans .env.dev")
        else:
            # Créer un nouveau fichier .env.dev
            with open(env_file, 'w') as f:
                f.write("# Configuration de développement\n")
                f.write("# Créé automatiquement par create_test_bot.py\n\n")
                f.write("# Credentials pour auto_start_bot.py\n")
                f.write("DEV_EMAIL=your@email.com\n")
                f.write("DEV_PASSWORD=your-password\n\n")
                f.write("# Bot ID auto-généré\n")
                f.write(f"AUTO_START_BOT_ID={bot_id}\n")
            
            print(f"✅ Fichier .env.dev créé avec le bot ID")
            print(f"⚠️  N'oubliez pas de mettre à jour DEV_EMAIL et DEV_PASSWORD dans .env.dev")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Impossible de sauvegarder le bot ID dans .env.dev: {e}")
        print(f"   Vous pouvez le faire manuellement: AUTO_START_BOT_ID={bot_id}")
        return False


async def create_test_bot():
    """Créer un nouveau bot de test."""
    
    async with AsyncSessionLocal() as db:
        try:
            # Vérifier/créer un utilisateur de test
            user_query = select(User).limit(1)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Créer un utilisateur de test
                user = User(
                    email="test@0xbot.com",
                    username="0xBot-Test",
                    hashed_password="$2b$12$dummy_hash_for_testing"  # Mot de passe de test
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"✅ Utilisateur de test créé: {user.email}")
            
            # Vérifier si un bot actif existe déjà
            query = select(Bot).where(Bot.status == BotStatus.ACTIVE)
            result = await db.execute(query)
            existing_bot = result.scalar_one_or_none()
            
            if existing_bot:
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"⚠️  Un bot actif existe déjà:")
                print(f"   ID: {existing_bot.id}")
                print(f"   Nom: {existing_bot.name}")
                print(f"   Capital: ${existing_bot.capital:,.2f}")
                print(f"   Initial: ${existing_bot.initial_capital:,.2f}")
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print()
                
                response = input("Voulez-vous le réinitialiser? (o/n): ").lower()
                if response == 'o':
                    # Réinitialiser le bot existant
                    existing_bot.capital = 10000.00
                    existing_bot.initial_capital = 10000.00
                    # Note: total_pnl est une propriété calculée, pas besoin de le définir
                    
                    await db.commit()
                    await db.refresh(existing_bot)
                    
                    print()
                    print(f"✅ Bot réinitialisé avec succès!")
                    print(f"   Capital: ${existing_bot.capital:,.2f}")
                    print(f"   Initial: ${existing_bot.initial_capital:,.2f}")
                    
                    # Sauvegarder automatiquement le bot ID dans .env.dev
                    print()
                    save_bot_id_to_env(existing_bot.id)
                    
                    return existing_bot
                else:
                    print("❌ Opération annulée")
                    return None
            
            # Créer un nouveau bot
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("🤖 Création d'un nouveau bot de test...")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            new_bot = Bot(
                user_id=user.id,  # Associer à l'utilisateur de test
                name="0xBot",
                status=BotStatus.ACTIVE,
                model_name="qwen-max",  # ou votre modèle préféré
                initial_capital=10000.00,
                capital=10000.00,
                # Note: total_pnl est une propriété calculée, on ne la définit pas ici
                paper_trading=True,  # Mode paper trading pour les tests
                trading_symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],  # Top 5 cryptos
                risk_params={
                    "max_position_pct": 0.15,
                    "max_exposure_pct": 0.85,
                    "stop_loss_pct": 0.035,
                    "take_profit_pct": 0.07
                }
            )
            
            db.add(new_bot)
            await db.commit()
            await db.refresh(new_bot)
            
            print()
            print(f"✅ Bot créé avec succès!")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"   ID: {new_bot.id}")
            print(f"   Nom: {new_bot.name}")
            print(f"   Statut: {new_bot.status.value}")
            print(f"   Modèle: {new_bot.model_name}")
            print(f"   Capital Initial: ${new_bot.initial_capital:,.2f}")
            print(f"   Capital Actuel: ${new_bot.capital:,.2f}")
            print(f"   Paper Trading: {new_bot.paper_trading}")
            print(f"   Symboles: {', '.join(new_bot.trading_symbols)}")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print()
            
            # Sauvegarder automatiquement le bot ID dans .env.dev
            save_bot_id_to_env(new_bot.id)
            print()
            print(f"🚀 Vous pouvez maintenant démarrer le bot avec: ./start.sh")
            
            return new_bot
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print()
    print("╔════════════════════════════════════════════════╗")
    print("║     CRÉATION BOT DE TEST - $10,000            ║")
    print("╚════════════════════════════════════════════════╝")
    print()
    
    asyncio.run(create_test_bot())

