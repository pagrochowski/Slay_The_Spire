"""
Run Summary Generator for Slay the Spire.

Generates formatted Run_Summary.md from parsed save data.
"""

from pathlib import Path
from typing import Dict, List, Optional, Counter
from collections import Counter as CollectionCounter
from src.knowledge.knowledge_base import KnowledgeBase
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("summary")


class RunSummaryGenerator:
    """Generates formatted run summaries."""
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialize summary generator.
        
        Args:
            knowledge_base: KnowledgeBase instance (creates new one if None)
        """
        self.kb = knowledge_base or KnowledgeBase()
        log.info("RunSummaryGenerator initialized")
    
    def _format_card_with_details(self, card_id: str) -> str:
        """
        Format a card with cost, type, and description.
        
        Args:
            card_id: Card ID (may include +/++ for upgrades)
            
        Returns:
            Formatted string: "CardName [Cost] (Type): Description"
        """
        # Strip upgrade markers
        base_name = card_id.rstrip('+')
        upgrade_count = card_id.count('+')
        
        # Get card data
        card_data = self.kb.get_card_data(base_name)
        
        if not card_data:
            # Fallback if card not found - return basic format
            display_name = base_name + ("+" * upgrade_count) if upgrade_count > 0 else base_name
            return f"{display_name}"
        
        # Determine cost (upgraded or base)
        if upgrade_count > 0 and "cost_upgraded" in card_data:
            cost = card_data.get("cost_upgraded", card_data.get("cost", "?"))
            description = card_data.get("description_upgraded", card_data.get("description", ""))
        else:
            cost = card_data.get("cost", "?")
            description = card_data.get("description", "")
        
        # Make description single-line (replace newlines with spaces)
        description = description.replace('\n', ' ').strip()
        
        card_type = card_data.get("type", "").capitalize()
        
        # Format with upgrade markers
        display_name = base_name + ("+" * upgrade_count) if upgrade_count > 0 else base_name
        
        return f"{display_name} [{cost}] ({card_type}): {description}"
    
    def _format_deck_cards(self, deck: List[str]) -> List[str]:
        """
        Format deck cards with multipliers for duplicates.
        
        Args:
            deck: List of card IDs
            
        Returns:
            List of formatted card strings (one per unique card)
        """
        # Count card occurrences
        card_counts = CollectionCounter(deck)
        
        # Format each unique card
        formatted_cards = []
        for card_id, count in sorted(card_counts.items()):
            formatted = self._format_card_with_details(card_id)
            
            # Add multiplier if more than 1
            if count > 1:
                formatted = f"{count}x " + formatted
            else:
                formatted = formatted
            
            formatted_cards.append(formatted)
        
        return formatted_cards
    
    def _format_relic_with_description(self, relic_name: str) -> str:
        """
        Format a relic with its description.
        
        Args:
            relic_name: Relic name (may include counter like "Molten Egg 2")
            
        Returns:
            Formatted string: "RelicName (Counter: X): Description"
        """
        # Extract bottled card metadata if present (e.g., "Bottled Flame [Bowling Bash]")
        import re
        bottled_card = None
        base_name = relic_name
        bottled_match = re.search(r'\s+\[(.+)\]$', relic_name)
        if bottled_match:
            bottled_card = bottled_match.group(1)
            base_name = relic_name[:bottled_match.start()]

        # Extract counter if present (e.g., "Molten Egg 2" → "Molten Egg", counter=2)
        counter = None
        counter_match = re.search(r'\s+(\d+)$', relic_name)
        if counter_match:
            counter = counter_match.group(1)
            base_name = base_name[:counter_match.start()]
        
        relic_data = self.kb.get_relic_data(base_name)
        
        if not relic_data:
            return f"{relic_name}"  # Just return name if not found
        
        description = relic_data.get("description", "")
        
        # Format with counter if present
        if counter:
            return f"{base_name} (Counter: {counter}): {description}"
        if bottled_card:
            return f"{base_name} ({bottled_card}): {description}"
        else:
            return f"{base_name}: {description}"
    
    def _format_potion_with_description(self, potion_name: str) -> str:
        """
        Format a potion with its description.
        
        Args:
            potion_name: Potion name
            
        Returns:
            Formatted string: "PotionName: Description"
        """
        # Clean potion ID (remove " Potion" suffix if present in ID)
        clean_name = potion_name.replace(" Potion", "").strip()
        
        # Try to find potion data
        potion_data = self.kb.get_potion_data(potion_name)
        if not potion_data:
            potion_data = self.kb.get_potion_data(clean_name)
        
        if not potion_data:
            return f"{potion_name}"  # Just return name if not found
        
        description = potion_data.get("description", "")
        display_name = potion_data.get("name", potion_name)
        
        return f"{display_name}: {description}"
    
    def generate_summary(
        self,
        run_data: Dict,
        output_path: Optional[Path] = None,
        preserve_choice: bool = True,
        current_choice_image: Optional[Path] = None,
    ) -> str:
        """
        Generate formatted run summary markdown.
        
        Args:
            run_data: Parsed run data from SaveParser
            output_path: Optional path to write summary file
            preserve_choice: If True and file exists, preserve existing "Current choice" section
            current_choice_image: Optional screenshot path for the current choice prompt
            
        Returns:
            Formatted markdown string
        """
        log.info("Generating run summary")
        log_operation(log, "generate_summary_start", {
            "character": run_data.get("character", "UNKNOWN"),
            "deck_size": len(run_data.get("deck", []))
        })
        
        # Extract current choice section if preserving
        existing_choice = ""
        if preserve_choice and output_path and output_path.exists():
            try:
                content = output_path.read_text(encoding='utf-8')
                if "**Current choice:**" in content:
                    # Extract everything from "Current choice" to the end or next section
                    choice_start = content.find("**Current choice:**")
                    choice_end = content.find("\n---", choice_start)
                    if choice_end == -1:
                        choice_end = len(content)
                    existing_choice = content[choice_start:choice_end].strip()
            except Exception as e:
                log.warning(f"Could not preserve existing choice: {e}")
        
        # Build summary sections
        character = run_data.get("character", "UNKNOWN")
        ascension = run_data.get("ascension", 0)
        act = run_data.get("act", 1)
        floor = run_data.get("floor", 0)
        current_hp = run_data.get("current_hp", 0)
        max_hp = run_data.get("max_hp", 0)
        gold = run_data.get("gold", 0)
        
        # Keys
        ruby = "✓" if run_data.get("has_ruby_key", False) else "✗"
        emerald = "✓" if run_data.get("has_emerald_key", False) else "✗"
        sapphire = "✓" if run_data.get("has_sapphire_key", False) else "✗"
        
        # Boss
        boss = run_data.get("boss", "Unknown")
        
        # Elites defeated
        elites = run_data.get("elites_defeated", [])
        if elites:
            elites_text = ", ".join(elites)
        else:
            elites_text = "None"
        
        # Format deck
        deck_cards = self._format_deck_cards(run_data.get("deck", []))
        deck_section = "\n".join(f"- {card}" for card in deck_cards)
        
        # Format relics
        relics = run_data.get("relics", [])
        relic_section = "\n".join(f"- {self._format_relic_with_description(relic)}" for relic in relics)
        
        # Format potions
        potions = run_data.get("potions", [])
        potion_section = "\n".join(f"- {self._format_potion_with_description(potion)}" for potion in potions)
        
        # Build full summary
        summary = f"""# Slay the Spire Run Summary

## Run Information
- **Character**: {character}
- **Ascension**: {ascension}
- **Act**: {act}
- **Floor**: {floor}

## Current Status
- **HP**: {current_hp}/{max_hp}
- **Gold**: {gold}

## Deck ({len(run_data.get('deck', []))} cards)
{deck_section if deck_section else "- No cards"}

## Relics
{relic_section if relic_section else "- No relics"}

## Potions
{potion_section if potion_section else "- No potions"}

## Keys
- Ruby: {ruby}
- Emerald: {emerald}
- Sapphire: {sapphire}

## Boss & Elites
- **Current Boss**: {boss}
- **Elites defeated this act:** {elites_text}

"""
        
        # Generate choice section with voice choices (always check for updates)
        from src.choice.choice_persistence import ChoicePersistence
        choice_persist = ChoicePersistence()
        
        # Check if we should clear old choice due to floor change
        current_floor = run_data.get('floor', 0)
        current_act = run_data.get('act', 1)
        
        if choice_persist.should_clear_choice(current_floor, current_act):
            choice_persist.clear_choice()
            log.info(f"Cleared old choice - floor changed to {current_act}/{current_floor}")
        
        # Get formatted voice choice text
        voice_choice_text = choice_persist.format_choice_text()
        
        if existing_choice:
            summary += existing_choice + "\n\n"
        else:
            image_reference = "As per screenshot"
            if current_choice_image is not None:
                image_path = Path(current_choice_image)
                image_reference = image_path.name

            summary += f"**Current choice:**\n{image_reference}\n"

            if voice_choice_text:
                summary += "\n" + voice_choice_text + "\n"

            summary += "\n- SKIP?\n\n"

        
        summary += "---\n"
        
        # Write to file if path provided
        if output_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(summary, encoding='utf-8')
                log.info(f"Summary written to: {output_path}")
                log_operation(log, "summary_written", {
                    "file": output_path.name,
                    "size": len(summary)
                })
            except Exception as e:
                log.error(f"Failed to write summary: {e}")
                log_operation(log, "summary_write_failed", {
                    "error": str(e)
                }, level="ERROR")
        
        return summary


if __name__ == "__main__":
    # Test the summary generator
    from src.core.config import Config
    from src.core.backup_manager import BackupManager
    from src.core.save_parser import SaveParser
    from datetime import datetime
    
    print("Run Summary Generator Test")
    print("=" * 50)
    
    # Get latest save and parse it
    backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
    latest_save = backup_mgr.find_latest_autosave()
    
    if not latest_save:
        print("❌ No autosave file found")
        exit(1)
    
    print(f"\n1. Found save: {latest_save.name}")
    
    # Create backup and parse
    backup = backup_mgr.create_backup(latest_save)
    parser = SaveParser()
    run_data = parser.parse_and_extract(backup)
    
    if not run_data:
        print("❌ Failed to parse save")
        exit(1)
    
    print(f"2. Parsed run data for {run_data['character']}")
    
    # Generate summary
    print("\n3. Generating summary...")
    generator = RunSummaryGenerator()
    summary = generator.generate_summary(run_data, Config.RUN_SUMMARY_PATH)
    
    print(f"\n4. Summary generated:")
    print("=" * 50)
    print(summary[:500] + "..." if len(summary) > 500 else summary)
    print("=" * 50)
    
    print(f"\n✅ Full summary written to: {Config.RUN_SUMMARY_PATH}")
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
