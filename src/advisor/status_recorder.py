"""
Slay the Spire Run Status Recorder with Knowledge Base.

Tracks run state and provides access to game knowledge.
No strategic advice - just state management and knowledge lookups.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from src.advisor.run_manager import RunManager, format_deck_counts


class KnowledgeBase:
    """Local knowledge base loaded from split JSON files in data/knowledge/.
    
    Knowledge organization is documented in data/knowledge/KNOWLEDGE_MAP.md
    which serves as the master index for all game data files.
    """
    
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
                    # Extract items from the data field (skip _meta)
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
        # Load all cards from split files (cards/*.json)
        cards_list = self._load_split_json("cards/*.json")
        for card in cards_list:
            name = card.get("name", "").lower()
            if name:
                self.cards[name] = card
        logger.info(f"Loaded {len(self.cards)} cards from split files")
        
        # Load all relics from split files (relics/*.json)
        relics_list = self._load_split_json("relics/*.json")
        for relic in relics_list:
            name = relic.get("name", "").lower()
            if name:
                self.relics[name] = relic
        logger.info(f"Loaded {len(self.relics)} relics from split files")
        
        # Load potions (single file)
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
        
        # Load boss info from raw/bosses.json
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
            if ratio > 0.6:
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
            if ratio > 0.6:
                results.append((ratio, name, relic))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]
    
    def get_card_info(self, card_name: str) -> Optional[str]:
        """Get formatted card info string."""
        matches = self.find_cards(card_name, limit=1)
        if not matches:
            return None
        
        _, _, card = matches[0]
        parts = [f"{card['name']} ({card.get('rarity', 'Unknown')} {card.get('type', 'Card')})"]
        parts.append(f"Cost: {card.get('cost', '?')} | {card.get('color', 'Colorless')}")
        if card.get("description"):
            parts.append(card["description"])
        if card.get("upgrade"):
            parts.append(f"Upgraded: {card['upgrade']}")
        return "\n".join(parts)
    
    def get_relic_info(self, relic_name: str) -> Optional[str]:
        """Get formatted relic info string."""
        matches = self.find_relics(relic_name, limit=1)
        if not matches:
            return None
        
        _, _, relic = matches[0]
        parts = [f"{relic['name']} ({relic.get('rarity', 'Unknown')} Relic)"]
        if relic.get("description"):
            parts.append(relic["description"])
        if relic.get("flavor"):
            parts.append(f"Flavor: {relic['flavor']}")
        return "\n".join(parts)


class StatusRecorder:
    """Slay the Spire run status recorder with persistent storage."""
    
    # Character data
    CHARACTERS = {
        "ironclad": {
            "name": "Ironclad",
            "hp": 80,
            "starter_relic": "Burning Blood",
            "color": "Red",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike", 
                           "Defend", "Defend", "Defend", "Defend", "Bash"]
        },
        "silent": {
            "name": "Silent",
            "hp": 70,
            "starter_relic": "Ring of the Snake",
            "color": "Green",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend", "Defend",
                           "Survivor", "Neutralize"]
        },
        "defect": {
            "name": "Defect",
            "hp": 75,
            "starter_relic": "Cracked Core",
            "color": "Blue",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend",
                           "Zap", "Dualcast"]
        },
        "watcher": {
            "name": "Watcher",
            "hp": 72,
            "starter_relic": "Pure Water",
            "color": "Purple",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend",
                           "Eruption", "Vigilance"]
        }
    }
    
    # Color mapping for card validation
    COLOR_MAP = {
        "Ironclad": "Red",
        "Silent": "Green",
        "Defect": "Blue",
        "Watcher": "Purple"
    }
    
    def __init__(self):
        load_dotenv()
        
        # Load knowledge base
        self.kb = KnowledgeBase()
        
        # Initialize run manager (persistent storage)
        self.run_manager = RunManager()
        
        # Try to resume latest active run
        self.resumed_run = self.run_manager.resume_latest_run()
        if self.resumed_run:
            logger.info(f"Resumed run: {self.resumed_run['character']} A{self.resumed_run['ascension']}")
            # Update summary file with resumed run state
            self.create_summary_file(silent=True)
        
        logger.info(f"Status recorder initialized")
        logger.info(f"Knowledge base: {len(self.kb.cards)} cards, {len(self.kb.relics)} relics")
    
    def start_run(self, character: str, ascension: int = 0) -> str:
        """Start a new run (ends any active run)."""
        char_key = character.lower()
        if char_key not in self.CHARACTERS:
            return f"Unknown character: {character}. Choose: Ironclad, Silent, Defect, Watcher"
        
        char_data = self.CHARACTERS[char_key]
        
        # End previous active run if exists
        previous_run = self.run_manager.get_active_run()
        if previous_run:
            previous_char = previous_run['character']
            previous_asc = previous_run['ascension']
            self.run_manager.end_run(victory=False, cause="Abandoned - started new run")
            logger.info(f"Ended previous run: {previous_char} A{previous_asc}")
        
        # Create new run
        run = self.run_manager.create_run(
            character=char_data["name"],
            ascension=ascension,
            starter_deck=char_data["starter_deck"],
            starter_relic=char_data["starter_relic"],
            max_hp=char_data["hp"],
            color=char_data["color"]
        )
        
        # Create initial summary file
        self.create_summary_file(silent=True)
        
        deck_str = format_deck_counts(char_data["starter_deck"])
        return f"New run started! {char_data['name']} Ascension {ascension}. HP: {char_data['hp']}. Deck: {deck_str}. Good luck!"
    
    def add_card(self, card_name: str) -> str:
        """Add a card to the current run with validation."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run. Start one first!"
        
        # Find card in database
        matches = self.kb.find_cards(card_name, limit=5)
        
        if not matches:
            return f"Card '{card_name}' not found in database. Could you spell it differently?"
        
        # Get best match
        score, _, card_data = matches[0]
        actual_name = card_data["name"]
        card_color = card_data.get("color", "Colorless").upper()  # Normalize to uppercase
        
        # Check if card matches current character or is colorless
        char = run["character"]
        char_color = self.COLOR_MAP.get(char, "Red").upper()  # Normalize to uppercase
        
        # Remove + suffix for base card matching
        base_name = actual_name.rstrip('+')
        
        if card_color != "COLORLESS" and card_color != char_color:
            # Wrong class card - suggest alternatives
            valid_matches = [
                (s, n, c) for s, n, c in matches 
                if c.get("color", "Colorless").upper() in [char_color, "COLORLESS"]
            ]
            if valid_matches:
                suggestions = ", ".join([c["name"] for _, _, c in valid_matches[:3]])
                return f"'{actual_name}' is a {card_color} card, but you're playing {char}. Did you mean: {suggestions}?"
            return f"'{actual_name}' is a {card_color} card, not available for {char}."
        
        # Low confidence match - ask for confirmation
        if score < 0.7:
            suggestions = ", ".join([c["name"] for _, _, c in matches[:3]])
            return f"Did you mean one of these? {suggestions}"
        
        # Valid card - add it
        run = self.run_manager.add_card(base_name if not actual_name.endswith('+') else actual_name)
        if run:
            deck = self.run_manager.get_full_deck(run)
            
            # Update summary file
            self.create_summary_file(silent=True)
            
            return f"Added {actual_name}"
        return "Failed to add card."
    
    def remove_card(self, card_name: str) -> str:
        """Remove a card from the current run."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        matches = self.kb.find_cards(card_name)
        actual_name = matches[0][2]["name"] if matches else card_name.title()
        
        run = self.run_manager.remove_card(actual_name)
        if run:
            deck = self.run_manager.get_full_deck(run)
            self.create_summary_file(silent=True)
            return f"Removed {actual_name}"
        return "Failed to remove card."
    
    def upgrade_card(self, card_name: str) -> str:
        """Upgrade a card in the current run."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        # Fuzzy match card name
        matches = self.kb.find_cards(card_name)
        if not matches:
            return f"Card '{card_name}' not found."
        
        actual_name = matches[0][2]["name"]
        base_name = actual_name.rstrip('+')
        
        # Check if card is in deck
        deck = self.run_manager.get_full_deck(run)
        upgraded_cards = run.get("upgraded_cards", [])
        
        # Check if we have this card (base or upgraded version)
        has_card = base_name in deck or f"{base_name}+" in deck
        
        if not has_card:
            return f"You don't have {base_name} in your deck."
        
        # Check if already upgraded
        if base_name in upgraded_cards:
            return f"{base_name} is already upgraded."
        
        # Upgrade it
        run = self.run_manager.upgrade_card(base_name)
        if run:
            self.create_summary_file(silent=True)
            return f"Upgraded {base_name}"
        return "Failed to upgrade card."
    
    def add_relic(self, relic_name: str) -> str:
        """Add a relic to the current run."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        # Fuzzy match relic name
        matches = self.kb.find_relics(relic_name, limit=3)
        if not matches:
            return f"Relic '{relic_name}' not found."
        
        score, _, relic_data = matches[0]
        actual_name = relic_data["name"]
        
        # Auto-add if score is decent (>0.5) or if it's the only reasonable match
        if score < 0.5:
            suggestions = ", ".join([r["name"] for _, _, r in matches[:3]])
            return f"Did you mean one of these? {suggestions}"
        
        # Score >= 0.5 - good enough match, just add it
        run = self.run_manager.add_relic(actual_name)
        if run:
            self.create_summary_file(silent=True)
            return f"Added {actual_name}"
        return "Failed to add relic."
    
    def remove_relic(self, relic_name: str) -> str:
        """Remove a relic from the current run."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        # Fuzzy match relic name against currently owned relics
        owned_relics = run.get("relics", [])
        if not owned_relics:
            return "You don't have any relics to remove."
        
        # Try exact match first (case-insensitive)
        for relic in owned_relics:
            if relic.lower() == relic_name.lower():
                run = self.run_manager.remove_relic(relic)
                if run:
                    self.create_summary_file(silent=True)
                    return f"Removed {relic}"
                return "Failed to remove relic."
        
        # If no exact match, try fuzzy matching against owned relics
        from difflib import get_close_matches
        matches = get_close_matches(relic_name.lower(), 
                                    [r.lower() for r in owned_relics], 
                                    n=1, cutoff=0.6)
        if matches:
            # Find the actual relic name (with proper casing)
            for relic in owned_relics:
                if relic.lower() == matches[0]:
                    run = self.run_manager.remove_relic(relic)
                    if run:
                        self.create_summary_file(silent=True)
                        return f"Removed {relic}"
                    return "Failed to remove relic."
        
        # No match found
        return f"You don't have '{relic_name}'. You have: {', '.join(owned_relics)}"
    
    def set_boss(self, boss_name: str) -> str:
        """Set the current act boss."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        run = self.run_manager.set_boss(boss_name)
        if run:
            self.create_summary_file(silent=True)
            return f"Boss set: {boss_name}"
        return "Failed to set boss."
    
    def update_act(self, act: int) -> str:
        """Update the current act."""
        run = self.run_manager.update_act(act)
        if run:
            self.create_summary_file(silent=True)
            return f"Now in Act {act}."
        return "No active run."
    
    def update_hp(self, current: int = None, max_hp: int = None) -> str:
        """Update HP. Can update current, max, or both independently."""
        updates = {}
        if current is not None:
            updates["hp"] = current
        if max_hp is not None:
            updates["max_hp"] = max_hp
        
        if not updates:
            return "No HP values provided."
        
        run = self.run_manager.update_run(**updates)
        if run:
            self.create_summary_file(silent=True)
            return f"HP: {run['hp']}/{run['max_hp']}"
        return "No active run."
    
    def update_gold(self, gold: int) -> str:
        """Update gold."""
        run = self.run_manager.update_run(gold=gold)
        if run:
            self.create_summary_file(silent=True)
            return f"Gold: {run['gold']}"
        return "No active run."
    
    def get_run_status(self) -> str:
        """Get current run status."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run. Say 'start a new run' to begin!"
        
        deck = self.run_manager.get_full_deck(run)
        
        status = (f"Playing {run['character']} Ascension {run['ascension']}. "
                f"Act {run['act']}. "
                f"HP {run['hp']}/{run['max_hp']}, {run['gold']} gold. "
                f"Deck has {len(deck)} cards, {len(run['relics'])} relics.")
        
        return status
    
    # Decision Point Tracking (for external advisor)
    
    def set_card_choice(self, options: list) -> str:
        """Set current card choice options."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        self.run_manager.set_card_choice(options)
        self.create_summary_file(silent=True)
        return "Card choice recorded"
    
    def set_relic_choice(self, options: list) -> str:
        """Set current relic choice options."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        self.run_manager.set_relic_choice(options)
        self.create_summary_file(silent=True)
        return "Relic choice recorded"
    
    def set_shop_choices(self, cards: list = None, relics: list = None, potions: list = None) -> str:
        """Set current shop options."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        self.run_manager.set_shop_choices(cards, relics, potions)
        self.create_summary_file(silent=True)
        
        parts = []
        if cards:
            parts.append(f"{len(cards)} cards")
        if relics:
            parts.append(f"{len(relics)} relics")
        if potions:
            parts.append(f"{len(potions)} potions")
        
        return f"Shop recorded: {', '.join(parts)}"
    
    def end_run(self, victory: bool = False, cause: str = None) -> str:
        """End the active run."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run to end."
        
        char = run['character']
        asc = run['ascension']
        
        self.run_manager.end_run(victory=victory, cause=cause)
        
        result = "Victory!" if victory else f"Defeated: {cause or 'unknown'}"
        return f"Run ended for {char} A{asc}. {result}"
    
    def create_summary_file(self, silent: bool = False) -> str:
        """Export run status to a markdown file."""
        run = self.run_manager.get_active_run()
        if not run:
            return "" if silent else "No active run to summarize."
        
        deck = self.run_manager.get_full_deck(run)
        deck_str = format_deck_counts(deck)
        
        # Build simplified markdown summary
        summary = f"""# Slay the Spire Run Summary

## Run Information
- **Character**: {run['character']}
- **Ascension**: {run['ascension']}
- **Act**: {run['act']}

## Current Status
- **HP**: {run['hp']}/{run['max_hp']}
- **Gold**: {run['gold']}

## Deck ({len(deck)} cards)
{deck_str}

## Relics
{chr(10).join(f'- {relic}' for relic in run['relics']) if run['relics'] else '- None'}

## Potions
{chr(10).join(f'- {potion}' for potion in run['potions']) if run['potions'] else '- None'}

## Keys
- Ruby: {'✓' if run['keys']['ruby'] else '✗'}
- Emerald: {'✓' if run['keys']['emerald'] else '✗'}
- Sapphire: {'✓' if run['keys']['sapphire'] else '✗'}
"""
        
        # Add boss info if set
        boss_name = run.get('current_boss')
        if boss_name:
            summary += f"\n## Current Boss\n{boss_name}\n"
        
        # Add current decision point
        choice = run.get('current_choice', {})
        choice_type = choice.get('type')
        choice_options = choice.get('options', [])
        
        if choice_type == 'cards' and choice_options:
            summary += f"\n## Current Decision\n**Choosing between {len(choice_options)} cards:**\n"
            for option in choice_options:
                summary += f"- {option}\n"
        elif choice_type == 'relics' and choice_options:
            summary += f"\n## Current Decision\n**Choosing between {len(choice_options)} relics:**\n"
            for option in choice_options:
                summary += f"- {option}\n"
        elif choice_type == 'shop' and isinstance(choice_options, dict):
            summary += f"\n## Current Decision\n**At shop:**\n"
            if choice_options.get('cards'):
                summary += f"\n**Cards available:**\n"
                for card in choice_options['cards']:
                    summary += f"- {card}\n"
            if choice_options.get('relics'):
                summary += f"\n**Relics available:**\n"
                for relic in choice_options['relics']:
                    summary += f"- {relic}\n"
            if choice_options.get('potions'):
                summary += f"\n**Potions available:**\n"
                for potion in choice_options['potions']:
                    summary += f"- {potion}\n"
        else:
            summary += f"\n## Current Decision\nNo decision pending\n"
        
        # Add footer
        summary += f"\n---\n\n\n"
        
        # Write to file
        filename = "Run_Summary.md"
        filepath = Path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Updated run summary file: {filename}")
        if silent:
            return ""
        return f"Summary file updated."
    
    def sync_from_summary(self, filename: str = "Run_Summary.md") -> str:
        """Sync run state from manually edited Run_Summary.md file."""
        filepath = Path(filename)
        
        if not filepath.exists():
            return "Summary file not found."
        
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run to sync."
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the markdown content
            import re
            
            # Extract character and ascension
            char_match = re.search(r'\*\*Character\*\*:\s*(\w+)', content)
            asc_match = re.search(r'\*\*Ascension\*\*:\s*(\d+)', content)
            act_match = re.search(r'\*\*Act\*\*:\s*(\d+)', content)
            hp_match = re.search(r'\*\*HP\*\*:\s*(\d+)/(\d+)', content)
            gold_match = re.search(r'\*\*Gold\*\*:\s*(\d+)', content)
            
            # Extract deck
            deck_match = re.search(r'## Deck \((\d+) cards\)\n(.+?)\n\n', content, re.DOTALL)
            
            # Extract relics
            relics_match = re.search(r'## Relics\n(.+?)\n\n', content, re.DOTALL)
            
            changes_made = []
            
            # Update character/ascension
            if char_match and run["character"].lower() != char_match.group(1).lower():
                run["character"] = char_match.group(1)
                changes_made.append(f"character → {char_match.group(1)}")
            
            if asc_match and run["ascension"] != int(asc_match.group(1)):
                run["ascension"] = int(asc_match.group(1))
                changes_made.append(f"ascension → {asc_match.group(1)}")
            
            # Update act
            if act_match and run["act"] != int(act_match.group(1)):
                run["act"] = int(act_match.group(1))
                changes_made.append(f"act → {act_match.group(1)}")
            
            # Update HP
            if hp_match:
                new_hp = int(hp_match.group(1))
                new_max_hp = int(hp_match.group(2))
                if run["hp"] != new_hp or run["max_hp"] != new_max_hp:
                    run["hp"] = new_hp
                    run["max_hp"] = new_max_hp
                    changes_made.append(f"HP → {new_hp}/{new_max_hp}")
            
            # Update gold
            if gold_match and run["gold"] != int(gold_match.group(1)):
                run["gold"] = int(gold_match.group(1))
                changes_made.append(f"gold → {gold_match.group(1)}")
            
            # Parse and sync deck
            if deck_match:
                deck_text = deck_match.group(2).strip()
                file_deck = []
                upgraded_cards = []
                
                # Parse deck entries like "5x Strike", "Bash+", "Calculated Gamble+"
                for item in re.split(r',\s*', deck_text):
                    item = item.strip()
                    # Handle "5x Strike" format
                    count_match = re.match(r'(\d+)x\s+(.+)', item)
                    if count_match:
                        count = int(count_match.group(1))
                        card_name = count_match.group(2)
                        for _ in range(count):
                            file_deck.append(card_name)
                    else:
                        file_deck.append(item)
                    
                    # Check for upgraded cards (ending with +)
                    if item.endswith('+'):
                        base_name = item.rstrip('+')
                        if base_name not in upgraded_cards:
                            upgraded_cards.append(base_name)
                
                # Reconstruct deck state from file
                # File deck has all cards (starter + added - removed, with upgrades)
                # We need to figure out added_cards and removed_cards
                
                current_deck = self.run_manager.get_full_deck(run)
                
                # For simplicity, if deck changed significantly, rebuild from scratch
                # Remove + suffixes for comparison
                current_base = [c.rstrip('+') for c in current_deck]
                file_base = [c.rstrip('+') for c in file_deck]
                
                if sorted(current_base) != sorted(file_base):
                    # Deck composition changed - rebuild added/removed lists
                    starter_base = [c.rstrip('+') for c in run["starter_deck"]]
                    
                    added = []
                    removed = []
                    
                    for card in file_base:
                        if card not in starter_base:
                            added.append(card)
                    
                    for card in starter_base:
                        if card not in file_base:
                            removed.append(card)
                    
                    run["added_cards"] = added
                    run["removed_cards"] = removed
                    changes_made.append("deck composition updated")
                
                # Sync upgraded cards
                if sorted(run.get("upgraded_cards", [])) != sorted(upgraded_cards):
                    run["upgraded_cards"] = upgraded_cards
                    changes_made.append(f"upgrades → {len(upgraded_cards)} cards")
            
            # Parse and sync relics
            if relics_match:
                relics_text = relics_match.group(1).strip()
                file_relics = []
                for line in relics_text.split('\n'):
                    line = line.strip()
                    if line.startswith('- '):
                        relic_name = line[2:].strip()
                        if relic_name and relic_name.lower() != 'none':
                            file_relics.append(relic_name)
                
                if sorted(run.get("relics", [])) != sorted(file_relics):
                    run["relics"] = file_relics
                    changes_made.append(f"relics → {len(file_relics)}")
            
            # Save changes
            if changes_made:
                run["last_updated"] = datetime.now().isoformat()
                self.run_manager._save()
                logger.info(f"Synced from file: {', '.join(changes_made)}")
                return f"Synced from file: {', '.join(changes_made)}"
            else:
                return "File matches current state, no changes needed."
        
        except Exception as e:
            logger.error(f"Failed to sync from file: {e}")
            return f"Failed to sync from file: {str(e)}"
