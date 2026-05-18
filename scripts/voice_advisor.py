#!/usr/bin/env python
"""
Voice Advisor with Groq AI + Edge TTS.

This script launches the voice interface using:
- Groq API for fast LLM inference (openai/gpt-oss-120b)
- Groq Whisper API for speech-to-text (whisper-large-v3 with turbo fallback)
- Edge TTS for natural-sounding voice output
- Local database for run tracking

Usage:
    python scripts/voice_advisor.py

Controls:
    - Press and hold F1 to speak
    - Release to get AI response
    - Press ESC to exit
"""

import os
import sys
from pathlib import Path
from difflib import SequenceMatcher

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.advisor.groq_advisor import GroqAdvisor as Advisor
from src.voice.voice_interface import VoiceInterface, VoiceConfig
from src.advisor.command_parser import CommandParser
from loguru import logger


def create_command_handler(advisor: Advisor, parser: CommandParser):
    """Create the command handler function with intelligent parsing."""
    
    def auto_update_after_change(trigger_strategy_update: bool = True):
        """Auto-update summary file and optionally revise strategy after run changes."""
        # Always update the summary file silently
        advisor.create_summary_file(silent=True)
        
        # Optionally trigger strategy revision in background
        if trigger_strategy_update:
            advisor.adjust_strategy(silent=True)
    
    def handle_command(text: str) -> str:
        """Process voice commands using two-layer LLM approach."""
        
        # Layer 1: Fast intent classification and entity extraction
        parsed = parser.parse(text)
        intent = parsed.get("intent", "unknown")
        
        logger.info(f"Parsed intent: {intent}, cards: {parsed.get('cards', [])}")
        
        # Handle based on intent
        if intent == "start_run":
            char = parsed.get("character")
            asc = parsed.get("ascension", 0) or 0
            if char:
                return advisor.start_run(char, asc)
            return "Which character would you like to play? Ironclad, Silent, Defect, or Watcher?"
        
        elif intent == "end_run":
            victory = parsed.get("victory", False)
            return advisor.end_run(victory=victory)
        
        elif intent == "status":
            return advisor.get_run_status()
        
        elif intent == "summary":
            # Create a markdown file with full run summary
            return advisor.create_summary_file()
        
        elif intent == "update_run":
            # User is describing/correcting their current run
            char = parsed.get("character")
            asc = parsed.get("ascension")
            max_hp = parsed.get("max_hp")
            max_hp_delta = parsed.get("max_hp_delta")
            
            # If character specified, start new run with those params
            if char and char != "null":
                asc = asc if asc is not None else 0
                result = advisor.start_run(char, asc)
                # If max_hp is different from default, update it
                if max_hp:
                    advisor.update_hp(current=max_hp, max_hp=max_hp)
                    result += f" Max HP set to {max_hp}."
                auto_update_after_change(trigger_strategy_update=False)
                return result
            # Handle relative max HP change (e.g., "8 extra max HP")
            elif max_hp_delta is not None:
                run = advisor.run_manager.get_active_run()
                if run:
                    new_max_hp = run["max_hp"] + max_hp_delta
                    # If gaining max HP, also increase current HP
                    new_hp = run["hp"] + max_hp_delta if max_hp_delta > 0 else run["hp"]
                    # Don't let HP exceed new max
                    new_hp = min(new_hp, new_max_hp)
                    result = advisor.update_hp(current=new_hp, max_hp=new_max_hp)
                    auto_update_after_change(trigger_strategy_update=False)
                    return result
                return "No active run."
            # Just updating max_hp on current run (absolute value)
            elif max_hp:
                result = advisor.update_hp(max_hp=max_hp)  # Only updates max, not current
                auto_update_after_change(trigger_strategy_update=False)
                return result
            return "What are your run parameters? (character, ascension, max HP)"
        
        elif intent == "add_card":
            cards = parsed.get("cards", [])
            if cards:
                # Add only the first card (user picked one)
                result = advisor.add_card(cards[0])
                auto_update_after_change(trigger_strategy_update=True)
                return result
            return "Which card did you pick?"
        
        elif intent == "remove_card":
            cards = parsed.get("cards", [])
            if cards:
                card_to_remove = cards[0]
                
                # Validate card is actually in the deck
                deck = advisor.run_manager.get_full_deck()
                if card_to_remove not in deck:
                    # Card not in deck - find similar cards that ARE in deck
                    deck_unique = list(set(deck))
                    similar_in_deck = []
                    
                    for deck_card in deck_unique:
                        # Check if the names are similar
                        similarity = SequenceMatcher(None, card_to_remove.lower(), deck_card.lower()).ratio()
                        if similarity > 0.5 or card_to_remove.lower() in deck_card.lower() or deck_card.lower() in card_to_remove.lower():
                            count = deck.count(deck_card)
                            similar_in_deck.append((deck_card, count))
                    
                    if similar_in_deck:
                        suggestions = ", ".join([f"{card} (x{count})" if count > 1 else card for card, count in similar_in_deck[:3]])
                        return f"'{card_to_remove}' is not in your deck. Did you mean: {suggestions}?"
                    else:
                        return f"'{card_to_remove}' is not in your deck."
                
                result = advisor.remove_card(card_to_remove)
                auto_update_after_change(trigger_strategy_update=True)
                return result
            return "Which card to remove?"
        
        elif intent == "card_removal":
            # User is at a card removal event and wants advice
            return advisor.advise_card_removal()
        
        elif intent == "upgrade_card":
            # User wants advice on which card to upgrade
            return advisor.advise_card_upgrade()
        
        elif intent == "add_relic":
            relics = parsed.get("relics", [])
            if relics:
                result = advisor.add_relic(relics[0])
                auto_update_after_change(trigger_strategy_update=True)
                return result
            return "Which relic did you get?"
        
        elif intent == "set_boss":
            boss = parsed.get("boss")
            if boss:
                result = advisor.set_boss(boss)
                # Trigger comprehensive boss-specific strategy update
                auto_update_after_change(trigger_strategy_update=False)  # Don't use generic strategy update
                logger.info("Triggering comprehensive boss strategy analysis...")
                strategy_result = advisor.adjust_strategy(silent=True, boss_focus=True)
                logger.info("Comprehensive strategy updated in background")
                return result
            return "Which boss are you facing?"
        
        elif intent == "update_floor":
            floor = parsed.get("floor")
            act = parsed.get("act")  # Get explicit act if provided
            if floor:
                result = advisor.update_floor(floor, act=act)
                auto_update_after_change(trigger_strategy_update=False)
                return result
            return "What floor are you on?"
        
        elif intent == "get_strategy":
            return advisor.get_strategy()
        
        elif intent == "adjust_strategy":
            # Ask the AI to analyze run and suggest/update strategy
            return advisor.adjust_strategy()
        
        elif intent == "clear_strategy":
            return advisor.clear_strategy()
        
        elif intent == "update_hp":
            hp = parsed.get("hp")
            max_hp = parsed.get("max_hp")
            hp_delta = parsed.get("hp_delta")
            max_hp_delta = parsed.get("max_hp_delta")
            
            # Handle delta values first
            if hp_delta is not None or max_hp_delta is not None:
                run = advisor.run_manager.get_active_run()
                if run:
                    new_hp = run["hp"] + (hp_delta or 0)
                    new_max_hp = run["max_hp"] + (max_hp_delta or 0)
                    # Clamp HP to [0, max_hp]
                    new_hp = max(0, min(new_hp, new_max_hp))
                    result = advisor.update_hp(current=new_hp, max_hp=new_max_hp if max_hp_delta else None)
                    auto_update_after_change(trigger_strategy_update=False)
                    return result
                return "No active run."
            # Handle absolute values
            elif hp is not None or max_hp is not None:
                result = advisor.update_hp(current=hp, max_hp=max_hp)
                auto_update_after_change(trigger_strategy_update=False)
                return result
            return "What's your current HP?"
        
        elif intent == "update_gold":
            gold = parsed.get("gold")
            if gold is not None:
                result = advisor.update_gold(gold)
                auto_update_after_change(trigger_strategy_update=False)
                return result
            return "How much gold do you have?"
        
        elif intent == "card_choice":
            # Layer 2: Pass to main model for strategic reasoning
            # Include the corrected card names in the query
            cards = parsed.get("cards", [])
            if cards:
                # Validate card names against database (even single cards)
                validated_cards = []
                uncertain_cards = []
                
                for card_name in cards:
                    matches = advisor.kb.find_cards(card_name, limit=10)
                    
                    if not matches:
                        # Card not found at all
                        uncertain_cards.append((card_name, None, []))
                    else:
                        best_match = matches[0]
                        score, _, card_data = best_match
                        actual_name = card_data["name"]
                        
                        # Check if the matched name is too different from what was said
                        name_similarity = SequenceMatcher(None, card_name.lower(), actual_name.lower()).ratio()
                        
                        if score < 0.7 or (score < 0.95 and name_similarity < 0.8):
                            # Uncertain match - ask for clarification
                            suggestions = [m[2]["name"] for m in matches if not m[2]["name"].endswith('+')][:4]
                            uncertain_cards.append((card_name, score, suggestions))
                        else:
                            # Good match
                            validated_cards.append(actual_name)
                
                # If any cards are uncertain, ask for clarification
                if uncertain_cards:
                    clarifications = []
                    for original, score, suggestions in uncertain_cards:
                        if suggestions:
                            suggest_str = ", ".join(suggestions[:3])
                            clarifications.append(f'I heard "{original}" but did you mean: {suggest_str}?')
                        else:
                            clarifications.append(f'I could not find a card called "{original}".')
                    
                    return " ".join(clarifications) + " Please say the card names again."
                
                # All cards validated
                if len(validated_cards) >= 2:
                    # Multiple cards - store and ask for advice
                    advisor.set_card_choices(validated_cards)
                    card_list = ", ".join(validated_cards[:-1]) + f" or {validated_cards[-1]}"
                    enhanced_query = f"Which card should I pick: {card_list}?"
                    return advisor.chat_message(enhanced_query)
                else:
                    # Single validated card - treat as question
                    return advisor.chat_message(text)
            # No cards - treat as question
            return advisor.chat_message(text)
        
        elif intent == "relic_choice":
            # Layer 2: Pass to main model for relic choice reasoning
            relics = parsed.get("relics", [])
            if relics:
                # Validate relic names against database
                validated_relics = []
                uncertain_relics = []
                
                for relic_name in relics:
                    matches = advisor.kb.find_relics(relic_name, limit=10)
                    
                    if not matches:
                        # Relic not found at all
                        uncertain_relics.append((relic_name, None, []))
                    else:
                        best_match = matches[0]
                        score, _, relic_data = best_match
                        actual_name = relic_data["name"]
                        
                        # Check if the matched name is too different from what was said
                        name_similarity = SequenceMatcher(None, relic_name.lower(), actual_name.lower()).ratio()
                        
                        if score < 0.7 or (score < 0.95 and name_similarity < 0.8):
                            # Uncertain match - ask for clarification
                            suggestions = [m[2]["name"] for m in matches][:4]
                            uncertain_relics.append((relic_name, score, suggestions))
                        else:
                            # Good match
                            validated_relics.append(actual_name)
                
                # If any relics are uncertain, ask for clarification
                if uncertain_relics:
                    clarifications = []
                    for original, score, suggestions in uncertain_relics:
                        if suggestions:
                            suggest_str = ", ".join(suggestions[:3])
                            clarifications.append(f'I heard "{original}" but did you mean: {suggest_str}?')
                        else:
                            clarifications.append(f'I could not find a relic called "{original}".')
                    
                    return " ".join(clarifications) + " Please say the relic names again."
                
                # All relics validated
                if len(validated_relics) >= 2:
                    # Multiple relics - ask for advice
                    advisor.last_relic_choices = validated_relics  # Store for followup questions
                    relic_list = ", ".join(validated_relics[:-1]) + f" or {validated_relics[-1]}"
                    enhanced_query = f"Which relic should I pick: {relic_list}?"
                    return advisor.chat_message(enhanced_query)
                else:
                    # Single validated relic - treat as question
                    return advisor.chat_message(text)
            # No relics - treat as question
            return advisor.chat_message(text)
        
        elif intent == "followup":
            # Follow-up question about previous card choice - DON'T clear stored cards
            # Pass original query directly - the advisor will inject previous card context
            return advisor.chat_message(parsed.get("original_query", text))
        
        elif intent == "unknown":
            # Ambiguous or unclear intent - ask for clarification
            ambiguity_note = parsed.get("ambiguity_note", "")
            
            # Try to provide helpful clarification based on keywords
            if "card" in text.lower():
                return "I did not quite understand your intention. Did you want to add a new card or remove it from the deck?"
            elif "relic" in text.lower():
                return "I did not quite understand. Did you get a new relic, or are you asking about relics?"
            elif "hp" in text.lower() or "health" in text.lower():
                return "I did not quite understand. Did you take damage, heal, or change your max HP?"
            else:
                return "I did not quite understand your intention. Could you rephrase that?"
        
        else:  # "question"
            # Validate any mentioned card/relic names before passing to main model
            cards = parsed.get("cards", [])
            relics = parsed.get("relics", [])
            
            # Validate cards if any mentioned
            if cards:
                uncertain_items = []
                for card_name in cards:
                    matches = advisor.kb.find_cards(card_name, limit=10)
                    if not matches:
                        uncertain_items.append(f'I could not find a card called "{card_name}"')
                    else:
                        best_match = matches[0]
                        score, _, card_data = best_match
                        actual_name = card_data["name"]
                        name_similarity = SequenceMatcher(None, card_name.lower(), actual_name.lower()).ratio()
                        
                        if score < 0.7 or (score < 0.95 and name_similarity < 0.8):
                            suggestions = [m[2]["name"] for m in matches if not m[2]["name"].endswith('+')][:3]
                            suggest_str = ", ".join(suggestions)
                            uncertain_items.append(f'I heard "{card_name}" but did you mean: {suggest_str}?')
                
                if uncertain_items:
                    return " ".join(uncertain_items) + " Please clarify."
            
            # Validate relics if any mentioned
            if relics:
                uncertain_items = []
                for relic_name in relics:
                    matches = advisor.kb.find_relics(relic_name, limit=5)
                    if not matches or matches[0][0] < 0.7:
                        if matches:
                            suggestions = [m[2]["name"] for m in matches[:3]]
                            suggest_str = ", ".join(suggestions)
                            uncertain_items.append(f'I heard "{relic_name}" but did you mean: {suggest_str}?')
                        else:
                            uncertain_items.append(f'I could not find a relic called "{relic_name}"')
                
                if uncertain_items:
                    return " ".join(uncertain_items) + " Please clarify."
            
            # All names validated or no items mentioned - pass to main model
            return advisor.chat_message(text)
    
    return handle_command


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🎮 SLAY THE SPIRE VOICE ADVISOR")
    print("=" * 60)
    print("Powered by: Groq (LLM + Whisper) + Edge TTS")
    print("=" * 60 + "\n")
    
    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in .env file!")
        print("   Add your API key to .env file and try again.")
        return
    
    try:
        # Initialize command parser (fast llama model for intent classification)
        print("Initializing command parser...")
        parser = CommandParser()
        print("✅ Command parser ready (llama-3.1-8b-instant)")
        
        # Initialize advisor
        print("Initializing Groq advisor...")
        advisor = Advisor()
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"✅ Groq advisor ready ({model_name})")
        
        # Configure voice interface with Groq Whisper + Edge TTS
        config = VoiceConfig(
            tts_engine="edge-tts",
            tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
            whisper_backend="groq",  # Use Groq API for better accuracy
            # whisper_model defaults to whisper-large-v3 (primary) with turbo fallback
            push_to_talk_key="f1"
        )
        
        # Create voice interface
        print("Initializing voice interface...")
        print("  STT: Groq Whisper API (whisper-large-v3 with turbo fallback)")
        print("  TTS: Edge TTS (en-US-AriaNeural)")
        interface = VoiceInterface(config)
        interface.on_command = create_command_handler(advisor, parser)
        
        # Welcome message
        interface.startup_message = "Voice advisor ready."
        
        # Run the interface
        interface.run()
        
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. A valid GROQ_API_KEY in .env")
        print("  2. Installed: pip install groq edge-tts pygame")
        raise


if __name__ == "__main__":
    main()
