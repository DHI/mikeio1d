from __future__ import annotations

from enum import Enum

from typing import List


class Marker(Enum):
    LEFT_LEVEE_BANK = 1
    LOWEST_POINT = 2
    RIGHT_LEVEE_BANK = 3
    LEFT_LOW_FLOW_BANK = 4
    RIGHT_LOW_FLOW_BANK = 5

    def __repr__(self) -> str:
        return Marker.pretty(self)

    def __int__(self) -> int:
        return self.value

    @staticmethod
    def is_default_marker(marker: int | Marker) -> bool:
        return marker in Marker

    @staticmethod
    def is_user_marker(marker: int | Marker) -> bool:
        MIN_USER_MARKER = 8
        return marker >= MIN_USER_MARKER

    @staticmethod
    def pretty(marker: int | Marker) -> str:
        if Marker.is_default_marker(marker):
            marker = marker if isinstance(marker, Marker) else Marker(marker)
            return marker.name.replace("_", " ").title() + f" ({marker.value})"
        elif Marker.is_user_marker(marker):
            return f"User Marker ({marker})"
        else:
            return f"Unknown Marker ({marker})"

    @staticmethod
    def from_pretty(marker: str) -> int:
        marker = int(marker.split("(")[-1][:-1])
        return marker

    @staticmethod
    def list_from_string(s: str) -> List[int]:
        return [int(m) for m in s.split(",")]
