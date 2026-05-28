#!/usr/bin/env python
"""Cleanup utility for generated files under data/processed."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.generated_file_manager import CleanupRule, GeneratedFileManager


def main():
    parser = argparse.ArgumentParser(description="Clean up generated PNG/WAV/JSON files")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=Config.GENERATED_FILE_MAX_AGE_HOURS,
        help=f"Maximum generated file age in hours (default: {Config.GENERATED_FILE_MAX_AGE_HOURS})",
    )
    args = parser.parse_args()

    rules = [
        CleanupRule(rule.relative_dir, rule.glob_pattern, args.max_age_hours, rule.recursive)
        for rule in GeneratedFileManager.DEFAULT_RULES
    ]
    manager = GeneratedFileManager(Config.PROCESSED_DIR, rules=rules)

    print("\n" + "=" * 60)
    print("Generated File Cleanup Utility")
    print("=" * 60)
    print(f"\nProcessed Directory: {Config.PROCESSED_DIR}")
    print(f"Max Age: {args.max_age_hours} hours")

    stats_before = manager.get_generated_file_stats()
    print(f"\nCurrent Generated Files: {stats_before['total_files']}")
    print(f"Total Size: {stats_before['total_size_mb']:.2f} MB")

    deleted = manager.cleanup_old_generated_files()
    print(f"\nDeleted {deleted} file(s)")

    stats_after = manager.get_generated_file_stats()
    print(f"Remaining Generated Files: {stats_after['total_files']}")
    print(f"Total Size: {stats_after['total_size_mb']:.2f} MB")

    print("\n" + "=" * 60)
    print(f"\nLogs: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    main()