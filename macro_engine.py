"""
macro_engine.py - High-Reliability Input Simulation & Global Hotkey Engine for Roblox Chat Macro
Uses Windows GetAsyncKeyState for 100% reliable unfocused keybind detection,
Win32 keybd_event with hardware scan codes, and automatic Roblox focus detection.
"""

import time
import threading
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any, Callable, Optional
from pynput.keyboard import Controller as PynputController

# Win32 API functions & types
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Configure 64-bit ctypes for Windows Clipboard
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

# Virtual Key lookup table for Windows GetAsyncKeyState
VK_LOOKUP: Dict[str, int] = {
    # Function Keys
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    # Navigation & Editing
    "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22, "PRIOR": 0x21, "NEXT": 0x22,
    "TAB": 0x09, "SPACE": 0x20, "CAPSLOCK": 0x14,
    "TILDE": 0xC0, "`": 0xC0,
    # Numpad
    "NUM0": 0x60, "NUM1": 0x61, "NUM2": 0x62, "NUM3": 0x63, "NUM4": 0x64,
    "NUM5": 0x65, "NUM6": 0x66, "NUM7": 0x67, "NUM8": 0x68, "NUM9": 0x69,
    # Failsafe
    "ESC": 0x1B, "ESCAPE": 0x1B
}
# Add A-Z
for i in range(ord('A'), ord('Z') + 1):
    VK_LOOKUP[chr(i)] = i
# Add 0-9
for i in range(ord('0'), ord('9') + 1):
    VK_LOOKUP[chr(i)] = i


def get_vk_for_keyname(name: str) -> Optional[int]:
    """Returns the Windows Virtual-Key code for a given key string."""
    clean = name.strip().upper()
    return VK_LOOKUP.get(clean)


def set_windows_clipboard(text: str) -> bool:
    """Sets text into Windows clipboard using native Win32 API."""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    
    for _ in range(5):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.01)
    else:
        return False

    try:
        user32.EmptyClipboard()
        encoded = (text + '\0').encode('utf-16le')
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            return False
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def focus_roblox_window() -> bool:
    """Attempts to find and bring the Roblox game window to the foreground."""
    found_hwnd = []
    
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                # Roblox window title is typically "Roblox" or starts with "Roblox"
                if "roblox" in title and "chat macro" not in title:
                    found_hwnd.append(hwnd)
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    
    if found_hwnd:
        target = found_hwnd[0]
        # Show and bring window to front
        user32.ShowWindow(target, 9)  # SW_RESTORE
        user32.SetForegroundWindow(target)
        return True
    return False


def send_key_press(vk: int, delay_press_ms: int = 20):
    """Sends a key down and key up event using Win32 keybd_event with scan codes."""
    scan = user32.MapVirtualKeyW(vk, 0)
    user32.keybd_event(vk, scan, 0, 0)
    time.sleep(delay_press_ms / 1000.0)
    user32.keybd_event(vk, scan, 2, 0)  # KEYEVENTF_KEYUP = 2


def send_ctrl_v():
    """Sends Ctrl+V to paste clipboard contents."""
    VK_CONTROL = 0x11
    VK_V = 0x56
    scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
    scan_v = user32.MapVirtualKeyW(VK_V, 0)

    # Ctrl Down
    user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
    time.sleep(0.015)
    # V Down
    user32.keybd_event(VK_V, scan_v, 0, 0)
    time.sleep(0.02)
    # V Up
    user32.keybd_event(VK_V, scan_v, 2, 0)
    time.sleep(0.015)
    # Ctrl Up
    user32.keybd_event(VK_CONTROL, scan_ctrl, 2, 0)


class MacroEngine:
    def __init__(self, 
                 on_status_change: Optional[Callable[[bool, str], None]] = None,
                 on_progress: Optional[Callable[[int, int], None]] = None):
        self.on_status_change = on_status_change
        self.on_progress = on_progress
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self._toggle_lock = threading.Lock()
        
        # Pynput fallback controller for typing
        self.pynput_controller = PynputController()

        # Hotkey listener state
        self.current_hotkey_str = "F8"
        self.current_vk: int = 0x77  # Default VK_F8
        self._shutdown_event = threading.Event()
        self.request_start_callback: Optional[Callable[[], None]] = None

        # Start dedicated background listener using GetAsyncKeyState
        self._listener_thread = threading.Thread(target=self._hotkey_poll_loop, daemon=True)
        self._listener_thread.start()

    def set_hotkey(self, key_name: str) -> bool:
        """Sets the active trigger keybind name and resolves its Virtual-Key code."""
        vk = get_vk_for_keyname(key_name)
        if vk is not None:
            self.current_hotkey_str = key_name.upper()
            self.current_vk = vk
            return True
        return False

    def set_start_request_callback(self, callback: Callable[[], None]):
        """Sets callback invoked when hotkey triggers a start request."""
        self.request_start_callback = callback

    def _hotkey_poll_loop(self):
        """
        Dedicated polling thread querying GetAsyncKeyState directly from Windows kernel.
        Works 100% of the time, whether focused, tabbed out, playing Roblox, in fullscreen,
        without requiring administrator privileges and without brittle low-level hooks.
        """
        prev_hotkey_down = False
        prev_esc_down = False

        while not self._shutdown_event.is_set():
            # 1. Check Trigger Keybind
            vk = self.current_vk
            if vk:
                is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                if is_down and not prev_hotkey_down:
                    # Debounce / Edge detected: Key just pressed down
                    self.toggle_macro_from_hotkey()
                prev_hotkey_down = is_down

            # 2. Check ESC Emergency Stop
            is_esc_down = bool(user32.GetAsyncKeyState(0x1B) & 0x8000)  # VK_ESCAPE = 0x1B
            if is_esc_down and not prev_esc_down:
                if self.is_running:
                    self.stop("Emergency STOP: [ESC] Pressed")
            prev_esc_down = is_esc_down

            # 10ms polling interval = 100 checks/sec = instant reaction with near-zero CPU usage
            time.sleep(0.01)

    def toggle_macro_from_hotkey(self):
        """Called whenever the configured hotkey is pressed."""
        with self._toggle_lock:
            if self.is_running:
                self.stop("Stopped by keybind")
            else:
                if self.request_start_callback:
                    self.request_start_callback()

    def start(self, 
              messages: List[str], 
              intervals_ms: List[int], 
              chat_key: str = "/", 
              focus_delay_ms: int = 70, 
              send_method: str = "clipboard", 
              loop_mode: str = "once", 
              repeat_count: int = 1,
              initial_delay_ms: int = 150) -> bool:
        """Starts macro execution in a dedicated worker thread."""
        with self._toggle_lock:
            if self.is_running:
                return False

            if not messages:
                if self.on_status_change:
                    self.on_status_change(False, "No messages queued to send.")
                return False

            self.stop_event.clear()
            self.is_running = True
            
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(messages, intervals_ms, chat_key, focus_delay_ms, send_method, loop_mode, repeat_count, initial_delay_ms),
                daemon=True
            )
            self.worker_thread.start()
            
            if self.on_status_change:
                self.on_status_change(True, f"Running [{self.current_hotkey_str} or ESC to Stop]")
            return True

    def stop(self, reason: str = "Stopped"):
        """Signals worker thread to abort immediately."""
        self.stop_event.set()
        self.is_running = False
        if self.on_status_change:
            self.on_status_change(False, reason)

    def shutdown(self):
        """Stops all threads upon program exit."""
        self.stop("Exiting")
        self._shutdown_event.set()

    def _interruptible_sleep(self, duration_ms: int) -> bool:
        """Sleeps in 10ms slices; returns False if stopped."""
        slices = max(1, int(duration_ms / 10))
        for _ in range(slices):
            if self.stop_event.is_set():
                return False
            time.sleep(0.01)
        return not self.stop_event.is_set()

    def _worker_loop(self, 
                     messages: List[str], 
                     intervals_ms: List[int], 
                     chat_key: str, 
                     focus_delay_ms: int, 
                     send_method: str, 
                     loop_mode: str, 
                     repeat_count: int,
                     initial_delay_ms: int):
        """Worker thread executing macro chat sequence."""
        total_messages = len(messages)
        cycle = 0

        # Wait for key release / countdown
        if not self._interruptible_sleep(initial_delay_ms):
            self.stop("Aborted")
            return

        # Determine virtual key code for chat activation key
        chat_vk = 0xBF  # Default VK_OEM_2 for '/'
        if chat_key != "/":
            custom_vk = get_vk_for_keyname(chat_key)
            if custom_vk is not None:
                chat_vk = custom_vk

        VK_RETURN = 0x0D

        while not self.stop_event.is_set():
            cycle += 1
            
            for idx, msg in enumerate(messages):
                if self.stop_event.is_set():
                    break

                text = msg.strip()
                if not text:
                    continue

                if self.on_progress:
                    self.on_progress(idx + 1, total_messages)

                # Step 1: Open Roblox Chat (press chat key)
                send_key_press(chat_vk, delay_press_ms=25)

                # Step 2: Wait for Roblox chat box to open and receive focus
                if not self._interruptible_sleep(max(40, focus_delay_ms)):
                    break

                # Step 3: Type or Paste the Message
                if send_method == "clipboard":
                    if set_windows_clipboard(text):
                        time.sleep(0.015)
                        send_ctrl_v()
                        time.sleep(0.02)
                    else:
                        # Fallback to direct typing
                        self.pynput_controller.type(text)
                else:
                    self.pynput_controller.type(text)

                # Step 4: Small delay before Enter
                if not self._interruptible_sleep(30):
                    break

                # Step 5: Press Enter to submit
                send_key_press(VK_RETURN, delay_press_ms=25)

                # Step 6: Wait interval before next message
                interval_ms = intervals_ms[idx] if idx < len(intervals_ms) else 1000
                if not self._interruptible_sleep(max(10, interval_ms)):
                    break

            # Check loop criteria
            if self.stop_event.is_set():
                break

            if loop_mode == "once":
                break
            elif loop_mode == "repeat":
                if cycle >= repeat_count:
                    break
            # continuous runs until stopped

        self.is_running = False
        if not self.stop_event.is_set():
            if self.on_status_change:
                self.on_status_change(False, "Completed successfully")
