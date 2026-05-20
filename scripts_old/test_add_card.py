import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src_old.advisor.status_recorder import StatusRecorder
from scripts.voice_recorder import create_command_handler

class StubParser:
    def parse(self, text):
        return {"intent":"add_card","cards":["Overclock"]}

rec = StatusRecorder()
handler = create_command_handler(rec, StubParser())
print(handler('I picked Overclock'))
