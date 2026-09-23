"""What a :class:`~mikeio1d.network.Network` is built on, and read through.

A network is a topology plus a way of answering about it afterwards: what the
period is, what quantities exist, what a location carries, and - the one
expensive question - what a series actually holds. :class:`_Source` is that
contract. A network is constructed from one and keeps it for its lifetime, so
the topology and the answers can never come from two different places.

The contract names no file anywhere, deliberately. The only implementation
today is :class:`~mikeio1d.network._res1d._Res1DSource`, which reads a result
file, but a source over reaches already in memory would answer the same
questions from the frames it was handed. Keeping ``Res1D`` out of the five
members below is what leaves that open.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime

    import pandas as pd

    from ._naming import Alias
    from ._types import NetworkReach

from abc import ABC, abstractmethod


class _Source(ABC):
    """Everything a :class:`~mikeio1d.network.Network` needs behind it.

    Five members: one that gives the network its shape, three that answer about
    it without touching timeseries, and one that reads them.
    """

    @abstractmethod
    def build(self) -> Sequence[NetworkReach]:
        """Give the reaches the network is made of.

        Called once, from the constructor. The reaches must not be retained
        afterwards: a network deep-copies them and shares its source, so a
        source holding on to them would leave a copy's two views of its own
        reaches pointing at different objects.
        """

    @property
    @abstractmethod
    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep available, without reading any of them."""

    @property
    @abstractmethod
    def units(self) -> Mapping[str, str]:
        """Unit abbreviation per quantity ID, for every quantity named anywhere."""

    @abstractmethod
    def quantities_at(self, alias: Alias) -> list[str] | None:
        """Quantity IDs readable at one location, or None if it has no series.

        An empty list and ``None`` are different answers: the first is a
        location carrying nothing, which is every node of a MIKE 11 result; the
        second is a location this source never saw.
        """

    @abstractmethod
    def read(self, items: Sequence[tuple[Alias, str]]) -> pd.DataFrame:
        """Read the series named by ``(alias, quantity)`` pairs.

        The returned frame has one column per element of ``items``, in that
        order and keeping duplicates, so a caller can line the columns up with
        whatever it asked for. Each distinct series is read once however often
        it was asked for.

        The aliases are the source's own spelling, as
        :meth:`quantities_at` keys them - a caller resolves an address before
        getting here, and every pair is one :meth:`quantities_at` confirmed.
        """
