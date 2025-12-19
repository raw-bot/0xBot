#!/usr/bin/env python3
"""
Script simple pour mettre à jour le modèle du bot vers deepseek-chat
"""

import sqlite3
import os

def main():
    print("🎯 MISE À JOUR DU MODÈLE LLM")
    print("============================")
    
    db_path = "/Users/cube/Documents/00-code/0xBot/backend/database.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Base de données non trouvée: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier le bot actuel
        cursor.execute("SELECT id, name, model_name FROM bots WHERE id = '88e3df10-eb6e-4f13-8f3a-de24788944dd'")
        bot = cursor.fetchone()
        
        if bot:
            print(f"🤖 Bot trouvé:")
            print(f"   ID: {bot[0]}")
            print(f"   Nom: {bot[1]}")
            print(f"   Ancien modèle: {bot[2]}")
            
            # Mettre à jour vers deepseek-chat
            cursor.execute("UPDATE bots SET model_name = 'deepseek-chat' WHERE id = '88e3df10-eb6e-4f13-8f3a-de24788944dd'")
            conn.commit()
            
            print("✅ Bot mis à jour vers deepseek-chat")
            
            # Vérifier la mise à jour
            cursor.execute("SELECT model_name FROM bots WHERE id = '88e3df10-eb6e-4f13-8f3a-de24788944dd'")
            new_model = cursor.fetchone()
            print(f"✅ Nouveau modèle confirmé: {new_model[0]}")
            
        else:
            print("❌ Bot non trouvé dans la base de données")
            
        conn.close()
        
        print("\n🎯 PROCHAINES ÉTAPES:")
        print("1. Arrêtez le bot (Ctrl+C dans le terminal)")
        print("2. Redémarrez avec: cd /Users/cube/Documents/00-code/0xBot && ./start.sh")
        print("3. Le bot utilisera DeepSeek Chat V3.1!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
