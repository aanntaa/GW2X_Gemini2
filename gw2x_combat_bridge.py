import mmap
import struct
import time

# Must match CombatInputShared in CombatInputHook.h exactly.
IPC_NAME = "GW2X_COMBAT_INPUT"
IPC_SIZE = 280

MAGIC = 0x49433247  # "G2CI"
VERSION = 1

OFF_MAGIC = 0
OFF_VERSION = 4
OFF_READY = 8
OFF_RESERVED = 12
OFF_HOOK_CALLS = 16
OFF_KEYS = 24
KEY_COUNT = 256

_mm = None
_last_connect_error = None


def _u32(offset):
    _mm.seek(offset)
    return struct.unpack("<I", _mm.read(4))[0]


def _u64(offset):
    _mm.seek(offset)
    return struct.unpack("<Q", _mm.read(8))[0]


def connect():
    """Open the named mapping created by kx-vision.dll inside Gw2-64.exe."""
    global _mm, _last_connect_error

    if _mm is not None:
        return True

    try:
        # On Windows, opening an existing named mmap uses the same tagname.
        _mm = mmap.mmap(-1, IPC_SIZE, tagname=IPC_NAME, access=mmap.ACCESS_WRITE)

        if _u32(OFF_MAGIC) != MAGIC:
            raise RuntimeError(
                f"bad IPC magic: 0x{_u32(OFF_MAGIC):08X}")

        if _u32(OFF_VERSION) != VERSION:
            raise RuntimeError(
                f"IPC version mismatch: DLL={_u32(OFF_VERSION)} Python={VERSION}")

        _last_connect_error = None
        return True

    except Exception as exc:
        _last_connect_error = exc
        if _mm is not None:
            try:
                _mm.close()
            except Exception:
                pass
        _mm = None
        return False


def disconnect():
    global _mm
    if _mm is not None:
        try:
            release_all()
        except Exception:
            pass
        try:
            _mm.close()
        except Exception:
            pass
        _mm = None


def ready():
    if not connect():
        return False

    try:
        return (
            _u32(OFF_MAGIC) == MAGIC
            and _u32(OFF_VERSION) == VERSION
            and _u32(OFF_READY) == 1
        )
    except Exception:
        return False


def hook_calls():
    if not connect():
        return 0

    try:
        return _u64(OFF_HOOK_CALLS)
    except Exception:
        return 0


def key_down(scan_code):
    if not ready():
        return False

    scan_code = int(scan_code)
    if not 0 <= scan_code < KEY_COUNT:
        return False

    try:
        _mm[OFF_KEYS + scan_code] = 1
        return True
    except Exception:
        return False


def key_up(scan_code):
    if not connect():
        return False

    scan_code = int(scan_code)
    if not 0 <= scan_code < KEY_COUNT:
        return False

    try:
        _mm[OFF_KEYS + scan_code] = 0
        return True
    except Exception:
        return False


def release_all():
    if not connect():
        return False

    try:
        _mm[OFF_KEYS:OFF_KEYS + KEY_COUNT] = b"\x00" * KEY_COUNT
        return True
    except Exception:
        return False


def tap(scan_code, hold_seconds=0.05, poll_timeout=0.25):
    """
    Frame-synchronized synthetic key tap.

    Instead of blindly sleeping for 50 ms, keep the DIK key down until the
    injected hook has processed at least one 256-byte keyboard-state poll.
    Then keep it down for the requested minimum hold and release it.

    This prevents very short macro taps from occurring entirely between
    two GetDeviceState() polls.
    """
    if not ready():
        return False

    scan_code = int(scan_code)
    if not 0 <= scan_code < KEY_COUNT:
        return False

    before_calls = hook_calls()

    if not key_down(scan_code):
        return False

    down_started = time.perf_counter()
    observed = False

    try:
        deadline = down_started + max(0.01, float(poll_timeout))

        # Wait until at least one keyboard-state call occurs while key is DOWN.
        while time.perf_counter() < deadline:
            if hook_calls() > before_calls:
                observed = True
                break
            time.sleep(0.001)

        # Always satisfy the requested minimum physical-equivalent hold time.
        remaining = float(hold_seconds) - (time.perf_counter() - down_started)
        if remaining > 0:
            time.sleep(remaining)

    finally:
        key_up(scan_code)

    # Give the hook an opportunity to observe the UP state as well.
    release_calls = hook_calls()
    release_deadline = time.perf_counter() + max(0.01, float(poll_timeout))
    while time.perf_counter() < release_deadline:
        if hook_calls() > release_calls:
            break
        time.sleep(0.001)

    return observed


def diagnostics():
    connected = connect()
    return {
        "ipc_connected": connected,
        "ready": ready() if connected else False,
        "hook_calls": hook_calls() if connected else 0,
        "error": None if _last_connect_error is None else str(_last_connect_error),
        "ipc_name": IPC_NAME,
    }
