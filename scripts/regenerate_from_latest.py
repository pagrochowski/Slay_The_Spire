#!/usr/bin/env python
"""
Regenerate Run_Summary.md from the LATEST save file (not backup).
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
print("🔄 Regenerating Summary from Latest Save")
print("=" * 70)

# Find the latest save (not backup)
backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
latest = backup_mgr.find_latest_autosave()

if not latest:
    print("❌ No save file found!")
    sys.exit(1)

print(f"\n📁 Latest save: {Path(latest).name}")

# Create backup
backup = backup_mgr.create_backup(latest)
print(f"📦 Created backup: {Path(backup).name}")

# Parse
parser = SaveParser()
run_data = parser.parse_and_extract(backup)

print(f"\n✅ Parsed:")
print(f"  Character: {run_data['character']}")
print(f"  HP: {run_data['current_hp']}/{run_data['max_hp']}")
print(f"  Gold: {run_data['gold']}")
print(f"  Deck: {len(run_data['deck'])} cards")
print(f"  Relics: {run_data['relics']}")
print(f"  Potions: {run_data['potions']}")

# Generate summary
kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)
summary = summary_gen.generate_summary(run_data, Config.RUN_SUMMARY_PATH, preserve_choice=True)

print(f"\n✅ Generated new Run_Summary.md")
print(f"  Length: {len(summary)} chars")
print(f"  Relics in summary: {len(run_data['relics'])}")

# Show relics section
print("\n📋 Relics Section:")
print("=" * 70)
in_relic_section = False
for line in summary.split('\n'):
    if line.startswith('## Relics'):
        in_relic_section = True
    elif line.startswith('## Potions'):
        break
    
    if in_relic_section:
        print(line)

print("\n" + "=" * 70)
print("✅ Done! Check Run_Summary.md")
print("=" * 70)
