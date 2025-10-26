# AI Trading Agent

Autonomous AI-powered cryptocurrency trading platform with support for Claude, GPT-4, DeepSeek, and Gemini.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)

### Setup

1. **Clone and navigate to project**
```bash
cd /Users/cube/Documents/00-code/nof1
git checkout 001-ai-trading-agent
```

2. **Start infrastructure services**
```bash
cd docker
docker-compose up -d
```

3. **Setup Backend**
```bash
cd ../backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp ../.env.example ../.env
# Edit .env and add your API keys

# Run database migrations
alembic upgrade head

# Start backend server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Setup Frontend** (in new terminal)
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure

```
nof1/
├── backend/               # Python FastAPI backend
│   ├── src/
│   │   ├── models/       # SQLAlchemy database models
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── core/         # Core utilities (DB, Redis, LLM, Exchange)
│   │   └── middleware/   # Auth, security, error handling
│   ├── alembic/          # Database migrations
│   ├── tests/            # Unit tests
│   └── requirements.txt  # Python dependencies
├── frontend/             # React TypeScript frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   ├── lib/          # Utilities (API client, WebSocket)
│   │   ├── hooks/        # Custom React hooks
│   │   └── contexts/     # React contexts (Auth)
│   └── package.json      # Node dependencies
├── docker/               # Docker Compose configuration
├── docs/                 # Documentation
└── specs/                # Project specifications
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **Database**: PostgreSQL 15 + TimescaleDB
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Auth**: JWT (python-jose)
- **Trading**: CCXT (Binance)
- **Technical Analysis**: TA-Lib
- **LLMs**: Anthropic, OpenAI, DeepSeek APIs

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State**: Zustand
- **UI**: shadcn/ui + Tailwind CSS
- **Charts**: Recharts
- **API**: Axios
- **WebSocket**: Native WebSocket API

## 🎯 Features Implemented

### Phase 1: Setup ✅
- [x] Project structure
- [x] Backend dependencies (FastAPI, SQLAlchemy, Redis, CCXT, LLM clients)
- [x] Frontend dependencies (React, TypeScript, Vite, shadcn/ui)
- [x] Docker Compose (PostgreSQL + Redis)
- [x] Environment configuration
- [x] Linting (Black, mypy, ESLint, Prettier)

### Phase 2: Foundation ✅
- [x] Database models (User, Bot, Position, Trade, LLMDecision, Alert)
- [x] Alembic migrations
- [x] JWT authentication (register, login)
- [x] API client with auto-JWT
- [x] Redis connection manager
- [x] WebSocket connection manager
- [x] Error handling middleware
- [x] Security headers
- [x] Structured logging
- [x] CCXT Exchange client (Binance)
- [x] LLM client interface (Claude, GPT-4, DeepSeek)
- [x] Rate limiting (50 RPM per model)
- [x] React Router + Auth context
- [x] Login/Register pages

### Phase 3: User Story 1 (In Progress)
- [ ] Bot CRUD operations
- [ ] Trading engine with 3-minute cycle
- [ ] Market data service
- [ ] Technical indicators (EMA, RSI, MACD)
- [ ] LLM prompt builder
- [ ] Trade executor
- [ ] Risk manager
- [ ] Bot dashboard UI

## 🔐 Environment Variables

Required in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_agent

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-secret-key-change-in-production

# LLM APIs
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
GEMINI_API_KEY=...

# Exchange APIs
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
```

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Sign in
- `POST /auth/refresh` - Refresh token
- `GET /auth/me` - Get current user

### Bots (Coming in Phase 3)
- `POST /bots` - Create bot
- `GET /bots` - List user's bots
- `GET /bots/{id}` - Get bot details
- `PUT /bots/{id}` - Update bot
- `DELETE /bots/{id}` - Delete bot
- `POST /bots/{id}/start` - Start trading
- `POST /bots/{id}/stop` - Stop trading

### WebSocket
- `ws://localhost:8000/bots/{id}/stream` - Real-time updates

## 🧪 Testing

### Backend
```bash
cd backend
source venv/bin/activate
pytest tests/
```

### Frontend
```bash
cd frontend
npm run lint
npm run build
```

## 📝 Development

### Backend Development
```bash
# Format code
black backend/src

# Type checking
mypy backend/src

# Create migration
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend Development
```bash
# Lint
npm run lint

# Build
npm run build

# Preview build
npm run preview
```

## 🐛 Debugging

### Check Services
```bash
# Check Docker services
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs redis

# Connect to PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/trading_agent

# Connect to Redis
redis-cli
```

## 📖 Documentation

- **Specification**: `specs/001-ai-trading-agent/spec.md`
- **Technical Plan**: `specs/001-ai-trading-agent/plan.md`
- **Tasks**: `specs/001-ai-trading-agent/tasks.md`
- **Implementation Status**: `docs/IMPLEMENTATION_STATUS.md`

## 🎯 Current Status

- **Phase 1**: ✅ 100% Complete (7/7 tasks)
- **Phase 2**: ✅ 100% Complete (19/19 tasks)
- **Phase 3**: 🔄 In Progress (0/23 tasks)
- **Phase 4**: ⏳ Pending (0/16 tasks)

**Total Progress**: 26/120 tasks (21.7%)

## 📄 License

MIT

## 🤝 Contributing

1. Create feature branch: `git checkout -b 001-feature-name`
2. Make changes
3. Run tests
4. Submit pull request