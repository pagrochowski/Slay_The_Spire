#!/usr/bin/env python
"""
Quick system validation test.

Tests all components without requiring actual audio/keyboard input.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("🧪 System Validation Test")
print("=" * 60)

# Test 1: Configuration
print("\n1️⃣  Testing Configuration...")
try:
    from src.core.config import Config
    Config.validate()
    print("   ✅ Config OK")
except Exception as e:
    print(f"   ❌ Config failed: {e}")
    sys.exit(1)

# Test 2: Logging
print("\n2️⃣  Testing Logging...")
try:
    from src.utils.logger import setup_logger
    log = setup_logger("test")
    log.info("Test message")
    print("   ✅ Logging OK")
except Exception as e:
    print(f"   ❌ Logging failed: {e}")
    sys.exit(1)

# Test 3: Knowledge Base
print("\n3️⃣  Testing Knowledge Base...")
try:
    from src.knowledge.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    cards = kb.get_cards_for_character("ironclad")
    relics = kb.get_all_relics()
    print(f"   ✅ KB OK ({len(cards)} cards, {len(relics)} relics)")
except Exception as e:
    print(f"   ❌ KB failed: {e}")
    sys.exit(1)

# Test 4: Backup Manager
print("\n4️⃣  Testing Backup Manager...")
try:
    from src.core.backup_manager import BackupManager
    mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
    stats = mgr.get_backup_stats()
    print(f"   ✅ Backup Manager OK ({stats['total_backups']} backups)")
except Exception as e:
    print(f"   ❌ Backup Manager failed: {e}")
    sys.exit(1)

# Test 5: LLM Name Corrector
print("\n5️⃣  Testing LLM Name Corrector...")
try:
    from src.llm.name_corrector import NameCorrector
    corrector = NameCorrector(knowledge_base=kb)
    print(f"   ✅ Name Corrector OK (4 models: {len(corrector.models)})")
except Exception as e:
    print(f"   ❌ Name Corrector failed: {e}")
    sys.exit(1)

# Test 6: Transcriber
print("\n6️⃣  Testing Transcriber...")
try:
    from src.voice.transcriber import AudioTranscriber
    transcriber = AudioTranscriber()
    print(f"   ✅ Transcriber OK ({transcriber.primary_model})")
except Exception as e:
    print(f"   ❌ Transcriber failed: {e}")
    sys.exit(1)

# Test 7: TTS
print("\n7️⃣  Testing TTS...")
try:
    from src.voice.tts import SimpleTTS
    tts = SimpleTTS()
    print(f"   ✅ TTS OK (voice: {tts.voice})")
except Exception as e:
    print(f"   ❌ TTS failed: {e}")

# Test 8: Summary Generator
print("\n8️⃣  Testing Summary Generator...")
try:
    from src.summary.summary_generator import RunSummaryGenerator
    gen = RunSummaryGenerator(knowledge_base=kb)
    test_run = {
        "character": "WATCHER",
        "ascension": 3,
        "act": 1,
        "floor": 5,
        "current_hp": 66,
        "max_hp": 72,
        "gold": 117,
        "deck": ["Strike_P", "Defend_P", "Eruption"],
        "relics": ["PureWater"],
        "potions": ["Regen Potion"],
        "has_ruby_key": False,
        "has_emerald_key": False,
        "has_sapphire_key": False,
        "boss": "The Guardian",
        "seed": "TEST123"
    }
    summary = gen.generate_summary(test_run, None, preserve_choice=False)
    print(f"   ✅ Summary Generator OK ({len(summary)} chars)")
except Exception as e:
    print(f"   ❌ Summary Generator failed: {e}")
    sys.exit(1)

# Test 9: Choice Updater
print("\n9️⃣  Testing Choice Updater...")
try:
    from src.summary.choice_updater import ChoiceUpdater
    updater = ChoiceUpdater()
    print(f"   ✅ Choice Updater OK")
except Exception as e:
    print(f"   ❌ Choice Updater failed: {e}")
    sys.exit(1)

# Success!
print("\n" + "=" * 60)
print("✅ ALL SYSTEMS OPERATIONAL!")
print("=" * 60)
print("\nThe voice recorder is ready to use:")
print("  python scripts/voice_recorder.py")
print("\nMake sure:")
print("  1. You have an active run in Slay the Spire")
print("  2. Groq API key is set in .env")
print("  3. Run as Administrator (for keyboard module)")
