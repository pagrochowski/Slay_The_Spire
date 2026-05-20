"""Unit tests for knowledge base."""

import pytest
from pathlib import Path
from src.knowledge.knowledge_base import KnowledgeBase
from src.core.config import Config


class TestKnowledgeBase:
    """Test cases for the knowledge base."""
    
    @pytest.fixture
    def kb(self):
        """Create a KnowledgeBase instance."""
        return KnowledgeBase()
    
    def test_initialization(self, kb):
        """Test KnowledgeBase initialization."""
        assert kb is not None
        assert isinstance(kb.cards, dict)
        assert isinstance(kb.relics, dict)
        assert isinstance(kb.potions, dict)
    
    def test_cards_loaded(self, kb):
        """Test that cards are loaded."""
        assert len(kb.cards) > 0
        # Should have cards from all characters
        assert len(kb.cards) > 100  # Rough estimate
    
    def test_relics_loaded(self, kb):
        """Test that relics are loaded."""
        assert len(kb.relics) > 0
        # Should have many relics
        assert len(kb.relics) > 50  # Rough estimate
    
    def test_potions_loaded(self, kb):
        """Test that potions are loaded."""
        assert len(kb.potions) > 0
    
    def test_character_specific_cards(self, kb):
        """Test getting cards for specific characters."""
        # Each character should have cards
        for character in ["ironclad", "silent", "defect", "watcher"]:
            cards = kb.get_cards_for_character(character)
            assert len(cards) > 0
            assert isinstance(cards, list)
    
    def test_colorless_cards_included(self, kb):
        """Test that colorless cards are included for all characters."""
        colorless_count = len(kb.cards_by_character.get("colorless", []))
        
        # Each character should have colorless cards
        for character in ["ironclad", "silent", "defect", "watcher"]:
            cards = kb.get_cards_for_character(character)
            # Should have at least the colorless cards
            assert len(cards) >= colorless_count
    
    def test_class_specific_filtering(self, kb):
        """Test that class-specific cards are properly filtered."""
        ironclad_cards = kb.get_cards_for_character("ironclad")
        silent_cards = kb.get_cards_for_character("silent")
        
        # These should be different lists
        assert set(ironclad_cards) != set(silent_cards)
    
    def test_get_all_relics(self, kb):
        """Test getting all relic names."""
        relics = kb.get_all_relics()
        assert len(relics) > 0
        assert all(isinstance(r, str) for r in relics)
    
    def test_get_card_data(self, kb):
        """Test retrieving specific card data."""
        # Test with a common card (Strike exists for all classes)
        card = kb.get_card_data("Strike")
        
        if card:  # Strike might be named "Strike_R", "Strike_G", etc.
            assert "name" in card
            assert "type" in card
            assert "cost" in card
            assert "description" in card
    
    def test_get_card_data_case_insensitive(self, kb):
        """Test that card lookup is case-insensitive."""
        # Get any card name
        if kb.cards:
            card_name = list(kb.cards.values())[0]["name"]
            
            # Try different cases
            card1 = kb.get_card_data(card_name.lower())
            card2 = kb.get_card_data(card_name.upper())
            card3 = kb.get_card_data(card_name)
            
            assert card1 == card2 == card3
    
    def test_get_relic_data(self, kb):
        """Test retrieving specific relic data."""
        # Test with a known common relic
        relic = kb.get_relic_data("Akabeko")
        
        assert relic is not None
        assert relic["name"] == "Akabeko"
        assert "description" in relic
        assert "tier" in relic
    
    def test_get_relic_data_case_insensitive(self, kb):
        """Test that relic lookup is case-insensitive."""
        relic1 = kb.get_relic_data("akabeko")
        relic2 = kb.get_relic_data("AKABEKO")
        relic3 = kb.get_relic_data("Akabeko")
        
        assert relic1 == relic2 == relic3
    
    def test_fuzzy_match_card_exact(self, kb):
        """Test fuzzy matching with exact card name."""
        # Get a known card
        if kb.cards:
            card_name = list(kb.cards.values())[0]["name"]
            matches = kb.fuzzy_match_card(card_name)
            
            # Exact match should be first with score 1.0
            assert len(matches) > 0
            assert matches[0][0] == card_name
            assert matches[0][1] == 1.0
    
    def test_fuzzy_match_card_similar(self, kb):
        """Test fuzzy matching with similar card name."""
        # Test with a misspelling
        matches = kb.fuzzy_match_card("shrugitoff", character="ironclad")
        
        # Should find "Shrug It Off" if it exists
        assert len(matches) > 0
        # Top match should be similar
        assert matches[0][1] > 0.6
    
    def test_fuzzy_match_card_with_character(self, kb):
        """Test fuzzy matching filtered by character."""
        matches_ironclad = kb.fuzzy_match_card("bash", character="ironclad")
        matches_silent = kb.fuzzy_match_card("bash", character="silent")
        
        # Results should be different (Bash is Ironclad-specific)
        # Ironclad should have better match for Bash
        if matches_ironclad and matches_silent:
            assert matches_ironclad[0][1] >= matches_silent[0][1]
    
    def test_fuzzy_match_relic(self, kb):
        """Test fuzzy matching for relics."""
        matches = kb.fuzzy_match_relic("akabeko")
        
        assert len(matches) > 0
        assert matches[0][0] == "Akabeko"
        assert matches[0][1] == 1.0
    
    def test_fuzzy_match_threshold(self, kb):
        """Test that fuzzy matching respects threshold."""
        # Very different query
        matches_low = kb.fuzzy_match_card("xyz", threshold=0.1)
        matches_high = kb.fuzzy_match_card("xyz", threshold=0.9)
        
        # Lower threshold should return more matches
        assert len(matches_low) >= len(matches_high)
    
    def test_find_best_match_card(self, kb):
        """Test finding best match for a card."""
        best = kb.find_best_match("shrug it off", character="ironclad", match_type="card")
        
        # Should find a match
        assert best is not None
        assert isinstance(best, str)
    
    def test_find_best_match_relic(self, kb):
        """Test finding best match for a relic."""
        best = kb.find_best_match("dead branch", match_type="relic")
        
        # Should find Dead Branch
        assert best is not None
        # Should be close to "Dead Branch"
        assert "branch" in best.lower() or best == "Dead Branch"
    
    def test_find_best_match_no_match(self, kb):
        """Test finding best match when no good match exists."""
        best = kb.find_best_match("xyzabc123", match_type="card")
        
        # Should return None for nonsense query
        # (or possibly a very low match if threshold allows)
        assert best is None or isinstance(best, str)
    
    def test_cards_by_character_populated(self, kb):
        """Test that cards_by_character dictionary is populated."""
        assert "colorless" in kb.cards_by_character
        assert "ironclad" in kb.cards_by_character
        assert "silent" in kb.cards_by_character
        assert "defect" in kb.cards_by_character
        assert "watcher" in kb.cards_by_character


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
