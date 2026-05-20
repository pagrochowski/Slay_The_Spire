"""Search for a card named Vengeance in the knowledge base."""
import sys
sys.path.insert(0, 'c:/Tragik/__DEV_folder/Slay_The_Spire')

from src_old.advisor.status_recorder import KnowledgeBase

kb = KnowledgeBase()

# Try to find Vengeance
print("Searching for 'Vengeance' in knowledge base...")
results = kb.find_cards("Vengeance", limit=5)

if results:
    print(f"\nFound {len(results)} matches:")
    for score, name, card in results:
        print(f"\n  Score: {score:.2f}")
        print(f"  Name: {name}")
        print(f"  Card: {card.get('name', 'NO NAME')}")
        print(f"  ID: {card.get('id', 'NO ID')}")
        print(f"  Type: {card.get('type', 'NO TYPE')}")
else:
    print("No matches found!")

# Let's also check all Watcher cards with similar starting letters
print("\n" + "="*60)
print("All Watcher cards starting with V:")
print("="*60)
for name, card in kb.cards.items():
    if card.get('color') == 'PURPLE' and name.startswith('v'):
        print(f"  - {card.get('name')} (ID: {name})")
