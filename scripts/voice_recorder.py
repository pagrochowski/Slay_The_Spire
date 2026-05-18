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
                # Use the best match from knowledge base
                validated.append(matches[0][2]["name"])
            else:
                # Keep original if no match found
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
                # Use the best match from knowledge base
                validated.append(matches[0][2]["name"])
            else:
                # Keep original if no match found
                validated.append(relic_name)
        return validated
    
    def handle_command(text: str) -> str:
        """Process voice commands."""
        
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
        if intent == "start_run":
            char = parsed.get("character")
            asc = parsed.get("ascension", 0) or 0
            if char:
                return recorder.start_run(char, asc)
            return "Which character? Ironclad, Silent, Defect, or Watcher?"
        
        elif intent == "end_run":
            victory = parsed.get("victory", False)
            cause = parsed.get("cause")
            return recorder.end_run(victory=victory, cause=cause)
        
        elif intent == "status":
            return recorder.get_run_status()
        
        elif intent == "summary":
            return recorder.create_summary_file()
        
        elif intent == "sync":
            return recorder.sync_from_summary()
        
        elif intent == "add_card":
            cards = parsed.get("cards", [])
            if cards:
                return recorder.add_card(cards[0])
            return "Which card did you pick?"
        
        elif intent == "remove_card":
            cards = parsed.get("cards", [])
            if cards:
                return recorder.remove_card(cards[0])
            return "Which card to remove?"
        
        elif intent == "upgrade_card":
            cards = parsed.get("cards", [])
            if cards:
                return recorder.upgrade_card(cards[0])
            return "Which card to upgrade?"
        
        elif intent == "add_relic":
            relics = parsed.get("relics", [])
            if relics:
                return recorder.add_relic(relics[0])
            return "Which relic did you get?"
        
        elif intent == "remove_relic":
            relics = parsed.get("relics", [])
            if relics:
                return recorder.remove_relic(relics[0])
            return "Which relic to remove?"
        
        elif intent == "set_boss":
            boss = parsed.get("boss")
            if boss:
                return recorder.set_boss(boss)
            return "Which boss?"
        
        elif intent == "update_act":
            act = parsed.get("act")
            if act:
                return recorder.update_act(act)
            return "Which act?"
        
        elif intent == "update_hp":
            hp = parsed.get("hp")
            max_hp = parsed.get("max_hp")
            hp_delta = parsed.get("hp_delta")
            max_hp_delta = parsed.get("max_hp_delta")
            
            # Handle relative HP change
            if hp_delta is not None:
                run = recorder.run_manager.get_active_run()
                if run:
                    new_hp = max(0, min(run["max_hp"], run["hp"] + hp_delta))
                    return recorder.update_hp(current=new_hp)
                return "No active run."
            
            # Handle relative max HP change
            elif max_hp_delta is not None:
                run = recorder.run_manager.get_active_run()
                if run:
                    new_max_hp = run["max_hp"] + max_hp_delta
                    new_hp = run["hp"] + max_hp_delta if max_hp_delta > 0 else run["hp"]
                    new_hp = min(new_hp, new_max_hp)
                    return recorder.update_hp(current=new_hp, max_hp=new_max_hp)
                return "No active run."
            
            # Handle absolute values
            return recorder.update_hp(current=hp, max_hp=max_hp)
        
        elif intent == "update_gold":
            gold = parsed.get("gold")
            gold_delta = parsed.get("gold_delta")
            
            if gold_delta is not None:
                run = recorder.run_manager.get_active_run()
                if run:
                    new_gold = max(0, run["gold"] + gold_delta)
                    return recorder.update_gold(new_gold)
                return "No active run."
            
            if gold is not None:
                return recorder.update_gold(gold)
            return "How much gold?"
        
        # Decision point tracking (for external advisor)
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
    
    # Auto-sync from file if it was modified after last run update
    from pathlib import Path
    from datetime import datetime
    
    summary_file = Path("Run_Summary.md")
    if summary_file.exists() and recorder.resumed_run:
        file_mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)
        run_updated = datetime.fromisoformat(recorder.resumed_run.get("last_updated", "2000-01-01T00:00:00"))
        
        if file_mtime > run_updated:
            print("\n⚠ Summary file was modified - syncing changes...")
            sync_result = recorder.sync_from_summary()
            print(f"  {sync_result}")
    
    # Check if we resumed an existing run
    startup_message = "Voice advisor ready"
    if recorder.resumed_run:
        char = recorder.resumed_run['character']
        asc = recorder.resumed_run['ascension']
        act = recorder.resumed_run.get('act', 1)
        hp = recorder.resumed_run['hp']
        max_hp = recorder.resumed_run['max_hp']
        deck_size = len(recorder.run_manager.get_full_deck())
        
        print(f"\n✓ Resumed run: {char} A{asc}, Act {act}")
        print(f"  HP: {hp}/{max_hp}, Deck: {deck_size} cards")
        startup_message = f"Resuming {char} run"
    else:
        print("\n✓ No active run - say 'start new run' to begin")
    
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
