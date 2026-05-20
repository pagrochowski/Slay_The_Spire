from pathlib import Path
import sys
sys.path.insert(0,str(Path('.').resolve()))
from src_old.advisor.status_recorder import StatusRecorder
from scripts.voice_recorder import create_command_handler
class StubParser:
    def parse(self, text):
        return {"intent":"add_card","cards":["Statistic","Sadistic Nature","Magnetism","Apotheosis"]}
rec=StatusRecorder()
handler=create_command_handler(rec, StubParser())
print('handler output ->', handler('Statistic Nature Magnetism Apotheosis'))
print('current_choice ->', rec.current_choice)
