#!/usr/bin/env python
"""
Backup Cleanup Utility.

Deletes backup files older than specified age (default: 24 hours).

Usage:
    python scripts/cleanup_backups.py [--max-age-hours 24]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.utils.logger import setup_logger

# Initialize logger
log = setup_logger("backup")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up old save file backups"
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=Config.BACKUP_MAX_AGE_HOURS,
        help=f"Maximum backup age in hours (default: {Config.BACKUP_MAX_AGE_HOURS})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🗑️  Backup Cleanup Utility")
    print("=" * 60)
    print(f"\nBackup Directory: {Config.BACKUP_DIR}")
    print(f"Max Age: {args.max_age_hours} hours")
    
    if args.dry_run:
        print("Mode: DRY RUN (no files will be deleted)")
    
    print("\n" + "-" * 60)
    
    # Initialize backup manager
    backup_mgr = BackupManager(
        Config.GAME_SAVES_DIR,
        Config.BACKUP_DIR,
        max_age_hours=args.max_age_hours
    )
    
    # Get stats before cleanup
    stats_before = backup_mgr.get_backup_stats()
    print(f"\nCurrent Backups: {stats_before['total_backups']}")
    print(f"Total Size: {stats_before['total_size_mb']:.2f} MB")
    
    if stats_before['total_backups'] > 0:
        print(f"Oldest: {stats_before['oldest_backup']} ({stats_before['oldest_age_hours']:.1f}h ago)")
        print(f"Newest: {stats_before['newest_backup']} ({stats_before['newest_age_hours']:.1f}h ago)")
    
    # Perform cleanup
    if not args.dry_run:
        print(f"\n🗑️  Cleaning up backups older than {args.max_age_hours} hours...")
        deleted = backup_mgr.cleanup_old_backups()
        
        print(f"\n✅ Deleted {deleted} file(s)")
        
        # Get stats after cleanup
        stats_after = backup_mgr.get_backup_stats()
        print(f"\nRemaining Backups: {stats_after['total_backups']}")
        print(f"Total Size: {stats_after['total_size_mb']:.2f} MB")
        
        log.info(f"Cleanup complete: {deleted} files deleted")
    else:
        print("\n(Dry run - no files deleted)")
    
    print("\n" + "=" * 60)
    print(f"\nLogs: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    main()
