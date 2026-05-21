#!/usr/bin/env python
"""
Main Voice Recorder Script for Slay the Spire.

Workflow:
1. Cleanup old backups (>24 hours)
2. Find and parse latest autosave
3. Generate Run_Summary.md
4. Listen for F1 to record voice
5. Transcribe audio with Groq Whisper
6. Correct names with LLM (4-model fallback)
7. Update "Current choice:" section
8. Press ESC to exit

Usage:
    python scripts/voice_recorder.py
"""

import sys
from pathlib import Path
from datetime import datetime
import keyboard

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.core.save_parser import SaveParser
from src.knowledge.knowledge_base import KnowledgeBase
from src.summary.summary_generator import RunSummaryGenerator
from src.summary.choice_updater import ChoiceUpdater
from src.voice.voice_recorder import VoiceRecorder
from src.voice.transcriber import AudioTranscriber
from src.voice.tts import speak
from src.llm.name_corrector import NameCorrector
from src.utils.logger import setup_logger, log_operation

# Initialize logger
log = setup_logger("general")


class VoiceRecorderApp:
    """Main application for voice-controlled run tracking."""
    
    def __init__(self):
        """Initialize the application."""
        log.info("=" * 60)
        log.info("Slay the Spire Voice Recorder - Starting")
        log.info("=" * 60)
        
        print("\n" + "=" * 60)
        print("🎮 Slay the Spire Voice Recorder")
        print("=" * 60)
        
        # Validate configuration
        try:
            Config.validate()
        except ValueError as e:
            log.error(f"Configuration error: {e}")
            print(f"\n❌ Configuration Error: {e}")
            sys.exit(1)
        
        # Create required directories
        Config.create_directories()
        
        # Initialize components
        print("\n📦 Initializing components...")
        
        self.backup_mgr = BackupManager(
            Config.GAME_SAVES_DIR,
            Config.BACKUP_DIR,
            max_age_hours=Config.BACKUP_MAX_AGE_HOURS
        )
        self.parser = SaveParser()
        self.kb = KnowledgeBase()
        self.summary_gen = RunSummaryGenerator(knowledge_base=self.kb)
        self.choice_updater = ChoiceUpdater()
        self.recorder = VoiceRecorder()
        self.transcriber = AudioTranscriber()
        self.name_corrector = NameCorrector(knowledge_base=self.kb)
        
        self.run_data = None
        
        print("✅ All components initialized")
        log.info("All components initialized successfully")
    
    def startup_sequence(self):
        """Run startup sequence."""
        # Cleanup old backups
        deleted = self.backup_mgr.cleanup_old_backups()
        
        # Find latest save
        latest_save = self.backup_mgr.find_latest_autosave()
        
        if not latest_save:
            log.error("No autosave file found")
            print("\n❌ No autosave found")
            print(f"   Looking in: {Config.GAME_SAVES_DIR}")
            print("   Make sure you have an active run in Slay the Spire")
            sys.exit(1)
        
        # Create backup
        backup = self.backup_mgr.create_backup(latest_save)
        
        if not backup:
            log.error("Failed to create backup")
            print("\n❌ Backup failed")
            sys.exit(1)
        
        # Parse save
        self.run_data = self.parser.parse_and_extract(backup)
        
        if not self.run_data:
            log.error("Failed to parse save file")
            print("\n❌ Parse failed")
            sys.exit(1)
        
        # Generate Run_Summary.md
        summary = self.summary_gen.generate_summary(
            self.run_data,
            Config.RUN_SUMMARY_PATH,
            preserve_choice=True
        )
        
        # Show summary
        print(f"\n🎮 {self.run_data['character']} Run (Ascension {self.run_data['ascension']}, Act {self.run_data['act']})")
        print(f"   HP: {self.run_data['current_hp']}/{self.run_data['max_hp']} | Gold: {self.run_data['gold']}")
        print(f"   Deck: {len(self.run_data['deck'])} cards | Relics: {len(self.run_data['relics'])}")
        
        log.info("Startup sequence complete")
        print("\n✅ Ready!")
    
    def refresh_run_data(self):
        """
        Refresh run data from the latest save file.
        
        This ensures HP, gold, deck, relics, and other stats are up-to-date
        before recording new choices.
        
        Returns:
            True if refresh successful, False otherwise
        """
        log.info("Refreshing run data from latest save")
        
        # Find latest save
        latest_save = self.backup_mgr.find_latest_autosave()
        
        if not latest_save:
            log.error("No autosave file found during refresh")
            print("\n⚠️  Warning: Could not find latest save file")
            return False
        
        # Create backup
        backup = self.backup_mgr.create_backup(latest_save)
        
        if not backup:
            log.error("Failed to create backup during refresh")
            print("\n⚠️  Warning: Backup failed during refresh")
            return False
        
        # Parse save
        refreshed_data = self.parser.parse_and_extract(backup)
        
        if not refreshed_data:
            log.error("Failed to parse save file during refresh")
            print("\n⚠️  Warning: Failed to parse save file")
            return False
        
        # Update run data
        self.run_data = refreshed_data
        
        # Regenerate summary with updated stats (preserve existing choices)
        summary = self.summary_gen.generate_summary(
            self.run_data,
            Config.RUN_SUMMARY_PATH,
            preserve_choice=True
        )
        
        log.info("Run data refreshed successfully")
        log_operation(log, "refresh_complete", {
            "hp": f"{self.run_data['current_hp']}/{self.run_data['max_hp']}",
            "gold": self.run_data['gold'],
            "deck_size": len(self.run_data['deck']),
            "relic_count": len(self.run_data['relics'])
        })
        
        return True
    
    def process_voice_input(self):
        """Record and process voice input."""
        # Refresh run data from latest save file before recording choices
        # This ensures HP, gold, deck, relics, etc. are up-to-date
        print("\n🔄 Refreshing stats from save file...")
        if not self.refresh_run_data():
            print("⚠️  Continuing with cached data (stats may be outdated)")
        
        # Record audio
        temp_audio_path = Config.PROCESSED_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        if not self.recorder.record_to_file(temp_audio_path):
            return
        
        # Transcribe
        text = self.transcriber.transcribe_audio(temp_audio_path)
        
        if not text:
            print("❌ Transcription failed")
            return
        
        print(f"\n📝 You said: \"{text}\"")
        
        # Parse text to track which specific words have upgrade keywords after them
        import re
        import string
        upgrade_keywords = ['plus', 'upgrade', 'upgraded']
        
        # Build upgrade map: track which words are followed by upgrade keywords
        # Example: "strike plus defend" → {"strike": True, "defend": False}
        words = text.split()
        upgrade_map = {}  # word (lowercase) → is_upgraded
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
            # Use stripped version for consistency
            cleaned_words.append(word_stripped)
            # Default to not upgraded (will be set to True if followed by upgrade keyword)
            if word_lower not in upgrade_map:
                upgrade_map[word_lower] = False
            
            i += 1
        
        # Build cleaned text without upgrade keywords
        cleaned_text = ' '.join(cleaned_words)
        
        # Show what we're analyzing
        has_upgrades = any(upgrade_map.values())
        if has_upgrades:
            upgraded_words = [w for w in cleaned_words if upgrade_map.get(w.lower(), False)]
            print(f"🔍 Analyzing: \"{cleaned_text}\"")
            print(f"⬆️  Upgrade markers detected after: {', '.join(upgraded_words)}")
        else:
            print(f"🔍 Analyzing: \"{cleaned_text}\"")
        
        # Correct names using LLM (with cleaned text)
        character = self.run_data['character'].lower()
        
        # Debug: show what we're sending to LLM
        print(f"   📤 Sending to LLM for {character.upper()}: \"{cleaned_text}\"")
        
        cards, relics = self.name_corrector.correct_names(cleaned_text, character)
        
        # Deduplicate matches (prevents "mutagenic strength" from matching twice)
        cards = list(dict.fromkeys(cards))  # Preserves order while removing duplicates
        relics = list(dict.fromkeys(relics))
        
        # Debug: Check if all words were matched
        if cards or relics:
            matched_words = set()
            for card in cards:
                # Add all words from matched card names
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
        
        # Apply upgrade detection to matched cards
        upgraded_cards = []
        for card_name in cards:
            # Check if this specific card should be upgraded
            # Match card name words against upgrade_map
            # Also check card name with hyphens/spaces normalized
            card_words = card_name.lower().replace('-', ' ').split()
            is_card_upgraded = any(upgrade_map.get(word, False) for word in card_words)
            
            if is_card_upgraded:
                upgraded_cards.append(f"{card_name}+")
            else:
                upgraded_cards.append(card_name)
        
        # Show matched items WITH upgrade status
        matched_items = []
        matched_items.extend(upgraded_cards)
        if relics:
            matched_items.extend(relics)
        
        print(f"✅ Matched: {', '.join(matched_items)}")
        
        # Show upgrade details if any
        if any('+' in card for card in upgraded_cards):
            upgraded_names = [card.replace('+', '') for card in upgraded_cards if '+' in card]
            print(f"   ⬆️  Upgraded: {', '.join(upgraded_names)}")
        
        # Format choices with descriptions using summary generator formatter
        choices = []
        
        for i, card_name in enumerate(cards):
            # Use the pre-computed upgraded card name
            card_id = upgraded_cards[i]
            
            # Use summary generator formatter for consistent single-line formatting
            formatted = self.summary_gen._format_card_with_details(card_id)
            choices.append(formatted)
        
        for relic_name in relics:
            # Relics don't have upgrades, format normally
            relic_data = self.kb.get_relic_data(relic_name)
            if relic_data:
                description = relic_data.get('description', '').replace('\n', ' ').strip()
                choices.append(f"{relic_name}: {description}")
            else:
                choices.append(relic_name)
        
        # Update choice section
        success = self.choice_updater.update_choice_section(
            Config.RUN_SUMMARY_PATH,
            choices
        )
        
        if success:
            print("✅ Updated Run_Summary.md")
            # Vocal acknowledgment
            try:
                speak("Choice recorded")
            except:
                pass  # TTS is optional
        else:
            print("❌ Failed to update summary")
    
    def run(self):
        """Main application loop."""
        # Run startup
        self.startup_sequence()
        
        # Vocal acknowledgment
        try:
            speak("Voice recorder ready")
        except:
            pass  # TTS is optional
        
        # Instructions
        print("\n" + "=" * 60)
        print(f"▶️  Hold {Config.RECORDING_HOTKEY.upper()} to record  |  Press {Config.EXIT_HOTKEY.upper()} to exit")
        print("=" * 60)
        
        log.info("Entering main loop")
        
        # Main loop
        try:
            while True:
                # Check for exit
                if keyboard.is_pressed(Config.EXIT_HOTKEY.lower()):
                    print("\n👋 Goodbye!")
                    log.info("User requested exit")
                    break
                
                # Check for F1
                if keyboard.is_pressed(Config.RECORDING_HOTKEY.lower()):
                    self.process_voice_input()
                
                # Small delay to avoid CPU spinning
                import time
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print(f"\n\n👋 Interrupted, exiting...")
            log.info("KeyboardInterrupt received")
        
        # Cleanup
        print("\n✅ Goodbye!")
        log.info("Application shutdown")
        log.info("=" * 60)


def main():
    """Entry point."""
    try:
        app = VoiceRecorderApp()
        app.run()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal Error: {e}")
        print(f"\nCheck logs: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
