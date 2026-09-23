"""The result files a :class:`~mikeio1d.network.Network` was opened from.

A network keeps the files it came from so that it can answer about them after
the open: what the period is, what quantities exist, what a location carries,
and - the one expensive question - what a series actually holds.

The series themselves are addressed by :class:`~mikeio1d.quantities.TimeSeriesId`
rather than by the ``ResultQuantity`` objects they came from. Loading a
companion's dynamic data replaces the whole ``ResultNetwork`` it hangs off
(see ``ResultReader._load_file``), so any quantity object captured before that
point is a stale handle onto a discarded object graph. A ``TimeSeriesId`` is
inert, and every read looks it up afresh.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from ..res1d import Res1D
    from ..quantities import TimeSeriesId
    from ._naming import Alias


@dataclass(frozen=True)
class _Series:
    """One timeseries, and the file it has to be read from."""

    res: Res1D
    tsid: TimeSeriesId


class _Source:
    """The files a network was opened from, and where each series sits in them.

    Parameters
    ----------
    res : Res1D
        The main result file.
    items : Mapping[Alias, Mapping[str, _Series]]
        Every addressable location, mapped to the series it carries by quantity
        ID. Built during the load, since only there is it known which gridpoint
        a break point was made from.
    companion : Res1D or None, optional
        The ``.resx`` read alongside, if there was one. Its quantities are in
        ``items`` like any other, but its header is needed for their units.
    """

    def __init__(
        self,
        res: Res1D,
        items: Mapping[Alias, Mapping[str, _Series]],
        companion: Res1D | None = None,
    ) -> None:
        self._res = res
        self._items = items
        self._companion = companion

    @property
    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep of the main result file."""
        return self._res.start_time, self._res.end_time

    @property
    def units(self) -> dict[str, str]:
        """Unit abbreviation per quantity ID, over the main file and companion.

        The main file wins where both spell the same quantity, since it is the
        one the network was opened from.
        """
        units: dict[str, str] = {}
        for res in (self._companion, self._res):
            if res is None:
                continue
            for quantity in res.result_data.Quantities:
                units[str(quantity.Id)] = str(quantity.EumQuantity.UnitAbbreviation)
        return units

    def quantities_at(self, alias: Alias) -> list[str] | None:
        """Quantity IDs readable at one location, or None if it has no series.

        An empty list and ``None`` are different answers: the first is a
        location carrying nothing, which is every node of a MIKE 11 result; the
        second is a location this source never saw.
        """
        carried = self._items.get(alias)
        return None if carried is None else list(carried)

    def series_at(self, alias: Alias, quantity: str) -> _Series | None:
        """Give the series for one quantity at one location, or None if absent."""
        return self._items.get(alias, {}).get(quantity)

    def read(self, series: Sequence[_Series]) -> pd.DataFrame:
        """Read the given series, one batched call per file they live in.

        The returned frame has one column per element of ``series``, in that
        order and keeping duplicates, so a caller can line the columns up with
        whatever it asked for. Each distinct series is read once however often
        it was asked for - an EPANET reach's two break points name the same
        gridpoint, so asking for both is one read, not two.
        """
        if not series:
            # Nothing asked for, nothing opened. The file's own time index would
            # be the tidier index to carry here, but reading it loads the whole
            # of the file's dynamic data, which is the one thing asking for
            # nothing should not do.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        # Grouped by file, and within a file de-duplicated, so what crosses the
        # interop boundary is each distinct series exactly once.
        by_file: dict[int, tuple[Res1D, list[TimeSeriesId]]] = {}
        for item in series:
            _, tsids = by_file.setdefault(id(item.res), (item.res, []))
            if item.tsid not in tsids:
                tsids.append(item.tsid)

        columns: dict[tuple[int, TimeSeriesId], pd.Series] = {}
        for res, tsids in by_file.values():
            frame = res.read(tsids, column_mode="timeseries")
            for tsid, (_, column) in zip(tsids, frame.items()):
                columns[(id(res), tsid)] = column

        return pd.concat(
            [columns[(id(item.res), item.tsid)] for item in series],
            axis=1,
            keys=range(len(series)),
        )
