# Knowledge Base Directory

This directory contains the complete Slay the Spire game knowledge in structured JSON files.

## 🎯 START HERE: [KNOWLEDGE_MAP.md](KNOWLEDGE_MAP.md)

**👉 Read [KNOWLEDGE_MAP.md](KNOWLEDGE_MAP.md) first** - it's the master index that explains:
- Which files contain what data
- When to load each file (context-based loading strategy)
- File counts and organization
- Best practices for LLM context management

## Directory Structure

```
knowledge/
├── KNOWLEDGE_MAP.md          ⭐ Master index - read this first
├── cards/                    # 5 files, 365 total cards
│   ├── cards_ironclad.json
│   ├── cards_silent.json
│   ├── cards_defect.json
│   ├── cards_watcher.json
│   └── cards_colorless.json
├── relics/                   # 6 files, 178 total relics
│   ├── relics_starter.json
│   ├── relics_common.json
│   ├── relics_uncommon.json
│   ├── relics_rare.json
│   ├── relics_boss.json
│   └── relics_shop.json
├── enemies/                  # 9 files, 37 total enemies
│   ├── enemies_act1_monsters.json
│   ├── enemies_act1_elites.json
│   ├── enemies_act1_bosses.json
│   ├── enemies_act2_monsters.json
│   ├── enemies_act2_elites.json
│   ├── enemies_act2_bosses.json
│   ├── enemies_act3_monsters.json
│   ├── enemies_act3_elites.json
│   └── enemies_act3_bosses.json
├── potions.json              # 42 potions
├── keywords.json             # 52 game keywords
├── archetypes.json           # 25 deck archetypes
└── ascension_modifiers.json  # 20 ascension levels
```

## File Format

All JSON files follow this structure:

```json
{
  "_meta": {
    "description": "Human-readable description",
    "usage": "When to load this file",
    "count": 123
  },
  "cards": [...],      // or "relics", "enemies", etc.
}
```

The `_meta` field provides LLM-friendly guidance for context-aware loading.

## Usage in Code

The knowledge base is loaded by [`src/advisor/groq_advisor.py`](../../src/advisor/groq_advisor.py):

```python
from src.advisor.groq_advisor import GroqAdvisor

advisor = GroqAdvisor()
# Access knowledge base
bash_card = advisor.kb.cards.get('bash')
dead_branch = advisor.kb.relics.get('dead branch')
```

## Data Sources

- **Cards, Relics, Potions, Keywords**: [Slay the Spire API](https://github.com/jhcheung/slay-the-spire-api)
- **Enemy Data**: Manually curated with comprehensive strategies
- **Boss Strategies**: [Slay the Spire Wiki](https://slay-the-spire.fandom.com)
- **Archetypes**: Expert player knowledge

## Maintenance

To regenerate knowledge files from raw data:

```powershell
# Download latest raw data
python scripts/download_data.py

# Migrate to split JSON files
python scripts/migrate_to_knowledge.py

# Generate enemy knowledge
python scripts/create_enemy_knowledge.py
```

## Design Philosophy

**Split by Context**: Files are organized so the LLM can load only what's needed:
- Character-specific cards (only load Ironclad cards when playing Ironclad)
- Act-specific enemies (only load Act 2 enemies when in Act 2)
- Rarity-specific relics (only load rare relics when evaluating rare choices)

This keeps LLM context windows small and efficient while maintaining comprehensive coverage.


# Personal notes

potki: zwieksza sie szansa zeby dostac potka z kazda walka o okolo 10% bez potka
szansa na zlota karte zwieksza sie z kazda walka o kilka %, zaczyna sie od -2%, az do zobaczenia jej w nagrodzie, po picku zeruje sie, a jesli nie to obniza o polowe

drugi akt jest trudny, poniewaz deck jest jeszcze nie ustabilizowany, a przeciwnicy juz mocno bija
dobrze skipowac blyszczace elitki w drugim akcie

pivot point podczas wybierania sciezki na mapie: zawsze miej plan B, aby moc uciec od trudnych walk, jesli wczesniejsze zle pojda

upgrade debt: niektore karty wymagaja upgrejdu, a okazji nie ma zbyt wiele, 4-5 na gre
np: true grit, uppercut
czesciowy debt: pommel strike, demon form, blood for blood

energia jest wazna do manipulacji kartami, im mniej energii, tym mniejsze pole manewru przy wyciaganiu z discardu lub dobieraniu kart

status into discard > draw pile

relikt: orange pellets

Hexaghost: 6 tura potezny atak zawsze, niezalezny od HP
The Champ: if he gets under 50%, then burst him down after he has enraged
