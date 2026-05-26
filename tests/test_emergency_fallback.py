"""
Tests for emergency fuzzy fallback when LLM fails.

When all LLM models fail (timeouts, rate limits), the system should
fall back to fuzzy matching to still provide some results.
"""

import pytest
from unittest.mock import patch
from src.llm.name_corrector import NameCorrector


class TestEmergencyFallback:
    """Test emergency fuzzy fallback when LLM completely fails."""
    
    def test_emergency_fallback_finds_cards(self):
        """
        Test that emergency fallback works when all LLMs fail.
        
        Simulates all LLM models timing out/failing, then verifies
        that fuzzy matching still finds cards.
        """
        nc = NameCorrector()
        
        # Mock LLM to always fail (simulating API timeout/rate limit)
        with patch.object(nc, '_try_models_with_fallback', return_value=None):
            cards, relics = nc.correct_names(
                "steam barrier ball lightning",
                character="defect"
            )
        
        # Should find cards via emergency fuzzy fallback
        assert len(cards) >= 2, (
            f"Emergency fallback should find at least 2 cards, but got {len(cards)}: {cards}"
        )
        assert "Steam Barrier" in cards, "Should find 'Steam Barrier' via fuzzy matching"
        assert "Ball Lightning" in cards, "Should find 'Ball Lightning' via fuzzy matching"
    
    def test_emergency_fallback_two_word_combos(self):
        """
        Test that emergency fallback tries two-word combinations.
        
        When individual words don't score high enough, trying pairs
        like "steam barrier" should match "Steam Barrier".
        """
        nc = NameCorrector()
        
        # Mock LLM to fail
        with patch.object(nc, '_try_models_with_fallback', return_value=None):
            cards, relics = nc.correct_names(
                "steam barrier",
                character="defect"
            )
        
        assert "Steam Barrier" in cards, (
            "Two-word combo 'steam barrier' should match 'Steam Barrier'"
        )
    
    @pytest.mark.integration
    def test_normal_path_doesnt_use_emergency_fallback(self):
        """
        Integration test: Normal LLM path should not trigger emergency fallback.
        
        When LLM works normally, the emergency fallback should not be used.
        """
        nc = NameCorrector()
        
        # Don't mock - use real LLM
        cards, relics = nc.correct_names(
            "hologram",
            character="defect"
        )
        
        # Should find via normal LLM path
        assert "Hologram" in cards, "Normal LLM should find 'Hologram'"
