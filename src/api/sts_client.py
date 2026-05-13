"""
Slay the Spire API Client

Fetches card, relic, and keyword data from the STS API.
API Source: https://github.com/jhcheung/slay-the-spire-api
"""

import httpx
from typing import Optional
from pydantic import BaseModel
from loguru import logger


# Default API base URL - this API needs to be self-hosted via Docker
# See: https://github.com/jhcheung/slay-the-spire-api#using-docker-compose
DEFAULT_BASE_URL = "http://localhost:3000"


class STSApiClient:
    """Client for the Slay the Spire API."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get_cards(self) -> list[dict]:
        """Fetch all cards from the API."""
        logger.info("Fetching cards from API...")
        response = await self._client.get("/api/v1/cards")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} cards")
        return data
    
    async def get_relics(self) -> list[dict]:
        """Fetch all relics from the API."""
        logger.info("Fetching relics from API...")
        response = await self._client.get("/api/v1/relics")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} relics")
        return data
    
    async def get_keywords(self) -> list[dict]:
        """Fetch all keywords from the API."""
        logger.info("Fetching keywords from API...")
        response = await self._client.get("/api/v1/keywords")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} keywords")
        return data
    
    async def fetch_all(self) -> dict:
        """Fetch all data (cards, relics, keywords) from the API."""
        return {
            "cards": await self.get_cards(),
            "relics": await self.get_relics(),
            "keywords": await self.get_keywords(),
        }


class SyncSTSApiClient:
    """Synchronous client for the Slay the Spire API."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
    
    def get_cards(self) -> list[dict]:
        """Fetch all cards from the API."""
        logger.info("Fetching cards from API...")
        response = httpx.get(f"{self.base_url}/api/v1/cards", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} cards")
        return data
    
    def get_relics(self) -> list[dict]:
        """Fetch all relics from the API."""
        logger.info("Fetching relics from API...")
        response = httpx.get(f"{self.base_url}/api/v1/relics", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} relics")
        return data
    
    def get_keywords(self) -> list[dict]:
        """Fetch all keywords from the API."""
        logger.info("Fetching keywords from API...")
        response = httpx.get(f"{self.base_url}/api/v1/keywords", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} keywords")
        return data
    
    def fetch_all(self) -> dict:
        """Fetch all data (cards, relics, keywords) from the API."""
        return {
            "cards": self.get_cards(),
            "relics": self.get_relics(),
            "keywords": self.get_keywords(),
        }
