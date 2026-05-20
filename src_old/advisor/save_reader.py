"""
Slay the Spire Save File Reader.

Reads the game's autosave files to get current run state.
Uses spireslayer library to parse save files.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

# Defer importing spireslayer until runtime to avoid import-time warnings
Editor = None


class SaveReader:
    """Reads Slay the Spire save files to extract run state."""
    
    def __init__(self, save_path: str = None, backup_dir: str = None):
        """Initialize save reader.
        
        Args:
            save_path: Path to saves directory. If None, uses spireslayer's default Steam detection.
            backup_dir: Directory to store save file backups. Defaults to data/backups/ in project root.
        """
        self.save_path = Path(save_path) if save_path else None
        
        # Set up backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Default to data/backups/ in project root
            project_root = Path(__file__).parent.parent.parent
            self.backup_dir = project_root / "data" / "backups"
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Save backups will be stored in: {self.backup_dir}")
    
    def backup_save_file(self, save_file: Path) -> Optional[Path]:
        """Create a backup of the save file before processing.
        
        Args:
            save_file: Path to the save file to backup
            
        Returns:
            Path to the backed up file, or None if backup failed
        """
        try:
            # Create a timestamp for the backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get the original filename (without extension) and extension
            stem = save_file.stem
            suffix = save_file.suffix
            
            # Create backup filename: original_stem_timestamp.suffix
            backup_filename = f"{stem}_{timestamp}{suffix}"
            backup_path = self.backup_dir / backup_filename
            
            # Copy the file
            shutil.copy2(save_file, backup_path)
            logger.info(f"Backed up save file to: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to backup save file: {e}")
            return None
        
    def find_latest_autosave(self) -> Optional[Path]:
        """Find the most recently modified .autosave file.
        
        Returns:
            Path to latest autosave file, or None if not found.
        """
        if not self.save_path or not self.save_path.exists():
            logger.warning(f"Save path not found: {self.save_path}")
            return None
        
        # Find all .autosave files
        autosave_files = list(self.save_path.glob("*.autosave"))
        
        if not autosave_files:
            logger.warning(f"No .autosave files found in {self.save_path}")
            return None
        
        # Return the most recently modified
        latest = max(autosave_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Found latest autosave: {latest.name}")
        return latest
    
    def read_save_state(self) -> Optional[Dict[str, Any]]:
        """Read the current game state from save file.
        
        Returns:
            Dictionary with run state, or None if no save found.
        """
        try:
            # Import spireslayer here to avoid import-time side effects
            global Editor
            if Editor is None:
                try:
                    import importlib, sys as _sys
                    from spireslayer.editor import Editor as _Editor
                    Editor = _Editor
                except Exception as ie:
                    # Provide diagnostic context to help debug environment issues
                    try:
                        import importlib, sys as _sys
                        logger.error(f"spireslayer import failed: {ie}")
                        logger.debug(f"sys.executable: {_sys.executable}")
                        logger.debug(f"sys.path (first 10): {_sys.path[:10]}")
                    except Exception:
                        logger.error(f"spireslayer import failed and diagnostics could not be collected: {ie}")
                    return None
            
            # Find latest autosave
            autosave_file = self.find_latest_autosave()
            if not autosave_file:
                return None
            
            # Backup the save file before processing
            self.backup_save_file(autosave_file)
            
            # Initialize editor with the specific autosave file
            editor = Editor(autosave_path=str(autosave_file))
            
            # Read the save file - spireslayer Editor has a .decoded attribute
            save_data = editor.decoded
            
            if not save_data:
                logger.warning("Save file loaded but contains no data")
                return None
            
            logger.info("Successfully read save file")
            return save_data
            
        except Exception as e:
            logger.error(f"Failed to read save file: {e}")
            return None
    
    def extract_run_state(self, save_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant run state from save data.
        
        Args:
            save_data: Raw save data from spireslayer
            
        Returns:
            Structured run state dictionary
        """
        if not save_data:
            return None
        
        try:
            # Extract character name from filename (since 'name' is player name)
            # The autosave filename is CHARACTER.autosave
            autosave_file = self.find_latest_autosave()
            if autosave_file:
                character_name = autosave_file.stem  # Gets filename without extension
            else:
                character_name = save_data.get("name", "Unknown")
            
            # Extract basic stats
            ascension = save_data.get("ascension_level", 0)
            act = save_data.get("act_num", 1)
            floor = save_data.get("floor_num", 0)
            hp = save_data.get("current_health", 0)
            max_hp = save_data.get("max_health", 0)
            gold = save_data.get("gold", 0)
            
            # Extract deck (cards with upgrade info)
            deck = []
            cards = save_data.get("cards", [])
            for card in cards:
                if isinstance(card, dict):
                    card_id = card.get("id", "")
                    upgrades = card.get("upgrades", 0)
                    # Add + for each upgrade level
                    deck.append(card_id + ("+" * upgrades) if upgrades > 0 else card_id)
                elif isinstance(card, str):
                    deck.append(card)
            
            # Extract relics
            relics = save_data.get("relics", [])
            if isinstance(relics, list):
                # Relics might be dicts with 'id' or just strings
                relic_names = []
                for relic in relics:
                    if isinstance(relic, dict):
                        relic_names.append(relic.get("id", str(relic)))
                    else:
                        relic_names.append(str(relic))
                relics = relic_names
            
            # Extract potions
            potions = save_data.get("potions", [])
            if isinstance(potions, list):
                potion_names = []
                for potion in potions:
                    if isinstance(potion, dict):
                        potion_names.append(potion.get("id", str(potion)))
                    elif potion:  # Skip empty slots
                        potion_names.append(str(potion))
                potions = potion_names
            
            # Extract keys: different save versions use different field names
            def _get_key_flag(sd, names):
                for n in names:
                    if n in sd:
                        return bool(sd.get(n))
                return False

            keys = {
                "ruby": _get_key_flag(save_data, ["ruby_key", "has_ruby_key", "hasRubyKey", "has_ruby", "ruby"]),
                "emerald": _get_key_flag(save_data, ["emerald_key", "has_emerald_key", "hasEmeraldKey", "has_emerald", "emerald"]),
                "sapphire": _get_key_flag(save_data, ["sapphire_key", "has_sapphire_key", "hasSapphireKey", "has_sapphire", "sapphire"])
            }
            
            # Extract boss (if available)
            boss = save_data.get("boss", None)
            
            # Construct run state
            run_state = {
                "character": character_name,
                "ascension": ascension,
                "act": act,
                "floor": floor,
                "hp": hp,
                "max_hp": max_hp,
                "gold": gold,
                "deck": deck,
                "relics": relics,
                "potions": potions,
                "keys": keys,
                "boss": boss,
                # Populate defeated elites (heuristic based on save structure)
                "elites_defeated": [],
                "raw_save_data": save_data  # Keep raw data for debugging
            }

            # Heuristic: try to detect bottled cards (Bottled Flame/Lightning/Tornado)
            try:
                def _find_bottled_mappings(data, deck_ids):
                    """Recursively search save data for references to deck card ids
                    where the surrounding key or parent suggests a 'bottled' mapping.
                    Returns dict of {relic_name_lower: card_id}
                    """
                    mappings = {}

                    def _walk(obj, parent_key=None):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, (dict, list)):
                                    _walk(v, k)
                                else:
                                    if v and isinstance(v, str):
                                        vl = v.strip()
                                        # Exact match to a deck id
                                        if vl in deck_ids:
                                            if parent_key and 'bottl' in str(parent_key).lower():
                                                mappings[parent_key.lower()] = vl
                                            elif 'bottl' in str(k).lower():
                                                mappings[k.lower()] = vl
                        elif isinstance(obj, list):
                            for item in obj:
                                _walk(item, parent_key)

                    _walk(data)
                    return mappings

                # Collect deck ids without upgrades for matching
                deck_ids = [d.rstrip('+') for d in run_state.get('deck', [])]
                bottled = _find_bottled_mappings(save_data, deck_ids)
                if bottled:
                    # Normalize keys to readable relic names where possible
                    norm = {}
                    for k, v in bottled.items():
                        # attempt to map key to known bottled relics
                        if 'flame' in k:
                            norm['Bottled Flame'] = v
                        elif 'lightning' in k:
                            norm['Bottled Lightning'] = v
                        elif 'tornado' in k:
                            norm['Bottled Tornado'] = v
                        else:
                            norm[k] = v
                    run_state['bottled_map'] = norm
            except Exception:
                # Non-fatal heuristic failure
                pass

                # Heuristic: detect defeated elites in the save data
                try:
                    def _find_defeated_elites(data):
                        found = []

                        def _walk(obj):
                            if isinstance(obj, dict):
                                # If this node explicitly marks something as dead/defeated
                                is_dead = False
                                if 'isDead' in obj:
                                    is_dead = bool(obj.get('isDead'))
                                if 'dead' in obj:
                                    try:
                                        is_dead = is_dead or bool(obj.get('dead'))
                                    except Exception:
                                        pass

                                # If node has a 'type' indicating elite encounter
                                node_type = str(obj.get('type', '')).lower() if obj.get('type') else ''

                                # Candidate name fields
                                name = None
                                if 'name' in obj and isinstance(obj.get('name'), str):
                                    name = obj.get('name')
                                elif 'id' in obj and isinstance(obj.get('id'), str):
                                    name = obj.get('id')

                                # If this node looks like an elite and marked dead/defeated, capture it
                                if (('elite' in node_type) or ('elite' in ''.join(k.lower() for k in obj.keys()))) and name:
                                    if is_dead:
                                        found.append(name)

                                # Some save formats include encounter lists or keys named 'elites'
                                for k, v in obj.items():
                                    if isinstance(k, str) and 'elite' in k.lower() and isinstance(v, list):
                                        for item in v:
                                            if isinstance(item, str):
                                                found.append(item)
                                            elif isinstance(item, dict):
                                                if 'name' in item and isinstance(item['name'], str):
                                                    found.append(item['name'])

                                # Recurse
                                for v in obj.values():
                                    if isinstance(v, (dict, list)):
                                        _walk(v)

                            elif isinstance(obj, list):
                                for item in obj:
                                    if isinstance(item, (dict, list)):
                                        _walk(item)
                                    elif isinstance(item, str):
                                        # Strings in lists may be elite ids
                                        if 'elite' in item.lower():
                                            found.append(item)

                        _walk(data)
                        # Deduplicate preserving order
                        seen = set()
                        out = []
                        for x in found:
                            if not x:
                                continue
                            key = x.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            out.append(x)
                        return out

                    elites = _find_defeated_elites(save_data)
                    if elites:
                        run_state['elites_defeated'] = elites

                    # Also capture any explicit 'elite_monster_list' entries found anywhere in the save
                    try:
                        def _collect_elite_lists(obj):
                            found = []

                            def _walk(o):
                                if isinstance(o, dict):
                                    for k, v in o.items():
                                        if isinstance(k, str) and k.lower() == 'elite_monster_list' and isinstance(v, list):
                                            for item in v:
                                                if isinstance(item, str):
                                                    found.append(item)
                                                elif isinstance(item, dict):
                                                    if 'name' in item and isinstance(item['name'], str):
                                                        found.append(item['name'])
                                                    elif 'id' in item and isinstance(item['id'], str):
                                                        found.append(item['id'])
                                        if isinstance(v, (dict, list)):
                                            _walk(v)
                                elif isinstance(o, list):
                                    for it in o:
                                        if isinstance(it, (dict, list)):
                                            _walk(it)

                            _walk(obj)
                            # Dedupe preserving order
                            seen = set()
                            out = []
                            for x in found:
                                if not x:
                                    continue
                                k = x.lower()
                                if k in seen:
                                    continue
                                seen.add(k)
                                out.append(x)
                            return out

                        elite_list_entries = _collect_elite_lists(save_data)
                        if elite_list_entries:
                            cur = run_state.get('elites_defeated', [])
                            for e in elite_list_entries:
                                if e not in cur:
                                    cur.append(e)
                            run_state['elites_defeated'] = cur
                        # Additionally, look for metric-based damage entries that reference enemy names
                        try:
                            metric_names = set()

                            def _collect_metric_names(o):
                                if isinstance(o, dict):
                                    for kk, vv in o.items():
                                        if isinstance(kk, str) and 'metric' in kk.lower():
                                            # scan vv for string enemy names
                                            def _scan_values(x):
                                                if isinstance(x, str):
                                                    metric_names.add(x)
                                                elif isinstance(x, list):
                                                    for it in x:
                                                        _scan_values(it)
                                                elif isinstance(x, dict):
                                                    for vvv in x.values():
                                                        _scan_values(vvv)
                                            _scan_values(vv)
                                        if isinstance(vv, (dict, list)):
                                            _collect_metric_names(vv)
                                elif isinstance(o, list):
                                    for it in o:
                                        _collect_metric_names(it)

                            _collect_metric_names(save_data)
                            # If metrics reference known elite names, prioritize those as defeated
                            if metric_names:
                                cur = run_state.get('elites_defeated', [])
                                # Preserve order: add metric hits first if they match known entries
                                for m in metric_names:
                                    if isinstance(m, str):
                                        # normalize and add if not present
                                        if m not in cur:
                                            cur.append(m)
                                run_state['elites_defeated'] = cur
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    pass
            
            logger.info(f"Extracted run state: {character_name} A{ascension}, Act {act}, Floor {floor}")
            return run_state
            
        except Exception as e:
            logger.error(f"Failed to extract run state: {e}")
            return None
    
    def get_current_run(self) -> Optional[Dict[str, Any]]:
        """Get the current run state from the latest autosave.
        
        Returns:
            Structured run state, or None if no active run found.
        """
        save_data = self.read_save_state()
        if not save_data:
            return None
        
        return self.extract_run_state(save_data)
