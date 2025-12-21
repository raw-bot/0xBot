# Debugging & Testing Recommendations for 0xBot

## Outils Déjà Installés

- ✅ pytest (9.0.2)
- ✅ pytest-asyncio (1.3.0)

## Outils Recommandés à Installer

```bash
pip install pytest-cov      # Coverage reports
pip install mypy            # Static type checking
pip install black           # Auto-formatting
pip install ruff            # Fast linter (replaces flake8)
pip install aiomonitor      # Async debugging in production
```

## Tests Spécifiques pour les Blocs

### 1. Test de Calcul d'Équité

```python
# tests/blocks/test_portfolio_calculations.py
import pytest
from decimal import Decimal
from src.blocks.block_portfolio import PortfolioBlock

@pytest.mark.asyncio
async def test_equity_calculation():
    # cash + invested + unrealized = equity
    pass
```

### 2. Test de Validation Risk

```python
# tests/blocks/test_risk_validation.py
from src.blocks.block_risk import RiskBlock
from src.models.position import PositionSide

def test_exit_conditions_long():
    risk = RiskBlock()
    # Mock position with PositionSide.LONG
    # Verify SL/TP triggers
```

### 3. Debug Mode pour Asyncio

```python
# Add to pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Or enable debug mode
import asyncio
asyncio.run(main(), debug=True)
```

## Configuration Recommandée

### pyproject.toml (add)

```toml
[tool.mypy]
python_version = "3.13"
plugins = ["sqlalchemy.ext.mypy.plugin"]
ignore_missing_imports = true
strict = false

[tool.ruff]
line-length = 88
target-version = "py313"
select = ["E", "F", "W", "I"]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]
```

## Commande pour Lancer les Tests avec Coverage

```bash
cd backend
pytest tests/ -v --cov=src --cov-report=html
```
