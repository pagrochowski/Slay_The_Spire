"""Test the specific issue: 'Crushed joints' should be extracted as 'Crush Joints'."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.voice_recorder import create_choice_handler
from src_old.advisor.status_recorder import StatusRecorder

r = StatusRecorder()
handler = create_choice_handler(r)

print(f'Current character: {r.current_run.get("character")}\n')

# Test the exact case from the user's log
print('=== Test: "Crushed joints, bowling bash, simmering fury" ===')
r.clear_choice()
res = handler('Crushed joints, bowling bash, simmering fury')
print(f'Result: {res}')
print(f'Choice options: {r.current_choice.get("options", [])}')
print(f'Expected: 3 cards (Crush Joints, Bowling Bash, Simmering Fury)')
print(f'Got: {len(r.current_choice.get("options", []))} cards')

if len(r.current_choice.get("options", [])) == 3:
    print("\n✅ SUCCESS: All 3 cards were extracted!")
else:
    print(f"\n❌ FAILED: Only {len(r.current_choice.get('options', []))} cards extracted")
    print("Missing cards:", set(['Crush Joints', 'Bowling Bash', 'Simmering Fury']) - set(r.current_choice.get('options', [])))
