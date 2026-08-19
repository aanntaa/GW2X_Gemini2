import ctypes
import pymem
import mmap
import struct
import json
import urllib.request
import types
import threading
import time
import win32gui
import logging
import math
from ctypes import windll
from ctypes import wintypes
try:
    from gw2x_arcdps_bridge import BridgeNameLookup
except Exception as _bridge_import_err:
    print(f"[Core] Bridge import failed: {_bridge_import_err}")
    BridgeNameLookup = None
# ==========================================================
# LOAD NPC DATABASE (NPC_db.json)
# ==========================================================
import json as _json
try:
    _NPC_DB_PATH = __import__('pathlib').Path(__file__).parent / "NPC_db.json"
    with open(_NPC_DB_PATH, 'r', encoding='utf-8') as _f:
        raw_npc = _json.load(_f)
        _NPC_DB = {}
        for k, v in raw_npc.items():
            # Auto-convert format string lama ke format dictionary baru
            if isinstance(v, str): _NPC_DB[k] = {"name": v, "type": ""}
            else: _NPC_DB[k] = v
    print(f"[Core] Loaded NPC database: {len(_NPC_DB)} entries")
except Exception as _e:
    print(f"[Core] NPC_db.json not found: {_e}")
    _NPC_DB = {}

# ==========================================================
# LOAD SPATIAL DATABASE (Obj_db.json)
# ==========================================================
try:
    _OBJ_DB_PATH = __import__('pathlib').Path(__file__).parent / "Obj_db.json"
    with open(_OBJ_DB_PATH, 'r', encoding='utf-8') as _f:
        _OBJ_DB = _json.load(_f)
    print(f"[Core] Loaded Object database: {len(_OBJ_DB)} maps")
except Exception as _e:
    print(f"[Core] Obj_db.json not found: {_e}")
    _OBJ_DB = {}

import os

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("gw2x_debug.log"),
        logging.StreamHandler()
    ]
)

# Windows thread context structures
class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("P1Home", ctypes.c_ulonglong),
        ("P2Home", ctypes.c_ulonglong),
        ("P3Home", ctypes.c_ulonglong),
        ("P4Home", ctypes.c_ulonglong),
        ("P5Home", ctypes.c_ulonglong),
        ("P6Home", ctypes.c_ulonglong),
        ("ContextFlags", ctypes.c_ulong),
        ("MxCsr", ctypes.c_ulong),
        ("SegCs", ctypes.c_ushort),
        ("SegDs", ctypes.c_ushort),
        ("SegEs", ctypes.c_ushort),
        ("SegFs", ctypes.c_ushort),
        ("SegGs", ctypes.c_ushort),
        ("SegSs", ctypes.c_ushort),
        ("EFlags", ctypes.c_ulong),
        ("Dr0", ctypes.c_ulonglong),
        ("Dr1", ctypes.c_ulonglong),
        ("Dr2", ctypes.c_ulonglong),
        ("Dr3", ctypes.c_ulonglong),
        ("Dr6", ctypes.c_ulonglong),
        ("Dr7", ctypes.c_ulonglong),
        ("Rax", ctypes.c_ulonglong),
        ("Rcx", ctypes.c_ulonglong),
        ("Rdx", ctypes.c_ulonglong),
        ("Rbx", ctypes.c_ulonglong),
        ("Rsp", ctypes.c_ulonglong),
        ("Rbp", ctypes.c_ulonglong),
        ("Rsi", ctypes.c_ulonglong),
        ("Rdi", ctypes.c_ulonglong),
        ("R8", ctypes.c_ulonglong),
        ("R9", ctypes.c_ulonglong),
        ("R10", ctypes.c_ulonglong),
        ("R11", ctypes.c_ulonglong),
        ("R12", ctypes.c_ulonglong),
        ("R13", ctypes.c_ulonglong),
        ("R14", ctypes.c_ulonglong),
        ("R15", ctypes.c_ulonglong),
        ("Rip", ctypes.c_ulonglong),
    ]

# ===============================
# REMOTE OFFSET LOADER
# ===============================

URL_CORE = 'https://raw.githubusercontent.com/Sabayonz/online_other_xx/main/GW2X/CORE.py'
URL_USER = 'https://raw.githubusercontent.com/Sabayonz/online_other_xx/main/GW2X/USER.py'

import urllib.request
import types

def load_module_from_url(url):
    try:
        response = urllib.request.urlopen(url)
        contents = response.read().decode('utf-8')
        module = types.ModuleType("remote_offsets")
        exec(contents, module.__dict__)
        return {k: v for k, v in module.__dict__.items() if not k.startswith("__")}
    except Exception as e:
        print(f"[Core] Remote load failed: {e}")
        return {}

print("[Core] Loading remote offsets...")
globals().update(load_module_from_url(URL_CORE))
globals().update(load_module_from_url(URL_USER))

# ===============================
# DIRECT ALIAS (NO MAPPING LAYER)
# ===============================
# Base
base_core_address        = xxxx1
# skyscalegreenbaraddress  = xxxx2
griffoninstaboostaddress = xxxx3
fishingmasteraddress     = xxxx4
skiffmasteraddress       = xxxx5
clippingaddress          = xxxx6
fullclippingaddress      = xxxx7
context_base_mem         = xxxx8
interacting              = xxxx9
interacting_value        = xxxx10
mountzom                 = xxxx11
playerzom                = xxxx12

# Visual / ESP
fgaddr      = xxxx13
fg2addr     = xxxx14
name        = xxxx15
brightness  = xxxx16
viewdist    = xxxx17
health1     = xxxx18
health2     = xxxx19
mprdr       = xxxx20
objname     = xxxx21
objhealth   = xxxx22

# Extra
anglersense = xxxx23
proskiff    = xxxx24
life_base_addr = xxxx25

# ===============================
# USER MOD VALUES (zzzz)
# ===============================

mapradarori       = zzzz1
mapradarmod       = zzzz2
nametagori        = zzzz3
nametagmod        = zzzz4
espbrightori      = zzzz5
espbrightmod      = zzzz6
viewdistanceori   = zzzz7
viewdistancemod   = zzzz8
objectespori      = zzzz9
objectespmod      = zzzz10
objecthpori       = zzzz11
objecthpmod       = zzzz12
hpbar1ori         = zzzz13
hpbar1mod         = zzzz14
hpbar2ori         = zzzz15
hpbar2mod         = zzzz16
nofogori          = zzzz17
nofogmod          = zzzz18
clearsurfaceori   = zzzz19
clearsurfacemod   = zzzz20
mapradar_hostile_ofset = zzzz35
mapradar_hostile_ori   = zzzz36
mapradar_hostile_mod   = zzzz37
mapradar_player_ofset  = zzzz38
mapradar_player_ori    = zzzz39
mapradar_player_mod    = zzzz40

# Critical Definitions
mountstamina_base_mem = base_core_address
mountstamina_offset_mem = [152, 16, 912, 12]

# Standard Speed Offsets
speed_base_mem = base_core_address
speed_offset_mem = [152, 56, 80, 696]
speed_base_mem1 = base_core_address
speed_offset_mem1 = [152, 56, 80, 692]
speed_base_mem2 = base_core_address
speed_offset_mem2 = [152, 56, 80, 688]

# Position Offsets
xpos_base_mem = base_core_address
xpos_offset_mem = [152, 80, 256, 288]
zpos_base_mem = base_core_address
zpos_offset_mem = [152, 80, 256, 292]
ypos_base_mem = base_core_address
ypos_offset_mem = [152, 80, 256, 296]

# ===============================
# FISHING OFFSETS (UPDATED)
# ===============================
fishing_base_mem = base_core_address
fishing_offset_mem = [1368, 96, 24, 128]

fishing_fish_bar_mem = base_core_address
fishing_fish_bar_offset_mem = [1368, 96, 24, 132]

fishing_player_bar_mem = base_core_address
fishing_player_bar_offset_mem = [1368, 96, 24, 136]

fishing_insta_hook_base_mem = base_core_address
fishing_insta_hook_offset_mem = [1368, 96, 24, 104]

fishing_active_mem = base_core_address
fishing_active_offset_mem = [1368, 96, 24, 368]

fishing_power_mem = base_core_address
fishing_power_offset_mem = [1368, 0, 204]
fishing_power_offset_mem1 = [1368, 0, 100]
fishing_power_offset_mem2 = [1368, 0, 396]
fishing_power_offset_mem3 = [1368, 0, 544]

fishing_insta_signing_base_mem = base_core_address
fishing_insta_signing_offset_mem = [1368, 96, 24, 95]

MOUSE_STATIC_OFFSET = 0x0283D850 + 0x240

# ===============================
# MUMBLE LINK STRUCTURES (NEW FIX)
# ===============================
class Link(ctypes.Structure):
    _fields_ = [
        ("uiVersion", ctypes.c_uint32),           # 4 bytes
        ("uiTick", ctypes.c_uint32),              # 4 bytes
        ("fAvatarPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarFront", ctypes.c_float * 3),     # 3*4 bytes
        ("fAvatarTop", ctypes.c_float * 3),       # 3*4 bytes
        ("name", ctypes.c_wchar * 256),           # 512 bytes
        ("fCameraPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraFront", ctypes.c_float * 3),     # 3*4 bytes
        ("fCameraTop", ctypes.c_float * 3),       # 3*4 bytes
        ("identity", ctypes.c_wchar * 256),       # 512 bytes
        ("context_len", ctypes.c_uint32),         # 4 bytes
    ]

class Context(ctypes.Structure):
    _fields_ = [
        ("serverAddress", ctypes.c_ubyte * 28),   # 28 bytes
        ("mapId", ctypes.c_uint32),               # 4 bytes
        ("mapType", ctypes.c_uint32),             # 4 bytes
        ("shardId", ctypes.c_uint32),             # 4 bytes
        ("instance", ctypes.c_uint32),            # 4 bytes
        ("buildId", ctypes.c_uint32),             # 4 bytes
        ("uiState", ctypes.c_uint32),             # 4 bytes
        ("compassWidth", ctypes.c_uint16),        # 2 bytes
        ("compassHeight", ctypes.c_uint16),       # 2 bytes
        ("compassRotation", ctypes.c_float),      # 4 bytes
        ("playerX", ctypes.c_float),              # 4 bytes
        ("playerY", ctypes.c_float),              # 4 bytes
        ("mapCenterX", ctypes.c_float),           # 4 bytes
        ("mapCenterY", ctypes.c_float),           # 4 bytes
        ("mapScale", ctypes.c_float),             # 4 bytes
        ("processId", ctypes.c_uint32),           # 4 bytes
        ("mountIndex", ctypes.c_uint8),           # 1 byte
    ]

class MumbleData:
    def __init__(self):
        self.mm = None
        self.link_name = None
        self.size_link = ctypes.sizeof(Link)
        self.size_context = ctypes.sizeof(Context)
        self.find_active_link()  

    def find_active_link(self):
        global _last_logged_pid

        candidates = ["MumbleLink", "MumbleLink_0"] + [f"MumbleLink_{i}" for i in range(1, 6)]

        for name in candidates:
            try:
                mm = mmap.mmap(-1, 5460, tagname=name, access=mmap.ACCESS_READ)
                mm.seek(0)

                raw_link = mm.read(self.size_link)
                link = Link.from_buffer_copy(raw_link)

                raw_context = mm.read(self.size_context)
                ctx = Context.from_buffer_copy(raw_context)

                # 🔥 ONLY ACCEPT LINK MATCHING SELECTED PID
                if ctx.processId == _last_logged_pid:
                    self.mm = mm
                    self.link_name = name
                    print(f"[Core] Connected to Mumble Link: {name} (PID Match)")
                    return

            except:
                continue

        print("[Core] No matching Mumble Link found.")

    def read(self):
        if not self.mm: 
            self.find_active_link()
            if not self.mm: return None

        try:
            self.mm.seek(0)
            raw_link = self.mm.read(self.size_link)
            link = Link.from_buffer_copy(raw_link)
            
            raw_context = self.mm.read(self.size_context)
            ctx = Context.from_buffer_copy(raw_context)

            # Bit 1 = Map Open (1 << 0)
            is_map_open = (ctx.uiState & 1) != 0 
            
            map_id = 0
            world_id = 0
            try:
                if link.identity:
                    j = json.loads(link.identity)
                    map_id = j.get('map_id', 0)
                    world_id = j.get('world', 0)
            except: pass
                
            if map_id == 0: map_id = ctx.mapId

            return {
                "pos": (link.fAvatarPosition[0], link.fAvatarPosition[1], link.fAvatarPosition[2]),
                "cam": (link.fCameraPosition[0], link.fCameraPosition[1], link.fCameraPosition[2]),
                "fCameraFront": (link.fCameraFront[0], link.fCameraFront[1], link.fCameraFront[2]),
                "map_id": map_id,
                "world_id": world_id,
                "map_center_x": ctx.mapCenterX,
                "map_center_y": ctx.mapCenterY,
                "map_scale": ctx.mapScale,
                "is_map_open": is_map_open,
                "ui_state": ctx.uiState,
                "tick": link.uiTick,
                "build_id": ctx.buildId,
                "process_id": ctx.processId,
                "player_x": ctx.playerX,
                "player_y": ctx.playerY,
                "mount_index": ctx.mountIndex
            }
        except Exception: return None


# ==========================================================
# DLL EVENT PROBE CONTROL (ABI V1)
# ==========================================================

class EventProbeControlV1(ctypes.Structure):
    """Exact layout shared with DataExtractor.cpp (372 bytes, packed)."""
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint16),
        ("struct_size", ctypes.c_uint16),
        ("request_sequence", ctypes.c_int32),
        ("completed_sequence", ctypes.c_int32),
        ("status", ctypes.c_int32),
        ("command", ctypes.c_uint32),
        ("client_build_id", ctypes.c_uint32),
        ("guid", ctypes.c_char * 40),
        ("message", ctypes.c_char * 256),
        ("inactive_block_count", ctypes.c_uint32),
        ("active_block_count", ctypes.c_uint32),
        ("verify_block_count", ctypes.c_uint32),
        ("candidate_count", ctypes.c_uint32),
        ("build_timestamp", ctypes.c_uint32),
        ("image_size", ctypes.c_uint32),
        ("process_id", ctypes.c_uint32),
        ("snapshot_bytes", ctypes.c_uint32),
        ("map_id", ctypes.c_uint32),
        ("player_x", ctypes.c_float),
        ("player_y", ctypes.c_float),
        ("player_z", ctypes.c_float),
    ]


if ctypes.sizeof(EventProbeControlV1) != 372:
    raise RuntimeError("GW2X Event Probe ABI layout mismatch")


class EventProbeBridge:
    TAG_NAME = "GW2X_EVENT_PROBE_CONTROL_V1"
    MAGIC = 0x31505645  # "EVP1"
    VERSION = 1
    FILE_MAP_WRITE = 0x0002
    FILE_MAP_READ = 0x0004

    COMMANDS = {
        "inactive": 1,
        "active": 2,
        "verify": 3,
        "reset": 4,
    }
    STATUS_NAMES = {
        0: "idle",
        1: "busy",
        2: "success",
        3: "error",
    }

    def __init__(self):
        self.handle = None
        self.view = None
        self.control = None
        self.kernel32 = None
        self.last_error = "Event Probe mapping unavailable; inject the rebuilt DLL"
        self._connect_error_logged = False
        self._lock = threading.Lock()

    def close(self):
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self):
        try:
            if self.kernel32 and self.view:
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(self.view))
        except Exception:
            pass
        try:
            if self.kernel32 and self.handle:
                self.kernel32.CloseHandle(ctypes.c_void_p(self.handle))
        except Exception:
            pass
        self.control = None
        self.view = None
        self.handle = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def connect(self):
        with self._lock:
            return self._connect_unlocked()

    def _connect_unlocked(self):
        if self.control is not None:
            try:
                if (self.control.magic == self.MAGIC and
                        self.control.version == self.VERSION and
                        self.control.struct_size == ctypes.sizeof(EventProbeControlV1)):
                    expected_pid = int(_last_logged_pid or 0)
                    if not expected_pid or self.control.process_id == expected_pid:
                        return True
            except Exception:
                pass
            self._close_unlocked()

        try:
            self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel32.OpenFileMappingW.argtypes = [
                wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            self.kernel32.OpenFileMappingW.restype = ctypes.c_void_p
            self.kernel32.MapViewOfFile.argtypes = [
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                wintypes.DWORD, ctypes.c_size_t]
            self.kernel32.MapViewOfFile.restype = ctypes.c_void_p
            self.kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
            self.kernel32.UnmapViewOfFile.restype = wintypes.BOOL
            self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            self.kernel32.CloseHandle.restype = wintypes.BOOL

            access = self.FILE_MAP_READ | self.FILE_MAP_WRITE
            handle = self.kernel32.OpenFileMappingW(access, False, self.TAG_NAME)
            if not handle:
                raise OSError(ctypes.get_last_error(), "OpenFileMappingW failed")

            view = self.kernel32.MapViewOfFile(
                handle, access, 0, 0, ctypes.sizeof(EventProbeControlV1))
            if not view:
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise OSError(ctypes.get_last_error(), "MapViewOfFile failed")

            control = EventProbeControlV1.from_address(view)
            if (control.magic != self.MAGIC or
                    control.version != self.VERSION or
                    control.struct_size != ctypes.sizeof(EventProbeControlV1)):
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(view))
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise RuntimeError(
                    f"Event Probe ABI mismatch (magic=0x{control.magic:08X}, "
                    f"version={control.version}, size={control.struct_size})")

            expected_pid = int(_last_logged_pid or 0)
            if expected_pid and control.process_id != expected_pid:
                actual_pid = int(control.process_id)
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(view))
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise RuntimeError(
                    f"Event Probe belongs to GW2 PID {actual_pid}, selected PID is {expected_pid}")

            self.handle = handle
            self.view = int(view)
            self.control = control
            self.last_error = ""
            if not self._connect_error_logged:
                print(f"[EventProbe] Connected to DLL control (PID {control.process_id}).")
            self._connect_error_logged = False
            return True
        except Exception as exc:
            self._close_unlocked()
            self.last_error = str(exc) or "Event Probe mapping unavailable"
            if not self._connect_error_logged:
                print(f"[EventProbe] {self.last_error}")
                self._connect_error_logged = True
            return False

    @staticmethod
    def _decode_text(value):
        return bytes(value).split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    def read_status(self):
        with self._lock:
            if not self._connect_unlocked():
                return {
                    "available": False,
                    "status": "unavailable",
                    "message": self.last_error,
                    "inactive_blocks": 0,
                    "active_blocks": 0,
                    "verify_blocks": 0,
                    "candidates": 0,
                }

            try:
                c = self.control
                if c.magic != self.MAGIC:
                    raise RuntimeError("DLL unloaded or Event Probe mapping became stale")
                return {
                    "available": True,
                    "status": self.STATUS_NAMES.get(int(c.status), f"status-{int(c.status)}"),
                    "message": self._decode_text(c.message),
                    "inactive_blocks": int(c.inactive_block_count),
                    "active_blocks": int(c.active_block_count),
                    "verify_blocks": int(c.verify_block_count),
                    "candidates": int(c.candidate_count),
                    "request_sequence": int(c.request_sequence),
                    "completed_sequence": int(c.completed_sequence),
                    "process_id": int(c.process_id),
                    "build_timestamp": int(c.build_timestamp),
                    "image_size": int(c.image_size),
                    "snapshot_bytes": int(c.snapshot_bytes),
                    "map_id": int(c.map_id),
                }
            except Exception as exc:
                self.last_error = str(exc)
                self._close_unlocked()
                return {
                    "available": False,
                    "status": "unavailable",
                    "message": self.last_error,
                    "inactive_blocks": 0,
                    "active_blocks": 0,
                    "verify_blocks": 0,
                    "candidates": 0,
                }

    def send_command(self, command, guid="", map_id=0, build_id=0,
                     player_position=(0.0, 0.0, 0.0)):
        command_id = self.COMMANDS.get(str(command).lower())
        if command_id is None:
            return False, f"Unknown Event Probe command: {command}"

        if command_id != self.COMMANDS["reset"]:
            import uuid
            try:
                guid = str(uuid.UUID(str(guid))).upper()
            except Exception:
                return False, "Select an event with a valid GUID first"
        else:
            guid = str(guid or "")

        with self._lock:
            if not self._connect_unlocked():
                return False, self.last_error

            c = self.control
            request = int(c.request_sequence)
            completed = int(c.completed_sequence)
            if request != completed or int(c.status) == 1:
                return False, "Event Probe is still processing the previous capture"

            try:
                px, py, pz = player_position or (0.0, 0.0, 0.0)
                c.command = command_id
                c.client_build_id = int(build_id or 0)
                c.guid = guid.encode("ascii", errors="ignore")[:39]
                c.map_id = int(map_id or 0)
                c.player_x = float(px)
                c.player_y = float(py)
                c.player_z = float(pz)

                next_sequence = max(request, completed) + 1
                if next_sequence <= 0 or next_sequence > 0x7FFFFFFF:
                    next_sequence = 1

                # request_sequence is naturally aligned at byte offset 8.  An
                # aligned 32-bit store is atomic on the x64 client; it is written
                # last so the DLL never observes a partially prepared request.
                ctypes.c_int32.from_address(
                    self.view + EventProbeControlV1.request_sequence.offset
                ).value = next_sequence
                return True, "Event Probe command queued"
            except Exception as exc:
                return False, f"Event Probe request failed: {exc}"


# ==========================================================
# DLL LIVE EVENT-COORDINATE FEED (ABI V1)
# ==========================================================

class LiveEventCoordinateV1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("runtime_id", ctypes.c_uint32),
        ("map_x", ctypes.c_float),
        ("map_y", ctypes.c_float),
        ("map_z", ctypes.c_float),
        ("object_ptr", ctypes.c_uint64),
        ("cc_offset", ctypes.c_uint16),
        ("array_offset", ctypes.c_uint16),
        ("array_index", ctypes.c_uint16),
        ("coordinate_offset", ctypes.c_uint16),
    ]


class LiveEventControlV1(ctypes.Structure):
    _pack_ = 1
    MAX_RECORDS = 128
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint16),
        ("struct_size", ctypes.c_uint16),
        ("sequence", ctypes.c_int32),
        ("process_id", ctypes.c_uint32),
        ("build_timestamp", ctypes.c_uint32),
        ("image_size", ctypes.c_uint32),
        ("last_update_tick", ctypes.c_uint64),
        ("record_count", ctypes.c_uint32),
        ("objects_scanned", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("records", LiveEventCoordinateV1 * MAX_RECORDS),
    ]


if ctypes.sizeof(LiveEventCoordinateV1) != 32:
    raise RuntimeError("GW2X Live Event record ABI layout mismatch")
if ctypes.sizeof(LiveEventControlV1) != 4144:
    raise RuntimeError("GW2X Live Event control ABI layout mismatch")


class LiveEventBridge:
    TAG_NAME = "GW2X_LIVE_EVENTS_V1"
    MAGIC = 0x3156454C  # "LEV1"
    VERSION = 1
    FILE_MAP_READ = 0x0004
    STALE_AFTER_MS = 3000

    def __init__(self):
        self.handle = None
        self.view = None
        self.control = None
        self.kernel32 = None
        self.last_error = "Live Event mapping unavailable; inject the rebuilt DLL"
        self._connect_error_logged = False
        self._lock = threading.Lock()

    def close(self):
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self):
        try:
            if self.kernel32 and self.view:
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(self.view))
        except Exception:
            pass
        try:
            if self.kernel32 and self.handle:
                self.kernel32.CloseHandle(ctypes.c_void_p(self.handle))
        except Exception:
            pass
        self.control = None
        self.view = None
        self.handle = None

    def _connect_unlocked(self):
        if self.control is not None:
            try:
                expected_pid = int(_last_logged_pid or 0)
                if (self.control.magic == self.MAGIC and
                        self.control.version == self.VERSION and
                        self.control.struct_size == ctypes.sizeof(LiveEventControlV1) and
                        (not expected_pid or self.control.process_id == expected_pid)):
                    return True
            except Exception:
                pass
            self._close_unlocked()

        try:
            self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel32.OpenFileMappingW.argtypes = [
                wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            self.kernel32.OpenFileMappingW.restype = ctypes.c_void_p
            self.kernel32.MapViewOfFile.argtypes = [
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                wintypes.DWORD, ctypes.c_size_t]
            self.kernel32.MapViewOfFile.restype = ctypes.c_void_p
            self.kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
            self.kernel32.UnmapViewOfFile.restype = wintypes.BOOL
            self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            self.kernel32.CloseHandle.restype = wintypes.BOOL
            self.kernel32.GetTickCount64.argtypes = []
            self.kernel32.GetTickCount64.restype = ctypes.c_uint64

            handle = self.kernel32.OpenFileMappingW(
                self.FILE_MAP_READ, False, self.TAG_NAME)
            if not handle:
                raise OSError(ctypes.get_last_error(), "OpenFileMappingW failed")
            view = self.kernel32.MapViewOfFile(
                handle, self.FILE_MAP_READ, 0, 0,
                ctypes.sizeof(LiveEventControlV1))
            if not view:
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise OSError(ctypes.get_last_error(), "MapViewOfFile failed")

            control = LiveEventControlV1.from_address(view)
            if (control.magic != self.MAGIC or
                    control.version != self.VERSION or
                    control.struct_size != ctypes.sizeof(LiveEventControlV1)):
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(view))
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise RuntimeError(
                    f"Live Event ABI mismatch (magic=0x{control.magic:08X}, "
                    f"version={control.version}, size={control.struct_size})")

            expected_pid = int(_last_logged_pid or 0)
            if expected_pid and control.process_id != expected_pid:
                actual_pid = int(control.process_id)
                self.kernel32.UnmapViewOfFile(ctypes.c_void_p(view))
                self.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise RuntimeError(
                    f"Live Event feed belongs to GW2 PID {actual_pid}, "
                    f"selected PID is {expected_pid}")

            self.handle = handle
            self.view = int(view)
            self.control = control
            self.last_error = ""
            if not self._connect_error_logged:
                print(f"[LiveEvent] Connected to DLL feed (PID {control.process_id}).")
            self._connect_error_logged = False
            return True
        except Exception as exc:
            self._close_unlocked()
            self.last_error = str(exc) or "Live Event mapping unavailable"
            if not self._connect_error_logged:
                print(f"[LiveEvent] {self.last_error}")
                self._connect_error_logged = True
            return False

    def read_snapshot(self):
        with self._lock:
            if not self._connect_unlocked():
                return {
                    "available": False, "fresh": False,
                    "message": self.last_error, "records": [],
                    "record_count": 0, "objects_scanned": 0,
                }

            try:
                snapshot = None
                sequence_offset = LiveEventControlV1.sequence.offset
                for _ in range(4):
                    sequence_before = ctypes.c_int32.from_address(
                        self.view + sequence_offset).value
                    if sequence_before & 1:
                        time.sleep(0)
                        continue
                    raw = ctypes.string_at(
                        self.view, ctypes.sizeof(LiveEventControlV1))
                    sequence_after = ctypes.c_int32.from_address(
                        self.view + sequence_offset).value
                    if (sequence_before == sequence_after and
                            not (sequence_after & 1)):
                        snapshot = LiveEventControlV1.from_buffer_copy(raw)
                        break
                if snapshot is None:
                    return {
                        "available": True, "fresh": False,
                        "message": "Live Event feed is updating", "records": [],
                        "record_count": 0, "objects_scanned": 0,
                    }
                if snapshot.magic != self.MAGIC:
                    raise RuntimeError("DLL unloaded or Live Event feed became stale")

                now = int(self.kernel32.GetTickCount64())
                update_tick = int(snapshot.last_update_tick)
                age_ms = max(0, now - update_tick) if update_tick else 0
                fresh = bool(update_tick and age_ms <= self.STALE_AFTER_MS)
                count = min(int(snapshot.record_count), LiveEventControlV1.MAX_RECORDS)
                records = []
                if fresh:
                    for index in range(count):
                        record = snapshot.records[index]
                        records.append({
                            "runtime_id": int(record.runtime_id),
                            "map_x": float(record.map_x),
                            "map_y": float(record.map_y),
                            "map_z": float(record.map_z),
                            "object_ptr": int(record.object_ptr),
                            "cc_offset": int(record.cc_offset),
                            "array_offset": int(record.array_offset),
                            "array_index": int(record.array_index),
                            "coordinate_offset": int(record.coordinate_offset),
                        })

                flags = int(snapshot.flags)
                source = "primary" if flags & 0x2 else (
                    "fallback" if flags & 0x4 else "unresolved")
                return {
                    "available": True,
                    "fresh": fresh,
                    "message": "Live Event feed ready" if fresh else "Live Event feed is stale",
                    "records": records,
                    "record_count": count if fresh else 0,
                    "objects_scanned": int(snapshot.objects_scanned),
                    "flags": flags,
                    "source": source,
                    "truncated": bool(flags & 0x8),
                    "age_ms": age_ms,
                    "process_id": int(snapshot.process_id),
                    "build_timestamp": int(snapshot.build_timestamp),
                    "image_size": int(snapshot.image_size),
                    "sequence": int(snapshot.sequence),
                }
            except Exception as exc:
                self.last_error = str(exc)
                self._close_unlocked()
                return {
                    "available": False, "fresh": False,
                    "message": self.last_error, "records": [],
                    "record_count": 0, "objects_scanned": 0,
                }

# ===============================
# SHARED MEMORY IPC (ENTITY LIST)
# ===============================

class SharedEntityData:
    # Struct layout must match SharedMemoryIPC.h:
    #   int32  agentId       (4)
    #   float  x, y, z      (12)
    #   int32  entityType    (4)
    #   int32  attitude      (4)
    #   float  currentHealth (4)
    #   float  maxHealth     (4)
    #   int32  isGatherable  (4)
    #   char   name[64]      (64)
    #   Total: 100 bytes
    STRUCT_SIZE   = 104
    MAX_ENTITIES  = 1000
    NAME_OFFSET   = 40   # bytes before name field (added isCommander int32)
    NAME_LEN      = 64

    def __init__(self):
        self.mm = None
        self.buffer_size = self.STRUCT_SIZE * self.MAX_ENTITIES

    def connect(self):
        try:
            self.mm = mmap.mmap(-1, self.buffer_size, tagname="GW2X_ENTITY_SHARED", access=mmap.ACCESS_READ)
            print("[Core-IPC] SUCCESS: Connected to Shared Memory (GW2X_ENTITY_SHARED).")
            return True
        except Exception as e:
            print(f"[Core-IPC] ERROR: Failed to map IPC memory. Is the .dll injected? Error: {e}")
            return False

    def _resolve_name(self, agent_id, raw_name, ent_type=None):
        species_id = None
        display_name = raw_name

        # Only resolve if it is SID-based entity
        if raw_name.startswith("SID:"):
            try:
                species_id = raw_name.split(":")[1]

                # ===============================
                # 1️⃣ ArcDPS Bridge (live or cache)
                # ===============================
                if hasattr(self, 'bridge_names') and self.bridge_names:
                    try:
                        live_name = self.bridge_names.get_name_by_sid(
                            int(species_id),
                            auto_update=False
                        )
                        if live_name:
                            return live_name, species_id
                    except:
                        pass

                # ===============================
                # 2️⃣ Static NPC_db.json fallback
                # ===============================
                db_name = get_def_name(species_id)
                if db_name:
                    return db_name, species_id

                # ===============================
                # 3️⃣ Final fallback
                # ===============================
                return f"SID:{species_id}", species_id

            except:
                pass

        # Non-SID names (players etc)
        elif raw_name and not raw_name.startswith("OBJ:"):
            return raw_name, None

        return display_name, species_id

    def read_entities(self):
        if not self.mm:
            if not self.connect():
                return []

        # ======================================================
        # SPATIAL INIT: Ambil Map ID sekali saja per frame
        # ======================================================
        current_map_id = "0"
        global mumble
        if mumble:
            m_data = mumble.read()
            if m_data:
                current_map_id = str(m_data.get("map_id", "0"))
        
        map_static_nodes = _OBJ_DB.get(current_map_id, [])

        entities = []
        try:
            self.mm.seek(0)
            raw_data = self.mm.read(self.buffer_size)

            for i in range(self.MAX_ENTITIES):
                offset = i * self.STRUCT_SIZE
                chunk = raw_data[offset:offset + self.STRUCT_SIZE]

                if len(chunk) < self.NAME_OFFSET:
                    continue

                agent_id, x, y, z, ent_type, att, hp_cur, hp_max, is_gatherable, is_commander = \
                    struct.unpack_from("<ifffii f f i i", chunk, 0)

                # --- FILTER LOGIKA ABSOLUT WAJIB DI SINI ---
                if agent_id <= 0 or agent_id > 10000000:
                    continue
                if hp_cur > 10000000 or hp_cur < 0:
                    continue
                # ---------------------------------------------

                # Read name field (offset 36, 64 bytes, null-terminated UTF-8)
                raw_name_bytes = chunk[self.NAME_OFFSET:self.NAME_OFFSET + self.NAME_LEN]
                raw_name = raw_name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')

                display_name, species_id = self._resolve_name(agent_id, raw_name, ent_type)

                db_type = ""
                # Kalo NPC
                if species_id and species_id != "None":
                    db_type = get_def_type(species_id)
                    
                # Kalo OBJ (Spatial)
                elif display_name.startswith("OBJ:"):
                    nearest = None
                    min_dist = float("inf")

                    for static_node in map_static_nodes:
                        dx = x - static_node.get("x", 0.0)
                        dy = y - static_node.get("y", 0.0)
                        dz = z - static_node.get("z", 0.0)
                        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                        radius = static_node.get("radius", 2.5)

                        if dist <= radius and dist < min_dist:
                            nearest = static_node
                            min_dist = dist

                    if nearest:
                        display_name = nearest["name"]
                        db_type = nearest.get("type", "")
                            
                # ==========================================
                # FUNCTIONAL LABELING (Tidak menimpa nama asli)
                # ==========================================
                func_label = ""
                if is_gatherable:
                    func_label = "Gathering Node"
                elif ent_type == 9: # GadgetAttackTarget
                    func_label = "Interactable"

                # =========================================================
                # PEMBUKTIAN ABSOLUT: MONITOR DYNAMIC BUFF
                # =========================================================
                global _cmd_tracker
                if '_cmd_tracker' not in globals():
                    _cmd_tracker = set()
                
                # Gunakan display_name yang sudah ada, jangan panggil 'ent'
                safe_name = display_name if display_name else str(agent_id)
                
                if is_commander:
                    if safe_name not in _cmd_tracker:
                        print(f"[BUKTI MUTLAK] 👑 Tag Menyala: {safe_name} (Buff ID 573 Terkunci!)")
                        _cmd_tracker.add(safe_name)
                else:
                    if safe_name in _cmd_tracker:
                        print(f"[BUKTI MUTLAK] ❌ Tag Mati: {safe_name} (Buff ID 573 Hilang)")
                        _cmd_tracker.remove(safe_name)
                # =========================================================

                entities.append({
                    "id":           agent_id,
                    "x": x, "y": y, "z": z,
                    "type":         ent_type,
                    "raw_attitude": att,
                    "hp_cur":       hp_cur,
                    "hp_max":       hp_max,
                    "is_gatherable": bool(is_gatherable),
                    "is_commander": bool(is_commander),
                    "real_name":    display_name,
                    "species_id":   species_id,
                    "func_label":   func_label
                })

            if not entities:
                print("[Core-IPC] WARNING: IPC connected, but buffer is empty (all IDs are 0).")

            return entities

        except struct.error as e:
            print(f"[Core-IPC] STRUCT UNPACK ERROR: {e}")
            return []
        except Exception as e:
            print(f"[Core-IPC] UNKNOWN ERROR during read: {e}")
            return []


    @staticmethod
    def process_entity(entity_data):
        # Evaluasi statis dari data yang valid: species_id bukan None
        if entity_data.get('species_id') is not None:
            if entity_data['species_id'] == "4294946450":
                print(f"Found Mistlock Singularity at ({entity_data['x']}, {entity_data['y']}, {entity_data['z']})")
        else:
            print(f"Unknown object: {entity_data['real_name']} (no static ID)")
            
class GameEntity(ctypes.Structure):
    _fields_ = [
        ("position", ctypes.c_float * 3), # glm::vec3
        ("visualDistance", ctypes.c_float),
        ("gameplayDistance", ctypes.c_float),
        ("isValid", ctypes.c_bool),
        # PADDING 3 byte biasanya otomatis ditambahkan C++, tapi ctypes terkadang butuh penyesuaian jika tidak pas.
        ("address", ctypes.c_uint64), # const void* (asumsi 64-bit)
        ("agent", ctypes.c_uint64),   # void*
        ("currentHealth", ctypes.c_float),
        ("maxHealth", ctypes.c_float),
        ("currentBarrier", ctypes.c_float),
        ("entityType", ctypes.c_int32),
        ("agentType", ctypes.c_int32),
        ("agentId", ctypes.c_int32),
        ("physicsWidth", ctypes.c_float),
        ("physicsDepth", ctypes.c_float),
        ("physicsHeight", ctypes.c_float),
        ("hasPhysicsDimensions", ctypes.c_bool),
        ("shapeType", ctypes.c_int32), # Padding 3 byte setelah bool biasanya
    ]

class NpcEntity(ctypes.Structure):
    _fields_ = [
        ("base", GameEntity),
        ("name", ctypes.c_char * 64),
        ("level", ctypes.c_uint32),
        ("attitude", ctypes.c_int32), # INI ADALAH TARGET KITA
        ("rank", ctypes.c_int32),
    ]
# ===============================
# CORE VARIABLES
# ===============================
pm = None
mumble = None
shared_entities = None
event_probe = None
live_events = None
stamina_thread = None
skyscale_thread = None
_skyscale_addr = None
current_hwnd = None
_last_logged_pid = None  
_GW2_WINDOW_RESOLVER_BUILD = "HWND-FIX-20260818-R1"
_last_map_hover = {
    "map_x": None,
    "map_y": None,
    "timestamp": 0.0
}

class OffsetManager:
    def __init__(self):
        self.offsets = {}
        self.loaded = False
    def load_offsets(self): return {} 

offset_manager = OffsetManager()


# === MAP SPACE DIRECT READ (GX/GY) ===

gx_static_offset = 0x2555AF4  # replace with your module offset
gy_static_offset = gx_static_offset + 4
map_center_x_offset = gx_static_offset + 8
map_center_y_offset = gx_static_offset + 12


def read_map_space_block():
    if not pm:
        return None

    try:
        module = pymem.process.module_from_name(pm.process_handle, "Gw2-64.exe")
        base = module.lpBaseOfDll

        gx = pm.read_float(base + gx_static_offset)
        gy = pm.read_float(base + gy_static_offset)
        mcx = pm.read_float(base + map_center_x_offset)
        mcy = pm.read_float(base + map_center_y_offset)

        print("---- MAP SPACE DEBUG ----")
        print("GX :", gx)
        print("GY :", gy)
        print("MCX:", mcx)
        print("MCY:", mcy)
        print("--------------------------")

        return {
            "player_x": gx,
            "player_y": gy,
            "map_center_x": mcx,
            "map_center_y": mcy
        }

    except:
        return None


# ===============================
# MEMORY OPS
# ===============================
def list_gw2_processes():
    import psutil
    processes = []

    for p in psutil.process_iter(['pid', 'name', 'create_time']):
        try:
            if p.info['name'] and "Gw2-64.exe" in p.info['name']:
                processes.append({
                    "pid": p.info["pid"],
                    "create_time": p.info["create_time"]
                })
        except:
            continue

    return processes

def _pmdbg_mapped_hwnd_for_pid(pid):
    """Return the exact GW2 HWND published by the debug DLL, if available."""
    reader = globals().get("_pmdbg_read_snapshot")
    if not callable(reader):
        return 0

    try:
        snapshot, _ = reader()
        if snapshot is None or not snapshot.ready:
            return 0
        if int(snapshot.dll_pid) != int(pid):
            return 0

        hwnd = int(snapshot.hwnd_value or 0)
        if not hwnd or not win32gui.IsWindow(hwnd):
            return 0

        import win32process
        _, owner_pid = win32process.GetWindowThreadProcessId(hwnd)
        return hwnd if int(owner_pid) == int(pid) else 0
    except Exception:
        # The DLL is optional. Normal same-PID window selection remains available.
        return 0


def _score_gw2_window_candidate(
    class_name,
    title,
    width,
    height,
    owner_hwnd,
    visible,
    enabled,
    is_mapped=False,
):
    """Score a top-level window, or return None for known non-game windows."""
    class_lower = (class_name or "").strip().lower()
    title_lower = (title or "").strip().lower()

    # The injected DLL's AllocConsole window has the same PID as GW2. It must
    # never become the PostMessage target.
    if (
        class_lower == "consolewindowclass"
        or "debug console" in title_lower
        or "kx vision" in title_lower and "console" in title_lower
        or "dummywindow" in class_lower
    ):
        return None

    score = 1_000_000 if is_mapped else 0
    if "arenanet" in class_lower or "dx_window" in class_lower:
        score += 50_000
    if title_lower == "guild wars 2":
        score += 30_000
    elif "guild wars 2" in title_lower:
        score += 15_000
    if visible:
        score += 500
    if not owner_hwnd:
        score += 200
    if enabled:
        score += 100

    # A render window is normally the largest top-level window in the GW2 PID.
    # Cap this component so class/title identity remains more important.
    area = max(0, int(width)) * max(0, int(height))
    score += min(area // 1000, 5_000)
    return score


def _usable_gw2_hwnd(hwnd, pid):
    """Check that a cached HWND still belongs to GW2 and is not its console."""
    if not hwnd:
        return False
    try:
        import win32process

        if not win32gui.IsWindow(hwnd):
            return False
        _, owner_pid = win32process.GetWindowThreadProcessId(hwnd)
        if int(owner_pid) != int(pid):
            return False

        class_name = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
        return _score_gw2_window_candidate(
            class_name,
            title,
            0,
            0,
            0,
            True,
            True,
            int(hwnd) == _pmdbg_mapped_hwnd_for_pid(pid),
        ) is not None
    except Exception:
        return False


def get_hwnd_from_pid(pid):
    """Resolve the GW2 render HWND, never an arbitrary last same-PID window."""
    import win32process

    pid = int(pid)
    mapped_hwnd = _pmdbg_mapped_hwnd_for_pid(pid)
    candidates = []

    def callback(hwnd, _):
        try:
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if int(found_pid) != pid:
                return True

            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
            visible = bool(win32gui.IsWindowVisible(hwnd))
            enabled = bool(win32gui.IsWindowEnabled(hwnd))
            owner_hwnd = int(win32gui.GetWindow(hwnd, 4) or 0)  # GW_OWNER
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, right - left)
            height = max(0, bottom - top)
            score = _score_gw2_window_candidate(
                class_name,
                title,
                width,
                height,
                owner_hwnd,
                visible,
                enabled,
                int(hwnd) == mapped_hwnd,
            )
            candidates.append({
                "hwnd": int(hwnd),
                "class": class_name,
                "title": title,
                "width": width,
                "height": height,
                "visible": visible,
                "owner": owner_hwnd,
                "score": score,
                "mapped": int(hwnd) == mapped_hwnd,
            })
        except Exception as exc:
            print(
                f"[WindowSelect] skipped hwnd=0x{int(hwnd):X}: {exc}"
            )
        return True

    win32gui.EnumWindows(callback, None)

    # Some display modes can temporarily hide a valid mapped render HWND from
    # EnumWindows. Preserve the DLL's exact HWND as a last-resort candidate.
    if mapped_hwnd and not any(c["hwnd"] == mapped_hwnd for c in candidates):
        try:
            candidates.append({
                "hwnd": mapped_hwnd,
                "class": win32gui.GetClassName(mapped_hwnd),
                "title": win32gui.GetWindowText(mapped_hwnd),
                "width": 0,
                "height": 0,
                "visible": bool(win32gui.IsWindowVisible(mapped_hwnd)),
                "owner": 0,
                "score": 1_000_000,
                "mapped": True,
            })
        except Exception:
            pass

    for candidate in candidates:
        score_text = "REJECT" if candidate["score"] is None else str(candidate["score"])
        print(
            "[WindowSelect] candidate "
            f"hwnd=0x{candidate['hwnd']:X} score={score_text} "
            f"mapped={int(candidate['mapped'])} visible={int(candidate['visible'])} "
            f"size={candidate['width']}x{candidate['height']} "
            f"class={candidate['class']!r} title={candidate['title']!r}"
        )

    eligible = [c for c in candidates if c["score"] is not None]
    if not eligible:
        print(
            f"[WindowSelect] {_GW2_WINDOW_RESOLVER_BUILD} found no usable "
            f"GW2 window for pid={pid}"
        )
        return None

    selected = max(eligible, key=lambda c: (c["score"], c["hwnd"]))
    source = "DLL_MAP" if selected["mapped"] else "PID_SCORE"
    print(
        f"[WindowSelect] {_GW2_WINDOW_RESOLVER_BUILD} selected "
        f"hwnd=0x{selected['hwnd']:X} source={source} "
        f"class={selected['class']!r} title={selected['title']!r}"
    )
    return selected["hwnd"]


def ensure_gw2_hwnd():
    """Return a freshly validated render HWND before posting background input."""
    global current_hwnd

    pid = _last_logged_pid or getattr(pm, "process_id", None)
    if not pid:
        return None
    if _usable_gw2_hwnd(current_hwnd, pid):
        return current_hwnd

    previous = int(current_hwnd or 0)
    current_hwnd = get_hwnd_from_pid(pid)
    print(
        "[WindowSelect] corrected cached target "
        f"old=0x{previous:X} new=0x{int(current_hwnd or 0):X}"
    )
    return current_hwnd

def connect(pid=None):
    global pm, mumble, shared_entities, event_probe, live_events, _last_logged_pid, current_hwnd
    import pymem

    try:
        if pid:
            new_pm = pymem.Pymem()
            new_pm.open_process_from_id(pid)

            pm = new_pm
            _last_logged_pid = pid  # <-- PINDAHKAN KE SINI

            mumble = MumbleData()
            shared_entities = SharedEntityData()
            if event_probe is not None:
                try:
                    event_probe.close()
                except Exception:
                    pass
            event_probe = EventProbeBridge()
            if live_events is not None:
                try:
                    live_events.close()
                except Exception:
                    pass
            live_events = LiveEventBridge()
                    
            # --- ARCDPS BRIDGE INIT ---
            if BridgeNameLookup is not None:
                try:
                    shared_entities.bridge_names = BridgeNameLookup()
                    if shared_entities.bridge_names.is_connected():
                        shared_entities.bridge_names.start_auto_update(2.0)
                        print("[Core] ✓ Bridge ready")
                    # bridge_names stays even if not connected — cache still loads
                except Exception as e:
                    print(f"[Core] Bridge init failed: {e}")
                    shared_entities.bridge_names = None

            # 🔥 THIS IS THE IMPORTANT PART
            current_hwnd = get_hwnd_from_pid(pid)

            print(f"[Core] Attached to PID {pid}")
            print(f"[Core] HWND: {current_hwnd}")

            return pid

        return list_gw2_processes()

    except Exception as e:
        print("[Core] Attach failed:", e)
        pm = None
        current_hwnd = None
        return None


def get_event_probe_status():
    """Return the current DLL probe state without blocking the UI."""
    global event_probe
    if event_probe is None:
        event_probe = EventProbeBridge()
    return event_probe.read_status()


def send_event_probe_command(command, guid=""):
    """Queue one capture/reset request using current Mumble map/build/XYZ data."""
    global event_probe
    if event_probe is None:
        event_probe = EventProbeBridge()

    map_id = 0
    build_id = 0
    position = (0.0, 0.0, 0.0)
    try:
        data = mumble.read() if mumble else None
        if data:
            map_id = int(data.get("map_id", 0) or 0)
            build_id = int(data.get("build_id", 0) or 0)
            position = tuple(data.get("pos", position))
    except Exception:
        pass

    return event_probe.send_command(
        command, guid=guid, map_id=map_id,
        build_id=build_id, player_position=position)


def get_live_event_status():
    """Return a consistent snapshot of actual live event-coordinate records."""
    global live_events
    if live_events is None:
        live_events = LiveEventBridge()
    return live_events.read_snapshot()


def get_live_event_records():
    """Compatibility helper used by gw2x_logic.EventDetector."""
    return get_live_event_status()

def get_addr(base_offset, offsets):
    if not pm: return 0
    try:
        addr = pm.read_longlong(pm.base_address + base_offset)
        for offset in offsets[:-1]:
            addr = pm.read_longlong(addr + offset)
        return addr + offsets[-1]
    except: return 0
# ===============================
# BASE CORE ADDRESS AUTO-DETECTION
# ===============================
# Scans the module data section for the static pointer that is base_core_address.
# Validates by following MULTIPLE chains simultaneously — false positive probability
# is essentially zero when all chains must produce plausible values at once.
#
# Chains validated (all rooted at the candidate pointer):
#   Speed:    [152, 56, 80, 696/692/688] → float 0–1000, all 3 equal
#   Position: [152, 80, 256, 288/292/296] → float plausible world coords
#   Stamina:  [152, 16, 912, 12]          → float 0–100
#   Fishing:  [1368, 96, 24, 128]         → float 0–1 (progress bar, may be 0 if not fishing)
#
# HOW TO UPDATE AFTER PATCH:
#   Nothing to update — this function finds it automatically every time.
#   If it fails, character must be in-game (not on login screen) with speed > 0.

_base_core_cache = None

def _walk_chain(root_ptr, offsets):
    """Walk pointer chain from a root pointer value (not module offset)."""
    addr = root_ptr
    for offset in offsets[:-1]:
        addr = pm.read_longlong(addr + offset)
        if not (0x10000 < addr < 0x0000800000000000):
            return None
    return addr + offsets[-1]

def _validate_candidate(ptr):
    """
    Test a candidate root pointer value against all known chains.
    Returns True only if ALL chains produce plausible values.
    """
    try:
        # --- Level 1: ptr+152 must be a valid heap address (shared by all chains) ---
        p152 = pm.read_longlong(ptr + 152)
        if not (0x10000 < p152 < 0x0000800000000000):
            return False

        # --- Speed: [152, 56, 80, 696/692/688] → all three floats must be equal and 0-1000 ---
        p56 = pm.read_longlong(p152 + 56)
        if not (0x10000 < p56 < 0x0000800000000000):
            return False
        p80 = pm.read_longlong(p56 + 80)
        if not (0x10000 < p80 < 0x0000800000000000):
            return False
        s1 = pm.read_float(p80 + 696)
        s2 = pm.read_float(p80 + 692)
        s3 = pm.read_float(p80 + 688)
        if not (0 < s1 < 1000):
            return False
        if abs(s1 - s2) > 0.01 or abs(s2 - s3) > 0.01:
            return False  # all 3 speed variants must match

        # --- Position: [152, 80, 256, 288/292/296] → plausible world coordinates ---
        p80b = pm.read_longlong(p152 + 80)
        if not (0x10000 < p80b < 0x0000800000000000):
            return False
        p256 = pm.read_longlong(p80b + 256)
        if not (0x10000 < p256 < 0x0000800000000000):
            return False
        px = pm.read_float(p256 + 288)
        pz = pm.read_float(p256 + 292)
        py = pm.read_float(p256 + 296)
        # GW2 world coords in inches — divide by 39.37 gives meters
        # Valid range: roughly -5M to +5M inches (~127km map)
        if not (-5_000_000 < px < 5_000_000): return False
        if not (-5_000_000 < pz < 5_000_000): return False
        if not (-5_000_000 < py < 5_000_000): return False

        # --- Stamina: [152, 16, 912, 12] → float 0-100 ---
        p16 = pm.read_longlong(p152 + 16)
        if not (0x10000 < p16 < 0x0000800000000000):
            return False
        p912 = pm.read_longlong(p16 + 912)
        if not (0x10000 < p912 < 0x0000800000000000):
            return False
        stamina = pm.read_float(p912 + 12)
        if not (0.0 <= stamina <= 100.0):
            return False

        return True

    except:
        return False


def find_base_core_address():
    """
    Scan the module data section for base_core_address.
    Character must be in-game and moving (speed > 0) for best results.
    Typically completes in 2-10 seconds depending on data section size.
    """
    global _base_core_cache

    if not pm:
        print("[BaseCore] pm not connected.")
        return None

    try:
        module = pymem.process.module_from_name(pm.process_handle, "Gw2-64.exe")
        mod_base = module.lpBaseOfDll
        mod_size = module.SizeOfImage
    except Exception as e:
        print(f"[BaseCore] Module lookup failed: {e}")
        return None

    # Data section is in the upper portion of the module image
    # Start at 60% to skip most of the code (.text) section
    scan_start = mod_base + int(mod_size * 0.60)
    scan_end   = mod_base + mod_size - 8

    print(f"[BaseCore] Scanning {(scan_end - scan_start) // 1024 // 1024}MB of data section...")
    found = 0
    addr  = scan_start

    while addr < scan_end:
        try:
            candidate_ptr = pm.read_longlong(addr)

            # Quick pre-filter: must look like a heap pointer
            if 0x10000 < candidate_ptr < 0x0000800000000000:
                if _validate_candidate(candidate_ptr):
                    module_offset = addr - mod_base
                    print(f"[BaseCore] FOUND: module+{hex(module_offset)} → {hex(candidate_ptr)}")
                    print(f"[BaseCore] Validated via speed/position/stamina chains.")
                    _base_core_cache = module_offset
                    _persist_base_core(module_offset)
                    return module_offset

        except:
            pass

        addr += 8  # all static pointers are 8-byte aligned

    print("[BaseCore] Not found. Make sure character is in-game and moving.")
    return None


def ensure_base_core_address():
    """
    Verify current base_core_address is still valid.
    If stale, run find_base_core_address() to rediscover it.
    Call this once after connecting to the game.
    """
    global base_core_address, _base_core_cache

    if _base_core_cache is not None:
        return _base_core_cache

    # Test current value
    if base_core_address:
        try:
            ptr = pm.read_longlong(pm.base_address + base_core_address)
            if _validate_candidate(ptr):
                print(f"[BaseCore] Current {hex(base_core_address)} validated OK.")
                _base_core_cache = base_core_address
                return base_core_address
        except:
            pass
        print(f"[BaseCore] {hex(base_core_address)} is stale. Scanning...")

    result = find_base_core_address()
    if result:
        base_core_address = result
    return result


def _persist_base_core(offset):
    """Save discovered offset to gw2x_address.json."""
    import json as _json, os as _os
    path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "gw2x_address.json")
    try:
        cfg = {}
        if _os.path.exists(path):
            with open(path) as f:
                cfg = _json.load(f)
        cfg["base_core_address"] = hex(offset)
        with open(path, "w") as f:
            _json.dump(cfg, f, indent=4)
        print(f"[BaseCore] Saved {hex(offset)} to gw2x_address.json")
    except Exception as e:
        print(f"[BaseCore] Save failed: {e}")



def is_gw2_running(window_title="Guild Wars 2"):
    return bool(win32gui.FindWindow(None, window_title))

def read_map_id_memory():
    if not pm or not context_base_mem: return 0
    try:
        return pm.read_int(pm.base_address + context_base_mem)
    except: return 0

def read_coords():
    if mumble:
        data = mumble.read()
        if data and "pos" in data: return data["pos"]
    mem_pos = read_coords_memory()
    if mem_pos:
        raw_x, raw_y, raw_z = mem_pos
        scale = 1.2303125 
        return (raw_x / scale, raw_y / scale, raw_z / scale)
    return None

def read_coords_memory():
    if not pm: return None
    try:
        x = pm.read_float(get_addr(xpos_base_mem, xpos_offset_mem))
        y = pm.read_float(get_addr(ypos_base_mem, ypos_offset_mem))
        z = pm.read_float(get_addr(zpos_base_mem, zpos_offset_mem))
        return (x, y, z)
    except: return None

def write_coords(x, y, z):
    if not pm: return
    try:
        addr_x = get_addr(xpos_base_mem, xpos_offset_mem)
        if addr_x: pm.write_float(addr_x, float(x))
        addr_y = get_addr(ypos_base_mem, ypos_offset_mem)
        if addr_y: pm.write_float(addr_y, float(y))
        addr_z = get_addr(zpos_base_mem, zpos_offset_mem)
        if addr_z: pm.write_float(addr_z, float(z))
    except: pass

def write_vertical(y):
    if not pm: return
    try:
        addr_y = get_addr(ypos_base_mem, ypos_offset_mem)
        if addr_y: pm.write_float(addr_y, float(y))
    except: pass

def write_specific_speed(index, value):
    if not pm: return
    try:
        addr = 0
        if index == 0: addr = get_addr(speed_base_mem, speed_offset_mem)
        elif index == 1: addr = get_addr(speed_base_mem1, speed_offset_mem1)
        elif index == 2: addr = get_addr(speed_base_mem2, speed_offset_mem2)
        if addr: pm.write_float(addr, float(value))
    except: pass

# ===============================
# MOUSE POSITION RESOLUTION
# ===============================

MOUSE_AOB_PATTERN = b"\x0F\x11\x86\x00\x03\x00\x00"  # movups [rsi+300], xmm0
_mouse_x_addr   = None  # cached absolute address of mouse X float
_mouse_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gw2x_address.json")


def _load_mouse_config():
    try:
        with open(_mouse_cfg_path) as f:
            cfg = json.load(f)
        base_off = int(cfg["pointer_base_offset"], 16)
        offsets  = [int(o, 16) for o in cfg["pointer_offsets"]]
        return base_off, offsets
    except Exception as e:
        print(f"[MouseCfg] Load failed: {e}")
        return None, None


def _save_mouse_config(base_off, offsets):
    try:
        cfg = {}
        if os.path.exists(_mouse_cfg_path):
            with open(_mouse_cfg_path) as f:
                cfg = json.load(f)
        cfg["pointer_base_offset"] = hex(base_off)
        cfg["pointer_offsets"]     = [hex(o) for o in offsets]
        cfg["version_hint"]        = "aob-derived"
        with open(_mouse_cfg_path, "w") as f:
            json.dump(cfg, f, indent=4)
        print("[MouseCfg] gw2x_address.json updated with AOB-derived offsets.")
    except Exception as e:
        print(f"[MouseCfg] Save failed: {e}")


def _try_pointer_chain(base):
    """Walk CE pointer chain from gw2x_address.json to find mouse X address."""
    base_off, offsets = _load_mouse_config()
    if base_off is None:
        return None
    try:
        addr = base + base_off
        for offset in offsets[:-1]:           # dereference all but last
            addr = pm.read_longlong(addr) + offset
        x_addr = addr + offsets[-1]           # last offset = data, no deref
        test = pm.read_float(x_addr)
        # Raw mouse coords are in inches — valid range is large but non-zero
        if test == 0.0 or not (-100_000_000 < test < 100_000_000):
            raise ValueError(f"Implausible value at pointer end: {test}")
        print(f"[MouseChain] OK → {hex(x_addr)}  raw_x={test:.1f}")
        return x_addr
    except Exception as e:
        print(f"[MouseChain] Failed: {e}")
        return None

def _try_aob(base, save_config=False):
    """
    Dynamically resolve mouse X from a RIP-relative LEA reference.

    Current relationship:

        code AOB
            ↓
        lea rcx,[rip+rel32]
            ↓
        mouse structure base
            ↓ +0x300
        mouse X

    No pointer_base_offset is required for resolution.
    """

    import re
    import struct as _struct

    print("[MouseAOB] Scanning for mouse structure reference...")

    # ---------------------------------------------------------
    # Current code:
    #
    # 48 8B 05 ?? ?? ?? ??
    # 48 8D 0D ?? ?? ?? ??
    # FF 90 88 00 00 00
    #
    # Both rel32 displacements are wildcarded.
    # ---------------------------------------------------------

    pattern = (
        re.escape(bytes.fromhex("48 8B 05"))
        + b"...."
        + re.escape(bytes.fromhex("48 8D 0D"))
        + b"...."
        + re.escape(bytes.fromhex("FF 90 88 00 00 00"))
    )

    match = pm.pattern_scan_module(
        pattern,
        "Gw2-64.exe"
    )

    if not match:
        print("[MouseAOB] Mouse structure AOB not found.")
        return None

    print(
        f"[MouseAOB] Signature found: "
        f"{hex(match)} "
        f"(module+{hex(match - base)})"
    )

    # ---------------------------------------------------------
    # Layout:
    #
    # match+0:
    #   48 8B 05 xx xx xx xx
    #
    # match+7:
    #   48 8D 0D xx xx xx xx
    #
    # So LEA RCX starts at +7.
    # ---------------------------------------------------------

    lea_addr = match + 7

    try:
        lea_bytes = pm.read_bytes(
            lea_addr,
            7
        )

        if lea_bytes[:3] != b"\x48\x8D\x0D":
            print(
                f"[MouseAOB] Expected LEA RCX not found "
                f"at {hex(lea_addr)}"
            )
            return None

        rel32 = _struct.unpack(
            "<i",
            lea_bytes[3:7]
        )[0]

        # RIP-relative:
        #
        # target = address after instruction + displacement
        #
        struct_base = (
            lea_addr
            + 7
            + rel32
        )

        mouse_x_addr = (
            struct_base
            + 0x300
        )

        print(
            f"[MouseAOB] LEA @ {hex(lea_addr)}"
        )

        print(
            f"[MouseAOB] Struct base: "
            f"{hex(struct_base)} "
            f"(module+{hex(struct_base - base)})"
        )

        print(
            f"[MouseAOB] Mouse X candidate: "
            f"{hex(mouse_x_addr)}"
        )

        # -----------------------------------------------------
        # Validate XYZ
        # -----------------------------------------------------

        rx = pm.read_float(mouse_x_addr)
        ry = pm.read_float(mouse_x_addr + 4)
        rz = pm.read_float(mouse_x_addr + 8)

        if not all(
            -100_000_000 < v < 100_000_000
            for v in (rx, ry, rz)
        ):
            print(
                f"[MouseAOB] Invalid XYZ values: "
                f"{rx}, {ry}, {rz}"
            )
            return None

        print(
            f"[MouseAOB] SUCCESS -> "
            f"X={hex(mouse_x_addr)} "
            f"raw=({rx:.1f}, {ry:.1f}, {rz:.1f})"
        )

        return mouse_x_addr

    except Exception as e:
        print(
            f"[MouseAOB] Resolution failed: {e}"
        )
        return None

def reset_mouse_cache():
    """Force re-resolution on next read (call after map load if needed)."""
    global _mouse_x_addr
    _mouse_x_addr = None


def read_mouse_3d_position():
    global _mouse_x_addr

    if not pm:
        return None

    if _mouse_x_addr is None:
        try:
            base = pymem.process.module_from_name(
                pm.process_handle,
                "Gw2-64.exe"
            ).lpBaseOfDll
        except Exception as e:
            print(f"[Mouse] Module base failed: {e}")
            return None

        # AOB-only resolution
        _mouse_x_addr = _try_aob(base)

        if not _mouse_x_addr:
            print("[Mouse] AOB resolution failed.")
            return None

    try:
        rx = pm.read_float(_mouse_x_addr)
        ry = pm.read_float(_mouse_x_addr + 4)
        rz = pm.read_float(_mouse_x_addr + 8)

        conv = 1.0 / 39.37

        mx = rx * conv
        mz = ry * conv
        my = -rz * conv

        return (mx, my, mz)

    except Exception as e:
        print(f"[Mouse] Read failed ({e}), resetting cache.")
        reset_mouse_cache()
        return None

def write_coords_raw(x, y, z):
    """Writes units using unified 1.2303125x engine multiplier."""
    if not pm:
        return False
    try:
        addr_x = get_addr(xpos_base_mem, xpos_offset_mem)
        addr_y = get_addr(ypos_base_mem, ypos_offset_mem)
        addr_z = get_addr(zpos_base_mem, zpos_offset_mem)

        scale = 1.2303125

        if addr_x and addr_y and addr_z:
            pm.write_float(addr_x, float(x * scale))
            pm.write_float(addr_y, float(y * scale))
            pm.write_float(addr_z, float(z * scale))
            print("[Core] Scaled write success.")
            return True
    except Exception as e:
        print("[Core] Write failed:", e)

    return False

# ===============================
# MAP DATA API
# ===============================
MAP_DATA_DB = {}
def fetch_map_data(map_id):
    try:
        url = f"https://api.guildwars2.com/v2/maps/{map_id}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            MAP_DATA_DB[map_id] = {
                'name': data.get('name', f"Map {map_id}"),
                'map_rect': data['map_rect'],
                'continent_rect': data['continent_rect']
            }
            return True
    except: return False

# ===============================
# EVENT DETAILS CACHE
# ===============================
_EVENT_DETAILS_CACHE = {}

def fetch_event_details(guid):
    """Fetch static event metadata (name, location) from v1 API. Cached permanently."""
    if guid in _EVENT_DETAILS_CACHE:
        return _EVENT_DETAILS_CACHE[guid]
    try:
        url = f"https://api.guildwars2.com/v1/event_details.json?event_id={guid}"
        req = urllib.request.Request(url, headers={"User-Agent": "GW2X/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        events = data.get("events", {})
        if guid in events:
            _EVENT_DETAILS_CACHE[guid] = events[guid]
            return events[guid]
    except Exception as e:
        print(f"[EventDetails] Fetch error for {guid[:8]}: {e}")
    return None

def scale_coords(continent_rect, map_rect, coords):
    """Convert map coordinate space → continent coordinate space.
    Matches the official GW2 wiki JS formula exactly.
    coords: [x, y] in map_rect space (from event_details.json)
    returns: [cx, cy] in continent space
    """
    cx = round(continent_rect[0][0] + (
        1.0 * (coords[0] - map_rect[0][0]) /
        (map_rect[1][0] - map_rect[0][0]) *
        (continent_rect[1][0] - continent_rect[0][0])
    ))
    cy = round(continent_rect[0][1] + (
        -1.0 * (coords[1] - map_rect[1][1]) /
        (map_rect[1][1] - map_rect[0][1]) *
        (continent_rect[1][1] - continent_rect[0][1])
    ))
    return [cx, cy]

def scale_length(map_rect, length):
    """Convert event radius/height from inches → continent units.
    Matches the official GW2 wiki JS formula exactly.
    """
    length = length / (1.0 / 24)  # inches → internal unit
    scalex = (length - map_rect[0][0]) / (map_rect[1][0] - map_rect[0][0])
    scaley = (length - map_rect[0][1]) / (map_rect[1][1] - map_rect[0][1])
    return math.sqrt(scalex * scalex + scaley * scaley)

def event_center_to_game_coords(guid, map_id):
    """Full pipeline: event GUID → game meters (x, z).
    Returns (game_x, game_z, radius_meters) or None on failure.
    """
    details = fetch_event_details(guid)
    if not details:
        return None

    loc = details.get("location", {})
    center = loc.get("center")
    radius = loc.get("radius", 0)
    if not center or len(center) < 2:
        return None

    # Ensure map data is loaded
    if map_id not in MAP_DATA_DB:
        if not fetch_map_data(map_id):
            return None

    info = MAP_DATA_DB[map_id]
    mr = info['map_rect']
    cr = info['continent_rect']

    # Step 1: map coords → continent coords
    cont = scale_coords(cr, mr, center)

    # Step 2: continent coords → game meters (reuse existing function)
    game = continent_to_game_coords(cont[0], cont[1], map_id)
    if not game:
        return None

    # Step 3: scale radius (continent units → meters approx)
    # continent unit ≈ 1 inch, so divide by 39.3701 for meters
    radius_m = radius / 39.3701

    return (game[0], game[2], radius_m)  # x, z (ignore y=0), radius in meters

def get_map_name(map_id):
    if map_id in MAP_DATA_DB: return MAP_DATA_DB[map_id].get('name', str(map_id))
    return str(map_id)

def continent_to_game_coords(c_x, c_y, map_id):
    if map_id not in MAP_DATA_DB:
        if not fetch_map_data(map_id): return None 
    info = MAP_DATA_DB[map_id]
    mr = info['map_rect']; cr = info['continent_rect']
    
    m_width = (mr[1][0] - mr[0][0])
    c_width = (cr[1][0] - cr[0][0])
    
    if c_width == 0: return None
    
    pct_x = (c_x - cr[0][0]) / c_width
    pct_y = (c_y - cr[0][1]) / (cr[1][1] - cr[0][1])
    
    game_x_inch = mr[0][0] + (m_width * pct_x)
    game_z_inch = mr[0][1] + ((mr[1][1] - mr[0][1]) * (1-pct_y))
    
    # Simple conversion back to meters (standard logic)
    return (game_x_inch / 39.37, 0, game_z_inch / 39.37) 

def update_map_hover(map_x, map_y):
    _last_map_hover["map_x"] = map_x
    _last_map_hover["map_y"] = map_y
    _last_map_hover["timestamp"] = time.time()

def get_last_map_hover():
    return _last_map_hover.copy()
    
# ===============================
# BACKGROUND INPUT (UPDATED)
# ===============================
_PMDBG_BUILD_ID = "PMDBG-20260818-R1"
_PMDBG_MESSAGE_NAME = "GW2X_POSTMESSAGE_DIAG_V1"
_PMDBG_MAPPING_NAME = "Local\\GW2X_POSTMESSAGE_DIAG_V1"
_PMDBG_MAGIC = 0x31444D50  # "PMD1"
_PMDBG_VERSION = 1
_PMDBG_FILE_MAP_READ = 0x0004
_PMDBG_ENABLED = os.environ.get("GW2X_PMDBG", "1").strip().lower() not in {
    "0", "false", "off", "no"
}

_pmdbg_user32 = ctypes.WinDLL("user32", use_last_error=True)
_pmdbg_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PostMessage = _pmdbg_user32.PostMessageW
PostMessage.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
PostMessage.restype = wintypes.BOOL

MapVirtualKey = _pmdbg_user32.MapVirtualKeyW
MapVirtualKey.argtypes = [wintypes.UINT, wintypes.UINT]
MapVirtualKey.restype = wintypes.UINT

_pmdbg_register_message = _pmdbg_user32.RegisterWindowMessageW
_pmdbg_register_message.argtypes = [wintypes.LPCWSTR]
_pmdbg_register_message.restype = wintypes.UINT

_pmdbg_is_window = _pmdbg_user32.IsWindow
_pmdbg_is_window.argtypes = [wintypes.HWND]
_pmdbg_is_window.restype = wintypes.BOOL

_pmdbg_get_foreground_window = _pmdbg_user32.GetForegroundWindow
_pmdbg_get_foreground_window.argtypes = []
_pmdbg_get_foreground_window.restype = wintypes.HWND

_pmdbg_get_window_thread_process_id = _pmdbg_user32.GetWindowThreadProcessId
_pmdbg_get_window_thread_process_id.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
_pmdbg_get_window_thread_process_id.restype = wintypes.DWORD

_pmdbg_open_file_mapping = _pmdbg_kernel32.OpenFileMappingW
_pmdbg_open_file_mapping.argtypes = [
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
_pmdbg_open_file_mapping.restype = wintypes.HANDLE

_pmdbg_map_view = _pmdbg_kernel32.MapViewOfFile
_pmdbg_map_view.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_size_t,
]
_pmdbg_map_view.restype = ctypes.c_void_p

_pmdbg_unmap_view = _pmdbg_kernel32.UnmapViewOfFile
_pmdbg_unmap_view.argtypes = [ctypes.c_void_p]
_pmdbg_unmap_view.restype = wintypes.BOOL

_pmdbg_close_handle = _pmdbg_kernel32.CloseHandle
_pmdbg_close_handle.argtypes = [wintypes.HANDLE]
_pmdbg_close_handle.restype = wintypes.BOOL

_PMDBG_REGISTERED_MESSAGE = _pmdbg_register_message(_PMDBG_MESSAGE_NAME)


class _PostMessageDiagShared(ctypes.Structure):
    """Must match PostMessageDiagShared in D3DRenderHook_WndProc.cpp."""
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("ready", ctypes.c_int32),
        ("dll_pid", ctypes.c_uint32),
        ("hwnd_value", ctypes.c_uint64),
        ("original_wndproc", ctypes.c_uint64),
        ("current_wndproc", ctypes.c_uint64),
        ("wndproc_thread_id", ctypes.c_uint32),
        ("window_thread_id", ctypes.c_uint32),
        ("probe_count", ctypes.c_int32),
        ("total_key_down", ctypes.c_int32),
        ("total_key_up", ctypes.c_int32),
        ("tagged_key_down", ctypes.c_int32),
        ("tagged_key_up", ctypes.c_int32),
        ("forwarded_tagged", ctypes.c_int32),
        ("last_probe_seq", ctypes.c_int32),
        ("last_probe_vk", ctypes.c_int32),
        ("last_probe_phase", ctypes.c_int32),
        ("last_message", ctypes.c_int32),
        ("last_key_vk", ctypes.c_int32),
        ("last_focused", ctypes.c_int32),
        ("last_forward_result", ctypes.c_int64),
        ("last_foreground_hwnd", ctypes.c_int64),
        ("last_error", ctypes.c_int32),
        ("last_tick", ctypes.c_int32),
        ("build_id", ctypes.c_char * 32),
    ]


if ctypes.sizeof(_PostMessageDiagShared) != 152:
    print(
        f"[PMDBG-PY] ERROR shared layout is "
        f"{ctypes.sizeof(_PostMessageDiagShared)} bytes, expected 152"
    )

_pmdbg_send_lock = threading.Lock()
_pmdbg_timer_lock = threading.Lock()
_pmdbg_timer = None
_pmdbg_sequence = 0
_pmdbg_verbose_remaining = 40
_pmdbg_target_logged = None
_pmdbg_marker_ready = False
_pmdbg_marker_hwnd = 0


def _pmdbg_window_details(hwnd):
    """Return safe target-window details without changing focus."""
    details = {
        "hwnd": int(hwnd or 0),
        "valid": False,
        "pid": 0,
        "tid": 0,
        "class": "",
        "title": "",
        "foreground": int(_pmdbg_get_foreground_window() or 0),
    }
    if not hwnd:
        return details

    try:
        details["valid"] = bool(_pmdbg_is_window(hwnd))
        process_id = wintypes.DWORD(0)
        details["tid"] = int(
            _pmdbg_get_window_thread_process_id(hwnd, ctypes.byref(process_id))
        )
        details["pid"] = int(process_id.value)
        details["class"] = win32gui.GetClassName(hwnd)
        details["title"] = win32gui.GetWindowText(hwnd)
    except Exception as exc:
        details["detail_error"] = str(exc)
    return details


def _pmdbg_read_snapshot():
    """Read the diagnostic mapping created by the injected DLL."""
    ctypes.set_last_error(0)
    mapping = _pmdbg_open_file_mapping(
        _PMDBG_FILE_MAP_READ,
        False,
        _PMDBG_MAPPING_NAME,
    )
    if not mapping:
        return None, ctypes.get_last_error()

    view = None
    try:
        ctypes.set_last_error(0)
        view = _pmdbg_map_view(
            mapping,
            _PMDBG_FILE_MAP_READ,
            0,
            0,
            ctypes.sizeof(_PostMessageDiagShared),
        )
        if not view:
            return None, ctypes.get_last_error()

        raw = ctypes.string_at(view, ctypes.sizeof(_PostMessageDiagShared))
        return _PostMessageDiagShared.from_buffer_copy(raw), 0
    finally:
        if view:
            _pmdbg_unmap_view(view)
        _pmdbg_close_handle(mapping)


def _pmdbg_marker_is_ready(hwnd):
    """Send markers only when the matching debug DLL mapping exists.

    This keeps non-DLL mode on the exact original PostMessage-only path.
    """
    global _pmdbg_marker_ready, _pmdbg_marker_hwnd
    numeric_hwnd = int(hwnd or 0)
    if _pmdbg_marker_ready and _pmdbg_marker_hwnd == numeric_hwnd:
        return True

    snapshot, _ = _pmdbg_read_snapshot()
    if (
        snapshot is not None
        and snapshot.magic == _PMDBG_MAGIC
        and snapshot.version == _PMDBG_VERSION
        and snapshot.ready
        and int(snapshot.hwnd_value) == numeric_hwnd
    ):
        _pmdbg_marker_ready = True
        _pmdbg_marker_hwnd = numeric_hwnd
        return True
    return False


def debug_postmessage_status():
    """Print an end-to-end Python -> DLL WndProc diagnostic snapshot."""
    target = int(ensure_gw2_hwnd() or 0)
    window = _pmdbg_window_details(target)
    print(
        "[PMDBG-PY] TARGET "
        f"hwnd=0x{target:X} valid={int(window['valid'])} "
        f"pid={window['pid']} tid={window['tid']} "
        f"foreground=0x{window['foreground']:X} "
        f"class={window['class']!r} title={window['title']!r}"
    )

    snapshot, error = _pmdbg_read_snapshot()
    if snapshot is None:
        print(
            "[PMDBG-PY] DLL_MAP_MISSING "
            f"error={error}. The debug DLL is not loaded, its WndProc is not "
            "installed on this window, or the build is still the old DLL."
        )
        return None

    build_id = bytes(snapshot.build_id).split(b"\0", 1)[0].decode(
        "ascii", errors="replace"
    )
    tagged_total = int(snapshot.tagged_key_down + snapshot.tagged_key_up)
    probe_count = int(snapshot.probe_count)
    forwarded = int(snapshot.forwarded_tagged)

    print(
        "[PMDBG-PY] DLL "
        f"build={build_id!r} magic=0x{snapshot.magic:08X} "
        f"version={snapshot.version} ready={snapshot.ready} "
        f"pid={snapshot.dll_pid} hwnd=0x{snapshot.hwnd_value:X} "
        f"wndprocTid={snapshot.wndproc_thread_id} "
        f"windowTid={snapshot.window_thread_id}"
    )
    print(
        "[PMDBG-PY] PATH "
        f"probes={probe_count} "
        f"totalDown/Up={snapshot.total_key_down}/{snapshot.total_key_up} "
        f"taggedDown/Up={snapshot.tagged_key_down}/{snapshot.tagged_key_up} "
        f"forwarded={forwarded} lastSeq={snapshot.last_probe_seq} "
        f"lastMsg=0x{snapshot.last_message & 0xFFFFFFFF:04X} "
        f"lastVK=0x{snapshot.last_key_vk & 0xFFFFFFFF:02X} "
        f"focused={snapshot.last_focused} "
        f"result={snapshot.last_forward_result} error={snapshot.last_error}"
    )
    print(
        "[PMDBG-PY] WNDPROC "
        f"original=0x{snapshot.original_wndproc:X} "
        f"current=0x{snapshot.current_wndproc:X} "
        f"foreground=0x{snapshot.last_foreground_hwnd & 0xFFFFFFFFFFFFFFFF:X}"
    )

    problem = None
    if snapshot.magic != _PMDBG_MAGIC or snapshot.version != _PMDBG_VERSION:
        problem = "BAD_LAYOUT: Python and DLL debugger versions do not match."
    elif build_id != _PMDBG_BUILD_ID:
        problem = "OLD_DLL: loaded DLL does not contain this debugger build."
    elif not snapshot.ready:
        problem = "DLL_NOT_READY: diagnostic mapping exists but WndProc is not ready."
    elif int(snapshot.hwnd_value) != target:
        problem = (
            "HWND_MISMATCH: Python posts to a different window than the DLL "
            "WndProc hook."
        )
    elif int(snapshot.dll_pid) != int(window["pid"]):
        problem = "PID_MISMATCH: selected HWND is not owned by the injected process."
    elif not snapshot.original_wndproc:
        problem = "NO_ORIGINAL_WNDPROC: DLL did not retain GW2's original WndProc."
    elif probe_count == 0:
        problem = "NO_PROBE: Python diagnostic messages did not reach the DLL WndProc."
    elif probe_count - tagged_total > 2:
        problem = (
            "KEY_MISSING: diagnostic markers arrive, but their WM_KEYDOWN/UP "
            "messages do not arrive."
        )
    elif tagged_total - forwarded > 1:
        problem = "NOT_FORWARDED: DLL receives tagged keys but does not forward them."
    elif tagged_total > 0 and forwarded >= tagged_total:
        problem = (
            "PATH_OK: PostMessage reached the DLL and the DLL called GW2's "
            "original WndProc. If the skill still does nothing, the failure is "
            "after the original WndProc."
        )

    if problem:
        print(f"[PMDBG-PY] DIAGNOSIS {problem}")
    return snapshot


def _pmdbg_report_worker():
    global _pmdbg_timer
    try:
        debug_postmessage_status()
    except Exception as exc:
        print(f"[PMDBG-PY] Reporter error: {exc}")
    finally:
        with _pmdbg_timer_lock:
            _pmdbg_timer = None


def _pmdbg_schedule_report():
    global _pmdbg_timer
    if not _PMDBG_ENABLED:
        return
    with _pmdbg_timer_lock:
        if _pmdbg_timer is not None:
            return
        _pmdbg_timer = threading.Timer(0.20, _pmdbg_report_worker)
        _pmdbg_timer.daemon = True
        _pmdbg_timer.start()


def _pmdbg_log_target_once(hwnd):
    global _pmdbg_target_logged
    numeric_hwnd = int(hwnd or 0)
    if _pmdbg_target_logged == numeric_hwnd:
        return
    _pmdbg_target_logged = numeric_hwnd
    details = _pmdbg_window_details(hwnd)
    print(
        "[PMDBG-PY] USING_TARGET "
        f"hwnd=0x{numeric_hwnd:X} valid={int(details['valid'])} "
        f"pid={details['pid']} tid={details['tid']} "
        f"class={details['class']!r} title={details['title']!r}"
    )


def _pmdbg_post_key(hwnd, message, scan_code, vk_code, lparam, phase):
    """Post one ordinary key message with an adjacent diagnostic marker."""
    global _pmdbg_sequence, _pmdbg_verbose_remaining

    with _pmdbg_send_lock:
        _pmdbg_sequence = (_pmdbg_sequence + 1) & 0x7FFFFFFF
        if _pmdbg_sequence == 0:
            _pmdbg_sequence = 1
        sequence = _pmdbg_sequence

        marker_ok = None
        marker_error = 0
        marker_active = _PMDBG_ENABLED and _pmdbg_marker_is_ready(hwnd)
        if marker_active:
            if _PMDBG_REGISTERED_MESSAGE:
                payload = (int(vk_code) & 0xFFFF) | ((int(phase) & 0xFF) << 16)
                ctypes.set_last_error(0)
                marker_ok = bool(
                    PostMessage(
                        hwnd,
                        _PMDBG_REGISTERED_MESSAGE,
                        sequence,
                        payload,
                    )
                )
                marker_error = 0 if marker_ok else ctypes.get_last_error()
            else:
                marker_ok = False
                marker_error = ctypes.get_last_error()

        ctypes.set_last_error(0)
        key_ok = bool(PostMessage(hwnd, message, vk_code, lparam))
        key_error = 0 if key_ok else ctypes.get_last_error()

    _pmdbg_log_target_once(hwnd)
    if _PMDBG_ENABLED and (
        _pmdbg_verbose_remaining > 0
        or not key_ok
        or (marker_active and not marker_ok)
    ):
        _pmdbg_verbose_remaining = max(0, _pmdbg_verbose_remaining - 1)
        phase_name = "DOWN" if phase == 1 else "UP"
        if not marker_active:
            marker_status = "SKIP(no matching debug DLL map)"
        else:
            marker_status = (
                f"{'OK' if marker_ok else 'FAIL'}({marker_error})"
            )
        print(
            "[PMDBG-PY] POST "
            f"seq={sequence} phase={phase_name} "
            f"scan=0x{int(scan_code):02X} vk=0x{int(vk_code):02X} "
            f"marker={marker_status} "
            f"key={'OK' if key_ok else 'FAIL'}({key_error})"
        )

    _pmdbg_schedule_report()
    return key_ok


print(
    f"[PMDBG-PY] Loaded {_PMDBG_BUILD_ID}; "
    f"enabled={int(_PMDBG_ENABLED)} message=0x{_PMDBG_REGISTERED_MESSAGE:04X}"
)

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102       # <--- ADDED THIS
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDBLCLK = 0x0203 

def get_virtual_key(scan_code_hex):
    """Konversi Hex String ke Int Scan Code & Virtual Key"""
    try:
        if isinstance(scan_code_hex, int):
            scan_code = scan_code_hex
        else:
            scan_code = int(scan_code_hex, 16)
        vk_code = MapVirtualKey(scan_code, 1) # MAPVK_VSC_TO_VK
        return scan_code, vk_code
    except Exception as exc:
        if _PMDBG_ENABLED:
            print(f"[PMDBG-PY] Invalid scan code {scan_code_hex!r}: {exc}")
        return 0, 0

def send_background_down(window_title, hex_scan_code):
    """Mengirim sinyal KEY DOWN ke window tertentu tanpa fokus"""
    try:
        hwnd = ensure_gw2_hwnd()
        if not hwnd:
            print("[PMDBG-PY] DOWN blocked: current_hwnd is empty")
            return False
        
        scan_code, vk_code = get_virtual_key(hex_scan_code)
        if vk_code == 0:
            print(f"[PMDBG-PY] DOWN blocked: scan={hex_scan_code!r} maps to VK 0")
            return False

        lparam = 1 | (scan_code << 16)
        return _pmdbg_post_key(
            hwnd,
            WM_KEYDOWN,
            scan_code,
            vk_code,
            lparam,
            1,
        )
    except Exception as e:
        print(f"[BgInput] Down Error: {e}")
        return False

def send_background_up(window_title, hex_scan_code):
    """Mengirim sinyal KEY UP ke window tertentu tanpa fokus"""
    try:
        hwnd = ensure_gw2_hwnd()
        if not hwnd:
            print("[PMDBG-PY] UP blocked: current_hwnd is empty")
            return False

        scan_code, vk_code = get_virtual_key(hex_scan_code)
        if vk_code == 0:
            print(f"[PMDBG-PY] UP blocked: scan={hex_scan_code!r} maps to VK 0")
            return False

        lparam = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)
        return _pmdbg_post_key(
            hwnd,
            WM_KEYUP,
            scan_code,
            vk_code,
            lparam,
            2,
        )
    except Exception as e:
        print(f"[BgInput] Up Error: {e}")
        return False

def send_background_key(window_title, hex_scan_code, duration=0.05):
    """Tekan dan Lepas (Tap) di background"""
    down_ok = send_background_down(window_title, hex_scan_code)
    time.sleep(float(duration))
    up_ok = send_background_up(window_title, hex_scan_code)
    return bool(down_ok and up_ok)

def presskey(window_title, hex_key_code, duration=0.05):
    """Wrapper fungsi presskey agar gw2x_ui.py tidak error Import."""
    return send_background_key(window_title, hex_key_code, duration)

def send_chat_message(window_title, text):
    """
    Mengirim pesan menggunakan SendInput (Hardware Level) dengan mekanisme
    Alt-Key Hack untuk mem-bypass OS ForegroundLockTimeout.
    """
    import ctypes
    import time
    import win32gui
    import win32con

    hwnd = current_hwnd
    if not hwnd: 
        print("[Core] Error: HWND target tidak valid.")
        return

    user32 = ctypes.windll.user32
    fg_hwnd = user32.GetForegroundWindow()

    # --- 1. BYPASS OS FOREGROUND LOCK (THE ALT-KEY HACK) ---
    if fg_hwnd != hwnd:
        # Trik Win32: Simulasi tekan & lepas tombol ALT mengelabui Windows 
        # untuk memberikan izin perpindahan fokus ke thread ini.
        VK_MENU = 0x12
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, 0x0002, 0) # KEYEVENTF_KEYUP
        
        # Eksekusi perpindahan
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"[Core] SetForegroundWindow API gagal: {e}")

        # Verifikasi Loop: Tahan eksekusi skrip sampai game benar-benar di depan
        timeout = 15 # Maksimal tunggu 1.5 detik
        while user32.GetForegroundWindow() != hwnd and timeout > 0:
            time.sleep(0.1)
            timeout -= 1

    if user32.GetForegroundWindow() != hwnd:
        print("[Core] GAGAL: Windows mengunci fokus secara absolut. Injeksi dibatalkan agar teks tidak nyasar ke konsol.")
        return

    time.sleep(0.1) # Jeda kritis agar engine GW2 siap menerima input pasca-fokus

    # --- 2. INJEKSI UNICODE HARDWARE ---
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    def send_unicode_char(char):
        extra = ctypes.c_ulong(0)
        
        # DOWN
        ii_down = Input_I()
        ii_down.ki = KeyBdInput(0, ord(char), KEYEVENTF_UNICODE, 0, ctypes.pointer(extra))
        x_down = Input(ctypes.c_ulong(1), ii_down)
        user32.SendInput(1, ctypes.pointer(x_down), ctypes.sizeof(x_down))
        
        # UP
        ii_up = Input_I()
        ii_up.ki = KeyBdInput(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
        x_up = Input(ctypes.c_ulong(1), ii_up)
        user32.SendInput(1, ctypes.pointer(x_up), ctypes.sizeof(x_up))

    # Buka Chat (Tekan Enter fisik: Scan code 0x1C)
    PressKey(0x1C)
    time.sleep(0.05)
    ReleaseKey(0x1C)
    
    time.sleep(0.2) # Jeda render UI Chat

    # Eksekusi Teks
    for char in text:
        send_unicode_char(char)
        time.sleep(0.01) 

    time.sleep(0.1)

    # Kirim Pesan (Enter)
    PressKey(0x1C)
    time.sleep(0.05)
    ReleaseKey(0x1C)

    # --- 3. KEMBALIKAN FOKUS KE UI PYTHON ---
    if fg_hwnd and fg_hwnd != hwnd:
        time.sleep(0.1)
        user32.SetForegroundWindow(fg_hwnd)

# --- Mouse Click Helper (Preserved) ---
def mouse_click(x, y):
    try:
        hwnd = hwnd = current_hwnd
        if not hwnd: return
        screen_point = (int(x), int(y))
        client_point = win32gui.ScreenToClient(hwnd, screen_point)
        c_x, c_y = client_point
        lParam = (c_y << 16) | (c_x & 0xFFFF)
        PostMessage(hwnd, 0x0200, 0, lParam)
        time.sleep(0.1)
        PostMessage(hwnd, 0x0201, 0x0001, lParam)
        time.sleep(0.05)
        PostMessage(hwnd, 0x0202, 0, lParam)
    except: pass
    
# ... [KEEP ALL REST OF THE FILE (Threading, Energy, Direct Input)] ...
# Ensure you keep the rest of the file (enable_mountstamina_loop, etc.)
# just like in your original file. I am only showing the changed input section above.

# ===============================
# THREADING & ENERGY LOGIC (RESTORED)
# ===============================
stamina_stop_event = threading.Event()
skyscale_stop_event = threading.Event()

def enable_mountstamina_loop():
    while not stamina_stop_event.is_set():
        try:
            if pm:
                addr = get_addr(mountstamina_base_mem, mountstamina_offset_mem)
                if addr: pm.write_float(addr, 100.0)
            time.sleep(1.0)
        except: time.sleep(1.0)

# ===============================
# SKYSCALE LOGIC (FIXED)
# ===============================
skyscale_stop_event = threading.Event()

# def enable_skyscale_loop():
#     logging.info("[Skyscale] Loop injeksi Skyscale bar dimulai.")
    
#     while not skyscale_stop_event.is_set():
#         try:
#             # Memastikan process memory dan variabel offset tersedia
#             if pm and skyscalegreenbaraddress:
#                 # Menghitung alamat absolut berdasarkan base address + static offset dari server
#                 target_addr = pm.base_address + skyscalegreenbaraddress
#                 pm.write_ushort(target_addr, 37008)  # Nilai modifikasi Skyscale Infinite
            
#             time.sleep(0.1) # Loop rate 10Hz
#         except Exception as e:
#             logging.error(f"[Skyscale] Gagal menulis ke memori: {e}")
#             time.sleep(0.5)
            
#     logging.info("[Skyscale] Loop injeksi dihentikan.")

# def toggle_skyscale_wall(active):
#     global skyscale_thread
    
#     if active:
#         if 'skyscale_thread' in globals() and skyscale_thread and skyscale_thread.is_alive():
#             logging.warning("[Skyscale] Thread sudah aktif. Mengabaikan perintah start.")
#             return

#         logging.info("[Skyscale] Mengaktifkan Infinite Wall.")
#         skyscale_stop_event.clear()
#         skyscale_thread = threading.Thread(target=enable_skyscale_loop, daemon=True)
#         skyscale_thread.start()

#     else:
#         logging.info("[Skyscale] Menonaktifkan Infinite Wall.")
#         skyscale_stop_event.set()

#         if pm and skyscalegreenbaraddress:
#             try:
#                 target_addr = pm.base_address + skyscalegreenbaraddress
#                 pm.write_ushort(target_addr, 4083)  # Kembalikan ke nilai standar engine
#                 logging.info("[Skyscale] Nilai default 4083 berhasil dikembalikan.")
#             except Exception as e:
#                 logging.error(f"[Skyscale] Gagal mengembalikan nilai default: {e}")

def toggle_mount_stamina(active):
    global stamina_thread
    if active:
        if stamina_thread and stamina_thread.is_alive(): return
        stamina_stop_event.clear()
        stamina_thread = threading.Thread(target=enable_mountstamina_loop, daemon=True)
        stamina_thread.start()
    else:
        stamina_stop_event.set()

def set_mount_stamina(active):
    toggle_mount_stamina(active)

def double_click_background(x, y):
    try:
        hwnd = current_hwnd
        if not hwnd: return
        screen_point = (int(x), int(y))
        client_point = win32gui.ScreenToClient(hwnd, screen_point)
        c_x, c_y = client_point
        lParam = (c_y << 16) | (c_x & 0xFFFF)
        PostMessage(hwnd, WM_MOUSEMOVE, 0, lParam)
        time.sleep(0.05)
        PostMessage(hwnd, WM_LBUTTONDOWN, 0x0001, lParam)
        PostMessage(hwnd, WM_LBUTTONUP, 0, lParam)
        time.sleep(0.05)
        PostMessage(hwnd, WM_LBUTTONDBLCLK, 0x0001, lParam)
        PostMessage(hwnd, WM_LBUTTONUP, 0, lParam)
        print(f"[Core] Native Double Click sent at {x}, {y}")
    except: pass
        
def get_window_center(window_title):
    try:
        hwnd = current_hwnd
        if not hwnd: return None
        rect = win32gui.GetWindowRect(hwnd)
        x, y, w, h = rect
        return (x + w) // 2, (y + h) // 2
    except: return None
    
# ===============================
# DIRECT INPUT (REQUIRED FOR FISHING)
# ===============================
# Struktur C++ untuk SendInput (Windows API) agar bisa menahan tombol
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

def PressKey(hexKeyCode):
    """Menahan tombol (Hold)"""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    # 0x0008 = KEYEVENTF_SCANCODE
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def ReleaseKey(hexKeyCode):
    """Melepas tombol (Release)"""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    # 0x0008 | 0x0002 = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def get_def_name(entity_id, default_name=None):
    data = _NPC_DB.get(str(entity_id))
    return data.get("name", default_name) if isinstance(data, dict) else default_name

def get_def_type(entity_id):
    data = _NPC_DB.get(str(entity_id))
    return data.get("type", "") if isinstance(data, dict) else ""

def save_custom_data(ent, new_name=None, new_type=None):
    global _NPC_DB, _OBJ_DB, mumble
    import math

    species_id = str(ent.get('species_id', '')).strip()
    is_npc = bool(species_id and species_id != "None" and species_id != "0")

    if is_npc:
        if species_id not in _NPC_DB:
            _NPC_DB[species_id] = {"name": ent.get('name', 'Unknown'), "type": ""}
        
        if new_name is not None: _NPC_DB[species_id]["name"] = new_name
        if new_type is not None: _NPC_DB[species_id]["type"] = new_type

        try:
            db_path = __import__('pathlib').Path(__file__).parent / "NPC_db.json"
            with open(db_path, 'w', encoding='utf-8') as f:
                _json.dump(_NPC_DB, f, indent=2, sort_keys=True)
            return True, "NPC_DB"
        except: return False, "ERROR"
    else:
        m_data = mumble.read() if mumble else None
        map_id = str(m_data.get("map_id", "0")) if m_data else "0"
        x, y, z = ent.get('x', 0), ent.get('y', 0), ent.get('z', 0)
        
        if map_id not in _OBJ_DB: _OBJ_DB[map_id] = []
            
        updated = False
        for node in _OBJ_DB[map_id]:
            dx = x - node.get("x", 0)
            dy = y - node.get("y", 0)
            dz = z - node.get("z", 0)
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            radius = node.get("radius", 0.8)  # ← DEFINE IT HERE

            if dist <= radius:
                # shrink old wide nodes automatically
                node["radius"] = 0.8  

                if new_name is not None:
                    node["name"] = new_name
                if new_type is not None:
                    node["type"] = new_type

                updated = True
                break
                
        if not updated:     
            _OBJ_DB[map_id].append({
                "name": new_name if new_name is not None else ent.get('name', 'OBJ'),
                "type": new_type if new_type is not None else "",
                "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
                "radius": 0.8
            })
            
        try:
            spatial_path = __import__('pathlib').Path(__file__).parent / "Obj_db.json"
            with open(spatial_path, 'w', encoding='utf-8') as f:
                _json.dump(_OBJ_DB, f, indent=2)
            return True, "OBJ_DB"
        except: return False, "ERROR"
