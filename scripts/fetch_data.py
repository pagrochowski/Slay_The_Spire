#!/usr/bin/env python
"""
Fetch data from the Slay the Spire API and save to local files.

NOTE: The API needs to be self-hosted. See:
https://github.com/jhcheung/slay-the-spire-api#using-docker-compose

Alternative: You can manually download/create JSON files from other sources.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.sts_client import SyncSTSApiClient
from src.utils.logger import setup_logger
from loguru import logger


DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def save_json(data: dict | list, filename: str) -> None:
    """Save data to JSON file."""
    filepath = DATA_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(data) if isinstance(data, list) else 'data'} to {filepath}")


def fetch_from_api(base_url: str = "http://localhost:3000") -> None:
    """Fetch all data from the API."""
    client = SyncSTSApiClient(base_url)
    
    try:
        logger.info("Fetching cards...")
        cards = client.get_cards()
        save_json(cards, "cards.json")
        
        logger.info("Fetching relics...")
        relics = client.get_relics()
        save_json(relics, "relics.json")
        
        logger.info("Fetching keywords...")
        keywords = client.get_keywords()
        save_json(keywords, "keywords.json")
        
        logger.success("All data fetched successfully!")
        
    except Exception as e:
        logger.error(f"Failed to fetch data from API: {e}")
        logger.info("Make sure the API is running. See README for setup instructions.")
        raise


def main():
    setup_logger("INFO")
    
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Slay the Spire data from API")
    parser.add_argument(
        "--url", 
        default="http://localhost:3000",
        help="Base URL of the STS API (default: http://localhost:3000)"
    )
    args = parser.parse_args()
    
    fetch_from_api(args.url)


if __name__ == "__main__":
    main()
