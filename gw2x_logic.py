import threading
import time
import os
import math
import random
import ctypes
import json
import struct
import win32gui
import gw2x_config
import gw2x_core as core
from datetime import datetime
import gw2x_data as data
from gw2x_map_target import MapTargetResolver
from gw2x_remote_identity import CommanderNameResolver, EventNameResolver


def is_valid_coord(v):
    if v is None:
        return False
    if math.isnan(v) or math.isinf(v):
        return False
    if abs(v) > 500000:
        return False
    return True

class EventDetector:
    """
    Detects actual live map-event records exposed by the rebuilt DLL.

    Static event_details data supplies the GUID/name/location. The DLL supplies
    only records currently loaded in GW2's live-event collection. A build-scoped
    runtime-ID binding disambiguates events that share one location.
    """
    _cache_path = None
    _runtime_id_path = None
    _event_db   = {}      # { map_id(int): [{guid, name, raw_xyz, converted coords}] }
    _raw_cache  = {}      # { map_id(int): map_rect, continent_rect } — fetched lazily
    _db_lock    = threading.Lock()
    _runtime_lock = threading.Lock()
    _runtime_ids = {"version": 1, "builds": {}}
    _runtime_ids_loaded = False
    _fetched    = False
    _building   = False

    # Confirmed by four inactive -> active -> inactive captures on build
    # 205655. Other builds are learned explicitly with Capture Active.
    _confirmed_runtime_ids = {
        "205655": {
            "985EBBAD-66FA-4F9D-9AA0-02A06EC24E68": {
                "runtime_id": 0x2408,
                "map_id": 929,
                "center": [-23.6807, -6082.4, -2629.6],
                "source": "probe-confirmed",
            },
        },
    }

    def __init__(self):
        import os
        EventDetector._cache_path = os.path.join(
            os.path.dirname(__file__), "event_db_cache.json")
        EventDetector._runtime_id_path = os.path.join(
            os.path.dirname(__file__), "event_runtime_ids.json")
        self.current_map_id = 0
        self._load_cache()
        self._load_runtime_ids()
        if not EventDetector._fetched and not EventDetector._building:
            threading.Thread(target=self._build_db, daemon=True).start()

    # ── Disk cache (processed DB only, NOT raw API) ───────────────────────
    def _load_cache(self):
        import os
        if not os.path.exists(EventDetector._cache_path):
            return
        try:
            with open(EventDetector._cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Validate: keys must be numeric map IDs, not "events"
            if "events" in raw:
                print("[EventDetector] Old raw cache detected — deleting, will rebuild")
                os.remove(EventDetector._cache_path)
                return
            db = {int(k): v for k, v in raw.items()}
            # V4 needs the exact raw float32 center to match the DLL feed. A
            # V3 cache cannot be upgraded losslessly from converted meters.
            if any(
                    "raw_x" not in ev or "raw_y" not in ev or "raw_z" not in ev
                    for events in db.values() for ev in events):
                print("[EventDetector] Pre-V4 cache detected — deleting, will rebuild")
                os.remove(EventDetector._cache_path)
                return
            with EventDetector._db_lock:
                EventDetector._event_db = db
            EventDetector._fetched = True
            total = sum(len(v) for v in db.values())
            print(f"[EventDetector] Cache loaded: {len(db)} maps, {total} events")
        except Exception as e:
            print(f"[EventDetector] Cache load error: {e}")

    def _load_runtime_ids(self):
        if EventDetector._runtime_ids_loaded:
            return
        merged = {"version": 1, "builds": {}}
        try:
            if os.path.exists(EventDetector._runtime_id_path):
                with open(EventDetector._runtime_id_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and isinstance(loaded.get("builds"), dict):
                    merged = loaded
        except Exception as exc:
            print(f"[EventDetector] Runtime-ID cache load error: {exc}")

        builds = merged.setdefault("builds", {})
        for build, bindings in EventDetector._confirmed_runtime_ids.items():
            target = builds.setdefault(build, {})
            for guid, binding in bindings.items():
                target.setdefault(guid, dict(binding))
        with EventDetector._runtime_lock:
            EventDetector._runtime_ids = merged
            EventDetector._runtime_ids_loaded = True

    def _save_runtime_ids(self):
        path = EventDetector._runtime_id_path
        temp_path = path + ".tmp"
        try:
            with EventDetector._runtime_lock:
                payload = json.loads(json.dumps(EventDetector._runtime_ids))
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
            os.replace(temp_path, path)
        except Exception as exc:
            print(f"[EventDetector] Runtime-ID cache save error: {exc}")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _save_cache(self):
        try:
            with EventDetector._db_lock:
                data = {str(k): v for k, v in EventDetector._event_db.items()}
            with open(EventDetector._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"[EventDetector] Cache saved to {EventDetector._cache_path}")
        except Exception as e:
            print(f"[EventDetector] Cache save error: {e}")

    # ── Map rect helper (lazy, cached in memory) ──────────────────────────
    def _get_map_info(self, mid):
        """Returns (map_rect, continent_rect) for map_id, fetching if needed."""
        if mid in EventDetector._raw_cache:
            return EventDetector._raw_cache[mid]
        if mid in core.MAP_DATA_DB:
            info = core.MAP_DATA_DB[mid]
            EventDetector._raw_cache[mid] = (info['map_rect'], info['continent_rect'])
            return EventDetector._raw_cache[mid]
        if core.fetch_map_data(mid):
            info = core.MAP_DATA_DB[mid]
            EventDetector._raw_cache[mid] = (info['map_rect'], info['continent_rect'])
            return EventDetector._raw_cache[mid]
        return None

    # ── Coordinate conversion (no extra API calls) ────────────────────────
    def _event_to_meters(self, center, radius, mid):
        info = self._get_map_info(mid)
        if not info:
            return None
        mr, cr = info

        # scale_coords: map space → continent space (wiki formula)
        m_w = mr[1][0] - mr[0][0]
        m_h = mr[1][1] - mr[0][1]
        c_w = cr[1][0] - cr[0][0]
        c_h = cr[1][1] - cr[0][1]
        if m_w == 0 or m_h == 0 or c_w == 0 or c_h == 0:
            return None

        cont_x = cr[0][0] + (center[0] - mr[0][0]) / m_w * c_w
        cont_y = cr[0][1] + (-1.0) * (center[1] - mr[1][1]) / m_h * c_h

        # Continent coords ARE in inches (1 continent unit = 1 inch)
        # Mumble meters = continent inches / 39.3701
        cx_m = cont_x / 39.3701
        cz_m = cont_y / 39.3701

        # Radius: convert from local map inches to continent scale, then to meters
        # Use X scale as approximation
        cont_radius = radius / m_w * c_w
        radius_m = max(cont_radius / 39.3701, 20.0)

        return (cx_m, cz_m, radius_m)

    # ── One-time DB build ─────────────────────────────────────────────────
    def _build_db(self):
        import urllib.request
        EventDetector._building = True
        print("[EventDetector] Downloading event_details.json...")

        try:
            url = "https://api.guildwars2.com/v1/event_details.json"
            req = urllib.request.Request(url, headers={"User-Agent": "GW2X/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[EventDetector] Download failed: {e}")
            EventDetector._building = False
            return

        events = raw.get("events", {})
        print(f"[EventDetector] Downloaded {len(events)} events. Converting coordinates...")

        # Group by map first so we only fetch each map's rect once
        by_map = {}
        for guid, ev in events.items():
            mid = ev.get("map_id", 0)
            if not mid:
                continue
            loc    = ev.get("location", {})
            center = loc.get("center")
            radius = loc.get("radius", 0)
            name   = ev.get("name", "") or f"[{guid[:8]}]"
            if not center or len(center) < 2:
                continue
            if mid not in by_map:
                by_map[mid] = []
            by_map[mid].append((guid, name, center, radius))

        db      = {}
        skipped = 0
        for mid, entries in by_map.items():
            # Fetch map rect once per map
            info = self._get_map_info(mid)
            if not info:
                skipped += len(entries)
                continue
            for guid, name, center, radius in entries:
                coords = self._event_to_meters(center, radius, mid)
                if not coords:
                    skipped += 1
                    continue
                cx_m, cz_m, radius_m = coords
                if mid not in db:
                    db[mid] = []
                db[mid].append({
                    "guid":     guid,
                    "name":     name,
                    "map_id":   int(mid),
                    "raw_x":    float(center[0]),
                    "raw_y":    float(center[1]),
                    "raw_z":    float(center[2]) if len(center) > 2 else 0.0,
                    "cx_m":     cx_m,
                    "cz_m":     cz_m,
                    "radius_m": radius_m,
                })

        with EventDetector._db_lock:
            EventDetector._event_db = db
        EventDetector._fetched  = True
        EventDetector._building = False

        total = sum(len(v) for v in db.values())
        print(f"[EventDetector] DB ready: {len(db)} maps, {total} events "
              f"({skipped} skipped)")
        self._save_cache()

    def refresh_cache(self):
        if not EventDetector._building:
            EventDetector._fetched = False
            threading.Thread(target=self._build_db, daemon=True).start()

    # ── Runtime detection ─────────────────────────────────────────────────
    @staticmethod
    def _float32_bits(value):
        return struct.unpack("<I", struct.pack("<f", float(value)))[0]

    @classmethod
    def _center_key(cls, item, prefix="raw_"):
        try:
            if prefix:
                values = (item[prefix + "x"], item[prefix + "y"], item[prefix + "z"])
            else:
                values = (item["map_x"], item["map_y"], item["map_z"])
            return tuple(cls._float32_bits(value) for value in values)
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _current_build_id():
        try:
            mumble_data = core.mumble.read() if core.mumble else None
            return int((mumble_data or {}).get("build_id", 0) or 0)
        except Exception:
            return 0

    @classmethod
    def _binding_for(cls, build_id, guid):
        with cls._runtime_lock:
            binding = cls._runtime_ids.get("builds", {}).get(
                str(int(build_id or 0)), {}).get(str(guid).upper())
            return dict(binding) if isinstance(binding, dict) else None

    def bind_runtime_id(self, event_entry):
        """Bind the selected active event to its build-specific runtime ID."""
        if not event_entry:
            return False, "Choose an event first"
        guid = str(event_entry.get("guid", "")).upper().strip()
        center_key = self._center_key(event_entry)
        if not guid or center_key is None:
            return False, "Selected event has no V4 raw-center data; refresh the event cache"

        status = core.get_live_event_status()
        if not status.get("available"):
            return False, status.get("message", "Live Event DLL feed unavailable")
        if not status.get("fresh"):
            return False, status.get("message", "Live Event DLL feed is stale")

        matches = [record for record in status.get("records", [])
                   if self._center_key(record, prefix="") == center_key]
        runtime_ids = sorted({int(record.get("runtime_id", 0))
                              for record in matches if int(record.get("runtime_id", 0)) > 0})
        if not runtime_ids:
            return False, "That event center is not live now; wait until the event is active"
        if len(runtime_ids) != 1:
            values = ", ".join(f"0x{value:X}" for value in runtime_ids)
            return False, f"Multiple live IDs share this center ({values}); capture another cycle"

        build_id = self._current_build_id()
        if not build_id:
            return False, "GW2 build ID is unavailable from MumbleLink"
        runtime_id = runtime_ids[0]
        binding = {
            "runtime_id": runtime_id,
            "map_id": int(event_entry.get("map_id", self.current_map_id) or 0),
            "center": [float(event_entry["raw_x"]), float(event_entry["raw_y"]),
                       float(event_entry["raw_z"])],
            "learned_at": datetime.now().isoformat(timespec="seconds"),
            "source": "capture-active",
        }
        with EventDetector._runtime_lock:
            builds = EventDetector._runtime_ids.setdefault("builds", {})
            builds.setdefault(str(build_id), {})[guid] = binding
        self._save_runtime_ids()
        print(f"[EventDetector] Bound {guid[:8]} to runtime ID 0x{runtime_id:X} "
              f"for build {build_id}")
        return True, f"Bound live runtime ID 0x{runtime_id:X} for build {build_id}"

    def get_active_events(self, active_only=True, documented_only=False):
        map_id = self.current_map_id
        if not map_id or not EventDetector._fetched:
            return []

        map_id_int = int(map_id)
        with EventDetector._db_lock:
            map_events = list(EventDetector._event_db.get(map_id_int, []))
        if not map_events:
            return []

        feed = core.get_live_event_status()
        live_records = feed.get("records", []) if feed.get("fresh") else []
        records_by_center = {}
        for record in live_records:
            key = self._center_key(record, prefix="")
            if key is not None:
                records_by_center.setdefault(key, []).append(record)

        events_by_center = {}
        for event in map_events:
            key = self._center_key(event)
            if key is not None:
                events_by_center.setdefault(key, []).append(event)
        build_id = self._current_build_id()

        player_mx, player_mz = None, None
        try:
            if core.mumble:
                mumble_data = core.mumble.read()
                if mumble_data:
                    pos = mumble_data.get("pos", (0, 0, 0))
                    player_mx, player_mz = pos[0], pos[2]
        except Exception:
            pass

        result = []
        for ev in map_events:
            entry = dict(ev)
            entry["map_id"] = map_id_int
            if player_mx is not None and ev.get("cx_m") is not None:
                dx = player_mx - ev["cx_m"]
                dz = player_mz - ev["cz_m"]
                entry["dist_m"] = math.sqrt(dx * dx + dz * dz)
            else:
                entry["dist_m"] = 999999

            center_key = self._center_key(ev)
            center_records = records_by_center.get(center_key, [])
            binding = self._binding_for(build_id, ev.get("guid", ""))
            runtime_id = int((binding or {}).get("runtime_id", 0) or 0)
            matched_record = None
            if runtime_id:
                matched_record = next(
                    (record for record in center_records
                     if int(record.get("runtime_id", 0)) == runtime_id), None)
            elif center_key is not None and len(events_by_center.get(center_key, [])) == 1:
                # A unique static center is safe without an explicit ID binding.
                matched_record = center_records[0] if len(center_records) == 1 else None

            entry["matched_npcs"] = []  # retained for older UI/teleport callers
            entry["likely_active"] = matched_record is not None
            entry["live_feed_available"] = bool(feed.get("available"))
            entry["live_feed_fresh"] = bool(feed.get("fresh"))
            entry["live_feed_source"] = feed.get("source", "unavailable")
            entry["live_center_present"] = bool(center_records)
            entry["center_event_count"] = len(events_by_center.get(center_key, []))
            entry["needs_runtime_id"] = bool(
                center_records and not runtime_id and entry["center_event_count"] > 1)
            entry["bound_runtime_id"] = runtime_id or None
            entry["live_runtime_id"] = (
                int(matched_record.get("runtime_id", 0)) if matched_record else None)
            entry["detection_source"] = (
                "dll-runtime-id" if matched_record and runtime_id else
                "dll-unique-center" if matched_record else "none")
            result.append(entry)

        result.sort(key=lambda event: event["dist_m"])
        return result


class MapEventNameResolver:
    """Join live map-icon packet coordinates to official GW2 event names."""
    _lock = threading.Lock()
    _ready = threading.Event()
    _index = {}
    _loading = False

    def __init__(self):
        self.cache_path = os.path.join(
            os.path.dirname(__file__), "map_event_name_cache.json")
        self._load_cache()
        with self._lock:
            if not self._index and not self._loading:
                self.__class__._loading = True
                threading.Thread(
                    target=self._download_index,
                    name="GW2X-EventNameIndex",
                    daemon=True,
                ).start()

    @staticmethod
    def _raw_radius(location, center):
        radius = float(location.get("radius", 0.0) or 0.0)
        if radius > 0.0:
            return radius
        points = location.get("points") or []
        for point in points:
            if len(point) >= 2:
                radius = max(radius, math.hypot(
                    float(point[0]) - center[0],
                    float(point[1]) - center[1],
                ))
        z_range = location.get("z_range") or []
        if len(z_range) >= 2:
            radius = max(radius, abs(float(z_range[0]) - center[2]),
                         abs(float(z_range[1]) - center[2]))
        return radius

    def _load_cache(self):
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if int(payload.get("version", 0)) != 1:
                return
            maps = payload.get("maps", {})
            parsed = {int(map_id): list(events)
                      for map_id, events in maps.items()}
            with self._lock:
                self.__class__._index = parsed
                self.__class__._ready.set()
            print(f"[EventNames63] Loaded {sum(map(len, parsed.values()))} "
                  f"official event names for {len(parsed)} maps.")
        except (OSError, ValueError, TypeError):
            pass

    def _download_index(self):
        import urllib.request
        try:
            request = urllib.request.Request(
                "https://api.guildwars2.com/v1/event_details.json",
                headers={"User-Agent": "GW2X/1.0"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                source = json.loads(response.read().decode("utf-8"))
            index = {}
            for guid, event in source.get("events", {}).items():
                map_id = int(event.get("map_id", 0) or 0)
                location = event.get("location") or {}
                center_value = location.get("center") or []
                if not map_id or len(center_value) < 2:
                    continue
                center = [float(center_value[0]), float(center_value[1]),
                          float(center_value[2]) if len(center_value) > 2 else 0.0]
                radius = self._raw_radius(location, center)
                if radius <= 0.0:
                    continue
                index.setdefault(map_id, []).append({
                    "guid": str(guid),
                    "name": str(event.get("name") or "Event"),
                    "level": int(event.get("level", 0) or 0),
                    "center": center,
                    "radius": radius,
                })
            payload = {"version": 1,
                       "maps": {str(k): v for k, v in index.items()}}
            temp_path = self.cache_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"))
            os.replace(temp_path, self.cache_path)
            with self._lock:
                self.__class__._index = index
                self.__class__._ready.set()
            print(f"[EventNames63] Downloaded {sum(map(len, index.values()))} "
                  f"official event names for {len(index)} maps.")
        except Exception as exc:
            print(f"[EventNames63] Event-name index unavailable: {exc}")
        finally:
            with self._lock:
                self.__class__._loading = False

    def decorate(self, points, map_id, active_guids=None):
        if not self._ready.is_set():
            self._ready.wait(1.5)
        with self._lock:
            events = list(self._index.get(int(map_id or 0), []))
        if not events:
            return points
        active_guids = {str(value).upper() for value in (active_guids or [])}
        for point in points:
            raw = point.get("raw")
            if not raw or len(raw) < 3:
                continue
            px, py, pz = map(float, raw[:3])
            matches = []
            for event in events:
                cx, cy, cz = event["center"]
                distance = math.sqrt(
                    (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2)
                radius = max(float(event["radius"]), 1.0)
                if distance <= radius * 1.10:
                    matches.append((distance, event))
            if not matches:
                continue
            active_matches = [
                row for row in matches
                if str(row[1]["guid"]).upper() in active_guids
            ]
            if not active_matches:
                distance, event = min(matches, key=lambda row: row[0])
                point["possible_event_name"] = event["name"]
                point["possible_event_guid"] = event["guid"]
                point["possible_event_level"] = event["level"]
                point["possible_event_distance_m"] = distance / 39.37
                continue
            distance, event = min(active_matches, key=lambda row: row[0])
            point["event_name"] = event["name"]
            point["event_guid"] = event["guid"]
            point["event_level"] = event["level"]
            point["event_match_distance_m"] = distance / 39.37
            point["source"] = "Verified active event + live map packet"
        return points


class GW2X_Logic:
    def __init__(self, pm, offsets, settings=None):
        self.pm = pm
        self.window_title = "Guild Wars 2"
        self.raw_offsets = offsets
        self.offsets = offsets
        self.base_address = pm.base_address if pm else 0
        self.griffoninstaboost_mod = self.offsets.get("griffoninstaboost_mod", 0)     
        self.griffoninstaboost_ori = self.offsets.get("griffoninstaboost_ori", 0)
        self.event_detector = EventDetector()
        self.map_event_names = MapEventNameResolver()
        self.commander_names = CommanderNameResolver()
        self.event_names = EventNameResolver(self.map_event_names)
        self._map_icon_cache = {}
    
        self.interact_scan = getattr(gw2x_config, "INTERACT", "21")

        # --- LOAD MAP NAMES ---
        self.map_names = {}
        try:
            json_path = os.path.join(os.path.dirname(__file__), "map_names.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)
                    for item in data_list:
                        mid = str(item.get("id", ""))
                        name = item.get("name", "")
                        if mid: self.map_names[mid] = name
        except Exception as e: print(f"[Logic] Error loading map_names: {e}")

        # --- LOAD NPCS (REFACTORED) ---
        self.npcs = []
        self.load_npcs() # Panggil fungsi baru

        self.offsets = offsets

        # Hardcoded Health Offsets
        self.offset_health_current = [180]
        self.offset_health_max     = [184]
        
        # State Variables
        self.speed_current = [None, None, None]
        self.speed_targets = [{"active": False, "val": 400.0} for _ in range(3)]
        self.inf_energy = False
        self.current_map_id = 0
        self.map_ready = False
        
        # Threading & Locks
        self.auto_tp_running = False
        self.auto_tp_stop_event = threading.Event()
        self.input_lock = threading.Lock()
        self.auto_tp_thread = None

        # Auto Features Config
        self.auto_quickness_enabled = False
        self.skill9_scan = "2F" 
        self.current_auto_tp_index = 0
        self.on_auto_tp_step = None  
        self.on_auto_tp_finished = None
        
        self.auto_tp_reverse = False
        self.auto_tp_random = False
        self.MAX_TP_DRIFT = 1.5
        self.CLAMP_COOLDOWN = 0.15
        self._user_stop_requested = False
        self.auto_tp_retry_enabled = False
        self.auto_tp_retry_count = 1
        
        self.map_target = MapTargetResolver()
        # --- MAP UI STATE ---
        self.map_ui_open = False
        self.map_scan = "32"   # SCAN CODE for M (change if different in your config)
        self.esc_scan = "01"   # SCAN CODE for ESC

        # --- BUILD STARTING WAYPOINT PER MAP ---
        self.starting_waypoints = {}

        for wp in data.WAYPOINT_DB:
            mid = wp.get("map_id")
            if mid and mid not in self.starting_waypoints:
                self.starting_waypoints[mid] = wp
                
        if settings:
            self.auto_tp_retry_enabled = settings.get("auto_tp_retry", False)
            self.auto_tp_retry_count = settings.get("auto_tp_retry_count", 1)
            
        self.manual_tp_step = 0
        self.current_auto_tp_index = 0
       
        self._last_hp = None
        self._hp_drop_ts = None

        self.flagged_tp_indices = set()
        self.active_flagged_tp = None
        
        self.relog_char_select_x = 1720
        self.relog_char_select_y = 780
        self.auto_relog_enabled = False
        self.auto_relog_twice_enabled = False
        self.auto_relog_loop_enabled = False
        self._last_auto_tp_args = None
        
        self.move_fwd_scan = None
        self.escape_scan = None
        
        self.interacting_addr = self.offsets.get("interacting")
        self.interacting_value = self.offsets.get("interacting_value", 2)
        
        self.auto_tp_interact_object = False
        self.auto_tp_interact_vista = False

        self._esp_enabled = {"esp_player": True, "esp_npc": True, "esp_path": True, "esp_health": True}
        self._clarity_enabled = True

        self._recover_npc_dictionary()

        threading.Thread(target=self._movement_loop, daemon=True).start()
        threading.Thread(target=self._map_check_loop, daemon=True).start()
        threading.Thread(target=self._visual_watchdog, daemon=True).start()
        threading.Thread(target=self._hotkey_monitor_loop, daemon=True).start()
        print("[Logic] Hotkey F6 (Nearest TP) aktif.")

    # ===============================
    # CORE CONNECTION
    # ===============================
    def _recover_npc_dictionary(self):  
        import os, json 
        
        # Keamanan: Pastikan kamus eksis    
        if not hasattr(data, 'NPC_ID_MAP'):
            data.NPC_ID_MAP = {}
            
        # 1. Pulihkan dari npc_id_map.json (Prioritas Utama)
        custom_map_path = os.path.join(os.path.dirname(__file__), "npc_id_map.json")
        if os.path.exists(custom_map_path):
            try:
                with open(custom_map_path, "r", encoding="utf-8") as f:
                    custom_map = json.load(f)
                    data.NPC_ID_MAP.update(custom_map) # Timpa kamus bawaan dengan nama kustom
            except Exception as e:
                print(f"[Logic] Gagal memuat npc_id_map.json: {e}")
        
        # 2. Pulihkan dari all_npcs.json (Sebagai Backup Absolut)
        all_npcs_path = os.path.join(os.path.dirname(__file__), "all_npcs.json")
        if os.path.exists(all_npcs_path):
            try:
                with open(all_npcs_path, "r", encoding="utf-8") as f:
                    all_npcs = json.load(f)
                    for npc in all_npcs:
                        nid = str(npc.get('id', '')).strip()
                        nname = npc.get('name', '').strip()
                        # Jangan timpa jika sudah ada di kamus custom (Prioritas 1)
                        if nid and nname and not nname.startswith("SID:") and nid not in data.NPC_ID_MAP:
                            data.NPC_ID_MAP[nid] = nname
            except Exception:
                pass

    def connect(self):
        res = core.connect()
        if core.pm:
            self.pm = core.pm
            self.base_address = core.pm.base_address
        return res

    def read_live_coords(self):
        return core.read_coords()

    def get_map_name(self):
        # Look up in loaded JSON dictionary
        mid = str(self.current_map_id)
        name = self.map_names.get(mid)
        
        # If found and valid, return name
        if name and name.strip():
            return name
            
        # Fallback: Return ID if name is missing or file not loaded
        return mid

    def _map_check_loop(self):
        while True:
            mid = core.read_map_id_memory()
            if mid == 0 and core.mumble:
                d = core.mumble.read()
                if d: mid = d.get("map_id", 0)
            
            if mid > 0 and mid not in core.MAP_DATA_DB:
                core.fetch_map_data(mid)

            self.current_map_id = mid
            self.map_ready = (mid > 0)
            time.sleep(1.0)
    
    def _log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}]{tag} {msg}")

    # ===============================
    # TELEPORT HELPERS
    # ===============================
    def get_live_entities(self):
        """Mengambil data real-time dari DLL via IPC"""
        if core.shared_entities:
            return core.shared_entities.read_entities()
        return []

    def teleport_to_entity(self, target_agent_id):
        """Mencari ID entitas di IPC dan melakukan teleport ke lokasinya"""
        entities = self.get_live_entities()
        
        if not entities:
            print("[Teleport] Gagal: Data entitas kosong atau DLL belum di-inject.")
            return False
            
        for ent in entities:
            if ent["id"] == target_agent_id:
                # Perhatikan: Kita perlu menguji apakah koordinat dari C++
                # sudah berskala benar. Jika game engine menggunakan skala inci, 
                # kita mungkin tidak perlu mengalikan dengan 1.2303125 seperti di teleport_custom.
                
                tx, ty, tz = ent["x"], ent["y"], ent["z"]
                print(f"[Teleport] Menemukan ID {target_agent_id}. Koordinat Mentah: {tx:.2f}, {ty:.2f}, {tz:.2f}")
                
                # Eksekusi Write Memory (menggunakan method raw agar tanpa scaling ekstra jika C++ sudah presisi)
                ok = core.write_coords_raw(tx, ty, tz)
                
                if ok:
                    print(f"[Teleport] Berhasil mendarat di entitas {target_agent_id}.")
                return ok
                
        print(f"[Teleport] Gagal: Agent ID {target_agent_id} tidak ditemukan di area render.")
        return False

    # Tambahkan ini sebagai fungsi sementara di dalam class GW2X_Logic
    def debug_entity_stream(self):
        entities = self.get_live_entities()
        if not entities:
            print("[-] IPC Terhubung tapi tidak ada entitas di area render (atau DLL belum dump data).")
        else:
            print(f"[+] TERDETEKSI: {len(entities)} Entitas di memori.")
            # Ambil 3 entitas pertama untuk verifikasi koordinat
            for ent in entities[:3]:
                print(f"    -> AgentID: {ent['id']} | Pos: ({ent['x']:.2f}, {ent['y']:.2f}, {ent['z']:.2f})")

    def _hotkey_monitor_loop(self):
        """Monitor hotkey F6 di latar belakang untuk pengujian."""
        import ctypes
        while True:
            # VK_F6 = 0x75
            if ctypes.windll.user32.GetAsyncKeyState(0x75) & 0x8000:
                print("[Hotkey] F6 ditekan: Memicu Teleport ke Entitas Terdekat...")
                self.teleport_to_nearest_live_entity()
                time.sleep(0.5) # Anti-spam
            time.sleep(0.01)

    def teleport_to_nearest_live_entity(self):
        """Membuktikan IPC berfungsi dengan mencari entitas terdekat."""
        entities = self.get_live_entities()
        current_pos = core.read_coords() # Mengambil posisi karakter Anda
        
        if not entities:
            print("[-] Gagal: Tidak ada data entitas dari DLL (IPC Kosong).")
            return
            
        if not current_pos:
            print("[-] Gagal: Posisi karakter tidak terdeteksi (Mumble Link aktif?).")
            return

        cx, cy, cz = current_pos
        nearest_ent = None
        min_dist = float('inf')

        for ent in entities:
            # Hitung jarak Euclidean 3D
            dx = ent['x'] - cx
            dy = ent['y'] - cy
            dz = ent['z'] - cz
            dist = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # Abaikan entitas yang terlalu dekat (kemungkinan diri sendiri)
            # Dan cari entitas dalam radius render (misal < 100m)
            if 2.0 < dist < min_dist:
                min_dist = dist
                nearest_ent = ent

        if nearest_ent:
            print(f"[!] Teleport ke ID: {nearest_ent['id']} | Jarak: {min_dist:.2f}m")
            # Menulis koordinat mentah dari C++ langsung ke memori game
            core.write_coords_raw(nearest_ent['x'], nearest_ent['y'], nearest_ent['z'])
        else:
            print("[-] Tidak ada entitas lain yang valid di sekitar Anda.")

    # ==========================================
    # LOGIKA UI LIVE ENTITIES
    # ==========================================
    def get_filtered_live_entities(self, category, search_query, attitude, sort_by, max_radius=9999.0):
        raw_entities = self.get_live_entities()
        if not raw_entities: return []

        current_pos = core.read_coords()
        cx, cy, cz = current_pos if current_pos else (0, 0, 0)

        local_name = None
        if hasattr(core, 'mumble') and core.mumble:
            m_data = core.mumble.read()
            if m_data and m_data.get("identity"):
                try:
                    import json
                    ident = json.loads(m_data["identity"])
                    local_name = ident.get("name")
                except: pass

        att_map = {0: "Friendly", 1: "Hostile", 2: "Neutral", 3: "Indifferent"}
        filtered = []

        for ent in raw_entities:
            ent_type = ent.get('type', -1)
            if category == "Players" and ent_type != 0: continue
            if category == "NPCs" and ent_type != 1: continue
            if category == "Objects" and ent_type not in (2, 3, 4): continue 

            dx, dy, dz = ent['x'] - cx, ent['y'] - cy, ent['z'] - cz
            dist = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # --- FILTER RADIUS MAKSIMAL ---
            if dist > max_radius:
                continue
                
            ent['distance'] = dist

            real_name = ent.get('real_name', '').strip()
            species_id = ent.get('species_id')
            ent['static_id'] = None

            extracted_static = None

            # ==========================
            # NPC TAB (Type 1)
            # ==========================
            if ent_type == 1:
                if real_name.startswith("SID:"):
                    extracted_static = real_name[4:]
                elif species_id and str(species_id) != "0":
                    extracted_static = str(species_id)
                else:
                    extracted_static = None
            elif ent_type in (2, 3, 4):
                extracted_static = real_name[5:] if real_name.startswith("ITEM:") else None
            else:
                extracted_static = None

            if extracted_static:
                try:
                    sid_int = int(extracted_static)
                    ent['static_id'] = sid_int
                    dict_name = data.NPC_ID_MAP.get(extracted_static)
                    if dict_name:
                        # Curated dict always wins
                        ent['name'] = dict_name
                    elif real_name and not real_name.startswith("SID:") and real_name != "Unknown":
                        # ArcdPS gave us a real display name — trust it
                        ent['name'] = real_name
                    else:
                        ent['name'] = f"SID:{sid_int}"
                except Exception:
                    ent['name'] = real_name if real_name else f"ID: {ent['id']}"
            else:
                if real_name and real_name != "Unknown" and not real_name.startswith("ID:") and not real_name.startswith("SID:"):
                    ent['name'] = real_name  # arcdps name used directly
                else:
                    ent['name'] = f"ID: {ent['id']}"

                if local_name and ent['name'] == local_name: continue
                if ent_type == 0 and dist < 0.1: continue

            alias = data.get_alias(self.current_map_id, ent)
            if alias:
                original_name = ent.get('name', '')
                ent['name'] = f"({alias}) {original_name}"

            raw_att_val = ent.get('raw_attitude', 2)
            ent['att_str'] = att_map.get(raw_att_val, f"Raw:{raw_att_val}") 

            if search_query and search_query.lower() not in ent['name'].lower(): continue
            if attitude != "All" and ent['att_str'] != attitude: continue

            filtered.append(ent)

        if sort_by == "Distance": filtered.sort(key=lambda x: x['distance'])
        elif sort_by == "Name": filtered.sort(key=lambda x: x['name'])
        
        return filtered
    
    def get_active_events(self, active_only=True, documented_only=False):
        self.event_detector.current_map_id = self.current_map_id
        return self.event_detector.get_active_events(
            active_only=active_only, documented_only=documented_only)

    def bind_event_runtime_id(self, event_entry):
        self.event_detector.current_map_id = self.current_map_id
        return self.event_detector.bind_runtime_id(event_entry)

    def get_live_event_status(self):
        return core.get_live_event_status()


    def is_event_db_ready(self):
        return EventDetector._fetched

    def match_npcs_to_events(self, npc_list=None):
        """For each active event, find hostile NPCs whose position falls within
        the event's radius. Returns list of {event, npcs_inside}.
        npc_list: list of dicts with keys 'name', 'x', 'z' in game meters.
                If None, reads from IPC automatically.
        """
        events = self.get_active_events(active_only=True)
        if not events:
            return []

        # Pull NPC positions from IPC if not provided
        if npc_list is None:
            ipc = core.read_ipc_data() if hasattr(core, 'read_ipc_data') else None
            if not ipc:
                return []
            npc_list = []
            for ent in ipc.get("entities", []):
                # type 1 = NPC, attitude 0 = hostile
                if ent.get("type") == 1 and ent.get("attitude") == 0:
                    x = ent.get("x") or ent.get("pos_x")
                    z = ent.get("z") or ent.get("pos_z")
                    if x is not None and z is not None:
                        npc_list.append({
                            "name":    ent.get("name", f"SID:{ent.get('species_id','')}"),
                            "agent_id": ent.get("agent_id"),
                            "x": x,
                            "z": z,
                        })

        result = []
        for ev in events:
            if ev["game_x"] is None:
                continue
            npcs_inside = []
            for npc in npc_list:
                dx = npc["x"] - ev["game_x"]
                dz = npc["z"] - ev["game_z"]
                dist = math.sqrt(dx*dx + dz*dz)
                if dist <= (ev["radius_m"] * 1.5):  # 1.5x tolerance for patrol radius
                    npcs_inside.append({**npc, "dist_m": round(dist, 1)})

            result.append({
                "event":      ev,
                "npcs_inside": sorted(npcs_inside, key=lambda n: n["dist_m"]),
            })

        return result

    def teleport_to_event(self, event_entry):
        cx_m   = event_entry.get("cx_m")
        cz_m   = event_entry.get("cz_m")
        map_id = event_entry.get("map_id", self.current_map_id)

        if cx_m is None or cz_m is None:
            return False, f"No location data for '{event_entry.get('name','?')}'"

        matched = event_entry.get("matched_npcs", [])
        SCALE   = 1.2303125

        if matched:
            # Teleport to first matched entity (name-correlated first, then hostile)
            npc = matched[0]
            tp = {
                "name":   event_entry.get("name", "Event"),
                "map_id": int(map_id),
                "x":      npc["x"] / SCALE,
                "y":      npc["y"] / SCALE,
                "z":      npc["z"] / SCALE,
            }
        else:
            current_y = 0
            try:
                coords = core.read_coords()
                if coords:
                    current_y = coords[1]
            except Exception:
                pass
            tp = {
                "name":   event_entry.get("name", "Event"),
                "map_id": int(map_id),
                "x":      cx_m,
                "y":      current_y,
                "z":      cz_m,
            }

        return self.teleport_smart_custom(tp)
    # ===============================
    # TELEPORT HELPERS
    # ===============================
    def teleport_to_exact_coords(self, x, y, z):
        """
        Menerima perintah dari UI (Live Entities) untuk teleport langsung ke koordinat X, Y, Z.
        """
        try:
            # Gunakan fungsi write_coords_raw yang memang sudah ada di core Anda
            ok = core.write_coords_raw(x, y, z) 
            
            if ok:
                print(f"[Logic] Teleport executed to Entity at -> X: {x:.3f}, Y: {y:.3f}, Z: {z:.3f}")
            else:
                print(f"[Logic] Write failed for Entity -> X: {x:.3f}, Y: {y:.3f}, Z: {z:.3f}")
                
        except AttributeError:
            # Fallback jika write_coords_raw tidak ada, coba write_coords biasa
            try:
                core.write_coords(x, y, z)
                print(f"[Logic] Teleport executed using scaled write_coords to -> X: {x:.3f}, Y: {y:.3f}, Z: {z:.3f}")
            except Exception as e:
                print(f"[Logic-Error] Kegagalan fallback teleportasi: {e}")
        except Exception as e:
            print(f"[Logic-Error] Kegagalan saat teleportasi: {e}")

    def teleport_from_map_double_click(self, map_dx, map_dy):
        # 1.6404 is the constant ratio (Meters * 39.37 / 24)
        # We divide MapUnits by this to get Meters.
        ratio = 1.6404 
        
        val_x_meters = map_dx / ratio
        val_y_meters = map_dy / ratio
        
        current = core.read_coords()
        if not current: return False
        cx, cy, cz = current
        
        # Apply Relative Teleport
        # NOTE: Map Y (South) is Game Z (South/North) inverted
        tx = cx + val_x_meters
        tz = cz - val_y_meters 
        
        print(f"[MapClick] Teleporting... Delta Meters: {val_x_meters:.2f}, {val_y_meters:.2f}")
        
        scale = 1.2303125
        core.write_coords(tx * scale, cy * scale, tz * scale)
        return True

    def teleport_manual_str(self, val_str):
        try:
            val_str = val_str.replace("[", "").replace("]", "").strip()
            parts = [float(x.strip()) for x in val_str.split(",")]
            if len(parts) != 3: return False, "Invalid format (x,y,z)"
            scale = 1.2303125
            core.write_coords(parts[0]*scale, parts[1]*scale, parts[2]*scale)
            return True, "Teleported"
        except Exception as e:
            return False, str(e)

    def teleport_vertical(self, val_str):
        try: 
            val = float(val_str)
            pos = core.read_coords()
            if not pos: return
            # pos[1] is usually height in GW2 memory read logic (X, Y=Height, Z)
            scale = 1.2303125
            core.write_coords(pos[0]*scale, (pos[1]+val)*scale, pos[2]*scale)
        except: pass

    def teleport_relative(self, dist_str, height_str=None, direction='n'):
        try:
            map_dist = float(dist_str)
        except:
            return

        try:
            height = float(height_str) if height_str not in (None, "", "0") else None
        except:
            height = None

        MAP_TO_WORLD = 1.0 / 39.37
        dist = map_dist * MAP_TO_WORLD

        pos = core.read_coords()
        if not pos:
            return
        x, y, z = pos

        dx = dz = 0.0

        if direction == 't':
            if not hasattr(self, "target_pos"):
                return

            tx, ty, tz = self.target_pos

            vx = tx - x
            vz = tz - z

            length = math.sqrt(vx * vx + vz * vz)
            if length < 0.001:
                return

            if dist >= length:
                x, z = tx, tz
            else:
                vx /= length
                vz /= length
                x += vx * dist
                z += vz * dist

        elif core.mumble:
            mumble_data = core.mumble.read()
            if mumble_data and "fCameraFront" in mumble_data:
                fx, _, fz = mumble_data["fCameraFront"]

                length = math.sqrt(fx * fx + fz * fz)
                if length > 0.001:
                    fx /= length
                    fz /= length

                    if direction == 'n':
                        x += fx * dist
                        z += fz * dist
                    elif direction == 's':
                        x -= fx * dist
                        z -= fz * dist
                    elif direction == 'e':
                        x += fz * dist
                        z -= fx * dist
                    elif direction == 'w':
                        x -= fz * dist
                        z += fx * dist

        else:
            if direction == 'n':   z += dist
            elif direction == 's': z -= dist
            elif direction == 'e': x += dist
            elif direction == 'w': x -= dist

        if height is not None:
            y += height

        scale = 1.2303125
        core.write_coords(x * scale, y * scale, z * scale)

    
    def _confirm_continuous_hp_drop(self, duration=2.0):
        start = time.time()
        last = None

        while time.time() - start < duration:
            if self.auto_tp_stop_event.is_set():
                return False

            cur, _ = self._check_health_status()
            if cur is None:
                return False

            if last is not None and cur >= last:
                return False  # stabilized or healed

            last = cur
            time.sleep(0.15)

        return True  # confirmed continuous drop
    
    def _build_random_order(self, total, start_index=0):
        indices = list(range(total))
        if start_index in indices:
            indices.remove(start_index)
        random.shuffle(indices)
        return [start_index] + indices
    
    def _clamp_to_tp_if_needed(self, tp, last_clamp_ts):
        pos = core.read_coords()
        if not pos:
            return last_clamp_ts

        dx = pos[0] - tp["x"]
        dy = pos[1] - tp["y"]
        dz = pos[2] - tp["z"]

        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist > self.MAX_TP_DRIFT:
            now = time.time()
            if now - last_clamp_ts >= self.CLAMP_COOLDOWN:
                scale = 1.2303125
                core.write_coords(
                    tp["x"] * scale,
                    tp["y"] * scale,
                    tp["z"] * scale
                )
                return now

        return last_clamp_ts
        
    def press_key_and_track(self, scan_code_hex, duration=0.05):
        """
        Sends a key AND updates map UI state deterministically.
        """
        core.presskey(self.window_title, scan_code_hex, duration)

        # MAP OPEN
        if scan_code_hex == self.map_scan:
            self.map_ui_open = True
            print("[MapUI] OPEN (M pressed)")

        # MAP CLOSE
        elif scan_code_hex == self.esc_scan:
            if self.map_ui_open:
                self.map_ui_open = False
                print("[MapUI] CLOSED (ESC pressed)")
    
    def is_map_open(self):
        if not core.mumble:
            return False
        data = core.mumble.read()
        if not data:
            return False
        return data.get("is_map_open", False)

    def open_map(self):
        """
        Explicitly opens the world map and tracks state.
        """
        print("[MapUI] Opening map...")
        self.press_key_and_track(self.map_scan, 0.05)

    def close_map(self):
        """
        Explicitly closes the world map.
        """
        print("[MapUI] Closing map...")
        self.press_key_and_track(self.esc_scan, 0.05)

    def scan_commanders(self, timeout=2.5):
        """Read only commanders proven by the resolver-owned collection."""
        if not core.commander_map:
            return None, "KX-Vision V73 commander registry is not initialized"

        result = core.commander_map.request_scan(timeout=timeout)
        if not result.get("ok"):
            return None, result.get("message", "Commander registry failed")
        map_error = self._registry_map_error(result)
        if map_error:
            return None, map_error

        points = list(result.get("commanders", []))
        points = self._append_nearby_commanders(points, result)
        if not points:
            return None, "No active commander tag in the map-wide feed"
        self.commander_names.decorate(points, self._read_identity_entities())
        self._decorate_remote_points(points)
        result["points"] = points
        return result, f"Found {len(points)} map-wide commander(s); map stayed closed"

    def scan_map_icons(self, timeout=2.5):
        """Read all non-commander map/NPC icon records for this map."""
        if not core.commander_map:
            return None, "KX-Vision V73 commander registry is not initialized"
        result = core.commander_map.request_scan(timeout=timeout)
        if not result.get("ok"):
            return None, result.get("message", "Map-icon registry failed")
        map_error = self._registry_map_error(result)
        if map_error:
            return None, map_error
        map_id = int(result.get("map_id", 0) or 0)
        points = list(result.get("markers", []))
        points = self._merge_map_icon_cache(
            points, map_id, int(result.get("map_epoch", 0) or 0)
        )
        points = self._dedupe_remote_points(points)
        if not points:
            return None, "No map/NPC icon record is currently available"
        self.event_detector.current_map_id = map_id
        live_events = self.event_detector.get_active_events()
        self._classify_proven_event_icons(points)
        self.event_names.decorate(points, map_id, live_events)
        self._decorate_nearby_npc_names(points)
        self._decorate_remote_points(points)
        result["points"] = points
        return result, f"Found {len(points)} map/NPC icon(s); map stayed closed"

    @staticmethod
    def _classify_proven_event_icons(points):
        """Mark only event icon codes proven by the supplied active test."""
        proven_active = {0x83E, 0x841}
        for point in points:
            icon_code = int(point.get("icon_code", 0) or 0)
            if icon_code in proven_active:
                point["active_event_icon"] = True
                point["active_event_icon_code"] = icon_code
                point["event_status_source"] = "Live map event-objective icon"
        return points

    # Compatibility aliases for older UI/extensions. These records were
    # incorrectly called squad markers in V55; they are map/NPC icons.
    def scan_squad_markers(self, timeout=2.5):
        return self.scan_map_icons(timeout=timeout)

    def _runtime_map_id(self):
        """Read the selected observer's PID-scoped authoritative map id."""
        try:
            if core.commander_map:
                map_id = int(core.commander_map.current_map_id() or 0)
            else:
                map_id = int(core.read_map_id_memory() or 0)
            if map_id > 0:
                return map_id
        except Exception:
            pass
        return 0

    def _registry_map_error(self, result):
        current_map = self._runtime_map_id()
        registry_map = int(result.get("map_id", 0) or 0)
        if current_map and registry_map and current_map != registry_map:
            return (f"Remote tracker is changing maps ({registry_map} -> "
                    f"{current_map}); wait for the current-map packets")
        return None

    @staticmethod
    def _dedupe_remote_points(points, tolerance=1.0):
        """Collapse layered icon records that resolve to the same world XYZ."""
        unique = []
        tolerance2 = float(tolerance) ** 2
        for point in sorted(points, key=lambda p: int(
                p.get("update_sequence", 0)), reverse=True):
            world = point.get("world")
            if not world:
                continue
            x, y, z = map(float, world)
            duplicate = None
            for kept in unique:
                kx, ky, kz = map(float, kept["world"])
                if ((x-kx)**2 + (y-ky)**2 + (z-kz)**2) <= tolerance2:
                    duplicate = kept
                    break
            if duplicate is None:
                point = dict(point)
                point["merged_logical_ids"] = [int(point.get("logical_id", 0))]
                unique.append(point)
            else:
                duplicate["merged_logical_ids"].append(
                    int(point.get("logical_id", 0)))
        return unique

    def _merge_map_icon_cache(self, points, map_id, map_epoch, ttl=90.0):
        """Bridge brief removals, strictly inside the current map epoch."""
        now = time.monotonic()
        scope = (int(map_id or 0), int(map_epoch or 0))
        cache = self._map_icon_cache.setdefault(scope, {})
        live_ids = set()
        for point in points:
            logical_id = int(point.get("logical_id", 0) or 0)
            key_a = int(point.get("key_a", 0) or 0)
            identity = (logical_id, key_a) if logical_id == 0 else (logical_id, 0)
            live_ids.add(identity)
            cache[identity] = (dict(point), now)
        merged = []
        for identity, (cached, seen_at) in list(cache.items()):
            age = now - seen_at
            if age > float(ttl):
                cache.pop(identity, None)
                continue
            item = dict(cached)
            item["cached"] = identity not in live_ids
            item["cache_age_seconds"] = age if item["cached"] else 0.0
            merged.append(item)
        self._map_icon_cache = {scope: cache}
        return merged

    @staticmethod
    def _read_identity_entities():
        """Read the independent Live Entities snapshot."""
        if not core.shared_entities:
            return []
        try:
            return list(core.shared_entities.read_entities())
        except Exception as exc:
            print(f"[RemoteNames65] Entity snapshot failed: {exc}")
            return []

    def _append_nearby_commanders(self, points, result):
        """Append ChCliCharacter-proven nearby commanders independently.

        This function never promotes, edits, caches, or keys a map-packet
        record. A nearby point is a separate local-only item with its own
        live agent identity and current coordinates.
        """
        entities = self._read_identity_entities()
        tagged = [
            entity for entity in entities
            if int(entity.get("type", -1)) == 0
            and bool(entity.get("is_commander"))
        ]
        if not tagged:
            return points

        combined = list(points)
        for entity in tagged:
            world = (
                float(entity.get("x", 0.0)),
                float(entity.get("y", 0.0)),
                float(entity.get("z", 0.0)),
            )
            # Prefer the live local-range item when a remote packet point is
            # already at the same player. This is presentation deduplication;
            # the two detectors remain independent.
            kept = []
            for point in combined:
                if point.get("local_only"):
                    kept.append(point)
                    continue
                remote = point.get("world", (float("inf"),) * 3)
                distance2 = sum(
                    (float(remote[index]) - world[index]) ** 2
                    for index in range(3)
                )
                if distance2 > 4.0:
                    kept.append(point)
            combined = kept

            agent_id = int(entity.get("id", 0) or 0)
            combined.append({
                "logical_id": 0x80000000 | (agent_id & 0x7FFFFFFF),
                "key_a": 0,
                "key_b": 0,
                "key_count": 0,
                "icon_code": 0,
                "flags": 2,
                "world": world,
                "x": world[0],
                "y": world[1],
                "z": world[2],
                "map_id": int(result.get("map_id", 0) or 0),
                "map_epoch": int(result.get("map_epoch", 0) or 0),
                "local_only": True,
                "live_agent_id": agent_id,
                "live_name": str(entity.get("real_name", "") or ""),
                "source": "Independent nearby commander signature",
            })
        return combined

    def _decorate_nearby_npc_names(self, points, max_distance=6.0):
        """Attach an NPC name only after an exact nearby-coordinate match."""
        if not core.shared_entities:
            return points
        try:
            npcs = []
            for entity in core.shared_entities.read_entities():
                if int(entity.get("type", -1)) != 1:
                    continue
                name = str(entity.get("real_name", "") or "").strip()
                if name and name.casefold() not in {"unknown", "unnamed"}:
                    npcs.append(entity)
            limit2 = float(max_distance) ** 2
            for point in points:
                if point.get("event_name"):
                    continue
                px, py, pz = map(float, point.get("world", (0.0, 0.0, 0.0)))
                matches = []
                for entity in npcs:
                    distance2 = ((px-float(entity["x"])) ** 2 +
                                 (py-float(entity["y"])) ** 2 +
                                 (pz-float(entity["z"])) ** 2)
                    if distance2 <= limit2:
                        matches.append((distance2, entity))
                if matches:
                    distance2, entity = min(matches, key=lambda row: row[0])
                    point["npc_name"] = str(entity.get("real_name", "")).strip()
                    point["npc_agent_id"] = int(entity.get("id", 0) or 0)
                    point["npc_match_distance_m"] = math.sqrt(distance2)
                    point["source"] = "Exact nearby NPC coordinate"
        except Exception as exc:
            print(f"[MapIconName63] Nearby NPC join failed: {exc}")
        return points

    def _decorate_remote_points(self, points):
        player_pos = None
        try:
            raw = core.read_coords_memory()
            if raw:
                scale = 1.2303125
                player_pos = tuple(float(value) / scale for value in raw)
        except Exception:
            pass
        if player_pos is None:
            player_pos = core.read_coords() or (0.0, 0.0, 0.0)
        px, py, pz = (float(player_pos[0]), float(player_pos[1]),
                      float(player_pos[2]))
        for point in points:
            x, y, z = point["world"]
            dx, dz = x - px, z - pz
            vertical = "N" if dz > 0.5 else "S" if dz < -0.5 else ""
            horizontal = "E" if dx > 0.5 else "W" if dx < -0.5 else ""
            point["direction"] = vertical + horizontal or "HERE"
            point["distance_m"] = math.sqrt(dx * dx + (y - py) ** 2 + dz * dz)
        points.sort(key=lambda p: p["distance_m"])
        for index, point in enumerate(points, 1):
            point["candidate_number"] = index

    def teleport_to_commander(self, result=None, point=None):
        """Teleport to one selected commander using exact packet XYZ."""
        if result is None:
            result, message = self.scan_commanders()
            if not result:
                print(f"[CommanderTP] BLOCKED: {message}")
                return False, message
        if point is None:
            point = result["points"][0]
        if point.get("local_only"):
            agent_id = int(point.get("live_agent_id", 0) or 0)
            for entity in self._read_identity_entities():
                if (int(entity.get("id", 0) or 0) == agent_id and
                        bool(entity.get("is_commander"))):
                    current = dict(point)
                    world = (float(entity["x"]), float(entity["y"]),
                             float(entity["z"]))
                    current.update({"world": world, "x": world[0],
                                    "y": world[1], "z": world[2]})
                    return self._teleport_remote_point(
                        current, "nearby commander")
            return False, "Nearby commander is no longer tagged or in range"
        point = self._refresh_remote_point(point, "commanders")
        if point is None:
            return False, "Commander record expired during a map change; scan again"
        return self._teleport_remote_point(point, "commander")

    def teleport_to_map_icon(self, result=None, point=None):
        if result is None:
            result, message = self.scan_map_icons()
            if not result:
                return False, message
        if point is None:
            point = result["points"][0]
        point = self._refresh_remote_point(point, "markers")
        if point is None:
            return False, "Map/NPC icon expired during a map change; scan again"
        return self._teleport_remote_point(point, "map/NPC icon")

    def teleport_to_squad_marker(self, result=None, point=None):
        return self.teleport_to_map_icon(result=result, point=point)

    def _refresh_remote_point(self, point, collection):
        latest = core.commander_map.snapshot() if core.commander_map else {}
        if not latest.get("ok") or self._registry_map_error(latest):
            return None
        candidates = list(latest.get(collection, []))
        if collection == "commanders":
            self.commander_names.decorate(
                candidates, self._read_identity_entities())
        if collection != "commanders":
            candidates = self._dedupe_remote_points(candidates)
        logical_id = int(point.get("logical_id", -1))
        selected_key = int(point.get("key_a", 0) or 0)
        for candidate in candidates:
            candidate_logical = int(candidate.get("logical_id", -2))
            candidate_key = int(candidate.get("key_a", 0) or 0)
            if (candidate_logical == logical_id and
                    (logical_id != 0 or candidate_key == selected_key)):
                return candidate
        if collection != "commanders":
            # Generic map records can be removed/recreated under a new logical
            # id between opening the chooser and clicking its row. The selected
            # packet XYZ remains valid only inside the exact same map epoch.
            selected_map = int(point.get("map_id", 0) or 0)
            selected_epoch = int(point.get("map_epoch", 0) or 0)
            latest_map = int(latest.get("map_id", 0) or 0)
            latest_epoch = int(latest.get("map_epoch", 0) or 0)
            if (selected_map and selected_epoch and
                    selected_map == latest_map and selected_epoch == latest_epoch):
                fallback = dict(point)
                fallback["source"] = "Map/NPC snapshot (same map epoch)"
                print(
                    "[MapIconTP63] Record ID changed before selection; "
                    f"using same-epoch snapshot map={latest_map} "
                    f"epoch={latest_epoch} logical=0x{logical_id:X}."
                )
                return fallback
        return None

    def _teleport_remote_point(self, point, kind):
        world = point.get("world")
        if not world or not all(math.isfinite(float(v)) for v in world):
            return False, f"{kind.title()} has no valid XYZ"
        x, y, z = map(float, world)
        if not core.write_coords_raw(x, y, z):
            return False, f"Failed to write {kind} coordinates"
        logical_id = int(point.get("logical_id", 0))
        message = (
            f"Teleported to {kind} 0x{logical_id:X} at "
            f"({x:.2f}, {y:.2f}, {z:.2f})"
        )
        print(f"[RemoteTP] {message}")
        return True, message
        
    def trigger_map_teleport(self, screen_x, screen_y):
        import time
        
        res, msg = self.map_target.calculate_mouse_teleport(screen_x, screen_y)
        if not res:
            print("[MapTP] FAILED:", msg)
            return False
            
        tx, ty, tz = res

        # Jika objek eksis di memori, koordinat 3D sudah presisi. Langsung mendarat.
        if msg == "SNAP_SUCCESS":
            ok = core.write_coords_raw(tx, ty, tz)
            print(f"[MapTP] INSTANT SNAP -> {tx:.2f}, {ty:.2f}, {tz:.2f}")
            return ok

        # Jika klik area kosong, eksekusi Forced Chunk Load (Hover) lalu Pindai
        elif msg == "NEEDS_HOVER":
            if core.write_coords_raw(tx, ty, tz): 
                print(f"[MapTP] Stage 1: Hovering at {ty:.1f}m. Forcing map chunk load...")
                
                time.sleep(0.8) # Beri waktu engine memuat data topografi ke memori
                
                final_ty = self.map_target.get_entity_height_only(tx, tz)
                
                if final_ty is not None:
                    print(f"[MapTP] Stage 2: Entity loaded post-hover. Landing.")
                    return core.write_coords_raw(tx, final_ty, tz)
                else:
                    print(f"[MapTP] Stage 2: No surface found. Staying at hover height.")
                    return True # Biarkan di udara agar tidak tembus map
                    
        return False

    def teleport_from_map_click(self, screen_x, screen_y):
        # --- HARD GUARD ---
        if not self.is_map_open():
            print("[MapTP] BLOCKED — map is not open")
            return False

        res, msg = self.map_target.calculate_mouse_teleport(screen_x, screen_y)
        if not res:
            print("[MapTP] FAILED:", msg)
            return False

        tx, ty, tz = res

        if core.write_coords_raw(tx, ty, tz):
            print(f"[MapTP] Landed @ ({tx:.2f}, {ty:.2f}, {tz:.2f})")
            return True

        print("[MapTP] Write failed")
        return False

    def teleport_from_cursor(self):
        # 1. Cek Map Tertutup
        if self.is_map_open():
            print("[MouseTP] BLOCKED — close map first")
            return False
            
        # 2. Baca Koordinat
        coords = core.read_mouse_3d_position()
        
        if not coords:
            # Pesan error sudah diprint di core jika +Inf
            return False
        mx, my, mz = coords
        
        # DEBUG: Raw mouse position values
        print(f"[MouseDebug] Raw from read_mouse_3d_position(): X={mx:.2f}, Y={my:.2f}, Z={mz:.2f}")
        
        # 3. Validasi Angka
        if not all(is_valid_coord(v) for v in (mx, my, mz)):
            print(f"[MouseTP] BLOCKED: invalid coords detected ({mx:.1f}, {my:.1f}, {mz:.1f})")
            return False
            
        # 4. Offset Tinggi (+0.5)
        safe_y = my + 0.25
        
        # DEBUG: Show height adjustment
        print(f"[MouseDebug] Height adjusted: {my:.2f} -> {safe_y:.2f} (+0.25m)")
        
        # 5. Konversi ke game coords
        scale = 1.2303125
        game_x = mx * scale
        game_y = safe_y * scale
        game_z = mz * scale
        
        # DEBUG: Show final values
        print(f"[MouseDebug] Meter coords: ({mx:.2f}, {safe_y:.2f}, {mz:.2f})")
        print(f"[MouseDebug] Game coords:  ({game_x:.2f}, {game_y:.2f}, {game_z:.2f})")
        print(f"[MouseTP] Attempting TP to: {mx:.2f}, {safe_y:.2f}, {mz:.2f}")
        
        # 6. Eksekusi
        ok = core.write_coords(game_x, game_y, game_z)
        
        if ok:
            print("[MouseTP] Success.")
        else:
            print("[MouseTP] Write failed")
            
        return ok

    # ===============================
    # RELOG LOGIC
    # ===============================
    def relog_game(self):
        """Executes relog sequence, handles double relog and auto-restart loop."""
        iterations = 2 if self.auto_relog_twice_enabled else 1

        def relog_sequence():
            if not core.is_gw2_running():
                print("[Relog] GW2 not running, abort relog")
                return

            print(f"[Relog] Starting sequence ({iterations} cycles)...")

            for i in range(iterations):
                try:
                    hwnd = win32gui.FindWindow(None, self.window_title)
                    if not hwnd:
                        print("[Relog] GW2 window not found, retrying...")
                        time.sleep(1.0)
                        continue
                    
                    time.sleep(0.5)
                    core.presskey(self.window_title, "58", 0.1) # F12
                    time.sleep(1.8)

                    if hwnd:
                        core.send_background_click(
                        hwnd,
                        self.relog_char_select_x,
                        self.relog_char_select_y
                    )
                    time.sleep(2.0) 

                    core.presskey(self.window_title, "1C", 0.12) # Enter
                    time.sleep(2.0)
                    core.presskey(self.window_title, "1C", 0.12) # Enter again
                    
                    if i < iterations - 1:
                        print("[Relog] Double relog active. Waiting 25s...")
                        time.sleep(25.0)

                except Exception as e:
                    print(f"[Relog] Error: {e}")

            print("[Relog] Finished.")
            
            if (
                self.auto_relog_loop_enabled
                and self._last_auto_tp_args
                and not self._user_stop_requested
            ):
                print("[RelogLoop] Restarting Auto TP in 5s...")
                time.sleep(5.0)

                if self._user_stop_requested:
                    print("[RelogLoop] Cancelled by user STOP")
                    return

                self.auto_tp_stop_event.clear()
                self.auto_tp_running = False

                self.auto_tp_stop_event.clear()
                self.auto_tp_running = False

                # Force restart from beginning after relog
                self._last_auto_tp_args["start_index"] = 0
                self._last_auto_tp_args["post_relog_wait"] = True

                self.start_auto_teleport(**self._last_auto_tp_args)

        threading.Thread(target=relog_sequence, daemon=True).start()

    # ===============================
    # MOVEMENT & TELEPORT
    # ===============================
    def set_speed_config(self, index, active, val_str):
        try: val = float(val_str)
        except: val = 294.0
        self.speed_targets[index] = {"active": active, "val": val}

    def _movement_loop(self):
        while True:
            for idx in range(3):
                target = self.speed_targets[idx]
                if not target["active"]:
                    if self.speed_current[idx] is not None:
                        core.write_specific_speed(idx, 294.0 / 39.37)
                        self.speed_current[idx] = None
                    continue
                engine_val = target["val"] / 39.37
                if self.speed_current[idx] != engine_val:
                    core.write_specific_speed(idx, engine_val)
                    self.speed_current[idx] = engine_val           
            time.sleep(0.05)
            
            data = core.mumble.read()
            if data and data.get("mount_index", 0) == 5:
                time.sleep(0.05)
                continue
            
    def teleport_custom(self, tp):
        if not self.map_ready: return False, "Map not ready"
        
        if tp.get("map_id", 0) != self.current_map_id and not tp.get("allow_cross_map", False):
            return False, "Teleport blocked (Wrong Map)"

        scale = 1.2303125
        core.write_coords(
            tp["x"] * scale,
            tp["y"] * scale,
            tp["z"] * scale
        )
        self._log("[TPCheck]", "READY (arrival/stability satisfied)")
        return True, "Teleported"
    
    def teleport_smart_custom(self, tp, chat_coords=(214, 1377)):
        """
        Smart teleport:
        - Same map OR Map ID 0 -> direct teleport (Local)
        - Different map -> waypoint first, wait for map load, then teleport
        """
        if not self.map_ready:
            return False, "Map not ready"

        target_map = int(tp.get("map_id", 0))
        current_map = self.current_map_id

        # --- FIX: ALLOW MAP 0 (Generic/Legacy TPs) ---
        # If the TP has ID 0, we assume it belongs to the current map.
        if target_map == current_map or target_map == 0:
            return self.teleport_custom(tp)

        # --- DIFFERENT MAP ---
        wp = self.get_starting_waypoint_for_map(target_map)
        if not wp:
            return False, f"No waypoint found for map {target_map}"

        self._log(
            "[SmartTP]",
            f"Cross-map detected: {current_map} -> {target_map}, waypoint='{wp.get('name')}'"
        )

        # 1. Teleport to waypoint
        ok, msg = self.teleport_smart_waypoint(
            wp,
            chat_coords[0],
            chat_coords[1]
        )
        if not ok:
            return False, f"Waypoint teleport failed: {msg}"

        # 2. Wait for map change
        start = time.time()
        while time.time() - start < 20.0:
            if self.current_map_id == target_map:
                break
            time.sleep(0.5)

        if self.current_map_id != target_map:
            return False, "Map change timeout"

        # 3. Final teleport to target TP
        return self.teleport_custom(tp)

    def teleport_global(self, coord_str, height_str, mode="wiki"):
        try:
            raw = coord_str.replace("[", "").replace("]", "").strip()
            c_x, c_y = map(float, raw.split(","))
            mid = self.current_map_id
            if mid == 0: return False, "Map ID not detected"

            if mode == "wiki":
                res = core.continent_to_game_coords(c_x, c_y, mid)
            else:
                res = core.timer_to_game_coords(c_x, c_y, mid)

            if not res: return False, f"No data for Map {mid}"
            
            pos = core.read_coords()
            try:
                h = float(height_str)
            except:
                h = (pos[1] + 5) if pos else 100
            
            scale = 1.2303125
            core.write_coords(res[0] * scale, h * scale, res[1] * scale)
            self._log("[TPCheck]", "READY (arrival/stability satisfied)")
            return True, "Teleported"
        except Exception as e:
            self._log("[TPCheck]", "TIMEOUT (not ready)")
            return False, str(e)
    
    # --- UPDATE: SAVE FUNCTION ---
    def save_npcs(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "all_npcs.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.npcs, f, indent=2)
            print(f"[Logic] Saved {len(self.npcs)} NPCs.")
        except Exception as e:
            print(f"[Logic] Error saving NPCs: {e}")    

    # --- UPDATE: TELEPORT NPC (Support Game Coords) ---
    def teleport_npc(self, npc):
        try:
            c = npc.get("coord")
            if not c or len(c) < 2: 
                return False, "Invalid NPC Coords"
            
            # CASE A: Game Coords (Added/Synced by User -> [x, y, z])
            if len(c) == 3:
                scale = 1.2303125
                core.write_coords(c[0] * scale, c[1] * scale, c[2] * scale)
                return True, f"Teleported to {npc.get('name', 'NPC')}"

            # CASE B: API/Continent Coords (Original JSON -> [u, v])
            mid = self.current_map_id
            if mid == 0: return False, "Map not ready"

            res = core.continent_to_game_coords(c[0], c[1], mid)
            if not res: 
                return False, "Conversion failed (Wrong Map?)"
            
            pos = core.read_coords()
            h = (pos[1] + 20) if pos else 500
            
            scale = 1.2303125
            core.write_coords(res[0] * scale, h * scale, res[1] * scale)
            return True, f"Teleported to {npc.get('name', 'NPC')}"
        except Exception as e:
            return False, str(e)
            
    def trigger_waypoint_chat(self, wp_id, chat_x, chat_y):
        import base64, struct
        try:
            # --- BAGIAN 1: GENERATE CODE ---
            # Format: Header(4) + ID(2 bytes) + Padding(0)
            raw = struct.pack('<BHH', 4, int(wp_id), 0)
            code = f"[&{base64.b64encode(raw).decode('utf-8')}]"
            
            print(f"[AutoTP] Generated Code: {code}")

            # --- BAGIAN 2: KIRIM KE CHAT ---
            core.send_chat_message(self.window_title, code)
            
            # --- BAGIAN 3: KLIK LINK (PERBAIKAN) ---
            # Tunggu sedikit lebih lama agar teks muncul sempurna di layar game
            time.sleep(0.5) 
            
            # Pastikan koordinat adalah integer
            cx = int(float(chat_x))
            cy = int(float(chat_y))
            
            print(f"[AutoTP] Clicking Chat Link at Screen Coords: {cx}, {cy}")
            core.mouse_click(cx, cy)
            
            # --- BAGIAN 4: TELEPORT SEQUENCE ---
            print("[AutoTP] Waiting for Map to open...")
            # Delay agar animasi buka map selesai
            time.sleep(1.5) 
            
            center = core.get_window_center(self.window_title)
            if center:
                cnt_x, cnt_y = center
                print(f"[AutoTP] Attempting Native Double Click at {cnt_x}, {cnt_y}")
                
                # A. Native Double Click (Metode Utama untuk TP)
                core.double_click_background(cnt_x, cnt_y)
                
                # B. Backup Plan: Konfirmasi Tombol Enter
                # Jika double click hanya dianggap 1 klik (muncul dialog biaya),
                # tekan Enter untuk memilih "Yes".
                time.sleep(0.6) 
                core.presskey(self.window_title, "1C", 0.1) # 1C = Enter
                
                return True, "Teleport Sequence Complete"
            else:
                return False, "Could not find window center"
                
        except Exception as e:
            print(f"[AutoTP] Error: {e}")
            return False, str(e)
            
    def teleport_smart_waypoint(self, wp_data, chat_x, chat_y):
        """
        Logic cerdas:
        1. Cek apakah Map ID sama.
        2. Cek apakah Waypoint memiliki koordinat (XYZ).
        3. Cek Health Player.
        -> Jika HIDUP & Sama Map & Ada Coords: Direct Teleport (Instan).
        -> Jika MATI (HP <= 0): Chat Link (Wajib agar Revive).
        -> Jika Beda Map / Tidak ada Coords: Chat Link (Loading Screen).
        """
        current_map = self.current_map_id
        target_map = wp_data.get("map_id", 0)
        coords = wp_data.get("coord") # Diload dari [ID, X, Y, Z]

        # 1. Check Health State
        cur_hp, _ = self._check_health_status()
        is_dead = (cur_hp is not None and cur_hp <= 0)

        # DEBUG LOG
        print(f"[SmartTP] CurMap:{current_map} TgtMap:{target_map} Dead:{is_dead} Coords:{coords}")

        # LOGIC: Direct TP ONLY if Alive AND Same Map AND Known Coords
        if not is_dead and current_map == target_map and coords and len(coords) == 3:
            scale = 1.2303125
            # Langsung tulis ke memory
            core.write_coords(coords[0]*scale, coords[1]*scale, coords[2]*scale)
            return True, f"Direct TP to {wp_data['name']}"
            
        # FALLBACK: Chat Link (For Revival, Map Change, or Missing Coords)
        else:
            wp_id = wp_data.get("id")
            if not wp_id: return False, "Invalid WP ID"
            
            if is_dead:
                print(f"[SmartTP] Player is dead (HP: {cur_hp}). Forcing Chat Link to revive.")
            
            # Fallback ke metode Chat Link
            return self.trigger_waypoint_chat(wp_id, chat_x, chat_y)
            
    def get_starting_waypoint_for_map(self, map_id):
        # 1. Explicit starting waypoint
        for wp in data.WAYPOINT_DB:
            if wp.get("map_id") == map_id and wp.get("is_starting"):
                return wp

        # 2. Fallback: first waypoint of map
        for wp in data.WAYPOINT_DB:
            if wp.get("map_id") == map_id:
                return wp

        return None
    
    def set_test_map_target(self):
        # example continent coords (replace with real ones)
        mx, my = 11054.3, 15321.8

        tgt = self.map_target.resolve_from_continent_coords(mx, my)
        if tgt:
            self.target_pos = tgt
            print("[MapTarget] Target set:", tgt)
        else:
            print("[MapTarget] Failed to resolve target")
    
    def teleport_portal_direct(self, portal):
        """
        Direct portal teleport.
        No map checks, no smart logic, no arrival checks.
        """
        try:
            x = float(portal["x"])
            y = float(portal["y"])
            z = float(portal["z"])
        except Exception:
            return False, "Invalid portal data"

        scale = 1.2303125
        core.write_coords(x * scale, y * scale, z * scale)

        self._log(
            "[PortalTP]",
            f"Direct write to ({x:.2f}, {y:.2f}, {z:.2f})"
        )
        return True, "Portal teleported"
    
    def teleport_character_to_mouse(self):
        print("[Logic][Sim] MouseTP triggered.")

        coords = core.read_mouse_3d_position()
        if not coords:
            return

        mx, my, mz = coords

        mount_index = 0
        if core.mumble:
            data = core.mumble.read()
            if data:
                mount_index = data.get("mount_index", 0)

        print("Mount Index:", mount_index)

        current = core.read_coords()
        if not current:
            return

        cx, cy, cz = current

        SKIFF_INDEX = 10

        if mount_index == SKIFF_INDEX:
            safe_y = cy
            print("[MouseTP] Skiff detected — preserving height")
        else:
            safe_y = my + 0.5

        print(f"[MouseTP] Target meters: {mx:.2f}, {safe_y:.2f}, {mz:.2f}")

        scale = 1.2303125
        core.write_coords(
            mx * scale,
            safe_y * scale,
            mz * scale
        )

    
    def load_npcs(self):
        """Reloads NPC data from file."""
        self.npcs = []
        try:
            npc_path = os.path.join(os.path.dirname(__file__), "all_npcs.json")
            if os.path.exists(npc_path):
                with open(npc_path, "r", encoding="utf-8") as f:
                    raw_npcs = json.load(f)
                    count = 0
                    for n in raw_npcs:
                        c = n.get("coord")
                        if c and len(c) >= 2 and c[0] is not None and c[1] is not None:
                            self.npcs.append(n)
                            count += 1
                print(f"[Logic] Loaded {count} valid NPCs.")
                return True
            else:
                print("[Logic] all_npcs.json not found")
                return False
        except Exception as e:
            print(f"[Logic] Error loading NPCs: {e}")
            return False
    # ===============================
    # AUTO TELEPORT LOGIC
    # ===============================
    def set_manual_index(self, index):
        self.current_auto_tp_index = index
    
    def _interact_until_complete(self, timeout=6.0):
        if not self.interact_scan:
            return False

        # Press interact once
        with self.input_lock:
            core.presskey(self.window_title, self.interact_scan, 0.06)

        start = time.time()
        seen_active = False

        while time.time() - start < timeout:
            if self.auto_tp_stop_event.is_set():
                return False

            state = self._read_interact_state()

            # Detect interaction actually started
            if state >= self.interacting_value:
                seen_active = True

            # Interaction finished → SUCCESS
            if seen_active and state < self.interacting_value:
                return True

            time.sleep(0.05)

        return False
        
    def step_tp_manual(self, direction, tp_list):
        """
        direction: +1 (next) or -1 (back)
        Works even when AutoTP is NOT running
        """
        if not tp_list:
            return

        idx = self.current_auto_tp_index or 0
        idx += direction

        # wrap around
        if idx < 0:
            idx = len(tp_list) - 1
        elif idx >= len(tp_list):
            idx = 0

        self.current_auto_tp_index = idx
                
        if self.on_auto_tp_step:
            self.on_auto_tp_step(self.current_auto_tp_index)
        # If AutoTP running → steer loop
        if self.auto_tp_running:
            self.manual_tp_step = direction
            self._log("[AutoTP]", f"Manual STEP {'NEXT' if direction > 0 else 'BACK'}")
            return

        tp = tp_list[idx]

        if tp.get("type") == "portal":
            ok, reason = self.teleport_portal_direct(tp)
        else:
            ok, reason = self.teleport_custom(tp)

        self._log(
            "[ManualTP]",
            f"STEP {'NEXT' if direction > 0 else 'BACK'} idx={idx} ok={ok} reason={reason}"
        )

        # 🔔 NOTIFY UI (move highlight)
        if ok and self.on_auto_tp_step:
            self.on_auto_tp_step(idx)
        
    def _hp_is_dropping(self, cur_hp):
        if self._last_hp is None:
            self._last_hp = cur_hp
            return False

        if cur_hp >= self._last_hp:
            self._last_hp = cur_hp
            return False

        self._last_hp = cur_hp
        return True      
    
    def _wait_for_full_health(self, timeout=60):
        print("[AutoTP] Waiting for HP restoration (100%)...")
        start_wait = time.time()
        
        while time.time() - start_wait < timeout:
            if self.auto_tp_stop_event.is_set(): return False
            
            cur, maxx = self._check_health_status()
            
            if cur is not None and maxx is not None and cur > 0 and maxx > 0:
                pct = (cur / maxx) * 100
                if pct >= 99: 
                    print("[AutoTP] Health fully restored!")
                    print("[AutoTP] Waiting 2s buffer...")
                    time.sleep(2.0)
                    return True
            
            time.sleep(1.0)
        
        print("[AutoTP] Health restore timed out.")
        return False

    def _recover_from_death(self, chat_coords):
        print("[AutoTP] Initiating Death Recovery...")
        
        valid_wps = [w for w in data.WAYPOINT_DB if w.get("map_id") == self.current_map_id]
        if not valid_wps:
            print("[AutoTP] CRITICAL: No Waypoints found for this map. Cannot Auto-Revive.")
            return False

        target_wp = valid_wps[0]
        print(f"[AutoTP] Reviving at Waypoint: {target_wp['name']}")

        cx, cy = chat_coords
        ok, msg = self.trigger_waypoint_chat(target_wp["id"], cx, cy)
        if not ok:
            print(f"[AutoTP] Revive click failed: {msg}")
            return False

        print("[AutoTP] Revive triggered. Waiting for HP restoration...")
        return self._wait_for_full_health(timeout=60)
        
    def start_auto_teleport(self, tp_list, delay=1.0, loop=True, loop_count=None, start_index=0, post_relog_wait=False, repeat_per_tp=1, chat_coords=(214, 1377)):
        # Safety reset
        self._user_stop_requested = False
        self.auto_tp_reverse = bool(getattr(self, "auto_tp_reverse", False))
        self.auto_tp_random = bool(getattr(self, "auto_tp_random", False))
        
        if self.auto_tp_running: return False, "Already running"
        if not tp_list: return False, "List empty"

        # CLEAR FLAGS ON START
        self.flagged_tp_indices.clear()
        self.active_flagged_tp = None
        
        # Track failures for summary
        failed_death_indices = []

        self.auto_tp_stop_event.clear()
        self.auto_tp_running = True
        
        try:
            repeat_per_tp = int(repeat_per_tp)
        except:
            repeat_per_tp = 1
        repeat_per_tp = max(1, repeat_per_tp)
        
        try: start_index = int(start_index)
        except: start_index = 0
        start_index = max(0, min(start_index, len(tp_list) - 1))

        def runner():
            try:
                if self.auto_quickness_enabled:
                    threading.Thread(target=self._run_quickness_loop, daemon=True).start()

                if post_relog_wait:
                    print("[AutoTP] Post-Relog: Waiting 7s for map load...")
                    wait_end = time.time() + 7.0
                    while time.time() < wait_end:
                        if self.auto_tp_stop_event.is_set(): return
                        time.sleep(0.5)

                completed_loops = 0
                total = len(tp_list)
                last_clamp_ts = 0.0

                # MODE SETUP
                if self.auto_tp_random:
                    order = self._build_random_order(total, start_index)
                elif self.auto_tp_reverse:
                    order = list(range(total))
                    order.reverse()
                    if start_index in order:
                        while order[0] != start_index:
                            order.append(order.pop(0))
                else:
                    order = list(range(total))
    
                pos = order.index(start_index) if start_index in order else 0
                
                while not self.auto_tp_stop_event.is_set():
                    if not self.map_ready:
                        time.sleep(1)
                        continue
                    
                    idx = order[pos]
                    tp = tp_list[idx]
                    
                    if tp.get("type") == "portal":
                        self._log("[AutoTP]", f"Skipping portal idx={idx}")
                        pos += 1
                        continue
                                                        
                    # MANUAL STEP OVERRIDE
                    step = self.manual_tp_step
                    self.manual_tp_step = 0
                    if step != 0:
                        pos += step
                        if pos < 0: pos = 0
                        elif pos >= len(order): pos = len(order) - 1
                        idx = order[pos]
                        tp = tp_list[idx]

                    # --- DEAD CHECK (BEFORE TELEPORT) ---
                    cur_hp, _ = self._check_health_status()
                    if cur_hp is not None and cur_hp <= 0:
                        self._log("[AutoTP]", f"Death detected before TP {idx}. Recovering...")
                        failed_death_indices.append(idx)
                        
                        if self._recover_from_death(chat_coords):
                            self._log("[AutoTP]", f"Skipping TP {idx} due to death.")
                            pos += 1 
                            if pos >= total:
                                pos = 0
                                completed_loops += 1
                            continue 
                        else:
                            self._log("[AutoTP]", "Recovery Failed. Stopping.")
                            break
                    # ------------------------------------
                    
                    MAX_RETRY = 1
                    attempt = 0
                    ok = False

                    while attempt < MAX_RETRY and not ok:
                        if self.auto_tp_stop_event.is_set(): return

                        ok, reason = self.teleport_custom(tp)
                        self._log("[AutoTP]", f"TP idx={idx} retry={attempt+1}/{MAX_RETRY} ok={ok} reason={reason}")

                        attempt += 1
                        if not ok: time.sleep(0.15)

                    time.sleep(0.12)

                    last_clamp_ts = self._clamp_to_tp_if_needed(tp, last_clamp_ts)

                    if ok and self.move_fwd_scan:
                        time.sleep(0.03)
                        with self.input_lock:
                            core.presskey(self.window_title, self.move_fwd_scan, 0.02)

                    if not ok:
                        print(f"[AutoTP] TP Failed at index {idx}. Skipping.")
                        pos += 1 
                        if pos >= total:
                            pos = 0
                            completed_loops += 1
                        continue
                   
                    channel_started_flag = False
                    interact_attempted = False
                    teleport_ready = False
                    
                    def mark_channel_started(val=True):
                        nonlocal channel_started_flag
                        channel_started_flag = val

                    def channel_started_cb():
                        return channel_started_flag
                    
                    if not teleport_ready:
                        teleport_ready = self._wait_for_arrival_and_stable(
                            tp,
                            timeout=2.5,
                            arrive_eps=0.6,
                            stable_window=0.5,
                            abort_if_channel_started=channel_started_cb
                        )

                        if not teleport_ready:
                            print(f"[AutoTP] TP {idx} not ready (arrival/stability), retrying")
                            time.sleep(0.2)
                            continue
                    
                    # HP DROP CHECK (DURING ARRIVAL)
                    cur_hp, max_hp = self._check_health_status()
                    if cur_hp and self._hp_is_dropping(cur_hp):
                        self._log("[AutoTP]", f"HP drop detected at idx={idx}, monitoring...")

                        if self._confirm_continuous_hp_drop(2.0):
                            self._log("[AutoTP]", f"HP still dropping. Backward TP")
                            pos = self.teleport_backward_once(tp_list, order, pos)
                            self.flagged_tp_indices.add(idx)
                            self.active_flagged_tp = idx
                            pos += 1   # 🔑 advance forward after fallback
                            continue
                                
                    time.sleep(0.2)
                    self.current_auto_tp_index = idx
                    if self.on_auto_tp_step:
                        self.on_auto_tp_step(idx)

                    try: data.update_last_auto_tp_index(idx)
                    except: pass
    
                    # --- INTERACT BLOCK ---
                    if (
                        teleport_ready
                        and idx not in self.flagged_tp_indices
                        and (self.auto_tp_interact_object or self.auto_tp_interact_vista)
                        and not interact_attempted
                    ):
                        interact_attempted = True
                        det_timeout = max(5.0, delay) 
                        
                        # EXECUTE INTERACTION
                        result = self._do_interact_blocking(
                            channel_started_cb=mark_channel_started, 
                            timeout=det_timeout
                        )
                        
                        # --- 1. HANDLE RETREAT (HP < 30%) ---
                        if result == "RETREAT":
                            self._log("[AutoTP]", f"EMERGENCY RETREAT at idx={idx} (<30% HP).")
                            failed_death_indices.append(idx)
                            
                            # Teleport to Safe Spot (Index 0)
                            if tp_list:
                                self._log("[AutoTP]", "Teleporting to Safe Spot (Index 0)...")
                                self.teleport_custom(tp_list[0])
                                time.sleep(1.0)
                                
                                # Sync Move
                                if self.move_fwd_scan:
                                    with self.input_lock:
                                        core.presskey(self.window_title, self.move_fwd_scan, 0.05)
                                        time.sleep(0.1)

                                # Wait Full HP
                                self._wait_for_full_health()
                                
                                # Skip to Next
                                self._log("[AutoTP]", f"Recovered. Skipping idx={idx}.")
                                pos += 1 
                                if pos >= total:
                                    pos = 0
                                    completed_loops += 1
                                continue # NEXT
                                
                        # --- 2. HANDLE FAILURE / DEATH ---
                        elif result == "COMBAT":
                            self.flagged_tp_indices.add(idx)
                            
                            if cur_hp is not None and cur_hp <= 0:
                                self._log("[AutoTP]", f"Died during interact at {idx}. Recovering...")
                                failed_death_indices.append(idx)
                                
                                if self._recover_from_death(chat_coords):
                                    self._log("[AutoTP]", "Recovery complete. Moving next.")
                                    # Don't add to flagged retry, treat as accident & skip
                                else:
                                    self._log("[AutoTP]", "Recovery Failed.")
                                    break
                            else:
                                # Normal failure
                                self._log("[AutoTP]", f"Interaction FAILED at idx={idx}. Flagging for retry.")
                                self.flagged_tp_indices.add(idx)
                                self.active_flagged_tp = idx
                        
                        last_clamp_ts = self._clamp_to_tp_if_needed(tp, last_clamp_ts)

                        if self.move_fwd_scan:
                            time.sleep(0.05)
                            with self.input_lock:
                                core.presskey(self.window_title, self.move_fwd_scan, 0.02)

                        time.sleep(0.05)
                        last_clamp_ts = self._clamp_to_tp_if_needed(tp, last_clamp_ts)

                    elif teleport_ready and idx in self.flagged_tp_indices:
                        print(f"[AutoTP] Skipping interact at idx={idx} (Flagged Failed)")

                    # DELAY LOOP
                    end_time = time.time() + delay
                    while time.time() < end_time:
                        if self.auto_tp_stop_event.is_set(): break
                        time.sleep(0.05)

                    pos += 1
                    if pos >= total:
                        completed_loops += 1

                        self._log("[AutoTP]", "Finished route.")

                        # =========================
                        # RETRY FLAGGED (POST LOOP)
                        # =========================
                        if self.flagged_tp_indices:
                            self._log(
                                "[AutoTP]",
                                f"Retrying flagged indices after loop: {sorted(self.flagged_tp_indices)}"
                            )

                            for flagged in list(self.flagged_tp_indices):
                                if self._user_stop_requested:
                                    break

                                self._log("[AutoTP]", f"Post-loop retry idx={flagged}")

                                # 1. Go to safe TP
                                self.teleport_custom(tp_list[0])
                                time.sleep(2.0)

                                # 2. Retry target
                                self.teleport_custom(tp_list[flagged])
                                time.sleep(0.4)

                                result = self._do_interact_blocking(timeout=8.0)

                                if result is True:
                                    self._log("[AutoTP]", f"Retry success idx={flagged}")
                                    self.flagged_tp_indices.discard(flagged)
                                else:
                                    all_flagged_resolved = False

                        # =========================
                        # AUTO LOOP / RELOG BARRIER
                        # =========================
                        if self.flagged_tp_indices:
                            self._log(
                                "[AutoTP]",
                                f"Auto-loop & relog PAUSED. Unresolved flagged TPs: {sorted(self.flagged_tp_indices)}"
                            )
                            self.auto_tp_stop_event.set()
                            self.auto_tp_running = False
                            return

                        # =========================
                        # AUTO RELOG (AFTER ALL FLAGGED CLEARED)
                        # =========================
                        if self.auto_relog_enabled:
                            self._log("[AutoTP]", "All flagged retries resolved. Proceeding to relog.")

                            self.auto_relog_loop_enabled = True
                            self.auto_tp_stop_event.set()
                            self.auto_tp_running = False
                            self.relog_game()
                            return

                        # =========================
                        # NORMAL STOP
                        # =========================
                        self.auto_tp_stop_event.set()
                        self.auto_tp_running = False
                        return
                            
            except Exception as e:
                print(f"[AutoTP] Error: {e}")
            finally:
                self.auto_tp_running = False
                
        self._last_auto_tp_args = {
            "tp_list": tp_list, "delay": delay, "loop": loop,
            "loop_count": loop_count, "start_index": start_index,
            "chat_coords": chat_coords
        }
        self.auto_tp_thread = threading.Thread(target=runner, daemon=True)
        self.auto_tp_thread.start()
        self._log("[TPCheck]", "READY (arrival/stability satisfied)")
        return True, "Started"
    
    def teleport_backward_once(self, tp_list, order, pos):
        if not tp_list or not order:
            return pos

        # move backward safely
        pos -= 1
        if pos < 0:
            pos = len(order) - 1

        idx = order[pos]
        tp = tp_list[idx]

        ok, reason = self.teleport_custom(tp)
        self._log("[AutoTP]", f"Backward TP idx={idx} ok={ok} reason={reason}")

        if ok:
            self.current_auto_tp_index = idx

        return pos
        
    def _wait_for_arrival_and_stable(
        self,
        tp,
        timeout=2.5,
        arrive_eps=0.6,
        stable_window=0.5,
        drift_eps=0.02,
        abort_if_channel_started=None
    ):
        self._log(
            "[TPCheck]",
            f"start timeout={timeout}s arrive_eps={arrive_eps} stable_window={stable_window}"
        )
        start = time.time()
        
        # --- FIX: REMOVED SCALING FACTOR ---
        target = (tp["x"], tp["y"], tp["z"])
        
        last = None
        stable_since = None

        # Tolerance fallback for slight geometry mismatches
        LOOSE_TOLERANCE = 200.0 

        while time.time() - start < timeout:
            # 1. External Abort (e.g. Channel started via macro)
            if abort_if_channel_started and abort_if_channel_started():
                self._log("[TPCheck]", "READY (channel started early)")
                return True

            # --- 2. NEW: DRIFT OVERRIDE (Interact Prompt) ---
            # If we are sliding/drifting BUT the interact prompt is visible, 
            # we consider it "arrived" so we can try to press F immediately.
            if (self.auto_tp_interact_object or self.auto_tp_interact_vista):
                state = self._read_interact_state()
                if state >= self.interacting_value:
                    self._log("[TPCheck]", f"READY (Interact prompt detected: {state}). Ignoring drift.")
                    return True
            # ------------------------------------------------

            pos = core.read_coords()
            if not pos:
                time.sleep(0.05)
                continue

            # --- 3. Calculate Distances ---
            dx = pos[0] - target[0]
            dy = pos[1] - target[1]
            dz = pos[2] - target[2]
            
            planar_dist = math.sqrt(dx*dx + dz*dz)
            height_dist = abs(dy)
            
            # --- 4. Check Stability ---
            if last:
                drifting = (
                    abs(pos[0] - last[0]) > drift_eps or
                    abs(pos[1] - last[1]) > drift_eps or
                    abs(pos[2] - last[2]) > drift_eps
                )
            else:
                drifting = True

            if not drifting:
                if stable_since is None:
                    stable_since = time.time()
            else:
                stable_since = None

            is_stable = (stable_since is not None) and (time.time() - stable_since >= stable_window)

            # --- 5. Check Arrival ---
            is_at_exact_spot = (planar_dist <= arrive_eps) and (height_dist <= arrive_eps * 2.0)
            is_close_enough = (planar_dist <= LOOSE_TOLERANCE) and (height_dist <= LOOSE_TOLERANCE)

            # Log periodically
            if int((time.time() - start) * 5) != int((time.time() - start - 0.05) * 5):
                stable_duration = (time.time() - stable_since) if stable_since else 0.0
                self._log(
                    "[TPCheck]",
                    f"pos=({pos[0]:.2f},{pos[1]:.2f},{pos[2]:.2f}) "
                    f"dist(xz)={planar_dist:.2f} dist(y)={height_dist:.2f} "
                    f"drifting={drifting} stable={stable_duration:.2f}"
                )
                
            if planar_dist > self.MAX_TP_DRIFT * 2:
                scale = 1.2303125
                core.write_coords(
                    target[0] * scale,
                    target[1] * scale,
                    target[2] * scale
                )
                stable_since = None
                time.sleep(0.05)
                continue

            # --- 6. Success Conditions ---
            if (is_at_exact_spot or is_close_enough) and is_stable:
                return True

            last = pos
            time.sleep(0.05)
            
        return False

    def stop_auto_teleport(self):
        print("[AutoTP] User requested STOP")

        self._user_stop_requested = True # 🔒 hard stop
        self.auto_relog_loop_enabled = False

        self.auto_tp_stop_event.set()
        self.auto_tp_running = False

    def _run_quickness_loop(self):
        sequence = [0.3, 27.0, 11.0] # Press -> Wait -> Wait
        while self.auto_tp_running and not self.auto_tp_stop_event.is_set():
            if self.skill9_scan:
                with self.input_lock:
                    core.presskey(self.window_title, self.skill9_scan, 0.05)
            for slp in sequence:
                end = time.time() + slp
                while time.time() < end:
                    if not self.auto_tp_running or self.auto_tp_stop_event.is_set(): return
                    time.sleep(0.1)

    def _do_interact_blocking(self, channel_started_cb=None, timeout=6.0):
        if not self.interact_scan:
            return True 

        # --- INTERNAL FUNCTION: SINGLE INTERACT ---
        # This contains the logic for opening ONE chest/node
        def _attempt_interact_once():
            print(f"[AutoTP][Interact] Waiting for prompt (Timeout: {timeout:.1f}s)...")
            stable_hits = 0
            start_wait = time.time()
            initial_prompt_detected = False

            while time.time() - start_wait < 1.5:
                if self.auto_tp_stop_event.is_set(): return False
                cur, _ = self._check_health_status()
                if cur is not None and cur <= 0: return False

                state = self._read_interact_state()
                if state > 0: 
                    stable_hits += 1
                    if stable_hits >= 2: 
                        initial_prompt_detected = True
                        break 
                else:
                    stable_hits = 0
                time.sleep(0.05)

            if initial_prompt_detected:
                print("[AutoTP][Interact] Prompt detected. Pressing F.")
            else:
                print("[AutoTP][Interact] Prompt NOT stable. Forcing interact anyway.")

            # Press Key
            with self.input_lock:
                for _ in range(2):
                    core.presskey(self.window_title, self.interact_scan, 0.04)
                    time.sleep(0.05)

            # Monitor
            print("[AutoTP][Interact] Monitoring state...")
            monitor_start = time.time()
            deadline = monitor_start + timeout
            
            GRACE_PERIOD = 0.8
            FINISH_STABILITY = 0.6
            zero_state_start = None
            
            while time.time() < deadline:
                if self.auto_tp_stop_event.is_set(): return False
                
                state = self._read_interact_state()
                cur_hp, max_hp = self._check_health_status()
                elapsed = time.time() - monitor_start

                # Dead/Retreat Checks
                if cur_hp is not None:
                    if cur_hp <= 0: return False
                    if max_hp and max_hp > 0 and (cur_hp / max_hp) < 0.30:
                        print(f"[AutoTP] CRITICAL HP. Triggering Retreat!")
                        return "RETREAT"

                # Stability Check Logic
                if state == 0:
                    if elapsed < GRACE_PERIOD:
                        zero_state_start = None
                        time.sleep(0.05)
                        continue

                    if zero_state_start is None:
                        zero_state_start = time.time()
                    
                    if (time.time() - zero_state_start) >= FINISH_STABILITY:
                        print(f"[AutoTP][Interact] Success (State 0 stable)")
                        return True
                else:
                    zero_state_start = None
                    if channel_started_cb: channel_started_cb(True)

                time.sleep(0.05)

            # Timeout Handler
            if state == 0:
                print("[AutoTP] Interaction timeout (State 0). Assuming complete.")
                return True
            else:
                print(f"[AutoTP] Interaction FAILED (Stuck at state {state}).")
                return False

        # --- MAIN LOOP: MULTI-LOOT LOGIC ---
        # Try up to 5 times in the same spot (handles stacked chests)
        total_success = False
        
        for i in range(5):
            # 1. Pre-Check (For 2nd chest onwards)
            if i > 0:
                # Wait a bit for server to spawn next prompt
                time.sleep(0.8) 
                
                # If no prompt appears, we are done
                if self._read_interact_state() == 0:
                    print(f"[AutoTP] No more prompts detected. Done.")
                    return True 
                
                print(f"[AutoTP] Another interact prompt detected! Starting loop {i+1}...")

            # 2. Run Single Interaction
            result = _attempt_interact_once()

            # 3. Handle Result
            if result == "RETREAT": 
                return "RETREAT"
            
            if result is False:
                # If we failed on the very first try, return False (Failed).
                # If we succeeded once but failed the second one, return True (Partial Success).
                return True if total_success else False
            
            if result is True:
                total_success = True
                # Continue loop to check for next chest
                continue

        return True
    
    def _check_health_status(self):
        try:
            ptr_off = self.offsets.get("player_health_base_mem")
            if not ptr_off: return None, None
            ptr = self.pm.read_ulonglong(self.pm.base_address + ptr_off)
            if not ptr: return None, None
            cur = self.pm.read_float(ptr + self.offset_health_current[0])
            maxx = self.pm.read_float(ptr + self.offset_health_max[0])
            return cur, maxx
        except: return None, None

    def _read_interact_state(self):
        if not self.pm or not self.interacting_addr:
            return 0
        try:
            return self.pm.read_int(self.base_address + self.interacting_addr)
        except:
            return 0

    def _visual_watchdog(self):
        # Mem-bypass rendering memicu assertion !m_head di TagList.h.
        # Seluruh operasi write visual dimatikan demi stabilitas arsitektur.
        was_connected = False
        while True:
            is_connected = bool(core.pm)
            if is_connected and not was_connected:
                # self.toggle_clarity(self._clarity_enabled)
                # for k, v in list(self._esp_enabled.items()):
                #     self.toggle_esp(k, v)
                print("[Logic] Visual memory patching dinonaktifkan secara paksa untuk menghindari crash TagList.")
            was_connected = is_connected
            time.sleep(1.0)

    def _write_visual(self, off_key, val_key, type="ulong"):
        try:
            pm_instance = core.pm 
            if not pm_instance: 
                return
            
            raw_off = self.offsets.get(off_key)
            raw_val = self.offsets.get(val_key)
            
            # Validasi jika key tidak ada di gw2x_data.py
            if raw_off is None:
                print(f"[LOGIC ERROR] Offset '{off_key}' tidak ditemukan di dictionary!")
                return
            if raw_val is None:
                print(f"[LOGIC ERROR] Value '{val_key}' tidak ditemukan di dictionary!")
                return
            
            # Parsing presisi: Konversi string hex atau string angka menjadi integer murni
            def parse_hex_or_int(v):
                if isinstance(v, str):
                    v = v.strip()
                    return int(v, 16) if v.lower().startswith("0x") else int(v)
                return int(v)
                
            off = parse_hex_or_int(raw_off)
            val = parse_hex_or_int(raw_val)
            
            addr = pm_instance.base_address + off
            
            # Eksekusi write berdasarkan tipe
            if type == "ushort": 
                pm_instance.write_ushort(addr, val)
            elif type == "float": 
                pm_instance.write_float(addr, float(val))
            else: 
                pm_instance.write_ulonglong(addr, val)
                
        except Exception as e: 
            # Membuang 'pass' agar error tidak menjadi silent fail
            print(f"[MEMORY ERROR] Gagal menulis {val_key} ke {off_key} ({type}): {e}")

    def toggle_clarity(self, state):
        self._clarity_enabled = bool(state)
        # Writes Mod ONCE when True, Ori ONCE when False
        if state:
            self._write_visual("fgaddr", "nofogmod")
            self._write_visual("fg2addr", "clearsurfacemod")
        else:
            self._write_visual("fgaddr", "nofogori")
            self._write_visual("fg2addr", "clearsurfaceori")

    def toggle_esp(self, key, state):
        self._esp_enabled[key] = bool(state)
        if state:
            if key == "esp_player": 
                self._write_visual("name", "nametagmod")
                self._write_visual("brightness", "espbrightmod")
                self._write_visual("viewdist", "viewdistancemod") # <- FIX: Crucial for ESP
            elif key == "esp_npc":
                self._write_visual("objname", "objectespmod", "ushort")
                self._write_visual("objhealth", "objecthpmod", "ushort")
                self._write_visual("viewdist", "viewdistancemod") # <- FIX: Crucial for ESP
            elif key == "esp_path": 
                self._write_visual("mprdr", "mapradarmod")
            elif key == "esp_health":
                self._write_visual("health1", "hpbar1mod", "ushort")
                self._write_visual("health2", "hpbar2mod", "ushort")
        else:
            if key == "esp_player": 
                self._write_visual("name", "nametagori")
                self._write_visual("brightness", "espbrightori")
                # Only revert view distance if Object ESP is also off
                if not self._esp_enabled.get("esp_npc"):
                    self._write_visual("viewdist", "viewdistanceori")
            elif key == "esp_npc":
                self._write_visual("objname", "objectespori", "ushort")
                self._write_visual("objhealth", "objecthpori", "ushort")
                # Only revert view distance if Player ESP is also off
                if not self._esp_enabled.get("esp_player"):
                    self._write_visual("viewdist", "viewdistanceori")
            elif key == "esp_path": 
                self._write_visual("mprdr", "mapradarori")
            elif key == "esp_health":
                self._write_visual("health1", "hpbar1ori", "ushort")
                self._write_visual("health2", "hpbar2ori", "ushort")

    def save_slot(self, idx):
        pos = core.read_coords()
        if pos: data.save_slot(idx, pos)
    
    def load_slot(self, idx):
        p = data.POSITION_SLOTS[idx]
        if p: core.write_coords(p[0]*1.2303125, p[1]*1.2303125, p[2]*1.2303125)
