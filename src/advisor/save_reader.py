"""
Slay the Spire Save File Reader.

Reads the game's autosave files to get current run state.
Uses spireslayer library to parse save files.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

try:
    from spireslayer.editor import Editor
except ImportError:
    logger.error("spireslayer not installed. Run: pip install spireslayer")
    Editor = None


class SaveReader:
    """Reads Slay the Spire save files to extract run state."""
    
    def __init__(self, save_path: str = None):
        """Initialize save reader.
        
        Args:
            save_path: Path to saves directory. If None, uses spireslayer's default Steam detection.
        """
        self.save_path = Path(save_path) if save_path else None
        
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
        if Editor is None:
            logger.error("spireslayer not available")
            return None
        
        try:
            # Find latest autosave
            autosave_file = self.find_latest_autosave()
            if not autosave_file:
                return None
            
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
            
            # Extract keys
            keys = {
                "ruby": save_data.get("ruby_key", False),
                "emerald": save_data.get("emerald_key", False),
                "sapphire": save_data.get("sapphire_key", False)
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
                "raw_save_data": save_data  # Keep raw data for debugging
            }
            
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
