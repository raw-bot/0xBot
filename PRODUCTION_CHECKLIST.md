# 0xBot Production Checklist

## Before Going Live

### Security

- [ ] Remove XRP from trading symbols (worst performer, R/R = 0.98:1)
- [ ] Tighten CORS origins (currently "\*")
- [ ] Verify .env is in .gitignore

### Configuration Decisions

- [ ] **Leverage dynamique** : Considérer de laisser le LLM suggérer le leverage (1x-5x pour LONG, 1x-3x pour SHORT) au lieu du fixe actuel. Cela permettrait d'adapter le risque aux conditions de marché.

### Testing

- [ ] Analyze 30+ days of paper trading results
- [ ] Verify win rate > 40% on all kept assets
- [ ] Confirm R/R ratio > 1.5:1 on all assets
