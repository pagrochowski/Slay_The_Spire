#!/usr/bin/env python
"""
Voice Advisor with Groq AI + Edge TTS.

This script launches the voice interface using:
- Groq API for fast LLM inference (gpt-oss-120b)
- Groq Whisper API for speech-to-text (whisper-large-v3-turbo)
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
                    return advisor.update_hp(current=new_hp, max_hp=new_max_hp)
                return "No active run."
            # Just updating max_hp on current run (absolute value)
            elif max_hp:
                return advisor.update_hp(max_hp=max_hp)  # Only updates max, not current
            return "What are your run parameters? (character, ascension, max HP)"
        
        elif intent == "add_card":
            cards = parsed.get("cards", [])
            if cards:
                # Add only the first card (user picked one)
                return advisor.add_card(cards[0])
            return "Which card did you pick?"
        
        elif intent == "remove_card":
            cards = parsed.get("cards", [])
            if cards:
                return advisor.remove_card(cards[0])
            return "Which card to remove?"
        
        elif intent == "card_removal":
            # User is at a card removal event and wants advice
            return advisor.advise_card_removal()
        
        elif intent == "add_relic":
            relics = parsed.get("relics", [])
            if relics:
                return advisor.add_relic(relics[0])
            return "Which relic did you get?"
        
        elif intent == "set_boss":
            boss = parsed.get("boss")
            if boss:
                return advisor.set_boss(boss)
            return "Which boss are you facing?"
        
        elif intent == "update_floor":
            floor = parsed.get("floor")
            if floor:
                return advisor.update_floor(floor)
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
                    return advisor.update_hp(current=new_hp, max_hp=new_max_hp if max_hp_delta else None)
                return "No active run."
            # Handle absolute values
            elif hp is not None or max_hp is not None:
                return advisor.update_hp(current=hp, max_hp=max_hp)
            return "What's your current HP?"
        
        elif intent == "update_gold":
            gold = parsed.get("gold")
            if gold is not None:
                return advisor.update_gold(gold)
            return "How much gold do you have?"
        
        elif intent == "card_choice":
            # Layer 2: Pass to main model for strategic reasoning
            # Include the corrected card names in the query
            cards = parsed.get("cards", [])
            if cards and len(cards) >= 2:
                # Store cards for follow-up questions (only if multiple options)
                advisor.set_card_choices(cards)
                # Rephrase with corrected card names for the main model
                card_list = ", ".join(cards[:-1]) + f" or {cards[-1]}" if len(cards) > 1 else cards[0]
                enhanced_query = f"Which card should I pick: {card_list}?"
                return advisor.chat_message(enhanced_query)
            # Single card mentioned without "why not" phrasing - treat as question
            return advisor.chat_message(text)
        
        elif intent == "followup":
            # Follow-up question about previous card choice - DON'T clear stored cards
            # Pass original query directly - the advisor will inject previous card context
            return advisor.chat_message(parsed.get("original_query", text))
        
        else:  # "question" or "unknown"
            # Layer 2: Pass to main model for reasoning
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
            whisper_model="whisper-large-v3-turbo",  # Best accuracy
            push_to_talk_key="f1"
        )
        
        # Create voice interface
        print("Initializing voice interface...")
        print("  STT: Groq Whisper API (whisper-large-v3-turbo)")
        print("  TTS: Edge TTS (en-US-AriaNeural)")
        interface = VoiceInterface(config)
        interface.on_command = create_command_handler(advisor, parser)
        
        # Welcome message
        interface.startup_message = (
            "Voice advisor ready! I'm using Groq Whisper for better speech recognition. "
            "Press F1 and tell me about your run, or ask for strategic advice!"
        )
        
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
