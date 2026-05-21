"""
Simulate voice recorder processing with the user's exact input.
Shows debugging output to help identify matching issues.
"""

import string


def simulate_full_process(text, simulated_llm_matches):
    """
    Simulate the complete voice recorder process.
    
    Args:
        text: The transcribed text
        simulated_llm_matches: What the LLM returns (cards, relics)
    """
    print("\n" + "="*70)
    print(f"📝 You said: \"{text}\"")
    print("="*70)
    
    # Step 1: Upgrade detection
    upgrade_keywords = ['plus', 'upgrade', 'upgraded']
    words = text.split()
    upgrade_map = {}
    cleaned_words = []
    
    i = 0
    while i < len(words):
        word = words[i]
        word_stripped = word.strip(string.punctuation)
        word_lower = word_stripped.lower()
        
        if word_lower in upgrade_keywords:
            if cleaned_words:
                prev_word = cleaned_words[-1]
                upgrade_map[prev_word.lower()] = True
            i += 1
            continue
        
        cleaned_words.append(word_stripped)
        if word_lower not in upgrade_map:
            upgrade_map[word_lower] = False
        
        i += 1
    
    cleaned_text = ' '.join(cleaned_words)
    
    # Show upgrade detection results
    has_upgrades = any(upgrade_map.values())
    if has_upgrades:
        upgraded_words = [w for w in cleaned_words if upgrade_map.get(w.lower(), False)]
        print(f"🔍 Analyzing: \"{cleaned_text}\"")
        print(f"⬆️  Upgrade markers detected after: {', '.join(upgraded_words)}")
    else:
        print(f"🔍 Analyzing: \"{cleaned_text}\"")
    
    # Step 2: Simulated LLM matching
    print(f"   📤 Sending to LLM for WATCHER: \"{cleaned_text}\"")
    cards, relics = simulated_llm_matches
    print(f"   📥 LLM returned: cards={cards}, relics={relics}")
    
    # Step 3: Check for unmatched words
    if cards or relics:
        matched_words = set()
        for card in cards:
            matched_words.update(card.lower().replace('-', ' ').split())
        for relic in relics:
            matched_words.update(relic.lower().replace('-', ' ').split())
        
        input_words = set(word.lower() for word in cleaned_words)
        unmatched = input_words - matched_words
        
        if unmatched:
            print(f"   ⚠️  Unmatched words: {', '.join(sorted(unmatched))}")
            print(f"      (These might be part of multi-word names or not in knowledge base)")
    
    if not cards and not relics:
        print("⚠️  No cards or relics matched")
        return
    
    # Step 4: Apply upgrades
    upgraded_cards = []
    for card_name in cards:
        card_words = card_name.lower().replace('-', ' ').split()
        is_card_upgraded = any(upgrade_map.get(word, False) for word in card_words)
        
        if is_card_upgraded:
            upgraded_cards.append(f"{card_name}+")
        else:
            upgraded_cards.append(card_name)
    
    # Show final results
    matched_items = []
    matched_items.extend(upgraded_cards)
    if relics:
        matched_items.extend(relics)
    
    print(f"✅ Matched: {', '.join(matched_items)}")
    
    if any('+' in card for card in upgraded_cards):
        upgraded_names = [card.replace('+', '') for card in upgraded_cards if '+' in card]
        print(f"   ⬆️  Upgraded: {', '.join(upgraded_names)}")
    
    print("="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("VOICE RECORDER SIMULATION - DEBUGGING OUTPUT")
    print("="*70)
    
    # User's problematic case
    print("\n1. USER'S REPORTED ISSUE:")
    print("   Input: 'Just Lucky Plus, Follow Up Plus, Brilliance Plus.'")
    print("   Expected: Just Lucky+, Follow-Up+, Brilliance+")
    print("   Actual (reported): Just Lucky, Brilliance (missing Follow-Up and upgrades)")
    
    # Simulate what's actually happening
    simulate_full_process(
        "Just Lucky Plus, Follow Up Plus, Brilliance Plus.",
        (["Just Lucky", "Brilliance"], [])  # What LLM actually returns (missing Follow-Up)
    )
    
    print("\n2. WHAT SHOULD HAPPEN IF LLM MATCHED CORRECTLY:")
    simulate_full_process(
        "Just Lucky Plus, Follow Up Plus, Brilliance Plus.",
        (["Just Lucky", "Follow-Up", "Brilliance"], [])  # What LLM should return
    )
    
    print("\n3. DIAGNOSIS:")
    print("   ✅ Upgrade detection is working correctly")
    print("   ✅ Punctuation handling is working correctly")
    print("   ❌ LLM is not matching 'Follow Up' to 'Follow-Up' card")
    print()
    print("   ISSUE: The knowledge base has 'Follow-Up' (hyphenated)")
    print("          but we send 'Follow Up' (no hyphen) to the LLM.")
    print()
    print("   SOLUTIONS:")
    print("   1. Improve LLM prompt to handle hyphen variations")
    print("   2. Add fuzzy matching in knowledge base lookup")
    print("   3. Pre-process text to add hyphens for known cards")
    print()
    
    print("\n4. OTHER TEST CASES:")
    
    # Other examples
    test_cases = [
        ("Collect Plus, Crescendo Plus, Evaluate.", ["Collect", "Crescendo", "Evaluate"]),
        ("Battle Hymn Plus, Third Eye.", ["Battle Hymn", "Third Eye"]),
        ("Strike plus defend", ["Strike", "Defend"]),
    ]
    
    for text, expected_cards in test_cases:
        simulate_full_process(text, (expected_cards, []))
