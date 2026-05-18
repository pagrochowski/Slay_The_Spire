# Refactoring Summary - Advisor to Status Recorder

## Changes Overview

### ✅ COMPLETED:
1. **RunManager (src/advisor/run_manager.py)**
   - ❌ Removed: floor tracking, events logging, strategy notes, archetype_hints
   - ✅ Added: current_choice tracking (type, options)
   - ✅ Added: set_card_choice(), set_relic_choice(), set_shop_choices(), clear_choice()
   - ✅ Simplified: All methods now focus on state updates only

### 🔄 IN PROGRESS:
2. **GroqAdvisor (src/advisor/groq_advisor.py)** - NEEDS MAJOR REFACTORING
   
   **Keep:**
   - KnowledgeBase class (entire - for future reference)
   - CHARACTERS dict
   - Basic state update methods: start_run, add_card, remove_card, add_relic
   - Status methods: update_hp, update_gold, update_act, set_boss
   - get_run_status (simplified)
   - create_summary_file (completely rewritten to new format)
   - Choice delegation methods: set_card_choice, set_relic_choice, set_shop_choices
   
   **Remove:**
   - adjust_strategy() method (lines 1013-1076)
   - chat_message() method (lines 626-695)
   - All auto-strategy update calls in add_card/remove_card/add_relic
   - detect_archetype_from_deck() from KnowledgeBase
   - _get_system_prompt() - not needed anymore
   - Messages history (self.messages)
   - _build_rag_context, _extract_strategy_updates
   
   **Simplify:**
   - __init__: No system prompt, no messages history
   - add_card: Just add card, no strategy update
   - remove_card: Just remove card
   - add_relic: Just add relic, no strategy update
   - set_boss: Just set boss name, no strategy generation
   - get_run_status: Remove strategy references

3. **create_summary_file - New Simple Format:**
```markdown
# Slay the Spire Run Summary

## Run Information
- Character: Ironclad
- Ascension: 1
- Act: 2

## Current Status
- HP: 82/88
- Gold: 217

## Deck (18 cards)
3x Strike, 2x Defend, 1x Bash, ...

## Relics
- Burning Blood
- Red Skull
...

## Potions
- Fire Potion
...

## Keys
- Ruby: ✗
- Emerald: ✗
- Sapphire: ✗

## Current Boss
Bronze Automaton

## Current Decision
**Choosing between 3 cards:**
- Bash
- Strike
- Defend

(Or "**At shop:**" with cards/relics/potions, or "**Choosing between 3 relics:**", or "No decision pending")
```

### 🔜 TODO:
4. **voice_advisor.py (scripts/voice_advisor.py)**
   - Remove handlers for: adjust_strategy, advise_card, compare_cards, general_question
   - Keep handlers for: start_run, add_card, remove_card, add_relic, update_hp, update_gold, update_act, set_boss, deck_status, relic_status, run_status, end_run
   - Add handlers for: card_choice, relic_choice, shop (these now just SET the choice, not give advice)

5. **AI_GUIDE.md**
   - Update project purpose: "Voice-controlled run status recorder"
   - Remove strategic intelligence references
   - Update architecture diagrams
   - Document new simplified flow
   - Update command list

## Files Affected:
- ✅ src/advisor/run_manager.py (DONE)
- 🔄 src/advisor/groq_advisor.py (IN PROGRESS)
- ⏳ scripts/voice_advisor.py (TODO)
- ⏳ AI_GUIDE.md (TODO)
- ⏳ README.md (TODO - optional)

## Estimated Line Changes:
- run_manager.py: ~150 lines removed, ~80 lines added
- groq_advisor.py: ~600 lines removed, ~50 lines added
- voice_advisor.py: ~200 lines removed/modified
- AI_GUIDE.md: ~400 lines modified

Would you like me to proceed with the full implementation?
