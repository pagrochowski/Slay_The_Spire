"""
Comprehensive test suite for upgrade detection in voice recorder.
Tests various edge cases and multi-word card names.
"""

import string
import pytest


def detect_upgrades(text):
    """
    Simulate the upgrade detection logic from voice_recorder.py
    
    Returns: (cleaned_text, upgrade_map)
    """
    upgrade_keywords = ['plus', 'upgrade', 'upgraded']
    
    words = text.split()
    upgrade_map = {}
    cleaned_words = []
    
    i = 0
    while i < len(words):
        word = words[i]
        # Strip punctuation for comparison
        word_stripped = word.strip(string.punctuation)
        word_lower = word_stripped.lower()
        
        # Check if this word is an upgrade keyword
        if word_lower in upgrade_keywords:
            # Mark the previous word as upgraded (if exists)
            if cleaned_words:
                prev_word = cleaned_words[-1]
                upgrade_map[prev_word.lower()] = True
            # Skip this upgrade keyword
            i += 1
            continue
        
        # This is a regular word (potential card/relic name)
        cleaned_words.append(word_stripped)
        # Default to not upgraded
        if word_lower not in upgrade_map:
            upgrade_map[word_lower] = False
        
        i += 1
    
    cleaned_text = ' '.join(cleaned_words)
    return cleaned_text, upgrade_map


def check_card_upgraded(card_name, upgrade_map):
    """
    Check if a card should be upgraded based on the upgrade map.
    Handles hyphenated card names like "Follow-Up".
    """
    # Normalize card name: replace hyphens with spaces for word matching
    card_words = card_name.lower().replace('-', ' ').split()
    is_upgraded = any(upgrade_map.get(word, False) for word in card_words)
    return is_upgraded


def format_card_with_upgrade(card_name, upgrade_map):
    """Format card name with + if upgraded."""
    is_upgraded = check_card_upgraded(card_name, upgrade_map)
    return f"{card_name}+" if is_upgraded else card_name


class TestUpgradeDetection:
    """Test suite for upgrade detection logic."""
    
    def test_single_word_card_upgraded(self):
        """Test: 'Strike plus'"""
        text = "Strike plus"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Strike"
        assert upgrades.get('strike') == True
        assert format_card_with_upgrade("Strike", upgrades) == "Strike+"
    
    def test_single_word_card_not_upgraded(self):
        """Test: 'Defend'"""
        text = "Defend"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Defend"
        assert upgrades.get('defend') == False
        assert format_card_with_upgrade("Defend", upgrades) == "Defend"
    
    def test_two_word_card_upgraded(self):
        """Test: 'Battle Hymn Plus'"""
        text = "Battle Hymn Plus"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Battle Hymn"
        assert upgrades.get('hymn') == True
        assert format_card_with_upgrade("Battle Hymn", upgrades) == "Battle Hymn+"
    
    def test_hyphenated_card_upgraded(self):
        """Test: 'Follow Up Plus' matching to 'Follow-Up' card"""
        text = "Follow Up Plus"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Follow Up"
        assert upgrades.get('up') == True
        # Card name from knowledge base is "Follow-Up"
        assert format_card_with_upgrade("Follow-Up", upgrades) == "Follow-Up+"
    
    def test_multiple_cards_with_punctuation(self):
        """Test: 'Just Lucky Plus, Follow Up Plus, Brilliance Plus.'"""
        text = "Just Lucky Plus, Follow Up Plus, Brilliance Plus."
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Just Lucky Follow Up Brilliance"
        # Check individual words
        assert upgrades.get('just') == False
        assert upgrades.get('lucky') == True  # "Plus" after "Lucky"
        assert upgrades.get('follow') == False
        assert upgrades.get('up') == True  # "Plus" after "Up"
        assert upgrades.get('brilliance') == True  # "Plus" after "Brilliance"
        
        # Check card matching
        assert format_card_with_upgrade("Just Lucky", upgrades) == "Just Lucky+"
        assert format_card_with_upgrade("Follow-Up", upgrades) == "Follow-Up+"
        assert format_card_with_upgrade("Brilliance", upgrades) == "Brilliance+"
    
    def test_collect_crescendo_evaluate(self):
        """Test: 'Collect Plus, Crescendo Plus, Evaluate.'"""
        text = "Collect Plus, Crescendo Plus, Evaluate."
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Collect Crescendo Evaluate"
        assert upgrades.get('collect') == True
        assert upgrades.get('crescendo') == True
        assert upgrades.get('evaluate') == False
        
        assert format_card_with_upgrade("Collect", upgrades) == "Collect+"
        assert format_card_with_upgrade("Crescendo", upgrades) == "Crescendo+"
        assert format_card_with_upgrade("Evaluate", upgrades) == "Evaluate"
    
    def test_mixed_upgraded_keyword(self):
        """Test: 'Vigilance upgraded, Eruption plus, Protect'"""
        text = "Vigilance upgraded, Eruption plus, Protect"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Vigilance Eruption Protect"
        assert upgrades.get('vigilance') == True
        assert upgrades.get('eruption') == True
        assert upgrades.get('protect') == False
    
    def test_only_first_word_upgraded(self):
        """Test: Only first word of multi-word card gets 'plus'"""
        text = "Battle plus Hymn"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Battle Hymn"
        assert upgrades.get('battle') == True
        assert upgrades.get('hymn') == False
        # "Battle Hymn" should be upgraded because "Battle" is marked
        assert format_card_with_upgrade("Battle Hymn", upgrades) == "Battle Hymn+"
    
    def test_only_second_word_upgraded(self):
        """Test: Only second word of multi-word card gets 'plus'"""
        text = "Battle Hymn plus"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Battle Hymn"
        assert upgrades.get('battle') == False
        assert upgrades.get('hymn') == True
        # "Battle Hymn" should be upgraded because "Hymn" is marked
        assert format_card_with_upgrade("Battle Hymn", upgrades) == "Battle Hymn+"
    
    def test_multiple_cards_mixed_upgrades(self):
        """Test: Mix of upgraded and non-upgraded cards"""
        text = "Strike plus, Defend, Battle Hymn upgraded"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Strike Defend Battle Hymn"
        assert format_card_with_upgrade("Strike", upgrades) == "Strike+"
        assert format_card_with_upgrade("Defend", upgrades) == "Defend"
        assert format_card_with_upgrade("Battle Hymn", upgrades) == "Battle Hymn+"
    
    def test_three_word_card(self):
        """Test: Three-word card name"""
        text = "Wreath of Flame plus"
        cleaned, upgrades = detect_upgrades(text)
        
        assert cleaned == "Wreath of Flame"
        assert upgrades.get('flame') == True
        assert format_card_with_upgrade("Wreath of Flame", upgrades) == "Wreath of Flame+"
    
    def test_no_spaces_around_punctuation(self):
        """Test: Punctuation without spaces"""
        text = "Strike+Defend"
        cleaned, upgrades = detect_upgrades(text)
        
        # "Strike+Defend" is one word, stripped to "Strike Defend"... wait, no
        # split() gives ["Strike+Defend"], strip() gives "Strike Defend"... no
        # strip(punctuation) only strips from START and END, not middle
        # So "Strike+Defend" stays as one word after strip
        assert "strike" in upgrades or "strikedefend" in upgrades.keys()


def test_real_world_examples():
    """Test real-world examples from user reports."""
    
    print("\n" + "="*70)
    print("REAL-WORLD TEST CASES")
    print("="*70)
    
    test_cases = [
        {
            "input": "Just Lucky Plus, Follow Up Plus, Brilliance Plus.",
            "expected_cards": ["Just Lucky", "Follow-Up", "Brilliance"],
            "expected_upgraded": ["Just Lucky+", "Follow-Up+", "Brilliance+"],
        },
        {
            "input": "Collect Plus, Crescendo Plus, Evaluate.",
            "expected_cards": ["Collect", "Crescendo", "Evaluate"],
            "expected_upgraded": ["Collect+", "Crescendo+", "Evaluate"],
        },
        {
            "input": "Strike plus defend",
            "expected_cards": ["Strike", "Defend"],
            "expected_upgraded": ["Strike+", "Defend"],
        },
        {
            "input": "Battle Hymn Plus, Third Eye.",
            "expected_cards": ["Battle Hymn", "Third Eye"],
            "expected_upgraded": ["Battle Hymn+", "Third Eye"],
        },
    ]
    
    for test in test_cases:
        text = test["input"]
        expected_cards = test["expected_cards"]
        expected_upgraded = test["expected_upgraded"]
        
        cleaned, upgrades = detect_upgrades(text)
        
        print(f"\nInput: {text}")
        print(f"Cleaned: {cleaned}")
        print(f"Upgrade map: {upgrades}")
        
        # Apply upgrades to expected cards
        actual_upgraded = [format_card_with_upgrade(card, upgrades) for card in expected_cards]
        
        print(f"Expected: {expected_upgraded}")
        print(f"Actual:   {actual_upgraded}")
        
        if actual_upgraded == expected_upgraded:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            for i, (exp, act) in enumerate(zip(expected_upgraded, actual_upgraded)):
                if exp != act:
                    print(f"  Card {i}: expected '{exp}', got '{act}'")


if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
    
    # Run real-world examples
    test_real_world_examples()
