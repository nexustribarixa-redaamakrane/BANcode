"""BANcode warncode codes"""

from enum import IntEnum

class WARNcode(IntEnum):
    """Non-fatal telemetry; threshold alerts, degraded performance, predictive maintenance. May be printable; useful when showing the glyph of the error, not just its codename or codepoint."""


    @classmethod
    def from_value(cls, val):
        try:
            return cls(val)
        except ValueError:
            return None

