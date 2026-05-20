#!/usr/bin/env python
"""
Test comprehensive fixes for:
1. Character name (strip timestamp)
2. Card/relic/potion ID normalization
3. Fuzzy matching improvements
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.id_normalizer import (
    normalize_character_name,
    normalize_card_id,
    normalize_relic_id,
    normalize_potion_id
)
from src.knowledge.knowledge_base import KnowledgeBase
from src.llm.name_corrector import NameCorrector

print("=" * 70)
print("🧪 Testing All Formatting Fixes")
print("=" * 70)

# Initialize
kb = KnowledgeBase()
corrector = NameCorrector(knowledge_base=kb)

# Test 1: Character Name Normalization
print("\n1️⃣  Character Name Normalization")
print("-" * 70)

test_filenames = [
    ("WATCHER_20260520_193647.autosave", "WATCHER"),
    ("IRONCLAD.autosave", "IRONCLAD"),
    ("SILENT_BACKUP", "SILENT")
]

for filename, expected in test_filenames:
    result = normalize_character_name(filename)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {filename:35} → {result:10} (expected: {expected})")

# Test 2: Card ID Normalization
print("\n2️⃣  Card ID Normalization")
print("-" * 70)

test_cards = [
    ("BattleHymn", "Battle Hymn"),
    ("Defend_P", "Defend"),
    ("Strike_R", "Strike"),
    ("Strike_P+", "Strike+"),
    ("Eruption", "Eruption")
]

for card_id, expected in test_cards:
    result = normalize_card_id(card_id, kb)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {card_id:20} → {result:20} (expected: {expected})")

# Test 3: Relic ID Normalization
print("\n3️⃣  Relic ID Normalization")
print("-" * 70)

test_relics = [
    ("PureWater", "Pure Water"),
    ("BagOfPreparation", "Bag of Preparation"),
    ("SingingBowl", "Singing Bowl")
]

for relic_id, expected in test_relics:
    result = normalize_relic_id(relic_id, kb)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {relic_id:20} → {result:25} (expected: {expected})")

# Test 4: Potion ID Normalization
print("\n4️⃣  Potion ID Normalization")
print("-" * 70)

test_potions = [
    ("FearPotion", "Fear Potion"),
    ("RegenPotion", "Regen Potion"),
    ("StrengthPotion", "Strength Potion")
]

for potion_id, expected in test_potions:
    result = normalize_potion_id(potion_id, kb)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {potion_id:20} → {result:20} (expected: {expected})")

# Test 5: Fuzzy Matching with Punctuation
print("\n5️⃣  Fuzzy Matching (with punctuation)")
print("-" * 70)

test_cases = [
    ("Third Eye, Wrath of Flame, Weave.", ["Third Eye", "Wreath of Flame", "Weave"]),
    ("Wheel kick, study, wrath of flame", ["Wheel Kick", "Study", "Wreath of Flame"])
]

for transcription, expected_cards in test_cases:
    print(f"\n  Input: \"{transcription}\"")
    cards, relics = corrector.correct_names(transcription, "watcher", include_relics=False)
    
    print(f"  Found: {', '.join(cards)}")
    print(f"  Expected: {', '.join(expected_cards)}")
    
    # Check all expected cards are found
    all_found = all(card in cards for card in expected_cards)
    no_extras = len(cards) == len(expected_cards)
    
    if all_found and no_extras:
        print(f"  ✅ PASS - All cards matched correctly")
    elif all_found:
        print(f"  ⚠️  PARTIAL - All expected found, but also got: {set(cards) - set(expected_cards)}")
    else:
        missing = set(expected_cards) - set(cards)
        print(f"  ❌ FAIL - Missing: {', '.join(missing)}")

# Test 6: Verify Status Cards Filtered
print("\n6️⃣  Status Card Filtering")
print("-" * 70)

choosable = kb.get_choosable_cards_for_character("watcher")
status_cards = ["Burn", "Dazed", "Slimed", "Wound"]

for card in status_cards:
    in_choosable = card in choosable
    status = "❌" if in_choosable else "✅"
    result = "INCORRECTLY INCLUDED" if in_choosable else "correctly filtered"
    print(f"  {status} {card:15} {result}")

print("\n" + "=" * 70)
print("✅ Comprehensive Fix Testing Complete")
print("=" * 70)
