import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from src_old.advisor.status_recorder import StatusRecorder

if __name__ == '__main__':
    r = StatusRecorder()
    r.refresh_from_save()
    print('Run_Summary.md regenerated')
