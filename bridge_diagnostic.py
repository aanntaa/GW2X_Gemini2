"""
GW2X Bridge Diagnostic Tool v2 - ENHANCED
==========================================
Tests bridge data AND verifies address matching with C++ side

Run this WHILE IN-GAME and looking at objects
"""

import ctypes
import struct
import time
import sys

# Bridge constants
BRIDGE_SHM_NAME = "GW2X_AGENT_BRIDGE"
BRIDGE_VERSION = 5
BRIDGE_MAX_ENTRIES = 16000

class BridgeEntry(ctypes.Structure):
    _fields_ = [
        ("agentAddr", ctypes.c_uint64),
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

def open_bridge():
    """Open bridge shared memory"""
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    h_map = kernel32.OpenFileMappingA(0x0004, False, BRIDGE_SHM_NAME.encode('ascii'))
    if not h_map:
        return None, None, None
    
    p_shm = kernel32.MapViewOfFile(h_map, 0x0004, 0, 0, 0)
    if not p_shm:
        kernel32.CloseHandle(h_map)
        return None, None, None
    
    shm = ctypes.cast(p_shm, ctypes.POINTER(BridgeSharedMemory)).contents
    
    return kernel32, h_map, shm

def close_bridge(kernel32, h_map, p_shm):
    """Close bridge shared memory"""
    if p_shm:
        kernel32.UnmapViewOfFile(p_shm)
    if h_map:
        kernel32.CloseHandle(h_map)

def main():
    print("=" * 70)
    print("GW2X Bridge Diagnostic Tool v2 - ENHANCED")
    print("=" * 70)
    
    kernel32, h_map, shm = open_bridge()
    
    if not shm:
        print("\n❌ CRITICAL: Bridge shared memory not found!")
        print("\nPossible causes:")
        print("  1. ArcdPS not installed")
        print("  2. arcdps_bridge.dll not in addons folder")
        print("  3. Guild Wars 2 not running")
        print("\nMake sure:")
        print("  - Guild Wars 2 is RUNNING")
        print("  - You see 'GW2X Bridge: 5.1.0' in ArcdPS extensions (Alt+Shift+T)")
        input("\nPress Enter to exit...")
        return
    
    print("\n✓ Bridge shared memory found!")
    print(f"  Version: {shm.version}")
    print(f"  Agent count: {shm.count}")
    
    if shm.version != BRIDGE_VERSION:
        print(f"\n⚠️  WARNING: Version mismatch!")
        print(f"  Expected: {BRIDGE_VERSION}")
        print(f"  Got: {shm.version}")
    
    if shm.count == 0:
        print("\n⚠️  PROBLEM: No agents registered!")
        print("\nThis means ArcdPS tracking callback isn't firing.")
        print("\nTroubleshooting steps:")
        print("  1. Make sure you're IN A MAP (not character select)")
        print("  2. Walk around near NPCs/objects")
        print("  3. Wait 5-10 seconds")
        print("  4. Check ArcdPS extensions shows 'GW2X Bridge: 5.1.0'")
        print("\nIf still 0 after walking around:")
        print("  - Enable diagnostic logging in bridge DLL")
        print("  - Use DebugView to see if tracking events are firing")
        
        close_bridge(kernel32, h_map, ctypes.cast(ctypes.pointer(shm), ctypes.c_void_p).value)
        input("\nPress Enter to exit...")
        return
    
    # Show statistics
    print(f"\n{'='*70}")
    print("BRIDGE DATA ANALYSIS")
    print(f"{'='*70}")
    
    agents_with_defid = 0
    agents_with_name = 0
    agents_with_instid = 0
    
    defid_examples = []
    no_defid_examples = []
    
    for i in range(min(shm.count, BRIDGE_MAX_ENTRIES)):
        entry = shm.entries[i]
        
        if entry.defId != 0:
            agents_with_defid += 1
            if len(defid_examples) < 5:
                name = entry.name.decode('utf-8', errors='ignore').strip('\x00')
                defid_examples.append((entry.agentAddr, entry.defId, name))
        else:
            if len(no_defid_examples) < 3:
                name = entry.name.decode('utf-8', errors='ignore').strip('\x00')
                no_defid_examples.append((entry.agentAddr, name))
        
        if entry.name[0]:
            agents_with_name += 1
        if entry.instId != 0:
            agents_with_instid += 1
    
    print(f"\nStatistics:")
    print(f"  Total agents: {shm.count}")
    print(f"  With defId:   {agents_with_defid} ({100*agents_with_defid//shm.count if shm.count > 0 else 0}%)")
    print(f"  With name:    {agents_with_name} ({100*agents_with_name//shm.count if shm.count > 0 else 0}%)")
    print(f"  With instId:  {agents_with_instid} ({100*agents_with_instid//shm.count if shm.count > 0 else 0}%)")
    
    # Show examples WITH defId
    if defid_examples:
        print(f"\n{'='*70}")
        print("✓ GOOD: Agents WITH static DefID (these should work in C++):")
        print(f"{'='*70}")
        for addr, defid, name in defid_examples:
            print(f"  Addr: 0x{addr:016X}  DefID: {defid:10d}  Name: {name}")
    
    # Show examples WITHOUT defId
    if no_defid_examples:
        print(f"\n{'='*70}")
        print("⚠️  Agents WITHOUT DefID (will show as OBJ:dynamic in C++):")
        print(f"{'='*70}")
        for addr, name in no_defid_examples:
            print(f"  Addr: 0x{addr:016X}  DefID: 0           Name: {name}")
    
    # Critical analysis
    print(f"\n{'='*70}")
    print("DIAGNOSIS:")
    print(f"{'='*70}")
    
    if agents_with_defid == 0:
        print("\n❌ CRITICAL ISSUE: NO agents have DefID!")
        print("\nThis means:")
        print("  - ArcdPS tracking callback IS firing (we have names)")
        print("  - BUT defId extraction is failing")
        print("\nSolution:")
        print("  1. Enable diagnostic logging in arcdps_bridge.cpp:")
        print("     static constexpr bool ENABLE_DIAGNOSTIC_LOGGING = true;")
        print("  2. Recompile and replace DLL")
        print("  3. Use DebugView to see what defIds are being extracted")
        print("  4. Check if src->prof and dst->prof are 0 for all gadgets")
    
    elif agents_with_defid < shm.count * 0.3:
        print("\n⚠️  WARNING: Less than 30% of agents have DefID")
        print("\nThis is EXPECTED for:")
        print("  - Player characters (they don't need static IDs)")
        print("  - Some gadgets with prof=0 (need memory reading)")
        print("\nBut if you're looking at objects and they show 'OBJ:dynamic',")
        print("those objects likely have prof=0 and need C++ memory reading.")
    
    else:
        print("\n✓ LOOKS GOOD: Most agents have DefID")
        print("\nIf C++ still shows 'OBJ:dynamic', the problem is:")
        print("  1. Address mismatch between ArcdPS and C++")
        print("  2. BridgeLookupByAddr not finding matching address")
        print("\nTo debug:")
        print("  1. Look at an object in-game")
        print("  2. Check C++ log: '[BridgeTest] agentAddr=0x...'")
        print("  3. Search for that address in the list above")
        print("  4. If not found → address mismatch problem")
    
    # Show full sample of first 20 entries for manual inspection
    print(f"\n{'='*70}")
    print("FULL SAMPLE (first 20 entries for manual inspection):")
    print(f"{'='*70}")
    print(f"{'Idx':<4} {'Address':<18} {'DefID':<12} {'InstID':<8} {'Name':<30}")
    print("-" * 70)
    
    for i in range(min(20, shm.count)):
        entry = shm.entries[i]
        name = entry.name.decode('utf-8', errors='ignore').strip('\x00')[:30]
        print(f"{i:<4} 0x{entry.agentAddr:016X} {entry.defId:<12} {entry.instId:<8} {name}")
    
    if shm.count > 20:
        print(f"... and {shm.count - 20} more entries")
    
    close_bridge(kernel32, h_map, ctypes.cast(ctypes.pointer(shm), ctypes.c_void_p).value)
    
    print(f"\n{'='*70}")
    print("Diagnostic complete!")
    print(f"{'='*70}")
    print("\nNEXT STEPS:")
    print("  1. Copy ONE address from the list above (e.g., 0x000001234567890A)")
    print("  2. Look at that object in-game")
    print("  3. Check your C++ log for '[BridgeTest] agentAddr=0x...'")
    print("  4. Compare the addresses - do they match?")
    print("\nIf addresses DON'T match:")
    print("  → ArcdPS src->id and C++ AgKeyFramed::data() are different")
    print("  → This is a fundamental architecture mismatch")
    print("\nIf addresses DO match but lookup fails:")
    print("  → BridgeLookupByAddr has a bug")
    print("  → Check the loop iteration and comparison logic")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")