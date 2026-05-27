"""Unit tests for choice persistence formatting."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.choice.choice_persistence import ChoicePersistence


class TestChoicePersistence:
    """Tests for current choice formatting."""

    def test_format_choice_text_with_relic_descriptions(self, tmp_path):
        """Relics in the current choice section should include descriptions when known."""
        choice_file = tmp_path / "current_choice.json"
        choice_file.write_text(
            json.dumps(
                {
                    "floor": 17,
                    "act": 1,
                    "cards": [],
                    "relics": ["Frozen Core", "Sozu", "Runic Dome"],
                }
            ),
            encoding="utf-8",
        )

        mock_kb = MagicMock()
        mock_kb.get_relic_data.side_effect = lambda name: {
            "Frozen Core": {"description": "Replaces Cracked Core. If you end your turn with any empty Orb slots, Channel 1 Frost."},
            "Sozu": {"description": "Gain [E] at the start of your turn. You can no longer obtain potions."},
            "Runic Dome": {"description": "Gain [E] at the start of your turn. You can no longer see enemy intents."},
        }.get(name)

        persistence = ChoicePersistence(choice_file=choice_file, knowledge_base=mock_kb)

        formatted = persistence.format_choice_text()

        assert formatted is not None
        assert "Relics to choose from:" in formatted
        assert "- Frozen Core: Replaces Cracked Core." in formatted
        assert "- Sozu: Gain [E] at the start of your turn." in formatted
        assert "- Runic Dome: Gain [E] at the start of your turn." in formatted

    def test_format_choice_text_falls_back_to_name_only(self, tmp_path):
        """Unknown relics should still render without descriptions."""
        choice_file = tmp_path / "current_choice.json"
        choice_file.write_text(
            json.dumps(
                {
                    "floor": 17,
                    "act": 1,
                    "cards": [],
                    "relics": ["Unknown Relic"],
                }
            ),
            encoding="utf-8",
        )

        mock_kb = MagicMock()
        mock_kb.get_relic_data.return_value = None

        persistence = ChoicePersistence(choice_file=choice_file, knowledge_base=mock_kb)

        formatted = persistence.format_choice_text()

        assert formatted == "Relics to choose from:\n- Unknown Relic"