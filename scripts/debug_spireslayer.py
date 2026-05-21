#!/usr/bin/env python
"""
Debug save parser issue - check what spireslayer returns.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from spireslayer.editor import Editor

save_path = Path(Config.GAME_SAVES_DIR) / "WATCHER.autosave"

print("=" * 70)
print("SPIRESLAYER DECODING TEST")
print("=" * 70)

print(f"\nSave file: {save_path}")
print(f"Exists: {save_path.exists()}")
print(f"Size: {save_path.stat().st_size} bytes")

# Load with spireslayer
print("\nLoading with spireslayer...")
editor = Editor(autosave_path=str(save_path))

print(f"\nEditor object: {editor}")
print(f"Editor.decoded type: {type(editor.decoded)}")
print(f"Editor.decoded is None: {editor.decoded is None}")

if editor.decoded:
    print(f"Editor.decoded keys: {len(editor.decoded.keys())}")
    print(f"\nFirst 20 keys:")
    for i, key in enumerate(list(editor.decoded.keys())[:20]):
        value = editor.decoded[key]
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
    
    # Check specific fields
    print(f"\nSpecific fields:")
    print(f"  'cards' in decoded: {'cards' in editor.decoded}")
    print(f"  'relics' in decoded: {'relics' in editor.decoded}")
    print(f"  'current_health' in decoded: {'current_health' in editor.decoded}")
    print(f"  'max_health' in decoded: {'max_health' in editor.decoded}")
    print(f"  'gold' in decoded: {'gold' in editor.decoded}")
    
    if 'relics' in editor.decoded:
        relics = editor.decoded['relics']
        print(f"\n  Relics: {relics}")
    
    if 'cards' in editor.decoded:
        cards = editor.decoded['cards']
        print(f"\n  Cards count: {len(cards)}")
        if cards:
            print(f"  First card: {cards[0]}")
else:
    print("\n❌ editor.decoded is None or empty!")

print("\n" + "=" * 70)
