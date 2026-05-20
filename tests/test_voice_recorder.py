"""
Unit tests for voice_recorder module.

Tests the F1 hotkey audio recording functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import numpy as np

from src.voice.voice_recorder import VoiceRecorder
from src.core.config import Config


class TestVoiceRecorder:
    """Tests for VoiceRecorder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.recorder = VoiceRecorder()
        self.test_audio = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        self.test_output_path = Path("test_output.wav")
    
    def teardown_method(self):
        """Clean up test files."""
        if self.test_output_path.exists():
            self.test_output_path.unlink()
    
    # Initialization tests
    def test_initialization(self):
        """Test recorder initializes with correct settings."""
        assert self.recorder.sample_rate == Config.AUDIO_SAMPLE_RATE
        assert self.recorder.channels == Config.AUDIO_CHANNELS
        assert isinstance(self.recorder.audio_data, list)
        assert len(self.recorder.audio_data) == 0
    
    # Audio saving tests
    @patch('wave.open')
    def test_save_audio_to_wav_success(self, mock_wave_open):
        """Test saving audio data to WAV file."""
        # Mock wave file object
        mock_wav = MagicMock()
        mock_wave_open.return_value.__enter__.return_value = mock_wav
        
        result = self.recorder.save_audio_to_wav(self.test_audio, self.test_output_path)
        
        assert result is True
        mock_wave_open.assert_called_once()
        mock_wav.setnchannels.assert_called_with(Config.AUDIO_CHANNELS)
        mock_wav.setframerate.assert_called_with(Config.AUDIO_SAMPLE_RATE)
    
    @patch('wave.open', side_effect=Exception("Write error"))
    def test_save_audio_to_wav_failure(self, mock_wave_open):
        """Test handling of WAV save errors."""
        result = self.recorder.save_audio_to_wav(self.test_audio, self.test_output_path)
        
        assert result is False
    
    def test_save_audio_to_wav_empty_data(self):
        """Test saving empty audio data."""
        empty_audio = np.array([], dtype=np.float32)
        result = self.recorder.save_audio_to_wav(empty_audio, self.test_output_path)
        
        # Should fail or return False for empty audio
        # (implementation dependent, but generally shouldn't save empty audio)
        assert result is False or not self.test_output_path.exists()
    
    # Recording callback tests
    def test_recording_callback_appends_data(self):
        """Test that recording callback appends audio data."""
        self.recorder.audio_data = []
        self.recorder.is_recording = True
        
        # Simulate callback with audio data
        indata = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        frames = 3
        time_info = None
        status = None
        
        self.recorder._audio_callback(indata, frames, time_info, status)
        
        assert len(self.recorder.audio_data) == 1
        np.testing.assert_array_equal(self.recorder.audio_data[0], indata)
    
    def test_recording_callback_status_warning(self):
        """Test callback logs warning when status is set."""
        # This would log a warning but not crash
        indata = np.array([[0.1]], dtype=np.float32)
        status = MagicMock(input_overflow=True)
        
        # Should not raise exception
        self.recorder._audio_callback(indata, 1, None, status)
    
    # Mock-based recording tests
    @patch('keyboard.is_pressed')
    @patch('sounddevice.InputStream')
    def test_record_audio_success(self, mock_input_stream, mock_is_pressed):
        """Test successful audio recording."""
        # Simulate F1 held for 3 "checks" then released
        mock_is_pressed.side_effect = [True, True, True, False]
        
        # Mock the stream
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        
        # Simulate some audio data being captured
        self.recorder.audio_data = [self.test_audio]
        
        result = self.recorder.record_audio(max_duration=5.0)
        
        # Should return concatenated audio
        assert result is not None
        assert isinstance(result, np.ndarray)
    
    @patch('keyboard.is_pressed', return_value=False)
    @patch('sounddevice.InputStream')
    def test_record_audio_no_recording(self, mock_input_stream, mock_is_pressed):
        """Test when F1 is released immediately (no recording)."""
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        
        result = self.recorder.record_audio(max_duration=5.0)
        
        # Should return None when no audio recorded
        assert result is None
    
    @patch('keyboard.is_pressed')
    @patch('sounddevice.InputStream', side_effect=Exception("Stream error"))
    def test_record_audio_stream_error(self, mock_input_stream, mock_is_pressed):
        """Test handling of stream errors during recording."""
        result = self.recorder.record_audio(max_duration=5.0)
        
        assert result is None
    
    @patch('keyboard.is_pressed')
    @patch('sounddevice.InputStream')
    @patch('time.time')
    def test_record_audio_max_duration(self, mock_time, mock_input_stream, mock_is_pressed):
        """Test max duration timeout."""
        # F1 is held down continuously
        mock_is_pressed.return_value = True
        
        # Simulate time passing beyond max_duration
        mock_time.side_effect = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5]  # Exceeds 3.0 max
        
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        
        self.recorder.audio_data = [self.test_audio]
        
        result = self.recorder.record_audio(max_duration=3.0)
        
        # Should stop at max duration and return data
        assert result is not None
    
    # Integration test: record_to_file
    @patch.object(VoiceRecorder, 'record_audio')
    @patch.object(VoiceRecorder, 'save_audio_to_wav')
    def test_record_to_file_success(self, mock_save, mock_record):
        """Test complete record-to-file workflow."""
        mock_record.return_value = self.test_audio
        mock_save.return_value = True
        
        result = self.recorder.record_to_file(self.test_output_path, 30.0)
        
        assert result is True
        mock_record.assert_called_once_with(30.0)
        mock_save.assert_called_once_with(self.test_audio, self.test_output_path)
    
    @patch.object(VoiceRecorder, 'record_audio', return_value=None)
    def test_record_to_file_no_audio(self, mock_record):
        """Test record-to-file when no audio captured."""
        result = self.recorder.record_to_file(self.test_output_path)
        
        assert result is False
    
    @patch.object(VoiceRecorder, 'record_audio')
    @patch.object(VoiceRecorder, 'save_audio_to_wav', return_value=False)
    def test_record_to_file_save_failed(self, mock_save, mock_record):
        """Test record-to-file when save fails."""
        mock_record.return_value = self.test_audio
        
        result = self.recorder.record_to_file(self.test_output_path)
        
        assert result is False
    
    # Buffer management tests
    def test_audio_buffer_concatenation(self):
        """Test that multiple buffer chunks are concatenated correctly."""
        chunk1 = np.array([[0.1], [0.2]], dtype=np.float32)
        chunk2 = np.array([[0.3], [0.4]], dtype=np.float32)
        
        self.recorder.audio_data = [chunk1, chunk2]
        
        # Manually test concatenation logic
        result = np.concatenate(self.recorder.audio_data, axis=0)
        
        expected = np.array([[0.1], [0.2], [0.3], [0.4]], dtype=np.float32)
        np.testing.assert_array_equal(result, expected)
