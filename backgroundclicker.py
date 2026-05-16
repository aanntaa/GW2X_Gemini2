import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import random
import json
import win32gui
import win32api
import ctypes
import win32con
from pynput import keyboard
from datetime import datetime


# Virtual Key Mapping
VK_CODE = {
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
    "Q": 0x51, "W": 0x57, "E": 0x45, "R": 0x52, "T": 0x54,
    "Y": 0x59, "U": 0x55, "I": 0x49, "O": 0x4F, "P": 0x50,
    "A": 0x41, "S": 0x53, "D": 0x44, "F": 0x46, "G": 0x47,
    "Z": 0x5A, "X": 0x58, "C": 0x43, "V": 0x56, "B": 0x42,
    "SPACE": 0x20,
    "TAB": 0x09,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "ALT": 0x12,
}


class GW2SequenceClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("GW2 Sequence Clicker (Editable)")
        self.root.geometry("550x800")
        self.root.resizable(True, True)
        
        # State
        self.running = False
        self.sequence = [] 
        self.target_hwnd = None
        
        # --- UI LAYOUT ---
        
        # 0. Window Settings
        frame_top = ttk.LabelFrame(root, text="Window Settings")
        frame_top.pack(pady=5, padx=10, fill="x")
        
        self.var_ontop = tk.BooleanVar(value=False)
        self.chk_ontop = ttk.Checkbutton(frame_top, text="Pin on Top", 
                                         variable=self.var_ontop, command=self.toggle_topmost)
        self.chk_ontop.pack(side="left", padx=10)

        ttk.Label(frame_top, text="Opacity:").pack(side="left", padx=(20, 5))
        self.scale_alpha = ttk.Scale(frame_top, from_=0.3, to=1.0, value=1.0, command=self.update_alpha)
        self.scale_alpha.pack(side="left", fill="x", expand=True, padx=10)
        
        # 1. Target Window
        frame_target = ttk.LabelFrame(root, text="1. Target Process")
        frame_target.pack(pady=5, padx=10, fill="x")
        
        self.combo_windows = ttk.Combobox(frame_target, state="readonly")
        self.combo_windows.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(frame_target, text="Refresh", command=self.refresh_windows).pack(side="right", padx=5)
        
        # 2. Step Editor
        frame_editor = ttk.LabelFrame(root, text="2. Add New Step (F8 to Pick Pos)")
        frame_editor.pack(pady=5, padx=10, fill="x")
        
        f_r1 = ttk.Frame(frame_editor)
        f_r1.pack(fill="x", pady=2)
        ttk.Label(f_r1, text="X:").pack(side="left", padx=5)
        self.entry_x = ttk.Entry(f_r1, width=6)
        self.entry_x.pack(side="left")
        ttk.Label(f_r1, text="Y:").pack(side="left", padx=5)
        self.entry_y = ttk.Entry(f_r1, width=6)
        self.entry_y.pack(side="left")
        ttk.Button(f_r1, text="Pick (F8)", command=lambda: self.log("Press F8 to capture coords")).pack(side="left", padx=10)
        
        f_r2 = ttk.Frame(frame_editor)
        f_r2.pack(fill="x", pady=2)
        
        ttk.Label(f_r2, text="Type:").pack(side="left", padx=5)
        self.var_type = tk.StringVar(value="Double")
        ttk.OptionMenu(f_r2, self.var_type, "Double", "Left", "Right", "Key").pack(side="left")
        
        ttk.Label(f_r2, text="Hold (s):").pack(side="left", padx=5)
        self.entry_hold = ttk.Entry(f_r2, width=5)
        self.entry_hold.insert(0, "0.05") 
        self.entry_hold.pack(side="left")
        
        ttk.Label(f_r2, text="Wait After (s):").pack(side="left", padx=5)
        self.entry_wait = ttk.Entry(f_r2, width=5)
        self.entry_wait.insert(0, "0.2")
        self.entry_wait.pack(side="left")

        ttk.Button(frame_editor, text="⬇ Add Step to Sequence ⬇", command=self.add_step).pack(fill="x", padx=5, pady=5)

        # 3. Editable Sequence List
        frame_seq = ttk.LabelFrame(root, text="3. Sequence Queue (Double-Click to Edit)")
        frame_seq.pack(pady=5, padx=10, fill="both", expand=True)
        
        columns = ("Type", "Pos", "Wait", "Hold")
        self.tree = ttk.Treeview(frame_seq, columns=columns, show="headings", height=8)
        self.tree.heading("Type", text="Action")
        self.tree.heading("Pos", text="Position (X, Y)")
        self.tree.heading("Wait", text="Wait (s)")
        self.tree.heading("Hold", text="Hold (s)")
        
        self.tree.column("Type", width=80)
        self.tree.column("Pos", width=100)
        self.tree.column("Wait", width=60)
        self.tree.column("Hold", width=60)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Bind Double Click for Editing
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        scroll = ttk.Scrollbar(frame_seq, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        
        # Sequence Controls
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", padx=10)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_seq).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_step).pack(side="left", expand=True, fill="x")
        
        # 4. Execution Settings
        frame_run = ttk.LabelFrame(root, text="4. Execution Settings")
        frame_run.pack(pady=5, padx=10, fill="x")
        
        ttk.Label(frame_run, text="Loops (0=Inf):").pack(side="left", padx=5)
        self.entry_loops = ttk.Entry(frame_run, width=6)
        self.entry_loops.insert(0, "0")
        self.entry_loops.pack(side="left")

        # Save/Load Buttons
        ttk.Button(frame_run, text="Save Sequence", command=self.save_json).pack(side="right", padx=5)
        ttk.Button(frame_run, text="Load Sequence", command=self.load_json).pack(side="right", padx=5)

        # START
        self.btn_start = ttk.Button(root, text="START SEQUENCE (F6)", command=self.toggle)
        self.btn_start.pack(pady=10, fill="x", padx=10)

        # Listener
        self.listener = keyboard.Listener(on_press=self.on_key)
        self.listener.start()
        
        self.refresh_windows()
        print("GW2 Sequence Clicker Ready. Logs will appear in this terminal.")

    # --- EDITING LOGIC ---
    def on_tree_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell": return
        
        column = self.tree.identify_column(event.x) # Returns #1, #2, etc.
        row_id = self.tree.identify_row(event.y)
        if not row_id: return
        
        # Get current values
        col_idx = int(column.replace("#", "")) - 1
        current_values = self.tree.item(row_id, "values")
        current_val = current_values[col_idx]
        
        # Calculate coordinate of the cell to place widget
        x, y, width, height = self.tree.bbox(row_id, column)
        
        # Create Edit Widget based on column
        if col_idx == 0: # Type (Action)
            self.entry_edit = ttk.Combobox(self.tree, values=["Double", "Left", "Right"], state="readonly")
            self.entry_edit.set(current_val)
        else: # Pos, Wait, or Hold
            self.entry_edit = ttk.Entry(self.tree)
            self.entry_edit.insert(0, current_val)
            self.entry_edit.select_range(0, tk.END)

        self.entry_edit.place(x=x, y=y, width=width, height=height)
        self.entry_edit.focus()
        
        # Bind close events
        self.entry_edit.bind("<Return>", lambda e: self.save_edit(row_id, col_idx))
        self.entry_edit.bind("<FocusOut>", lambda e: self.entry_edit.destroy())

    def save_edit(self, row_id, col_idx):
        new_val = self.entry_edit.get()
        self.entry_edit.destroy()
        
        # Update Treeview Display
        current_values = list(self.tree.item(row_id, "values"))
        current_values[col_idx] = new_val
        self.tree.item(row_id, values=current_values)
        
        # Update Underlying Data List
        idx = self.tree.index(row_id)
        step = self.sequence[idx]
        
        try:
            if col_idx == 0: # Type
                step["type"] = new_val
            elif col_idx == 1:
                if step["type"] == "Key":
                    step["key"] = new_val.upper().strip()
                else:
                    parts = new_val.split(",")
                    step["x"] = int(parts[0].strip())
                    step["y"] = int(parts[1].strip())

            elif col_idx == 2: # Wait
                step["wait"] = float(new_val)
            elif col_idx == 3: # Hold
                step["hold"] = float(new_val)
            self.log(f"Updated step {idx+1}")
        except Exception as e:
            self.log(f"Edit Failed: Invalid Format. ({e})")
            # Refresh tree from data to revert bad edit
            self.refresh_tree_row(row_id, idx)

    def refresh_tree_row(self, row_id, idx):
        s = self.sequence[idx]

        if s["type"] == "Key":
            self.tree.item(row_id,
                values=("Key", s["key"], s["wait"], s["hold"]))
        else:
            self.tree.item(row_id,
                values=(s["type"],
                        f"{s['x']}, {s['y']}",
                        s["wait"],
                        s["hold"]))

    # --- CORE UTILS ---
    def log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] {msg}")

    def update_alpha(self, val):
        self.root.attributes('-alpha', float(val))

    def toggle_topmost(self):
        self.root.attributes('-topmost', self.var_ontop.get())

    def refresh_windows(self):
        self.windows = []
        def cb(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t: self.windows.append((hwnd, t))
        win32gui.EnumWindows(cb, None)
        values = [f"[{h}] {t}" for h, t in self.windows]
        self.combo_windows['values'] = values
        for i, v in enumerate(values):
            if "Guild Wars 2" in v:
                self.combo_windows.current(i)
                return
        if values: self.combo_windows.current(0)

    def get_hwnd(self):
        try: return int(self.combo_windows.get().split(']')[0][1:])
        except: return None

    # --- INPUT HANDLING ---
    def on_key(self, key):
        if key == keyboard.Key.f8:
            self.root.after(0, self.capture_pos)
        elif key == keyboard.Key.f6:
            self.root.after(0, self.toggle)

    def capture_pos(self):
        hwnd = self.get_hwnd()
        if not hwnd:
            self.log("ERROR: Select a window first!")
            return
        
        mx, my = win32api.GetCursorPos()
        try:
            cx, cy = win32gui.ScreenToClient(hwnd, (mx, my))
            self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(cx))
            self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(cy))
            self.log(f"Captured Pos: {cx}, {cy}")
        except Exception as e:
            self.log(f"Capture Error: {e}")

    # --- SEQUENCE MANAGEMENT ---
    def add_step(self):
        try:
            step_type = self.var_type.get()

            if step_type == "Key":
                key_value = self.entry_x.get().upper().strip()
                if key_value not in VK_CODE:
                    self.log("Invalid Key! Use like: 1, Q, E, SPACE, TAB")
                    return

                step = {
                    "type": "Key",
                    "key": key_value,
                    "hold": float(self.entry_hold.get()),
                    "wait": float(self.entry_wait.get())
                }

                self.sequence.append(step)
                self.tree.insert("", "end",
                                 values=("Key", key_value,
                                         step["wait"], step["hold"]))
                self.log(f"Added KEY step: {key_value}")

            else:
                step = {
                    "x": int(self.entry_x.get()),
                    "y": int(self.entry_y.get()),
                    "type": step_type,
                    "hold": float(self.entry_hold.get()),
                    "wait": float(self.entry_wait.get())
                }

                self.sequence.append(step)
                self.tree.insert("", "end",
                                 values=(step["type"],
                                         f"{step['x']}, {step['y']}",
                                         step['wait'], step['hold']))
                self.log(f"Added step: {step['type']} at {step['x']},{step['y']}")

        except ValueError:
            self.log("Invalid Input!")

    def remove_step(self):
        sel = self.tree.selection()
        for item in sel:
            idx = self.tree.index(item)
            del self.sequence[idx]
            self.tree.delete(item)

    def clear_seq(self):
        self.sequence = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.log("Sequence Cleared.")

    def save_json(self):
        fname = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fname:
            try:
                with open(fname, 'w') as f:
                    json.dump(self.sequence, f, indent=4)
                self.log(f"Saved sequence to {fname}")
            except Exception as e:
                self.log(f"Error saving: {e}")

    def load_json(self):
        fname = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if fname:
            try:
                with open(fname, 'r') as f:
                    self.sequence = json.load(f)
                
                # Rebuild UI
                for item in self.tree.get_children(): self.tree.delete(item)
                for step in self.sequence:
                    self.tree.insert("", "end", values=(step["type"], f"{step['x']}, {step['y']}", step['wait'], step['hold']))
                self.log(f"Loaded {len(self.sequence)} steps.")
            except Exception as e:
                self.log(f"Error loading: {e}")
    
    def send_key_background(self, hwnd, step):
        key = step["key"]
        vk = VK_CODE.get(key)

        if not vk:
            return

        # Convert VK → Scan Code
        scan_code = win32api.MapVirtualKey(vk, 0)

        # Structures
        PUL = ctypes.POINTER(ctypes.c_ulong)

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("ki", KEYBDINPUT)
            ]

        # KEY DOWN
        extra = ctypes.c_ulong(0)
        ii_ = INPUT(
            type=1,
            ki=KEYBDINPUT(
                wVk=0,
                wScan=scan_code,
                dwFlags=win32con.KEYEVENTF_SCANCODE,
                time=0,
                dwExtraInfo=ctypes.pointer(extra)
            )
        )

        ctypes.windll.user32.SendInput(1, ctypes.byref(ii_), ctypes.sizeof(ii_))
        time.sleep(max(0.03, step["hold"]))

        # KEY UP
        ii_.ki.dwFlags = win32con.KEYEVENTF_SCANCODE | win32con.KEYEVENTF_KEYUP
        ctypes.windll.user32.SendInput(1, ctypes.byref(ii_), ctypes.sizeof(ii_))


    # --- EXECUTION LOGIC ---
    def toggle(self):
        if self.running:
            self.running = False
            self.btn_start.config(text="START SEQUENCE (F6)")
            self.log("STOP Requested.")
        else:
            if not self.sequence:
                self.log("Sequence is empty!")
                return
            self.running = True
            self.btn_start.config(text="STOP (F6)")
            threading.Thread(target=self.run_sequence, daemon=True).start()

    def click_logic(self, hwnd, step):
        x, y = step['x'], step['y']
        lparam = win32api.MAKELONG(x, y)
        
        # 1. Hover (Wake Up)
        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.02)
        
        if step['type'] == "Right":
            down, up = win32con.WM_RBUTTONDOWN, win32con.WM_RBUTTONUP
            wparam = win32con.MK_RBUTTON
        else:
            down, up = win32con.WM_LBUTTONDOWN, win32con.WM_LBUTTONUP
            wparam = win32con.MK_LBUTTON

        # 2. Click
        win32api.PostMessage(hwnd, down, wparam, lparam)
        time.sleep(max(0.03, step['hold']))
        win32api.PostMessage(hwnd, up, 0, lparam)

        # 3. Double Click
        if step['type'] == "Double":
            time.sleep(0.05)
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONDBLCLK, wparam, lparam)
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def run_sequence(self):
        hwnd = self.get_hwnd()
        try: max_loops = int(self.entry_loops.get())
        except: max_loops = 0
        
        loop_count = 0
        self.log(f"Starting. Loops: {'Inf' if max_loops==0 else max_loops}")

        while self.running:
            if not win32gui.IsWindow(hwnd):
                self.log("Target window lost.")
                break

            for i, step in enumerate(self.sequence):
                if not self.running: break
                
                if step["type"] == "Key":
                    print(f"Step {i+1}: KEY {step['key']}")
                else:
                    print(f"Step {i+1}: {step['type']} @ {step['x']},{step['y']}")
                
                # Highlight current row
                children = self.tree.get_children()
                if i < len(children):
                    self.tree.selection_set(children[i])
                    self.tree.see(children[i])

                if step["type"] == "Key":
                    self.send_key_background(hwnd, step)
                else:
                    self.click_logic(hwnd, step)
                    
                time.sleep(step['wait'] + random.uniform(0, 0.02))
            
            loop_count += 1
            if max_loops > 0 and loop_count >= max_loops:
                self.log("Max loops reached.")
                break
                
        self.running = False
        self.root.after(0, lambda: self.btn_start.config(text="START SEQUENCE (F6)"))
        self.log("Sequence Finished.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GW2SequenceClicker(root)
    root.mainloop()