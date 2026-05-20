"""Unit tests for choice updater."""

import pytest
from pathlib import Path
from src.summary.choice_updater import ChoiceUpdater


class TestChoiceUpdater:
    """Test cases for the choice updater."""
    
    @pytest.fixture
    def updater(self):
        """Create a ChoiceUpdater instance."""
        return ChoiceUpdater()
    
    @pytest.fixture
    def mock_summary(self, tmp_path):
        """Create a mock summary file."""
        summary_path = tmp_path / "Run_Summary.md"
        content = """# Slay the Spire Run Summary

## Run Information
- **Character**: WATCHER

## Deck (5 cards)
- Strike
- Defend

**Current choice:**
- Old Card 1
- Old Card 2
- SKIP?

---
"""
        summary_path.write_text(content, encoding='utf-8')
        return summary_path
    
    def test_initialization(self, updater):
        """Test ChoiceUpdater initialization."""
        assert updater is not None
    
    def test_format_choice_section(self, updater):
        """Test formatting choice section."""
        choices = ["Card A", "Card B", "Card C"]
        formatted = updater._format_choice_section(choices)
        
        assert "**Current choice:**" in formatted
        assert "- Card A" in formatted
        assert "- Card B" in formatted
        assert "- Card C" in formatted
        assert "- SKIP?" in formatted
        assert formatted.endswith("- SKIP?")
    
    def test_format_choice_section_empty(self, updater):
        """Test formatting with no choices."""
        formatted = updater._format_choice_section([])
        
        assert "**Current choice:**" in formatted
        assert "- SKIP?" in formatted
        # Should only have header and SKIP
        assert formatted.count('\n') == 1  # One newline between header and SKIP
    
    def test_update_choice_section_replace(self, updater, mock_summary):
        """Test replacing choice section."""
        new_choices = ["New Card 1", "New Card 2"]
        
        success = updater.update_choice_section(mock_summary, new_choices)
        assert success
        
        # Read updated content
        content = mock_summary.read_text()
        
        # Should have new choices
        assert "New Card 1" in content
        assert "New Card 2" in content
        assert "SKIP?" in content
        
        # Should NOT have old choices
        assert "Old Card 1" not in content
        assert "Old Card 2" not in content
    
    def test_update_choice_section_preserves_other_sections(self, updater, mock_summary):
        """Test that updating choice doesn't affect other sections."""
        original_content = mock_summary.read_text()
        
        new_choices = ["New Card"]
        updater.update_choice_section(mock_summary, new_choices)
        
        updated_content = mock_summary.read_text()
        
        # Other sections should be preserved
        assert "# Slay the Spire Run Summary" in updated_content
        assert "## Run Information" in updated_content
        assert "## Deck (5 cards)" in updated_content
        assert "- Strike" in updated_content
    
    def test_update_choice_section_always_ends_with_skip(self, updater, mock_summary):
        """Test that choice section always ends with SKIP?."""
        choices = ["Card 1", "Card 2", "Card 3"]
        
        updater.update_choice_section(mock_summary, choices)
        
        content = mock_summary.read_text()
        choice_start = content.find("**Current choice:**")
        choice_end = content.find("\n---", choice_start)
        choice_section = content[choice_start:choice_end]
        
        # Should end with SKIP?
        assert choice_section.strip().endswith("- SKIP?")
    
    def test_update_choice_section_nonexistent_file(self, updater, tmp_path):
        """Test updating a file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.md"
        
        success = updater.update_choice_section(nonexistent, ["Card"])
        
        # Should fail gracefully
        assert not success
    
    def test_update_choice_section_no_existing_section(self, updater, tmp_path):
        """Test updating file that has no choice section."""
        summary_path = tmp_path / "summary.md"
        summary_path.write_text("# Summary\n\nSome content\n")
        
        new_choices = ["Card 1"]
        success = updater.update_choice_section(summary_path, new_choices)
        
        assert success
        
        # Should have added choice section
        content = summary_path.read_text()
        assert "**Current choice:**" in content
        assert "- Card 1" in content
        assert "- SKIP?" in content
    
    def test_extract_existing_choices(self, updater, mock_summary):
        """Test extracting existing choices."""
        existing = updater._extract_existing_choices(mock_summary)
        
        assert len(existing) == 2
        assert "Old Card 1" in existing
        assert "Old Card 2" in existing
        assert "SKIP?" not in existing  # SKIP should be filtered out
    
    def test_extract_existing_choices_empty(self, updater, tmp_path):
        """Test extracting from file with no choices."""
        summary_path = tmp_path / "summary.md"
        summary_path.write_text("# Summary\n")
        
        existing = updater._extract_existing_choices(summary_path)
        
        assert existing == []
    
    def test_add_choices_replace_mode(self, updater, mock_summary):
        """Test adding choices in replace mode."""
        new_choices = ["Replace Card"]
        
        success = updater.add_choices_to_summary(mock_summary, new_choices, append=False)
        assert success
        
        content = mock_summary.read_text()
        assert "Replace Card" in content
        assert "Old Card 1" not in content
    
    def test_add_choices_append_mode(self, updater, mock_summary):
        """Test adding choices in append mode."""
        new_choices = ["Append Card"]
        
        success = updater.add_choices_to_summary(mock_summary, new_choices, append=True)
        assert success
        
        content = mock_summary.read_text()
        
        # Should have both old and new
        assert "Old Card 1" in content
        assert "Old Card 2" in content
        assert "Append Card" in content
    
    def test_add_choices_append_deduplicates(self, updater, mock_summary):
        """Test that appending deduplicates choices."""
        # Add a choice that already exists
        new_choices = ["Old Card 1", "New Unique Card"]
        
        updater.add_choices_to_summary(mock_summary, new_choices, append=True)
        
        content = mock_summary.read_text()
        
        # Old Card 1 should only appear once
        assert content.count("Old Card 1") == 1
        assert "New Unique Card" in content
    
    def test_multiple_updates(self, updater, mock_summary):
        """Test multiple sequential updates."""
        # First update
        updater.update_choice_section(mock_summary, ["Choice 1"])
        content1 = mock_summary.read_text()
        assert "Choice 1" in content1
        
        # Second update
        updater.update_choice_section(mock_summary, ["Choice 2"])
        content2 = mock_summary.read_text()
        assert "Choice 2" in content2
        assert "Choice 1" not in content2  # Should be replaced
    
    def test_update_with_long_descriptions(self, updater, mock_summary):
        """Test updating with choices that have long descriptions."""
        long_choice = (
            "Battle Hymn [1] (Power): At the start of each turn, "
            "add a *Smite into your hand. This is a very long description."
        )
        
        success = updater.update_choice_section(mock_summary, [long_choice])
        assert success
        
        content = mock_summary.read_text()
        assert long_choice in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
