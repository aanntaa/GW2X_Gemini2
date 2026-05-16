# gw2x_fishing.py
import threading
import time
import ctypes
import win32gui
import tkinter as tk
from tkinter import ttk
import gw2x_core as core

# --- WIN32 CONSTANTS ---
PostMessage = ctypes.windll.user32.PostMessageW
MapVirtualKey = ctypes.windll.user32.MapVirtualKeyW
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

class GW2X_Fishing:
    def __init__(self, pm, hotkey_cfg):
        self.pm = pm
        self.hk = hotkey_cfg
        self.hwnd = None

        # Control Flags
        self.slow_enabled = False
        self.slow_stop = threading.Event()
        self.fast_enabled = False
        self.fast_stop = threading.Event()
        self.full_enabled = False
        self.full_stop = threading.Event()

        # States
        self.fishing_catching = threading.Event()
        self.fishing_count = 0
        
        print("[DEBUG] Initializing Fishing Module with Full Diagnostics...")
        try:
            self.rethrow_delay = 4.0 # Set to 4s as requested for animation
            self.hk_cast = self._get_clean_key(getattr(self.hk, "fishinghotkeyDirectInput", "02")) 
            self.hk_left = self._get_clean_key(getattr(self.hk, "fishingLeftDirectInput", "03"))   
            self.hk_right = self._get_clean_key(getattr(self.hk, "fishingRightDirectInput", "04")) 
            
            print(f"[DEBUG] Config Loaded -> Cast: {self.hk_cast}, Left: {self.hk_left}, Right: {self.hk_right}")
        except Exception as e:
            print(f"[DEBUG] Config Load Error: {e}")
            self.hk_cast, self.hk_left, self.hk_right = "02", "03", "04"

    def _get_clean_key(self, hex_str):
        if not hex_str: return "0"
        return "".join(c for c in str(hex_str) if c in "0123456789abcdefABCDEF")

    def addr(self, base, offsets):
        return core.get_addr(base, offsets)
    
    def _find_window(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.hwnd = win32gui.FindWindow(None, "Guild Wars 2")
        return self.hwnd

    def _press_background(self, hex_key, duration=0.1, label="Action"):
        hwnd = self._find_window()
        if not hwnd: return
        try:
            scan_code = int(hex_key, 16)
            vk_code = MapVirtualKey(scan_code, 1)
            print(f"[INPUT-TRACE] {label} | Hex(DIK): {hex_key} | VK: {vk_code} | Scan: {scan_code}")
            
            lparam_down = 1 | (scan_code << 16)
            lparam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)

            PostMessage(hwnd, WM_KEYDOWN, vk_code, lparam_down)
            time.sleep(duration)
            PostMessage(hwnd, WM_KEYUP, vk_code, lparam_up)
        except Exception as e:
            print(f"[INPUT-EXC] {label}: {e}")

    # ===============================
    # CORE LOGIC: FISHING FIGHT
    # ===============================
    def fishing_fight(self, instant=False):
        """Logic-driven catch verification by monitoring progress movement."""
        self.fishing_catching.clear() 
        start_time = time.time()
        
        # Get memory addresses
        addr_prog = self.addr(core.fishing_base_mem, core.fishing_offset_mem)
        addr_hook = self.addr(core.fishing_insta_hook_base_mem, core.fishing_insta_hook_offset_mem)

        while not self.fishing_catching.is_set():
            try:
                elapsed = time.time() - start_time

                if instant or elapsed >= 8.0:
                    # --- THE PRECISION GATE ---
                    # We wait until the progress bar actually moves or state changes.
                    # This proves the server has acknowledged the 'Hook' input.
                    hook_synced = False
                    for _ in range(50): # Wait up to 2.5 seconds
                        # Check if progress has started (even a tiny bit) OR hook state is no longer 'Bite'
                        if self.pm.read_float(addr_prog) > 0.0 or self.pm.read_int(addr_hook) != 2:
                            hook_synced = True
                            break
                        time.sleep(0.05)
                    
                    if not hook_synced:
                        print("[DEBUG] FAIL: Server desync. Hook was never acknowledged.")
                        break

                    # --- THE FINALIZER ---
                    # Now that we KNOW the minigame is active, we write the success.
                    for i in range(5): 
                        self.pm.write_float(addr_prog, 1.0)
                        self.pm.write_int(addr_hook, 1) 
                        
                        if self.pm.read_int(addr_hook) == 1:
                            print(f"[DEBUG] Verified Catch | Latency: {elapsed:.2f}s | Attempt: {i+1}")
                            break
                        time.sleep(0.05)

                    self.fishing_catching.set()
                    break

                # --- Movement logic for 'Slow' mode ---
                f_pos = self.pm.read_float(self.addr(core.fishing_fish_bar_mem, core.fishing_fish_bar_offset_mem))
                p_pos = self.pm.read_float(self.addr(core.fishing_player_bar_mem, core.fishing_player_bar_offset_mem))
                
                if f_pos >= p_pos:
                    self._press_background(self.hk_right, 0.02, "R")
                else:
                    self._press_background(self.hk_left, 0.02, "L")
                time.sleep(0.01) 

            except Exception as e:
                print(f"[DEBUG] Logic Error: {e}")
                break
    # ===============================
    # AUTOMATION LOOPS
    # ===============================
    
    def _fast_assist_loop(self):
        """Manual Casting, but Bot does Instant Catch on Bite"""
        print("[DEBUG] Fast Assist (Instant Hook) Active.")
        while not self.fast_stop.is_set():
            try:
                addr_hook = self.addr(core.fishing_insta_hook_base_mem, core.fishing_insta_hook_offset_mem)
                if self.pm.read_int(addr_hook) == 2:
                    self._press_background(self.hk_cast, 0.2, "Instant Hook")
                    self.pm.write_int(addr_hook, 1)
                    self.fishing_fight(instant=True)
                    self.fishing_catching.clear()
                time.sleep(0.1)
            except: pass

    def _wait_for_idle(self, timeout=12.0):
        """
        Logic: Monitors the hook address. When it hits 0, the game 
        is ready for a new 'Cast' input.
        """
        addr_hook = self.addr(core.fishing_insta_hook_base_mem, core.fishing_insta_hook_offset_mem)
        start_wait = time.time()
        
        while (time.time() - start_wait) < timeout:
            current_state = self.pm.read_int(addr_hook)
            
            # If the state is 0, the character is physically ready to cast again
            if current_state == 0:
                print(f"[DEBUG] Character is Idle. Ready after {time.time() - start_wait:.2f}s")
                return True
            
            # Polling rate of 5Hz is enough for UI/animation checks
            time.sleep(0.2)
            
        print("[DEBUG] Idle Detection Timeout. Attempting re-cast anyway.")
        return False

    def _logic_step(self, instant):
        try:
            addr_hook = self.addr(core.fishing_insta_hook_base_mem, core.fishing_insta_hook_offset_mem)
            if self.pm.read_int(addr_hook) == 2:
                # 1. Hook and Fight
                self._press_background(self.hk_cast, 0.2, "Hook Action")
                self.fishing_fight(instant=instant)
                
                # 2. Dynamic Wait: Wait for the game to reset to state 0
                # We add a small initial sleep (2s) to let the 'Success' state settle
                time.sleep(2.0) 
                self._wait_for_idle(timeout=12.0)
                
                # 3. Final Rethrow
                print("[DEBUG] Executing Rethrow...")
                self._press_background(self.hk_cast, 0.3, "Rethrow")
        except Exception as e:
            print(f"[DEBUG] Logic Step Error: {e}")
            
    def _fast_loop(self):
        """Full Auto + Instant Catch"""
        print("[DEBUG] Full Auto (Fast) Active.")
        while not self.fast_stop.is_set():
            self._logic_step(instant=True)
            time.sleep(0.1)

    def _full_loop(self):
        """Full Auto + Reeling (Slow)"""
        print("[DEBUG] Full Auto (Slow) Active.")
        while not self.full_stop.is_set():
            self._logic_step(instant=False)
            time.sleep(0.1)

    # ===============================
    # TOGGLES
    # ===============================
    def toggle_fast_assist(self):
        """Manual Cast -> Bot Instantly Hooks & Catches"""
        if self.fast_enabled:
            self.fast_stop.set()
            self.fast_enabled = False
            return False
        self.fast_enabled = True
        self.fast_stop.clear()
        threading.Thread(target=self._fast_assist_loop, daemon=True).start()
        return True

    def toggle_fast_fishing(self):
        """Full Auto -> Casts and Instant Catches"""
        if self.fast_enabled: # Shared flag with assist for simplicity
            self.fast_stop.set()
            self.fast_enabled = False
            return False
        self.fast_enabled = True
        self.fast_stop.clear()
        threading.Thread(target=self._fast_loop, daemon=True).start()
        return True

    def toggle_full_fishing(self):
        """Full Auto -> Casts and Reels (Slow)"""
        if self.full_enabled:
            self.full_stop.set()
            self.full_enabled = False
            return False
        self.full_enabled = True
        self.full_stop.clear()
        threading.Thread(target=self._full_loop, daemon=True).start()
        return True

# ===============================
# UI CLASS
# ===============================
class FishingUI:
    def __init__(self, fishing, make_draggable, gui):
        self.fishing = fishing
        self.make_draggable = make_draggable
        self.gui = gui

    def build_ui(self, win):
        header = tk.Frame(win, bg="#333333", height=28)
        header.pack(fill=tk.X)
        tk.Label(header, text="Fishing Assist [DIAGNOSTIC]", bg="#333333", fg="orange", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=8)
        
        close_btn = tk.Label(header, text="✕", bg="#333333", fg="#aaaaaa", cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=8)
        close_btn.bind("<Button-1>", lambda e: self.gui.close_tool_window(win, "Fishing Assist"))
        
        self.make_draggable(header, win, "Fishing Assist") 

        body = tk.Frame(win, bg="#121212")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._add_row(body, "🎣 Slow Assist", self._toggle_slow, "slow")
        self._add_row(body, "⚡ Fast Assist", self._toggle_insta, "insta")
        self._add_row(body, "🤖 Auto (Slow)", self._toggle_full, "full")
        self._add_row(body, "🚀 Auto (Fast)", self._toggle_fast, "fast")

    def _add_row(self, parent, label, cmd, attr):
        row = tk.Frame(parent, bg="#121212")
        row.pack(fill=tk.X, pady=4)
        btn = tk.Button(row, text=label, bg="#222222", fg="#00ff88", command=cmd)
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        status = tk.Label(row, text="OFF", width=5, bg="#1a1a1a", fg="#888888")
        status.pack(side=tk.LEFT, padx=5)
        setattr(self, f"{attr}_status", status)

    def _update_row(self, attr, active):
        status = getattr(self, f"{attr}_status")
        status.config(text="ON" if active else "OFF", fg="#00ff00" if active else "#888888")

    def _toggle_slow(self): 
        # Implement slow assist toggle if needed, or link to existing
        pass
        
    def _toggle_insta(self):
        self._update_row("insta", self.fishing.toggle_fast_assist())
    
    def _toggle_full(self): 
        self._update_row("full", self.fishing.toggle_full_fishing())
        
    def _toggle_fast(self): 
        self._update_row("fast", self.fishing.toggle_fast_fishing())