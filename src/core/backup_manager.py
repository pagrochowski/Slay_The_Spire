"""
Backup Manager for Slay the Spire save files.

Functions:
- Find latest autosave file
- Create timestamped backups
- Auto-cleanup backups older than 24 hours
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("backup")


class BackupManager:
    """Manages save file backups."""
    
    def __init__(self, saves_dir: Path, backup_dir: Path, max_age_hours: int = 24):
        """
        Initialize backup manager.
        
        Args:
            saves_dir: Directory containing game save files
            backup_dir: Directory to store backups
            max_age_hours: Maximum age of backups before deletion (default: 24)
        """
        self.saves_dir = Path(saves_dir)
        self.backup_dir = Path(backup_dir)
        self.max_age_hours = max_age_hours
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        log.info(f"BackupManager initialized")
        log_operation(log, "init", {
            "saves_dir": self.saves_dir,
            "backup_dir": self.backup_dir,
            "max_age_hours": max_age_hours
        })
    
    def find_latest_autosave(self, character: Optional[str] = None) -> Optional[Path]:
        """
        Find the most recently modified autosave file.
        
        Args:
            character: Optional character name to filter (e.g., "IRONCLAD", "WATCHER")
            
        Returns:
            Path to latest autosave file, or None if not found
        """
        log.debug(f"Searching for latest autosave in: {self.saves_dir}")
        
        if not self.saves_dir.exists():
            log.error(f"Saves directory not found: {self.saves_dir}")
            return None
        
        # Find all .autosave files
        autosave_files = list(self.saves_dir.glob("*.autosave"))
        
        if not autosave_files:
            log.warning(f"No .autosave files found in {self.saves_dir}")
            return None
        
        # Filter by character if specified
        if character:
            character_upper = character.upper()
            autosave_files = [
                f for f in autosave_files
                if character_upper in f.name.upper()
            ]
            
            if not autosave_files:
                log.warning(f"No .autosave files found for character: {character}")
                return None
        
        # Get the most recently modified file
        latest = max(autosave_files, key=lambda p: p.stat().st_mtime)
        
        log.info(f"Found latest autosave: {latest.name}")
        log_operation(log, "find_latest", {
            "file": latest.name,
            "modified": datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "size": f"{latest.stat().st_size} bytes"
        })
        
        return latest
    
    def create_backup(self, source_path: Path) -> Optional[Path]:
        """
        Create a timestamped backup of a save file.
        
        Args:
            source_path: Path to the save file to backup
            
        Returns:
            Path to the created backup file, or None if backup failed
        """
        if not source_path.exists():
            log.error(f"Source file not found: {source_path}")
            return None
        
        try:
            # Create timestamp for backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get original filename components
            stem = source_path.stem  # e.g., "IRONCLAD"
            suffix = source_path.suffix  # e.g., ".autosave"
            
            # Create backup filename: CHARACTERNAME_TIMESTAMP.autosave
            backup_filename = f"{stem}_{timestamp}{suffix}"
            backup_path = self.backup_dir / backup_filename
            
            # Copy the file
            log.debug(f"Creating backup: {source_path} -> {backup_path}")
            shutil.copy2(source_path, backup_path)
            
            # Log success
            log.info(f"Backup created successfully: {backup_filename}")
            log_operation(log, "backup_created", {
                "source": source_path.name,
                "backup": backup_filename,
                "size": f"{backup_path.stat().st_size} bytes",
                "timestamp": timestamp
            })
            
            return backup_path
            
        except Exception as e:
            log.error(f"Failed to create backup: {e}")
            log_operation(log, "backup_failed", {
                "source": source_path.name,
                "error": str(e)
            }, level="ERROR")
            return None
    
    def cleanup_old_backups(self) -> int:
        """
        Delete backups older than max_age_hours.
        
        Returns:
            Number of backups deleted
        """
        log.info(f"Starting backup cleanup (max age: {self.max_age_hours} hours)")
        
        if not self.backup_dir.exists():
            log.warning(f"Backup directory not found: {self.backup_dir}")
            return 0
        
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        
        # Find all backup files
        backup_files = list(self.backup_dir.glob("*.autosave"))
        deleted_count = 0
        
        for backup_file in backup_files:
            try:
                # Get file modification time
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                age_hours = (datetime.now() - mod_time).total_seconds() / 3600
                
                # Delete if older than cutoff
                if mod_time < cutoff_time:
                    log.debug(f"Deleting old backup: {backup_file.name} (age: {age_hours:.1f}h)")
                    backup_file.unlink()
                    deleted_count += 1
                    
                    log_operation(log, "backup_deleted", {
                        "file": backup_file.name,
                        "age_hours": f"{age_hours:.1f}",
                        "mod_time": mod_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            except Exception as e:
                log.error(f"Failed to delete backup {backup_file.name}: {e}")
                log_operation(log, "delete_failed", {
                    "file": backup_file.name,
                    "error": str(e)
                }, level="ERROR")
        
        log.info(f"Backup cleanup complete: {deleted_count} file(s) deleted")
        log_operation(log, "cleanup_complete", {
            "deleted_count": deleted_count,
            "total_backups": len(backup_files),
            "cutoff_time": cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return deleted_count
    
    def get_backup_stats(self) -> dict:
        """
        Get statistics about current backups.
        
        Returns:
            Dictionary with backup statistics
        """
        if not self.backup_dir.exists():
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
        
        backup_files = list(self.backup_dir.glob("*.autosave"))
        
        if not backup_files:
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in backup_files)
        
        # Find oldest and newest
        oldest = min(backup_files, key=lambda p: p.stat().st_mtime)
        newest = max(backup_files, key=lambda p: p.stat().st_mtime)
        
        stats = {
            "total_backups": len(backup_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": oldest.name,
            "oldest_age_hours": round((datetime.now() - datetime.fromtimestamp(oldest.stat().st_mtime)).total_seconds() / 3600, 1),
            "newest_backup": newest.name,
            "newest_age_hours": round((datetime.now() - datetime.fromtimestamp(newest.stat().st_mtime)).total_seconds() / 3600, 1)
        }
        
        log_operation(log, "stats_retrieved", stats, level="DEBUG")
        
        return stats


if __name__ == "__main__":
    # Test the backup manager
    from src.core.config import Config
    
    print("Backup Manager Test")
    print("=" * 50)
    
    # Initialize manager
    manager = BackupManager(
        saves_dir=Config.GAME_SAVES_DIR,
        backup_dir=Config.BACKUP_DIR,
        max_age_hours=24
    )
    
    # Find latest autosave
    print("\n1. Finding latest autosave...")
    latest = manager.find_latest_autosave()
    if latest:
        print(f"   ✅ Found: {latest.name}")
        
        # Create backup
        print("\n2. Creating backup...")
        backup = manager.create_backup(latest)
        if backup:
            print(f"   ✅ Backup created: {backup.name}")
    else:
        print("   ❌ No autosave found")
    
    # Get stats
    print("\n3. Backup statistics:")
    stats = manager.get_backup_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Cleanup old backups
    print("\n4. Cleaning up old backups...")
    deleted = manager.cleanup_old_backups()
    print(f"   ✅ Deleted {deleted} old backup(s)")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
