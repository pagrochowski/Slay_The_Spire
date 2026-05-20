#!/usr/bin/env python
"""
Debug relic extraction from save file.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.core.save_parser import SaveParser
from spireslayer.editor import Editor

print("=" * 70)
print("🔍 Debugging Relic Extraction")
print("=" * 70)

# Find latest save
backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
latest = backup_mgr.find_latest_autosave()

if not latest:
    print("❌ No save file found!")
    sys.exit(1)

print(f"\n📁 Using save: {Path(latest).name}")

# Parse with spireslayer directly first
print("\n1️⃣  Direct spireslayer parsing:")
print("-" * 70)
editor = Editor(autosave_path=str(latest))
save_data = editor.decoded

if "relics" in save_data:
    relics_raw = save_data["relics"]
    print(f"Raw relics type: {type(relics_raw)}")
    print(f"Raw relics count: {len(relics_raw) if isinstance(relics_raw, (list, dict)) else 'N/A'}")
    print(f"Raw relics data:")
    for i, relic in enumerate(relics_raw[:10] if isinstance(relics_raw, list) else []):
        print(f"  [{i}] {relic} (type: {type(relic).__name__})")
else:
    print("❌ No 'relics' key in save data!")

# Now parse with our parser
print("\n2️⃣  Our parser extraction:")
print("-" * 70)
parser = SaveParser()
run_data = parser.parse_and_extract(latest)

print(f"Extracted relics: {run_data['relics']}")
print(f"Count: {len(run_data['relics'])}")

# Check if we're missing any
print("\n3️⃣  Comparison:")
print("-" * 70)
if isinstance(relics_raw, list):
    raw_count = len(relics_raw)
    parsed_count = len(run_data['relics'])
    
    print(f"Raw relics in save: {raw_count}")
    print(f"Parsed relics: {parsed_count}")
    
    if raw_count != parsed_count:
        print(f"\n⚠️  MISMATCH! We're missing {raw_count - parsed_count} relics!")
        
        # Show what we have vs what we should have
        print("\nRaw relics:")
        for relic in relics_raw:
            print(f"  - {relic}")
        
        print("\nParsed relics:")
        for relic in run_data['relics']:
            print(f"  - {relic}")
    else:
        print("✅ All relics extracted correctly!")

print("\n" + "=" * 70)
