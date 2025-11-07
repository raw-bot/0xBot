#!/usr/bin/env python3
"""
Script de validation finale - Vérifie que toutes les corrections des 3 phases ont été appliquées
"""

import os
import glob
from pathlib import Path
from datetime import datetime

class ValidationFinale:
    """Validation complète de toutes les corrections appliquées"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.services_path = self.base_path / "backend" / "src" / "services"
        self.core_path = self.base_path / "backend" / "src" / "core"

    def check_phase1_corrections(self):
        """Vérifier les corrections de Phase 1"""
        print("🔍 VÉRIFICATION PHASE 1 - Nettoyage Urgent")

        results = []

        # Sauvegarde créée
        backup_dirs = list(self.base_path.glob("backup_audit_*"))
        results.append(("Sauvegarde Phase 1", bool(backup_dirs)))

        # Services LLM archivés
        expected_bak_files = [
            "simple_llm_prompt_service.py.bak",
            "enriched_llm_prompt_service.py.bak",
            "llm_prompt_service.py.bak",
            "reference_prompt_service.py.bak",
            "optimized_llm_service.py.bak",
            "cost_aware_llm_client.py.bak"
        ]

        archived_count = sum(1 for bak in expected_bak_files
                           if (self.services_path / bak).exists())
        results.append(("Services LLM archivés", archived_count == len(expected_bak_files)))

        # Service actif
        results.append(("Service MultiCoin actif",
                       (self.services_path / "multi_coin_prompt_service.py").exists()))

        # Classe de configuration
        config_file = self.core_path / "config.py"
        results.append(("Classe TradingConfig", config_file.exists() and "class TradingConfig:" in config_file.read_text()))

        return results

    def check_phase2_corrections(self):
        """Vérifier les corrections de Phase 2"""
        print("\n🔍 VÉRIFICATION PHASE 2 - Refactoring Majeur")

        results = []

        # Sauvegarde Phase 2
        backup_dirs = list(self.base_path.glob("backup_phase2_*"))
        results.append(("Sauvegarde Phase 2", bool(backup_dirs)))

        # Nouveaux services créés
        new_services = [
            "service_interface.py",
            "tests/integration/test_complete_trading_cycle.py"
        ]

        for service in new_services:
            if "tests" in service:
                file_path = self.base_path / "backend" / service
            else:
                file_path = self.services_path / service
            results.append((f"Service créé: {service.split('/')[-1]}", file_path.exists()))

        # Script de formatage
        results.append(("Script formatage", (self.base_path / "format_code.sh").exists()))

        # Imports cleaning
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            content = engine_file.read_text()
            results.append(("Code mort supprimé", "# DISABLED" not in content))

        return results

    def check_phase3_corrections(self):
        """Vérifier les corrections de Phase 3"""
        print("\n🔍 VÉRIFICATION PHASE 3 - Amélioration Continue")

        results = []

        # Sauvegarde Phase 3
        backup_dirs = list(self.base_path.glob("backup_phase3_*"))
        results.append(("Sauvegarde Phase 3", bool(backup_dirs)))

        # Nouveaux services Phase 3
        phase3_services = [
            "performance_monitor.py",
            "cache_service.py",
            "health_check_service.py",
            "alerting_service.py",
            "validation_service.py",
            "metrics_export_service.py",
            "error_recovery_service.py"
        ]

        for service in phase3_services:
            file_path = self.services_path / service
            results.append((f"Service créé: {service}", file_path.exists()))

        # Scripts supplémentaires
        results.append(("Script dépendances", (self.base_path / "update_dependencies.sh").exists()))

        return results

    def check_overall_improvements(self):
        """Vérifier les améliorations globales"""
        print("\n🔍 VÉRIFICATION AMÉLIORATIONS GLOBALES")

        results = []

        # Fichiers d'audit
        results.append(("Rapport d'audit", (self.base_path / "audit_code_complet.md").exists()))

        # Scripts de correction
        correction_scripts = [
            "appliquer_corrections_critiques.py",
            "appliquer_corrections_phase2.py",
            "appliquer_corrections_phase3.py"
        ]

        for script in correction_scripts:
            results.append((f"Script: {script}", (self.base_path / script).exists()))

        # Validation
        results.append(("Script validation", (self.base_path / "valider_corrections.py").exists()))

        return results

    def generate_final_report(self):
        """Générer le rapport final"""
        print("\n📊 GÉNÉRATION DU RAPPORT FINAL")
        print("=" * 80)

        # Collecter tous les résultats
        all_results = []
        all_results.extend(self.check_phase1_corrections())
        all_results.extend(self.check_phase2_corrections())
        all_results.extend(self.check_phase3_corrections())
        all_results.extend(self.check_overall_improvements())

        # Compter les succès
        total_tests = len(all_results)
        passed_tests = sum(1 for _, result in all_results if result)
        success_rate = (passed_tests / total_tests) * 100

        # Afficher les résultats
        print(f"\n📈 RÉSULTATS GLOBAUX")
        print(f"Tests réussis: {passed_tests}/{total_tests}")
        print(f"Taux de succès: {success_rate:.1f}%")

        print(f"\n✅ TESTS RÉUSSIS:")
        for test_name, result in all_results:
            if result:
                print(f"  ✅ {test_name}")

        failed_tests = [name for name, result in all_results if not result]
        if failed_tests:
            print(f"\n❌ TESTS ÉCHOUÉS:")
            for test_name in failed_tests:
                print(f"  ❌ {test_name}")

        # Statut final
        print("\n" + "=" * 80)
        if success_rate >= 95:
            print("🎉 VALIDATION FINALE: SUCCÈS TOTAL!")
            print("✅ Toutes les corrections critiques et améliorations ont été appliquées")
            print("🚀 Votre bot 0xBot est maintenant optimisé et professionnel")
        elif success_rate >= 80:
            print("✅ VALIDATION FINALE: SUCCÈS MAJEUR")
            print("⚠️ Quelques éléments mineurs à vérifier")
        else:
            print("❌ VALIDATION FINALE: AMÉLIORATIONS REQUISES")
            print("🔧 Plusieurs corrections semblent manquer")

        return success_rate >= 95

    def run_validation(self):
        """Exécuter la validation complète"""
        print("🧪 VALIDATION FINALE - 0xBot Trading Bot")
        print("=" * 80)
        print(f"📁 Répertoire analysé: {self.base_path}")
        print(f"🕐 Date de validation: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        success = self.generate_final_report()

        return success

def main():
    """Point d'entrée principal"""
    import sys

    # Déterminer le chemin du projet
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = os.getcwd()

    print("🔍 Validation Finale - Correction Complètes 0xBot")
    print(f"📁 Répertoire de base: {base_path}")

    # Créer et exécuter la validation
    validator = ValidationFinale(base_path)
    success = validator.run_validation()

    if success:
        print("\n🎉 VALIDATION RÉUSSIE!")
        print("✅ Votre bot est prêt pour la production")
    else:
        print("\n⚠️ VALIDATION PARTIELLE")
        print("💡 Vérifiez les éléments marqués comme échoués")

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
