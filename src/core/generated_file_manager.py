"""Cleanup manager for generated files under data/processed."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from src.core.config import Config
from src.utils.logger import log_operation, setup_logger

log = setup_logger("cleanup")


@dataclass(frozen=True)
class CleanupRule:
    """Retention rule for generated files."""

    relative_dir: str
    glob_pattern: str
    max_age_hours: int
    recursive: bool = False


class GeneratedFileManager:
    """Manages cleanup of generated PNG, WAV, and JSON files."""

    DEFAULT_RULES = [
        CleanupRule(".", "relic_choice_*.wav", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule(".", "voice_*.wav", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule(".", "test_recording_*.wav", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule(".", "test_transcribe_*.wav", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule(".", "run_data_*.json", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule("captures", "*.png", Config.GENERATED_FILE_MAX_AGE_HOURS),
        CleanupRule("background_capture_tests", "*.png", Config.GENERATED_FILE_MAX_AGE_HOURS, recursive=True),
    ]

    def __init__(self, processed_dir: Path, rules: List[CleanupRule] | None = None):
        self.processed_dir = Path(processed_dir)
        self.rules = rules or list(self.DEFAULT_RULES)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        log.info("GeneratedFileManager initialized")
        log_operation(
            log,
            "generated_cleanup_init",
            {
                "processed_dir": self.processed_dir,
                "rules": len(self.rules),
            },
        )

    def cleanup_old_generated_files(self) -> int:
        """Delete generated files older than the configured retention windows."""
        deleted_count = 0

        for rule in self.rules:
            target_dir = self.processed_dir / rule.relative_dir
            if not target_dir.exists():
                continue

            cutoff_time = datetime.now() - timedelta(hours=rule.max_age_hours)
            iterator = target_dir.rglob(rule.glob_pattern) if rule.recursive else target_dir.glob(rule.glob_pattern)

            for file_path in iterator:
                if not file_path.is_file():
                    continue

                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                age_hours = (datetime.now() - mod_time).total_seconds() / 3600

                if mod_time < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        log_operation(
                            log,
                            "generated_file_deleted",
                            {
                                "file": file_path.relative_to(self.processed_dir),
                                "age_hours": f"{age_hours:.1f}",
                                "rule": f"{rule.relative_dir}:{rule.glob_pattern}",
                            },
                        )
                    except Exception as exc:
                        log_operation(
                            log,
                            "generated_file_delete_failed",
                            {
                                "file": file_path,
                                "error": str(exc),
                            },
                            level="ERROR",
                        )

            self._cleanup_empty_directories(target_dir)

        log_operation(log, "generated_cleanup_complete", {"deleted_count": deleted_count})
        return deleted_count

    def get_generated_file_stats(self) -> dict:
        """Summarize generated files covered by the cleanup rules."""
        files = []
        for rule in self.rules:
            target_dir = self.processed_dir / rule.relative_dir
            if not target_dir.exists():
                continue

            iterator = target_dir.rglob(rule.glob_pattern) if rule.recursive else target_dir.glob(rule.glob_pattern)
            files.extend(path for path in iterator if path.is_file())

        if not files:
            return {
                "total_files": 0,
                "total_size_mb": 0,
                "oldest_file": None,
                "newest_file": None,
            }

        total_size = sum(path.stat().st_size for path in files)
        oldest = min(files, key=lambda path: path.stat().st_mtime)
        newest = max(files, key=lambda path: path.stat().st_mtime)

        return {
            "total_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": str(oldest.relative_to(self.processed_dir)),
            "newest_file": str(newest.relative_to(self.processed_dir)),
        }

    def _cleanup_empty_directories(self, root_dir: Path) -> None:
        """Remove empty directories left behind after recursive cleanup."""
        if not root_dir.exists():
            return

        for directory in sorted((path for path in root_dir.rglob("*") if path.is_dir()), reverse=True):
            try:
                if not any(directory.iterdir()):
                    directory.rmdir()
            except OSError:
                continue