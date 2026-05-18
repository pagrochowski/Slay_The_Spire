#!/usr/bin/env python
"""
Voice-Controlled Run Status Recorder.

This script tracks Slay the Spire run state via voice commands:
- Groq API for intent parsing (4-tier fallback)
- Groq Whisper API for speech-to-text
- Edge TTS for voice confirmations
- Persistent run storage in JSON

Usage:
    python scripts/voice_advisor.py

Controls:
    - Press and hold SPACE to speak
    - Release to process command
    - Press ESC to exit
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.advisor.status_recorder import StatusRecorder
from src.voice.voice_interface import VoiceInterface, VoiceConfig
from src.advisor.command_parser import CommandParser
from loguru import logger


def create_command_handler(recorder: StatusRecorder, parser: CommandParser):
    """Create the command handler function with intent parsing."""
    
    def validate_card_names(cards: list) -> list:
        """Validate and correct card names using knowledge base."""
        if not cards:
            return []
        
        validated = []
        for card_name in cards:
            matches = recorder.kb.find_cards(card_name, limit=1)
            if matches:
                validated.append(matches[0][2]["name"])
            else:
                validated.append(card_name)
        return validated
    
    def validate_relic_names(relics: list) -> list:
        """Validate and correct relic names using knowledge base."""
        if not relics:
            return []
        
        validated = []
        for relic_name in relics:
            matches = recorder.kb.find_relics(relic_name, limit=1)
            if matches:
                validated.append(matches[0][2]["name"])
            else:
                validated.append(relic_name)
        return validated
    
    def handle_command(text: str) -> str:
        """Process voice commands."""
        
        # Refresh from save file before processing command
        recorder.refresh_from_save()
        
        # Parse intent
        parsed = parser.parse(text)
        intent = parsed.get("intent", "unknown")
        
        # Validate card and relic names against knowledge base
        if "cards" in parsed and parsed["cards"]:
            parsed["cards"] = validate_card_names(parsed["cards"])
        if "relics" in parsed and parsed["relics"]:
            parsed["relics"] = validate_relic_names(parsed["relics"])
        
        logger.info(f"Parsed intent: {intent}, cards: {parsed.get('cards', [])}")
        
        # Handle based on intent
        if intent == "status":
            return recorder.get_run_status()
        
        elif intent == "summary":
            return recorder.create_summary_file()
        
        elif intent == "sync" or intent == "refresh":
            return recorder.refresh_from_save()
        
        elif intent == "card_choice":
            options = parsed.get("cards", [])
            if len(options) >= 2:
                return recorder.set_card_choice(options)
            return "What are your card options?"
        
        elif intent == "relic_choice":
            options = parsed.get("relics", [])
            if len(options) >= 2:
                return recorder.set_relic_choice(options)
            return "What are your relic options?"
        
        elif intent == "clear_choice":
            return recorder.clear_choice()
        
        # Unknown or unsupported intents
        else:
            return "Sorry, I didn't understand that command."
    
    return handle_command


def main():
    """Main entry point."""
    print("=" * 60)
    print("Slay the Spire Run Status Recorder")
    print("=" * 60)
    print("\nInitializing...")
    
    # Initialize components
    recorder = StatusRecorder()
    parser = CommandParser()
    handler = create_command_handler(recorder, parser)
    
    # Check if we found an active game
    startup_message = "Voice advisor ready"
    if recorder.current_run:
        r = recorder.current_run
        char = r['character']
        asc = r['ascension']
        act = r['act']
        hp = r['hp']
        max_hp = r['max_hp']
        
        print(f"\n✓ Found active game: {char} A{asc}, Act {act}")
        print(f"  HP: {hp}/{max_hp}")
        startup_message = f"Resuming {char} run"
    else:
        print("\n⚠ No active game found in save file")
        print("  Start a game in Slay the Spire, then use voice commands")
        startup_message = "Current game not found"
    
    # Configure voice interface
    config = VoiceConfig(
        push_to_talk_key='f1',
        tts_engine='edge-tts',
        tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
        whisper_backend='groq',
        whisper_model=os.getenv("WHISPER_MODEL", "whisper-large-v3"),
        whisper_fallback_model=os.getenv("WHISPER_FALLBACK", "whisper-large-v3-turbo")
    )
    
    voice = VoiceInterface(config)
    voice.on_command = handler
    voice.startup_message = startup_message
    
    print("\n✓ Ready!")
    print("\nControls:")
    print("  - Hold F1 to speak")
    print("  - Release to process")
    print("  - Press ESC to exit")
    print("\nListening for commands...\n")
    
    # Start the voice interface loop
    voice.run()


if __name__ == "__main__":
    main()
