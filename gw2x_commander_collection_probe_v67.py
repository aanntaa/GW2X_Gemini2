"""V67 commander collection-root discovery controller.

No MumbleLink, guessed IDs, or nearby entities are used. The DLL correlates the
proven resolver, descriptor lookup, and record writer during a controlled tag
lifecycle so the stable collection can be separated from transient records.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import mmap
import os
from pathlib import Path
import struct
import sys
import time


BUILD = "GW2X-COMMANDER-COLLECTION-PROBE-V67.0"
IPC_MAGIC = 0x37504343
IPC_VERSION = 1
IPC = struct.Struct("<IHHllIll128s")


def list_gw2_processes():
    try:
        import psutil
    except ImportError:
        return []
    found = []
    for process in psutil.process_iter(["pid", "name"]):
        try:
            if (process.info.get("name") or "").lower() == "gw2-64.exe":
                found.append(int(process.info["pid"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(found)


def choose_pid(explicit):
    if explicit:
        return int(explicit)
    pids = list_gw2_processes()
    if pids:
        print("\nChoose OBSERVER GW2 process:")
        for index, pid in enumerate(pids, 1):
            print(f"  {index}. PID {pid}  Gw2-64.exe")
        value = input("OBSERVER number or PID: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(pids):
            return pids[int(value) - 1]
        if value.isdigit():
            return int(value)
    return int(input("OBSERVER PID: ").strip())


def read_state(mm):
    mm.seek(0)
    values = IPC.unpack(mm.read(IPC.size))
    return {
        "magic": values[0],
        "version": values[1],
        "size": values[2],
        "phase": values[3],
        "request": values[4],
        "pid": values[5],
        "events": values[6],
        "dropped": values[7],
        "message": values[8].split(b"\0", 1)[0].decode("utf-8", "replace"),
    }


def set_phase(mm, phase):
    state = read_state(mm)
    message = state["message"].encode("utf-8", "replace")[:127].ljust(128, b"\0")
    payload = IPC.pack(
        state["magic"], state["version"], state["size"], int(phase),
        int(state["request"]) + 1, state["pid"], state["events"],
        state["dropped"], message,
    )
    mm.seek(0)
    mm.write(payload)
    mm.flush()
    return read_state(mm)


def countdown(seconds):
    for remaining in range(seconds, 0, -1):
        print(f"  capturing: {remaining:2d}s", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int)
    parser.add_argument("--window", type=int, default=12)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("V67 must run on Windows.")

    print(BUILD)
    pid = choose_pid(args.pid)
    tag = rf"Local\GW2X_COMMANDER_COLLECTION_PROBE_V67_{pid}"
    try:
        mm = mmap.mmap(-1, IPC.size, tagname=tag, access=mmap.ACCESS_WRITE)
    except OSError as error:
        raise SystemExit(
            "V67 mapping unavailable. Build/load KX-Vision-v67 into the observer first."
        ) from error

    output = Path("commander_collection_probe_v67") / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("v67")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S")
    for handler in (
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(output / "commander_collection_probe_v67.log", encoding="utf-8"),
    ):
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    timeline = []
    try:
        state = read_state(mm)
        if state["magic"] != IPC_MAGIC or state["version"] != IPC_VERSION:
            raise SystemExit("V67 DLL/controller ABI mismatch.")
        if state["pid"] != pid:
            raise SystemExit("V67 mapping belongs to another process.")
        logger.info("%s observer=%d writer=%s", BUILD, pid, state["message"])

        input(
            "\nKeep the controlled commander outside nearby-entity range, "
            "set tag OFF, then press Enter... "
        )
        for phase, instruction in (
            (1, "KEEP TAG OFF"),
            (2, "TURN TAG ON; MOVE SLIGHTLY"),
            (3, "TURN TAG OFF NOW"),
            (4, "TURN TAG ON AGAIN; MOVE"),
        ):
            state = set_phase(mm, phase)
            stamp = dt.datetime.now().isoformat(timespec="seconds")
            timeline.append({"phase": phase, "instruction": instruction, "time": stamp})
            logger.info("PHASE %d: %s", phase, instruction)
            print(f"\n=== {instruction} ===")
            countdown(max(5, min(30, int(args.window))))
            state = read_state(mm)
            logger.info("phase=%d events=%d dropped=%d", phase, state["events"], state["dropped"])

        final_state = set_phase(mm, 5)
        result = {
            "build": BUILD,
            "observer_pid": pid,
            "timeline": timeline,
            "final_state": final_state,
        }
        (output / "commander_collection_probe_v67.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        logger.info("COMPLETE events=%d dropped=%d", final_state["events"], final_state["dropped"])
        print("\nSend the newest kx-vision_debug log and this output folder.")
    finally:
        mm.close()


if __name__ == "__main__":
    main()
