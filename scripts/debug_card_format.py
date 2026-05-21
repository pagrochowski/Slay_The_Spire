#!/usr/bin/env python
"""
Debug script to test card formatting.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator

kb = KnowledgeBase()
gen = RunSummaryGenerator(knowledge_base=kb)

# Test Weave card
card_data = kb.get_card_data("Weave")
print("Card Data for Weave:")
print(f"  name: {card_data.get('name')}")
print(f"  description: {repr(card_data.get('description'))}")
print(f"  description length: {len(card_data.get('description', ''))}")

# Test formatting
formatted = gen._format_card_with_details("Weave")
print(f"\nFormatted: {formatted}")
print(f"Contains newline: {chr(10) in formatted}")
print(f"Repr: {repr(formatted)}")
