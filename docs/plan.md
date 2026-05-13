# Slay the Spire Advisor - Development Plan

## Project Overview

Building an intelligent game advisor for Slay the Spire that:
1. Maintains a comprehensive knowledge database of all game data
2. Uses LLM intelligence to provide strategic advice
3. Eventually supports voice interaction for real-time guidance during runs

## Architecture Decisions

### Phase 1: Knowledge Database (Current)
- **Database**: SQLite (local, no server needed, game data is static)
- **Data Source**: Direct JSON download from GitHub (no Docker/API required)
  - URL: `https://raw.githubusercontent.com/jhcheung/slay-the-spire-api/master/db/items.json`
- **ORM**: SQLAlchemy for database operations

### Phase 2: LLM Integration (Future)
- **Initial Approach**: Use online LLM (VS Code Copilot) to query database and provide advice
  - The LLM will use its general knowledge + database context to make strategic inferences
- **Later**: Migrate to local LLM (Ollama) for offline operation
- **Knowledge Enhancement**: After validating with online LLM, scrape additional strategic data from:
  - Reddit (r/slaythespire)
  - Spirelogs.com tier lists
  - Wiki strategic guides

### Phase 3: Voice Interface (Future)
- TBD based on requirements
- Likely Whisper for speech recognition
- Local TTS for responses

## Data Model

The game has no more updates, so data is static. We store:

### From API/JSON:
- **Cards**: ~400 cards (all characters + colorless + curses + status)
- **Relics**: ~180 relics
- **Keywords**: ~50 game mechanics
- **Potions**: ~40 potions
- **Creatures**: ~70 enemies/bosses

### To Be Added (Strategic Layer):
- **Tier ratings**: Card/relic power rankings
- **Synergies**: Card-card and relic-card interactions
- **Archetypes**: Deck strategies (e.g., "Poison Silent", "Strength Ironclad")
- **Tips**: Context-aware strategic advice

## Character Coverage

All 4 characters:
- **Ironclad** (Red) - Strength/Exhaust
- **Silent** (Green) - Poison/Shiv/Discard
- **Defect** (Blue) - Orbs/Focus
- **Watcher** (Purple) - Stances/Scry

## Development Roadmap

### Phase 1: Database Foundation ✅ COMPLETE
- [x] Project structure
- [x] Database models (SQLAlchemy)
- [x] API client / data fetcher
- [x] Download items.json from GitHub
- [x] Parse and populate database
- [x] Verify data integrity
- [x] Run tracking models (Run, RunCard, RunRelic, RunEvent)
- [x] Ascension modifier data (A1-A20)

### Phase 2: Query Interface ✅ COMPLETE
- [x] Create query functions for common lookups
- [x] Add card search (by name, color)
- [x] Add relic search
- [x] Add enemy/potion/keyword search
- [x] Run management functions (create, update, add cards/relics)
- [x] Event logging functions

### Phase 3: LLM Documentation ✅ COMPLETE
- [x] Create LLM context document (docs/llm_context.md)
- [x] Create system prompt (docs/system_prompt.md)
- [x] Create function schema (docs/llm_functions.json)
- [x] Create strategic reference (docs/strategic_reference.md)

### Phase 4: Strategic Enrichment
- [ ] Add tier ratings to database
- [ ] Define card synergies
- [ ] Create archetype definitions
- [ ] Add strategic tips per situation
- [ ] Scrape community resources (Reddit, Spirelogs)

### Phase 5: LLM Integration
- [ ] Create API layer for function calling
- [ ] Build context provider (deck state, relics, floor, etc.)
- [ ] Test with VS Code Copilot queries
- [ ] Evaluate response quality
- [ ] Build chat interface

### Phase 6: Local LLM Migration (Ollama)
- [ ] Set up Ollama
- [ ] Choose appropriate model (llama3, mistral, etc.)
- [ ] Implement RAG if needed for large context
- [ ] Test offline operation
- [ ] Fine-tune prompts for local model

### Phase 7: Voice Interface
- [ ] Research voice recognition options
- [ ] Implement speech-to-text (Whisper)
- [ ] Implement text-to-speech
- [ ] Create voice command parser

### Phase 8: Game Integration
- [ ] Research deck tracking methods (save file, memory, mods)
- [ ] Implement real-time state updates
- [ ] Build live advisor loop

## Data Sources

### Primary (Items.json):
```
https://raw.githubusercontent.com/jhcheung/slay-the-spire-api/master/db/items.json
```

Contains:
- `cards`: All cards with name, color, rarity, type, cost, description
- `relics`: All relics with name, tier, pool, description, flavorText
- `potions`: All potions
- `creatures`: All enemies with HP
- `keywords`: All game mechanics

### Future Strategic Sources:
- Spirelogs.com (tier lists, pick rates)
- Reddit r/slaythespire (community wisdom)
- Slay the Spire Wiki (detailed mechanics)

## Notes

- Game data is static (no more updates to Slay the Spire 1)
- Database can be fully local after initial population
- LLM should use database as context, not as sole source of strategy
- Voice interface priority is lower than core functionality
