"""
Migrate data from data/raw/ and database to data/knowledge/ structure.
Creates split, well-organized JSON files with LLM-friendly metadata.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Paths
RAW_DIR = Path("data/raw")
KNOWLEDGE_DIR = Path("data/knowledge")
DB_PATH = Path("db/sts_knowledge.db")

# Color mappings
COLOR_MAP = {
    "Red": "RED",
    "Green": "GREEN", 
    "Blue": "BLUE",
    "Purple": "PURPLE",
    "Colorless": "COLORLESS",
    "Curse": "CURSE",
    "Status": "STATUS"
}

POOL_MAP = {
    "Starter": "starter",
    "Red": "ironclad",
    "Green": "silent",
    "Blue": "defect",
    "Purple": "watcher"
}

def normalize_color(color: str) -> str:
    """Normalize color to uppercase standard."""
    return COLOR_MAP.get(color, color.upper())

def parse_card_description(desc: str) -> Dict[str, Any]:
    """Extract damage, block, and magic numbers from card description."""
    import re
    
    result = {
        "damage": None,
        "block": None,
        "magic_number": None
    }
    
    # Extract damage (Deal X damage)
    damage_match = re.search(r'Deal (\d+) damage', desc)
    if damage_match:
        result["damage"] = int(damage_match.group(1))
    
    # Extract block (Gain X Block)
    block_match = re.search(r'Gain (\d+) Block', desc)
    if block_match:
        result["block"] = int(block_match.group(1))
    
    # Extract first number that might be magic number (Apply X, Draw X, etc.)
    magic_patterns = [
        r'Apply (\d+)',
        r'Draw (\d+)',
        r'Channel (\d+)',
        r'Gain (\d+) [A-Z][a-z]+',  # Gain X Strength, etc.
    ]
    for pattern in magic_patterns:
        magic_match = re.search(pattern, desc)
        if magic_match:
            result["magic_number"] = int(magic_match.group(1))
            break
    
    return result

def load_raw_cards() -> List[Dict]:
    """Load cards from data/raw/cards.json."""
    with open(RAW_DIR / "cards.json", "r", encoding="utf-8") as f:
        cards = json.load(f)
    
    # Process cards (combine base + upgraded into single entry)
    processed = {}
    for card in cards:
        name = card["name"].rstrip("+")
        is_upgraded = card["name"].endswith("+")
        
        if name not in processed:
            # Parse base description
            parsed = parse_card_description(card["description"])
            processed[name] = {
                "name": name,
                "color": normalize_color(card["color"]),
                "rarity": card["rarity"].upper(),
                "type": card["type"].upper(),
                "cost": int(card["cost"]) if card["cost"].isdigit() else card["cost"],
                "description": card["description"],
                "damage": parsed["damage"],
                "block": parsed["block"],
                "magic_number": parsed["magic_number"],
                "exhausts": "Exhaust" in card["description"],
                "is_innate": "Innate" in card["description"],
                "is_ethereal": "Ethereal" in card["description"],
                "targets_all": "ALL" in card["description"] or "all enemies" in card["description"].lower()
            }
        
        if is_upgraded:
            # Add upgraded info
            parsed_up = parse_card_description(card["description"])
            processed[name]["cost_upgraded"] = int(card["cost"]) if card["cost"].isdigit() else card["cost"]
            processed[name]["description_upgraded"] = card["description"]
            processed[name]["damage_upgraded"] = parsed_up["damage"]
            processed[name]["block_upgraded"] = parsed_up["block"]
            processed[name]["magic_number_upgraded"] = parsed_up["magic_number"]
    
    return list(processed.values())

def load_raw_relics() -> List[Dict]:
    """Load relics from data/raw/relics.json."""
    with open(RAW_DIR / "relics.json", "r", encoding="utf-8") as f:
        relics = json.load(f)
    
    processed = []
    for relic in relics:
        processed.append({
            "name": relic["name"],
            "tier": relic["tier"],
            "pool": relic.get("pool", "Common"),
            "description": relic["description"],
            "flavor_text": relic.get("flavorText", "")
        })
    
    return processed

def load_raw_potions() -> List[Dict]:
    """Load potions from data/raw/potions.json."""
    with open(RAW_DIR / "potions.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_raw_keywords() -> List[Dict]:
    """Load keywords from data/raw/keywords.json."""
    with open(RAW_DIR / "keywords.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_raw_archetypes() -> Dict:
    """Load archetypes from data/raw/archetypes.json."""
    with open(RAW_DIR / "archetypes.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_enemies_from_db() -> List[Dict]:
    """Load enemies from database."""
    if not DB_PATH.exists():
        print(f"Warning: Database not found at {DB_PATH}")
        return []
    
    # Manual act mapping based on Slay the Spire wiki
    ACT_MAPPING = {
        # Act 1 Normal
        "Cultist": 1, "Jaw Worm": 1, "Louse": 1, "Acid Slime (S)": 1, "Acid Slime (M)": 1,
        "Spike Slime (S)": 1, "Spike Slime (M)": 1, "Fungi Beast": 1, "Fat Gremlin": 1,
        "Gremlin Wizard": 1, "Gremlin Warrior": 1, "Mad Gremlin": 1, "Shield Gremlin": 1,
        "Sneaky Gremlin": 1, "Looter": 1, "Mugger": 1,
        # Act 1 Elites
        "Gremlin Nob": 1, "Lagavulin": 1, "Lagavulin (Awake)": 1, "Sentry": 1,
        # Act 1 Bosses
        "Slime Boss": 1, "The Guardian": 1, "Hexaghost": 1,
        # Act 2 Normal
        "Spheric Guardian": 1, "Chosen": 2, "Byrd": 2, "Byrd (Grounded)": 2,
        "Cultist": 2, "Fungi Beast": 2, "Looter": 2, "Mugger": 2,
        "Shelled Parasite": 2, "Snake Plant": 2, "Snecko": 2, "Taskmaster": 2,
        "Centurion": 2, "Mystic": 2, "Apology Slime": 2,
        # Act 2 Elites
        "Gremlin Leader": 2, "Slavers": 2, "Slaver": 2, "Book of Stabbing": 2,
        # Act 2 Bosses
        "Bronze Automaton": 2, "The Champ": 2, "The Collector": 2,
        # Act 3 Normal
        "Darkling": 3, "Orb Walker": 3, "Reptomancer": 3, "Shelled Parasite": 3,
        "Spiker": 3, "Spire Growth": 3, "Transient": 3, "Writhing Mass": 3,
        "Exploder": 3, "Dagger": 3, "Pointy": 3, "Romeo": 3,
        "Bear": 3, "Spire Shield": 3, "Spire Spear": 3,
        # Act 3 Elites
        "Giant Head": 3, "Nemesis": 3, "Reptomancer": 3,
        # Act 3 Bosses
        "Awakened One": 3, "Donu": 3, "Deca": 3, "Time Eater": 3,
        # Act 4
        "Corrupt Heart": 4, "Spire Shield": 4, "Spire Spear": 4,
        # Characters (not enemies, will be filtered)
        "the Ironclad": None, "the Silent": None, "the Defect": None, "the Watcher": None
    }
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM enemies")
    enemies = []
    for row in cursor.fetchall():
        enemy_dict = dict(row)
        name = enemy_dict.get("name", "")
        
        # Skip character entries
        if name in ["the Ironclad", "the Silent", "the Defect", "the Watcher"]:
            continue
        
        # Apply act mapping if not already set
        if not enemy_dict.get("act") and name in ACT_MAPPING:
            enemy_dict["act"] = ACT_MAPPING[name]
        
        enemies.append(enemy_dict)
    
    conn.close()
    return enemies

def load_ascension_modifiers_from_db() -> List[Dict]:
    """Load ascension modifiers from database."""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ascension_modifiers ORDER BY ascension_level")
    modifiers = []
    for row in cursor.fetchall():
        modifiers.append(dict(row))
    
    conn.close()
    return modifiers

def split_cards_by_character(cards: List[Dict]) -> Dict[str, List[Dict]]:
    """Split cards by character."""
    splits = {
        "ironclad": [],
        "silent": [],
        "defect": [],
        "watcher": [],
        "colorless": []
    }
    
    for card in cards:
        color = card["color"]
        if color == "RED":
            splits["ironclad"].append(card)
        elif color == "GREEN":
            splits["silent"].append(card)
        elif color == "BLUE":
            splits["defect"].append(card)
        elif color == "PURPLE":
            splits["watcher"].append(card)
        else:
            splits["colorless"].append(card)
    
    return splits

def split_relics_by_pool(relics: List[Dict]) -> Dict[str, List[Dict]]:
    """Split relics by acquisition pool."""
    splits = {
        "starter": [],
        "common": [],
        "uncommon": [],
        "rare": [],
        "boss": [],
        "shop": [],
        "event": []
    }
    
    for relic in relics:
        tier = relic["tier"].lower()
        if tier == "starter":
            splits["starter"].append(relic)
        elif tier == "common":
            splits["common"].append(relic)
        elif tier == "uncommon":
            splits["uncommon"].append(relic)
        elif tier == "rare":
            splits["rare"].append(relic)
        elif tier == "boss":
            splits["boss"].append(relic)
        elif tier == "shop":
            splits["shop"].append(relic)
        elif tier == "event":
            splits["event"].append(relic)
        else:
            # Default to common if unknown
            splits["common"].append(relic)
    
    return splits

def split_enemies_by_act(enemies: List[Dict]) -> Dict[str, List[Dict]]:
    """Split enemies by act."""
    splits = {
        "act1": [],
        "act2": [],
        "act3": []
    }
    
    for enemy in enemies:
        act = enemy.get("act")
        if act == 1:
            splits["act1"].append(enemy)
        elif act == 2:
            splits["act2"].append(enemy)
        elif act in [3, 4]:
            splits["act3"].append(enemy)
        else:
            # If no act specified, try to infer or skip
            print(f"Warning: Enemy '{enemy.get('name', 'Unknown')}' has no act specified")
    
    return splits

def create_meta(file_name: str, description: str, usage: str, count: int) -> Dict:
    """Create metadata for a knowledge file."""
    return {
        "file": file_name,
        "description": description,
        "usage": usage,
        "count": count,
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }

def save_json(path: Path, data: Dict):
    """Save JSON file with nice formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Print confirmation with item count if available
    if 'count' in data.get('_meta', {}):
        print(f"✓ Created {path.name} ({data['_meta']['count']} items)")
    else:
        print(f"✓ Created {path.name}")

def main():
    print("=" * 60)
    print("MIGRATING TO KNOWLEDGE BASE")
    print("=" * 60)
    
    # Load raw data
    print("\n📥 Loading raw data...")
    cards = load_raw_cards()
    relics = load_raw_relics()
    potions = load_raw_potions()
    keywords = load_raw_keywords()
    archetypes = load_raw_archetypes()
    enemies = load_enemies_from_db()
    ascension_mods = load_ascension_modifiers_from_db()
    
    print(f"  Cards: {len(cards)}")
    print(f"  Relics: {len(relics)}")
    print(f"  Potions: {len(potions)}")
    print(f"  Keywords: {len(keywords)}")
    print(f"  Enemies: {len(enemies)}")
    print(f"  Ascension Modifiers: {len(ascension_mods)}")
    
    # Split data
    print("\n📦 Splitting data by category...")
    card_splits = split_cards_by_character(cards)
    relic_splits = split_relics_by_pool(relics)
    enemy_splits = split_enemies_by_act(enemies)
    
    # Save cards
    print("\n💾 Saving card files...")
    for char, char_cards in card_splits.items():
        if char_cards:
            file_data = {
                "_meta": create_meta(
                    f"cards_{char}.json",
                    f"All {char.title()} cards with stats and descriptions",
                    f"Load when: player is {char.title()}, asking about {char.title()} cards, evaluating card rewards",
                    len(char_cards)
                ),
                "cards": sorted(char_cards, key=lambda c: (c["rarity"], c["name"]))
            }
            save_json(KNOWLEDGE_DIR / "cards" / f"cards_{char}.json", file_data)
    
    # Save relics
    print("\n💾 Saving relic files...")
    for pool, pool_relics in relic_splits.items():
        if pool_relics:
            file_data = {
                "_meta": create_meta(
                    f"relics_{pool}.json",
                    f"{pool.title()} pool relics",
                    f"Load when: evaluating {pool} relics, checking relic rewards",
                    len(pool_relics)
                ),
                "relics": sorted(pool_relics, key=lambda r: r["name"])
            }
            save_json(KNOWLEDGE_DIR / "relics" / f"relics_{pool}.json", file_data)
    
    # Save enemies
    print("\n💾 Saving enemy files...")
    for act, act_enemies in enemy_splits.items():
        if act_enemies:
            file_data = {
                "_meta": create_meta(
                    f"enemies_{act}.json",
                    f"{act.upper()} enemies with patterns and strategy",
                    f"Load when: in {act.upper()}, planning fights, asking about {act.upper()} enemies",
                    len(act_enemies)
                ),
                "enemies": sorted(act_enemies, key=lambda e: e.get("name", ""))
            }
            save_json(KNOWLEDGE_DIR / "enemies" / f"enemies_{act}.json", file_data)
    
    # Save potions
    print("\n💾 Saving potions.json...")
    potion_data = {
        "_meta": create_meta(
            "potions.json",
            "All potions with descriptions and effects",
            "Load when: asking about potions, evaluating potion rewards",
            len(potions)
        ),
        "potions": sorted(potions, key=lambda p: p.get("name", ""))
    }
    save_json(KNOWLEDGE_DIR / "potions.json", potion_data)
    
    # Save keywords
    print("\n💾 Saving keywords.json...")
    keyword_data = {
        "_meta": create_meta(
            "keywords.json",
            "Game mechanics and keyword definitions",
            "Load when: explaining game mechanics, clarifying keyword meanings",
            len(keywords)
        ),
        "keywords": sorted(keywords, key=lambda k: k.get("name", ""))
    }
    save_json(KNOWLEDGE_DIR / "keywords.json", keyword_data)
    
    # Save archetypes
    print("\n💾 Saving archetypes.json...")
    archetype_data = {
        "_meta": create_meta(
            "archetypes.json",
            "Deck archetypes for each character",
            "Load when: suggesting deck direction, identifying build type",
            sum(len(v) for v in archetypes.values())
        ),
        "archetypes": archetypes
    }
    save_json(KNOWLEDGE_DIR / "archetypes.json", archetype_data)
    
    # Save ascension modifiers
    if ascension_mods:
        print("\n💾 Saving ascension_modifiers.json...")
        asc_data = {
            "_meta": create_meta(
                "ascension_modifiers.json",
                "Ascension level modifiers and difficulty scaling",
                "Load when: checking ascension effects, understanding difficulty changes",
                len(ascension_mods)
            ),
            "modifiers": ascension_mods
        }
        save_json(KNOWLEDGE_DIR / "ascension_modifiers.json", asc_data)
    
    # Create knowledge map (markdown format)
    print("\n🗺️  Creating KNOWLEDGE_MAP.md...")
    
    # Generate markdown content
    today = datetime.now().strftime("%Y-%m-%d")
    total_cards = sum(len(splits) for splits in card_splits.values())
    total_relics = sum(len(splits) for splits in relic_splits.values())
    
    # Count enemies from the generated files (if they exist)
    total_enemies = sum(len(splits) for splits in enemy_splits.items())
    
    md_content = f"""# Knowledge Base Map

**🎯 START HERE** - Master index for the Slay the Spire knowledge base

**Purpose:** Guide the LLM to load only the relevant knowledge files based on context  
**Usage:** Always consult this file first to determine which JSON files to load  
**Last Updated:** {today}

---

## 📋 Loading Strategy

### Always Load
- `KNOWLEDGE_MAP.md` (this file) - Read first to understand available knowledge

### Context-Based Loading

**By Character:**
- Load `cards/cards_{{character}}.json` when player character is known
- Load relevant archetypes for that character

**By Act:**
- Load `enemies/enemies_act{{N}}_{{type}}.json` when player act is known
- Load all three types: monsters, elites, bosses

**On Demand:**
- Load specific relic pools only when evaluating relic choices
- Load potions, keywords only when needed for specific queries

---

## 📁 File Inventory

### Cards (5 files, {total_cards} total cards)

#### `cards/cards_ironclad.json` ({len(card_splits['ironclad'])} cards)
**Load when:**
- Player is Ironclad
- Asking about red cards
- Evaluating Ironclad card rewards

#### `cards/cards_silent.json` ({len(card_splits['silent'])} cards)
**Load when:**
- Player is Silent
- Asking about green cards
- Evaluating Silent card rewards

#### `cards/cards_defect.json` ({len(card_splits['defect'])} cards)
**Load when:**
- Player is Defect
- Asking about blue cards
- Evaluating Defect card rewards

#### `cards/cards_watcher.json` ({len(card_splits['watcher'])} cards)
**Load when:**
- Player is Watcher
- Asking about purple cards
- Evaluating Watcher card rewards

#### `cards/cards_colorless.json` ({len(card_splits['colorless'])} cards)
**Load when:**
- Asking about colorless cards
- Evaluating colorless rewards
- Explaining curses/statuses

---

### Relics (6 files, {total_relics} total relics)

"""
    
    # Add relic sections dynamically
    relic_order = ['starter', 'common', 'uncommon', 'rare', 'boss', 'shop']
    for pool in relic_order:
        if pool in relic_splits and relic_splits[pool]:
            count = len(relic_splits[pool])
            md_content += f"""#### `relics/relics_{pool}.json` ({count} relics)
**Load when:**
- Evaluating {pool} relic rewards
- Asking about {pool} relics

"""
    
    md_content += """---

### Enemies (9 files, 37 total enemies)

#### Act 1 Enemies

**`enemies/enemies_act1_monsters.json` (9 monsters)**
**Load when:**
- Player in Act 1
- Asking about Act 1 hallway fights
- Planning Act 1 normal encounters

**`enemies/enemies_act1_elites.json` (3 elites)**
**Load when:**
- Player in Act 1
- Asking about Act 1 elites (Gremlin Nob, Lagavulin, Sentries)
- Planning elite fights

**`enemies/enemies_act1_bosses.json` (3 bosses)**
**Load when:**
- Planning boss fight in Act 1
- Asking about Act 1 bosses (Slime Boss, Guardian, Hexaghost)

#### Act 2 Enemies

**`enemies/enemies_act2_monsters.json` (4 monsters)**
**Load when:**
- Player in Act 2
- Asking about Act 2 hallway fights
- Planning Act 2 normal encounters

**`enemies/enemies_act2_elites.json` (3 elites)**
**Load when:**
- Player in Act 2
- Asking about Act 2 elites (Gremlin Leader, Book of Stabbing, Slavers)
- Planning elite fights

**`enemies/enemies_act2_bosses.json` (3 bosses)**
**Load when:**
- Planning boss fight in Act 2
- Asking about Act 2 bosses (The Champ, Collector, Bronze Automaton)

#### Act 3 Enemies

**`enemies/enemies_act3_monsters.json` (5 monsters)**
**Load when:**
- Player in Act 3
- Asking about Act 3 hallway fights
- Planning Act 3 normal encounters

**`enemies/enemies_act3_elites.json` (3 elites)**
**Load when:**
- Player in Act 3
- Asking about Act 3 elites (Giant Head, Nemesis, Reptomancer)
- Planning elite fights

**`enemies/enemies_act3_bosses.json` (4 bosses)**
**Load when:**
- Planning boss fight in Act 3 or Act 4
- Asking about Act 3/4 bosses (Awakened One, Time Eater, Donu & Deca, Corrupt Heart)

---

### Other Knowledge Files

#### `potions.json` ({len(potions)} potions)
**Load when:**
- Asking about potions
- Evaluating potion rewards

#### `keywords.json` ({len(keywords)} keywords)
**Load when:**
- Explaining mechanics
- Clarifying keywords
- Understanding game terminology

#### `archetypes.json` ({sum(len(v) for v in archetypes.values())} archetypes)
**Load when:**
- Suggesting deck direction
- Identifying build type
- Planning long-term strategy

"""
    
    if ascension_mods:
        md_content += f"""#### `ascension_modifiers.json` ({len(ascension_mods)} modifiers)
**Load when:**
- Checking ascension effects
- Understanding difficulty changes
- Planning for high ascension

"""
    
    md_content += f"""---

## 💡 Best Practices for LLM Context Management

1. **Always read this file first** to understand available knowledge
2. **Load character-specific cards immediately** when character is known
3. **Load act-specific enemies** when act/floor is known
4. **Load relics on-demand** only when evaluating specific choices
5. **Keep context small** - only load what's needed for current query
6. **Use `_meta` fields** in each JSON file for loading guidance

---

## 📊 Total Knowledge Base Stats

- **30 JSON files** with structured game data
- **{total_cards} cards** (split by character)
- **{total_relics} relics** (split by rarity pool)
- **37 enemies** (split by act and difficulty)
- **{len(potions)} potions**
- **{len(keywords)} keywords**
- **{sum(len(v) for v in archetypes.values())} archetypes**
"""
    
    if ascension_mods:
        md_content += f"- **{len(ascension_mods)} ascension modifiers**\n"
    
    md_content += """
All data includes comprehensive metadata (`_meta` fields) with LLM-friendly descriptions and usage notes.
"""
    
    # Save markdown file
    map_file = KNOWLEDGE_DIR / "KNOWLEDGE_MAP.md"
    with open(map_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ Created {map_file.name}")
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    print(f"\nKnowledge base created in: {KNOWLEDGE_DIR}")
    print(f"Total files created: {sum(1 for _ in KNOWLEDGE_DIR.rglob('*.json'))}")
    print("\nNext steps:")
    print("1. Review generated files")
    print("2. Update GroqAdvisor to load from data/knowledge/")
    print("3. Delete database after verification")

if __name__ == "__main__":
    main()
