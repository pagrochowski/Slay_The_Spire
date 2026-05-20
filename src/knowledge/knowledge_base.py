"""
Knowledge Base for Slay the Spire cards, relics, and potions.

Provides access to game data with character-specific filtering and fuzzy matching.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from src.core.config import Config
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("parsing")


class KnowledgeBase:
    """Access layer for game knowledge base."""
    
    def __init__(self, knowledge_dir: Optional[Path] = None):
        """
        Initialize knowledge base.
        
        Args:
            knowledge_dir: Path to knowledge directory (default: from Config)
        """
        self.knowledge_dir = knowledge_dir or Config.KNOWLEDGE_DIR
        
        # Storage for loaded data
        self.cards: Dict[str, dict] = {}  # {card_name_lower: card_data}
        self.cards_by_character: Dict[str, List[str]] = {}  # {character: [card_names]}
        self.relics: Dict[str, dict] = {}  # {relic_name_lower: relic_data}
        self.potions: Dict[str, dict] = {}  # {potion_name_lower: potion_data}
        
        # Load all data
        self._load_all_data()
        
        log.info("KnowledgeBase initialized")
        log_operation(log, "kb_initialized", {
            "total_cards": len(self.cards),
            "total_relics": len(self.relics),
            "total_potions": len(self.potions)
        })
    
    def _load_json_file(self, filepath: Path) -> dict:
        """Load a JSON file and return its contents."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load {filepath.name}: {e}")
            return {}
    
    def _load_all_data(self):
        """Load all cards, relics, and potions from JSON files."""
        log.debug("Loading knowledge base data")
        
        # Load cards by character
        for character, card_file in Config.CARD_FILES.items():
            filepath = self.knowledge_dir / card_file
            if not filepath.exists():
                log.warning(f"Card file not found: {filepath}")
                continue
            
            data = self._load_json_file(filepath)
            cards_list = data.get("cards", [])
            
            # Store cards in main dictionary
            card_names = []
            for card in cards_list:
                name = card.get("name", "")
                if name:
                    name_lower = name.lower()
                    self.cards[name_lower] = card
                    card_names.append(name)
            
            # Store character-specific card names
            self.cards_by_character[character] = card_names
            
            log.debug(f"Loaded {len(card_names)} cards for {character}")
        
        # Load relics
        for relic_file in Config.RELIC_FILES:
            filepath = self.knowledge_dir / relic_file
            if not filepath.exists():
                log.warning(f"Relic file not found: {filepath}")
                continue
            
            data = self._load_json_file(filepath)
            relics_list = data.get("relics", [])
            
            for relic in relics_list:
                name = relic.get("name", "")
                if name:
                    self.relics[name.lower()] = relic
        
        log.debug(f"Loaded {len(self.relics)} relics")
        
        # Load potions
        potion_filepath = self.knowledge_dir / Config.POTION_FILE
        if potion_filepath.exists():
            data = self._load_json_file(potion_filepath)
            potions_list = data.get("potions", [])
            
            for potion in potions_list:
                name = potion.get("name", "")
                if name:
                    self.potions[name.lower()] = potion
            
            log.debug(f"Loaded {len(self.potions)} potions")
    
    def get_cards_for_character(self, character: str) -> List[str]:
        """
        Get all card names available for a specific character.
        
        Args:
            character: Character name (ironclad, silent, defect, watcher)
            
        Returns:
            List of card names (includes colorless + character-specific)
        """
        character_lower = character.lower()
        
        # Get colorless cards (available to all)
        colorless_cards = self.cards_by_character.get("colorless", [])
        
        # Get character-specific cards
        character_cards = self.cards_by_character.get(character_lower, [])
        
        # Combine (colorless + character-specific)
        all_cards = colorless_cards + character_cards
        
        log.debug(f"Retrieved {len(all_cards)} cards for {character} "
                  f"({len(colorless_cards)} colorless + {len(character_cards)} class-specific)")
        
        return all_cards
    
    def get_choosable_cards_for_character(self, character: str) -> List[str]:
        """
        Get choosable card names for a character (excludes STATUS and CURSE cards).
        
        Use this for card choice/reward contexts where status/curse cards don't appear.
        
        Args:
            character: Character name (ironclad, silent, defect, watcher)
            
        Returns:
            List of choosable card names (no STATUS/CURSE cards)
        """
        all_cards = self.get_cards_for_character(character)
        
        # Filter out status and curse cards
        choosable = []
        filtered = []
        
        for card_name in all_cards:
            card_data = self.get_card_data(card_name)
            if card_data:
                card_type = card_data.get("type", "").upper()
                if card_type in ["STATUS", "CURSE"]:
                    filtered.append(card_name)
                else:
                    choosable.append(card_name)
            else:
                # If we can't find data, include it (shouldn't happen)
                choosable.append(card_name)
        
        log.debug(f"Filtered {len(filtered)} status/curse cards from {character} pool: {', '.join(filtered[:5])}")
        log.debug(f"Returning {len(choosable)} choosable cards for {character}")
        
        return choosable
    
    def get_all_relics(self) -> List[str]:
        """
        Get all relic names.
        
        Returns:
            List of all relic names
        """
        return [relic["name"] for relic in self.relics.values()]
    
    def get_card_data(self, card_name: str) -> Optional[dict]:
        """
        Get full data for a specific card.
        
        Args:
            card_name: Card name (case-insensitive)
            
        Returns:
            Card data dictionary, or None if not found
        """
        return self.cards.get(card_name.lower())
    
    def get_relic_data(self, relic_name: str) -> Optional[dict]:
        """
        Get full data for a specific relic.
        
        Args:
            relic_name: Relic name (case-insensitive)
            
        Returns:
            Relic data dictionary, or None if not found
        """
        return self.relics.get(relic_name.lower())
    
    def get_potion_data(self, potion_name: str) -> Optional[dict]:
        """
        Get full data for a specific potion.
        
        Args:
            potion_name: Potion name (case-insensitive)
            
        Returns:
            Potion data dictionary, or None if not found
        """
        return self.potions.get(potion_name.lower())
    
    def fuzzy_match_card(self, query: str, character: Optional[str] = None, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Find cards matching a query using fuzzy string matching.
        
        Args:
            query: Search query (potentially misspelled card name)
            character: Optional character to filter cards (ironclad, silent, etc.)
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of (card_name, similarity_score) tuples, sorted by score descending
        """
        query_lower = query.lower()
        
        # Get candidate cards
        if character:
            candidates = self.get_cards_for_character(character)
        else:
            candidates = [card["name"] for card in self.cards.values()]
        
        # Calculate similarity scores
        matches = []
        for card_name in candidates:
            similarity = SequenceMatcher(None, query_lower, card_name.lower()).ratio()
            if similarity >= threshold:
                matches.append((card_name, similarity))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        log.debug(f"Fuzzy match for '{query}': found {len(matches)} matches (threshold={threshold})")
        
        return matches
    
    def fuzzy_match_relic(self, query: str, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Find relics matching a query using fuzzy string matching.
        
        Args:
            query: Search query (potentially misspelled relic name)
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of (relic_name, similarity_score) tuples, sorted by score descending
        """
        query_lower = query.lower()
        
        # Calculate similarity scores for all relics
        matches = []
        for relic_name in self.get_all_relics():
            similarity = SequenceMatcher(None, query_lower, relic_name.lower()).ratio()
            if similarity >= threshold:
                matches.append((relic_name, similarity))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        log.debug(f"Fuzzy match for '{query}': found {len(matches)} relics (threshold={threshold})")
        
        return matches
    
    def find_best_match(self, query: str, character: Optional[str] = None, match_type: str = "card") -> Optional[str]:
        """
        Find the single best match for a query.
        
        Args:
            query: Search query
            character: Optional character for card filtering
            match_type: Type of match ("card" or "relic")
            
        Returns:
            Best matching name, or None if no good match found
        """
        if match_type == "card":
            matches = self.fuzzy_match_card(query, character=character, threshold=0.6)
        elif match_type == "relic":
            matches = self.fuzzy_match_relic(query, threshold=0.6)
        else:
            return None
        
        if matches:
            best_match, score = matches[0]
            log.debug(f"Best match for '{query}': '{best_match}' (score={score:.2f})")
            return best_match
        
        return None


if __name__ == "__main__":
    # Test the knowledge base
    from datetime import datetime
    
    print("Knowledge Base Test")
    print("=" * 50)
    
    # Initialize KB
    kb = KnowledgeBase()
    
    print(f"\n1. Total Data Loaded:")
    print(f"   Cards: {len(kb.cards)}")
    print(f"   Relics: {len(kb.relics)}")
    print(f"   Potions: {len(kb.potions)}")
    
    print(f"\n2. Character-Specific Cards:")
    for character in ["ironclad", "silent", "defect", "watcher"]:
        cards = kb.get_cards_for_character(character)
        print(f"   {character.capitalize()}: {len(cards)} cards")
    
    print(f"\n3. Test Card Lookup:")
    card = kb.get_card_data("Strike")
    if card:
        print(f"   Name: {card['name']}")
        print(f"   Type: {card['type']}")
        print(f"   Cost: {card['cost']}")
        print(f"   Description: {card['description']}")
    
    print(f"\n4. Test Relic Lookup:")
    relic = kb.get_relic_data("Akabeko")
    if relic:
        print(f"   Name: {relic['name']}")
        print(f"   Tier: {relic['tier']}")
        print(f"   Description: {relic['description']}")
    
    print(f"\n5. Test Fuzzy Matching (Card):")
    matches = kb.fuzzy_match_card("shrug it off", character="ironclad")
    for name, score in matches[:3]:
        print(f"   {name}: {score:.2f}")
    
    print(f"\n6. Test Fuzzy Matching (Relic):")
    matches = kb.fuzzy_match_relic("dead branch")
    for name, score in matches[:3]:
        print(f"   {name}: {score:.2f}")
    
    print(f"\n7. Test Best Match:")
    best = kb.find_best_match("warcry", character="ironclad", match_type="card")
    print(f"   Query: 'warcry' -> Best: '{best}'")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
