"""Unit tests for save parser."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.core.save_parser import SaveParser


class TestSaveParser:
    """Test cases for the save parser."""
    
    @pytest.fixture
    def parser(self):
        """Create a SaveParser instance."""
        return SaveParser()
    
    @pytest.fixture
    def mock_save_data(self):
        """Mock save data that spireslayer would return (actual format)."""
        return {
            "name": "PlayerName",  # Player name, not character class
            "ascension_level": 3,
            "act_num": 1,
            "floor_num": 8,
            "current_health": 66,
            "max_health": 72,
            "gold": 117,
            "cards": [
                {"id": "Strike_P", "upgrades": 0},
                {"id": "Strike_P", "upgrades": 0},
                {"id": "Strike_P", "upgrades": 0},
                {"id": "Strike_P", "upgrades": 0},
                {"id": "Defend_P", "upgrades": 0},
                {"id": "Defend_P", "upgrades": 0},
                {"id": "Defend_P", "upgrades": 0},
                {"id": "Defend_P", "upgrades": 0},
                {"id": "Eruption", "upgrades": 0},
                {"id": "Vigilance", "upgrades": 1}  # Upgraded card
            ],
            "relics": [
                {"id": "PureWater"},
                {"id": "Lantern"}
            ],
            "potions": [
                {"id": "Regen Potion"},
                {"id": "Strength Potion"},
                {"id": ""}  # Empty potion slot
            ],
            "ruby_key": False,
            "emerald_key": False,
            "sapphire_key": False,
            "boss": "The Guardian",
            "path_taken": [],
            "room_phase": "COMBAT",
            "seed": 123456789
        }
    
    @pytest.fixture
    def temp_save_file(self, tmp_path):
        """Create a temporary mock save file."""
        save_file = tmp_path / "WATCHER.autosave"
        save_file.write_text("mock autosave data")
        return save_file
    
    def test_initialization(self, parser):
        """Test SaveParser initialization."""
        assert parser is not None
        assert parser.editor_class is None  # Lazy loading
    
    @patch('spireslayer.editor.Editor')
    def test_parse_save_file_success(self, mock_editor_class, parser, temp_save_file, mock_save_data):
        """Test successful save file parsing."""
        # Mock the spireslayer Editor
        mock_editor_instance = Mock()
        mock_editor_instance.decoded = mock_save_data
        mock_editor_class.return_value = mock_editor_instance
        
        # Import spireslayer (simulates successful import)
        with patch('spireslayer.editor.Editor', mock_editor_class):
            parser._import_spireslayer()
            
            # Parse the file
            result = parser.parse_save_file(temp_save_file)
            
            assert result is not None
            assert result == mock_save_data
            mock_editor_class.assert_called_once_with(autosave_path=str(temp_save_file))
    
    @patch('spireslayer.editor.Editor')
    def test_parse_save_file_empty_data(self, mock_editor_class, parser, temp_save_file):
        """Test parsing when save file has no data."""
        # Mock editor with empty data
        mock_editor_instance = Mock()
        mock_editor_instance.decoded = None
        mock_editor_class.return_value = mock_editor_instance
        
        with patch('spireslayer.editor.Editor', mock_editor_class):
            parser._import_spireslayer()
            result = parser.parse_save_file(temp_save_file)
            
            assert result is None
    
    @patch('spireslayer.editor.Editor')
    def test_parse_save_file_exception(self, mock_editor_class, parser, temp_save_file):
        """Test parsing when an exception occurs."""
        # Mock editor to raise exception
        mock_editor_class.side_effect = Exception("Parse error")
        
        with patch('spireslayer.editor.Editor', mock_editor_class):
            parser._import_spireslayer()
            result = parser.parse_save_file(temp_save_file)
            
            assert result is None
    
    def test_extract_run_data_success(self, parser, mock_save_data):
        """Test successful run data extraction."""
        run_data = parser.extract_run_data(mock_save_data, save_filename="WATCHER.autosave")
        
        assert run_data["character"] == "WATCHER"  # From filename
        assert run_data["ascension"] == 3
        assert run_data["act"] == 1
        assert run_data["floor"] == 8
        assert run_data["current_hp"] == 66
        assert run_data["max_hp"] == 72
        assert run_data["gold"] == 117
        assert len(run_data["deck"]) == 10
        assert "Vigilance+" in run_data["deck"]  # Upgraded card
        assert len(run_data["relics"]) == 2  # PureWater and Lantern
        assert len(run_data["potions"]) == 2  # 2 potions (empty slot excluded)
        assert run_data["boss"] == "The Guardian"
    
    def test_extract_run_data_missing_fields(self, parser):
        """Test extraction with missing fields."""
        minimal_data = {"name": "PlayerName"}
        
        run_data = parser.extract_run_data(minimal_data, save_filename="IRONCLAD.autosave")
        
        # Should use defaults for missing fields
        assert run_data["character"] == "IRONCLAD"  # From filename
        assert run_data["ascension"] == 0
        assert run_data["act"] == 1
        assert run_data["gold"] == 0

    def test_extract_run_data_bottled_relic_card(self, parser):
        """Test that bottled relics include the captured card from save metadata."""
        save_data = {
            "ascension_level": 4,
            "act_num": 1,
            "floor_num": 12,
            "cards": [{"id": "BowlingBash", "upgrades": 0}],
            "relics": [{"id": "BottledFlame"}],
            "potions": [],
            "boss": "The Guardian",
            "bottled_flame": "BowlingBash",
            "bottled_flame_upgrade": 0,
        }

        run_data = parser.extract_run_data(save_data, save_filename="WATCHER.autosave")

        assert "Bottled Flame [Bowling Bash]" in run_data["relics"]
    
    def test_extract_run_data_exception_handling(self, parser):
        """Test extraction with invalid data causing exception."""
        invalid_data = "not a dictionary"
        
        run_data = parser.extract_run_data(invalid_data)
        
        # Should return minimal default data
        assert run_data["character"] == "UNKNOWN"
        assert run_data["ascension"] == 0
        assert run_data["deck"] == []
    
    def test_save_to_json(self, parser, tmp_path):
        """Test saving run data to JSON."""
        run_data = {
            "character": "WATCHER",
            "ascension": 3,
            "deck": ["Strike", "Defend"]
        }
        
        json_path = tmp_path / "run_data.json"
        success = parser.save_to_json(run_data, json_path)
        
        assert success
        assert json_path.exists()
        
        # Verify content
        with open(json_path, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == run_data
    
    def test_save_to_json_creates_directories(self, parser, tmp_path):
        """Test that save_to_json creates parent directories."""
        json_path = tmp_path / "subdir" / "nested" / "run_data.json"
        run_data = {"test": "data"}
        
        success = parser.save_to_json(run_data, json_path)
        
        assert success
        assert json_path.exists()
        assert json_path.parent.exists()
    
    @patch('spireslayer.editor.Editor')
    def test_parse_and_extract_workflow(self, mock_editor_class, parser, temp_save_file, mock_save_data, tmp_path):
        """Test complete parse and extract workflow."""
        # Mock the editor
        mock_editor_instance = Mock()
        mock_editor_instance.decoded = mock_save_data
        mock_editor_class.return_value = mock_editor_instance
        
        with patch('spireslayer.editor.Editor', mock_editor_class):
            parser._import_spireslayer()
            
            # Run workflow
            json_path = tmp_path / "output.json"
            run_data = parser.parse_and_extract(temp_save_file, json_path)
            
            assert run_data is not None
            assert run_data["character"] == temp_save_file.stem.upper()
            assert json_path.exists()
    
    @patch('spireslayer.editor.Editor')
    def test_parse_and_extract_no_json_output(self, mock_editor_class, parser, temp_save_file, mock_save_data):
        """Test parse and extract without JSON output."""
        mock_editor_instance = Mock()
        mock_editor_instance.decoded = mock_save_data
        mock_editor_class.return_value = mock_editor_instance
        
        with patch('spireslayer.editor.Editor', mock_editor_class):
            parser._import_spireslayer()
            
            # Run workflow without JSON path
            run_data = parser.parse_and_extract(temp_save_file)
            
            assert run_data is not None
            assert run_data["character"] == temp_save_file.stem.upper()
        assert run_data["character"] == "WATCHER"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

