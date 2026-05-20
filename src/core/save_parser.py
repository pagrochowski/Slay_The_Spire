"""
Save file parser for Slay the Spire.

Uses the spireslayer library to parse game save files and extract run data.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.utils.logger import setup_logger, log_operation
from src.utils.id_normalizer import (
    normalize_character_name,
    normalize_card_id,
    normalize_relic_id,
    normalize_potion_id
)

# Initialize logger for this module
log = setup_logger("parsing")


class SaveParser:
    """Parser for Slay the Spire save files."""
    
    def __init__(self):
        """Initialize the save parser."""
        self.editor_class = None
        log.info("SaveParser initialized")
    
    def _import_spireslayer(self) -> bool:
        """
        Lazy import of spireslayer to avoid import-time issues.
        
        Returns:
            True if import successful, False otherwise
        """
        if self.editor_class is not None:
            return True
        
        try:
            from spireslayer.editor import Editor
            self.editor_class = Editor
            log.info("spireslayer.Editor imported successfully")
            return True
            
        except ImportError as e:
            log.error(f"Failed to import spireslayer: {e}")
            log.error("Make sure spireslayer is installed: pip install spireslayer")
            return False
    
    def parse_save_file(self, save_file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse a save file using spireslayer.
        
        Args:
            save_file_path: Path to the .autosave file
            
        Returns:
            Dictionary containing parsed save data, or None if parsing failed
        """
        log.info(f"Parsing save file: {save_file_path.name}")
        log_operation(log, "parse_start", {
            "file": save_file_path.name,
            "size": f"{save_file_path.stat().st_size} bytes"
        })
        
        # Import spireslayer
        if not self._import_spireslayer():
            return None
        
        try:
            # Initialize editor with the save file
            log.debug(f"Initializing spireslayer Editor with: {save_file_path}")
            editor = self.editor_class(autosave_path=str(save_file_path))
            
            # Get decoded save data
            save_data = editor.decoded
            
            if not save_data:
                log.warning("Save file parsed but contains no data")
                return None
            
            log.info("Save file parsed successfully")
            log_operation(log, "parse_complete", {
                "file": save_file_path.name,
                "data_keys": len(save_data.keys()) if isinstance(save_data, dict) else 0
            })
            
            return save_data
            
        except Exception as e:
            log.error(f"Failed to parse save file: {e}")
            log_operation(log, "parse_failed", {
                "file": save_file_path.name,
                "error": str(e)
            }, level="ERROR")
            return None
    
    def extract_run_data(self, save_data: Dict[str, Any], save_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract relevant run information from parsed save data.
        
        Args:
            save_data: Parsed save data from spireslayer
            save_filename: Optional filename to extract character name from
            
        Returns:
            Dictionary with extracted run information
        """
        log.debug("Extracting run data from save")
        
        try:
            # Extract character name from filename (e.g., "WATCHER_20260520_193647.autosave" -> "WATCHER")
            character = "UNKNOWN"
            if save_filename:
                character = normalize_character_name(save_filename)
            elif "name" in save_data:
                # Fallback: use player name (but this is not the character class)
                character = save_data.get("name", "UNKNOWN").upper()
            
            # Extract deck cards (handle both dict and string formats)
            deck_cards = []
            cards = save_data.get("cards", [])
            for card in cards:
                if isinstance(card, dict):
                    card_id = card.get("id", "")
                    upgrades = card.get("upgrades", 0)
                    # Normalize the card ID and add + for each upgrade level
                    normalized_id = normalize_card_id(card_id)
                    deck_cards.append(normalized_id + ("+" * upgrades) if upgrades > 0 else normalized_id)
                elif isinstance(card, str):
                    deck_cards.append(normalize_card_id(card))
                else:
                    deck_cards.append(str(card))
            
            # Extract relics (handle both dict and string formats)
            relic_list = []
            relics = save_data.get("relics", [])
            for relic in relics:
                if isinstance(relic, dict):
                    relic_id = relic.get("id", str(relic))
                    relic_list.append(normalize_relic_id(relic_id))
                else:
                    relic_list.append(normalize_relic_id(str(relic)))
            
            # Extract potions (handle both dict and string formats)
            potion_list = []
            potions = save_data.get("potions", [])
            for potion in potions:
                if isinstance(potion, dict):
                    potion_id = potion.get("id", "")
                    if potion_id:  # Skip empty slots
                        potion_list.append(normalize_potion_id(potion_id))
                elif potion and isinstance(potion, str):
                    potion_list.append(normalize_potion_id(potion))
            
            # Extract boss information (handle various formats)
            boss_name = "Unknown"
            if "boss" in save_data:
                boss_data = save_data["boss"]
                if isinstance(boss_data, dict):
                    boss_name = boss_data.get("name", "Unknown")
                elif isinstance(boss_data, str):
                    boss_name = boss_data
            
            run_data = {
                # Character info
                "character": character,
                "ascension": save_data.get("ascension_level", 0),
                
                # Run progress
                "act": save_data.get("act_num", 1),
                "floor": save_data.get("floor_num", 0),
                
                # Player stats
                "current_hp": save_data.get("current_health", 0),
                "max_hp": save_data.get("max_health", 0),
                "gold": save_data.get("gold", 0),
                
                # Deck cards (normalized)
                "deck": deck_cards,
                
                # Relics (normalized)
                "relics": relic_list,
                
                # Potions (normalized)
                "potions": potion_list,
                
                # Keys (for Act 4 access)
                "has_ruby_key": save_data.get("ruby_key", False),
                "has_emerald_key": save_data.get("emerald_key", False),
                "has_sapphire_key": save_data.get("sapphire_key", False),
                
                # Boss info
                "boss": boss_name,
                
                # Path taken (for tracking which rooms visited)
                "path_taken": save_data.get("path_taken", []),
                
                # Current room
                "current_room": save_data.get("room_phase", "Unknown"),
                
                # Seed (for run tracking)
                "seed": str(save_data.get("seed", "Unknown")),
            }
            
            log.info("Run data extracted successfully")
            log_operation(log, "extract_run_data", {
                "character": run_data["character"],
                "ascension": run_data["ascension"],
                "act": run_data["act"],
                "floor": run_data["floor"],
                "deck_size": len(run_data["deck"]),
                "relic_count": len(run_data["relics"]),
                "potion_count": len(run_data["potions"])
            })
            
            return run_data
            
        except Exception as e:
            log.error(f"Failed to extract run data: {e}")
            log_operation(log, "extract_failed", {
                "error": str(e)
            }, level="ERROR")
            
            # Return minimal data on error
            return {
                "character": "UNKNOWN",
                "ascension": 0,
                "act": 1,
                "floor": 0,
                "current_hp": 0,
                "max_hp": 0,
                "gold": 0,
                "deck": [],
                "relics": [],
                "potions": [],
                "has_ruby_key": False,
                "has_emerald_key": False,
                "has_sapphire_key": False,
                "boss": "Unknown",
                "path_taken": [],
                "current_room": "Unknown",
                "seed": "Unknown"
            }
    
    def save_to_json(self, run_data: Dict[str, Any], output_path: Path) -> bool:
        """
        Save extracted run data to a JSON file.
        
        Args:
            run_data: Extracted run data dictionary
            output_path: Path to save JSON file
            
        Returns:
            True if save successful, False otherwise
        """
        log.debug(f"Saving run data to JSON: {output_path}")
        
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON with pretty formatting
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(run_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"Run data saved to JSON: {output_path.name}")
            log_operation(log, "json_saved", {
                "file": output_path.name,
                "size": f"{output_path.stat().st_size} bytes"
            })
            
            return True
            
        except Exception as e:
            log.error(f"Failed to save JSON: {e}")
            log_operation(log, "json_save_failed", {
                "file": output_path.name,
                "error": str(e)
            }, level="ERROR")
            return False
    
    def parse_and_extract(self, save_file_path: Path, json_output_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Convenience method to parse save file and extract run data in one step.
        
        Args:
            save_file_path: Path to the .autosave file
            json_output_path: Optional path to save JSON output
            
        Returns:
            Extracted run data dictionary, or None if parsing failed
        """
        log.info(f"Parse and extract workflow started for: {save_file_path.name}")
        
        # Parse the save file
        save_data = self.parse_save_file(save_file_path)
        if not save_data:
            return None
        
        # Extract run data (pass filename for character extraction)
        run_data = self.extract_run_data(save_data, save_filename=save_file_path.name)
        
        # Optionally save to JSON
        if json_output_path:
            self.save_to_json(run_data, json_output_path)
        
        return run_data


if __name__ == "__main__":
    # Test the save parser
    from src.core.config import Config
    from src.core.backup_manager import BackupManager
    from datetime import datetime
    
    print("Save Parser Test")
    print("=" * 50)
    
    # Initialize backup manager to find latest save
    backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
    latest_save = backup_mgr.find_latest_autosave()
    
    if not latest_save:
        print("❌ No autosave file found")
        exit(1)
    
    print(f"\n1. Found save file: {latest_save.name}")
    
    # Create a backup first
    print("\n2. Creating backup...")
    backup = backup_mgr.create_backup(latest_save)
    if backup:
        print(f"   ✅ Backup created: {backup.name}")
    
    # Parse the backup (not the live save)
    print(f"\n3. Parsing save file: {backup.name}")
    parser = SaveParser()
    
    # Parse and extract
    json_path = Config.PROCESSED_DIR / f"run_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    run_data = parser.parse_and_extract(backup, json_path)
    
    if run_data:
        print("\n4. Run Data Extracted:")
        print(f"   Character: {run_data['character']}")
        print(f"   Ascension: {run_data['ascension']}")
        print(f"   Act: {run_data['act']}, Floor: {run_data['floor']}")
        print(f"   HP: {run_data['current_hp']}/{run_data['max_hp']}")
        print(f"   Gold: {run_data['gold']}")
        print(f"   Deck Size: {len(run_data['deck'])} cards")
        print(f"   Relics: {len(run_data['relics'])}")
        print(f"   Potions: {len(run_data['potions'])}")
        print(f"   Boss: {run_data['boss']}")
        print(f"\n5. JSON saved to: {json_path}")
    else:
        print("   ❌ Failed to parse save file")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
