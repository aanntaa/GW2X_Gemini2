import ctypes
import time
from ctypes import wintypes

# Konfigurasi SendInput untuk DirectX (Scan Codes)
user32 = ctypes.windll.user32
INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", KEYBDINPUT),
        ("padding", ctypes.c_ubyte * 8)
    ]

def _send_input(scan_code, flags):
    # Pastikan scan_code adalah integer. Jika string hex (misal "2F"), convert dulu.
    if isinstance(scan_code, str): 
        try:
            scan_code = int(scan_code, 16)
        except ValueError:
            print(f"[Driver] Error: Invalid Scancode '{scan_code}'")
            return

    ii = INPUT()
    ii.type = INPUT_KEYBOARD
    # wVk harus 0 jika kita menggunakan Scan Codes
    ii.ki = KEYBDINPUT(0, scan_code, KEYEVENTF_SCANCODE | flags, 0, 0)
    user32.SendInput(1, ctypes.byref(ii), ctypes.sizeof(ii))

# --- FUNGSI UTAMA ---

def key_down(key): 
    """Menahan tombol. Argumen 'win' dihapus/diabaikan di layer atas."""
    _send_input(key, 0)

def key_up(key):
    """Melepas tombol."""
    _send_input(key, KEYEVENTF_KEYUP)

def press(key, duration=0.05):
    """Tekan tombol dengan durasi tertentu."""
    key_down(key)
    time.sleep(duration)
    key_up(key)