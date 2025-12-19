# 🤖 GUIDE: Changer de LLM pour Votre Bot

## 🎯 **OBJECTIF**

Votre bot utilise actuellement **Qwen** (qui ne fonctionne plus). Nous allons le basculer vers un **LLM fonctionnel**.

## 🔍 **LLMs DISPONIBLES**

| LLM          | Nom dans le Code    | Clé API Requise    | Qualité    | Coût   |
| ------------ | ------------------- | ------------------ | ---------- | ------ |
| **Claude**   | `claude-4.5-sonnet` | `CLAUDE_API_KEY`   | ⭐⭐⭐⭐⭐ | 💰💰   |
| **GPT-4**    | `gpt-4`             | `OPENAI_API_KEY`   | ⭐⭐⭐⭐⭐ | 💰💰💰 |
| **DeepSeek** | `deepseek-v3`       | `DEEPSEEK_API_KEY` | ⭐⭐⭐⭐   | 💰     |
| **Qwen**     | `qwen-max`          | `QWEN_API_KEY`     | ⭐⭐⭐     | 💰     |

## 🔧 **MÉTHODE 1: Via Interface Web (Recommandée)**

### **1. Créer un Nouveau Bot**

1. Accédez à l'interface web de votre bot
2. Créez un **nouveau bot** avec :
   - **Nom** : "Bot Trading Claude" (ou GPT-4)
   - **Model** : `claude-4.5-sonnet` ou `gpt-4`
   - **Capital** : $10,000 (ou votre montant)

### **2. Démarrer le Nouveau Bot**

- Utilisez le nouveau bot au lieu de l'ancien
- L'ancien bot peut être arrêté

## 🔧 **MÉTHODE 2: Via Base de Données**

### **1. Identifier Votre Bot**

```sql
SELECT id, name, model_name, status FROM bots;
```

### **2. Mettre à Jour le Modèle**

```sql
UPDATE bots
SET model_name = 'claude-4.5-sonnet'
WHERE name = 'VotreNomDeBot';
```

## 🔧 **MÉTHODE 3: Modification Directe du Code**

### **1. Forcer un Modèle Spécifique**

Dans `trading_engine_service.py`, ligne ~315 :

```python
# AVANT
llm_response = await self.llm_client.analyze_market(
    model=current_bot.model_name,
    prompt=prompt_data["prompt"],
    ...
)

# APRÈS (temporaire)
llm_response = await self.llm_client.analyze_market(
    model="claude-4.5-sonnet",  # Force Claude
    prompt=prompt_data["prompt"],
    ...
)
```

## 🔑 **CONFIGURATION DES CLÉS API**

### **Fichiers de Configuration**

Créez/modifiez `.env` avec :

```bash
# Claude (Recommandé)
CLAUDE_API_KEY=sk-ant-your-claude-key-here

# OU GPT-4
OPENAI_API_KEY=sk-your-openai-key-here

# OU DeepSeek (Économique)
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

### **Variables d'Environnement Serveur**

Si déployé sur serveur :

```bash
export CLAUDE_API_KEY="sk-ant-your-key"
# OU
export OPENAI_API_KEY="sk-your-key"
```

## 📊 **RECOMMANDATION**

### **Meilleur Choix : Claude**

```yaml
Modèle: claude-4.5-sonnet
Clé: CLAUDE_API_KEY
Avantages:
  - Très stable et fiable
  - Excellent pour trading
  - API robuste
  - Bonne qualité de réponse
```

### **Alternative Économique : DeepSeek**

```yaml
Modèle: deepseek-v3
Clé: DEEPSEEK_API_KEY
Avantages:
  - Coût très faible
  - Bonne performance
  - API simple à configurer
```

## ⚡ **SOLUTION RAPIDE**

### **Pour Tester Immédiatement**

1. **Configurez CLAUDE_API_KEY** dans vos variables d'environnement
2. **Créez un nouveau bot** avec `claude-4.5-sonnet`
3. **Démarrez le nouveau bot**

### **Pour Debugging**

Ajoutez temporairement dans `trading_engine_service.py` :

```python
# Ligne ~315 - Force Claude temporairement
model_to_use = "claude-4.5-sonnet"  # Override pour debug
llm_response = await self.llm_client.analyze_market(
    model=model_to_use,
    prompt=prompt_data["prompt"],
    ...
)
```

## 🧪 **TEST DE CONNEXION**

### **Test Manuel**

```python
# Créez un fichier test_llm.py
import asyncio
from backend.src.core.llm_client import get_llm_client

async def test_llm():
    client = get_llm_client()
    response = await client.analyze_market(
        model="claude-4.5-sonnet",
        prompt="Say 'Hello, Claude works!' in JSON format: {\"test\": \"success\"}"
    )
    print(response)

asyncio.run(test_llm())
```

## 🚨 **POINTS D'ATTENTION**

1. **Une LLM à la fois** : Un bot = un LLM
2. **Nouvelle clé requise** : Chaque LLM a sa propre API key
3. **Coûts différents** : GPT-4 est plus cher que DeepSeek
4. **Performance** : Tous supportent votre format de prompt simplifié

## ✅ **PROCHAINE ÉTAPE**

**Dites-moi quel LLM vous préférez :**

- **Claude** (recommandé, stable)
- **GPT-4** (excellent, cher)
- **DeepSeek** (économique, bon)

Et je vous aiderai à le configurer !
