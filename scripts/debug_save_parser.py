#!/usr/bin/env python
"""
Debug the save_parser to see where data is lost.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.save_parser import SaveParser

save_path = Path(Config.BACKUP_DIR) / "WATCHER_20260521_110028.autosave"

print("=" * 70)
print("SAVE PARSER DEBUG")
print("=" * 70)

parser = SaveParser()

print(f"\nSave file: {save_path}")
print(f"Exists: {save_path.exists()}")

# Step 1: Parse save file
print("\n[Step 1: Parse save file]")
save_data = parser.parse_save_file(save_path)

if save_data:
    print(f"✓ save_data type: {type(save_data)}")
    print(f"✓ save_data keys: {len(save_data.keys())}")
    print(f"✓ 'relics' in save_data: {'relics' in save_data}")
    if 'relics' in save_data:
        print(f"✓ save_data['relics']: {save_data['relics']}")
else:
    print("❌ save_data is None or empty!")
    sys.exit(1)

# Step 2: Extract run data
print("\n[Step 2: Extract run data]")
run_data = parser.extract_run_data(save_data, save_filename=save_path.name)

print(f"✓ run_data type: {type(run_data)}")
print(f"✓ run_data keys: {run_data.keys()}")
print(f"\nExtracted values:")
print(f"  character: {run_data.get('character')}")
print(f"  current_hp: {run_data.get('current_hp')}")
print(f"  max_hp: {run_data.get('max_hp')}")
print(f"  gold: {run_data.get('gold')}")
print(f"  deck length: {len(run_data.get('deck', []))}")
print(f"  relics: {run_data.get('relics')}")
print(f"  potions: {run_data.get('potions')}")

# Step 3: Full parse_and_extract
print("\n[Step 3: Full parse_and_extract]")
run_data2 = parser.parse_and_extract(save_path)

print(f"✓ run_data2 type: {type(run_data2)}")
print(f"\nExtracted values:")
print(f"  character: {run_data2.get('character')}")
print(f"  current_hp: {run_data2.get('current_hp')}")
print(f"  max_hp: {run_data2.get('max_hp')}")
print(f"  gold: {run_data2.get('gold')}")
print(f"  deck length: {len(run_data2.get('deck', []))}")
print(f"  relics: {run_data2.get('relics')}")
print(f"  potions: {run_data2.get('potions')}")

print("\n" + "=" * 70)
