# 0xBot Improvement Roadmap (Audit-Prioritized)

**Based on AUDIT_REPORT.md findings - January 18, 2026**

---

## Executive Summary

This roadmap is **re-prioritized by audit scores** to address the most critical gaps first:

1. **Security (2/10) 🔴** - Exposed secrets, public database access
2. **Testing (2/10) 🔴** - Only 0.46% code coverage
3. **DevOps (3/10) 🔴** - Manual deployment, no CI/CD
4. **Reliability (5/10) 🟠** - Weak error recovery
5. **Performance (6/10) 🟠** - NullPool scalability bottleneck
6. **Code Quality (6/10) 🟠** - Type safety gaps, monolithic services
7. **Database (7/10) ✓** - Good schema, monitor only
8. **Enterprise (Optional)** - RBAC, advanced risk management

---

## Milestone 1: Critical Security Hardening

**Overall Score: 2/10** 🔴
**Timeline: 2-3 weeks**
**Blocker for Production**: YES

### Phase 1.1: Emergency Security Fixes (48 hours)

**Goal**: Revoke exposed secrets and remove public access vulnerabilities.

**Tasks**:
- [ ] Revoke all exposed API keys (OKX, DeepSeek, CryptoCompare)
- [ ] Change database password from `postgres:postgres`
- [ ] Remove `.env` from git history using BFG
- [ ] Add Redis `requirepass` authentication
- [ ] Remove port mappings (5432, 6379) or add firewall rules
- [ ] Verify no hardcoded secrets remain

**Success Criteria**:
- All API keys revoked
- `.env` removed from git history
- Database password changed
- Zero exposed secrets found via grep
- Redis requires authentication

**Effort**: 4-6 hours

---

### Phase 1.2: API & Authentication Hardening (1 week)

**Goal**: Secure API endpoints and authentication mechanisms.

**Tasks**:
- [ ] Replace NullPool mention: CORS restricted to known origins only (not `["*"]`)
- [ ] Remove `unsafe-inline` and `unsafe-eval` from CSP header
- [ ] Reduce JWT expiration from 7 days → 2 hours
- [ ] Add rate limiting to auth endpoints (brute-force protection)
- [ ] Add CSRF token protection to state-changing endpoints
- [ ] Require authentication for `/api/dashboard` endpoint
- [ ] Add request signing for sensitive operations

**Success Criteria**:
- CORS restricted to `localhost:5173`, `localhost:8020` (dev) and specific domain (prod)
- CSP header: no `unsafe-*` directives
- JWT expires in 120 minutes
- Auth endpoints rate-limited (5 attempts/minute per IP)
- CSRF tokens on all POST/PUT/DELETE
- `/api/dashboard` requires valid JWT
- Tests pass, no broken functionality

**Effort**: 8-12 hours

---

### Phase 1.3: Input Validation & Secrets Management (1 week)

**Goal**: Validate all inputs and implement external secrets management.

**Tasks**:
- [ ] Add Pydantic validation for all API inputs
- [ ] Validate trading symbol against ALLOWED_SYMBOLS
- [ ] Add bounds checking on leverage (max 5x), position size (max 50%)
- [ ] Validate LLM outputs against schema before trading
- [ ] Implement external secrets management (environment variables or Vault)
- [ ] Add sanitization for user inputs
- [ ] Add audit logging for all user actions and trades

**Success Criteria**:
- All inputs validated with clear error messages
- LLM outputs validated before trading decisions
- No direct SQL queries (all use ORM)
- Secrets only in environment variables
- Audit log captures: who, what, when, where, why
- 0 security test failures

**Effort**: 12-16 hours

---

## Milestone 2: Comprehensive Test Coverage

**Overall Score: 2/10** 🔴
**Timeline: 3-4 weeks**
**Current Coverage: 0.46%** (61 tests, 13,292 LOC)
**Target: 80%+**

### Phase 2.1: Backend Testing Infrastructure (1 week)

**Goal**: Set up pytest foundation and test critical services.

**Tasks**:
- [ ] Create `conftest.py` with reusable fixtures (database, bot, mocks)
- [ ] Set up pytest-cov for coverage reporting
- [ ] Create database fixtures for transaction-based testing
- [ ] Add fixtures for mock Exchange, LLM, Redis
- [ ] Configure CI integration with coverage thresholds
- [ ] Document testing patterns and conventions

**Success Criteria**:
- conftest.py with 5+ reusable fixtures
- pytest-cov installed and configured
- Coverage reports generated
- CI pipeline runs tests on every commit
- Testing docs complete

**Effort**: 16-20 hours

---

### Phase 2.2: Service Testing (2 weeks)

**Goal**: Achieve 70%+ coverage on critical services.

**Services to test** (priority order):
1. `trade_executor_service.py` - Execute trades, verify fills
2. `market_data_service.py` - Fetch and parse market data
3. `risk_manager_service.py` - Validate risk parameters
4. `position_service.py` - Open/close position logic
5. `market_analysis_service.py` - Technical indicators
6. `kelly_position_sizing_service.py` - Position sizing logic
7. Remaining 15+ services

**Tasks**:
- [ ] Unit tests for each service (happy path + error cases)
- [ ] Mock external dependencies (Exchange, LLM, Redis)
- [ ] Integration tests between services
- [ ] Error scenario testing (API failures, timeouts)
- [ ] Database transaction testing
- [ ] Concurrent operation testing

**Success Criteria**:
- 70%+ coverage on critical 7 services
- All edge cases tested
- Mock patterns established
- Tests run in <2 seconds per service
- Zero flaky tests

**Effort**: 40-50 hours

---

### Phase 2.3: API & Frontend Testing (2 weeks)

**Goal**: Test all endpoints and add frontend test framework.

**Backend API Tests**:
- [ ] Test all route handlers (930 LOC)
- [ ] Authentication/authorization tests
- [ ] Input validation tests
- [ ] Error response tests
- [ ] Rate limiting tests
- [ ] WebSocket connection tests

**Frontend Tests**:
- [ ] Set up Vitest + React Testing Library
- [ ] Component unit tests
- [ ] Integration tests (components + hooks)
- [ ] User interaction tests (form submission, data loading)
- [ ] Error state tests
- [ ] Accessibility tests

**Tasks**:
- [ ] Create pytest-fastapi fixtures for route testing
- [ ] Test all 20+ API endpoints
- [ ] Install Vitest, React Testing Library
- [ ] Test 10 frontend components
- [ ] Set up coverage gates in CI

**Success Criteria**:
- 80%+ coverage on routes (API endpoints)
- 60%+ coverage on frontend components
- E2E test for complete trading cycle
- All critical paths covered
- CI enforces coverage gates

**Effort**: 50-60 hours

---

## Milestone 3: DevOps & CI/CD Pipeline

**Overall Score: 3/10** 🔴
**Timeline: 2 weeks**
**Blocker for Automated Scaling**: YES

### Phase 3.1: GitHub Actions CI Pipeline (1 week)

**Goal**: Automate testing, linting, and security scanning.

**Tasks**:
- [ ] Create `.github/workflows/test.yml` - Run pytest on all PRs
- [ ] Create `.github/workflows/lint.yml` - ESLint, Black, isort checks
- [ ] Create `.github/workflows/security.yml` - npm audit, pip audit, SAST
- [ ] Create `.github/workflows/typecheck.yml` - mypy, TypeScript strict
- [ ] Set up branch protection rules requiring CI pass
- [ ] Add coverage badge to README
- [ ] Configure dependabot for automated dependency updates

**Success Criteria**:
- Tests run automatically on PR
- Lint checks pass before merge
- Security scans detect vulnerabilities
- Type checking enforced
- No broken code merged
- Coverage reports visible

**Effort**: 12-16 hours

---

### Phase 3.2: Production Dockerfile & Secrets (1 week)

**Goal**: Create production-ready containerization with secrets management.

**Tasks**:
- [ ] Create production `Dockerfile` with multi-stage builds
- [ ] Implement non-root user for container security
- [ ] Add image scanning (Trivy)
- [ ] Create `.dockerignore` to exclude test files
- [ ] Implement secrets management (environment variables or Vault)
- [ ] Set up docker-compose for production (PostgreSQL + Redis + App)
- [ ] Add health checks for all services
- [ ] Document deployment process

**Success Criteria**:
- Production image builds successfully
- Image scanned for vulnerabilities
- Image <500MB (optimized)
- Zero secrets in image
- Health checks pass
- Container starts in <5 seconds
- Graceful shutdown on SIGTERM

**Effort**: 16-20 hours

---

### Phase 3.3: Deployment Automation (1 week)

**Goal**: Automated deployment pipeline from git to production.

**Tasks**:
- [ ] Create CD workflow (build, push to registry, deploy)
- [ ] Implement blue-green deployment strategy
- [ ] Create database migration automation
- [ ] Set up rollback procedure
- [ ] Create deployment runbook
- [ ] Set up monitoring/alerts for deployments
- [ ] Document deployment checklist

**Success Criteria**:
- Merge to main → automatic deployment
- Blue-green deployment working
- Rollback possible within 5 minutes
- Zero downtime deployments
- All team members can deploy
- Post-deployment checks pass

**Effort**: 16-20 hours

---

## Milestone 4: Reliability & Error Handling

**Overall Score: 5/10** 🟠
**Timeline: 2-3 weeks**

### Phase 4.1: Error Recovery Patterns (1 week)

**Goal**: Replace catch-all handlers with sophisticated error management.

**Tasks**:
- [ ] Create custom exception hierarchy (ExchangeError, LLMError, DatabaseError, etc.)
- [ ] Implement retry logic with exponential backoff for APIs
- [ ] Add circuit breaker pattern (pybreaker) for failing services
- [ ] Implement graceful degradation (fallback strategies)
- [ ] Add order status verification on exchange
- [ ] Implement timeout handling for all external APIs
- [ ] Replace 171 generic `except Exception:` with specific exception types

**Success Criteria**:
- 0 generic exception handlers
- Retry logic tested
- Circuit breaker prevents cascading failures
- Timeouts configured (<30 seconds for APIs)
- Graceful shutdown works
- Error logs are informative

**Effort**: 24-32 hours

---

### Phase 4.2: Health Checks & Observability (1 week)

**Goal**: Comprehensive observability and health monitoring.

**Tasks**:
- [ ] Implement `/health` endpoint returning service status
- [ ] Health checks for: Database, Redis, Exchange API, LLM API
- [ ] Structured logging with JSON format
- [ ] PII masking in logs (no passwords, keys, email)
- [ ] Request ID tracking for debugging
- [ ] Add Prometheus metrics (trades, latency, errors)
- [ ] Configure Grafana dashboards

**Success Criteria**:
- Health endpoint returns detailed status
- Logs are machine-readable (JSON)
- No sensitive data in logs
- Metrics exported to Prometheus
- Grafana dashboards show system health
- Alerts configured for critical issues

**Effort**: 16-20 hours

---

### Phase 4.3: Database Reliability (1 week)

**Goal**: Ensure database doesn't cause cascading failures.

**Tasks**:
- [ ] Implement connection pooling (QueuePool, not NullPool) 👈 CRITICAL
- [ ] Add deadlock detection and recovery
- [ ] Implement transaction timeout handling
- [ ] Add data archival policy (1-year retention)
- [ ] Document backup/restore procedures
- [ ] Test database failover
- [ ] Monitor slow queries

**Success Criteria**:
- QueuePool configured properly
- Max 100 concurrent connections
- No N+1 queries
- Transaction rollback works
- Backups verified restorable
- Slow query logging enabled

**Effort**: 12-16 hours

---

## Milestone 5: Performance Optimization

**Overall Score: 6/10** 🟠
**Timeline: 2 weeks**

### Phase 5.1: Database Performance (1 week)

**Goal**: Optimize queries and connection management.

**Tasks**:
- [ ] Replace NullPool with QueuePool (enables 100x scaling!)
- [ ] Add indices on bot_id, user_id, symbol, created_at
- [ ] Implement eager loading (selectinload) to prevent N+1
- [ ] Add query profiling and monitoring
- [ ] Optimize dashboard queries (<50ms p95)
- [ ] Implement pagination (limit 100 results default)

**Success Criteria**:
- Database handles 100 bots without exhausting connections
- Query time <50ms (p95)
- No N+1 queries detected
- Dashboard loads in <100ms
- Slow query log shows improvements

**Effort**: 16-20 hours

---

### Phase 5.2: Caching Strategy (1 week)

**Goal**: Implement intelligent caching to reduce API calls.

**Tasks**:
- [ ] Add Redis caching for market data (5-minute TTL)
- [ ] Cache technical indicators (RSI, EMA, MACD)
- [ ] Implement LLM response caching (same market conditions)
- [ ] Add client-side caching (stale-while-revalidate)
- [ ] Implement cache invalidation strategies
- [ ] Monitor cache hit rates

**Success Criteria**:
- Market data cached, not recalculated every cycle
- Cache hit rate >70%
- Indicator calculation time reduced by 50%
- LLM API calls reduced by 30%
- Cache invalidation is reliable

**Effort**: 12-16 hours

---

## Milestone 6: Code Quality & Architecture

**Overall Score: 6/10** 🟠
**Timeline: 3 weeks**

### Phase 6.1: Service Refactoring (1 week)

**Goal**: Break down monolithic services.

**Tasks**:
- [ ] Refactor `trading_engine_service.py` (1118 LOC → 300 LOC each)
- [ ] Remove `services/archived/` directory (8 unused files)
- [ ] Replace global singletons with dependency injection
- [ ] Consolidate duplicate configuration constants
- [ ] Extract reusable patterns into utilities
- [ ] Document service responsibilities

**Success Criteria**:
- No service > 300 LOC
- Archived files deleted
- All services injectable (no globals)
- Configuration centralized
- Service tests passing

**Effort**: 20-24 hours

---

### Phase 6.2: Type Safety & Consistency (1 week)

**Goal**: Enforce type safety across codebase.

**Tasks**:
- [ ] Add type hints to 8 service files missing annotations
- [ ] Standardize type imports (List vs list, Optional vs Union)
- [ ] Add mypy/TypeScript to CI pipeline
- [ ] Remove magic numbers, centralize constants
- [ ] Add comprehensive docstrings (Google-style)
- [ ] Enforce consistent error response formats

**Success Criteria**:
- 100% functions have type hints
- mypy --strict passes
- TypeScript strict mode enabled
- Zero `any` types
- Docstrings complete
- Code style consistent

**Effort**: 16-20 hours

---

### Phase 6.3: Frontend Architecture (1 week)

**Goal**: Improve frontend scalability.

**Tasks**:
- [ ] Migrate to Zustand state management (if Context API is bottleneck)
- [ ] Add React.memo to expensive components
- [ ] Implement code splitting by route
- [ ] Add accessibility attributes (alt text, ARIA)
- [ ] Replace console.log with logger library
- [ ] Add E2E tests for critical flows

**Success Criteria**:
- State management is clean and scalable
- Component re-renders optimized
- Bundle size optimized
- No accessibility violations
- E2E tests passing
- Performance metrics improved

**Effort**: 16-20 hours

---

## Milestone 7: Database Monitoring (Optional but Recommended)

**Overall Score: 7/10** ✓
**Timeline: 1 week**

### Phase 7.1: Query Optimization & Monitoring

**Goal**: Continuous database performance monitoring.

**Tasks**:
- [ ] Enable PostgreSQL slow query logging
- [ ] Set up query analysis and optimization
- [ ] Create data archival job (monthly)
- [ ] Implement query performance dashboard
- [ ] Test migration rollback procedures
- [ ] Document data retention policies

**Success Criteria**:
- Slow queries identified and optimized
- Data archival automated
- Migrations reversible
- No query regressions

**Effort**: 8-12 hours

---

## Milestone 8: Enterprise Features (Optional)

**Overall Score: Not Scored Yet**
**Timeline: 4+ weeks (low priority)**

### Phase 8.1: Multi-User & RBAC

**Goal**: Support multiple users with role-based access.

**Tasks**:
- [ ] Implement RBAC: Admin, Trader, Viewer roles
- [ ] Add user organization/team support
- [ ] Implement shared bot templates
- [ ] Add activity audit trails
- [ ] Bot access delegation

**Effort**: 40-50 hours

---

### Phase 8.2: Advanced Risk Management

**Goal**: Enterprise-grade risk controls.

**Tasks**:
- [ ] Portfolio-level risk limits
- [ ] Market regime detection
- [ ] Dynamic position sizing
- [ ] Max loss per trade enforcement

**Effort**: 30-40 hours

---

### Phase 8.3: Performance Analytics

**Goal**: Comprehensive performance tracking.

**Tasks**:
- [ ] Sharpe/Sortino ratio calculations
- [ ] Trade replay and backtesting
- [ ] Performance attribution
- [ ] Compliance reporting

**Effort**: 40-50 hours

---

## Implementation Timeline

```
Week 1-2:   Phase 1 (Security) - CRITICAL
            ├─ 1.1 Emergency fixes (48h)
            ├─ 1.2 API hardening (1 week)
            └─ 1.3 Secrets management (1 week)
                ↓
Week 3-6:   Phase 2 (Testing) - CRITICAL
            ├─ 2.1 Testing infrastructure
            ├─ 2.2 Service testing
            └─ 2.3 API + Frontend testing
                ↓
Week 7-8:   Phase 3 (DevOps) - CRITICAL
            ├─ 3.1 CI pipeline
            ├─ 3.2 Production Docker
            └─ 3.3 Deployment automation
                ↓
Week 9-11:  Phase 4 (Reliability) - PARALLEL with 5
            ├─ 4.1 Error handling
            ├─ 4.2 Health checks
            └─ 4.3 Database reliability
                ↓
Week 9-10:  Phase 5 (Performance) - PARALLEL with 4
            ├─ 5.1 Database optimization (NullPool fix!)
            └─ 5.2 Caching strategy
                ↓
Week 12-14: Phase 6 (Code Quality)
            ├─ 6.1 Service refactoring
            ├─ 6.2 Type safety
            └─ 6.3 Frontend architecture
                ↓
Week 15:    Phase 7 (Database Monitoring) - Optional
                ↓
Week 16+:   Phase 8 (Enterprise) - Optional, low priority
```

---

## Success Criteria per Phase

| Phase | Effort | Done When | Success Metrics |
|-------|--------|-----------|-----------------|
| 1.1 | 4-6h | Keys revoked | Zero exposed secrets |
| 1.2 | 8-12h | Tests pass | Security score: 5/10 |
| 1.3 | 12-16h | Validation complete | Security score: 7/10 |
| 2.1 | 16-20h | Infra ready | Testing framework set up |
| 2.2 | 40-50h | Services tested | 70% coverage on services |
| 2.3 | 50-60h | All tests written | 80%+ overall coverage |
| 3.1 | 12-16h | CI passes | All tests auto-run |
| 3.2 | 16-20h | Image built | No vulns, <500MB |
| 3.3 | 16-20h | First deploy | Zero downtime possible |
| 4.1 | 24-32h | No catch-alls | Custom exceptions used |
| 4.2 | 16-20h | Dashboard created | Health checks working |
| 4.3 | 12-16h | QueuePool running | 100 bots possible |
| 5.1 | 16-20h | Optimized | <50ms queries |
| 5.2 | 12-16h | Cached | 70% cache hit rate |
| 6.1 | 20-24h | Refactored | Max 300 LOC/service |
| 6.2 | 16-20h | Typed | 100% type coverage |
| 6.3 | 16-20h | Optimized | FCP improved by 40% |

---

## Total Effort Estimate

- **Critical Path (Phases 1-5)**: 200-250 hours (5-6 weeks full-time)
- **With Code Quality (Add Phase 6)**: 270-330 hours (6-8 weeks full-time)
- **With Enterprise (Add Phase 8)**: 380-450 hours (9-11 weeks full-time)

---

## Next Action

**Ready to start Phase 1.1: Emergency Security Fixes?**

```bash
/gsd:plan-phase 1.1
```

Or review this roadmap first:
```bash
cat .planning/ROADMAP.md | less
```

---

**Generated**: January 18, 2026
**Based on**: AUDIT_REPORT.md findings (4.6/10 overall health)
**Priority**: Security → Testing → DevOps → Reliability → Performance → Code Quality
