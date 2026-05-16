import math
import gw2x_core as core
import gw2x_data as data
import gw2x_memory
import tkinter as tk
import ctypes
from ctypes import wintypes

class MapTargetResolver:
    def __init__(self):
        self.last_target = None
        self.mem = gw2x_memory.GW2Memory()

    def get_current_map_id(self):
        mid = core.read_map_id_memory()
        if mid == 0 and core.mumble:
            d = core.mumble.read()
            if d: mid = d.get("map_id", 0)
        return mid

    def get_smart_height(self, map_id, target_x_meter, target_z_meter, current_y_meter):
        import gw2x_data as data
        
        if not data.ALL_MAP_MARKERS:
            return current_y_meter + 50.0 
            
        SEARCH_RADIUS = 800.0   
        CONFLICT_RADIUS = 120.0 

        candidates = []
        for m in data.ALL_MAP_MARKERS:
            if m.get("map_id") != map_id: 
                continue

            c = m.get("coord")
            if not c or len(c) < 3: 
                continue
             
            dx = c[0] - target_x_meter
            dz = c[2] - target_z_meter
            dist = math.hypot(dx, dz)

            if dist <= SEARCH_RADIUS:
                candidates.append({"marker": m, "dist": dist})

        if not candidates:
            return current_y_meter + 50.0

        candidates.sort(key=lambda x: x["dist"])
        close_markers = [cand for cand in candidates if cand["dist"] <= CONFLICT_RADIUS]
        selected_candidate = candidates[0] 

        if len(close_markers) > 1:
            user_choice = self._prompt_user_selection(close_markers, current_y_meter)
            if user_choice:
                selected_candidate = user_choice

        c_exact = selected_candidate["marker"]["coord"]
        target_y = c_exact[1] + 0.5
        
        return target_y

    def get_entity_height_only(self, target_x_meter, target_z_meter):
        """Memindai entitas lokal (NPC > Obj > Player) secara absolut pasca-hover."""
        import gw2x_core as core
        import math
        
        if not core.shared_entities:
            return None
            
        live_entities = core.shared_entities.read_entities()
        if not live_entities:
            return None
            
        ENTITY_SEARCH_RADIUS = 3000.0  # Batas maksimum render engine GW2
        
        candidates_npc = []
        candidates_obj = []
        candidates_player = []
        
        for ent in live_entities:
            dx = ent["x"] - target_x_meter
            dz = ent["z"] - target_z_meter
            dist = math.hypot(dx, dz)
            
            if dist <= ENTITY_SEARCH_RADIUS:
                ent_type = ent.get("type", -1)
                if ent_type == 1:
                    candidates_npc.append({"entity": ent, "dist": dist})
                elif ent_type in (2, 3, 4):
                    candidates_obj.append({"entity": ent, "dist": dist})
                elif ent_type == 0:
                    candidates_player.append({"entity": ent, "dist": dist})
                    
        best_entity_candidate = None
        target_type_str = ""
        
        # Resolusi Hierarki Mutlak
        if candidates_npc:
            candidates_npc.sort(key=lambda x: x["dist"])
            best_entity_candidate = candidates_npc[0]
            target_type_str = "NPC"
        elif candidates_obj:
            candidates_obj.sort(key=lambda x: x["dist"])
            best_entity_candidate = candidates_obj[0]
            target_type_str = "OBJECT"
        elif candidates_player:
            candidates_player.sort(key=lambda x: x["dist"])
            best_entity_candidate = candidates_player[0]
            target_type_str = "PLAYER"
            
        if best_entity_candidate:
            ent = best_entity_candidate["entity"]
            m_name = ent.get("real_name", "Unknown Entity")
            print(f"[HoverProbe] Locked onto [{target_type_str}] {m_name} at distance {best_entity_candidate['dist']:.1f}m")
            return ent["y"] + 0.5 # +0.5m agar tidak mendarat di dalam hitbox
            
        return None
            
    def _prompt_user_selection(self, candidates, current_y_meter):
        """Membuat temporary Tkinter window untuk memilih target snap."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw() 
        
        choice = [None] 
        
        dlg = tk.Toplevel(root)
        dlg.title("Multiple Targets Detected")
        dlg.geometry("480x300")
        dlg.configure(bg="#121212")
        dlg.attributes("-topmost", True)
        
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() // 2) - (480 // 2)
        y = (dlg.winfo_screenheight() // 2) - (300 // 2)
        dlg.geometry(f"+{x}+{y}")

        tk.Label(dlg, text="Select target to snap height:", bg="#121212", fg="#00ff00", font=("Segoe UI", 10, "bold")).pack(pady=10)

        def on_select(idx):
            choice[0] = candidates[idx]
            dlg.destroy()
            root.destroy()

        def on_cancel():
            choice[0] = None
            dlg.destroy()
            root.destroy()

        dlg.protocol("WM_DELETE_WINDOW", on_cancel)

        for i, item in enumerate(candidates[:5]):
            m = item["marker"]
            m_type = str(m.get("type", "???")).upper()
            m_name = m.get("name", "Unknown")
            coords = m.get("coord", [0, 0, 0])
            
            # Kalkulasi komparasi elevasi untuk UI
            t_y = coords[1] + 0.5
            d_y = t_y - current_y_meter
            direction = "UP" if d_y >= 0 else "DOWN"
            
            btn_text = f"[{m_type}] {m_name} | Dist: {item['dist']:.1f}m\nXYZ: ({coords[0]:.1f}, {coords[1]:.1f}, {coords[2]:.1f}) | {direction} {abs(d_y):.1f}m"
            
            tk.Button(
                dlg, text=btn_text, anchor="w", justify="left",
                bg="#2a2a2a", fg="white", relief="flat", font=("Consolas", 9),
                command=lambda idx=i: on_select(idx)
            ).pack(fill=tk.X, padx=10, pady=2)

        tk.Button(dlg, text="Cancel (Use Absolute Nearest)", command=on_cancel, bg="#552222", fg="white", relief="flat").pack(pady=10)

        dlg.wait_window()
        return choice[0]

    def calculate_mouse_teleport(self, screen_x, screen_y):
        import gw2x_data as data
        import math
        import ctypes

        if not core.mumble:
            return None, "MumbleLink not available"
        mdata = core.mumble.read()
        if not mdata or not mdata.get("is_map_open"):
            return None, "Map is not open"

        map_id = mdata.get("map_id", 0)
        map_scale = mdata.get("map_scale", 1.0)
        map_center_x = mdata["map_center_x"]
        map_center_y = mdata["map_center_y"]

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Guild Wars 2")
        if not hwnd:
            return None, "Game Window not found"

        # --- DETEKSI TOMBOL (DIPERLUAS UNTUK MENGHINDARI HOTKEY BLOCK) ---
        # 0x12 = ALT (Sky), 0x11 = CTRL (Ground), 0x10 = SHIFT (Fallback Sky)
        is_alt_pressed = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0   
        is_ctrl_pressed = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0  
        is_shift_pressed = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0 

        rect = ctypes.wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        origin = ctypes.wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(origin))

        cx = origin.x + ((rect.right - rect.left) / 2)
        cy = origin.y + ((rect.bottom - rect.top) / 2)

        try:
            dpi_scale = user32.GetDpiForWindow(hwnd) / 96.0
        except:
            dpi_scale = 1.0

        units_per_px = map_scale / dpi_scale
        target_cont_x = map_center_x + ((screen_x - cx) * units_per_px)
        target_cont_y = map_center_y + ((screen_y - cy) * units_per_px)

        world = core.continent_to_game_coords(target_cont_x, target_cont_y, map_id)
        if not world:
            return None, "Map conversion failed"

        target_x, _, target_z = world

        # --- RADIUS DIPERBESAR AGAR KLIK MAP LEBIH TOLERAN ---
        HEIGHT_SEARCH_RADIUS = 3000.0  
        candidates = []

        # 1. Scan Live Entities & Objects
        if core.shared_entities:
            live_entities = core.shared_entities.read_entities()

            for ent in live_entities:
                ent_type = ent.get("type", -1)

                # Skip PLAYER entity (type 0)
                if ent_type == 0:
                    continue

                dx = ent["x"] - target_x
                dz = ent["z"] - target_z
                dist = math.hypot(dx, dz)

                if dist <= HEIGHT_SEARCH_RADIUS:
                    candidates.append({
                        "y": ent["y"] + 0.5,
                        "dist": dist,
                        "name": f"[{ent_type}] {ent.get('real_name', 'Unknown')}"
                    })
        # 2. Pindai Static Markers
        if hasattr(data, 'ALL_MAP_MARKERS') and data.ALL_MAP_MARKERS:
            for m in data.ALL_MAP_MARKERS:
                if m.get("map_id") != map_id: continue
                c = m.get("coord")
                if not c or len(c) < 3: continue
                
                dx = c[0] - target_x
                dz = c[2] - target_z
                dist = math.hypot(dx, dz)
                
                if dist <= HEIGHT_SEARCH_RADIUS:
                    m_type = str(m.get("type", "marker")).upper()
                    candidates.append({
                        "y": c[1] + 0.5,
                        "dist": dist,
                        "name": f"[{m_type}] {m.get('name', 'Unknown')}"
                    })

        # --- FASE RESOLUSI TINGGI Y ---
        if candidates:
            if is_alt_pressed or is_shift_pressed:
                best_cand = max(candidates, key=lambda c: c["y"])
                pref_str = "SKY/HIGHEST (ALT/SHIFT)"
            elif is_ctrl_pressed:
                best_cand = min(candidates, key=lambda c: c["y"])
                pref_str = "GROUND/LOWEST (CTRL)"
            else:
                # 1. Limit search to a 300m radius of the clicked map coordinates
                local_candidates = [c for c in candidates if c["dist"] <= 150.0]
                
                if local_candidates:
                    # 2. Find the absolute closest horizontal (2D) distance to the click
                    min_dist = min(local_candidates, key=lambda c: c["dist"])["dist"]
                    
                    # 3. Group objects only in that exact vertical spot 
                    # (using a tight 10m tolerance from the closest object)
                    vertical_stack = [c for c in local_candidates if c["dist"] <= min_dist + 10.0]
                    
                    # 4. Snap to the lowest Y *only* within that tight stack to ignore floating objects
                    best_cand = min(vertical_stack, key=lambda c: c["y"])
                    pref_str = "NEAREST 2D (GROUNDED STACK)"
                else:
                    # Fallback if the clicked area is completely barren within 300m
                    best_cand = min(candidates, key=lambda c: c["dist"])
                    pref_str = "NEAREST 2D (FALLBACK)"

            snapped_y = best_cand["y"]
            target_name = best_cand["name"]
            
            print(f"\n[MapTarget] --- VERTICAL SNAP TRIGGERED ---")
            print(f"[MapTarget] Mode     : {pref_str}")
            print(f"[MapTarget] Target   : {target_name} at Y: {snapped_y:.1f}")
            print(f"[MapTarget] Coords   : X:{target_x:.1f} | Z:{target_z:.1f}")
            print(f"[MapTarget] Radius   : Checked within {HEIGHT_SEARCH_RADIUS}m")
            print(f"[MapTarget] -------------------------------\n")
            
            self.last_target = (target_x, snapped_y, target_z)
            return (target_x, snapped_y, target_z), "SNAP_SUCCESS"