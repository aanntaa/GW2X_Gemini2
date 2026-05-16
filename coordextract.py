import json
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def select_xml_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Pilih File XML", filetypes=[("XML files", "*.xml")])

def run_extraction():
    xml_path = select_xml_file()
    if not xml_path: return
    
    json_path = Path("map_names.json")
    with open(json_path, "r", encoding="utf-8") as f:
        maps_data = json.load(f)
    
    map_lookup = {str(m["id"]): m for m in maps_data}
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # 1. Map Categories (Recursive)
    category_map = {}
    def find_cats(el):
        for c in el.findall("MarkerCategory"):
            if c.get("name") and c.get("DisplayName"):
                category_map[c.get("name")] = c.get("DisplayName")
            find_cats(c)
    find_cats(root)

    # 2. Trackers for Debug
    stats = {"updated": 0, "mismatch_waypoint": 0, "other_marker_types": 0}
    mismatch_details = []
    processed_waypoint_names = set()

    # 3. Process POIs
    for poi in root.iter("POI"):
        m_id = poi.get("MapID")
        p_type = poi.get("type", "").split('.')[-1]
        display_name = category_map.get(p_type)

        if not display_name or m_id not in map_lookup:
            continue

        target_map = map_lookup[m_id]
        wps_dict = target_map.get("waypoints", {})
        json_key = display_name.upper().strip()

        # Logika Filter
        is_waypoint = "WAYPOINT" in json_key
        
        if json_key in wps_dict:
            # UPDATE DATA
            try:
                x, y, z = float(poi.get("xpos")), float(poi.get("ypos")), float(poi.get("zpos"))
                current_val = wps_dict[json_key]
                wps_dict[json_key] = [current_val[0], x, y, z]
                stats["updated"] += 1
                processed_waypoint_names.add(f"{m_id}:{json_key}")
            except: pass
        else:
            if is_waypoint:
                stats["mismatch_waypoint"] += 1
                mismatch_details.append(f"[MISMATCH] Map {m_id} ({target_map['name']}): XML '{json_key}' tidak ada di JSON.")
            else:
                stats["other_marker_types"] += 1

    # 4. Audit: Apa yang ada di JSON tapi TIDAK ada di XML?
    audit_missing = []
    for m in maps_data:
        m_id = str(m["id"])
        for wp_name in m.get("waypoints", {}):
            if f"{m_id}:{wp_name.upper()}" not in processed_waypoint_names:
                audit_missing.append(f"[MISSING IN XML] Map {m_id} ({m['name']}): '{wp_name}'")

    # 5. Output Log
    print(f"\n{'='*40}")
    print(f" HASIL EKSTRAKSI: {Path(xml_path).name}")
    print(f"{'='*40}")
    print(f"Successfully Updated   : {stats['updated']} Waypoints")
    print(f"Waypoint Name Mismatch : {stats['mismatch_waypoint']} (Cek detail di bawah)")
    print(f"Other Markers Ignored  : {stats['other_marker_types']} (Vista/POI/Signs)")
    print(f"{'='*40}")

    if mismatch_details:
        print("\n[!] DETAIL MISMATCH (Nama di XML berbeda dengan di JSON):")
        for detail in mismatch_details[:15]: # Show top 15
            print(detail)

    if audit_missing:
        print("\n[?] WAYPOINT DI JSON YANG TIDAK PUNYA DATA DI XML INI:")
        for audit in audit_missing[:10]:
            print(audit)

    # Save
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(maps_data, f, indent=2)
    print(f"\n[+] File {json_path} telah diperbarui.")

if __name__ == "__main__":
    run_extraction()