"""The Marker enum and related functions."""

from __future__ import annotations

from enum import IntEnum

from typing import List


class Marker(IntEnum):
    """The standard markers used in cross sections.

    Notes
    -----
    User markers are integers greater than 7. They are specified as an integer, not an enum.

    """

    LEFT_LEVEE_BANK = 1
    LOWEST_POINT = 2
    RIGHT_LEVEE_BANK = 3
    LEFT_LOW_FLOW_BANK = 4
    RIGHT_LOW_FLOW_BANK = 5

    def __repr__(self) -> str:
        """Return a string representation of the marker."""
        return Marker.pretty(self)

    def __int__(self) -> int:
        """Return the integer value of the marker."""
        return self.value

    @staticmethod
    def is_default_marker(marker: int | Marker) -> bool:
        """Check if the int/Marker is a default marker (e.g. left levee bank)."""
        marker = int(marker)
        return marker in (e.value for e in Marker)

    @staticmethod
    def is_user_marker(marker: int | Marker) -> bool:
        """Check if the int/Marker is a user marker (i.e. value > 7)."""
        MIN_USER_MARKER = 8
        return marker >= MIN_USER_MARKER

    @staticmethod
    def pretty(marker: int | Marker) -> str:
        """Get a pretty string presentation of the marker."""
        if Marker.is_default_marker(marker):
            marker = marker if isinstance(marker, Marker) else Marker(marker)
            return marker.name.replace("_", " ").title() + f" ({marker.value})"
        elif Marker.is_user_marker(marker):
            return f"User Marker ({marker})"
        else:
            return f"Unknown Marker ({marker})"

    @staticmethod
    def from_pretty(marker: str) -> int:
        """Parse a string created from Marker.pretty to the corresponding marker value."""
        marker = int(marker.split("(")[-1][:-1])
        return marker

    @staticmethod
    def list_from_string(s: str) -> List[int]:
        """Convert a string of comma-separated markers to a list of integers."""
        return [int(m) for m in s.split(",")]
