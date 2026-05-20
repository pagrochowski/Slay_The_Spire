#!/usr/bin/env python
"""
Download Slay the Spire data directly from GitHub.

This script downloads the items.json file which contains all game data:
- Cards
- Relics
- Potions
- Creatures
- Keywords

No Docker or API server required!
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from loguru import logger

from src_old.utils.logger import setup_logger


DATA_URL = "https://raw.githubusercontent.com/jhcheung/slay-the-spire-api/master/db/items.json"
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def download_data() -> dict:
    """Download the items.json file from GitHub."""
    logger.info(f"Downloading data from {DATA_URL}...")
    
    response = httpx.get(DATA_URL, timeout=30.0)
    response.raise_for_status()
    
    data = response.json()
    logger.success(f"Downloaded data successfully!")
    
    return data


def save_data(data: dict) -> None:
    """Save data to individual JSON files for easier processing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save complete file
    complete_path = DATA_DIR / "items_complete.json"
    with open(complete_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved complete data to {complete_path}")
    
    # Save individual collections
    collections = {
        "cards.json": data.get("cards", []),
        "relics.json": data.get("relics", []),
        "potions.json": data.get("potions", []),
        "creatures.json": data.get("creatures", []),
        "keywords.json": data.get("keywords", []),
    }
    
    for filename, items in collections.items():
        filepath = DATA_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(items)} items to {filename}")


def print_summary(data: dict) -> None:
    """Print a summary of downloaded data."""
    print("\n" + "=" * 50)
    print("DATA SUMMARY")
    print("=" * 50)
    print(f"Cards:     {len(data.get('cards', []))}")
    print(f"Relics:    {len(data.get('relics', []))}")
    print(f"Potions:   {len(data.get('potions', []))}")
    print(f"Creatures: {len(data.get('creatures', []))}")
    print(f"Keywords:  {len(data.get('keywords', []))}")
    print("=" * 50)
    
    # Card breakdown by color
    cards = data.get("cards", [])
    colors = {}
    for card in cards:
        color = card.get("color", "Unknown")
        colors[color] = colors.get(color, 0) + 1
    
    print("\nCards by Color:")
    for color, count in sorted(colors.items()):
        print(f"  {color}: {count}")
    
    # Relic breakdown by tier
    relics = data.get("relics", [])
    tiers = {}
    for relic in relics:
        tier = relic.get("tier", "Unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
    
    print("\nRelics by Tier:")
    for tier, count in sorted(tiers.items()):
        print(f"  {tier}: {count}")


def main():
    setup_logger("INFO")
    
    try:
        # Download
        data = download_data()
        
        # Save
        save_data(data)
        
        # Summary
        print_summary(data)
        
        logger.success("\nData download complete! Run 'python scripts/populate_db.py' to populate the database.")
        
    except Exception as e:
        logger.error(f"Failed to download data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
