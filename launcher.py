import os
import sys
import subprocess
import ctypes

# -----------------------------
# Check admin privileges
# -----------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Relaunch as admin
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{os.path.abspath(__file__)}"',
        None,
        1
    )
    sys.exit()

# -----------------------------
# Launcher loop
# -----------------------------
while True:

    print("\n=======================")
    print(" GW2X Launcher")
    print("=======================\n")

    try:
        process = subprocess.run(
            [sys.executable, "gw2x_main.py"]
        )

        code = process.returncode

        if code == 10:
            print("Restart requested...")
            continue

        if code == 20:
            print("Closing launcher...")
            break

    except KeyboardInterrupt:
        print("\nCtrl+C detected")

    # Menu after Ctrl+C or exit
    print("\nOptions:")
    print("1. Restart")
    print("2. Exit")

    choice = input("Select: ")

    if choice == "1":
        print("Restarting...\n")
        continue
    else:
        print("Exiting launcher...")
        break