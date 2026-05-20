"""Unit tests for the logging system."""

import pytest
from pathlib import Path
from datetime import datetime
import shutil
from src.utils.logger import setup_logger, log_operation, LoggerConfig


class TestLogger:
    """Test cases for the logging system."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down test environment."""
        # Setup: Create test log directory
        self.test_log_dir = Path("logs") / "test"
        self.test_log_dir.mkdir(parents=True, exist_ok=True)
        
        yield
        
        # Teardown: Clean up test logs
        # (Commented out to allow inspection - uncomment in production)
        # if self.test_log_dir.exists():
        #     shutil.rmtree(self.test_log_dir.parent)
    
    def test_logger_initialization(self):
        """Test that logger initializes correctly."""
        log = setup_logger("test")
        assert log is not None
        
        # Verify log directory was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = LoggerConfig.LOG_BASE_DIR / today
        assert log_dir.exists()
    
    def test_component_specific_logs(self):
        """Test that different components create separate log files."""
        components = ["backup", "parsing", "voice", "llm", "summary"]
        
        for component in components:
            log = setup_logger(component)
            log.info(f"Test message for {component}")
        
        # Verify each component's log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = LoggerConfig.LOG_BASE_DIR / today
        
        for component in components:
            log_file = log_dir / LoggerConfig.COMPONENTS[component]
            assert log_file.exists(), f"Log file not created for {component}"
    
    def test_error_log_created(self):
        """Test that errors.log is created automatically."""
        log = setup_logger("test")
        log.error("Test error message")
        
        # Verify errors.log exists
        today = datetime.now().strftime("%Y-%m-%d")
        error_log = LoggerConfig.LOG_BASE_DIR / today / "errors.log"
        assert error_log.exists()
        
        # Verify error was written to errors.log
        content = error_log.read_text()
        assert "Test error message" in content
    
    def test_log_operation_structured(self):
        """Test structured operation logging."""
        log = setup_logger("test")
        
        log_operation(
            log,
            "test_operation",
            {
                "file": "test.txt",
                "size": 1024,
                "duration": "0.5s"
            },
            level="INFO"
        )
        
        # Verify log was written
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LoggerConfig.LOG_BASE_DIR / today / "test.log"
        content = log_file.read_text()
        
        assert "test_operation" in content
        assert "file=test.txt" in content
        assert "size=1024" in content
    
    def test_log_levels(self):
        """Test that different log levels work correctly."""
        log = setup_logger("test")
        
        log.debug("Debug message")
        log.info("Info message")
        log.warning("Warning message")
        log.error("Error message")
        
        # Verify log file contains messages
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LoggerConfig.LOG_BASE_DIR / today / "test.log"
        content = log_file.read_text()
        
        assert "Debug message" in content
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content
    
    def test_daily_log_directory_creation(self):
        """Test that daily directories are created automatically."""
        log = setup_logger("test")
        log.info("Test message")
        
        # Verify today's directory exists
        today = datetime.now().strftime("%Y-%m-%d")
        daily_dir = LoggerConfig.LOG_BASE_DIR / today
        assert daily_dir.exists()
        assert daily_dir.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
