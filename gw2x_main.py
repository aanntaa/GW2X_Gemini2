import tkinter as tk
import sys
import ctypes

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    if not is_admin():
        print("[Main] Requesting Administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # Import dependencies HANYA setelah hak akses Administrator didapatkan
    from gw2x_ui import GW2X_UI
    import gw2x_data as data
    import gw2x_core as core

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass

    try:
        print("[Main] Starting GW2X...")
        offsets = data.OFFSETS

        root = tk.Tk()
        root.withdraw()  # Hide main window until process selected

        processes = core.connect()  # now returns list

        if not processes:
            print("[Main] No GW2 process found.")
            root.deiconify()
            app = GW2X_UI(root, None, offsets)
            root.mainloop()
            sys.exit()

        # If only one process → auto attach
        if len(processes) == 1:
            pid = processes[0]["pid"]
            core.connect(pid)

            root.deiconify()
            app = GW2X_UI(root, core.pm, offsets)
            root.mainloop()

        else:
            # Multiple processes → show selector
            from gw2x_ui import show_process_selector

            def after_attach(pid):
                root.deiconify()
                GW2X_UI(root, core.pm, offsets)

            show_process_selector(after_attach)
            root.mainloop()

    except Exception as e:
        print(f"Critical Error: {e}")
        input("Press Enter to exit...")