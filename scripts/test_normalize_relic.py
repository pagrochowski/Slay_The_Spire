#!/usr/bin/env python
"""
Test the normalize_relic_id function.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.id_normalizer import normalize_relic_id
from src.knowledge.knowledge_base import KnowledgeBase

print("=" * 70)
print("TESTING normalize_relic_id")
print("=" * 70)

kb = KnowledgeBase()

test_relics = [
    "PureWater",
    "Darkstone Periapt",
    "Vajra",
    "Kunai",
    "Molten Egg 2",
    "Cursed Key"
]

for relic in test_relics:
    print(f"\nInput: {repr(relic)}")
    
    # Test without KB
    result_no_kb = normalize_relic_id(relic)
    print(f"  Without KB: {result_no_kb}")
    
    # Test with KB
    result_with_kb = normalize_relic_id(relic, kb)
    print(f"  With KB: {result_with_kb}")
    
    # Check if they're different
    if result_no_kb != result_with_kb:
        print(f"  ⚠️  Results differ!")
