"""BANcode softcode codes"""

from enum import IntEnum

class SOFTcode(IntEnum):
    """Soft recovery, fault containment, cache reconciliation, self-healing routines; also soft errors. May be printable; useful when showing the glyph of the error, not just its codename or codepoint."""


    @classmethod
    def from_value(cls, val):
        try:
            return cls(val)
        except ValueError:
            return None

