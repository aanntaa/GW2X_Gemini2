import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent

MAP_PORTALS_JSON = BASE_DIR / "map_portals.json"
MAP_NAMES_JSON   = BASE_DIR / "map_names.json"
XML_PATH         = BASE_DIR / "tw_me_portalsbetweenmaps.xml"
OUT_JSON         = BASE_DIR / "map_portals_merged.json"


# ──────────────────────────────────────
# Load map names
# ──────────────────────────────────────
with open(MAP_NAMES_JSON, "r", encoding="utf-8") as f:
    map_names_raw = json.load(f)

map_names = {
    str(m["id"]): m["name"]
    for m in map_names_raw
}

# ──────────────────────────────────────
# Load existing portals JSON
# ──────────────────────────────────────
with open(MAP_PORTALS_JSON, "r", encoding="utf-8") as f:
    maps = json.load(f)

map_index = {m["id"]: m for m in maps}


# ──────────────────────────────────────
# Parse XML
# ──────────────────────────────────────
tree = ET.parse(XML_PATH)
root = tree.getroot()


# ── Build MarkerCategory lookup
marker_labels = {}
for cat in root.findall(".//MarkerCategory"):
    name = cat.attrib.get("name")
    tip  = cat.attrib.get("tip-name") or cat.attrib.get("DisplayName")
    if name and tip:
        marker_labels[name] = tip


# ── Process POIs
pois = root.find("POIs")

for poi in pois:
    src_id = poi.attrib["MapID"]
    x = float(poi.attrib["xpos"])
    y = float(poi.attrib["ypos"])
    z = float(poi.attrib["zpos"])

    marker_key = poi.attrib["type"].split(".")[-1]
    label = marker_labels.get(marker_key)

    if not label:
        continue

    # ensure map entry exists
    if src_id not in map_index:
        map_index[src_id] = {
            "id": src_id,
            "name": map_names.get(src_id, f"Map {src_id}"),
            "portals": {}
        }
        maps.append(map_index[src_id])

    map_index[src_id]["portals"][label] = [x, y, z]

# ──────────────────────────────────────
# Save merged output
# ──────────────────────────────────────
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(maps, f, indent=2)

print(f"✔ merged portals written to {OUT_JSON}")
