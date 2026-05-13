#!/usr/bin/env python
"""
Voice Advisor with Gemini API + Edge TTS.

This script launches the voice interface using:
- Gemini 1.5 Flash for fast, intelligent responses
- Edge TTS for natural-sounding voice output
- Local database for run tracking

Usage:
    python scripts/voice_gemini.py

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

from src.advisor.gemini_advisor import GeminiAdvisor
from src.voice.voice_interface import VoiceInterface, VoiceConfig
from loguru import logger


def create_command_handler(advisor: GeminiAdvisor):
    """Create the command handler function."""
    
    def handle_command(text: str) -> str:
        """Process voice commands."""
        text_lower = text.lower().strip()
        
        # Run management commands
        if any(phrase in text_lower for phrase in ["new run", "start a run", "start run", "begin run"]):
            # Parse character and ascension
            for char in ["ironclad", "silent", "defect", "watcher"]:
                if char in text_lower:
                    # Try to find ascension number
                    import re
                    asc_match = re.search(r'(?:ascension|asc|a)?\s*(\d+)', text_lower)
                    ascension = int(asc_match.group(1)) if asc_match else 0
                    return advisor.start_run(char, ascension)
            return "Which character would you like to play? Ironclad, Silent, Defect, or Watcher?"
        
        if any(phrase in text_lower for phrase in ["end run", "run over", "died", "run ended"]):
            victory = any(word in text_lower for word in ["victory", "won", "beat", "killed the heart"])
            return advisor.end_run(victory=victory)
        
        if any(phrase in text_lower for phrase in ["run status", "current status", "where am i", "my status"]):
            return advisor.get_run_status()
        
        # Card/relic management
        if "add card" in text_lower or "picked" in text_lower and "card" in text_lower:
            # Extract card name
            import re
            match = re.search(r'(?:add card|picked)\s+(.+?)(?:\s+card)?$', text_lower)
            if match:
                return advisor.add_card(match.group(1).strip())
        
        if "add relic" in text_lower or "got relic" in text_lower:
            import re
            match = re.search(r'(?:add relic|got relic|got)\s+(.+?)(?:\s+relic)?$', text_lower)
            if match:
                return advisor.add_relic(match.group(1).strip())
        
        # Default: chat with Gemini for strategic advice
        return advisor.chat_message(text)
    
    return handle_command


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🎮 SLAY THE SPIRE VOICE ADVISOR")
    print("=" * 60)
    print("Powered by: Gemini 1.5 Flash + Edge TTS")
    print("=" * 60 + "\n")
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found in .env file!")
        print("   Add your API key to .env file and try again.")
        return
    
    try:
        # Initialize Gemini advisor
        print("Initializing Gemini advisor...")
        advisor = GeminiAdvisor()
        print("✅ Gemini advisor ready")
        
        # Configure voice interface with Edge TTS
        config = VoiceConfig(
            tts_engine="edge-tts",
            tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
            whisper_model="base",
            whisper_device="cuda",  # Use GPU for faster transcription
            push_to_talk_key="f1"
        )
        
        # Create voice interface
        print("Initializing voice interface...")
        interface = VoiceInterface(config)
        interface.on_command = create_command_handler(advisor)
        
        # Welcome message
        interface.startup_message = (
            "Voice advisor ready! I'm powered by Gemini and can help with your Slay the Spire runs. "
            "Press F1 and tell me about your run, or ask for strategic advice!"
        )
        
        # Run the interface
        interface.run()
        
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. A valid GEMINI_API_KEY in .env")
        print("  2. Installed: pip install google-generativeai edge-tts pygame")
        raise


if __name__ == "__main__":
    main()
