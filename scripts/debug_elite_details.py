#!/usr/bin/env python
"""
Debug script to check which elites were defeated.
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

print(f"Loading: {save_path.name}\n")

# Load with spireslayer
editor = Editor(autosave_path=str(save_path))
game_state = editor.decoded

# Check elite tracking
print("Elite Tracking:")
print("=" * 70)
print(f"Elites killed in Act 1: {game_state.get('elites1_killed', 0)}")
print(f"Elites killed in Act 2: {game_state.get('elites2_killed', 0)}")
print(f"Elites killed in Act 3: {game_state.get('elites3_killed', 0)}")
print(f"\nElite monster pool: {game_state.get('elite_monster_list', [])}")

# Check metric_path_taken to see the actual path
print("\n\nPath Taken (metric_path_taken):")
print("=" * 70)
path_taken = game_state.get('metric_path_taken', [])
for i, room_type in enumerate(path_taken):
    print(f"Floor {i}: {room_type}")

# Check metric_damage_taken to see combat encounters
print("\n\nDamage Taken (metric_damage_taken):")
print("=" * 70)
damage_taken = game_state.get('metric_damage_taken', [])
for i, encounter in enumerate(damage_taken):
    print(f"Combat {i+1}: {encounter}")

# Check metric_path_per_floor for more details
print("\n\nPath Per Floor (metric_path_per_floor):")
print("=" * 70)
path_per_floor = game_state.get('metric_path_per_floor', [])
for i, floor_data in enumerate(path_per_floor):
    print(f"Floor {i+1}: {floor_data}")

# Look for any field containing "elite" or "Elite"
print("\n\nAll fields containing 'elite':")
print("=" * 70)
for key in sorted(game_state.keys()):
    if 'elite' in key.lower():
        value = game_state[key]
        if isinstance(value, (list, dict)):
            print(f"{key}: {type(value).__name__} (len={len(value)})")
            if len(value) <= 10:
                print(f"  Value: {value}")
        else:
            print(f"{key}: {value}")
