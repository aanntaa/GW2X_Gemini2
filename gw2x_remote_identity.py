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
        # Renderer keys, icon codes, and the synthetic nearby-row ID all
        # change at the live-entity boundary.  The real agent ID does not.
        # Keep a second, map-incarnation-scoped identity ledger so an exact
        # proof can follow that agent across nearby/remote representations.
        self._agent_cache = {}
        self._active_map_scope = None
        self._last_map_scopes = frozenset()
        self._last_summary = None

    @staticmethod
    def _valid_player_name(entity):
        return (
            str(entity.get("real_name", "") or "").strip().casefold()
            not in {"", "unknown", "unnamed"}
        )

    @staticmethod
    def _remember(name, source, player=None, distance=None):
        value = {
            "name": str(name),
            "source": str(source),
        }
        if player is not None:
            value["live_agent_id"] = int(player.get("id", 0) or 0)
            value["player_commander_flag"] = bool(
                player.get("is_commander"))
        if distance is not None:
            value["distance_m"] = float(distance)
        return value

    @staticmethod
    def _apply_cached(point, cached):
        # Accept V99's string-only cache if a resolver survives a hot reload.
        if not isinstance(cached, dict):
            point["live_name"] = str(cached)
            point["name_source"] = "Stable commander-name cache"
            return
        point["live_name"] = cached["name"]
        point["name_source"] = cached["source"]
        if cached.get("live_agent_id"):
            point["live_agent_id"] = cached["live_agent_id"]
        if "player_commander_flag" in cached:
            point["name_player_commander_flag"] = cached[
                "player_commander_flag"
            ]
        if "distance_m" in cached:
            point["name_match_distance_m"] = cached["distance_m"]

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

    @staticmethod
    def _agent_scope(map_id, map_epoch, agent_id):
        return (int(map_id or 0), int(map_epoch or 0), int(agent_id or 0))

    def set_active_map_scope(self, map_id, map_epoch):
        """Invalidate identity proof when the map incarnation changes."""
        scope = (int(map_id or 0), int(map_epoch or 0))
        if scope == self._active_map_scope:
            return
        self._active_map_scope = scope
        self._cache = {
            key: value for key, value in self._cache.items()
            if key[:2] == scope
        }
        self._agent_cache = {
            key: value for key, value in self._agent_cache.items()
            if key[:2] == scope
        }
        self._last_map_scopes = frozenset({scope}) if any(scope) else frozenset()
        self._last_summary = None

    def remember_agent_identity(self, map_id, map_epoch, agent_id, name,
                                source, player=None,
                                active_receipt_name=None):
        """Remember an exact agent/name proof, independent of renderer keys."""
        agent_scope = self._agent_scope(map_id, map_epoch, agent_id)
        clean_name = str(name or "").strip()
        if agent_scope[2] <= 0 or not clean_name:
            return None
        value = self._remember(clean_name, source, player)
        previous = self._agent_cache.get(agent_scope)
        if isinstance(previous, dict):
            # Once a lifecycle receipt is attached, keep its active-state
            # marker even if an exact live-ID observation refreshes the row.
            if previous.get("active_receipt_name"):
                value["active_receipt_name"] = previous[
                    "active_receipt_name"
                ]
        if active_receipt_name:
            value["active_receipt_name"] = str(
                active_receipt_name).strip().casefold()
            value["source"] = (
                "Lifecycle receipt bound to exact live agent identity"
            )
        self._agent_cache[agent_scope] = value
        if (not isinstance(previous, dict) or
                str(previous.get("name", "")).casefold() !=
                clean_name.casefold()):
            print(
                f"[CommanderIdentity103] LEARN agent=0x{agent_scope[2]:X} "
                f"name={clean_name!r} source={value['source']!r} "
                f"map={agent_scope[0]} epoch={agent_scope[1]}"
            )
        return value

    def lookup_agent_identity(self, map_id, map_epoch, agent_id):
        value = self._agent_cache.get(
            self._agent_scope(map_id, map_epoch, agent_id))
        return value if isinstance(value, dict) else None

    def sync_active_receipts(self, map_id, map_epoch, receipt_names):
        """Revoke receipt-backed identities only after the DLL removes them."""
        map_scope = (int(map_id or 0), int(map_epoch or 0))
        active = {
            str(name or "").strip().casefold()
            for name in (receipt_names or []) if str(name or "").strip()
        }
        revoked_agents = set()
        for key, value in list(self._agent_cache.items()):
            if key[:2] != map_scope or not isinstance(value, dict):
                continue
            receipt_name = value.get("active_receipt_name")
            if receipt_name and receipt_name not in active:
                revoked_agents.add(key[2])
                self._agent_cache.pop(key, None)
                print(
                    f"[CommanderIdentity103] REVOKE agent=0x{key[2]:X} "
                    f"name={value.get('name', '')!r} "
                    f"map={key[0]} epoch={key[1]} reason=receipt-removed"
                )
        if revoked_agents:
            self._cache = {
                key: value for key, value in self._cache.items()
                if not (key[:2] == map_scope and isinstance(value, dict) and
                        int(value.get("live_agent_id", 0) or 0) in
                        revoked_agents)
            }

    def observe_proven_agents(self, points, entities):
        """Learn exact remote logical-ID to live agent-ID relationships."""
        players = {}
        ambiguous = set()
        for player in (entities or []):
            if (int(player.get("type", -1)) != 0 or
                    bool(player.get("is_local_player")) or
                    not self._valid_player_name(player)):
                continue
            agent_id = int(player.get("id", 0) or 0)
            if agent_id <= 0 or agent_id in ambiguous:
                continue
            prior = players.get(agent_id)
            if prior is None:
                players[agent_id] = player
                continue
            prior_name = str(prior.get("real_name", "") or "").strip()
            name = str(player.get("real_name", "") or "").strip()
            if prior_name.casefold() != name.casefold():
                players.pop(agent_id, None)
                ambiguous.add(agent_id)

        for point in (points or []):
            if bool(point.get("local_only")):
                continue
            logical_id = int(point.get("logical_id", 0) or 0)
            if logical_id <= 0 or (logical_id & 0x80000000):
                continue
            map_id = int(point.get("map_id", 0) or 0)
            map_epoch = int(point.get("map_epoch", 0) or 0)
            self.set_active_map_scope(map_id, map_epoch)
            player = players.get(logical_id)
            if player is not None:
                self.remember_agent_identity(
                    map_id, map_epoch, logical_id,
                    str(player.get("real_name", "") or "").strip(),
                    "Exact live agent ID matches proven remote logical ID",
                    player,
                )
            exported_name = str(point.get("live_name", "") or "").strip()
            if (exported_name and point.get("name_source") ==
                    "Lifecycle key/name receipt"):
                self.remember_agent_identity(
                    map_id, map_epoch, logical_id, exported_name,
                    "Lifecycle key/name receipt",
                    active_receipt_name=exported_name,
                )

    def decorate(self, points, entities, max_distance=8.0):
        named_players = [
            entity for entity in (entities or [])
            if int(entity.get("type", -1)) == 0
            and not bool(entity.get("is_local_player"))
            and self._valid_player_name(entity)
        ]
        tagged_players = [
            entity for entity in named_players
            if bool(entity.get("is_commander"))
        ]

        # An independently proven remote commander uses the same logical ID
        # as the live entity extractor's agent ID.  Index all named players,
        # not only entities whose unreliable commander flag happens to be set.
        # Conflicting duplicate IDs are deliberately left unresolved.
        players_by_agent_id = {}
        ambiguous_agent_ids = set()
        for player in named_players:
            agent_id = int(player.get("id", 0) or 0)
            if agent_id <= 0 or agent_id in ambiguous_agent_ids:
                continue
            previous = players_by_agent_id.get(agent_id)
            if previous is None:
                players_by_agent_id[agent_id] = player
                continue
            previous_name = str(previous.get("real_name", "") or "").strip()
            player_name = str(player.get("real_name", "") or "").strip()
            if previous_name.casefold() != player_name.casefold():
                players_by_agent_id.pop(agent_id, None)
                ambiguous_agent_ids.add(agent_id)
            elif (bool(player.get("is_commander")) and
                    not bool(previous.get("is_commander"))):
                players_by_agent_id[agent_id] = player

        if points:
            self.set_active_map_scope(
                int(points[0].get("map_id", 0) or 0),
                int(points[0].get("map_epoch", 0) or 0),
            )
        self.observe_proven_agents(points, named_players)

        active_scopes = {self._scope(point) for point in points}
        active_map_scopes = frozenset(scope[:2] for scope in active_scopes)
        if active_map_scopes != self._last_map_scopes:
            self._last_map_scopes = active_map_scopes
            self._last_summary = None
        if active_map_scopes:
            self._cache = {
                key: value for key, value in self._cache.items()
                if key[:2] in active_map_scopes
            }

        limit2 = float(max_distance) ** 2
        unresolved = []
        for point in points:
            scope = self._scope(point)
            exported_name = str(point.get("live_name", "") or "").strip()
            if (exported_name and point.get("name_source") ==
                    "Lifecycle key/name receipt"):
                # The DLL correlated this name with the exact lifecycle key.
                # Preserve it over every Python-side fallback.
                self._cache[scope] = self._remember(
                    exported_name, "Lifecycle key/name receipt")
                logical_id = int(point.get("logical_id", 0) or 0)
                if logical_id > 0 and not (logical_id & 0x80000000):
                    self.remember_agent_identity(
                        scope[0], scope[1], logical_id, exported_name,
                        "Lifecycle key/name receipt",
                        active_receipt_name=exported_name,
                    )
                continue

            logical_id = int(point.get("logical_id", 0) or 0)
            agent_id = int(point.get("live_agent_id", 0) or 0)
            if not agent_id and not bool(point.get("local_only")):
                agent_id = logical_id
            agent_cached = self.lookup_agent_identity(
                scope[0], scope[1], agent_id)
            if agent_cached:
                self._apply_cached(point, agent_cached)
                self._cache[scope] = dict(agent_cached)
                continue

            cached = self._cache.get(scope)
            if (isinstance(cached, dict) and cached.get("source") in {
                    "Lifecycle key/name receipt",
                    "Exact live agent ID matches proven remote logical ID",
            }):
                self._apply_cached(point, cached)
                continue

            exact_player = None
            if (logical_id > 0
                    and not bool(point.get("local_only"))
                    and not (logical_id & 0x80000000)):
                exact_player = players_by_agent_id.get(logical_id)
            if exact_player is not None:
                name = str(exact_player.get("real_name", "") or "").strip()
                source = "Exact live agent ID matches proven remote logical ID"
                cached = self._remember(name, source, exact_player)
                self._cache[scope] = cached
                self.remember_agent_identity(
                    scope[0], scope[1], logical_id, name, source,
                    exact_player,
                )
                self._apply_cached(point, cached)
                print(
                    f"[CommanderName100] ID-BIND logical=0x{logical_id:X} "
                    f"agent={int(exact_player.get('id', 0) or 0)} "
                    f"name={name!r} "
                    f"tagged={int(bool(exact_player.get('is_commander')))}"
                )
                continue

            if cached:
                self._apply_cached(point, cached)
                continue
            unresolved.append((point, scope))

        # Match the whole commander set at once. V65 required exactly one
        # player inside 2 m for each row, so two nearby commanders could make
        # both rows ambiguous or leave one unnamed. A one-to-one assignment
        # allows both names while still preventing one player from naming two
        # remote packet points. Only an entity whose commander flag is set may
        # name a commander point. Coordinate proximity alone previously bound
        # nearby untagged players such as Haas Unica to an object collision.
        candidates = []
        for point_index, (point, _scope) in enumerate(unresolved):
            px, py, pz = map(float, point.get("world", (0.0, 0.0, 0.0)))
            for player_index, player in enumerate(tagged_players):
                distance2 = (
                    (px - float(player.get("x", 0.0))) ** 2
                    + (py - float(player.get("y", 0.0))) ** 2
                    + (pz - float(player.get("z", 0.0))) ** 2
                )
                if distance2 <= limit2:
                    candidates.append((distance2, point_index, player_index))

        used_points = set()
        used_players = set()
        for distance2, point_index, player_index in sorted(candidates):
            if point_index in used_points or player_index in used_players:
                continue
            point, scope = unresolved[point_index]
            player = tagged_players[player_index]
            name = str(player.get("real_name", "") or "").strip()
            distance = math.sqrt(distance2)
            source = "One-to-one nearby tagged commander at commander XYZ"
            cached = self._remember(
                name, source, player, distance
            )
            self._cache[scope] = cached
            self._apply_cached(point, cached)
            used_points.add(point_index)
            used_players.add(player_index)
            print(
                f"[CommanderName100] XYZ-BIND logical=0x{scope[2]:X} "
                f"name={name!r} error={distance:.3f}m "
                f"tagged={int(bool(player.get('is_commander')))}"
            )
        if unresolved:
            summary = (
                tuple(sorted(scope[2] for _point, scope in unresolved)),
                len(named_players),
                len(tagged_players),
                len(candidates),
                len(used_points),
                tuple(sorted(ambiguous_agent_ids)),
            )
            if summary != self._last_summary:
                print(
                    f"[CommanderName100] SUMMARY "
                    f"remote={len(unresolved)} "
                    f"named_players={len(named_players)} "
                    f"tagged_players={len(tagged_players)} "
                    f"candidates={len(candidates)} "
                    f"bound={len(used_points)} "
                    f"ambiguous_ids={len(ambiguous_agent_ids)} "
                    f"radius={float(max_distance):.1f}m"
                )
                self._last_summary = summary
        else:
            self._last_summary = None
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
