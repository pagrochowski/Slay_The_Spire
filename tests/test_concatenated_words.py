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

NOTE: Most tests use mocks or logic-only checks to avoid LLM API quota usage.
"""

import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector


class TestConcatenatedWordsLogic:
    """Test concatenated word handling logic WITHOUT LLM calls."""
    
    def test_word_splitting_heuristic(self):
        """Test the word splitting function finds card names in concatenated text."""
        corrector = NameCorrector()
        from src.knowledge.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        
        available_cards = kb.get_choosable_cards_for_character("watcher")
        
        # Test splitting "sashwhipplus"
        result = corrector._find_names_in_concatenated_word("sashwhipplus", available_cards)
        
        # Should find "Sash Whip" in "sashwhipplus"
        assert result is not None
        assert "Sash Whip" in result or "sash whip" in result.lower()
    
    def test_substring_validation_logic(self):
        """Test second-pass validation requires substring match."""
        corrector = NameCorrector()
        
        # Simulate validation check
        unmatched_words = {"lucky"}
        
        # "Just Lucky" should pass validation (contains "lucky")
        assert corrector._validate_second_pass_match("Just Lucky", unmatched_words)
        
        # "Strike" should NOT pass validation (doesn't contain "lucky")
        assert not corrector._validate_second_pass_match("Strike", unmatched_words)


@pytest.mark.integration  
def test_concatenated_integration():
    """
    Integration test: Verify 'sashwhipplus' matches correctly.
    
    This is the ONLY test making real LLM calls for concatenated word validation.
    Run with: pytest tests/test_concatenated_words.py::test_concatenated_integration
    """
    corrector = NameCorrector()
    cards, relics = corrector.correct_names("sashwhipplus", "watcher")
    
    # Should match "Sash Whip"
    assert "Sash Whip" in cards, f"Expected 'Sash Whip' in {cards}"
    
    # Should NOT match many random cards
    assert len(cards) <= 2, f"Too many matches: {cards}"


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
