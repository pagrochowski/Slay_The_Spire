"""Read cards from the most recent backup save file."""
from pathlib import Path
from spireslayer.editor import Editor

# Find most recent backup
backup_dir = Path("c:/Tragik/__DEV_folder/Slay_The_Spire/data/backups")
backups = sorted(backup_dir.glob("*.autosave"), key=lambda p: p.stat().st_mtime, reverse=True)

if backups:
    latest = backups[0]
    print(f"Reading from: {latest.name}\n")
    
    editor = Editor(autosave_path=str(latest))
    data = editor.decoded
    
    cards = data.get('cards', [])
    print(f"Cards in deck ({len(cards)} total):")
    print("=" * 50)
    for i, card in enumerate(cards, 1):
        card_id = card.get('id', card) if isinstance(card, dict) else card
        print(f"{i}. {card_id}")
    print("=" * 50)
    
    # Check for Vengeance and Vigilance
    card_ids = [card.get('id', card) if isinstance(card, dict) else card for card in cards]
    vengeance_count = sum(1 for card_id in card_ids if 'Vengeance' in card_id)
    vigilance_count = sum(1 for card_id in card_ids if 'Vigilance' in card_id)
    
    print(f"\nVengeance count: {vengeance_count}")
    print(f"Vigilance count: {vigilance_count}")
else:
    print("No backup files found!")
