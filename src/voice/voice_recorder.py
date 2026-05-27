"""
Voice Recorder for Slay the Spire.

Handles F1 hotkey audio recording using sounddevice and keyboard libraries.
"""

import io
import wave
import time
from pathlib import Path
from typing import Optional, Callable
import numpy as np
import sounddevice as sd
import keyboard
from src.core.config import Config
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("voice")


class VoiceRecorder:
    """Records audio on F1 hotkey press."""
    
    def __init__(
        self,
        hotkey: str = None,
        sample_rate: int = None,
        channels: int = None
    ):
        """
        Initialize voice recorder.
        
        Args:
            hotkey: Hotkey to trigger recording (default: from Config)
            sample_rate: Audio sample rate (default: from Config)
            channels: Audio channels (default: from Config)
        """
        self.hotkey = hotkey or Config.RECORDING_HOTKEY
        self.sample_rate = sample_rate or Config.AUDIO_SAMPLE_RATE
        self.channels = channels or Config.AUDIO_CHANNELS
        
        self.is_recording = False
        self.audio_data = []
        
        log.info("VoiceRecorder initialized")
        log_operation(log, "recorder_init", {
            "hotkey": self.hotkey,
            "sample_rate": self.sample_rate,
            "channels": self.channels
        })
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio recording."""
        if status:
            log.warning(f"Audio callback status: {status}")
        
        if self.is_recording:
            # Copy audio data
            self.audio_data.append(indata.copy())
    
    def record_audio(
        self,
        max_duration: float = 30.0,
        wait_for_hotkey: bool = True
    ) -> Optional[np.ndarray]:
        """
        Record audio while F1 is held down.
        
        Args:
            max_duration: Maximum recording duration in seconds
            wait_for_hotkey: Whether to wait for the hotkey before recording
            
        Returns:
            Numpy array of audio data, or None if recording failed
        """
        if wait_for_hotkey:
            log.info(f"Press and hold {self.hotkey.upper()} to record...")
            print(f"🎤 Press and hold {self.hotkey.upper()} to record audio...")
            keyboard.wait(self.hotkey)
        else:
            log.info(f"Recording immediately while {self.hotkey.upper()} is held")
        
        # Start recording
        self.is_recording = True
        self.audio_data = []
        
        log.info("Recording started")
        log_operation(log, "recording_start", {
            "hotkey": self.hotkey,
            "max_duration": max_duration
        })
        
        print(f"🔴 Recording... (Release {self.hotkey.upper()} to stop)")
        
        start_time = time.time()
        
        try:
            # Open audio stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback
            ):
                # Record until key released or max duration
                while keyboard.is_pressed(self.hotkey):
                    time.sleep(0.01)  # Small delay to avoid CPU spinning
                    
                    # Check max duration
                    if time.time() - start_time > max_duration:
                        log.warning(f"Max recording duration ({max_duration}s) reached")
                        break
                
                # Stop recording
                self.is_recording = False
                
                # Small delay to ensure last audio chunks are captured
                time.sleep(0.1)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Combine audio chunks
            if not self.audio_data:
                log.warning("No audio data recorded")
                print("⚠️  No audio recorded")
                return None
            
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            log.info(f"Recording complete")
            log_operation(log, "recording_complete", {
                "duration": f"{duration:.2f}s",
                "samples": len(audio_array),
                "size": f"{audio_array.nbytes} bytes"
            })
            
            print(f"✅ Recording complete ({duration:.1f}s)")
            
            return audio_array
            
        except Exception as e:
            log.error(f"Recording failed: {e}")
            log_operation(log, "recording_failed", {
                "error": str(e)
            }, level="ERROR")
            print(f"❌ Recording failed: {e}")
            return None
    
    def save_audio_to_wav(self, audio_data: np.ndarray, output_path: Path) -> bool:
        """
        Save audio data to WAV file.
        
        Args:
            audio_data: Numpy array of audio samples
            output_path: Path to save WAV file
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write WAV file
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            log.info(f"Audio saved to: {output_path.name}")
            log_operation(log, "audio_saved", {
                "file": output_path.name,
                "size": f"{output_path.stat().st_size} bytes"
            })
            
            return True
            
        except Exception as e:
            log.error(f"Failed to save audio: {e}")
            log_operation(log, "audio_save_failed", {
                "error": str(e)
            }, level="ERROR")
            return False
    
    def record_to_file(
        self,
        output_path: Path,
        max_duration: float = 30.0,
        wait_for_hotkey: bool = True
    ) -> bool:
        """
        Record audio and save directly to file.
        
        Args:
            output_path: Path to save WAV file
            max_duration: Maximum recording duration
            wait_for_hotkey: Whether to wait for the hotkey before recording
            
        Returns:
            True if recording and save successful, False otherwise
        """
        if wait_for_hotkey:
            audio_data = self.record_audio(max_duration)
        else:
            audio_data = self.record_audio(max_duration, wait_for_hotkey=False)
        
        if audio_data is None:
            return False
        
        return self.save_audio_to_wav(audio_data, output_path)


if __name__ == "__main__":
    # Test the voice recorder
    from datetime import datetime
    
    print("Voice Recorder Test")
    print("=" * 50)
    
    # Initialize recorder
    recorder = VoiceRecorder()
    
    # Test recording
    print(f"\n1. Testing audio recording...")
    print(f"   Hotkey: {recorder.hotkey.upper()}")
    print(f"   Sample Rate: {recorder.sample_rate} Hz")
    
    # Record audio
    audio = recorder.record_audio(max_duration=10.0)
    
    if audio is not None:
        print(f"\n2. Audio recorded successfully")
        print(f"   Duration: {len(audio) / recorder.sample_rate:.2f}s")
        print(f"   Samples: {len(audio)}")
        
        # Save to temp file
        temp_path = Config.PROCESSED_DIR / f"test_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        if recorder.save_audio_to_wav(audio, temp_path):
            print(f"\n3. Audio saved to: {temp_path}")
        else:
            print(f"\n3. Failed to save audio")
    else:
        print(f"\n2. No audio recorded")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
