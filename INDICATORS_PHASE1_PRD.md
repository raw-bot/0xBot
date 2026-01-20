# 🚀 INDICATORS PHASE 1 - QUICK WINS (Ralph Loop PRD)

**Objective**: Add 4 critical missing indicators to boost win rate +8%

**Current State**:
- Trinity Framework: SMA-200, EMA-20, ADX (simplified), RSI, Supertrend, Volume
- Score: 6/10 (functional but conservative)
- Problem: Only 1% average confidence, $200 position sizes

**Deliverables**:
- VWAP indicator added (daily support/resistance)
- True ADX replacing simplified version
- MACD activated (momentum confirmation)
- OBV added (accumulation detection)
- Updated confluence model with weighted scoring
- All 328+ tests passing with 0 regressions

**Expected Impact**: +8% win rate (50% → 58%)

---

## TASK 1: Add VWAP Indicator (30 min)

**Goal**: Implement Volume Weighted Average Price for daily confluence levels

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Add calculate_vwap() method
- `backend/src/blocks/block_trinity_decision.py` - Integrate VWAP signal

**Requirements**:
1. Implement calculate_vwap() in IndicatorService
   - Input: List[Dict] of OHLCV candles
   - Output: float (current VWAP value)
   - Formula: Cumulative(TP * Volume) / Cumulative(Volume)
   - TP = (High + Low + Close) / 3
   - Cache with TTL 3600s

2. Integrate into Trinity decision block
   - Add signal: signals['price_above_vwap'] = price > vwap
   - Log: "[VWAP] Price: ${price:.2f}, VWAP: ${vwap:.2f}, Signal: {bool}"
   - Add to confluence: confluence_score += signals['price_above_vwap'] * 20

3. Test
   - pytest backend/tests/services/test_indicator_service.py::test_vwap_calculation
   - Verify logs contain "[VWAP]" entries

**Success Criteria**:
- ✅ VWAP calculates correctly
- ✅ Signal added to Trinity
- ✅ All tests pass
- ✅ No regressions in existing signals

---

## TASK 2: True ADX (Replace Simplified) (1 hour)

**Goal**: Replace simplified ADX (just SMA-200 slope) with real TA-Lib ADX

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Add calculate_adx()
- `backend/src/blocks/block_trinity_decision.py` - Use true ADX

**Requirements**:
1. Add calculate_adx() to IndicatorService
   - Use talib.ADX(high, low, close, timeperiod=14)
   - Return: float (ADX value 0-100)
   - ADX > 25: Strong trend
   - ADX 15-25: Weak trend
   - ADX < 15: Choppy (avoid)

2. Replace in Trinity block
   - Remove: old simplified ADX calculation
   - Add: adx = await self.indicator_service.calculate_adx(...)
   - Add signals:
     * signals['trend_strong'] = adx > 25
     * signals['trend_weak'] = 15 < adx <= 25
     * signals['trend_choppy'] = adx <= 15
   - Log: "[ADX] Value: {adx:.1f}, Strong: {bool}"
   - Add to confluence: confluence_score += signals['trend_strong'] * 20

3. Test
   - pytest backend/tests/services/test_indicator_service.py::test_adx_calculation
   - Verify real ADX vs old simplified

**Success Criteria**:
- ✅ True ADX using TA-Lib
- ✅ Replaces old simplified version
- ✅ All tests pass
- ✅ ADX values make sense (0-100)

---

## TASK 3: Activate MACD (1 hour)

**Goal**: MACD exists but is never used - activate it in Trinity

**Files to Modify**:
- `backend/src/blocks/block_trinity_decision.py` - Integrate MACD signal

**Requirements**:
1. MACD already implemented in IndicatorService
   - Just need to USE it in Trinity block

2. Integrate into Trinity
   - Get MACD: macd_line, signal_line, histogram = await self.indicator_service.get_macd(...)
   - Add signals:
     * signals['macd_positive'] = macd_line[-1] > signal_line[-1]
     * signals['macd_bullish_cross'] = (macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2])
   - Log: "[MACD] Line: {line:.6f}, Signal: {signal:.6f}, Positive: {bool}, Cross: {bool}"
   - Add to confluence: confluence_score += signals['macd_positive'] * 15

3. Test
   - pytest backend/tests/blocks/test_trinity_decision.py -v
   - Verify MACD signals are generated

**Success Criteria**:
- ✅ MACD integrated into Trinity
- ✅ Signals logged correctly
- ✅ All tests pass
- ✅ No regressions

---

## TASK 4: Add OBV (On-Balance Volume) (45 min)

**Goal**: Detect whale accumulation/distribution with OBV

**Files to Modify**:
- `backend/src/services/indicator_service.py` - Add calculate_obv()
- `backend/src/blocks/block_trinity_decision.py` - Integrate OBV signal

**Requirements**:
1. Add calculate_obv() to IndicatorService
   - Input: List[Dict] of OHLCV candles
   - Output: Tuple[float, float, bool] = (current_obv, obv_ma, obv_trending)
   - Logic:
     * If close > prev_close: obv += volume
     * If close < prev_close: obv -= volume
     * If close == prev_close: obv stays same
   - OBV_MA: 14-period moving average
   - obv_trending = current_obv > obv_ma

2. Integrate into Trinity
   - Get OBV: current_obv, obv_ma, obv_trending = await self.indicator_service.calculate_obv(...)
   - Add signal: signals['obv_accumulating'] = obv_trending
   - Log: "[OBV] Current: {obv:.0f}, MA: {obv_ma:.0f}, Accumulating: {bool}"
   - Add to confluence: confluence_score += signals['obv_accumulating'] * 10

3. Test
   - pytest backend/tests/services/test_indicator_service.py::test_obv_calculation
   - Verify OBV calculation logic

**Success Criteria**:
- ✅ OBV calculates correctly
- ✅ Signal added to Trinity
- ✅ All tests pass
- ✅ No regressions

---

## TASK 5: Update Confluence Model (Integrated)

**Goal**: Apply weighted scoring across all 4 new signals

**Files to Modify**:
- `backend/src/blocks/block_trinity_decision.py` - Update confluence scoring

**Requirements**:
1. Replace simple sum with weighted confluence
   ```
   confluence_score = 0
   
   # 1. RÉGIME (25%) - CRITICAL
   if signals['price_above_sma_200'] or signals['price_above_vwap']:
       confluence_score += 25
   
   # 2. TREND (20%) - IMPORTANT
   if signals['trend_strong']:  # True ADX > 25
       confluence_score += 20
   
   # 3. ENTRY (20%) - IMPORTANT
   if signals['price_in_ema20_zone']:
       confluence_score += 20
   
   # 4. MOMENTUM (20%) - IMPORTANT
   if signals['rsi_oversold'] or signals['macd_positive']:
       confluence_score += 20
   
   # 5. ACCUMULATION (10%) - USEFUL
   if signals['obv_accumulating'] and signals['volume_confirmed']:
       confluence_score += 10
   
   # 6. VOLATILITY (5%) - NICE TO HAVE
   if signals['volatility_sufficient']:
       confluence_score += 5
   ```

2. New confidence scale
   - 100% (6/6) → 10% position
   - 85% (5/6) → 8% position
   - 70% (4/6) → 6% position
   - <70% → NO SIGNAL

3. Test
   - pytest backend/tests/blocks/test_trinity_decision.py -v
   - Verify confidence calculation

**Success Criteria**:
- ✅ Weighted scoring implemented
- ✅ Position sizes adjust to confidence
- ✅ All tests pass
- ✅ Win rate tracking shows improvement

---

## VALIDATION CHECKLIST

After all tasks:

- [ ] VWAP calculation verified
- [ ] True ADX replacing simplified version
- [ ] MACD activated and logging
- [ ] OBV accumulation detected
- [ ] Weighted confluence model working
- [ ] All 328+ tests passing (0 regressions)
- [ ] No runtime errors in logs
- [ ] New signals logged for 24 hours
- [ ] Win rate improvement tracked
- [ ] Position sizes reflect new confluence
- [ ] Paper trading ready

---

## EXPECTED RESULTS

**Before Phase 1**:
```
Trinity Confidence: 1%
Position Size: $200 (2% of capital)
Signal Frequency: Very low
Win Rate: ~50%
```

**After Phase 1**:
```
Trinity Confidence: 60-85%
Position Size: $600-800 (6-8% of capital)
Signal Frequency: Higher quality
Win Rate: ~58% (+8%)
```

---

## END OF RALPH TASK

When all tasks complete successfully:
- Commit with message starting "feat: Phase 1 Indicators"
- All tests pass
- Output: <promise>COMPLETE</promise>

