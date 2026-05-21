"""
Test the improved LLM prompt with two-pass matching for partial names.

This script tests specific cases that previously failed:
1. "trust lucky" → should match "Just Lucky" (partial word matching)
2. "follow up" → should match "Follow-Up" (hyphen/space variations)
3. "battle him" → should match "Battle Hymn" (phonetic errors)
4. Combined difficult cases

The two-pass system:
- First pass: Normal LLM matching with full prompt
- Second pass: Focused matching on unmatched words (more aggressive)
- Fuzzy fallback: Final safety net for any remaining unmatched words
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector
from src.knowledge.knowledge_base import KnowledgeBase


def test_llm_matching():
    """Test LLM with problematic inputs."""
    print("\n" + "="*70)
    print("TWO-PASS LLM MATCHING TEST")
    print("="*70)
    print("\nThis tests the enhanced LLM matching with:")
    print("  1. First pass: Standard matching with improved prompt")
    print("  2. Second pass: Focused matching on unmatched words")
    print("  3. Fuzzy fallback: Final safety net")
    print("="*70)
    
    corrector = NameCorrector()
    
    test_cases = [
        {
            "input": "trust lucky tranquility third eye",
            "character": "watcher",
            "expected_cards": ["Just Lucky", "Tranquility", "Third Eye"],
            "description": "Partial word 'lucky' should match 'Just Lucky' (ignore 'trust')",
            "difficulty": "Hard - requires partial matching"
        },
        {
            "input": "follow up brilliance",
            "character": "watcher",
            "expected_cards": ["Follow-Up", "Brilliance"],
            "description": "Space-separated should match hyphenated",
            "difficulty": "Medium - requires hyphen normalization"
        },
        {
            "input": "battle him third eye",
            "character": "watcher",
            "expected_cards": ["Battle Hymn", "Third Eye"],
            "description": "Transcription error 'him' → 'hymn'",
            "difficulty": "Medium - phonetic matching"
        },
        {
            "input": "just lucky follow up brilliance",
            "character": "watcher",
            "expected_cards": ["Just Lucky", "Follow-Up", "Brilliance"],
            "description": "Full correct input (baseline)",
            "difficulty": "Easy - exact matches"
        },
        {
            "input": "fist evaluate",
            "character": "watcher",
            "expected_cards": ["Empty Fist", "Evaluate"],
            "description": "Partial word 'fist' should match 'Empty Fist'",
            "difficulty": "Hard - requires partial matching"
        },
        {
            "input": "wheel kick study",
            "character": "watcher",
            "expected_cards": ["Wheel Kick", "Study"],
            "description": "Multi-word cards with exact match",
            "difficulty": "Easy - exact matches"
        },
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_cases)}: {test['description']}")
        print(f"Difficulty: {test['difficulty']}")
        print(f"{'='*70}")
        print(f"Input: \"{test['input']}\"")
        print(f"Expected: {test['expected_cards']}")
        
        try:
            cards, relics = corrector.correct_names(
                test['input'],
                test['character']
            )
            
            print(f"Actual:   {cards}")
            
            # Check if we got the expected cards
            expected_set = set(test['expected_cards'])
            actual_set = set(cards)
            
            if expected_set == actual_set:
                print(f"\n✅ PASS - Perfect match!")
                results.append(True)
            elif expected_set.issubset(actual_set):
                extra = actual_set - expected_set
                print(f"\n⚠️  PARTIAL PASS - Got all expected cards plus extras: {extra}")
                results.append(True)  # Still count as pass
            else:
                missing = expected_set - actual_set
                extra = actual_set - expected_set
                print(f"\n❌ FAIL")
                if missing:
                    print(f"   Missing: {missing}")
                if extra:
                    print(f"   Extra: {extra}")
                results.append(False)
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*70)
    print(f"FINAL RESULTS: {sum(results)}/{len(results)} tests passed")
    print("="*70)
    
    if all(results):
        print("\n✅ EXCELLENT! All tests passed!")
        print("   The two-pass LLM matching is working correctly.")
    elif sum(results) >= len(results) * 0.8:
        print(f"\n✅ GOOD! {sum(results)}/{len(results)} tests passed ({sum(results)/len(results)*100:.0f}%)")
        print("   Most cases working. LLM responses can vary slightly.")
    else:
        print(f"\n⚠️  {sum(results)}/{len(results)} tests passed")
        print("   Some tests failed. The LLM might need more prompt tuning.")
        print("   Note: LLM responses can vary. Try running again.")
    
    return all(results)


if __name__ == "__main__":
    success = test_llm_matching()
    sys.exit(0 if success else 1)
