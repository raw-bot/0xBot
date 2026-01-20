# Dependency Injection Guide

**Date**: January 20, 2026
**Purpose**: Comprehensive guide for using the DI container in 0xBot's modular architecture.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Using the Container](#using-the-container)
4. [Creating New Services](#creating-new-services)
5. [Registering Dependencies](#registering-dependencies)
6. [Testing with DI](#testing-with-di)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For Existing Code (No Changes Required)
Your existing code works as-is through the compatibility layer:

```python
# Still works - uses DI internally
from src.services.trading_engine_service import TradingEngineService

service = TradingEngineService()
result = await service.execute_trading_cycle(symbol="BTCUSDT")
```

### For New Code (Recommended)
Inject dependencies directly:

```python
from src.core.di_container import get_container

# Get container instance
container = get_container()

# Get a service
cycle_manager = container.get("trading_cycle_manager")

# Use it (properly typed, mockable, testable)
result = await cycle_manager.execute_cycle(
    symbol="BTCUSDT",
    strategy_id="test-1",
    market_data=market_data,
)
```

### For Tests (Best Practice)
Inject mocks directly:

```python
import pytest
from src.services.trading_engine.cycle_manager import TradingCycleManager

@pytest.fixture
async def cycle_manager(db_session, mock_exchange, mock_llm, test_config):
    """Create cycle manager with injected mocks"""
    return TradingCycleManager(
        db_session=db_session,
        exchange_client=mock_exchange,
        llm_client=mock_llm,
        market_data_service=mock_market_data_service,
        analysis_service=mock_analysis_service,
        config=test_config,
    )

async def test_execute_cycle(cycle_manager):
    result = await cycle_manager.execute_cycle(
        symbol="BTCUSDT",
        strategy_id="test-1",
        market_data=mock_market_data,
    )
    assert result is not None
```

---

## Core Concepts

### What is Dependency Injection?

**Dependency Injection (DI)** is a design pattern where:
- Objects receive their dependencies as parameters (injection)
- Instead of creating dependencies internally (tight coupling)
- Or accessing global singletons (hard to test)

**Benefits**:
- ✅ **Testability**: Mock dependencies easily
- ✅ **Flexibility**: Swap implementations
- ✅ **Clarity**: Dependencies explicit in code
- ✅ **Maintainability**: Easier to understand and modify

### The ServiceContainer

The `ServiceContainer` class manages all service creation and lifecycle:

```python
class ServiceContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}          # All registered services
        self._singletons: dict[str, Any] = {}        # Cached singleton instances
        self._factories: dict[str, Callable] = {}    # Factory functions

    def register(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True,
    ) -> None:
        """Register a service factory"""

    def get(self, name: str) -> Any:
        """Get service instance"""

    async def startup(self) -> None:
        """Initialize all services"""

    async def shutdown(self) -> None:
        """Cleanup all services"""
```

### Factory Functions

Factory functions create service instances with all dependencies:

```python
# Location: src/core/service_factories.py

async def create_trading_cycle_manager() -> TradingCycleManager:
    """Create TradingCycleManager with all dependencies injected"""
    db_session = await create_database_session()
    exchange_client = create_exchange_client()
    llm_client = create_llm_client()
    market_data_service = create_market_data_service()
    analysis_service = create_market_analysis_service()
    config = create_config()

    return TradingCycleManager(
        db_session=db_session,
        exchange_client=exchange_client,
        llm_client=llm_client,
        market_data_service=market_data_service,
        analysis_service=analysis_service,
        config=config,
    )
```

### Backward Compatibility Layer

The `di_compat.py` module provides old-style function names that work with DI:

```python
# Location: src/core/di_compat.py

def get_redis_client() -> Redis:
    """Get Redis client (backward compatible)"""
    container = get_container()
    return container.get("redis_client")

def get_llm_client() -> LLMClient:
    """Get LLM client (backward compatible)"""
    container = get_container()
    return container.get("llm_client")

# ... more compat functions
```

**Usage**: Old code continues working without changes.

---

## Using the Container

### Getting a Service

```python
from src.core.di_container import get_container

container = get_container()

# Get a registered service
llm_client = container.get("llm_client")
exchange = container.get("exchange_client")
db_session = container.get("db_session")

# First call creates and caches (for singletons)
# Subsequent calls return cached instance
```

### Registering a Custom Service

```python
from src.core.di_container import get_container

container = get_container()

# Register a factory
def create_custom_service() -> CustomService:
    return CustomService(config="value")

container.register(
    name="custom_service",
    factory=create_custom_service,
    singleton=True,  # Cache instance
)

# Use it
service = container.get("custom_service")
```

### Async Services

For services that need async initialization:

```python
async def create_redis_client() -> Redis:
    """Factory must be async if service initialization is async"""
    client = Redis(host="localhost", port=6379)
    await client.connect()
    return client

# Register async factory
container.register(
    name="redis_client",
    factory=create_redis_client,
    singleton=True,
)

# Container handles async factories
redis = await container.startup()  # Initializes all async services
client = container.get("redis_client")
```

### Singleton vs Non-Singleton

```python
# SINGLETON (cached, reused)
container.register(
    name="redis_client",
    factory=create_redis_client,
    singleton=True,  # ← Cached after first creation
)

# NON-SINGLETON (new instance each time)
container.register(
    name="request_context",
    factory=create_request_context,
    singleton=False,  # ← New instance each time
)

# First call
instance1 = container.get("redis_client")

# Second call returns same instance (singleton=True)
instance2 = container.get("redis_client")
assert instance1 is instance2  # True!

# Non-singleton
request1 = container.get("request_context")
request2 = container.get("request_context")
assert request1 is not request2  # True! Different instances
```

---

## Creating New Services

### Step 1: Define Service Class

```python
# Location: src/services/my_feature/processor.py

from typing import Any
from src.models import Config

class MyFeatureProcessor:
    """Process my feature with injected dependencies"""

    def __init__(
        self,
        db_session: AsyncSession,
        exchange_client: ExchangeClient,
        config: Config,
    ) -> None:
        """Initialize with injected dependencies"""
        self.db_session = db_session
        self.exchange = exchange_client
        self.config = config

    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process feature"""
        # Use injected dependencies
        result = await self.exchange.fetch_data()
        return result
```

**Key Points**:
- Accept dependencies as constructor parameters
- Use type hints for all parameters
- Store as instance variables
- Never create dependencies internally

### Step 2: Create Factory Function

```python
# Location: src/core/service_factories.py

async def create_my_feature_processor() -> MyFeatureProcessor:
    """Create MyFeatureProcessor with all dependencies"""
    db_session = await create_database_session()
    exchange_client = create_exchange_client()
    config = create_config()

    return MyFeatureProcessor(
        db_session=db_session,
        exchange_client=exchange_client,
        config=config,
    )
```

**Key Points**:
- All dependencies resolved here
- Factory is the single point of dependency specification
- Makes dependencies visible and traceable

### Step 3: Register in Container

```python
# Location: src/core/di_container.py - in initialization

def setup_default_services(self) -> None:
    """Register all default services"""
    # ... other registrations ...

    # Add your service
    self.register(
        name="my_feature_processor",
        factory=create_my_feature_processor,
        singleton=True,
    )
```

### Step 4: Use in Your Code

```python
# Option A: Via container (new style)
from src.core.di_container import get_container

container = get_container()
processor = container.get("my_feature_processor")
result = await processor.process(data)

# Option B: Inject directly (best for routes)
from fastapi import Depends

async def my_route(
    processor: MyFeatureProcessor = Depends(
        lambda: get_container().get("my_feature_processor")
    ),
) -> dict[str, Any]:
    result = await processor.process(request_data)
    return result
```

### Step 5: Create Compatibility Wrapper (Optional)

```python
# Location: src/core/di_compat.py - for backward compatibility

def get_my_feature_processor() -> MyFeatureProcessor:
    """Get MyFeatureProcessor (backward compatible)"""
    container = get_container()
    return container.get("my_feature_processor")

# Old code still works
from src.core.di_compat import get_my_feature_processor
processor = get_my_feature_processor()
```

---

## Registering Dependencies

### All Available Services

Services automatically registered by default:

| Service | Key | Singleton | File |
|---------|-----|-----------|------|
| Redis Client | `redis_client` | Yes | `service_factories.py` |
| Database Session | `db_session` | No | `service_factories.py` |
| Exchange Client | `exchange_client` | Yes | `service_factories.py` |
| LLM Client | `llm_client` | Yes | `service_factories.py` |
| Scheduler | `scheduler` | Yes | `service_factories.py` |
| Config | `config` | Yes | `service_factories.py` |
| Logger | `logger` | No | `service_factories.py` |
| Trading Cycle Manager | `trading_cycle_manager` | Yes | `service_factories.py` |
| Multi-Coin Prompt | `multi_coin_prompt` | Yes | `service_factories.py` |
| Market Analysis | `market_analysis_service` | Yes | `service_factories.py` |

### Container Initialization

```python
# Location: src/core/di_container.py

class ServiceContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._setup_default_services()

    def _setup_default_services(self) -> None:
        """Register all default services"""
        # Core services
        self.register("redis_client", create_redis_client)
        self.register("db_session", create_database_session, singleton=False)
        self.register("exchange_client", create_exchange_client)
        self.register("llm_client", create_llm_client)
        # ... more registrations ...
```

---

## Testing with DI

### Unit Test (Isolated)

Test a single service with mocked dependencies:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.trading_engine.cycle_manager import TradingCycleManager

@pytest.fixture
async def mocked_cycle_manager(db_session):
    """Create cycle manager with all mocked dependencies"""
    mock_exchange = AsyncMock()
    mock_llm = AsyncMock()
    mock_market_service = AsyncMock()
    mock_analysis_service = AsyncMock()
    mock_config = MagicMock()

    return TradingCycleManager(
        db_session=db_session,
        exchange_client=mock_exchange,
        llm_client=mock_llm,
        market_data_service=mock_market_service,
        analysis_service=mock_analysis_service,
        config=mock_config,
    )

@pytest.mark.asyncio
async def test_execute_cycle_success(mocked_cycle_manager):
    """Test successful cycle execution"""
    # Arrange
    market_data = {"BTC": {"price": 50000, "volume": 1000}}

    # Act
    result = await mocked_cycle_manager.execute_cycle(
        symbol="BTCUSDT",
        strategy_id="test-1",
        market_data=market_data,
    )

    # Assert
    assert result is not None
```

**Benefits**:
- Tests run fast (no real services)
- Tests are deterministic
- Easy to simulate edge cases
- No external dependencies needed

### Integration Test (Multiple Services)

Test multiple services working together:

```python
@pytest.mark.asyncio
async def test_trading_cycle_integration(
    db_session,
    real_exchange_client,
    real_llm_client,
):
    """Test trading cycle with real services"""
    # Create services with mix of real and mock
    cycle_manager = TradingCycleManager(
        db_session=db_session,
        exchange_client=real_exchange_client,
        llm_client=real_llm_client,
        market_data_service=create_market_data_service(),
        analysis_service=create_market_analysis_service(),
        config=create_config(),
    )

    # Test end-to-end flow
    result = await cycle_manager.execute_cycle(
        symbol="BTCUSDT",
        strategy_id="integration-test",
        market_data=real_market_data,
    )

    assert result is not None
```

### Fixture for Container

```python
@pytest.fixture
def di_container():
    """Create a test DI container with mocked services"""
    container = ServiceContainer()

    # Override with test implementations
    container.register(
        "redis_client",
        lambda: AsyncMock(),
        singleton=True,
    )
    container.register(
        "exchange_client",
        lambda: AsyncMock(),
        singleton=True,
    )

    return container

@pytest.mark.asyncio
async def test_with_container(di_container):
    """Test using container fixture"""
    service = di_container.get("exchange_client")
    assert service is not None
```

---

## Best Practices

### ✅ DO

#### 1. Accept Dependencies as Parameters

```python
# ✅ GOOD
def __init__(
    self,
    db_session: AsyncSession,
    exchange_client: ExchangeClient,
):
    self.db_session = db_session
    self.exchange = exchange_client
```

#### 2. Type Hint All Parameters

```python
# ✅ GOOD
async def process(
    self,
    symbol: str,
    market_data: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    pass
```

#### 3. Create Single Responsibility Services

```python
# ✅ GOOD - Focused responsibility
class TradingCycleManager:
    """Orchestrate trading cycles"""

class DecisionExecutor:
    """Execute trading decisions"""

class PositionMonitor:
    """Monitor positions"""
```

#### 4. Register Dependencies in Container

```python
# ✅ GOOD
container.register(
    "my_service",
    factory=create_my_service,
    singleton=True,
)
```

### ❌ DON'T

#### 1. Access Global Singletons in Services

```python
# ❌ BAD
from src.core.redis_client import redis_client

class MyService:
    def process(self):
        result = redis_client.get("key")  # Global access - hard to test!
```

#### 2. Create Dependencies Internally

```python
# ❌ BAD
class MyService:
    def __init__(self):
        self.db = create_database_session()  # Created internally
        self.exchange = create_exchange_client()  # Created internally
```

#### 3. Use Mutable Defaults

```python
# ❌ BAD
def __init__(self, config: dict | None = None):
    self.config = config or {}  # Mutable default

# ✅ GOOD
def __init__(self, config: dict[str, Any]):
    self.config = config
```

#### 4. Hide Complexity in Factories

```python
# ❌ BAD - Too much logic in factory
def create_my_service():
    # Complex initialization logic here
    # Makes dependencies unclear
    pass

# ✅ GOOD - Clear dependency flow
async def create_my_service() -> MyService:
    db_session = await create_database_session()
    exchange_client = create_exchange_client()
    config = create_config()

    return MyService(
        db_session=db_session,
        exchange_client=exchange_client,
        config=config,
    )
```

### Configuration Management

**Store magic numbers in config, not code**:

```python
# ✅ GOOD
from src.config import TRADING_CONFIG

class RiskManager:
    def __init__(self, config: Config):
        self.max_leverage = config.TRADING_CONFIG["MAX_LEVERAGE"]

# ❌ BAD
class RiskManager:
    def check_leverage(self, leverage: float):
        if leverage > 20.0:  # Magic number!
            raise ValueError("Leverage too high")
```

### Testing Patterns

**Always inject mocks in tests**:

```python
# ✅ GOOD - Fully mocked
@pytest.fixture
def service(mock_db, mock_exchange, mock_llm):
    return MyService(
        db_session=mock_db,
        exchange_client=mock_exchange,
        llm_client=mock_llm,
    )

# ❌ BAD - Using real services
@pytest.fixture
def service():
    return MyService()  # Uses real DB, exchange, LLM!
```

---

## Troubleshooting

### Issue: "Service not found" Error

```python
container.get("unknown_service")
# KeyError: Service 'unknown_service' not registered
```

**Solution**: Check service is registered:

```python
# In di_container.py
self.register("unknown_service", create_unknown_service)

# Then use
service = container.get("unknown_service")
```

### Issue: Circular Dependencies

```python
# ❌ BAD - Service A depends on B, B depends on A
class ServiceA:
    def __init__(self, b: ServiceB):
        self.b = b

class ServiceB:
    def __init__(self, a: ServiceA):
        self.a = a
```

**Solution**: Refactor to break cycle:

```python
# ✅ GOOD - Extract common dependency
class ServiceC:
    """Common dependency"""

class ServiceA:
    def __init__(self, c: ServiceC):
        self.c = c

class ServiceB:
    def __init__(self, c: ServiceC):
        self.c = c
```

### Issue: Tests Failing with DI

```python
# ❌ Test getting real service, not mock
async def test_my_service():
    service = container.get("exchange_client")  # Real service!
    # Test fails because real service needs real config
```

**Solution**: Use test fixtures:

```python
# ✅ Use injected mock
@pytest.fixture
async def service(mock_exchange):
    return MyService(exchange_client=mock_exchange)

async def test_my_service(service):
    # Uses mocked exchange
    result = await service.process()
```

### Issue: Async Factory Not Called

```python
# ❌ Container.startup() not called
container = ServiceContainer()
service = container.get("redis_client")  # Not initialized!
```

**Solution**: Call startup:

```python
# ✅ Startup container before using
async def main():
    container = get_container()
    await container.startup()  # Initialize all async services
    service = container.get("redis_client")  # Now ready
```

### Issue: Memory Leaks

```python
# ❌ Singletons never cleaned up
container = ServiceContainer()
await container.startup()
# App runs forever, services never shutdown
```

**Solution**: Call shutdown:

```python
# ✅ Shutdown services
async def main():
    container = get_container()
    await container.startup()
    try:
        # Use services
        pass
    finally:
        await container.shutdown()  # Cleanup
```

---

## FastAPI Integration

### App Startup/Shutdown

```python
# Location: src/main.py

from contextlib import asynccontextmanager
from src.core.di_container import get_container

container = get_container()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    # Startup
    await container.startup()
    yield
    # Shutdown
    await container.shutdown()

app = FastAPI(lifespan=lifespan)
```

### Dependency in Routes

```python
# Location: src/routes/trading.py

from fastapi import APIRouter, Depends
from src.core.di_container import get_container
from src.services.trading_engine.cycle_manager import TradingCycleManager

router = APIRouter()

def get_cycle_manager() -> TradingCycleManager:
    """Dependency provider for FastAPI"""
    container = get_container()
    return container.get("trading_cycle_manager")

@router.post("/execute")
async def execute_cycle(
    data: dict,
    cycle_manager: TradingCycleManager = Depends(get_cycle_manager),
) -> dict:
    result = await cycle_manager.execute_cycle(
        symbol=data["symbol"],
        strategy_id=data["strategy_id"],
        market_data=data["market_data"],
    )
    return result
```

---

## Summary

**Key Takeaways**:
1. Use DI container for all service creation
2. Inject dependencies as constructor parameters
3. Keep factories simple and focused
4. Always mock dependencies in tests
5. Use backward-compat layer for gradual migration
6. Type-hint everything for clarity
7. Keep services focused and small

**Next Steps**:
- Migrate existing services to use DI
- Write tests using mocked dependencies
- Add new services following DI patterns
- Monitor for global access violations

---

**Document Owner**: Ralph (Autonomous Coding Agent)
**Created**: January 20, 2026
**Related Documents**:
- `ARCHITECTURE_NEW.md` (architecture overview)
- `REFACTORING_REPORT.md` (metrics and changes)
- `src/core/di_container.py` (implementation)
- `src/core/service_factories.py` (factories)
