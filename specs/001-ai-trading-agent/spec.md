# AI Trading Agent - Product Specification

## Document Purpose
This specification defines WHAT the AI Trading Agent must do and WHY, 
without prescribing HOW to implement it. Implementation details are in plan.md.

---

## 1. Product Vision

### 1.1 Core Value Proposition
Deploy frontier LLMs (Claude, GPT, DeepSeek, Gemini) as autonomous crypto 
traders managing real capital 24/7 with complete transparency.

### 1.2 Problem Statement
- Manual crypto trading requires 24/7 attention (markets never close)
- Emotional decisions lead to poor trade execution (fear, greed, FOMO)
- Traders miss opportunities during sleep/work hours
- No easy way to test if AI can generate trading alpha

### 1.3 Target Users
- **Primary**: Intermediate/advanced crypto traders wanting AI automation
- **Secondary**: Researchers testing LLM financial capabilities  
- **Tertiary**: Tech-savvy investors seeking passive exposure

---

## 2. User Scenarios & Testing *(mandatory)*

### 🎯 User Story 1: Deploy AI Trader (Priority: P1 - MVP)

**As a** crypto trader  
**I want to** deploy an AI agent with my capital  
**So that** it trades autonomously while I sleep/work

**Why P1**: Core value prop - without this, there's no product.

**Independent Test**: User selects Claude, allocates $1000, starts agent, 
sees ≥1 trade within 24h with AI reasoning visible.

**Acceptance Scenarios**:

1. **Given** I'm authenticated on platform  
   **When** I select "Claude 4.5 Sonnet" and allocate $1000  
   **Then** agent activates and begins market analysis within 3 minutes

2. **Given** my agent is analyzing markets  
   **When** it identifies a high-confidence opportunity  
   **Then** it executes trade and I see position in dashboard with full reasoning

3. **Given** my agent has 3 open positions  
   **When** market conditions change (e.g., BTC drops 5%)  
   **Then** agent manages exits autonomously and updates PnL real-time

4. **Given** I want to stop trading  
   **When** I click "Deactivate Agent"  
   **Then** it closes all positions within 60 seconds and returns to cash

---

### 🎯 User Story 2: Monitor Activity in Real-Time (Priority: P1 - MVP)

**As a** trader with active AI agent  
**I want to** see what my AI is doing and why, in real-time  
**So that** I can trust it with my capital

**Why P1**: Trust = capital allocation. Without transparency, users won't fund.

**Independent Test**: With active agent, dashboard shows: current positions, 
real-time PnL, recent AI analysis, trade history. Updates <5s after any action.

**Acceptance Scenarios**:

1. **Given** my agent analyzed markets 30 seconds ago  
   **When** I open dashboard  
   **Then** I see latest analysis timestamp, key insights, confidence levels

2. **Given** my agent executes a $500 BTC long  
   **When** trade completes  
   **Then** I receive notification within 5 seconds with: asset, direction, 
          size, entry price, reasoning, stop-loss, take-profit

3. **Given** I want to understand a past decision  
   **When** I click on any trade in history  
   **Then** I see complete reasoning, market context at time, outcome

4. **Given** I have 5 open positions  
   **When** I view portfolio  
   **Then** I see real-time: position size, entry price, current price, 
          unrealized PnL, stop-loss, take-profit

---

### 🎯 User Story 3: Customize Risk Parameters (Priority: P2)

**As a** trader with risk preferences  
**I want to** control how aggressively my AI trades  
**So that** it matches my risk tolerance

**Why P2**: Enables both conservative and aggressive traders to use platform.

**Independent Test**: User sets max position size (10%), max drawdown (20%), 
max trades/day (5). Agent respects all constraints in all decisions.

**Acceptance Scenarios**:

1. **Given** I set max position size to 10% of capital  
   **When** agent identifies opportunity  
   **Then** it never allocates >10% to single position

2. **Given** my portfolio is down 15% and max drawdown is 20%  
   **When** agent evaluates new trades  
   **Then** it reduces position sizes and trades more conservatively

3. **Given** I set max 5 trades/day and agent made 5 trades  
   **When** new opportunity appears  
   **Then** agent skips it and waits until next day

4. **Given** I update risk parameters while agent is active  
   **When** changes are saved  
   **Then** they apply immediately to future trades without closing existing

---

### 🎯 User Story 4: Compare AI Models (Priority: P3)

**As a** data-driven trader  
**I want to** run multiple AI models simultaneously  
**So that** I can discover which generates best alpha

**Why P3**: Power user feature that creates stickiness and differentiation.

**Independent Test**: User deploys Claude, GPT-4, DeepSeek, Gemini with $1000 
each. Dashboard shows comparative metrics: win rate, Sharpe, drawdown, PnL.

**Acceptance Scenarios**:

1. **Given** I want to compare models  
   **When** I create 4 agents with $1000 each  
   **Then** all agents operate independently without interference

2. **Given** 4 agents are trading for 7 days  
   **When** I view comparison dashboard  
   **Then** I see side-by-side: total trades, win rate, avg duration, PnL, Sharpe

3. **Given** Claude outperforms others by 15%  
   **When** I increase its capital to $5000  
   **Then** capital updates without stopping other agents

4. **Given** same market drop affects all agents  
   **When** I review model-specific audit trails  
   **Then** I see how different AIs approached same conditions differently

---

### 🎯 User Story 5: Receive Smart Alerts (Priority: P3)

**As a** trader who can't watch 24/7  
**I want to** be notified of significant events only  
**So that** I stay aware without alert fatigue

**Why P3**: Enables awareness without constant monitoring.

**Independent Test**: User receives alerts for: trades >5% capital, PnL changes 
>10% daily, approaching risk limits. No alerts for routine analysis.

**Acceptance Scenarios**:

1. **Given** agent executes trade >5% of capital  
   **When** trade completes  
   **Then** I receive push notification with details

2. **Given** portfolio drops 10% in one day  
   **When** threshold crossed  
   **Then** I'm alerted with drawdown details and agent's plan

3. **Given** my 20% max drawdown limit and portfolio at 18%  
   **When** agent calculates risk  
   **Then** I receive warning before limit hit

4. **Given** I configure custom alert preferences  
   **When** I set thresholds for PnL, position size, volatility  
   **Then** alerts respect my preferences

---

### 🚨 Edge Cases (Critical for Robustness)

1. **Exchange API Down**  
   - Agent must pause trading immediately
   - Log issue with timestamp
   - Alert user via all channels (email, push)
   - Resume automatically when connection restored
   - Never execute trades without confirmation

2. **AI Produces Invalid Trade**  
   - System validates: asset exists, size >minimum, price reasonable
   - Reject invalid trades immediately
   - Alert user with details
   - Log for debugging/model improvement
   - Continue operation normally

3. **Rapid Market Crash** (e.g., -20% in 10 minutes)  
   - Emergency stop-loss overrides AI decisions
   - Close all positions if drawdown velocity >threshold
   - Alert user immediately
   - Require manual re-activation
   - Preserve capital above all

4. **Insufficient Capital**  
   - Agent detects capital below minimum trade size
   - Pause trading automatically
   - Alert user: "Need minimum $X to continue"
   - Resume when capital added

5. **Conflicting AI Signals**  
   - System prioritizes: exit > entry, stop-loss > take-profit
   - Risk management always overrides opportunity
   - Log conflicts for analysis
   - Execute highest-priority action only

6. **Asset Delisting**  
   - Agent auto-liquidates position before delisting
   - Alert user immediately
   - Blacklist asset from future trading
   - Log event with reasoning

7. **Model Version Update**  
   - Track which model version made which trades
   - Notify user of available updates
   - Allow opt-in to new versions (no auto-update)
   - Maintain audit trail across versions

---

## 3. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support ≥4 frontier LLMs: Claude 4.5, GPT-4/5, DeepSeek V3, Gemini 2.5
- **FR-002**: System MUST analyze markets every 3 minutes (configurable 1-60min)
- **FR-003**: System MUST execute trades autonomously without human approval once activated
- **FR-004**: System MUST log complete AI reasoning for every decision (analysis, trades, exits)
- **FR-005**: System MUST provide real-time dashboard: positions, PnL, agent status
- **FR-006**: System MUST support ≥2 crypto exchanges with unified position tracking
- **FR-007**: System MUST enforce risk parameters: max position size %, max drawdown %, trade frequency
- **FR-008**: System MUST calculate real-time PnL (realized and unrealized) per position and portfolio
- **FR-009**: System MUST support position management: entry, exit, stop-loss, take-profit
- **FR-010**: System MUST operate 24/7 with automatic recovery from connection failures
- **FR-011**: System MUST provide searchable audit trail: all trades with timestamps and reasoning
- **FR-012**: Users MUST activate/deactivate agents instantly (<10 seconds)
- **FR-013**: System MUST support capital allocation per agent (min $100, max user-defined)
- **FR-014**: System MUST notify users of significant events via configurable channels
- **FR-015**: System MUST validate all AI outputs before execution (size, price, asset validity)
- **FR-016**: System MUST support paper trading mode (simulated with real market data)
- **FR-017**: System MUST track performance metrics: win rate, Sharpe ratio, max drawdown, total return
- **FR-018**: System MUST handle API rate limits gracefully without missing opportunities
- **FR-019**: System MUST provide emergency stop (halt all trading immediately, close positions)
- **FR-020**: System MUST persist all data with automated backup (positions, history, reasoning)

### Non-Functional Requirements

- **NFR-001**: Trading decisions MUST execute within 5 seconds of AI signal
- **NFR-002**: Dashboard MUST update within 5 seconds of any agent action
- **NFR-003**: System MUST maintain 99.5% uptime during market hours
- **NFR-004**: AI reasoning logs MUST be stored ≥1 year (regulatory compliance)
- **NFR-005**: System MUST handle ≥10 concurrent agents without performance degradation
- **NFR-006**: Market data MUST be <10 seconds old when AI analyzes it
- **NFR-007**: Database MUST auto-backup hourly with point-in-time recovery
- **NFR-008**: API response time MUST be <200ms for dashboard queries (95th percentile)
- **NFR-009**: System MUST encrypt sensitive data (API keys, capital) at rest and in transit

---

## 4. Key Entities (Business Domain)

- **Agent**: Autonomous trading entity (assigned AI model, capital, risk params, status)
- **Trade**: Executed transaction (entry/exit details, reasoning, timestamp, outcome)
- **Position**: Open market exposure (asset, size, entry price, current value, unrealized PnL)
- **Analysis**: AI market assessment (insights, confidence, opportunities, timestamp)
- **Risk Parameters**: User constraints (max position %, max drawdown %, frequency limits)
- **Audit Trail**: Historical record (all decisions, actions, reasoning)
- **Portfolio**: Aggregate view (positions, cash, total PnL, performance metrics)
- **Alert**: User notification (triggered by events, severity level, delivery method)

---

## 5. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users deploy agent and see first autonomous trade within 4 hours
- **SC-002**: System processes 480 analyses/day per agent (every 3min) with 99% success
- **SC-003**: Dashboard loads complete portfolio in <2s with data <5s old
- **SC-004**: 90% of users understand AI reasoning based on audit trail clarity
- **SC-005**: Zero unauthorized trades (all match documented reasoning + risk params)
- **SC-006**: System handles 10 concurrent agents without latency increase
- **SC-007**: Emergency stop halts all trading within 10s across all agents
- **SC-008**: Users can compare 4 models with clear performance visualizations
- **SC-009**: 95% of trades execute <5s after signal with <0.5% slippage
- **SC-010**: Audit trail reconstructs any decision within 30s of query

### Business Metrics

- **BM-001**: Users allocate avg $5,000+ within first month
- **BM-002**: Platform retention >60% after 90 days of operation
- **BM-003**: Multi-model users allocate 3x more capital than single-model
- **BM-004**: 70% transition from paper trading to real money within 30 days
- **BM-005**: Agents demonstrate positive Sharpe ratio over 90-day periods

---

## 6. Technical Constraints

### Must Use
- Real-time data streaming (WebSocket or equivalent)
- LLM APIs with structured output (JSON)
- Crypto exchange APIs (REST + WebSocket)
- Time-series storage for market data
- Job scheduler for guaranteed 3-minute cycles
- Append-only audit logging (immutable)

### Must Not Use
- Accept AI hallucinations (all outputs validated)
- Blocking operations in trading loop
- Unencrypted storage for secrets
- Single point of failure architecture

---

## 7. Open Questions *(require resolution before implementation)*

- **OQ-001**: Which exchanges initially? **Suggest**: Binance + Coinbase (liquidity + US market)
- **OQ-002**: Minimum capital per agent? **Suggest**: $100 (meaningful position sizes)
- **OQ-003**: LLM API cost handling? **Options**: Pass-through / Platform fee / Hybrid
- **OQ-004**: Liability framework for losses? **Require**: Legal review + ToS drafting
- **OQ-005**: Support leverage trading? **Recommend**: No for v1 (high risk/complexity)
- **OQ-006**: Market manipulation detection? **Require**: Compliance review + pattern detection
- **OQ-007**: KYC/AML compliance strategy? **Require**: Legal framework before launch
- **OQ-008**: Trade NFTs or fungible only? **Suggest**: Fungible only for v1
- **OQ-009**: Disaster recovery if exchange hacked? **Require**: Insurance + emergency protocol
- **OQ-010**: Prevent wash trading by AI? **Require**: Pattern detection + circuit breakers

---

## 8. Out of Scope (v1)

- Multi-exchange arbitrage
- Options/derivatives beyond perpetuals
- Social/copy trading features
- Mobile native apps (web-responsive only)
- Custom indicator creation
- Backtesting UI (users can export data)
- Multi-currency support (USD/USDT only)

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-20  
**Status**: Ready for plan.md  
**Next Step**: Create technical implementation plan (plan.md)
```

---

## **🔥 POURQUOI CE FORMAT MARCHE POUR L'IA**
```
✅ Contexte limité (~3000 tokens) = Pas de dépassement
✅ Zéro implémentation = Pas de confusion
✅ User stories testables = IA comprend success
✅ Requirements atomiques = Traçables dans plan.md
✅ Edge cases explicites = IA anticipe les erreurs
✅ Success criteria mesurables = IA peut valider