#!/usr/bin/env python
"""
Comprehensive test for all three fixes:
1. Elite tracking
2. Card formatting (single-line descriptions)
3. Upgrade detection
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.core.save_parser import SaveParser
from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator
from src.llm.name_corrector import NameCorrector

print("=" * 70)
print("COMPREHENSIVE TEST - All Three Fixes")
print("=" * 70)

# Test 1: Elite Tracking
print("\n[TEST 1: Elite Tracking]")
print("-" * 70)

backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
latest = backup_mgr.find_latest_autosave()

if not latest:
    print("ERROR: No save file found!")
    sys.exit(1)

backup = backup_mgr.create_backup(latest)
parser = SaveParser()
run_data = parser.parse_and_extract(backup)

elites = run_data.get('elites_defeated', [])
print(f"Elites defeated: {elites}")
print(f"Count: {len(elites)}")

if len(elites) > 0:
    print("PASS: Elites extracted from save file")
else:
    print("FAIL: No elites found")

# Test 2: Card Formatting (Single Line)
print("\n[TEST 2: Card Formatting - Single Line Descriptions]")
print("-" * 70)

kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)

# Test cards with multi-line descriptions
test_cards = ["Weave", "Adaptation", "Battle Hymn", "Third Eye"]

for card_name in test_cards:
    formatted = summary_gen._format_card_with_details(card_name)
    has_newline = '\\n' in formatted or chr(10) in formatted
    
    print(f"{card_name}:")
    print(f"  {formatted}")
    print(f"  Contains newline: {has_newline}")
    
    if has_newline:
        print(f"  FAIL: Contains newline")
    else:
        print(f"  PASS: Single line")

# Test 3: Upgrade Detection
print("\n[TEST 3: Upgrade Detection]")
print("-" * 70)

# Test upgrade markers
test_cases = [
    ("Strike", False, "Strike [1] (Attack): Deal 6 damage."),
    ("Strike+", True, "Strike+ [1] (Attack): Deal 9 damage."),
    ("Defend+", True, "Defend+ [1] (Skill): Gain 8 Block."),
]

for card_id, is_upgraded, expected_pattern in test_cases:
    formatted = summary_gen._format_card_with_details(card_id)
    print(f"{card_id}:")
    print(f"  {formatted}")
    
    # Check if it shows upgraded damage/block
    if is_upgraded:
        if '+' in formatted:
            print(f"  PASS: Shows upgrade marker")
        else:
            print(f"  FAIL: No upgrade marker")
    else:
        if '+' not in formatted:
            print(f"  PASS: No upgrade marker (correct)")
        else:
            print(f"  FAIL: Unexpected upgrade marker")

# Test 4: Integration - Generate Summary with All Features
print("\n[TEST 4: Integration - Full Summary Generation]")
print("-" * 70)

summary = summary_gen.generate_summary(run_data, None, preserve_choice=False)

# Check for elites in summary
if "Elites defeated this act:" in summary:
    print("PASS: Summary contains elite section")
    
    # Extract elite line
    for line in summary.split('\\n'):
        if "Elites defeated this act:" in line:
            print(f"  {line}")
            break
else:
    print("FAIL: Summary missing elite section")

# Check for multi-line descriptions
lines = summary.split('\\n')
in_deck = False
multi_line_found = False

for i, line in enumerate(lines):
    if line.startswith('## Deck'):
        in_deck = True
    elif line.startswith('##'):
        in_deck = False
    elif in_deck and line.startswith('- ') and ':' in line:
        # Check if next line continues the description
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line and not next_line.startswith('-') and not next_line.startswith('#'):
                if not next_line.strip() == '':
                    multi_line_found = True
                    print(f"FAIL: Multi-line description found:")
                    print(f"  {line}")
                    print(f"  {next_line}")

if not multi_line_found:
    print("PASS: All card descriptions are single-line")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
