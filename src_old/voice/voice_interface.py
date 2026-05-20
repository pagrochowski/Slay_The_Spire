"""
Voice interface for the Slay the Spire advisor.

Features:
- Push-to-talk with F1 key (configurable)
- Speech-to-text using faster-whisper (local)
- Text-to-speech using pyttsx3 (offline) or edge-tts (higher quality)

Usage:
    python -m src.voice.voice_interface

Requirements:
    pip install faster-whisper sounddevice numpy keyboard pyttsx3
    
Optional for higher quality TTS:
    pip install edge-tts

Note: faster-whisper requires CUDA for GPU acceleration.
      Falls back to CPU if CUDA not available.
"""

import io
import sys
import time
import wave
import queue
import threading
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class VoiceConfig:
    """Configuration for voice interface."""
    # Hotkey settings
    push_to_talk_key: str = "f1"
    
    # Audio settings
    sample_rate: int = 16000  # Whisper expects 16kHz
    channels: int = 1
    dtype: str = "int16"
    
    # Whisper settings
    whisper_backend: str = "groq"  # groq (API, better accuracy) or local (faster-whisper)
    whisper_model: str = "whisper-large-v3"  # Primary: whisper-large-v3 (better accuracy)
    whisper_fallback_model: str = "whisper-large-v3-turbo"  # Fallback: turbo (faster)
    whisper_device: str = "cuda"  # cuda, cpu, auto (only for local backend)
    whisper_compute_type: str = "float16"  # float16, int8, int8_float16 (only for local)
    
    # TTS settings
    tts_engine: str = "pyttsx3"  # pyttsx3, edge-tts
    tts_rate: int = 175  # Words per minute for pyttsx3
    tts_voice: Optional[str] = None  # Specific voice ID
    
    # Behavior
    min_audio_length: float = 0.5  # Minimum recording length in seconds
    max_audio_length: float = 30.0  # Maximum recording length
    silence_threshold: float = 500  # Amplitude threshold for silence detection


class SpeechToText:
    """Speech-to-text using Groq API or local faster-whisper."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.model = None  # For local whisper
        self.groq_client = None  # For Groq API
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the Whisper backend."""
        if self.config.whisper_backend == "groq":
            return self._init_groq()
        else:
            return self._init_local()
    
    def _init_groq(self) -> bool:
        """Initialize Groq Whisper API."""
        try:
            import os
            from groq import Groq
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.error("GROQ_API_KEY not found for Whisper API")
                return False
            
            self.groq_client = Groq(api_key=api_key)
            logger.info(f"Groq Whisper API initialized (primary: {self.config.whisper_model}, fallback: {self.config.whisper_fallback_model})")
            self._initialized = True
            return True
        except ImportError:
            logger.error("groq not installed. Run: pip install groq")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Groq Whisper: {e}")
            return False
    
    def _init_local(self) -> bool:
        """Initialize local faster-whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            # Use base model for local
            local_model = self.config.whisper_model if self.config.whisper_backend == "local" else "base"
            logger.info(f"Loading local Whisper model: {local_model}")
            
            # Try GPU first, fall back to CPU
            def try_load_model(device: str, compute_type: str) -> WhisperModel:
                """Load model and test it works."""
                model = WhisperModel(
                    local_model,
                    device=device,
                    compute_type=compute_type
                )
                # Test transcription to catch cuBLAS errors early
                test_audio = np.zeros(16000, dtype=np.float32)  # 1 second silence
                list(model.transcribe(test_audio, language="en"))
                return model
            
            try:
                self.model = try_load_model(
                    self.config.whisper_device,
                    self.config.whisper_compute_type
                )
                logger.info(f"Whisper loaded on {self.config.whisper_device}")
            except Exception as e:
                logger.warning(f"GPU not available ({e}), falling back to CPU")
                self.model = try_load_model("cpu", "int8")
                logger.info("Whisper loaded on CPU")
            
            self._initialized = True
            return True
            
        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")
            return False
    
    def _reinit_cpu(self):
        """Reinitialize model on CPU after CUDA failure."""
        if self.config.whisper_backend == "groq":
            return  # N/A for API
        try:
            from faster_whisper import WhisperModel
            logger.info("Reinitializing Whisper on CPU due to CUDA error...")
            self.model = WhisperModel(
                "base",
                device="cpu",
                compute_type="int8"
            )
            logger.info("Whisper reloaded on CPU")
        except Exception as e:
            logger.error(f"Failed to reinitialize on CPU: {e}")
            self._initialized = False
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio to text."""
        if not self._initialized:
            logger.error("Whisper not initialized")
            return ""
        
        if self.config.whisper_backend == "groq":
            return self._transcribe_groq(audio_data)
        else:
            return self._transcribe_local(audio_data)
    
    def _transcribe_groq(self, audio_data: np.ndarray, use_fallback: bool = False) -> str:
        """Transcribe using Groq Whisper API with fallback support."""
        import tempfile
        
        # Select model (primary or fallback)
        model = self.config.whisper_fallback_model if use_fallback else self.config.whisper_model
        
        try:
            # Save audio to temp WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            # Write WAV file
            import wave
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # int16
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Send to Groq
            with open(temp_path, "rb") as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(temp_path, audio_file.read()),
                    model=model,
                    temperature=0,
                    language="en",
                    response_format="text",
                )
            
            # Clean up temp file
            import os
            os.unlink(temp_path)
            
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            logger.debug(f"Transcribed (Groq {model}): {text}")
            return text
            
        except Exception as e:
            error_str = str(e)
            # Try fallback model if primary fails
            if not use_fallback:
                logger.warning(f"Primary whisper model ({model}) failed: {e}, trying fallback...")
                return self._transcribe_groq(audio_data, use_fallback=True)
            
            logger.error(f"Groq transcription failed (both models): {e}")
            return ""
    
    def _transcribe_local(self, audio_data: np.ndarray) -> str:
        """Transcribe using local faster-whisper."""
        try:
            # Convert to float32 for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            segments, info = self.model.transcribe(
                audio_float,
                language="en",
                beam_size=5,
                vad_filter=True,  # Voice activity detection
            )
            
            # Combine all segments
            text = " ".join(segment.text.strip() for segment in segments)
            logger.debug(f"Transcribed (local): {text}")
            return text.strip()
            
        except Exception as e:
            error_msg = str(e)
            # Check for CUDA library errors and fall back to CPU
            if "cublas" in error_msg.lower() or "cuda" in error_msg.lower():
                logger.warning(f"CUDA error: {e}")
                self._reinit_cpu()
                # Retry on CPU
                if self._initialized:
                    return self._transcribe_local(audio_data)
            logger.error(f"Transcription failed: {e}")
            return ""


class TextToSpeech:
    """Text-to-speech output with interrupt support."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.engine = None
        self._initialized = False
        self._speaking = False
        self._interrupt_requested = False
    
    def initialize(self) -> bool:
        """Initialize the TTS engine."""
        if self.config.tts_engine == "pyttsx3":
            return self._init_pyttsx3()
        elif self.config.tts_engine == "edge-tts":
            return self._init_edge_tts()
        else:
            logger.error(f"Unknown TTS engine: {self.config.tts_engine}")
            return False
    
    def _init_pyttsx3(self) -> bool:
        """Initialize TTS using Windows System.Speech via PowerShell."""
        try:
            import subprocess
            
            # Test that System.Speech is available
            test_script = '''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Dispose()
'''
            result = subprocess.run(
                ["powershell", "-Command", test_script],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"System.Speech not available: {result.stderr.decode()}")
                return False
            
            self._initialized = True
            logger.info("Windows System.Speech TTS initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            return False
    
    def _init_edge_tts(self) -> bool:
        """Initialize edge-tts (async)."""
        try:
            import edge_tts
            self._initialized = True
            logger.info("edge-tts initialized")
            return True
        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            return False
    
    def interrupt(self) -> None:
        """Interrupt any ongoing speech."""
        if self._speaking:
            self._interrupt_requested = True
            logger.info("🔇 Speech interrupted")
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass  # pygame not available or not initialized
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._speaking
    
    def speak(self, text: str) -> None:
        """Speak the given text."""
        if not self._initialized:
            logger.error("TTS not initialized")
            return
        
        # Validate text has actual content
        clean_check = text.replace('.', '').replace('!', '').replace('?', '').strip()
        if not clean_check or len(clean_check) < 5:
            logger.warning(f"Response too short to speak: '{text}'")
            text = "I'm not sure what to say about that."
        
        # Truncate very long responses for TTS (keep first ~500 chars)
        if len(text) > 500:
            # Find a sentence break near 500 chars
            truncate_at = text.rfind('.', 0, 500)
            if truncate_at > 200:
                text = text[:truncate_at + 1]
            else:
                text = text[:500] + "..."
            logger.debug(f"Truncated response for TTS to {len(text)} chars")
        
        if self.config.tts_engine == "pyttsx3":
            self._speak_pyttsx3(text)
        elif self.config.tts_engine == "edge-tts":
            self._speak_edge_tts(text)
    
    def _speak_pyttsx3(self, text: str) -> None:
        """Speak using pyttsx3 via subprocess to avoid threading issues."""
        try:
            import subprocess
            import sys
            
            # Clean text for TTS (remove markdown)
            clean_text = text.replace('**', '').replace('*', '').replace('#', '').replace('`', '')
            # Escape quotes for command line
            clean_text = clean_text.replace('"', "'")
            logger.debug(f"TTS speaking: {clean_text[:50]}...")
            
            # Use PowerShell's built-in SAPI for more reliable TTS
            # This runs in a subprocess to avoid threading conflicts
            ps_script = f'''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 2
$synth.Speak("{clean_text}")
'''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=60  # Max 60 seconds for TTS
            )
            
            if result.returncode != 0:
                logger.error(f"PowerShell TTS error: {result.stderr.decode()}")
            else:
                logger.debug("TTS finished speaking")
            
        except subprocess.TimeoutExpired:
            logger.error("TTS timed out")
        except Exception as e:
            logger.error(f"TTS speak failed: {e}")
    
    def _speak_edge_tts(self, text: str) -> None:
        """Speak using edge-tts with natural voices."""
        import asyncio
        import tempfile
        import subprocess
        
        self._speaking = True
        self._interrupt_requested = False
        
        async def _generate_and_play():
            try:
                import edge_tts
                
                # Clean text for TTS
                clean_text = text.replace('**', '').replace('*', '').replace('#', '').replace('`', '')
                
                # Use configured voice or default
                voice = getattr(self.config, 'tts_voice', 'en-US-AriaNeural')
                logger.debug(f"Edge TTS speaking with voice {voice}: {clean_text[:50]}...")
                
                # Generate audio
                communicate = edge_tts.Communicate(clean_text, voice)
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name
                
                await communicate.save(temp_path)
                
                # Check for interrupt after generation
                if self._interrupt_requested:
                    Path(temp_path).unlink(missing_ok=True)
                    return
                
                # Wait for file to be fully written
                await asyncio.sleep(0.1)
                
                # Play using pygame or fallback
                try:
                    # Try pygame first (best quality)
                    import pygame
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and not self._interrupt_requested:
                        await asyncio.sleep(0.05)  # Faster check for interrupt
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                except Exception as pygame_error:
                    logger.warning(f"pygame failed: {pygame_error}, trying playsound")
                    # Fallback to playsound (more robust for MP3)
                    try:
                        from playsound import playsound
                        playsound(temp_path)
                    except ImportError:
                        # Last resort: Windows Media Player via PowerShell
                        subprocess.run(
                            ["powershell", "-Command", 
                             f'Add-Type -AssemblyName presentationCore; '
                             f'$mediaPlayer = New-Object System.Windows.Media.MediaPlayer; '
                             f'$mediaPlayer.Open([System.Uri]::new("{temp_path}")); '
                             f'$mediaPlayer.Play(); '
                             f'Start-Sleep -Seconds 10'],
                            capture_output=True,
                            timeout=60
                        )
                
                logger.debug("Edge TTS finished speaking")
                Path(temp_path).unlink(missing_ok=True)
                
            except Exception as e:
                logger.error(f"edge-tts failed: {e}")
            finally:
                self._speaking = False
        
        # Run async function
        try:
            asyncio.run(_generate_and_play())
        except RuntimeError:
            # Already in async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate_and_play())
            loop.close()


class AudioRecorder:
    """Audio recorder with push-to-talk."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self._stream = None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        if self.is_recording:
            self.audio_queue.put(indata.copy())
    
    def start_recording(self) -> None:
        """Start recording audio."""
        self.audio_queue = queue.Queue()  # Clear queue
        self.is_recording = True
        
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            callback=self._audio_callback
        )
        self._stream.start()
        logger.debug("Recording started")
    
    def stop_recording(self) -> np.ndarray:
        """Stop recording and return audio data."""
        self.is_recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        # Collect all audio from queue
        chunks = []
        while not self.audio_queue.empty():
            chunks.append(self.audio_queue.get())
        
        if not chunks:
            return np.array([], dtype=np.int16)
        
        audio_data = np.concatenate(chunks, axis=0).flatten()
        logger.debug(f"Recording stopped, {len(audio_data)} samples")
        return audio_data


class VoiceInterface:
    """
    Main voice interface for the STS Advisor.
    
    Press F1 (or configured key) to start speaking.
    Release F1 (or press again) to stop and process.
    """
    
    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        on_command: Optional[Callable[[str], str]] = None
    ):
        self.config = config or VoiceConfig()
        self.on_command = on_command
        
        self.stt = SpeechToText(self.config)
        self.tts = TextToSpeech(self.config)
        self.recorder = AudioRecorder(self.config)
        
        self._running = False
        self._recording = False
    
    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("Initializing voice interface...")
        
        # Initialize STT
        if not self.stt.initialize():
            logger.error("Failed to initialize speech-to-text")
            return False
        
        # Initialize TTS
        if not self.tts.initialize():
            logger.error("Failed to initialize text-to-speech")
            return False
        
        logger.info("Voice interface initialized successfully")
        return True
    
    def _on_key_press(self, key) -> None:
        """Handle key press for push-to-talk."""
        # Always interrupt TTS when F1 is pressed
        if self.tts.is_speaking():
            self.tts.interrupt()
            return  # Don't start recording if we just interrupted
        
        if not self._recording:
            self._recording = True
            logger.info("🎤 Recording... (release key to stop)")
            self.recorder.start_recording()
    
    def _on_key_release(self, key) -> None:
        """Handle key release for push-to-talk."""
        if self._recording:
            self._recording = False
            logger.info("⏹️ Processing...")
            
            # Get audio
            audio_data = self.recorder.stop_recording()
            
            if len(audio_data) < self.config.sample_rate * self.config.min_audio_length:
                logger.warning("Recording too short, ignoring")
                return
            
            # Transcribe
            text = self.stt.transcribe(audio_data)
            
            if not text:
                logger.warning("No speech detected")
                self.tts.speak("I didn't catch that. Please try again.")
                return
            
            logger.info(f"📝 You said: {text}")
            
            # Process command
            if self.on_command:
                response = self.on_command(text)
            else:
                response = f"You said: {text}"
            
            logger.info(f"🔊 Responding: {response}")
            
            # Speak response
            self.tts.speak(response)
    
    def run(self) -> None:
        """Run the voice interface main loop."""
        try:
            import keyboard
        except ImportError:
            logger.error("keyboard library not installed. Run: pip install keyboard")
            return
        
        if not self.initialize():
            logger.error("Failed to initialize voice interface")
            return
        
        self._running = True
        
        print("\n" + "=" * 50)
        print("🎮 STS VOICE ADVISOR")
        print("=" * 50)
        print(f"Press and hold [{self.config.push_to_talk_key.upper()}] to speak")
        print("Press [ESC] to exit")
        print("=" * 50 + "\n")
        
        # Register hotkey handlers
        keyboard.on_press_key(self.config.push_to_talk_key, lambda e: self._on_key_press(e))
        keyboard.on_release_key(self.config.push_to_talk_key, lambda e: self._on_key_release(e))
        
        # Startup message (use custom message if set, otherwise default)
        startup_msg = getattr(self, 'startup_message', None) or "Voice advisor ready. Press F1 and speak your command."
        self.tts.speak(startup_msg)
        
        # Wait for ESC to exit
        keyboard.wait('esc')
        
        self._running = False
        logger.info("Voice interface stopped")
    
    def process_single(self, audio_data: np.ndarray) -> str:
        """Process a single audio input and return response."""
        text = self.stt.transcribe(audio_data)
        
        if not text:
            return ""
        
        if self.on_command:
            return self.on_command(text)
        
        return text


def create_advisor_voice_interface():
    """Create a voice interface connected to the STS Advisor."""
    from src_old.advisor import STSAdvisor
    
    # Initialize advisor
    advisor = STSAdvisor()
    
    def handle_command(text: str) -> str:
        """Handle voice command and return response."""
        text_lower = text.lower()
        
        # Check for special commands
        if "new run" in text_lower or "start run" in text_lower or "start a run" in text_lower:
            # Extract character
            for char in ["ironclad", "silent", "defect", "watcher"]:
                if char in text_lower:
                    # Extract ascension if mentioned
                    import re
                    asc_match = re.search(r'ascension\s*(\d+)', text_lower)
                    asc = int(asc_match.group(1)) if asc_match else 0
                    return advisor.start_run(char, asc)
            return "Which character? Say Ironclad, Silent, Defect, or Watcher."
        
        elif "run status" in text_lower or "current run" in text_lower:
            return advisor.get_run_status()
        
        elif "got relic" in text_lower or "picked up" in text_lower or "received" in text_lower:
            # Try to extract relic name (this is simplified - real impl would be smarter)
            return advisor.chat(text)
        
        elif "end run" in text_lower or "died" in text_lower or "won" in text_lower:
            if "won" in text_lower or "victory" in text_lower:
                return advisor.end_run(victory=True)
            else:
                return advisor.end_run(victory=False, killed_by="Unknown")
        
        elif "what card" in text_lower or "should i take" in text_lower or "card reward" in text_lower:
            return advisor.chat(text)
        
        else:
            # General chat
            return advisor.chat(text)
    
    # Create voice interface
    config = VoiceConfig(
        whisper_model="base",  # Good balance of speed/accuracy
        tts_engine="pyttsx3",  # Offline TTS
        push_to_talk_key="f1"
    )
    
    interface = VoiceInterface(config=config, on_command=handle_command)
    return interface


def main():
    """Run the voice interface."""
    interface = create_advisor_voice_interface()
    interface.run()


if __name__ == "__main__":
    main()
