import json
import os
import uuid
import base64
import struct
import math
from collections import defaultdict
import urllib.request
import gw2x_core as core

UI_SETTINGS_FILE = "gw2x_ui_config.json"
POSITION_SLOTS_FILE = "saved_positions.json"
FAV_FILE = "npc_favorites.json"
WAYPOINTS_FILE = "map_names.json"
NPC_FILE = "all_npcs.json"
CUSTOM_TP_FILE = "custom_teleports.json"
PORTALS_FILE = "map_portals.json"

CUSTOM_TP_DIR = os.path.join(
    os.path.dirname(__file__),
    "teleports",
    "custom"
)
os.makedirs(CUSTOM_TP_DIR, exist_ok=True)


CUSTOM_TP_DB = {"groups": {"Default": []}}
WAYPOINT_DB = []
ALL_MAP_MARKERS = []
PORTAL_DB = {}
RAW_MAP_DATA = []
NPC_DATA = []
NPC_INDEX = defaultdict(lambda: defaultdict(list))
NPC_NAME_MAP = {}
NPC_DB = {}
ALL_NPCS_FILE = os.path.join(os.path.dirname(__file__), "all_npcs.json")
FAVORITE_NPCS = set()
POSITION_SLOTS = [None] * 5
ALIAS_FILE = "gw2x_aliases.json"
ALIASES = {}

OFFSETS = {
    "fgaddr": core.fgaddr,
    "fg2addr": core.fg2addr,
    "name": core.name,
    "brightness": core.brightness,
    "viewdist": core.viewdist,
    "health1": core.health1,
    "health2": core.health2,
    "objname": core.objname,
    "objhealth": core.objhealth,
    "mprdr": core.mprdr,

    # mod values
    "nametagmod": core.nametagmod,
    "nametagori": core.nametagori,
    "espbrightmod": core.espbrightmod,
    "espbrightori": core.espbrightori,
    "viewdistancemod": core.viewdistancemod,
    "viewdistanceori": core.viewdistanceori,
    "objectespmod": core.objectespmod,
    "objectespori": core.objectespori,
    "objecthpmod": core.objecthpmod,
    "objecthpori": core.objecthpori,
    "hpbar1mod": core.hpbar1mod,
    "hpbar1ori": core.hpbar1ori,
    "hpbar2mod": core.hpbar2mod,
    "hpbar2ori": core.hpbar2ori,
    "mapradarmod": core.mapradarmod,
    "mapradarori": core.mapradarori,
    "nofogmod": core.nofogmod,
    "nofogori": core.nofogori,
    "clearsurfacemod": core.clearsurfacemod,
    "clearsurfaceori": core.clearsurfaceori,
}

offsets = OFFSETS
# ===========================
# NEW: VISUALS CONFIGURATION
# ===========================
# Default settings for the new Visuals features
VISUAL_DEFAULTS = {
    "vis_fog": 0,           # 0 = Fog On, 1 = Fog Off
    "vis_bloom": 0,         # 0 = Bloom On, 1 = Bloom Off
    "esp_player": 0,        # 1 = Show Players
    "esp_npc": 0,           # 1 = Show NPCs
    "esp_gadget": 0,        # 1 = Show Gadgets
    "esp_path": 0,          # 1 = Show Radar/Path
    "esp_health": 0,        # 1 = Show Health Bars
}

# Variable names expected from the remote offset loader (from Decompiled script)
# This helps Logic know what keys to look for in the loaded module.
REQUIRED_OFFSETS = [
    "fgaddr", "nofogori", "nofogmod",
    "fg2addr", "clearsurfacemod", "clearsurfaceori",    # Fog
    "name", "nametagmod",                         # Player Tags
    "padang", "espbrightmod",                       # Brightness
    "viewdist", "viewdistancemod", "viewdistanceori", # View Distance
    "health1", "hpbar1mod", "hpbar1ori",             # Health Bar 1
    "health2", "hpbar2mod", "hpbar2ori",             # Health Bar 2
    "objname", "objectespmod", "objectespori",    # Object Tags
    "objhealth", "objecthpmod", "ojecthpori",        # Object Health
    "mprdr", "mapradarmod", "mapradarori",          # Map Radar
    "anglersense", "anglersensemod", "anglersenseori" # Angler Sense
]

# ... (Rest of load_ui_settings function remains the same) ...
def load_ui_settings():
    # Gunakan copy() agar tidak merubah global VISUAL_DEFAULTS
    default = VISUAL_DEFAULTS.copy()
    default.update({
        "transparency": 0.95,
        "always_on_top": True,
        "allow_resize": False,
        "positions": {"main": {"x": 100, "y": 100}},
        "open_windows": [],
        "inputs": {},
        "expanded": False,
        "macro_hotkeys": {}
    })

    if not os.path.exists(UI_SETTINGS_FILE):
        return default

    try:
        with open(UI_SETTINGS_FILE, "r", encoding="utf-8") as f:
            file_content = f.read().strip()
            if not file_content: # Cek jika file kosong
                return default
            data = json.loads(file_content)
            
        # Merge data yang ada dengan default (agar key baru tetap ada)
        for k, v in default.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"[Config] Error loading settings ({e}). Resetting to defaults.")
        return default

def save_ui_settings(
    transparency,
    always_on_top,
    positions,
    allow_resize=False,
    open_windows=None,
    inputs=None,
    expanded=False,
    macro_hotkeys=None
):
    cfg = {
        "transparency": transparency,
        "always_on_top": always_on_top,
        "positions": positions,
        "allow_resize": allow_resize,
        "open_windows": open_windows or [],
        "inputs": inputs or {},
        "expanded": expanded,
        "macro_hotkeys": macro_hotkeys or {}
    }

    with open("gw2x_ui_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
 

def update_last_auto_tp_index(idx):
    cfg = load_ui_settings()
    inputs = cfg.get("inputs", {})
    inputs["last_auto_tp_index"] = idx
    cfg["inputs"] = inputs
    save_ui_settings(
        cfg.get("transparency", 0.95),
        cfg.get("always_on_top", True),
        cfg.get("positions", {}),
        allow_resize=cfg.get("allow_resize", False),
        open_windows=cfg.get("open_windows", []),
        inputs=inputs,
        expanded=cfg.get("expanded", False),
        macro_hotkeys=cfg.get("macro_hotkeys", {})
    ) 

def get_entity_name_by_species_id(species_id):
    """
    Look up entity name from static species/gadget ID
    """
    # Try both formats (some IDs are stored as string, some as int)
    id_str = str(species_id)
    
    # Load from def_db
    try:
        with open("gw2x_def_db.json", "r", encoding="utf-8") as f:
            def_db = json.load(f)
            return def_db.get(id_str, f"Unknown (SID:{species_id})")
    except:
        return f"SID:{species_id}"

def is_mistlock_singularity(species_id):
    """
    Check if entity is a Mistlock Singularity
    """
    return species_id in [44690, 4294946450]

# ===========================
# SAVED POSITIONS (GAME COORDS)
# ===========================
def load_position_slots():
    global POSITION_SLOTS
    if os.path.exists(POSITION_SLOTS_FILE):
        try:
            with open(POSITION_SLOTS_FILE, "r") as f: POSITION_SLOTS = json.load(f)
        except: POSITION_SLOTS = [None] * 5

def save_slot(index, pos_tuple):
    POSITION_SLOTS[index] = pos_tuple
    try:
        with open(POSITION_SLOTS_FILE, "w") as f: json.dump(POSITION_SLOTS, f, indent=2)
    except: pass

# ===========================
# WAYPOINTS
# ===========================
def generate_chat_code(wp_id):
    """
    Generate GW2 Chat Link untuk Waypoint.
    Format: [&...=]
    Struct: Header (1 byte, 0x04) + Waypoint ID (4 bytes, Little Endian)
    """
    try:
        # PENTING: Gunakan '<BI' (Byte, Unsigned Int 4-byte).
        # Jangan gunakan '<BHH' karena itu akan crash jika ID > 65535.
        raw = struct.pack('<BI', 4, int(wp_id))
        encoded = base64.b64encode(raw).decode('utf-8')
        return f"[&{encoded}]"
    except Exception as e:
        print(f"[Data] Error generating chat code for WP {wp_id}: {e}")
        return ""

def load_waypoints_from_file(filename="map_names.json"):
    global WAYPOINT_DB, RAW_MAP_DATA
    WAYPOINT_DB.clear()
    RAW_MAP_DATA = []

    if not os.path.exists(filename):
        print(f"[Waypoints] File {filename} not found.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            RAW_MAP_DATA = json.load(f)
            
        # ... (kode parsing list selanjutnya tetap sama) ...
        count = 0
        if isinstance(RAW_MAP_DATA, list):
            for map_info in RAW_MAP_DATA:
                try:
                    m_id = int(map_info.get("id", 0))
                except ValueError:
                    continue  # Abaikan map dengan ID yang tidak valid
                    
                m_name = map_info.get("name", "Unknown Map")
                wps = map_info.get("waypoints", {})
                starting_wp_id = map_info.get("starting_waypoint")
                
                for wp_name, wp_val in wps.items():
                    wp_id = 0
                    coords = None
                    if isinstance(wp_val, list):
                        if len(wp_val) >= 1: wp_id = int(wp_val[0])
                        if len(wp_val) >= 4: coords = [float(wp_val[1]), float(wp_val[2]), float(wp_val[3])]
                    else:
                        wp_id = int(wp_val)

                    entry = {"name": wp_name, "id": wp_id, "map_id": m_id, "map_name": m_name, "coord": coords, "is_starting": (wp_id == starting_wp_id)}
                    WAYPOINT_DB.append(entry)
                    count += 1
        print(f"[Waypoints] Successfully loaded {count} waypoints.")

    except json.JSONDecodeError as e:
        print(f"\n[CRITICAL ERROR] JSON Syntax Salah di baris {e.lineno}, kolom {e.colno}:")
        print(f"Pesan: {e.msg}")
        print("TIPS: Cek koma berlebih (trailing comma) di akhir list/object!\n")
    except Exception as e:
        print(f"[Waypoints] Error loading file: {e}")

def update_and_save_waypoint(wp_name, map_id, x, y, z, filename="map_names.json"):
    """
    Mengupdate koordinat di memori dan menyimpannya langsung ke map_names.json
    dalam format: "WP NAME": [ID, X, Y, Z]
    """
    global RAW_MAP_DATA, WAYPOINT_DB
    
    # 1. Update Flat DB (Untuk UI Real-time)
    for wp in WAYPOINT_DB:
        if wp["name"] == wp_name and wp["map_id"] == map_id:
            wp["coord"] = [x, y, z]
            break
            
    # 2. Update Raw Structure (Untuk Saving)
    found = False
    for map_info in RAW_MAP_DATA:
        if int(map_info.get("id", 0)) == map_id:
            wps = map_info.get("waypoints", {})
            if wp_name in wps:
                # Ambil ID lama (entah dari int atau list)
                old_val = wps[wp_name]
                wp_id = old_val[0] if isinstance(old_val, list) else old_val
                
                # UPDATE KE FORMAT BARU: [ID, X, Y, Z]
                wps[wp_name] = [wp_id, round(x, 2), round(y, 2), round(z, 2)]
                found = True
            break
    
    if found:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(RAW_MAP_DATA, f, indent=2)
            print(f"[Waypoints] Saved coords for {wp_name} to {filename}")
            return True
        except Exception as e:
            print(f"[Waypoints] Save failed: {e}")
            return False
    return False


# ==========================================
# MAP-SPECIFIC ALIAS LOGIC
# ==========================================
def load_aliases():
    global ALIASES
    if not os.path.exists(ALIAS_FILE): return
    try:
        with open(ALIAS_FILE, "r", encoding="utf-8") as f:
            ALIASES = json.load(f)
    except: pass

def save_alias(map_id, ent, alias_name):
    global ALIASES
    import math

    map_id = str(map_id)

    if map_id not in ALIASES:
        ALIASES[map_id] = []

    species_id = str(ent.get("species_id"))
    x, y, z = ent.get("x"), ent.get("y"), ent.get("z")

    cleaned = []

    # Clean corrupted entries
    for a in ALIASES[map_id]:

        # Skip non-dict entries
        if not isinstance(a, dict):
            continue

        if (
            a.get("species_id") == species_id
            and math.dist(
                (a.get("x",0), a.get("y",0), a.get("z",0)),
                (x, y, z)
            ) < 1.5
        ):
            continue

        cleaned.append(a)

    ALIASES[map_id] = cleaned

    # Add new alias
    if alias_name:
        ALIASES[map_id].append({
            "species_id": species_id,
            "x": x,
            "y": y,
            "z": z,
            "radius": 2.0,
            "alias": alias_name
        })

    with open(ALIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ALIASES, f, indent=2)

def get_alias(map_id, ent):
    map_id = str(map_id)
    entries = ALIASES.get(map_id)

    if not entries:
        return None

    species_id = str(ent.get("species_id"))
    x, y, z = ent.get("x"), ent.get("y"), ent.get("z")

    # 🔥 BACKWARD COMPATIBILITY: old dict format
    if isinstance(entries, dict):
        return entries.get(species_id)

    # 🔥 NEW spatial format
    if isinstance(entries, list):
        for a in entries:
            if not isinstance(a, dict):
                continue

            if a.get("species_id") != species_id:
                continue

            dx = x - a.get("x", 0)
            dy = y - a.get("y", 0)
            dz = z - a.get("z", 0)
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            if dist <= a.get("radius", 2.0):
                return a.get("alias")

    return None

# Panggil saat modul di-load
load_aliases()

def save_live_entity_to_json(ent, custom_name, zone_name="Unknown"):
    global NPC_DATA
    
    # Skema standar mengikuti all_npcs.json Anda
    new_npc = {
        "name": custom_name,
        "service": "Live Scanner",
        "region": "Custom",
        "zone": zone_name,
        "area": "Saved Entities",
        "id": str(ent.get("id", "")),
        "coord": [ent.get("x", 0), ent.get("y", 0), ent.get("z", 0)]
    }
    
    file_data = []
    if os.path.exists(NPC_FILE):
        try:
            with open(NPC_FILE, "r", encoding="utf-8") as f:
                file_data = json.load(f)
        except:
            file_data = []
            
    # Validasi duplikasi: Timpa jika jarak < 1 meter atau ID sama persis
    is_updated = False
    for i, npc in enumerate(file_data):
        coords = npc.get("coord", [0, 0, 0])
        if len(coords) >= 3:
            dist = sum((coords[j] - new_npc["coord"][j])**2 for j in range(3))**0.5
            if dist < 1.0 or (npc.get("id") and npc.get("id") == new_npc["id"]):
                file_data[i] = new_npc
                is_updated = True
                break
                
    if not is_updated:
        file_data.insert(0, new_npc) # Tambahkan ke baris paling atas
        
    try:
        with open(NPC_FILE, "w", encoding="utf-8") as f:
            json.dump(file_data, f, indent=2)
        load_npcs_from_file() # Refresh in-memory DB
        return True
    except Exception as e:
        print(f"[Data] Failed to save entity: {e}")
        return False
        
# ===========================
# MAP PORTALS
# ===========================
def load_map_portals():
    global PORTAL_DB
    PORTAL_DB = {}
    path = os.path.join(os.path.dirname(__file__), PORTALS_FILE)
    
    if not os.path.exists(path): return

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        
        if isinstance(raw, dict): raw = [raw]
            
        for entry in raw:
            map_id = int(entry.get("id", 0))
            map_name = entry.get("name", f"Map {map_id}")
            portals = entry.get("portals", {})

            if not portals: continue
            PORTAL_DB.setdefault(map_name, [])

            for portal_name, coords in portals.items():
                # Validasi ketat sebelum unpacking
                if not isinstance(coords, list) or len(coords) < 3:
                    continue

                try:
                    PORTAL_DB[map_name].append({
                        "name": portal_name,
                        "x": float(coords[0]),
                        "y": float(coords[1]),
                        "z": float(coords[2]),
                        "map_id": map_id,
                        "allow_cross_map": True,
                        "type": "portal"
                    })
                except ValueError: continue # Skip jika koordinat bukan angka

        print(f"[Portals] Loaded {sum(len(v) for v in PORTAL_DB.values())} portals")
    except Exception as e:
        print(f"[Portals] Error: {e}")

def load_custom_teleports():
    global CUSTOM_TP_DB

    # Reset database
    CUSTOM_TP_DB = {"groups": {}}

    if not os.path.isdir(CUSTOM_TP_DIR):
        return

    # Scan recursive untuk semua subfolder
    for root, dirs, files in os.walk(CUSTOM_TP_DIR):
        for fname in files:
            if not fname.lower().endswith((".tps", ".json")):
                continue

            path = os.path.join(root, fname)
            group_name = os.path.splitext(fname)[0]

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content: continue

                # --- 1. COBA BACA SEBAGAI JSON ---
                try:
                    data = json.loads(content)
                    
                    # A. Format Standar GW2X
                    if "teleports" in data:
                        group = data.get("group", group_name)
                        teleports = data.get("teleports", [])
                        CUSTOM_TP_DB["groups"][group] = teleports
                        continue 

                    # B. Format "AutoConverter" (Auto-Swap Y/Z)
                    elif "Coordinates" in data:
                        group = data.get("Name", group_name)
                        raw_list = data.get("Coordinates", [])
                        converted_tps = []
                        for item in raw_list:
                            c_x = float(item.get("X", 0))
                            c_y = float(item.get("Y", 0)) 
                            c_z = float(item.get("Z", 0))
                            
                            # Swap Z (File) -> Y (App Height)
                            final_x = c_x
                            final_y = c_z 
                            final_z = c_y 

                            converted_tps.append({
                                "id": str(uuid.uuid4()),
                                "name": item.get("Name", "Unknown"),
                                "x": final_x, "y": final_y, "z": final_z,
                                "map_id": 0, "allow_cross_map": True
                            })
                        CUSTOM_TP_DB["groups"][group] = converted_tps
                        continue

                except json.JSONDecodeError:
                    pass 

                # --- 2. FORMAT TEXT LEGACY (Name X Y Z) ---
                teleports = []
                for line_idx, line in enumerate(content.splitlines()):
                    line = line.strip()
                    if not line: continue
                    
                    parts = line.split()
                    
                    # PERBAIKAN: Izinkan minimal 3 parts (X Y Z saja)
                    if len(parts) < 3: continue 

                    try:
                        # Ambil 3 angka terakhir sebagai koordinat
                        z = float(parts[-1])
                        y = float(parts[-2])
                        x = float(parts[-3])
                        
                        # Tentukan Nama
                        if len(parts) == 3:
                            # Jika tidak ada nama, gunakan "Spot <urutan>"
                            name = f"Spot {line_idx + 1}"
                        else:
                            # Gabungkan sisa teks di depan sebagai nama
                            name = " ".join(parts[:-3])
                        
                        teleports.append({
                            "id": str(uuid.uuid4()),
                            "name": name,
                            "x": x, "y": y, "z": z,
                            "map_id": 0,
                            "allow_cross_map": True
                        })
                    except ValueError:
                        continue

                if teleports:
                    CUSTOM_TP_DB["groups"][group_name] = teleports

            except Exception as e:
                print(f"[TP DB] Failed to load {path}: {e}")


def save_custom_teleports():
    groups = CUSTOM_TP_DB.get("groups", {})

    for group, teleports in groups.items():
        safe = "".join(c for c in group if c not in r'\/:*?"<>|')
        path = os.path.join(CUSTOM_TP_DIR, f"{safe}.tps")

        payload = {
            "group": group,
            "teleports": teleports
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"[TP DB] Save error ({group}): {e}")


def new_teleport(name, map_id, x, y, z, allow_cross_map=True):
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "map_id": int(map_id),
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "allow_cross_map": bool(allow_cross_map)
    }

def load_all_map_markers(filename="map_names.json"):
    global ALL_MAP_MARKERS
    ALL_MAP_MARKERS.clear()

    if not os.path.exists(filename):
        print(f"[Markers] File {filename} not found.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            maps = json.load(f)

        MARKER_KEYS = {
            "waypoints": "waypoint",
            "vista": "vista",
            "poi": "poi",
            "hero": "hero",
            "mastery": "mastery"
        }

        count = 0

        for map_info in maps:
            try:
                map_id = int(map_info.get("id", 0))
            except ValueError:
                continue  # Abaikan map dengan ID yang tidak valid
                
            map_name = map_info.get("name", "Unknown")

            for json_key, marker_type in MARKER_KEYS.items():
                section = map_info.get(json_key)
                if not isinstance(section, dict):
                    continue

                for name, val in section.items():
                    # Validasi format list
                    if not isinstance(val, list):
                        continue
                    
                    try:
                        # Logika Parsing yang Aman
                        marker_id = 0
                        x, y, z = 0.0, 0.0, 0.0

                        # Format A: [ID, X, Y, Z] (biasanya Waypoint)
                        if len(val) >= 4:
                            marker_id = int(val[0])
                            x, y, z = float(val[1]), float(val[2]), float(val[3])
                        
                        # Format B: [X, Y, Z] (biasanya POI/Vista)
                        elif len(val) == 3:
                            x, y, z = float(val[0]), float(val[1]), float(val[2])
                        
                        # Format C: [ID, X, Y] (Kasus aneh, skip Z)
                        else:
                            # Skip format yang tidak dikenal untuk mencegah crash
                            continue

                        ALL_MAP_MARKERS.append({
                            "type": marker_type,
                            "name": name,
                            "id": marker_id,
                            "map_id": map_id,
                            "map_name": map_name,
                            "coord": [x, y, z]
                        })
                        count += 1
                    except (ValueError, IndexError):
                        # Jika data di dalam list bukan angka valid, skip entry ini
                        continue

        print(f"[Markers] Loaded {count} total map markers")

    except Exception as e:
        print(f"[Markers] Failed to load markers: {e}")

# ===========================
# NPCS & FAVORITES
# ===========================
def load_npcs_from_file():
    global NPC_DATA, NPC_INDEX, NPC_NAME_MAP, FAVORITE_NPCS, NPC_ID_MAP

    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r") as f: FAVORITE_NPCS = set(json.load(f))
        except: FAVORITE_NPCS = set()

    if not os.path.exists(NPC_FILE): return False
    try:
        with open(NPC_FILE, "r", encoding="utf-8") as f: NPC_DATA = json.load(f)
        NPC_INDEX.clear()
        NPC_NAME_MAP.clear()
        NPC_ID_MAP.clear() # <--- BERSIHKAN MAP LAMA

        for npc in NPC_DATA:
            if not npc.get("coord"): continue
            r = npc.get("region", "Unknown")
            a = npc.get("area", "Unknown")
            NPC_INDEX[r][a].append(npc)
            NPC_NAME_MAP[npc["name"]] = npc

            # --- TAMBAHAN UNTUK MAPPING ID ---
            npc_id = str(npc.get("id", "")).strip()
            if npc_id and npc_id != "0" and npc_id != "None":
                NPC_ID_MAP[npc_id] = npc["name"] # Petakan ID ke Nama Kustom

        return True
    except: return False
    
def save_favorites():
    try:
        with open(FAV_FILE, "w", encoding="utf-8") as f:
            json.dump(list(FAVORITE_NPCS), f, indent=2)
    except: pass
    

# ===============================
# INITIAL DATA LOAD
# ===============================
print("[Data] INIT LOAD START")

load_waypoints_from_file("map_names.json")
print("[Data] WAYPOINTS DONE")

load_all_map_markers("map_names.json")
print("[Data] MARKERS DONE")

load_map_portals()
print("[Data] PORTALS DONE")

load_waypoints_from_file("map_names.json")
load_map_portals()

offsets = OFFSETS
load_aliases()