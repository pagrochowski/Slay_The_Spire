"""
Persistent run storage for Slay the Spire advisor.

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
                logger.info(f"Resumed run: {run['character']} A{run['ascension']} (Floor {run.get('floor', 1)})")
                return run
        return None
    
    def create_run(self, character: str, ascension: int, starter_deck: list, 
                   starter_relic: str, max_hp: int, color: str) -> dict:
        """Create a new run."""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        run = {
            "id": run_id,
            "character": character,
            "color": color,
            "ascension": ascension,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            
            # Progress
            "floor": 1,
            "act": 1,
            
            # Resources
            "hp": max_hp,
            "max_hp": max_hp,
            "gold": 99,
            
            # Deck & Items
            "starter_deck": starter_deck,
            "added_cards": [],
            "removed_cards": [],
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
            
            # Detected archetype tendencies
            "archetype_hints": [],
            
            # Strategy notes (evolve during run)
            "strategy": [],
            
            # Events log (for context)
            "events": [
                {
                    "floor": 0,
                    "type": "run_start",
                    "timestamp": datetime.now().isoformat(),
                    "details": f"Started {character} A{ascension}"
                }
            ]
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
        run["events"].append({
            "type": "card_added",
            "timestamp": datetime.now().isoformat(),
            "details": card_name
        })
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def remove_card(self, card_name: str) -> Optional[dict]:
        """Remove a card from the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["removed_cards"].append(card_name)
        run["events"].append({
            "type": "card_removed",
            "timestamp": datetime.now().isoformat(),
            "details": card_name
        })
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def add_relic(self, relic_name: str) -> Optional[dict]:
        """Add a relic to the active run."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["relics"].append(relic_name)
        run["events"].append({
            "type": "relic_added",
            "timestamp": datetime.now().isoformat(),
            "details": relic_name
        })
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
    
    def advance_floor(self, new_floor: int = None, new_act: int = None) -> Optional[dict]:
        """Advance to next floor."""
        run = self.get_active_run()
        if not run:
            return None
        
        if new_floor:
            run["floor"] = new_floor
        else:
            run["floor"] += 1
        
        # Update act based on floor or explicit act parameter
        if new_act:
            run["act"] = new_act
        else:
            # Auto-calculate act from floor (Act 1: 1-16, Act 2: 17-33, Act 3: 34-50, Act 4: 51+)
            if run["floor"] <= 16:
                run["act"] = 1
            elif run["floor"] <= 33:
                run["act"] = 2
            elif run["floor"] <= 50:
                run["act"] = 3
            else:
                run["act"] = 4
        
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        return run
    
    def set_boss(self, boss_name: str) -> Optional[dict]:
        """Set the current act boss."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["current_boss"] = boss_name
        run["events"].append({
            "type": "boss_scouted",
            "timestamp": datetime.now().isoformat(),
            "details": f"Boss: {boss_name}"
        })
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info(f"Boss set: {boss_name}")
        return run
    
    def add_archetype_hint(self, archetype: str) -> Optional[dict]:
        """Track that the deck is leaning toward an archetype."""
        run = self.get_active_run()
        if not run:
            return None
        
        if "archetype_hints" not in run:
            run["archetype_hints"] = []
        
        if archetype not in run["archetype_hints"]:
            run["archetype_hints"].append(archetype)
            run["last_updated"] = datetime.now().isoformat()
            self._save()
        return run
    
    def add_strategy(self, note: str) -> Optional[dict]:
        """Add a strategy note to the run."""
        run = self.get_active_run()
        if not run:
            return None
        
        if "strategy" not in run:
            run["strategy"] = []
        
        # Avoid exact duplicates
        if note not in run["strategy"]:
            run["strategy"].append(note)
            run["last_updated"] = datetime.now().isoformat()
            self._save()
            logger.info(f"Strategy added: {note}")
        return run
    
    def remove_strategy(self, note: str) -> Optional[dict]:
        """Remove a strategy note from the run."""
        run = self.get_active_run()
        if not run:
            return None
        
        if "strategy" in run and note in run["strategy"]:
            run["strategy"].remove(note)
            run["last_updated"] = datetime.now().isoformat()
            self._save()
            logger.info(f"Strategy removed: {note}")
        return run
    
    def clear_strategy(self) -> Optional[dict]:
        """Clear all strategy notes."""
        run = self.get_active_run()
        if not run:
            return None
        
        run["strategy"] = []
        run["last_updated"] = datetime.now().isoformat()
        self._save()
        logger.info("Strategy cleared")
        return run
    
    def get_strategy(self) -> list:
        """Get current strategy notes."""
        run = self.get_active_run()
        if not run:
            return []
        return run.get("strategy", [])
    
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
        
        run["events"].append({
            "floor": run["floor"],
            "type": "run_end",
            "timestamp": datetime.now().isoformat(),
            "details": "Victory!" if victory else f"Defeated: {cause or 'unknown'}"
        })
        
        self.active_run_id = None
        self._save()
        
        logger.info(f"Run ended: {run['character']} A{run['ascension']} - {'Victory' if victory else 'Defeat'}")
        return run
    
    def get_full_deck(self, run: dict = None) -> list:
        """Get the full current deck (starter + added - removed)."""
        run = run or self.get_active_run()
        if not run:
            return []
        
        deck = run.get("starter_deck", []).copy()
        deck.extend(run.get("added_cards", []))
        
        # Remove cards (handle duplicates properly)
        for card in run.get("removed_cards", []):
            if card in deck:
                deck.remove(card)
        
        return deck
    
    def get_recent_events(self, run: dict = None, count: int = 5) -> list:
        """Get recent events from the run."""
        run = run or self.get_active_run()
        if not run:
            return []
        
        events = run.get("events", [])
        return events[-count:] if events else []


def format_deck_counts(cards: list) -> str:
    """Format a deck list with counts (e.g., '5x Strike, 4x Defend, 1x Bash')."""
    from collections import Counter
    counts = Counter(cards)
    parts = [f"{count}x {card}" for card, count in counts.items()]
    return ", ".join(parts)
