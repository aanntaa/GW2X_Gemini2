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

        # Each run has independent controls so a restarted macro cannot clear
        # an older worker's stop signal.
        self._controls = {"A": None, "B": None}
        self._state_lock = threading.RLock()

    # -------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------

    def set_skill_key_hotkey(self, obj):
        self.hotkeys_obj = obj

    def set_boon_state(self, key, quickness=True, alacrity=True):
        """Store plain booleans; worker threads must not access Tk variables."""
        if key not in self.macros:
            return False
        with self._state_lock:
            self.macros[key]["quickness"] = bool(quickness)
            self.macros[key]["alacrity"] = bool(alacrity)
        return True

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
        if key not in self.macros:
            print(f"[Macro] Unknown slot: {key}")
            return False

        if self.running[key]:
            print(f"[Macro] Stop slot {key} before loading another file.")
            return False

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
                            delay_ms = max(0.0, float(parts[1]))
                            actions.append((skill_name, delay_ms))
                        except ValueError:
                            continue
            
            if not actions:
                print(f"[Macro] No valid actions found in: {file_path}")
                return False

            # A marker after the final action otherwise creates a busy loop.
            if loop_idx >= len(actions):
                loop_idx = 0

            with self._state_lock:
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
        if key not in self.macros:
            return False
        with self._state_lock:
            data = list(self.macros[key]["actions"])
            loop_index = self.macros[key]["loop_index"]
        if not data: return False
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                for i, (name, delay) in enumerate(data):
                    # Reconstruct loop tag if needed (simplified)
                    if i == loop_index and i != 0:
                        f.write(f"{name} {int(delay)} #Loop here\n")
                    else:
                        f.write(f"{name} {int(delay)}\n")
            return True
        except: return False

    # -------------------------------------------------
    # EXECUTION CONTROL
    # -------------------------------------------------

    def start(self, key):
        if key not in self.macros:
            return False

        with self._state_lock:
            if not self.macros[key]["actions"]:
                print(f"[Macro] Cannot start {key}: No actions loaded.")
                return False

            old_thread = self.threads.get(key)
            if old_thread and old_thread.is_alive():
                return False

            stop_event = threading.Event()
            resume_event = threading.Event()
            resume_event.set()
            actions = tuple(self.macros[key]["actions"])
            loop_point = int(self.macros[key].get("loop_index", 0))
            if not 0 <= loop_point < len(actions):
                loop_point = 0

            self._controls[key] = (stop_event, resume_event)
            self.running[key] = True
            self.paused[key] = False
            thread = threading.Thread(
                target=self._runner,
                args=(key, stop_event, resume_event, actions, loop_point),
                name=f"GW2X-Combat-{key}",
                daemon=True,
            )
            self.threads[key] = thread

        thread.start()
        return True

    def stop(self, key):
        if key not in self.macros:
            return False
        with self._state_lock:
            control = self._controls.get(key)
            self.running[key] = False
            self.paused[key] = False
            if control:
                stop_event, resume_event = control
                stop_event.set()
                resume_event.set()
        return True

    def pause(self, key):
        if key not in self.macros or not self.running[key]:
            return False
        with self._state_lock:
            control = self._controls.get(key)
            self.paused[key] = True
            if control:
                control[1].clear()
        return True

    def resume(self, key):
        if key not in self.macros or not self.running[key]:
            return False
        with self._state_lock:
            control = self._controls.get(key)
            self.paused[key] = False
            if control:
                control[1].set()
        return True

    # -------------------------------------------------
    # THE LOGIC RUNNER
    # -------------------------------------------------

    def _get_hex_code(self, skill_name):
        if not self.hotkeys_obj:
            return None
        val = getattr(self.hotkeys_obj, skill_name, None)
        if val is None or isinstance(val, bool):
            return None
        try:
            code = val if isinstance(val, int) else int(str(val).strip(), 16)
        except (TypeError, ValueError):
            return None
        return code if 0 < code <= 0xFF else None

    def _runner(self, key, stop_event, resume_event, actions, loop_point):
        print(f"[Macro {key}] Engine Started.")
        current_idx = 0
        consecutive_failures = 0

        try:
            while not stop_event.is_set():
                while not resume_event.wait(0.1):
                    if stop_event.is_set():
                        return
                if stop_event.is_set():
                    break

                if current_idx >= len(actions):
                    current_idx = loop_point

                skill_name, base_delay_ms = actions[current_idx]

                with self._state_lock:
                    macro_data = self.macros[key]
                    quickness = bool(macro_data.get("quickness", True))
                    alacrity = bool(macro_data.get("alacrity", True))

                scale = 1.0
                if not quickness:
                    scale *= 1.5
                if not alacrity:
                    scale *= 1.25

                hex_code = self._get_hex_code(skill_name)
                if hex_code is None:
                    print(f"[Macro {key}] No DIK scan code configured for {skill_name}")
                    consecutive_failures += 1
                else:
                    try:
                        delivered = self.presskey(self.window_title, hex_code)
                        if delivered is False:
                            print(
                                f"[Macro {key}] Background key tap failed: "
                                f"{skill_name} (0x{hex_code:02X})"
                            )
                            consecutive_failures += 1
                        else:
                            consecutive_failures = 0
                    except Exception as exc:
                        print(f"[Macro {key}] Input error for {skill_name}: {exc}")
                        consecutive_failures += 1

                if consecutive_failures >= 3:
                    print(f"[Macro {key}] Stopped after 3 consecutive input failures.")
                    break

                current_idx += 1
                delay_sec = max(0.0, base_delay_ms * scale / 1000.0)
                if stop_event.wait(delay_sec):
                    break
        finally:
            with self._state_lock:
                if self._controls.get(key) == (stop_event, resume_event):
                    self.running[key] = False
                    self.paused[key] = False
                    self._controls[key] = None
            print(f"[Macro {key}] Engine Stopped.")
