"""
Simple TTS Module for Voice Acknowledgments.

Provides vocal feedback using Edge TTS (high quality) with pygame playback.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional
import pygame
from src.core.config import Config
from src.utils.logger import setup_logger, log_operation

# Initialize logger
log = setup_logger("voice")


class SimpleTTS:
    """Simple text-to-speech for voice acknowledgments."""
    
    def __init__(self, voice: str = "en-US-AriaNeural"):
        """
        Initialize TTS.
        
        Args:
            voice: Edge TTS voice name
        """
        self.voice = voice
        self.enabled = True
        
        try:
            import edge_tts
            self.edge_tts = edge_tts
            log.info(f"SimpleTTS initialized with voice: {voice}")
        except ImportError:
            log.warning("edge-tts not installed, TTS disabled")
            self.enabled = False
    
    def speak(self, text: str) -> None:
        """
        Speak text using Edge TTS.
        
        Args:
            text: Text to speak
        """
        if not self.enabled:
            return
        
        try:
            asyncio.run(self._async_speak(text))
        except Exception as e:
            log.error(f"TTS error: {e}")
    
    async def _async_speak(self, text: str) -> None:
        """
        Async speak implementation.
        
        Args:
            text: Text to speak
        """
        try:
            # Create temp file for audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio with Edge TTS
            communicate = self.edge_tts.Communicate(text, self.voice)
            await communicate.save(temp_path)
            
            # Play audio with pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            
            # Cleanup temp file
            Path(temp_path).unlink(missing_ok=True)
            
            log.debug(f"TTS spoke: {text}")
            
        except Exception as e:
            log.error(f"TTS playback error: {e}")


# Global TTS instance
_tts_instance: Optional[SimpleTTS] = None


def get_tts() -> SimpleTTS:
    """Get global TTS instance (singleton)."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = SimpleTTS()
    return _tts_instance


def speak(text: str) -> None:
    """
    Speak text using global TTS instance.
    
    Args:
        text: Text to speak
    """
    tts = get_tts()
    tts.speak(text)


if __name__ == "__main__":
    # Test TTS
    print("Testing TTS...")
    speak("Voice recorder ready")
    print("Done!")
