# Slay the Spire Voice Advisor

A **voice-controlled AI assistant** for **Slay the Spire** that provides real-time strategic advice during runs using Groq AI, Whisper speech-to-text, and Edge TTS.

## ✨ Features

- 🎤 **Voice Commands** - Push-to-talk with Whisper-large-v3 for accurate speech recognition
- 🤖 **Intelligent Advice** - Groq AI (GPT-OSS-120B) provides strategic guidance on cards, relics, and enemies
- 🔊 **Natural Speech** - Edge TTS (en-US-AriaNeural) for natural voice responses
- 📊 **Comprehensive Knowledge Base** - 365 cards, 178 relics, 37 enemies with detailed stats and strategies
- 💾 **Run Tracking** - Automatic run state management and strategy updates
- 🎯 **Intent-Based Commands** - 21 command types including card choice, relic choice, upgrade advice, boss strategy
- 🔄 **Dual Model Fallback** - Automatic failover between models for robustness
- 📝 **Auto-Summary** - Generates detailed run summaries with strategy notes

## Current Status: Fully Operational

The voice advisor is complete and ready to use with:
- ✅ Voice interface with push-to-talk
- ✅ Intent parser for natural language commands
- ✅ Run state persistence (data/runs.json)
- ✅ Comprehensive knowledge base (data/knowledge/)
- ✅ Boss strategy system with detailed mechanics
- ✅ Automatic strategy updates on deck changes
- ✅ RAG system for card/relic/enemy lookups

## Tech Stack

- **Python 3.13** with venv
- **Groq API** - LLM inference
  - Primary: `openai/gpt-oss-120b` (advisor)
  - Fallback: `llama-3.3-70b-versatile` (advisor)
  - Parser: `llama-3.1-8b-instant` / `openai/gpt-oss-20b` (fallback)
- **Whisper-large-v3** - Speech-to-text (Groq API)
  - Fallback: `whisper-large-v3-turbo`
- **Edge TTS** - Natural voice synthesis (en-US-AriaNeural)
- **JSON Knowledge Base** - Structured game data in `data/knowledge/`
- **loguru** - Logging
- **python-dotenv** - Environment configuration

## Knowledge Base Structure

All game data is stored as split JSON files for efficient LLM context loading:

**📖 See [data/knowledge/KNOWLEDGE_MAP.md](data/knowledge/KNOWLEDGE_MAP.md)** - Master index with loading strategies

```
data/knowledge/
├── KNOWLEDGE_MAP.md            ⭐ Master index (read this first)
├── README.md                   # Developer documentation
├── cards/                      # 5 files split by character
├── relics/                     # 6 files split by rarity/pool  
├── enemies/                    # 9 files split by act + difficulty
├── potions.json
├── keywords.json
├── archetypes.json
└── ascension_modifiers.json
```

**Benefits:**
- Small context windows (load only what's needed)
- Fast lookups with `_meta` guidance
- Comprehensive data (stats, mechanics, strategies)

## Quick Start

### Prerequisites
- Python 3.13+ (tested with 3.13.9)
- Groq API key ([get one free](https://console.groq.com))
- Microphone for voice input

### Installation

1. **Clone and setup environment:**
   ```powershell
   cd Slay_The_Spire
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```powershell
   # Create .env file
   echo GROQ_API_KEY=your_api_key_here > .env
   ```

3. **Run the voice advisor:**
   ```powershell
   python scripts/voice_advisor.py
   ```

### Usage

**Start a new run:**
```
You: "Start a new Ironclad run at ascension 10"
```

**Get card advice:**
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



