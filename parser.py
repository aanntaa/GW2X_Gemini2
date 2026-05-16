"""
evtc_parser.py
==============
Parses ArcdPS .zevtc, .evtc, and extensionless EVTC log files.
Extracts a defId->name dictionary for all NPCs, gadgets, and world objects.

USAGE:
    python evtc_parser.py "C:/path/to/arcdps.cbtlogs"
    python evtc_parser.py "C:/path/to/single_file.zevtc"

OUTPUT:
    gw2x_def_db.json  — merged {defId_str: name} dict loaded at runtime.

AGENT TYPES IN EVTC:
    elite == 0xFFFFFFFF + prof < 0xFFFF0000  → real NPC/creature (e.g. 8937 = "Flame Legion Bladestorm")
    elite == 0xFFFFFFFF + prof >= 0xFFFF0000 → ArcdPS synthetic gadget/object ID
                                                (e.g. 0xFFFFC56E = "Ballista")
                                                NOTE: these are NOT the real GW2 defIds.
                                                The real defId (e.g. 44916) is only available
                                                at spawn via hooked game function — not in logs.
    elite != 0xFFFFFFFF                       → player (skip)
"""

import zipfile
import struct
import json
import os
import sys
import glob
from pathlib import Path

DB_FILE     = Path(__file__).parent / "gw2x_def_db.json"
AGENT_SIZE  = 96
AGENT_START = 20
parsed_entries_this_run = {}


def _is_evtc(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b'EVTC'


def parse_evtc_bytes(data: bytes) -> dict:
    """
    Parse raw EVTC bytes.
    Returns {str(prof): name} for ALL NPC/gadget agents
    (both real GW2 defIds and ArcdPS synthetic IDs).
    """
    if not _is_evtc(data):
        return {}

    agent_count = struct.unpack_from('<I', data, 16)[0]
    if agent_count == 0 or agent_count > 100000:
        return {}

    results = {}
    for i in range(agent_count):
        base = AGENT_START + i * AGENT_SIZE
        if base + AGENT_SIZE > len(data):
            break

        prof  = struct.unpack_from('<I', data, base + 0x08)[0]
        elite = struct.unpack_from('<I', data, base + 0x0C)[0]
        name_raw = data[base + 0x1C: base + 0x1C + 68]
        name = name_raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()

        # Only non-players (elite == 0xFFFFFFFF), with a valid prof and name
        if elite == 0xFFFFFFFF and prof > 0 and name:
            # Skip internal ArcdPS "gdXXXXX-YY" noise entries
            if name.startswith('gd') and '-' in name:
                continue
                
            # STRIP MASKING: Bersihkan ArcdPS bitmask untuk mendapatkan Native ID
            if prof >= 0xFFFF0000:
                prof = prof & 0x0000FFFF  # Operasi Bitwise AND mengeliminasi 16-bit atas
                
            results[str(prof)] = name

    return results


def _read_file(filepath: str) -> bytes | None:
    """Read a .zevtc, .evtc, or extensionless EVTC file into bytes."""
    try:
        # Try as zip first (handles .zevtc and any zip-wrapped file)
        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                return z.read(z.namelist()[0])
        except zipfile.BadZipFile:
            pass

        # Read raw bytes (handles .evtc and extensionless files)
        with open(filepath, 'rb') as f:
            data = f.read()

        if _is_evtc(data):
            return data

        print(f"  [SKIP] Not an EVTC file: {filepath}")
        return None

    except Exception as e:
        print(f"  [WARN] Failed to read {filepath}: {e}")
        return None


def parse_evtc_file(filepath: str) -> dict:
    """Parse a single file. Returns {str(prof): name}."""
    data = _read_file(filepath)
    if data is None:
        return {}
    return parse_evtc_bytes(data)


def parse_evtc_folder(folder: str) -> dict:
    """
    Parse all EVTC files in a folder (recursively).
    Accepts .zevtc, .evtc, and extensionless files.
    Returns merged {str(prof): name} dict.
    """
    # Collect files: known extensions + extensionless files that look like EVTC dates
    files = set()
    for ext in ('*.zevtc', '*.evtc'):
        files.update(glob.glob(os.path.join(folder, '**', ext), recursive=True))

    # Also pick up extensionless files (ArcdPS map logs like "20260228-052230")
    for root, dirs, filenames in os.walk(folder):
        for fname in filenames:
            if '.' not in fname:  # no extension
                files.add(os.path.join(root, fname))

    print(f"Found {len(files)} candidate files in {folder}")

    combined = {}
    parsed = 0
    for f in sorted(files):
        entries = parse_evtc_file(f)
        if entries:
            parsed += 1
            new = {k: v for k, v in entries.items() if k not in combined}
            if new:
                print(f"  {os.path.basename(f)}: +{len(new)} new entries "
                      f"({len(entries)} total in file)")
            combined.update(entries)

    print(f"Parsed {parsed} valid EVTC files, {len(combined)} unique entries total")
    return combined


def load_def_db() -> dict:
    """Load existing gw2x_def_db.json, or return empty dict."""
    if DB_FILE.exists():
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load {DB_FILE}: {e}")
    return {}


def save_def_db(db: dict):
    """Save sorted def database to gw2x_def_db.json."""
    sorted_db = dict(sorted(db.items(), key=lambda x: int(x[0])))
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_db, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(sorted_db)} entries to {DB_FILE}")


# Singleton cache for runtime use
_cached_db: dict = None

def get_def_db() -> dict:
    """Returns cached def database (loaded once from gw2x_def_db.json)."""
    global _cached_db
    if _cached_db is None:
        _cached_db = load_def_db()
    return _cached_db


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        default = os.path.expandvars(
            r'%USERPROFILE%\OneDrive\Documents\Guild Wars 2\addons\arcdps\arcdps.cbtlogs')
        if os.path.exists(default):
            folder = default
            print(f"Using default log path: {folder}")
        else:
            print("Usage: python evtc_parser.py <path_to_logs_folder_or_single_file>")
            sys.exit(1)
    else:
        folder = sys.argv[1]

    existing = load_def_db()
    print(f"Existing database: {len(existing)} entries\n")

    # Single file or folder
    if os.path.isfile(folder):
        new_entries = parse_evtc_file(folder)
    else:
        new_entries = parse_evtc_folder(folder)

    # --- Determine only truly NEW entries ---
    new_only = {k: v for k, v in new_entries.items() if k not in existing}

    before = len(existing)
    existing.update(new_entries)
    added = len(existing) - before

    print(f"\nAdded {added} new entries (total: {len(existing)})")
    save_def_db(existing)

    # --- Show ONLY newly added entries ---
    if new_only:
        print(f"\nNew entries added this run ({len(new_only)} total):")

        sorted_new = dict(sorted(new_only.items(), key=lambda x: int(x[0])))

        for k, v in sorted_new.items():
            synthetic = int(k) >= 0xFFFF0000
            tag = " [synthetic]" if synthetic else ""
            print(f"  {k}: {v}{tag}")
    else:
        print("\nNo new entries were added.")