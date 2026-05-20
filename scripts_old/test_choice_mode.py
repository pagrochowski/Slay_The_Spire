import sys
from pathlib import Path
# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.voice_recorder import create_choice_handler
from src_old.advisor.status_recorder import StatusRecorder

r = StatusRecorder()
handler = create_choice_handler(r)

# Clear any existing choice data
r.clear_choice()
print(f'Current character: {r.current_run.get("character")}')
print(f'Starting choice: {r.current_choice}\n')

# Test 1: Simple card names
print('=== Test 1: Simple Watcher card names ===')
res = handler('Bowling Bash, Third Eye, Tranquility')
print(f'Input: "Bowling Bash, Third Eye, Tranquility"')
print(f'Result: {res}')
print(f'Choice: {r.current_choice}\n')

# Test 2: Space-separated (no commas)
r.clear_choice()
print('=== Test 2: Space-separated (like voice transcription) ===')
res = handler('Bowling Bash Third Eye Tranquility')
print(f'Input: "Bowling Bash Third Eye Tranquility"')
print(f'Result: {res}')
print(f'Choice: {r.current_choice}\n')

# Test 3: Relics only
r.clear_choice()
print('=== Test 3: Relic names only ===')
res = handler('Snecko Eye, Ginger, Cursed Key')
print(f'Input: "Snecko Eye, Ginger, Cursed Key"')
print(f'Result: {res}')
print(f'Choice: {r.current_choice}\n')

# Test 4: Verify Run_Summary.md shows the last choice
print('=== Run_Summary.md excerpt ===')
with open("Run_Summary.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
    in_choice = False
    for line in lines:
        if "**Current choice:**" in line:
            in_choice = True
        if in_choice:
            print(line.rstrip())
            if line.strip() == "---":
                break
