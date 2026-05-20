import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src_old.advisor.save_reader import SaveReader

sr = SaveReader(os.getenv('SAVE_PATH'))
sd = sr.read_save_state()
if not sd:
    print('No save data loaded')
    raise SystemExit(1)

print('ROOT KEYS:', list(sd.keys()))
for k in ['ruby_key','rubyKey','ruby','hasRuby','ruby_key_obtained','emerald_key','emeraldKey','sapphire_key','sapphireKey']:
    if k in sd:
        print(k, '=>', sd.get(k))

# traverse to find key-related entries
def walk(o, path=''):
    if isinstance(o, dict):
        for kk, vv in o.items():
            p = f"{path}/{kk}" if path else kk
            if any(s in kk.lower() for s in ['ruby','emerald','sapphire','key']):
                print('Found field:', p, '=>', vv)
            if isinstance(vv, (dict, list)):
                walk(vv, p)
            elif isinstance(vv, str):
                if vv.lower() in ['ruby','emerald','sapphire']:
                    print('Found string value:', p, '=>', vv)
    elif isinstance(o, list):
        for i, it in enumerate(o):
            walk(it, f"{path}[{i}]")

walk(sd)
rs = sr.extract_run_state(sd)
print('run_state keys:', rs.get('keys'))
