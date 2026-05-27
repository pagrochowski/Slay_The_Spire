"""
Slay The Spire Screenshot + Summary Auto-Paste Tool

Workflow:
1. Make sure Slay The Spire is running
2. Click in your chat application input box (ChatGPT/Claude)
3. Press F1 to record voice choices (cards/relics)
4. Press F2 to take screenshot + paste
5. Script automatically:
   - Takes screenshot of game window
   - Regenerates Run_Summary.md from latest autosave
   - Pastes screenshot + text summary
"""

import io
import time
import ctypes
import threading
from pathlib import Path
import win32clipboard
import win32gui
import win32ui
import win32con
from PIL import Image
import keyboard
import pyperclip

# Import our modules for refreshing summary
from spireslayer.editor import Editor
from src.core.save_parser import SaveParser
from src.summary.summary_generator import RunSummaryGenerator
from src.core.config import Config
from src.core.backup_manager import BackupManager
from src.voice.voice_recorder import VoiceRecorder
from src.voice.transcriber import AudioTranscriber
from src.llm.name_corrector import NameCorrector
from src.choice.choice_persistence import ChoicePersistence
from src.knowledge.knowledge_base import KnowledgeBase
from datetime import datetime

# Lock to prevent concurrent executions
_execution_lock = threading.Lock()
_is_processing = False
_is_recording = False


def find_slay_the_spire_window():
    """Find the Slay The Spire window handle."""
    
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and "slay the spire" in title.lower():
                windows.append((hwnd, title))
        return True
    
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if windows:
        hwnd, title = windows[0]
        return hwnd, title
    
    return None, None


def screenshot_game_window(hwnd):
    """
    Take a screenshot of a specific window by cropping from full screen.
    Most reliable method for games.
    """
    
    # Get window position and size on screen
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    
    print(f"   📐 Window: {width}x{height} at ({left}, {top})")
    
    # Take full screen screenshot
    full_screen = ImageGrab.grab()
    
    # Crop to window area
    screenshot = full_screen.crop((left, top, right, bottom))
    
    print(f"   ✅ Cropped to game window")
    
    return screenshot


def read_run_summary() -> str:
    """Read the Run_Summary.md file."""
    summary_path = Path("Run_Summary.md")
    if not summary_path.exists():
        return "⚠️ Run_Summary.md not found!"
    
    return summary_path.read_text(encoding='utf-8')


def refresh_run_summary():
    """Refresh Run_Summary.md from the latest autosave."""
    try:
        print("      🔍 Getting latest autosave...")
        # Get latest autosave
        backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
        autosave_path = backup_mgr.find_latest_autosave()
        
        if not autosave_path:
            print("      ❌ No autosave found!")
            return False
            
        print(f"      📁 Autosave: {Path(autosave_path).name}")
        
        print("      📖 Loading save file...")
        # Load save file (must use autosave_path= named parameter!)
        editor = Editor(autosave_path=str(autosave_path))
        save_data = editor.decoded
        
        print("      🔧 Parsing run data...")
        # Parse run data (pass filename to extract character name)
        parser = SaveParser()
        run_data = parser.extract_run_data(save_data, save_filename=Path(autosave_path).name)
        
        print("      📝 Generating summary...")
        # Generate summary (don't preserve choice - always regenerate with latest voice choices)
        generator = RunSummaryGenerator()
        generator.generate_summary(run_data, output_path=Path('Run_Summary.md'), preserve_choice=False)
        
        print("      💾 Run_Summary.md regenerated!")
        return True
    except Exception as e:
        print(f"   ⚠️ Warning: Could not refresh summary: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_voice_input():
    """Record and process voice input for choices."""
    global _is_recording
    
    if _is_recording:
        print("\n⏭️ Already recording - ignoring")
        return
    
    _is_recording = True
    
    try:
        print("\n🔄 Recording voice choice...")
        
        # Initialize components
        recorder = VoiceRecorder(hotkey='f1')
        transcriber = AudioTranscriber()
        kb = KnowledgeBase()
        corrector = NameCorrector(knowledge_base=kb)
        choice_persist = ChoicePersistence()
        
        # Record to temp file
        temp_audio_path = Config.PROCESSED_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        if not recorder.record_to_file(temp_audio_path):
            print("   ❌ Recording failed")
            return
        
        # Transcribe
        text = transcriber.transcribe_audio(temp_audio_path)
        
        if not text:
            print("   ❌ Transcription failed")
            return
        
        print(f"\n📝 You said: \"{text}\"")
        
        # Get current floor/act from save
        print("\n💾 Getting current floor from save...")
        backup_mgr = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
        autosave_path = backup_mgr.find_latest_autosave()
        
        if not autosave_path:
            print("   ❌ No autosave found - cannot track floor")
            return
        
        editor = Editor(autosave_path=str(autosave_path))
        save_data = editor.decoded
        parser = SaveParser()
        run_data = parser.extract_run_data(save_data, save_filename=Path(autosave_path).name)
        
        current_floor = run_data.get('floor', 0)
        current_act = run_data.get('act', 1)
        character = run_data.get('character', 'IRONCLAD').lower()
        
        print(f"   ✅ Current position: Act {current_act}, Floor {current_floor}, Character: {character.upper()}")
        
        # Correct names using LLM
        print("🔧 Correcting names with LLM...")
        cards, relics = corrector.correct_names(
            text,
            character,
            include_relics=True
        )
        
        print(f"   ✅ Found {len(cards)} cards, {len(relics)} relics")
        if cards:
            print(f"      Cards: {', '.join(cards)}")
        if relics:
            print(f"      Relics: {', '.join(relics)}")
        
        # Save choice
        print("\n💾 Saving choice...")
        choice_persist.save_choice(
            floor=current_floor,
            act=current_act,
            cards=cards,
            relics=relics
        )
        
        print("   ✅ Choice saved!")
        
        # Immediately update the summary to show the voice choices
        print("\n📋 Updating Run_Summary.md with voice choices...")
        refresh_run_summary()
        print("   ✅ Summary updated! Voice choices now visible in Run_Summary.md")
        print()
        
    except Exception as e:
        print(f"   ❌ Error processing voice: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _is_recording = False


def copy_image_to_clipboard(image: Image.Image):
    """Copy image to clipboard with retry logic."""
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()
    
    # Retry logic for clipboard access
    max_retries = 5
    for attempt in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()
            return  # Success!
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.05)  # Wait 50ms before retry
            else:
                raise  # Re-raise on final attempt


def auto_paste_both(screenshot: Image.Image, text: str):
    """Automatically paste both screenshot and text."""
    
    print("\n🤖 Auto-pasting in 1.5 seconds...")
    print("   >>> MAKE SURE CURSOR IS IN CHAT INPUT BOX! <<<")
    time.sleep(1.5)
    
    # 1. Copy screenshot to clipboard
    print("   📸 [STEP 1] Copying screenshot to clipboard...")
    copy_image_to_clipboard(screenshot)
    print("   ✅ Screenshot copied")
    time.sleep(0.2)
    
    # 2. Paste screenshot with Ctrl+V
    print("   📋 [STEP 2] Pasting screenshot with Ctrl+V...")
    keyboard.press_and_release('ctrl+v')
    print("   ✅ Screenshot pasted")
    time.sleep(0.5)  # Wait for screenshot to paste
    
    # 3. Copy text to clipboard
    print("   📝 [STEP 3] Copying text to clipboard...")
    pyperclip.copy(text)
    print(f"   ✅ Text copied to clipboard ({len(text)} chars)")
    time.sleep(0.2)
    
    # 4. Paste text with Ctrl+V
    print("   📋 [STEP 4] Pasting text with Ctrl+V...")
    keyboard.press_and_release('ctrl+v')
    print("   ✅ Text pasted")
    time.sleep(0.3)
    
    print("\n✅ Done! Screenshot + summary pasted to chat.")



def on_trigger():
    """Handle the trigger event (F2)."""
    global _is_processing
    
    # Prevent concurrent executions
    if _is_processing:
        print("\n⏭️ Already processing - ignoring duplicate trigger")
        return
    
    with _execution_lock:
        if _is_processing:
            return
        _is_processing = True
    
    try:
        print("\n" + "=" * 60)
        print("🎮 F2 detected! Processing...")
        print("=" * 60)
        
        # 1. Find game window
        print("\n1️⃣ Finding Slay The Spire window...")
        hwnd, title = find_slay_the_spire_window()
        
        if not hwnd:
            print("   ❌ Game window not found!")
            print("   Make sure Slay The Spire is running.")
            return
        
        print(f"   ✅ Found: '{title}' (handle: {hwnd})")
        
        # 2. Take screenshot
        print("\n2️⃣ Taking screenshot of game...")
        try:
            screenshot = screenshot_game_window(hwnd)
            print(f"   ✅ Screenshot captured ({screenshot.size[0]}x{screenshot.size[1]})")
        except Exception as e:
            print(f"   ❌ Screenshot failed: {e}")
            return
        
        # 3. Refresh Run_Summary.md from latest autosave
        print("\n3️⃣ Regenerating Run_Summary.md from latest autosave...")
        if refresh_run_summary():
            print("   ✅ Summary refreshed with latest game data")
        else:
            print("   ⚠️ Using existing summary (refresh failed)")
        
        # 4. Read summary
        print("\n4️⃣ Reading Run_Summary.md...")
        summary_text = read_run_summary()
        print(f"   ✅ Summary loaded ({len(summary_text)} chars)")
        
        # 5. Auto-paste both
        print("\n5️⃣ Auto-pasting to chat...")
        auto_paste_both(screenshot, summary_text)
        
        print("\n" + "=" * 60)
    
    finally:
        # Always reset the processing flag
        _is_processing = False


def main():
    """Main program loop."""
    print("=" * 60)
    print("🎮 Slay The Spire Screenshot + Summary Tool")
    print("=" * 60)
    print()
    print("📋 Instructions:")
    print("   1. Make sure Slay The Spire is running")
    print("   2. Open your chat (ChatGPT/Claude) in browser")
    print("   3. Press and hold F1 to record voice choices (optional)")
    print("   4. Click in chat input box and press F2 to paste")
    print()
    print("🔧 Controls:")
    print("   F1  = Press and hold to record choices (relics/cards)")
    print("   F2  = Screenshot + paste to chat")
    print("   ESC = Exit program")
    print()
    print("✅ Ready! Press F1 to record choices or F2 to paste.")
    print("=" * 60)
    print()
    
    # Main loop - check for key presses (pure loop like old script)
    try:
        print("🔄 Main loop started - waiting for F1, F2, or ESC...")
        f1_was_pressed = False
        f2_was_pressed = False
        
        while True:
            # Check for exit
            if keyboard.is_pressed('esc'):
                break
            
            # Check for F1 - process voice input (prevent repeat triggers)
            f1_pressed = keyboard.is_pressed('f1')
            if f1_pressed and not f1_was_pressed:
                print("🎤 F1 detected! Starting voice recording...")
                process_voice_input()
                f1_was_pressed = True
            elif not f1_pressed:
                f1_was_pressed = False
            
            # Check for F2 - screenshot and paste (prevent repeat triggers)
            f2_pressed = keyboard.is_pressed('f2')
            if f2_pressed and not f2_was_pressed:
                print("📸 F2 detected! Starting screenshot...")
                on_trigger()
                f2_was_pressed = True
            elif not f2_pressed:
                f2_was_pressed = False
            
            # Small delay to avoid CPU spinning
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        pass
    
    print("\n👋 Exiting...")


if __name__ == "__main__":
    main()
