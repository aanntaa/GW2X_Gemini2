"""Read-only name enrichment for remote commander and event records.

This module never creates, removes, or reclassifies a commander and never
changes teleport coordinates.  Detection stays in the packet registries;
nearby entities and official event metadata are optional name sources only.
"""

import math


class CommanderNameResolver:
    """Attach a stable local player name to an already-proven commander."""

    def __init__(self):
        self._cache = {}

    @staticmethod
    def _scope(point):
        keys = sorted((
            int(point.get("key_a", 0) or 0),
            int(point.get("key_b", 0) or 0),
        ))
        return (
            int(point.get("map_id", 0) or 0),
            int(point.get("map_epoch", 0) or 0),
            int(point.get("logical_id", 0) or 0),
            int(point.get("icon_code", 0) or 0),
            keys[0],
            keys[1],
        )

    def decorate(self, points, entities, max_distance=2.0):
        players = [
            entity for entity in (entities or [])
            if int(entity.get("type", -1)) == 0
            and not bool(entity.get("is_local_player"))
        ]
        active_scopes = {self._scope(point) for point in points}
        if active_scopes:
            map_scope = next(iter(active_scopes))[:2]
            self._cache = {
                key: value for key, value in self._cache.items()
                if key[:2] == map_scope
            }

        limit2 = float(max_distance) ** 2
        for point in points:
            scope = self._scope(point)
            cached = self._cache.get(scope)
            if cached:
                point["live_name"] = cached
                point["name_source"] = "Stable commander-name cache"
                continue

            px, py, pz = map(float, point.get("world", (0.0, 0.0, 0.0)))
            matches = []
            for player in players:
                distance2 = (
                    (px - float(player.get("x", 0.0))) ** 2
                    + (py - float(player.get("y", 0.0))) ** 2
                    + (pz - float(player.get("z", 0.0))) ** 2
                )
                if distance2 <= limit2:
                    matches.append((distance2, player))

            # Name enrichment is deliberately conservative. A crowd produces
            # no name instead of selecting the nearest player.
            if len(matches) != 1:
                if len(matches) > 1:
                    point["name_ambiguous"] = True
                continue
            distance2, player = matches[0]
            name = str(player.get("real_name", "") or "").strip()
            if not name or name.casefold() in {"unknown", "unnamed"}:
                continue
            self._cache[scope] = name
            point["live_name"] = name
            point["name_source"] = "Unique local player at proven commander XYZ"
            point["name_match_distance_m"] = math.sqrt(distance2)
            print(
                f"[CommanderName65] BIND logical=0x{scope[2]:X} "
                f"name={name!r} error={math.sqrt(distance2):.3f}m"
            )
        return points


class EventNameResolver:
    """Name map records from live event IDs plus official event metadata."""

    def __init__(self, spatial_resolver):
        self._spatial_resolver = spatial_resolver

    def decorate(self, points, map_id, live_events):
        active_guids = {
            str(event.get("guid", "")).upper()
            for event in (live_events or [])
            if event.get("likely_active") and event.get("guid")
        }
        self._spatial_resolver.decorate(points, map_id, active_guids)
        for point in points:
            if point.get("event_name"):
                point["event_name_confidence"] = "active-guid-and-area"
                point["event_name_source"] = (
                    "Live event GUID + official event area + map record"
                )
            elif point.get("possible_event_name"):
                point["event_name_confidence"] = "area-only"
                point["event_name_source"] = "Official event area only"
        return points


def resolve_commander_names(points, entities, resolver=None):
    """Public helper for name-only commander enrichment."""
    resolver = resolver or CommanderNameResolver()
    return resolver.decorate(points, entities)


def resolve_event_names(points, map_id, live_events, spatial_resolver):
    """Public helper for event-name enrichment with explicit confidence."""
    return EventNameResolver(spatial_resolver).decorate(
        points, map_id, live_events
    )
