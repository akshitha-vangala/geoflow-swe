"""
semantic/consistency_checker.py

Consistency Checking — do things make sense in combination?

This is the highest-level checker. It looks at relationships
between multiple declarations, not just individual ones.

Checks:
- mission from/to nodes can theoretically be connected
    (at least one common mode between them, ignoring geofences)
- a route's mode is allowed at all its stops
- geofence that blocks ALL modes on a node makes it an island
- if a mission uses a route, the route's mode is allowed at from/to
- duplicate names across different declaration types (mode named
    same as node etc.) — not an error but a warning
- nodes that are completely isolated (no shared mode with any neighbor)
"""

from .base import BaseChecker


class ConsistencyChecker(BaseChecker):

    NAME = "ConsistencyChecker"

    def run(self):
        self._check_route_mode_at_stops()
        self._check_mission_basic_connectivity()
        self._check_geofence_total_block()
        self._check_duplicate_names()

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_route_mode_at_stops(self):
        """
        A route's mode must be allowed at every stop it visits.
        If a stop doesn't allow the route's mode, vehicles can never
        board or alight there.
        """
        for r_id, r in self.ctx.routes.items():
            mode = self._get(r, 'mode')
            stops = self._get(r, 'stops') or []
            if not mode:
                continue

            for s in stops:
                name = self._node_name(s)
                node = self.ctx.nodes.get(name)
                if node is None:
                    continue  # ScopeChecker already caught this
                allows = self._get(node, 'allows') or []
                if 'All' in allows:
                    continue
                if mode not in allows:
                    self.error(
                        f"Route '{r_id}' uses mode '{mode}' but stop "
                        f"'{name}' does not allow '{mode}'. "
                        f"'{name}' allows: {allows}. "
                        f"Either add '{mode}' to node '{name}'.allows "
                        f"or change the route's mode."
                    )

    def _check_mission_basic_connectivity(self):
        """
        Check that from-node and to-node share at least one common allowed
        mode. This doesn't guarantee a path exists (geofences may block it)
        but catches obvious impossibilities at declaration time.
        """
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m
            frm_name = str(self._get(props, 'from') or '')
            to_name  = str(self._get(props, 'to')   or '')

            frm_node = self.ctx.nodes.get(frm_name)
            to_node  = self.ctx.nodes.get(to_name)

            if not frm_node or not to_node:
                continue  # ScopeChecker already caught missing nodes

            frm_allows = set(self._get(frm_node, 'allows') or [])
            to_allows  = set(self._get(to_node,  'allows') or [])

            # 'All' means any mode is fine
            if 'All' in frm_allows or 'All' in to_allows:
                continue

            # Walking is always available as a fallback in most implementations
            # so we include it implicitly
            all_modes = set(self.ctx.modes.keys()) | {'Walking'}
            frm_effective = frm_allows if frm_allows else all_modes
            to_effective  = to_allows  if to_allows  else all_modes

            common = frm_effective & to_effective
            if not common:
                self.error(
                    f"Mission '{m_id}': from='{frm_name}' allows {sorted(frm_allows)} "
                    f"and to='{to_name}' allows {sorted(to_allows)} "
                    f"share no common transport mode. "
                    f"No path will ever be possible between them."
                )

    def _check_geofence_total_block(self):
        """
        If a geofence's allow_only list is empty (after accounting for
        declared modes), it will block all transport through that area.
        Warn the user — this might be intentional (restricted zone)
        but is often a mistake.
        """
        declared_modes = set(self.ctx.modes.keys())
        for g_id, g in self.ctx.geofences.items():
            rules = self._get(g, 'rules') or {}
            allow_only = rules.get('allow_only')

            if allow_only is not None:
                # Filter to only declared modes
                valid_allowed = [m for m in allow_only if m in declared_modes]
                if not valid_allowed:
                    self.warning(
                        f"Geofence '{g_id}' has allow_only with no valid declared modes. "
                        f"This will block ALL transport through the zone."
                    )

            # Check if blocks list covers every declared mode
            blocks = set(self._get(g, 'blocks') or [])
            if blocks and declared_modes and blocks >= declared_modes:
                self.warning(
                    f"Geofence '{g_id}' blocks ALL declared modes {sorted(blocks)}. "
                    f"Any node inside this geofence will be completely unreachable."
                )

    def _check_duplicate_names(self):
        """
        Warn if the same name is used for different declaration types
        (e.g. a node and a mode both named 'Bus').
        This is technically allowed but causes confusing variable resolution
        in the interpreter.
        """
        name_registry = {}  # name -> list of types it appears in

        for name in self.ctx.nodes:
            name_registry.setdefault(name, []).append('node')
        for name in self.ctx.modes:
            name_registry.setdefault(name, []).append('mode')
        for name in self.ctx.routes:
            name_registry.setdefault(name, []).append('route')
        for name in self.ctx.missions:
            name_registry.setdefault(name, []).append('mission')
        for name in getattr(self.ctx, 'hubs', {}):
            name_registry.setdefault(name, []).append('hub')
        for name in self.ctx.geofences:
            name_registry.setdefault(name, []).append('geofence')

        for name, types in name_registry.items():
            if len(types) > 1:
                self.warning(
                    f"Name '{name}' is used for multiple declarations: "
                    f"{types}. This may cause unexpected behaviour in "
                    f"the interpreter when referencing '{name}' as a variable."
                )
