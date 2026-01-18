# Archived Services

These services were archived on **2026-01-16** because they were not referenced or used anywhere in the codebase. They are kept here for potential future implementation.

## Services in this Directory

### 1. **alerting_service.py**
- **Purpose**: Send alerts (email, Slack, SMS) on trade events
- **Status**: Not integrated into bot
- **Reason for Archive**: No alerting implemented in current pipeline
- **When to Use**: If implementing real-time notifications for trades/errors

### 2. **cache_service.py**
- **Purpose**: Cache market data and calculations
- **Status**: Not used
- **Reason for Archive**: Direct database queries are fast enough in current implementation
- **When to Use**: If bot scales to 100+ symbols or needs to reduce API calls

### 3. **error_recovery_service.py**
- **Purpose**: Auto-recovery from network/database failures
- **Status**: Error handling done inline in each block
- **Reason for Archive**: Not needed for current single-bot architecture
- **When to Use**: If implementing multi-bot clustering or high-availability setup

### 4. **health_check_service.py**
- **Purpose**: Monitor bot health and system metrics
- **Status**: Logging exists but no formal health check service
- **Reason for Archive**: Health monitoring not centralized
- **When to Use**: If implementing bot dashboard or multi-bot monitoring system

### 5. **llm_decision_logger.py**
- **Purpose**: Detailed logging of LLM decisions and reasoning
- **Status**: Logging exists inline in decision blocks
- **Reason for Archive**: Logging is done directly, no separate service needed
- **When to Use**: If implementing detailed decision audit trail for compliance

### 6. **metrics_export_service.py**
- **Purpose**: Export metrics to Prometheus/Grafana
- **Status**: Not integrated
- **Reason for Archive**: Metrics are only logged, not exported
- **When to Use**: If implementing observability dashboard or monitoring

### 7. **performance_monitor.py**
- **Purpose**: Monitor bot performance metrics (win rate, Sharpe ratio, drawdown)
- **Status**: Calculations exist but not aggregated into a service
- **Reason for Archive**: Performance tracking is done ad-hoc
- **When to Use**: If implementing detailed performance analytics or backtesting

### 8. **validation_service.py**
- **Purpose**: Validate trading setup and parameters
- **Status**: Validation done in RiskBlock and TradeFilterService
- **Reason for Archive**: Validation is distributed across blocks
- **When to Use**: If consolidating all validation logic into single service (architectural refactoring)

---

## How to Restore

If you need any of these services:

```bash
git restore src/services/archived/[service_name].py
# OR
mv src/services/archived/[service_name].py src/services/
```

Then integrate it into the appropriate block or service.

---

## Code Cleanup Date

- **Date Archived**: 2026-01-16
- **Reason**: Codebase audit identified 0 references to these services
- **Audit Report**: See `/CODEBASE_AUDIT.md` Issue #7

## Future Improvements

These services represent good future features:

1. **Alerting** → Critical for production deployment
2. **Caching** → Important if scaling to many symbols
3. **Error Recovery** → Essential for robustness
4. **Health Checks** → Needed for multi-bot management
5. **Detailed Logging** → Good for debugging
6. **Metrics Export** → Necessary for observability
7. **Performance Monitoring** → Great for optimization
8. **Validation Service** → Good architectural consolidation

Consider implementing them in this order of priority when scaling or moving to production.
