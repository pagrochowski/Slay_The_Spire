"""
Standalone helper for relic voice capture and image paste.

Workflow:
1. Focus Slay the Spire.
2. Hold F1 to record relic names from the current reward screen.
3. Focus the target LLM chat input.
4. Press F2 to capture the game window and paste the image only.
5. Press ESC to exit.
"""

import io
import ctypes
import threading
import time
from datetime import datetime
from pathlib import Path

import keyboard
import win32clipboard
import win32con
import win32gui
import win32ui
from PIL import Image, ImageGrab
from spireslayer.editor import Editor

from src.choice.choice_persistence import ChoicePersistence
from src.core.backup_manager import BackupManager
from src.core.config import Config
from src.core.save_parser import SaveParser
from src.knowledge.knowledge_base import KnowledgeBase
from src.llm.name_corrector import NameCorrector
from src.summary.summary_generator import RunSummaryGenerator
from src.voice.transcriber import AudioTranscriber
from src.voice.voice_recorder import VoiceRecorder


_execution_lock = threading.Lock()
_is_processing = False
_is_recording = False


def find_slay_the_spire_window():
    """Find the Slay the Spire window handle and title."""

    browser_classes = {
        "Chrome_WidgetWin_1",
        "MozillaWindowClass",
        "ApplicationFrameWindow",
    }

    exact_matches = []
    partial_matches = []

    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True

            title_lower = title.strip().lower()
            class_name = win32gui.GetClassName(hwnd)

            if title_lower == "slay the spire":
                exact_matches.append((hwnd, title))
            elif "slay the spire" in title_lower and class_name not in browser_classes:
                partial_matches.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)

    if exact_matches:
        return exact_matches[0]
    if partial_matches:
        return partial_matches[0]
    return None, None


def capture_game_window(hwnd) -> Image.Image:
    """Capture the Slay the Spire client area from the visible screen."""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    full_screen = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)

    client_rect = win32gui.GetClientRect(hwnd)
    client_left_top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
    client_right_bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))

    crop_left = max(client_left_top[0] - left, 0)
    crop_top = max(client_left_top[1] - top, 0)
    crop_right = min(client_right_bottom[0] - left, right - left)
    crop_bottom = min(client_right_bottom[1] - top, bottom - top)

    if crop_right > crop_left and crop_bottom > crop_top:
        return full_screen.crop((crop_left, crop_top, crop_right, crop_bottom))

    return full_screen


def activate_window(hwnd):
    """Bring a window to the foreground if possible."""
    if not hwnd:
        return

    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def capture_visible_game_window(hwnd, previous_hwnd) -> Image.Image:
    """Activate the game window, capture it from screen, then restore the previous window."""
    activate_window(hwnd)
    time.sleep(0.25)

    screenshot = capture_game_window(hwnd)

    if previous_hwnd and win32gui.IsWindow(previous_hwnd):
        activate_window(previous_hwnd)
        time.sleep(0.15)

    return screenshot


def copy_image_to_clipboard(image: Image.Image):
    """Copy a Pillow image into the Windows clipboard as CF_DIB."""
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()

    max_retries = 5
    for attempt in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()
            return
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.05)


def get_current_run_data():
    """Load and parse the latest autosave into run data."""
    backup_manager = BackupManager(Config.GAME_SAVES_DIR, Config.BACKUP_DIR)
    autosave_path = backup_manager.find_latest_autosave()
    if not autosave_path:
        return None

    editor = Editor(autosave_path=str(autosave_path))
    save_data = editor.decoded
    parser = SaveParser()
    return parser.extract_run_data(save_data, save_filename=Path(autosave_path).name)


def refresh_run_summary(run_data=None) -> bool:
    """Regenerate Run_Summary.md from the latest autosave."""
    try:
        if run_data is None:
            run_data = get_current_run_data()
        if not run_data:
            print("No autosave found. Using existing Run_Summary.md.")
            return False

        generator = RunSummaryGenerator()
        generator.generate_summary(
            run_data,
            output_path=Config.RUN_SUMMARY_PATH,
            preserve_choice=False,
        )
        return True
    except Exception as exc:
        print(f"Warning: failed to refresh Run_Summary.md: {exc}")
        return False


def record_relic_choices():
    """Record relic names on F1 and persist them to the current choice file."""
    global _is_recording

    if _is_recording:
        print("Already recording; ignoring duplicate F1 press.")
        return

    _is_recording = True
    try:
        print("Recording relic names...")
        recorder = VoiceRecorder(hotkey="f1")
        transcriber = AudioTranscriber()
        knowledge_base = KnowledgeBase()
        corrector = NameCorrector(knowledge_base=knowledge_base)
        choice_persistence = ChoicePersistence()

        audio_path = Config.PROCESSED_DIR / f"relic_choice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        if not recorder.record_to_file(audio_path, wait_for_hotkey=False):
            print("No audio captured.")
            return

        transcribed_text = transcriber.transcribe_audio(audio_path)
        if not transcribed_text:
            print("Transcription failed.")
            return

        print(f"Heard: {transcribed_text}")

        run_data = get_current_run_data()
        if not run_data:
            print("Could not load the current run data.")
            return

        relics = corrector.correct_relic_names(transcribed_text)
        if not relics:
            print("No relic names matched the existing knowledge base.")
            return

        choice_persistence.save_choice(
            floor=run_data.get("floor", 0),
            act=run_data.get("act", 1),
            cards=[],
            relics=relics,
        )
        refresh_run_summary(run_data=run_data)
        print(f"Saved relic choices: {', '.join(relics)}")
    except Exception as exc:
        print(f"Error while recording relic choices: {exc}")
    finally:
        _is_recording = False


def paste_screenshot(screenshot: Image.Image):
    """Paste the screenshot into the currently focused chat input."""
    print("Pasting screenshot in 1.5 seconds.")
    time.sleep(1.5)

    copy_image_to_clipboard(screenshot)
    keyboard.press_and_release("ctrl+v")


def handle_image_paste():
    """Capture the game window and paste the image into the focused chat."""
    global _is_processing

    if _is_processing:
        print("Already processing; ignoring duplicate F2 press.")
        return

    with _execution_lock:
        if _is_processing:
            return
        _is_processing = True

    try:
        previous_hwnd = win32gui.GetForegroundWindow()
        hwnd, title = find_slay_the_spire_window()
        if not hwnd:
            print("Slay the Spire window was not found.")
            return

        print(f"Capturing window: {title}")
        screenshot = capture_visible_game_window(hwnd, previous_hwnd)
        paste_screenshot(screenshot)
        print("Screenshot pasted.")
    except Exception as exc:
        print(f"Error while pasting image: {exc}")
    finally:
        _is_processing = False


def main():
    """Run the helper loop until ESC is pressed."""
    Config.create_directories()

    print("=" * 60)
    print("Slay the Spire Relic Helper")
    print("=" * 60)
    print("F1  Hold to record relic choices from the current reward screen")
    print("F2  Capture the game window and paste the screenshot only")
    print("ESC Exit")
    print()
    print("Keep the target LLM chat input focused before pressing F2.")
    print()

    try:
        f1_was_pressed = False
        f2_was_pressed = False

        while True:
            if keyboard.is_pressed("esc"):
                break

            f1_pressed = keyboard.is_pressed("f1")
            if f1_pressed and not f1_was_pressed:
                record_relic_choices()
                f1_was_pressed = True
            elif not f1_pressed:
                f1_was_pressed = False

            f2_pressed = keyboard.is_pressed("f2")
            if f2_pressed and not f2_was_pressed:
                handle_image_paste()
                f2_was_pressed = True
            elif not f2_pressed:
                f2_was_pressed = False

            time.sleep(0.05)
    except KeyboardInterrupt:
        pass

    print("Exiting helper.")


if __name__ == "__main__":
    main()