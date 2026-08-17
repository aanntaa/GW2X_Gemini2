import mmap
import struct
import time

NAME = "GW2X_KEYBOARD_PROBE"
SIZE = 104

MAGIC = 0x504B3247
VERSION = 1

O = {
    "magic": 0, "version": 4, "ready": 8,
    "async_total": 16, "async_gw2": 24,
    "keystate_total": 32, "keystate_gw2": 40,
    "keyboardstate_total": 48, "keyboardstate_gw2": 56,
    "peek_total": 64, "peek_gw2": 72,
    "last_async_vk": 80, "last_async_result": 84,
    "last_keystate_vk": 88, "last_keystate_result": 92,
    "last_msg": 96, "last_msg_wparam": 100,
}

_mm = None

def connect():
    global _mm
    if _mm is not None:
        return True
    try:
        _mm = mmap.mmap(-1, SIZE, tagname=NAME, access=mmap.ACCESS_WRITE)
        return True
    except Exception as e:
        print("connect failed:", e)
        return False

def u32(off):
    return struct.unpack_from("<I", _mm, off)[0]

def i32(off):
    return struct.unpack_from("<i", _mm, off)[0]

def u64(off):
    return struct.unpack_from("<Q", _mm, off)[0]

def snap():
    if not connect():
        return None
    return {
        "ready": u32(O["ready"]),
        "async.total": u64(O["async_total"]),
        "async.GW2": u64(O["async_gw2"]),
        "GetKeyState.total": u64(O["keystate_total"]),
        "GetKeyState.GW2": u64(O["keystate_gw2"]),
        "GetKeyboardState.total": u64(O["keyboardstate_total"]),
        "GetKeyboardState.GW2": u64(O["keyboardstate_gw2"]),
        "PeekMessage.total": u64(O["peek_total"]),
        "PeekMessage.GW2": u64(O["peek_gw2"]),
        "lastAsyncVK": hex(u32(O["last_async_vk"])),
        "lastAsyncResult": hex(i32(O["last_async_result"]) & 0xFFFF),
        "lastGetKeyStateVK": hex(u32(O["last_keystate_vk"])),
        "lastGetKeyStateResult": hex(i32(O["last_keystate_result"]) & 0xFFFF),
        "lastMsg": hex(u32(O["last_msg"])),
        "lastMsgWParam": hex(u32(O["last_msg_wparam"])),
    }

def diff(a,b):
    ks = [
        "async.total","async.GW2",
        "GetKeyState.total","GetKeyState.GW2",
        "GetKeyboardState.total","GetKeyboardState.GW2",
        "PeekMessage.total","PeekMessage.GW2"
    ]
    return {k:b[k]-a[k] for k in ks}

print("=== GW2X KEYBOARD API PROBE ===")
print("initial:", snap())

print("\nFOCUSED TEST: for 5 sec press 1, 8 and 0 repeatedly. Avoid moving mouse.")
a=snap()
time.sleep(5)
b=snap()
print("focused delta:", diff(a,b))
print("focused final:", b)

print("\nALT-TAB now. Waiting 3 sec...")
time.sleep(3)

print("UNFOCUSED TEST: for 5 sec type ordinary keys in the other app.")
a=snap()
time.sleep(5)
b=snap()
print("unfocused delta:", diff(a,b))
print("unfocused final:", b)
