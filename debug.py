from gw2x_arcdps_bridge import get_bridge
import time

b = get_bridge()
b.connect()
time.sleep(5)  # walk around a bit

all_data = b.get_all()
print(f"Bridge has {len(all_data)} entries")
for inst_id, (name, def_id) in list(all_data.items())[:15]:
    print(f"  bridgeId={inst_id}   defId={def_id}   name={name}")