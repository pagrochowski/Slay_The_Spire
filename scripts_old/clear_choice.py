"""Quick script to clear the corrupted relic choice and verify card-only logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.voice_recorder import create_choice_handler
from src_old.advisor.status_recorder import StatusRecorder

r = StatusRecorder()
handler = create_choice_handler(r)

print(f"Current character: {r.current_run.get('character')}")
print(f"Current choice BEFORE clear: {r.current_choice}")
print()

# Clear the corrupted relic data
print("=== Clearing choice ===")
result = handler("clear")
print(f"Result: {result}")
print(f"Current choice AFTER clear: {r.current_choice}")
print()

# Verify Run_Summary.md was updated
with open("Run_Summary.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
    in_choice = False
    print("Run_Summary.md Current choice section:")
    for line in lines:
        if "**Current choice:**" in line:
            in_choice = True
        if in_choice:
            print(line.rstrip())
            if line.strip() == "---":
                break
