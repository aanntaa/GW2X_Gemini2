import time
import gw2x_combat_bridge as b

print("=== GW2X COMBAT IPC DIAGNOSTIC ===")
print("diagnostics:", b.diagnostics())

if not b.ready():
    raise SystemExit("IPC is not ready.")

for dik, name in [(0x02, "SKILL_1"), (0x2E, "SKILL_8"), (0x2C, "SKILL_10")]:
    before = b.hook_calls()
    print(f"\n{name}: DIK 0x{dik:02X}")
    print("hook calls before:", before)

    ok = b.tap(dik, 0.05)

    after = b.hook_calls()
    print("hook calls after :", after)
    print("delta            :", after - before)
    print("observed DOWN    :", ok)

    time.sleep(0.5)
