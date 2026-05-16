import os
import ctypes

# 1. Exact path to your compiled C++ DLL
dll_path = r"C:\Users\muham\OneDrive\Desktop\Trainer\GW2X_MAR_15\XXXX\Scripts\New folder\x64\Debug\kx-vision.dll"

gw2_dll = None

try:
    # 2. Load the DLL
    gw2_dll = ctypes.CDLL(dll_path)
    
    # 3. Define the function we exported in EntityExtractor.cpp
    # (Assuming you named the export 'TriggerMouseTeleport')
    gw2_dll.TriggerMouseTeleport.argtypes = []
    gw2_dll.TriggerMouseTeleport.restype = None
    print(f"[MouseTP] Successfully hooked C++ DLL: kx-vision.dll")
except OSError as e:
    # A common error here is Error 193: %1 is not a valid Win32 application.
    # This happens if your Python is 32-bit but the DLL is 64-bit.
    print(f"[MouseTP] Failed to load DLL! Check path or Python architecture.\nError: {e}")
except AttributeError as e:
    print(f"[MouseTP] DLL loaded, but couldn't find the exported function.\nError: {e}")
except Exception as e:
    print(f"[MouseTP] Unexpected error loading DLL: {e}")


# ===============================
# EXPORTED FUNCTION FOR LOGIC.PY
# ===============================

def on_mouse_teleport():
    """
    Called by gw2x_logic.py when you press the hotkey.
    Instantly triggers the C++ internal teleport.
    """
    if gw2_dll:
        # Tells the DLL to execute the TeleportToMouse() function instantly
        gw2_dll.TriggerMouseTeleport()
    else:
        print("[MouseTP] Cannot teleport. kx-vision.dll is not loaded.")

def reset_mouse_cache():
    """
    Kept so gw2x_logic.py doesn't crash when it tries to clear the cache.
    C++ handles resolution now, so this doesn't need to do anything.
    """
    pass