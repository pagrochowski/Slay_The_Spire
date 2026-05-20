"""Check what's actually in the save file deck."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.save_reader import SaveReader
import os

save_path = os.getenv("SAVE_PATH")
reader = SaveReader(save_path)

# Read the raw save file
save_data = reader.read_save_state()
print("Raw save file cards:")
print("=" * 60)

cards = save_data.get("cards", [])
print(f"Total cards in save: {len(cards)}\n")

for i, card in enumerate(cards, 1):
    if isinstance(card, dict):
        card_id = card.get("id", "")
        upgrades = card.get("upgrades", 0)
        print(f"{i}. {card_id} (upgrades: {upgrades})")
    else:
        print(f"{i}. {card}")

# Get extracted run state
print("\n" + "=" * 60)
print("Extracted deck from run state:")
print("=" * 60)

run = reader.get_current_run()
deck = run.get("deck", [])
print(f"Total deck entries: {len(deck)}\n")

from collections import Counter
counts = Counter(deck)
for card, count in sorted(counts.items()):
    print(f"{count}x {card}")
