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

from src.advisor.save_reader import SaveReader


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
    
    def refresh_from_save(self) -> str:
        """Refresh run state from game save file."""
        run_state = self.save_reader.get_current_run()
        
        if not run_state:
            self.current_run = None
            logger.warning("No active game found in save file")
            return "Current game not found"
        
        self.current_run = run_state
        logger.info(f"Refreshed from save: {run_state['character']} A{run_state['ascension']}, Act {run_state['act']}")
        
        # Update summary file
        self.create_summary_file(silent=True)
        
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
        if not self.current_run:
            return "No active game found"
        
        self.current_choice = {
            "type": "cards",
            "options": options
        }
        self.create_summary_file(silent=True)
        return "Card choice recorded"
    
    def set_relic_choice(self, options: list) -> str:
        """Record current relic choice options."""
        if not self.current_run:
            return "No active game found"
        
        self.current_choice = {
            "type": "relics",
            "options": options
        }
        self.create_summary_file(silent=True)
        return "Relic choice recorded"
    
    def clear_choice(self) -> str:
        """Clear current decision point."""
        self.current_choice = {
            "type": None,
            "options": []
        }
        self.create_summary_file(silent=True)
        return "Choice cleared"
    
    def create_summary_file(self, silent: bool = False) -> str:
        """Generate Run_Summary.md from current game state."""
        if not self.current_run:
            if not silent:
                return "No active game to summarize"
            return ""
        
        r = self.current_run
        
        # Format deck with counts
        from collections import Counter
        deck = r.get("deck", [])
        deck_counts = Counter(deck)
        formatted_deck = []
        for card, count in sorted(deck_counts.items()):
            if count > 1:
                formatted_deck.append(f"{count}x {card}")
            else:
                formatted_deck.append(card)
        deck_str = ", ".join(formatted_deck)
        
        # Format relics
        relics = r.get("relics", [])
        relics_str = "\n".join([f"- {relic}" for relic in relics]) if relics else "- None"
        
        # Format potions
        potions = r.get("potions", [])
        potions_str = "\n".join([f"- {potion}" for potion in potions]) if potions else "- None"
        
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

## Current Decision
"""
        
        # Add current choice if any
        choice_type = self.current_choice.get("type")
        choice_options = self.current_choice.get("options", [])
        
        if choice_type == "cards" and choice_options:
            summary += f"**Choosing between {len(choice_options)} cards:**\n"
            for option in choice_options:
                summary += f"- {option}\n"
        elif choice_type == "relics" and choice_options:
            summary += f"**Choosing between {len(choice_options)} relics:**\n"
            for option in choice_options:
                summary += f"- {option}\n"
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
