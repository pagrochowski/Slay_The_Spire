#!/usr/bin/env python
"""
Debug script to check elite tracking in save files.
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from spireslayer.editor import Editor

# Load the latest save
save_path = Path(Config.GAME_SAVES_DIR) / "WATCHER.autosave"

if not save_path.exists():
    print(f"ERROR: Save not found: {save_path}")
    sys.exit(1)

print(f"Loading: {save_path.name}")

# Load with spireslayer
editor = Editor(autosave_path=str(save_path))
game_state = editor.decoded

print(f"\nSave data type: {type(game_state)}")

if not isinstance(game_state, dict):
    print("ERROR: Expected dict, got:", type(game_state))
    sys.exit(1)

print("\nLooking for elite-related fields...")
print("=" * 70)

# Check various fields that might track elites
fields_to_check = [
    'elites_killed',
    'elites_defeated', 
    'monsters_killed',
    'kill_count',
    'combat_history',
    'path_taken',
    'path',
    'map',
    'event_list',
    'cards_killed',
    'act_num',
    'elites1_killed',
    'elites2_killed', 
    'elites3_killed',
    'elite_monster_list'
]

for field in fields_to_check:
    if field in game_state:
        value = game_state[field]
        print(f"\nFOUND {field}:")
        print(f"   Type: {type(value)}")
        if isinstance(value, (list, dict)):
            print(f"   Length: {len(value)}")
            if len(value) <= 20:  # Show value if small enough
                print(f"   Value: {value}")
            else:
                print(f"   Value (first 5): {value[:5] if isinstance(value, list) else list(value.items())[:5]}")
        else:
            print(f"   Value: {value}")

# Check all keys
print("\n\nAll available keys:")
print("=" * 70)
for key in sorted(game_state.keys()):
    value = game_state[key]
    print(f"  {key}: {type(value).__name__}", end="")
    if isinstance(value, (int, str, bool, float)):
        if len(str(value)) < 50:
            print(f" = {value}")
        else:
            print(f" = {str(value)[:47]}...")
    elif isinstance(value, (list, dict)):
        print(f" (len={len(value)})")
    else:
        print()
