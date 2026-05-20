"""Test fuzzy extraction for speech-to-text variations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder

r = StatusRecorder()

# Test cases
test_cases = [
    "Crushed joints, bowling bash, simmering fury",
    "Crush Joints, Bowling Bash, Simmering Fury",  # exact
    "crushed joint bowling bash simmering fury",  # missing 's'
    "crush joints bowl bash simmer fury",  # shortened words
]

for test in test_cases:
    print(f"\n=== Input: '{test}' ===")
    extracted = r.kb.extract_mentioned_items(test)
    print(f"Cards: {extracted.get('cards', [])}")
    print(f"Relics: {extracted.get('relics', [])}")
