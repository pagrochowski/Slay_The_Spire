"""
Persistent run storage for Slay the Spire status recorder.

Stores run data in JSON file so runs persist across sessions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


class RunManager:
    """Manages persistent run storage."""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("data/runs.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.runs: list = []
        self.active_run_id: Optional[str] = None
        self._load()
    
    def _load(self):
        """Load runs from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.runs = data.get("runs", [])
                    self.active_run_id = data.get("active_run_id")
                logger.info(f"Loaded {len(self.runs)} runs from storage")
            except Exception as e:
                logger.error(f"Failed to load runs: {e}")
                self.runs = []
                self.active_run_id = None
        else:
            logger.info("No existing runs file, starting fresh")
    
    def _save(self):
        """Save runs to storage file."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "runs": self.runs,
                    "active_run_id": self.active_run_id
                }, f, indent=2, default=str)
            logger.debug("Runs saved to storage")
        except Exception as e:
            logger.error(f"Failed to save runs: {e}")
    
    def get_active_run(self) -> Optional[dict]:
        """Get the currently active run."""
        if not self.active_run_id:
            return None
        
        for run in self.runs:
            if run.get("id") == self.active_run_id:
                return run
        return None
    
    def get_latest_run(self) -> Optional[dict]:
        """Get the most recent run (active or not)."""
        if not self.runs:
            return None
        
        # Sort by last_updated descending
        sorted_runs = sorted(
            self.runs, 
            key=lambda r: r.get("last_updated", ""), 
            reverse=True
        )
        return sorted_runs[0] if sorted_runs else None
    
    def resume_latest_run(self) -> Optional[dict]:
        """Resume the latest non-ended run, or return None."""
        for run in sorted(self.runs, key=lambda r: r.get("last_updated", ""), reverse=True):
            if run.get("status") == "active":
                self.active_run_id = run["id"]
                self._save()
                logger.info(f"Resumed run: {run['character']} A{run['ascension']} (Act {run.get('act', 1)})")
                return run
        return None
    
    def create_run(self, character: str, ascension: int, starter_deck: list, 
                   starter_relic: str, max_hp: int, color: str) -> dict:
        """Create a new run with unique ID."""
        # Generate unique ID with milliseconds to avoid collisions
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]  # Include microseconds, truncate to reasonable length
        
        # Ensure ID is truly unique (in case of extremely fast consecutive calls)
        existing_ids = {r["id"] for r in self.runs}
        counter = 0
        original_id = run_id
        while run_id in existing_ids:
            counter += 1
            run_id = f"{original_id}_{counter}"
        
        run = {
            "id": run_id,
            "character": character,
            "color": color,
            "ascension": ascension,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            
            # Progress
            "act": 1,
            
            # Resources
            "hp": max_hp,
            "max_hp": max_hp,
            "gold": 99,
            
            # Deck & Items
            "starter_deck": starter_deck,
            "added_cards": [],
            "removed_cards": [],
            "upgraded_cards": [],
            "relics": [starter_relic],
            "potions": [],
            
            # Keys for Act 4
            "keys": {
                "ruby": False,
                "emerald": False,
                "sapphire": False
            },
            
            # Current boss (set when player sees the map)
            "current_boss": None,
            
            # Current decision point (for external advisor context)
            "current_choice": {
                "type": None,  # "cards", "relics", "shop", None
                "options": []   # List of available options
            }
        }
        
        self.runs.append(run)
        self.active_run_id = run_id
        self._save()
        
        logger.info(f"Created new run: {character} A{ascension}, ID: {run_id}")
        return run
    
    def update_run(self, **kwargs) -> Optional[dict]:
        """Update the active run with new values."""
        run = self.get_active_run()
        if not run:
            return None
        
        for key, value in kwargs.items():
            if key in run and value is not None:
                run[key] = value
        
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def add_card(self, card_name: str) -> Optional[dict]:
        """Add a card to the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["added_cards"].append(card_name)
        run["last_updated"] = datetime.now().isoformat()
        
        # Clear current choice after making decision
        self.clear_choice()
        
        self._save()
        return run
    
    def remove_card(self, card_name: str) -> Optional[dict]:
        """Remove a card from the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["removed_cards"].append(card_name)
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def upgrade_card(self, card_name: str) -> Optional[dict]:
        """Upgrade a card in the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        # Remove + suffix if present (user might say "upgrade strike+")
        base_name = card_name.rstrip('+')
        
        # Only add if not already upgraded
        if base_name not in run.get("upgraded_cards", []):
            if "upgraded_cards" not in run:
                run["upgraded_cards"] = []
            run["upgraded_cards"].append(base_name)
        
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def add_relic(self, relic_name: str) -> Optional[dict]:
        """Add a relic to the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["relics"].append(relic_name)
        run["last_updated"] = datetime.now().isoformat()
        
        # Clear current choice after making decision
        self.clear_choice()
        
        self._save()
        return run
    
    def remove_relic(self, relic_name: str) -> Optional[dict]:
        """Remove a relic from the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        # Find the relic (case-insensitive)
        relics = run["relics"]
        found = False
        for i, r in enumerate(relics):
            if r.lower() == relic_name.lower():
                relics.pop(i)
                found = True
                break
        
        if not found:
            return None
        
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def add_potion(self, potion_name: str) -> Optional[dict]:
        """Add a potion to the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        if len(run["potions"]) >= 3:
            return None  # Potion slots full
        
        run["potions"].append(potion_name)
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def use_potion(self, potion_name: str) -> Optional[dict]:
        """Use/remove a potion from the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        if potion_name in run["potions"]:
            run["potions"].remove(potion_name)
            run["last_updated"] = datetime.now().isoformat()
            self._save()
        return run
    
    def set_boss(self, boss_name: str) -> Optional[dict]:
        """Set the current act boss."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["current_boss"] = boss_name
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info(f"Boss set: {boss_name}")
        return run
    
    def update_act(self, act: int) -> Optional[dict]:
        """Update the current act."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["act"] = act
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    # Current Choice Tracking (for external advisor context)
    
    def set_card_choice(self, options: list) -> Optional[dict]:
        """Set current card choice options."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["current_choice"] = {
            "type": "cards",
            "options": options
        }
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info(f"Card choice set: {', '.join(options)}")
        return run
    
    def set_relic_choice(self, options: list) -> Optional[dict]:
        """Set current relic choice options."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["current_choice"] = {
            "type": "relics",
            "options": options
        }
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info(f"Relic choice set: {', '.join(options)}")
        return run
    
    def set_shop_choices(self, cards: list = None, relics: list = None, potions: list = None) -> Optional[dict]:
        """Set current shop options."""
        run = self.get_active_run()
        if not run:
            return None
        
        shop_options = {}
        if cards:
            shop_options["cards"] = cards
        if relics:
            shop_options["relics"] = relics
        if potions:
            shop_options["potions"] = potions
        
        run["current_choice"] = {
            "type": "shop",
            "options": shop_options
        }
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info(f"Shop choices set")
        return run
    
    def clear_choice(self) -> Optional[dict]:
        """Clear the current decision point."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["current_choice"] = {
            "type": None,
            "options": []
        }
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def end_run(self, victory: bool = False, cause: str = None) -> Optional[dict]:
        """End the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["status"] = "victory" if victory else "defeat"
        run["ended_at"] = datetime.now().isoformat()
        run["last_updated"] = datetime.now().isoformat()
        
        if cause:
            run["death_cause"] = cause
        
        self.active_run_id = None
        self._save()
        
        logger.info(f"Run ended: {run['character']} A{run['ascension']} - {'Victory' if victory else 'Defeat'}")
        return run
    
    def get_full_deck(self, run: dict = None) -> list:
        """Get the full current deck (starter + added - removed), with upgrades marked."""
        run = run or self.get_active_run()
        if not run:
            return []
        
        deck = run.get("starter_deck", []).copy()
        deck.extend(run.get("added_cards", []))
        
        # Remove cards (handle duplicates properly)
        for card in run.get("removed_cards", []):
            if card in deck:
                deck.remove(card)
        
        # Mark upgraded cards with "+"
        upgraded_cards = run.get("upgraded_cards", [])
        if upgraded_cards:
            deck_with_upgrades = []
            for card in deck:
                base_name = card.rstrip('+')
                if base_name in upgraded_cards:
                    deck_with_upgrades.append(f"{base_name}+")
                else:
                    deck_with_upgrades.append(card)
            return deck_with_upgrades
        
        return deck


def format_deck_counts(cards: list) -> str:
    """Format a deck list with counts (e.g., '5x Strike, 4x Defend, 1x Bash')."""
    from collections import Counter
    counts = Counter(cards)
    formatted = []
    for card, count in sorted(counts.items()):
        if count > 1:
            formatted.append(f"{count}x {card}")
        else:
            formatted.append(card)
    return ", ".join(formatted)
