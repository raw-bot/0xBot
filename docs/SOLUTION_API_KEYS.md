# 🚨 SOLUTION: Problème Clé API LLM

## 🔍 **DIAGNOSTIC**

L'erreur `401 - Incorrect API key provided` indique que votre bot ne peut pas se connecter au service LLM Qwen.

## 🔧 **VÉRIFICATION DES CLÉS API**

### **1. Vérifier les Variables d'Environnement**

Votre bot utilise ces clés API :

```bash
# Clés LLM (nécessaires pour le trading)
QWEN_API_KEY=your_qwen_key_here
CLAUDE_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Clés OKX (nécessaires pour le trading)
OKX_API_KEY=your_okx_key_here
OKX_SECRET_KEY=your_okx_secret_here
```

### **2. Fichiers de Configuration**

Vérifiez que ces fichiers existent :

- `.env` (variables locales)
- `.env.dev` (variables développement)
- Configuration serveur/production

## 📁 **EMPLACEMENTS DES FICHIERS**

<read_file>
<args>
<file>
<path>.env.dev.example</path>
</file>
</read_file>
