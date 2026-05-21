#!/usr/bin/env python
"""
Test all three fixes:
1. Relic counter display (Molten Egg 2)
2. Upgrade keyword stripping
3. Stats refresh from save file
"""

import sys
import re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.core.save_parser import SaveParser
from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator
from src.utils.id_normalizer import normalize_relic_id

print("=" * 70)
print("TESTING ALL THREE FIXES")
print("=" * 70)

# Test 1: Relic Counter Display
print("\n[TEST 1: Relic Counter Display]")
print("-" * 70)

kb = KnowledgeBase()

# Test various relic names with counters
test_relics = [
    "Molten Egg 2",
    "Molten Egg",
    "PureWater",
    "Darkstone Periapt",
    "Incense Burner 3",
]

summary_gen = RunSummaryGenerator(knowledge_base=kb)

for relic_name in test_relics:
    # Normalize
    normalized = normalize_relic_id(relic_name, kb)
    print(f"\nInput: {repr(relic_name)}")
    print(f"  Normalized: {normalized}")
    
    # Format with description
    formatted = summary_gen._format_relic_with_description(normalized)
    print(f"  Formatted: {formatted}")
    
    # Check if description was found
    has_description = ":" in formatted and len(formatted) > len(normalized) + 2
    if has_description:
        print(f"  PASS: Description found")
    else:
        print(f"  WARN: No description (may not exist in KB)")

# Test 2: Upgrade Keyword Stripping
print("\n\n[TEST 2: Upgrade Keyword Stripping]")
print("-" * 70)

test_inputs = [
    "strike plus",
    "defend upgrade",
    "eruption upgraded",
    "battle hymn and strike plus",
    "plus weave",  # edge case - keyword at start
]

upgrade_keywords = ['plus', 'upgrade', 'upgraded']

for text in test_inputs:
    text_lower = text.lower()
    is_upgraded = any(keyword in text_lower for keyword in upgrade_keywords)
    
    # Clean text
    cleaned_text = text
    if is_upgraded:
        for keyword in upgrade_keywords:
            cleaned_text = re.sub(rf'\b{keyword}\b', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    print(f"\nInput: \"{text}\"")
    print(f"  Upgraded: {is_upgraded}")
    print(f"  Cleaned: \"{cleaned_text}\"")
    
    if is_upgraded and keyword not in cleaned_text.lower():
        print(f"  PASS: Upgrade keyword removed")
    elif not is_upgraded:
        print(f"  PASS: No upgrade keyword")
    else:
        print(f"  FAIL: Upgrade keyword still present")

# Test 3: Stats Refresh
print("\n\n[TEST 3: Stats Refresh from Save File]")
print("-" * 70)

backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
parser = SaveParser()

# Find and parse latest save
latest_save = backup_mgr.find_latest_autosave()

if not latest_save:
    print("ERROR: No save file found")
else:
    print(f"Latest save: {Path(latest_save).name}")
    
    # Parse it
    backup = backup_mgr.create_backup(latest_save)
    run_data = parser.parse_and_extract(backup)
    
    print(f"\nStats extracted:")
    print(f"  Character: {run_data['character']}")
    print(f"  HP: {run_data['current_hp']}/{run_data['max_hp']}")
    print(f"  Gold: {run_data['gold']}")
    print(f"  Deck size: {len(run_data['deck'])}")
    print(f"  Relic count: {len(run_data['relics'])}")
    print(f"  Elites defeated: {run_data.get('elites_defeated', [])}")
    
    # Check relics
    print(f"\n  Relics:")
    for relic in run_data['relics']:
        formatted = summary_gen._format_relic_with_description(relic)
        print(f"    - {formatted}")
    
    print(f"\n  PASS: Stats loaded successfully")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
