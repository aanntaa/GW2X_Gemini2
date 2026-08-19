#!/usr/bin/env python3
"""
GW2 Mumble map-bridge probe
===========================

Reads the official GW2 MumbleLink shared memory directly and prints the
avatar/world coordinates together with the context's playerX/playerY and
mapCenter/mapScale values.

Why:
The collision files use map/HAVK coordinates, while fAvatarPosition is game
world space. playerX/playerY are the missing bridge candidate.

Usage:
    python gw2_mumble_map_bridge_probe.py

Optional continuous mode:
    python gw2_mumble_map_bridge_probe.py --watch

In watch mode it prints a line whenever the avatar moves enough.
"""

import argparse
import mmap
import struct
import time

SIZE = 5460

# LinkedMem offsets from GW2 MumbleLink layout.
OFF_UI_TICK = 4
OFF_AVATAR_POS = 8
OFF_CONTEXT = 1108

CTX_MAP_ID = OFF_CONTEXT + 28
CTX_MAP_TYPE = OFF_CONTEXT + 32
CTX_INSTANCE = OFF_CONTEXT + 40
CTX_BUILD_ID = OFF_CONTEXT + 44
CTX_UI_STATE = OFF_CONTEXT + 48
CTX_COMPASS_ROT = OFF_CONTEXT + 56
CTX_PLAYER_X = OFF_CONTEXT + 60
CTX_PLAYER_Y = OFF_CONTEXT + 64
CTX_MAP_CENTER_X = OFF_CONTEXT + 68
CTX_MAP_CENTER_Y = OFF_CONTEXT + 72
CTX_MAP_SCALE = OFF_CONTEXT + 76
CTX_PROCESS_ID = OFF_CONTEXT + 80

def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]

def f32(buf, off):
    return struct.unpack_from("<f", buf, off)[0]

def vec3(buf, off):
    return struct.unpack_from("<3f", buf, off)

def open_link():
    names = ["MumbleLink", "MumbleLink_0"] + [f"MumbleLink_{i}" for i in range(1, 10)]
    for name in names:
        try:
            mm = mmap.mmap(-1, SIZE, tagname=name, access=mmap.ACCESS_READ)
            return name, mm
        except Exception:
            pass
    raise RuntimeError("No GW2 MumbleLink shared memory found.")

def snapshot(mm):
    mm.seek(0)
    b = mm.read(SIZE)
    return {
        "tick": u32(b, OFF_UI_TICK),
        "avatar": vec3(b, OFF_AVATAR_POS),
        "map_id": u32(b, CTX_MAP_ID),
        "map_type": u32(b, CTX_MAP_TYPE),
        "instance": u32(b, CTX_INSTANCE),
        "build_id": u32(b, CTX_BUILD_ID),
        "ui_state": u32(b, CTX_UI_STATE),
        "compass_rotation": f32(b, CTX_COMPASS_ROT),
        "player_x": f32(b, CTX_PLAYER_X),
        "player_y": f32(b, CTX_PLAYER_Y),
        "map_center_x": f32(b, CTX_MAP_CENTER_X),
        "map_center_y": f32(b, CTX_MAP_CENTER_Y),
        "map_scale": f32(b, CTX_MAP_SCALE),
        "process_id": u32(b, CTX_PROCESS_ID),
    }

def print_snapshot(s):
    ax, ay, az = s["avatar"]
    print(
        f'tick={s["tick"]} '
        f'mapId={s["map_id"]} instance={s["instance"]} build={s["build_id"]} '
        f'avatar=({ax:.6f},{ay:.6f},{az:.6f}) '
        f'playerXY=({s["player_x"]:.6f},{s["player_y"]:.6f}) '
        f'mapCenter=({s["map_center_x"]:.6f},{s["map_center_y"]:.6f}) '
        f'mapScale={s["map_scale"]:.9f} '
        f'compassRot={s["compass_rotation"]:.9f} '
        f'uiState=0x{s["ui_state"]:08X}'
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=0.25)
    ap.add_argument("--move-threshold", type=float, default=0.50)
    args = ap.parse_args()

    name, mm = open_link()
    print(f"[+] Opened {name}")

    if not args.watch:
        print_snapshot(snapshot(mm))
        return

    last = None
    try:
        while True:
            s = snapshot(mm)
            p = s["avatar"]
            if last is None:
                print_snapshot(s)
                last = p
            else:
                dx = p[0] - last[0]
                dy = p[1] - last[1]
                dz = p[2] - last[2]
                if dx*dx + dy*dy + dz*dz >= args.move_threshold**2:
                    print_snapshot(s)
                    last = p
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[+] stopped")

if __name__ == "__main__":
    main()
