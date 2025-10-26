# AI Trading Agent - Technical Plan

## 1. Architecture (High-Level)
```
USER (Browser)
    ↓
FRONTEND (React + WebSocket)
    ↓
API (FastAPI + JWT Auth)
    ↓
TRADING ENGINE (Background Loop)
    ├→ Market Data (Binance API)
    ├→ Indicators (TA-Lib)
    ├→ LLM Client (Claude/GPT/DeepSeek)
    ├→ Order Executor (Exchange API)
    └→ Position Manager
    ↓
DATABASE (PostgreSQL + Redis)
```

**Key Decision**: Single-threaded async loop per bot to avoid race conditions.

---

## 2. Tech Stack
```yaml
Backend:  Python 3.11 + FastAPI + SQLAlchemy + Redis
Frontend: React 18 + TypeScript + Vite + shadcn/ui
Database: PostgreSQL 15 (TimescaleDB for market data)
LLMs:     Anthropic, OpenAI, DeepSeek, Google APIs
Exchange: CCXT library (Binance primary)
Infra:    Docker Compose (dev) → VPS (prod)
```

---

## 3. Database Schema (Core Tables Only)
```sql
users (id, email, password_hash, created_at)
bots (id, user_id, model_name, capital, risk_params, status)
positions (id, bot_id, symbol, quantity, entry_price, stop_loss, take_profit, status)
trades (id, bot_id, position_id, symbol, side, quantity, price, executed_at)
llm_decisions (id, bot_id, prompt, response, parsed_decisions, tokens, timestamp)
market_data_snapshots (symbol, timestamp, ohlc, indicators)
alerts (id, user_id, bot_id, type, message, created_at)
```

---

## 4. API Endpoints (Summary)
```
Auth:       POST /auth/register, /auth/login
Bots:       CRUD /bots, POST /bots/:id/start|pause|stop
Trading:    GET /bots/:id/positions|trades|performance
Decisions:  GET /bots/:id/decisions
WebSocket:  ws://bots/:id/stream (real-time updates)
```

---

## 5. Trading Engine Loop (Every 3 minutes)
```python
async def trading_cycle():
    # 1. Fetch market data (OHLCV + funding)
    # 2. Calculate indicators (EMA, RSI, MACD)
    # 3. Get portfolio state (positions, cash)
    # 4. Build prompt for LLM
    # 5. Call LLM API → Get decisions (JSON)
    # 6. Validate decisions (risk checks)
    # 7. Execute orders (market + stop-loss + take-profit)
    # 8. Update positions in DB
    # 9. Log + broadcast via WebSocket
```

---

## 6. LLM Integration
```python
Models: claude-4.5-sonnet, gpt-4, deepseek-v3, gemini-2.5-pro
Input:  Market data + indicators + positions (formatted like Alpha Arena)
Output: JSON with signals: 'hold' | 'entry/exit' | 'close_position'

Rate Limits: 
- 50 RPM per model
- Track token usage in Redis
- Cache responses in dev (not prod)
```

---

## 7. Implementation Phases

**Phase 1 (2 weeks)**: Core engine - Single bot trades BTC on testnet with Claude  
**Phase 2 (2 weeks)**: Web dashboard - Real-time monitoring + WebSocket  
**Phase 3 (1 week)**: Multi-model - Add GPT/DeepSeek/Gemini support  
**Phase 4 (1 week)**: Production - Monitoring, alerts, backups, deploy to VPS  

**Total**: 6 weeks

---

## 8. Critical Decisions

- **No leverage >10x** in v1 (reduce risk)
- **Paper trading required** before real money
- **Single VPS** for MVP (scale later if needed)
- **Hourly DB backups** to S3
- **Emergency stop** closes all positions immediately

---

**Document Size**: 100 lines ✅  
**Ready for**: task.md generation  
**Next Step**: Break into atomic tasks (1-4h each)
```

---

## **💡 POURQUOI CETTE VERSION EST MEILLEURE**

| Critère | Version longue (500 lignes) | Version courte (100 lignes) |
|---------|---------------------------|----------------------------|
| **Contexte IA** | Overload (hallucinations) | Gérable ✅ |
| **Temps de lecture** | 20 minutes | 3 minutes ✅ |
| **Focus** | Perdu dans les détails | Clair et actionnable ✅ |
| **Maintenance** | Difficile à mettre à jour | Facile ✅ |
| **Pour task.md** | Trop d'infos inutiles | Juste ce qu'il faut ✅ |

---

## **📚 OÙ METTRE LE RESTE ?**

Les 400 lignes que j'ai coupées ne sont PAS perdues, elles vont dans :
```
/docs/
  ├─ architecture.md      ← Diagrammes détaillés
  ├─ database.md          ← Schemas SQL complets + migrations
  ├─ api-reference.md     ← Tous les endpoints avec exemples
  ├─ security.md          ← Encryption, JWT, rate limiting
  ├─ deployment.md        ← Docker, VPS, monitoring
  └─ llm-integration.md   ← Prompts, rate limits, caching