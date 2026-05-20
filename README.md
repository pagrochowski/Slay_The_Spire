# Slay the Spire Voice Recorder

**Version 2.0** - Clean, professional refactor

A **voice-controlled choice recorder** for **Slay the Spire** that lets you record card and relic choices via hotkey, automatically transcribes them with Whisper, and updates your Run_Summary.md using LLM-powered name correction.

## ✨ Features

- 🎤 **F1 Hotkey Recording** - Press and hold F1 to record card/relic choices
- 🎙️ **Groq Whisper Transcription** - Automatic voice-to-text with whisper-large-v3
- 🤖 **LLM Name Correction** - 4-model fallback chain corrects misspellings
- 📊 **Knowledge Base** - 365 cards, 178 relics, 42 potions with fuzzy matching
- 💾 **Auto-Backup** - Save file backups with auto-cleanup (24h retention)
- 📄 **Run Summary** - Auto-generated markdown with deck, relics, and choices
- 📝 **Comprehensive Logging** - Daily logs with millisecond timestamps
- ✅ **98% Test Coverage** - 150+ unit tests with pytest

## 🎯 How It Works

1. **Startup**: Finds latest save → Creates backup → Parses run data → Generates Run_Summary.md
2. **F1 Loop**: Press F1 → Record audio → Transcribe → Correct names → Update choice section
3. **ESC to Exit**: Clean shutdown with logs

## 🛠️ Tech Stack

- **Python 3.13**
- **Groq API** - Whisper (transcription) + LLMs (name correction)
  - Whisper: `whisper-large-v3` → `whisper-large-v3-turbo`
  - LLMs: `llama-3.1-8b-instant` ↔ `openai/gpt-oss-20b` → `llama-3.3-70b-versatile` → `openai/gpt-oss-120b`
- **spireslayer 2.0.0** - Save file parsing
- **sounddevice + keyboard** - Audio recording with hotkey
- **loguru** - Logging system

## 📁 Project Structure

```
Slay_The_Spire/
├── src/                           # Clean modular code
│   ├── core/                      # Save file operations
│   │   ├── config.py             # Configuration
│   │   ├── backup_manager.py     # Backup creation & cleanup
│   │   └── save_parser.py        # Save file parsing
│   ├── voice/                     # Voice recording
│   │   ├── voice_recorder.py     # F1 hotkey recording
│   │   └── transcriber.py        # Groq Whisper API
│   ├── llm/                       # LLM integration
│   │   └── name_corrector.py     # 4-model fallback
│   ├── knowledge/                 # Knowledge base
│   │   └── knowledge_base.py     # Card/relic lookup
│   ├── summary/                   # Summary management
│   │   ├── summary_generator.py  # Generate markdown
│   │   └── choice_updater.py     # Update choice section
│   └── utils/
│       └── logger.py             # Logging system
├── scripts/
│   ├── voice_recorder.py         # Main application
│   └── cleanup_backups.py        # Backup cleanup utility
├── tests/                         # 150+ unit tests
├── data/
│   ├── knowledge/                # JSON game data
│   ├── backups/                  # Save file backups
│   └── processed/                # Parsed JSON & temp audio
├── logs/                          # Daily log folders
├── Run_Summary.md                 # Auto-generated run summary
├── AI_GUIDE.md                    # Technical documentation
└── IMPLEMENTATION_PLAN.md         # Development roadmap
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.13+**
- **Groq API Key** - [Get one free](https://console.groq.com)
- **Microphone** for voice input
- **Admin rights** on Windows (for keyboard module)

### Installation

1. **Clone and activate environment:**
   ```powershell
   cd c:\Tragik\__DEV_folder\Slay_The_Spire
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   ```powershell
   # Create .env file in project root
   "GROQ_API_KEY=your_api_key_here" | Out-File -FilePath .env -Encoding UTF8
   ```

4. **Configure game save path** (edit `src/core/config.py`):
   ```python
   GAME_SAVES_DIR = Path(r"c:\Games\Slay.the.Spire.v2.3.4\...\saves")
   ```

### Usage

**Start the voice recorder:**
```powershell
python scripts/voice_recorder.py
```

**Workflow:**
1. Application starts → Cleans old backups → Finds latest save → Parses run → Generates Run_Summary.md
2. Press and hold **F1** to record card/relic choices
3. Release F1 → Audio transcribed → Names corrected → Choice section updated
4. Press **ESC** to exit

**Example voice input:**
```
"Battle Hymn and Third Eye"
→ Transcribed: "battle him and third eye"  
→ Corrected: ["Battle Hymn", "Third Eye"]
→ Run_Summary.md updated with full descriptions
```

## 📄 Run Summary Format

Auto-generated `Run_Summary.md`:

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
- Pure Water: At the start of each combat, add a Miracle into your hand.

**Current choice:**
- Battle Hymn [1] (Power): At the start of each turn, add a *Smite into your hand.
- Third Eye [1] (Skill): Gain 7 Block. Scry 3.
- SKIP?
```

## 🧪 Testing

**Run all tests:**
```powershell
pytest tests/ -v
```

**Test coverage:**
```powershell
pytest tests/ --cov=src --cov-report=html
```

**Current status:** 150 tests, ~98% coverage

## 📊 Knowledge Base

JSON files in `data/knowledge/`:
- **Cards**: 365 total (colorless + 4 classes)
- **Relics**: 178 total (by rarity)
- **Potions**: 42 total

Example card data:
```json
{
  "name": "Battle Hymn",
  "color": "PURPLE",
  "type": "POWER",
  "cost": 1,
  "description": "At the start of each turn, add a *Smite into your hand."
}
```

## 📝 Logging

Logs saved to `logs/YYYY-MM-DD/`:
- `backup_operations.log` - Backup creation & cleanup
- `save_parsing.log` - Save file parsing
- `voice_recording.log` - Audio recording
- `llm_corrections.log` - LLM name correction
- `summary_updates.log` - Summary updates
- `errors.log` - All errors

## 🔧 Configuration

Edit `src/core/config.py` for:
- Game save directory path
- Backup retention (default: 24 hours)
- Hotkeys (default: F1 record, ESC exit)
- LLM models & timeout
- Audio settings

## 📚 Documentation

- [AI_GUIDE.md](AI_GUIDE.md) - Complete technical documentation for developers
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Development roadmap
- `logs/` - Daily operation logs

## 🛠️ Utilities

**Cleanup old backups:**
```powershell
python scripts/cleanup_backups.py --max-age-hours 24
```

**Dry run (no deletion):**
```powershell
python scripts/cleanup_backups.py --dry-run
```

## 🐛 Troubleshooting

### No autosave found
- Check `GAME_SAVES_DIR` path in config.py
- Ensure Slay the Spire has an active run (not main menu)

### Groq API errors
- Verify .env file contains valid GROQ_API_KEY
- Check API rate limits (models auto-fallback)

### Audio recording not working
- Run PowerShell as Administrator (required for keyboard module)
- Check microphone is enabled
- Test with: `python -m sounddevice`

### Choice section not updating
- Ensure Run_Summary.md is not open in another program
- Check logs/YYYY-MM-DD/summary_updates.log for details

## 📦 Requirements

See [requirements.txt](requirements.txt) for complete dependency list.

Key dependencies:
- `spireslayer==2.0.0` - Save file parsing
- `groq` - API client
- `sounddevice` - Audio recording
- `keyboard` - Hotkey support
- `loguru` - Logging
- `python-dotenv` - Environment config
- `pytest` - Testing

## 🎯 Next Steps

The system is complete and ready to use! Future enhancements could include:
- GUI interface
- Multiple hotkey support (different actions)
- Voice command recognition (not just choices)
- Integration with streaming overlays
- Cloud sync for run summaries

---

**For detailed technical documentation, see [AI_GUIDE.md](AI_GUIDE.md)**
```
You: "I can choose between Bash, Perfected Strike, or Heavy Blade"
```

**Add cards to deck:**
```
You: "Add Perfected Strike"
```

**Set boss and get strategy:**
```
You: "The boss is Bronze Automaton"
→ Automatically generates comprehensive strategy covering:
  - Boss mechanics and move patterns
  - Long-term deck goals
  - Short-term problems to solve
  - Card priorities for rewards
```

**Get upgrade advice:**
```
You: "Should I upgrade Perfected Strike?"
```

**Update floor/act:**
```
You: "I'm on floor 23 in act 2"
```

**Push-to-talk:** Hold SPACE to speak, release to process

## Commands

The voice advisor supports 21 intent types:

| Intent | Example | Description |
|--------|---------|-------------|
| `start_run` | "Start Ironclad ascension 5" | Begin new run tracking |
| `card_choice` | "Strike, Bash, or Defend?" | Get card pick advice |
| `add_card` | "Add Perfected Strike" | Add card to deck |
| `remove_card` | "Remove basic Strike" | Remove card from deck |
| `upgrade_card` | "Should I upgrade Bash?" | Get upgrade advice |
| `relic_choice` | "Dead Branch or Toxic Egg?" | Compare relics |
| `add_relic` | "Add Dead Branch" | Add relic to run |
| `set_boss` | "Boss is The Champ" | Set and strategize for boss |
| `update_floor` | "Floor 17 act 2" | Update progress |
| `update_hp` | "80 out of 88 HP" | Update health |
| `update_gold` | "I have 217 gold" | Update gold |
| `adjust_strategy` | "Update strategy" | Regenerate comprehensive strategy |
| `general_question` | "What beats Gremlin Nob?" | Ask game questions |

See full list with `--help`

## Project Structure

```
Slay_The_Spire/
├── scripts/
│   └── voice_advisor.py        # Main entry point
├── src/
│   ├── advisor/
│   │   ├── groq_advisor.py     # Groq AI integration + RAG
│   │   ├── command_parser.py   # Intent classification
│   │   └── run_manager.py      # Run state persistence
│   └── voice/
│       └── voice_interface.py  # STT/TTS with push-to-talk
├── data/
│   ├── knowledge/              # JSON knowledge base (19 files)
│   ├── raw/                    # Source data (cards, relics, bosses)
│   └── runs.json               # Active run persistence
└── docs/
    ├── README.md               # Documentation overview
    └── strategic_reference.md  # Expert tier lists & strategies
```

```

## Features & Architecture

### Voice Interface
- **Speech-to-Text**: Whisper-large-v3 via Groq API (99% accuracy)
- **Text-to-Speech**: Edge TTS with en-US-AriaNeural voice
- **Push-to-Talk**: Hold SPACE bar to record
- **Dual Model Fallback**: Automatic failover if primary model is rate-limited

### Intent Parser
- **Fast Classification**: llama-3.1-8b-instant processes commands in <1s
- **21 Intent Types**: Card choice, relic choice, upgrade advice, boss strategy, etc.
- **JSON-Only Output**: Enforced with `response_format={"type": "json_object"}`
- **Modifier Handling**: Recognizes "basic strike" vs "Swift Strike"
- **Act Detection**: Automatically determines act from floor number

### Strategic Advisor  
- **Context-Aware**: Uses run state (deck, relics, floor, HP, boss)
- **RAG System**: Injects card/relic/enemy info into LLM context
- **Comprehensive Strategy**: 4-section updates (boss tactics, long-term goals, problems, card priorities)
- **Auto-Updates**: Regenerates summary and strategy after deck changes
- **Boss Focus**: Special strategy mode when boss is set

### Run Management
- **Persistent Storage**: All runs saved to `data/runs.json`
- **Event Logging**: Tracks cards added/removed, relics, floor progression
- **Summary Generation**: Creates `run_summary_{character}_A{ascension}.md`
- **Resume Support**: Continue interrupted runs automatically
- **Multi-Run Support**: Keep up to 5 recent runs

## Configuration

Edit `.env` to customize:
```ini
GROQ_API_KEY=your_key_here

# Voice settings (optional)
WHISPER_MODEL=whisper-large-v3
TTS_VOICE=en-US-AriaNeural

# Model settings (optional)  
ADVISOR_MODEL=openai/gpt-oss-120b
PARSER_MODEL=llama-3.1-8b-instant
```

## Future Enhancements

- [ ] Screen capture integration (auto-detect cards/relics)
- [ ] Real-time deck overlay
- [ ] Historical run analytics
- [ ] Win rate predictions
- [ ] Elite/boss fight timers
- [ ] Potion usage tracking
- [ ] Event decision database

## Contributing

Data improvements welcome! The knowledge base is in `data/knowledge/` and `data/raw/`.

## License

MIT

## Acknowledgments

- Game data from [Slay the Spire API](https://github.com/jhcheung/slay-the-spire-api)
- Boss strategies from [Slay the Spire Wiki](https://slay-the-spire.fandom.com)
- Powered by [Groq](https://groq.com) for fast AI inference
- Slay the Spire by [MegaCrit](https://www.megacrit.com/)



