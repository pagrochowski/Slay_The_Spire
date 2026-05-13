#!/usr/bin/env python
"""
Populate the database with Slay the Spire data from local JSON files.

Run download_data.py first to fetch the data from GitHub.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager, Card, Relic, Keyword, Enemy, Potion
from src.utils.logger import setup_logger
from loguru import logger


DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DB_PATH = Path(__file__).parent.parent / "db" / "sts_knowledge.db"


def load_json(filename: str) -> list[dict]:
    """Load data from JSON file."""
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        logger.warning(f"File not found: {filepath}")
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_cost(cost_str: Optional[str]) -> Optional[int]:
    """Parse cost string to integer, handling X and empty costs."""
    if cost_str is None or cost_str == "" or cost_str == "X":
        return None
    try:
        return int(cost_str)
    except ValueError:
        return None


def detect_card_flags(description: str) -> dict:
    """Detect card flags from description text."""
    desc_lower = description.lower() if description else ""
    return {
        "exhausts": "exhaust" in desc_lower and "exhaust." in desc_lower,
        "is_innate": "innate" in desc_lower,
        "is_ethereal": "ethereal" in desc_lower,
        "targets_all": "all enemies" in desc_lower,
    }


def transform_card_data(api_card: dict) -> dict:
    """Transform API card data to database model format."""
    description = api_card.get("description", "")
    flags = detect_card_flags(description)
    
    # Map color to standard format
    color_map = {
        "Red": "RED",
        "Green": "GREEN",
        "Blue": "BLUE", 
        "Purple": "PURPLE",
        "Colorless": "COLORLESS",
        "Curse": "CURSE",
    }
    
    # Map rarity to standard format
    rarity_map = {
        "Basic": "BASIC",
        "Common": "COMMON",
        "Uncommon": "UNCOMMON",
        "Rare": "RARE",
        "Special": "SPECIAL",
        "Curse": "CURSE",
    }
    
    # Map type to standard format
    type_map = {
        "Attack": "ATTACK",
        "Skill": "SKILL",
        "Power": "POWER",
        "Status": "STATUS",
        "Curse": "CURSE",
    }
    
    raw_color = api_card.get("color", "")
    raw_rarity = api_card.get("rarity", "")
    raw_type = api_card.get("type", "")
    
    return {
        "name": api_card.get("name", "Unknown"),
        "description": description,
        "color": color_map.get(raw_color, raw_color.upper() if raw_color else None),
        "rarity": rarity_map.get(raw_rarity, raw_rarity.upper() if raw_rarity else None),
        "card_type": type_map.get(raw_type, raw_type.upper() if raw_type else None),
        "cost": parse_cost(api_card.get("cost")),
        "exhausts": flags["exhausts"],
        "is_innate": flags["is_innate"],
        "is_ethereal": flags["is_ethereal"],
        "targets_all": flags["targets_all"],
    }


def transform_relic_data(api_relic: dict) -> dict:
    """Transform API relic data to database model format."""
    # Map tier to standard rarity
    tier_map = {
        "Starter": "STARTER",
        "Common": "COMMON",
        "Uncommon": "UNCOMMON",
        "Rare": "RARE",
        "Boss": "BOSS",
        "Shop": "SHOP",
        "Special": "SPECIAL",
        "Event": "EVENT",
    }
    
    # Map pool to standard format
    pool_map = {
        "Red": "IRONCLAD",
        "Green": "SILENT",
        "Blue": "DEFECT",
        "Purple": "WATCHER",
        "": "SHARED",
    }
    
    raw_tier = api_relic.get("tier", "")
    raw_pool = api_relic.get("pool", "")
    
    return {
        "name": api_relic.get("name", "Unknown"),
        "description": api_relic.get("description"),
        "flavor_text": api_relic.get("flavorText"),
        "rarity": tier_map.get(raw_tier, raw_tier.upper() if raw_tier else None),
        "pool": pool_map.get(raw_pool, raw_pool.upper() if raw_pool else "SHARED"),
    }


def transform_keyword_data(api_keyword: dict) -> dict:
    """Transform API keyword data to database model format."""
    return {
        "name": api_keyword.get("name", "Unknown"),
        "description": api_keyword.get("description"),
    }


def transform_creature_data(api_creature: dict) -> dict:
    """Transform API creature data to Enemy model format."""
    # Determine enemy type based on various fields
    name = api_creature.get("name", "Unknown")
    
    # Boss names
    bosses = [
        "The Guardian", "Hexaghost", "Slime Boss",
        "The Champ", "Collector", "Automaton", "Bronze Automaton",
        "Awakened One", "Donu", "Deca", "Time Eater",
        "Corrupt Heart", "The Heart"
    ]
    
    # Elite names
    elites = [
        "Gremlin Nob", "Lagavulin", "Sentry", "Sentries",
        "Book of Stabbing", "Gremlin Leader", "Slavers", "Taskmaster",
        "Giant Head", "Nemesis", "Reptomancer"
    ]
    
    if name in bosses or "boss" in name.lower():
        enemy_type = "BOSS"
    elif name in elites or "elite" in api_creature.get("type", "").lower():
        enemy_type = "ELITE"
    elif "minion" in api_creature.get("type", "").lower():
        enemy_type = "MINION"
    else:
        enemy_type = "NORMAL"
    
    # Parse HP - may be a range like "10-14" or single value
    hp_str = str(api_creature.get("hp", ""))
    hp_min = None
    hp_max = None
    
    if "-" in hp_str:
        parts = hp_str.split("-")
        try:
            hp_min = int(parts[0].strip())
            hp_max = int(parts[1].strip())
        except (ValueError, IndexError):
            pass
    elif hp_str.isdigit():
        hp_min = hp_max = int(hp_str)
    
    return {
        "name": name,
        "enemy_type": enemy_type,
        "base_hp_min": hp_min,
        "base_hp_max": hp_max,
        "abilities": json.dumps(api_creature.get("abilities", [])) if api_creature.get("abilities") else None,
    }


def transform_potion_data(api_potion: dict) -> dict:
    """Transform API potion data to Potion model format."""
    rarity_map = {
        "Common": "COMMON",
        "Uncommon": "UNCOMMON",
        "Rare": "RARE",
    }
    
    raw_rarity = api_potion.get("rarity", "")
    
    return {
        "name": api_potion.get("name", "Unknown"),
        "rarity": rarity_map.get(raw_rarity, raw_rarity.upper() if raw_rarity else None),
        "description": api_potion.get("description"),
    }


def populate_database(reset: bool = False) -> None:
    """Populate the database with data from JSON files."""
    
    db = DatabaseManager(str(DB_PATH))
    
    if reset:
        logger.warning("Resetting database...")
        db.drop_tables()
    
    db.create_tables()
    
    with db.get_session() as session:
        # Load and insert cards
        cards_data = load_json("cards.json")
        if cards_data:
            logger.info(f"Processing {len(cards_data)} cards...")
            for card_api in cards_data:
                try:
                    card_db = transform_card_data(card_api)
                    existing = db.get_card_by_name(session, card_db["name"])
                    if not existing:
                        db.add_card(session, card_db)
                except Exception as e:
                    logger.warning(f"Failed to add card {card_api.get('name')}: {e}")
            session.commit()
            logger.success(f"Cards processed: {db.count(session, Card)}")
        
        # Load and insert relics
        relics_data = load_json("relics.json")
        if relics_data:
            logger.info(f"Processing {len(relics_data)} relics...")
            for relic_api in relics_data:
                try:
                    relic_db = transform_relic_data(relic_api)
                    existing = db.get_relic_by_name(session, relic_db["name"])
                    if not existing:
                        db.add_relic(session, relic_db)
                except Exception as e:
                    logger.warning(f"Failed to add relic {relic_api.get('name')}: {e}")
            session.commit()
            logger.success(f"Relics processed: {db.count(session, Relic)}")
        
        # Load and insert keywords
        keywords_data = load_json("keywords.json")
        if keywords_data:
            logger.info(f"Processing {len(keywords_data)} keywords...")
            for kw_api in keywords_data:
                try:
                    kw_db = transform_keyword_data(kw_api)
                    existing = db.get_keyword_by_name(session, kw_db["name"])
                    if not existing:
                        db.add_keyword(session, kw_db)
                except Exception as e:
                    logger.warning(f"Failed to add keyword {kw_api.get('name')}: {e}")
            session.commit()
            logger.success(f"Keywords processed: {db.count(session, Keyword)}")
        
        # Load and insert creatures/enemies
        creatures_data = load_json("creatures.json")
        if creatures_data:
            logger.info(f"Processing {len(creatures_data)} creatures/enemies...")
            for creature_api in creatures_data:
                try:
                    enemy_db = transform_creature_data(creature_api)
                    existing = db.get_enemy_by_name(session, enemy_db["name"])
                    if not existing:
                        db.add_enemy(session, enemy_db)
                except Exception as e:
                    logger.warning(f"Failed to add enemy {creature_api.get('name')}: {e}")
            session.commit()
            logger.success(f"Enemies processed: {db.count(session, Enemy)}")
        
        # Load and insert potions
        potions_data = load_json("potions.json")
        if potions_data:
            logger.info(f"Processing {len(potions_data)} potions...")
            for potion_api in potions_data:
                try:
                    potion_db = transform_potion_data(potion_api)
                    existing = db.get_potion_by_name(session, potion_db["name"])
                    if not existing:
                        db.add_potion(session, potion_db)
                except Exception as e:
                    logger.warning(f"Failed to add potion {potion_api.get('name')}: {e}")
            session.commit()
            logger.success(f"Potions processed: {db.count(session, Potion)}")
        
        # Print stats
        stats = db.get_stats(session)
        logger.info("=" * 40)
        logger.info("Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")


def main():
    setup_logger("INFO")
    
    import argparse
    parser = argparse.ArgumentParser(description="Populate STS knowledge database")
    parser.add_argument(
        "--reset", 
        action="store_true",
        help="Drop and recreate all tables before populating"
    )
    args = parser.parse_args()
    
    populate_database(reset=args.reset)


if __name__ == "__main__":
    main()
