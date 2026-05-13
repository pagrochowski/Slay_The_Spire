"""
Script to populate Ascension modifier data.

Ascension levels add cumulative difficulty - each level includes all previous modifiers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.database import DatabaseManager, AscensionModifier


# Ascension data - cumulative modifiers
ASCENSION_DATA = [
    {
        "ascension_level": 1,
        "description": "Elites spawn more often",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.30,
        "has_ascenders_bane": False,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 2,
        "description": "Normal enemies have more challenging movesets",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.30,
        "has_ascenders_bane": False,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 3,
        "description": "Elites have more challenging movesets",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.30,
        "has_ascenders_bane": False,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 4,
        "description": "Start with Ascender's Bane curse (unremovable)",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.30,
        "has_ascenders_bane": True,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 5,
        "description": "Heal 25% less at rest sites (25% instead of 30%)",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 6,
        "description": "Start with less gold (99 -> 99, shops cost more)",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 7,
        "description": "Bosses have more challenging movesets",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 8,
        "description": "Bosses deal more damage",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": False,
        "double_boss": False,
    },
    {
        "ascension_level": 9,
        "description": "Events have unfavorable outcomes more often",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": 0,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 10,
        "description": "Start with 10 less max HP",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 11,
        "description": "Start with 1 less potion slot",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 12,
        "description": "Upgraded cards appear less often in rewards",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 13,
        "description": "Bosses drop more punishing relics",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 14,
        "description": "More Elite fights on floor 2",
        "enemy_hp_percent": 1.0,
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 15,
        "description": "Normal enemies have more HP",
        "enemy_hp_percent": 1.10,  # +10% HP
        "enemy_damage_percent": 1.0,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 16,
        "description": "Normal enemies deal more damage",
        "enemy_hp_percent": 1.10,
        "enemy_damage_percent": 1.10,  # +10% damage
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 17,
        "description": "Act 1 and 2 bosses have harder patterns",
        "enemy_hp_percent": 1.10,
        "enemy_damage_percent": 1.10,
        "elite_hp_percent": 1.0,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 18,
        "description": "Elites have more HP",
        "enemy_hp_percent": 1.10,
        "enemy_damage_percent": 1.10,
        "elite_hp_percent": 1.10,  # +10% Elite HP
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 19,
        "description": "The Heart fight has additional mechanics",
        "enemy_hp_percent": 1.10,
        "enemy_damage_percent": 1.10,
        "elite_hp_percent": 1.10,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": False,
    },
    {
        "ascension_level": 20,
        "description": "Double boss fight in Act 3",
        "enemy_hp_percent": 1.10,
        "enemy_damage_percent": 1.10,
        "elite_hp_percent": 1.10,
        "boss_hp_percent": 1.0,
        "starting_hp_modifier": -10,
        "starting_gold": 99,
        "rest_heal_percent": 0.25,
        "has_ascenders_bane": True,
        "unfavorable_events": True,
        "double_boss": True,
    },
]


def populate_ascension_modifiers() -> None:
    """Populate the ascension modifiers table."""
    logger.info("Populating ascension modifiers...")
    
    db = DatabaseManager()
    
    with db.get_session() as session:
        # Check if already populated
        existing = db.get_all_ascension_modifiers(session)
        if existing:
            logger.info(f"Found {len(existing)} existing ascension modifiers")
            logger.info("Clearing existing data...")
            for mod in existing:
                session.delete(mod)
            session.commit()
        
        # Add all ascension levels
        for data in ASCENSION_DATA:
            db.add_ascension_modifier(session, data)
            logger.debug(f"Added A{data['ascension_level']}: {data['description']}")
        
        session.commit()
        logger.success(f"Successfully added {len(ASCENSION_DATA)} ascension modifiers")


if __name__ == "__main__":
    populate_ascension_modifiers()
