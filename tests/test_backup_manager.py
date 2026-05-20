"""Unit tests for backup manager."""

import pytest
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from src.core.backup_manager import BackupManager


class TestBackupManager:
    """Test cases for the backup manager."""
    
    @pytest.fixture
    def test_dirs(self, tmp_path):
        """Create temporary test directories."""
        saves_dir = tmp_path / "saves"
        backup_dir = tmp_path / "backups"
        saves_dir.mkdir()
        backup_dir.mkdir()
        return saves_dir, backup_dir
    
    @pytest.fixture
    def mock_autosave(self, test_dirs):
        """Create a mock autosave file."""
        saves_dir, _ = test_dirs
        autosave = saves_dir / "IRONCLAD.autosave"
        autosave.write_text("mock save data")
        return autosave
    
    def test_initialization(self, test_dirs):
        """Test BackupManager initialization."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        assert manager.saves_dir == saves_dir
        assert manager.backup_dir == backup_dir
        assert manager.max_age_hours == 24
        assert backup_dir.exists()
    
    def test_find_latest_autosave_single(self, test_dirs, mock_autosave):
        """Test finding latest autosave with single file."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        latest = manager.find_latest_autosave()
        assert latest is not None
        assert latest.name == "IRONCLAD.autosave"
    
    def test_find_latest_autosave_multiple(self, test_dirs):
        """Test finding latest autosave with multiple files."""
        saves_dir, backup_dir = test_dirs
        
        # Create multiple autosave files with different timestamps
        files = []
        for i, char in enumerate(["IRONCLAD", "SILENT", "DEFECT"]):
            file = saves_dir / f"{char}.autosave"
            file.write_text(f"mock data {i}")
            files.append(file)
            
            # Modify timestamps to make them different
            import time
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        manager = BackupManager(saves_dir, backup_dir)
        latest = manager.find_latest_autosave()
        
        assert latest is not None
        # Should be the most recently created
        assert latest.name == "DEFECT.autosave"
    
    def test_find_latest_autosave_by_character(self, test_dirs):
        """Test finding latest autosave filtered by character."""
        saves_dir, backup_dir = test_dirs
        
        # Create autosaves for different characters
        for char in ["IRONCLAD", "SILENT", "WATCHER"]:
            file = saves_dir / f"{char}.autosave"
            file.write_text(f"mock data {char}")
        
        manager = BackupManager(saves_dir, backup_dir)
        
        # Find specific character
        latest = manager.find_latest_autosave(character="SILENT")
        assert latest is not None
        assert "SILENT" in latest.name
    
    def test_find_latest_no_autosaves(self, test_dirs):
        """Test finding latest when no autosaves exist."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        latest = manager.find_latest_autosave()
        assert latest is None
    
    def test_create_backup(self, test_dirs, mock_autosave):
        """Test creating a backup file."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        backup = manager.create_backup(mock_autosave)
        
        assert backup is not None
        assert backup.exists()
        assert backup.parent == backup_dir
        assert "IRONCLAD" in backup.name
        assert backup.suffix == ".autosave"
        
        # Verify content was copied
        assert backup.read_text() == mock_autosave.read_text()
    
    def test_create_backup_with_timestamp(self, test_dirs, mock_autosave):
        """Test that backup filename includes timestamp."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        backup = manager.create_backup(mock_autosave)
        
        # Filename should be: IRONCLAD_YYYYMMDD_HHMMSS.autosave
        assert backup is not None
        parts = backup.stem.split("_")
        assert len(parts) >= 3  # At least CHARACTER_DATE_TIME
        assert parts[0] == "IRONCLAD"
    
    def test_create_backup_nonexistent_source(self, test_dirs):
        """Test creating backup from nonexistent file."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        fake_file = saves_dir / "NONEXISTENT.autosave"
        backup = manager.create_backup(fake_file)
        
        assert backup is None
    
    def test_cleanup_old_backups(self, test_dirs):
        """Test cleaning up old backups."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir, max_age_hours=24)
        
        # Create some backup files
        old_backup = backup_dir / "IRONCLAD_20200101_120000.autosave"
        recent_backup = backup_dir / "SILENT_20260520_120000.autosave"
        
        old_backup.write_text("old data")
        recent_backup.write_text("recent data")
        
        # Set old file's modification time to 48 hours ago
        old_time = datetime.now() - timedelta(hours=48)
        import os
        os.utime(old_backup, (old_time.timestamp(), old_time.timestamp()))
        
        # Cleanup
        deleted = manager.cleanup_old_backups()
        
        # Old backup should be deleted, recent should remain
        assert not old_backup.exists()
        assert recent_backup.exists()
        assert deleted == 1
    
    def test_cleanup_no_old_backups(self, test_dirs):
        """Test cleanup when no old backups exist."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir, max_age_hours=24)
        
        # Create only recent backups
        for i in range(3):
            backup = backup_dir / f"IRONCLAD_{i}.autosave"
            backup.write_text(f"data {i}")
        
        deleted = manager.cleanup_old_backups()
        assert deleted == 0
        
        # All files should still exist
        assert len(list(backup_dir.glob("*.autosave"))) == 3
    
    def test_get_backup_stats(self, test_dirs):
        """Test getting backup statistics."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        # Create some backups
        for i in range(3):
            backup = backup_dir / f"IRONCLAD_{i}.autosave"
            backup.write_text("x" * 1024)  # 1KB each
        
        stats = manager.get_backup_stats()
        
        assert stats["total_backups"] == 3
        assert stats["total_size_mb"] > 0
        assert stats["oldest_backup"] is not None
        assert stats["newest_backup"] is not None
    
    def test_get_backup_stats_empty(self, test_dirs):
        """Test stats when no backups exist."""
        saves_dir, backup_dir = test_dirs
        manager = BackupManager(saves_dir, backup_dir)
        
        stats = manager.get_backup_stats()
        
        assert stats["total_backups"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["oldest_backup"] is None
        assert stats["newest_backup"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
