"""
Choice Persistence for Slay the Spire.

Stores voice-recorded choices with floor tracking to prevent wiping on summary regeneration.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from src.utils.logger import setup_logger

log = setup_logger("choice")


class ChoicePersistence:
    """Manages persistent storage of voice-recorded choices."""
    
    def __init__(self, choice_file: Path = None):
        """
        Initialize choice persistence.
        
        Args:
            choice_file: Path to JSON file storing choices (default: current_choice.json)
        """
        self.choice_file = choice_file or Path("current_choice.json")
        log.info(f"ChoicePersistence initialized: {self.choice_file}")
    
    def load_choice(self) -> Optional[Dict[str, Any]]:
        """
        Load the current choice from file.
        
        Returns:
            Dictionary with 'floor', 'act', 'cards', 'relics', or None if no choice exists
        """
        if not self.choice_file.exists():
            log.debug("No choice file exists")
            return None
        
        try:
            with open(self.choice_file, 'r', encoding='utf-8') as f:
                choice = json.load(f)
            
            log.info(f"Loaded choice: Floor {choice.get('floor')}, Act {choice.get('act')}")
            return choice
        
        except Exception as e:
            log.error(f"Failed to load choice: {e}")
            return None
    
    def save_choice(
        self,
        floor: int,
        act: int,
        cards: List[str] = None,
        relics: List[str] = None
    ) -> bool:
        """
        Save a choice to file.
        
        Args:
            floor: Current floor number
            act: Current act number
            cards: List of card names
            relics: List of relic names
            
        Returns:
            True if saved successfully, False otherwise
        """
        choice_data = {
            "floor": floor,
            "act": act,
            "cards": cards or [],
            "relics": relics or []
        }
        
        try:
            with open(self.choice_file, 'w', encoding='utf-8') as f:
                json.dump(choice_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"Saved choice: Floor {floor}, Act {act}, Cards: {len(cards or [])}, Relics: {len(relics or [])}")
            return True
        
        except Exception as e:
            log.error(f"Failed to save choice: {e}")
            return False
    
    def clear_choice(self) -> bool:
        """
        Clear the current choice (delete file).
        
        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.choice_file.exists():
            log.debug("No choice file to clear")
            return True
        
        try:
            self.choice_file.unlink()
            log.info("Cleared choice file")
            return True
        
        except Exception as e:
            log.error(f"Failed to clear choice: {e}")
            return False
    
    def should_clear_choice(self, current_floor: int, current_act: int) -> bool:
        """
        Check if the choice should be cleared due to floor change.
        
        Args:
            current_floor: Current floor number from save
            current_act: Current act number from save
            
        Returns:
            True if choice should be cleared, False otherwise
        """
        choice = self.load_choice()
        
        if not choice:
            return False  # No choice to clear
        
        saved_floor = choice.get('floor', 0)
        saved_act = choice.get('act', 0)
        
        # Clear if floor or act changed
        if saved_floor != current_floor or saved_act != current_act:
            log.info(f"Floor/Act changed: ({saved_act}/{saved_floor}) -> ({current_act}/{current_floor}). Clearing choice.")
            return True
        
        return False
    
    def format_choice_text(self) -> Optional[str]:
        """
        Format the current choice as text for appending to summary.
        
        Returns:
            Formatted text, or None if no choice exists
        """
        choice = self.load_choice()
        
        if not choice:
            return None
        
        cards = choice.get('cards', [])
        relics = choice.get('relics', [])
        
        # If no items, return None
        if not cards and not relics:
            return None
        
        lines = []
        
        if relics:
            relics_text = ", ".join(relics)
            lines.append(f"Relics to choose from: {relics_text}")
        
        if cards:
            cards_text = ", ".join(cards)
            lines.append(f"Cards to choose from: {cards_text}")
        
        return "\n".join(lines)
