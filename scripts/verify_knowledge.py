#!/usr/bin/env python
"""
Verify the integrity of the knowledge base.

Checks:
- All JSON files are valid
- All expected files exist
- Card/relic/enemy counts are accurate
- Required fields are present
- _meta fields exist in all data files
- No duplicate entries
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Knowledge base directory
KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"


class KnowledgeVerifier:
    """Verifies knowledge base integrity."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict = {}
    
    def error(self, msg: str):
        """Record an error."""
        self.errors.append(f"❌ {msg}")
        logger.error(msg)
    
    def warning(self, msg: str):
        """Record a warning."""
        self.warnings.append(f"⚠️  {msg}")
        logger.warning(msg)
    
    def info(self, msg: str):
        """Log info."""
        logger.info(msg)
    
    def verify_json_valid(self, filepath: Path) -> bool:
        """Verify a JSON file is valid."""
        try:
            with open(filepath, encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.error(f"Invalid JSON in {filepath.name}: {e}")
            return False
        except Exception as e:
            self.error(f"Failed to read {filepath.name}: {e}")
            return False
    
    def verify_meta_field(self, filepath: Path, data: dict) -> bool:
        """Verify _meta field exists and is complete."""
        if "_meta" not in data:
            self.error(f"{filepath.name} missing _meta field")
            return False
        
        meta = data["_meta"]
        required_meta = ["description", "usage"]
        missing = [f for f in required_meta if f not in meta]
        
        if missing:
            self.warning(f"{filepath.name} _meta missing fields: {', '.join(missing)}")
            return False
        
        return True
    
    def verify_required_fields(self, filepath: Path, items: List[Dict], item_type: str) -> bool:
        """Verify required fields exist in all items."""
        required_fields = {
            "card": ["name", "description", "rarity", "type", "color"],
            "relic": ["name", "description"],  # tier/pool are optional since rarity is in filename
            "enemy": ["name", "hp_range", "type"],  # Basic enemy data
            "monster": ["name", "hp_range", "type"],  # Alternative enemy structure
            "potion": ["name", "description"],  # rarity is optional
            "keyword": ["name", "description"],
            "archetype": ["name", "description"]
        }
        
        if item_type not in required_fields:
            return True
        
        required = required_fields[item_type]
        has_errors = False
        
        for i, item in enumerate(items):
            missing = [f for f in required if f not in item]
            if missing:
                self.error(f"{filepath.name} item {i} ({item.get('name', 'unknown')}) missing fields: {', '.join(missing)}")
                has_errors = True
        
        return not has_errors
    
    def verify_no_duplicates(self, filepath: Path, items: List[Dict]) -> bool:
        """Verify no duplicate names."""
        names: Set[str] = set()
        duplicates = []
        
        for item in items:
            name = item.get("name", "").lower()
            if name in names:
                duplicates.append(name)
            names.add(name)
        
        if duplicates:
            self.error(f"{filepath.name} has duplicate names: {', '.join(duplicates)}")
            return False
        
        return True
    
    def verify_card_file(self, filepath: Path) -> Dict:
        """Verify a card file."""
        if not self.verify_json_valid(filepath):
            return {}
        
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        
        self.verify_meta_field(filepath, data)
        
        cards = data.get("cards", [])
        self.verify_required_fields(filepath, cards, "card")
        self.verify_no_duplicates(filepath, cards)
        
        return {"count": len(cards), "file": filepath.name}
    
    def verify_relic_file(self, filepath: Path) -> Dict:
        """Verify a relic file."""
        if not self.verify_json_valid(filepath):
            return {}
        
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        
        self.verify_meta_field(filepath, data)
        
        relics = data.get("relics", [])
        self.verify_required_fields(filepath, relics, "relic")
        self.verify_no_duplicates(filepath, relics)
        
        return {"count": len(relics), "file": filepath.name}
    
    def verify_enemy_file(self, filepath: Path) -> Dict:
        """Verify an enemy file."""
        if not self.verify_json_valid(filepath):
            return {}
        
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        
        self.verify_meta_field(filepath, data)
        
        # Enemy files can have "enemies", "monsters", "elites", or "bosses" as the key
        enemies = (data.get("enemies", []) or 
                  data.get("monsters", []) or 
                  data.get("elites", []) or 
                  data.get("bosses", []))
        
        # Determine item type from data structure
        if enemies:
            item_type = "enemy" if "hp_range" in enemies[0] else "monster"
        else:
            item_type = "enemy"
        
        self.verify_required_fields(filepath, enemies, item_type)
        self.verify_no_duplicates(filepath, enemies)
        
        return {"count": len(enemies), "file": filepath.name}
    
    def verify_structure(self) -> bool:
        """Verify knowledge base structure."""
        self.info("Verifying knowledge base structure...")
        
        # Check main directory exists
        if not KNOWLEDGE_DIR.exists():
            self.error(f"Knowledge directory not found: {KNOWLEDGE_DIR}")
            return False
        
        # Check KNOWLEDGE_MAP.md exists
        map_file = KNOWLEDGE_DIR / "KNOWLEDGE_MAP.md"
        if not map_file.exists():
            self.error("KNOWLEDGE_MAP.md not found")
        else:
            self.info("✓ KNOWLEDGE_MAP.md found")
        
        # Check subdirectories
        required_dirs = ["cards", "relics", "enemies"]
        for dir_name in required_dirs:
            dir_path = KNOWLEDGE_DIR / dir_name
            if not dir_path.exists():
                self.error(f"Required directory not found: {dir_name}/")
            else:
                self.info(f"✓ {dir_name}/ directory found")
        
        # Check required root files
        required_files = ["potions.json", "keywords.json", "archetypes.json"]
        for filename in required_files:
            filepath = KNOWLEDGE_DIR / filename
            if not filepath.exists():
                self.error(f"Required file not found: {filename}")
            else:
                self.info(f"✓ {filename} found")
        
        return len(self.errors) == 0
    
    def verify_cards(self) -> Dict:
        """Verify all card files."""
        self.info("\nVerifying card files...")
        
        card_dir = KNOWLEDGE_DIR / "cards"
        expected_files = [
            "cards_ironclad.json",
            "cards_silent.json",
            "cards_defect.json",
            "cards_watcher.json",
            "cards_colorless.json"
        ]
        
        total_cards = 0
        for filename in expected_files:
            filepath = card_dir / filename
            if not filepath.exists():
                self.error(f"Card file not found: {filename}")
                continue
            
            stats = self.verify_card_file(filepath)
            if stats:
                total_cards += stats["count"]
                self.info(f"✓ {filename}: {stats['count']} cards")
        
        self.stats["cards"] = {"total": total_cards, "files": len(expected_files)}
        return self.stats["cards"]
    
    def verify_relics(self) -> Dict:
        """Verify all relic files."""
        self.info("\nVerifying relic files...")
        
        relic_dir = KNOWLEDGE_DIR / "relics"
        expected_files = [
            "relics_starter.json",
            "relics_common.json",
            "relics_uncommon.json",
            "relics_rare.json",
            "relics_boss.json",
            "relics_shop.json"
        ]
        
        total_relics = 0
        for filename in expected_files:
            filepath = relic_dir / filename
            if not filepath.exists():
                self.error(f"Relic file not found: {filename}")
                continue
            
            stats = self.verify_relic_file(filepath)
            if stats:
                total_relics += stats["count"]
                self.info(f"✓ {filename}: {stats['count']} relics")
        
        self.stats["relics"] = {"total": total_relics, "files": len(expected_files)}
        return self.stats["relics"]
    
    def verify_enemies(self) -> Dict:
        """Verify all enemy files."""
        self.info("\nVerifying enemy files...")
        
        enemy_dir = KNOWLEDGE_DIR / "enemies"
        expected_files = [
            "enemies_act1_monsters.json",
            "enemies_act1_elites.json",
            "enemies_act1_bosses.json",
            "enemies_act2_monsters.json",
            "enemies_act2_elites.json",
            "enemies_act2_bosses.json",
            "enemies_act3_monsters.json",
            "enemies_act3_elites.json",
            "enemies_act3_bosses.json"
        ]
        
        total_enemies = 0
        for filename in expected_files:
            filepath = enemy_dir / filename
            if not filepath.exists():
                self.error(f"Enemy file not found: {filename}")
                continue
            
            stats = self.verify_enemy_file(filepath)
            if stats:
                total_enemies += stats["count"]
                self.info(f"✓ {filename}: {stats['count']} enemies")
        
        self.stats["enemies"] = {"total": total_enemies, "files": len(expected_files)}
        return self.stats["enemies"]
    
    def verify_other_files(self) -> Dict:
        """Verify other knowledge files."""
        self.info("\nVerifying other files...")
        
        other_stats = {}
        
        # Potions
        potions_file = KNOWLEDGE_DIR / "potions.json"
        if potions_file.exists():
            if self.verify_json_valid(potions_file):
                with open(potions_file, encoding='utf-8') as f:
                    data = json.load(f)
                self.verify_meta_field(potions_file, data)
                potions = data.get("potions", [])
                other_stats["potions"] = len(potions)
                self.info(f"✓ potions.json: {len(potions)} potions")
        
        # Keywords
        keywords_file = KNOWLEDGE_DIR / "keywords.json"
        if keywords_file.exists():
            if self.verify_json_valid(keywords_file):
                with open(keywords_file, encoding='utf-8') as f:
                    data = json.load(f)
                self.verify_meta_field(keywords_file, data)
                keywords = data.get("keywords", [])
                other_stats["keywords"] = len(keywords)
                self.info(f"✓ keywords.json: {len(keywords)} keywords")
        
        # Archetypes
        archetypes_file = KNOWLEDGE_DIR / "archetypes.json"
        if archetypes_file.exists():
            if self.verify_json_valid(archetypes_file):
                with open(archetypes_file, encoding='utf-8') as f:
                    data = json.load(f)
                self.verify_meta_field(archetypes_file, data)
                arch_data = data.get("archetypes", {})
                total_arch = sum(len(v.get("archetypes", [])) for v in arch_data.values())
                other_stats["archetypes"] = total_arch
                self.info(f"✓ archetypes.json: {total_arch} archetypes")
        
        # Ascension modifiers (optional)
        asc_file = KNOWLEDGE_DIR / "ascension_modifiers.json"
        if asc_file.exists():
            if self.verify_json_valid(asc_file):
                with open(asc_file, encoding='utf-8') as f:
                    data = json.load(f)
                self.verify_meta_field(asc_file, data)
                modifiers = data.get("modifiers", [])
                other_stats["ascension_modifiers"] = len(modifiers)
                self.info(f"✓ ascension_modifiers.json: {len(modifiers)} modifiers")
        
        self.stats["other"] = other_stats
        return other_stats
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        # Stats
        if self.stats:
            print("\n📈 Knowledge Base Stats:")
            if "cards" in self.stats:
                print(f"  Cards:     {self.stats['cards']['total']} across {self.stats['cards']['files']} files")
            if "relics" in self.stats:
                print(f"  Relics:    {self.stats['relics']['total']} across {self.stats['relics']['files']} files")
            if "enemies" in self.stats:
                print(f"  Enemies:   {self.stats['enemies']['total']} across {self.stats['enemies']['files']} files")
            if "other" in self.stats:
                for key, value in self.stats["other"].items():
                    print(f"  {key.title()}: {value}")
        
        # Errors
        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"  {error}")
        
        # Warnings
        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  {warning}")
        
        # Final result
        print("\n" + "=" * 60)
        if not self.errors:
            print("✅ VERIFICATION PASSED - Knowledge base is valid!")
        else:
            print(f"❌ VERIFICATION FAILED - {len(self.errors)} errors found")
        print("=" * 60)
        
        return len(self.errors) == 0


def main():
    """Run verification."""
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="INFO", format="<level>{message}</level>")
    
    print("=" * 60)
    print("🔍 KNOWLEDGE BASE VERIFICATION")
    print("=" * 60)
    
    verifier = KnowledgeVerifier()
    
    # Run verifications
    verifier.verify_structure()
    verifier.verify_cards()
    verifier.verify_relics()
    verifier.verify_enemies()
    verifier.verify_other_files()
    
    # Print summary
    success = verifier.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
