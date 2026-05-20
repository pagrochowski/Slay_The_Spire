#!/usr/bin/env python
"""
Quick test to verify Third Eye bug is fixed.

Tests that name validation checks both card and relic pools
when LLM mis-categorizes items.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from src.knowledge.knowledge_base import KnowledgeBase
from src.llm.name_corrector import NameCorrector

print("=" * 60)
print("🧪 Testing Third Eye Bug Fix")
print("=" * 60)

# Initialize
kb = KnowledgeBase()
corrector = NameCorrector(knowledge_base=kb)

# Test case: LLM mis-categorizes "Third Eye" as a relic
# (It's actually a Watcher card)
print("\n1️⃣  Test: LLM categorizes 'Third Eye' as relic (incorrect)")
print("   Expected: Should reclassify it as a card")

llm_response = json.dumps({
    "cards": ["Foresight", "Battle Hymn"],
    "relics": ["Third Eye"]  # WRONG! This is a card, not a relic
})

cards, relics = corrector._parse_correction_result(llm_response)

print(f"\n   Cards found: {cards}")
print(f"   Relics found: {relics}")

# Verify
if "Third Eye" in cards:
    print("   ✅ PASS - Third Eye correctly reclassified as card")
elif "Third Eye" in relics:
    print("   ❌ FAIL - Third Eye still treated as relic")
else:
    print("   ❌ FAIL - Third Eye was discarded")

# Test case 2: LLM mis-categorizes a relic as a card
print("\n2️⃣  Test: LLM categorizes 'Singing Bowl' as card (incorrect)")
print("   Expected: Should reclassify it as a relic")

llm_response = json.dumps({
    "cards": ["Strike", "Defend", "Singing Bowl"],  # WRONG! This is a relic
    "relics": []
})

cards, relics = corrector._parse_correction_result(llm_response)

print(f"\n   Cards found: {cards}")
print(f"   Relics found: {relics}")

# Verify
if "Singing Bowl" in relics:
    print("   ✅ PASS - Singing Bowl correctly reclassified as relic")
elif "Singing Bowl" in cards:
    print("   ❌ FAIL - Singing Bowl still treated as card")
else:
    print("   ❌ FAIL - Singing Bowl was discarded")

# Test case 3: Everything correctly categorized
print("\n3️⃣  Test: All items correctly categorized")
print("   Expected: Cards stay as cards, relics stay as relics")

llm_response = json.dumps({
    "cards": ["Strike", "Defend", "Third Eye"],
    "relics": ["Singing Bowl", "Bag of Preparation"]
})

cards, relics = corrector._parse_correction_result(llm_response)

print(f"\n   Cards found: {cards}")
print(f"   Relics found: {relics}")

expected_cards = {"Strike", "Defend", "Third Eye"}
expected_relics = {"Singing Bowl", "Bag of Preparation"}

if set(cards) == expected_cards and set(relics) == expected_relics:
    print("   ✅ PASS - All items correctly validated")
else:
    print("   ❌ FAIL - Some items mis-categorized")
    print(f"      Expected cards: {expected_cards}")
    print(f"      Expected relics: {expected_relics}")

print("\n" + "=" * 60)
print("✅ Third Eye Bug Fix Test Complete")
print("=" * 60)
