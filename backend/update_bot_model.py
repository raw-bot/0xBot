#!/usr/bin/env python3
import os
import sys
sys.path.append('backend')

try:
    from backend.src.models.bot import Bot, ModelName
    from backend.src.core.database import get_db
    
    print("🔧 Updating bot model in database...")
    
    with get_db() as db:
        # Trouver et mettre à jour le bot
        bot = db.query(Bot).filter(Bot.id == '88e3df10-eb6e-4f13-8f3a-de24788944dd').first()
        if bot:
            print(f"Bot trouvé: {bot.name}")
            print(f"Ancien modèle: {bot.model_name}")
            
            # Mettre à jour vers deepseek-chat
            bot.model_name = "deepseek-chat"
            db.commit()
            
            print(f"Nouveau modèle: {bot.model_name}")
            print("✅ Bot mis à jour vers deepseek-chat")
        else:
            print("❌ Bot non trouvé!")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Copiez ce script dans le dossier backend et lancez: python3 update_bot_model.py")
except Exception as e:
    print(f"❌ Error: {e}")
