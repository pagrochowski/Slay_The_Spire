# Slay the Spire Advisor

An intelligent game advisor for **Slay the Spire** that tracks deck building, relic collection, and provides real-time strategic advice during runs.

## Project Overview

### Vision
A voice-controlled AI assistant that:
- Tracks your current deck composition and relics
- Provides strategic advice on card picks, relic choices, and pathing
- Responds to voice commands with spoken advice in real-time
- Uses a local LLM with access to comprehensive game knowledge

### Current Phase: Knowledge Database
Building a comprehensive database of Slay the Spire game data including:
- All cards (attributes, synergies, strategies)
- All relics (effects, synergies, tier rankings)
- Game keywords and mechanics
- Character-specific information (Ironclad, Silent, Defect, Watcher)
- Strategic knowledge (archetypes, combos, tier lists)

## Data Sources

- **Primary API**: [Slay the Spire API](https://github.com/jhcheung/slay-the-spire-api)
  - `/api/v1/cards` - Card data
  - `/api/v1/relics` - Relic data
  - `/api/v1/keywords` - Game keywords/mechanics

## Project Structure

```
Slay_The_Spire/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── api/                    # API client for data fetching
│   │   ├── __init__.py
│   │   └── sts_client.py       # Slay the Spire API client
│   ├── database/               # Database models and operations
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy/database models
│   │   └── db_manager.py       # Database operations
│   ├── data/                   # Data processing and enrichment
│   │   ├── __init__.py
│   │   ├── card_processor.py
│   │   └── relic_processor.py
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       └── logger.py
├── data/                       # Raw and processed data files
│   ├── raw/                    # Raw API responses
│   └── processed/              # Cleaned/enriched data
├── db/                         # Database files
│   └── sts_knowledge.db        # SQLite database
├── scripts/                    # Utility scripts
│   ├── fetch_data.py           # Fetch data from API
│   ├── populate_db.py          # Populate database
│   └── validate_data.py        # Data validation
├── tests/                      # Unit tests
│   └── __init__.py
└── docs/                       # Documentation
    └── database_schema.md
```

## Tech Stack

- **Python 3.11+**
- **SQLite** (development) / **PostgreSQL** (production-ready option)
- **SQLAlchemy** - ORM for database operations
- **httpx/requests** - API client
- **Pydantic** - Data validation

### Future Additions
- **Local LLM** - For intelligent advice generation
- **Speech Recognition** - Voice command input
- **Text-to-Speech** - Voiced responses
- **Game State Tracking** - Real-time deck/relic monitoring

## Setup

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. Clone/navigate to the project directory
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Fetch and populate database:
   ```bash
   python scripts/fetch_data.py
   python scripts/populate_db.py
   ```

## Development Roadmap

### Phase 1: Knowledge Database (Current)
- [ ] Set up project structure
- [ ] Create API client for data fetching
- [ ] Design database schema
- [ ] Populate database with cards, relics, keywords
- [ ] Add strategic metadata (tier lists, synergies)

### Phase 2: Knowledge Enrichment
- [ ] Add card synergy mappings
- [ ] Add archetype definitions
- [ ] Add strategic tips and priorities
- [ ] Create relic interaction database

### Phase 3: LLM Integration
- [ ] Set up local LLM (e.g., Ollama, llama.cpp)
- [ ] Create RAG system for game knowledge
- [ ] Implement query interface

### Phase 4: Voice Interface
- [ ] Integrate speech recognition
- [ ] Implement text-to-speech
- [ ] Create voice command parser

### Phase 5: Game Integration
- [ ] Real-time deck tracking
- [ ] Run state management
- [ ] Live advice during gameplay

## License

This project is for personal/educational use. Slay the Spire is developed by MegaCrit.

## Acknowledgments

- [MegaCrit](https://www.megacrit.com/) - Slay the Spire developers
- [jhcheung/slay-the-spire-api](https://github.com/jhcheung/slay-the-spire-api) - API source
