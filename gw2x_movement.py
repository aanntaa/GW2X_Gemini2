import threading
import ctypes
import time
import tkinter as tk
from tkinter import ttk
import gw2x_core as core
import gw2x_logic

# ===============================
# OFFSETS (Extracted & Fixed)
# ===============================
# BASE_CORE_OFFSET removed — use core.base_core_address directly (loaded from remote)

# Pointer Chains
OFFSET_SPEED_1 = [152, 56, 80, 696]
OFFSET_SPEED_2 = [152, 56, 80, 692]
OFFSET_SPEED_3 = [152, 56, 80, 688]
OFFSET_GLIDER_DOWNRATE = [152, 56, 80, 732] 
OFFSET_WALLCLIMB = [152, 56, 80, 668]
GROUND_OFFSET_MEM = [152, 80, 256, 280]

# Speed Conversion
GW2_SPEED_DIVISOR = 32.0
DEFAULT_BASE_SPEED_US = 294.0  # Standard out-of-combat speed in u/s

stop_airwalk_slider = threading.Event()

class MovementModule:
    def __init__(self, ui, logic):
        self.ui = ui
        self.logic = logic
        self.pm = logic.pm
        self.DEBUG = True

        # --- State Flags ---
        self.is_walk_active = True
        self.proglider_active = False
        self.wallclimb_active = False

        # --- Threads ---
        self.walk_thread = None
        
        # --- UI Variables ---
        self.var_speed_active = None 
        self.var_speed_val = None    
        self.var_pro_glider = None   
        self._speed_pause_until = 0

        # --- Griffon Variables ---
        self._griffon_running = False
        self._griffon_addr = None
        self._resolve_griffon_patch_point()
        self._griffon_hotkey = {"mods": [0x12], "key": 0x34, "text": "Alt+4"}
        threading.Thread(target=self._start_griffon_hotkey_listener, daemon=True).start()

        # --- Skyscale Variables ---
        self._skyscale_addr = None
        self._skyscale_active = False
        threading.Thread(target=self._skyscale_loop, daemon=True).start()

        # --- Mount Stamina Variables ---
        self._stamina_addr = None

        # --- Pro Glider Hotkey ---
        self._proglider_hotkey = {"key": 0x10, "text": "SHIFT"}  # default SHIFT
        threading.Thread(target=self._start_proglider_hotkey_listener, daemon=True).start()

        # --- Mount Energy ---
        self._mount_energy_active = True
        threading.Thread(target=self._mount_energy_loop, daemon=True).start()

        # --- Auto-Enable Skyscale Wall ---
        def auto_enable_skyscale():
            while not core.pm:
                time.sleep(1)
            time.sleep(1)
            try: self.toggle_skyscale(True)
            except: pass
        threading.Thread(target=auto_enable_skyscale, daemon=True).start()
        threading.Thread(target=self._zoom_loop, daemon=True).start()

        self.BTN_NORMAL = "#2b2b2b"
        self.BTN_ACTIVE = "#3a7bd5"
        self.BTN_DIM    = "#1f1f1f"            


    def _dbg(self, msg):
        if getattr(self, "DEBUG", False):
            print(f"[MovementDBG] {msg}")

    def start_background_threads(self):
        threading.Thread(target=self._start_proglider_hotkey_listener, daemon=True).start()
        threading.Thread(target=self._start_griffon_hotkey_listener, daemon=True).start()
        threading.Thread(target=self._mount_energy_loop, daemon=True).start()

    # ==========================
    # Helper: Pointer Resolution
    # ==========================
    def get_pointer_address(self, base_static_offset, offsets):
        try:
            root_ptr = self.pm.base_address + base_static_offset
            addr = self.pm.read_longlong(root_ptr)

            if addr == 0 or addr == 0xFFFFFFFFFFFFFFFF:
                return 0

            for offset in offsets[:-1]:
                addr = self.pm.read_longlong(addr + offset)

                if addr == 0 or addr == 0xFFFFFFFFFFFFFFFF:
                    return 0

            final = addr + offsets[-1]

            # Valid 64-bit userspace range: 64KB to 128TB
            if 0x10000 < final < 0x0000800000000000:
                return final

            return 0

        except:
            return 0

    # ==========================
    # Logic: Walk Speed
    # ==========================
    def _walk_speed_loop(self):
        self._dbg("Walk speed loop started (Smooth Version)")
        self._dbg(f"base_core_address = {hex(core.base_core_address) if core.base_core_address else 'NOT SET'}")

        self._last_y = None

        while self.is_walk_active:
            try:
                # Pause during pro-glider boost window
                if time.time() < getattr(self, "_speed_pause_until", 0):
                    time.sleep(0.01)
                    continue

                # Resolve pointers once per loop
                speed_ptrs = []
                for offset in [OFFSET_SPEED_1, OFFSET_SPEED_2, OFFSET_SPEED_3]:
                    addr = self.get_pointer_address(core.base_core_address, offset)
                    if addr:
                        speed_ptrs.append(addr)

                glider_ptr = self.get_pointer_address(core.base_core_address, OFFSET_GLIDER_DOWNRATE)

                # ---- 1️⃣ Detect Gliding ----
                gliding = False
                if glider_ptr:
                    try:
                        g_val = self.pm.read_float(glider_ptr)
                        if -4.5 <= g_val <= -2.5:
                            gliding = True
                    except:
                        pass

                # ---- 2️⃣ Detect Airborne (Smoother & Faster Check) ----
                airborne = False
                pos = core.read_coords()
                
                if pos:
                    current_y = pos[1] # Axis vertikal
                    if self._last_y is not None:
                        # Toleransi dinaikkan dari 0.005 ke 0.06
                        # Ini memungkinkan karakter lari di tanjakan/turunan curam tanpa memicu "airborne" palsu
                        if abs(current_y - self._last_y) > 0.06:
                            airborne = True
                    self._last_y = current_y

                # ---- 3️⃣ If Airborne or Gliding → DO NOTHING ----
                if airborne or gliding:
                    time.sleep(0.01)
                    continue

                # ---- 4️⃣ Grounded → Apply Speed ----
                try:
                    target_us_speed = float(self.var_speed_val.get())
                except:
                    target_us_speed = DEFAULT_BASE_SPEED_US

                internal_speed = target_us_speed / GW2_SPEED_DIVISOR

                for addr in speed_ptrs:
                    try:
                        self.pm.write_float(addr, internal_speed)
                    except:
                        pass

            except:
                pass

            # Polling rate diturunkan ke 5ms (200 tick/detik) agar injeksi memori sangat padat dan mulus
            time.sleep(0.005)

    def on_walkspeed_change(self, *args):
        if not self.var_speed_active or not self.var_speed_val: return    

        active = self.var_speed_active.get()
        try:
            val = self.var_speed_val.get()
        except:
            val = DEFAULT_BASE_SPEED_US

        if not active or val == DEFAULT_BASE_SPEED_US:
            self.is_walk_active = False
            if self.walk_thread and self.walk_thread.is_alive():
                self.walk_thread.join(timeout=0.2)
            
            internal_default = DEFAULT_BASE_SPEED_US / GW2_SPEED_DIVISOR
            
            for offset in [OFFSET_SPEED_1, OFFSET_SPEED_2, OFFSET_SPEED_3]:
                addr = self.get_pointer_address(core.base_core_address, offset)
                if addr:
                    self.pm.write_float(addr, internal_default)
            
        else:
            if not self.is_walk_active:
                self.is_walk_active = True
                self.walk_thread = threading.Thread(target=self._walk_speed_loop, daemon=True)
                self.walk_thread.start()

    # ==========================
    # Logic: Pro Glider (FIXED)
    # ========================
    def toggle_proglider(self, active=None):
        if active is None:
            self.proglider_active = not self.proglider_active
        else:
            self.proglider_active = active

        self._dbg(f"ProGlider state set to {self.proglider_active}")

        if hasattr(self, "_proglider_button"):
            color = self.BTN_ACTIVE if self.proglider_active else self.BTN_NORMAL
            self._proglider_button.configure(bg=color)


    # ==========================
    # Pro Glider UI / Hotkey
    # ==========================

    def _toggle_proglider_button(self):
        self.toggle_proglider()


    def _proglider_enable(self):
        pass

    def _prompt_proglider_hotkey(self):
        dlg = tk.Toplevel(self.ui.root)
        dlg.title("Bind Pro Glider")
        dlg.geometry("200x80")
        dlg.configure(bg="#121212")

        tk.Label(dlg, text="Press key...", fg="#00ffcc", bg="#121212").pack(expand=True)

        def poll():
            if not dlg.winfo_exists():
                return

            user32 = ctypes.windll.user32

            for vk in range(8, 255):
                if user32.GetAsyncKeyState(vk) & 0x8000 and vk not in (0x10, 0x11, 0x12):
                    self._proglider_hotkey["key"] = vk
                    self._proglider_hotkey["text"] = f"Key_{vk}"

                    if hasattr(self, "_proglider_button"):
                        self._proglider_button.config(
                            text=f"PRO GLIDER\n[Key_{vk}]"
                        )

                    dlg.destroy()
                    return

            dlg.after(15, poll)

        dlg.after(100, poll)

    def _start_proglider_hotkey_listener(self):
        user32 = ctypes.windll.user32
        was_down = False

        self._dbg("ProGlider hotkey listener started")

        while True:
            try:
                vk = self._proglider_hotkey.get("key", 0x10)
                is_down = user32.GetAsyncKeyState(vk) & 0x8000

                if is_down and self.proglider_active:
                    # Continuously apply hover and speed while held
                    self._proglider_boost()
                
                elif not is_down and was_down and self.proglider_active:
                    # Released -> Instantly restore speed to default to prevent sliding
                    self._speed_pause_until = 0  # Resume walk loop immediately
                    self._restore_speed_defaults()

                was_down = is_down
                time.sleep(0.02) # Fast polling for smooth hover

            except Exception as e:
                self._dbg(f"Hotkey listener error: {e}")
                time.sleep(0.5)

    def _proglider_boost(self):
        try:
            glider_ptr = self.get_pointer_address(core.base_core_address, OFFSET_GLIDER_DOWNRATE)
            if not glider_ptr:
                print("[MovementDBG] ProGlider: Pointer is NULL (0x0). Base offset might be wrong.")
                return

            try:
                g_val = self.pm.read_float(glider_ptr)
                
                # --- DEBUG PRINT ---
                # Ini akan mencetak nilai gravitasi ke terminal saat kamu menekan tombol boost
                print(f"[MovementDBG] Raw Downrate Value: {g_val:.3f}")
                
            except Exception as e:
                print(f"[MovementDBG] Read Error: {e}")
                return

            # EXACT ORIGINAL LOGIC: 
            if (-4.0 <= g_val <= -3.0) or (-0.002 <= g_val <= 0.0):
                self._speed_pause_until = time.time() + 0.5
                self.pm.write_float(glider_ptr, -0.001)

                speed_ptrs = []
                for offset in [OFFSET_SPEED_1, OFFSET_SPEED_2, OFFSET_SPEED_3]:
                    addr = self.get_pointer_address(core.base_core_address, offset)
                    if addr:
                        speed_ptrs.append(addr)

                for addr in speed_ptrs:
                    self.pm.write_float(addr, 60.0)

            elif -2.0 <= g_val <= 1.0:
                pass

        except Exception as e:
            print(f"[MovementDBG] ProGlider Error: {e}")

    def _restore_speed_defaults(self):
        """Helper to snap speed back to normal when releasing the hotkey"""
        try:
            # 1. Paksa kembalikan gravitasi (downrate) agar karakter bisa jatuh/mendarat
            glider_ptr = self.get_pointer_address(core.base_core_address, OFFSET_GLIDER_DOWNRATE)
            if glider_ptr:
                self.pm.write_float(glider_ptr, -3.2)
                
            # 2. Kembalikan kecepatan ke standar mid-air orisinal (12.0)
            for offset in [OFFSET_SPEED_1, OFFSET_SPEED_2, OFFSET_SPEED_3]:
                addr = self.get_pointer_address(core.base_core_address, offset)
                if addr:
                    self.pm.write_float(addr, 12.0)
        except Exception as e:
            self._dbg(f"Restore error: {e}")
    # ==========================
    # Logic: Wall Climb
    # ==========================
    def _wall_climb_loop(self):
        while self.wallclimb_active:
            try:
                wall_ptr = self.get_pointer_address(core.base_core_address, OFFSET_WALLCLIMB)
                if wall_ptr: self.pm.write_float(wall_ptr, 30.0)
            except: pass
            time.sleep(0.1)

    def toggle_wall_climb(self, active):
        self.wallclimb_active = active
        if active:
            threading.Thread(target=self._wall_climb_loop, daemon=True).start()
        else:
            try:
                wall_ptr = self.get_pointer_address(core.base_core_address, OFFSET_WALLCLIMB)
                if wall_ptr: self.pm.write_float(wall_ptr, 3.0)
            except: pass

    # Vanilla engine defaults
    _PLAYER_ZOOM_DEFAULT = 400.0
    _MOUNT_ZOOM_DEFAULT  = 400.0

    def _write_if_reset(self, addr, target, tolerance=1.0):
        """Only write if game has reset the value below our target."""
        try:
            current = self.pm.read_float(addr)
            if current < (target - tolerance):
                self.pm.write_float(addr, target)
        except:
            pass

    def _apply_zoom(self, val):
        if not self.pm:
            return

        float_val = float(val)

        # 1. PLAYER ZOOM — offset [60] is the true max zoom distance
        try:
            if hasattr(core, 'playerzom'):
                p_max = self.get_pointer_address(core.playerzom, [60])
                if p_max:
                    self.pm.write_float(p_max, float_val)
        except Exception as e:
            self._dbg(f"Player Zoom Error: {e}")

        # 2. MOUNT ZOOM — cap at 1200 to avoid engine glitch
        # Only write [132] (max zoom distance); [144]/[148] are NOT zoom distance
        # and writing arbitrary values there causes the mount camera glitch
        try:
            if hasattr(core, 'mountzom'):
                mount_zoom = min(float_val, 1200.0)
                m_max = self.get_pointer_address(core.mountzom, [132])
                if m_max:
                    self.pm.write_float(m_max, mount_zoom)
        except Exception as e:
            self._dbg(f"Mount Zoom Error: {e}")

    def _zoom_loop(self):
        """
        Re-apply zoom when the engine resets it.
        Uses read-before-write so we don't fight geometry collision logic
        (engine legitimately clamps zoom under bridges/ceilings on short frames).
        20Hz polling beats engine reset without hammering CPU.
        """
        while True:
            try:
                if hasattr(self, 'var_zoom') and self.var_zoom is not None:
                    target = self.var_zoom.get()
                    if target <= self._PLAYER_ZOOM_DEFAULT:
                        time.sleep(0.05)
                        continue

                    # Player zoom
                    if hasattr(core, 'playerzom'):
                        p_max = self.get_pointer_address(core.playerzom, [60])
                        if p_max:
                            self._write_if_reset(p_max, target)

                    # Mount zoom
                    if hasattr(core, 'mountzom'):
                        mount_target = min(target, 1200.0)
                        m_max = self.get_pointer_address(core.mountzom, [132])
                        if m_max:
                            self._write_if_reset(m_max, mount_target)

            except:
                pass

            time.sleep(0.05)  # 20Hz

    def _ground_data(self, val):
        """
        Rekreasi 1:1 dari decompiled script:
        pm.write_float(getPointerAddress(pm.base_address + ground_base_mem, offsets=ground_offset_mem), xxx)
        """
        try:
            if not core.base_core_address: return

            ground_offset_mem = [152, 80, 256, 280]
            ptr = self.get_pointer_address(core.base_core_address, ground_offset_mem)
            
            if ptr:
                self.pm.write_float(ptr, float(val))
        except Exception:
            pass
    # ==========================
    # UI Construction
    # ==========================
    def build_player_enhancement_ui(self, win):
        fixed, frame = self.ui.create_scroll_area(win, scroll=True)
        
        # Header
        h = tk.Label(fixed, text="Player Enhancement", bg="#333333", fg="white", font=("Segoe UI", 10, "bold"), pady=6)
        h.pack(fill=tk.X)
        self.ui.make_draggable(h, win, "Player Enhancement", is_group_move=False)
        
        c = tk.Label(h, text="x", bg="#333333", fg="#888", font=("Arial", 12))
        c.pack(side=tk.RIGHT, padx=10)
        c.bind("<Button-1>", lambda e: self.ui.close_tool_window(win, "Player Enhancement"))
        
        def section_lbl(txt): 
            tk.Label(fixed, text=txt, bg="#121212", fg="#0078d7", font=("Segoe UI", 9, "bold"), pady=4).pack(fill=tk.X, pady=(10, 5))

        # ==========================
        # 1. PRO GLIDER (TOP)
        # ==========================
        section_lbl("Pro Glider (Hover + Boost)")
        
        hotkey_text = self._proglider_hotkey.get("text", "SHIFT")
        self._proglider_button = tk.Button(
            fixed,
            text=f"PRO GLIDER\n[{hotkey_text}]",
            bg=self.BTN_ACTIVE if self.proglider_active else self.BTN_NORMAL,
            fg="white",
            height=3,
            relief="flat",
            command=self._toggle_proglider_button
        )
        self._proglider_button.pack(fill=tk.X, pady=4)
        self._proglider_button.bind("<Button-3>", lambda e: self._prompt_proglider_hotkey())
        tk.Label(fixed, text="Right-click to rebind. Auto-boosts when gliding.", bg="#121212", fg="#555", font=("Segoe UI", 8), justify=tk.LEFT).pack(anchor="w", padx=25)    

        # ==========================
        # 2. WALL CLIMB
        # ==========================
        section_lbl("Movement")
        
        self.var_wall = tk.BooleanVar(value=self.wallclimb_active)
        self.var_wall.trace_add("write", lambda *a: self.toggle_wall_climb(self.var_wall.get()))
        self.ui.create_checkbox(fixed, "Wall Climb", self.var_wall, window_key="Player Enhancement")

        # ==========================
        # 3. SPEED CONTROLS
        # ==========================
        section_lbl("Speed Controls (Walk/Swim/Glider)")
        
        self.var_speed_active = tk.BooleanVar(value=False)
        self.var_speed_val = tk.DoubleVar(value=DEFAULT_BASE_SPEED_US) 

        def on_speed_change_wrapper(*args):
            self.on_walkspeed_change()

        self.var_speed_active.trace_add("write", on_speed_change_wrapper)
        self.var_speed_val.trace_add("write", on_speed_change_wrapper)

        # Baris Pertama: Checkbox Speed Hack
        self.ui.create_checkbox(fixed, "Enable Speed Hack", self.var_speed_active, window_key="Player Enhancement")
        
        # [NEW] Baris Kedua: Tombol Preset Speed Hack
        preset_frame = tk.Frame(fixed, bg="#121212")
        preset_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        def set_preset_speed(val):
            self.var_speed_val.set(val)
            
        tk.Button(preset_frame, text="Default (294)", bg="#333", fg="white", relief="flat", command=lambda: set_preset_speed(294.0)).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        tk.Button(preset_frame, text="Preset (380)", bg="#333", fg="white", relief="flat", command=lambda: set_preset_speed(380.0)).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        tk.Button(preset_frame, text="Preset (450)", bg="#333", fg="white", relief="flat", command=lambda: set_preset_speed(450.0)).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        # Baris Ketiga: Slider Speed Hack
        slider_frame = tk.Frame(fixed, bg="#121212")
        slider_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(slider_frame, text="u/s:", bg="#121212", fg="#aaa").pack(side=tk.LEFT)
        tk.Entry(slider_frame, textvariable=self.var_speed_val, width=6, bg="#202020", fg="white", relief="flat").pack(side=tk.RIGHT)
        ttk.Scale(slider_frame, from_=100, to=2500, variable=self.var_speed_val, orient="horizontal").pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

       # ==========================
        # 4. AIRWALK (ORIGINAL DECOMPILED LOGIC)
        # ==========================
        section_lbl("Airwalk")
        
        global is_airwalk_active, previous_slider_value, airwalk_printing_thread
        is_airwalk_active = False
        previous_slider_value = 0.0  # DIKOREKSI: Default mutlak adalah 0.0
        
        airwalk_label = tk.Label(fixed, text="AIRWALK", bg="#121212", fg="white", font=("Segoe UI", 9, "bold"))
        airwalk_label.pack(anchor="w", padx=10, pady=(5,0))
        
        # DIKOREKSI: Rentang slider dari 0.0 hingga -20.0
        airwalk_slider = ttk.Scale(fixed, from_=0.0, to=-20.0, orient="horizontal", value=0.0)
        airwalk_slider.pack(fill=tk.X, padx=10, pady=(0, 10))

        def airwalk_value_apply():
            while not stop_airwalk_slider.is_set():
                try:
                    slider_val = float(airwalk_slider.get())
                    self._ground_data(slider_val)
                except Exception:
                    pass
                time.sleep(0.1) # Interval orisinal 0.1s

        def on_airwalk_slider(event):
            global is_airwalk_active, previous_slider_value, airwalk_printing_thread
            
            try:
                current_slider_value = float(airwalk_slider.get())
                
                if current_slider_value != previous_slider_value:
                    # DIKOREKSI: Logika OFF dieksekusi saat slider berada di 0.0
                    if current_slider_value == 0.0:
                        if is_airwalk_active:
                            is_airwalk_active = False
                            stop_airwalk_slider.set() 
                            
                            airwalk_slider.set(0.0)
                            previous_slider_value = 0.0
                            
                            self._ground_data(0.0) # Kembalikan lantai ke 0.0 (OFF)
                            
                            airwalk_label.configure(text='AIRWALK', fg="white")
                    else:
                        if not is_airwalk_active:
                            stop_airwalk_slider.clear()
                            is_airwalk_active = True
                            
                            airwalk_printing_thread = threading.Thread(target=airwalk_value_apply)
                            airwalk_printing_thread.daemon = True
                            airwalk_printing_thread.start()
                            
                            airwalk_label.configure(fg="#3a7bd5")
                    
                    previous_slider_value = current_slider_value
                    if current_slider_value != 0.0:
                        airwalk_label.configure(text=f'AIRWALK ({str(current_slider_value)[:5]})')
                        
            except Exception as e:
                print(f'[Airwalk] Event Handler Error: {e}')

        airwalk_slider.bind("<ButtonRelease-1>", on_airwalk_slider)

        # ==========================
        # 4. ZOOM CONTROLS (INDENTASI DIKOREKSI)
        # ==========================        
        section_lbl("Zoom Controls")
        
        zf = tk.Frame(fixed, bg="#121212", pady=5)
        zf.pack(fill=tk.X)
        
        top_zf = tk.Frame(zf, bg="#121212")
        top_zf.pack(fill=tk.X)
        tk.Label(top_zf, text="Max Zoom", bg="#121212", fg="white").pack(side=tk.LEFT)
        
        self.var_zoom = tk.DoubleVar(value=400)
        zoom_val_lbl = tk.Label(top_zf, text="400", bg="#121212", fg="#00ffcc", font=("Segoe UI", 9, "bold"))
        zoom_val_lbl.pack(side=tk.RIGHT)

        def _on_zoom_slide(val):
            v = float(val)
            zoom_val_lbl.config(text=f"{int(v)}")
            self._apply_zoom(v)

        zoom_slider = ttk.Scale(zf, from_=400, to=5000, variable=self.var_zoom, orient="horizontal", command=_on_zoom_slide)
        zoom_slider.pack(fill=tk.X, pady=5)

    # ==========================
    # Griffon / Mount Logic (Preserved)
    # ==========================
    
    def _griffon_toggle(self, btn):
        if self._griffon_running: return
        threading.Thread(target=self._griffon_boost_sequence, args=(btn,), daemon=True).start()  

    # =========================================================
    # AOB PATCH RESOLUTION
    # All three use the same strategy as griffon:
    #   1. Convert known ori value to bytes → scan module
    #   2. Found addr = location of that value in .exe
    #   3. Toggle by writing mod/ori at that addr
    #
    # SKYSCALE:
    #   ori = 4083  (ushort, vanilla skyscale bar value)
    #   mod = 37008 (ushort, infinite wall value)
    #   static offset = 0x12040A0 from module base
    #   No scan needed — direct static write like skyscalegreenbaraddress
    #   Survives patches as long as that data offset doesn't move
    #   If it breaks: CE → scan ushort 4083 → find what writes → check module offset
    #
    # MOUNT STAMINA:
    #   ori bytes = movss [reg+offset], xmm0  where xmm0 = stamina float
    #   We scan for a known float constant the engine writes to stamina
    #   Pattern: the float 1.0 written as a constant load near the stamina write
    #   If it breaks: CE → scan float stamina → find what writes → copy 8 bytes
    #
    # HOW TO UPDATE AFTER PATCH:
    #   Griffon:  CE find what writes to griffon boost value → copy 8 bytes → update griffoninstaboost_ori
    #   Skyscale: CE scan ushort 4083 → check module offset → update SKYSCALE_OFFSET
    #   Stamina:  CE find what writes to mount stamina float → copy 8 bytes → update STAMINA_ORI
    # =========================================================

    # Skyscale constants
    SKYSCALE_OFFSET  = 0x1212310  # module-relative, direct static address
    SKYSCALE_ORI     = 4083        # vanilla ushort value
    SKYSCALE_MOD     = 37008       # infinite wall ushort value

    # Mount stamina constants
    # Pattern: 8 bytes surrounding the stamina float write instruction
    # Update these if mount stamina breaks after a patch
    STAMINA_ORI = 8376135823064497152   # original 8 bytes (little-endian)
    STAMINA_MOD = 8376135823064497152   # same as ori until you find the correct patch bytes
    # NOTE: STAMINA uses a different approach — instead of patching code,
    # we resolve the address via AOB then write 1.0 in a loop (same as before
    # but resilient because we find the address dynamically, not via pointer chain)

    def _resolve_griffon_patch_point(self):
        griffoninstaboost_ori = 8417936924145618931
        pattern = griffoninstaboost_ori.to_bytes(8, 'little')
        addr = self.pm.pattern_scan_module(pattern, "Gw2-64.exe")
        if addr:
            self._griffon_addr = addr
            self._dbg(f"Griffon patch point: {hex(addr)}")
        else:
            self._dbg("Griffon AOB not found")

    def _resolve_skyscale_addr(self):
        """Skyscale uses a direct static offset — same stability as griffon."""
        try:
            base = self.pm.base_address
            addr = base + self.SKYSCALE_OFFSET
            # Verify: read current value, should be 4083 or 37008
            val = self.pm.read_ushort(addr)
            self._dbg(f"Skyscale addr: {hex(addr)}  current value: {val}")
            return addr
        except Exception as e:
            self._dbg(f"Skyscale resolve failed: {e}")
            return None

    # Mount stamina chain — only option without CE code bytes
    # Chain: [base_core_address] +152 +16 +912 +12 = stamina float
    # Breaks if: base_core_address is stale, OR struct layout changes
    # To upgrade to griffon-style: CE → find what writes to stamina float
    #   → copy 8 bytes → add STAMINA_ORI/STAMINA_MOD constants here
    STAMINA_CHAIN = [152, 16, 912, 12]

    def _resolve_stamina_addr(self):
        """
        Walk pointer chain to find mount stamina float address.
        Validates result by reading current value — must be 0.0 to 1.0.
        Re-called automatically when cached address goes stale.
        """
        try:
            base_off = core.base_core_address
            if not base_off:
                self._dbg("Stamina: base_core_address not set")
                return None

            # Walk chain manually so we can pinpoint which step fails
            addr = self.pm.read_longlong(self.pm.base_address + base_off)
            for i, offset in enumerate(self.STAMINA_CHAIN[:-1]):
                if not (0x10000 < addr < 0x0000800000000000):
                    self._dbg(f"Stamina chain broken at step {i} (addr={hex(addr)})")
                    return None
                addr = self.pm.read_longlong(addr + offset)

            final = addr + self.STAMINA_CHAIN[-1]

            # Validate: stamina float must be a plausible value (0-100 range)
            test = self.pm.read_float(final)
            if not (0.0 <= test <= 100.0):
                return None  # silent — bad address, just return None

            self._dbg(f"Stamina addr resolved: {hex(final)}  current={test:.1f}")
            return final

        except:
            return None  # silent failure, loop will retry next tick

    def _griffon_boost_sequence(self, btn):
        if not self._griffon_addr:
            return

        self._griffon_running = True

        griffoninstaboost_ori = 8417936924145618931
        griffoninstaboost_mod = 8417936958505357299
        hint = f"[{self._griffon_hotkey.get('text','HOTKEY')}]"

        try:
            self.pm.write_longlong(self._griffon_addr, griffoninstaboost_mod)

            steps = [
                (f'CHARGING...(5)\n PRESS {hint}', self.BTN_ACTIVE),
                (f'CHARGING...(4)\n PRESS {hint}', self.BTN_DIM),
                (f'CHARGING...(3)\n PRESS {hint}', self.BTN_ACTIVE),
                (f'CHARGING...(2)\n PRESS {hint}', self.BTN_DIM),
                (f'CHARGING...(1)\n PRESS {hint}', self.BTN_ACTIVE),
                (f'READY\n PRESS {hint}', self.BTN_DIM)
            ]

            for text, color in steps:
                if btn and btn.winfo_exists():
                    btn.configure(bg=color, text=text)
                time.sleep(1.0)

            if btn and btn.winfo_exists():
                btn.configure(bg=self.BTN_NORMAL, text=f'GRIFFON BOOST\nPRESS {hint}')

            self.pm.write_longlong(self._griffon_addr, griffoninstaboost_mod)
            time.sleep(0.5)
            self.pm.write_longlong(self._griffon_addr, griffoninstaboost_ori)

        except:
            pass
        finally:
            self._griffon_running = False


    def build_mount_enhancement(self, win):
        fixed, frame = self.ui.create_scroll_area(win, scroll=True)
        h = tk.Label(fixed, text="Mount Enhancement", bg="#333333", fg="white", font=("Segoe UI", 10, "bold"), pady=6)
        h.pack(fill=tk.X); self.ui.make_draggable(h, win, "Mount Enhancement", is_group_move=False)
        c = tk.Label(h, text="x", bg="#333333", fg="#888", font=("Arial", 12)); c.pack(side=tk.RIGHT, padx=10)
        c.bind("<Button-1>", lambda e: self.ui.close_tool_window(win, "Mount Enhancement"))
        
        # --- NEW: Skyscale Wall & Mount Energy ---
        # Inisiasi nilai UI sebagai True karena backend sudah auto-enable
        if not hasattr(self.ui, 'cb_skywall'):
            self.ui.cb_skywall = tk.BooleanVar(value=True) 
        if not hasattr(self.ui, 'cb_mount_energy'):
            self.ui.cb_mount_energy = tk.BooleanVar(value=True)

        def on_mount_energy_toggle():
            self._mount_energy_active = self.ui.cb_mount_energy.get()
            
        self.ui.create_checkbox(fixed, "Skyscale Infinite Wall", self.ui.cb_skywall, window_key="Mount Enhancement", command=lambda: self.toggle_skyscale(self.ui.cb_skywall.get()))
        self.ui.create_checkbox(fixed, "Infinite Mount Energy", self.ui.cb_mount_energy, window_key="Mount Enhancement", command=on_mount_energy_toggle)

        # Pembatas Visual (Garis)
        tk.Frame(fixed, bg="#333333", height=1).pack(fill=tk.X, pady=(10, 5))

        self._build_griffon_boost(fixed)

    def _build_griffon_boost(self, parent):
        self._griffon_button = tk.Button(parent, text="GRIFFON BOOST", bg=self.BTN_NORMAL, fg="white", height=3, relief="flat", command=lambda: self._griffon_toggle(self._griffon_button))
        self._griffon_button.pack(fill=tk.X, pady=4)
        self._griffon_button.bind("<Button-3>", lambda e: self._prompt_griffon_hotkey())

    def _prompt_griffon_hotkey(self):
        dlg = tk.Toplevel(self.ui.root); dlg.title("Bind"); dlg.geometry("200x80"); dlg.configure(bg="#121212")
        tk.Label(dlg, text="Press key...", fg="#00ffcc", bg="#121212").pack(expand=True)
        def poll():
            if not dlg.winfo_exists(): return
            user32 = ctypes.windll.user32
            for vk in range(8, 255):
                if user32.GetAsyncKeyState(vk) & 0x8000 and vk not in (0x10, 0x11, 0x12):
                    self._griffon_hotkey["key"] = vk; self._griffon_hotkey["text"] = f"Key_{vk}"
                    self._griffon_button.config(text=f"GRIFFON BOOST\n[Key_{vk}]")
                    dlg.destroy(); return
            dlg.after(15, poll)
        dlg.after(100, poll)

    def _start_griffon_hotkey_listener(self):
        user32 = ctypes.windll.user32
        was_down = False

        while True:
            try:
                is_down = user32.GetAsyncKeyState(self._griffon_hotkey["key"]) & 0x8000

                if is_down and not was_down and not self._griffon_running:
                    self._griffon_boost_sequence(
                        self._griffon_button if hasattr(self, "_griffon_button") else None
                    )

                was_down = is_down
                time.sleep(0.02)

            except:
                pass

    def _skyscale_loop(self):
        """
        Continuously re-apply skyscale mod value when active.
        Resolves address once, re-resolves if write fails (patch resilient).
        """
        while True:
            try:
                if self._skyscale_active:
                    if not self._skyscale_addr:
                        self._skyscale_addr = self._resolve_skyscale_addr()
                    if self._skyscale_addr:
                        self.pm.write_ushort(self._skyscale_addr, self.SKYSCALE_MOD)
            except Exception as e:
                self._dbg(f"Skyscale loop error: {e}")
                self._skyscale_addr = None  # force re-resolve next tick
            time.sleep(0.1)

    def toggle_skyscale(self, active):
        """Enable/disable skyscale infinite wall — replaces core.toggle_skyscale_wall."""
        self._skyscale_active = active
        if not active and self._skyscale_addr:
            try:
                self.pm.write_ushort(self._skyscale_addr, self.SKYSCALE_ORI)
                self._dbg("Skyscale restored to vanilla")
            except:
                pass

    def _mount_energy_loop(self):
        """
        Continuously write max value to mount stamina float.
        Resolves address once, retries on failure with backoff.
        """
        _retry_at = 0
        while True:
            try:
                if self._mount_energy_active:
                    if not self._stamina_addr:
                        now = time.time()
                        if now >= _retry_at:
                            self._stamina_addr = self._resolve_stamina_addr()
                            if not self._stamina_addr:
                                _retry_at = now + 3.0  # retry every 3s, not every 16ms
                    if self._stamina_addr:
                        self.pm.write_float(self._stamina_addr, 100.0)
            except:
                self._stamina_addr = None
                _retry_at = time.time() + 3.0
            time.sleep(0.016)

    def start_mount_energy_loop(self):
        pass