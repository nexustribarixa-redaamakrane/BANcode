"""BANcode bancode codes"""

from enum import IntEnum

class BANcode(IntEnum):
    """Unrecoverable critical panics, hardware faults, fatal exceptions. May be printable; useful when showing the glyph of the error, not just its codename or codepoint."""


    @classmethod
    def from_value(cls, val):
        try:
            return cls(val)
        except ValueError:
            return None

