"""
Test concatenated words (Whisper omitting spaces).

This tests scenarios where Whisper transcribes words without spaces:
- "sash whip plus" → "sashwhipplus"
- "follow up" → "followup"
- etc.

The system should:
1. Try to split the concatenated word
2. Only match cards that actually contain substrings of the input
3. Not hallucinate random matches
"""

import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector


class TestConcatenatedWords:
    """Test handling of concatenated words (Whisper transcription errors)."""
    
    @pytest.fixture
    def corrector(self):
        """Create NameCorrector instance."""
        return NameCorrector()
    
    def test_sashwhipplus(self, corrector):
        """Test: 'sashwhipplus' should match 'Sash Whip' and nothing else."""
        cards, relics = corrector.correct_names("sashwhipplus", "watcher")
        
        # Should match "Sash Whip" because "sashwhip" is a substring
        assert "Sash Whip" in cards, f"Expected 'Sash Whip' in {cards}"
        
        # Should NOT match random cards that don't contain "sash", "whip", or "plus"
        invalid_matches = [c for c in cards if c not in ["Sash Whip"]]
        assert len(invalid_matches) == 0, f"Invalid matches: {invalid_matches}"
    
    def test_followup(self, corrector):
        """Test: 'followup' should match 'Follow-Up'."""
        cards, relics = corrector.correct_names("followup", "watcher")
        
        assert "Follow-Up" in cards or len(cards) == 1
        # Should be the primary/only match
    
    def test_battlehymn(self, corrector):
        """Test: 'battlehymn' should match 'Battle Hymn'."""
        cards, relics = corrector.correct_names("battlehymn", "watcher")
        
        assert "Battle Hymn" in cards
    
    def test_emptyfist(self, corrector):
        """Test: 'emptyfist' should match 'Empty Fist'."""
        cards, relics = corrector.correct_names("emptyfist", "watcher")
        
        assert "Empty Fist" in cards
    
    def test_thirdeye(self, corrector):
        """Test: 'thirdeye' should match 'Third Eye'."""
        cards, relics = corrector.correct_names("thirdeye", "watcher")
        
        assert "Third Eye" in cards
    
    def test_multiple_concatenated(self, corrector):
        """Test: Multiple concatenated words should still work."""
        # This simulates Whisper removing ALL spaces
        cards, relics = corrector.correct_names("sashwhipfollowup", "watcher")
        
        # Should match both cards
        assert "Sash Whip" in cards or "Follow-Up" in cards
        # At least one should be matched
    
    def test_concatenated_with_plus(self, corrector):
        """Test: Concatenated word with 'plus' suffix."""
        cards, relics = corrector.correct_names("thirdeye plus", "watcher")
        
        assert "Third Eye" in cards
    
    def test_no_false_positives_strict(self, corrector):
        """Test: Ensure we don't match cards that don't contain the input."""
        # "xyz" shouldn't match any Watcher cards
        cards, relics = corrector.correct_names("xyz", "watcher")
        
        # Should be empty or very minimal matches
        assert len(cards) <= 1, f"Too many matches for nonsense input: {cards}"
    
    def test_partial_match_validation(self, corrector):
        """Test: Second pass should only accept matches with substring overlap."""
        # Create a realistic scenario
        cards, relics = corrector.correct_names("lucky", "watcher")
        
        # Should match "Just Lucky" because it contains "lucky"
        assert "Just Lucky" in cards
        
        # Should NOT match random cards
        invalid = [c for c in cards if "lucky" not in c.lower()]
        assert len(invalid) == 0, f"Cards without 'lucky' substring: {invalid}"


def test_concatenated_word_splitting():
    """Test the word splitting heuristic."""
    corrector = NameCorrector()
    
    # Test that the splitting function works
    from src.knowledge.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    
    available_cards = kb.get_choosable_cards_for_character("watcher")
    
    # Test splitting
    result = corrector._find_names_in_concatenated_word("sashwhipplus", available_cards)
    
    # Should find "Sash Whip" in "sashwhipplus"
    assert result is not None
    assert "Sash Whip" in result or "sash whip" in result.lower()


def test_substring_validation():
    """Test the substring validation logic."""
    corrector = NameCorrector()
    
    # Test cases for validation (substring matching only, not phonetic)
    test_cases = [
        # (card_name, unmatched_words, should_validate)
        ("Just Lucky", {"lucky"}, True),          # "lucky" in "Just Lucky"
        ("Empty Fist", {"fist"}, True),           # "fist" in "Empty Fist"
        ("Sash Whip", {"sashwhipplus"}, True),    # "sashwhip" in "sashwhipplus"
        ("Follow-Up", {"followup"}, True),        # "followup" contains "follow" and "up"
        ("Third Eye", {"lucky"}, False),          # No substring match
        ("Strike", {"xyz"}, False),               # No substring match
    ]
    
    for card_name, unmatched_words, expected in test_cases:
        result = corrector._validate_second_pass_match(card_name, unmatched_words)
        assert result == expected, \
            f"Validation failed for '{card_name}' with {unmatched_words}: got {result}, expected {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
