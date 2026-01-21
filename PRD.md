# 🔧 INDICATORS PHASE 2 - MEDIUM EFFORT (Ralph Loop PRD)

**Objective**: Enhance Trinity with squeeze detection + weighted confluence scoring

**Current State** (After Phase 1):
- Trinity Framework: VWAP, EMA-20, True ADX, RSI, Supertrend, Volume, MACD, OBV
- Score: 7.5/10 (significant improvement from 6/10)
- Confidence: 60-85% average
- Position Sizes: $600-800
- Win Rate: ~58% (+8% from baseline)

**Deliverables**:
- Bollinger Bands squeeze detection (volatility compression signals)
- Stochastic RSI integration (intra-candle momentum)
- VWAP Bands dynamic volatility levels
- Weighted confluence system (25% regime, 20% trend, 20% entry, 20% momentum, 10% volume, 5% volatility)
- Adaptive position sizing based on weighted confluence
- All 328+ tests passing with 0 regressions

**Expected Impact**: +3-5% additional win rate improvement (58% → 63%)

**Total After Phase 1+2**: Score 8.5/10

---

## TASK 1: Bollinger Bands Integration (1.5 hours) ✅

**Goal**: Detect volatility squeeze (expansion expected before move)

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Enhance Bollinger Bands
- `backend/src/blocks/block_trinity_decision.py` - Add squeeze detection

**Requirements**:
1. Enhance calculate_bollinger_bands() in IndicatorService
   - Input: close prices, period=20, std_dev=2
   - Output: (upper_band, middle_band, lower_band, bandwidth_ratio)
   - Bandwidth = (upper - lower) / middle
   - Store historical bandwidth to detect squeeze

2. Add squeeze detection signals
   - signals['bollinger_squeeze'] = bandwidth < median_bandwidth * 0.7
   - signals['bollinger_expansion'] = bandwidth > median_bandwidth * 1.3
   - signals['price_near_band'] = abs(price - middle) / (upper - lower) > 0.8
   - Log: "[BOLLINGER] Squeeze: {bool}, Expansion: {bool}, Price near band: {bool}"

3. Integrate into Trinity
   - Squeeze = increased volatility expected (good for trading)
   - Expansion = volatility release (confirm breakout)
   - Add to confluence: confluence_score += signals['bollinger_expansion'] * 15

4. Test
   - pytest backend/tests/services/test_indicator_service.py::test_bollinger_bands
   - Verify squeeze detection logic

**Success Criteria**:
- ✅ Bollinger Bands enhanced
- ✅ Squeeze detection working
- ✅ All tests pass
- ✅ No regressions

---

## TASK 2: Stochastic Integration (1 hour) ✅

**Goal**: Intra-candle overbought/oversold detection

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Add calculate_stochastic()
- `backend/src/blocks/block_trinity_decision.py` - Integrate Stochastic signals

**Requirements**:
1. Add calculate_stochastic() to IndicatorService
   - Use: talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
   - Output: (k_line, d_line, histogram)
   - K < 30: Oversold
   - K > 70: Overbought
   - K-D crossover: Signal change

2. Add Stochastic signals
   - signals['stoch_oversold'] = k_line[-1] < 30
   - signals['stoch_overbought'] = k_line[-1] > 70
   - signals['stoch_bullish_cross'] = (k_line[-1] > d_line[-1] and k_line[-2] <= d_line[-2])
   - Log: "[STOCHASTIC] K: {k:.0f}, D: {d:.0f}, Oversold: {bool}, Cross: {bool}"

3. Integrate into Trinity
   - Oversold + RSI < 40 = strong pullback entry
   - Bullish cross = momentum confirmation
   - Add to confluence: confluence_score += signals['stoch_bullish_cross'] * 10

4. Test
   - pytest backend/tests/services/test_indicator_service.py::test_stochastic
   - Verify K/D values

**Success Criteria**:
- ✅ Stochastic calculated correctly
- ✅ Signals integrated
- ✅ All tests pass
- ✅ No regressions

---

## TASK 3: VWAP Bands (Dynamic Volatility) (45 minutes) ✅

**Goal**: VWAP ± 1 ATR = dynamic support/resistance based on volatility

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Add calculate_vwap_bands()
- `backend/src/blocks/block_trinity_decision.py` - Use VWAP Bands

**Requirements**:
1. Add calculate_vwap_bands() to IndicatorService
   - vwap = existing VWAP
   - atr = existing ATR
   - vwap_upper = vwap + atr
   - vwap_lower = vwap - atr
   - Output: (vwap, vwap_upper, vwap_lower)

2. Add VWAP Bands signals
   - signals['price_above_vwap_upper'] = price > vwap_upper
   - signals['price_below_vwap_lower'] = price < vwap_lower
   - signals['price_in_vwap_band'] = vwap_lower < price < vwap_upper
   - Log: "[VWAP_BANDS] Lower: {lower:.2f}, VWAP: {vwap:.2f}, Upper: {upper:.2f}"

3. Integrate into Trinity
   - Price above VWAP Upper = strong breakout
   - Price below VWAP Lower = strong breakdown
   - Price in band = support/resistance confirmed
   - Add to confluence: confluence_score += signals['price_above_vwap_upper'] * 12

4. Test
   - pytest backend/tests/services/test_indicator_service.py::test_vwap_bands

**Success Criteria**:
- ✅ VWAP Bands calculated
- ✅ Dynamic levels working
- ✅ All tests pass

---

## TASK 4: Weighted Confluence System (2-3 hours) ⭐ CRITICAL ✅

**Goal**: Replace simple sum with intelligent weighted scoring

**Files to Modify**:
- `backend/src/blocks/block_trinity_decision.py` - Implement weighted model

**Requirements**:
1. Define weighting system
   ```
   weight_regime = 0.25        # 25% - Most important (regime filter)
   weight_trend = 0.20         # 20% - Trend confirmation
   weight_entry = 0.20         # 20% - Entry quality
   weight_momentum = 0.20      # 20% - Momentum strength
   weight_volume = 0.10        # 10% - Volume confirmation
   weight_volatility = 0.05    # 5% - Volatility readiness
   ```

2. Replace old confluence calculation
   ```python
   # OLD: confluence_score = sum of signals * weights (0-100 scale)
   
   # NEW: weighted_confluence = (
   #     (signals['regime_met'] * weight_regime) +
   #     (signals['trend_strong'] * weight_trend) +
   #     (signals['entry_valid'] * weight_entry) +
   #     (signals['momentum_positive'] * weight_momentum) +
   #     (signals['volume_confirmed'] * weight_volume) +
   #     (signals['volatility_sufficient'] * weight_volatility)
   # ) * 100  # Scale to 0-100
   ```

3. New confidence scale
   ```
   100% = 6/6 conditions weighted = 10% position
   85% = 5/6 conditions weighted = 8% position
   70% = 4/6 conditions weighted = 6% position
   50% = 3/6 conditions weighted = 4% position
   <50% = NO SIGNAL
   ```

4. Adaptive position sizing
   ```python
   def calculate_position_size(weighted_confidence):
       if weighted_confidence >= 0.95:
           return 0.10  # 10%
       elif weighted_confidence >= 0.80:
           return 0.08  # 8%
       elif weighted_confidence >= 0.65:
           return 0.06  # 6%
       elif weighted_confidence >= 0.50:
           return 0.04  # 4%
       else:
           return 0.00  # No trade
   ```

5. Test
   - pytest backend/tests/blocks/test_trinity_decision.py -v
   - Verify confidence calculation logic
   - Compare old vs new scoring

**Success Criteria**:
- ✅ Weighted confluence working
- ✅ Position sizes reflect confidence
- ✅ Backward compatible with Kelly sizing
- ✅ All tests pass
- ✅ No regressions

---

## TASK 5: Final Validation & Testing (1 hour)

**Goal**: Ensure all Phase 2 improvements working together

**Files to Test**:
- Full Trinity decision block
- All indicator services
- Position sizing logic
- Edge cases

**Requirements**:
1. Run full test suite
   - pytest backend/tests/ -v
   - Ensure 328+ tests passing
   - 0 regressions

2. Validate new signals
   - Log 24 hours of signals
   - Verify Bollinger squeeze detection
   - Verify Stochastic crossovers
   - Verify VWAP Bands usage

3. Compare metrics
   - Old vs New win rate
   - Average position size before/after
   - Confidence distribution

4. Documentation
   - Update PRD with completion summary
   - Document weighted confluence logic
   - Add example trades

**Success Criteria**:
- ✅ All tests passing
- ✅ No regressions
- ✅ New signals verified
- ✅ Metrics improved
- ✅ Ready for paper trading

---

## VALIDATION CHECKLIST

After all Phase 2 tasks:

- [x] Bollinger Bands squeeze detection working
- [x] Stochastic K/D crossovers detected
- [x] VWAP Bands dynamic levels calculated
- [x] Weighted confluence scoring implemented
- [x] Position sizing adaptive to confidence
- [ ] All 328+ tests passing (0 regressions)
- [ ] No runtime errors
- [ ] New signals logged for 24+ hours
- [ ] Win rate comparison showing improvement
- [ ] Confidence distribution 60-90% range
- [ ] Ready for Phase 2 paper trading validation

---

## EXPECTED RESULTS

### After Phase 1:
```
Trinity Score: 7.5/10
Confidence: 60-85%
Position Size: $600-800
Win Rate: 58%
```

### After Phase 1+2:
```
Trinity Score: 8.5/10 🚀
Confidence: 70-95% (higher range)
Position Size: $700-1000 (better optimal)
Win Rate: 63% (+5% from Phase 1)
Sharpe Ratio: Improved ~20%
```

---

## ROADMAP

**Phase 1**: Quick Wins (COMPLETED ✅)
- VWAP, True ADX, MACD, OBV
- Result: 6/10 → 7.5/10

**Phase 2**: Medium Effort (THIS PHASE)
- Bollinger, Stochastic, VWAP Bands, Weighted Confluence
- Result: 7.5/10 → 8.5/10

**Phase 3**: Advanced (Optional)
- Ichimoku Cloud, MACD Divergence, Order Flow
- Result: 8.5/10 → 9.5/10

---

## END OF RALPH TASK

When all Phase 2 tasks complete successfully:
- Commit with message starting "feat: Phase 2 Indicators"
- All tests pass (328+)
- Output: <promise>COMPLETE</promise>

