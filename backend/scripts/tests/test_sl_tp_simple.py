#!/usr/bin/env python3
"""
Simple test for SL/TP validation logic without dependencies
"""

from decimal import Decimal

def calculate_sl_tp_percentages(entry_price, sl_price, tp_price, side):
    """Calculate SL/TP percentages based on side"""

    entry_price = Decimal(str(entry_price))
    sl_price = Decimal(str(sl_price))
    tp_price = Decimal(str(tp_price))

    if side == 'long':
        sl_pct = (entry_price - sl_price) / entry_price if entry_price > 0 else Decimal("0")
        tp_pct = (tp_price - entry_price) / entry_price if entry_price > 0 else Decimal("0")
    else:  # short
        sl_pct = (sl_price - entry_price) / entry_price if entry_price > 0 else Decimal("0")
        tp_pct = (entry_price - tp_price) / entry_price if entry_price > 0 else Decimal("0")

    return sl_pct, tp_pct

def validate_price_relationships(entry_price, sl_price, tp_price, side):
    """Validate price relationships based on side"""

    if side == 'long':
        return sl_price < entry_price < tp_price
    else:  # short
        return tp_price < entry_price < sl_price

def test_validation():
    """Test the validation logic"""

    print("🧪 Testing SL/TP validation logic...")

    # Test case 1: Valid LONG position (like ETH/USDT from logs)
    entry_price = 4064.62
    sl_price = 4035.0
    tp_price = 4150.0
    side = 'long'

    sl_pct, tp_pct = calculate_sl_tp_percentages(entry_price, sl_price, tp_price, side)
    valid_relationship = validate_price_relationships(entry_price, sl_price, tp_price, side)

    print("
📊 Test 1 - Valid LONG position:")
    print(f"   Entry: ${entry_price}")
    print(f"   SL: ${sl_price} ({sl_pct:.4f} = ".4f"l_pct:.1%})")
    print(f"   TP: ${tp_price} ({tp_pct:.4f} = ".4f"ct:.1%})")
    print(f"   Relationship valid: {valid_relationship}")
    print(f"   SL% > 0: {sl_pct > 0}")
    print(f"   TP% > 0: {tp_pct > 0}")
    print(f"   Risk/Reward ratio: {tp_pct/sl_pct:.2f".2f"
    # Test case 2: Invalid LONG position (SL above entry)
    entry_price2 = 4064.62
    sl_price2 = 4100.0  # Above entry (invalid for LONG)
    tp_price2 = 4150.0
    side2 = 'long'

    sl_pct2, tp_pct2 = calculate_sl_tp_percentages(entry_price2, sl_price2, tp_price2, side2)
    valid_relationship2 = validate_price_relationships(entry_price2, sl_price2, tp_price2, side2)

    print("
📊 Test 2 - Invalid LONG position (SL above entry):")
    print(f"   Entry: ${entry_price2}")
    print(f"   SL: ${sl_price2} ({sl_pct2:.4f} = {sl_pct2:.1%})")
    print(f"   TP: ${tp_price2} ({tp_pct2:.4f} = {tp_pct2:.1%})")
    print(f"   Relationship valid: {valid_relationship2}")
    print(f"   SL% > 0: {sl_pct2 > 0}")
    print(f"   TP% > 0: {tp_pct2 > 0}")

    # Test case 3: Valid SHORT position
    entry_price3 = 4064.62
    sl_price3 = 4100.0
    tp_price3 = 4035.0
    side3 = 'short'

    sl_pct3, tp_pct3 = calculate_sl_tp_percentages(entry_price3, sl_price3, tp_price3, side3)
    valid_relationship3 = validate_price_relationships(entry_price3, sl_price3, tp_price3, side3)

    print("
📊 Test 3 - Valid SHORT position:")
    print(f"   Entry: ${entry_price3}")
    print(f"   SL: ${sl_price3} ({sl_pct3:.4f} = {sl_pct3:.1%})")
    print(f"   TP: ${tp_price3} ({tp_pct3:.4f} = {tp_pct3:.1%})")
    print(f"   Relationship valid: {valid_relationship3}")
    print(f"   SL% > 0: {sl_pct3 > 0}")
    print(f"   TP% > 0: {tp_pct3 > 0}")
    print(f"   Risk/Reward ratio: {tp_pct3/sl_pct3:.2f}")
    # Summary
    test1_valid = sl_pct > 0 and tp_pct > 0 and valid_relationship and (tp_pct/sl_pct) >= 1.3
    test2_valid = not (sl_pct2 > 0)  # Should be invalid
    test3_valid = sl_pct3 > 0 and tp_pct3 > 0 and valid_relationship3 and (tp_pct3/sl_pct3) >= 1.3

    print("
🎯 Summary:")
    print(f"   Test 1 (Valid LONG): {'✅ PASSED' if test1_valid else '❌ FAILED'}")
    print(f"   Test 2 (Invalid LONG): {'✅ PASSED' if test2_valid else '❌ FAILED'}")
    print(f"   Test 3 (Valid SHORT): {'✅ PASSED' if test3_valid else '❌ FAILED'}")

    all_passed = test1_valid and test2_valid and test3_valid

    if all_passed:
        print("
🎉 All validation tests PASSED! The fix should work correctly."        return True
    else:
        print("
❌ Some validation tests FAILED! The fix needs more work.")
        return False

if __name__ == "__main__":
    print("🚀 Testing SL/TP validation logic (no dependencies)...\n")

    success = test_validation()

    if success:
        print("\n✅ The validation logic is working correctly!")
        print("The bot should now accept valid SL/TP from LLM decisions.")
    else:
        print("\n❌ The validation logic has issues.")
        print("Need to review the calculation formulas.")