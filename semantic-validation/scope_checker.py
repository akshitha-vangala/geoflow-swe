"""
semantic/scope_checker.py

Scope Checking — do all referenced names actually exist?

Checks:
  - nodes referenced in routes exist
  - nodes referenced in hubs exist
  - nodes referenced in missions (from/to) exist
  - modes referenced in nodes (allows) exist
  - modes referenced in routes exist
  - modes referenced in geofence blocks/rules exist
  - program-block variable references are not checked here
    (that is handled at runtime by the interpreter)
"""

from .base import BaseChecker


class ScopeChecker(BaseChecker):

    NAME = "ScopeChecker"

    def run(self):
        self._check_node_allows()
        self._check_route_nodes()
        self._check_route_modes()
        self._check_hub_nodes()
        self._check_mission_nodes()
        self._check_geofence_modes()

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_node_allows(self):
        """Every mode listed in a node's allows must be declared."""
        declared_modes = set(self.ctx.modes.keys())
        for n_id, n in self.ctx.nodes.items():
            allows = self._get(n, 'allows') or []
            for mode in allows:
                if mode == 'All':
                    continue
                if mode not in declared_modes:
                    self.error(
                        f"Node '{n_id}' allows mode '{mode}' "
                        f"which is not declared. "
                        f"Declared modes: {sorted(declared_modes)}"
                    )

    def _check_route_nodes(self):
        """Every stop in a route must be a declared node."""
        declared_nodes = set(self.ctx.nodes.keys())
        for r_id, r in self.ctx.routes.items():
            stops = self._get(r, 'stops') or []
            for s in stops:
                name = self._node_name(s)
                if name not in declared_nodes:
                    self.error(
                        f"Route '{r_id}' references undeclared node '{name}'."
                    )

    def _check_route_modes(self):
        """Every route's mode must be declared."""
        declared_modes = set(self.ctx.modes.keys())
        for r_id, r in self.ctx.routes.items():
            mode = self._get(r, 'mode')
            if mode and mode not in declared_modes:
                self.error(
                    f"Route '{r_id}' uses undeclared mode '{mode}'. "
                    f"Declared modes: {sorted(declared_modes)}"
                )

    def _check_hub_nodes(self):
        """Every node a hub connects must be declared."""
        declared_nodes = set(self.ctx.nodes.keys())
        hubs = getattr(self.ctx, 'hubs', {}) or {}
        for h_id, h in hubs.items():
            connects = self._get(h, 'connects') or []
            for c in connects:
                name = self._node_name(c)
                if name not in declared_nodes:
                    self.error(
                        f"Hub '{h_id}' connects to undeclared node '{name}'."
                    )

    def _check_mission_nodes(self):
        """Mission from/to must reference declared nodes."""
        declared_nodes = set(self.ctx.nodes.keys())
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m
            for field in ('from', 'to'):
                val = self._get(props, field)
                if val is None:
                    self.error(
                        f"Mission '{m_id}' is missing required field '{field}'."
                    )
                elif str(val) not in declared_nodes:
                    # Try to suggest the closest match
                    suggestion = self._closest(str(val), declared_nodes)
                    hint = f" Did you mean '{suggestion}'?" if suggestion else ""
                    self.error(
                        f"Mission '{m_id}' has {field}='{val}' "
                        f"which is not a declared node.{hint}"
                    )

    def _check_geofence_modes(self):
        """Geofence blocks and allow_only must reference declared modes."""
        declared_modes = set(self.ctx.modes.keys())
        for g_id, g in self.ctx.geofences.items():

            # blocks list
            for mode in (self._get(g, 'blocks') or []):
                if mode not in declared_modes:
                    self.error(
                        f"Geofence '{g_id}' blocks undeclared mode '{mode}'."
                    )

            # rules.allow_only
            rules = self._get(g, 'rules') or {}
            for mode in (rules.get('allow_only') or []):
                if mode not in declared_modes:
                    self.error(
                        f"Geofence '{g_id}' allow_only references "
                        f"undeclared mode '{mode}'."
                    )

            # rules.reduce_speed / increase_cost keys
            for rule_key in ('reduce_speed', 'increase_speed',
                             'reduce_cost',  'increase_cost'):
                modifier = rules.get(rule_key) or {}
                for mode in modifier:
                    if mode not in declared_modes:
                        self.error(
                            f"Geofence '{g_id}' rule '{rule_key}' "
                            f"references undeclared mode '{mode}'."
                        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _closest(name: str, candidates: set) -> str:
        """
        Very simple Levenshtein-free typo suggestion —
        finds the candidate with the most matching characters.
        Good enough for short identifiers.
        """
        name_l = name.lower()
        best, best_score = None, 0
        for c in candidates:
            c_l = c.lower()
            # count shared characters in order
            score = sum(a == b for a, b in zip(name_l, c_l))
            # bonus for same starting letter
            if c_l and name_l and c_l[0] == name_l[0]:
                score += 2
            if score > best_score:
                best, best_score = c, score
        # Only suggest if reasonably similar
        return best if best_score >= max(2, len(name) // 2) else None
