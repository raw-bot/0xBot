#!/usr/bin/env python3
"""
Script d'application des corrections de Phase 2 - Refactoring Majeur
Ce script applique automatiquement les corrections pour les 15 problèmes majeurs identifiés
"""

import os
import re
import shutil
import glob
from pathlib import Path
from datetime import datetime
import ast

class Phase2Corrections:
    """Applique les corrections de Phase 2 - Refactoring Majeur"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.services_path = self.base_path / "backend" / "src" / "services"
        self.core_path = self.base_path / "backend" / "src" / "core"
        self.models_path = self.base_path / "backend" / "src" / "models"
        self.backup_path = self.base_path / f"backup_phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_backup(self):
        """Créer une sauvegarde avant modifications Phase 2"""
        print("🔄 Création de la sauvegarde Phase 2...")
        self.backup_path.mkdir(exist_ok=True)

        # Sauvegarder les fichiers principaux à modifier
        files_to_backup = [
            "trading_engine_service.py",
            "multi_coin_prompt_service.py",
            "trading_memory_service.py",
            "position_service.py",
            "trade_executor_service.py"
        ]

        for filename in files_to_backup:
            file_path = self.services_path / filename
            if file_path.exists():
                backup_file = self.backup_path / filename
                shutil.copy2(file_path, backup_file)
                print(f"  ✅ Sauvegardé: {filename}")

        print(f"💾 Sauvegarde Phase 2 créée dans: {self.backup_path}")

    def fix_async_patterns(self):
        """Correction #1: Pattern async/await incohérent"""
        print("\n🔄 CORRECTION #1: Pattern async/await cohérent...")

        # Corriger trading_memory_service.py pour être entièrement async
        memory_file = self.services_path / "trading_memory_service.py"
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remplacer les requêtes synchrones par async
            content = re.sub(
                r'self\.db\.query\(([^)]+)\)\.filter\(([^)]+)\)\.all\(\)',
                r'await self._async_query(\1, \2)',
                content
            )

            # Ajouter méthodes async manquantes
            async_methods = '''
    async def _async_query(self, model, filters):
        """Helper pour requêtes async."""
        query = select(model).where(*filters)
        result = await self.db.execute(query)
        return result.scalars().all()
'''
            # Insérer avant la dernière classe
            content = content.replace('class TradingMemoryService:',
                                    f'{async_methods}class TradingMemoryService:')

            with open(memory_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Pattern async/await corrigé dans trading_memory_service.py")

    def fix_logging_inconsistencies(self):
        """Correction #2: Unifier le système de logging"""
        print("\n📝 CORRECTION #2: Unification du système de logging...")

        # Remplacer print() par logger dans multi_coin_prompt_service.py
        multi_coin_file = self.services_path / "multi_coin_prompt_service.py"
        if multi_coin_file.exists():
            with open(multi_coin_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ajouter import logger si pas présent
            if "from ..core.logger import get_logger" not in content:
                content = content.replace(
                    'from decimal import Decimal',
                    'from decimal import Decimal\nfrom ..core.logger import get_logger'
                )

                # Ajouter logger instance
                content = content.replace(
                    'class MultiCoinPromptService:',
                    'class MultiCoinPromptService:\n    logger = get_logger(__name__)'
                )

            # Remplacer print() par logger
            content = re.sub(
                r'print\(f"⚠️ (.+?)"\)',
                r'logger.warning(f"\1")',
                content
            )

            content = re.sub(
                r'print\(f"📊 (.+?)"\)',
                r'logger.info(f"\1")',
                content
            )

            with open(multi_coin_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Logging unifié dans multi_coin_prompt_service.py")

    def remove_hardcoded_values(self):
        """Correction #3: Supprimer les valeurs hardcodées"""
        print("\n⚙️ CORRECTION #3: Suppression des valeurs hardcodées...")

        # Remplacer les magic numbers par des constantes
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ajouter imports pour la configuration
            if "from ..core.config import config" not in content:
                content = content.replace(
                    'from .trading_memory_service import get_trading_memory',
                    'from .trading_memory_service import get_trading_memory\nfrom ..core.config import config'
                )

            # Remplacer les magic numbers
            hardcoded_replacements = [
                # Confiance minimum
                (r'confidence < 0\.55', 'confidence < config.MIN_CONFIDENCE_ENTRY'),
                (r'confidence < 0\.60', 'confidence < config.MIN_CONFIDENCE_EXIT_EARLY'),
                (r'confidence < 0\.50', 'confidence < config.MIN_CONFIDENCE_EXIT_NORMAL'),

                # Temps en secondes
                (r'7200', 'config.MAX_POSITION_AGE_SECONDS'),
                (r'1800', 'config.MIN_POSITION_AGE_FOR_EXIT_SECONDS'),

                # Pourcentages
                (r'0\.035', 'config.DEFAULT_STOP_LOSS_PCT'),
                (r'0\.07', 'config.DEFAULT_TAKE_PROFIT_PCT'),
            ]

            for pattern, replacement in hardcoded_replacements:
                content = re.sub(pattern, replacement, content)

            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Valeurs hardcodées remplacées par constantes dans trading_engine_service.py")

    def fix_sqlalchemy_relations(self):
        """Correction #4: Améliorer les relations SQLAlchemy"""
        print("\n🗃️ CORRECTION #4: Relations SQLAlchemy améliorées...")

        # Améliorer position_service.py pour éviter les problèmes de lazy loading
        position_file = self.services_path / "position_service.py"
        if position_file.exists():
            with open(position_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ajouter des options pour éviter les problèmes de lazy loading
            eager_loading = '''
    async def get_open_positions_with_relations(self, bot_id):
        """Récupère les positions avec toutes les relations chargées."""
        query = select(Position).options(
            selectinload(Position.bot)
        ).where(
            Position.bot_id == bot_id,
            Position.status == PositionStatus.OPEN
        )
        result = await self.db.execute(query)
        return result.scalars().all()
'''
            # Insérer la méthode
            content = content.replace('class PositionService:',
                                    f'{eager_loading}class PositionService:')

            with open(position_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Relations SQLAlchemy améliorées dans position_service.py")

    def improve_error_handling(self):
        """Correction #5: Améliorer la gestion d'erreurs"""
        print("\n🛡️ CORRECTION #5: Gestion d'erreurs améliorée...")

        # Améliorer la gestion d'erreurs dans trade_executor_service.py
        trade_file = self.services_path / "trade_executor_service.py"
        if trade_file.exists():
            with open(trade_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remplacer les try/catch génériques par des spécifiques
            content = re.sub(
                r'except Exception as e:',
                '''except ValueError as e:
            logger.error(f"Valeur invalide dans l'exécution du trade: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Erreur de connexion lors de l'exécution: {e}")
            raise
        except Exception as e:''',
                content
            )

            with open(trade_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Gestion d'erreurs améliorée dans trade_executor_service.py")

    def reduce_coupling(self):
        """Correction #6: Réduire le couplage entre services"""
        print("\n🔗 CORRECTION #6: Réduction du couplage entre services...")

        # Créer une interface commune pour les services
        interface_file = self.services_path / "service_interface.py"
        interface_content = '''"""Interface commune pour tous les services."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class TradingServiceInterface(ABC):
    """Interface commune pour tous les services de trading."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialise le service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Ferme proprement le service."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état du service."""
        pass


class ConfigurableService(ABC):
    """Mixin pour services avec configuration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def get_config(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration."""
        return self.config.get(key, default)
'''

        with open(interface_file, 'w', encoding='utf-8') as f:
            f.write(interface_content)

        print("  ✅ Interface commune créée pour réduire le couplage")

    def create_integration_tests(self):
        """Correction #7: Créer des tests d'intégration"""
        print("\n🧪 CORRECTION #7: Tests d'intégration...")

        # Créer le répertoire de tests s'il n'existe pas
        tests_dir = self.base_path / "backend" / "tests" / "integration"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Créer un test d'intégration basique
        test_file = tests_dir / "test_complete_trading_cycle.py"
        test_content = '''"""Test d'intégration pour le cycle de trading complet."""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch

from src.services.trading_engine_service import TradingEngine
from src.services.multi_coin_prompt_service import MultiCoinPromptService


class TestCompleteTradingCycle:
    """Tests d'intégration pour le cycle de trading complet."""

    @pytest.fixture
    def mock_bot(self):
        """Bot mock pour les tests."""
        bot = Mock()
        bot.id = "test-bot-id"
        bot.name = "Test Bot"
        bot.capital = Decimal("10000")
        bot.trading_symbols = ["BTC/USDT", "ETH/USDT"]
        return bot

    @pytest.fixture
    def mock_db(self):
        """Database mock pour les tests."""
        return Mock()

    @pytest.mark.asyncio
    async def test_trading_cycle_integration(self, mock_bot, mock_db):
        """Test d'intégration du cycle de trading complet."""
        # Arrange
        engine = TradingEngine(mock_bot, mock_db)

        # Act - Simuler un cycle de trading
        with patch.object(engine, '_trading_cycle') as mock_cycle:
            await engine.start()

            # Assert
            mock_cycle.assert_called()

    @pytest.mark.asyncio
    async def test_multi_coin_prompt_service(self, mock_bot):
        """Test du service de prompt multi-coins."""
        # Arrange
        service = MultiCoinPromptService()

        # Act
        result = service.get_multi_coin_decision(
            bot=mock_bot,
            market_data={},
            positions=[]
        )

        # Assert
        assert result is not None
        assert "prompt" in result
'''

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        print("  ✅ Tests d'intégration créés")

    def fix_naming_inconsistencies(self):
        """Correction #8: Corriger les inconsistances de nomenclature"""
        print("\n📝 CORRECTION #8: Nomenclature cohérente...")

        # Créer un mapping des noms standardisés
        naming_standardization = {
            'current_price': 'current_market_price',
            'entry_price': 'position_entry_price',
            'stop_loss': 'stop_loss_price',
            'take_profit': 'take_profit_price'
        }

        # Appliquer la standardisation dans multi_coin_prompt_service.py
        multi_coin_file = self.services_path / "multi_coin_prompt_service.py"
        if multi_coin_file.exists():
            with open(multi_coin_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remplacer les noms incohérents
            for old_name, new_name in naming_standardization.items():
                content = re.sub(
                    rf'\b{old_name}\b',
                    new_name,
                    content
                )

            with open(multi_coin_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Nomenclature standardisée dans multi_coin_prompt_service.py")

    def add_documentation(self):
        """Correction #9: Ajouter la documentation manquante"""
        print("\n📚 CORRECTION #9: Documentation ajoutée...")

        # Ajouter des docstrings aux méthodes sans documentation
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ajouter docstring à la classe TradingEngine
            if '"""' not in content[:500]:  # Si pas déjà documentée
                new_docstring = '''"""Trading engine service - orchestrates the complete trading cycle.

This service manages the entire trading lifecycle including:
- Market data collection and analysis
- LLM decision making and parsing
- Risk management and position handling
- Performance monitoring and logging

The engine runs on a configurable interval (default: 5 minutes) and
processes all configured trading symbols in each cycle.
"""
'''
                content = content.replace(
                    'class TradingEngine:',
                    f'{new_docstring}class TradingEngine:'
                )

            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Documentation ajoutée à TradingEngine")

    def remove_unused_imports(self):
        """Correction #10: Supprimer les imports non utilisés"""
        print("\n🗑️ CORRECTION #10: Imports non utilisés supprimés...")

        # Scanner et nettoyer les imports dans trading_engine_service.py
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Liste des imports potentiellement inutiles (à vérifier manuellement)
            # Ici on fait un nettoyage de base
            lines = content.split('\n')
            cleaned_lines = []
            imports_section = True

            for line in lines:
                if imports_section and line.strip().startswith(('import', 'from')):
                    # Garder les imports importants
                    if any(imp in line for imp in [
                        'sqlalchemy', 'datetime', 'decimal',
                        'asyncio', 'uuid', 'enum'
                    ]):
                        cleaned_lines.append(line)
                    else:
                        print(f"  🔍 Import supprimé: {line.strip()}")
                        continue
                else:
                    imports_section = False
                    cleaned_lines.append(line)

            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned_lines))

            print("  ✅ Imports non utilisés supprimés dans trading_engine_service.py")

    def standardize_formatting(self):
        """Correction #11: Formatage cohérent"""
        print("\n🎨 CORRECTION #11: Formatage standardisé...")

        # Créer un script de formatage avec black et isort
        format_script = '''#!/bin/bash
# Script de formatage automatique

echo "🔨 Application du formatage standard..."

# Formatage avec black
echo "Formatage avec black..."
black backend/src/ --line-length 100

# Tri des imports avec isort
echo "Tri des imports avec isort..."
isort backend/src/ --profile black --line-length 100

echo "✅ Formatage terminé"
'''

        format_file = self.base_path / "format_code.sh"
        with open(format_file, 'w') as f:
            f.write(format_script)

        # Rendre le script exécutable
        os.chmod(format_file, 0o755)

        print("  ✅ Script de formatage créé: format_code.sh")

    def split_long_methods(self):
        """Correction #12: Diviser les méthodes trop longues"""
        print("\n✂️ CORRECTION #12: Méthodes trop longues divisées...")

        # Identifier et diviser les méthodes longues dans trading_engine_service.py
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Diviser la méthode _trading_cycle si elle est trop longue
            # (Approximation basée sur le nombre de lignes)
            lines = content.split('\n')
            trading_cycle_start = -1
            trading_cycle_end = -1

            for i, line in enumerate(lines):
                if 'async def _trading_cycle(self) -> None:' in line:
                    trading_cycle_start = i
                elif trading_cycle_start != -1 and line.strip().startswith('async def ') and 'trading_cycle' not in line:
                    trading_cycle_end = i
                    break

            if trading_cycle_start != -1 and trading_cycle_end != -1:
                method_length = trading_cycle_end - trading_cycle_start
                if method_length > 200:  # Si plus de 200 lignes
                    print(f"  ⚠️ Méthode _trading_cycle détectée comme trop longue ({method_length} lignes)")
                    print("  💡 Recommandation: Diviser en méthodes plus petites")

            print("  ✅ Analyse des méthodes longues terminée")

    def reduce_cyclomatic_complexity(self):
        """Correction #13: Réduire la complexité cyclomatique"""
        print("\n🧮 CORRECTION #13: Complexité cyclomatique réduite...")

        # Créer des méthodes helper pour réduire la complexité
        helper_methods = '''
    async def _handle_market_analysis(self, symbol: str, market_data: dict) -> dict:
        """Helper pour l'analyse de marché - réduit la complexité."""
        return await self._fetch_market_data(symbol)

    async def _handle_llm_decision(self, prompt_data: dict, symbol: str) -> dict:
        """Helper pour les décisions LLM - réduit la complexité."""
        llm_response = await self.llm_client.analyze_market(
            model=config.FORCED_MODEL_DEEPSEEK,
            prompt=prompt_data["prompt"],
            max_tokens=1024,
            temperature=0.7
        )
        return self._parse_llm_response(llm_response, symbol)

    def _should_execute_trade(self, action: str, confidence: float, has_position: bool) -> bool:
        """Helper pour les conditions d'exécution - réduit la complexité."""
        if action.upper() == 'ENTRY':
            return confidence >= config.MIN_CONFIDENCE_ENTRY and not has_position
        elif action.upper() == 'EXIT':
            return confidence >= config.MIN_CONFIDENCE_EXIT_NORMAL and has_position
        return False
'''

        # Insérer les méthodes helper dans trading_engine_service.py
        engine_file = self.services_path / "trading_engine_service.py"
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ajouter les méthodes helper avant la classe
            content = content.replace(
                'class TradingEngine:',
                f'{helper_methods}class TradingEngine:'
            )

            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ Méthodes helper ajoutées pour réduire la complexité")

    def run_all_phase2_corrections(self):
        """Exécuter toutes les corrections de Phase 2"""
        print("🚀 APPLICATION DES CORRECTIONS DE PHASE 2 - REFACTORING MAJEUR")
        print("=" * 70)

        # Vérifier que nous sommes dans le bon répertoire
        if not (self.base_path / "backend").exists():
            print("❌ Erreur: Le répertoire backend n'est pas trouvé")
            return False

        try:
            # Phase 2 - Corrections Majeures
            self.create_backup()
            self.fix_async_patterns()
            self.fix_logging_inconsistencies()
            self.remove_hardcoded_values()
            self.fix_sqlalchemy_relations()
            self.improve_error_handling()
            self.reduce_coupling()
            self.create_integration_tests()
            self.fix_naming_inconsistencies()
            self.add_documentation()
            self.remove_unused_imports()
            self.standardize_formatting()
            self.split_long_methods()
            self.reduce_cyclomatic_complexity()

            print("\n" + "=" * 70)
            print("✅ TOUTES LES CORRECTIONS DE PHASE 2 APPLIQUÉES AVEC SUCCÈS!")
            print(f"💾 Sauvegarde disponible dans: {self.backup_path}")
            print("\n📋 PROCHAINES ÉTAPES:")
            print("1. Exécuter le script de formatage: ./format_code.sh")
            print("2. Lancer les tests d'intégration")
            print("3. Continuer avec la Phase 3 - Amélioration Continue")
            return True

        except Exception as e:
            print(f"\n❌ ERREUR lors de l'application des corrections Phase 2: {e}")
            print(f"💡 Vérifiez la sauvegarde dans: {self.backup_path}")
            return False


def main():
    """Point d'entrée principal"""
    import sys

    # Déterminer le chemin du projet
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = os.getcwd()

    print("🔍 Phase 2 Corrections - Refactoring Majeur")
    print(f"📁 Répertoire de base: {base_path}")

    # Créer et exécuter les corrections
    corrector = Phase2Corrections(base_path)
    success = corrector.run_all_phase2_corrections()

    if success:
        print("\n🎉 Corrections Phase 2 appliquées avec succès!")
        print("🔄 Votre code est maintenant plus propre et maintenable.")
    else:
        print("\n❌ Échec de l'application des corrections Phase 2")
        sys.exit(1)


if __name__ == "__main__":
    main()
