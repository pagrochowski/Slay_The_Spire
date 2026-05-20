"""Check the raw save file data for the mysterious Vengeance card."""
from pathlib import Path
from spireslayer.editor import Editor
import json

# Find most recent backup
backup_dir = Path("c:/Tragik/__DEV_folder/Slay_The_Spire/data/backups")
backups = sorted(backup_dir.glob("*.autosave"), key=lambda p: p.stat().st_mtime, reverse=True)

if backups:
    latest = backups[0]
    print(f"Reading from: {latest.name}\n")
    
    editor = Editor(autosave_path=str(latest))
    data = editor.decoded
    
    cards = data.get('cards', [])
    print(f"Raw card data for positions 9-11:")
    print("="*60)
    for i in range(8, 11):
        if i < len(cards):
            card = cards[i]
            print(f"\nCard {i+1}:")
            print(json.dumps(card, indent=2))
    print("="*60)
    
    # Check if it's maybe "Vigilance" duplicated
    card_ids = [c.get('id') if isinstance(c, dict) else c for c in cards]
    print(f"\nAll card IDs:")
    for i, cid in enumerate(card_ids, 1):
        print(f"  {i}. {cid}")
