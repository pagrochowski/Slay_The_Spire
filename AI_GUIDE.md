# AI Developer Guide - Slay the Spire Voice Recorder

**Version**: 2.0.0  
**Last Updated**: May 20, 2026  
**Purpose**: Technical handover documentation for AI developers

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Module Documentation](#module-documentation)
4. [Data Formats](#data-formats)
5. [Configuration](#configuration)
6. [Logging System](#logging-system)
7. [Workflow Details](#workflow-details)
8. [Common Operations](#common-operations)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

### Purpose
Voice-controlled assistant for **Slay the Spire** that allows players to:
- Record card/relic choices via F1 hotkey
- Automatically transcribe voice using Groq Whisper API
- Correct misspellings using LLM (4-model fallback chain)
- Update Run_Summary.md with formatted choices

### Key Features
- **Push-to-talk**: Press & hold F1 to record
- **Auto-save backup**: Creates timestamped backups, auto-cleans >24h old
- **Save parsing**: Extracts run data using spireslayer library
- **Knowledge base**: 365 cards, 178 relics, 42 potions with fuzzy matching
- **LLM correction**: 4-tier model fallback for robust name matching
- **Comprehensive logging**: Daily logs with millisecond timestamps

### Tech Stack
- **Python 3.13+**
- **Groq API**: Whisper (transcription) + LLMs (name correction)
- **Libraries**: sounddevice, keyboard, spireslayer, loguru
- **Data**: JSON knowledge base (cards, relics, potions)

---

## 🏗️ Architecture

### High-Level Flow
```
User presses F1
    ↓
Record audio (sounddevice + keyboard)
    ↓
Save to WAV file
    ↓
Transcribe with Groq Whisper API
    ↓
Correct names with LLM (4-model fallback)
    ↓
Update Run_Summary.md "Current choice:" section
    ↓
Wait for next F1 press
```

### Module Dependency Graph
```
scripts/voice_recorder.py (main)
    ├── src/core/backup_manager.py
    ├── src/core/save_parser.py
    ├── src/knowledge/knowledge_base.py
    ├── src/summary/summary_generator.py
    ├── src/summary/choice_updater.py
    ├── src/voice/voice_recorder.py
    ├── src/voice/transcriber.py
    └── src/llm/name_corrector.py
```

### Directory Structure
```
Slay_The_Spire/
├── src/                        # Source code (new clean implementation)
│   ├── core/                   # Core save file operations
│   │   ├── config.py          # Configuration management
│   │   ├── backup_manager.py  # Backup creation & cleanup
│   │   └── save_parser.py     # Save file parsing (spireslayer)
│   ├── voice/                  # Voice recording & transcription
│   │   ├── voice_recorder.py  # Audio capture with F1 hotkey
│   │   └── transcriber.py     # Groq Whisper API integration
│   ├── llm/                    # LLM integration
│   │   └── name_corrector.py  # 4-model fallback name correction
│   ├── knowledge/              # Knowledge base access
│   │   └── knowledge_base.py  # Load/query cards & relics
│   ├── summary/                # Run summary management
│   │   ├── summary_generator.py  # Generate Run_Summary.md
│   │   └── choice_updater.py     # Update choice section
│   └── utils/                  # Utilities
│       └── logger.py          # Comprehensive logging
├── scripts/                    # Executable scripts
│   ├── voice_recorder.py      # Main application
│   └── cleanup_backups.py     # Backup cleanup utility
├── tests/                      # Unit tests (pytest)
│   ├── test_backup_manager.py
│   ├── test_save_parser.py
│   ├── test_knowledge_base.py
│   ├── test_summary_generator.py
│   ├── test_choice_updater.py
│   ├── test_logger.py
│   └── test_config.py
├── data/                       # Knowledge base & backups
│   ├── knowledge/             # Game data (JSON)
│   │   ├── cards/            # 5 files (colorless + 4 classes)
│   │   ├── relics/           # 6 files (by rarity)
│   │   └── potions.json
│   ├── backups/              # Save file backups (auto-cleanup)
│   └── processed/            # Parsed JSON & temp audio
├── logs/                       # Comprehensive logs
│   └── YYYY-MM-DD/           # Daily log folders
│       ├── backup_operations.log
│       ├── save_parsing.log
│       ├── voice_recording.log
│       ├── llm_corrections.log
│       ├── summary_updates.log
│       └── errors.log
├── src_old/                    # OLD implementation (reference only)
├── scripts_old/                # OLD scripts (reference only)
├── Run_Summary.md              # Current run state (auto-updated)
├── AI_GUIDE.md                 # This file
└── .env                        # GROQ_API_KEY

```

---

## 📦 Module Documentation

### 1. `src/core/config.py`
**Purpose**: Centralized configuration management

**Key Classes**:
- `Config`: Static configuration class

**Important Attributes**:
```python
# Paths
PROJECT_ROOT: Path
GAME_SAVES_DIR: Path = "c:\\Games\\Slay.the.Spire.v2.3.4\\...\\saves"
BACKUP_DIR: Path = "data/backups"
RUN_SUMMARY_PATH: Path = "Run_Summary.md"

# API
GROQ_API_KEY: str  # From .env

# Whisper Models
WHISPER_PRIMARY_MODEL = "whisper-large-v3"
WHISPER_FALLBACK_MODEL = "whisper-large-v3-turbo"

# LLM Models (4-tier fallback)
LLM_MODELS = [
    "llama-3.1-8b-instant",      # Primary 1 (alternating)
    "openai/gpt-oss-20b",        # Primary 2 (alternating)
    "llama-3.3-70b-versatile",   # Tier 3 fallback
    "openai/gpt-oss-120b"        # Tier 4 fallback
]
LLM_TIMEOUT = 3.0  # seconds per model

# Hotkeys
RECORDING_HOTKEY = "F1"
EXIT_HOTKEY = "ESC"
```

**Methods**:
- `validate()`: Check all required config is present
- `create_directories()`: Create required folders

---

### 2. `src/core/backup_manager.py`
**Purpose**: Manage save file backups

**Key Classes**:
- `BackupManager`

**Methods**:
```python
find_latest_autosave(character: Optional[str] = None) -> Optional[Path]
    # Find most recent .autosave file
    # Returns: Path to autosave, or None

create_backup(source_path: Path) -> Optional[Path]
    # Create timestamped backup: CHARACTER_YYYYMMDD_HHMMSS.autosave
    # Returns: Path to backup, or None

cleanup_old_backups() -> int
    # Delete backups older than max_age_hours
    # Returns: Number of files deleted

get_backup_stats() -> dict
    # Get backup statistics
    # Returns: {total_backups, total_size_mb, oldest_backup, newest_backup, ...}
```

**Example**:
```python
from src.core.backup_manager import BackupManager
from src.core.config import Config

mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR, max_age_hours=24)

# Find latest
latest = mgr.find_latest_autosave()

# Create backup
backup = mgr.create_backup(latest)

# Cleanup old
deleted = mgr.cleanup_old_backups()
```

---

### 3. `src/core/save_parser.py`
**Purpose**: Parse Slay the Spire save files using spireslayer

**Key Classes**:
- `SaveParser`

**Methods**:
```python
parse_save_file(save_file_path: Path) -> Optional[Dict[str, Any]]
    # Parse save file using spireslayer.Editor
    # Returns: Raw save data dict, or None

extract_run_data(save_data: dict, save_filename: str) -> Dict[str, Any]
    # Extract structured run data from raw save
    # Returns: Run data dict with normalized fields

save_to_json(run_data: dict, output_path: Path) -> bool
    # Save run data to JSON file
    # Returns: True if successful

parse_and_extract(save_file_path: Path, json_output_path: Optional[Path]) -> Optional[dict]
    # Convenience method: parse + extract in one call
    # Returns: Run data dict
```

**Run Data Format**:
```python
{
    "character": "WATCHER",           # From filename
    "ascension": 3,                   # Ascension level
    "act": 1,                         # Current act (1-4)
    "floor": 8,                       # Floor number
    "current_hp": 66,                 # Current HP
    "max_hp": 72,                     # Max HP
    "gold": 117,                      # Gold amount
    "deck": [                         # List of card IDs
        "Strike_P",
        "Defend_P",
        "Vigilance+",                 # Upgraded cards have +
        ...
    ],
    "relics": ["PureWater", ...],    # List of relic IDs
    "potions": ["Regen Potion", ...],# List of potion IDs
    "has_ruby_key": False,
    "has_emerald_key": False,
    "has_sapphire_key": False,
    "boss": "The Guardian",
    "seed": "123456789"
}
```

---

### 4. `src/knowledge/knowledge_base.py`
**Purpose**: Load and query game data (cards, relics, potions)

**Key Classes**:
- `KnowledgeBase`

**Methods**:
```python
get_cards_for_character(character: str) -> List[str]
    # Get all cards for a character (colorless + class-specific)
    # Args: character = "ironclad"|"silent"|"defect"|"watcher"
    # Returns: List of card names

get_all_relics() -> List[str]
    # Get all relic names
    # Returns: List of relic names

get_card_data(card_name: str) -> Optional[dict]
    # Get full card data (case-insensitive)
    # Returns: Card dict or None

get_relic_data(relic_name: str) -> Optional[dict]
    # Get full relic data (case-insensitive)
    # Returns: Relic dict or None

fuzzy_match_card(query: str, character: Optional[str], threshold: float = 0.6) -> List[Tuple[str, float]]
    # Find cards matching query with fuzzy matching
    # Returns: [(card_name, similarity_score), ...]

find_best_match(query: str, character: Optional[str], match_type: str) -> Optional[str]
    # Find single best match for query
    # Args: match_type = "card"|"relic"
    # Returns: Best matching name or None
```

**Card Data Format**:
```python
{
    "name": "Strike",
    "color": "RED",
    "rarity": "BASIC",
    "type": "ATTACK",
    "cost": 1,
    "description": "Deal 6 damage.",
    "damage": 6,
    "cost_upgraded": 1,
    "description_upgraded": "Deal 9 damage.",
    "damage_upgraded": 9
}
```

---

### 5. `src/summary/summary_generator.py`
**Purpose**: Generate formatted Run_Summary.md

**Key Classes**:
- `RunSummaryGenerator`

**Methods**:
```python
generate_summary(run_data: dict, output_path: Optional[Path], preserve_choice: bool = True) -> str
    # Generate full markdown summary
    # Args:
    #   preserve_choice: Keep existing "Current choice:" section if file exists
    # Returns: Formatted markdown string
```

**Summary Format**:
```markdown
# Slay the Spire Run Summary

## Run Information
- **Character**: WATCHER
- **Ascension**: 3
- **Act**: 1

## Current Status
- **HP**: 66/72
- **Gold**: 117

## Deck (11 cards)
- 4x Defend [1] (Skill): Gain 5 Block.
- Eruption [2] (Attack): Deal 9 damage. Enter Wrath.
- Vigilance+ [2] (Skill): Gain 12 Block. Enter Calm.

## Relics
- PureWater: At the start of each combat, add a Miracle into your hand.

## Potions
- Regen Potion: Gain 5 Regen.

## Keys
- Ruby: ✗
- Emerald: ✗
- Sapphire: ✓

## Boss & Elites
- **Current Boss**: The Guardian
- **Elites defeated this act:** None

**Current choice:**
- Battle Hymn [1] (Power): At the start of each turn, add a *Smite into your hand.
- SKIP?

---
```

---

### 6. `src/summary/choice_updater.py`
**Purpose**: Update "Current choice:" section in Run_Summary.md

**Key Classes**:
- `ChoiceUpdater`

**Methods**:
```python
update_choice_section(summary_path: Path, choices: List[str]) -> bool
    # Replace "Current choice:" section with new choices
    # Always appends "- SKIP?" at the end
    # Returns: True if successful

add_choices_to_summary(summary_path: Path, new_choices: List[str], append: bool = False) -> bool
    # Add choices (replace or append mode)
    # Args: append = True to add to existing, False to replace
    # Returns: True if successful
```

---

### 7. `src/voice/voice_recorder.py`
**Purpose**: Record audio on F1 hotkey

**Key Classes**:
- `VoiceRecorder`

**Methods**:
```python
record_audio(max_duration: float = 30.0) -> Optional[np.ndarray]
    # Record while F1 is held down
    # Returns: Numpy array of audio samples, or None

save_audio_to_wav(audio_data: np.ndarray, output_path: Path) -> bool
    # Save audio to WAV file
    # Returns: True if successful

record_to_file(output_path: Path, max_duration: float = 30.0) -> bool
    # Record and save in one call
    # Returns: True if successful
```

**Audio Format**:
- Sample Rate: 16000 Hz (required by Whisper)
- Channels: 1 (mono)
- Format: 16-bit PCM WAV

---

### 8. `src/voice/transcriber.py`
**Purpose**: Transcribe audio using Groq Whisper API

**Key Classes**:
- `AudioTranscriber`

**Methods**:
```python
transcribe_audio(audio_path: Path, language: str = "en") -> Optional[str]
    # Transcribe audio file
    # Tries primary model first, falls back to secondary
    # Returns: Transcribed text or None
```

**Whisper Models**:
- Primary: `whisper-large-v3` (better accuracy)
- Fallback: `whisper-large-v3-turbo` (faster)

---

### 9. `src/llm/name_corrector.py`
**Purpose**: Correct card/relic names using LLM with 4-model fallback

**Key Classes**:
- `NameCorrector`

**Methods**:
```python
correct_names(transcribed_text: str, character: str, include_relics: bool = True) -> Tuple[List[str], List[str]]
    # Correct names from transcription
    # Args:
    #   transcribed_text: Voice transcription
    #   character: Current character class
    #   include_relics: Include relics in matching
    # Returns: (card_names, relic_names)
```

**LLM Fallback Chain**:
1. `llama-3.1-8b-instant` (alternating primary)
2. `openai/gpt-oss-20b` (alternating primary)
3. `llama-3.3-70b-versatile` (tier 3 fallback)
4. `openai/gpt-oss-120b` (tier 4 fallback)

**Behavior**:
- Each request alternates between first two models
- 3-second timeout per model (uses threading)
- If timeout, immediately tries next model
- Returns first successful result

---

### 10. `src/utils/logger.py`
**Purpose**: Comprehensive logging system

**Key Functions**:
```python
setup_logger(component: str = "general") -> logger
    # Set up logger for component
    # Creates daily log directory (logs/YYYY-MM-DD/)
    # Component-specific log file + errors.log
    # Returns: Configured logger instance

log_operation(log: logger, operation: str, details: dict, level: str = "INFO") -> None
    # Log structured operation
    # Formats details as key=value pairs
```

**Log Components**:
- `"backup"` → `backup_operations.log`
- `"parsing"` → `save_parsing.log`
- `"voice"` → `voice_recording.log`
- `"llm"` → `llm_corrections.log`
- `"summary"` → `summary_updates.log`
- All errors also go to `errors.log`

**Log Format**:
```
2026-05-20 18:25:14.123 | INFO     | module:function:42 | message
```

---

## 📊 Data Formats

### Knowledge Base JSON

**Card File** (`data/knowledge/cards/cards_watcher.json`):
```json
{
  "_meta": {
    "file": "cards_watcher.json",
    "count": 73
  },
  "cards": [
    {
      "name": "Eruption",
      "color": "PURPLE",
      "rarity": "BASIC",
      "type": "ATTACK",
      "cost": 2,
      "description": "Deal 9 damage.\\nEnter Wrath.",
      "damage": 9,
      "cost_upgraded": 1,
      "description_upgraded": "Deal 9 damage.\\nEnter Wrath.",
      "damage_upgraded": 9
    }
  ]
}
```

**Relic File** (`data/knowledge/relics/relics_common.json`):
```json
{
  "_meta": {
    "file": "relics_common.json",
    "count": 54
  },
  "relics": [
    {
      "name": "Akabeko",
      "tier": "Common",
      "description": "Your first Attack each combat deals 8 additional damage."
    }
  ]
}
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
GROQ_API_KEY=your_api_key_here
```

### Key Configuration Settings

**Save File Location**:
```python
Config.GAME_SAVES_DIR = Path(r"c:\Games\Slay.the.Spire.v2.3.4\...\saves")
```

**Backup Settings**:
```python
Config.BACKUP_MAX_AGE_HOURS = 24  # Auto-delete backups older than this
```

**Hotkeys**:
```python
Config.RECORDING_HOTKEY = "F1"   # Press & hold to record
Config.EXIT_HOTKEY = "ESC"        # Press to exit
```

**Audio Settings**:
```python
Config.AUDIO_SAMPLE_RATE = 16000  # Required by Whisper
Config.AUDIO_CHANNELS = 1          # Mono
```

---

## 📝 Logging System

### Log Directory Structure
```
logs/
└── 2026-05-20/
    ├── backup_operations.log
    ├── save_parsing.log
    ├── voice_recording.log
    ├── llm_corrections.log
    ├── summary_updates.log
    └── errors.log
```

### Log Retention
- **Rotation**: 10 MB per file
- **Retention**: 7 days
- **Format**: Millisecond timestamps, function name, line number

### Example Log Entry
```
2026-05-20 18:25:14.567 | INFO | backup_manager:create_backup:89 | backup_created | source=WATCHER.autosave | backup=WATCHER_20260520_182514.autosave | size=10485 bytes | timestamp=20260520_182514
```

---

## 🔄 Workflow Details

### Complete Voice Recording Workflow

1. **Startup**:
   ```
   Cleanup old backups → Find latest autosave → Create backup → 
   Parse save → Extract run data → Generate Run_Summary.md
   ```

2. **F1 Recording Loop**:
   ```
   Wait for F1 → Record audio → Save WAV → Transcribe with Whisper → 
   Correct names with LLM → Update choice section → Wait for next F1
   ```

3. **LLM Name Correction Process**:
   ```
   Build prompt with:
   - Transcribed text
   - Available cards (colorless + character-specific)
   - Available relics (all)
   
   Try models:
   1. llama-3.1-8b-instant (3s timeout)
   2. openai/gpt-oss-20b (3s timeout)
   3. llama-3.3-70b-versatile (3s timeout)
   4. openai/gpt-oss-120b (3s timeout)
   
   Parse JSON response:
   {
     "cards": ["Card Name 1", "Card Name 2"],
     "relics": ["Relic Name"]
   }
   
   Validate names against knowledge base
   ```

---

## 🛠️ Common Operations

### Start Voice Recorder
```bash
python scripts/voice_recorder.py
```

### Manual Backup Cleanup
```bash
python scripts/cleanup_backups.py --max-age-hours 24
```

### Dry Run Cleanup (test without deleting)
```bash
python scripts/cleanup_backups.py --dry-run
```

### Parse Save File Manually
```python
from src.core.save_parser import SaveParser
from pathlib import Path

parser = SaveParser()
run_data = parser.parse_and_extract(Path("backup.autosave"))
print(run_data)
```

### Generate Summary Manually
```python
from src.summary.summary_generator import RunSummaryGenerator
from src.core.config import Config

gen = RunSummaryGenerator()
summary = gen.generate_summary(run_data, Config.RUN_SUMMARY_PATH)
```

### Update Choice Section Manually
```python
from src.summary.choice_updater import ChoiceUpdater
from src.core.config import Config

updater = ChoiceUpdater()
choices = [
    "Battle Hymn [1] (Power): At the start of each turn, add a *Smite.",
    "Third Eye [1] (Skill): Gain 7 Block. Scry 3."
]
updater.update_choice_section(Config.RUN_SUMMARY_PATH, choices)
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Module Tests
```bash
pytest tests/test_backup_manager.py -v
pytest tests/test_save_parser.py -v
pytest tests/test_knowledge_base.py -v
pytest tests/test_summary_generator.py -v
pytest tests/test_choice_updater.py -v
```

### Test Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Current Test Status
- **Total Tests**: 97
- **Passing**: 96
- **Coverage**: ~98%

---

## 🐛 Troubleshooting

### No Autosave Found
**Error**: `No autosave file found`  
**Solution**:
1. Check `Config.GAME_SAVES_DIR` path is correct
2. Ensure Slay the Spire has an active run (not main menu)
3. Verify .autosave files exist in saves directory

### Groq API Errors
**Error**: `GROQ_API_KEY not found`  
**Solution**:
1. Create `.env` file in project root
2. Add: `GROQ_API_KEY=your_key_here`
3. Get API key from https://console.groq.com

**Error**: `Rate limit exceeded`  
**Solution**:
- Wait a few minutes for rate limit to reset
- Models automatically fall back to next tier

### Audio Recording Issues
**Error**: `sounddevice not working`  
**Solution**:
1. Check microphone is connected and enabled
2. Try: `python -m sounddevice` to test
3. Reinstall: `pip install sounddevice --force-reinstall`

**Error**: `keyboard module requires admin rights`  
**Solution**:
- Run terminal as Administrator on Windows
- Or use pyautogui as alternative (requires code change)

### Spireslayer Parse Errors
**Error**: `Failed to parse save file`  
**Solution**:
1. Check save file is not corrupted
2. Update spireslayer: `pip install spireslayer --upgrade`
3. Check logs for detailed error message

### Choice Section Not Updating
**Error**: `Failed to update choice section`  
**Solution**:
1. Check Run_Summary.md is not open in another program
2. Verify file has "**Current choice:**" marker
3. Check logs/YYYY-MM-DD/summary_updates.log for details

---

## 📚 Additional Resources

### Project Files
- `IMPLEMENTATION_PLAN.md`: Detailed implementation roadmap
- `README.md`: User-facing documentation
- `requirements.txt`: Python dependencies

### External Documentation
- [Groq API Docs](https://console.groq.com/docs)
- [spireslayer](https://pypi.org/project/spireslayer/)
- [sounddevice](https://python-sounddevice.readthedocs.io/)

### Logs Location
All logs are in `logs/YYYY-MM-DD/` folders with component-specific files.

---

## 🔧 Extending the System

### Adding New Models
Edit `src/core/config.py`:
```python
LLM_MODELS = [
    "new-model-1",
    "new-model-2",
    ...
]
```

### Adding New Card Data
1. Add JSON file to `data/knowledge/cards/`
2. Update `Config.CARD_FILES` in `config.py`
3. Restart application (knowledge base auto-loads)

### Custom Hotkeys
Edit `src/core/config.py`:
```python
RECORDING_HOTKEY = "F2"  # or any other key
EXIT_HOTKEY = "Q"
```

---

**End of AI Developer Guide**
