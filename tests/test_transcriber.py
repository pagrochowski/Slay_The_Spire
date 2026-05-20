"""
Unit tests for transcriber module.

Tests Groq Whisper API transcription with fallback.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from src.voice.transcriber import AudioTranscriber
from src.core.config import Config


class TestAudioTranscriber:
    """Tests for AudioTranscriber class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transcriber = AudioTranscriber()
        self.test_audio_path = Path("test_audio.wav")
        self.test_text = "strike defend eruption"
    
    # Initialization tests
    def test_initialization(self):
        """Test transcriber initializes with correct API key."""
        assert self.transcriber.api_key == Config.GROQ_API_KEY
        assert self.transcriber.primary_model == Config.WHISPER_PRIMARY_MODEL
        assert self.transcriber.fallback_model == Config.WHISPER_FALLBACK_MODEL
    
    def test_initialization_missing_api_key(self):
        """Test initialization fails gracefully without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.core.config.Config.GROQ_API_KEY', None):
                # Should raise ValueError
                with pytest.raises(ValueError, match="GROQ_API_KEY"):
                    AudioTranscriber()
    
    # Transcription with primary model tests
    @patch('groq.Groq')
    @patch('builtins.open', mock_open(read_data=b'fake audio data'))
    def test_transcribe_with_model_success(self, mock_groq_class):
        """Test successful transcription with a model."""
        # Mock Groq client
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        # Mock transcription response
        mock_response = MagicMock()
        mock_response.text = self.test_text
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        result = self.transcriber._transcribe_with_model(
            self.test_audio_path,
            Config.WHISPER_PRIMARY_MODEL,
            "en"
        )
        
        assert result == self.test_text
        
        # Verify API was called correctly
        mock_client.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs['model'] == Config.WHISPER_PRIMARY_MODEL
        assert call_kwargs['language'] == "en"
    
    @patch('groq.Groq')
    @patch('builtins.open', mock_open(read_data=b'fake audio data'))
    def test_transcribe_with_model_api_error(self, mock_groq_class):
        """Test handling of API errors during transcription."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        # Simulate API error
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        result = self.transcriber._transcribe_with_model(
            self.test_audio_path,
            Config.WHISPER_PRIMARY_MODEL,
            "en"
        )
        
        assert result is None
    
    @patch('groq.Groq')
    def test_transcribe_with_model_file_not_found(self, mock_groq_class):
        """Test handling when audio file doesn't exist."""
        nonexistent_path = Path("nonexistent.wav")
        result = self.transcriber._transcribe_with_model(
            nonexistent_path,
            Config.WHISPER_PRIMARY_MODEL,
            "en"
        )
        
        assert result is None
    
    # Main transcribe_audio tests
    @patch.object(AudioTranscriber, '_transcribe_with_model')
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_primary_success(self, mock_stat, mock_transcribe):
        """Test transcription succeeds with primary model."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        mock_transcribe.return_value = self.test_text
        
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        assert result == self.test_text
        # Should only call primary model
        mock_transcribe.assert_called_once_with(
            self.test_audio_path,
            Config.WHISPER_PRIMARY_MODEL,
            "en"
        )
    
    @patch.object(AudioTranscriber, '_transcribe_with_model')
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_fallback_success(self, mock_stat, mock_transcribe):
        """Test transcription falls back to secondary model."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        # Primary fails, fallback succeeds
        mock_transcribe.side_effect = [None, self.test_text]
        
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        assert result == self.test_text
        # Should call both models
        assert mock_transcribe.call_count == 2
        
        # Check calls
        calls = mock_transcribe.call_args_list
        assert calls[0][0][1] == Config.WHISPER_PRIMARY_MODEL
        assert calls[1][0][1] == Config.WHISPER_FALLBACK_MODEL
    
    @patch.object(AudioTranscriber, '_transcribe_with_model', return_value=None)
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_both_fail(self, mock_stat, mock_transcribe):
        """Test when both primary and fallback fail."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        assert result is None
        # Should try both models
        assert mock_transcribe.call_count == 2
    
    # Language parameter tests
    @patch.object(AudioTranscriber, '_transcribe_with_model')
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_custom_language(self, mock_stat, mock_transcribe):
        """Test transcription with custom language."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        mock_transcribe.return_value = "texto en español"
        
        result = self.transcriber.transcribe_audio(
            self.test_audio_path,
            language="es"
        )
        
        assert result == "texto en español"
        mock_transcribe.assert_called_with(
            self.test_audio_path,
            Config.WHISPER_PRIMARY_MODEL,
            "es"
        )
    
    # Empty/whitespace transcription tests
    @patch.object(AudioTranscriber, '_transcribe_with_model')
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_empty_result(self, mock_stat, mock_transcribe):
        """Test handling of empty transcription result."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        mock_transcribe.return_value = ""
        
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        # Empty string should be treated as failure, try fallback
        assert mock_transcribe.call_count == 2
    
    @patch.object(AudioTranscriber, '_transcribe_with_model')
    @patch('pathlib.Path.stat')
    def test_transcribe_audio_whitespace_result(self, mock_stat, mock_transcribe):
        """Test handling of whitespace-only transcription."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        mock_transcribe.return_value = "   "
        
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        # Whitespace should be treated as failure
        assert mock_transcribe.call_count == 2
    
    # Model configuration tests
    def test_primary_model_configured(self):
        """Test that primary model is correctly configured."""
        assert self.transcriber.primary_model == "whisper-large-v3"
    
    def test_fallback_model_configured(self):
        """Test that fallback model is correctly configured."""
        assert self.transcriber.fallback_model == "whisper-large-v3-turbo"
    
    # Integration-style tests
    @patch('groq.Groq')
    @patch('builtins.open', mock_open(read_data=b'fake audio'))
    @patch('pathlib.Path.stat')
    def test_full_transcription_workflow(self, mock_stat, mock_groq_class):
        """Test complete transcription workflow."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        
        # Set up mock client
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "battle hymn third eye"
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        result = self.transcriber.transcribe_audio(
            self.test_audio_path,
            language="en"
        )
        
        assert result == "battle hymn third eye"
        
        # Verify Groq client created with API key
        mock_groq_class.assert_called_once_with(api_key=Config.GROQ_API_KEY)
    
    @patch('groq.Groq')
    @patch('builtins.open', mock_open(read_data=b'fake audio'))
    @patch('pathlib.Path.stat')
    def test_fallback_on_rate_limit(self, mock_stat, mock_groq_class):
        """Test fallback when primary model hits rate limit."""
        # Mock file size
        mock_stat.return_value = MagicMock(st_size=1024)
        
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        # Primary model: rate limit error
        # Fallback model: success
        mock_response = MagicMock()
        mock_response.text = "vigilance eruption"
        
        mock_client.audio.transcriptions.create.side_effect = [
            Exception("Rate limit exceeded"),
            mock_response
        ]
        
        result = self.transcriber.transcribe_audio(self.test_audio_path)
        
        assert result == "vigilance eruption"
        # Should have tried both models
        assert mock_client.audio.transcriptions.create.call_count == 2
