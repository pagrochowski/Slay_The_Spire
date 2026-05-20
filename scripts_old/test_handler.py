import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder
from scripts.voice_recorder import create_command_handler

class StubParser:
    def parse(self, text):
        # Simulate the parser returning the detected intent and raw card mentions
        return {"intent": "card_choice", "cards": ["Streamline", "Melter"], "relics": []}

rec = StatusRecorder()
parser = StubParser()
handler = create_command_handler(rec, parser)

text = "Card choice go for the ice streamline melter"
print('Input text:', text)
print('Handler output:')
print(handler(text))
