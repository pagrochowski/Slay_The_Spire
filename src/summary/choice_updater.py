"""
Choice Updater for Run Summary.

Updates the "Current choice:" section in Run_Summary.md with new card/relic choices.
"""

from pathlib import Path
from typing import List
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("summary")


class ChoiceUpdater:
    """Updates choice section in run summary."""
    
    def __init__(self):
        """Initialize choice updater."""
        log.info("ChoiceUpdater initialized")
    
    def update_choice_section(self, summary_path: Path, choices: List[str]) -> bool:
        """
        Update the "Current choice:" section in the summary file.
        
        Args:
            summary_path: Path to Run_Summary.md file
            choices: List of choice items (card/relic names)
            
        Returns:
            True if update successful, False otherwise
        """
        log.info(f"Updating choice section with {len(choices)} items")
        log_operation(log, "update_choice_start", {
            "file": summary_path.name,
            "choice_count": len(choices)
        })
        
        if not summary_path.exists():
            log.error(f"Summary file not found: {summary_path}")
            return False
        
        try:
            # Read current content
            content = summary_path.read_text(encoding='utf-8')
            
            # Find the "Current choice:" section
            choice_marker = "**Current choice:**"
            end_marker = "\n---"
            
            choice_start = content.find(choice_marker)
            if choice_start == -1:
                log.warning("Current choice section not found in summary")
                # Append new choice section at the end
                new_choice_section = self._format_choice_section(choices)
                content += "\n" + new_choice_section + "\n---\n"
            else:
                # Find end of choice section
                choice_end = content.find(end_marker, choice_start)
                if choice_end == -1:
                    choice_end = len(content)
                
                # Log what we're replacing
                old_section = content[choice_start:choice_end].strip()
                log.debug(f"Replacing choice section:\n{old_section[:100]}...")
                
                # Replace the section
                new_choice_section = self._format_choice_section(choices)
                content = (
                    content[:choice_start] +
                    new_choice_section +
                    "\n" +
                    content[choice_end:]
                )
            
            # Write updated content
            summary_path.write_text(content, encoding='utf-8')
            
            log.info(f"Choice section updated successfully")
            log_operation(log, "update_choice_complete", {
                "file": summary_path.name,
                "choices": ", ".join(choices) if len(choices) <= 5 else f"{len(choices)} choices"
            })
            
            return True
            
        except Exception as e:
            log.error(f"Failed to update choice section: {e}")
            log_operation(log, "update_choice_failed", {
                "error": str(e)
            }, level="ERROR")
            return False
    
    def _format_choice_section(self, choices: List[str]) -> str:
        """
        Format the choice section with choices and SKIP?.
        
        Args:
            choices: List of choice items
            
        Returns:
            Formatted choice section string
        """
        lines = ["**Current choice:**"]
        
        # Add each choice
        for choice in choices:
            lines.append(f"- {choice}")
        
        # Always end with SKIP?
        lines.append("- SKIP?")
        
        return "\n".join(lines)
    
    def add_choices_to_summary(self, summary_path: Path, new_choices: List[str], append: bool = False) -> bool:
        """
        Add new choices to the summary (either replacing or appending).
        
        Args:
            summary_path: Path to Run_Summary.md file
            new_choices: List of new choice items
            append: If True, append to existing choices; if False, replace them
            
        Returns:
            True if update successful, False otherwise
        """
        if append:
            # Get existing choices first
            existing = self._extract_existing_choices(summary_path)
            # Combine and deduplicate
            all_choices = list(dict.fromkeys(existing + new_choices))
            return self.update_choice_section(summary_path, all_choices)
        else:
            # Replace entirely
            return self.update_choice_section(summary_path, new_choices)
    
    def _extract_existing_choices(self, summary_path: Path) -> List[str]:
        """
        Extract existing choice items from summary.
        
        Args:
            summary_path: Path to Run_Summary.md file
            
        Returns:
            List of existing choice items (excluding SKIP?)
        """
        if not summary_path.exists():
            return []
        
        try:
            content = summary_path.read_text(encoding='utf-8')
            
            # Find the choice section
            choice_marker = "**Current choice:**"
            end_marker = "\n---"
            
            choice_start = content.find(choice_marker)
            if choice_start == -1:
                return []
            
            choice_end = content.find(end_marker, choice_start)
            if choice_end == -1:
                choice_end = len(content)
            
            # Extract the section
            choice_section = content[choice_start:choice_end]
            
            # Parse choice lines
            choices = []
            for line in choice_section.split('\n'):
                line = line.strip()
                if line.startswith('- ') and not line.endswith('SKIP?'):
                    # Remove "- " prefix
                    choice_text = line[2:].strip()
                    if choice_text:
                        choices.append(choice_text)
            
            return choices
            
        except Exception as e:
            log.warning(f"Failed to extract existing choices: {e}")
            return []


if __name__ == "__main__":
    # Test the choice updater
    from src.core.config import Config
    from datetime import datetime
    import shutil
    
    print("Choice Updater Test")
    print("=" * 50)
    
    # Create a backup of the current Run_Summary.md
    summary_path = Config.RUN_SUMMARY_PATH
    backup_path = Config.PROJECT_ROOT / "Run_Summary.md.backup"
    
    if summary_path.exists():
        shutil.copy2(summary_path, backup_path)
        print(f"\n1. Created backup: {backup_path.name}")
    else:
        print(f"\n1. No existing summary found")
    
    # Initialize updater
    updater = ChoiceUpdater()
    
    # Test updating with new choices
    print("\n2. Testing choice update...")
    test_choices = [
        "Battle Hymn [1] (Power): At the start of each turn, add a *Smite into your hand.",
        "Third Eye [1] (Skill): Gain 7 Block. Scry 3.",
        "Foresight [1] (Power): At the start of your turn, Scry 3."
    ]
    
    success = updater.update_choice_section(summary_path, test_choices)
    
    if success:
        print("   ✅ Choice section updated")
        
        # Read and display the updated section
        content = summary_path.read_text(encoding='utf-8')
        choice_start = content.find("**Current choice:**")
        choice_end = content.find("\n---", choice_start)
        if choice_start != -1:
            choice_section = content[choice_start:choice_end] if choice_end != -1 else content[choice_start:]
            print(f"\n3. Updated choice section:")
            print(choice_section)
    else:
        print("   ❌ Failed to update choice section")
    
    # Test extracting existing choices
    print("\n4. Testing choice extraction...")
    existing = updater._extract_existing_choices(summary_path)
    print(f"   Found {len(existing)} existing choices")
    
    # Test appending choices
    print("\n5. Testing append mode...")
    new_choice = ["Tantrum [1] (Attack): Deal 3 damage 3 times."]
    updater.add_choices_to_summary(summary_path, new_choice, append=True)
    
    # Restore backup
    if backup_path.exists():
        print(f"\n6. Restoring original summary from backup")
        shutil.copy2(backup_path, summary_path)
        backup_path.unlink()
        print("   ✅ Original restored")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
