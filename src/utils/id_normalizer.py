"""
ID Normalization Utilities for Slay the Spire.

Converts save file IDs to display names for cards, relics, and potions.
"""

import re
from typing import Optional
from src.knowledge.knowledge_base import KnowledgeBase


def normalize_card_id(card_id: str, kb: Optional[KnowledgeBase] = None) -> str:
    """
    Normalize a card ID from save file to display name.
    
    Examples:
        "BattleHymn" → "Battle Hymn"
        "Defend_P" → "Defend"
        "Strike_R" → "Strike"
        "Shrug it Off" → "Shrug It Off"
    
    Args:
        card_id: Card ID from save file
        kb: Optional KnowledgeBase to verify match
        
    Returns:
        Normalized card name
    """
    if not card_id:
        return card_id
    
    # Handle upgrades (e.g., "Strike+" or "Strike+++")
    upgrade_count = card_id.count('+')
    base_id = card_id.rstrip('+')
    
    # Remove character suffix (_P, _R, _G, _B for Purple/Red/Green/Blue)
    base_id = re.sub(r'_[PRGB]$', '', base_id)
    
    # Split camelCase into words
    # Insert space before uppercase letters (except first letter)
    normalized = re.sub(r'(?<!^)(?=[A-Z])', ' ', base_id)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Try to find exact match in knowledge base
    if kb:
        # Try exact match first
        if kb.get_card_data(normalized):
            return normalized + ('+' * upgrade_count) if upgrade_count > 0 else normalized
        
        # Try fuzzy match
        from rapidfuzz import process, fuzz
        all_cards = []
        for char in ["ironclad", "silent", "defect", "watcher", "colorless"]:
            all_cards.extend(kb.get_cards_for_character(char))
        
        if all_cards:
            match = process.extractOne(
                normalized,
                all_cards,
                scorer=fuzz.ratio
            )
            if match and match[1] >= 80:  # 80% similarity
                return match[0] + ('+' * upgrade_count) if upgrade_count > 0 else match[0]
    
    # Return normalized version even if no KB match
    return normalized + ('+' * upgrade_count) if upgrade_count > 0 else normalized


def normalize_relic_id(relic_id: str, kb: Optional[KnowledgeBase] = None) -> str:
    """
    Normalize a relic ID from save file to display name.
    
    Examples:
        "PureWater" → "Pure Water"
        "BagOfPreparation" → "Bag of Preparation"
        "Molten Egg 2" → "Molten Egg 2" (preserves counter)
    
    Args:
        relic_id: Relic ID from save file
        kb: Optional KnowledgeBase to verify match
        
    Returns:
        Normalized relic name (with counter if present)
    """
    if not relic_id:
        return relic_id
    
    # Extract counter if present (e.g., "Molten Egg 2" → "Molten Egg", counter=2)
    # Relic counters appear as "RelicName <number>" at the end
    counter = None
    base_relic = relic_id
    counter_match = re.search(r'\s+(\d+)$', relic_id)
    if counter_match:
        counter = counter_match.group(1)
        base_relic = relic_id[:counter_match.start()]
    
    # Split camelCase into words
    normalized = re.sub(r'(?<!^)(?=[A-Z])', ' ', base_relic)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Handle "of" in names (e.g., "Bag Of Preparation" → "Bag of Preparation")
    normalized = re.sub(r'\bOf\b', 'of', normalized)
    
    # Try to find exact match in knowledge base
    if kb:
        if kb.get_relic_data(normalized):
            # Return with counter if present
            return f"{normalized} {counter}" if counter else normalized
        
        # Try fuzzy match
        from rapidfuzz import process, fuzz
        all_relics = kb.get_all_relics()
        
        if all_relics:
            match = process.extractOne(
                normalized,
                all_relics,
                scorer=fuzz.ratio
            )
            if match and match[1] >= 80:
                matched_name = match[0]
                return f"{matched_name} {counter}" if counter else matched_name
    
    # Return with counter if present
    return f"{normalized} {counter}" if counter else normalized


def normalize_potion_id(potion_id: str, kb: Optional[KnowledgeBase] = None) -> str:
    """
    Normalize a potion ID from save file to display name.
    
    Examples:
        "FearPotion" → "Fear Potion"
        "RegenPotion" → "Regen Potion"
    
    Args:
        potion_id: Potion ID from save file
        kb: Optional KnowledgeBase to verify match
        
    Returns:
        Normalized potion name
    """
    if not potion_id:
        return potion_id
    
    # Split camelCase into words
    normalized = re.sub(r'(?<!^)(?=[A-Z])', ' ', potion_id)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Try to find exact match in knowledge base
    if kb:
        potion_data = kb.get_potion_data(normalized)
        if potion_data:
            return potion_data.get("name", normalized)
        
        # Try fuzzy match
        from rapidfuzz import process, fuzz
        all_potions = [p.get("name", "") for p in kb.potions.values()]
        
        if all_potions:
            match = process.extractOne(
                normalized,
                all_potions,
                scorer=fuzz.ratio
            )
            if match and match[1] >= 80:
                return match[0]
    
    return normalized


def normalize_character_name(filename: str) -> str:
    """
    Extract character name from save filename.
    
    Examples:
        "WATCHER_20260520_193647.autosave" → "WATCHER"
        "IRONCLAD.autosave" → "IRONCLAD"
        "SILENT_BACKUP" → "SILENT"
    
    Args:
        filename: Save file name
        
    Returns:
        Character name (UPPERCASE)
    """
    from pathlib import Path
    
    # Get stem (filename without extension)
    stem = Path(filename).stem.upper()
    
    # Extract character name (everything before first underscore or number)
    # Match: WATCHER, IRONCLAD, SILENT, DEFECT
    match = re.match(r'^(WATCHER|IRONCLAD|SILENT|DEFECT)', stem)
    if match:
        return match.group(1)
    
    # Fallback: take first word before underscore
    parts = stem.split('_')
    return parts[0] if parts else stem


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add project root to path for testing
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    
    # Test the normalizations
    print("Testing ID Normalization:")
    print("=" * 60)
    
    test_cards = ["BattleHymn", "Defend_P", "Strike_R+", "ShrugItOff++"]
    print("\nCards:")
    for card_id in test_cards:
        normalized = normalize_card_id(card_id)
        print(f"  {card_id:20} → {normalized}")
    
    test_relics = ["PureWater", "BagOfPreparation", "SingingBowl"]
    print("\nRelics:")
    for relic_id in test_relics:
        normalized = normalize_relic_id(relic_id)
        print(f"  {relic_id:20} → {normalized}")
    
    test_potions = ["FearPotion", "RegenPotion", "StrengthPotion"]
    print("\nPotions:")
    for potion_id in test_potions:
        normalized = normalize_potion_id(potion_id)
        print(f"  {potion_id:20} → {normalized}")
    
    test_filenames = [
        "WATCHER_20260520_193647.autosave",
        "IRONCLAD.autosave",
        "SILENT_BACKUP"
    ]
    print("\nCharacter Names:")
    for filename in test_filenames:
        character = normalize_character_name(filename)
        print(f"  {filename:35} → {character}")
