import time
import threading
import os

class CombatMacroEngine:
    def __init__(self, presskey_func, keydown_func, keyup_func, window_title="Guild Wars 2"):
        # UI Bridges
        self.presskey = presskey_func
        self._raw_key_down = keydown_func
        self._raw_key_up = keyup_func
        self.window_title = window_title

        # Configuration Object (Holds SKILL_1="02", etc.)
        self.hotkeys_obj = None

        # --- State Management ---
        # Structure: "A": {"actions": [(name, delay), ...], "loop_index": 0}
        self.macros = {
            "A": {"actions": [], "loop_index": 0}, 
            "B": {"actions": [], "loop_index": 0}
        }       
        self.running = {"A": False, "B": False} 
        self.paused = {"A": False, "B": False}  
        self.threads = {"A": None, "B": None}   

    # -------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------

    def set_skill_key_hotkey(self, obj):
        self.hotkeys_obj = obj

    def initialize_mappings(self, config_path, map_path):
        pass

    # -------------------------------------------------
    # LOADING LOGIC (With Loop Detection)
    # -------------------------------------------------

    def load_macro_simple(self, key, file_path):
        """
        Parses a file. Looks for '#Loop here' to set the reset point.
        Uses .update() to preserve UI variable bindings (Quickness/Alacrity).
        """
        if not os.path.exists(file_path):
            print(f"[Macro] File not found: {file_path}")
            return False

        actions = []
        loop_idx = 0 # Default to 0 (start of file)
        opener_text = None
        reading_opener = False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    original_line = line.strip()
                    if not original_line:
                        continue

                    # Detect Opener Section
                    if original_line.startswith("#Opener"):
                        reading_opener = True
                        continue

                    # Detect Rotation Section
                    if original_line.startswith("#Rotation"):
                        reading_opener = False
                        continue

                    # If we are inside Opener block, capture text
                    if reading_opener and not original_line.startswith("#"):
                        opener_text = original_line.strip()
                        continue

                    # Skip other comments (except Loop)
                    if original_line.startswith("#") and "#Loop here" not in original_line:
                        continue
                    
                    # 1. Check for Loop Tag BEFORE cleaning the line
                    if "#Loop here" in original_line:
                        loop_idx = len(actions) # The next item added will be the loop point
                    
                    # 2. Clean comments (remove anything after #)
                    clean_line = original_line.split("#")[0].strip()
                    if not clean_line: continue

                    # 3. Parse SKILL DELAY
                    parts = clean_line.split()
                    if len(parts) >= 2:
                        skill_name = parts[0]
                        try:
                            delay_ms = float(parts[1])
                            actions.append((skill_name, delay_ms))
                        except ValueError:
                            continue
            
            # --- PERBAIKAN DI SINI ---
            # Gunakan .update() agar referensi Quickness/Alacrity dari UI tidak hilang
            if key not in self.macros:
                self.macros[key] = {}
                
            self.macros[key].update({
                "actions": actions,
                "loop_index": loop_idx,
                "opener_text": opener_text
            })
            
            print(f"[Macro] Loaded Slot {key}: {len(actions)} actions. Loop Point at index: {loop_idx}")
            return True

        except Exception as e:
            print(f"[Macro] Error loading file: {e}")
            return False
            
    def save_rotation_to_file(self, key, save_path):
        data = self.macros[key]["actions"]
        if not data: return False
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                for i, (name, delay) in enumerate(data):
                    # Reconstruct loop tag if needed (simplified)
                    if i == self.macros[key]["loop_index"] and i != 0:
                        f.write(f"{name} {int(delay)} #Loop here\n")
                    else:
                        f.write(f"{name} {int(delay)}\n")
            return True
        except: return False

    # -------------------------------------------------
    # EXECUTION CONTROL
    # -------------------------------------------------

    def start(self, key):
        if not self.macros[key]["actions"]:
            print(f"[Macro] Cannot start {key}: No actions loaded.")
            return

        if self.running[key]: return 

        self.running[key] = True
        self.paused[key] = False
        
        self.threads[key] = threading.Thread(target=self._runner, args=(key,), daemon=True)
        self.threads[key].start()

    def stop(self, key):
        self.running[key] = False
        self.paused[key] = False

    def pause(self, key):
        self.paused[key] = True

    def resume(self, key):
        self.paused[key] = False

    # -------------------------------------------------
    # THE LOGIC RUNNER
    # -------------------------------------------------

    def _get_hex_code(self, skill_name):
        if not self.hotkeys_obj: return None
        val = getattr(self.hotkeys_obj, skill_name, None)
        if val:
            try:
                return int(val, 16)
            except ValueError:
                return None
        return None

    def _runner(self, key):
        print(f"[Macro {key}] Engine Started.")
        
        macro_data = self.macros[key]
        actions = macro_data["actions"]
        loop_point = macro_data["loop_index"]
        
        current_idx = 0
        
        while self.running[key]:
            # --- 1. PAUSE CHECK ---
            while self.paused[key]:
                if not self.running[key]:
                    return
                time.sleep(0.1)

            if not self.running[key]:
                break

            # --- 2. LOOP CHECK ---
            if current_idx >= len(actions):
                print(f"[Macro {key}] Looping back to index {loop_point}")
                current_idx = loop_point
                continue

            skill_name, base_delay_ms = actions[current_idx]

            # ======================================================
            # BOON SCALING LOGIC
            # ======================================================
            scale = 1.0

            quick_var = macro_data.get("quickness")
            alac_var = macro_data.get("alacrity")

            # If Quickness is OFF → casting is 33% slower (x1.5 time)
            if quick_var and not quick_var.get():
                scale *= 1.5

            # If Alacrity is OFF → cooldown 25% slower (x1.25 time)
            if alac_var and not alac_var.get():
                scale *= 1.25

            delay_ms = base_delay_ms * scale
            # ======================================================

            # --- 3. PRESS KEY ---
            hex_code = self._get_hex_code(skill_name)
            if hex_code is not None:
                self.presskey(self.window_title, hex_code)

            # --- 4. HANDLE DELAY ---
            sleep_sec = delay_ms / 1000.0
            end_time = time.time() + sleep_sec
            
            while time.time() < end_time:
                if not self.running[key]:
                    break
                time.sleep(0.01)

            current_idx += 1

        print(f"[Macro {key}] Engine Stopped.")
