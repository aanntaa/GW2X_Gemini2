# main.py
import gw2x_data as data
import pymem
from gw2x_logic import GW2X_Logic
from gw2x_ui import run_ui

# ---- SETUP LOGIC ----
pm = pymem.Pymem("Gw2-64.exe")       # your process manager
offsets = data.OFFSETS  # your offsets dict

logic = GW2X_Logic(pm, offsets, settings)

# ---- LOAD ROUTE / TP LIST ----
# Example:
# logic.tp_list = load_tp_route("route.json")

logic.tp_list = []  # TEMP: empty list for testing UI

# ---- START UI ----
run_ui("gw2x_main.ui", logic)