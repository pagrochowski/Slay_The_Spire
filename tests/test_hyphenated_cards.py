"""
Tests for hyphenated card name matching (e.g., "Multi-Cast").

Ensures that when word splitting converts "multicast" → "Multi-Cast",
the fuzzy fallback doesn't incorrectly match "multicast" to similar
cards like "Dualcast".
"""

import pytest
from src.llm.name_corrector import NameCorrector


class TestHyphenatedCardMatching:
    """Test matching of hyphenated card names like 'Multi-Cast'."""
    
    def test_hyphenated_normalization_logic(self):
        """
        Test that _get_unmatched_words() correctly normalizes hyphenated names.
        
        When "Multi-Cast" is matched, the word "multicast" should be
        considered matched (not unmatched).
        """
        nc = NameCorrector()
        
        # Simulate: word splitting changed "multicast" → "Multi-Cast" in text
        transcribed_text = "Hologram Recycle Multi-Cast"
        matched_cards = ["Hologram", "Recycle", "Multi-Cast"]
        matched_relics = []
        
        unmatched = nc._get_unmatched_words(transcribed_text, matched_cards, matched_relics)
        
        # Should be empty - all words matched (including "multicast" → "Multi-Cast")
        assert unmatched == set(), (
            f"Expected no unmatched words, but got: {unmatched}. "
            "The word 'multicast' should be recognized as matching 'Multi-Cast'."
        )
    
    @pytest.mark.integration
    def test_multicast_doesnt_match_dualcast(self):
        """
        Integration test: "hologram recycle multicast" should match exactly 3 cards.
        
        Before the fix, this matched 4 cards:
        - Hologram ✓
        - Recycle ✓  
        - Multi-Cast ✓ (from word splitting)
        - Dualcast ✗ (incorrectly matched by fuzzy fallback)
        
        After the fix, fuzzy fallback correctly recognizes "multicast" is already
        matched to "Multi-Cast" and doesn't try to match it again to "Dualcast".
        """
        nc = NameCorrector()
        
        cards, relics = nc.correct_names("hologram recycle multicast", character="defect")
        
        assert len(cards) == 3, (
            f"Expected exactly 3 cards, but got {len(cards)}: {cards}. "
            "Should match: Hologram, Recycle, Multi-Cast (NOT Dualcast)."
        )
        assert "Hologram" in cards
        assert "Recycle" in cards
        assert "Multi-Cast" in cards
        assert "Dualcast" not in cards, "Dualcast should NOT be matched!"
    
    @pytest.mark.integration
    def test_other_hyphenated_cards(self):
        """
        Test other hyphenated cards work correctly.
        
        Examples: Follow-Up, Well-Laid Plans, etc.
        """
        nc = NameCorrector()
        
        # Test "Follow-Up" (Watcher card)
        cards, relics = nc.correct_names("followup", character="watcher")
        
        assert len(cards) == 1, f"Expected 1 card for 'followup', got {len(cards)}: {cards}"
        assert "Follow-Up" in cards
        
        # Test "Well-Laid Plans" (Silent card)
        cards, relics = nc.correct_names("welllaidplans", character="silent")
        
        assert len(cards) == 1, f"Expected 1 card for 'welllaidplans', got {len(cards)}: {cards}"
        assert "Well-Laid Plans" in cards
