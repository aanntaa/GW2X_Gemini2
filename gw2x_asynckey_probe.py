import mmap
import struct
import time

NAME = "GW2X_ASYNC_KEY_PROBE"

MAGIC = 0x4B413247
VERSION = 1

# C++ packed layout:
# 16-byte header
# uint64 totalGW2Calls
# uint64 calls[256]
# uint64 physicalDownCalls[256]
# uint64 lastCallerRva[256]
# uint8 syntheticDown[256]
OFF_TOTAL = 16
OFF_CALLS = 24
OFF_PHYS_DOWN = OFF_CALLS + 256 * 8
OFF_CALLER_RVA = OFF_PHYS_DOWN + 256 * 8
OFF_SYNTH = OFF_CALLER_RVA + 256 * 8
SIZE = OFF_SYNTH + 256

_mm = None

TARGETS = {
    "1 / SKILL_1": 0x31,
    "8 physical":   0x38,
    "0 physical":   0x30,
    "C / SKILL_8":  0x43,
    "Z / SKILL_10": 0x5A,
    "W movement":    0x57,
    "A movement":    0x41,
    "S movement":    0x53,
    "D movement":    0x44,
    "SHIFT":         0x10,
}


def connect():
    global _mm
    if _mm is not None:
        return True

    try:
        _mm = mmap.mmap(-1, SIZE, tagname=NAME, access=mmap.ACCESS_WRITE)
        return True
    except Exception as e:
        print("[AsyncKeyProbe] connect failed:", e)
        return False


def u32(off):
    return struct.unpack_from("<I", _mm, off)[0]


def u64(off):
    return struct.unpack_from("<Q", _mm, off)[0]


def ready():
    return (
        connect()
        and u32(0) == MAGIC
        and u32(4) == VERSION
        and u32(8) == 1
    )


def calls(vk):
    return u64(OFF_CALLS + (vk & 0xFF) * 8)


def physical_down_calls(vk):
    return u64(OFF_PHYS_DOWN + (vk & 0xFF) * 8)


def caller_rva(vk):
    return u64(OFF_CALLER_RVA + (vk & 0xFF) * 8)


def synthetic_down(vk):
    _mm[OFF_SYNTH + (vk & 0xFF)] = 1


def synthetic_up(vk):
    _mm[OFF_SYNTH + (vk & 0xFF)] = 0


def release_all():
    _mm[OFF_SYNTH:OFF_SYNTH + 256] = b"\x00" * 256


def snap():
    d = {}
    for name, vk in TARGETS.items():
        d[name] = {
            "vk": f"0x{vk:02X}",
            "calls": calls(vk),
            "physical_down": physical_down_calls(vk),
            "caller_rva": f"Gw2-64.exe+0x{caller_rva(vk):X}",
        }
    return d


def delta(a, b):
    result = {}
    for name in TARGETS:
        result[name] = {
            "calls": b[name]["calls"] - a[name]["calls"],
            "physical_down": (
                b[name]["physical_down"] - a[name]["physical_down"]
            ),
            "caller_rva": b[name]["caller_rva"],
        }
    return result


def print_nonzero(d):
    for name, x in d.items():
        if x["calls"] or x["physical_down"]:
            print(f"{name:16s} -> {x}")


if __name__ == "__main__":
    print("=== GW2X ASYNC KEY PROBE V5 ===")

    if not ready():
        raise SystemExit("AsyncKeyProbe is not ready.")

    release_all()

    print("\nFOCUSED PHYSICAL TEST")
    print("For 6 seconds, with GW2 focused, repeatedly press:")
    print("  1, C, Z, W, D")
    a = snap()
    time.sleep(6)
    b = snap()

    print("\nFocused physical deltas:")
    print_nonzero(delta(a, b))

    print("\nFOCUSED SYNTHETIC VALIDATION")
    print("Keep GW2 focused. I will synthesize C (your SKILL_8) for 0.4 sec.")
    time.sleep(1)
    before = calls(0x43)
    synthetic_down(0x43)
    time.sleep(0.4)
    synthetic_up(0x43)
    time.sleep(0.3)
    after = calls(0x43)
    print("C polling delta during validation:", after - before)

    print("\nNow synthesize Z (your SKILL_10) for 0.4 sec.")
    before = calls(0x5A)
    synthetic_down(0x5A)
    time.sleep(0.4)
    synthetic_up(0x5A)
    time.sleep(0.3)
    after = calls(0x5A)
    print("Z polling delta during validation:", after - before)

    print("\nALT-TAB TEST")
    print("Alt-tab to another app now. Waiting 3 seconds...")
    time.sleep(3)

    a = snap()
    print("Holding synthetic C while GW2 is unfocused for 2 seconds.")
    synthetic_down(0x43)
    time.sleep(2)
    synthetic_up(0x43)
    b = snap()

    print("\nUnfocused deltas:")
    print_nonzero(delta(a, b))

    release_all()

    print("\nIMPORTANT:")
    print("- If physical C/Z show calls + physical_down, GetAsyncKeyState is the skill path.")
    print("- If synthetic C/Z activate skills while focused, spoofing this API is validated.")
    print("- If unfocused C/Z call delta is 0, the remaining problem is the internal focus/poll gate.")
