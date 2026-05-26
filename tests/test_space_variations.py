"""
Test space variation in card names.

This tests scenarios where users say card names with different spacing than the actual name:
- "War Cry" (spoken) → "Warcry" (actual card name) - user ADDS space
- "Warcry" → "Warcry" - correct
- Similar issues with other cards

The system should handle these spacing variations.

NOTE: Most tests use mocks to avoid LLM API quota usage.
"""

import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.llm.name_corrector import NameCorrector


class TestSpaceVariationsLogic:
    """Test space variation handling logic WITHOUT LLM calls."""
    
    def test_prompt_includes_space_rules(self):
        """Test: Correction prompts include space variation rules."""
        corrector = NameCorrector()
        from src.knowledge.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        
        cards = kb.get_choosable_cards_for_character("ironclad")
        relics = kb.get_all_relics()
        
        prompt = corrector._build_correction_prompt("war cry", cards, relics)
        
        # Should include space variation instructions
        assert "space" in prompt.lower() or "spacing" in prompt.lower()
        assert "war cry" in prompt.lower()


@pytest.mark.integration
def test_warcry_integration():
    """
    Integration test: Verify 'war cry' matches 'Warcry' card, not 'War Paint' relic.
    
    This is the ONLY test making real LLM calls for space variation validation.
    Run with: pytest tests/test_space_variations.py::test_warcry_integration
    """
    corrector = NameCorrector()
    cards, relics = corrector.correct_names("war cry", "ironclad")
    
    # Should match "Warcry" card
    assert "Warcry" in cards, f"Expected 'Warcry' in cards: {cards}"
    
    # Should NOT match "War Paint" relic
    assert "War Paint" not in relics, f"Should not match War Paint relic: {relics}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
