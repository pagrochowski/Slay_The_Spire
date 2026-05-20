#!/usr/bin/env python
"""
Test "Wrath of Flame" → "Wreath of Flame" matching specifically.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.knowledge_base import KnowledgeBase
from src.llm.name_corrector import NameCorrector

print("=" * 70)
print("🔥 Testing 'Wrath of Flame' → 'Wreath of Flame' Matching")
print("=" * 70)

# Initialize
kb = KnowledgeBase()
corrector = NameCorrector(knowledge_base=kb)

# Test cases that were failing
test_cases = [
    ("Third Eye, Wrath of Flame, Weave", ["Third Eye", "Wreath of Flame", "Weave"]),
    ("Third Eye, Wrath of Flame, Weave.", ["Third Eye", "Wreath of Flame", "Weave"]),
    ("wrath of flame", ["Wreath of Flame"]),
    ("Wrath of Flame", ["Wreath of Flame"]),
    ("wheel kick study wrath of flame", ["Wheel Kick", "Study", "Wreath of Flame"]),
]

print("\n📝 Testing Various Formats:")
print("=" * 70)

all_passed = True

for i, (transcription, expected_cards) in enumerate(test_cases, 1):
    print(f"\n{i}. Input: \"{transcription}\"")
    
    cards, relics = corrector.correct_names(transcription, "watcher", include_relics=False)
    
    print(f"   Expected: {', '.join(expected_cards)}")
    print(f"   Got:      {', '.join(cards)}")
    
    # Check all expected cards are found
    expected_set = set(expected_cards)
    found_set = set(cards)
    
    all_found = expected_set.issubset(found_set)
    no_extras = found_set.issubset(expected_set)
    
    if all_found and no_extras:
        print(f"   ✅ PASS - Perfect match!")
    elif all_found:
        extras = found_set - expected_set
        print(f"   ⚠️  PARTIAL - All expected found, but also: {', '.join(extras)}")
        all_passed = False
    else:
        missing = expected_set - found_set
        print(f"   ❌ FAIL - Missing: {', '.join(missing)}")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("🎉 ALL TESTS PASSED!")
    print("'Wrath of Flame' → 'Wreath of Flame' matching is working perfectly!")
else:
    print("⚠️  Some tests need improvement")
    print("\nCheck logs in logs/YYYY-MM-DD/ for detailed fuzzy matching scores")
print("=" * 70)
