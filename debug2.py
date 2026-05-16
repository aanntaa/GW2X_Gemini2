from gw2x_core import SharedEntityData
ipc = SharedEntityData()
entities = ipc.read_entities()
for e in entities[:5]:
    print(f"  agentId={e['id']}   name={e['real_name']}")
