"""
Configuration management for Slay the Spire Voice Recorder.

Loads settings from environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Config:
    """Centralized configuration."""
    
    # ========== Paths ==========
    # Project directories
    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = PROJECT_ROOT / "data"
    KNOWLEDGE_DIR = DATA_DIR / "knowledge"
    BACKUP_DIR = DATA_DIR / "backups"
    PROCESSED_DIR = DATA_DIR / "processed"
    LOGS_DIR = PROJECT_ROOT / "logs"
    
    # Game save file location
    GAME_SAVES_DIR = Path(r"c:\Games\Slay.the.Spire.v2.3.4\Slay.the.Spire.v2.3.4\saves")
    
    # Run summary file
    RUN_SUMMARY_PATH = PROJECT_ROOT / "Run_Summary.md"
    
    # AI guide file
    AI_GUIDE_PATH = PROJECT_ROOT / "AI_GUIDE.md"
    
    # ========== API Configuration ==========
    # Groq API key
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    
    # Whisper models (transcription)
    WHISPER_PRIMARY_MODEL = "whisper-large-v3"
    WHISPER_FALLBACK_MODEL = "whisper-large-v3-turbo"
    
    # LLM models for name correction (4-tier fallback)
    LLM_MODELS = [
        "llama-3.1-8b-instant",      # Alternating primary 1
        "openai/gpt-oss-20b",        # Alternating primary 2
        "llama-3.3-70b-versatile",   # Tier 3 fallback
        "openai/gpt-oss-120b"        # Tier 4 fallback
    ]
    
    # LLM timeout per model (seconds)
    LLM_TIMEOUT = 3.0
    
    # ========== Backup Configuration ==========
    # Maximum age of backups in hours (older backups are deleted)
    BACKUP_MAX_AGE_HOURS = 24
    
    # ========== Voice Recording Configuration ==========
    # Hotkey for voice recording
    RECORDING_HOTKEY = "F1"
    
    # Exit hotkey
    EXIT_HOTKEY = "ESC"
    
    # Audio sample rate
    AUDIO_SAMPLE_RATE = 16000
    
    # Audio channels (mono)
    AUDIO_CHANNELS = 1
    
    # ========== Knowledge Base Configuration ==========
    # Character names
    CHARACTERS = ["ironclad", "silent", "defect", "watcher"]
    
    # Card file patterns
    CARD_FILES = {
        "colorless": "cards/cards_colorless.json",
        "ironclad": "cards/cards_ironclad.json",
        "silent": "cards/cards_silent.json",
        "defect": "cards/cards_defect.json",
        "watcher": "cards/cards_watcher.json",
    }
    
    # Relic file patterns
    RELIC_FILES = [
        "relics/relics_boss.json",
        "relics/relics_common.json",
        "relics/relics_rare.json",
        "relics/relics_shop.json",
        "relics/relics_starter.json",
        "relics/relics_uncommon.json",
    ]
    
    # Potion file
    POTION_FILE = "potions.json"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If required configuration is missing
        """
        # Check API key
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Check game saves directory exists
        if not cls.GAME_SAVES_DIR.exists():
            raise ValueError(f"Game saves directory not found: {cls.GAME_SAVES_DIR}")
        
        # Check knowledge directory exists
        if not cls.KNOWLEDGE_DIR.exists():
            raise ValueError(f"Knowledge directory not found: {cls.KNOWLEDGE_DIR}")
        
        return True
    
    @classmethod
    def create_directories(cls) -> None:
        """Create required directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.BACKUP_DIR.mkdir(exist_ok=True)
        cls.PROCESSED_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test configuration
    print("Configuration Test")
    print("=" * 50)
    print(f"Project Root: {Config.PROJECT_ROOT}")
    print(f"Game Saves Dir: {Config.GAME_SAVES_DIR}")
    print(f"Knowledge Dir: {Config.KNOWLEDGE_DIR}")
    print(f"Backup Dir: {Config.BACKUP_DIR}")
    print(f"API Key Set: {'Yes' if Config.GROQ_API_KEY else 'No'}")
    print(f"LLM Models: {Config.LLM_MODELS}")
    print(f"Whisper Models: {Config.WHISPER_PRIMARY_MODEL}, {Config.WHISPER_FALLBACK_MODEL}")
    print("=" * 50)
    
    try:
        Config.validate()
        print("✅ Configuration is valid!")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
    
    # Create directories
    Config.create_directories()
    print("✅ Directories created/verified")
