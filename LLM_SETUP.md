# LLM Setup Guide - Slay the Spire AI Advisor

This guide contains all the documentation needed to initialize an LLM as a Slay the Spire game advisor.

## Quick Start

To set up an LLM chat session for the Slay the Spire advisor:

1. **Load System Prompt**: Use [docs/system_prompt.md](docs/system_prompt.md) as the system message
2. **Inject Context**: Load [docs/llm_context.md](docs/llm_context.md) into the conversation context
3. **Register Functions**: If using function calling, load [docs/llm_functions.json](docs/llm_functions.json)
4. **Reference Strategy**: Keep [docs/strategic_reference.md](docs/strategic_reference.md) available for lookups

## Documentation Files

### Core LLM Files

#### [docs/system_prompt.md](docs/system_prompt.md)
**Purpose:** System-level instructions for the LLM  
**Use:** Set as the system message when initializing the chat  
**Contains:**
- Role definition (Slay the Spire advisor)
- Core capabilities overview
- Response guidelines
- Key game knowledge summary

**Size:** ~1,200 tokens (concise, optimized for system prompt)

---

#### [docs/llm_context.md](docs/llm_context.md)
**Purpose:** Complete reference documentation for the LLM  
**Use:** Inject as initial user message or use for RAG retrieval  
**Contains:**
- Game overview (characters, ascension, mechanics)
- Complete database schema with all tables
- All available functions with signatures and examples
- Strategic advisory guidelines
- Example interactions

**Size:** ~8,000 tokens (comprehensive context document)

---

#### [docs/llm_functions.json](docs/llm_functions.json)
**Purpose:** Function calling schema for LLM  
**Use:** Register these functions for the LLM to call  
**Contains:**
- 23 function definitions in OpenAI/Ollama format
- Query functions (cards, relics, enemies, potions, keywords, ascension)
- Run management functions (create, update, track)
- Event logging functions

**Format:** OpenAI function calling JSON schema

---

#### [docs/strategic_reference.md](docs/strategic_reference.md)
**Purpose:** Expert strategic knowledge  
**Use:** Reference for tier lists, strategies, and calculations  
**Contains:**
- Card tier lists by character (S/A/B tier)
- Boss fight strategies (all 11 bosses)
- Relic tier rankings
- Event decision guides
- Energy math and damage calculations

**Size:** ~6,000 tokens (strategic knowledge base)

---

### Supporting Documentation

#### [docs/database_schema.md](docs/database_schema.md)
**Purpose:** Database structure reference  
**Use:** Understanding the data model  
**Contains:**
- All table schemas (15 tables)
- Column descriptions
- Relationships and foreign keys
- Run tracking models

---

#### [docs/plan.md](docs/plan.md)
**Purpose:** Project roadmap and architecture  
**Use:** Understanding project goals and progress  
**Contains:**
- Development phases (completed: 1-3, pending: 4-8)
- Architecture decisions
- Future plans (local LLM, voice interface)

---

## Database Files

The SQLite database is located at:
```
db/sts_knowledge.db
```

**Contents:**
- 709 cards (all characters + colorless + curses)
- 178 relics
- 66 enemies/creatures
- 42 potions
- 52 keywords
- 20 ascension modifiers (A1-A20)

**Scripts to regenerate data:**
```bash
python scripts/download_data.py        # Download from GitHub
python scripts/populate_db.py --reset  # Populate database
python scripts/populate_ascension.py   # Add ascension data
python scripts/verify_db.py            # Verify and test
```

---

## Usage Examples

### Example 1: OpenAI API Setup

```python
import openai

# Load system prompt
with open('docs/system_prompt.md', 'r') as f:
    system_prompt = f.read()

# Load context
with open('docs/llm_context.md', 'r') as f:
    context = f.read()

# Load functions
import json
with open('docs/llm_functions.json', 'r') as f:
    functions_schema = json.load(f)

# Initialize conversation
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Context:\n{context}"}
]

# Make request with function calling
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=messages,
    functions=functions_schema['functions']
)
```

### Example 2: Ollama Setup

```python
import ollama

# Load prompts
with open('docs/system_prompt.md', 'r') as f:
    system_prompt = f.read()

with open('docs/llm_context.md', 'r') as f:
    context = f.read()

# Combine for Ollama (no separate system message)
full_prompt = f"{system_prompt}\n\n{context}\n\nUser: I'm playing Ironclad A10..."

response = ollama.chat(
    model='llama3',
    messages=[{'role': 'user', 'content': full_prompt}]
)
```

### Example 3: Simple Chat Test

Start with a basic test query:

```
User: "I'm playing Ironclad A10, floor 5, Act 1. I have 50/70 HP. 
Card reward: Carnage, Shrug It Off, or Iron Wave. Which should I take?"

Expected Response: LLM should:
1. Consider character (Ironclad), ascension (A10), current HP
2. Evaluate each card option
3. Recommend Shrug It Off (block + draw is premium early)
4. Explain reasoning
```

---

## Function Implementation

The LLM will call functions like:

```python
get_card(name="Carnage")
get_run_summary(run_id=1)
add_card_to_run(run_id=1, card_name="Bash", floor=3, source="combat_reward")
```

You need to implement these functions to:
1. Connect to the SQLite database
2. Use the `DatabaseManager` class from `src/database/db_manager.py`
3. Return results to the LLM

Example implementation:

```python
from src.database import DatabaseManager

db = DatabaseManager()

def get_card(name: str) -> dict:
    with db.get_session() as session:
        card = db.get_card_by_name(session, name)
        if card:
            return {
                "name": card.name,
                "cost": card.cost,
                "type": card.card_type,
                "rarity": card.rarity,
                "description": card.description
            }
        return {"error": "Card not found"}
```

---

## Token Budget Considerations

**Total context size** (all documents):
- system_prompt.md: ~1,200 tokens
- llm_context.md: ~8,000 tokens
- strategic_reference.md: ~6,000 tokens
- **Total: ~15,200 tokens**

**Optimization strategies:**
1. **For small context models** (8k): Use system_prompt + llm_context only
2. **For medium context models** (32k): Include strategic_reference
3. **For large context models** (128k+): Include everything
4. **With RAG**: Index strategic_reference and retrieve relevant sections

---

## Next Steps

After setting up the LLM:

1. **Test Basic Queries**
   - Query cards: "Tell me about the card Demon Form"
   - Query relics: "What does Dead Branch do?"
   
2. **Test Run Tracking**
   - Create run: "Start a new Ironclad A5 run"
   - Add cards: "I picked up Carnage from floor 3"
   
3. **Test Strategic Advice**
   - Card picks: "Should I take Offering or Feed?"
   - Boss prep: "I'm about to fight Slime Boss, what should I know?"

4. **Integration**
   - Build API wrapper around database functions
   - Create chat interface
   - Add voice input/output (future)

---

## Database Access

The LLM needs access to the database to answer queries. Two approaches:

### Approach 1: Direct Database Access
```python
from src.database import DatabaseManager

db = DatabaseManager("db/sts_knowledge.db")
session = db.get_session()

# Query data
card = db.get_card_by_name(session, "Strike")
relics = db.get_all_relics(session)
```

### Approach 2: API Wrapper
Create an API layer that the LLM can call via functions:

```python
# api/advisor.py
from fastapi import FastAPI
from src.database import DatabaseManager

app = FastAPI()
db = DatabaseManager()

@app.get("/card/{name}")
def get_card(name: str):
    with db.get_session() as session:
        return db.get_card_by_name(session, name)
```

---

## Troubleshooting

**Issue:** LLM doesn't recognize functions  
**Solution:** Ensure functions are properly registered and match the schema in llm_functions.json

**Issue:** LLM gives generic advice without querying database  
**Solution:** Emphasize in prompts that it should query specific cards/relics, not rely on general knowledge

**Issue:** Context too large for model  
**Solution:** Use RAG to retrieve only relevant sections of strategic_reference.md

**Issue:** Run tracking not working  
**Solution:** Verify database models are created (`db.create_tables()`) and functions return proper IDs

---

## Project Structure

```
Slay_The_Spire/
├── LLM_SETUP.md           ← You are here
├── README.md              ← Project overview
├── requirements.txt       ← Python dependencies
│
├── docs/                  ← LLM documentation
│   ├── system_prompt.md          ← System message
│   ├── llm_context.md            ← Main context document
│   ├── llm_functions.json        ← Function schemas
│   ├── strategic_reference.md    ← Strategy guide
│   ├── database_schema.md        ← DB structure
│   └── plan.md                   ← Project roadmap
│
├── src/
│   ├── database/
│   │   ├── models.py             ← SQLAlchemy models
│   │   ├── db_manager.py         ← Database operations
│   │   └── __init__.py
│   └── utils/
│       └── logger.py
│
├── scripts/
│   ├── download_data.py          ← Fetch game data
│   ├── populate_db.py            ← Seed database
│   ├── populate_ascension.py     ← Seed ascension data
│   └── verify_db.py              ← Test database
│
├── db/
│   └── sts_knowledge.db          ← SQLite database
│
└── data/
    └── raw/                      ← Downloaded JSON data
        ├── cards.json
        ├── relics.json
        ├── enemies.json
        └── ...
```

---

## Questions?

Refer to:
- **Game data questions**: Check docs/llm_context.md
- **Strategic advice**: Check docs/strategic_reference.md
- **Database structure**: Check docs/database_schema.md
- **Implementation**: Check src/database/db_manager.py
