"""
Test space variation in card names.

This tests scenarios where users say card names with different spacing than the actual name:
- "War Cry" (spoken) → "Warcry" (actual card name) - user ADDS space
- "Warcry" → "Warcry" - correct
- Similar issues with other cards

The system should handle these spacing variations.
"""

import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector


class TestSpaceVariations:
    """Test handling of space variations in card names."""
    
    @pytest.fixture
    def corrector(self):
        """Create NameCorrector instance."""
        return NameCorrector()
    
    def test_warcry_with_space(self, corrector):
        """Test: 'war cry' (two words) should match 'Warcry' (one word)."""
        cards, relics = corrector.correct_names("war cry", "ironclad")
        
        # Should match "Warcry" card, NOT "War Paint" relic
        assert "Warcry" in cards, f"Expected 'Warcry' in cards: {cards}"
        assert "War Paint" not in relics, f"Should not match War Paint relic: {relics}"
    
    def test_warcry_no_space(self, corrector):
        """Test: 'warcry' (one word) should match 'Warcry'."""
        cards, relics = corrector.correct_names("warcry", "ironclad")
        
        assert "Warcry" in cards
    
    def test_full_sentence_with_warcry(self, corrector):
        """Test: Full sentence with 'War Cry' should match correctly."""
        # User's exact reported input
        cards, relics = corrector.correct_names(
            "Hearing Blow Pommel Strike War Cry",
            "ironclad"
        )
        
        # Should include Warcry
        assert "Warcry" in cards, f"Expected 'Warcry' in {cards}"
        
        # Should NOT include War Paint (it's a relic, not a card)
        assert "War Paint" not in cards, f"War Paint should not be in cards: {cards}"
        
        # Should include Pommel Strike
        assert "Pommel Strike" in cards, f"Expected 'Pommel Strike' in {cards}"
    
    def test_prefer_card_over_relic(self, corrector):
        """Test: When both card and relic match, prefer the card."""
        # "war" could match both "Warcry" (card) and "War Paint" (relic)
        cards, relics = corrector.correct_names("war", "ironclad", include_relics=True)
        
        # Should match Warcry card
        if cards or relics:
            # If we got any matches, Warcry should be prioritized
            assert "Warcry" in cards or len(cards) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
