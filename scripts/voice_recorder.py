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
    
    def process_voice_input(self):
        """Record and process voice input."""
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
        
        # Correct names using LLM
        character = self.run_data['character'].lower()
        cards, relics = self.name_corrector.correct_names(text, character)
        
        if not cards and not relics:
            print("⚠️  No cards or relics matched")
            return
        
        # Show matched items
        matched_items = []
        if cards:
            matched_items.extend(cards)
        if relics:
            matched_items.extend(relics)
        
        print(f"✅ Matched: {', '.join(matched_items)}")
        
        # Format choices with descriptions
        choices = []
        
        for card_name in cards:
            card_data = self.kb.get_card_data(card_name)
            if card_data:
                cost = card_data.get('cost', '?')
                card_type = card_data.get('type', '').capitalize()
                description = card_data.get('description', '')
                choices.append(f"{card_name} [{cost}] ({card_type}): {description}")
            else:
                choices.append(card_name)
        
        for relic_name in relics:
            relic_data = self.kb.get_relic_data(relic_name)
            if relic_data:
                description = relic_data.get('description', '')
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
