import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder
from scripts.voice_recorder import create_command_handler

class StubParser:
    def parse(self, text):
        return {"intent": "card_choice", "cards": ["Sunder"]}

rec = StatusRecorder()
handler = create_command_handler(rec, StubParser())
print('Input: single card choice Sunder')
print('Output:', handler('Card choice Sunder'))
