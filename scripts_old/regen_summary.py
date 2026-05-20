"""Force regenerate Run_Summary.md to see if duplicate persists."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder

r = StatusRecorder()

print("Current deck from recorder:")
deck = r.current_run.get("deck", [])
print(f"Total cards: {len(deck)}")

from collections import Counter
counts = Counter(deck)
print("\nDeck breakdown:")
for card, count in sorted(counts.items()):
    print(f"  {count}x {card}")

print("\nRegenerating Run_Summary.md...")
r.create_summary_file(skip_refresh=True)

print("\nChecking Run_Summary.md for Vigilance entries...")
with open("Run_Summary.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
    vigilance_count = 0
    for i, line in enumerate(lines):
        if "Vigilance" in line and "Deck" not in line:
            vigilance_count += 1
            print(f"Line {i+1}: {line.rstrip()}")
    
    print(f"\nTotal Vigilance entries in summary: {vigilance_count}")
    print(f"Expected: 1")
    if vigilance_count > 1:
        print("❌ DUPLICATE FOUND")
    else:
        print("✅ NO DUPLICATE")
