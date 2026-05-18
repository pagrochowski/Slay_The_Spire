# Knowledge Base Map

**🎯 START HERE** - Master index for the Slay the Spire knowledge base

**Purpose:** Guide the LLM to load only the relevant knowledge files based on context  
**Usage:** Always consult this file first to determine which JSON files to load  
**Last Updated:** 2026-05-14

---

## 📋 Loading Strategy

### Always Load
- `KNOWLEDGE_MAP.md` (this file) - Read first to understand available knowledge

### Context-Based Loading

**By Character:**
- Load `cards/cards_{character}.json` when player character is known
- Load relevant archetypes for that character

**By Act:**
- Load `enemies/enemies_act{N}_{type}.json` when player act is known
- Load all three types: monsters, elites, bosses

**On Demand:**
- Load specific relic pools only when evaluating relic choices
- Load potions, keywords only when needed for specific queries

---

## 📁 File Inventory

### Cards (5 files, 365 total cards)

#### `cards/cards_ironclad.json` (76 cards)
**Load when:**
- Player is Ironclad
- Asking about red cards
- Evaluating Ironclad card rewards

#### `cards/cards_silent.json` (73 cards)
**Load when:**
- Player is Silent
- Asking about green cards
- Evaluating Silent card rewards

#### `cards/cards_defect.json` (73 cards)
**Load when:**
- Player is Defect
- Asking about blue cards
- Evaluating Defect card rewards

#### `cards/cards_watcher.json` (73 cards)
**Load when:**
- Player is Watcher
- Asking about purple cards
- Evaluating Watcher card rewards

#### `cards/cards_colorless.json` (70 cards)
**Load when:**
- Asking about colorless cards
- Evaluating colorless rewards
- Explaining curses/statuses

---

### Relics (6 files, 178 total relics)

#### `relics/relics_starter.json` (4 relics)
**Load when:**
- Evaluating starter relic rewards
- Asking about starter relics

#### `relics/relics_common.json` (54 relics)
**Load when:**
- Evaluating common relic rewards
- Asking about common relics

#### `relics/relics_uncommon.json` (36 relics)
**Load when:**
- Evaluating uncommon relic rewards
- Asking about uncommon relics

#### `relics/relics_rare.json` (34 relics)
**Load when:**
- Evaluating rare relic rewards
- Asking about rare relics

#### `relics/relics_boss.json` (30 relics)
**Load when:**
- Evaluating boss relic rewards
- Asking about boss relics

#### `relics/relics_shop.json` (20 relics)
**Load when:**
- Evaluating shop relic rewards
- Asking about shop relics

---

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

#### `potions.json` (42 potions)
**Load when:**
- Asking about potions
- Evaluating potion rewards

#### `keywords.json` (52 keywords)
**Load when:**
- Explaining mechanics
- Clarifying keywords
- Understanding game terminology

#### `archetypes.json` (25 archetypes)
**Load when:**
- Suggesting deck direction
- Identifying build type
- Planning long-term strategy

#### `ascension_modifiers.json` (20 modifiers)
**Load when:**
- Checking ascension effects
- Understanding difficulty changes
- Planning for high ascension

---

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
- **365 cards** (split by character)
- **178 relics** (split by rarity pool)
- **37 enemies** (split by act and difficulty)
- **42 potions**
- **52 keywords**
- **25 archetypes**
- **20 ascension modifiers**

All data includes comprehensive metadata (`_meta` fields) with LLM-friendly descriptions and usage notes.
