import pymem
import pymem.process
import struct

class GW2Memory:
    MAP_BASE_STATIC = 0x024FA468
    MAP_POINTER_CHAIN = [0x8, 0x8, 0x28, 0x10, 0x10, 0x18, 0x32C]

    def __init__(self):
        self.pm = None
        self.base_address = None
        self.connect()

    def connect(self):
        try:
            self.pm = pymem.Pymem("Gw2-64.exe")
            self.module = pymem.process.module_from_name(
                self.pm.process_handle, "Gw2-64.exe"
            )
            self.base_address = self.module.lpBaseOfDll
            print(f"[Mem] Connected. Base: {hex(self.base_address)}")
        except Exception as e:
            print(f"[Mem] Connection Failed: {e}")
            self.pm = None

    def resolve_pointer(self, base_offset, offsets):
        try:
            addr = self.base_address + base_offset
            addr = self.pm.read_longlong(addr)
            for off in offsets[:-1]:
                addr = self.pm.read_longlong(addr + off)
            return addr + offsets[-1]
        except:
            return None
            
    def read_map_context(self):
        if not self.pm:
            self.connect()
        if not self.pm:
            return None

        try:
            map_x_addr = self.resolve_pointer(
                self.MAP_BASE_STATIC,
                self.MAP_POINTER_CHAIN
            )

            if not map_x_addr:
                return None

            mx = self.pm.read_float(map_x_addr)

            # Y and Scale are NOT guaranteed adjacent.
            # Read them via raw static until separately scanned.
            my = self.pm.read_float(map_x_addr + 4)
            mz = self.pm.read_float(map_x_addr + 8)

            print("DEBUG:", mx, my, mz)

            return {
                "map_center_x": mx,
                "map_center_y": my,
                "map_scale": mz,
                "is_map_open": True
            }

        except Exception as e:
            print("[MapMem Error]", e)
            return None