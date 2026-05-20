import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import `src`
sys.path.insert(0, str(Path(__file__).parent.parent))
from src_old.advisor.save_reader import SaveReader

sr = SaveReader(os.getenv('SAVE_PATH'))
save_data = sr.read_save_state()
if not save_data:
    print('No save data found')
    raise SystemExit(1)

# search for 'nemesis' occurrences
matches = []

def walk(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}/{k}" if path else k
            if isinstance(v, str):
                if 'nemesis' in v.lower():
                    matches.append((p, v))
            walk(v, p)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(item, str):
                if 'nemesis' in item.lower():
                    matches.append((p, item))
            walk(item, p)

walk(save_data)
run_state = sr.extract_run_state(save_data)
print('Boss from save state:', run_state.get('boss'))
print('Elites detected by heuristic:', run_state.get('elites_defeated'))
print('\nMatches for "nemesis" in raw save data:')
if matches:
    for p, v in matches:
        print('-', p, '=>', v)
else:
    print('No "nemesis" string found in decoded save data')

print('\nSearching explicitly for elite_monster_list keys...')

def find_elite_lists(obj, path=''):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}/{k}" if path else k
            if isinstance(k, str) and k.lower() == 'elite_monster_list':
                found.append((p, v))
            if isinstance(v, (dict, list)):
                found.extend(find_elite_lists(v, p))
    elif isinstance(obj, list):
        for i, it in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(it, (dict, list)):
                found.extend(find_elite_lists(it, p))
    return found

elist = find_elite_lists(save_data)
if elist:
    for p, v in elist:
        print('-', p, '=>', v)
else:
    print('No elite_monster_list found')
