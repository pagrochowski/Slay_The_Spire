# Slay the Spire Voice Recorder - Refactoring Implementation Plan

**Date**: May 20, 2026  
**Goal**: Complete clean rebuild with professional code structure, comprehensive logging, and unit tests

---

## 📁 **NEW PROJECT STRUCTURE**

```
Slay_The_Spire/
├── src/                          # Clean source code
│   ├── __init__.py
│   ├── core/                     # Core save file operations
│   │   ├── __init__.py
│   │   ├── backup_manager.py    # Copy & cleanup save file backups
│   │   ├── save_parser.py       # Parse save files using spireslayer
│   │   └── config.py            # Configuration management
│   ├── voice/                    # Voice recording
│   │   ├── __init__.py
│   │   ├── voice_recorder.py    # F1 hotkey, audio capture
│   │   └── transcriber.py       # Groq Whisper API integration
│   ├── llm/                      # LLM integration
│   │   ├── __init__.py
│   │   └── name_corrector.py    # 4-model fallback name correction
│   ├── knowledge/                # Knowledge base access
│   │   ├── __init__.py
│   │   └── knowledge_base.py    # Load/query card & relic data
│   ├── summary/                  # Run summary management
│   │   ├── __init__.py
│   │   ├── summary_generator.py # Generate Run_Summary.md
│   │   └── choice_updater.py    # Update current choice section
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── logger.py            # Comprehensive logging system
├── scripts/                      # Executable scripts
│   ├── voice_recorder.py        # Main F1 voice recorder (no --choice-mode)
│   ├── cleanup_backups.py       # Daily backup cleanup utility
│   └── regenerate_guide.py      # Generate AI_GUIDE.md
├── tests/                        # Unit tests (pytest)
│   ├── __init__.py
│   ├── test_backup_manager.py
│   ├── test_save_parser.py
│   ├── test_knowledge_base.py
│   ├── test_summary_generator.py
│   ├── test_voice_recorder.py
│   ├── test_name_corrector.py
│   └── test_choice_updater.py
├── data/                         # Knowledge base (keep as-is)
│   ├── knowledge/
│   │   ├── cards/
│   │   ├── relics/
│   │   └── potions.json
│   ├── backups/                 # Save file backups (auto-cleanup >24h)
│   └── processed/
├── logs/                         # Comprehensive logging
│   └── YYYY-MM-DD/              # Daily log folders
│       ├── backup_operations.log
│       ├── save_parsing.log
│       ├── voice_recording.log
│       ├── llm_corrections.log
│       ├── summary_updates.log
│       └── errors.log
├── scripts_old/                  # KEEP as reference (don't delete)
├── src_old/                      # KEEP as reference (don't delete)
├── AI_GUIDE.md                   # Auto-generated technical documentation
├── Run_Summary.md                # Current run state (auto-updated)
├── requirements.txt              # Python dependencies
└── .env                          # GROQ_API_KEY
```

---

## 🔄 **WORKFLOW OVERVIEW**

### Main Voice Recorder Flow:
1. **On Startup:**
   - Auto-cleanup backups >24 hours old
   - Find latest `.autosave` file from game saves folder
   - Create timestamped backup copy
   - Parse backup to JSON
   - Generate/update `Run_Summary.md`
   - Log all operations

2. **F1 Hotkey Pressed:**
   - Start recording audio (press & hold)
   - User speaks card/relic names
   - Release F1 to stop recording
   - Send audio to Groq Whisper API for transcription
   - Log transcription result

3. **Name Correction:**
   - Extract character class from parsed save
   - Load relevant card/relic names (colorless + current class + all relics)
   - Send to LLM with 4-model fallback
   - Get corrected/matched names
   - Log LLM input/output

4. **Update Summary:**
   - Replace "Current choice:" section in `Run_Summary.md`
   - Add matched card/relic names (one per line with "- ")
   - Always end with "- SKIP?"
   - Log file modifications

---

## 🧩 **MODULE SPECIFICATIONS**

### 1. `src/core/backup_manager.py`
**Purpose**: Manage save file backups  
**Functions:**
- `cleanup_old_backups(backup_dir, max_age_hours=24)` - Delete backups >24h old
- `create_backup(source_path, backup_dir)` - Copy save file with timestamp
- `find_latest_autosave(saves_dir)` - Find most recent `.autosave` file

**Logging:**
- Every backup created: timestamp, source, destination
- Every backup deleted: timestamp, filename, age
- Errors: file not found, permission issues

**Tests:**
- Test backup creation with timestamp
- Test cleanup removes old files only
- Test find latest returns correct file

---

### 2. `src/core/save_parser.py`
**Purpose**: Parse save files to JSON  
**Functions:**
- `parse_save_file(backup_path)` - Use `spireslayer` to parse save
- `extract_run_data(parsed_save)` - Extract character, deck, relics, etc.

**Logging:**
- Parse start/end with file path
- Each data extraction step
- Parsing errors with stack trace

**Tests:**
- Test valid save file parsing
- Test invalid file handling
- Test data extraction accuracy

---

### 3. `src/knowledge/knowledge_base.py`
**Purpose**: Load and query knowledge base  
**Functions:**
- `load_knowledge_base(data_dir)` - Load all JSON files
- `get_cards_for_character(character)` - Return colorless + class-specific
- `get_all_relics()` - Return all relic names
- `find_fuzzy_match(query, candidates, threshold=0.6)` - Fuzzy matching helper

**Logging:**
- Files loaded with counts
- Query results with match scores

**Tests:**
- Test loading all card/relic files
- Test character-specific filtering
- Test fuzzy matching accuracy

---

### 4. `src/summary/summary_generator.py`
**Purpose**: Generate Run_Summary.md from parsed data  
**Functions:**
- `generate_summary(run_data, output_path)` - Create full markdown
- `format_deck_cards(cards)` - One per line with multipliers (e.g., "3x Strike")
- `format_card_with_details(card_name, knowledge_base)` - Add energy cost + description
- `format_relic_with_description(relic_name, knowledge_base)` - Add description
- `format_potion_with_description(potion_name, knowledge_base)` - Add description

**Logging:**
- Summary generation start/end
- Card/relic lookups in knowledge base
- File write operations

**Tests:**
- Test full summary generation
- Test card multiplier formatting
- Test description lookups

---

### 5. `src/voice/voice_recorder.py`
**Purpose**: F1 hotkey and audio recording  
**Functions:**
- `initialize_recorder(config)` - Set up audio device
- `record_audio(hotkey='F1')` - Press & hold to record
- `save_audio_temp(audio_data)` - Save to temp WAV file

**Logging:**
- Hotkey press/release timestamps
- Audio duration and file size
- Recording errors

**Tests:**
- Test audio device initialization
- Test temp file creation
- Mock hotkey events

---

### 6. `src/voice/transcriber.py`
**Purpose**: Groq Whisper API transcription  
**Functions:**
- `transcribe_audio(audio_file_path, model='whisper-large-v3')` - Send to API
- `transcribe_with_fallback(audio_file_path)` - Try both Whisper models

**Groq Models:**
- Primary: `whisper-large-v3` (better accuracy)
- Fallback: `whisper-large-v3-turbo` (faster)

**Logging:**
- API call start/end with model name
- Transcription result text
- API errors and fallback attempts

**Tests:**
- Mock API responses
- Test fallback on error
- Test empty audio handling

---

### 7. `src/llm/name_corrector.py`
**Purpose**: LLM-based name correction with 4-model fallback  
**Functions:**
- `correct_names(transcribed_text, available_cards, available_relics)` - Main function
- `_call_with_timeout(model, prompt, timeout=3.0)` - Threading-based timeout
- `_build_correction_prompt(text, cards, relics)` - Create LLM prompt

**Groq Models (fallback chain):**
1. `llama-3.1-8b-instant` (alternating primary)
2. `openai/gpt-oss-20b` (alternating primary)
3. `llama-3.3-70b-versatile` (tier 3 fallback)
4. `openai/gpt-oss-120b` (tier 4 fallback)

**Timeout Strategy:**
- 3 seconds per model
- Use threading to abandon slow requests
- Alternate between first two models
- Escalate to tier 3/4 if both primaries fail

**Logging:**
- Each model attempt with timestamp
- Timeout events
- Final matched names
- Full prompt and response (for debugging)

**Tests:**
- Mock LLM responses
- Test timeout behavior
- Test 4-model fallback chain
- Test name matching accuracy

---

### 8. `src/summary/choice_updater.py`
**Purpose**: Update "Current choice:" section in Run_Summary.md  
**Functions:**
- `update_current_choice(summary_path, choices)` - Replace choice section
- `format_choice_list(choices)` - Format as "- Card Name\n- SKIP?"

**Behavior:**
- Replaces entire "Current choice:" section each time
- Always ends with "- SKIP?"
- Preserves all other sections

**Logging:**
- Before/after content snapshots
- Line numbers modified
- Choices added

**Tests:**
- Test section replacement
- Test preserving other sections
- Test SKIP appending

---

### 9. `src/utils/logger.py`
**Purpose**: Comprehensive logging system  
**Features:**
- Daily log folders: `logs/YYYY-MM-DD/`
- Separate logs by component (backup, parsing, voice, llm, summary, errors)
- Millisecond timestamps
- Include: function name, line number, operation type
- Auto-rotation (10 MB per file, 7 days retention)

**Log Files:**
- `backup_operations.log` - All backup create/delete operations
- `save_parsing.log` - Save file read & parse steps
- `voice_recording.log` - F1 events, recording, transcription
- `llm_corrections.log` - All LLM calls with prompts/responses
- `summary_updates.log` - Run_Summary.md modifications
- `errors.log` - All exceptions and errors

**Functions:**
- `setup_logger(component_name)` - Initialize logger for component
- `log_operation(logger, operation, details)` - Structured operation logging

**Tests:**
- Test log file creation
- Test log rotation
- Test multi-component logging

---

## 📝 **MAIN SCRIPT: scripts/voice_recorder.py**

**Purpose**: Main executable for voice recording workflow  
**Behavior:**
```python
1. Parse arguments (NO --choice-mode flag)
2. Initialize logger
3. Load configuration (.env, save paths)
4. Auto-cleanup old backups (>24h)
5. Find latest autosave
6. Create backup
7. Parse save to JSON
8. Load knowledge base
9. Generate Run_Summary.md
10. Start F1 hotkey listener loop:
    - On F1 press: record audio
    - On F1 release: transcribe
    - Correct names with LLM
    - Update current choice section
    - Log all steps
11. Exit on ESC key
```

**Logging:**
- Startup sequence
- Each workflow step
- Graceful shutdown

---

## 🧪 **TESTING STRATEGY**

### Unit Tests (pytest):
1. **test_backup_manager.py**
   - Test backup creation with mock files
   - Test cleanup with various ages
   - Test find latest autosave

2. **test_save_parser.py**
   - Mock spireslayer responses
   - Test data extraction
   - Test error handling

3. **test_knowledge_base.py**
   - Test loading JSON files
   - Test character filtering
   - Test fuzzy matching

4. **test_summary_generator.py**
   - Test full summary generation
   - Test card formatting with multipliers
   - Test description lookups

5. **test_voice_recorder.py**
   - Mock audio device
   - Test recording flow
   - Test temp file handling

6. **test_name_corrector.py**
   - Mock LLM API responses
   - Test timeout behavior
   - Test 4-model fallback
   - Test name matching

7. **test_choice_updater.py**
   - Test section replacement
   - Test SKIP appending
   - Test file preservation

### Integration Tests:
- End-to-end workflow with test save file
- Verify Run_Summary.md generation
- Verify choice updates

---

## 📋 **IMPLEMENTATION ORDER**

### Phase 1: Foundation (Days 1-2)
1. ✅ Create new folder structure
2. ✅ Set up logging system (`src/utils/logger.py`)
3. ✅ Create configuration module (`src/core/config.py`)
4. ✅ Write unit tests for logger

### Phase 2: Core Functionality (Days 3-5)
5. ✅ Implement backup manager
6. ✅ Implement save parser
7. ✅ Implement knowledge base loader
8. ✅ Write unit tests for core modules

### Phase 3: Summary Generation (Days 6-7)
9. ✅ Implement summary generator
10. ✅ Implement choice updater
11. ✅ Write unit tests

### Phase 4: Voice & LLM (Days 8-10)
12. ✅ Implement voice recorder
13. ✅ Implement transcriber
14. ✅ Implement name corrector with 4-model fallback
15. ✅ Write unit tests

### Phase 5: Integration (Days 11-12)
16. ✅ Create main voice_recorder.py script
17. ✅ Create cleanup_backups.py utility
18. ✅ Integration testing
19. ✅ Bug fixes

### Phase 6: Documentation (Day 13)
20. ✅ Generate AI_GUIDE.md (comprehensive technical doc)
21. ✅ Update README.md
22. ✅ Final review

---

## 🔑 **KEY TECHNICAL DETAILS**

### Save File Location:
```
c:\Games\Slay.the.Spire.v2.3.4\Slay.the.Spire.v2.3.4\saves\
```

### Groq API Models:
**Whisper (transcription):**
- Primary: `whisper-large-v3`
- Fallback: `whisper-large-v3-turbo`

**LLM (name correction):**
1. `llama-3.1-8b-instant` (alternating)
2. `openai/gpt-oss-20b` (alternating)
3. `llama-3.3-70b-versatile` (fallback)
4. `openai/gpt-oss-120b` (final fallback)

### Hotkey Behavior:
- Press and hold F1 to record
- Release F1 to stop and process
- ESC to exit program

### Character-Specific Cards:
- Ironclad: Include colorless + ironclad (exclude silent, defect, watcher)
- Silent: Include colorless + silent (exclude others)
- Defect: Include colorless + defect (exclude others)
- Watcher: Include colorless + watcher (exclude others)
- **Always include ALL relics** (relics are not class-specific)

---

## 📖 **AI_GUIDE.md CONTENTS**

The auto-generated technical documentation should include:

1. **Project Overview**
   - Purpose and functionality
   - High-level workflow diagram

2. **Architecture**
   - Module breakdown with responsibilities
   - Data flow diagrams
   - Dependency graph

3. **Module Documentation**
   - Each module's purpose
   - Key functions with signatures
   - Data structures and types

4. **Data Formats**
   - Save file structure (spireslayer output)
   - Knowledge base JSON schemas
   - Run_Summary.md template
   - LLM prompt/response formats

5. **Configuration**
   - Environment variables
   - File paths
   - API keys and models

6. **Logging**
   - Log file locations
   - Log format specifications
   - How to debug issues

7. **Testing**
   - How to run tests
   - Test coverage requirements
   - Mock data locations

8. **Common Operations**
   - How to add a new card
   - How to debug LLM failures
   - How to manually edit summaries

9. **Troubleshooting**
   - Common errors and solutions
   - API quota issues
   - Save file corruption handling

---

## ✅ **SUCCESS CRITERIA**

- ✅ All modules have >80% test coverage
- ✅ Comprehensive logs for every operation
- ✅ 4-model LLM fallback works reliably
- ✅ Run_Summary.md generated correctly with descriptions
- ✅ Voice recording works with F1 hotkey
- ✅ Auto-cleanup removes backups >24h old
- ✅ AI_GUIDE.md is comprehensive and accurate
- ✅ No --choice-mode flag (removed)
- ✅ Class-specific card filtering works
- ✅ Code is clean, well-commented, and maintainable

---

**Status**: Ready to implement Phase 1  
**Next Step**: Create folder structure and logging system
