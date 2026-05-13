# Database Schema Documentation

## Overview

The Slay the Spire knowledge database stores game data and strategic information for the advisor chatbot.

## Tables

### cards
Stores all card information from the game.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Card name (unique, indexed) |
| description | TEXT | Card effect description |
| flavor_text | TEXT | Flavor text |
| color | VARCHAR(50) | Character color (RED, GREEN, BLUE, PURPLE, COLORLESS, CURSE) |
| rarity | VARCHAR(50) | Rarity (BASIC, COMMON, UNCOMMON, RARE, CURSE, SPECIAL) |
| card_type | VARCHAR(50) | Type (ATTACK, SKILL, POWER, STATUS, CURSE) |
| cost | INTEGER | Energy cost |
| cost_upgraded | INTEGER | Energy cost when upgraded |
| damage | INTEGER | Base damage |
| damage_upgraded | INTEGER | Damage when upgraded |
| block | INTEGER | Base block |
| block_upgraded | INTEGER | Block when upgraded |
| magic_number | INTEGER | Special effect value |
| magic_number_upgraded | INTEGER | Special effect when upgraded |
| description_upgraded | TEXT | Description when upgraded |
| tier_rating | FLOAT | Strategic tier rating (1-5) |
| pick_priority | INTEGER | Card pick priority (lower = pick earlier) |
| archetype_tags | VARCHAR(500) | Comma-separated archetype tags |
| strategy_notes | TEXT | Strategic notes and tips |
| is_innate | BOOLEAN | Starts in hand |
| is_ethereal | BOOLEAN | Exhausts if not played |
| exhausts | BOOLEAN | Removes from deck when played |
| targets_all | BOOLEAN | Hits all enemies |
| image_url | VARCHAR(500) | URL to card image |
| created_at | DATETIME | Record creation timestamp |
| updated_at | DATETIME | Record update timestamp |

### relics
Stores all relic information.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Relic name (unique, indexed) |
| description | TEXT | Relic effect description |
| flavor_text | TEXT | Flavor text |
| rarity | VARCHAR(50) | Rarity (STARTER, COMMON, UNCOMMON, RARE, BOSS, SHOP, EVENT, SPECIAL) |
| pool | VARCHAR(50) | Character pool (IRONCLAD, SILENT, DEFECT, WATCHER, SHARED) |
| tier_rating | FLOAT | Strategic tier rating (1-5) |
| pick_priority | INTEGER | Pick priority |
| strategy_notes | TEXT | Strategic notes |
| synergy_tags | VARCHAR(500) | Comma-separated synergy tags |
| image_url | VARCHAR(500) | URL to relic image |
| created_at | DATETIME | Record creation timestamp |
| updated_at | DATETIME | Record update timestamp |

### keywords
Stores game keywords/mechanics.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Keyword name (unique, indexed) |
| description | TEXT | Keyword explanation |

### archetypes
Stores deck archetype definitions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Archetype name (unique, indexed) |
| character | VARCHAR(50) | Character (IRONCLAD, SILENT, DEFECT, WATCHER) |
| description | TEXT | Archetype description |
| key_cards | TEXT | Comma-separated key card names |
| key_relics | TEXT | Comma-separated key relic names |
| strategy_guide | TEXT | How to play the archetype |
| difficulty_rating | INTEGER | Difficulty to execute (1-5) |
| created_at | DATETIME | Record creation timestamp |

### strategic_tips
Stores general strategic advice.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| category | VARCHAR(50) | Tip category (indexed) |
| context | VARCHAR(200) | Situational context |
| tip | TEXT | The advice |
| priority | INTEGER | Importance/ordering |
| created_at | DATETIME | Record creation timestamp |

### enemies
Stores enemy/creature information.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Enemy name (indexed) |
| enemy_type | VARCHAR(50) | Type (NORMAL, ELITE, BOSS, MINION) |
| base_hp_min | INTEGER | Minimum base HP |
| base_hp_max | INTEGER | Maximum base HP |
| act | INTEGER | Act where enemy appears (1, 2, 3, or NULL) |
| move_pattern | TEXT | JSON description of moves |
| abilities | TEXT | JSON list of abilities |
| strategy_notes | TEXT | How to fight them |
| danger_rating | INTEGER | Danger level 1-5 |
| created_at | DATETIME | Record creation timestamp |

### potions
Stores potion information.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Potion name (unique, indexed) |
| rarity | VARCHAR(50) | Rarity (COMMON, UNCOMMON, RARE) |
| description | TEXT | Potion effect |
| tier_rating | FLOAT | Strategic rating |
| strategy_notes | TEXT | When to use |
| created_at | DATETIME | Record creation timestamp |

### ascension_modifiers
Stores ascension level difficulty modifiers.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| ascension_level | INTEGER | Level 1-20 (unique, indexed) |
| description | TEXT | Human-readable description |
| enemy_hp_percent | FLOAT | Enemy HP multiplier |
| enemy_damage_percent | FLOAT | Enemy damage multiplier |
| elite_hp_percent | FLOAT | Elite HP multiplier |
| boss_hp_percent | FLOAT | Boss HP multiplier |
| starting_hp_modifier | INTEGER | Starting HP change (e.g., -10) |
| starting_gold | INTEGER | Starting gold amount |
| rest_heal_percent | FLOAT | Rest site heal percentage |
| has_ascenders_bane | BOOLEAN | Starts with curse |
| unfavorable_events | BOOLEAN | Events have worse outcomes |
| double_boss | BOOLEAN | Double boss in Act 3 |

---

## Run Tracking Tables

### runs
Tracks individual runs through the Spire.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(100) | External identifier (unique, indexed) |
| character | VARCHAR(50) | Character name (indexed) |
| ascension_level | INTEGER | Ascension 0-20 |
| current_act | INTEGER | Current act (1-4) |
| current_floor | INTEGER | Current floor (0-57) |
| current_hp | INTEGER | Current HP |
| max_hp | INTEGER | Maximum HP |
| gold | INTEGER | Current gold |
| potion_slots | INTEGER | Number of potion slots |
| potions | TEXT | JSON list of held potions |
| status | VARCHAR(50) | IN_PROGRESS, VICTORY, DEFEAT, ABANDONED |
| has_ruby_key | BOOLEAN | Red key collected |
| has_emerald_key | BOOLEAN | Green key collected |
| has_sapphire_key | BOOLEAN | Blue key collected |
| cards_played | INTEGER | Total cards played |
| damage_dealt | INTEGER | Total damage dealt |
| damage_taken | INTEGER | Total damage taken |
| gold_earned | INTEGER | Total gold earned |
| gold_spent | INTEGER | Total gold spent |
| final_floor | INTEGER | Floor where run ended |
| victory | BOOLEAN | Win/loss |
| killed_by | VARCHAR(100) | Enemy that killed player |
| started_at | DATETIME | Run start timestamp |
| updated_at | DATETIME | Last update timestamp |
| ended_at | DATETIME | Run end timestamp |

### run_cards
Tracks cards in a run's deck.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | INTEGER | Foreign key to runs (indexed) |
| card_id | INTEGER | Foreign key to cards |
| card_name | VARCHAR(100) | Card name (denormalized) |
| is_upgraded | BOOLEAN | Whether card is upgraded |
| upgrade_count | INTEGER | For Searing Blow |
| obtained_floor | INTEGER | Floor when obtained |
| obtained_from | VARCHAR(100) | Source (combat_reward, shop, etc.) |
| times_played | INTEGER | Usage count |
| added_at | DATETIME | When added to deck |

### run_relics
Tracks relics collected in a run.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | INTEGER | Foreign key to runs (indexed) |
| relic_id | INTEGER | Foreign key to relics |
| relic_name | VARCHAR(100) | Relic name (denormalized) |
| obtained_floor | INTEGER | Floor when obtained |
| obtained_from | VARCHAR(100) | Source (boss, elite, shop, etc.) |
| counter | INTEGER | For relics that track usage |
| enabled | BOOLEAN | Some relics can be disabled |
| added_at | DATETIME | When collected |

### run_events
Tracks events and decisions during a run.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | INTEGER | Foreign key to runs (indexed) |
| floor | INTEGER | Floor number |
| event_type | VARCHAR(50) | Type (COMBAT, ELITE, BOSS, SHOP, etc.) |
| event_name | VARCHAR(200) | Enemy or event name |
| details | TEXT | JSON additional details |
| hp_before | INTEGER | HP before event |
| hp_after | INTEGER | HP after event |
| gold_before | INTEGER | Gold before event |
| gold_after | INTEGER | Gold after event |
| decision | VARCHAR(200) | Choice made |
| alternatives | TEXT | JSON of other options |
| damage_dealt | INTEGER | Combat damage dealt |
| damage_taken | INTEGER | Combat damage taken |
| turns_taken | INTEGER | Combat turns |
| timestamp | DATETIME | When event occurred |

### map_nodes
Tracks map layout for a run (optional).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | INTEGER | Foreign key to runs (indexed) |
| floor | INTEGER | Floor number |
| x_position | INTEGER | Column position |
| node_type | VARCHAR(50) | MONSTER, ELITE, REST, SHOP, etc. |
| visited | BOOLEAN | Whether node was visited |
| connections | TEXT | JSON list of connected nodes |

## Association Tables

### card_keywords
Links cards to their keywords.

| Column | Type | Description |
|--------|------|-------------|
| card_id | INTEGER | Foreign key to cards |
| keyword_id | INTEGER | Foreign key to keywords |

### card_synergies
Links cards that synergize with each other.

| Column | Type | Description |
|--------|------|-------------|
| card_id | INTEGER | Foreign key to cards |
| synergy_card_id | INTEGER | Foreign key to cards |

### relic_card_synergies
Links relics to cards they synergize with.

| Column | Type | Description |
|--------|------|-------------|
| relic_id | INTEGER | Foreign key to relics |
| card_id | INTEGER | Foreign key to cards |

## Character Colors

- **RED**: Ironclad
- **GREEN**: Silent
- **BLUE**: Defect
- **PURPLE**: Watcher
- **COLORLESS**: Available to all characters
- **CURSE**: Curse cards (negative)
