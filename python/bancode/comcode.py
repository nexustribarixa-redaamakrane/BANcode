"""BANcode comcode codes"""

from enum import IntEnum

class COMcode(IntEnum):
    """IPC events, bus orchestration, hardware handshakes, driver attachment, control plane signals; also success reports. May be printable; useful when showing the glyph of the error, not just its codename or codepoint."""


    @classmethod
    def from_value(cls, val):
        try:
            return cls(val)
        except ValueError:
            return None

