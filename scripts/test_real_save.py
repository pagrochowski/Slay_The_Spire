#!/usr/bin/env python
"""
Test with actual save file to verify all formatting fixes.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.core.save_parser import SaveParser
from src.summary.summary_generator import RunSummaryGenerator
from src.knowledge.knowledge_base import KnowledgeBase

print("=" * 70)
print("🎮 Testing Real Save File Formatting")
print("=" * 70)

# Initialize components
backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
parser = SaveParser()
kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)

# Find latest save
print("\n1️⃣  Finding latest save file...")
latest = backup_mgr.find_latest_autosave()
if not latest:
    print("❌ No save file found!")
    sys.exit(1)

print(f"  ✅ Found: {Path(latest).name}")

# Create backup
print("\n2️⃣  Creating backup...")
backup = backup_mgr.create_backup(latest)
print(f"  ✅ Backup created: {Path(backup).name}")

# Parse save
print("\n3️⃣  Parsing save file...")
run_data = parser.parse_and_extract(backup)

if not run_data:
    print("❌ Parse failed!")
    sys.exit(1)

print(f"  ✅ Character: {run_data['character']}")
print(f"  ✅ Ascension: {run_data['ascension']}")
print(f"  ✅ HP: {run_data['current_hp']}/{run_data['max_hp']}")
print(f"  ✅ Deck: {len(run_data['deck'])} cards")
print(f"  ✅ Relics: {len(run_data['relics'])} relics")
print(f"  ✅ Potions: {len(run_data['potions'])} potions")

# Generate summary
print("\n4️⃣  Generating summary...")
summary_path = Config.PROJECT_ROOT / "test_summary.md"
summary = summary_gen.generate_summary(run_data, summary_path, preserve_choice=False)

print(f"  ✅ Summary generated ({len(summary)} chars)")
print(f"  ✅ Saved to: {summary_path}")

# Show deck section to verify formatting
print("\n5️⃣  Deck Section Preview:")
print("=" * 70)

in_deck_section = False
for line in summary.split('\n'):
    if line.startswith('## Deck'):
        in_deck_section = True
    elif line.startswith('## Relics'):
        break
    
    if in_deck_section:
        print(line)

# Show relics section
print("\n6️⃣  Relics Section Preview:")
print("=" * 70)

in_relic_section = False
for line in summary.split('\n'):
    if line.startswith('## Relics'):
        in_relic_section = True
    elif line.startswith('## Potions'):
        break
    
    if in_relic_section:
        print(line)

# Show potions section
print("\n7️⃣  Potions Section Preview:")
print("=" * 70)

in_potion_section = False
for line in summary.split('\n'):
    if line.startswith('## Potions'):
        in_potion_section = True
    elif line.startswith('## Keys'):
        break
    
    if in_potion_section:
        print(line)

# Validation checks
print("\n8️⃣  Validation:")
print("=" * 70)

issues = []

# Check character name (should not have timestamp)
if '_' in run_data['character']:
    issues.append(f"❌ Character name has underscore: {run_data['character']}")
else:
    print(f"✅ Character name clean: {run_data['character']}")

# Check for double dashes in summary
if '- -' in summary:
    issues.append("❌ Found double dashes '- -' in summary")
else:
    print("✅ No double dashes")

# Check for glued words (PureWater, BattleHymn, etc.)
glued_patterns = ['PureWater', 'BattleHymn', 'FearPotion', 'Defend_P', 'Strike_P']
for pattern in glued_patterns:
    if pattern in summary:
        issues.append(f"❌ Found glued word: {pattern}")

if not any(pattern in summary for pattern in glued_patterns):
    print("✅ No glued words found")

# Check for multi-line descriptions (should all be single-line)
lines = summary.split('\n')
for i, line in enumerate(lines):
    if line.strip().startswith('- ') and '[' in line and ']' in line:
        # This is a card line
        if ':' not in line:
            issues.append(f"❌ Line {i+1}: Card without description: {line[:50]}")

if not issues:
    print("✅ All cards have single-line descriptions")

# Summary
print("\n" + "=" * 70)
if issues:
    print("⚠️  Issues Found:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("🎉 ALL FORMATTING CHECKS PASSED!")
print("=" * 70)
