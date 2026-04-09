"""
semantic/type_checker.py

Type Checking — are values the right types for their fields?

Checks:
  - mode properties are numbers (speed, cost, payload_capacity, build_cost)
  - node loc is a coordinate pair of numbers
  - node allows is a list
  - geofence bounds is a list of coordinate pairs
  - geofence activate_at is a valid TIME string
  - mission start_time is a valid TIME string
  - mission alpha is a number
  - mission optimize is a valid identifier ("time" or "cost")
  - route stops is a list
  - modifier values (reduce_speed etc.) are numbers
"""

import re
from .base import BaseChecker

# Valid TIME pattern: HH:MM
_TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')

# Valid optimize values
_OPTIMIZE_VALUES = {'time', 'cost'}


class TypeChecker(BaseChecker):

    NAME = "TypeChecker"

    def run(self):
        self._check_modes()
        self._check_nodes()
        self._check_routes()
        self._check_geofences()
        self._check_missions()

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_modes(self):
        """Mode properties must all be non-negative numbers."""
        numeric_props = ('speed', 'cost', 'payload_capacity', 'build_cost')
        for m_id, m in self.ctx.modes.items():
            for prop in numeric_props:
                val = self._get(m, prop)
                if val is None:
                    continue  # optional props — not required
                if not self._is_number(val):
                    self.error(
                        f"Mode '{m_id}'.{prop} must be a number, "
                        f"got {type(val).__name__} '{val}'."
                    )
                elif float(val) < 0:
                    self.error(
                        f"Mode '{m_id}'.{prop} must be >= 0, got {val}."
                    )

            # speed is required and must be > 0
            speed = self._get(m, 'speed')
            if speed is None:
                self.error(f"Mode '{m_id}' is missing required property 'speed'.")
            elif self._is_number(speed) and float(speed) <= 0:
                self.error(
                    f"Mode '{m_id}'.speed must be > 0 "
                    f"(otherwise travel time is infinite), got {speed}."
                )

    def _check_nodes(self):
        """Node loc must be a 2-tuple of numbers. allows must be a list."""
        for n_id, n in self.ctx.nodes.items():
            # loc
            loc = self._get(n, 'loc')
            if loc is None:
                self.error(f"Node '{n_id}' is missing required property 'loc'.")
            else:
                if not (hasattr(loc, '__len__') and len(loc) == 2):
                    self.error(
                        f"Node '{n_id}'.loc must be a coordinate pair (lat, lon), "
                        f"got '{loc}'."
                    )
                else:
                    lat, lon = loc[0], loc[1]
                    if not self._is_number(lat) or not self._is_number(lon):
                        self.error(
                            f"Node '{n_id}'.loc values must be numbers, "
                            f"got ({lat}, {lon})."
                        )
                    else:
                        # Sanity-check coordinate ranges
                        if not (-90 <= float(lat) <= 90):
                            self.error(
                                f"Node '{n_id}'.loc latitude {lat} is out of "
                                f"range [-90, 90]."
                            )
                        if not (-180 <= float(lon) <= 180):
                            self.error(
                                f"Node '{n_id}'.loc longitude {lon} is out of "
                                f"range [-180, 180]."
                            )

            # allows
            allows = self._get(n, 'allows')
            if allows is not None and not isinstance(allows, (list, tuple)):
                self.error(
                    f"Node '{n_id}'.allows must be a list, "
                    f"got {type(allows).__name__}."
                )

    def _check_routes(self):
        """Route stops must be a list."""
        for r_id, r in self.ctx.routes.items():
            stops = self._get(r, 'stops')
            if stops is None:
                self.error(f"Route '{r_id}' is missing required property 'stops'.")
            elif not isinstance(stops, (list, tuple)):
                self.error(
                    f"Route '{r_id}'.stops must be a list, "
                    f"got {type(stops).__name__}."
                )

    def _check_geofences(self):
        """
        Geofence bounds must be a list of (lat, lon) pairs.
        activate_at must be a valid TIME string.
        Modifier values must be positive numbers.
        """
        for g_id, g in self.ctx.geofences.items():

            # bounds
            bounds = self._get(g, 'bounds') or []
            if not isinstance(bounds, (list, tuple)):
                self.error(
                    f"Geofence '{g_id}'.bounds must be a list of coordinates."
                )
            else:
                for i, pt in enumerate(bounds):
                    if not (hasattr(pt, '__len__') and len(pt) == 2):
                        self.error(
                            f"Geofence '{g_id}'.bounds[{i}] must be a "
                            f"(lat, lon) pair, got '{pt}'."
                        )
                    elif not (self._is_number(pt[0]) and self._is_number(pt[1])):
                        self.error(
                            f"Geofence '{g_id}'.bounds[{i}] contains "
                            f"non-numeric values: {pt}."
                        )

            # activate_at
            activate_at = self._get(g, 'activate_at') or '00:00'
            if not _TIME_RE.match(str(activate_at)):
                self.error(
                    f"Geofence '{g_id}'.activate_at='{activate_at}' "
                    f"is not a valid time (expected HH:MM)."
                )

            # modifier values in rules
            rules = self._get(g, 'rules') or {}
            for rule_key in ('reduce_speed', 'increase_speed',
                             'reduce_cost', 'increase_cost'):
                modifier = rules.get(rule_key) or {}
                for mode, val in modifier.items():
                    if not self._is_number(val):
                        self.error(
                            f"Geofence '{g_id}' rule '{rule_key}[{mode}]' "
                            f"must be a number, got '{val}'."
                        )
                    elif float(val) <= 0:
                        self.error(
                            f"Geofence '{g_id}' rule '{rule_key}[{mode}]' "
                            f"must be > 0, got {val}."
                        )

    def _check_missions(self):
        """
        Mission start_time must be valid TIME.
        alpha must be a number.
        optimize must be 'time' or 'cost'.
        limit values must be numbers.
        """
        for m_id, m in self.ctx.missions.items():
            props = self._get(m, 'props') or m

            # start_time
            start_time = self._get(props, 'start_time')
            if start_time is not None:
                if not _TIME_RE.match(str(start_time)):
                    self.error(
                        f"Mission '{m_id}'.start_time='{start_time}' "
                        f"is not a valid time (expected HH:MM)."
                    )

            # alpha
            alpha = self._get(props, 'alpha')
            if alpha is not None and not self._is_number(alpha):
                self.error(
                    f"Mission '{m_id}'.alpha must be a number, "
                    f"got '{alpha}'."
                )

            # optimize
            optimize = self._get(props, 'optimize')
            if optimize is not None and str(optimize) not in _OPTIMIZE_VALUES:
                self.error(
                    f"Mission '{m_id}'.optimize='{optimize}' is invalid. "
                    f"Must be one of: {sorted(_OPTIMIZE_VALUES)}."
                )

            # limit values (limit payload: X, limit budget: X)
            for limit_key in ('limit_payload', 'limit_budget', 'payload', 'budget'):
                val = self._get(props, limit_key)
                if val is not None and not self._is_number(val):
                    self.error(
                        f"Mission '{m_id}'.limit {limit_key}='{val}' "
                        f"must be a number."
                    )
                elif val is not None and float(val) <= 0:
                    self.error(
                        f"Mission '{m_id}'.limit {limit_key}={val} "
                        f"must be > 0."
                    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_number(val) -> bool:
        """True if val is an int, float, or a string that parses as one."""
        if isinstance(val, (int, float)):
            return True
        try:
            float(str(val))
            return True
        except (ValueError, TypeError):
            return False
