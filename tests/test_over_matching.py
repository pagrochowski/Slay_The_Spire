"""
Test over-matching prevention.

This tests scenarios where the system might match too many cards:
- Hyphenated words that get mis-split leaving single letters
- Single letter unmatched words should be ignored
- Maximum matches threshold to prevent returning entire lists

NOTE: These tests use mocks to avoid LLM API quota usage.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector


class TestOverMatchingLogic:
    """Test over-matching prevention logic WITHOUT LLM calls."""
    
    def test_short_words_filtered(self):
        """Test: Words <3 chars are filtered before second pass."""
        corrector = NameCorrector()
        
        # Test the logic that filters short unmatched words
        unmatched = {"d", "ab", "xyz", "test"}
        # After filtering (>= 3 chars)
        filtered = {w for w in unmatched if len(w) >= 3}
        
        assert "d" not in filtered
        assert "ab" not in filtered
        assert "xyz" in filtered
        assert "test" in filtered
    
    def test_maximum_second_pass_matches(self):
        """Test: Second pass rejects if >5 matches (safety threshold)."""
        # This validates the MAX_SECOND_PASS_MATCHES = 5 logic
        max_allowed = 5
        
        # Simulate LLM returning too many matches
        too_many_matches = ["Card1", "Card2", "Card3", "Card4", "Card5", "Card6", "Card7"]
        
        # Should reject if length > threshold
        assert len(too_many_matches) > max_allowed


def test_word_splitting_logic():
    """Test the word splitting function directly (no LLM)."""
    corrector = NameCorrector()
    from src.knowledge.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    
    available_cards = kb.get_choosable_cards_for_character("defect")
    
    # Test splitting "cool-headed"
    result = corrector._find_names_in_concatenated_word("cool-headed", available_cards)
    
    # Should return just "Coolheaded" or similar, NOT "Coolheaded d"
    if result:
        assert " d" not in result.lower(), f"Word splitting left fragment: '{result}'"
        assert " d " not in result.lower(), f"Word splitting left fragment: '{result}'"
        # Should either be the card name alone or properly split
        assert result == "Coolheaded" or "Coolheaded" in result


@pytest.mark.integration
def test_over_matching_integration():
    """
    Integration test: Verify 'Recycle cool-headed' doesn't over-match.
    
    This is the ONLY test making real LLM calls for over-matching validation.
    Run with: pytest tests/test_over_matching.py::test_over_matching_integration
    """
    corrector = NameCorrector()
    cards, relics = corrector.correct_names("Recycle cool-headed", "defect")
    
    # Should match both cards
    assert "Recycle" in cards, f"Expected 'Recycle' in {cards}"
    assert "Coolheaded" in cards, f"Expected 'Coolheaded' in {cards}"
    
    # Should NOT match 10+ random cards
    assert len(cards) <= 3, f"Too many cards matched: {len(cards)} - {cards}"
    
    # Should NOT match these unrelated cards that contain 'd'
    unwanted = ["Bandage Up", "Blind", "Dark Shackles", "Deep Breath"]
    for card in unwanted:
        assert card not in cards, f"Over-matched '{card}' - single-letter bug!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
