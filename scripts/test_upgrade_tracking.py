#!/usr/bin/env python
"""
Test the new per-card upgrade tracking system.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("PER-CARD UPGRADE TRACKING TEST")
print("=" * 70)

# Test the upgrade parsing logic
upgrade_keywords = ['plus', 'upgrade', 'upgraded']

test_cases = [
    # (input, expected_clean, expected_upgrades)
    ("strike plus defend", "strike defend", {"strike": True, "defend": False}),
    ("empty body weave plus protect", "empty body weave protect", {"empty": False, "body": False, "weave": True, "protect": False}),
    ("strike", "strike", {"strike": False}),
    ("battle hymn plus", "battle hymn", {"battle": False, "hymn": True}),
    ("defend upgrade strike plus", "defend strike", {"defend": True, "strike": True}),
    ("eruption plus weave plus vigilance", "eruption weave vigilance", {"eruption": True, "weave": True, "vigilance": False}),
    ("third eye upgrade", "third eye", {"third": False, "eye": True}),
]

for text, expected_clean, expected_upgrades in test_cases:
    print(f"\n{'=' * 70}")
    print(f"Input: \"{text}\"")
    print(f"{'=' * 70}")
    
    # Parse text to track which specific words have upgrade keywords after them
    words = text.split()
    upgrade_map = {}
    cleaned_words = []
    
    i = 0
    while i < len(words):
        word = words[i]
        word_lower = word.lower()
        
        # Check if this word is an upgrade keyword
        if word_lower in upgrade_keywords:
            # Mark the previous word as upgraded (if exists)
            if cleaned_words:
                prev_word = cleaned_words[-1]
                upgrade_map[prev_word.lower()] = True
            # Skip this upgrade keyword
            i += 1
            continue
        
        # This is a regular word (potential card/relic name)
        cleaned_words.append(word)
        # Default to not upgraded
        if word_lower not in upgrade_map:
            upgrade_map[word_lower] = False
        
        i += 1
    
    # Build cleaned text
    cleaned_text = ' '.join(cleaned_words)
    
    print(f"Cleaned text: \"{cleaned_text}\"")
    print(f"Upgrade map: {upgrade_map}")
    
    # Verify
    if cleaned_text == expected_clean:
        print("✓ PASS: Cleaned text matches expected")
    else:
        print(f"✗ FAIL: Expected \"{expected_clean}\"")
    
    if upgrade_map == expected_upgrades:
        print("✓ PASS: Upgrade map matches expected")
    else:
        print(f"✗ FAIL: Expected {expected_upgrades}")
    
    # Show which words are upgraded
    upgraded_words = [w for w in cleaned_words if upgrade_map.get(w.lower(), False)]
    if upgraded_words:
        print(f"Upgraded words: {', '.join(upgraded_words)}")

print(f"\n{'=' * 70}")
print("MULTI-WORD CARD NAME MATCHING TEST")
print(f"{'=' * 70}")

# Test matching multi-word card names to upgrade map
from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator

kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)

# Simulate: "empty body weave plus protect"
# Upgrade map: {"empty": False, "body": False, "weave": True, "protect": False}
# LLM returns: ["Empty Body", "Weave", "Protect"]

test_cases_matching = [
    # (card_name_from_llm, upgrade_map, should_be_upgraded)
    ("Empty Body", {"empty": False, "body": False, "weave": True, "protect": False}, False),
    ("Weave", {"empty": False, "body": False, "weave": True, "protect": False}, True),
    ("Protect", {"empty": False, "body": False, "weave": True, "protect": False}, False),
    ("Battle Hymn", {"battle": False, "hymn": True}, True),  # "hymn" has upgrade
    ("Third Eye", {"third": False, "eye": True}, True),  # "eye" has upgrade
    ("Strike", {"strike": True}, True),
]

for card_name, upgrade_map, should_be_upgraded in test_cases_matching:
    # Check if this specific card should be upgraded
    card_words = card_name.lower().split()
    is_card_upgraded = any(upgrade_map.get(word, False) for word in card_words)
    
    print(f"\nCard: {card_name}")
    print(f"  Words: {card_words}")
    print(f"  Upgrade map: {upgrade_map}")
    print(f"  Is upgraded: {is_card_upgraded}")
    
    if is_card_upgraded == should_be_upgraded:
        print(f"  ✓ PASS")
    else:
        print(f"  ✗ FAIL: Expected {should_be_upgraded}")
    
    # Format with upgrade marker
    card_id = card_name + ('+' if is_card_upgraded else '')
    formatted = summary_gen._format_card_with_details(card_id)
    print(f"  Formatted: {formatted}")

print(f"\n{'=' * 70}")
print("TEST COMPLETE")
print(f"{'=' * 70}")
