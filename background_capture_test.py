"""
Background capture test harness for Slay the Spire.

This script does not interfere with the working helper flow. Press F3 while the
game is in the background to try several window capture backends and save the
results for inspection.
"""

import ctypes
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import keyboard
import win32con
import win32gui
import win32ui
from PIL import Image, ImageStat

from src.core.config import Config


@dataclass
class CaptureResult:
    backend: str
    image: Image.Image
    stats: str


def find_slay_the_spire_window():
    """Find the actual Slay the Spire top-level window."""
    browser_classes = {
        "Chrome_WidgetWin_1",
        "MozillaWindowClass",
        "ApplicationFrameWindow",
    }

    exact_matches = []
    partial_matches = []

    def callback(hwnd, windows):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True

        title_lower = title.strip().lower()
        class_name = win32gui.GetClassName(hwnd)

        if title_lower == "slay the spire":
            exact_matches.append((hwnd, title, class_name))
        elif "slay the spire" in title_lower and class_name not in browser_classes:
            partial_matches.append((hwnd, title, class_name))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)

    if exact_matches:
        return exact_matches[0]
    if partial_matches:
        return partial_matches[0]
    return None, None, None


def get_window_metrics(hwnd):
    """Get window and client geometry in screen coordinates."""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    client_rect = win32gui.GetClientRect(hwnd)
    client_left_top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
    client_right_bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))

    return {
        "window": (left, top, right, bottom),
        "client_screen": (
            client_left_top[0],
            client_left_top[1],
            client_right_bottom[0],
            client_right_bottom[1],
        ),
        "client_offset": (
            max(client_left_top[0] - left, 0),
            max(client_left_top[1] - top, 0),
            min(client_right_bottom[0] - left, right - left),
            min(client_right_bottom[1] - top, bottom - top),
        ),
    }


def crop_to_client(image: Image.Image, metrics) -> Image.Image:
    """Crop a window capture down to its client area when possible."""
    crop_left, crop_top, crop_right, crop_bottom = metrics["client_offset"]
    if crop_right > crop_left and crop_bottom > crop_top:
        return image.crop((crop_left, crop_top, crop_right, crop_bottom))
    return image


def compute_stats(image: Image.Image) -> str:
    """Compute lightweight image diagnostics for terminal output."""
    rgb_image = image.convert("RGB")
    stat = ImageStat.Stat(rgb_image)
    mean = tuple(round(value, 1) for value in stat.mean)
    extrema = stat.extrema
    grayscale = rgb_image.convert("L")
    gray_stat = ImageStat.Stat(grayscale)
    stddev = round(gray_stat.stddev[0], 2)
    return f"size={rgb_image.size}, mean={mean}, gray_stddev={stddev}, extrema={extrema}"


def image_from_bitmap(bitmap) -> Image.Image:
    """Convert a pywin32 bitmap into a Pillow image."""
    info = bitmap.GetInfo()
    raw = bitmap.GetBitmapBits(True)
    return Image.frombuffer(
        "RGB",
        (info["bmWidth"], info["bmHeight"]),
        raw,
        "raw",
        "BGRX",
        0,
        1,
    )


def capture_with_dc(hwnd, width: int, height: int, source_dc_handle: int) -> Image.Image:
    """Capture pixels from a device context using BitBlt."""
    src_dc = win32ui.CreateDCFromHandle(source_dc_handle)
    mem_dc = src_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()

    try:
        bitmap.CreateCompatibleBitmap(src_dc, width, height)
        mem_dc.SelectObject(bitmap)
        mem_dc.BitBlt((0, 0), (width, height), src_dc, (0, 0), win32con.SRCCOPY)
        return image_from_bitmap(bitmap)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        mem_dc.DeleteDC()
        src_dc.DeleteDC()


def backend_printwindow(hwnd, metrics, flags: int) -> Image.Image:
    """Capture the window using PrintWindow with a specific flag."""
    left, top, right, bottom = metrics["window"]
    width = right - left
    height = bottom - top

    window_dc = win32gui.GetWindowDC(hwnd)
    src_dc = win32ui.CreateDCFromHandle(window_dc)
    mem_dc = src_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()

    try:
        bitmap.CreateCompatibleBitmap(src_dc, width, height)
        mem_dc.SelectObject(bitmap)
        result = ctypes.windll.user32.PrintWindow(hwnd, mem_dc.GetSafeHdc(), flags)
        if result != 1:
            raise RuntimeError(f"PrintWindow failed with flags={flags}")
        image = image_from_bitmap(bitmap)
        return crop_to_client(image, metrics)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        mem_dc.DeleteDC()
        src_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)


def backend_printwindow_full(hwnd, metrics) -> Image.Image:
    return backend_printwindow(hwnd, metrics, 2)


def backend_printwindow_basic(hwnd, metrics) -> Image.Image:
    return backend_printwindow(hwnd, metrics, 0)


def backend_window_dc(hwnd, metrics) -> Image.Image:
    """Capture the full window DC and crop to the client area."""
    left, top, right, bottom = metrics["window"]
    width = right - left
    height = bottom - top
    window_dc = win32gui.GetWindowDC(hwnd)
    try:
        image = capture_with_dc(hwnd, width, height, window_dc)
        return crop_to_client(image, metrics)
    finally:
        win32gui.ReleaseDC(hwnd, window_dc)


def backend_client_dc(hwnd, metrics) -> Image.Image:
    """Capture the client DC directly."""
    client_left, client_top, client_right, client_bottom = metrics["client_screen"]
    width = client_right - client_left
    height = client_bottom - client_top
    client_dc = win32gui.GetDC(hwnd)
    try:
        return capture_with_dc(hwnd, width, height, client_dc)
    finally:
        win32gui.ReleaseDC(hwnd, client_dc)


BACKENDS: list[tuple[str, Callable]] = [
    ("printwindow_full", backend_printwindow_full),
    ("printwindow_basic", backend_printwindow_basic),
    ("window_dc", backend_window_dc),
    ("client_dc", backend_client_dc),
]


def run_capture_test(output_dir: Path):
    """Run all background capture backends and save results."""
    hwnd, title, class_name = find_slay_the_spire_window()
    if not hwnd:
        print("Slay the Spire window not found.")
        return

    metrics = get_window_metrics(hwnd)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = output_dir / f"capture_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    print(f"Testing background capture against: {title} [{class_name}]")
    print(f"Saving outputs to: {batch_dir}")

    for backend_name, backend in BACKENDS:
        try:
            image = backend(hwnd, metrics)
            stats = compute_stats(image)
            output_path = batch_dir / f"{backend_name}.png"
            image.save(output_path)
            print(f"  OK   {backend_name}: {stats}")
            print(f"       saved -> {output_path}")
        except Exception as exc:
            print(f"  FAIL {backend_name}: {exc}")

    print("Capture batch complete.")


def main():
    """Run the test harness until ESC is pressed."""
    output_dir = Config.PROCESSED_DIR / "background_capture_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Slay the Spire Background Capture Test")
    print("=" * 60)
    print("F3  Run all background capture backends and save PNGs")
    print("ESC Exit")
    print()
    print("Use this while Slay the Spire stays in the background.")
    print(f"Outputs are written under: {output_dir}")
    print()

    try:
        f3_was_pressed = False
        while True:
            if keyboard.is_pressed("esc"):
                break

            f3_pressed = keyboard.is_pressed("f3")
            if f3_pressed and not f3_was_pressed:
                run_capture_test(output_dir)
                f3_was_pressed = True
            elif not f3_pressed:
                f3_was_pressed = False

            time.sleep(0.05)
    except KeyboardInterrupt:
        pass

    print("Exiting background capture test.")


if __name__ == "__main__":
    main()