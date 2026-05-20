import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder
from scripts.voice_recorder import create_command_handler

class StubParser:
    def parse(self, text):
        # Simulate parser returning unknown but extracting a card
        return {"intent": "unknown", "cards": ["FTL"]}

rec = StatusRecorder()
handler = create_command_handler(rec, StubParser())
print('Input: Cart Choice FTL')
print('Output:', handler('Cart Choice FTL'))
