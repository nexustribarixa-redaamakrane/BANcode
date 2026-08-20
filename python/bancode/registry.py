"""BANcode master registry lookup."""

from dataclasses import dataclass
from typing import Optional
from bancode.bancode import BANcode
from bancode.warncode import WARNcode
from bancode.comcode import COMcode
from bancode.softcode import SOFTcode


@dataclass
class CodeEntry:
    """Complete metadata for a single BANcode."""
    hex_value: str
    value: int
    name: str
    category: str
    subcategory: str
    description: str


class BANcodeRegistry:
    """Singleton registry for all BANcode codes."""

    _instance = None
    _codes = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        codes = {
        }
        self._codes = codes

    def lookup(self, code):
        """Look up a code by int value. Returns CodeEntry or None."""
        return self._codes.get(code)

    def name(self, code):
        """Return codename string or 'UNKNOWN'."""
        entry = self._codes.get(code)
        return entry.name if entry else "UNKNOWN"

    def is_valid(self, code):
        """Return True if code is a known BANcode."""
        return code in self._codes

    @property
    def all_codes(self):
        return list(self._codes.values())
