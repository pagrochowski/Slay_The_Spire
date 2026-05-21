"""
Test upgrade detection with punctuation in transcribed text.
Tests the fix for: "Collect Plus, Crescendo Plus, Evaluate."
"""

import string

def test_upgrade_detection(text):
    """Test the upgrade detection logic."""
    print(f"\n{'='*70}")
    print(f"Testing: \"{text}\"")
    print('='*70)
    
    upgrade_keywords = ['plus', 'upgrade', 'upgraded']
    
    # Build upgrade map: track which words are followed by upgrade keywords
    words = text.split()
    upgrade_map = {}  # word (lowercase) → is_upgraded
    cleaned_words = []
    
    print(f"\nOriginal words: {words}")
    
    i = 0
    while i < len(words):
        word = words[i]
        # Strip punctuation for comparison
        word_stripped = word.strip(string.punctuation)
        word_lower = word_stripped.lower()
        
        print(f"  [{i}] '{word}' -> stripped: '{word_stripped}' -> lower: '{word_lower}'")
        
        # Check if this word is an upgrade keyword
        if word_lower in upgrade_keywords:
            print(f"    ✓ Found upgrade keyword!")
            # Mark the previous word as upgraded (if exists)
            if cleaned_words:
                prev_word = cleaned_words[-1]
                upgrade_map[prev_word.lower()] = True
                print(f"    → Marking '{prev_word}' as upgraded")
            # Skip this upgrade keyword
            i += 1
            continue
        
        # This is a regular word (potential card/relic name)
        cleaned_words.append(word_stripped)
        # Default to not upgraded (will be set to True if followed by upgrade keyword)
        if word_lower not in upgrade_map:
            upgrade_map[word_lower] = False
        
        i += 1
    
    # Build cleaned text without upgrade keywords
    cleaned_text = ' '.join(cleaned_words)
    
    print(f"\nCleaned words: {cleaned_words}")
    print(f"Cleaned text: \"{cleaned_text}\"")
    print(f"\nUpgrade map:")
    for word, is_upgraded in upgrade_map.items():
        status = "✓ UPGRADED" if is_upgraded else "  not upgraded"
        print(f"  {status}: {word}")
    
    # Show what would be displayed
    has_upgrades = any(upgrade_map.values())
    if has_upgrades:
        upgraded_words = [w for w in cleaned_words if upgrade_map.get(w.lower(), False)]
        print(f"\n🔍 Analyzing: \"{cleaned_text}\"")
        print(f"⬆️  Upgrade markers detected after: {', '.join(upgraded_words)}")
    else:
        print(f"\n🔍 Analyzing: \"{cleaned_text}\"")
    
    # Expected results
    print(f"\n{'='*70}")
    print("EXPECTED RESULTS:")
    print("  - Collect: UPGRADED")
    print("  - Crescendo: UPGRADED")
    print("  - Evaluate: NOT upgraded")
    
    # Verify
    print(f"\n{'='*70}")
    print("VERIFICATION:")
    collect_upgraded = upgrade_map.get('collect', False)
    crescendo_upgraded = upgrade_map.get('crescendo', False)
    evaluate_upgraded = upgrade_map.get('evaluate', False)
    
    print(f"  Collect upgraded: {collect_upgraded} {'✅' if collect_upgraded else '❌'}")
    print(f"  Crescendo upgraded: {crescendo_upgraded} {'✅' if crescendo_upgraded else '❌'}")
    print(f"  Evaluate NOT upgraded: {not evaluate_upgraded} {'✅' if not evaluate_upgraded else '❌'}")
    
    all_correct = collect_upgraded and crescendo_upgraded and not evaluate_upgraded
    print(f"\n  Overall: {'✅ PASS' if all_correct else '❌ FAIL'}")
    print('='*70)
    
    return all_correct


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Collect Plus, Crescendo Plus, Evaluate.",
        "Strike plus defend",
        "Battle Hymn Plus, Third Eye.",
        "Vigilance upgraded, Eruption plus, Protect",
        "Akabeko, Pen Nib Plus",  # Should handle relics too (Pen Nib doesn't upgrade, but test the logic)
    ]
    
    results = []
    for test_text in test_cases:
        result = test_upgrade_detection(test_text)
        results.append((test_text, result))
        print()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for text, passed in results:
        status = "✅ PASS" if passed else "⚠️  CHECK"
        print(f"{status}: {text}")
