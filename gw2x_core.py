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
skyscalegreenbaraddress  = xxxx2
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
                "player_x": ctx.playerX,
                "player_y": ctx.playerY,
                "mount_index": ctx.mountIndex
            }
        except Exception: return None

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
stamina_thread = None
skyscale_thread = None
_skyscale_addr = None
current_hwnd = None
_last_logged_pid = None  
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

def get_hwnd_from_pid(pid):
    import win32gui
    import win32process

    hwnd_result = None

    def callback(hwnd, _):
        nonlocal hwnd_result
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid and win32gui.IsWindowVisible(hwnd):
            hwnd_result = hwnd
        return True

    win32gui.EnumWindows(callback, None)
    return hwnd_result

def connect(pid=None):
    global pm, mumble, shared_entities, _last_logged_pid, current_hwnd
    import pymem

    try:
        if pid:
            new_pm = pymem.Pymem()
            new_pm.open_process_from_id(pid)

            pm = new_pm
            _last_logged_pid = pid  # <-- PINDAHKAN KE SINI

            mumble = MumbleData()
            shared_entities = SharedEntityData()
                    
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


def _try_aob(base):
    """AOB scan → find mov rsi,[rip+x] before instruction → dereference → struct base."""
    import struct as _struct
    print("[MouseAOB] Scanning for write instruction...")
    instr = pm.pattern_scan_module(MOUSE_AOB_PATTERN, "Gw2-64.exe")
    if not instr:
        print("[MouseAOB] Pattern not found — update MOUSE_AOB_PATTERN after patch.")
        return None
    print(f"[MouseAOB] Instruction at {hex(instr)}")

    # Dump surrounding bytes for diagnosis regardless
    try:
        window = pm.read_bytes(instr - 128, 128)
    except Exception as e:
        print(f"[MouseAOB] Cannot read memory window: {e}")
        return None

    print(f"[MouseAOB] Bytes before instruction: {window[-32:].hex(' ').upper()}")

    # Try: mov rsi, [rip+offset]  →  48 8B 35 XX XX XX XX
    for sig, reg_name in [(b"\x48\x8B\x35", "rsi"), (b"\x4C\x8B\x35", "r14"), (b"\x48\x8B\x3D", "rdi")]:
        idx = window.rfind(sig)
        if idx == -1:
            continue
        rip_off    = _struct.unpack("<i", window[idx+3:idx+7])[0]
        instr_abs  = (instr - 128) + idx
        static_ptr = instr_abs + 7 + rip_off
        print(f"[MouseAOB] Found mov {reg_name},[rip+off] → static ptr @ {hex(static_ptr)}")
        try:
            struct_base = pm.read_longlong(static_ptr)
            x_addr      = struct_base + 0x300
            test        = pm.read_float(x_addr)
            if test == 0.0 or not (-100_000_000 < test < 100_000_000):
                raise ValueError(f"Implausible value: {test}")
            print(f"[MouseAOB] OK → {hex(x_addr)}  raw_x={test:.1f}")
            _save_mouse_config(static_ptr - base, [0x300])
            return x_addr
        except Exception as e:
            print(f"[MouseAOB] {reg_name} path failed: {e}")
            continue

    print("[MouseAOB] Could not resolve struct base. Check the byte dump above in CE.")
    return None


def reset_mouse_cache():
    """Force re-resolution on next read (call after map load if needed)."""
    global _mouse_x_addr
    _mouse_x_addr = None


def read_mouse_3d_position():
    global _mouse_x_addr
    if not pm:
        return None

    # Use cached address if available
    if _mouse_x_addr is None:
        try:
            base = pymem.process.module_from_name(pm.process_handle, "Gw2-64.exe").lpBaseOfDll
        except Exception as e:
            print(f"[Mouse] Module base failed: {e}")
            return None
        _mouse_x_addr = _try_pointer_chain(base) or _try_aob(base)
        if not _mouse_x_addr:
            print("[Mouse] All resolution methods failed.")
            return None

    try:
        rx = pm.read_float(_mouse_x_addr)
        ry = pm.read_float(_mouse_x_addr + 4)
        rz = pm.read_float(_mouse_x_addr + 8)

        conv = 1.0 / 39.37
        mx   =  rx * conv
        mz   =  ry * conv
        my   = -rz * conv

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
PostMessage = ctypes.windll.user32.PostMessageW
MapVirtualKey = ctypes.windll.user32.MapVirtualKeyW
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
    except:
        return 0, 0

def send_background_down(window_title, hex_scan_code):
    """Mengirim sinyal KEY DOWN ke window tertentu tanpa fokus"""
    try:
        hwnd = current_hwnd
        if not hwnd: return
        
        scan_code, vk_code = get_virtual_key(hex_scan_code)
        if vk_code == 0: return

        lparam = 1 | (scan_code << 16)
        PostMessage(hwnd, WM_KEYDOWN, vk_code, lparam)
    except Exception as e:
        print(f"[BgInput] Down Error: {e}")

def send_background_up(window_title, hex_scan_code):
    """Mengirim sinyal KEY UP ke window tertentu tanpa fokus"""
    try:
        hwnd = current_hwnd
        if not hwnd: return

        scan_code, vk_code = get_virtual_key(hex_scan_code)
        if vk_code == 0: return

        lparam = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)
        PostMessage(hwnd, WM_KEYUP, vk_code, lparam)
    except Exception as e:
        print(f"[BgInput] Up Error: {e}")

def send_background_key(window_title, hex_scan_code, duration=0.05):
    """Tekan dan Lepas (Tap) di background"""
    send_background_down(window_title, hex_scan_code)
    time.sleep(float(duration))
    send_background_up(window_title, hex_scan_code)

def presskey(window_title, hex_key_code, duration=0.05):
    """Wrapper fungsi presskey agar gw2x_ui.py tidak error Import."""
    send_background_key(window_title, hex_key_code, duration)

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

def enable_skyscale_loop():
    logging.info("[Skyscale] Loop injeksi Skyscale bar dimulai.")
    
    while not skyscale_stop_event.is_set():
        try:
            # Memastikan process memory dan variabel offset tersedia
            if pm and skyscalegreenbaraddress:
                # Menghitung alamat absolut berdasarkan base address + static offset dari server
                target_addr = pm.base_address + skyscalegreenbaraddress
                pm.write_ushort(target_addr, 37008)  # Nilai modifikasi Skyscale Infinite
            
            time.sleep(0.1) # Loop rate 10Hz
        except Exception as e:
            logging.error(f"[Skyscale] Gagal menulis ke memori: {e}")
            time.sleep(0.5)
            
    logging.info("[Skyscale] Loop injeksi dihentikan.")

def toggle_skyscale_wall(active):
    global skyscale_thread
    
    if active:
        if 'skyscale_thread' in globals() and skyscale_thread and skyscale_thread.is_alive():
            logging.warning("[Skyscale] Thread sudah aktif. Mengabaikan perintah start.")
            return

        logging.info("[Skyscale] Mengaktifkan Infinite Wall.")
        skyscale_stop_event.clear()
        skyscale_thread = threading.Thread(target=enable_skyscale_loop, daemon=True)
        skyscale_thread.start()

    else:
        logging.info("[Skyscale] Menonaktifkan Infinite Wall.")
        skyscale_stop_event.set()

        if pm and skyscalegreenbaraddress:
            try:
                target_addr = pm.base_address + skyscalegreenbaraddress
                pm.write_ushort(target_addr, 4083)  # Kembalikan ke nilai standar engine
                logging.info("[Skyscale] Nilai default 4083 berhasil dikembalikan.")
            except Exception as e:
                logging.error(f"[Skyscale] Gagal mengembalikan nilai default: {e}")

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