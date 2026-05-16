"""
ArcdPS Bridge Enhancement - Live NPC Name Lookup (NON-BLOCKING VERSION)
========================================================================
This version won't hang if the bridge DLL isn't loaded.
"""

import ctypes
import threading
import time
from typing import Dict, Optional
import json, os

try:
    NPC_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "npc_name_cache.json")
except NameError:
    NPC_CACHE_FILE = os.path.join(os.getcwd(), "npc_name_cache.json")
# Bridge constants
BRIDGE_SHM_NAME = "GW2X_AGENT_BRIDGE"
BRIDGE_VERSION = 5
BRIDGE_MAX_ENTRIES = 16000

class BridgeEntry(ctypes.Structure):
    _fields_ = [
        ("agentId", ctypes.c_uint64),      # Changed from agentAddr to agentId
        ("instId", ctypes.c_uint16),
        ("_pad", ctypes.c_uint8 * 2),
        ("defId", ctypes.c_uint32),
        ("name", ctypes.c_char * 64)
    ]

class BridgeSharedMemory(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("count", ctypes.c_uint32),
        ("_pad", ctypes.c_uint32 * 2),
        ("entries", BridgeEntry * BRIDGE_MAX_ENTRIES)
    ]

class BridgeNameLookup:
    """
    Live NPC name lookup from ArcDPS bridge (non-blocking).
    """
    
    def __init__(self):
        """Initialize bridge connection (returns immediately, won't hang)"""
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # --- PERBAIKAN: Deklarasi Tipe Pointer 64-bit ---
        # Ini mencegah sistem memotong alamat memori yang menyebabkan crash seketika
        self.kernel32.OpenFileMappingA.restype = ctypes.c_void_p
        self.kernel32.MapViewOfFile.restype = ctypes.c_void_p
        self.kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        # -----------------------------------------------

        self.h_map = None
        self.p_shm = None
        self.shm = None
        self.sid_to_name: Dict[int, str] = {}
        self.last_update_count = 0
        self._lock = threading.Lock()
        self._connected = False
        
        # Try to connect (returns immediately)
        try:
            self._connected = self._connect()
        except Exception as e:
            print(f"[BridgeName] ✗ Init error: {e}")
            self._connected = False

        self.load_cache()  # Always load cache regardless of bridge connection

    def load_cache(self):
        """Load previously discovered names from disk"""
        if os.path.exists(NPC_CACHE_FILE):
            try:
                with open(NPC_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self.sid_to_name = {int(k): v for k, v in data.items()}
                    print(f"[BridgeName] Loaded {len(self.sid_to_name)} cached names")
            except Exception as e:
                print(f"[BridgeName] Cache load error: {e}")
        
    def _connect(self):
        """Connect to bridge shared memory (non-blocking)"""
        try:
            # OpenFileMappingA returns immediately (doesn't block)
            self.h_map = self.kernel32.OpenFileMappingA(
                0x0004,  # FILE_MAP_READ
                False,
                BRIDGE_SHM_NAME.encode('ascii')
            )
            
            if not self.h_map:
                return False  # Bridge not available
            
            self.p_shm = self.kernel32.MapViewOfFile(
                self.h_map, 0x0004, 0, 0, 0
            )
            
            if not self.p_shm:
                self.kernel32.CloseHandle(self.h_map)
                self.h_map = None
                return False
            
            self.shm = ctypes.cast(self.p_shm, ctypes.POINTER(BridgeSharedMemory)).contents
            
            print(f"[BridgeName] ✓ Connected - {self.shm.count} agents")
            return True
            
        except Exception as e:
            print(f"[BridgeName] ✗ Connection failed: {e}")
            return False
    
    def is_connected(self):
        """Check if bridge is available"""
        return self._connected and self.shm is not None
    
    def update_mappings(self, force: bool = False):
        """Update SID -> Name mappings from bridge"""
        if not self.is_connected():
            return
        
        with self._lock:
            try:
                current_count = self.shm.count
                
                if not force and current_count == self.last_update_count:
                    return
                
                start_idx = 0 if force else self.last_update_count
                new_mappings = 0
                
                for i in range(start_idx, min(current_count, BRIDGE_MAX_ENTRIES)):
                    entry = self.shm.entries[i]
                    
                    if entry.defId == 0:
                        continue
                    
                    name = entry.name.decode('utf-8', errors='ignore').strip('\x00')
                    if not name:
                        continue
                    
                    if entry.defId not in self.sid_to_name or self.sid_to_name[entry.defId] != name:
                        self.sid_to_name[entry.defId] = name
                        new_mappings += 1
                
                self.last_update_count = current_count
                
                if new_mappings > 0:
                    print(f"[BridgeName] +{new_mappings} new (total: {len(self.sid_to_name)})")
                    self.save_cache()
            except Exception as e:
                print(f"[BridgeName] Update error: {e}")
    
    def get_name_by_sid(self, species_id: int, auto_update: bool = True) -> Optional[str]:
        """Get NPC name for species ID — works from cache even if bridge offline"""
        if self.is_connected() and auto_update:
            self.update_mappings()
        
        with self._lock:
            return self.sid_to_name.get(species_id)
    
    def get_all_mappings(self, auto_update: bool = True) -> Dict[int, str]:
        """Get all SID -> Name mappings"""
        if not self.is_connected():
            return {}
        
        if auto_update:
            self.update_mappings()
        
        with self._lock:
            return dict(self.sid_to_name)
    
    def save_cache(self):
        """Save all discovered names to disk securely"""
        try:
            # Pengecekan keamanan: Jangan pernah simpan jika dictionary kosong
            if not self.sid_to_name:
                print(f"[BridgeName] Peringatan: Tidak ada data di memory. Membatalkan penyimpanan agar cache lama tidak terhapus.")
                return

            # Baca file lama terlebih dahulu jika ada, untuk perlindungan tambahan
            existing_data = {}
            if os.path.exists(NPC_CACHE_FILE):
                try:
                    with open(NPC_CACHE_FILE, 'r') as f:
                        data = json.load(f)
                        existing_data = {int(k): v for k, v in data.items()}
                except Exception:
                    pass # Abaikan error baca, anggap saja file belum ada atau rusak
            
            # Gabungkan data lama dengan data baru (data baru akan menimpa data lama dengan ID sama)
            merged_data = existing_data.copy()
            merged_data.update(self.sid_to_name)

            # Jika setelah digabung ternyata jumlah datanya justru berkurang, kita batalkan simpan
            if existing_data and len(merged_data) < len(existing_data):
                print(f"[BridgeName] Error: Terdeteksi penurunan drastis pada jumlah data. Membatalkan proses overwrite untuk melindungi cache lama!")
                return
            
            # Update dictionary memori internal dengan hasil gabungan
            self.sid_to_name = merged_data

            # Simpan data yang sudah digabungkan dan divalidasi
            with open(NPC_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in self.sid_to_name.items()}, f, indent=2, ensure_ascii=False)
            
            print(f"[BridgeName] Cache berhasil diamankan: {len(self.sid_to_name)} entries → {NPC_CACHE_FILE}")

        except Exception as e:
            print(f"[BridgeName] Cache save FAILED: {e}")
            
    def export_to_json(self, filepath: str):
        """Export mappings to JSON file"""
        if not self.is_connected():
            print("[BridgeName] ✗ Not connected, cannot export")
            return
        
        import json
        
        self.update_mappings(force=True)
        
        with self._lock:
            export_data = {str(k): v for k, v in self.sid_to_name.items()}
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"[BridgeName] ✓ Exported {len(export_data)} to {filepath}")
    
    def start_auto_update(self, interval_seconds: float = 2.0):
        """Start background auto-update thread"""
        if not self.is_connected():
            print("[BridgeName] ✗ Not connected, auto-update disabled")
            return
        
        def _update_loop():
            while True:
                try:
                    self.update_mappings()
                    time.sleep(interval_seconds)
                except Exception as e:
                    print(f"[BridgeName] Auto-update error: {e}")
                    time.sleep(interval_seconds * 2)
        
        thread = threading.Thread(target=_update_loop, daemon=True)
        thread.start()
        print(f"[BridgeName] ✓ Auto-update started ({interval_seconds}s)")
    
    def __del__(self):
        """Cleanup"""
        try:
            if self.p_shm:
                self.kernel32.UnmapViewOfFile(self.p_shm)
            if self.h_map:
                self.kernel32.CloseHandle(self.h_map)
        except:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    print("Testing BridgeNameLookup (non-blocking)...")
    bridge = BridgeNameLookup()
    
    if bridge.is_connected():
        print("✓ Bridge connected!")
        bridge.update_mappings(force=True)
        
        all_npcs = bridge.get_all_mappings()
        print(f"Total NPCs: {len(all_npcs)}")
        
        for i, (sid, name) in enumerate(sorted(all_npcs.items())[:5]):
            print(f"  [{i+1}] SID:{sid} = {name}")
    else:
        print("✗ Bridge not available (DLL not loaded or game not running)")
        print("This is OK - script will work without live names")