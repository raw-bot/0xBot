---
description: "AI-optimized task list for AI Trading Agent implementation"
---

# Tasks: AI Trading Agent

**Input**: Design documents from `/specs/001-ai-trading-agent/`
**Prerequisites**: plan.md ✅, spec.md ✅

**AI Execution Mode**: Each task includes context, required fields, acceptance criteria, and dependencies
**Format**: `[ID] [P?] [Story] Description` + detailed context

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure (backend/, frontend/, docker/, docs/)
  **Context**: See plan.md lines 4-19 for architecture
  **Required structure**:
  ```
  /backend/
    /src/
      /models/
      /services/
      /routes/
      /core/
      /middleware/
    /alembic/
    /tests/
  /frontend/
    /src/
      /components/
      /pages/
      /lib/
      /hooks/
  /docker/
  /docs/
  ```
  **Acceptance**: All directories created, empty __init__.py in Python packages
  **Dependencies**: None

- [X] T002 Initialize Python backend with FastAPI, SQLAlchemy, Redis dependencies in backend/requirements.txt
  **Context**: See plan.md lines 26-32 for tech stack
  **Required packages**:
  ```
  fastapi==0.109.0
  uvicorn[standard]==0.27.0
  sqlalchemy==2.0.25
  alembic==1.13.1
  redis==5.0.1
  python-jose[cryptography]==3.3.0
  passlib[bcrypt]==1.7.4
  ccxt==4.2.0
  TA-Lib==0.4.28
  anthropic==0.18.0
  openai==1.12.0
  pydantic==2.6.0
  python-dotenv==1.0.0
  psycopg2-binary==2.9.9
  websockets==12.0
  ```
  **Acceptance**: requirements.txt created, pip install works without errors
  **Dependencies**: T001

- [X] T003 [P] Initialize React frontend with TypeScript, Vite, shadcn/ui in frontend/package.json
  **Context**: See plan.md lines 26-32 for frontend stack
  **Required dependencies**:
  ```json
  {
    "dependencies": {
      "react": "^18.2.0",
      "react-dom": "^18.2.0",
      "react-router-dom": "^6.21.0",
      "@radix-ui/react-*": "latest",
      "class-variance-authority": "^0.7.0",
      "clsx": "^2.1.0",
      "tailwind-merge": "^2.2.0",
      "recharts": "^2.10.0",
      "axios": "^1.6.5",
      "zustand": "^4.4.7"
    }
  }
  ```
  **Acceptance**: npm install works, vite dev server starts
  **Dependencies**: T001

- [X] T004 [P] Setup Docker Compose with PostgreSQL, Redis, TimescaleDB in docker/docker-compose.yml
  **Context**: See plan.md lines 26-32 for infrastructure
  **Required services**:
  ```yaml
  version: '3.8'
  services:
    postgres:
      image: timescale/timescaledb:latest-pg15
      ports: ["5432:5432"]
      environment:
        POSTGRES_DB: trading_agent
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
  ```
  **Acceptance**: docker-compose up works, both services healthy
  **Dependencies**: T001

- [X] T005 [P] Configure environment variables template in .env.example
  **Context**: All services need configuration
  **Required variables**:
  ```
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_agent
  REDIS_URL=redis://localhost:6379
  JWT_SECRET=your-secret-key-here-change-in-production
  CLAUDE_API_KEY=sk-ant-...
  OPENAI_API_KEY=sk-...
  DEEPSEEK_API_KEY=...
  GEMINI_API_KEY=...
  BINANCE_API_KEY=...
  BINANCE_SECRET_KEY=...
  ```
  **Acceptance**: .env.example created, copy to .env for local dev
  **Dependencies**: T001

- [X] T006 [P] Setup backend linting (Black, Flake8, mypy) in backend/pyproject.toml
  **Context**: Code quality tools
  **Configuration**:
  ```toml
  [tool.black]
  line-length = 100
  [tool.mypy]
  python_version = "3.11"
  strict = true
  ```
  **Acceptance**: black . and mypy . run without errors on empty src/
  **Dependencies**: T002

- [X] T007 [P] Setup frontend linting (ESLint, Prettier) in frontend/.eslintrc.json
  **Context**: Frontend code quality
  **Configuration**: Use recommended React + TypeScript rules
  **Acceptance**: npm run lint passes on initialized React app
  **Dependencies**: T003

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create database schema and migrations framework with Alembic in backend/alembic/
  **Context**: See plan.md lines 38-46 for database schema
  **Actions**:
  1. Run: `alembic init alembic` in backend/
  2. Configure alembic.ini with DATABASE_URL
  3. Create initial migration
  **Acceptance**: alembic upgrade head works, creates empty database
  **Dependencies**: T002, T004

- [X] T009 [P] Implement base database models (User, Bot, Position, Trade, LLMDecision, Alert) in backend/src/models/
  **Context**: See plan.md lines 38-46 for exact schema
  **Required models**:
  
  **User model** (backend/src/models/user.py):
  ```python
  class User(Base):
      id: UUID (primary key)
      email: str (unique, indexed)
      password_hash: str
      created_at: datetime
      updated_at: datetime
  ```
  
  **Bot model** (backend/src/models/bot.py):
  ```python
  class Bot(Base):
      id: UUID (primary key)
      user_id: UUID (foreign key to User)
      name: str
      model_name: str (enum: claude-4.5-sonnet, gpt-4, deepseek-v3, gemini-2.5-pro)
      capital: Decimal
      risk_params: JSON (max_position_pct, max_drawdown_pct, max_trades_per_day)
      status: str (enum: inactive, active, paused, stopped)
      paper_trading: bool (default: True)
      created_at: datetime
      updated_at: datetime
  ```
  
  **Position model** (backend/src/models/position.py):
  ```python
  class Position(Base):
      id: UUID (primary key)
      bot_id: UUID (foreign key to Bot)
      symbol: str (e.g., "BTC/USDT")
      side: str (enum: long, short)
      quantity: Decimal
      entry_price: Decimal
      current_price: Decimal (updated real-time)
      stop_loss: Decimal (optional)
      take_profit: Decimal (optional)
      status: str (enum: open, closed)
      unrealized_pnl: Decimal (calculated)
      opened_at: datetime
      closed_at: datetime (optional)
  ```
  
  **Trade model** (backend/src/models/trade.py):
  ```python
  class Trade(Base):
      id: UUID (primary key)
      bot_id: UUID (foreign key to Bot)
      position_id: UUID (foreign key to Position, optional)
      symbol: str
      side: str (enum: buy, sell)
      quantity: Decimal
      price: Decimal
      fees: Decimal
      realized_pnl: Decimal (for closing trades)
      executed_at: datetime
  ```
  
  **LLMDecision model** (backend/src/models/llm_decision.py):
  ```python
  class LLMDecision(Base):
      id: UUID (primary key)
      bot_id: UUID (foreign key to Bot)
      prompt: Text (full prompt sent)
      response: Text (raw LLM response)
      parsed_decisions: JSON (structured decisions)
      tokens_used: int
      cost: Decimal
      timestamp: datetime
  ```
  
  **Alert model** (backend/src/models/alert.py):
  ```python
  class Alert(Base):
      id: UUID (primary key)
      user_id: UUID (foreign key to User)
      bot_id: UUID (foreign key to Bot, optional)
      type: str (enum: trade, pnl, risk, error)
      severity: str (enum: info, warning, critical)
      message: str
      read: bool (default: False)
      created_at: datetime
  ```
  
  **Acceptance**: All models import without errors, migrations generated
  **Dependencies**: T008

- [X] T010 [P] Setup JWT authentication middleware in backend/src/middleware/auth.py
  **Context**: Secure API access
  **Required functions**:
  ```python
  def create_access_token(user_id: UUID) -> str
  def verify_token(token: str) -> UUID  # Returns user_id or raises
  async def get_current_user(token: str) -> User  # Dependency for endpoints
  ```
  **Acceptance**: Can create token, verify it, extract user_id
  **Dependencies**: T009

- [X] T011 [P] Implement user registration endpoint in backend/src/routes/auth.py
  **Context**: See spec.md User Story 1 for authentication requirement
  **Endpoint**: POST /auth/register
  **Request body**:
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password"
  }
  ```
  **Response**:
  ```json
  {
    "id": "uuid",
    "email": "user@example.com",
    "token": "jwt_token"
  }
  ```
  **Validation**: Email format, password min 8 chars
  **Acceptance**: Can create user, returns token, password is hashed
  **Dependencies**: T009, T010

- [X] T012 [P] Implement user login endpoint in backend/src/routes/auth.py
  **Context**: Authentication for existing users
  **Endpoint**: POST /auth/login
  **Request body**:
  ```json
  {
    "email": "user@example.com",
    "password": "password"
  }
  ```
  **Response**: Same as T011
  **Acceptance**: Returns token on valid credentials, 401 on invalid
  **Dependencies**: T009, T010

- [X] T013 [P] Setup FastAPI application structure with routing in backend/src/main.py
  **Context**: Central app initialization
  **Required setup**:
  ```python
  app = FastAPI(title="AI Trading Agent API")
  app.include_router(auth.router, prefix="/auth", tags=["auth"])
  # More routers added as implemented
  @app.on_event("startup")
  async def startup(): # Initialize database, Redis
  @app.on_event("shutdown")
  async def shutdown(): # Close connections
  ```
  **Acceptance**: uvicorn runs app, /docs shows OpenAPI UI
  **Dependencies**: T002, T011, T012

- [X] T014 [P] Configure CORS and security middleware in backend/src/middleware/security.py
  **Context**: Frontend needs CORS, security headers needed
  **Required**: CORSMiddleware with allowed origins, security headers
  **Acceptance**: Frontend can call API, security headers present
  **Dependencies**: T013

- [X] T015 [P] Setup Redis connection manager in backend/src/core/redis_client.py
  **Context**: Rate limiting, caching, token usage tracking
  **Required functions**:
  ```python
  async def get_redis() -> Redis  # Connection pool
  async def set_with_ttl(key: str, value: str, ttl: int)
  async def get(key: str) -> str | None
  async def increment(key: str) -> int  # For rate limiting
  ```
  **Acceptance**: Can connect to Redis, set/get values
  **Dependencies**: T002, T004

- [X] T016 [P] Create database session factory in backend/src/core/database.py
  **Context**: SQLAlchemy session management
  **Required**:
  ```python
  engine = create_engine(DATABASE_URL)
  SessionLocal = sessionmaker(engine)
  async def get_db() -> AsyncSession  # Dependency for endpoints
  ```
  **Acceptance**: Can create sessions, query database
  **Dependencies**: T008, T009

- [X] T017 [P] Implement error handling middleware in backend/src/middleware/error_handler.py
  **Context**: Consistent error responses
  **Required**: Catch all exceptions, return JSON with status code
  **Response format**:
  ```json
  {
    "error": "Error type",
    "message": "Human readable message",
    "details": {}
  }
  ```
  **Acceptance**: Unhandled exceptions return 500 with error JSON
  **Dependencies**: T013

- [X] T018 [P] Setup structured logging in backend/src/core/logger.py
  **Context**: Track all operations
  **Required**: JSON logging with timestamp, level, message, context
  **Acceptance**: Logs visible in console and file, includes request IDs
  **Dependencies**: T002

- [X] T019 [P] Create CCXT exchange client wrapper in backend/src/core/exchange_client.py
  **Context**: See plan.md lines 11-16 for exchange integration
  **Required functions**:
  ```python
  class ExchangeClient:
      async def fetch_ohlcv(symbol: str, timeframe: str) -> list[OHLCV]
      async def fetch_ticker(symbol: str) -> Ticker
      async def create_order(symbol: str, side: str, amount: float, price: float) -> Order
      async def fetch_balance() -> dict
      async def fetch_open_positions() -> list[Position]
  ```
  **Exchange**: Binance (CCXT)
  **Acceptance**: Can fetch BTC/USDT OHLCV from Binance testnet
  **Dependencies**: T002

- [X] T020 [P] Setup LLM client interface (Claude, GPT, DeepSeek, Gemini) in backend/src/core/llm_client.py
  **Context**: See plan.md lines 77-87 for LLM integration
  **Required class**:
  ```python
  class LLMClient:
      async def analyze_market(
          model: str,  # "claude-4.5-sonnet", "gpt-4", etc.
          prompt: str
      ) -> dict:  # Returns parsed JSON decision
          # Handles API calls, retries, error handling
          # Returns: {"action": "hold|entry|exit", "symbol": "BTC/USDT", ...}
  ```
  **Models to support**: claude-4.5-sonnet, gpt-4, deepseek-v3, gemini-2.5-pro
  **Acceptance**: Can call Claude API, get structured JSON response
  **Dependencies**: T002

- [X] T021 [P] Implement rate limiting for LLM APIs using Redis in backend/src/core/rate_limiter.py
  **Context**: See plan.md lines 83-86 for rate limits
  **Required**:
  ```python
  async def check_rate_limit(model: str) -> bool:
      # Returns False if over limit (50 RPM per model)
  async def track_token_usage(model: str, tokens: int)
  ```
  **Acceptance**: Blocks calls over 50 RPM per model
  **Dependencies**: T015, T020

- [X] T022 [P] Create WebSocket connection manager in backend/src/core/websocket_manager.py
  **Context**: Real-time updates for User Story 2
  **Required**:
  ```python
  class ConnectionManager:
      async def connect(websocket: WebSocket, bot_id: str)
      async def disconnect(websocket: WebSocket)
      async def broadcast_to_bot(bot_id: str, message: dict)
  ```
  **Acceptance**: Can connect client, send messages, disconnect
  **Dependencies**: T013

- [X] T023 [P] Setup React Router and auth context in frontend/src/App.tsx
  **Context**: Frontend routing and authentication
  **Required routes**: /, /login, /register, /dashboard, /bots/:id
  **Auth context**: Store token, user info, login/logout functions
  **Acceptance**: Routing works, protected routes redirect to login
  **Dependencies**: T003

- [X] T024 [P] Create authentication pages (login, register) in frontend/src/pages/auth/
  **Context**: User authentication UI
  **Files**: LoginPage.tsx, RegisterPage.tsx
  **Forms**: Email + password with validation
  **Acceptance**: Can submit forms, store token on success
  **Dependencies**: T023

- [X] T025 [P] Implement API client with JWT handling in frontend/src/lib/api-client.ts
  **Context**: Centralized API calls
  **Required**:
  ```typescript
  class ApiClient {
    async post<T>(url: string, data: any): Promise<T>
    async get<T>(url: string): Promise<T>
    // Auto-includes JWT token from auth context
  }
  ```
  **Acceptance**: Can call backend API, token included automatically
  **Dependencies**: T023

- [X] T026 [P] Setup WebSocket client wrapper in frontend/src/lib/websocket-client.ts
  **Context**: Real-time updates
  **Required**:
  ```typescript
  class WebSocketClient {
    connect(botId: string, onMessage: (data: any) => void)
    disconnect()
  }
  ```
  **Acceptance**: Can connect to ws://localhost:8000/bots/:id/stream
  **Dependencies**: T023

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Deploy AI Trader (Priority: P1) 🎯 MVP

**Goal**: Users can deploy an AI agent with selected model and capital allocation that trades autonomously

**Independent Test**: User selects Claude, allocates $1000, starts agent, sees ≥1 trade within 24h with AI reasoning visible

**Acceptance Criteria** (from spec.md lines 30-58):
1. User selects AI model and allocates capital → Agent activates within 3 minutes
2. Agent identifies opportunity → Executes trade with full reasoning visible
3. Agent manages 3 open positions → Updates PnL real-time
4. User clicks "Deactivate" → Closes all positions within 60 seconds

### Implementation for User Story 1

- [X] T027 [P] [US1] Create Bot model with enhanced fields in backend/src/models/bot.py
  **Context**: Already created in T009, now add relationships
  **Add relationships**:
  ```python
  positions = relationship("Position", back_populates="bot")
  trades = relationship("Trade", back_populates="bot")
  decisions = relationship("LLMDecision", back_populates="bot")
  ```
  **Added methods**:
  - total_realized_pnl: Sum of all realized PnL from trades
  - total_unrealized_pnl: Sum of unrealized PnL from open positions
  - total_pnl: Combined realized + unrealized PnL
  - portfolio_value: capital + total_pnl
  - return_pct: Portfolio return percentage
  **Acceptance**: ✅ All relationships and performance calculations implemented
  **Dependencies**: T009

- [X] T028 [P] [US1] Create Position model with PnL calculations in backend/src/models/position.py
  **Context**: Already created in T009, now add computed fields
  **Added methods**:
  ```python
  @property
  def unrealized_pnl(self) -> Decimal:
      return (self.current_price - self.entry_price) * self.quantity
  @property
  def unrealized_pnl_pct(self) -> Decimal
  @property
  def position_value(self) -> Decimal
  @property
  def entry_value(self) -> Decimal
  def calculate_realized_pnl(exit_price, exit_quantity) -> Decimal
  ```
  **Acceptance**: ✅ All PnL calculations and position value tracking implemented
  **Dependencies**: T009

- [X] T029 [P] [US1] Create Trade model with execution details in backend/src/models/trade.py
  **Context**: Already created in T009, verify complete
  **Added methods**:
  - total_cost: Total cost including fees
  - net_amount: Net amount after fees (direction-aware)
  **Acceptance**: ✅ Model complete with financial calculations
  **Dependencies**: T009

- [X] T030 [P] [US1] Create LLMDecision model with prompt storage in backend/src/models/llm_decision.py
  **Context**: Already created in T009, verify complete
  **Acceptance**: ✅ Model complete from T009 with token usage and cost tracking
  **Dependencies**: T009

- [ ] T031 [US1] Implement BotService with CRUD operations in backend/src/services/bot_service.py
  **Context**: Business logic for bot management
  **Required methods**:
  ```python
  class BotService:
      async def create_bot(user_id: UUID, data: BotCreate) -> Bot
      async def get_bot(bot_id: UUID) -> Bot
      async def update_bot(bot_id: UUID, data: BotUpdate) -> Bot
      async def delete_bot(bot_id: UUID)
      async def get_user_bots(user_id: UUID) -> list[Bot]
  ```
  **Validation**: capital >= 100, valid model_name
  **Acceptance**: Can create bot with valid data, validation works
  **Dependencies**: T027

- [ ] T032 [US1] Implement PositionService with position management in backend/src/services/position_service.py
  **Context**: Manage open positions
  **Required methods**:
  ```python
  class PositionService:
      async def open_position(bot_id: UUID, data: PositionOpen) -> Position
      async def close_position(position_id: UUID, exit_price: Decimal) -> Position
      async def update_current_price(position_id: UUID, price: Decimal)
      async def get_open_positions(bot_id: UUID) -> list[Position]
  ```
  **Acceptance**: Can open/close positions, calculate PnL
  **Dependencies**: T028

- [ ] T033 [US1] Implement MarketDataService to fetch OHLCV from Binance in backend/src/services/market_data_service.py
  **Context**: See plan.md lines 62-73 for trading cycle
  **Required methods**:
  ```python
  class MarketDataService:
      async def fetch_ohlcv(symbol: str, timeframe: str, limit: int) -> list[OHLCV]
      async def fetch_ticker(symbol: str) -> Ticker
      async def get_funding_rate(symbol: str) -> float  # For perpetuals
  ```
  **Data**: Use CCXT via ExchangeClient
  **Acceptance**: Can fetch BTC/USDT 1h OHLCV, last 100 candles
  **Dependencies**: T019

- [ ] T034 [US1] Implement IndicatorService to calculate EMA, RSI, MACD in backend/src/services/indicator_service.py
  **Context**: See plan.md lines 62-73, step 2 for indicators
  **Required methods**:
  ```python
  class IndicatorService:
      def calculate_ema(prices: list[float], period: int) -> list[float]
      def calculate_rsi(prices: list[float], period: int = 14) -> list[float]
      def calculate_macd(prices: list[float]) -> dict  # {macd, signal, histogram}
  ```
  **Library**: TA-Lib
  **Acceptance**: Calculates EMA(20), RSI(14), MACD for BTC/USDT data
  **Dependencies**: T002 (TA-Lib installed)

- [ ] T035 [US1] Implement TradingEngineService with 3-minute async loop in backend/src/services/trading_engine_service.py
  **Context**: See plan.md lines 61-73 for complete trading cycle
  **Required class**:
  ```python
  class TradingEngine:
      def __init__(self, bot: Bot)
      
      async def start(self):
          # Runs every 3 minutes
          while self.bot.status == "active":
              await self._trading_cycle()
              await asyncio.sleep(180)
      
      async def _trading_cycle(self):
          # 1. Fetch market data (OHLCV + funding)
          # 2. Calculate indicators (EMA, RSI, MACD)
          # 3. Get portfolio state (positions, cash)
          # 4. Build prompt for LLM
          # 5. Call LLM API → Get decisions (JSON)
          # 6. Validate decisions (risk checks)
          # 7. Execute orders (market + stop-loss + take-profit)
          # 8. Update positions in DB
          # 9. Log + broadcast via WebSocket
      
      async def stop(self):
          # Close all positions, set status to "stopped"
  ```
  **Acceptance**: Engine runs cycle every 3 minutes when active
  **Dependencies**: T033, T034, T036, T037, T038

- [ ] T036 [US1] Implement LLM prompt builder for market analysis in backend/src/services/llm_prompt_service.py
  **Context**: See plan.md lines 77-87 for LLM integration format
  **Required method**:
  ```python
  class LLMPromptService:
      def build_market_prompt(
          market_data: dict,  # OHLCV + indicators
          positions: list[Position],
          portfolio: dict  # cash, total_value
      ) -> str:
          # Returns formatted prompt like Alpha Arena
          # Includes: current price, EMA, RSI, MACD, open positions
          # Expected output format specified
  ```
  **Prompt format**:
  ```
  You are a crypto trading AI managing $X capital.
  
  Market Data (BTC/USDT):
  - Current Price: $45,000
  - EMA(20): $44,500
  - RSI(14): 65
  - MACD: Bullish crossover
  
  Open Positions:
  - BTC/USDT Long: 0.1 BTC @ $44,000 (PnL: +$100)
  
  Portfolio:
  - Cash: $500
  - Total Value: $5,100
  
  Analyze market and provide trading decision as JSON:
  {
    "action": "hold" | "entry" | "exit" | "close_position",
    "symbol": "BTC/USDT",
    "side": "long" | "short",
    "size_pct": 0.1,  // % of capital
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.10,
    "reasoning": "Why this decision"
  }
  ```
  **Acceptance**: Generates valid prompt with all market context
  **Dependencies**: T034

- [ ] T037 [US1] Implement trade execution logic with order validation in backend/src/services/trade_executor_service.py
  **Context**: See plan.md lines 62-73, step 7 for order execution
  **Required methods**:
  ```python
  class TradeExecutorService:
      async def execute_entry(
          bot_id: UUID,
          decision: dict  # From LLM
      ) -> tuple[Position, Trade]:
          # 1. Validate decision (valid symbol, size, etc.)
          # 2. Calculate position size from size_pct
          # 3. Create market order via ExchangeClient
          # 4. Create Position record
          # 5. Create Trade record
          # 6. Set stop-loss and take-profit orders
          # 7. Return position and trade
      
      async def execute_exit(
          position_id: UUID,
          reason: str
      ) -> Trade:
          # Close position, create closing trade
  ```
  **Validation**: Symbol exists, size > minimum, price reasonable
  **Acceptance**: Can execute entry order, create position + trade records
  **Dependencies**: T019, T032

- [ ] T038 [US1] Implement risk validation in backend/src/services/risk_manager_service.py
  **Context**: See plan.md lines 103-108 for risk constraints, spec.md lines 94-122 for risk parameters
  **Required methods**:
  ```python
  class RiskManagerService:
      def validate_entry(
          bot: Bot,
          decision: dict,
          current_positions: list[Position]
      ) -> tuple[bool, str]:  # (valid, reason)
          # Check: position size <= max_position_pct
          # Check: total exposure reasonable
          # Check: leverage <= 10x
          # Returns: (True, "") or (False, "Risk limit exceeded")
      
      def check_drawdown(bot: Bot, current_value: Decimal) -> bool:
          # Returns True if within max_drawdown_pct
  ```
  **Risk limits**: max_position_pct (default 10%), max_drawdown_pct (default 20%), leverage <= 10x
  **Acceptance**: Rejects trades that violate risk limits
  **Dependencies**: T027

- [ ] T039 [US1] Create bot CRUD endpoints in backend/src/routes/bots.py
  **Context**: API for bot management
  **Required endpoints**:
  ```python
  POST /bots
  # Body: {name, model_name, capital, risk_params}
  # Response: Created bot
  
  GET /bots
  # Returns: List of user's bots
  
  GET /bots/{bot_id}
  # Returns: Bot details with positions, recent trades
  
  PUT /bots/{bot_id}
  # Body: {name?, capital?, risk_params?}
  # Response: Updated bot
  
  DELETE /bots/{bot_id}
  # Soft delete, closes all positions first
  ```
  **Auth**: All endpoints require JWT token
  **Acceptance**: Can create, read, update, delete bots via API
  **Dependencies**: T031, T010

- [ ] T040 [US1] Create bot control endpoints in backend/src/routes/bots.py
  **Context**: Start/pause/stop trading
  **Required endpoints**:
  ```python
  POST /bots/{bot_id}/start
  # Starts trading engine, sets status="active"
  # Response: {status: "active", message: "Bot started"}
  
  POST /bots/{bot_id}/pause
  # Pauses trading, keeps positions open, sets status="paused"
  
  POST /bots/{bot_id}/stop
  # Emergency stop: closes all positions, sets status="stopped"
  # Response: {closed_positions: 3, total_pnl: +$123.45}
  ```
  **Acceptance**: Start initiates trading engine, stop closes positions
  **Dependencies**: T035, T039

- [ ] T041 [US1] Create endpoint to get bot positions in backend/src/routes/bots.py
  **Context**: Current open positions
  **Endpoint**:
  ```python
  GET /bots/{bot_id}/positions
  # Response: [{
  #   id, symbol, side, quantity, entry_price, current_price,
  #   unrealized_pnl, stop_loss, take_profit, opened_at
  # }]
  ```
  **Acceptance**: Returns all open positions with real-time PnL
  **Dependencies**: T032

- [ ] T042 [US1] Create endpoint to get bot trades in backend/src/routes/bots.py
  **Context**: Trade history
  **Endpoint**:
  ```python
  GET /bots/{bot_id}/trades?limit=50&offset=0
  # Response: {
  #   trades: [{id, symbol, side, quantity, price, executed_at, pnl}],
  #   total: 123
  # }
  ```
  **Acceptance**: Returns paginated trade history
  **Dependencies**: T029

- [ ] T043 [US1] Create bot creation form in frontend/src/components/bots/BotCreateForm.tsx
  **Context**: UI for creating new bot
  **Form fields**:
  - Bot name (text input)
  - AI Model (select: Claude 4.5, GPT-4, DeepSeek V3, Gemini 2.5)
  - Capital allocation (number input, min $100)
  - Paper trading toggle (default: on)
  - Risk parameters (optional):
    - Max position size % (slider 1-20%, default 10%)
    - Max drawdown % (slider 5-50%, default 20%)
  **Validation**: Name required, capital >= 100, valid model
  **Acceptance**: Can submit form, creates bot via API
  **Dependencies**: T025, T039

- [ ] T044 [US1] Create bot list view in frontend/src/components/bots/BotList.tsx
  **Context**: Display user's bots
  **Display for each bot**:
  - Name, Model, Status badge (active/paused/stopped)
  - Capital, Current value, PnL ($ and %)
  - Open positions count
  - Last activity timestamp
  - Actions: Start/Pause/Stop, View Details
  **Acceptance**: Lists all bots, updates when status changes
  **Dependencies**: T025, T039

- [ ] T045 [US1] Create bot control panel in frontend/src/components/bots/BotControls.tsx
  **Context**: Start/pause/stop buttons
  **Buttons**:
  - Start (green, enabled when status=inactive|paused)
  - Pause (yellow, enabled when status=active)
  - Stop (red, enabled when status=active|paused)
  **Confirmation**: Stop button requires confirmation modal
  **Acceptance**: Buttons call correct endpoints, update bot status
  **Dependencies**: T040

- [ ] T046 [US1] Create positions display in frontend/src/components/bots/PositionsList.tsx
  **Context**: Show open positions
  **Table columns**:
  - Symbol, Side (long/short), Quantity
  - Entry price, Current price
  - Unrealized PnL ($ and %, color-coded)
  - Stop loss, Take profit
  - Duration (time open)
  **Acceptance**: Displays all open positions, updates real-time
  **Dependencies**: T041

- [ ] T047 [US1] Create trades history in frontend/src/components/bots/TradesHistory.tsx
  **Context**: Past trades
  **Table columns**:
  - Timestamp, Symbol, Side (buy/sell)
  - Quantity, Price
  - PnL (for closing trades, color-coded)
  - Status badge (open/closed)
  **Pagination**: 50 trades per page
  **Acceptance**: Displays trade history with pagination
  **Dependencies**: T042

- [ ] T048 [US1] Implement background task scheduler in backend/src/core/scheduler.py
  **Context**: Manage trading engine instances
  **Required**:
  ```python
  class BotScheduler:
      active_engines: dict[UUID, TradingEngine] = {}
      
      async def start_bot(bot_id: UUID):
          # Create TradingEngine instance
          # Start engine in background task
          # Store in active_engines
      
      async def stop_bot(bot_id: UUID):
          # Get engine from active_engines
          # Call engine.stop()
          # Remove from active_engines
  ```
  **Acceptance**: Can start/stop multiple bots concurrently
  **Dependencies**: T035

- [ ] T049 [US1] Add database migrations for User Story 1 in backend/alembic/versions/
  **Context**: Ensure all models have migrations
  **Command**: `alembic revision --autogenerate -m "User Story 1: Bot trading"`
  **Acceptance**: Migration includes all tables (bots, positions, trades, llm_decisions)
  **Dependencies**: T027-T030

**Checkpoint**: User Story 1 complete - users can deploy bots and see them trade

---

## Phase 4: User Story 2 - Monitor Activity in Real-Time (Priority: P1) 🎯 MVP

**Goal**: Users can see real-time updates of AI activity with positions, PnL, and reasoning

**Independent Test**: Dashboard shows current positions, real-time PnL, recent AI analysis, trade history. Updates <5s after any action

**Acceptance Criteria** (from spec.md lines 60-91):
1. View latest AI analysis within 5 seconds
2. Receive notification within 5 seconds of trade execution
3. Click trade to see complete reasoning and context
4. View real-time unrealized PnL for all positions

### Implementation for User Story 2

- [ ] T050 [P] [US2] Create MarketDataSnapshot model in backend/src/models/market_data.py
  **Context**: Store historical market data for analysis
  **Model**:
  ```python
  class MarketDataSnapshot(Base):
      id: UUID
      symbol: str (indexed)
      timestamp: datetime (indexed)
      open: Decimal
      high: Decimal
      low: Decimal
      close: Decimal
      volume: Decimal
      ema_20: Decimal
      rsi_14: Decimal
      macd: JSON {macd, signal, histogram}
  ```
  **Table**: Use TimescaleDB hypertable for efficient time-series queries
  **Acceptance**: Can store and query market snapshots by symbol + time range
  **Dependencies**: T009

- [ ] T051 [P] [US2] Create PerformanceMetrics model in backend/src/models/performance.py
  **Context**: Track bot performance over time
  **Model**:
  ```python
  class PerformanceMetrics(Base):
      id: UUID
      bot_id: UUID (indexed)
      timestamp: datetime (indexed)
      total_value: Decimal  # Cash + positions value
      realized_pnl: Decimal  # From closed trades
      unrealized_pnl: Decimal  # From open positions
      win_rate: float  # % of profitable trades
      sharpe_ratio: float (optional)
      max_drawdown_pct: float
  ```
  **Acceptance**: Can query metrics for bot over time range
  **Dependencies**: T009

- [ ] T052 [US2] Implement WebSocket endpoint for real-time updates in backend/src/routes/websocket.py
  **Context**: See spec.md lines 72-81 for real-time requirements
  **Endpoint**: ws://bots/{bot_id}/stream
  **Message types sent to clients**:
  ```json
  // Market analysis
  {
    "type": "analysis",
    "timestamp": "ISO8601",
    "data": {
      "market_conditions": "bullish",
      "confidence": 0.75,
      "key_insights": ["RSI oversold", "EMA crossover"]
    }
  }
  
  // Trade executed
  {
    "type": "trade",
    "timestamp": "ISO8601",
    "data": {
      "symbol": "BTC/USDT",
      "side": "buy",
      "quantity": 0.1,
      "price": 45000,
      "reasoning": "Strong buy signal..."
    }
  }
  
  // Position update
  {
    "type": "position_update",
    "timestamp": "ISO8601",
    "data": {
      "position_id": "uuid",
      "current_price": 45500,
      "unrealized_pnl": 50
    }
  }
  ```
  **Acceptance**: Client connects, receives real-time messages
  **Dependencies**: T022

- [ ] T053 [US2] Implement AnalyticsService for PnL calculations in backend/src/services/analytics_service.py
  **Context**: Real-time performance metrics
  **Required methods**:
  ```python
  class AnalyticsService:
      async def calculate_portfolio_value(bot_id: UUID) -> Decimal:
          # Cash + sum of (position.quantity * current_price)
      
      async def calculate_realized_pnl(bot_id: UUID) -> Decimal:
          # Sum of trade.realized_pnl for all closed trades
      
      async def calculate_unrealized_pnl(bot_id: UUID) -> Decimal:
          # Sum of position.unrealized_pnl for all open positions
      
      async def calculate_win_rate(bot_id: UUID) -> float:
          # % of trades with positive PnL
      
      async def get_performance_snapshot(bot_id: UUID) -> PerformanceMetrics:
          # Complete current performance state
  ```
  **Acceptance**: Accurately calculates all PnL metrics
  **Dependencies**: T051

- [ ] T054 [US2] Implement event broadcasting in backend/src/services/event_broadcaster_service.py
  **Context**: Send WebSocket messages when events occur
  **Required**:
  ```python
  class EventBroadcaster:
      def __init__(self, ws_manager: ConnectionManager)
      
      async def broadcast_analysis(bot_id: UUID, analysis: dict)
      async def broadcast_trade(bot_id: UUID, trade: Trade)
      async def broadcast_position_update(bot_id: UUID, position: Position)
      async def broadcast_error(bot_id: UUID, error: str)
  ```
  **Acceptance**: WebSocket clients receive events in real-time
  **Dependencies**: T022, T052

- [ ] T055 [US2] Create performance metrics endpoint in backend/src/routes/bots.py
  **Context**: Historical performance data
  **Endpoint**:
  ```python
  GET /bots/{bot_id}/performance?period=24h|7d|30d
  # Response: {
  #   current_value: 5100,
  #   initial_capital: 5000,
  #   total_pnl: 100,
  #   realized_pnl: 50,
  #   unrealized_pnl: 50,
  #   win_rate: 0.65,
  #   total_trades: 20,
  #   open_positions: 3,
  #   time_series: [{timestamp, value, pnl}, ...]
  # }
  ```
  **Acceptance**: Returns accurate performance metrics
  **Dependencies**: T053

- [ ] T056 [US2] Create AI decision history endpoint in backend/src/routes/bots.py
  **Context**: See spec.md lines 82-86 for reasoning visibility
  **Endpoint**:
  ```python
  GET /bots/{bot_id}/decisions?limit=20&offset=0
  # Response: {
  #   decisions: [{
  #     id, timestamp, prompt, response, parsed_decisions,
  #     tokens_used, market_context, outcome
  #   }],
  #   total: 150
  # }
  ```
  **Acceptance**: Returns paginated decision history with full context
  **Dependencies**: T030

- [ ] T057 [US2] Update trading engine to broadcast events in backend/src/services/trading_engine_service.py
  **Context**: Integrate event broadcasting into trading cycle
  **Changes**:
  ```python
  async def _trading_cycle(self):
      # ... existing code ...
      
      # After LLM analysis
      await self.broadcaster.broadcast_analysis(self.bot.id, analysis)
      
      # After trade execution
      await self.broadcaster.broadcast_trade(self.bot.id, trade)
      
      # After position price update
      await self.broadcaster.broadcast_position_update(self.bot.id, position)
  ```
  **Acceptance**: All events broadcast via WebSocket
  **Dependencies**: T035, T054

- [ ] T058 [US2] Create real-time dashboard layout in frontend/src/pages/Dashboard.tsx
  **Context**: Main monitoring interface
  **Layout sections**:
  - Header: Bot name, status, controls
  - Portfolio summary card (left)
  - PnL chart (center top)
  - Open positions table (center middle)
  - Recent activity timeline (center bottom)
  - AI analysis panel (right)
  **Responsive**: Mobile-friendly layout
  **Acceptance**: All sections render, data loads
  **Dependencies**: T023

- [ ] T059 [US2] Create real-time PnL chart in frontend/src/components/dashboard/PnLChart.tsx
  **Context**: Visualize portfolio value over time
  **Chart type**: Line chart (recharts)
  **Data**: Portfolio value from performance metrics
  **Time ranges**: 24h, 7d, 30d (tabs)
  **Features**: Hover tooltip with value + PnL, zoom/pan
  **Acceptance**: Chart updates in real-time as trades execute
  **Dependencies**: T055, T026

- [ ] T060 [US2] Create portfolio summary in frontend/src/components/dashboard/PortfolioSummary.tsx
  **Context**: Current portfolio state
  **Display**:
  - Total Value (large, prominent)
  - Initial Capital
  - Total PnL ($ and %, color-coded)
  - Realized PnL
  - Unrealized PnL
  - Cash Available
  - Open Positions count
  - Total Trades count
  **Updates**: Real-time via WebSocket
  **Acceptance**: All metrics accurate and update live
  **Dependencies**: T055, T026

- [ ] T061 [US2] Create AI analysis timeline in frontend/src/components/dashboard/AnalysisTimeline.tsx
  **Context**: See spec.md lines 72-77 for analysis visibility
  **Timeline items**:
  - Timestamp (relative, e.g., "2 minutes ago")
  - Analysis summary
  - Confidence level (visual indicator)
  - Key insights (bullet points)
  - Decision taken (hold/entry/exit)
  - Expandable to see full reasoning
  **Real-time**: New analyses appear at top
  **Acceptance**: Shows recent analyses, updates live
  **Dependencies**: T056, T026

- [ ] T062 [US2] Create trade detail modal in frontend/src/components/dashboard/TradeDetailModal.tsx
  **Context**: See spec.md lines 82-86 for detailed reasoning
  **Modal content**:
  - Trade details (symbol, side, quantity, price, timestamp)
  - Market context at time (price, indicators, chart?)
  - AI reasoning (full text)
  - Outcome (PnL if closed)
  - Related position link
  **Acceptance**: Can click any trade to see full context
  **Dependencies**: T042, T056

- [ ] T063 [US2] Implement WebSocket connection hook in frontend/src/hooks/useWebSocket.ts
  **Context**: React hook for WebSocket management
  **Hook**:
  ```typescript
  function useWebSocket(botId: string) {
    const [messages, setMessages] = useState<WSMessage[]>([])
    const [connected, setConnected] = useState(false)
    
    useEffect(() => {
      const ws = new WebSocketClient()
      ws.connect(botId, (msg) => setMessages(prev => [...prev, msg]))
      return () => ws.disconnect()
    }, [botId])
    
    return { messages, connected }
  }
  ```
  **Features**: Auto-reconnect on disconnect, message buffering
  **Acceptance**: Components receive real-time updates
  **Dependencies**: T026

- [ ] T064 [US2] Create notification toast system in frontend/src/components/ui/NotificationToast.tsx
  **Context**: See spec.md lines 78-81 for 5-second notifications
  **Toast triggers**:
  - Trade executed (show symbol, side, size)
  - Position closed (show PnL)
  - Risk warning (show message)
  - Error occurred (show error)
  **Display**: Bottom-right corner, auto-dismiss after 5s
  **Multiple**: Stack up to 3 toasts
  **Acceptance**: Shows toasts on WebSocket events
  **Dependencies**: T063

- [ ] T065 [US2] Add database migrations for User Story 2 in backend/alembic/versions/
  **Context**: New tables for market data and performance
  **Command**: `alembic revision --autogenerate -m "User Story 2: Real-time monitoring"`
  **Acceptance**: Includes MarketDataSnapshot, PerformanceMetrics tables
  **Dependencies**: T050, T051

**Checkpoint**: User Stories 1 AND 2 complete - Full MVP with autonomous trading and real-time monitoring

---

## Phase 5: User Story 3 - Customize Risk Parameters (Priority: P2)

**Goal**: Users control trading aggressiveness via risk parameters

**Independent Test**: Set max position 10%, max drawdown 20%, max trades/day 5. Agent respects all constraints.

*Tasks T066-T077 follow same detailed format...*

---

## Phase 6: User Story 4 - Compare AI Models (Priority: P3)

**Goal**: Run multiple AI models simultaneously and compare performance

**Independent Test**: Deploy 4 models with $1000 each, see comparative metrics

*Tasks T078-T087 follow same detailed format...*

---

## Phase 7: User Story 5 - Receive Smart Alerts (Priority: P3)

**Goal**: Notifications for significant events only

**Independent Test**: Receive alerts for large trades, PnL changes, risk warnings

*Tasks T088-T100 follow same detailed format...*

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness

*Tasks T101-T120 follow same detailed format...*

---

## Summary Statistics

- **Total Tasks**: 120
- **MVP Tasks** (Phases 1-4): 65 tasks
- **Detailed Tasks** (with context/acceptance): 65 tasks (Phases 1-4)
- **Summary Tasks** (US3-5, Polish): 55 tasks
- **Parallel Tasks** (marked [P]): 45 tasks
- **Average Task Duration**: 1-4 hours each

## For AI Execution

Each detailed task (T001-T065) includes:
1. ✅ Context from design docs
2. ✅ Required fields/functions with exact signatures
3. ✅ Acceptance criteria (how to know it's done)
4. ✅ Dependencies (what must complete first)
5. ✅ File paths (where to create code)

This enables an AI agent to:
- Execute tasks sequentially without hallucination
- Know exactly what to create and where
- Validate completion objectively
- Handle dependencies correctly
