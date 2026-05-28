"""
Unit tests for name_corrector module.

Tests LLM-based name correction with 4-model fallback chain.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.llm.name_corrector import NameCorrector
from src.core.config import Config
from src.knowledge.knowledge_base import KnowledgeBase


class TestNameCorrector:
    """Tests for NameCorrector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock knowledge base
        self.mock_kb = MagicMock(spec=KnowledgeBase)
        
        # Set up mock card/relic data - return actual lists, not MagicMock
        self.mock_kb.get_choosable_cards_for_character.return_value = [
            "Strike", "Defend", "Eruption", "Vigilance", "Battle Hymn"
        ]
        self.mock_kb.get_all_relics.return_value = [
            "Pure Water", "Akabeko", "Pen Nib", "Frozen Core", "Sozu", "Runic Dome"
        ]
        
        self.corrector = NameCorrector(knowledge_base=self.mock_kb)
    
    # Initialization tests
    def test_initialization(self):
        """Test corrector initializes with KB and models."""
        assert self.corrector.kb == self.mock_kb
        assert self.corrector.api_key == Config.GROQ_API_KEY
        assert self.corrector.models == Config.LLM_MODELS
        assert self.corrector.timeout == Config.LLM_TIMEOUT
        assert self.corrector.next_primary_index == 0
    
    def test_initialization_without_kb(self):
        """Test initialization creates default KB if none provided."""
        corrector = NameCorrector()
        assert isinstance(corrector.kb, KnowledgeBase)
    
    # Prompt building tests
    def test_build_correction_prompt_cards_only(self):
        """Test prompt building with cards only."""
        cards = ["Strike", "Defend", "Eruption"]
        relics = []
        
        prompt = self.corrector._build_correction_prompt(
            "strike and defend",
            cards,
            relics
        )
        
        assert "strike and defend" in prompt.lower()
        assert "Strike" in prompt
        assert "Defend" in prompt
    
    def test_build_correction_prompt_with_relics(self):
        """Test prompt building with cards and relics."""
        cards = ["Strike", "Defend"]
        relics = ["Pure Water", "Akabeko"]
        
        prompt = self.corrector._build_correction_prompt(
            "pure water and akabeko",
            cards,
            relics
        )
        
        assert "pure water and akabeko" in prompt.lower()
        assert "Pure Water" in prompt
        assert "Akabeko" in prompt

    def test_build_relic_correction_prompt(self):
        """Test relic-only prompt building."""
        relics = ["Pure Water", "Akabeko"]

        prompt = self.corrector._build_relic_correction_prompt(
            "akabeko and pure water",
            relics
        )

        assert "akabeko and pure water" in prompt.lower()
        assert "Pure Water" in prompt
        assert "Akabeko" in prompt
    
    def test_build_correction_prompt_character_filtering(self):
        """Test that correct cards are provided to prompt builder."""
        # This test should check that correct_names gets the right cards
        # Not the prompt builder itself
        pass
    
    # Model timeout tests
    @patch('threading.Thread')
    def test_call_model_with_timeout_success(self, mock_thread_class):
        """Test successful model call within timeout."""
        # Mock the corrector's client directly
        mock_client = MagicMock()
        self.corrector.client = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": ["Strike"], "relics": []}'
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock thread that completes immediately and calls the target function
        def mock_thread_init(target=None, *args, **kwargs):
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False  # Thread finished
            # Execute the target function immediately to simulate successful completion
            if target:
                target()
            return mock_thread
        
        mock_thread_class.side_effect = mock_thread_init
        
        result = self.corrector._call_model_with_timeout(
            "llama-3.1-8b-instant",
            "test prompt"
        )
        
        assert result == '{"cards": ["Strike"], "relics": []}'
    
    @patch('groq.Groq')
    @patch('threading.Thread')
    def test_call_model_with_timeout_exceeded(self, mock_thread_class, mock_groq):
        """Test timeout handling when model is too slow."""
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        
        # Mock thread that never finishes (timeout)
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True  # Still running after timeout
        mock_thread_class.return_value = mock_thread
        
        result = self.corrector._call_model_with_timeout(
            "slow-model",
            "test prompt"
        )
        
        assert result is None
    
    # Fallback chain tests
    @patch.object(NameCorrector, '_call_model_with_timeout')
    def test_try_models_with_fallback_first_succeeds(self, mock_call):
        """Test fallback chain when first model succeeds."""
        mock_call.return_value = '{"cards": ["Strike"], "relics": []}'
        
        result = self.corrector._try_models_with_fallback("test prompt")
        
        assert result == '{"cards": ["Strike"], "relics": []}'
        # Should only call first model
        assert mock_call.call_count == 1
        assert mock_call.call_args[0][0] == Config.LLM_MODELS[0]
    
    @patch.object(NameCorrector, '_call_model_with_timeout')
    def test_try_models_with_fallback_second_succeeds(self, mock_call):
        """Test fallback to second model."""
        # First fails, second succeeds
        mock_call.side_effect = [
            None,
            '{"cards": ["Defend"], "relics": []}'
        ]
        
        result = self.corrector._try_models_with_fallback("test prompt")
        
        assert result == '{"cards": ["Defend"], "relics": []}'
        assert mock_call.call_count == 2
        assert mock_call.call_args_list[1][0][0] == Config.LLM_MODELS[1]
    
    @patch.object(NameCorrector, '_call_model_with_timeout')
    def test_try_models_with_fallback_all_fail(self, mock_call):
        """Test when all models in chain fail."""
        mock_call.return_value = None
        
        result = self.corrector._try_models_with_fallback("test prompt")
        
        assert result is None
        # Should try all 4 models
        assert mock_call.call_count == 4
    
    @patch.object(NameCorrector, '_call_model_with_timeout')
    def test_try_models_alternating_primary(self, mock_call):
        """Test that primary model alternates between calls."""
        mock_call.return_value = '{"cards": [], "relics": []}'
        
        # First call: should start with model at index 0
        self.corrector.next_primary_index = 0
        self.corrector._try_models_with_fallback("prompt 1")
        first_model = mock_call.call_args[0][0]
        
        # Index should switch
        assert self.corrector.next_primary_index == 1
        
        # Second call: should start with model at index 1
        mock_call.reset_mock()
        self.corrector._try_models_with_fallback("prompt 2")
        second_model = mock_call.call_args[0][0]
        
        # Models should be different
        assert first_model != second_model
        assert self.corrector.next_primary_index == 0  # Wraps back
    
    # JSON parsing tests
    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response."""
        json_str = '{"cards": ["Strike", "Defend"], "relics": ["Pure Water"]}'
        
        result = json.loads(json_str)
        
        assert result["cards"] == ["Strike", "Defend"]
        assert result["relics"] == ["Pure Water"]
    
    def test_parse_invalid_json_response(self):
        """Test handling invalid JSON."""
        invalid_json = '{"cards": ["Strike",}'  # Invalid
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    # Name validation tests
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_valid_response(self, mock_try_models):
        """Test complete name correction with valid LLM response."""
        mock_try_models.return_value = '{"cards": ["Strike", "Defend"], "relics": ["Pure Water"]}'
        
        # Mock KB validation
        self.mock_kb.get_card_data.side_effect = lambda name: {"name": name} if name in ["Strike", "Defend"] else None
        self.mock_kb.get_relic_data.side_effect = lambda name: {"name": name} if name == "Pure Water" else None
        
        cards, relics = self.corrector.correct_names(
            "strike defend and pure water",
            character="watcher"
        )
        
        assert cards == ["Strike", "Defend"]
        assert relics == ["Pure Water"]
    
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_filters_invalid(self, mock_try_models):
        """Test that invalid names are filtered out."""
        mock_try_models.return_value = '{"cards": ["Strike", "InvalidCard"], "relics": ["FakeRelic"]}'
        
        # Only Strike is valid
        self.mock_kb.get_card_data.side_effect = lambda name: {"name": name} if name == "Strike" else None
        self.mock_kb.get_relic_data.return_value = None
        
        cards, relics = self.corrector.correct_names("text", "watcher")
        
        assert cards == ["Strike"]
        assert relics == []
    
    @patch.object(NameCorrector, '_try_models_with_fallback', return_value=None)
    def test_correct_names_llm_failure(self, mock_try_models):
        """Test handling when LLM completely fails."""
        cards, relics = self.corrector.correct_names("text", "watcher")
        
        assert cards == []
        assert relics == []
    
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_invalid_json(self, mock_try_models):
        """Test handling when LLM returns invalid JSON."""
        mock_try_models.return_value = 'This is not JSON'
        
        cards, relics = self.corrector.correct_names("text", "watcher")
        
        assert cards == []
        assert relics == []
    
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_missing_fields(self, mock_try_models):
        """Test handling when JSON is missing required fields."""
        mock_try_models.return_value = '{"cards": ["Strike"]}'  # Missing relics
        
        self.mock_kb.get_card_data.side_effect = lambda name: {"name": name} if name == "Strike" else None
        
        cards, relics = self.corrector.correct_names("text", "watcher")
        
        # Should handle gracefully
        assert cards == ["Strike"]
        assert relics == []
    
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_exclude_relics(self, mock_try_models):
        """Test excluding relics from correction."""
        mock_try_models.return_value = '{"cards": ["Strike"], "relics": []}'
        
        self.mock_kb.get_card_data.return_value = {"name": "Strike"}
        
        cards, relics = self.corrector.correct_names(
            "strike",
            "watcher",
            include_relics=False
        )
        
        assert cards == ["Strike"]
        assert relics == []
        
        # Verify KB was called correctly
        self.mock_kb.get_choosable_cards_for_character.assert_called_with("watcher")
        self.mock_kb.get_all_relics.assert_not_called()

    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_relic_names(self, mock_try_models):
        """Test relic-only correction flow."""
        mock_try_models.return_value = '{"cards": [], "relics": ["Akabeko", "Pen Nib"]}'

        self.mock_kb.get_relic_data.side_effect = lambda name: {"name": name} if name in ["Akabeko", "Pen Nib"] else None
        self.mock_kb.get_card_data.return_value = None

        relics = self.corrector.correct_relic_names("akabeko pen nib")

        assert relics == ["Akabeko", "Pen Nib"]
        self.mock_kb.get_all_relics.assert_called()
        self.mock_kb.get_choosable_cards_for_character.assert_not_called()

    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_relic_names_phrase_fallback(self, mock_try_models):
        """Relic phrase fallback should recover near-miss spoken phrases like Runic Dawn."""
        mock_try_models.return_value = '{"cards": [], "relics": ["Frozen Core", "Sozu"]}'

        self.mock_kb.get_relic_data.side_effect = lambda name: {"name": name} if name in [
            "Frozen Core", "Sozu", "Runic Dome"
        ] else None
        self.mock_kb.get_card_data.return_value = None

        relics = self.corrector.correct_relic_names("Frozen core, Sozu, Runic Dawn")

        assert relics == ["Frozen Core", "Sozu", "Runic Dome"]

    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_relic_names_single_phrase_does_not_add_extra_stone_relic(self, mock_try_models):
        """A strong single-phrase match like Wet stone should resolve to Whetstone only."""
        mock_try_models.return_value = '{"cards": [], "relics": []}'
        self.mock_kb.get_all_relics.return_value = [
            "Whetstone",
            "Darkstone Periapt",
            "Sling of Courage",
        ]

        relics = self.corrector.correct_relic_names("Wet stone")

        assert relics == ["Whetstone"]

    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_relic_names_period_separated_phrases(self, mock_try_models):
        """Period-separated relic phrases should each resolve without adding noisy stone matches."""
        mock_try_models.return_value = '{"cards": [], "relics": ["Sling of Courage"]}'
        self.mock_kb.get_all_relics.return_value = [
            "Whetstone",
            "Darkstone Periapt",
            "Sling of Courage",
        ]

        relics = self.corrector.correct_relic_names("Wet stone. Sling of courage.")

        assert relics == ["Sling of Courage", "Whetstone"]
    
    # Edge cases
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_empty_transcription(self, mock_try_models):
        """Test with empty transcription text."""
        mock_try_models.return_value = '{"cards": [], "relics": []}'
        
        cards, relics = self.corrector.correct_names("", "watcher")
        
        assert cards == []
        assert relics == []
    
    @patch.object(NameCorrector, '_try_models_with_fallback')
    def test_correct_names_whitespace_transcription(self, mock_try_models):
        """Test with whitespace-only transcription."""
        mock_try_models.return_value = '{"cards": [], "relics": []}'
        
        cards, relics = self.corrector.correct_names("   ", "watcher")
        
        assert cards == []
        assert relics == []
    
    # Configuration tests
    def test_timeout_configuration(self):
        """Test timeout is correctly configured."""
        assert self.corrector.timeout == 3.0
        assert self.corrector.timeout == Config.LLM_TIMEOUT
    
    def test_models_configuration(self):
        """Test models list is correctly configured."""
        assert len(self.corrector.models) == 4
        assert "llama-3.1-8b-instant" in self.corrector.models
        assert "openai/gpt-oss-20b" in self.corrector.models
