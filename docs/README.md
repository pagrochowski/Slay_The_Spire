# Documentation Folder

This folder contains reference materials for the Slay the Spire Voice Advisor project.

## Contents

### strategic_reference.md

Expert-curated strategic knowledge including:
- **Card tier lists** by character (S/A/B tier rankings)
- **Boss fight strategies** for all 10 bosses (Act 1-4)
- **Relic tier rankings** and synergies
- **Strategic insights** for deck building and combat

This serves as supplementary reference material alongside the structured knowledge base in `data/knowledge/`.

## Knowledge Base Structure

The main knowledge base has been migrated to JSON files in `data/knowledge/`:

**📖 See [data/knowledge/KNOWLEDGE_MAP.md](../data/knowledge/KNOWLEDGE_MAP.md)** for the complete master index.

```
data/knowledge/
├── KNOWLEDGE_MAP.md            ⭐ Master index - read this first
├── README.md                   # Developer guide
├── cards/                      # Split by character (5 files, 365 cards)
├── relics/                     # Split by rarity pool (6 files, 178 relics)
├── enemies/                    # Split by act & difficulty (9 files, 37 enemies)
├── potions.json               # 42 potions
├── keywords.json              # 52 game mechanics
├── archetypes.json            # 25 deck archetypes
└── ascension_modifiers.json   # 20 ascension levels
```

## Source Data

Raw data files from various sources are in `data/raw/`:
- Cards, relics, potions, keywords from GitHub API
- Boss strategies from wiki HTML files
- Manual annotations and corrections

## Current System

The voice advisor uses:
- **Groq API** for LLM inference (dual model fallback)
- **Whisper-large-v3** for speech-to-text
- **Edge TTS** for text-to-speech
- **JSON knowledge base** for card/relic/enemy data
- **Run tracking** in data/runs.json

See the main README for usage instructions.
