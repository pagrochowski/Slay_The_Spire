#!/usr/bin/env python
"""
Regenerate Run_Summary.md from latest backup with new formatting.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.save_parser import SaveParser
from src.summary.summary_generator import RunSummaryGenerator
from src.knowledge.knowledge_base import KnowledgeBase

# Use the specific backup
backup_file = Config.BACKUP_DIR / "WATCHER_20260520_193647.autosave"

if not backup_file.exists():
    print(f"❌ Backup not found: {backup_file}")
    sys.exit(1)

print(f"📁 Using backup: {backup_file.name}")

# Parse
parser = SaveParser()
run_data = parser.parse_and_extract(backup_file)

print(f"✅ Parsed:")
print(f"  Character: {run_data['character']}")
print(f"  Deck cards: {run_data['deck']}")
print(f"  Relics: {run_data['relics']}")
print(f"  Potions: {run_data['potions']}")

# Generate summary
kb = KnowledgeBase()
summary_gen = RunSummaryGenerator(knowledge_base=kb)
summary = summary_gen.generate_summary(run_data, Config.RUN_SUMMARY_PATH, preserve_choice=True)

print(f"\n✅ Generated new Run_Summary.md")
print(f"  Length: {len(summary)} chars")
print("\n" + "=" * 70)
print("Preview:")
print("=" * 70)
print(summary[:1000])
print("...")
