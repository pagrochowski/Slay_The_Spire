#!/usr/bin/env python
"""
Test the comprehensive name matching fix.

Tests the exact user scenario:
Input: "Wheel kick study wrath of flame"
Expected Output: Wheel Kick, Study, Wreath of Flame
Not Expected: Burn (status card)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.knowledge_base import KnowledgeBase
from src.llm.name_corrector import NameCorrector

print("=" * 70)
print("🧪 Testing Comprehensive Name Matching Fix")
print("=" * 70)

# Initialize
kb = KnowledgeBase()
corrector = NameCorrector(knowledge_base=kb)

# Test case: User's exact scenario
print("\n📝 User's Input: \"Wheel kick study wrath of flame\"")
print("\nExpected:")
print("  ✅ Wheel Kick (exact match)")
print("  ✅ Study (should be found)")
print("  ✅ Wreath of Flame (fuzzy match from 'wrath of flame')")
print("  ❌ Burn (status card - should NOT appear)")

print("\n" + "-" * 70)
print("Running name correction...")
print("-" * 70)

# Test with Watcher character
transcription = "Wheel kick study wrath of flame"
cards, relics = corrector.correct_names(transcription, "watcher", include_relics=False)

print("\n📊 Results:")
print(f"  Cards found: {len(cards)}")
for i, card in enumerate(cards, 1):
    print(f"    {i}. {card}")

if relics:
    print(f"  Relics found: {len(relics)}")
    for i, relic in enumerate(relics, 1):
        print(f"    {i}. {relic}")

# Validation
print("\n" + "=" * 70)
print("✅ Validation")
print("=" * 70)

success = True

# Check for expected cards
expected_cards = {"Wheel Kick", "Study", "Wreath of Flame"}
found_cards = set(cards)

for card in expected_cards:
    if card in found_cards:
        print(f"  ✅ Found: {card}")
    else:
        print(f"  ❌ MISSING: {card}")
        success = False

# Check that Burn is NOT present
if "Burn" in found_cards:
    print(f"  ❌ ERROR: 'Burn' (status card) should NOT be in results!")
    success = False
else:
    print(f"  ✅ Status card 'Burn' correctly filtered")

# Check for unexpected cards
unexpected = found_cards - expected_cards
if unexpected:
    print(f"\n  ⚠️  Unexpected cards found: {', '.join(unexpected)}")

print("\n" + "=" * 70)
if success and len(found_cards) == 3:
    print("🎉 ALL TESTS PASSED!")
else:
    print("⚠️  Some issues remain - check results above")
print("=" * 70)

# Additional test: Check that choosable cards filter works
print("\n\n📋 Verifying STATUS/CURSE Filter")
print("=" * 70)

all_cards = kb.get_cards_for_character("watcher")
choosable_cards = kb.get_choosable_cards_for_character("watcher")

print(f"  Total Watcher cards (with colorless): {len(all_cards)}")
print(f"  Choosable cards (no STATUS/CURSE): {len(choosable_cards)}")
print(f"  Filtered out: {len(all_cards) - len(choosable_cards)} cards")

# Check specific status cards
status_cards_in_all = [c for c in all_cards if c in ["Burn", "Dazed", "Slimed", "Wound"]]
status_cards_in_choosable = [c for c in choosable_cards if c in ["Burn", "Dazed", "Slimed", "Wound"]]

print(f"\n  Status cards in all_cards: {', '.join(status_cards_in_all) if status_cards_in_all else 'None'}")
print(f"  Status cards in choosable_cards: {', '.join(status_cards_in_choosable) if status_cards_in_choosable else 'None (correctly filtered)'}")

if not status_cards_in_choosable:
    print("\n  ✅ Status cards correctly filtered from choosable pool")
else:
    print("\n  ❌ ERROR: Status cards still in choosable pool!")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
