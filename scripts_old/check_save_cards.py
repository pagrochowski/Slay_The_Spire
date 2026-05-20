"""Check what cards are actually in the save file."""
import sys
sys.path.insert(0, 'c:/Tragik/__DEV_folder/Slay_The_Spire')

from src_old.advisor.save_reader import SaveReader

reader = SaveReader()
save_data = reader.read_save_state()

if not save_data:
    print("ERROR: No save file found!")
    sys.exit(1)
    
state = reader.extract_run_state(save_data)

print("Cards in save file:")
print("=" * 50)
for i, card in enumerate(state['deck'], 1):
    print(f"{i}. {card}")
print("=" * 50)
print(f"\nTotal: {len(state['deck'])} cards")

# Check for Vengeance and Vigilance specifically
vengeance_count = sum(1 for card in state['deck'] if 'vengeance' in card.lower())
vigilance_count = sum(1 for card in state['deck'] if 'vigilance' in card.lower())

print(f"\nVengeance count: {vengeance_count}")
print(f"Vigilance count: {vigilance_count}")
