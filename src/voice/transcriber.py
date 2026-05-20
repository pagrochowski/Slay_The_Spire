"""
Audio Transcriber using Groq Whisper API.

Converts audio files to text using Groq's Whisper API with fallback models.
"""

import os
from pathlib import Path
from typing import Optional
from groq import Groq
from src.core.config import Config
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("voice")


class AudioTranscriber:
    """Transcribes audio using Groq Whisper API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize audio transcriber.
        
        Args:
            api_key: Groq API key (default: from Config)
        """
        self.api_key = api_key or Config.GROQ_API_KEY
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        self.primary_model = Config.WHISPER_PRIMARY_MODEL
        self.fallback_model = Config.WHISPER_FALLBACK_MODEL
        
        log.info("AudioTranscriber initialized")
        log_operation(log, "transcriber_init", {
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model
        })
    
    def transcribe_audio(
        self,
        audio_path: Path,
        language: str = "en"
    ) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (WAV format)
            language: Language code (default: "en")
            
        Returns:
            Transcribed text, or None if transcription failed
        """
        log.info(f"Transcribing audio: {audio_path.name}")
        log_operation(log, "transcribe_start", {
            "file": audio_path.name,
            "size": f"{audio_path.stat().st_size} bytes",
            "model": self.primary_model
        })
        
        # Try primary model
        result = self._transcribe_with_model(audio_path, self.primary_model, language)
        
        # Fallback to secondary model if primary fails
        if result is None:
            log.warning(f"Primary model failed, trying fallback: {self.fallback_model}")
            result = self._transcribe_with_model(audio_path, self.fallback_model, language)
        
        if result:
            log.info(f"Transcription successful")
            log_operation(log, "transcribe_complete", {
                "file": audio_path.name,
                "text_length": len(result),
                "text_preview": result[:100] if len(result) > 100 else result
            })
        else:
            log.error("Transcription failed with all models")
            log_operation(log, "transcribe_failed", {
                "file": audio_path.name
            }, level="ERROR")
        
        return result
    
    def _transcribe_with_model(
        self,
        audio_path: Path,
        model: str,
        language: str
    ) -> Optional[str]:
        """
        Transcribe using a specific Whisper model.
        
        Args:
            audio_path: Path to audio file
            model: Whisper model name
            language: Language code
            
        Returns:
            Transcribed text, or None if failed
        """
        try:
            # Open audio file
            with open(audio_path, 'rb') as audio_file:
                # Call Groq Whisper API
                transcription = self.client.audio.transcriptions.create(
                    file=(audio_path.name, audio_file.read()),
                    model=model,
                    language=language,
                    response_format="text"
                )
            
            # Extract text
            if isinstance(transcription, str):
                text = transcription
            else:
                text = transcription.text if hasattr(transcription, 'text') else str(transcription)
            
            text = text.strip()
            
            log.debug(f"Transcription with {model}: {text[:100]}...")
            
            return text if text else None
            
        except Exception as e:
            log.warning(f"Transcription failed with {model}: {e}")
            return None


if __name__ == "__main__":
    # Test the transcriber
    from src.voice.voice_recorder import VoiceRecorder
    from datetime import datetime
    
    print("Audio Transcriber Test")
    print("=" * 50)
    
    # Initialize transcriber
    try:
        transcriber = AudioTranscriber()
        print("\n1. Transcriber initialized")
        print(f"   Primary model: {transcriber.primary_model}")
        print(f"   Fallback model: {transcriber.fallback_model}")
    except ValueError as e:
        print(f"\n❌ Failed to initialize: {e}")
        exit(1)
    
    # Record audio
    print("\n2. Recording audio for transcription test...")
    recorder = VoiceRecorder()
    audio_path = Config.PROCESSED_DIR / f"test_transcribe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    if recorder.record_to_file(audio_path):
        print(f"\n3. Audio saved: {audio_path.name}")
        
        # Transcribe
        print("\n4. Transcribing audio...")
        text = transcriber.transcribe_audio(audio_path)
        
        if text:
            print(f"\n5. Transcription Result:")
            print(f"   Text: '{text}'")
            print(f"   Length: {len(text)} characters")
        else:
            print(f"\n5. Transcription failed")
    else:
        print(f"\n3. Audio recording failed")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
