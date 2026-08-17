import mmap
import struct
import time

NAME = "GW2X_INPUT_PROBE"
SIZE = 120

MAGIC = 0x50523247
VERSION = 1

OFF = {
    "magic": 0,
    "version": 4,
    "ready": 8,

    "data_total": 16,
    "data_gw2": 24,
    "data_trainer": 32,

    "buffer_total": 40,
    "buffer_gw2": 48,
    "buffer_trainer": 56,

    "kb_gw2": 64,
    "kb_trainer": 72,

    "last_type": 80,
    "last_vkey": 84,
    "last_make": 88,
    "last_flags": 92,

    "last_gw2_caller": 96,
    "last_trainer_caller": 104,
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
        print("[RawProbe] connect failed:", e)
        return False


def u32(off):
    return struct.unpack_from("<I", _mm, off)[0]


def u64(off):
    return struct.unpack_from("<Q", _mm, off)[0]


def snapshot():
    if not connect():
        return None

    return {
        "magic_ok": u32(OFF["magic"]) == MAGIC,
        "version": u32(OFF["version"]),
        "ready": u32(OFF["ready"]),

        "GetRawInputData.total": u64(OFF["data_total"]),
        "GetRawInputData.GW2": u64(OFF["data_gw2"]),
        "GetRawInputData.trainer": u64(OFF["data_trainer"]),

        "GetRawInputBuffer.total": u64(OFF["buffer_total"]),
        "GetRawInputBuffer.GW2": u64(OFF["buffer_gw2"]),
        "GetRawInputBuffer.trainer": u64(OFF["buffer_trainer"]),

        "keyboard.GW2": u64(OFF["kb_gw2"]),
        "keyboard.trainer": u64(OFF["kb_trainer"]),

        "lastGW2.type": u32(OFF["last_type"]),
        "lastGW2.vkey": u32(OFF["last_vkey"]),
        "lastGW2.makeCode": u32(OFF["last_make"]),
        "lastGW2.flags": u32(OFF["last_flags"]),

        "lastGW2.caller": hex(u64(OFF["last_gw2_caller"])),
        "lastTrainer.caller": hex(u64(OFF["last_trainer_caller"])),
    }


def diff(a, b):
    if a is None or b is None:
        return None

    keys = [
        "GetRawInputData.total",
        "GetRawInputData.GW2",
        "GetRawInputData.trainer",
        "GetRawInputBuffer.total",
        "GetRawInputBuffer.GW2",
        "GetRawInputBuffer.trainer",
        "keyboard.GW2",
        "keyboard.trainer",
    ]

    return {k: b[k] - a[k] for k in keys}


if __name__ == "__main__":
    print("=== GW2X RAW INPUT PROBE ===")

    s0 = snapshot()
    print("Initial:")
    print(s0)

    if not s0 or not s0["magic_ok"] or s0["version"] != VERSION or s0["ready"] != 1:
        raise SystemExit("RawInputProbe is not ready.")

    print("\nFor 5 seconds, keep GW2 FOCUSED and press 1, 8, 0 several times.")
    a = snapshot()
    time.sleep(5)
    b = snapshot()
    print("Focused delta:")
    print(diff(a, b))
    print("Focused final:")
    print(b)

    print("\nNow ALT-TAB to another app. You have 8 seconds.")
    time.sleep(3)
    print("Probe running unfocused for 5 seconds; press ordinary keys in the other app.")
    a = snapshot()
    time.sleep(5)
    b = snapshot()
    print("Unfocused delta:")
    print(diff(a, b))
    print("Unfocused final:")
    print(b)
