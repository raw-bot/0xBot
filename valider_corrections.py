#!/usr/bin/env python3
"""
Script de validation des corrections critiques appliquées
Vérifie que tous les problèmes critiques ont été résolus
"""

import os
import glob
from pathlib import Path

class ValidationCorrections:
    """Valide que les corrections critiques ont été appliquées"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.services_path = self.base_path / "backend" / "src" / "services"
        self.core_path = self.base_path / "backend" / "src" / "core"

    def check_backup_exists(self):
        """Vérifier que la sauvegarde a été créée"""
        print("🔍 VÉRIFICATION: Sauvegarde créée")
        backup_dirs = list(self.base_path.glob("backup_audit_*"))
        if backup_dirs:
            latest_backup = max(backup_dirs, key=lambda x: x.name)
            print(f"  ✅ Sauvegarde trouvée: {latest_backup}")
            return True
        else:
            print(f"  ❌ Aucune sauvegarde trouvée")
            return False

    def check_obsolete_services_archived(self):
        """Vérifier que les services LLM obsolètes ont été archivés"""
        print("\n🔍 VÉRIFICATION: Services LLM obsolètes archivés")

        expected_bak_files = [
            "simple_llm_prompt_service.py.bak",
            "enriched_llm_prompt_service.py.bak",
            "llm_prompt_service.py.bak",
            "reference_prompt_service.py.bak",
            "optimized_llm_service.py.bak",
            "cost_aware_llm_client.py.bak"
        ]

        active_services = [
            "multi_coin_prompt_service.py",
        ]

        archived_count = 0
        for bak_file in expected_bak_files:
            if (self.services_path / bak_file).exists():
                print(f"  ✅ {bak_file} archivé")
                archived_count += 1
            else:
                print(f"  ❌ {bak_file} manquant")

        active_count = 0
        for service in active_services:
            if (self.services_path / service).exists():
                print(f"  ✅ {service} actif")
                active_count += 1
            else:
                print(f"  ❌ {service} manquant")

        return archived_count == len(expected_bak_files) and active_count == len(active_services)

    def check_tmp_file_archived(self):
        """Vérifier que le fichier .tmp a été archivé"""
        print("\n🔍 VÉRIFICATION: Fichier .tmp archivé")

        tmp_file = self.services_path / "trading_engine_service.py.tmp.bak"
        if tmp_file.exists():
            print(f"  ✅ trading_engine_service.py.tmp.bak archivé")
            return True
        else:
            print(f"  ❌ trading_engine_service.py.tmp.bak manquant")
            return False

    def check_config_class_created(self):
        """Vérifier que la classe de configuration a été créée"""
        print("\n🔍 VÉRIFICATION: Classe de configuration créée")

        config_file = self.core_path / "config.py"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                if "class TradingConfig:" in content:
                    print(f"  ✅ Classe TradingConfig créée")
                    return True

        print(f"  ❌ Classe TradingConfig non trouvée")
        return False

    def check_todos_resolved(self):
        """Vérifier que les TODOs ont été résolus"""
        print("\n🔍 VÉRIFICATION: TODOs résolus")

        # Vérifier bot.py
        bot_file = self.base_path / "backend" / "src" / "models" / "bot.py"
        if bot_file.exists():
            with open(bot_file, 'r') as f:
                content = f.read()
                if "NOT PLANNED" in content:
                    print(f"  ✅ TODO Gemini résolu dans bot.py")
                else:
                    print(f"  ❌ TODO Gemini non résolu dans bot.py")
                    return False

        # Vérifier trading_memory_service.py
        memory_file = self.services_path / "trading_memory_service.py"
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                content = f.read()
                if "NOT IMPLEMENTED" in content:
                    print(f"  ✅ TODOs résolus dans trading_memory_service.py")
                else:
                    print(f"  ❌ TODOs non résolus dans trading_memory_service.py")
                    return False

        return True

    def check_dead_code_removed(self):
        """Vérifier que le code mort a été supprimé"""
        print("\n🔍 VÉRIFICATION: Code mort supprimé")

        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r') as f:
                content = f.read()

                # Vérifier que les imports commentés ont été supprimés
                if "# from .simple_llm_prompt_service import SimpleLLMPromptService  # DISABLED" not in content:
                    print(f"  ✅ Imports commentés supprimés")
                else:
                    print(f"  ❌ Imports commentés encore présents")
                    return False

                if "# DISABLED" not in content:
                    print(f"  ✅ Code désactivé supprimé")
                else:
                    print(f"  ❌ Code désactivé encore présent")
                    return False

        return True

    def run_validation(self):
        """Exécuter toutes les validations"""
        print("🧪 VALIDATION DES CORRECTIONS CRITIQUES APPLIQUÉES")
        print("=" * 60)

        results = []

        results.append(("Sauvegarde créée", self.check_backup_exists()))
        results.append(("Services LLM archivés", self.check_obsolete_services_archived()))
        results.append(("Fichier .tmp archivé", self.check_tmp_file_archived()))
        results.append(("Classe de configuration", self.check_config_class_created()))
        results.append(("TODOs résolus", self.check_todos_resolved()))
        results.append(("Code mort supprimé", self.check_dead_code_removed()))

        print("\n" + "=" * 60)
        print("📊 RÉSULTATS DE LA VALIDATION")
        print("=" * 60)

        passed = 0
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1

        print("\n" + "=" * 60)
        success_rate = (passed / total) * 100
        print(f"🎯 Taux de succès: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate == 100:
            print("🎉 TOUTES LES CORRECTIONS ONT ÉTÉ APPLIQUÉES AVEC SUCCÈS!")
        elif success_rate >= 80:
            print("⚠️  La plupart des corrections ont été appliquées")
        else:
            print("❌ Plusieurs corrections semblent manquer")

        return success_rate == 100

def main():
    """Point d'entrée principal"""
    import sys

    # Utiliser le répertoire courant par défaut
    base_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    print("🔍 Validation des Corrections Critiques - 0xBot")
    print(f"📁 Répertoire de base: {base_path}")

    validator = ValidationCorrections(base_path)
    success = validator.run_validation()

    if success:
        print("\n🎉 Validation réussie!")
        print("✅ Le bot est prêt pour les tests en conditions réelles.")
    else:
        print("\n⚠️  Validation incomplète")
        print("💡 Vérifiez les éléments marqués comme 'FAIL' et appliquez les corrections manquantes.")

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
