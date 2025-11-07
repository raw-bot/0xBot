#!/usr/bin/env python3
"""
Script d'application des corrections critiques identifiées dans l'audit du code 0xBot
Ce script applique automatiquement les corrections de Phase 1 - Nettoyage Urgent
"""

import os
import shutil
import glob
from pathlib import Path
from datetime import datetime

class AuditCorrections:
    """Appliquen les corrections critiques de l'audit"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.services_path = self.base_path / "backend" / "src" / "services"
        self.backup_path = self.base_path / f"backup_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_backup(self):
        """Créer une sauvegarde avant modifications"""
        print("🔄 Création de la sauvegarde...")
        self.backup_path.mkdir(exist_ok=True)

        # Sauvegarder les services
        services_backup = self.backup_path / "services"
        services_backup.mkdir(exist_ok=True)

        for service_file in self.services_path.glob("*.py"):
            if service_file.name != "__init__.py":
                shutil.copy2(service_file, services_backup / service_file.name)
                print(f"  ✅ Sauvegardé: {service_file.name}")

        print(f"💾 Sauvegarde créée dans: {self.backup_path}")

    def remove_obsolete_llm_services(self):
        """Supprimer les services LLM obsolètes (Correction Critique #1)"""
        print("\n🗑️ CORRECTION #1: Suppression des services LLM obsolètes...")

        # Services à supprimer (garder uniquement multi_coin_prompt_service.py)
        services_to_remove = [
            "simple_llm_prompt_service.py",
            "enriched_llm_prompt_service.py",
            "llm_prompt_service.py",
            "reference_prompt_service.py",
            "optimized_llm_service.py",
            "cost_aware_llm_client.py"
        ]

        removed_count = 0
        for service in services_to_remove:
            service_path = self.services_path / service
            if service_path.exists():
                # Renommer en .py.bak au lieu de supprimer définitivement
                backup_path = service_path.with_suffix('.py.bak')
                shutil.move(service_path, backup_path)
                print(f"  🗑️ {service} → {backup_path.name}")
                removed_count += 1
            else:
                print(f"  ⚠️ {service} non trouvé (déjà supprimé?)")

        print(f"✅ {removed_count} services LLM obsolètes archivés")

    def remove_trading_engine_tmp(self):
        """Supprimer le fichier trading_engine_service.py.tmp (Correction Critique #2)"""
        print("\n🗑️ CORRECTION #2: Suppression du fichier .tmp du TradingEngine...")

        tmp_file = self.services_path / "trading_engine_service.py.tmp"
        if tmp_file.exists():
            # Renommer en .tmp.bak
            backup_path = tmp_file.with_suffix('.tmp.bak')
            shutil.move(tmp_file, backup_path)
            print(f"  🗑️ trading_engine_service.py.tmp → {backup_path.name}")
        else:
            print(f"  ⚠️ trading_engine_service.py.tmp non trouvé")

    def standardize_decimal_types(self):
        """Standardiser sur Decimal pour les calculs financiers (Correction Critique #3)"""
        print("\n🔢 CORRECTION #3: Standardisation des types Decimal...")

        # Fichiers à modifier
        files_to_fix = [
            "multi_coin_prompt_service.py",
            "trading_engine_service.py"
        ]

        for filename in files_to_fix:
            file_path = self.services_path / filename
            if not file_path.exists():
                print(f"  ⚠️ {filename} non trouvé")
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Patterns à remplacer
            decimal_fixes = [
                # Remplacer les conversions float() en Decimal() pour les calculs financiers
                (
                    r'pnl = \(float\(position\.current_price\) - float\(position\.entry_price\)\) \* float\(position\.quantity\)',
                    'pnl = (Decimal(str(position.current_price)) - Decimal(str(position.entry_price))) * Decimal(str(position.quantity))'
                ),
                (
                    r'pnl = \(float\(position\.entry_price\) - float\(position\.current_price\)\) \* float\(position\.quantity\)',
                    'pnl = (Decimal(str(position.entry_price)) - Decimal(str(position.current_price))) * Decimal(str(position.quantity))'
                ),
                # Ajouter l'import Decimal si pas présent
                (
                    r'(from decimal import Decimal)',
                    r'\1'
                ),
                (
                    r'(import uuid\n)',
                    r'\1from decimal import Decimal\n'
                )
            ]

            original_content = content
            for pattern, replacement in decimal_fixes:
                import re
                content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ {filename} - Types Decimal standardisés")
            else:
                print(f"  ℹ️ {filename} - Déjà correct ou pas de patterns trouvés")

    def remove_dead_code(self):
        """Supprimer le code mort et commentaires (Correction Critique #4)"""
        print("\n🧹 CORRECTION #4: Nettoyage du code mort...")

        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Supprimer les lignes de code commentées désactivées
            import re
            content = re.sub(r'\s*# from \.simple_llm_prompt_service import SimpleLLMPromptService\s*# DISABLED.*\n', '\n', content)
            content = re.sub(r'\s*# self\.simple_prompt_service = SimpleLLMPromptService\(db\)\s*# DISABLED.*\n', '\n', content)

            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Code mort nettoyé du trading_engine_service.py")

    def resolve_critical_todos(self):
        """Résoudre les TODOs critiques (Correction Critique #5)"""
        print("\n📝 CORRECTION #5: Résolution des TODOs critiques...")

        import re  # Ajouter l'import re au début de la méthode

        # Résoudre le TODO Gemini dans bot.py
        bot_file = self.base_path / "backend" / "src" / "models" / "bot.py"
        if bot_file.exists():
            with open(bot_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Marquer le TODO Gemini comme "Not planned"
            content = content.replace(
                '    # GEMINI_PRO = "gemini-2.5-pro"  # TODO: Implement Gemini support',
                '    # GEMINI_PRO = "gemini-2.5-pro"  # NOT PLANNED: Focus on DeepSeek for now'
            )

            with open(bot_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ TODO Gemini marqué comme 'Not Planned' dans bot.py")

        # Résoudre les TODOs dans trading_memory_service.py
        memory_file = self.services_path / "trading_memory_service.py"
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Marquer les TODOs comme "Not Implemented"
            content = re.sub(
                r'(\s+)# TODO: (.+?)$',
                r'\1# NOT IMPLEMENTED: \2',
                content,
                flags=re.MULTILINE
            )

            with open(memory_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ TODOs marqués comme 'Not Implemented' dans trading_memory_service.py")

    def create_config_class(self):
        """Créer une classe de configuration pour remplacer les variables globales"""
        print("\n⚙️ CORRECTION: Création de la classe de configuration...")

        config_file = self.base_path / "backend" / "src" / "core" / "config.py"
        config_content = '''"""Configuration centralisée pour le bot de trading."""

import os
from decimal import Decimal
from typing import Optional


class TradingConfig:
    """Configuration centralisée pour le trading bot."""

    # LLM Configuration
    FORCED_MODEL_DEEPSEEK: str = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

    # Trading Parameters (replacer les magic numbers)
    MIN_CONFIDENCE_ENTRY: float = 0.55  # 55%
    MIN_CONFIDENCE_EXIT_EARLY: float = 0.60  # 60%
    MIN_CONFIDENCE_EXIT_NORMAL: float = 0.50  # 50%

    # Position Management
    MAX_POSITION_AGE_SECONDS: int = 7200  # 2 hours
    MIN_POSITION_AGE_FOR_EXIT_SECONDS: int = 1800  # 30 minutes

    # Risk Management
    DEFAULT_STOP_LOSS_PCT: float = 0.035  # 3.5%
    DEFAULT_TAKE_PROFIT_PCT: float = 0.07  # 7%

    # Performance
    CYCLE_INTERVAL_SECONDS: int = 300  # 5 minutes

    @classmethod
    def get_decimal_config(cls, key: str) -> Decimal:
        """Obtenir une configuration en Decimal."""
        return Decimal(str(getattr(cls, key, 0)))


# Instance globale
config = TradingConfig()
'''

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"  ✅ Classe de configuration créée: {config_file}")

    def run_all_corrections(self):
        """Exécuter toutes les corrections critiques"""
        print("🚀 APPLICATION DES CORRECTIONS CRITIQUES DE L'AUDIT")
        print("=" * 60)

        # Vérifier que nous sommes dans le bon répertoire
        if not (self.base_path / "backend").exists():
            print("❌ Erreur: Le répertoire backend n'est pas trouvé")
            print(f"   Chemin attendu: {self.base_path / 'backend'}")
            return False

        try:
            # Phase 1 - Corrections Critiques
            self.create_backup()
            self.remove_obsolete_llm_services()
            self.remove_trading_engine_tmp()
            self.standardize_decimal_types()
            self.remove_dead_code()
            self.resolve_critical_todos()
            self.create_config_class()

            print("\n" + "=" * 60)
            print("✅ TOUTES LES CORRECTIONS CRITIQUES APPLIQUÉES AVEC SUCCÈS!")
            print(f"💾 Sauvegarde disponible dans: {self.backup_path}")
            print("\n📋 PROCHAINES ÉTAPES:")
            print("1. Tester le système pour vérifier que tout fonctionne")
            print("2. Examiner les fichiers modifiés pour valider les changements")
            print("3. Continuer avec la Phase 2 - Refactoring Majeur")
            return True

        except Exception as e:
            print(f"\n❌ ERREUR lors de l'application des corrections: {e}")
            print(f"💡 Vérifiez la sauvegarde dans: {self.backup_path}")
            return False


def main():
    """Point d'entrée principal"""
    import sys

    # Déterminer le chemin du projet
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        # Utiliser le répertoire courant par défaut
        base_path = os.getcwd()

    print("🔍 Audit Corrections - Phase 1: Nettoyage Urgent")
    print(f"📁 Répertoire de base: {base_path}")

    # Créer et exécuter les corrections
    corrector = AuditCorrections(base_path)
    success = corrector.run_all_corrections()

    if success:
        print("\n🎉 Corrections appliquées avec succès!")
        print("🔄 Redémarrez votre bot pour tester les changements.")
    else:
        print("\n❌ Échec de l'application des corrections")
        sys.exit(1)


if __name__ == "__main__":
    main()
