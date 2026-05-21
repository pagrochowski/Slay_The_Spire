#!/usr/bin/env python
"""
Demonstrate upgrade keyword handling in voice input processing.
"""

import sys
import re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator

print("=" * 70)
print("UPGRADE KEYWORD HANDLING DEMONSTRATION")
print("=" * 70)

kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)

# Simulate voice inputs with upgrade keywords
test_cases = [
    ("strike plus", ["Strike"]),
    ("defend upgrade", ["Defend"]),
    ("weave upgraded", ["Weave"]),
    ("battle hymn and eruption plus", ["Battle Hymn", "Eruption"]),
    ("third eye upgrade and vigilance", ["Third Eye", "Vigilance"]),
]

upgrade_keywords = ['plus', 'upgrade', 'upgraded']

for voice_input, expected_cards in test_cases:
    print(f"\n{'=' * 70}")
    print(f"Voice Input: \"{voice_input}\"")
    print(f"{'=' * 70}")
    
    # Step 1: Detect upgrade keywords
    text_lower = voice_input.lower()
    is_upgraded = any(keyword in text_lower for keyword in upgrade_keywords)
    print(f"\n1. Upgrade Detection:")
    print(f"   Detected: {is_upgraded}")
    
    # Step 2: Strip upgrade keywords
    cleaned_text = voice_input
    if is_upgraded:
        for keyword in upgrade_keywords:
            cleaned_text = re.sub(rf'\b{keyword}\b', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    print(f"\n2. Text Cleaning:")
    print(f"   Original: \"{voice_input}\"")
    print(f"   Cleaned:  \"{cleaned_text}\"")
    print(f"   → This cleaned text would be sent to LLM")
    
    # Step 3: Simulate LLM returning card names (we'll use expected for demo)
    print(f"\n3. LLM Returns:")
    print(f"   Cards: {expected_cards}")
    
    # Step 4: Apply upgrade markers
    print(f"\n4. Apply Upgrade Markers:")
    for card_name in expected_cards:
        # Add upgrade marker if detected
        card_id = card_name + ('+' if is_upgraded else '')
        
        # Format with summary generator
        formatted = summary_gen._format_card_with_details(card_id)
        
        print(f"   - {formatted}")
    
    print(f"\n✓ RESULT: Upgrade keywords excluded from LLM, applied to result")

print(f"\n{'=' * 70}")
print(f"KEY BENEFITS:")
print(f"{'=' * 70}")
print("""
1. LLM doesn't try to match "plus" or "upgrade" as card names
2. Clean text improves matching accuracy
3. Upgrade markers applied consistently to ALL matched cards
4. Works with multiple cards in one input
5. Handles edge cases (keyword at start/end)
""")
