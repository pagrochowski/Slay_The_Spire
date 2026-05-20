"""
Slay the Spire Status Recorder (Refactored for Save File Integration).

Reads run state from game save files using spireslayer.
Only tracks current decision points manually via voice commands.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from src_old.advisor.save_reader import SaveReader


class KnowledgeBase:
    """Local knowledge base loaded from split JSON files in data/knowledge/."""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or PROJECT_ROOT / "data" / "knowledge"
        self.cards = {}
        self.relics = {}
        self.potions = {}
        self.bosses = {}
        self._load_data()
    
    def _load_split_json(self, pattern: str) -> List[Dict]:
        """Load data from multiple JSON files matching a pattern."""
        items = []
        for filepath in self.data_dir.glob(pattern):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    # Extract items from the data field
                    if "cards" in data:
                        items.extend(data["cards"])
                    elif "relics" in data:
                        items.extend(data["relics"])
                    elif "enemies" in data:
                        items.extend(data["enemies"])
                    elif "potions" in data:
                        items.extend(data["potions"])
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")
        return items
    
    def _load_data(self):
        """Load all data from knowledge base JSON files."""
        # Load cards
        cards_list = self._load_split_json("cards/*.json")
        for card in cards_list:
            name = card.get("name", "").lower()
            if name:
                self.cards[name] = card
        logger.info(f"Loaded {len(self.cards)} cards from split files")
        
        # Load relics
        relics_list = self._load_split_json("relics/*.json")
        for relic in relics_list:
            name = relic.get("name", "").lower()
            if name:
                self.relics[name] = relic
        logger.info(f"Loaded {len(self.relics)} relics from split files")
        
        # Load potions
        potions_file = self.data_dir / "potions.json"
        if potions_file.exists():
            with open(potions_file, encoding="utf-8") as f:
                data = json.load(f)
                potions_list = data.get("potions", [])
                for potion in potions_list:
                    name = potion.get("name", "").lower()
                    if name:
                        self.potions[name] = potion
            logger.info(f"Loaded {len(self.potions)} potions")
        
        # Load bosses
        bosses_file = PROJECT_ROOT / "data" / "raw" / "bosses.json"
        if bosses_file.exists():
            with open(bosses_file, encoding="utf-8") as f:
                bosses_data = json.load(f)
                for act_bosses in bosses_data.values():
                    for boss_name, boss_info in act_bosses.items():
                        self.bosses[boss_name] = boss_info
            logger.info(f"Loaded {len(self.bosses)} boss info entries")
    
    def find_cards(self, query: str, limit: int = 5) -> list:
        """Find cards matching a query using fuzzy matching."""
        query_lower = query.lower().strip()
        results = []
        
        for name, card in self.cards.items():
            if query_lower == name:
                results.append((1.0, name, card))
                continue
            if query_lower in name:
                results.append((0.9, name, card))
                continue
            ratio = SequenceMatcher(None, query_lower, name).ratio()
            if ratio >= 0.75:  # Stricter threshold to prevent false matches like Vengeance→Vigilance
                results.append((ratio, name, card))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]
    
    def find_relics(self, query: str, limit: int = 5) -> list:
        """Find relics matching a query."""
        query_lower = query.lower().strip()
        results = []
        
        for name, relic in self.relics.items():
            if query_lower == name:
                results.append((1.0, name, relic))
                continue
            if query_lower in name:
                results.append((0.9, name, relic))
                continue
            ratio = SequenceMatcher(None, query_lower, name).ratio()
            if ratio >= 0.75:  # Stricter threshold to prevent false matches
                results.append((ratio, name, relic))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]

    def get_card_info(self, card_name: str) -> Optional[str]:
        """Return a short description for a card from the KB."""
        if not card_name:
            return None
        # Remove upgrade markers like +
        base = card_name.rstrip('+').strip().lower()
        card = self.cards.get(base)
        if not card:
            # Try fuzzy lookup
            matches = self.find_cards(card_name, limit=1)
            if not matches:
                return None
            card = matches[0][2]
        desc = card.get("description") or card.get("description_upgraded") or ""
        return desc

    def get_relic_info(self, relic_name: str) -> Optional[str]:
        if not relic_name:
            return None
        base = relic_name.lower().strip()
        relic = self.relics.get(base)
        if not relic:
            matches = self.find_relics(relic_name, limit=1)
            if not matches:
                return None
            relic = matches[0][2]
        return relic.get("description") or relic.get("flavor_text") or None

    def get_potion_info(self, potion_name: str) -> Optional[str]:
        if not potion_name:
            return None
        base = potion_name.lower().strip()
        potion = self.potions.get(base)
        if not potion:
            return None
        return potion.get("description") or None

    def extract_mentioned_items(self, text: str) -> dict:
        """Extract card and relic names mentioned in free text using fuzzy word-boundary matching.
        
        Handles speech-to-text variations (e.g., 'crushed joints' -> 'crush joints').
        Filters out shorter matches that are substrings of longer matches to avoid
        false positives (e.g., "Bash" when "Bowling Bash" was already matched).
        """
        import re
        from difflib import SequenceMatcher
        text_lower = (text or "").lower()
        found = {"cards": [], "relics": []}

        # Match longest names first to avoid partial matches
        sorted_cards = sorted(self.cards.keys(), key=len, reverse=True)
        sorted_relics = sorted(self.relics.keys(), key=len, reverse=True)

        card_matches_with_pos = []
        for name in sorted_cards:
            # First try exact match
            pattern = r'\b' + re.escape(name) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                card_matches_with_pos.append((name, match.start(), match.end()))
                continue
            
            # For multi-word names, try fuzzy matching each word
            # (handles "crushed joints" -> "crush joints")
            if ' ' in name:
                name_words = name.split()
                # Split text into tokens
                text_tokens = re.findall(r'\b\w+\b', text_lower)
                
                # Look for sequences of words similar to the card name
                for i in range(len(text_tokens) - len(name_words) + 1):
                    candidate = text_tokens[i:i + len(name_words)]
                    # Check if each word is similar
                    all_similar = True
                    for card_word, text_word in zip(name_words, candidate):
                        ratio = SequenceMatcher(None, card_word, text_word).ratio()
                        if ratio < 0.75:  # Allow 25% difference for speech-to-text errors
                            all_similar = False
                            break
                    
                    if all_similar:
                        # Find position in original text
                        candidate_phrase = ' '.join(candidate)
                        start_pos = text_lower.find(candidate_phrase)
                        if start_pos >= 0:
                            end_pos = start_pos + len(candidate_phrase)
                            card_matches_with_pos.append((name, start_pos, end_pos))
                            break

        # Filter out overlapping/substring matches (keep longer ones)
        filtered_cards = []
        for i, (name1, start1, end1) in enumerate(card_matches_with_pos):
            is_overlapped = False
            for j, (name2, start2, end2) in enumerate(card_matches_with_pos):
                if i == j:
                    continue
                # Check if name1's match overlaps with name2's match and name2 is longer
                if start1 >= start2 and end1 <= end2 and len(name1) < len(name2):
                    is_overlapped = True
                    break
            if not is_overlapped:
                filtered_cards.append(name1)
        
        found["cards"] = filtered_cards

        # Same fuzzy matching for relics
        relic_matches_with_pos = []
        for name in sorted_relics:
            # First try exact match
            pattern = r'\b' + re.escape(name) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                relic_matches_with_pos.append((name, match.start(), match.end()))
                continue
            
            # For multi-word relic names, try fuzzy matching
            if ' ' in name:
                name_words = name.split()
                text_tokens = re.findall(r'\b\w+\b', text_lower)
                
                for i in range(len(text_tokens) - len(name_words) + 1):
                    candidate = text_tokens[i:i + len(name_words)]
                    all_similar = True
                    for relic_word, text_word in zip(name_words, candidate):
                        ratio = SequenceMatcher(None, relic_word, text_word).ratio()
                        if ratio < 0.75:
                            all_similar = False
                            break
                    
                    if all_similar:
                        candidate_phrase = ' '.join(candidate)
                        start_pos = text_lower.find(candidate_phrase)
                        if start_pos >= 0:
                            end_pos = start_pos + len(candidate_phrase)
                            relic_matches_with_pos.append((name, start_pos, end_pos))
                            break

        filtered_relics = []
        for i, (name1, start1, end1) in enumerate(relic_matches_with_pos):
            is_overlapped = False
            for j, (name2, start2, end2) in enumerate(relic_matches_with_pos):
                if i == j:
                    continue
                if start1 >= start2 and end1 <= end2 and len(name1) < len(name2):
                    is_overlapped = True
                    break
            if not is_overlapped:
                filtered_relics.append(name1)
        
        found["relics"] = filtered_relics

        return found


class StatusRecorder:
    """Slay the Spire status recorder - reads state from game save files."""
    
    def __init__(self):
        load_dotenv()
        
        # Load knowledge base
        self.kb = KnowledgeBase()
        
        # Initialize save reader
        save_path = os.getenv("SAVE_PATH")
        self.save_reader = SaveReader(save_path)
        
        # Current decision tracking (not in save file)
        self.current_choice = {
            "type": None,  # "cards", "relics", "shop", None
            "options": []
        }
        
        # Current run state from save file
        self.current_run = None
        
        # Refresh on init
        self.refresh_from_save()
        
        logger.info(f"Status recorder initialized")
        logger.info(f"Knowledge base: {len(self.kb.cards)} cards, {len(self.kb.relics)} relics")
    
    def refresh_from_save(self, skip_create_summary: bool = False) -> str:
        """Refresh run state from game save file."""
        run_state = self.save_reader.get_current_run()
        
        if not run_state:
            self.current_run = None
            logger.warning("No active game found in save file")
            return "Current game not found"
        
        self.current_run = run_state
        logger.info(f"Refreshed from save: {run_state['character']} A{run_state['ascension']}, Act {run_state['act']}")
        
        # Update summary file (skip refresh to avoid infinite loop)
        if not skip_create_summary:
            self.create_summary_file(silent=True, skip_refresh=True)
        
        return f"Refreshed: {run_state['character']} A{run_state['ascension']}"
    
    def get_run_status(self) -> str:
        """Get current run status."""
        if not self.current_run:
            return "No active game found"
        
        r = self.current_run
        deck_size = len(r.get("deck", []))
        relic_count = len(r.get("relics", []))
        
        status = f"Playing {r['character']} Ascension {r['ascension']}. "
        status += f"Act {r['act']}, Floor {r.get('floor', 0)}. "
        status += f"HP {r['hp']}/{r['max_hp']}, {r['gold']} gold. "
        status += f"Deck has {deck_size} cards, {relic_count} relics."
        
        return status
    
    def set_card_choice(self, options: list) -> str:
        """Record current card choice options."""
        # First refresh from save file to get latest run state
        self.refresh_from_save(skip_create_summary=True)
        
        if not self.current_run:
            return "No active game found"
        
        self.current_choice = {
            "type": "cards",
            "options": options
        }
        self.create_summary_file(silent=True, skip_refresh=True)
        return "Card choice recorded"
    
    def set_relic_choice(self, options: list) -> str:
        """Record current relic choice options."""
        # First refresh from save file to get latest run state
        self.refresh_from_save(skip_create_summary=True)
        
        if not self.current_run:
            return "No active game found"
        
        self.current_choice = {
            "type": "relics",
            "options": options
        }
        self.create_summary_file(silent=True, skip_refresh=True)
        return "Relic choice recorded"
    
    def clear_choice(self) -> str:
        """Clear current decision point."""
        # First refresh from save file to get latest run state
        self.refresh_from_save(skip_create_summary=True)
        
        self.current_choice = {
            "type": None,
            "options": []
        }
        self.create_summary_file(silent=True, skip_refresh=True)
        return "Choice cleared"
    
    def create_summary_file(self, silent: bool = False, skip_refresh: bool = False) -> str:
        """Generate Run_Summary.md from current game state."""
        # First refresh from save file to get latest run state (unless skipped)
        if not skip_refresh:
            self.refresh_from_save()
        
        if not self.current_run:
            if not silent:
                return "No active game to summarize"
            return ""
        
        r = self.current_run
        
        # Format deck as bullet list with descriptions and energy cost
        from collections import Counter
        deck = r.get("deck", [])
        deck_counts = Counter(deck)
        logger.debug(f"Deck counts from Counter: {deck_counts}")
        deck_lines = []
        for card, count in sorted(deck_counts.items()):
            logger.debug(f"Processing card: '{card}' with count: {count}")
            # Normalize display name: prefer KB canonical name when available
            has_plus = card.endswith('+')
            raw_name = str(card)
            base_name = raw_name.rstrip('+').strip()
            # Normalize common save tokens (e.g., Defend_B -> Defend)
            base_for_lookup = base_name.replace('_b', '').replace('_B', '').replace('_', ' ').strip()

            kb_card = None
            matches = self.kb.find_cards(base_for_lookup, limit=1)
            if matches:
                kb_card = matches[0][2]
                canonical = kb_card.get('name')
            else:
                canonical = base_name

            display = f"{count}x {canonical + ('+' if has_plus else '')}" if count > 1 else (canonical + ('+' if has_plus else ''))
            logger.debug(f"Display name: '{display}', canonical: '{canonical}'")

            # Lookup description, type, and cost from KB
            desc = self.kb.get_card_info(canonical + ('+' if has_plus else ''))
            card_type = None
            cost = None
            if kb_card:
                t = kb_card.get('type')
                if t:
                    card_type = t.capitalize()
                # Get cost: use upgraded cost if card is upgraded
                if has_plus:
                    cost = kb_card.get('cost_upgraded')
                    if cost is None:
                        cost = kb_card.get('cost')
                else:
                    cost = kb_card.get('cost')
                # Handle special case: X cost
                if cost == 'X' or cost == 'x':
                    cost_str = 'X'
                elif cost is not None:
                    cost_str = str(cost)
                else:
                    cost_str = None

            # Replace game tokens in descriptions (e.g., [B] -> energy)
            if desc:
                desc = desc.replace('[B]', 'energy')

            # Build line with all info
            line_parts = [f"- {display}"]
            if cost_str is not None:
                line_parts.append(f" [{cost_str}]")
            if card_type:
                line_parts.append(f" ({card_type})")
            if desc:
                line_parts.append(f": {desc}")
            deck_lines.append("".join(line_parts))
        deck_str = "\n".join(deck_lines) if deck_lines else "- None"
        
        # Format relics
        relics = r.get("relics", [])
        relic_lines = []
        # If save provided bottled mappings, attach them to relic descriptions
        bottled_map = r.get('bottled_map', {}) if isinstance(r, dict) else {}
        for relic in relics:
            desc = self.kb.get_relic_info(relic)
            extra = ''
            # Check for bottled mapping (keys in bottled_map may be canonical relic names)
            bottled_card = None
            for k, v in bottled_map.items():
                if k.lower() == relic.lower() or k.lower().endswith(relic.lower()):
                    bottled_card = v
                    break

            if bottled_card:
                # Map bottled card id -> canonical name via KB
                mapped = self.kb.find_cards(bottled_card, limit=1)
                if mapped:
                    bottled_name = mapped[0][2].get('name')
                else:
                    bottled_name = bottled_card
                # If the bottled card appears upgraded in the run deck, append '+'
                try:
                    deck_entries = r.get('deck', [])
                    for de in deck_entries:
                        if not isinstance(de, str):
                            continue
                        if de.lower().rstrip('+').strip() == bottled_card.lower().rstrip('+').strip():
                            if de.endswith('+') and not bottled_name.endswith('+'):
                                bottled_name = bottled_name + '+'
                            break
                except Exception:
                    pass
                extra = f" (bottled: {bottled_name})"

            if desc:
                relic_lines.append(f"- {relic}{extra}: {desc}")
            else:
                relic_lines.append(f"- {relic}{extra}")
        relics_str = "\n".join(relic_lines) if relic_lines else "- None"
        
        # Format potions
        potions = r.get("potions", [])
        potion_lines = []
        for potion in potions:
            desc = self.kb.get_potion_info(potion)
            if desc:
                potion_lines.append(f"- {potion}: {desc}")
            else:
                potion_lines.append(f"- {potion}")
        potions_str = "\n".join(potion_lines) if potion_lines else "- None"
        
        # Format keys
        keys = r.get("keys", {})
        ruby = "✓" if keys.get("ruby") else "✗"
        emerald = "✓" if keys.get("emerald") else "✗"
        sapphire = "✓" if keys.get("sapphire") else "✗"
        
        # Build summary
        summary = f"""# Slay the Spire Run Summary

## Run Information
- **Character**: {r['character']}
- **Ascension**: {r['ascension']}
- **Act**: {r['act']}

## Current Status
- **HP**: {r['hp']}/{r['max_hp']}
- **Gold**: {r['gold']}

## Deck ({len(deck)} cards)
{deck_str}

## Relics
{relics_str}

## Potions
{potions_str}

## Keys
- Ruby: {ruby}
- Emerald: {emerald}
- Sapphire: {sapphire}
"""

        # Determine current boss display
        boss_val = r.get('boss')
        boss_display = None
        if boss_val:
            if isinstance(boss_val, str):
                kb_boss = self.kb.bosses.get(boss_val) or self.kb.bosses.get(str(boss_val))
                if kb_boss:
                    boss_display = boss_val
                else:
                    boss_display = boss_val
            else:
                boss_display = str(boss_val)

        summary += "\n## Boss & Elites\n"
        if boss_display:
            summary += f"- **Current Boss**: {boss_display}\n"
        else:
            summary += "- **Current Boss**: Unknown\n"

        elites = r.get('elites_defeated', []) or []
        # If empty, try a metric-based detection (preferred), otherwise fall back to
        # the raw 'elite_monster_list' field in the save data.
        if not elites:
            raw = r.get('raw_save_data', {})
            # Collect enemy names referenced by metric fields (e.g., metric_damage_taken)
            metric_hits = []
            try:
                def _collect_metric_enemy_names(o):
                    out = []
                    if isinstance(o, dict):
                        for kk, vv in o.items():
                            if isinstance(kk, str) and 'metric' in kk.lower():
                                # scan vv recursively for strings
                                def _scan(x):
                                    if isinstance(x, str):
                                        out.append(x)
                                    elif isinstance(x, list):
                                        for it in x:
                                            _scan(it)
                                    elif isinstance(x, dict):
                                        for vvv in x.values():
                                            _scan(vvv)
                                _scan(vv)
                            if isinstance(vv, (dict, list)):
                                out.extend(_collect_metric_enemy_names(vv))
                    elif isinstance(o, list):
                        for it in o:
                            out.extend(_collect_metric_enemy_names(it))
                    return out

                metric_hits = list(dict.fromkeys([str(x) for x in _collect_metric_enemy_names(raw) if isinstance(x, str)]))
            except Exception:
                metric_hits = []

            # Also pull explicit elite_monster_list if present
            eml = []
            try:
                if isinstance(raw, dict) and 'elite_monster_list' in raw and isinstance(raw.get('elite_monster_list'), list):
                    eml = [str(x) for x in raw.get('elite_monster_list') if x]
            except Exception:
                eml = []

            # Prefer metric hits that also appear in elite_monster_list (likely defeated)
            if metric_hits:
                if eml:
                    eml_lc = [e.lower() for e in eml]
                    elites = [m for m in metric_hits if m.lower() in eml_lc]
                else:
                    elites = metric_hits
            elif eml:
                # dedupe eml preserving order
                seen = set()
                uniq = []
                for x in eml:
                    k = x.lower()
                    if k in seen:
                        continue
                    seen.add(k)
                    uniq.append(x)
                elites = uniq
        if elites:
            summary += "- **Elites defeated this act:**\n"
            for e in elites:
                summary += f"- {e}\n"
        else:
            summary += "- **Elites defeated this act:** None\n"

        summary += "\n"
        
        # Add current choice section with descriptions and energy cost
        choice_type = self.current_choice.get("type")
        choice_options = self.current_choice.get("options", [])

        summary += "**Current choice:**\n"
        if choice_options:
            for option in choice_options:
                # Look up description just like in the deck section
                display = option
                desc = None
                card_type = None
                relic_desc = None
                cost_str = None

                if choice_type == "cards":
                    # Card: get info from KB
                    base_name = str(option).rstrip('+').strip()
                    base_for_lookup = base_name.replace('_b', '').replace('_B', '').replace('_', ' ').strip()
                    matches = self.kb.find_cards(base_for_lookup, limit=1)
                    if matches:
                        kb_card = matches[0][2]
                        canonical = kb_card.get('name')
                        has_plus = str(option).endswith('+')
                        display = canonical + ('+' if has_plus else '')
                        desc = kb_card.get('description') or kb_card.get('description_upgraded') or ''
                        t = kb_card.get('type')
                        if t:
                            card_type = t.capitalize()
                        # Get cost: use upgraded cost if card is upgraded
                        cost = None
                        if has_plus:
                            cost = kb_card.get('cost_upgraded')
                            if cost is None:
                                cost = kb_card.get('cost')
                        else:
                            cost = kb_card.get('cost')
                        # Handle special case: X cost
                        if cost == 'X' or cost == 'x':
                            cost_str = 'X'
                        elif cost is not None:
                            cost_str = str(cost)
                        else:
                            cost_str = None
                        if desc:
                            desc = desc.replace('[B]', 'energy')
                elif choice_type == "relics":
                    # Relic: get info from KB
                    relic_desc = self.kb.get_relic_info(option)

                # Build the line with all info
                line_parts = [f"- {display}"]
                if cost_str is not None:
                    line_parts.append(f" [{cost_str}]")
                if card_type:
                    line_parts.append(f" ({card_type})")
                if desc or relic_desc:
                    full_desc = desc if desc else relic_desc
                    line_parts.append(f": {full_desc}")
                summary += "".join(line_parts) + "\n"

            # If these are card options, include explicit skip marker
            if choice_type == "cards":
                summary += "- SKIP?\n"
        else:
            summary += "- None\n"
        
        summary += "\n---\n"
        
        # Write to file
        filename = "Run_Summary.md"
        filepath = Path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Updated run summary file: {filename}")
        if silent:
            return ""
        return "Summary file updated."
