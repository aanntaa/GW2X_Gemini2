import pymem
import struct

# Konfigurasi Offset Terverifikasi
GLOBAL_POINTER_OFFSET = 0x02608A20 
AG_CONTEXT_OFFSET = 0xf0 
TARGET_ID = 3758

def debug_agent_by_id():
    try:
        pm = pymem.Pymem("Gw2-64.exe")
        base = pymem.process.module_from_name(pm.process_handle, "Gw2-64.exe").lpBaseOfDll
        
        # 1. Dapatkan True Address ContextCollection
        ctx_coll = pm.read_longlong(base + GLOBAL_POINTER_OFFSET)
        ag_ctx = pm.read_longlong(ctx_coll + AG_CONTEXT_OFFSET)
        
        # 2. Akses Array (Offset +0x60, Count +0x6C)
        array_ptr = pm.read_longlong(ag_ctx + 0x60)
        count = pm.read_uint(ag_ctx + 0x6c)

        print(f"[*] Mencari Agent ID {TARGET_ID} di antara {count} entitas...")

        for i in range(count):
            try:
                agent_ptr = pm.read_longlong(array_ptr + (i * 8))
                if agent_ptr < 0x10000: continue

                # Baca Agent ID di offset +0x0C
                found_id = pm.read_uint(agent_ptr + 0x0C)

                if found_id == TARGET_ID:
                    print(f"\n[!!!] TARGET DITEMUKAN PADA INDEX {i}!")
                    print(f"    Agent Pointer: {hex(agent_ptr)}")
                    
                    # DEBUG: Mencari Koordinat di berbagai offset potensial
                    # Kita uji jalur standar AgChar (+0x50 -> +0x30)
                    try:
                        coords_ptr = pm.read_longlong(agent_ptr + 0x50)
                        pos = struct.unpack('fff', pm.read_bytes(coords_ptr + 0x30, 12))
                        print(f"    Pos (+0x50->+0x30): ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                        print(f"    Pos in Meters     : ({pos[0]/39.37:.2f}, {pos[1]/39.37:.2f}, {pos[2]/39.37:.2f})")
                    except:
                        print("    [!] Jalur koordinat standar (+0x50) gagal dibaca.")

                    # Jika meter pos tidak cocok dengan 180.26, 
                    # kita cari di offset AgKeyframed (+0x120)
                    try:
                        pos_alt = struct.unpack('fff', pm.read_bytes(agent_ptr + 0x120, 12))
                        print(f"    Pos Alt (+0x120)  : ({pos_alt[0]/32.0:.2f}, {pos_alt[1]/32.0:.2f}, {pos_alt[2]/-32.0:.2f})")
                    except: pass
                    
                    return
            except:
                continue

        print(f"\n[-] Agent ID {TARGET_ID} tidak ditemukan di AgContext (0xf0).")
        print("[?] Ini menandakan 0xf0 mungkin bukan Global List, atau Commander berada di Context lain.")

    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    debug_agent_by_id()