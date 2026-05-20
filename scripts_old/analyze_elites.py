import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import os
from src_old.advisor.save_reader import SaveReader

sr = SaveReader(os.getenv('SAVE_PATH'))
save_data = sr.read_save_state()
if not save_data:
    print('No save data found')
    raise SystemExit(1)

# collect elite_monster_list
elite_list = None
if isinstance(save_data, dict) and 'elite_monster_list' in save_data:
    elite_list = save_data.get('elite_monster_list')

print('elite_monster_list:', elite_list)

candidates = set()
if elite_list and isinstance(elite_list, list):
    for e in elite_list:
        if isinstance(e, str):
            candidates.add(e)

# fallback: include common names we saw
candidates = sorted(candidates)
print('\nCandidates to inspect:', candidates)

# search for occurrences and nearby defeat indicators
indicators = ['isDead','is_dead','dead','defeated','dead_monsters','current_hp','hp','current_health']

matches = []

def walk(obj, path='', parent=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}/{k}" if path else k
            # if value is a string equal to a candidate
            if isinstance(v, str) and v in candidates:
                # collect parent context
                ctx = {}
                # look for indicators in the current dict
                for ind in indicators:
                    if ind in obj:
                        ctx[ind] = obj.get(ind)
                # also inspect sibling keys for numeric hp fields
                for sk, sv in obj.items():
                    if isinstance(sv, (int, float, str)):
                        if any(ind in sk.lower() for ind in ['hp','health']):
                            ctx[sk] = sv
                matches.append((v, p, ctx, obj))
            # recursive
            if isinstance(v, (dict, list)):
                walk(v, p, obj)
    elif isinstance(obj, list):
        for i, it in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(it, str) and it in candidates:
                ctx = {}
                matches.append((it, p, ctx, None))
            if isinstance(it, (dict, list)):
                walk(it, p, obj)

walk(save_data)

print('\nFound occurrences and context:')
for name, path, ctx, parent in matches:
    print(f"- {name} @ {path}")
    if ctx:
        print('  context indicators:')
        for k, v in ctx.items():
            print(f'    {k}: {v}')
    # try to detect if parent contains 'isDead' or similar deeper
    if parent and isinstance(parent, dict):
        for key in ['isDead','is_dead','dead','defeated']:
            if key in parent:
                print(f'  parent.{key} = {parent[key]}')

# Heuristic: determine defeated elites by presence in metric_damage_taken 'enemies' entries
print('\nChecking metrics for damage/death references...')

def find_metrics(obj, path=''):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}/{k}" if path else k
            if isinstance(v, dict) or isinstance(v, list):
                out.extend(find_metrics(v, p))
            else:
                if isinstance(v, str) and v in candidates:
                    out.append((p, v))
    elif isinstance(obj, list):
        for i, it in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(it, (dict, list)):
                out.extend(find_metrics(it, p))
            elif isinstance(it, str) and it in candidates:
                out.append((p, it))
    return out

metric_hits = find_metrics(save_data)
for p, v in metric_hits:
    print('-', p, '=>', v)

# Summarize likely defeated elites based on contexts
likely_defeated = set()
for name, path, ctx, parent in matches:
    # if any indicator suggests death
    if ctx:
        if any((k in ctx and ctx[k]) for k in ['isDead','dead','defeated','is_dead']):
            likely_defeated.add(name)
    # check if path contains 'metric_damage_taken' or similar
    if 'metric_damage' in path.lower() or 'damage' in path.lower():
        likely_defeated.add(name)

# fallback: if no ctx, use elite_monster_list but filter by occurrences in metric_hits
if not likely_defeated and candidates:
    # use metric hits to pick which of candidate names are present in damage metrics
    for p, v in metric_hits:
        if v in candidates:
            likely_defeated.add(v)

print('\nLikely defeated elites based on heuristics:', sorted(likely_defeated))

# Print run_state elites from SaveReader for comparison
run_state = sr.extract_run_state(save_data)
print('\nrun_state[elites_defeated]:', run_state.get('elites_defeated'))
print('boss:', run_state.get('boss'))
