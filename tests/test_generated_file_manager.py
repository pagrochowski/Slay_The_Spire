"""Unit tests for generated file cleanup."""

from datetime import datetime, timedelta
from pathlib import Path
import os

from src.core.generated_file_manager import CleanupRule, GeneratedFileManager


class TestGeneratedFileManager:
    def test_cleanup_old_generated_files(self, tmp_path):
        processed_dir = tmp_path / "processed"
        captures_dir = processed_dir / "captures"
        captures_dir.mkdir(parents=True)

        old_wav = processed_dir / "relic_choice_old.wav"
        recent_wav = processed_dir / "relic_choice_recent.wav"
        old_png = captures_dir / "old_capture.png"

        for file_path in [old_wav, recent_wav, old_png]:
            file_path.write_text("data", encoding="utf-8")

        old_time = datetime.now() - timedelta(hours=48)
        os.utime(old_wav, (old_time.timestamp(), old_time.timestamp()))
        os.utime(old_png, (old_time.timestamp(), old_time.timestamp()))

        rules = [
            CleanupRule(".", "relic_choice_*.wav", 24),
            CleanupRule("captures", "*.png", 24),
        ]
        manager = GeneratedFileManager(processed_dir, rules=rules)

        deleted = manager.cleanup_old_generated_files()

        assert deleted == 2
        assert not old_wav.exists()
        assert not old_png.exists()
        assert recent_wav.exists()

    def test_get_generated_file_stats(self, tmp_path):
        processed_dir = tmp_path / "processed"
        captures_dir = processed_dir / "captures"
        captures_dir.mkdir(parents=True)

        (processed_dir / "relic_choice_one.wav").write_text("x" * 1024, encoding="utf-8")
        (captures_dir / "capture_one.png").write_text("x" * 1024, encoding="utf-8")

        rules = [
            CleanupRule(".", "relic_choice_*.wav", 24),
            CleanupRule("captures", "*.png", 24),
        ]
        manager = GeneratedFileManager(processed_dir, rules=rules)

        stats = manager.get_generated_file_stats()

        assert stats["total_files"] == 2
        assert stats["total_size_mb"] >= 0
        assert stats["oldest_file"] is not None
        assert stats["newest_file"] is not None