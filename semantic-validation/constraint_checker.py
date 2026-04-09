"""
semantic/constraint_checker.py

Constraint Checking — are values in valid ranges and logically sensible?

Checks:
  - alpha is in [0.0, 1.0]
  - mission from != to  (no self-loop)
  - geofence polygon has >= 3 points
  - route has >= 2 stops
  - hub connects >= 2 nodes
  - reduce_speed modifier is in (0, 1] (you can't reduce speed by more than 100%)
  - increase_cost modifier is >= 1.0 (increase means >= 1x)
  - node has at least one allowed mode (otherwise unreachable)
  - schedule_windows don't overlap and end > start
  - improvement is in (0, 1] if present
"""

import re
from .base import BaseChecker

_TIME_RE = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')


def _time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' to integer minutes since midnight."""
    m = _TIME_RE.match(str(t))
    if not m:
        return -1
    return int(m.group(1)) * 60 + int(m.group(2))


class ConstraintChecker(BaseChecker):

    NAME = "ConstraintChecker"

    def run(self):
        self._check_mission_alpha()
        self._check_mission_self_loop()
        self._check_mission_improvement()
        self._check_geofence_polygon()
        self._check_geofence_modifiers()
        self._check_route_min_stops()
        self._check_hub_min_connects()
        self._check_node_reachability()
        self._check_schedule_windows()

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_mission_alpha(self):
        """Alpha must be in [0.0, 1.0]."""
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m
            alpha = self._get(props, 'alpha')
            if alpha is None:
                continue
            try:
                a = float(alpha)
                if not (0.0 <= a <= 1.0):
                    self.error(
                        f"Mission '{m_id}'.alpha={a} is out of range. "
                        f"Must be between 0.0 (cost-only) and 1.0 (time-only)."
                    )
            except (ValueError, TypeError):
                pass  # TypeChecker already reported this

    def _check_mission_self_loop(self):
        """Mission from and to must be different nodes."""
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m
            frm = str(self._get(props, 'from') or '')
            to  = str(self._get(props, 'to')   or '')
            if frm and to and frm == to:
                self.error(
                    f"Mission '{m_id}' has the same from and to node "
                    f"'{frm}'. A mission must travel between two different nodes."
                )

    def _check_mission_improvement(self):
        """improvement target must be in (0.0, 1.0] if present."""
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m
            imp = self._get(props, 'improvement')
            if imp is None:
                continue
            try:
                v = float(imp)
                if not (0.0 < v <= 1.0):
                    self.error(
                        f"Mission '{m_id}'.improvement={v} is out of range. "
                        f"Must be in (0.0, 1.0] — "
                        f"e.g. 0.2 means 20% improvement target."
                    )
            except (ValueError, TypeError):
                pass  # TypeChecker handles this

    def _check_geofence_polygon(self):
        """A geofence needs at least 3 points to form a closed polygon."""
        for g_id, g in self.ctx.geofences.items():
            bounds = self._get(g, 'bounds') or []
            if len(bounds) < 3:
                self.error(
                    f"Geofence '{g_id}' has only {len(bounds)} bound point(s). "
                    f"A polygon needs at least 3 points."
                )

    def _check_geofence_modifiers(self):
        """
        reduce_speed values should be in (0, 1) — they're multipliers that
        *reduce* speed, so > 1 would increase it (use increase_speed for that).
        increase_cost values should be > 1 — < 1 would reduce cost.
        """
        for g_id, g in self.ctx.geofences.items():
            rules = self._get(g, 'rules') or {}

            for mode, val in (rules.get('reduce_speed') or {}).items():
                try:
                    v = float(val)
                    if not (0.0 < v < 1.0):
                        self.error(
                            f"Geofence '{g_id}' reduce_speed[{mode}]={v} "
                            f"should be in (0.0, 1.0). "
                            f"It's a multiplier: 0.5 = half speed."
                        )
                except (ValueError, TypeError):
                    pass

            for mode, val in (rules.get('increase_speed') or {}).items():
                try:
                    v = float(val)
                    if v <= 1.0:
                        self.warning(
                            f"Geofence '{g_id}' increase_speed[{mode}]={v} "
                            f"is <= 1.0 and won't actually increase speed. "
                            f"Did you mean reduce_speed?"
                        )
                except (ValueError, TypeError):
                    pass

            for mode, val in (rules.get('increase_cost') or {}).items():
                try:
                    v = float(val)
                    if v < 1.0:
                        self.warning(
                            f"Geofence '{g_id}' increase_cost[{mode}]={v} "
                            f"is < 1.0 and will actually reduce cost. "
                            f"Did you mean reduce_cost?"
                        )
                except (ValueError, TypeError):
                    pass

            for mode, val in (rules.get('reduce_cost') or {}).items():
                try:
                    v = float(val)
                    if not (0.0 < v < 1.0):
                        self.error(
                            f"Geofence '{g_id}' reduce_cost[{mode}]={v} "
                            f"should be in (0.0, 1.0). "
                            f"It's a multiplier: 0.5 = half cost."
                        )
                except (ValueError, TypeError):
                    pass

    def _check_route_min_stops(self):
        """A route must have at least 2 stops to be traversable."""
        for r_id, r in self.ctx.routes.items():
            stops = self._get(r, 'stops') or []
            if len(stops) < 2:
                self.error(
                    f"Route '{r_id}' has only {len(stops)} stop(s). "
                    f"A route needs at least 2 stops."
                )

    def _check_hub_min_connects(self):
        """A hub must connect at least 2 nodes — otherwise it's pointless."""
        hubs = getattr(self.ctx, 'hubs', {}) or {}
        for h_id, h in hubs.items():
            connects = self._get(h, 'connects') or []
            if len(connects) < 2:
                self.warning(
                    f"Hub '{h_id}' connects only {len(connects)} node(s). "
                    f"A hub should connect at least 2 nodes to be useful."
                )

    def _check_node_reachability(self):
        """
        A node with no allowed modes can never be visited.
        This is a warning, not an error — it might be intentional
        (e.g. a placeholder node).
        """
        for n_id, n in self.ctx.nodes.items():
            allows = self._get(n, 'allows') or []
            if not allows:
                self.warning(
                    f"Node '{n_id}' has no allowed modes and will be "
                    f"unreachable by any transport."
                )

    def _check_schedule_windows(self):
        """
        Schedule windows must have end > start and must not overlap.
        Format: ['HH:MM-HH:MM', ...]
        """
        for n_id, n in self.ctx.nodes.items():
            windows = self._get(n, 'schedule_windows') or []
            parsed = []

            for i, w in enumerate(windows):
                # windows come in as tuples (start, end) from transformer
                if isinstance(w, (list, tuple)) and len(w) == 2:
                    start_str, end_str = str(w[0]), str(w[1])
                else:
                    # Try parsing string format "HH:MM-HH:MM"
                    parts = str(w).split('-')
                    if len(parts) != 2:
                        self.error(
                            f"Node '{n_id}' schedule_windows[{i}]='{w}' "
                            f"is not a valid window (expected HH:MM-HH:MM)."
                        )
                        continue
                    start_str, end_str = parts[0].strip(), parts[1].strip()

                start_m = _time_to_minutes(start_str)
                end_m   = _time_to_minutes(end_str)

                if start_m < 0:
                    self.error(
                        f"Node '{n_id}' schedule_windows[{i}] "
                        f"start='{start_str}' is not a valid time."
                    )
                    continue
                if end_m < 0:
                    self.error(
                        f"Node '{n_id}' schedule_windows[{i}] "
                        f"end='{end_str}' is not a valid time."
                    )
                    continue
                if end_m <= start_m:
                    self.error(
                        f"Node '{n_id}' schedule_windows[{i}]: "
                        f"end '{end_str}' must be after start '{start_str}'."
                    )
                    continue

                parsed.append((start_m, end_m, i))

            # Check for overlaps
            parsed.sort()
            for j in range(len(parsed) - 1):
                a_start, a_end, a_idx = parsed[j]
                b_start, b_end, b_idx = parsed[j + 1]
                if b_start < a_end:
                    self.error(
                        f"Node '{n_id}' schedule_windows[{a_idx}] and "
                        f"schedule_windows[{b_idx}] overlap."
                    )
