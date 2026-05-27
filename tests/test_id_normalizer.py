"""Focused tests for save ID normalization."""

from src.utils.id_normalizer import normalize_relic_id


class TestRelicIdNormalization:
    """Tests for relic save ID normalization."""

    def test_normalize_internal_cables_id(self):
        """Internal relic ID Cables should map to the canonical relic name."""
        assert normalize_relic_id("Cables") == "Gold-Plated Cables"

    def test_normalize_internal_cables_id_with_counter(self):
        """Counter suffixes should still be preserved after alias mapping."""
        assert normalize_relic_id("Cables 2") == "Gold-Plated Cables 2"