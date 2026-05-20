"""Unit tests for configuration module."""

import pytest
import os
from pathlib import Path
from src.core.config import Config


class TestConfig:
    """Test cases for configuration management."""
    
    def test_project_root_exists(self):
        """Test that project root path is correct."""
        assert Config.PROJECT_ROOT.exists()
        assert Config.PROJECT_ROOT.is_dir()
    
    def test_required_directories_defined(self):
        """Test that all required directories are defined."""
        assert hasattr(Config, "DATA_DIR")
        assert hasattr(Config, "KNOWLEDGE_DIR")
        assert hasattr(Config, "BACKUP_DIR")
        assert hasattr(Config, "LOGS_DIR")
        assert hasattr(Config, "GAME_SAVES_DIR")
    
    def test_api_key_loaded(self):
        """Test that API key is loaded from environment."""
        # This test assumes .env file is present
        # If not, it should gracefully handle None
        assert hasattr(Config, "GROQ_API_KEY")
    
    def test_llm_models_defined(self):
        """Test that LLM models are properly defined."""
        assert len(Config.LLM_MODELS) == 4
        assert "llama-3.1-8b-instant" in Config.LLM_MODELS
        assert "openai/gpt-oss-20b" in Config.LLM_MODELS
        assert "llama-3.3-70b-versatile" in Config.LLM_MODELS
        assert "openai/gpt-oss-120b" in Config.LLM_MODELS
    
    def test_whisper_models_defined(self):
        """Test that Whisper models are defined."""
        assert Config.WHISPER_PRIMARY_MODEL == "whisper-large-v3"
        assert Config.WHISPER_FALLBACK_MODEL == "whisper-large-v3-turbo"
    
    def test_backup_configuration(self):
        """Test backup-related configuration."""
        assert Config.BACKUP_MAX_AGE_HOURS == 24
        assert Config.BACKUP_DIR is not None
    
    def test_recording_hotkeys(self):
        """Test voice recording hotkey configuration."""
        assert Config.RECORDING_HOTKEY == "F1"
        assert Config.EXIT_HOTKEY == "ESC"
    
    def test_audio_configuration(self):
        """Test audio settings."""
        assert Config.AUDIO_SAMPLE_RATE == 16000
        assert Config.AUDIO_CHANNELS == 1
    
    def test_character_list(self):
        """Test that all characters are defined."""
        assert "ironclad" in Config.CHARACTERS
        assert "silent" in Config.CHARACTERS
        assert "defect" in Config.CHARACTERS
        assert "watcher" in Config.CHARACTERS
        assert len(Config.CHARACTERS) == 4
    
    def test_card_files_mapping(self):
        """Test that card file mappings are correct."""
        assert "colorless" in Config.CARD_FILES
        assert "ironclad" in Config.CARD_FILES
        assert "silent" in Config.CARD_FILES
        assert "defect" in Config.CARD_FILES
        assert "watcher" in Config.CARD_FILES
    
    def test_relic_files_list(self):
        """Test that relic files are defined."""
        assert len(Config.RELIC_FILES) == 6
        assert any("boss" in f for f in Config.RELIC_FILES)
        assert any("common" in f for f in Config.RELIC_FILES)
        assert any("rare" in f for f in Config.RELIC_FILES)
    
    def test_create_directories(self):
        """Test that create_directories creates required folders."""
        Config.create_directories()
        
        # Verify directories exist
        assert Config.DATA_DIR.exists()
        assert Config.BACKUP_DIR.exists()
        assert Config.PROCESSED_DIR.exists()
        assert Config.LOGS_DIR.exists()
    
    def test_validation_with_missing_api_key(self, monkeypatch):
        """Test validation fails when API key is missing."""
        # Temporarily remove API key
        monkeypatch.setattr(Config, "GROQ_API_KEY", None)
        
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            Config.validate()
    
    def test_validation_with_missing_game_dir(self, monkeypatch):
        """Test validation fails when game directory doesn't exist."""
        # Temporarily set invalid path
        monkeypatch.setattr(Config, "GAME_SAVES_DIR", Path("/nonexistent/path"))
        
        with pytest.raises(ValueError, match="Game saves directory"):
            Config.validate()
    
    def test_llm_timeout_configured(self):
        """Test that LLM timeout is set."""
        assert Config.LLM_TIMEOUT == 3.0
        assert isinstance(Config.LLM_TIMEOUT, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
