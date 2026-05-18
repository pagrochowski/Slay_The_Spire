# AI Agent Guide - Slay the Spire Run Status Recorder

**Last Updated:** 2026-05-16  
**Project Status:** ✅ Fully Operational  
**Purpose:** Voice-controlled run state tracker that records Slay the Spire gameplay for external advisor consultation

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Current Status](#current-status)
3. [Architecture](#architecture)
4. [File Structure](#file-structure)
5. [Knowledge Base](#knowledge-base)
6. [Key Components](#key-components)
7. [Data Flow](#data-flow)
8. [How to Extend](#how-to-extend)
9. [Future Tasks](#future-tasks)
10. [Design Decisions](#design-decisions)

---

## 🎯 Project Overview

### What It Does
A voice-controlled state recorder that:
- Listens to player commands via push-to-talk (SPACE bar)
- Transcribes speech using Groq Whisper-large-v3
- Parses intent with 4-tier LLM fallback (llama-3.1-8b-instant → openai/gpt-oss-20b → llama-3.3-70b-versatile → openai/gpt-oss-120b)
- Tracks run state (deck, relics, HP, gold, etc.)
- Records decision points for external advisor
- Speaks confirmations using Edge TTS (en-US-AriaNeural)
- Maintains persistent state in `data/runs.json`
- Generates markdown summaries for external consultation

### Why It Exists
Slay the Spire requires complex strategic decisions. This tool:
- **Records** all run state changes via voice
- **Tracks** current decision points (card choices, relic options, shop items)
- **Exports** clean summaries for external advisors (human or AI)
- **No built-in advice** - user consults external experts for strategy

This separation allows flexible advisor choices while maintaining seamless state tracking.

### Tech Stack
- **Python 3.13** with venv
- **Groq API** for LLM inference (4-tier fallback for reliability)
- **Whisper-large-v3** for speech-to-text
- **Edge TTS** for voice confirmations
- **JSON files** for persistent storage
- **loguru** for logging

---

## ✅ Current Status

### What Works
- ✅ Voice interface with push-to-talk
- ✅ 4-tier LLM fallback (prevents rate limit failures)
- ✅ Run state persistence and resume
- ✅ Decision point tracking (card choices, relic options)
- ✅ Auto-summary generation in markdown
- ✅ Card/relic name normalization from speech
- ✅ HP/gold/act tracking
- ✅ Knowledge base for lookups (365 cards, 178 relics)

### Recent Changes (2026-05-16)
- **Complete pivot from advisor to recorder**:
  - Removed all strategy generation code
  - Removed RAG system and archetype detection
  - Created new `StatusRecorder` class (replaces `GroqAdvisor`)
  - Simplified `RunManager` (removed floor, events, strategy fields)
- **4-tier LLM fallback**:
  - Tier 1: llama-3.1-8b-instant (smallest, fastest)
  - Tier 2: openai/gpt-oss-20b (medium)
  - Tier 3: llama-3.3-70b-versatile (large)
  - Tier 4: openai/gpt-oss-120b (largest, last resort)
  - Automatically escalates on rate limits/errors
- **Decision point tracking**:
  - `set_card_choice(options)` - records card reward choices
  - `set_relic_choice(options)` - records relic choices
  - `set_shop_choices(cards, relics, potions)` - records shop inventory
  - `clear_choice()` - removes current decision after choosing
- **New summary format**:
  - Includes "Current Decision" section
  - Shows pending choices for external advisor review
  - Simple state snapshot (no strategy commentary)

---

## 🏗️ Architecture

### High-Level Flow

```
Player speaks → Whisper STT → Intent Parser → StatusRecorder → Edge TTS → Player hears
                                      ↓
                                 Run Manager
                                      ↓
                              data/runs.json (persistence)
                                      ↓
                              Knowledge Base (JSON - for lookups only)
```

### Component Layers

```
┌─────────────────────────────────────────────┐
│  scripts/voice_recorder.py (entry point)    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Voice Interface (STT/TTS)                  │
│  - Push-to-talk with SPACE                  │
│  - Whisper-large-v3 speech-to-text         │
│  - Edge TTS confirmations                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Command Parser (Intent Classification)     │
│  - 4-tier LLM fallback                      │
│  - Tier 1: llama-3.1-8b-instant (fastest)  │
│  - Tier 2: openai/gpt-oss-20b              │
│  - Tier 3: llama-3.3-70b-versatile         │
│  - Tier 4: openai/gpt-oss-120b (last resort)│
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  StatusRecorder (State Tracking)            │
│  - No strategic advice                      │
│  - Simple state updates                     │
│  - Decision point tracking                  │
│  - Summary generation for external advisor  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Run Manager (State Persistence)            │
│  - Tracks deck, relics, HP, gold, act      │
│  - Current decision point                   │
│  - Auto-saves to runs.json                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Knowledge Base (30 JSON files)             │
│  - Used only for card/relic normalization  │
│  - No RAG system                            │
│  - Simple lookups                           │
└─────────────────────────────────────────────┘
```

---

## 📁 File Structure

### Root Directory

```
Slay_The_Spire/
├── README.md                    # Main project documentation
├── AI_GUIDE.md                  # This file (AI agent reference)
├── REFACTORING_PLAN.md          # Advisor → Recorder transition plan
├── requirements.txt             # Python dependencies
├── .env                         # API keys (GROQ_API_KEY)
├── .gitignore                   # Git ignore patterns
├── run_summary_*.md             # Generated run summaries (for external advisor)
│
├── data/                        # All data files
│   ├── knowledge/               # ⭐ Knowledge base (30 JSON files)
│   ├── raw/                     # Source data (cards, relics, bosses)
│   └── runs.json                # Active run persistence
│
├── docs/                        # Documentation
│   ├── README.md                # Documentation index
│   └── strategic_reference.md   # Expert tier lists & strategies
│
├── scripts/                     # Utility scripts
│   ├── voice_recorder.py        # ⭐ Main entry point (NEW)
│   ├── voice_advisor.py         # ⚠️ OLD - uses GroqAdvisor (deprecated)
│   ├── verify_knowledge.py      # Integrity checker
│   ├── migrate_to_knowledge.py  # DB→JSON migration
│   ├── create_enemy_knowledge.py # Enemy data generator
│   ├── download_data.py         # Fetch raw data
│   └── test_kb.py               # Quick knowledge base test
│
├── src/                         # Source code
│   ├── advisor/                 # State tracking
│   │   ├── status_recorder.py   # ⭐ Main recorder (NEW)
│   │   ├── command_parser.py    # Intent classification (4-tier fallback)
│   │   ├── run_manager.py       # Run state management (simplified)
│   │   ├── groq_advisor.py      # ⚠️ OLD - strategic advisor (deprecated)
│   │   └── __init__.py
│   ├── voice/                   # Voice interface
│   │   ├── voice_interface.py   # STT/TTS
│   │   └── __init__.py
│   ├── utils/                   # Utilities
│   │   ├── logger.py            # Logging setup
│   │   └── __init__.py
│   └── __init__.py
│
└── venv/                        # Python virtual environment
```

### Important: What's REMOVED (no longer exists)

Deleted after SQLite → JSON migration:
- ❌ `src/database/` - SQLite models & manager
- ❌ `src/api/` - API client
- ❌ `scripts/populate_db.py`, `verify_db.py`, `chat.py`, etc.
- ❌ `db/sts_knowledge.db` - SQLite database

### Important: What's DEPRECATED (still exists but not used)

- ⚠️ `scripts/voice_advisor.py` - Uses GroqAdvisor (old strategic advisor)
- ⚠️ `src/advisor/groq_advisor.py` - Old advisor with strategy generation
- ⚠️ `src/advisor/run_manager_old.py` - Backup of old run manager

**Use `scripts/voice_recorder.py` instead** (new status recorder)

---

## 📚 Knowledge Base

### Organization

**Master Index:** [`data/knowledge/KNOWLEDGE_MAP.md`](data/knowledge/KNOWLEDGE_MAP.md)

**Purpose:** Reference documentation for:
- What data exists
- File organization
- Data structure

**Usage:** StatusRecorder loads knowledge base for:
- Card name normalization from speech
- Relic name normalization
- Basic lookups
- **NOT for strategy or advice**

### File Split Strategy

```
data/knowledge/
├── KNOWLEDGE_MAP.md          # Master index
├── README.md                 # Developer guide
│
├── cards/                    # Split by CHARACTER
│   ├── cards_ironclad.json   # 76 red cards
│   ├── cards_silent.json     # 73 green cards
│   ├── cards_defect.json     # 73 blue cards
│   ├── cards_watcher.json    # 73 purple cards
│   └── cards_colorless.json  # 70 colorless/curse/status
│
├── relics/                   # Split by RARITY POOL
│   ├── relics_starter.json   # 4 starter relics
│   ├── relics_common.json    # 54 common relics
│   ├── relics_uncommon.json  # 36 uncommon relics
│   ├── relics_rare.json      # 34 rare relics
│   ├── relics_boss.json      # 30 boss relics
│   └── relics_shop.json      # 20 shop-only relics
│
├── enemies/                  # Split by ACT × DIFFICULTY
│   ├── enemies_act1_monsters.json  # 9 normal enemies
│   ├── enemies_act1_elites.json    # 3 elite enemies
│   ├── enemies_act1_bosses.json    # 3 bosses
│   ├── enemies_act2_monsters.json  # 4 normal enemies
│   ├── enemies_act2_elites.json    # 3 elite enemies
│   ├── enemies_act2_bosses.json    # 3 bosses
│   ├── enemies_act3_monsters.json  # 5 normal enemies
│   ├── enemies_act3_elites.json    # 3 elite enemies
│   └── enemies_act3_bosses.json    # 4 bosses (includes Heart)
│
├── potions.json              # 42 potions
├── keywords.json             # 52 game mechanics
├── archetypes.json           # 25 deck archetypes
└── ascension_modifiers.json  # 20 ascension levels
```

### Why This Split?

**Context-Aware Loading:** LLM only loads what's needed:
- Playing Ironclad? Load `cards_ironclad.json` only (not all 365 cards)
- In Act 2? Load `enemies_act2_*.json` only (not all acts)
- Choosing rare relic? Load `relics_rare.json` only (not all pools)

**Benefits:**
- ✅ Small LLM context windows
- ✅ Fast lookups
- ✅ Efficient token usage
- ✅ Easy to extend (just add more files)

### JSON File Structure

All data files follow this pattern:

```json
{
  "_meta": {
    "description": "Human-readable description",
    "usage": "When to load this file",
    "count": 123,
    "last_updated": "2026-05-14"
  },
  "cards": [...]  // or "relics", "enemies", etc.
}
```

The `_meta` field provides LLM-friendly guidance but is NOT used by Python code.

### How Python Loads Knowledge

**File:** `src/advisor/groq_advisor.py` → `KnowledgeBase` class

```python
class KnowledgeBase:
    def __init__(self):
        self.cards = {}      # Loaded from cards/*.json
        self.relics = {}     # Loaded from relics/*.json
        self.potions = {}    # Loaded from potions.json
        self.archetypes = {} # Loaded from archetypes.json
        self.bosses = {}     # Loaded from raw/bosses.json
        self._load_data()    # Reads all JSON files on init
```

**Loading Process:**
1. Glob pattern matching: `data/knowledge/cards/*.json`
2. Parse JSON and extract data field (skip `_meta`)
3. Store in dictionaries keyed by lowercase name
4. Fuzzy matching for lookups: `find_cards("bash")` → Bash card

**Important:** Python never reads `KNOWLEDGE_MAP.md` - it's purely documentation!

---

## 🔧 Key Components

### 1. Voice Interface (`src/voice/voice_interface.py`)

**Purpose:** Handle speech-to-text and text-to-speech

**Key Methods:**
- `listen()` - Record audio until SPACE released
- `transcribe()` - Groq Whisper API for STT
- `speak()` - Edge TTS for natural voice
- Dual model fallback for STT reliability

**Push-to-Talk:**
- Hold SPACE to record
- Release to process
- Visual feedback in terminal

### 2. Command Parser (`src/advisor/command_parser.py`)

**Purpose:** Classify user intent from transcribed text

**Model:** `llama-3.1-8b-instant` (fast classification)

**21 Intent Types:**
```python
start_run, card_choice, add_card, remove_card, upgrade_card,
relic_choice, add_relic, set_boss, update_floor, update_hp,
update_gold, adjust_strategy, general_question, deck_status,
relic_status, run_status, end_run, get_help, confirm_yes,
confirm_no, unknown
```

**Output:** JSON only (enforced by `response_format`)

```json
{
  "intent": "card_choice",
  "parameters": {
    "options": ["Strike", "Bash", "Defend"],
    "context": "Need AoE damage"
  }
}
```

**Modifiers:** Handles "basic Strike" vs "Swift Strike", "upgrade Bash" vs "Bash+"

### 3. GroqAdvisor (`src/advisor/groq_advisor.py`)

**Purpose:** Main strategic intelligence with RAG system

**Components:**
- `KnowledgeBase` class - Loads and searches JSON data
- `GroqAdvisor` class - LLM interaction + run management
- RAG system - Injects relevant card/relic info into context

**Models:**
- Primary: `openai/gpt-oss-120b` (best quality)
- Fallback: `llama-3.3-70b-versatile` (backup)
- Auto-retry on rate limits

**Key Features:**

**RAG System:**
```python
# Extract mentioned items from user query
mentioned = kb.extract_mentioned_items(query)

# Inject card info into context
for card_name in mentioned["cards"]:
    info = kb.get_card_info(card_name)
    context += f"[CARD INFO] {info}\n"
```

**Auto-Strategy Updates:**
When boss is set, generates 4-section strategy:
1. Boss mechanics and move patterns
2. Long-term deck goals
3. Short-term problems to solve
4. Card priorities for rewards

**Automatic Updates:**
Strategy automatically regenerates (silently) when:
- Card added to deck (`add_card()`)
- Card removed from deck (`remove_card()`)
- Relic added (`add_relic()`)
- Boss set (`set_boss()`)
- Act changes (`update_floor()` with new act)

**Output:**
- Full strategy written to `run_summary_{character}_A{ascension}.md`
- Brief one-sentence summary spoken aloud
- Example: "Strategy updated. Focus on frontloaded damage for the Automaton."

**Archetype Detection:**
Scans deck for archetype indicators:
```python
# Example: Perfected Strike archetype
indicators = ["perfected strike", "pommel strike", "twin strike"]
if any(card in deck for card in indicators):
    score += weight
```

**System Prompt:** Teaches LLM to:
- Trust run state (never invent data)
- Prioritize immediate problems over archetypes
- Recommend SKIP when appropriate
- Be concise (responses are spoken aloud)
- Update strategy when detecting shifts

### 4. Run Manager (`src/advisor/run_manager.py`)

**Purpose:** Persistent run state management

**Storage:** `data/runs.json` (max 5 recent runs)

**Run Structure:**
```json
{
  "run_id": "ironclad_1_1736879345",
  "character": "Ironclad",
  "ascension": 1,
  "act": 2,
  "floor": 17,
  "hp": 82,
  "max_hp": 88,
  "gold": 217,
  "deck": ["Strike", "Strike", ...],
  "relics": ["Burning Blood", "Red Skull", ...],
  "potions": [],
  "boss": "Bronze Automaton",
  "strategy_notes": [...],
  "events": [...],
  "created_at": "2026-05-14T12:34:56"
}
```

**Key Methods:**
- `start_run()` - Initialize new run
- `resume_latest_run()` - Auto-resume on startup
- `add_card()` / `remove_card()` - Deck management
- `add_relic()` - Relic tracking
- `set_boss()` - Triggers strategy generation
- `end_run()` - Generate summary markdown

**Event Logging:**
```python
{
  "timestamp": "2026-05-14T12:35:00",
  "type": "card_added",
  "data": {"card": "Perfected Strike"}
}
```

**Auto-Summary:**
Generates `run_summary_{character}_A{ascension}.md` with:
- Final deck composition
- Relics collected
- Strategy notes
- Event timeline
- Archetype tendencies

---

## 🔄 Data Flow

### Typical Interaction Flow

```
1. USER: Hold SPACE, say "I picked Bash"
   ↓
2. VoiceInterface.listen() → Records audio
   ↓
3. VoiceInterface.transcribe() → Groq Whisper API
   Result: "I picked Bash"
   ↓
4. CommandParser.parse() → 4-tier LLM fallback
   Tries: llama-3.1-8b-instant → openai/gpt-oss-20b → llama-3.3-70b-versatile → openai/gpt-oss-120b
   Result: {"intent": "add_card", "cards": ["Bash"], "original_query": "I picked Bash"}
   ↓
5. StatusRecorder.add_card("Bash")
   - Updates deck in run state
   - Saves to data/runs.json
   - Updates summary file (run_summary_Ironclad_A1.md)
   ↓
6. VoiceInterface.speak() → Edge TTS
   Player hears: "Added Bash. Deck now has 11 cards."
   ↓
7. Summary file updated with current deck state + any pending decision
```

### 4-Tier LLM Fallback

```
CommandParser.parse(text)
  ↓
Try Tier 1: llama-3.1-8b-instant (smallest, fastest)
  ↓
  Error/Rate Limit? → Try Tier 2: openai/gpt-oss-20b
    ↓
    Error/Rate Limit? → Try Tier 3: llama-3.3-70b-versatile
      ↓
      Error/Rate Limit? → Try Tier 4: openai/gpt-oss-120b (last resort)
        ↓
        All failed? → Return {"intent": "unknown", "error": "All models failed"}
```

### Knowledge Loading

```
StatusRecorder.__init__()
  ↓
KnowledgeBase._load_data()
  ↓
For each pattern (cards/*.json, relics/*.json, potions.json, bosses.json):
  ↓
  Glob match files
  ↓
  Load JSON
  ↓
  Extract data field (skip _meta)
  ↓
  Store in self.cards / self.relics / etc.
  
Result: In-memory dictionaries for name normalization
```

### Run Persistence

```
Any state change (add card, update HP, etc.)
  ↓
StatusRecorder.add_card() / update_hp() / etc.
  ↓
RunManager updates in-memory run dict
  ↓
_save() → Write to data/runs.json
  ↓
create_summary_file() → Write markdown summary
  ↓
Keep only 5 most recent runs in runs.json
```

---

## 🎮 Available Commands

### Run Management
- **"Start a new run with Ironclad ascension 10"** → `start_run()`
- **"End run, I died"** → `end_run(victory=False)`
- **"End run, I won"** → `end_run(victory=True)`
- **"What's my status?"** → `get_run_status()`
- **"Create summary"** → `create_summary_file()`

### Deck Tracking
- **"I picked Bash"** → `add_card("Bash")`
- **"Added Bash to my deck"** → `add_card("Bash")`
- **"I removed a Strike"** → `remove_card("Strike")`

### Relic Tracking
- **"I got Anchor"** → `add_relic("Anchor")`
- **"Added Snecko Eye"** → `add_relic("Snecko Eye")`

### Boss & Act
- **"Boss is Hexaghost"** → `set_boss("Hexaghost")`
- **"Entering Act 2"** → `update_act(2)`

### HP & Gold
- **"HP is 45"** → `update_hp(current=45)`
- **"Max HP is 85"** → `update_hp(max_hp=85)`
- **"Took 10 damage"** → `update_hp(hp_delta=-10)`
- **"Gained 8 max HP"** → `update_hp(max_hp_delta=8)`
- **"Gold is 150"** → `update_gold(150)`
- **"Spent 50 gold"** → `update_gold(gold_delta=-50)`

### Decision Point Tracking (for external advisor)
- **"Card options are Strike, Bash, Defend"** → `set_card_choice(["Strike", "Bash", "Defend"])`
- **"Relic options are Anchor and Lantern"** → `set_relic_choice(["Anchor", "Lantern"])`

**Note:** Decision tracking does NOT provide advice. It only records choices for external advisor consultation.

---

## 🚀 How to Extend

### Adding New Intent Types

1. **Update CommandParser system prompt** (`src/advisor/command_parser.py`):
```python
SYSTEM_PROMPT = """...(existing prompt)...

NEW INTENTS:
- potion_choice: User presenting potion options
  Example: {"intent": "potion_choice", "potions": ["Fire Potion", "Block Potion"]}
"""
```

2. **Add Handler in StatusRecorder** (`src/advisor/status_recorder.py`):
```python
def set_potion_choice(self, options: List[str]) -> str:
    """Record potion choice for external advisor."""
    self.run_manager.set_potion_choice(options)
    self.create_summary_file(silent=True)
    return f"Potion choice recorded: {', '.join(options)}"
```

3. **Add to RunManager** (`src/advisor/run_manager.py`):
```python
def set_potion_choice(self, options: List[str]):
    """Set current potion choice."""
    self.current_choice = {
        "type": "potion",
        "options": options
    }
    self._save()
```

4. **Route in Main Loop** (`scripts/voice_recorder.py`):
```python
elif result["intent"] == "potion_choice":
    response = advisor.handle_potion_choice(result["parameters"]["options"])
```

### Adding New Knowledge Files

1. **Create JSON file** in `data/knowledge/`:
```json
{
  "_meta": {
    "description": "Event outcomes and choices",
    "usage": "Load when: asking about events, evaluating event choices",
    "count": 50
  },
  "events": [
    {
      "name": "Golden Shrine",
      "description": "Gain gold, lose max HP",
      "choices": [...]
    }
  ]
}
```

2. **Load in KnowledgeBase** (`src/advisor/groq_advisor.py`):
```python
def _load_data(self):
    # ... existing loads
    
    # Load events
    events_file = self.data_dir / "events.json"
    if events_file.exists():
        with open(events_file, encoding='utf-8') as f:
            data = json.load(f)
            for event in data.get("events", []):
                name = event.get("name", "").lower()
                if name:
                    self.events[name] = event
```

3. **Update KNOWLEDGE_MAP.md**:
Run `python scripts/migrate_to_knowledge.py` or manually update

### Adding Data Sources (Podcasts, Web Scrapes, etc.)

**Pattern:**
1. Scrape/download raw data → `data/raw/podcast_transcripts/`
2. Process into structured JSON → `data/knowledge/podcast_insights.json`
3. Load in KnowledgeBase similar to existing files
4. Update KNOWLEDGE_MAP.md with new file
5. Run `python scripts/verify_knowledge.py` to ensure integrity

**Example: Podcast Transcripts**
```json
{
  "_meta": {
    "description": "Expert strategy insights from podcasts",
    "usage": "Load when: asking for advanced strategy, specific archetype advice",
    "count": 25,
    "source": "Jorbs YouTube transcripts"
  },
  "insights": [
    {
      "topic": "Corruption strategies",
      "character": "Ironclad",
      "key_points": [
        "Corruption needs exhaust synergies like Feel No Pain",
        "Dead Branch makes it broken"
      ],
      "source": "Jorbs Overexplained Run #47"
    }
  ]
}
```

---

## 📝 Future Tasks

### High Priority
- [ ] Screen capture integration (auto-detect cards/relics from game window)
- [ ] Real-time deck overlay (shows deck composition on screen)
- [ ] Potion tracking and usage suggestions
- [ ] Event decision database and advice

### Medium Priority
- [ ] Historical run analytics (win rate by character, ascension)
- [ ] Win rate predictions based on deck state
- [ ] Elite/boss fight timers and combat advice
- [ ] Relic synergy suggestions (e.g., "Dead Branch + Corruption combo")

### Low Priority
- [ ] Export runs to CSV for analysis
- [ ] Integration with Slay the Spire mod API (if available)
- [ ] Multi-language support
- [ ] Web dashboard for run statistics

### Knowledge Expansion
- [ ] Add podcast transcripts (Jorbs, Baalorlord, etc.)
- [ ] Scrape wiki for advanced strategies
- [ ] Add expert player tier lists
- [ ] Compile common mistakes database
- [ ] Create counter-play guide (e.g., how to beat Gremlin Nob with each character)

### Code Quality
- [ ] Add unit tests for core components
- [ ] Add integration tests for full workflows
- [ ] Performance profiling (knowledge loading, LLM calls)
- [ ] Error recovery improvements (graceful degradation)

---

## 💡 Design Decisions

### Why JSON Instead of Database?

**Rationale:**
- ✅ Simple: No ORM, no migrations, no database server
- ✅ Portable: Works anywhere Python runs
- ✅ Version Control: JSON diffs in git are readable
- ✅ Fast: In-memory dictionaries after initial load
- ✅ LLM-Friendly: Easy to inject into prompts
- ✅ **Single Source of Truth**: All data from `data/knowledge/` and `data/raw/bosses.json`
- ❌ SQLite was overkill for read-only data

**No Hardcoded Data:**
- Removed `BOSSES = {...}` dictionary (was hardcoded boss strategies)
- All boss data now from `data/raw/bosses.json` (manually curated)
- All card/relic/enemy data from `data/knowledge/*.json`
- Character starter info still in `CHARACTERS` dict (not in knowledge base)

**Trade-offs:**
- No complex queries (but we don't need them)
- Slower initial load (acceptable ~1 second)
- Higher memory usage (acceptable ~50MB)

### Why Split by Context?

**Rationale:**
- ✅ LLM context limits (avoid hitting token caps)
- ✅ Faster responses (less data to parse)
- ✅ Future-proof (can add more files without breaking existing)
- ✅ Semantic organization (matches how players think)

**Example:** Player using Ironclad doesn't need Silent cards in context.

### Why Markdown for KNOWLEDGE_MAP?

**Rationale:**
- ✅ LLMs read it for guidance (clearer than JSON)
- ✅ Developers read it for reference
- ✅ NOT in data pipeline (Python never touches it)
- ✅ Auto-generated by migration script

### Why Groq Instead of Local LLM?

**Rationale:**
- ✅ Speed: ~2s response time vs 30s+ local
- ✅ Quality: GPT-OSS-120B beats most local models
- ✅ Cost: Free tier is generous ($0 so far)
- ✅ Fallback: Dual model prevents failures
- ❌ Ollama was too slow for real-time voice

**Trade-offs:**
- Requires internet connection
- Dependent on third-party API
- Rate limits (mitigated with fallback)

### Why Edge TTS?

**Rationale:**
- ✅ Free and unlimited
- ✅ Natural voices (Microsoft's best)
- ✅ Fast synthesis (<1s)
- ✅ No API key needed
- ❌ Alternatives (ElevenLabs, Google) cost money

### Why Run State Persistence?

**Rationale:**
- ✅ Players can pause/resume
- ✅ Crash recovery
- ✅ Historical tracking
- ✅ Post-run analysis

**Implementation:** Simple JSON file (max 5 runs to keep size small)

---

## 🔍 Debugging Tips

### Common Issues

**1. "Module not found" Errors**
- Always activate venv: `.\venv\Scripts\Activate.ps1`
- Reinstall dependencies: `pip install -r requirements.txt`

**2. Groq API Errors**
- Check `.env` has `GROQ_API_KEY`
- Verify key is valid at console.groq.com
- **Rate Limit Handling:** System automatically switches between models bidirectionally
  - If primary model (gpt-oss-120b) hits rate limit → switches to fallback (llama-3.3-70b)
  - If fallback hits rate limit → switches back to primary
  - User hears: "Sorry, encountered error." (simplified, full error in logs)
- **Error Messages:** User only hears "Sorry, encountered error." - check logs for details

**3. Knowledge Base Not Loading**
- Run: `python scripts/verify_knowledge.py`
- Check file paths (should be `data/knowledge/`)
- Verify JSON is valid (use JSON validator)

**4. Voice Interface Not Working**
- Check microphone permissions
- Test with: `python -c "import pyaudio; p=pyaudio.PyAudio(); print(p.get_default_input_device_info())"`
- Edge TTS requires internet connection

### Verification Commands

```powershell
# Activate environment
.\venv\Scripts\Activate.ps1

# Test knowledge base loading
python scripts/test_kb.py

# Verify knowledge integrity
python scripts/verify_knowledge.py

# Run voice advisor
python scripts/voice_advisor.py
```

### Log Files

Logs are output to console. To save to file:
```powershell
python scripts/voice_advisor.py 2>&1 | Tee-Object -FilePath advisor.log
```

---

## 📖 Key Files Reference

### `scripts/voice_advisor.py`
**Main entry point** - Start here to understand flow

**Key sections:**
- `main()` - Initializes all components
- Command routing - Maps intents to handlers
- Main loop - Listen → Parse → Advise → Speak

### `src/advisor/groq_advisor.py`
**Strategic intelligence core**

**Key classes:**
- `KnowledgeBase` - Loads/searches JSON data
- `GroqAdvisor` - LLM interaction + RAG

**Key methods:**
- `_get_system_prompt()` - Teaches LLM how to advise
- `_build_run_context()` - Injects run state
- `_call_groq()` - API call with fallback
- `generate_boss_strategy()` - 4-section comprehensive strategy

### `src/advisor/run_manager.py`
**Run state persistence**

**Key methods:**
- `start_run()` - New run initialization
- `resume_latest_run()` - Auto-resume
- `add_card()` / `remove_card()` - Deck management
- `set_boss()` - Boss assignment + strategy trigger
- `end_run()` - Summary generation
- `_save()` - Write to JSON

### `src/voice/voice_interface.py`
**Voice I/O handling**

**Key methods:**
- `listen()` - Record with push-to-talk
- `transcribe()` - Groq Whisper STT
- `speak()` - Edge TTS output

### `scripts/verify_knowledge.py`
**Integrity checker**

**Validates:**
- JSON syntax
- Required fields
- No duplicates
- _meta fields
- File existence

### `scripts/migrate_to_knowledge.py`
**Data migration tool**

**Generates:**
- Split JSON files from raw data
- KNOWLEDGE_MAP.md with counts
- _meta fields with guidance

### `data/knowledge/KNOWLEDGE_MAP.md`
**Master index for LLM + developers**

**Contains:**
- File inventory
- When to load each file
- Loading strategies
- Total counts

---

## 🎓 Learning the Codebase

### Start Here (15 min)
1. Read `README.md` - Project overview
2. Run `python scripts/test_kb.py` - See knowledge loading
3. Browse `data/knowledge/KNOWLEDGE_MAP.md` - Understand data organization

### Deep Dive (1 hour)
1. Read `src/advisor/groq_advisor.py` - Core logic
2. Trace a command: `voice_advisor.py` → `command_parser.py` → `groq_advisor.py`
3. Check `data/runs.json` - See run state structure

### Full Understanding (3 hours)
1. Run voice advisor: `python scripts/voice_advisor.py`
2. Issue commands and watch logs
3. Review generated `run_summary_*.md` files
4. Read system prompt in `groq_advisor.py` → `_get_system_prompt()`

---

## 📌 Important Notes

### Environment Variables
```ini
# .env file (REQUIRED)
GROQ_API_KEY=your_key_here

# Optional customization
WHISPER_MODEL=whisper-large-v3
WHISPER_FALLBACK=whisper-large-v3-turbo
TTS_VOICE=en-US-AriaNeural
ADVISOR_MODEL=openai/gpt-oss-120b
ADVISOR_FALLBACK=llama-3.3-70b-versatile
PARSER_MODEL=llama-3.1-8b-instant
PARSER_FALLBACK=openai/gpt-oss-20b
```

### Data Sources
- Cards/Relics/Potions/Keywords: [Slay the Spire API](https://github.com/jhcheung/slay-the-spire-api)
- Boss Strategies: [Slay the Spire Wiki](https://slay-the-spire.fandom.com)
- Enemy Data: Manually curated from game/wiki
- Archetypes: Expert player knowledge

### Git Workflow
- Main branch: stable, working code
- Feature branches: new features
- Tag releases: `v1.0.0`, `v1.1.0`, etc.

### Dependencies
See `requirements.txt` for full list. Key ones:
- `groq` - Groq API client
- `python-dotenv` - Environment variables
- `loguru` - Logging
- `edge-tts` - Text-to-speech
- `pyaudio` - Audio recording

---

## 🚨 Critical Warnings

### DO NOT
- ❌ Commit `.env` file (contains API key)
- ❌ Delete `data/runs.json` (contains active runs)
- ❌ Modify JSON files manually (use scripts)
- ❌ Change file structure without updating loaders
- ❌ Remove `_meta` fields from JSON (used for documentation)

### ALWAYS
- ✅ Activate venv before running anything
- ✅ Run `verify_knowledge.py` after data changes
- ✅ Test with `test_kb.py` after code changes
- ✅ Update `KNOWLEDGE_MAP.md` when adding files (or run migration script)
- ✅ Keep this AI_GUIDE.md updated with major changes

---

## 📞 Contact & Resources

- **Project Repository:** (Add GitHub URL when created)
- **Groq Console:** https://console.groq.com
- **Slay the Spire Wiki:** https://slay-the-spire.fandom.com
- **Game API Docs:** https://github.com/jhcheung/slay-the-spire-api

---

**End of AI Agent Guide**

*This document is maintained by AI agents working on this project. Keep it updated as the codebase evolves.*
