"""Unit tests for run summary generator."""

import pytest
from pathlib import Path
from src.summary.summary_generator import RunSummaryGenerator
from src.knowledge.knowledge_base import KnowledgeBase


class TestRunSummaryGenerator:
    """Test cases for the run summary generator."""
    
    @pytest.fixture
    def kb(self):
        """Create a KnowledgeBase instance."""
        return KnowledgeBase()
    
    @pytest.fixture
    def generator(self, kb):
        """Create a RunSummaryGenerator instance."""
        return RunSummaryGenerator(knowledge_base=kb)
    
    @pytest.fixture
    def mock_run_data(self):
        """Mock run data for testing."""
        return {
            "character": "WATCHER",
            "ascension": 3,
            "act": 1,
            "floor": 8,
            "current_hp": 66,
            "max_hp": 72,
            "gold": 117,
            "deck": [
                "Strike_P", "Strike_P", "Strike_P", "Strike_P",
                "Defend_P", "Defend_P", "Defend_P", "Defend_P",
                "Eruption", "Vigilance+", "CrushJoints"
            ],
            "relics": ["PureWater", "Akabeko"],
            "potions": ["Regen Potion", "Strength Potion"],
            "has_ruby_key": False,
            "has_emerald_key": False,
            "has_sapphire_key": True,
            "boss": "The Guardian"
        }
    
    def test_initialization(self, generator):
        """Test RunSummaryGenerator initialization."""
        assert generator is not None
        assert generator.kb is not None
    
    def test_format_card_with_details_basic(self, generator):
        """Test formatting a basic card."""
        formatted = generator._format_card_with_details("Eruption")
        
        assert "Eruption" in formatted
        assert "[" in formatted  # Cost bracket
        assert "(" in formatted  # Type parenthesis
        assert ":" in formatted  # Description separator
    
    def test_format_card_with_details_upgraded(self, generator):
        """Test formatting an upgraded card."""
        formatted = generator._format_card_with_details("Vigilance+")
        
        assert "Vigilance+" in formatted
        assert "[" in formatted
        # Upgraded cost or description should be used
    
    def test_format_deck_cards_with_multipliers(self, generator):
        """Test deck formatting with multipliers for duplicates."""
        deck = ["Strike_P", "Strike_P", "Strike_P", "Defend_P", "Eruption"]
        formatted = generator._format_deck_cards(deck)
        
        # Should have fewer lines than cards (due to multipliers)
        assert len(formatted) < len(deck)
        
        # Should contain multipliers
        formatted_text = "\n".join(formatted)
        assert "3x" in formatted_text or "Strike_P" in formatted_text
    
    def test_format_deck_cards_no_duplicates(self, generator):
        """Test deck formatting with all unique cards."""
        deck = ["Eruption", "Vigilance", "CrushJoints"]
        formatted = generator._format_deck_cards(deck)
        
        # Should have same number of lines as cards
        assert len(formatted) == len(deck)
        
        # Should NOT have multipliers
        formatted_text = "\n".join(formatted)
        assert "2x" not in formatted_text
        assert "3x" not in formatted_text
    
    def test_format_relic_with_description(self, generator):
        """Test formatting a relic."""
        formatted = generator._format_relic_with_description("Akabeko")
        
        assert "Akabeko" in formatted
        assert ":" in formatted
        # Should have description
        assert len(formatted) > len("Akabeko: ")
    
    def test_format_relic_unknown(self, generator):
        """Test formatting an unknown relic."""
        formatted = generator._format_relic_with_description("UnknownRelic123")
        
        # Should still format gracefully
        assert "UnknownRelic123" in formatted
    
    def test_format_potion_with_description(self, generator):
        """Test formatting a potion."""
        formatted = generator._format_potion_with_description("Regen Potion")
        
        assert "Regen" in formatted or "Potion" in formatted
        assert ":" in formatted
    
    def test_generate_summary_structure(self, generator, mock_run_data):
        """Test that generated summary has correct structure."""
        summary = generator.generate_summary(mock_run_data)
        
        # Check for required sections
        assert "# Slay the Spire Run Summary" in summary
        assert "## Run Information" in summary
        assert "## Current Status" in summary
        assert "## Deck" in summary
        assert "## Relics" in summary
        assert "## Potions" in summary
        assert "## Keys" in summary
        assert "## Boss & Elites" in summary
        assert "**Current choice:**" in summary
        assert "- SKIP?" in summary
    
    def test_generate_summary_character_info(self, generator, mock_run_data):
        """Test that character info is included."""
        summary = generator.generate_summary(mock_run_data)
        
        assert "WATCHER" in summary
        assert "Ascension**: 3" in summary
        assert "Act**: 1" in summary
    
    def test_generate_summary_hp_gold(self, generator, mock_run_data):
        """Test that HP and gold are included."""
        summary = generator.generate_summary(mock_run_data)
        
        assert "66/72" in summary  # HP
        assert "117" in summary    # Gold
    
    def test_generate_summary_deck_count(self, generator, mock_run_data):
        """Test that deck count is accurate."""
        summary = generator.generate_summary(mock_run_data)
        
        deck_size = len(mock_run_data["deck"])
        assert f"## Deck ({deck_size} cards)" in summary
    
    def test_generate_summary_keys(self, generator, mock_run_data):
        """Test that keys are formatted correctly."""
        summary = generator.generate_summary(mock_run_data)
        
        # Sapphire key is true, others false
        assert "Ruby: ✗" in summary
        assert "Emerald: ✗" in summary
        assert "Sapphire: ✓" in summary
    
    def test_generate_summary_boss(self, generator, mock_run_data):
        """Test that boss name is included."""
        summary = generator.generate_summary(mock_run_data)
        
        assert "The Guardian" in summary
    
    def test_generate_summary_write_to_file(self, generator, mock_run_data, tmp_path):
        """Test writing summary to file."""
        output_path = tmp_path / "test_summary.md"
        
        summary = generator.generate_summary(mock_run_data, output_path)
        
        # File should exist
        assert output_path.exists()
        
        # Content should match
        file_content = output_path.read_text(encoding='utf-8')
        assert file_content == summary
    
    def test_generate_summary_preserve_choice(self, generator, mock_run_data, tmp_path):
        """Test preserving existing choice section."""
        output_path = tmp_path / "test_summary.md"
        
        # Create initial summary with custom choice
        initial_content = """# Summary

**Current choice:**
- Custom Card 1
- Custom Card 2
- SKIP?

---
"""
        output_path.write_text(initial_content, encoding='utf-8')
        
        # Generate new summary with preserve_choice=True
        summary = generator.generate_summary(mock_run_data, output_path, preserve_choice=True)
        
        # Should preserve the custom choice
        assert "Custom Card 1" in summary
        assert "Custom Card 2" in summary
    
    def test_generate_summary_no_preserve_choice(self, generator, mock_run_data, tmp_path):
        """Test not preserving existing choice section."""
        output_path = tmp_path / "test_summary.md"
        
        # Create initial summary with custom choice
        initial_content = """# Summary

**Current choice:**
- Custom Card 1
- SKIP?

---
"""
        output_path.write_text(initial_content, encoding='utf-8')
        
        # Generate new summary with preserve_choice=False
        summary = generator.generate_summary(mock_run_data, output_path, preserve_choice=False)
        
        # Should NOT preserve the custom choice
        # Should only have default SKIP?
        assert "Custom Card 1" not in summary
        assert "**Current choice:**" in summary
        assert "- SKIP?" in summary
    
    def test_generate_summary_empty_deck(self, generator):
        """Test generating summary with empty deck."""
        run_data = {
            "character": "IRONCLAD",
            "ascension": 0,
            "act": 1,
            "floor": 0,
            "current_hp": 80,
            "max_hp": 80,
            "gold": 0,
            "deck": [],
            "relics": [],
            "potions": [],
            "has_ruby_key": False,
            "has_emerald_key": False,
            "has_sapphire_key": False,
            "boss": "Unknown"
        }
        
        summary = generator.generate_summary(run_data)
        
        assert "## Deck (0 cards)" in summary
        assert "No cards" in summary or "## Relics" in summary  # Should handle empty gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
