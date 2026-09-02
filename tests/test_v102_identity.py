import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_resolver():
    path = ROOT / "GW2X" / "gw2x_remote_identity.py"
    spec = importlib.util.spec_from_file_location("v102_identity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CommanderNameResolver


def load_append_method():
    path = ROOT / "GW2X" / "gw2x_logic.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    method = next(
        item
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GW2X_Logic"
        for item in node.body
        if isinstance(item, ast.FunctionDef)
        and item.name == "_append_nearby_commanders"
    )
    namespace = {}
    ast.fix_missing_locations(method)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"),
         namespace)
    return namespace["_append_nearby_commanders"]


def player(agent_id=0xBFF, name="Lan Yunzu"):
    return {
        "type": 0,
        "id": agent_id,
        "real_name": name,
        "is_local_player": False,
        "is_commander": False,
        "x": 10.0,
        "y": 20.0,
        "z": 30.0,
    }


def remote(agent_id=0xBFF, key_a=0x96, key_b=0x92, icon=0x4A4,
           epoch=1):
    return {
        "logical_id": agent_id,
        "key_a": key_a,
        "key_b": key_b,
        "icon_code": icon,
        "flags": 3,
        "world": (100.0, 200.0, 300.0),
        "map_id": 988,
        "map_epoch": epoch,
    }


def receipt(name="Lan Yunzu"):
    return {"live_name": name, "flags": 17}


class FakeLogic:
    _append_nearby_commanders = load_append_method()

    def __init__(self, resolver):
        self.commander_names = resolver
        self._logged_lifecycle_live_receipts = set()


def test_exact_remote_identity_survives_renderer_key_and_icon_change():
    Resolver = load_resolver()
    resolver = Resolver()
    resolver.decorate([remote()], [player()])

    changed = remote(key_a=0x86, key_b=0x71, icon=0)
    resolver.decorate([changed], [])

    assert changed["live_name"] == "Lan Yunzu"
    assert changed["live_agent_id"] == 0xBFF


def test_remote_to_live_to_remote_is_one_canonical_agent():
    Resolver = load_resolver()
    resolver = Resolver()
    logic = FakeLogic(resolver)
    result = {
        "map_id": 988,
        "map_epoch": 1,
        "name_receipts": [receipt()],
    }

    nearby = logic._append_nearby_commanders(
        [remote()], result, [player()])
    assert len(nearby) == 1
    assert nearby[0]["local_only"] is True
    assert nearby[0]["live_agent_id"] == 0xBFF
    assert nearby[0]["live_name"] == "Lan Yunzu"

    outside = remote(key_a=0x86, key_b=0x71, icon=0)
    resolver.decorate([outside], [])
    assert outside["live_name"] == "Lan Yunzu"


def test_proven_agent_keeps_nearby_detection_when_remote_row_is_suppressed():
    Resolver = load_resolver()
    resolver = Resolver()
    logic = FakeLogic(resolver)
    base = {"map_id": 988, "map_epoch": 1, "name_receipts": []}

    logic._append_nearby_commanders([remote()], base, [player()])
    nearby_only = logic._append_nearby_commanders([], base, [player()])

    assert len(nearby_only) == 1
    assert nearby_only[0]["local_only"] is True
    assert nearby_only[0]["live_agent_id"] == 0xBFF


def test_receipt_remove_revokes_receipt_backed_identity():
    Resolver = load_resolver()
    resolver = Resolver()
    logic = FakeLogic(resolver)
    active = {
        "map_id": 988,
        "map_epoch": 1,
        "name_receipts": [receipt()],
    }
    removed = {"map_id": 988, "map_epoch": 1, "name_receipts": []}

    first = logic._append_nearby_commanders([], active, [player()])
    assert len(first) == 1
    second = logic._append_nearby_commanders([], removed, [player()])
    assert second == []


def test_map_epoch_change_invalidates_canonical_agent_identity():
    Resolver = load_resolver()
    resolver = Resolver()
    logic = FakeLogic(resolver)
    old = {"map_id": 988, "map_epoch": 1, "name_receipts": []}
    new = {"map_id": 988, "map_epoch": 2, "name_receipts": []}

    logic._append_nearby_commanders([remote()], old, [player()])
    assert logic._append_nearby_commanders([], new, [player()]) == []


def test_cpp_receipts_are_remove_scoped_not_time_scoped():
    text = (ROOT / "KX-Vision" / "src" / "Hooking" /
            "RemoteMapPacketTracker.cpp").read_text(encoding="utf-8")
    assert "COMMANDER_NAME_TTL_MS" not in text
    assert "ForgetCommanderNamesForKeyLocked(key);" in text
    assert "s_commanderNames.data()" in text

